"""Bounded structural validation and diagnostics for local teaching plans."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import defaultdict

from .models import Page, Region


ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
SOURCE_REF_RE = re.compile(r"^([pr])([1-9][0-9]*)$")
PAUSE_RE = re.compile(r"\bpause\s+(?:here|now)\b", re.IGNORECASE)
SUPPORTED_VISUAL_KINDS = {
    "text", "equation", "plot", "geometry", "process", "circuit", "bus", "timing", "source_image",
}
MAX_PLAN_BYTES = 512 * 1024
MAX_DATABASE_ID = 2**63 - 1


class TeachingPlanShapeError(ValueError):
    def __init__(self, errors):
        super().__init__(errors[0]["message"] if errors else "Invalid teaching plan.")
        self.errors = errors


def _shape_error(path, message, code="invalid_teaching_plan"):
    raise TeachingPlanShapeError([{"code": code, "path": path, "message": message}])


def _closed_record(value, path, fields):
    if not isinstance(value, dict):
        _shape_error(path, "Expected an object.")
    missing = fields - set(value)
    if missing:
        name = sorted(missing)[0]
        _shape_error(f"{path}.{name}" if path else name, "This field is required.")
    unknown = set(value) - fields
    if unknown:
        name = sorted(unknown)[0]
        _shape_error(f"{path}.{name}" if path else name, "Unknown field.")


def _array(value, path, limit):
    if not isinstance(value, list):
        _shape_error(path, "Expected an array.")
    if len(value) > limit:
        _shape_error(path, f"At most {limit} items are allowed.", "teaching_plan_limit_exceeded")
    return value


def _string(value, path, limit, *, identifier=False, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()) or len(value) > limit:
        qualifier = "possibly empty " if allow_empty else "non-empty "
        _shape_error(path, f"Expected a {qualifier}string of at most {limit} characters.")
    if identifier and not ID_RE.fullmatch(value):
        _shape_error(path, "Use an ID that starts with a letter and contains only letters, numbers, '_' or '-'.")
    return value


def _unique(values, path, label):
    seen = set()
    for index, value in enumerate(values):
        if value in seen:
            _shape_error(f"{path}.{index}", f"Duplicate {label}: {value}.", "duplicate_teaching_plan_id")
        seen.add(value)


def _id_array(value, path, limit):
    result = _array(value, path, limit)
    for index, item in enumerate(result):
        _string(item, f"{path}.{index}", 64, identifier=True)
    _unique(result, path, "reference")
    return result


def validate_teaching_plan_shape(plan):
    """Validate the closed v1 record and return an isolated copy."""
    try:
        encoded = json.dumps(plan, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        _shape_error("teaching_plan", "Teaching plan must be JSON data.")
    if len(encoded) > MAX_PLAN_BYTES:
        _shape_error("teaching_plan", "Teaching plan must be at most 512 KiB.", "teaching_plan_limit_exceeded")
    _closed_record(plan, "teaching_plan", {"version", "goals", "assumed_prerequisites", "scenes"})
    if isinstance(plan["version"], bool) or not isinstance(plan["version"], int) or plan["version"] != 1:
        _shape_error("teaching_plan.version", "Only teaching plan version 1 is supported.")

    goals = _array(plan["goals"], "teaching_plan.goals", 40)
    goal_ids = []
    for index, goal in enumerate(goals):
        path = f"teaching_plan.goals.{index}"
        _closed_record(goal, path, {"id", "text", "requires"})
        goal_ids.append(_string(goal["id"], f"{path}.id", 64, identifier=True))
        _string(goal["text"], f"{path}.text", 600)
        _id_array(goal["requires"], f"{path}.requires", 40)
    _unique(goal_ids, "teaching_plan.goals", "goal ID")

    assumptions = _array(plan["assumed_prerequisites"], "teaching_plan.assumed_prerequisites", 40)
    assumption_ids = []
    for index, assumption in enumerate(assumptions):
        path = f"teaching_plan.assumed_prerequisites.{index}"
        _closed_record(assumption, path, {"id", "text"})
        assumption_ids.append(_string(assumption["id"], f"{path}.id", 64, identifier=True))
        _string(assumption["text"], f"{path}.text", 600)
    _unique(assumption_ids, "teaching_plan.assumed_prerequisites", "assumption ID")
    overlap = set(goal_ids) & set(assumption_ids)
    if overlap:
        _shape_error("teaching_plan.assumed_prerequisites", f"Goal and assumption IDs must be distinct: {sorted(overlap)[0]}.", "duplicate_teaching_plan_id")

    scenes = _array(plan["scenes"], "teaching_plan.scenes", 288)
    scene_ids = []
    check_ids = []
    for index, scene in enumerate(scenes):
        path = f"teaching_plan.scenes.{index}"
        _closed_record(scene, path, {"scene_id", "goal_ids", "evidence", "visual_requests", "checks"})
        scene_ids.append(_string(scene["scene_id"], f"{path}.scene_id", 64, identifier=True))
        _id_array(scene["goal_ids"], f"{path}.goal_ids", 40)

        evidence = _array(scene["evidence"], f"{path}.evidence", 20)
        evidence_refs = []
        for evidence_index, item in enumerate(evidence):
            item_path = f"{path}.evidence.{evidence_index}"
            _closed_record(item, item_path, {"source_ref", "fingerprint"})
            source_ref = _string(item["source_ref"], f"{item_path}.source_ref", 160)
            if not SOURCE_REF_RE.fullmatch(source_ref):
                _shape_error(f"{item_path}.source_ref", "Use a page or region reference such as p12 or r3.")
            evidence_refs.append(source_ref)
            _string(item["fingerprint"], f"{item_path}.fingerprint", 128)
        _unique(evidence_refs, f"{path}.evidence", "source reference")

        visuals = _array(scene["visual_requests"], f"{path}.visual_requests", 6)
        visual_ids = []
        for visual_index, item in enumerate(visuals):
            item_path = f"{path}.visual_requests.{visual_index}"
            _closed_record(item, item_path, {"object_id", "kind", "purpose"})
            visual_ids.append(_string(item["object_id"], f"{item_path}.object_id", 64, identifier=True))
            _string(item["kind"], f"{item_path}.kind", 64)
            _string(item["purpose"], f"{item_path}.purpose", 600)
        _unique(visual_ids, f"{path}.visual_requests", "visual object ID")

        checks = _array(scene["checks"], f"{path}.checks", 6)
        for check_index, item in enumerate(checks):
            item_path = f"{path}.checks.{check_index}"
            _closed_record(item, item_path, {"id", "goal_ids", "question", "expected_reasoning"})
            check_ids.append(_string(item["id"], f"{item_path}.id", 64, identifier=True))
            _id_array(item["goal_ids"], f"{item_path}.goal_ids", 40)
            _string(item["question"], f"{item_path}.question", 600)
            _string(item["expected_reasoning"], f"{item_path}.expected_reasoning", 2000)
    _unique(scene_ids, "teaching_plan.scenes", "scene ID")
    _unique(check_ids, "teaching_plan.scenes", "check ID")
    return copy.deepcopy(plan)


def _canonical_fingerprint(data):
    value = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _page_fingerprint(page):
    return _canonical_fingerprint({
        "v": 1,
        "source_digest": page.source.digest,
        "page": {"id": page.id, "source_id": page.source_id, "number": page.number},
        "text": page.text,
    })


def _region_fingerprint(region):
    page = region.page
    return _canonical_fingerprint({
        "v": 1,
        "source_digest": page.source.digest,
        "page": {"id": page.id, "source_id": page.source_id, "number": page.number},
        "page_text": page.text,
        "region": {
            "id": region.id,
            "text": region.text,
            "geometry": [region.x, region.y, region.width, region.height],
        },
    })


def evidence_state(source_refs, course_id):
    """Resolve source refs in bounded batches and identify missing/foreign refs."""
    page_ids, region_ids = set(), set()
    for source_ref in source_refs:
        match = SOURCE_REF_RE.fullmatch(source_ref) if isinstance(source_ref, str) else None
        if not match:
            continue
        object_id = int(match.group(2))
        if object_id <= MAX_DATABASE_ID:
            (page_ids if match.group(1) == "p" else region_ids).add(object_id)
    pages = {page.id: page for page in Page.objects.filter(pk__in=page_ids).select_related("source")}
    regions = {region.id: region for region in Region.objects.filter(pk__in=region_ids).select_related("page__source")}
    result = {}
    for source_ref in source_refs:
        match = SOURCE_REF_RE.fullmatch(source_ref) if isinstance(source_ref, str) else None
        if not match:
            result[source_ref] = {"state": "missing"}
            continue
        object_id = int(match.group(2))
        item = None if object_id > MAX_DATABASE_ID else pages.get(object_id) if match.group(1) == "p" else regions.get(object_id)
        if item is None:
            result[source_ref] = {"state": "missing"}
            continue
        item_course_id = item.source.course_id if match.group(1) == "p" else item.page.source.course_id
        if item_course_id != course_id:
            result[source_ref] = {"state": "foreign"}
            continue
        fingerprint = _page_fingerprint(item) if match.group(1) == "p" else _region_fingerprint(item)
        result[source_ref] = {"state": "valid", "fingerprint": fingerprint}
    return result


def _issue(code, severity, path, message, **context):
    return {"code": code, "severity": severity, "path": path, "message": message} | {
        key: value for key, value in context.items() if value is not None
    }


def _spec_maps(spec):
    scene_map = {}
    chapter_map = {}
    ordered_scenes = []
    for chapter_index, chapter in enumerate(spec.get("chapters", [])):
        chapter_map[chapter.get("id")] = chapter
        for scene_index, scene in enumerate(chapter.get("scenes", [])):
            scene_map[scene.get("id")] = scene
            ordered_scenes.append((chapter_index, scene_index, scene))
    return scene_map, chapter_map, ordered_scenes


def _goal_cycles(plan):
    goal_ids = {goal["id"] for goal in plan["goals"]}
    edges = {goal["id"]: [item for item in goal["requires"] if item in goal_ids] for goal in plan["goals"]}
    visiting, visited, cycles = set(), set(), set()

    def visit(goal_id):
        if goal_id in visiting:
            cycles.add(goal_id)
            return True
        if goal_id in visited:
            return False
        visiting.add(goal_id)
        in_cycle = False
        for required in edges[goal_id]:
            if visit(required):
                cycles.add(goal_id)
                in_cycle = True
        visiting.remove(goal_id)
        visited.add(goal_id)
        return in_cycle

    for goal_id in edges:
        visit(goal_id)
    return cycles


def _manifest_data(manifest, valid_scene_ids):
    if not isinstance(manifest, dict):
        return [], [], []
    manifest_scenes = manifest.get("scenes") if isinstance(manifest.get("scenes"), list) else []
    intervals = []
    for item in manifest_scenes:
        if not isinstance(item, dict) or item.get("scene_id") not in valid_scene_ids:
            continue
        start, end = item.get("start_seconds"), item.get("end_seconds")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (start, end)) or end <= start:
            continue
        intervals.append((item["scene_id"], float(start), float(end)))
    practices = []
    raw_practice = manifest.get("practice") if isinstance(manifest.get("practice"), list) else []
    for index, item in enumerate(raw_practice):
        if not isinstance(item, dict):
            continue
        practice_id = item.get("id")
        scene_id = item.get("scene_id")
        seconds = item.get("time_seconds")
        if not isinstance(practice_id, str) or not practice_id or practice_id in {practice["id"] for practice in practices}:
            continue
        if scene_id not in valid_scene_ids and not isinstance(seconds, bool) and isinstance(seconds, (int, float)) and math.isfinite(seconds):
            scene_id = next((candidate for candidate, start, end in intervals if start <= seconds <= end), None)
        if scene_id in valid_scene_ids:
            practices.append({"id": practice_id, "scene_id": scene_id})
    cues = manifest.get("cues") if isinstance(manifest.get("cues"), list) else []
    return intervals, practices, cues


def _pause_gap_issues(intervals, practices, cues, valid_scene_ids):
    practice_scene_ids = {practice["scene_id"] for practice in practices}
    issues = []
    for cue_index, cue in enumerate(cues):
        if not isinstance(cue, dict) or not isinstance(cue.get("text"), str) or not PAUSE_RE.search(cue["text"]):
            continue
        start, end = cue.get("start_seconds"), cue.get("end_seconds")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (start, end)) or end <= start:
            continue
        scene_id = cue.get("scene_id") if cue.get("scene_id") in valid_scene_ids else None
        if scene_id is None and isinstance(cue.get("id"), str):
            scene_id = next((candidate for candidate in valid_scene_ids if cue["id"] == candidate or cue["id"].startswith(candidate + "-")), None)
        if scene_id is None:
            scene_id = next((candidate for candidate, scene_start, scene_end in intervals if scene_start <= start and end <= scene_end + 1e-6), None)
        if scene_id and scene_id not in practice_scene_ids:
            issues.append(_issue("spoken_pause_without_checkpoint", "warning", f"manifest.cues.{cue_index}", "Spoken pause cue has no installed checkpoint in its scene.", scene_id=scene_id, start_seconds=float(start), end_seconds=float(end)))
    return issues


def teaching_plan_report(spec, plan, course_id, manifest=None, *, media_status="draft_not_rendered"):
    """Return structural planning findings; this is not a scientific review."""
    scene_map, _, ordered_scenes = _spec_maps(spec)
    valid_scene_ids = set(scene_map)
    issues = []
    incomplete = False

    for chapter_index, chapter in enumerate(spec.get("chapters", [])):
        if not isinstance(chapter.get("objective"), str) or not chapter.get("objective", "").strip():
            issues.append(_issue("missing_chapter_objective", "warning", f"spec.chapters.{chapter_index}.objective", "Add a chapter objective."))
            incomplete = True
        for scene_index, scene in enumerate(chapter.get("scenes", [])):
            if not isinstance(scene.get("objective"), str) or not scene.get("objective", "").strip():
                issues.append(_issue("missing_scene_objective", "warning", f"spec.chapters.{chapter_index}.scenes.{scene_index}.objective", "Add a scene objective.", scene_id=scene.get("id")))
                incomplete = True

    all_spec_refs = []
    spec_ref_occurrences = []
    for chapter_index, scene_index, scene in ordered_scenes:
        for ref_index, source_ref in enumerate(scene.get("source_refs", [])):
            if source_ref not in all_spec_refs:
                all_spec_refs.append(source_ref)
            spec_ref_occurrences.append((source_ref, f"spec.chapters.{chapter_index}.scenes.{scene_index}.source_refs.{ref_index}", scene.get("id")))
    plan_refs = [] if plan is None else [item["source_ref"] for scene in plan["scenes"] for item in scene["evidence"]]
    states = evidence_state(list(dict.fromkeys(all_spec_refs + plan_refs)), course_id)
    evidence_bindings = [
        {"source_ref": source_ref, "fingerprint": states[source_ref]["fingerprint"]}
        for source_ref in all_spec_refs if states.get(source_ref, {}).get("state") == "valid"
    ]
    for source_ref, path, scene_id in spec_ref_occurrences:
        state = states.get(source_ref, {}).get("state")
        if state == "foreign":
            issues.append(_issue("foreign_source_ref", "error", path, "Source reference belongs to another course.", scene_id=scene_id))
        elif state == "missing":
            issues.append(_issue("unknown_source_ref", "error", path, "Source reference does not exist.", scene_id=scene_id))

    intervals, practices, cues = _manifest_data(manifest, valid_scene_ids)
    pause_issues = _pause_gap_issues(intervals, practices, cues, valid_scene_ids)

    if plan is None:
        issues.insert(0, _issue("missing_teaching_plan", "warning", "teaching_plan", "No teaching plan is saved for this revision."))
        issues.extend(pause_issues)
        return {
            "plan_status": "missing",
            "can_save": not any(issue["severity"] == "error" for issue in issues),
            "issues": issues,
            "coverage": [],
            "evidence_bindings": evidence_bindings,
            "media_status": media_status,
        }

    goal_ids = {goal["id"] for goal in plan["goals"]}
    assumption_ids = {assumption["id"] for assumption in plan["assumed_prerequisites"]}
    if not goal_ids:
        issues.append(_issue("missing_goals", "warning", "teaching_plan.goals", "Add at least one teaching goal."))
        incomplete = True
    for goal_index, goal in enumerate(plan["goals"]):
        for required_index, required in enumerate(goal["requires"]):
            if required not in goal_ids | assumption_ids:
                issues.append(_issue("unknown_prerequisite", "error", f"teaching_plan.goals.{goal_index}.requires.{required_index}", "Prerequisite must name a goal or explicit assumption.", goal_id=goal["id"]))
    for goal_id in sorted(_goal_cycles(plan)):
        issues.append(_issue("goal_dependency_cycle", "error", "teaching_plan.goals", "Goal prerequisites must not contain a cycle.", goal_id=goal_id))

    plan_scene_map = {scene["scene_id"]: (index, scene) for index, scene in enumerate(plan["scenes"])}
    explanations = defaultdict(list)
    planned_checks = defaultdict(list)
    for scene_index, plan_scene in enumerate(plan["scenes"]):
        scene_id = plan_scene["scene_id"]
        path = f"teaching_plan.scenes.{scene_index}"
        spec_scene = scene_map.get(scene_id)
        if spec_scene is None:
            issues.append(_issue("unknown_scene", "error", f"{path}.scene_id", "Scene does not exist in this storyboard.", scene_id=scene_id))
        for goal_index, goal_id in enumerate(plan_scene["goal_ids"]):
            if goal_id not in goal_ids:
                issues.append(_issue("unknown_goal", "error", f"{path}.goal_ids.{goal_index}", "Scene references an unknown goal.", scene_id=scene_id, goal_id=goal_id))
            elif spec_scene is not None:
                explanations[goal_id].append(scene_id)

        spec_refs = set(spec_scene.get("source_refs", [])) if spec_scene else set()
        mapped_refs = set()
        for evidence_index, evidence in enumerate(plan_scene["evidence"]):
            source_ref = evidence["source_ref"]
            evidence_path = f"{path}.evidence.{evidence_index}"
            mapped_refs.add(source_ref)
            if source_ref not in spec_refs:
                issues.append(_issue("evidence_not_in_scene", "error", f"{evidence_path}.source_ref", "Evidence must also appear in the storyboard scene source_refs.", scene_id=scene_id))
            state = states.get(source_ref, {}).get("state")
            if state == "foreign":
                issues.append(_issue("foreign_source_ref", "error", f"{evidence_path}.source_ref", "Evidence belongs to another course.", scene_id=scene_id))
            elif state == "missing":
                issues.append(_issue("unknown_source_ref", "error", f"{evidence_path}.source_ref", "Evidence does not exist.", scene_id=scene_id))
            elif evidence["fingerprint"] != states[source_ref]["fingerprint"]:
                issues.append(_issue("stale_evidence_fingerprint", "error", f"{evidence_path}.fingerprint", "Evidence changed after it was bound. Rebind the current evidence explicitly.", scene_id=scene_id))
        if spec_scene is not None:
            for source_ref in spec_scene.get("source_refs", []):
                if source_ref not in mapped_refs:
                    issues.append(_issue("missing_evidence_mapping", "warning", f"{path}.evidence", f"Bind current evidence {source_ref} to this scene.", scene_id=scene_id))
                    incomplete = True

        objects = {item.get("id"): item for item in spec_scene.get("objects", [])} if spec_scene else {}
        requested = set()
        for visual_index, visual in enumerate(plan_scene["visual_requests"]):
            visual_path = f"{path}.visual_requests.{visual_index}"
            requested.add(visual["object_id"])
            obj = objects.get(visual["object_id"])
            if visual["kind"] not in SUPPORTED_VISUAL_KINDS:
                issues.append(_issue("unsupported_visual_kind", "error", f"{visual_path}.kind", "Visual kind is not supported by the renderer.", scene_id=scene_id))
            if obj is None:
                issues.append(_issue("unknown_visual_object", "error", f"{visual_path}.object_id", "Visual request must name an object in this scene.", scene_id=scene_id))
            elif visual["kind"] != obj.get("kind"):
                issues.append(_issue("visual_kind_mismatch", "error", f"{visual_path}.kind", "Visual request kind must match the storyboard object.", scene_id=scene_id))
        for object_id in objects:
            if object_id not in requested:
                issues.append(_issue("missing_visual_request", "warning", f"{path}.visual_requests", "Describe the teaching purpose of this scene object.", scene_id=scene_id))
                incomplete = True

        for check_index, check in enumerate(plan_scene["checks"]):
            check_path = f"{path}.checks.{check_index}"
            for goal_index, goal_id in enumerate(check["goal_ids"]):
                if goal_id not in goal_ids:
                    issues.append(_issue("unknown_goal", "error", f"{check_path}.goal_ids.{goal_index}", "Check references an unknown goal.", scene_id=scene_id, goal_id=goal_id))
                elif goal_id not in plan_scene["goal_ids"]:
                    issues.append(_issue("check_goal_not_in_scene", "error", f"{check_path}.goal_ids.{goal_index}", "Check goals must be assigned to the same scene.", scene_id=scene_id, goal_id=goal_id))
                elif spec_scene is not None:
                    planned_checks[goal_id].append(check["id"])

    for _, _, spec_scene in ordered_scenes:
        planned = plan_scene_map.get(spec_scene["id"])
        if planned is None or not planned[1]["goal_ids"]:
            issues.append(_issue("missing_scene_assignment", "warning", "teaching_plan.scenes", "Assign at least one teaching goal to this scene.", scene_id=spec_scene["id"]))
            incomplete = True
        if planned is None:
            for source_ref in spec_scene.get("source_refs", []):
                issues.append(_issue("missing_evidence_mapping", "warning", "teaching_plan.scenes", f"Bind current evidence {source_ref} to this scene.", scene_id=spec_scene["id"]))
                incomplete = True
            for _ in spec_scene.get("objects", []):
                issues.append(_issue("missing_visual_request", "warning", "teaching_plan.scenes", "Describe the teaching purpose of this scene object.", scene_id=spec_scene["id"]))
                incomplete = True

    practice_by_scene = defaultdict(list)
    for practice in practices:
        practice_by_scene[practice["scene_id"]].append(practice["id"])
    coverage = []
    for goal in plan["goals"]:
        goal_id = goal["id"]
        goal_scenes = explanations[goal_id]
        goal_checks = planned_checks[goal_id]
        installed = [practice_id for scene_id in goal_scenes for practice_id in practice_by_scene.get(scene_id, [])]
        coverage.append({
            "goal_id": goal_id,
            "explanation_scene_ids": goal_scenes,
            "planned_check_ids": goal_checks,
            "installed_practice_ids": installed,
        })
        if not goal_scenes:
            issues.append(_issue("missing_goal_explanation", "warning", "teaching_plan.scenes", "Assign this goal to at least one explanation scene.", goal_id=goal_id))
            incomplete = True
        if not goal_checks:
            issues.append(_issue("missing_goal_check", "warning", "teaching_plan.scenes", "Add a planned check for this goal.", goal_id=goal_id))
            incomplete = True

    issues.extend(pause_issues)

    has_errors = any(issue["severity"] == "error" for issue in issues)
    return {
        "plan_status": "incomplete" if incomplete or has_errors else "complete",
        "can_save": not has_errors,
        "issues": issues,
        "coverage": coverage,
        "evidence_bindings": evidence_bindings,
        "media_status": media_status,
    }

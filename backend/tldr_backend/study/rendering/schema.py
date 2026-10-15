"""Closed lesson language: bounded math notation, never programs or file paths."""
from __future__ import annotations

import copy
import math
import re

ID = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,63}$"}
TEXT = {"type": "string", "minLength": 1, "maxLength": 600}
NUMBER = {"type": "number", "minimum": -1e9, "maximum": 1e9}
NORMALIZED = {"type": "number", "minimum": 0, "maximum": 1}


def record(properties, required):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": required}


OBJECT = record({
    "id": ID, "kind": {"enum": ["text", "equation", "plot", "geometry", "process", "circuit", "bus", "timing", "source_image"]},
    "label": TEXT, "text": TEXT, "latex": dict(TEXT, description="Optional math-only LaTeX on equation objects, without delimiters. Keep text as the readable fallback. Supports bounded fractions, roots, calculus, matrices, aligned and cases; no macros, files, HTML or extension loading."),
    "points": {"type": "array", "minItems": 2, "maxItems": 200, "items": {"type": "array", "items": NUMBER, "minItems": 2, "maxItems": 2}},
    "shape": {"enum": ["circle", "rectangle", "triangle"]},
    "nodes": {"type": "array", "minItems": 2, "maxItems": 5, "items": {"type": "string", "minLength": 1, "maxLength": 60}},
    "signals": {"type": "array", "minItems": 1, "maxItems": 5, "items": record({"name": TEXT, "values": {"type": "array", "items": {"enum": [0, 1]}, "minItems": 2, "maxItems": 24}}, ["name", "values"])},
    "source_ref": {"type": "string", "pattern": "^[pr][1-9][0-9]*$"},
    "overlays": {"type": "array", "maxItems": 12, "items": record({"x": NORMALIZED, "y": NORMALIZED, "width": NORMALIZED, "height": NORMALIZED}, ["x", "y", "width", "height"])},
    "calculation": record({"kind": {"enum": ["bus_read", "ohms_law", "ohms_law_plot", "compound_interest", "quadratic", "quadratic_plot", "biology_concept"]}, "inputs": {"type": "object", "maxProperties": 8, "additionalProperties": {"anyOf": [NUMBER, {"type": "string", "maxLength": 100}]}}}, ["kind", "inputs"]),
}, ["id", "kind", "label"])
OBJECT["allOf"] = [{"if": {"properties": {"kind": {"enum": ["bus", "circuit"]}}}, "then": {"properties": {"nodes": {"minItems": 2, "maxItems": 2}}}}]
SCENE = record({
    "id": ID, "title": TEXT, "narration": {"type": "string", "minLength": 20, "maxLength": 12000},
    "objective": TEXT,
    "source_refs": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 160}, "maxItems": 20},
    "objects": {"type": "array", "items": OBJECT, "minItems": 1, "maxItems": 6},
    "steps": {"type": "array", "minItems": 1, "maxItems": 12, "items": record({"object_ids": {"type": "array", "items": ID, "minItems": 1, "maxItems": 6}, "caption": {"type": "string", "minLength": 1, "maxLength": 180}, "narration_anchor": {"type": "string", "minLength": 1, "maxLength": 180}}, ["object_ids", "caption"])},
}, ["id", "title", "narration", "source_refs", "objects", "steps"])
SCHEMA = record({
    "id": ID, "title": TEXT, "target_minutes": {"enum": [1, 2, 3, 10, 15, 20]},
    "purpose": {"enum": ["lesson", "followup"]},
    "learning_objectives": {"type": "array", "items": TEXT, "maxItems": 20},
    "chapters": {"type": "array", "minItems": 1, "maxItems": 12, "items": record({"id": ID, "title": TEXT, "objective": TEXT, "scenes": {"type": "array", "items": SCENE, "minItems": 1, "maxItems": 24}}, ["id", "title", "scenes"])},
}, ["id", "title", "target_minutes", "chapters"])


def lesson_json_schema():
    return copy.deepcopy(SCHEMA)


class LessonValidationError(ValueError):
    pass


def calculate(kind: str, inputs: dict) -> dict:
    """Auditable teaching calculations, with explicit domains and units."""
    allowed = {
        "bus_read": {"address", "value", "width"}, "ohms_law": {"voltage", "resistance"},
        "ohms_law_plot": {"resistance", "voltage_min", "voltage_max", "samples"},
        "compound_interest": {"principal", "annual_rate", "periods_per_year", "years"},
        "quadratic": {"a", "b", "c", "x"},
        "quadratic_plot": {"a", "b", "c", "x_min", "x_max", "samples"},
        "biology_concept": {"concept"},
    }
    if kind not in allowed or set(inputs) != allowed[kind]:
        raise LessonValidationError(f"{kind}: expected inputs {sorted(allowed.get(kind, []))}")
    if kind == "biology_concept":
        if inputs["concept"] not in {"transcription_translation", "cell_cycle"}:
            raise LessonValidationError("Unsupported biology concept; use reviewed conceptual labels")
        return {"concept": inputs["concept"], "verification": "conceptual illustration, not a numerical simulation"}
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1e9 for v in inputs.values()):
        raise LessonValidationError(f"{kind}: finite numeric inputs required")
    p = inputs
    if kind == "bus_read":
        if any(int(v) != v for v in p.values()) or not 1 <= p["width"] <= 32 or not 0 <= p["address"] < 2**32 or not 0 <= p["value"] < 2**p["width"]:
            raise LessonValidationError("bus_read: integer address, width 1..32 and fitting unsigned value required")
        return {"address": int(p["address"]), "sampled_value": int(p["value"]), "bits": format(int(p["value"]), f'0{int(p["width"])}b'), "phases": ["address", "read_request", "data_valid", "sample", "release"], "verification": "pedagogical handshake, not a specific processor protocol"}
    if kind in {"ohms_law", "ohms_law_plot"}:
        if p["resistance"] <= 0:
            raise LessonValidationError(f"{kind}: resistance must be positive (ohms)")
    if kind == "ohms_law_plot":
        samples=p["samples"]
        if samples != int(samples) or not 2 <= samples <= 200 or p["voltage_min"] >= p["voltage_max"]:
            raise LessonValidationError("ohms_law_plot: integer samples 2..200 and voltage_min < voltage_max required")
        step=(p["voltage_max"]-p["voltage_min"])/(int(samples)-1)
        points=[]
        for index in range(int(samples)):
            voltage=p["voltage_min"]+index*step
            current=voltage/p["resistance"]
            if not math.isfinite(current) or abs(current)>1e9:
                raise LessonValidationError("ohms_law_plot: sampled current exceeds the finite numeric range")
            points.append([voltage,current])
        return {"points":points,"verification":"server-sampled Ohm's law I = V/R; x=volts, y=amperes"}
    if kind == "ohms_law":
        result = {"current_amperes": p["voltage"] / p["resistance"], "power_watts": p["voltage"]**2 / p["resistance"]}
        if not all(math.isfinite(value) for value in result.values()):
            raise LessonValidationError("ohms_law: current or power exceeds finite numeric range; use physically meaningful voltage and resistance")
        return result
    if kind == "compound_interest":
        n = p["periods_per_year"]
        if p["principal"] < 0 or n < 1 or n != int(n) or n > 365 or not 0 <= p["years"] <= 100 or not -1 < p["annual_rate"] <= 1:
            raise LessonValidationError("compound_interest: principal >=0, integer periods 1..365, years 0..100, rate (-1,1] required")
        amount = p["principal"] * (1 + p["annual_rate"] / n)**(n * p["years"])
        return {"amount": amount, "interest": amount - p["principal"], "assumptions": "fixed nominal annual rate; no deposits, fees, taxes or inflation"}
    if kind == "quadratic_plot":
        samples = p["samples"]
        if samples != int(samples) or not 2 <= samples <= 200 or p["x_min"] >= p["x_max"]:
            raise LessonValidationError("quadratic_plot: integer samples 2..200 and x_min < x_max required")
        step = (p["x_max"] - p["x_min"]) / (int(samples) - 1)
        points = []
        for index in range(int(samples)):
            x = p["x_min"] + index * step
            y = p["a"] * x**2 + p["b"] * x + p["c"]
            if not math.isfinite(y) or abs(y) > 1e9:
                raise LessonValidationError("quadratic_plot: sampled y exceeds the finite numeric range")
            points.append([x, y])
        return {"points": points, "verification": "server-sampled quadratic y = a*x^2 + b*x + c"}
    return {"y": p["a"] * p["x"]**2 + p["b"] * p["x"] + p["c"]}


def validate_lesson(lesson: dict) -> dict:
    from jsonschema import Draft202012Validator
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(lesson), key=lambda e: str(e.path))
    if errors:
        e = errors[0]
        raise LessonValidationError(f"{'/'.join(map(str, e.path))}: {e.message}")
    expected_targets = {1, 2, 3} if lesson.get("purpose", "lesson") == "followup" else {10, 15, 20}
    if lesson["target_minutes"] not in expected_targets:
        raise LessonValidationError("Follow-up clips require 1–3 minutes; full lessons require 10, 15 or 20 minutes")
    seen = set()
    scene_count = 0
    for chapter in lesson["chapters"]:
        for item in [chapter, *chapter["scenes"]]:
            if item["id"] in seen:
                raise LessonValidationError(f"Duplicate chapter or scene ID: {item['id']}")
            seen.add(item["id"])
        for scene in chapter["scenes"]:
            scene_count += 1
            ids = [o["id"] for o in scene["objects"]]
            if len(set(ids)) != len(ids):
                raise LessonValidationError("Object IDs must be unique within each scene")
            for step in scene["steps"]:
                if not set(step["object_ids"]).issubset(ids):
                    raise LessonValidationError("Step references an unknown object ID")
                if "narration_anchor" in step and step["narration_anchor"] not in scene["narration"]:
                    raise LessonValidationError("Step narration_anchor must quote exact narration text")
            anchors = [scene["narration"].find(s["narration_anchor"]) for s in scene["steps"] if "narration_anchor" in s]
            if any(a >= b for a,b in zip(anchors, anchors[1:])):
                raise LessonValidationError("Step narration anchors must occur in spoken order")
            for obj in scene["objects"]:
                if 'latex' in obj:
                    from .math_svg import validate_math
                    if obj['kind']!='equation':
                        raise LessonValidationError('LaTeX notation is only supported on equation objects.')
                    try:validate_math(obj['latex'])
                    except ValueError as exc:raise LessonValidationError(str(exc)) from exc
                if obj["kind"] == "source_image":
                    allowed = {"id", "kind", "label", "source_ref", "overlays"}
                    if set(obj) - allowed:
                        raise LessonValidationError(f"{obj['id']}: source_image accepts only source_ref and normalized overlays")
                    if obj.get("source_ref") not in scene["source_refs"]:
                        raise LessonValidationError(f"{obj['id']}: source_ref must also appear in its scene source_refs")
                    for box in obj.get("overlays", []):
                        if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in box.values()) or box["width"] <= 0 or box["height"] <= 0 or box["x"] + box["width"] > 1 or box["y"] + box["height"] > 1:
                            raise LessonValidationError(f"{obj['id']}: overlay must fit inside normalized source bounds")
                else:
                    required = {"text": "text", "equation": "text", "plot": "points", "geometry": "shape", "process": "nodes", "circuit": "nodes", "bus": "nodes", "timing": "signals"}[obj["kind"]]
                    if obj["kind"] == "plot" and obj.get("calculation", {}).get("kind") in {"quadratic_plot","ohms_law_plot"}:
                        required = "calculation"
                    if required not in obj:
                        raise LessonValidationError(f"{obj['id']}: {obj['kind']} requires {required}")
                if "calculation" in obj:
                    result = calculate(**obj["calculation"])
                    if obj["kind"] == "plot" and "points" not in result:
                        raise LessonValidationError(f"{obj['id']}: plot calculations must produce verified samples")
                    if obj["kind"] == "plot" and "points" in obj:
                        raise LessonValidationError(f"{obj['id']}: verified plot samples are generated by the server, not supplied as points")
                if obj["kind"] == "timing" and len({len(s["values"]) for s in obj["signals"]}) != 1:
                    raise LessonValidationError("Timing traces must share the same sample count and time origin")
                if "points" in obj:
                    if any(not math.isfinite(v) for point in obj["points"] for v in point):
                        raise LessonValidationError("Plot points must be finite")
                    if any(a[0] >= b[0] for a, b in zip(obj["points"], obj["points"][1:])):
                        raise LessonValidationError("Plot x samples must be strictly increasing")
    if scene_count > 120:
        raise LessonValidationError("At most 120 scenes per lesson")
    return copy.deepcopy(lesson)


def narration_guidance(target_minutes: int = 15) -> str:
    structure = "Use one focused chapter and 2-4 scenes. " if target_minutes <= 3 else "Use 3-6 chapters, each with an objective, and distinct 25-70 second scenes. "
    return (f"Produce a {target_minutes}-minute lesson, roughly {target_minutes * 130} to {target_minutes * 155} spoken words. "
            + structure + "Explain each transition and at least one worked example, "
            "misconception and retrieval question. Never repeat text or request long waits to fill time. The renderer "
            "measures speech and reports actual duration; target_minutes is a goal, not a timing command. "
            "Use only the closed schema. Narration must be spoken words, without LaTeX commands or delimiters. "
            "Equation text is a readable plain-text fallback; optional latex supplies bounded math-only notation without delimiters, "
            "including fractions, roots, calculus and matrices. Do not define macros, load extensions or access files/HTML. "
            "Typesetting does not verify the formula. For new quantitative math "
            "plots use a supported server-side calculation such as quadratic_plot or ohms_law_plot; raw point arrays remain conceptual "
            "data illustrations. Use source_image with only a cited pN/rN source_ref and optional normalized overlay "
            "rectangles when the original course diagram matters; never redraw it from memory. Preserve source_refs and stable scene/object IDs. "
            "Each step after the first should include narration_anchor quoting the exact phrase where it begins. "
            "Use bus, timing and circuit primitives for supported engineering concepts. Label conceptual biology "
            "as illustration. State uncertainty and the simplified nature of pedagogical bus protocols.")

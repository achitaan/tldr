"""Build and install the reviewed receiving-endpoint pause as one immutable revision.

This is a local authored-media path.  It reuses the reviewed narration PCM and
seven completed chapter movies, renders only the changed propagation chapter,
and never invokes generation, speech, or provider APIs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import wave

import av
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/ece224-lesson"
OUTPUT = ROOT / "artifacts/endpoint-production"
BASELINE = ROOT / "artifacts/endpoint-production-before"
OPENING = ROOT / "artifacts/showcase/opening/opening.mp4"
BACKEND = ROOT / "backend/tldr_backend"

COURSE_ID = 8
LESSON_ID = 3
SOURCE_REVISION_ID = 6
SOURCE_VIDEO_SHA256 = "6b3886d68f0159449e02b344079689ca62a6ceb54ea097b50d68912e62db16ff"
CHAPTER_ID = "propagation"
SCENE_ID = "propagation-12"
SOURCE_PAGE = 22
INSERT_AFTER_SENTENCE = 16
SILENCE_SECONDS = 3
CHECKPOINT_LOCAL_SECONDS = 105.15045833333332
QUESTION = (
    "For this synchronous read, where must the returned data meet the setup "
    "requirement, and why is the slave's internal Data Valid signal alone insufficient?"
)
ANSWER = (
    "At the receiving master (M), at least the required setup time before the next "
    "positive clock edge. The slave's internal Data Valid signal precedes the driver "
    "and bus propagation delays, so it does not establish that data is already stable at M."
)
LABEL = "PAUSE · Where must returned data meet setup?"


def digest(path: Path | str) -> str:
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def json_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".pending")
    pending.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    pending.replace(path)


def stamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    return (
        f"{milliseconds // 3600000:02}:"
        f"{milliseconds // 60000 % 60:02}:"
        f"{milliseconds // 1000 % 60:02}."
        f"{milliseconds % 1000:03}"
    )


def setup_django() -> None:
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tldr_backend.settings")
    import django

    django.setup()


def validate_media(path: Path, expected: float | None = None, *, subtitles: bool = False) -> float:
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        actual = container.duration / av.time_base
        if (video.width, video.height) != (1920, 1080) or float(video.average_rate) != 30:
            raise ValueError(f"Unexpected video format: {path}")
        if len(container.streams.audio) != 1:
            raise ValueError(f"Expected exactly one audio stream: {path}")
        if subtitles and len(container.streams.subtitles) != 1:
            raise ValueError(f"Expected embedded captions: {path}")
        if expected is not None and abs(actual - expected) > 0.2:
            raise ValueError(f"Duration mismatch for {path}: {actual} versus {expected}")
        return actual


def full_decode(path: Path) -> None:
    completed = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", os.devnull],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800,
    )
    if completed.returncode:
        raise ValueError(f"Full media decode failed: {completed.stderr[-2000:]}")


def verify_preserved_hashes() -> dict[str, str]:
    expected = json.loads((BASELINE / "hashes.json").read_text(encoding="utf-8"))
    actual = {}
    for relative, expected_hash in expected.items():
        path = ROOT / relative
        actual[relative] = digest(path)
        if actual[relative] != expected_hash:
            raise ValueError(f"Protected baseline file changed: {relative}")
    return actual


def approved_payload() -> dict[str, object]:
    return {
        "question": QUESTION,
        "answer": ANSWER,
        "label": LABEL,
        "classification": "recall_explanation",
        "scene_id": SCENE_ID,
        "source_page": SOURCE_PAGE,
        "after_sentence": INSERT_AFTER_SENTENCE,
        "silence_seconds": SILENCE_SECONDS,
        "checkpoint_local_seconds": CHECKPOINT_LOCAL_SECONDS,
        "answer_overlay": None,
    }


def prepare_beat(narration: dict, audio_path: Path) -> tuple[dict, float]:
    original = next(beat for beat in narration["beats"] if beat["id"] == CHAPTER_ID)
    if original.get("practice"):
        raise ValueError("The source propagation chapter unexpectedly has practice data.")
    beat = deepcopy(original)
    cut = beat["cues"][INSERT_AFTER_SENTENCE]["end_seconds"]
    if abs(cut - 104.65045833333332) > 1e-9:
        raise ValueError("The reviewed narration insertion boundary changed.")
    beat["audio"] = str(audio_path.resolve())
    beat["duration_seconds"] += SILENCE_SECONDS
    beat["practice"] = [
        {
            "after_sentence": INSERT_AFTER_SENTENCE,
            "dwell_seconds": SILENCE_SECONDS,
            "question": QUESTION,
            "answer": ANSWER,
            "classification": "recall_explanation",
        }
    ]
    for cue in beat["cues"][INSERT_AFTER_SENTENCE + 1 :]:
        cue["start_seconds"] += SILENCE_SECONDS
        cue["end_seconds"] += SILENCE_SECONDS
    return beat, cut


def audio_identity(original_audio: Path) -> dict[str, object]:
    return {
        "source_pcm_sha256": digest(original_audio),
        "insert_after_sentence": INSERT_AFTER_SENTENCE,
        "silence_seconds": SILENCE_SECONDS,
        "format": "original PCM parameters; zero-valued frames inserted",
    }


def prepare_audio(original_audio: Path) -> tuple[Path, dict[str, object], bool]:
    identity = audio_identity(original_audio)
    key = json_hash(identity)
    folder = OUTPUT / "cache/audio" / key
    target = folder / "propagation-with-pause.wav"
    marker = folder / "complete.json"
    if marker.is_file() and target.is_file():
        record = json.loads(marker.read_text(encoding="utf-8"))
        if record.get("identity") == identity and record.get("sha256") == digest(target):
            return target, record, True
        raise ValueError("The endpoint audio cache exists but failed validation.")
    if folder.exists():
        raise ValueError("An incomplete endpoint audio cache exists; refusing to overwrite it.")
    staging = OUTPUT / "staging" / f"audio-{key}-{os.getpid()}"
    staging.mkdir(parents=True, exist_ok=False)
    try:
        output = staging / target.name
        with wave.open(str(original_audio), "rb") as source:
            params = source.getparams()
            if params.comptype != "NONE" or params.sampwidth != 2:
                raise ValueError("Expected uncompressed 16-bit authored narration PCM.")
            pcm = source.readframes(params.nframes)
        narration = json.loads((SOURCE / "audio/narration.json").read_text(encoding="utf-8"))
        original = next(beat for beat in narration["beats"] if beat["id"] == CHAPTER_ID)
        cut_seconds = original["cues"][INSERT_AFTER_SENTENCE]["end_seconds"]
        frame_bytes = params.sampwidth * params.nchannels
        cut = round(cut_seconds * params.framerate) * frame_bytes
        silence = b"\0" * (SILENCE_SECONDS * params.framerate * frame_bytes)
        edited = pcm[:cut] + silence + pcm[cut:]
        if edited[:cut] + edited[cut + len(silence) :] != pcm:
            raise AssertionError("Narration PCM changed outside the silence insertion.")
        with wave.open(str(output), "wb") as destination:
            destination.setparams(params)
            destination.writeframes(edited)
        with wave.open(str(output), "rb") as candidate:
            actual_seconds = candidate.getnframes() / candidate.getframerate()
        expected_seconds = params.nframes / params.framerate + SILENCE_SECONDS
        if abs(actual_seconds - expected_seconds) > 1 / params.framerate:
            raise ValueError("Inserted narration duration is inconsistent.")
        record = {
            "identity": identity,
            "sha256": digest(output),
            "duration_seconds": actual_seconds,
            "speech_pcm_unchanged_outside_insertion": True,
        }
        atomic_json(staging / "complete.json", record)
        folder.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(folder)
        return target, record, False
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def render_identity(beat: dict, assets: dict, original_audio: Path) -> dict[str, object]:
    beat_identity = deepcopy(beat)
    beat_identity["audio"] = audio_identity(original_audio)
    program_paths = [
        Path(__file__),
        ROOT / "examples/showcase/full_scene.py",
        ROOT / "examples/showcase/full_render.py",
        ROOT / "examples/showcase/timing_math.py",
        ROOT / "examples/showcase/source_focus.py",
    ]
    pages = {}
    for page in beat["pages"]:
        asset = assets["pages"][str(page)]
        if digest(asset["path"]) != asset["sha256"]:
            raise ValueError(f"Source crop {page} no longer matches its immutable asset hash.")
        pages[str(page)] = {"asset": asset, "file_sha256": asset["sha256"]}
    return {
        "beat": beat_identity,
        "override": approved_payload(),
        "program": {str(path.relative_to(ROOT)): digest(path) for path in program_paths},
        "source_pages": pages,
        "resolution": [1920, 1080],
        "fps": 30,
    }


def render_propagation(beat: dict, assets: dict, identity: dict[str, object]) -> tuple[Path, dict, bool]:
    key = json_hash(identity)
    folder = OUTPUT / "cache/render" / key
    movie = folder / "propagation.mp4"
    timing_path = folder / "propagation-timing.json"
    marker = folder / "complete.json"
    if marker.is_file() and movie.is_file() and timing_path.is_file():
        record = json.loads(marker.read_text(encoding="utf-8"))
        if record.get("key") != key or record.get("sha256") != digest(movie) or record.get("timing_sha256") != digest(timing_path):
            raise ValueError("The endpoint render cache exists but failed validation.")
        validate_media(movie, record["duration_seconds"])
        return movie, json.loads(timing_path.read_text(encoding="utf-8")), True
    if folder.exists():
        raise ValueError("An incomplete endpoint render cache exists; refusing to overwrite it.")
    staging = OUTPUT / "staging" / f"render-{key}-{os.getpid()}"
    staging.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        if str(ROOT / "examples/showcase") not in sys.path:
            sys.path.insert(0, str(ROOT / "examples/showcase"))
        from manim import tempconfig
        import full_scene

        previous_output = full_scene.OUTPUT
        previous_events = full_scene.EVENTS
        try:
            full_scene.OUTPUT = staging
            full_scene.EVENTS = deepcopy(full_scene.EVENTS)
            reviewed_event = full_scene.EVENTS[CHAPTER_ID][-1]
            if reviewed_event[0] != INSERT_AFTER_SENTENCE or reviewed_event[1] != SOURCE_PAGE:
                raise ValueError("The propagation event boundary changed.")
            full_scene.EVENTS[CHAPTER_ID][-1] = (INSERT_AFTER_SENTENCE, SOURCE_PAGE, None, LABEL)
            with tempconfig(
                {
                    "pixel_width": 1920,
                    "pixel_height": 1080,
                    "frame_rate": 30,
                    "media_dir": str(staging / "media"),
                    "output_file": "endpoint-pause",
                    "disable_caching": True,
                    "write_to_movie": True,
                    "preview": False,
                    "verbosity": "WARNING",
                }
            ):
                scene = full_scene.EvidenceChapter()
                scene.beat = beat
                scene.assets = assets
                scene.render()
                shutil.copyfile(scene.renderer.file_writer.movie_file_path, staging / movie.name)
        finally:
            full_scene.OUTPUT = previous_output
            full_scene.EVENTS = previous_events
        timing = json.loads((staging / timing_path.name).read_text(encoding="utf-8"))
        actual = validate_media(staging / movie.name, beat["duration_seconds"] + 0.15)
        selected = next(scene for scene in timing["scenes"] if scene["start_seconds"] <= CHECKPOINT_LOCAL_SECONDS < scene["end_seconds"])
        if selected["id"] != SCENE_ID or selected["page"] != SOURCE_PAGE or selected["label"] != LABEL:
            raise ValueError("The reviewed checkpoint does not select the required scene and source page.")
        if max(abs(event["visual_seconds"] - event["cue_seconds"]) for event in timing["events"]) > 1 / 30 + 0.001:
            raise ValueError("A propagation visual missed its narration cue.")
        record = {
            "key": key,
            "sha256": digest(staging / movie.name),
            "timing_sha256": digest(staging / timing_path.name),
            "duration_seconds": actual,
            "render_wall_seconds": time.perf_counter() - started,
            "measurement_scope": "one local production render observation, not a benchmark",
        }
        atomic_json(staging / "complete.json", record)
        folder.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(folder)
        return movie, timing, False
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def load_source_revision() -> tuple[object, dict]:
    setup_django()
    from study.models import Revision

    revision = Revision.objects.select_related("lesson__course").get(pk=SOURCE_REVISION_ID)
    if revision.lesson_id != LESSON_ID or revision.lesson.course_id != COURSE_ID or revision.teaching_plan is not None:
        raise ValueError("Source revision identity or nullable teaching plan changed.")
    if not revision.video or digest(revision.video.path) != SOURCE_VIDEO_SHA256:
        raise ValueError("Source revision 6 video no longer matches its reviewed SHA-256.")
    jobs = list(revision.lesson.jobs.filter(kind="render", status="complete", payload__revision_id=revision.id).order_by("id"))
    if not jobs:
        raise ValueError("Source revision 6 has no completed render manifest.")
    manifest = jobs[-1].result.get("manifest")
    if not manifest or manifest.get("video_sha256") != SOURCE_VIDEO_SHA256:
        raise ValueError("Source revision 6 manifest is unavailable or stale.")
    return revision, deepcopy(manifest)


def verify_database_baseline(own_fingerprint: str | None = None, *, allow_existing_endpoint: bool = False) -> None:
    setup_django()
    from study.models import Job, Revision

    baseline_revisions = json.loads((BASELINE / "revisions.json").read_text(encoding="utf-8"))
    baseline_ids = {row["id"] for row in baseline_revisions}
    current = {revision.id: revision for revision in Revision.objects.filter(pk__in=baseline_ids)}
    if set(current) != baseline_ids:
        raise ValueError("A baseline revision was removed.")
    for row in baseline_revisions:
        revision = current[row["id"]]
        expected_spec = json.loads(row["spec"])
        expected_citations = json.loads(row["citations"])
        expected_teaching_plan = json.loads(row["teaching_plan"]) if isinstance(row["teaching_plan"], str) else row["teaching_plan"]
        fields = (revision.number, revision.lesson_id, revision.video.name, revision.captions.name, revision.transcript.name, revision.poster.name)
        expected = (row["number"], row["lesson_id"], row["video"], row["captions"], row["transcript"], row["poster"])
        if fields != expected or revision.spec != expected_spec or revision.citations != expected_citations or revision.teaching_plan != expected_teaching_plan:
            raise ValueError(f"Baseline revision {revision.id} changed.")
    extras = list(Revision.objects.exclude(pk__in=baseline_ids))
    endpoint_jobs = [
        job
        for job in Job.objects.filter(lesson_id=LESSON_ID, kind="render", status="complete")
        if job.payload.get("endpoint_pause_fingerprint")
    ]
    if own_fingerprint is None and not allow_existing_endpoint and extras:
        raise ValueError("Unexpected revision drift occurred after the production baseline.")
    if own_fingerprint is not None or allow_existing_endpoint:
        own_jobs = endpoint_jobs if allow_existing_endpoint else [
            job for job in endpoint_jobs if job.payload.get("endpoint_pause_fingerprint") == own_fingerprint
        ]
        own_ids = {job.payload.get("revision_id") for job in own_jobs}
        if {revision.id for revision in extras} != own_ids or len(own_ids) > 1:
            raise ValueError("Unexpected revision drift occurred outside this endpoint install.")
    baseline_jobs = json.loads((BASELINE / "jobs.json").read_text(encoding="utf-8"))
    for row in baseline_jobs:
        job = Job.objects.filter(pk=row["id"]).first()
        if job is None or job.kind != row["kind"] or job.status != row["status"]:
            raise ValueError(f"Baseline job {row['id']} changed.")
    if Job.objects.filter(status__in=("queued", "running")).exists() or Job.objects.filter(worker_active=True).exists():
        raise ValueError("An active job prevents an atomic endpoint install.")


def verified_parts(narration: dict, assets: dict, propagation: Path) -> tuple[list[tuple[str, Path, float]], dict[str, str]]:
    if str(ROOT / "examples/showcase") not in sys.path:
        sys.path.insert(0, str(ROOT / "examples/showcase"))
    from full_render import chapter_key

    opening_proof = json.loads((ROOT / "artifacts/showcase/opening/export-verification.json").read_text(encoding="utf-8"))
    if digest(OPENING) != opening_proof["sha256"]:
        raise ValueError("The reviewed opening movie changed.")
    parts = [("opening", OPENING, validate_media(OPENING))]
    hashes = {"opening": digest(OPENING)}
    for beat in narration["beats"]:
        if beat["id"] == CHAPTER_ID:
            path = propagation
        else:
            path = SOURCE / f"{beat['id']}.mp4"
            marker = json.loads((SOURCE / f"complete-{beat['id']}.json").read_text(encoding="utf-8"))
            if marker["key"] != chapter_key(beat, assets) or marker["sha256"] != digest(path):
                raise ValueError(f"Completed chapter {beat['id']} is stale or changed.")
        parts.append((beat["id"], path, validate_media(path)))
        hashes[beat["id"]] = digest(path)
    return parts, hashes


def clone_spec(source_spec: dict) -> dict:
    spec = deepcopy(source_spec)
    changed = 0
    for chapter in spec["chapters"]:
        for scene in chapter["scenes"]:
            if scene["id"] == SCENE_ID:
                scene["title"] = LABEL
                for step in scene.get("steps", []):
                    if step.get("caption"):
                        step["caption"] = LABEL
                changed += 1
    if changed != 1:
        raise ValueError("Expected exactly one propagation-12 scene in source spec.")
    return spec


def validate_cached_metadata(revision: object, job: object, source_revision: object, manifest: dict) -> None:
    """Reject cached-install certification when immutable revision metadata drifted."""
    expected_spec = clone_spec(source_revision.spec)
    if revision.spec != expected_spec:
        raise ValueError("The cached endpoint revision spec changed.")
    if revision.citations != source_revision.citations:
        raise ValueError("The cached endpoint revision citations changed.")
    if revision.teaching_plan is not None:
        raise ValueError("The cached endpoint revision teaching plan must remain null.")
    if job.result != {"revision_id": revision.id, "manifest": manifest}:
        raise ValueError("The cached endpoint render job manifest changed.")


def create_owned_directory(path: Path) -> bool:
    """Create a fresh revision directory and return ownership only after success."""
    path.mkdir(parents=True, exist_ok=False)
    return True


def cleanup_owned_directory(path: Path | None, owned: bool) -> None:
    """Clean only a directory successfully created by this helper invocation."""
    if not owned or path is None or not path.exists():
        return
    shutil.rmtree(path)
    parent = path.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def build_manifest(base: dict, narration: dict, beat: dict, timing: dict, parts: list[tuple[str, Path, float]]) -> dict:
    chapter_lengths = {name: length for name, _path, length in parts}
    base_chapters = {chapter["id"]: chapter for chapter in base["chapters"]}
    order = [chapter["id"] for chapter in base["chapters"]]
    if order != [name for name, _path, _length in parts]:
        raise ValueError("Source chapter order changed.")
    offsets = {}
    chapters = []
    offset = 0.0
    for chapter_id in order:
        offsets[chapter_id] = offset
        original = base_chapters[chapter_id]
        chapters.append(deepcopy(original) | {"start_seconds": offset, "end_seconds": offset + chapter_lengths[chapter_id]})
        offset += chapter_lengths[chapter_id]
    if not 600 <= offset <= 1200:
        raise ValueError("Actual assembled lesson must remain 10–20 minutes.")

    scenes = []
    base_by_id = {scene["scene_id"]: scene for scene in base["scenes"]}
    for chapter_id in order:
        original_chapter = base_chapters[chapter_id]
        chapter_scenes = [scene for scene in base["scenes"] if scene["chapter_id"] == chapter_id]
        if chapter_id == CHAPTER_ID:
            for index, rendered in enumerate(timing["scenes"]):
                original = deepcopy(base_by_id[rendered["id"]])
                start = rendered["sentence_index"]
                stop = timing["scenes"][index + 1]["sentence_index"] if index + 1 < len(timing["scenes"]) else len(beat["cues"])
                original.update(
                    title=rendered["label"],
                    page=rendered["page"],
                    sentence_index=start,
                    start_seconds=offsets[chapter_id] + rendered["start_seconds"],
                    end_seconds=offsets[chapter_id] + rendered["end_seconds"],
                    narration=" ".join(cue["text"] for cue in beat["cues"][start:stop]),
                )
                scenes.append(original)
        else:
            for original in chapter_scenes:
                shifted = deepcopy(original)
                shifted["start_seconds"] = offsets[chapter_id] + original["start_seconds"] - original_chapter["start_seconds"]
                shifted["end_seconds"] = offsets[chapter_id] + original["end_seconds"] - original_chapter["start_seconds"]
                scenes.append(shifted)
            if chapter_scenes:
                scenes[-1]["end_seconds"] = offsets[chapter_id] + chapter_lengths[chapter_id]

    opening_cues = len(base["cues"]) - sum(len(item["cues"]) for item in narration["beats"])
    if opening_cues <= 0:
        raise ValueError("Cannot identify the opening caption boundary.")
    cues = deepcopy(base["cues"][:opening_cues])
    for original_beat in narration["beats"]:
        current = beat if original_beat["id"] == CHAPTER_ID else original_beat
        for cue in current["cues"]:
            cues.append(
                deepcopy(cue)
                | {
                    "start_seconds": offsets[current["id"]] + cue["start_seconds"],
                    "end_seconds": offsets[current["id"]] + cue["end_seconds"],
                }
            )

    scene_chapter = {scene["scene_id"]: scene["chapter_id"] for scene in base["scenes"]}
    practice = []
    for point in base["practice"]:
        chapter_id = scene_chapter[point["scene_id"]]
        practice.append(
            deepcopy(point)
            | {
                "time_seconds": offsets[chapter_id] + point["time_seconds"] - base_chapters[chapter_id]["start_seconds"]
            }
        )
    practice.append(
        {
            "id": "propagation-practice-0",
            "scene_id": SCENE_ID,
            "time_seconds": offsets[CHAPTER_ID] + CHECKPOINT_LOCAL_SECONDS,
            "question": QUESTION,
            "answer": ANSWER,
            "classification": "recall_explanation",
        }
    )
    practice.sort(key=lambda point: point["time_seconds"])
    result = deepcopy(base)
    result.update(duration_seconds=offset, chapters=chapters, scenes=scenes, cues=cues, practice=practice, warnings=[])
    result.pop("assembly_wall_seconds", None)
    result.pop("video_sha256", None)
    validate_manifest(result, base)
    return result


def validate_manifest(manifest: dict, base: dict) -> None:
    if len(manifest["chapters"]) != 8 or len(manifest["scenes"]) != 100 or len(manifest["cues"]) != 153 or len(manifest["practice"]) != 7:
        raise ValueError("Endpoint manifest counts changed unexpectedly.")
    if [cue["text"] for cue in manifest["cues"]] != [cue["text"] for cue in base["cues"]]:
        raise ValueError("Spoken/caption words changed.")
    if [(point["id"], point["question"], point["answer"]) for point in manifest["practice"] if point["id"] != "propagation-practice-0"] != [
        (point["id"], point["question"], point["answer"]) for point in base["practice"]
    ]:
        raise ValueError("A preexisting practice checkpoint changed.")
    for left, right in zip(manifest["scenes"], manifest["scenes"][1:]):
        if abs(left["end_seconds"] - right["start_seconds"]) > 0.05:
            raise ValueError("Scene timeline contains a gap or overlap.")
    duration = manifest["duration_seconds"]
    if any(not 0 <= cue["start_seconds"] < cue["end_seconds"] <= duration for cue in manifest["cues"]):
        raise ValueError("Caption interval is outside the assembled media.")
    for left, right in zip(manifest["cues"], manifest["cues"][1:]):
        if left["end_seconds"] > right["start_seconds"] + 1e-9:
            raise ValueError("Caption cues overlap.")
    scenes = {scene["scene_id"]: scene for scene in manifest["scenes"]}
    for point in manifest["practice"]:
        scene = scenes[point["scene_id"]]
        if not scene["start_seconds"] <= point["time_seconds"] < scene["end_seconds"]:
            raise ValueError(f"Practice checkpoint {point['id']} is outside its scene.")
    endpoint = next(point for point in manifest["practice"] if point["id"] == "propagation-practice-0")
    scene = scenes[SCENE_ID]
    if scene.get("page") != SOURCE_PAGE or scene["title"] != LABEL:
        raise ValueError("Endpoint scene context is not the reviewed source page and label.")
    if any(cue["start_seconds"] <= endpoint["time_seconds"] < cue["end_seconds"] for cue in manifest["cues"]):
        raise ValueError("A spoken/caption cue is active at the endpoint checkpoint.")


def write_sidecars(folder: Path, manifest: dict) -> None:
    (folder / "captions.vtt").write_text(
        "WEBVTT\n\n"
        + "\n\n".join(
            f"{index + 1}\n{stamp(cue['start_seconds'])} --> {stamp(cue['end_seconds'])}\n{cue['text']}"
            for index, cue in enumerate(manifest["cues"])
        )
        + "\n",
        encoding="utf-8",
    )
    (folder / "transcript.txt").write_text(
        "\n\n".join(scene["narration"] for scene in manifest["scenes"]), encoding="utf-8"
    )


def assembly_identity(manifest: dict, part_hashes: dict[str, str], render_key: str) -> dict[str, object]:
    return {
        "manifest": manifest,
        "parts": part_hashes,
        "render_key": render_key,
        "ffmpeg": imageio_ffmpeg.get_ffmpeg_exe(),
        "captions": "mov_text plus UTF-8 WebVTT sidecar",
    }


def assemble(manifest: dict, parts: list[tuple[str, Path, float]], part_hashes: dict[str, str], render_key: str) -> tuple[Path, dict, bool]:
    identity = assembly_identity(manifest, part_hashes, render_key)
    key = json_hash(identity)
    folder = OUTPUT / "cache/assembly" / key
    marker_path = folder / "complete.json"
    required = ["lesson.mp4", "captions.vtt", "transcript.txt", "poster.jpg", "manifest.json"]
    if marker_path.is_file() and all((folder / name).is_file() for name in required):
        record = json.loads(marker_path.read_text(encoding="utf-8"))
        if record.get("key") != key or any(record["files"].get(name) != digest(folder / name) for name in required):
            raise ValueError("The endpoint assembly cache exists but failed validation.")
        validate_media(folder / "lesson.mp4", manifest["duration_seconds"], subtitles=True)
        return folder, record, True
    if folder.exists():
        raise ValueError("An incomplete endpoint assembly cache exists; refusing to overwrite it.")
    staging = OUTPUT / "staging" / f"assembly-{key}-{os.getpid()}"
    staging.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        for index, (_name, source, _duration) in enumerate(parts):
            shutil.copyfile(source, staging / f"part-{index:02}.mp4")
        (staging / "concat.txt").write_text(
            "\n".join(f"file 'part-{index:02}.mp4'" for index in range(len(parts))), encoding="utf-8"
        )
        write_sidecars(staging, manifest)
        with (staging / "assemble.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "1", "-i", "concat.txt",
                    "-i", "captions.vtt", "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0", "-c:v", "copy",
                    "-c:a", "aac", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-movflags", "+faststart",
                    "lesson.pending.mp4",
                ],
                cwd=staging,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=1200,
            )
        validate_media(staging / "lesson.pending.mp4", manifest["duration_seconds"], subtitles=True)
        (staging / "lesson.pending.mp4").replace(staging / "lesson.mp4")
        full_decode(staging / "lesson.mp4")
        with av.open(str(staging / "lesson.mp4")) as container:
            video = container.streams.video[0]
            container.seek(int(84 / video.time_base), stream=video)
            for frame in container.decode(video):
                if frame.time >= 84:
                    frame.to_image().save(staging / "poster.jpg")
                    break
        final_manifest = deepcopy(manifest)
        final_manifest["video_sha256"] = digest(staging / "lesson.mp4")
        final_manifest["assembly_wall_seconds"] = time.perf_counter() - started
        atomic_json(staging / "manifest.json", final_manifest)
        record = {
            "key": key,
            "duration_seconds": final_manifest["duration_seconds"],
            "video_sha256": final_manifest["video_sha256"],
            "files": {name: digest(staging / name) for name in required},
            "full_file_decode": True,
            "assembly_wall_seconds": final_manifest["assembly_wall_seconds"],
            "measurement_scope": "one local production assembly observation, not a benchmark",
        }
        atomic_json(staging / "complete.json", record)
        folder.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(folder)
        return folder, record, False
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def install(source_revision: object, assembly: Path, manifest: dict, fingerprint: str) -> tuple[dict, bool]:
    setup_django()
    from django.conf import settings
    from django.db import transaction
    from django.db.models import Max
    from study.models import Job, Lesson, Revision, StudyItem

    matches = list(Job.objects.filter(lesson_id=LESSON_ID, kind="render", payload__endpoint_pause_fingerprint=fingerprint))
    if len(matches) > 1:
        raise ValueError("Multiple endpoint installs share one content fingerprint.")
    if matches:
        job = matches[0]
        revision_id = job.payload.get("revision_id")
        revision = Revision.objects.filter(pk=revision_id, lesson_id=LESSON_ID).first()
        if job.status != "complete" or not revision:
            raise ValueError("A stale endpoint install fingerprint already exists.")
        validate_cached_metadata(revision, job, source_revision, manifest)
        for field, filename in (("video", "lesson.mp4"), ("captions", "captions.vtt"), ("transcript", "transcript.txt"), ("poster", "poster.jpg")):
            stored = getattr(revision, field)
            if not stored or digest(stored.path) != digest(assembly / filename):
                raise ValueError("The cached endpoint revision media changed.")
        result = {
            "course_id": COURSE_ID,
            "lesson_id": LESSON_ID,
            "source_revision_id": SOURCE_REVISION_ID,
            "revision_id": revision.id,
            "revision_number": revision.number,
            "job_id": job.id,
            "duration_seconds": manifest["duration_seconds"],
            "video_sha256": manifest["video_sha256"],
            "install_fingerprint": fingerprint,
            "url": f"http://127.0.0.1:5173/?course={COURSE_ID}&revision={revision.id}",
            "practice_points": len(manifest["practice"]),
            "scenes": len(manifest["scenes"]),
        }
        return result, True

    verify_database_baseline()
    lesson = Lesson.objects.select_related("course").get(pk=LESSON_ID, course_id=COURSE_ID)
    study_items_before = StudyItem.objects.count()
    directory = None
    directory_created_by_this_run = False
    revision = None
    job = None
    try:
        with transaction.atomic():
            if Job.objects.filter(status__in=("queued", "running")).exists() or Job.objects.filter(worker_active=True).exists():
                raise ValueError("An active job appeared before endpoint installation.")
            if Job.objects.filter(lesson_id=LESSON_ID, payload__endpoint_pause_fingerprint=fingerprint).exists():
                raise ValueError("The endpoint fingerprint appeared during installation.")
            next_number = (lesson.revisions.aggregate(value=Max("number"))["value"] or 0) + 1
            revision = Revision.objects.create(
                lesson=lesson,
                number=next_number,
                spec=clone_spec(source_revision.spec),
                citations=deepcopy(source_revision.citations),
                teaching_plan=None,
            )
            directory = settings.MEDIA_ROOT / "renders" / str(revision.id) / "endpoint-pause"
            directory_created_by_this_run = create_owned_directory(directory)
            for field, filename in (("video", "lesson.mp4"), ("captions", "captions.vtt"), ("transcript", "transcript.txt"), ("poster", "poster.jpg")):
                target = directory / filename
                if target.exists():
                    raise ValueError(f"Refusing to overwrite revision media: {target}")
                shutil.copyfile(assembly / filename, target)
                setattr(revision, field, target.relative_to(settings.MEDIA_ROOT).as_posix())
            revision.save(update_fields=["video", "captions", "transcript", "poster"])
            atomic_json(directory / "manifest.json", manifest)
            job = Job.objects.create(
                course_id=COURSE_ID,
                lesson=lesson,
                kind="render",
                status="complete",
                progress=100,
                payload={
                    "revision_id": revision.id,
                    "source_revision_id": SOURCE_REVISION_ID,
                    "endpoint_pause_fingerprint": fingerprint,
                    "authored_import": True,
                },
                result={"revision_id": revision.id, "manifest": manifest},
            )
            if StudyItem.objects.count() != study_items_before:
                raise ValueError("Endpoint installation must not create or rewrite study items.")
    except BaseException:
        cleanup_owned_directory(directory, directory_created_by_this_run)
        raise
    result = {
        "course_id": COURSE_ID,
        "lesson_id": LESSON_ID,
        "source_revision_id": SOURCE_REVISION_ID,
        "revision_id": revision.id,
        "revision_number": revision.number,
        "job_id": job.id,
        "duration_seconds": manifest["duration_seconds"],
        "video_sha256": manifest["video_sha256"],
        "install_fingerprint": fingerprint,
        "url": f"http://127.0.0.1:5173/?course={COURSE_ID}&revision={revision.id}",
        "practice_points": len(manifest["practice"]),
        "scenes": len(manifest["scenes"]),
    }
    return result, False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-install", action="store_true", help="Build and validate local media without changing the database.")
    args = parser.parse_args()
    started = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protected_before = verify_preserved_hashes()
    source_revision, base_manifest = load_source_revision()
    verify_database_baseline(allow_existing_endpoint=True)
    narration = json.loads((SOURCE / "audio/narration.json").read_text(encoding="utf-8"))
    assets = json.loads((SOURCE / "assets.json").read_text(encoding="utf-8"))
    original_beat = next(item for item in narration["beats"] if item["id"] == CHAPTER_ID)
    original_audio = Path(original_beat["audio"])
    audio, audio_record, audio_cached = prepare_audio(original_audio)
    beat, silence_start = prepare_beat(narration, audio)
    identity = render_identity(beat, assets, original_audio)
    render_key = json_hash(identity)
    propagation, timing, render_cached = render_propagation(beat, assets, identity)
    parts, part_hashes = verified_parts(narration, assets, propagation)
    manifest = build_manifest(base_manifest, narration, beat, timing, parts)
    assembly, assembly_record, assembly_cached = assemble(manifest, parts, part_hashes, render_key)
    manifest = json.loads((assembly / "manifest.json").read_text(encoding="utf-8"))
    install_fingerprint = json_hash(
        {
            "source_revision_id": SOURCE_REVISION_ID,
            "source_spec": source_revision.spec,
            "source_citations": source_revision.citations,
            "manifest": manifest,
            "approved": approved_payload(),
            "render_key": render_key,
        }
    )
    installed = None
    install_cached = None
    if not args.no_install:
        installed, install_cached = install(source_revision, assembly, manifest, install_fingerprint)
        atomic_json(OUTPUT / "installed.json", installed)
        verify_database_baseline(install_fingerprint)
    protected_after = verify_preserved_hashes()
    if protected_before != protected_after:
        raise ValueError("A protected baseline file changed during production.")
    report = {
        "status": "installed" if installed else "built_not_installed",
        "approved": approved_payload(),
        "silence_start_seconds": silence_start,
        "silence_duration_seconds": SILENCE_SECONDS,
        "checkpoint_local_seconds": CHECKPOINT_LOCAL_SECONDS,
        "speech_pcm_unchanged_outside_insertion": audio_record["speech_pcm_unchanged_outside_insertion"],
        "cache": {
            "audio_reused": audio_cached,
            "render_reused": render_cached,
            "assembly_reused": assembly_cached,
            "install_reused": install_cached,
            "render_key": render_key,
            "assembly_key": assembly_record["key"],
        },
        "media": {
            "duration_seconds": manifest["duration_seconds"],
            "resolution": [1920, 1080],
            "fps": 30,
            "video_sha256": manifest["video_sha256"],
            "full_file_decode": assembly_record["full_file_decode"],
            "embedded_and_sidecar_captions": True,
            "caption_cues": len(manifest["cues"]),
            "chapters": len(manifest["chapters"]),
            "scenes": len(manifest["scenes"]),
            "practice_points": len(manifest["practice"]),
        },
        "preservation": {
            "protected_hashes": protected_after,
            "source_revision_id": SOURCE_REVISION_ID,
            "source_video_sha256": SOURCE_VIDEO_SHA256,
            "seven_other_chapters_reused": True,
            "provider_requests": 0,
            "tts_jobs": 0,
            "study_items_created_or_rewritten": 0,
        },
        "installed": installed,
        "wall_seconds": time.perf_counter() - started,
        "measurement_scope": "one local functional production observation; wall time is not a benchmark",
        "remaining_environment_validation": [
            "player continuous-crossing auto-pause and wait-for-action behavior",
            "hidden answer reveal/hide/continue behavior",
            "selected original-diagram context in the live browser",
            "human listening and final 1080p legibility review",
        ],
    }
    atomic_json(OUTPUT / "verification.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

"""Cancellable, checkpointed local narration and controlled Manim rendering."""
from __future__ import annotations

import hashlib
import html
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
import wave
from collections.abc import Mapping

from .schema import validate_lesson, calculate

RENDER_VERSION = "tldr-controlled-4"
CONFIG = {"width": 1280, "height": 720, "fps": 30, "voice": "System.Speech default", "rate": 0}


class RenderCancelled(RuntimeError):
    pass


def ffmpeg_path():
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def dependency_status():
    status = {"manim": importlib.util.find_spec("manim") is not None,
              "speech": platform.system() == "Windows" and bool(shutil.which("powershell")),
              "ffmpeg": False, "configuration": CONFIG.copy(), "version": RENDER_VERSION}
    try:
        status["ffmpeg"] = Path(ffmpeg_path()).is_file()
    except (ImportError, RuntimeError):
        pass
    status["ready"] = all(status[k] for k in ("manim", "speech", "ffmpeg"))
    from .math_svg import math_dependencies
    status['latex']=math_dependencies()
    return status


def _hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path, data):
    path = Path(path)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _run(args, *, cancelled, cwd=None, env=None, timeout=1800):
    """No shell or model-generated command strings. Kill child tree on cancellation."""
    import tempfile
    start = time.monotonic()
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            while process.poll() is None:
                if cancelled():
                    raise RenderCancelled("Rendering cancelled; completed scene cache is retained")
                if time.monotonic() - start > timeout:
                    raise RuntimeError(f"Render subprocess exceeded its {timeout} second timeout")
                time.sleep(0.15)
            if process.returncode:
                log.seek(0, 2)
                log.seek(max(0, log.tell() - 6000))
                raise RuntimeError("Local media process failed: " + log.read().decode("utf-8", errors="replace"))
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                    if killed.returncode and process.poll() is None:
                        # Restricted Windows shells may block taskkill; the owned
                        # Popen handle still permits terminating our direct child.
                        process.kill()
                else:
                    process.kill()
                process.wait(timeout=10)


def _media(path, *, require_audio=True):
    import av
    with av.open(str(path)) as container:
        video = list(container.streams.video)
        audio = list(container.streams.audio)
        if not video or (require_audio and not audio):
            raise RuntimeError(f"Invalid media streams: {path.name}")
        v = video[0]
        if v.width != CONFIG["width"] or v.height != CONFIG["height"] or abs(float(v.average_rate or 0) - CONFIG["fps"]) > .05:
            raise RuntimeError("Media has incorrect resolution or frame rate")
        duration = float(container.duration or 0) / av.time_base
        if duration <= 0:
            raise RuntimeError("Media has no positive duration")
        return duration


def _wav_duration(path):
    with wave.open(str(path), "rb") as w:
        duration = w.getnframes() / w.getframerate()
        if duration < 1:
            raise RuntimeError("Narration must contain at least one second of audio")
        return duration


def cache_valid(folder: Path, filename: str, *, audio=False):
    try:
        record = json.loads((folder / "complete.json").read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return False
        recorded_duration = record.get("duration_seconds")
        if isinstance(recorded_duration, bool) or not isinstance(recorded_duration, (int, float)) or not math.isfinite(recorded_duration) or recorded_duration <= 0:
            return False
        path = folder / filename
        if record["sha256"] != _file_hash(path):
            return False
        if audio and record.get("marks_sha256") != _file_hash(folder / "speechmarks.json"):
            return False
        duration = _wav_duration(path) if audio else _media(path)
        return abs(duration - recorded_duration) < .1
    except (OSError, ValueError, KeyError, RuntimeError, EOFError):
        return False


def _speak(text, folder, cancelled):
    folder.mkdir(parents=True, exist_ok=True)
    wav = folder / "narration.wav"
    request = folder / "speech.json"
    _write(request, {"text": text, "path": str(wav.resolve()), "marks_path": str((folder / "speechmarks.json").resolve()), "rate": CONFIG["rate"]})
    script = Path(__file__).with_name("speak.ps1")
    _run([shutil.which("powershell"), "-NoProfile", "-NonInteractive", "-File", str(script), str(request.resolve())], cancelled=cancelled, timeout=600)
    duration = _wav_duration(wav)
    _write(folder / "complete.json", {"sha256": _file_hash(wav), "marks_sha256": _file_hash(folder / "speechmarks.json"), "duration_seconds": duration})
    return duration


def speech_cues(text, marks, duration):
    """Map source sentence starts to engine audio positions (UTF-16 char offsets)."""
    sentences = list(re.finditer(r"\S.*?(?:[.!?](?=\s|$)|$)", text, flags=re.DOTALL))
    valid = valid_speech_marks(marks, duration)
    starts = []
    matches = []
    for sentence in sentences:
        utf16_start = len(text[:sentence.start()].encode("utf-16-le")) // 2
        match = next((m for m in valid if m["character_position"] >= utf16_start), None)
        matches.append(match)
    aligned = bool(valid) and all(matches)
    for sentence, match in zip(sentences, matches):
        starts.append(float(match["seconds"]) if aligned else duration * sentence.start()/max(1,len(text)))
    if starts:
        starts[0] = 0.
    return [{"start_seconds": starts[i], "end_seconds": starts[i+1] if i+1 < len(starts) else duration, "text": s.group().strip()} for i, s in enumerate(sentences)], aligned


def valid_speech_marks(marks, duration):
    if not marks or any(not isinstance(m.get("seconds"), (int, float)) or not math.isfinite(m["seconds"]) or not 0 <= m["seconds"] <= duration or not isinstance(m.get("character_position"), int) for m in marks):
        return []
    if any(a["seconds"] > b["seconds"] or a["character_position"] > b["character_position"] for a,b in zip(marks,marks[1:])):
        return []
    return marks


def step_timings(scene, marks, duration):
    marks = valid_speech_marks(marks, duration)
    count = len(scene["steps"])
    starts = [0.]
    for i, step in enumerate(scene["steps"][1:], 1):
        anchor = step.get("narration_anchor")
        position = len(scene["narration"][:scene["narration"].find(anchor)].encode("utf-16-le"))//2 if anchor else None
        mark = next((m for m in marks if position is not None and m["character_position"] >= position), None)
        candidate = float(mark["seconds"]) if mark else duration*i/count
        starts.append(candidate)
    if any(b-a < .15 for a,b in zip(starts, starts[1:]+[duration])):
        # Engine marks may merge normalized tokens; a usable visual slot is required.
        return [duration/count] * count
    return [b-a for a,b in zip(starts, starts[1:]+[duration])]


def _timestamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}"


def _trusted_asset_snapshot(trusted_assets):
    if trusted_assets is None:
        return {}
    if not isinstance(trusted_assets, Mapping):
        raise ValueError("Trusted source assets must be a mapping")
    result={}
    for ref,asset in trusted_assets.items():
        if not re.fullmatch(r"[pr][1-9][0-9]*",ref) or not isinstance(asset,Mapping):
            raise ValueError("Invalid trusted source asset")
        content=asset.get("content")
        crop=asset.get("crop")
        if not isinstance(content,bytes) or hashlib.sha256(content).hexdigest()!=asset.get("sha256") or not isinstance(crop,Mapping):
            raise ValueError(f"Trusted source asset {ref} failed its content hash")
        if set(crop)!={"x","y","width","height"} or any(isinstance(crop[k],bool) or not isinstance(crop[k],(int,float)) or not math.isfinite(crop[k]) for k in crop) or crop["x"]<0 or crop["y"]<0 or crop["width"]<=0 or crop["height"]<=0 or crop["x"]+crop["width"]>1 or crop["y"]+crop["height"]>1:
            raise ValueError(f"Trusted source asset {ref} has an invalid crop")
        result[ref]={"content":content,"sha256":asset["sha256"],"width":asset.get("width"),"height":asset.get("height"),"crop":dict(crop),"provenance":"original_source"}
    return result


def _object_provenance(obj):
    if obj["kind"]=="source_image":
        return "original_source"
    if obj.get('latex'):
        # Typesetting arbitrary notation does not verify that notation against
        # an independently attached calculation.
        return 'conceptual'
    calculation=obj.get("calculation",{})
    if calculation and calculation.get("kind")!="biology_concept":
        return "verified_tool"
    return "conceptual"


def source_asset_fingerprint(scene, trusted_assets):
    """Cache identity for the exact crop bytes, crop transform, and display overlays."""
    return {obj["source_ref"]:{"sha256":trusted_assets[obj["source_ref"]]["sha256"],
            "crop":trusted_assets[obj["source_ref"]]["crop"],"overlays":obj.get("overlays",[])}
            for obj in scene["objects"] if obj["kind"]=="source_image"}


def render_lesson(lesson: dict, output_dir: Path, cache_dir: Path, *, trusted_assets=None, on_progress=None, is_cancelled=None) -> dict:
    lesson = validate_lesson(lesson)
    trusted_assets = _trusted_asset_snapshot(trusted_assets)
    required_assets={obj["source_ref"] for chapter in lesson["chapters"] for scene in chapter["scenes"] for obj in scene["objects"] if obj["kind"]=="source_image"}
    missing=required_assets-set(trusted_assets)
    if missing:
        raise ValueError(f"Missing trusted source assets: {', '.join(sorted(missing))}")
    cancelled = is_cancelled or (lambda: False)
    progress = on_progress or (lambda event: None)
    if cancelled():
        raise RenderCancelled("Rendering cancelled before start")
    status = dependency_status()
    if not status["ready"]:
        raise RuntimeError("Local rendering unavailable: install Manim and FFmpeg; Windows System.Speech is required. " + json.dumps(status))
    output_dir, cache_dir = Path(output_dir).resolve(), Path(cache_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    from .math_svg import prepare_equations
    math_assets,math_identity=prepare_equations(lesson,cache_dir/'math',_run,cancelled)
    asset_dir=cache_dir / "assets"
    asset_dir.mkdir(parents=True,exist_ok=True)
    trusted_paths={}
    for ref,asset in trusted_assets.items():
        path=asset_dir/(asset["sha256"]+".png")
        if not path.is_file() or _file_hash(path)!=asset["sha256"]:
            temp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
            temp.write_bytes(asset["content"]);temp.replace(path)
        trusted_paths[ref]={k:v for k,v in asset.items() if k!="content"} | {"path":str(path.resolve())}
    versions = {name: importlib.metadata.version(name) for name in ("manim", "av", "imageio-ffmpeg")}
    versions.update({"renderer": RENDER_VERSION, "python": platform.python_version(), "platform": platform.platform()})
    fingerprint = {"versions": versions, "config": CONFIG,
                   "implementation": {name: _file_hash(Path(__file__).with_name(name)) for name in ("scene.py", "schema.py", "renderer.py", "speak.ps1")}}
    scenes, chapters, cues, paths = [], [], [], []
    total = sum(len(c["scenes"]) for c in lesson["chapters"])
    start = time.monotonic()
    offset = 0.
    cache_hits = 0
    exact_captions = True
    for chapter in lesson["chapters"]:
        chapter_start = offset
        for scene in chapter["scenes"]:
            if cancelled():
                raise RenderCancelled("Rendering cancelled; completed scene cache is retained")
            audio_key = _hash({"narration": scene["narration"], "engine": "System.Speech", "script": fingerprint["implementation"]["speak.ps1"], "voice": CONFIG["voice"], "rate": CONFIG["rate"], "platform": platform.platform()})
            audio_dir = cache_dir / "audio" / audio_key
            audio_cached = cache_valid(audio_dir, "narration.wav", audio=True)
            progress({"stage": "narration", "scene_id": scene["id"], "completed": len(scenes), "total": total, "cached": audio_cached})
            duration = _wav_duration(audio_dir / "narration.wav") if audio_cached else _speak(scene["narration"], audio_dir, cancelled)
            speech = json.loads((audio_dir / "speechmarks.json").read_text(encoding="utf-8-sig"))
            marks = speech.get("marks", [])
            if duration > 180:
                raise RuntimeError(f"Scene {scene['id']} narration exceeds three minutes; split it into focused scenes")
            scene_asset_fingerprint=source_asset_fingerprint(scene,trusted_assets)
            scene_math={o['id']:math_assets[o['latex']] for o in scene['objects'] if o.get('latex')}
            key = _hash({"scene": scene, "audio": audio_key, "source_assets":scene_asset_fingerprint, "fingerprint": fingerprint,
                         'math_engine':math_identity if scene_math else {}})
            folder = cache_dir / "scenes" / key
            cached = cache_valid(folder, "scene.mp4")
            progress({"stage": "rendering", "scene_id": scene["id"], "completed": len(scenes), "total": total, "cached": cached})
            if not cached:
                folder.mkdir(parents=True, exist_ok=True)
                _write(folder / "request.json", {"scene": scene, "duration_seconds": duration, "step_durations": step_timings(scene, marks, duration), "output_dir": str(folder), "config": CONFIG,
                    "trusted_assets":{ref:trusted_paths[ref] for ref in scene_asset_fingerprint},'trusted_math':scene_math})
                env = os.environ.copy()
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + env.get("PYTHONPATH", "")
                _run([sys.executable, "-m", "study.rendering.scene", str(folder / "request.json")], cancelled=cancelled, env=env)
                visual = folder / "visual.mp4"
                if not visual.exists():
                    raise RuntimeError("Manim did not produce the expected visual.mp4")
                _media(visual, require_audio=False)
                temp_video = folder / "mux.mp4"
                _run([ffmpeg_path(), "-y", "-i", str(visual), "-i", str(audio_dir / "narration.wav"), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(temp_video)], cancelled=cancelled)
                actual = _media(temp_video)
                temp_video.replace(folder / "scene.mp4")
                _write(folder / "complete.json", {"sha256": _file_hash(folder / "scene.mp4"), "duration_seconds": actual, "key": key})
            else:
                cache_hits += 1
            actual = _media(folder / "scene.mp4")
            objects = [{"id": o["id"], "kind": o["kind"], "label": o["label"], "provenance":_object_provenance(o),
                        **({'typesetting':'local_mathjax','typesetting_scope':'notation only; attached calculation checks its own inputs'} if o.get('latex') else {}),
                        **({"calculation_result": calculate(**o["calculation"])} if "calculation" in o else {}),
                        **({"source_ref":o["source_ref"],"asset_sha256":trusted_assets[o["source_ref"]]["sha256"],"crop":trusted_assets[o["source_ref"]]["crop"]} if o["kind"]=="source_image" else {})} for o in scene["objects"]]
            scenes.append({"scene_id": scene["id"], "chapter_id": chapter["id"], "title": scene["title"], "start_seconds": offset, "end_seconds": offset + actual, "source_refs": scene["source_refs"], "objects": objects, "cache_key": key, "narration": scene["narration"]})
            scene_cues, aligned = speech_cues(scene["narration"], marks, duration)
            exact_captions = exact_captions and aligned
            for cue in scene_cues:
                cues.append({"start_seconds": offset + cue["start_seconds"], "end_seconds": min(offset + cue["end_seconds"], offset + actual), "text": cue["text"], "scene_id": scene["id"]})
            paths.append(folder / "scene.mp4")
            offset += actual
            _write(output_dir / "checkpoint.json", {"lesson_hash": _hash(lesson), "completed_scene_ids": [s["scene_id"] for s in scenes], "scene_keys": [s["cache_key"] for s in scenes]})
        chapters.append({"id": chapter["id"], "title": chapter["title"], "objective": chapter.get("objective", ""), "start_seconds": chapter_start, "end_seconds": offset})
    progress({"stage": "assembling", "completed": total, "total": total})
    vtt = "WEBVTT\n\n" + "\n\n".join(f"{i+1}\n{_timestamp(c['start_seconds'])} --> {_timestamp(c['end_seconds'])}\n{html.escape(c['text']).replace('--&gt;', '→')}" for i, c in enumerate(cues)) + "\n"
    (output_dir / "captions.vtt").write_text(vtt, encoding="utf-8")
    # Copy/link to fixed internal names; the concat list never contains user-controlled paths.
    for i, path in enumerate(paths):
        dest = output_dir / f"part-{i:03}.mp4"
        if dest.exists():
            dest.unlink()
        try:
            os.link(path, dest)
        except OSError:
            shutil.copyfile(path, dest)
    (output_dir / "concat.txt").write_text("\n".join(f"file 'part-{i:03}.mp4'" for i in range(len(paths))), encoding="utf-8")
    _run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "1", "-i", "concat.txt", "-i", "captions.vtt", "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0", "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-threads", "2", "-c:a", "aac", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", "lesson.pending.mp4"], cancelled=cancelled, cwd=output_dir)
    actual = _media(output_dir / "lesson.pending.mp4")
    (output_dir / "lesson.pending.mp4").replace(output_dir / "lesson.mp4")
    _run([ffmpeg_path(), "-y", "-i", "lesson.mp4", "-frames:v", "1", "poster.jpg"], cancelled=cancelled, cwd=output_dir)
    (output_dir / "transcript.txt").write_text("\n\n".join(s["narration"] for s in scenes), encoding="utf-8")
    warnings = []
    if abs(actual - lesson["target_minutes"] * 60) > lesson["target_minutes"] * 60 * .2:
        warnings.append(f"Actual narration is {actual / 60:.1f} minutes; requested {lesson['target_minutes']}. Expand or shorten the substantive script; no artificial padding was added.")
    provenance_counts={category:sum(1 for scene in scenes for obj in scene["objects"] if obj["provenance"]==category) for category in ("original_source","verified_tool","conceptual")}
    manifest = {"lesson_id": lesson["id"], "title": lesson["title"], "purpose": lesson.get("purpose", "lesson"), "target_minutes": lesson["target_minutes"], "duration_seconds": actual,
                "video_path": str(output_dir / "lesson.mp4"), "subtitle_path": str(output_dir / "captions.vtt"),
                "video": "lesson.mp4", "captions": "captions.vtt", "transcript": "transcript.txt", "poster": "poster.jpg",
                "chapters": chapters, "scenes": scenes, "cues": cues, "caption_alignment": "System.Speech word audio positions" if exact_captions else "estimated sentence timings (speech marks unavailable)",
                "warnings": warnings, "versions": versions, "configuration": CONFIG.copy(), "cache_hits": cache_hits,
                "provenance":{"categories":{"original_source":"unaltered course image or normalized crop with optional display-only overlays","verified_tool":"samples or values computed by a supported server-side calculation","conceptual":"schematic or supplied point illustration; not a verified quantitative result"},"counts":provenance_counts},
                "render_elapsed_seconds": time.monotonic() - start}
    _write(output_dir / "manifest.json", manifest)
    return manifest

"""Cancel a real renderer subprocess, then resume from a completed scene cache."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"backend"/"tldr_backend"))
from study.rendering import RenderCancelled, render_lesson

lesson = json.loads((ROOT/"examples"/"bus-read.json").read_text(encoding="utf-8"))
lesson["chapters"][0]["scenes"][1]["steps"][0]["caption"] = "Recovery proof: sample valid data, then release the read request."
out = ROOT/"examples"/"rendered"/"recovery"
cache = ROOT/"examples"/"render-cache"
cancelled = [False]


def progress(event):
    print(json.dumps(event), flush=True)
    if event["stage"] == "rendering" and event["scene_id"] == "sample":
        cancelled[0] = True


try:
    render_lesson(lesson, out, cache, on_progress=progress, is_cancelled=lambda: cancelled[0])
except RenderCancelled:
    checkpoint = json.loads((out/"checkpoint.json").read_text())
    assert "request" in checkpoint["completed_scene_ids"]
    print("Cancellation preserved the completed request scene.", flush=True)
else:
    raise AssertionError("The cancellation request was not observed")

result = render_lesson(lesson, out, cache)
assert result["cache_hits"] >= 1
print(json.dumps({"recovered": True, "cache_hits": result["cache_hits"], "duration_seconds": result["duration_seconds"]}))

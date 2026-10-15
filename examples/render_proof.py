"""Offline proof, measured with process-tree RSS; never calls Gemini or another API."""
import argparse
import copy
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tldr_backend"))
from study.rendering import render_lesson, RenderCancelled


def measured(lesson, name, cache):
    import psutil
    finished = threading.Event()
    peak = [0]
    def monitor():
        root = psutil.Process()
        while not finished.is_set():
            rss = 0
            for proc in [root, *root.children(recursive=True)]:
                try:
                    rss += proc.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            peak[0] = max(peak[0], rss)
            finished.wait(.1)
    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()
    started = time.perf_counter()
    try:
        result = render_lesson(lesson, ROOT/"examples"/"rendered"/name, cache,
                               on_progress=lambda e: print(json.dumps(e), flush=True))
    finally:
        finished.set()
        watcher.join()
    return result, {"run": name, "wall_seconds": time.perf_counter()-started,
                    "peak_process_tree_rss_bytes": peak[0], "cache_hits": result["cache_hits"],
                    "duration_seconds": result["duration_seconds"], "versions": result["versions"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-primitives", action="store_true")
    args = parser.parse_args()
    cache = ROOT/"examples"/"render-cache"
    lesson = json.loads((ROOT/"examples"/"bus-read.json").read_text())
    _, baseline = measured(lesson, "bus", cache)
    _, warm = measured(lesson, "bus-warm", cache)
    assert warm["cache_hits"] == 2
    revision = copy.deepcopy(lesson)
    revision["chapters"][0]["scenes"][1]["steps"][0]["caption"] = "Data must be valid before the processor samples it."
    _, selective = measured(revision, "bus-revision", cache)
    assert selective["cache_hits"] == 1
    results = [baseline, warm, selective]
    if args.all_primitives:
        for name in ("math", "finance", "biology", "circuit", "geometry"):
            fixture = json.loads((ROOT/"examples"/(name+".json")).read_text(encoding="utf-8"))
            _, result = measured(fixture, name, cache)
            results.append(result)
    (ROOT/"examples"/"proof-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))

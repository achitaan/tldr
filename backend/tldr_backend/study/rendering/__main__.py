"""python -m study.rendering examples/bus-read.json --output ... --cache ..."""
import argparse
import json
from pathlib import Path
from . import render_lesson, validate_lesson, dependency_status

parser = argparse.ArgumentParser(description="Render a validated local lesson without an API key")
parser.add_argument("lesson", type=Path, nargs="?")
parser.add_argument("--output", type=Path, default=Path("render-output"))
parser.add_argument("--cache", type=Path, default=Path("render-cache"))
parser.add_argument("--validate-only", action="store_true")
args = parser.parse_args()
if args.lesson is None:
    print(json.dumps(dependency_status(), indent=2))
else:
    spec = validate_lesson(json.loads(args.lesson.read_text(encoding="utf-8")))
    if args.validate_only:
        print("Valid lesson: " + spec["id"])
    else:
        result = render_lesson(spec, args.output, args.cache, on_progress=lambda e: print(json.dumps(e), flush=True))
        print(json.dumps(result, indent=2))

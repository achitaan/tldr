"""Optional installed-Manim geometry checks; no video generation or network calls."""
import json
from pathlib import Path
import tempfile
from manim import tempconfig
from .scene import primitive


def main():
    fixtures = Path(__file__).resolve().parents[4] / "examples"
    with tempfile.TemporaryDirectory() as folder, tempconfig({"media_dir": folder}):
        circuit = json.loads((fixtures/"circuit.json").read_text(encoding="utf-8"))
        visual = primitive(circuit["chapters"][0]["scenes"][0]["objects"][0])
        battery = visual.visual_body[1]
        long_plate, short_plate = battery
        # Conventional battery notation: longer positive plate is above shorter
        # negative plate; displayed conventional current exits along upper wire.
        assert long_plate.width > short_plate.width
        assert long_plate.get_center()[1] > short_plate.get_center()[1]
        path = visual.visual_body.motion_paths[0]
        assert path.get_start()[1] > battery.get_center()[1]
        lesson = json.loads((fixtures/"bus-read.json").read_text(encoding="utf-8"))
        timing = primitive(lesson["chapters"][0]["scenes"][1]["objects"][0])
        rows = timing.visual_body[0]
        # One discrete time index must map to one x coordinate in all traces.
        lefts = [row[1].get_left()[0] for row in rows]
        rights = [row[1].get_right()[0] for row in rows]
        assert max(lefts)-min(lefts) < 1e-9
        assert max(rights)-min(rights) < 1e-9
    print("Battery polarity/current direction and shared timing origin verified.")


if __name__ == "__main__":
    main()

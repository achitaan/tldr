"""Known-answer numerics and renderer boundary regression tests; no API calls."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import calculate, validate_lesson, LessonValidationError, RenderCancelled, render_lesson
from .renderer import _hash, _object_provenance, cache_valid, _run, source_asset_fingerprint, speech_cues, step_timings

EXAMPLES = Path(__file__).resolve().parents[4] / "examples"


class CalculationsTest(unittest.TestCase):
    def test_bus_read(self):
        result = calculate("bus_read", {"address": 16, "value": 42, "width": 8})
        # Binary positional notation: 42 = 32 + 8 + 2.
        self.assertEqual(result["bits"], "00101010")
        self.assertEqual(result["sampled_value"], 42)
        self.assertLess(result["phases"].index("data_valid"), result["phases"].index("sample"))

    def test_circuit(self):
        result = calculate("ohms_law", {"voltage": 12, "resistance": 6})
        # Ohm's law I=V/R=12/6=2; Joule power P=VI=24.
        self.assertEqual(result["current_amperes"], 2)
        self.assertEqual(result["power_watts"], 24)

    def test_interest(self):
        result = calculate("compound_interest", {"principal": 1000, "annual_rate": .05, "periods_per_year": 1, "years": 2})
        # Two explicit annual applications: 1000*(105/100)*(105/100)=1102.5.
        self.assertAlmostEqual(result["amount"], 1102.5, places=10)
        self.assertAlmostEqual(result["interest"], 102.5, places=10)

    def test_quadratic(self):
        result = calculate("quadratic", {"a": 2, "b": -3, "c": 4, "x": -2})
        # Direct substitution: 2*(-2)^2 - 3*(-2) + 4 = 18.
        self.assertEqual(result["y"], 18)

    def test_quadratic_plot_samples_are_server_derived(self):
        result = calculate("quadratic_plot", {"a": 1, "b": 0, "c": 0, "x_min": -1, "x_max": 1, "samples": 3})
        # Analytical reference: y=x^2 at x=(-1,0,1) gives y=(1,0,1).
        self.assertEqual(result["points"], [[-1, 1], [0, 0], [1, 1]])
        self.assertIn("server-sampled quadratic", result["verification"])

    def test_ohms_law_plot_samples_are_server_derived(self):
        result=calculate("ohms_law_plot",{"resistance":2,"voltage_min":0,"voltage_max":4,"samples":3})
        # Ohm's law reference: I=V/R for V=(0,2,4) volts and R=2 ohms gives I=(0,1,2) amperes.
        self.assertEqual(result["points"],[[0,0],[2,1],[4,2]])

    def test_biology_is_not_claimed_as_numerically_verified(self):
        result = calculate("biology_concept", {"concept": "transcription_translation"})
        self.assertIn("not a numerical simulation", result["verification"])

    def test_reject_undefined_domains(self):
        for kind, inputs in [("ohms_law", {"voltage": 12, "resistance": 0}), ("bus_read", {"address": 0, "value": 256, "width": 8}), ("quadratic", {"a": math.nan, "b": 1, "c": 1, "x": 1})]:
            with self.subTest(kind=kind), self.assertRaises(LessonValidationError):
                calculate(kind, inputs)

    def test_circuit_numeric_overflow_is_rejected(self):
        # IEEE-754 double cannot represent 5 / 1e-320 as a finite number.
        with self.assertRaisesRegex(LessonValidationError, "finite numeric range"):
            calculate("ohms_law", {"voltage": 5, "resistance": 1e-320})


class BoundaryTest(unittest.TestCase):
    def setUp(self):
        self.lesson = json.loads((EXAMPLES / "bus-read.json").read_text(encoding="utf-8"))

    def test_original_fixtures_validate(self):
        for name in ("bus-read", "math", "finance", "biology", "circuit", "geometry"):
            path = EXAMPLES / (name + ".json")
            with self.subTest(path=path.name):
                validate_lesson(json.loads(path.read_text(encoding="utf-8")))

    def test_code_and_unknown_visual_are_rejected(self):
        for key, value in [("code", "import os"), ("kind", "python")]:
            lesson = copy.deepcopy(self.lesson)
            lesson["chapters"][0]["scenes"][0]["objects"][0][key] = value
            with self.assertRaises(LessonValidationError):
                validate_lesson(lesson)

    def test_source_image_contract_and_normalized_overlays(self):
        scene=self.lesson["chapters"][0]["scenes"][0]
        ref="p1";scene["source_refs"]=[ref]
        scene["objects"]=[{"id":"source1","kind":"source_image","label":"Course diagram","source_ref":ref,"overlays":[{"x":.25,"y":.2,"width":.5,"height":.4}]}]
        scene["steps"]=[{"object_ids":["source1"],"caption":"Inspect the preserved source"}]
        self.assertEqual(validate_lesson(self.lesson)["chapters"][0]["scenes"][0]["objects"][0]["source_ref"],ref)
        for mutation in ({"path":"C:/secret.png"},{"overlays":[{"x":.8,"y":.2,"width":.3,"height":.4}]},{"overlays":[{"x":math.nan,"y":.2,"width":.3,"height":.4}]}):
            invalid=copy.deepcopy(self.lesson);invalid["chapters"][0]["scenes"][0]["objects"][0].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(LessonValidationError):
                validate_lesson(invalid)

    def test_source_overlay_maps_to_display_coordinates_without_changing_image(self):
        from PIL import Image
        from .scene import primitive
        fixture=Path(__file__).parent/'fixtures'/'source-grid.ppm'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'crop.png';Image.open(fixture).save(path)
            visual=primitive({"id":"source1","kind":"source_image","label":"Original","source_ref":"p1","overlays":[{"x":.25,"y":.25,"width":.5,"height":.5}]},{"p1":{"path":str(path),"sha256":"unused","width":4,"height":2,"crop":{"x":0,"y":0,"width":1,"height":1},"provenance":"original_source"}})
            image,overlays=visual.visual_body
            rectangle=overlays[0]
            # Normalized center (.5,.5) maps to the rendered image center; width/height are half its dimensions.
            self.assertAlmostEqual(rectangle.get_center()[0],image.get_center()[0],places=7)
            self.assertAlmostEqual(rectangle.get_center()[1],image.get_center()[1],places=7)
            self.assertAlmostEqual(rectangle.width,image.width*.5,places=7)
            self.assertAlmostEqual(rectangle.height,image.height*.5,places=7)

    def test_provenance_and_source_cache_identity_are_explicit(self):
        source={"id":"s","kind":"source_image","label":"Original","source_ref":"p1","overlays":[]}
        raw_plot={"id":"p","kind":"plot","label":"Supplied data","points":[[0,0],[1,1]]}
        verified=raw_plot | {"calculation":{"kind":"quadratic_plot","inputs":{"a":1,"b":0,"c":0,"x_min":0,"x_max":1,"samples":2}}}
        self.assertEqual([_object_provenance(x) for x in (source,raw_plot,verified)],["original_source","conceptual","verified_tool"])
        scene={"objects":[source]};asset={"p1":{"sha256":"a"*64,"crop":{"x":0,"y":0,"width":1,"height":1}}}
        baseline=_hash(source_asset_fingerprint(scene,asset))
        scene["objects"][0]["overlays"]=[{"x":0,"y":0,"width":.5,"height":.5}]
        self.assertNotEqual(baseline,_hash(source_asset_fingerprint(scene,asset)))
        asset["p1"]["sha256"]="b"*64
        self.assertNotEqual(baseline,_hash(source_asset_fingerprint({"objects":[source | {"overlays":[]}]},asset)))

    def test_bad_object_reference_is_rejected(self):
        self.lesson["chapters"][0]["scenes"][0]["steps"][0]["object_ids"] = ["missing"]
        with self.assertRaises(LessonValidationError):
            validate_lesson(self.lesson)

    def test_two_minute_followup_is_supported(self):
        self.lesson.update(purpose="followup", target_minutes=2)
        self.assertEqual(validate_lesson(self.lesson)["purpose"], "followup")

    def test_purpose_and_duration_must_agree(self):
        for purpose, target in [("lesson", 2), ("followup", 15)]:
            lesson = copy.deepcopy(self.lesson)
            lesson.update(purpose=purpose, target_minutes=target)
            with self.subTest(purpose=purpose), self.assertRaises(LessonValidationError):
                validate_lesson(lesson)

    def test_duplicate_stable_id_rejected(self):
        scenes = self.lesson["chapters"][0]["scenes"]
        scenes[1]["id"] = scenes[0]["id"]
        with self.assertRaises(LessonValidationError):
            validate_lesson(self.lesson)

    def test_timing_traces_share_time_axis(self):
        self.lesson["chapters"][0]["scenes"][1]["objects"][0]["signals"][0]["values"].append(0)
        with self.assertRaisesRegex(LessonValidationError, "same sample count"):
            validate_lesson(self.lesson)

    def test_cancel_before_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RenderCancelled):
                render_lesson(self.lesson, Path(folder)/"out", Path(folder)/"cache", is_cancelled=lambda: True)
            self.assertFalse((Path(folder)/"out").exists())

    def test_engine_word_positions_drive_sentence_cues(self):
        text = "Start here. Then sample."
        marks = [{"seconds": .1, "character_position": 0}, {"seconds": .4, "character_position": 6}, {"seconds": 1.7, "character_position": 12}, {"seconds": 2.2, "character_position": 17}]
        cues, aligned = speech_cues(text, marks, 3.)
        self.assertTrue(aligned)
        # Supplied engine mark for 'Then' is 1.7 seconds, not a word-count estimate.
        self.assertEqual(cues[0]["end_seconds"], 1.7)
        self.assertEqual(cues[1]["start_seconds"], 1.7)
        self.assertEqual(cues[1]["end_seconds"], 3.)

    def test_step_anchor_uses_engine_position(self):
        scene = {"narration": "Start here. Then sample.", "steps": [{}, {"narration_anchor": "Then sample"}]}
        # Exact anchor begins at character 12; its engine timestamp is 1.7.
        self.assertEqual(step_timings(scene, [{"seconds": 1.7, "character_position": 12}], 3.), [1.7, 1.3])

    def test_missing_word_marks_are_explicit_fallback(self):
        _, aligned = speech_cues("Start here. Then sample.", [], 3.)
        self.assertFalse(aligned)

    def test_invalid_engine_times_never_make_negative_cues(self):
        cues, aligned = speech_cues("First sentence. Final sentence.", [{"seconds": 1., "character_position": 0}, {"seconds": 8., "character_position": 16}], 4.)
        self.assertFalse(aligned)
        self.assertTrue(all(c["end_seconds"] > c["start_seconds"] for c in cues))

    def test_cancel_running_subprocess(self):
        import sys
        with self.assertRaises(RenderCancelled):
            _run([sys.executable, "-c", "import time; time.sleep(60)"], cancelled=lambda: True)

    def test_hash_determinism_and_invalidation(self):
        self.assertEqual(_hash({"a": 1, "b": 2}), _hash({"b": 2, "a": 1}))
        before = _hash(self.lesson["chapters"][0]["scenes"][0])
        self.lesson["chapters"][0]["scenes"][0]["narration"] += " Another example."
        self.assertNotEqual(before, _hash(self.lesson["chapters"][0]["scenes"][0]))

    def test_partial_and_corrupt_cache_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder/"scene.mp4").write_bytes(b"partial")
            self.assertFalse(cache_valid(folder, "scene.mp4"))
            (folder/"complete.json").write_text(json.dumps({"sha256": "invalid", "duration_seconds": 5}))
            self.assertFalse(cache_valid(folder, "scene.mp4"))
            with patch('study.rendering.renderer._file_hash', return_value='a'*64), patch('study.rendering.renderer._media', return_value=2):
                valid={"sha256":"a"*64,"duration_seconds":2}
                for record in (None, [], {}, *({**valid,"duration_seconds":value} for value in (None,[],"2",True,-1,0,float('nan'),float('inf')))):
                    with self.subTest(marker=record):
                        (folder/"complete.json").write_text(json.dumps(record))
                        self.assertFalse(cache_valid(folder,"scene.mp4"))
                (folder/"complete.json").write_text(json.dumps(valid))
                self.assertTrue(cache_valid(folder,"scene.mp4"))


if __name__ == "__main__":
    unittest.main()

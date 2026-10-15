"""Focused contract tests for the isolated endpoint-pause production helper."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

import endpoint_pause


class EndpointPauseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.narration = json.loads((endpoint_pause.SOURCE / "audio/narration.json").read_text(encoding="utf-8"))
        cls.base = json.loads((endpoint_pause.SOURCE / "assembled/manifest.preinstall.json").read_text(encoding="utf-8"))
        cls.candidate_timing = json.loads(
            (endpoint_pause.SOURCE / "endpoint-pause-candidate/propagation-timing.json").read_text(encoding="utf-8")
        )

    def test_prepare_beat_inserts_silence_without_changing_words(self):
        original = next(item for item in self.narration["beats"] if item["id"] == endpoint_pause.CHAPTER_ID)
        beat, cut = endpoint_pause.prepare_beat(self.narration, Path("reviewed.wav"))
        self.assertEqual([cue["text"] for cue in beat["cues"]], [cue["text"] for cue in original["cues"]])
        self.assertAlmostEqual(cut, original["cues"][16]["end_seconds"])
        self.assertEqual(beat["cues"][16], original["cues"][16])
        self.assertAlmostEqual(beat["cues"][17]["start_seconds"], original["cues"][17]["start_seconds"] + 3)
        self.assertAlmostEqual(beat["duration_seconds"], original["duration_seconds"] + 3)
        self.assertEqual(beat["practice"][0]["question"], endpoint_pause.QUESTION)

    def test_prepare_audio_preserves_source_pcm_outside_zero_insertion(self):
        original = next(item for item in self.narration["beats"] if item["id"] == endpoint_pause.CHAPTER_ID)
        with tempfile.TemporaryDirectory(dir=endpoint_pause.ROOT / "artifacts") as temporary, patch.object(endpoint_pause, "OUTPUT", Path(temporary)):
            target, record, cached = endpoint_pause.prepare_audio(Path(original["audio"]))
            self.assertFalse(cached)
            self.assertTrue(record["speech_pcm_unchanged_outside_insertion"])
            second, second_record, second_cached = endpoint_pause.prepare_audio(Path(original["audio"]))
            self.assertTrue(second_cached)
            self.assertEqual(target, second)
            self.assertEqual(record["sha256"], second_record["sha256"])
            with wave.open(original["audio"], "rb") as source, wave.open(str(target), "rb") as edited:
                self.assertEqual(source.getparams()[:3], edited.getparams()[:3])
                self.assertEqual(source.getparams()[4:], edited.getparams()[4:])
                self.assertEqual(edited.getnframes() - source.getnframes(), 3 * source.getframerate())

    def test_manifest_adds_only_reviewed_checkpoint_and_three_second_shift(self):
        beat, _cut = endpoint_pause.prepare_beat(self.narration, Path("reviewed.wav"))
        timing = deepcopy(self.candidate_timing)
        timing["scenes"][-1]["label"] = endpoint_pause.LABEL
        timing["events"][-1]["label"] = endpoint_pause.LABEL
        base_lengths = {chapter["id"]: chapter["end_seconds"] - chapter["start_seconds"] for chapter in self.base["chapters"]}
        base_lengths[endpoint_pause.CHAPTER_ID] = timing["duration_seconds"]
        parts = [(chapter["id"], Path(chapter["id"]), base_lengths[chapter["id"]]) for chapter in self.base["chapters"]]
        manifest = endpoint_pause.build_manifest(self.base, self.narration, beat, timing, parts)
        self.assertEqual(len(manifest["practice"]), 7)
        point = next(item for item in manifest["practice"] if item["id"] == "propagation-practice-0")
        self.assertEqual(point["question"], endpoint_pause.QUESTION)
        self.assertEqual(point["answer"], endpoint_pause.ANSWER)
        selected = next(scene for scene in manifest["scenes"] if scene["scene_id"] == point["scene_id"])
        self.assertEqual((selected["title"], selected["page"]), (endpoint_pause.LABEL, 22))
        self.assertFalse(any(cue["start_seconds"] <= point["time_seconds"] < cue["end_seconds"] for cue in manifest["cues"]))
        old_handshake = next(chapter for chapter in self.base["chapters"] if chapter["id"] == "handshake")
        new_handshake = next(chapter for chapter in manifest["chapters"] if chapter["id"] == "handshake")
        self.assertAlmostEqual(new_handshake["start_seconds"] - old_handshake["start_seconds"], 3, places=5)

    def test_manifest_rejects_caption_active_at_checkpoint(self):
        beat, _cut = endpoint_pause.prepare_beat(self.narration, Path("reviewed.wav"))
        timing = deepcopy(self.candidate_timing)
        timing["scenes"][-1]["label"] = endpoint_pause.LABEL
        timing["events"][-1]["label"] = endpoint_pause.LABEL
        lengths = {chapter["id"]: chapter["end_seconds"] - chapter["start_seconds"] for chapter in self.base["chapters"]}
        lengths[endpoint_pause.CHAPTER_ID] = timing["duration_seconds"]
        parts = [(chapter["id"], Path(chapter["id"]), lengths[chapter["id"]]) for chapter in self.base["chapters"]]
        manifest = endpoint_pause.build_manifest(self.base, self.narration, beat, timing, parts)
        point = next(item for item in manifest["practice"] if item["id"] == "propagation-practice-0")
        cue = next(item for item in manifest["cues"] if item["end_seconds"] < point["time_seconds"])
        cue["end_seconds"] = point["time_seconds"] + 0.1
        with self.assertRaisesRegex(ValueError, "overlap|active"):
            endpoint_pause.validate_manifest(manifest, self.base)

    def test_clone_spec_changes_only_reviewed_scene_label_metadata(self):
        baseline = json.loads((endpoint_pause.BASELINE / "revisions.json").read_text(encoding="utf-8"))
        source = json.loads(next(row for row in baseline if row["id"] == 6)["spec"])
        cloned = endpoint_pause.clone_spec(source)
        changed = []
        for old_chapter, new_chapter in zip(source["chapters"], cloned["chapters"]):
            for old_scene, new_scene in zip(old_chapter["scenes"], new_chapter["scenes"]):
                if old_scene != new_scene:
                    changed.append((old_scene, new_scene))
        self.assertEqual(len(changed), 1)
        old_scene, new_scene = changed[0]
        self.assertEqual(new_scene["id"], endpoint_pause.SCENE_ID)
        expected = deepcopy(old_scene)
        expected["title"] = endpoint_pause.LABEL
        for step in expected.get("steps", []):
            if step.get("caption"):
                step["caption"] = endpoint_pause.LABEL
        self.assertEqual(new_scene, expected)

    def test_revision_directory_collision_never_deletes_preexisting_content(self):
        with tempfile.TemporaryDirectory(dir=endpoint_pause.ROOT / "artifacts") as temporary:
            directory = Path(temporary) / "existing-revision" / "endpoint-pause"
            directory.mkdir(parents=True)
            sentinel = directory / "owned-by-someone-else.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            owned = False
            with self.assertRaises(FileExistsError):
                try:
                    owned = endpoint_pause.create_owned_directory(directory)
                finally:
                    endpoint_pause.cleanup_owned_directory(directory, owned)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

    def test_cached_install_rejects_any_metadata_or_manifest_tamper(self):
        baseline = json.loads((endpoint_pause.BASELINE / "revisions.json").read_text(encoding="utf-8"))
        row = next(item for item in baseline if item["id"] == 6)
        source = SimpleNamespace(spec=json.loads(row["spec"]), citations=json.loads(row["citations"]))
        manifest = {"video_sha256": "a" * 64, "scenes": []}
        revision = SimpleNamespace(
            id=12,
            spec=endpoint_pause.clone_spec(source.spec),
            citations=deepcopy(source.citations),
            teaching_plan=None,
        )
        job = SimpleNamespace(result={"revision_id": revision.id, "manifest": deepcopy(manifest)})
        endpoint_pause.validate_cached_metadata(revision, job, source, manifest)
        mutations = (
            lambda: revision.spec.update(title="tampered"),
            lambda: revision.citations.append({"tampered": True}),
            lambda: setattr(revision, "teaching_plan", {}),
            lambda: job.result["manifest"].update(duration_seconds=1),
        )
        for mutate in mutations:
            revision.spec = endpoint_pause.clone_spec(source.spec)
            revision.citations = deepcopy(source.citations)
            revision.teaching_plan = None
            job.result = {"revision_id": revision.id, "manifest": deepcopy(manifest)}
            mutate()
            with self.assertRaisesRegex(ValueError, "cached endpoint"):
                endpoint_pause.validate_cached_metadata(revision, job, source, manifest)


if __name__ == "__main__":
    unittest.main()

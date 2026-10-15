import copy
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Course, Job, Lesson, Page, Region, Revision, Source


class TeachingPlanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.course = Course.objects.create(name="Signals")
        self.other = Course.objects.create(name="Other")
        self.source = Source.objects.create(course=self.course, title="Notes", kind="text", status="ready", digest="a" * 64)
        self.page = Page.objects.create(source=self.source, number=1, text="A sample needs setup and hold time.", original_text="A sample needs setup and hold time.")
        self.lesson = Lesson.objects.create(course=self.course, title="Sampling")
        self.spec = self.lesson_spec(f"p{self.page.id}")
        self.revision = Revision.objects.create(lesson=self.lesson, number=1, spec=self.spec, citations=[{"page_id": self.page.id, "quote": "setup and hold"}])

    def lesson_spec(self, source_ref):
        return {
            "id": "samplingLesson",
            "title": "Sampling",
            "target_minutes": 10,
            "learning_objectives": ["Explain the sampling window."],
            "chapters": [{
                "id": "timing",
                "title": "Timing",
                "objective": "Relate the valid window to the sampling edge.",
                "scenes": [{
                    "id": "window",
                    "title": "The receiving window",
                    "objective": "Identify both sides of the sampling window.",
                    "narration": "The receiving endpoint needs stable data before and after its sampling edge.",
                    "source_refs": [source_ref],
                    "objects": [{"id": "windowPlot", "kind": "text", "label": "Sampling window", "text": "setup | edge | hold"}],
                    "steps": [{"object_ids": ["windowPlot"], "caption": "Inspect the window"}],
                }],
            }],
        }

    def validate(self, data, course=None):
        course = course or self.course
        return self.client.post(f"/api/courses/{course.id}/teaching-plan/validate/", data, format="json")

    def current_fingerprint(self, spec=None, source_ref=None):
        spec = spec or self.spec
        response = self.validate({"spec": spec, "teaching_plan": None})
        self.assertEqual(response.status_code, 200, response.data)
        bindings = {item["source_ref"]: item["fingerprint"] for item in response.data["evidence_bindings"]}
        return bindings[source_ref or spec["chapters"][0]["scenes"][0]["source_refs"][0]]

    def complete_plan(self, spec=None, source_ref=None, fingerprint=None):
        spec = spec or self.spec
        source_ref = source_ref or spec["chapters"][0]["scenes"][0]["source_refs"][0]
        fingerprint = fingerprint or self.current_fingerprint(spec, source_ref)
        return {
            "version": 1,
            "goals": [{"id": "readWindow", "text": "Read both sides of the sampling window.", "requires": ["edgeMeaning"]}],
            "assumed_prerequisites": [{"id": "edgeMeaning", "text": "A clock edge names a sampling instant."}],
            "scenes": [{
                "scene_id": "window",
                "goal_ids": ["readWindow"],
                "evidence": [{"source_ref": source_ref, "fingerprint": fingerprint}],
                "visual_requests": [{"object_id": "windowPlot", "kind": "text", "purpose": "Show setup and hold on opposite sides of the edge."}],
                "checks": [{"id": "checkWindow", "goal_ids": ["readWindow"], "question": "Which interval must be stable?", "expected_reasoning": "The valid interval must cover setup before and hold after the edge."}],
            }],
        }

    def test_legacy_revision_is_missing_and_returns_current_evidence_binding(self):
        response = self.validate({"revision_id": self.revision.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan_status"], "missing")
        self.assertTrue(response.data["can_save"])
        self.assertEqual(response.data["media_status"], "saved_revision")
        self.assertEqual(response.data["evidence_bindings"][0]["source_ref"], f"p{self.page.id}")
        self.assertIsNone(self.client.get(f"/api/lessons/{self.lesson.id}/").data["revisions"][0]["teaching_plan"])

    @patch("study.provider.generate_json", side_effect=AssertionError("provider must not be called"))
    def test_valid_plan_round_trips_only_on_a_new_revision(self, _provider):
        plan = self.complete_plan()
        before_jobs = Job.objects.count()
        response = self.client.post(f"/api/lessons/{self.lesson.id}/revisions/", {
            "spec": self.spec,
            "citations": [{"page_id": self.page.id, "quote": "setup and hold"}],
            "teaching_plan": plan,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["teaching_plan"], plan)
        self.revision.refresh_from_db()
        self.assertIsNone(self.revision.teaching_plan)
        saved = Revision.objects.get(pk=response.data["id"])
        self.assertEqual(saved.teaching_plan, plan)
        self.assertEqual(saved.number, 2)
        self.assertEqual(Job.objects.count(), before_jobs)
        report = self.validate({"revision_id": saved.id})
        self.assertEqual(report.data["plan_status"], "complete")
        self.assertTrue(report.data["can_save"])

    def test_shape_is_closed_bounded_and_rejects_bool_version_and_duplicates(self):
        plan = self.complete_plan()
        cases = []
        value = copy.deepcopy(plan); value["version"] = True; cases.append(value)
        value = copy.deepcopy(plan); value["extra"] = 1; cases.append(value)
        value = copy.deepcopy(plan); value["goals"].append(copy.deepcopy(value["goals"][0])); cases.append(value)
        value = copy.deepcopy(plan); value["goals"] = [{"id": f"g{i}", "text": "goal", "requires": []} for i in range(41)]; cases.append(value)
        value = copy.deepcopy(plan); value["scenes"][0]["goal_ids"] = "readWindow"; cases.append(value)
        for invalid in cases:
            response = self.validate({"spec": self.spec, "teaching_plan": invalid})
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("path", response.data["teaching_plan"][0])

    def test_request_forms_are_exact_and_revision_is_course_scoped(self):
        self.assertEqual(self.validate({"revision_id": True}).status_code, 400)
        self.assertEqual(self.validate({"revision_id": self.revision.id, "manifest": {}}).status_code, 400)
        self.assertEqual(self.validate({"spec": self.spec}).status_code, 400)
        self.assertEqual(self.validate({"revision_id": self.revision.id}, self.other).status_code, 404)

    def test_incomplete_plan_has_saveable_structural_warnings(self):
        plan = {"version": 1, "goals": [], "assumed_prerequisites": [], "scenes": []}
        response = self.validate({"spec": self.spec, "teaching_plan": plan})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan_status"], "incomplete")
        self.assertTrue(response.data["can_save"])
        self.assertTrue({"missing_goals", "missing_scene_assignment"}.issubset({issue["code"] for issue in response.data["issues"]}))
        saved = self.client.post(f"/api/lessons/{self.lesson.id}/revisions/", {
            "spec": self.spec,
            "citations": [{"page_id": self.page.id, "quote": "setup and hold"}],
            "teaching_plan": plan,
        }, format="json")
        self.assertEqual(saved.status_code, 201, saved.data)

    def test_integrity_errors_fail_save_atomically_without_jobs(self):
        plan = self.complete_plan()
        plan["goals"][0]["requires"] = ["readWindow"]
        plan["scenes"][0]["visual_requests"][0]["object_id"] = "missingObject"
        plan["scenes"][0]["visual_requests"][0]["kind"] = "video"
        plan["scenes"][0]["evidence"][0]["fingerprint"] = "stale"
        report = self.validate({"spec": self.spec, "teaching_plan": plan})
        self.assertEqual(report.status_code, 200)
        self.assertFalse(report.data["can_save"])
        self.assertEqual(report.data["plan_status"], "incomplete")
        self.assertTrue({"goal_dependency_cycle", "unsupported_visual_kind", "unknown_visual_object", "stale_evidence_fingerprint"}.issubset({issue["code"] for issue in report.data["issues"]}))
        revision_count, job_count = Revision.objects.count(), Job.objects.count()
        response = self.client.post(f"/api/lessons/{self.lesson.id}/revisions/", {
            "spec": self.spec,
            "citations": [{"page_id": self.page.id, "quote": "setup and hold"}],
            "teaching_plan": plan,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Revision.objects.count(), revision_count)
        self.assertEqual(Job.objects.count(), job_count)

    def test_non_null_teaching_plan_requires_spec_before_prompt_job_creation(self):
        revision_count, job_count = Revision.objects.count(), Job.objects.count()
        for teaching_plan in ({"invalid": True}, self.complete_plan()):
            response = self.client.post(f"/api/lessons/{self.lesson.id}/revisions/", {
                "prompt": "Explain sampling",
                "teaching_plan": teaching_plan,
            }, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("teaching_plan", response.data)
            self.assertEqual(Revision.objects.count(), revision_count)
            self.assertEqual(Job.objects.count(), job_count)

    def test_foreign_page_region_and_scene_references_are_errors(self):
        foreign_source = Source.objects.create(course=self.other, title="Private", kind="text")
        foreign_page = Page.objects.create(source=foreign_source, number=1, text="private")
        foreign_region = Region.objects.create(page=foreign_page, x=0, y=0, width=1, height=1, text="private region")
        for source_ref in (f"p{foreign_page.id}", f"r{foreign_region.id}"):
            spec = self.lesson_spec(source_ref)
            plan = self.complete_plan(spec, source_ref, "submitted")
            response = self.validate({"spec": spec, "teaching_plan": plan})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.data["can_save"])
            self.assertIn("foreign_source_ref", {issue["code"] for issue in response.data["issues"]})
        plan = self.complete_plan(); plan["scenes"][0]["scene_id"] = "foreignScene"
        response = self.validate({"spec": self.spec, "teaching_plan": plan})
        self.assertIn("unknown_scene", {issue["code"] for issue in response.data["issues"]})

    def test_oversized_page_and_region_ids_are_bounded_before_database_lookup(self):
        for prefix in ("p", "r"):
            source_ref = prefix + "9" * 100
            spec = self.lesson_spec(source_ref)
            plan = self.complete_plan(spec, source_ref, "submitted")
            response = self.validate({"spec": spec, "teaching_plan": plan})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertFalse(response.data["can_save"])
            self.assertIn("unknown_source_ref", {issue["code"] for issue in response.data["issues"]})

    def test_page_and_region_drift_require_explicit_rebinding(self):
        page_plan = self.complete_plan()
        submitted = page_plan["scenes"][0]["evidence"][0]["fingerprint"]
        self.page.text += " Changed."
        self.page.save(update_fields=["text"])
        response = self.validate({"spec": self.spec, "teaching_plan": page_plan})
        self.assertIn("stale_evidence_fingerprint", {issue["code"] for issue in response.data["issues"]})
        self.assertEqual(page_plan["scenes"][0]["evidence"][0]["fingerprint"], submitted)
        self.assertNotEqual(response.data["evidence_bindings"][0]["fingerprint"], submitted)

        region = Region.objects.create(page=self.page, x=.1, y=.2, width=.3, height=.4, text="sample edge")
        region_ref = f"r{region.id}"
        spec = self.lesson_spec(region_ref)
        plan = self.complete_plan(spec, region_ref)
        region.x = .2
        region.save(update_fields=["x"])
        response = self.validate({"spec": spec, "teaching_plan": plan})
        self.assertIn("stale_evidence_fingerprint", {issue["code"] for issue in response.data["issues"]})

    def test_manifest_keeps_planned_checks_distinct_from_installed_practice_and_flags_pause_gap(self):
        plan = self.complete_plan()
        self.revision.teaching_plan = plan
        self.revision.save(update_fields=["teaching_plan"])
        Job.objects.create(
            course=self.course,
            lesson=self.lesson,
            kind="render",
            status="complete",
            payload={"revision_id": self.revision.id},
            result={"manifest": {
                "scenes": [{"scene_id": "window", "start_seconds": 440.0, "end_seconds": 455.0}],
                "practice": [],
                "cues": [{"start_seconds": 445.4371243333334, "end_seconds": 450.6171243333333, "text": "Pause here and identify the receiving endpoint."}],
            }},
        )
        response = self.validate({"revision_id": self.revision.id})
        coverage = response.data["coverage"][0]
        self.assertEqual(coverage["planned_check_ids"], ["checkWindow"])
        self.assertEqual(coverage["installed_practice_ids"], [])
        self.assertIn("spoken_pause_without_checkpoint", {issue["code"] for issue in response.data["issues"]}, response.data)
        pause = next(issue for issue in response.data["issues"] if issue["code"] == "spoken_pause_without_checkpoint")
        self.assertEqual(pause["scene_id"], "window")
        self.assertEqual(pause["start_seconds"], 445.4371243333334)
        self.assertEqual(pause["end_seconds"], 450.6171243333333)
        self.assertEqual(response.data["plan_status"], "complete")

        self.revision.teaching_plan = None
        self.revision.save(update_fields=["teaching_plan"])
        missing = self.validate({"revision_id": self.revision.id})
        self.assertEqual(missing.data["plan_status"], "missing")
        self.assertIn("spoken_pause_without_checkpoint", {issue["code"] for issue in missing.data["issues"]})
        self.revision.teaching_plan = plan
        self.revision.save(update_fields=["teaching_plan"])

        Job.objects.create(
            course=self.course,
            lesson=self.lesson,
            kind="render",
            status="complete",
            payload={"revision_id": self.revision.id},
            result={"manifest": {
                "scenes": [{"scene_id": "window", "start_seconds": 440.0, "end_seconds": 455.0}],
                "practice": [{"id": "installedWindow", "scene_id": "window", "time_seconds": 451.0}],
                "cues": [{"start_seconds": 445.4371243333334, "end_seconds": 450.6171243333333, "text": "Pause now and answer."}],
            }},
        )
        response = self.validate({"revision_id": self.revision.id})
        self.assertEqual(response.data["coverage"][0]["planned_check_ids"], ["checkWindow"])
        self.assertEqual(response.data["coverage"][0]["installed_practice_ids"], ["installedWindow"])
        self.assertNotIn("spoken_pause_without_checkpoint", {issue["code"] for issue in response.data["issues"]})

    def test_draft_storyboard_still_uses_closed_renderer_validation(self):
        spec = copy.deepcopy(self.spec)
        spec["chapters"][0]["scenes"][0]["objects"][0]["kind"] = "html"
        response = self.validate({"spec": spec, "teaching_plan": None})
        self.assertEqual(response.status_code, 400)
        self.assertIn("spec", response.data)

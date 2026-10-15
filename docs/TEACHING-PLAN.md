# Local teaching plans

Implemented and independently reviewed locally, October 14, 2026.

A teaching plan records goals, prerequisite links, scene assignments, evidence bindings, visual purposes and proposed questions separately from the animation specification. It is a planning tool. Structural completeness does not certify scientific correctness, a human review or learner mastery.

## Student workflow

1. Open an existing lesson's **Storyboard**. Older revisions explicitly have no saved teaching plan; nothing is inferred or approved automatically.
2. Create a plan. Write observable goals and name assumed prerequisites, then assign goals to scenes.
3. Validate coverage to obtain current source bindings and findings. Bind the relevant evidence deliberately, and describe what each visual teaches.
4. Add proposed questions with expected reasoning and link them to the scene's goals. These are planning records; they do not install a player checkpoint or change narration.
5. Validate again after edits. Correct integrity errors or save an incomplete draft as a new revision. The original revision and media remain unchanged.

The first AI storyboard still uses the existing generation flow. Planning begins after that storyboard exists; this feature does not introduce automatic source-to-teaching-plan generation. The static public demo makes no validation or save requests.

## Data boundary

`Revision.teaching_plan` is a nullable JSON field added by migration `0005_revision_teaching_plan`. Existing revisions and generated lessons default to `null`. Plans save only with a newly created revision; reports are recomputed so they cannot silently become a durable approval badge. The closed renderer schema is unchanged.

Version 1 has this shape:

```json
{
  "version": 1,
  "goals": [{"id": "goal-window", "text": "Identify the stable interval.", "requires": ["clock-basics"]}],
  "assumed_prerequisites": [{"id": "clock-basics", "text": "Recognize a sampling edge."}],
  "scenes": [{
    "scene_id": "interval-model",
    "goal_ids": ["goal-window"],
    "evidence": [{"source_ref": "p123", "fingerprint": "CURRENT_SERVER_FINGERPRINT"}],
    "visual_requests": [{"object_id": "required-window", "kind": "equation", "purpose": "Locate both interval boundaries."}],
    "checks": [{"id": "check-window", "goal_ids": ["goal-window"], "question": "Which boundaries are required?", "expected_reasoning": "Subtract setup time and add hold time at the receiving sampling edge."}]
  }]
}
```

This illustrates the record shape, not a portable valid course binding. The source, scene and object must exist in the chosen course/storyboard. Obtain the fingerprint from that course's validation report; do not copy this placeholder or infer a fingerprint.

Records reject unknown properties and wrong types. Bounds are 40 goals, 40 assumed prerequisites, 288 scene records, 40 prerequisite/goal references per array, 20 evidence bindings, six visuals and six checks per scene. Text/question/purpose fields are bounded to 600 characters, expected reasoning to 2,000, IDs to the renderer's existing syntax, and serialized plans to 512 KiB. Empty arrays support incomplete drafts; malformed records do not.

## Local API

`POST /api/courses/{course_id}/teaching-plan/validate/` accepts exactly one of:

```json
{"revision_id": 123}
```

```json
{"spec": {"...": "an existing valid lesson specification"}, "teaching_plan": null}
```

The draft form can also carry a version-1 teaching plan. The abbreviated specification above is explanatory, not valid renderer input. Saved-revision requests resolve that revision inside the chosen course and inspect its latest completed render manifest. Draft requests have no rendered media. Clients cannot submit a manifest. Validation creates no job, calls no provider and writes no database record.

The response includes:

| Field | Meaning |
| --- | --- |
| `plan_status` | `missing`, `incomplete` or `complete`; completeness describes structural planning coverage only |
| `can_save` | Whether integrity checks permit saving; it is not a release, scientific-review or learning result |
| `issues` | Code, severity, field path and explanation, with scene/goal IDs and timing where applicable |
| `coverage` | For each goal, assigned explanation scenes, linked planned checks and separately reported installed practice IDs |
| `evidence_bindings` | Current fingerprints for valid references in the storyboard |
| `media_status` | `saved_revision` or `draft_not_rendered`; a saved revision may still have no rendered video |

Malformed request/plan data returns HTTP 400. A missing or foreign-course revision returns scoped HTTP 404. Well-shaped plans with semantic findings return HTTP 200 and `can_save:false` for integrity failures. Missing goals, scene assignments/objectives, evidence mappings and assessment coverage are incomplete warnings; they remain saveable drafts.

The existing `POST /api/lessons/{lesson_id}/revisions/` accepts optional `teaching_plan` alongside `spec` and `citations`. Omitted/null retains existing behavior. A non-null plan without `spec` returns HTTP 400 before prompt generation can create a job. Supplied malformed or integrity-invalid plans fail before a revision is created. Existing renderer and citation validation still apply. The revision serializer returns its plan; no separate mutable plan-update endpoint exists.

## What the checks establish

- Prerequisite links name existing goals or explicit assumptions; cycles are reported.
- Scene, goal and visual-object references resolve. A visual request names an existing object and matches a supported renderer kind. This does not add arbitrary graphs, solvers or simulations.
- Evidence belongs to the course and to the scene's source references. Its fingerprint covers source digest, page identity/current text and region identity/text/geometry when applicable. Source edits can make a stored binding stale. Validation does not replace the submitted fingerprint; rebind explicitly after reviewing the change.
- Existing renderer source-asset validation remains responsible for rendered image-byte identity. A teaching-plan fingerprint is not a replacement for that check or for claim-support review.
- Planned checks and installed practice remain separate. A new revision without a completed manifest has no installed checkpoints, even when every goal has a planned question. Installed IDs associated with a goal's scenes do not prove that the question adequately assesses that goal.
- Saved manifest cues containing an explicit “pause here/now” instruction can produce a timed metadata diagnostic when their scene has no installed checkpoint. This is a narrow text/manifest check, not human listening or a general analysis of teaching quality.

Scientific entailment, misconception diagnosis, actual student responses, automatic grading, persistent claim-review decisions, full source-to-video automation and dependency-aware re-rendering are outside this foundation. The broader [teaching pipeline](TEACHING-PIPELINE.md) retains those proposed stages. Human listening and learning evaluation remain separate work.

## Verification

The complete backend suite passes 98 tests, including 12 teaching-plan checks. All 29 frontend tests, the production build and lint pass. Tests cover strict inputs/bounds, course/reference isolation, evidence drift, prerequisite cycles, failed-save atomicity, immutable old revisions, null legacy plans, planned-versus-installed checks and stale validation responses. The existing socket-pair deadline test needs loopback permission in this environment; it and the full suite pass with that permission, without changes to web ingestion.

Actual local HTTP checks verify plan save/reload, failed-save rejection, no new jobs and the existing ECE224 pause diagnostic. Browser checks verify legacy plan inspection, empty-plan creation, edit invalidation, cyclic-save rejection, new-revision saving, persistence after reload and old-revision isolation. A separate retained [original-only planning workspace](http://127.0.0.1:5173/?course=16&revision=10) demonstrates the forms. It is a storyboard, with two proposed questions and no rendered video; a 10-minute target in its specification is not an actual lesson duration. These IDs belong to this local installation.

The fresh independent reviewer approved this bounded feature after two findings were corrected: delayed validation responses now require both request generation and matching scope, and plan-without-spec requests cannot enqueue generation. The reviewer independently reran 12 backend tests and nine focused frontend tests. No scientific, learning or media-quality approval is implied. See [VERIFICATION.md](VERIFICATION.md) for the current evidence and remaining gates.

The tool has also been applied to the full [ECE224 course draft](http://127.0.0.1:5173/?course=8&revision=11): eight goals, 100 authored scene objectives and eleven planned questions, with current course evidence bindings. Choose **Storyboard**. This is a separate unrendered draft with no installed checkpoints. Its new content has not received independent teaching review; the earlier feature review approves the software, not these annotations. See [the applied audit](ECE224-TEACHING-AUDIT.md#applied-course-draft).

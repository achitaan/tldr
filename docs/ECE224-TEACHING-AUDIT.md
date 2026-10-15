# ECE224 teaching coverage audit

October 14, 2026 · baseline revision ID 6, displayed as Revision 4

The later [receiving-endpoint checkpoint revision](ENDPOINT-CHECKPOINT.md) adds the reviewed question in revision ID 12 / displayed Revision 5. The audit below records the original baseline and separate draft; the original video is preserved.

The installed video and its persisted render manifest were read directly from the local database and filesystem. Its SHA-256 remains `6b3886d68f0159449e02b344079689ca62a6ceb54ea097b50d68912e62db16ff`. The audit made no database writes, provider requests or media changes. Raw structural results are retained locally in `artifacts/ece224-lesson/teaching-coverage-audit.json`.

The lesson has eight chapters, 100 scenes, 153 caption cues, six player practice pauses and three top-level learning objectives. None of the eight chapters or 100 scenes has an explicit objective saved in the installed specification. Titles and narration convey intent, but that intent is not yet structured metadata a pipeline can check.

## Actual teaching coverage

The goal descriptions below are a proposed interpretation of the authored material, not existing saved objectives. Time ranges are rounded for reading; authoritative intervals remain in the manifest. A missing local pause does not mean the topic is never revisited elsewhere.

| Chapter | Approximate range | Proposed goal | Existing player practice |
| --- | --- | --- | --- |
| Opening | 0:00–2:07 | Distinguish location, current bus value and accepted answer | None here; revisited at 13:43 |
| Ownership | 2:07–3:59 | Identify address and returned-data drivers | 3:45 |
| Ideal read | 3:59–5:46 | Distinguish selected, available and stored in the course sequence | 5:23 |
| Propagation | 5:46–7:37 | Choose the receiving endpoint before making a timing claim | None; no dedicated endpoint question later |
| Setup/hold window | 7:37–9:23 | Check the two boundaries independently | No local pause; one passing interval at 14:12 |
| Interlocked read | 9:23–11:21 | Explain which earlier event permits the next action | 10:55; revisited at 14:35 |
| Asynchronous delays | 11:21–13:21 | Explain why local ready changes do not establish remote ordering | None; final handshake question tests ideal release order instead |
| Prediction recap | 13:21–15:28 | Explain and apply the address/value, interval and release distinctions | 13:43, 14:12, 14:35 |

Four chapters have no local player practice pause. That count describes interaction coverage; it is not a teaching-quality score. The audit checked that installed source references resolve within this course. It did not establish that every source entails every sentence.

## Findings to address next

1. **A spoken pause is not backed by a player pause.** The propagation caption at 445.437–450.617 seconds says, “Pause here and point to the receiving endpoint before writing an inequality.” There is no practice entry in that chapter. A viewer can pause manually, but the optional question-pause mode does not pause here. Add an actual endpoint prediction with a hidden explanation in a new revision. This is a verified metadata/narration mismatch, not a listening-based finding.
2. **Objective coverage cannot be checked from titles alone.** Add explicit chapter/scene goals and links to prerequisites and questions in a separate planning layer. Preserve the original renderer specification until a reviewed compiler supports that layer. The current lesson's three top-level objectives do not supply those links.
3. **Receiving-endpoint reasoning lacks a dedicated check.** Ask which endpoint must satisfy the returned-data sampling condition, then require the learner to explain why validity at the slave is insufficient. This would test the propagation chapter's central distinction rather than just asking for a clock-edge name.
4. **The final numerical question checks a passing case only.** The lesson narrates separate setup and hold failures, but the existing numerical player question asks whether [7, 11.5] ns covers [8, 11] ns. Add changed-value examples that require distinguishing a setup failure from a hold failure, with independent known answers. This is an assessment-coverage gap; the current arithmetic is not reported as wrong.
5. **Teach the diagram convention before relying on it.** The ideal chapter uses the address/data bands from 4:29, then explains that each band represents multiple wires at 4:56. For learners unfamiliar with timing diagrams, introduce the convention and check clock-edge vocabulary first. This is a proposed sequencing improvement, not evidence that this learner lacks that knowledge.
6. **Separate two meanings of completion.** The ideal read discusses data storage at the master; the fully interlocked read also discusses return to the inactive state. Make the distinction explicit in the teaching plan and questions so a correct answer is tied to the requested event. The source protocols remain separate.

## Concrete draft for the pipeline

[The teaching-plan example](../examples/showcase/teaching_plan.example.json) maps all eight chapters to observable goals, prerequisite dependencies, original page numbers, current practice IDs and five proposed checks. It is deliberately separate from renderer JSON and is not loaded by the application. It contains no supplied PDF images or text extracts.

The two proposed changed-value interval questions were evaluated with the existing exact `timing_window` function:

| Sample / setup / hold | Actual valid interval | Required interval | Setup margin | Hold margin | Result |
| --- | --- | --- | --- | --- | --- |
| 12 / 1.5 / 0.5 ns | [10.75, 13] ns | [10.5, 12.5] ns | −0.25 ns | +0.5 ns | Setup fails |
| 12 / 1.5 / 0.5 ns | [10, 12.25] ns | [10.5, 12.5] ns | +0.5 ns | −0.25 ns | Hold fails |

These are illustrative interval-containment calculations, not measurements or physical circuit simulation. Draft reference integrity, prerequisite ordering/acyclicity, existing practice ownership and the two numerical answers were checked locally. Those structural checks do not approve the new wording for release or demonstrate comprehension.

The subsequent [teaching-plan foundation](TEACHING-PLAN.md) implements local structural validation and storyboard coverage, with nullable plan storage on new revisions. It identifies absent goals, broken references, prerequisite cycles, stale evidence, uncovered goals and unsupported visual requests without provider calls. Its saved-revision report exposes the pause mismatch above. A separate original-only planning workspace exercises plan persistence; the ECE video and metadata remain unchanged. The design example here is still not automatically loaded, and the five proposed questions have not been added to the player. Installing the actual teaching changes requires a new reviewed lesson revision and playback checks.

Human normal-speed listening, pronunciation/pacing feedback, successful live AI explanations/follow-ups and delayed learner assessment remain unverified. The audit does not establish equivalence to 3Blue1Brown's teaching quality.

## Applied course draft

The planning tool is now populated with a separate [ECE224 teaching draft](http://127.0.0.1:5173/?course=8&revision=11), titled **DRAFT — bus-read teaching plan**. Choose **Storyboard** to inspect it. This installation stores it as lesson 8 / revision 11, separate from the existing video lesson 3 / revision 6.

It contains eight chapter goals, prerequisite links, 100 specific scene objectives, current source fingerprints and a teaching purpose for each existing visual object. The objectives are editable annotations in [ece224_scene_objectives.json](../examples/showcase/ece224_scene_objectives.json), matched individually to the existing narration rather than copied from chapter titles. Six questions from the original practice points and the five proposed checks above are represented as **eleven planned questions**. All eight goals have explanation and planned-assessment links.

The reviewed validator accepts the draft with zero structural findings. The two changed-value interval answers were checked again with the existing exact interval function. Browser inspection confirms the receiving-endpoint question, source binding and visual purpose appear in their intended scene. The source lesson's narration, objects, steps and source references remain unchanged; no AI or render jobs were created.

This is an editable draft for content review, not a newly reviewed video. It has no render manifest, video or installed practice pauses. The eleven questions are planning records, including the six reused questions; they do not repair the original video's pause mismatch yet. Structural completeness does not establish the accuracy, sufficiency or teaching quality of these new annotations. Further content review is required before production.

Local evidence: `artifacts/ece224-lesson/teaching-draft.json`, `teaching-draft-plan.json`, `teaching-draft-report.json`, `teaching-draft-calculations.json` and `teaching-draft-workspace.png`. No additional Lane agents were launched for this content-authoring step.

See [the pipeline specification](TEACHING-PIPELINE.md), [current choreography](CHOREOGRAPHY-REVISION.md) and [verification history](VERIFICATION.md).

## Receiving-endpoint chapter preview

This is retained authoring history. The later [1080p production revision](ENDPOINT-CHECKPOINT.md) uses more precise, independently reviewed wording and an actual player checkpoint. The 720p candidate described below was not installed.

A local, unreleased propagation-chapter candidate is available at `artifacts/ece224-lesson/endpoint-pause-candidate/candidate.mp4`. It is 113.667 seconds at 1280×720 / 30 fps, with 18 embedded caption cues. It inserts three seconds of silence immediately after the existing spoken instruction to pause. The proposed player checkpoint is at chapter time 105.150 seconds, in scene `propagation-12`, bound to source page 22.

Frame inspection caught an answer leak in the first preview: the receiving-master trace remained highlighted during the question. The second preview clears that overlay and restores the full original diagram while asking which endpoint must satisfy sampling. This is a process-local event-table override in the ignored authoring script, not a change to the production renderer. The first preview's report and question frame are retained for comparison.

Local checks confirm that the spoken PCM samples outside the inserted silence are identical, the maximum visual cue error is below one 30-fps frame, and the original chapter, narration, source images and renderer source are unchanged. The second preview took 48.6 seconds to render on this run; that single observation is not a performance benchmark. No provider requests or database writes occurred.

The candidate is **not installed in the application**. Its three-second video dwell alone is not an automatic player pause or an answer/reveal interaction. Content review, installation, playback and assembly checks were subsequent production work, recorded separately above; human listening remains outstanding. Revision 6 itself remains unchanged, and no learning-efficacy claim follows from either artifact.

Evidence: `artifacts/ece224-lesson/endpoint-pause-candidate/verification.json`, `narration-candidate.json`, `propagation-timing.json`, `captions.vtt` and `pause.png`. Candidate SHA-256: `5eb0a26f22e20719f2a99ac5007fbcfae39328a56b5d4577abd301e9462e94de`.

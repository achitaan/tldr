# Visual teaching demo: quality work

The active objective is an original working visual tutor with the explanatory quality of a carefully authored mathematical animation. 3Blue1Brown is a reference for that quality; this project does not copy its scripts, branding or voice, and equivalent quality has not been established.

The [teaching pipeline design](TEACHING-PIPELINE.md) defines a repeatable source-to-lesson workflow, chapter teaching sequence, scene contract, visual-selection rules and accuracy/review gates. Its first [local teaching-plan stage](TEACHING-PLAN.md) is implemented: edit goals/prerequisites/scene plans, bind evidence, inspect structural coverage and save a new revision. The report exposes the existing spoken-pause gap without changing the ECE video. Claim-support review, full automation and learning efficacy remain outside this foundation.

## Available now

The running app includes a new **126.633-second opening study**, “Why a computer has to wait,” with a persistent processor/memory model, camera focus, selected address row, an early-sampling counterexample and a transition to a shared timing diagram. It is 1920×1080 at 30 fps, with locally generated narration and 35 sentence-aligned caption cues. Twenty key visual events are scheduled against the measured sentence boundaries; the current export reports at most 0.032 seconds of frame-quantization error. That checks event scheduling, not the perceptual quality of every animation. The original 45-second renderer proof remains available as a separate lesson.

The opening is also the first chapter of the completed local authored ECE224 sample described below. The previous 12:52 rendering proof establishes a separate long-form rendering path, not the quality of the new explanation. Equivalent 3Blue1Brown teaching quality has not been established.

The demo model states its assumptions: address 16 selects a row containing 42; the old bus value 19 is a counterexample; request, valid and sample traces share six illustrative phases. It is not an electrical simulation or a processor-specific protocol. These assets were authored independently of the subsequently supplied Waterloo PDFs and remain labelled original TLDR teaching material.

The ten supplied PDF filenames yielded nine distinct documents and 220 pages, imported into the local **ECE224 — course samples** folder. The duplicate drivers file was not imported twice. Course material and OCR stay in ignored local storage; these files are not part of the public demo. See [the animation architecture](ANIMATION-ENGINE.md) for the distinction between the installed Manim engine, working tutor extensions and planned capabilities.

## Source fidelity

Uploaded diagrams should appear as their original page images or crops. Display-only highlights stay separate. The design gallery now demonstrates this using an unmodified frame from TLDR's own sample animation; it does not draw a second circuit over the original. Quantitative new graphs require a supported calculation and checked inputs. Arbitrary sampled points are conceptual data illustrations, not independently verified scientific results.

See [the ingestion and memory research](MEMORY-INGESTION-RESEARCH.md) for evidence and proposed next steps.

## Design comparison

Open `http://127.0.0.1:5173/?designs=1` for ten full-size directions and comparison mode. The user selected **01 Focus Canvas** for the working application. Gallery interactions are simulations; the application retains its actual course, source, chat, rendering and study APIs.

## Reproducing the opening

The optional narration runtime is isolated under ignored `artifacts/voice/.venv`; it does not alter the verified backend runtime. Install `examples/showcase/voice-requirements.txt` there. Download `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the [documented Kokoro ONNX model release](https://github.com/thewh1teagle/kokoro-onnx/blob/main/examples/save.py) into `artifacts/voice/models/`. The narration script verifies the pinned SHA-256 values before inference. Kokoro ONNX is MIT licensed; the model is Apache 2.0. Inference is local and requires no account or API key.

```powershell
.\artifacts\voice\.venv\Scripts\python.exe examples\showcase\narrate.py
.\backend\.venv\Scripts\python.exe examples\showcase\scene.py
.\backend\.venv\Scripts\python.exe examples\showcase\export.py
```

The first command caches each independently synthesized sentence; actual WAV lengths establish sentence boundaries. The second renders the fixed, reviewed Manim program. This is trusted project source, never generated Python executed from an AI response. The third verifies streams, dimensions, frame rate, duration and cue intervals before exporting the media and static demo metadata. Generated audio, intermediate renders and model weights are ignored; the reviewed opening MP4, captions and source frame are included in the static demo.

## Full authored ECE224 sample

### Available locally

`examples/showcase/full_lesson.json` adds seven authored chapters to the reviewed opening: bus ownership, the course's ideal synchronous read, endpoint propagation, a separate checked setup/hold example, fully interlocked sequencing, asynchronous ordering delays and prediction practice. The assembled lesson is **927.7 seconds (15:27.7), 1920×1080 at 30 fps**, with eight chapters, 100 contextual scenes, 153 caption cues and six deliberate three-second practice dwells. These dwells serve prediction questions; they are not added to reach the requested duration.

On the checked local installation, open [the full lesson](http://127.0.0.1:5173/?course=8&revision=6). The URL's revision ID is 6; the lesson's selector displays its fourth version as **Revision 4**. Course and revision identifiers are installation-specific; `artifacts/ece224-lesson/installed.json` records the actual URL after import. This is an authored sample with source-bound evidence, not proof of live automatic lesson generation.

`full_scene.py` preserves the imported figures as original image crops and animates overview/detail focus. The numerical example keeps a shared ruler while moving the validity interval; `timing_math.py` checks its margins with exact rational arithmetic. Course figures and their magnified details are not redrawn. The fixed program, source identity, crop hashes and sentence audio enter chapter cache keys. A renderer program change deliberately invalidates old scene media.

A direct source-content audit matched the authored ownership, synchronous sequencing, propagation, setup/hold and asynchronous ordering explanations against Part Va pages 5, 13, 19, 22, 24, 34, 35, 37, 38 and 40. Original images on pages 13, 19, 22 and 24 were inspected where extracted text lost timing symbols. This checks the lesson's named mechanisms against those pages; it does not certify all uploaded material or replace full scientific/teaching review.

The player supports optional question pauses, hidden explanations, keyboard reveal/continue and a synchronized caption panel below the image. Revealing an answer does not record mastery. The authored fixture importer adds editable flashcards alongside the lesson. It does not enable or simulate a cloud tutor when Gemini is unconfigured.

Reproduce locally after importing the supplied Part Va PDF and specifying its course/source IDs if they differ:

```powershell
.\backend\.venv\Scripts\python.exe examples\showcase\full_prepare.py --course 8 --source 12
.\artifacts\voice\.venv\Scripts\python.exe examples\showcase\narrate.py --script examples\showcase\full_lesson.json --output artifacts\ece224-lesson\audio
.\backend\.venv\Scripts\python.exe examples\showcase\full_render.py
.\backend\.venv\Scripts\python.exe examples\showcase\full_export.py
.\backend\.venv\Scripts\python.exe examples\showcase\full_verify.py --context-smoke
.\backend\.venv\Scripts\python.exe examples\showcase\full_audio_verify.py
```

The exporter refuses stale chapter media, validates streams/captions/timelines, binds course evidence to an immutable revision, then installs the completed lesson in local media storage. Its printed URL opens the course and revision directly. Supplied course figures are never copied into the static public bundle. Authoring intermediates and local measurements remain in ignored `artifacts/ece224-lesson`; these explicit authoring/export copies are separate from the application's course deletion.

The first reviewed full video (revision 2) has SHA-256 `df586ca5996fe2974c94faea53f5913c3516738b1f6cee1534f8d718cc775988`; revision 3 below supersedes it without altering that media. Export validation checks current program/audio/source hashes, positive caption intervals, continuous scene intervals and visual event scheduling within one frame. Real HTTP checks confirmed Range seeking, caption delivery and preserved revision/scene/object/time context for a question and a separate follow-up. With generation disabled, both jobs paused without a provider request; the original lesson stayed intact and temporary verification records were deleted.

The audio verifier respects decoded presentation timestamps and compares 21 voiced samples across the seven new chapters with their original WAVs. The largest offset was 21.334 ms, with minimum normalized correlation 0.99828. This checks alignment, not pronunciation or teaching quality. Raw narration had no clipped PCM samples; all six practice dwells contained the intended three seconds of silence.

The first reviewed seven-chapter render took 702.46 seconds with 652.0 MB peak sampled process-tree RSS. An unchanged rerun reused all seven chapters in 0.224 seconds. These are single functional observations under development load, not controlled performance benchmarks; summed working sets may count shared memory more than once. Assembly and prior narration synthesis are separate costs.

The revision-2 independent reviewer approved the authored local lesson with follow-ups and no remaining P0/P1 finding. They verified the media hash/streams, all seven chapter cache identities, 100 scene joins, 153 caption intervals and visual-cue error below one frame (maximum 0.03325 seconds). Live browser checks confirmed the installed deep link, natural question pause with its answer hidden, paused page-22 context, exact-crop raster thumbnails and no console errors. Their peripheral-glyph clipping follow-up motivated the revision below. Normal-speed human listening, learner feedback and equivalent teaching quality remain unestablished. This approval does not complete the broader quality objective.

### Remaining acceptance checks

Current acceptance audit, October 14, 2026:

| Requirement | Evidence and remaining gate |
| --- | --- |
| A working 10–20-minute local visual lesson | The live API serves revision ID 6, 927.7 seconds, with SHA-256 `6b3886d68f0159449e02b344079689ca62a6ceb54ea097b50d68912e62db16ff`. The launcher, API, worker and browser workspace are running. |
| Playback and synchronized captions in the actual app | A fresh browser check played at 1× from 0, 395 and 913 seconds for seven wall-clock seconds each. Positions advanced to 5.987, 401.952 and 919.956 seconds, with decoded video frames, current captions, readyState 4 and no media error. Practice-pause settings were restored. This is sampled functional playback, not a full listen-through. |
| Faithful course diagrams and checked examples | Original source snapshots, normalized highlights, receiving-endpoint focus and exact setup/hold arithmetic have bounded verification and prior independent review. This does not verify every statement in every uploaded document or simulate physical hardware. |
| Questions and separate follow-up context | Previous real-browser/API checks preserve revision, scene, selected object and timestamp; unavailable generation pauses without changing the original video. The dedicated free project is now configured and authenticated, but live generation returned HTTP 503/high demand. Successful AI explanations and generated follow-up clips remain unverified. |
| New LaTeX support | Browser math, saved flashcards and the separate short equation video work. The tenth Lane call independently approved the bounded feature after its equation-cache recovery finding was fixed. Tests and the separately verified shared-cache guard are recorded in VERIFICATION.md. Those first ten calls are complete; the subsequent three-call choreography packet is also complete. Per-call token counters are unavailable. |
| Narration and teaching quality comparable to the requested reference | Full normal-speed listening, pronunciation/pacing assessment and learner feedback remain open. Media duration, cue correlation and test counts do not establish this requirement. |
| Final workspace design | The user rejected the prototype appearance and explicitly deferred redesign. Keep the UI backlog for later; do not treat the existing style as accepted. |

The independent LaTeX review is complete using the existing signed-in account. Remaining quality gates are full listening and learner feedback; live generated answers/follow-up clips additionally require successful service availability and account quota. The broader quality goal remains incomplete.

### Script, visual and pacing review

On October 14, the complete opening and seven-chapter narration scripts were read, and ten actual decoded frames were inspected at 20, 90, 180, 280, 400, 510, 640, 760, 860 and 914 seconds. The review also checked the seven chapters' sentence timings and existing audio alignment/clipping measurements. This is a script/visual/timing review, not a perceptual listen-through or learner study: the available tools do not provide audio hearing.

The opening uses one persistent processor/memory model, distinguishes location 16 from stored value 42, and makes old value 19 a concrete counterexample before introducing validity. Later chapters carry that question into the source diagrams, separate sending and receiving endpoints, and compare setup/hold boundaries on one numerical ruler. The prediction questions require an answer before the player reveals it. These are useful teaching choices rather than a sequence of unrelated slide summaries.

The seven later chapters measure 128.1–146.6 words per minute overall, including practice dwells; sentence medians range from 138.6 to 152.7. The fastest individual sentence is approximately 194.8 words per minute. Longest caption sentences range from 115 to 149 characters. These are observations, not validated comprehension thresholds or evidence that the synthetic voice sounds natural. Exact chapter results are saved locally in `artifacts/ece224-lesson/teaching-audit-metrics.json`; extracted frames are in `artifacts/ece224-lesson/teaching-audit/`.

Prioritized polish findings:

1. Listen to numerical and acronym passages before approving pronunciation/prosody, particularly the setup/hold chapter and DMA/MDR. Slower delivery should be chosen from actual listening evidence, not applied globally from word counts alone.
2. At approximately 4:40, the magnifier correctly selects the negative clock edge, but a peripheral `valid address` label is cut at its right edge in installed revision 3. The complete overview remains visible. The follow-up below widens both detail views; this review did not find a wrong active clock edge.
3. Several source chapters retain long stretches of overview/detail framing. The next teaching revision should connect more transformations directly to the opening's persistent model while preserving the original figures. This is the main visual-storytelling gap relative to the requested reference.
4. Keep scope/provenance labels available, but reduce repeated explanatory caveats in narration when revising the script. Preserve the distinction between source figures, checked numerical examples and physical simulation.

The current verdict is a usable authored study prototype with technical and source-grounding evidence. Equivalent 3Blue1Brown teaching quality and natural narration remain unproven. No uploaded course material was sent to a cloud service for this review.

### Connected motion installed and independently reviewed

[The completed choreography packet](CHOREOGRAPHY-REVISION.md) connects the ideal-read chapter's original clock figure to the opening's persistent processor/memory model. Address 16 travels toward memory, data 42 returns while the register remains 19, and storage changes the register only at the corresponding narration cue. Prediction replay clears the earlier answer before the existing pause. Original source pixels remain intact, and both the video and contextual-chat specification distinguish the original logical example from course evidence.

Revision ID 6 is installed with seventeen authored checks passing and a fresh independent **approve with follow-ups** verdict for this bounded change. The extended silent proof exercises all thirteen production events. Media, captions, unchanged sources/narration and actual provider-bound scene contexts pass verification. Browser checks confirmed hidden-answer pause, reveal, resume and attachment of the selected register/scene/time without submitting an AI request. All thirteen authorized Lane calls are complete. Human listening and learner feedback remain open; the last live generation attempt returned HTTP 503/high demand, so successful AI answers and follow-up clips remain unverified.

### Original-label crop polish installed

The page-13 detail view now retains both complete original `valid address` and `valid data` labels. Only the normalized crop extents changed; source pixels, highlight coordinates, narration and timing remain unchanged. `focus_proof.py` now includes both clock edges and the intervening data-valid view. The 36-second proof rendered successfully, and decoded frames at 26 and 34 seconds were visually checked against the unchanged original source crop. Both labels are complete, and the negative/final-positive clock highlights agree between the overview and detail. All ten existing timing/coordinate tests pass.

All seven authored chapters rebuilt, and the full lesson was installed as revision ID 5. Actual media remains 927.7 seconds at 1920×1080/30 fps, with eight chapters, 100 scenes, 153 captions and six practice points. SHA-256 is `a1da11b4cf74560650597763fa090f35447ca93fe9f6726fa208f32aee5eb2fc`. The full media/API verifier passed, including HTTP 206 seeking, embedded/sidecar captions and timeline checks. All 21 decoded audio comparisons passed again (maximum offset 21.334 ms, minimum correlation 0.99828). This remains alignment evidence, not human listening.

The real browser loaded `/media/renders/5/authored/lesson.mp4`, played through the corrected chapter without a media error and sought to 280 seconds while paused. Both complete validity labels and the matching clock highlight were checked in frames decoded from the actual chapter. The browser reported readyState 4 and no console errors. The workspace proof is `artifacts/ece224-lesson/label-polish-workspace.png`; final chapter frames are `ideal-label-final-6.png` and `ideal-label-final-8.png` in that directory. The original proof frames remain available separately.

The rebuild took 630.00 seconds with 650,977,280 bytes peak sampled process-tree RSS. A warm verification reused all seven chapters in 0.219 seconds. These are single observations, not performance comparisons; assembly/narration are separate costs and summed working sets may count shared memory more than once. Installed revision IDs 2 and 3 still match their earlier hashes; their media was not overwritten. The previous installation metadata is saved as `installed-before-label-polish.json`. This small crop follow-up was directly checked and is outside the tenth independent review's scope. No further cloud requests were made.

Two wording corrections clarify actual service behavior: the sidebar now states that files are stored locally while AI requests send relevant text/images to Gemini, and the service badge says **configured** rather than promising readiness. Browser inspection and the production build verify these text-only changes. The deferred UI redesign remains deferred.

### Free-AI setup and live availability check

The root `.env.local` was prepared from the existing example and is ignored by Git. The earlier browser tools could not access an authenticated Google session: the native tool failed initialization, and Chrome did not expose a debugging connection. After the computer-use runtime updated, a scoped browser-extension connection successfully opened the authorized AI Studio page. No browser security settings were changed.

The dedicated project **TLDR Study Tutor**, ID `gen-lang-client-0809907059`, was created in AI Studio. Its Projects row explicitly showed **Free tier** and **Set up billing**; billing was not enabled. After the owner's explicit authorization, one key named **TLDR local study tutor** was created and saved privately in the ignored root `.env.local`, together with the billing-disabled and free-service data-use acknowledgements. No credential was printed or added to source control. The local API and worker were restarted with generation enabled and no configuration issues. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) listed `gemini-3.8-flash` standard input/output as free on the Free Tier when checked October 14; that does not establish available account quota.

Authenticated model lookup returned HTTP 200 and listed `generateContent` support. An original, non-sensitive bus-read sample was saved in local course 15, conversation 14, job 45. Generation paused after its bounded retry; one explicit retry of the same saved job also paused. One minimal original JSON diagnostic returned HTTP 503 / `UNAVAILABLE`: “This model is currently experiencing high demand.” No successful answer or follow-up was produced. Stop further retries until a later explicit retry; the original question remains saved in Activity. Existing paused course questions and uploaded private PDFs were not sent. No model/provider fallback or billing change occurred. Metadata success verifies authentication and the model endpoint, not generation capacity or answer quality.

The provider now distinguishes service errors from configuration errors: after the existing two-attempt bound, HTTP 5xx pauses the job with an explicit saved-work/retry-later message. A new integration regression verifies the saved question, paused status, exactly two attempts to the same model and no false quota pause. All 86 backend tests pass. This small error-copy change was directly verified; it was not a new independent review.

Automatic approval review previously rejected full-window Chrome inspection and an unscoped key-creation control. Scoped inspection, a dedicated verified free project and the owner's subsequent explicit authorization resolved those steps. The completed key list, showing only a masked credential and Free tier, is saved at `artifacts/ai-setup/key-created.png`. Safe diagnostic metadata is in `artifacts/ai-setup`; it contains no key.

Tests, video duration and a successful render are necessary evidence; they do not alone prove the requested explanatory quality.

The later LaTeX implementation adds local browser math, editable flashcards and a separate 63-second equation-video sample. See [the verification record](VERIFICATION.md#local-latex-follow-up). This is functional progress and does not change the ECE224 lesson's acceptance status. The user rejected the prototype's visual design and deferred redesign; the [UI checklist](UI-REDESIGN-CHECKLIST.md) remains the design backlog.

### Follow-up visual and chat fixes

Revision 3 is installed with matching source-coordinate highlights in the overview and magnifier. The page 22/24/37/38 detail crops are wider or taller to retain complete nearby labels. A silent 20-second proof exercises five original-source views before the full render. `source_focus.py` maps each full-page annotation into the visible detail viewport; five tests cover receiving-endpoint placement, partial clipping, full-page identity, disjoint boundaries and invalid geometry. Neither the original images nor the numerical/narration content changes.

A real paused-question browser check also exposed two defects: paused course jobs could keep the composer busy indefinitely, and DRF rejected EventSource's `Accept: text/event-stream` header with HTTP 406. The fix derives composer busy state from submission/current conversation messages and allows the event-stream media type only on the stream action. Browser errors and course lookup boundaries retain their HTTP statuses. The interface labels unconfigured AI questions as saved for later rather than promising an answer in progress.

The backend suite now passes 78 tests, including browser-style success/reconnect, paused completion and cross-course rejection. The frontend build, lint and 14 tests pass; the authored timing/coordinate suite passes 10 tests. A real temporary course saved two paused questions through the UI, restored four messages, recovered its composer and kept its second conversation empty. The updated stream returned HTTP 200 with paused/error/done events. Only the temporary course was deleted.

Revision 3 is 927.7 seconds with SHA-256 `032f8aa73a6baf7afaadd4ad317067fcdc1d4220e8831c1b58f071b35733af3e`. Media/timeline, HTTP Range, caption, contextual-question/follow-up and 21-sample audio-alignment checks pass again. Revision 2 retains its original hash. The revised seven chapters rendered in 916.77 seconds with 629.28 MB peak sampled process-tree RSS; an unchanged run reused all seven in 0.334 seconds with 43.54 MB sampled RSS. These remain single observations, not performance comparisons.

The ninth, user-authorized reviewer approved the bounded follow-up with no blocking regression. They independently checked the installed revision/hash/cache identities, Range response, preserved prior media, real player/source highlights at 429 seconds, paused-composer recovery, conversation isolation and selected page-22 context. Durable checked-in frontend state regression tests remain a follow-up. This review does not establish equivalent teaching quality or normal-speed human listening.

The user subsequently rejected the interface's appearance as unprofessional and deferred its redesign. The [UI backlog](UI-REDESIGN-CHECKLIST.md) records the requested future work and completed functional LaTeX support. Functional review approval does not imply acceptance of the current visual design.

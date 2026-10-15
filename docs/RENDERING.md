# Controlled local lesson rendering

The renderer accepts validated lesson JSON and runs one fixed Manim program. It never executes model-generated Python, shell commands or TeX programs. Equations support plain Unicode text or bounded LaTeX notation converted locally to SVG. Plot coordinates are explicit finite samples or come from supported calculations; no arbitrary expression evaluator is installed. Source references and scene/object IDs survive into the playback manifest.

From the repository root on Windows:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-render.txt
$env:PYTHONPATH = 'backend/tldr_backend'
backend/.venv/Scripts/python.exe -m study.rendering
backend/.venv/Scripts/python.exe -m study.rendering examples/bus-read.json --validate-only
backend/.venv/Scripts/python.exe -m study.rendering examples/bus-read.json --output examples/rendered/bus --cache examples/render-cache
backend/.venv/Scripts/python.exe -m unittest study.rendering.test_rendering -v
backend/.venv/Scripts/python.exe -m study.rendering.visual_checks
backend/.venv/Scripts/python.exe examples/render_proof.py --all-primitives
backend/.venv/Scripts/python.exe examples/recovery_proof.py
```

These commands use no API key. Windows PowerShell and its System.Speech desktop voice synthesize WAV narration. Manim 0.19.0 supplies Cairo/Pango visuals; `imageio-ffmpeg` supplies FFmpeg if it is absent from PATH. A TeX installation is unnecessary. Equation typesetting additionally requires Node.js and `npm ci` in `frontend/tldr-frontend`. The default voice is the Windows System.Speech default. A missing voice or media dependency causes an actionable failed render, not a silent or simulated success. Dependency status reports installed tools; successful synthesis still depends on a working installed voice.

## Local LaTeX equations

An `equation` object can include `latex`, without delimiters, alongside its required plain `text` fallback and label. For example: `{"id":"slope","kind":"equation","label":"Derivative","text":"Derivative of x squared is two x","latex":"\\frac{d}{dx}x^2=2x"}`. Narration must use spoken words. The storyboard provides an equation editor and browser preview; video validation uses a narrower notation contract.

The fixed Node converter uses MathJax 4.1.3 with bundled New Computer Modern fonts, only base/AMS packages and network access disabled. Python validates a closed command/environment list before conversion and revalidates the resulting SVG. Equations are limited to 600 characters, brace depth 20 and twelve row breaks. Fractions, roots, calculus, matrices, aligned equations, cases and units via `\mathrm` are supported. File access, links, HTML, macro definitions and dynamic extensions are rejected. The full policy lives in `backend/tldr_backend/study/rendering/math-policy.json`; invalid notation fails visibly rather than producing an invented replacement.

SVG caches include the notation, converter/policy/helper hashes, dependency lockfile and package versions. Cached SVG digests and structure are checked before reuse. Equation changes invalidate affected scenes. Rendering notation does not verify it: arbitrary `latex` objects remain conceptual, even when they also carry a separately checked calculation.

Run `backend/.venv/Scripts/python.exe examples/math_workspace.py` with the API/worker running to install the original short math workspace fixture. It contains a quadratic, a derivative limit and a matrix determinant. The installed proof is 63.253 seconds at 720p/30 fps with Windows narration and captions. It is not a 10–20-minute generated lesson. Browser captions can typeset delimited math; the exported VTT and native subtitle track remain plain text.

## Callable contract

`study.rendering` exports:

- `lesson_json_schema()` returns the closed JSON schema used in generation prompts.
- `validate_lesson(spec)` returns a copied, validated spec or raises `LessonValidationError`.
- `narration_guidance(target_minutes=15)` describes substantive narration and chapter requirements.
- `dependency_status()` reports Manim, FFmpeg and Windows speech availability.
- `render_lesson(spec, output_dir, cache_dir, trusted_assets=None, on_progress=None, is_cancelled=None)` returns the output manifest or raises `RenderCancelled` / a media error. The optional arguments are keyword-only.

Progress callbacks receive `{stage, scene_id?, completed, total, cached?}`. Stages are `narration`, `rendering`, `assembling`. Callbacks run synchronously in the rendering worker. Cancellation is checked before scenes and every 150 ms while waiting for a subprocess. Windows process trees are terminated with taskkill; a restricted environment falls back to terminating the owned direct child. An individual process has a 30-minute timeout; speech has a ten-minute timeout.

The disposable Windows Manim child exits explicitly after `Scene.render()` closes its writer and the completed movie is copied. This avoids an observed native interpreter-shutdown hang after successful rendering. The API/worker parent remains running and independently validates the copied media before caching it. Failed renders still raise errors and cannot acquire completion markers.

The manifest contains relative filenames `video`, `captions`, `transcript`, `poster`, plus `video_path` and `subtitle_path` for the local worker. The backend exposes these only through course-authorized media routes. It also contains measured `duration_seconds`, timed `chapters`, timed `scenes`, sentence `cues`, cache keys, version/configuration metadata and warnings. Source refs are opaque identifiers: production generation uses `p{page_id}` / `r{region_id}`. Backend citation validation and ownership checks resolve them. Fixtures use `original-*-fixture` because they are original instructional material, not uploaded pages.

## Supported visual language

Every scene contains `id`, `title`, `narration`, `source_refs`, `objects` and ordered `steps`. Each step selects `object_ids` and a `caption`. Objects require `id`, `kind` and `label` plus the kind's data:

| Kind | Data | Behaviour and limits |
| --- | --- | --- |
| `text` | `text` | Plain text explanation |
| `equation` | `text` | Safe Unicode equation, no TeX interpreter |
| `plot` | `points: [[x,y],…]` | Draw explicit ordered samples; connecting segments approximate a curve |
| `geometry` | `shape` | Draw circle, rectangle or triangle |
| `process` | `nodes` | Two to five labelled stages with arrows |
| `circuit` | Exactly two `nodes` | Ideal source–single-resistor loop, battery/resistor/ground symbols, moving current indicator |
| `bus` | Exactly two `nodes` | Address, read-request and return-data channels with sequential moving signal tokens |
| `timing` | `signals: [{name, values:[0,1,…]}]` | Digital traces and moving time cursor, highlighting the first asserted Sample phase when supplied |

Unknown kinds, fields, unsafe identifiers, unknown step references, duplicate stable IDs, nonfinite samples and excessive sizes are rejected. The circuit primitive does not support arbitrary topologies, AC analysis, transients or component simulation. The bus is a pedagogical handshake, explicitly **not an exact ECE224 or processor-specific protocol**. Animated current/signal tokens are teaching indicators, not physical particle trajectories or measured propagation speeds.

Optional `calculation: {kind, inputs}` objects run a small deterministic calculation and display its result. Supported kinds are `bus_read`, `ohms_law`, `compound_interest`, `quadratic`, and `biology_concept`; see `schema.py` for exact input keys/domains. Biology results identify themselves as conceptual illustrations. These calculations do not establish the correctness of every narrative claim. Grounding, source checks and human storyboard review remain necessary.

## Duration, synchronization and outputs

The optional `purpose` is `lesson` (default) or `followup`. Follow-up clips accept target durations 1, 2 or 3 minutes; full lessons accept 10, 15 or 20. Mixing a follow-up purpose with a full-lesson duration, or omitting the follow-up purpose for a short target, is rejected. Follow-up narration guidance asks for one focused chapter and two to four scenes.

Targets are 10, 15 or 20 minutes (generation default 15). A target is a script-writing goal. The renderer measures the actual WAV narration, allocates each scene's visual steps across that speech, and reports the actual assembled duration. It never stretches, loops or adds silence to fill a target. A difference greater than 20% produces a clear warning. The example fixtures are **short proofs**, not completed ten- or fifteen-minute lessons.

Each scene is limited to three minutes of speech. Split longer material into focused scenes. At most 120 scenes are accepted. Output is 1280×720 at 30 fps, H.264/AAC MP4 with a selectable embedded subtitle track, plus WebVTT captions, UTF-8 transcript, JPEG poster and JSON scene index/manifest. Assembly re-encodes at a constant frame rate to avoid timestamp gaps from joining AAC clips.

Sentence captions use the Windows engine's `SpeakProgress` word audio positions and source character positions. A fixed C# event collector records these alongside each WAV. Steps may supply `narration_anchor`, an exact phrase in the narration, to begin at its spoken position. Anchors must occur in script order. Missing anchors use evenly distributed slots; missing speech marks use explicitly labelled estimated captions. The manifest reports which caption timing method was used. Domain animations illustrate progression within each slot; this is not a general animation choreography language. Microsoft documents the [speech progress fields and their offsets](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speakprogresseventargs?view=netframework-4.8.1).

Speech output is explicitly 16 kHz, 16-bit mono PCM. This keeps the tested desktop voice's word-event positions consistent with WAV time; the engine's default output format gave inconsistent positions in local testing. All marks must be finite, in range and monotonic. Invalid marks trigger an entirely estimated sequence, never a mixture that could produce negative subtitle durations. The narration cache validates both WAV and speech-mark hashes.

## Cache and recovery

Narration keys include its exact text, speech script hash, engine, voice/rate configuration and platform. Scene keys include the validated scene, narration key, renderer source hashes, Manim/PyAV/FFmpeg package versions and rendering configuration. Changing a scene only regenerates that scene; changing narration regenerates that speech and scene. Changing rendering code invalidates scene media while allowing speech reuse.

Only completed cache entries with matching SHA-256 and valid media streams/duration are reused. Interrupted files have no completion marker and are ignored. The output checkpoint records completed scene IDs and cache keys after every scene. On worker restart, calling the same render again reuses those valid entries. Cache directories should be course-scoped and operated by the single rendering worker; simultaneous independent writers to one shared cache are not supported.

The proof script records wall time, sampled peak process-tree RSS, cache hits, actual duration and dependency versions in `examples/proof-results.json`. Its warm run must reuse both bus scenes. Editing one caption must reuse exactly one. Generated artifacts and caches are ignored by Git; the original fixtures and reproducible commands are versioned.

## Numerical verification

Known-answer tests cite their analytical basis in the test source: 42 is binary `00101010`; a 12 V / 6 Ω ideal circuit carries 2 A and dissipates 24 W; 1000 compounded annually at 5% for two years becomes 1102.5; and direct quadratic substitution is checked exactly. Boundary tests reject invalid resistance, overflowing bus values, NaN, unknown executable fields and invalid object references. Cancellation tests terminate an actual sleeping child process.

The implementation follows the [Manim Community rendering guide](https://docs.manim.community/en/stable/guides/deep_dive.html) and uses reviewed declarative primitives through `Scene.render()` and `tempconfig`. No numerical solver or stochastic model is used.

## Original-source images and verified plots

`source_image` objects take an existing `source_ref` (`p{page_id}` or `r{region_id}`) and optional normalized overlay rectangles. Model output cannot supply paths or URLs. Production revision citations snapshot the asset's source/page identity, image digest, dimensions and region crop. Before rendering, the backend resolves same-course assets and rejects changed, missing or mismatched snapshots. Trusted PNG bytes enter a separate renderer argument; their digest, crop and overlay geometry participate in the scene cache key. The original image keeps its aspect ratio and color; highlights are separate display objects.

For calculated plots, supply `calculation.kind` as `quadratic_plot` or `ohms_law_plot` with the documented finite inputs from `schema.py`. The server generates the samples. A plot cannot supply both a checked calculation and its own points. The manifest labels original-source, verified-tool and conceptual objects separately. Unchecked point arrays are conceptual data illustrations.

A real source-image render produced a 9.088-second 720p/30 fps video with audio and captions; the inspected source digest was unchanged. This proves the bounded source-display path, not correctness of a generated interpretation. The independently reviewed fixed opening and extension direction are documented in [the quality record](DEMO-QUALITY.md) and [animation architecture](ANIMATION-ENGINE.md).

## Local proof evidence

The Windows proof produced a 45.481-second narrated bus clip with H.264 video, AAC audio and an embedded subtitle track, verified at 1280×720 and exactly 30 fps. Its captions use actual System.Speech word events and all cue intervals are positive. The original circuit proof was rerendered after visual review corrected the battery symbol polarity; the final clip is 25.792 seconds. Geometry checks verify that the long positive plate is above the short negative plate, conventional current exits the upper positive terminal, and every timing trace shares the same time origin. The renderer unit suite contains 22 numerical, schema, caption, cancellation, corruption and follow-up-duration checks.

All six original short fixtures were rendered locally: bus, mathematics, finance, biology, circuit and geometry. No Gemini call was used. Cancellation during a real second-scene render retained the first-scene checkpoint, and restart completed the lesson with one scene-cache hit. These are local functional proofs, not claims of protocol fidelity or broad numerical simulation. The separate longer lesson fixture is maintained and validated by the integrating task; its final duration should be read from its own generated manifest.

The final short-bus cache proof completed with 0, 2 and 1 scene-cache hits for initial, unchanged and single-caption revision runs respectively. Observed wall times were 84.77, 14.56 and 45.97 seconds; peak sampled process-tree RSS was 976, 323 and 951 MB. This was one functional measurement sequence while other local work was running, not an isolated performance benchmark or a speedup guarantee. Exact values and dependency versions are reproduced in the ignored `examples/proof-results.json` output.

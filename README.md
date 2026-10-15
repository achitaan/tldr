# TLDR

A local desktop-browser study workspace: keep course sources together, ask image-aware questions with citations, and turn concepts into narrated visual lessons you can pause and question.

The current interface is a functional prototype. The user requested a later redesign; the prioritized [UI checklist](docs/UI-REDESIGN-CHECKLIST.md) records that deferred work. Local LaTeX rendering now covers chat, source previews, study notes, quizzes and both sides of flashcards.

The [complete project overview](docs/PROJECT-OVERVIEW.md) covers the architecture, source-to-lesson pipeline, memory/RAG, current verification, remaining work, and the selected Cinema Video / Margin Notes frontend direction.

React and TypeScript provide the workspace. Django REST Framework stores courses, conversations, annotations, study items and lesson revisions in SQLite. Retrieval searches only the current course. Gemini supplies structured answers and storyboards; local code validates them before Manim renders video.

## Run on Windows

The verified setup uses Python 3.10 and Node.js 22 on Windows. Python 3.10 receives the checked dependency constraints; newer Python versions use the declared ranges and have not been verified here. Tesseract is needed for screenshots and scanned pages. The renderer uses installed Windows voices through System.Speech; its FFmpeg fallback is installed with the rendering dependencies. The controlled renderer does not execute generated Python.

In PowerShell, from this repository:

```powershell
.\scripts\setup.ps1 -WithRenderer
.\scripts\start.ps1
```

Open **http://127.0.0.1:5173**. Keep the launcher running; Ctrl+C stops its API, worker and frontend processes. Logs are under `artifacts/logs/`.

The static portfolio preview is **http://127.0.0.1:5173/?demo=1**. It uses original sample material and makes no AI requests. Real uploads belong in the local workspace, never in a public deployment.

The checked local installation also includes an authored ECE224 bus-read lesson of approximately **15½ minutes**, using original course diagrams, checked setup/hold examples, captions and seven practice checkpoints. Its latest local revision and verification are in the [receiving-endpoint production record](docs/ENDPOINT-CHECKPOINT.md); the [demo quality record](docs/DEMO-QUALITY.md) retains earlier production history. Supplied course figures remain local; they are not part of the static portfolio preview. This sample runs without an AI key; generating new answers or lessons still requires configuration.

To build a static-only portfolio bundle, run these commands from `frontend/tldr-frontend`:

```powershell
$env:VITE_DEMO_MODE='true'
npm run build
Remove-Item Env:VITE_DEMO_MODE
```

Publish only its `dist/` output. This repository does not deploy or publish automatically.

## Configure free-tier AI

Course storage and source editing work without an API key. Generation requires your own eligible Gemini project. Before enabling it:

1. Create a dedicated project in [Google AI Studio](https://aistudio.google.com/) and verify **billing is disabled**. Check the model's current free quota in your account.
2. Read Google's [free-service data terms](https://ai.google.dev/gemini-api/terms). Selected source excerpts and relevant images are sent to Google; free-service content may be used to improve products. Start with non-sensitive examples.
3. Copy `.env.example` to `.env.local` in the repository root, add the project's key, and set these acknowledgements only after those checks:

```dotenv
TLDR_FREE_PROJECT_ACK=I_CONFIRM_BILLING_IS_DISABLED
TLDR_DATA_TERMS_ACK=I_ACCEPT_GOOGLE_FREE_TIER_DATA_TERMS
```

Restart the launcher after configuration changes. Values in `.env.local` are literal `NAME=value` entries, without quotes or shell expansion. Keys stay in the backend environment and are never returned to the browser. Legacy `backend/tldr_backend/.env` is not loaded.

The default model is `gemini-3.8-flash`, listed with free input/output in Google's [pricing documentation](https://ai.google.dev/gemini-api/docs/pricing) when checked on October 13, 2026. The app cannot prove billing status from an API key. Account eligibility and quotas must be checked in AI Studio; free availability can change. It never enables billing or selects another provider. A quota response pauses generation and saves the job until you explicitly retry after quota is available.

There is no required subscription. The service-cost target is $0 within the dedicated project's free quota; electricity, internet and disk use remain.

## Memory and sources

- SQLite stores conversations, course folders, source corrections, image regions, lesson revisions and study progress across restarts.
- SQLite full-text retrieval finds course passages. Optional local `embeddinggemma` embeddings add semantic retrieval through Ollama at `127.0.0.1:11434`.
- To enable semantic retrieval, install Ollama, run `ollama pull embeddinggemma`, set `TLDR_OLLAMA_EMBEDDINGS=1`, and restart TLDR. No large local tutoring model is required. Keep Ollama cloud features disabled.
- PDFs preserve page images and extracted text. Screenshots and scans use local Tesseract OCR. Correct extraction errors before relying on a citation.
- Citation validation checks that quoted text exists in the retrieved source. It does not prove the model's scientific interpretation is correct.

New data lives in `backend/tldr_backend/local_data/`, outside Git. `TLDR_DATA_DIR` can select another local directory. Back up that entire directory while the app is stopped. Course export downloads an archive; deleting a course removes its records and associated media. Original legacy data remains local and is not automatically imported.

## Visual lessons

Math supports `\(x^2\)` or `$x^2$` inline and `\[\frac{1}{2}\]` or `$$\frac{1}{2}$$` as display equations. Flashcards retain raw LaTeX while editing and offer a preview. KaTeX and its fonts are bundled locally. Unsupported expressions remain readable as their original TeX; webpage equation cross-references are not resolved. Typesetting does not verify mathematical correctness.

The installed local math sample is [Mathematics — LaTeX samples](http://127.0.0.1:5173/?course=11&revision=4), with two flashcards, a quiz, formatted notes and a 63-second narrated equation video. This is a short typesetting sample. To install it in another local database while the API and worker run, use `backend/.venv/Scripts/python.exe examples/math_workspace.py`; the script prints its new local URL. No AI key is needed. See [the math contract](docs/RENDERING.md#local-latex-equations) for video notation limits.

Review the storyboard before rendering. Lesson targets are 10, 15 or 20 minutes. Actual narration length is checked rather than padded with blank screen time. Rendered scenes have stable identifiers, captions and a transcript. Questions retain the lesson revision, scene, timestamp and selected objects; a separate 1–3-minute follow-up lesson keeps the original intact.

The storyboard also supports a separate [teaching plan](docs/TEACHING-PLAN.md): goals, prerequisites, scene assignments, evidence bindings, visual purposes and proposed questions. Validate coverage locally, then save edits as a new revision. Checks flag broken/stale references and missing planning coverage; they do not certify scientific correctness. Proposed questions remain distinct from actual video checkpoints. See the [source-to-lesson workflow](docs/TEACHING-PIPELINE.md) for the full pipeline design and remaining stages.

Supported visuals are controlled equations, sampled graphs, geometry, processes, circuit symbols, bus links and timing signals. Verified calculations are deliberately bounded. Other diagrams are conceptual illustrations, not circuit or physics simulations. Unsupported scenes require correction rather than arbitrary generated code execution.

One generation lane and one rendering lane run at a time. Jobs persist; rendering reuses unchanged scene and narration caches. See [rendering documentation](docs/RENDERING.md) for the schema, sample fixtures and rendering commands. See [API contract](docs/API.md) for local integration.

## Development and verification

Use **Import webpage** in the source desk to add a single public HTTPS page, such as [Paul's Online Math Notes: Definition of the Derivative](https://tutorial.math.lamar.edu/Classes/CalcI/DefnOfDerivative.aspx). The local worker saves the HTML for download and extracts article text, headings, links, and source TeX. Importing does not require Gemini credentials. It does require outbound HTTPS access; blocked sites and pages that depend on JavaScript can fail or yield incomplete text.

Web sources show their origin and fetch time. The extraction is plain text; images and interactive diagrams are not reconstructed. Open the original page or upload a PDF for faithful visuals. After updating an existing installation, run `python manage.py migrate` from `backend/tldr_backend` using the backend virtual environment, then restart the API and worker. The additive website provenance migration preserves existing file/text sources. See the [website API contract](docs/API.md#webpage-sources) for network and size limits.

```powershell
.\scripts\verify.ps1
```

The checks run without AI credentials. Live Gemini quality, quota and long-lesson throughput require a configured free project and representative course material. See [verification record](docs/VERIFICATION.md) for checks actually performed and remaining limitations; passing mocked provider tests is not evidence of live model quality.

The original long bus fixture rendered locally into a **12:52 narrated video**, with 12 scenes and synchronized captions. This verifies local rendering of a reviewed script; it does not establish the quality of an AI-generated lesson.

This application is intended for a single user on loopback interfaces. Do not expose its local API to a network or use the development server for public accounts.

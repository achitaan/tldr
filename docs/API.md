# TLDR local API contract

Base: `http://127.0.0.1:8765/api/`. JSON, trailing slashes, integer IDs. Lists are JSON arrays (no pagination). Errors use `{detail: string}` or DRF field errors. Every course-filtered list requires `?course=<id>`. Stored course data is local. Explicit webpage imports contact the requested public website; explicitly enabled Gemini generation contacts Google. Browser origins are restricted to local app origins. No API key is returned.

## Resources

- `/courses/`: GET list, POST `{name, description?}`. `/courses/{id}/`: GET/PATCH/DELETE (cascades all course data and media). Fields `id,name,description,created_at`.
- `/sources/?course=id`: GET; POST multipart `{course,title?,file}` or JSON `{course,title,text}`. PDF, PNG/JPEG/WebP, UTF-8 `.txt`/`.md`; max 20 MB and 100 PDF pages. Returns source with `id,course,title,kind,status,error,original_url,created_at,pages`. Ingestion creates a persistent job. `status`: queued/ready/error. Pages contain `id,source,number,text,original_text,corrected,image_url,width,height,regions`. Poll source/job until ready. `/sources/{id}/`: GET/DELETE.
- `/pages/{id}/`: GET/PATCH `{text}` for OCR correction and retrieval reindex. Original extraction retained. `/regions/?course=id`: GET; POST `{page,label?,x,y,width,height,text?,confirmed?}` with normalized coordinates in [0,1], rectangle entirely inside page; PATCH/DELETE `/regions/{id}/`. Regions contain `id,page,label,x,y,width,height,text,confirmed`.
- `/conversations/?course=id`: GET; POST `{course,title?}`. `/conversations/{id}/`: GET/PATCH title/DELETE. `/conversations/{id}/messages/`: GET ordered messages; POST `{content,region_ids?:[],context?:{revision_id,scene_id,time_seconds,object_ids:[]}}` returns HTTP 202 `{message,job}`. Fields `id,conversation,role,content,citations,context,status,created_at`. `citations` each `{page_id,source_id,source_title,page_number,quote,region_id?}`; quote must exactly occur in the supplied page/region extraction. Status pending/complete/error.
- `/conversations/{id}/stream/?job=id`: GET SSE, accepting the browser's `Accept: text/event-stream` header. Emits `event: status` with job; `event: message` with completed persisted assistant message; `event: done` on terminal state, or `event: error` for failure/pause. Generation is buffered until validated, then delivered; no unvalidated token streaming. Reconnect/reload recovers persisted messages. Event-stream negotiation is scoped to this action; pre-stream errors keep their HTTP status and use an SSE error body when requested. Other API actions retain their normal content-negotiation rules.
- `/lessons/?course=id`: GET; POST `{course,title,prompt,region_ids?:[]}` creates lesson and generation job; response includes `job`. `/lessons/{id}/`: GET/PATCH title/DELETE. Fields `id,course,title,created_at,revisions,jobs`. `/lessons/{id}/revisions/`: GET list; POST `{prompt,region_ids?:[]}` queues a new immutable revision, returns `{job}`. `/lessons/{id}/render/`: POST `{revision_id}` queues render, returns `{job}`.
- Revision fields: `id,lesson,number,spec,citations,teaching_plan,manifest,video_url,captions_url,transcript_url,poster_url,created_at`. `spec` is the renderer-owned validated lesson schema described below; malformed output is rejected, never executed. `teaching_plan` is separate nullable planning data, saved only on new revisions.
- `/jobs/?course=id`: GET; `/jobs/{id}/`: GET. Fields `id,course,kind,status,progress,error,result,created_at,updated_at`. Kinds ingest/chat/lesson/render. Status queued/running/complete/failed/cancelled/paused. `/jobs/{id}/cancel/` POST; `/jobs/{id}/retry/` POST requeues failed/paused jobs only after configuration is ready. Quota errors pause generation until explicit retry; no paid/model fallback. Result includes `source_id`, `message_id`, or `revision_id` as applicable.
- `/study-items/?course=id`: GET; POST `{course,kind,title,body?,data?,page?,lesson?}`. `/study-items/{id}/` GET/PATCH/DELETE. kind flashcard/quiz/checklist/bookmark/confusion; body text; data object (e.g. flashcard `{answer}`, quiz `{options,answer,attempts}`, checklist `{items:[{text,done}]}`), `completed` boolean. References must belong to the same course.
- `/courses/{id}/export/`: GET ZIP with course JSON, original documents, page images, lesson specs and rendered artifacts. `/data/`: DELETE `{confirm:"DELETE ALL LOCAL DATA"}` removes all study records and media.
- `/status/`: GET `{provider,model,generation_enabled,configuration_issues,quota_paused,ocr_available,embedding_enabled,embedding_model,worker}`. `POST /status/resume/` clears global quota pause (explicit acknowledgement to try again); does not retry paused jobs automatically.

## Generation configuration

### Webpage sources

POST `/sources/` with JSON `{course,url,title?}` returns HTTP 201 with a queued source and persistent `job`. The same worker, polling, cancellation, retry, deletion, and course-scoping contracts apply. Import one page per request; links are retained as text and never crawled. URL, file, and pasted text inputs are mutually exclusive.

Web sources have `kind:"web"` and additive fields `source_url`, `fetched_url`, `fetched_at`, `digest` (SHA-256 of decoded HTTP-body bytes saved as HTML), and `extraction_notes`. An omitted title becomes the extracted document title when available. Extracted pages retain source attribution, headings, links, plain TeX, and image alternative text. No remote scripts, frames, formulas, or subresources are executed or fetched. HTML originals are attachment-only with a sandbox CSP; the UI renders extraction as plain text and links to the original site. Images, layout, interactive content, and JavaScript are not archived; use a PDF for faithful diagrams.

The importer requires public HTTPS on port 443 without credentials. It checks all DNS answers on every redirect, pins a checked numeric address for the connection, and verifies TLS against the original hostname. Proxy environment settings are unused. Limits: three redirects, 30 seconds across the request chain, five-second DNS/connect bounds, eight-second maximum read waits constrained by the remaining deadline, 2 MB body download, 5 MB decompressed HTML, bounded HTTP framing, and bounded extraction complexity. Invalid URLs fail immediately with HTTP 400; DNS, HTTP, TLS, extraction, and size failures set the source to `error` and job to `failed`, with a user-visible error.

Apply migration `0004_source_web_provenance` before restarting the API and worker. Existing sources receive blank/null provenance; file and text request shapes are unchanged.

Deleting a source removes its originals, extracted pages, and regions. Existing lesson videos and render caches may retain source snapshots; delete the course to remove its lessons and course-scoped render cache.

`GEMINI_API_KEY`; `TLDR_GEMINI_MODEL` defaults `gemini-3.8-flash`; `TLDR_FREE_PROJECT_ACK=I_CONFIRM_BILLING_IS_DISABLED`; `TLDR_DATA_TERMS_ACK=I_ACCEPT_GOOGLE_FREE_TIER_DATA_TERMS`. Both acknowledgements required before any cloud request. The application cannot inspect project billing from an API key. Bounded timeouts/retries; 429 pauses queue; no model/provider fallback. Optional `TLDR_OLLAMA_EMBEDDINGS=1` enables local `embeddinggemma` at fixed `http://127.0.0.1:11434` (model must already be installed). Missing embeddings retain local lexical retrieval with status visibility.

Run `python manage.py study_worker` in one process; one generation/ingestion thread and one rendering thread claim persisted jobs. Interrupted running jobs recover at worker startup. API does not spawn workers. No scheduled ingestion/cloud processing without user action.

## Lesson schema

### Teaching-plan validation

`POST /courses/{id}/teaching-plan/validate/` accepts exactly `{revision_id}` for a revision in that course, or `{spec,teaching_plan}` for an unsaved draft. It returns current structural findings, per-goal explanation/planned-check/installed-practice coverage and evidence fingerprints. It creates no jobs and makes no provider requests. Foreign revisions return 404; malformed requests return 400; integrity findings return 200 with `can_save:false`. Drafts cannot supply a render manifest. A missing plan is explicit and can still show saved-media diagnostics.

`POST /lessons/{id}/revisions/` additionally accepts `{spec,citations,teaching_plan?}` to save an immutable local storyboard revision without generation. A non-null plan requires `spec`; prompt-only requests carrying a plan return 400 before any job is created. Omitted/null preserves the existing prompt-generation contract. Malformed or integrity-invalid plans are rejected before revision creation; missing coverage can save as an incomplete draft. See [the complete plan format and bounds](TEACHING-PLAN.md). Structural completeness is not scientific approval, and proposed checks are not installed video checkpoints.

### Renderer specification

See [the renderer contract](RENDERING.md). Equation objects accept optional bounded `latex` notation alongside the required plain `text` fallback. Other object kinds reject this field. Treat `spec` as validated JSON; use the completed manifest's authoritative scene times for synchronized playback. Assets have same-origin `/media/` URLs.

Message content and study item titles, bodies, answers and quiz choices preserve raw LaTeX strings. The browser formats standard delimited math locally; it does not store generated HTML. Source-text previews likewise leave saved text and citation quotes unchanged. Browser support is broader than the closed video notation policy.

## Contract clarifications

- Lesson create/generate accepts `target_minutes` 10, 15 or 20 (default 15). Generation creates a storyboard revision only. Review it before calling the explicit render action.
- A follow-up uses POST `/lessons/` with `purpose:"followup"`, `target_minutes` 1, 2 or 3 (default 2), and required `context:{revision_id,scene_id,time_seconds,object_ids}`. This creates a separate lesson. Revision generation rejects the follow-up purpose. The backend retrieves the paused scene's actual source references and supplies its content even for a question such as "Why?"; context must belong to the same course. Once rendered, timestamps must fall inside the selected scene's manifest interval.
- POST `/lessons/{id}/revisions/` may instead contain `{spec,citations}` to save an edited storyboard as a new immutable revision. Schema, course ownership, exact quotes and scene source references are revalidated.
- Revision responses include nullable `manifest`, populated after rendering, with authoritative scene times/cues/duration and duration warnings.
- A selected region with no extracted text can use `{page_id,region_id,quote:"",visual:true}` only when its image was supplied to Gemini. The UI distinguishes visual evidence from exact extracted-text quotes. At most three downsampled local images/crops are sent with any generation request.
- Only `gemini-3.8-flash` is allowed; other model settings disable generation pending explicit verified-free support. Local rendering caches are course-scoped and removed with the course.

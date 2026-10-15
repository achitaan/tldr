# TLDR: source ingestion, application memory, and learning retention

Research snapshot: 2026-10-13. Read-only inspection of the working tree plus official documentation and primary studies. Implementation may change concurrently; the code findings below describe the inspected baseline. No model benchmark, learner experiment, dependency installation, or database change was performed.

**Decision.** Build around preserved originals, versioned passages, and source-linked learning attempts. Keep SQLite and local extraction as the baseline. Improve passage coverage and provenance before adding a larger model, a vector service, or an elaborate memory framework. Treat Docling and a local reranker as candidates for a bounded comparison, not established improvements on TLDR's material. Confidence: high for the architectural priorities; medium for the best extraction/model choice until representative course files are measured.

Three different outcomes need separate records and tests:

| Outcome | Record | Evidence of success |
|---|---|---|
| Faithful ingestion | Original bytes, page image, text/layout extraction, corrections | The source content and its location survive extraction |
| Useful application memory | Versioned passages, citations, selected user preferences, conversation events | The tutor retrieves the right current evidence across sessions |
| Student retention | Unassisted attempts, feedback, later reviews | The learner recalls and applies material after a delay |

Saving every chat establishes persistence. It does not establish successful retrieval or learning.

**Observed code gaps and strengths — high confidence.**

| Location | Observed behavior | Consequence |
|---|---|---|
| `backend/tldr_backend/study/ingestion.py` | Retains source originals and SHA-256 digest; renders PDF pages to PNG; caps images at 2400 pixels on the longest side | Sound foundation for original visuals; small labels need an on-demand higher-resolution crop from the original |
| Same | PDF text extraction first; OCR only when the whole page's extracted text is blank; plain OCR strings | A page with a digital title and a scanned figure can skip OCR for the figure; reading order, word boxes, and confidence are discarded |
| Same | One `Page` per PDF page; text files split every 12,000 characters; extracted page text capped at 100,000 characters | Page boundaries and fixed character cuts are not reliable semantic boundaries; truncation should be reported |
| `retrieval.py` | FTS5 plus optional cosine search, combined with reciprocal-rank-style scores | Hybrid retrieval already exists; improve it rather than describing it as absent |
| Same | One embedding per page, first 12,000 characters; semantic candidates limited to the first 1,000 course pages | Later content can be absent from semantic search; lexical search is not subject to that 1,000-page cap |
| Same | Returns up to eight evidence items, each at most 6,000 characters; window anchored by a matching query token | A semantic match without matching query words can return the opening text instead of the supporting passage |
| Same | Course filters and exact substring citation validation | Useful isolation and quote integrity; exact quotation alone does not prove that the cited text supports the answer |
| Same | `image_parts` stops at `len(parts) >= 6`, adding two parts per image | At most three image inputs are supplied, despite six being an easy reading of the bound; selection order matters |
| Same / `models.py` | Selected regions are included without filtering `confirmed`; the comment calls them user-confirmed | Treat selection and confirmation as separate states; define which state authorizes factual use |
| `models.py`, `views.py` | Original and corrected text retained, but corrections overwrite current text; citations lack extraction-version hashes | Later edits can make old explanations stale; source digest alone does not version OCR corrections |
| `jobs.py` | Last ten complete messages supplied; no durable structured conversation summary | Earlier preferences, unresolved questions, and corrected misunderstandings fall out of context |
| `models.py`, `StudyTools.tsx` | Flashcards, quizzes, and completion state; no explicit attempt history or review schedule | Completion/reveal does not demonstrate recall; scheduling needs observed attempts |
| `SourceWorkspace.tsx` | Original page image with SVG region overlays, rotation, and zoom | Reuse this coordinate/provenance model for lesson visuals |
| `rendering/schema.py` | No source-image object in the inspected baseline; free plot samples are checked for finiteness and increasing x | A scene citation does not reproduce the cited diagram; syntactically valid samples need not describe a valid scientific curve |

**Ingestion choices and local feasibility.**

| Approach | Fit | Cost and uncertainty | Decision |
|---|---|---|---|
| Extend current PDFium/Tesseract pipeline | Digitally generated PDFs, ordinary scanned text, immediate source crops | No per-call service charge; CPU time, storage, and maintenance remain. Layout/OCR accuracy must be measured | First implementation |
| Optional Docling adapter | Mixed layouts, tables, picture/caption relationships, structured passages | Local model downloads and additional runtime/RAM; exact cost on this computer is unmeasured | Evaluate on difficult pages before adoption |
| Vision-model extraction | Potential help for handwriting, diagrams, ambiguous notation | Can invent or misread content; hosted use requires configuration, quota, and data-transfer acceptance | Suggest annotations with visible uncertainty; never replace original evidence |

Tesseract supports structured TSV/hOCR with word coordinates and confidence; retain those instead of only its flattened text. Confidence is a triage signal, not a calibrated probability that a mathematical symbol is correct. [Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).

Docling's document model represents text, tables, pictures, hierarchy, reading order, provenance, and available bounding boxes. Its formula enrichment can produce LaTeX. Those capabilities justify a trial, not a claim that extracted mathematics is correct. Keep any formula transcription next to its original crop until checked. Context7 also verified offline use with previously downloaded model artifacts. [Document model](https://docling-project.github.io/docling/concepts/docling_document/), [enrichments](https://docling-project.github.io/docling/usage/enrichments/), [offline configuration](https://github.com/docling-project/docling/blob/main/docs/faq/index.md).

Recommended ingestion contract: retain immutable original bytes; derive versioned page renders; extract text blocks and boxes; selectively OCR image regions or suspicious pages; attach figure captions and nearby explanatory text; create passages with exact offsets back to that extraction version. Store extractor/version/settings, language, source/page IDs, digest, dimensions, coordinate origin, rotation, block type, reading order, and review state. Separate machine text, human correction, and generated description. Never index generated descriptions as if they were source quotations.

**Retrieval and persistent application memory.**

1. Add a `Passage` representation without replacing original pages. Start with paragraph/section units, approximately 300–600 tokens as a tunable seed, preserving heading context and limited overlap. Keep equations, figure captions, table rows and their headers together when possible. Larger units can be returned by expanding from a matched passage to neighboring blocks. This size is an engineering hypothesis, not a universal optimum.
2. Index each passage in FTS5 and, optionally, the existing local embedding model. Apply course and source-version filters to every retrieval path. Remove the silent first-1,000-page semantic omission: either search the whole bounded course corpus or explicitly report partial semantic coverage. Do not add an external vector database until measurement demonstrates a need.
3. Use model-token-aware limits and model-specific query/document formatting. EmbeddingGemma 1's official card specifies a 2K input context and distinct retrieval prompts; 12,000 characters is not a safe substitute. Pin the installed Ollama model digest and inspect whether its template applies prompts before adding them, to avoid double prefixing. Record model/prompt versions with each vector. [EmbeddingGemma model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card).
4. Retain lexical/dense fusion. Consider a small local cross-encoder only after passage coverage works; rerank a bounded candidate set and compare quality against CPU latency and RAM. Sentence Transformers documents this two-stage approach, but its examples do not establish a gain for this corpus. [Retrieve and rerank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html).
5. Bind each claim to an evidence item, immutable extraction revision, quote offsets, page, and optional box. Validate quote existence, course membership, image availability, and revision match mechanically. Separately audit whether the quote entails the claim. Visual observations need image provenance; they should not require a fabricated text quote. Missing evidence should produce an explicit unsupported/uncertain response.
6. Maintain a short, editable conversation summary with underlying message IDs and timestamps: current objective, notation preferences, decisions, unresolved questions, and corrections. Distinguish user-stated facts from model inferences and attempted answers. Retrieve relevant prior events rather than appending unlimited chat. Supersede stale facts and invalidate summaries dependent on changed sources. Keep course content evidence separate from personalization.

Temporal updates and abstention deserve explicit memory tests. LongMemEval provides useful categories—extraction, multi-session reasoning, temporal reasoning, updates, and abstention—but its published scores are not TLDR results. [LongMemEval, ICLR 2025](https://arxiv.org/abs/2410.10813).

**Enforceable visual policy.**

| Visual class | Required behavior |
|---|---|
| Original source | Default for diagrams, graphs, tables, equations and scientific images already supplied. Display the actual page/crop, preserving aspect ratio and labels; animate highlights, arrows, masking, and zoom as separate overlays |
| Verified generated graph | Allow only a supported equation/calculation with explicit domain, parameters, units, assumptions and server-computed samples. Record tool/version and verification evidence; label it as generated |
| Conceptual illustration | Only an explicitly labeled non-quantitative teaching aid. It cannot replace a source figure or claim exact topology, scale, protocol behavior or scientific accuracy without validation |

Use a closed `source_image` object carrying a source reference, not a path or remote URL. Resolve the reference server-side against the revision's validated citations and course; create a trusted asset map; hash crop bytes and transform/overlay settings in the render cache. Reject deleted/stale assets and invalid boxes. Coordinate conversion must account for PDF versus image origins and rotations. Keep original assets intact. Tiny text should trigger a higher-resolution source crop, not invented replacement labels.

For generated quantitative visuals, schema validation is only the first gate. Use reviewed calculation functions; test analytical values, dimensions, signs, boundaries, discontinuities and domains. Numerical simulations additionally need convergence or conservation checks where relevant. Match plotted samples to the approved calculation, show axes/units, and preserve discontinuities rather than connecting across them. General-purpose plotting software cannot certify a model's physics. If a formula cannot be verified, retain the original and explain the uncertainty. This policy is an engineering recommendation based on the user's fidelity requirement; no claim is made that the present renderer satisfies it.

**Learning retention.**

Add a short closed-book recall or application prompt at a meaningful lesson boundary, then reveal source-grounded feedback. Use original diagrams with selected labels masked, requests to explain a relationship, worked-step completion, and new numerical values for verified calculations. Record the response, hints, self-confidence, scoring rubric, correctness, source version, and feedback. A model's grading should remain reviewable; one failed answer should not become a permanent trait about the learner.

The direction has strong evidence; the exact TLDR schedule does not. Roediger and Karpicke's two prose-learning experiments found an advantage for testing over restudy on delayed assessments, while immediate results favored restudy. This supports measuring delayed recall rather than lesson completion. [Primary study](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf).

Cepeda and colleagues studied more than 1,350 people and retention intervals up to a year; useful spacing depended on the desired retention interval. Avoid presenting a fixed sequence as universally optimal. A transparent initial schedule such as 1, 3, 7 and 14 days can be a product heuristic adjusted after actual recall, not a research-proven optimum. [Primary spacing study](https://escholarship.org/content/qt0kp5q19x/qt0kp5q19x.pdf).

Feedback can also help correct answers given with low confidence; record both outcome and confidence, and show why the answer is correct. [Butler, Karpicke and Roediger, 2008](https://learninglab.psych.purdue.edu/downloads/2008/2008_Butler_Karpicke_Roediger_JEPLMC.pdf). These findings do not guarantee the same effect size for video lessons, advanced mathematics, or this learner.

**Bounded evaluation plan — proposed, not run.**

Start with a consented course fixture set spanning digital and scanned PDFs, mixed pages, long pages, multi-column text, diagrams, equations, and repeated terminology in different courses. Inventory language, length, OCR failures and modality counts before selecting models. Human-label the correct passage/box and acceptable answer for each question. Preserve near-duplicate documents in the same development or held-out group; keep question paraphrases and related pages together. Freeze the held-out suite before tuning.

| Test | Measurement and release decision |
|---|---|
| Long-page recall | Recall@8 for evidence after character 12,000, paraphrased queries, and pages outside the current semantic candidate cap; compare page baseline versus passage retrieval |
| Mixed-page extraction | Word/symbol error and correct reading order against transcribed samples; explicitly inspect superscripts, minus signs, Greek symbols, and diagram labels |
| Diagram/equation retrieval | Correct source crop/box recovered; caption linked to the right visual; image-only questions included |
| Citation fidelity | Quote/offset/version validity plus blinded human claim-support judgments; require zero invalid source bindings in deterministic fixtures |
| Course isolation | Adversarial duplicate terms and cross-course region/asset references; require zero leaks in the fixture suite |
| Stale memory | Correct/change/delete a source or preference; require superseded evidence to be flagged or excluded and unsupported questions to abstain |
| Visual correctness | Pixel provenance for crops; aspect-ratio/overlay tests; known-answer/domain tests for every supported graph type |
| Local operating cost | Warm and cold timings, repeated ingestion/query measurements, peak RAM, storage and model download size; report machine and versions |

A zero-failure fixture result is a regression gate, not proof of universal safety. Report counts and uncertainty grouped by independent document/course, not each overlapping passage. Compare lexical-only, passage hybrid, and optional reranking under the same prompt/evidence budget. Archive all runs, source hashes, seeds, settings and failures. Make no readiness or quality-uplift claim before this comparison.

For learning, first conduct a feasibility pilot. Compare the same lesson plus retrieval/feedback/review against time-matched restudy, with course/topic and prior knowledge balanced. For a small within-learner pilot, randomize matched independent topics to conditions and counterbalance order; avoid using the same topic in both arms because learning cannot be washed out. Use a predeclared seven-day unassisted recall/transfer score, with later follow-up if feasible, blind rubric scoring, and recorded outside study. Treat repeated questions as measurements nested within learner/topic, not independent people. A single-user pilot can guide this user's workflow, but cannot establish population efficacy. Determine a powered sample from pilot variability and a meaningful effect before a confirmatory claim.

**Priority and next evidence.**

P0: source-image rendering with overlays, provenance/version checks, and verified graph gates. P1: passage indexing plus token budgeting and explicit retrieval coverage. P2: attempt/review records and editable conversation memory. P3: compare optional Docling/reranking on representative hard files. All can avoid per-call service fees locally, but hardware, downloads, disk and engineering are real costs. No Gemini key is available in the task context; ingestion/search can work locally, while present generative tutoring still depends on the configured provider. Do not promise a complete local tutor from embeddings alone.

The highest-impact unknowns are the actual mix of handwriting/mathematics/diagrams, corpus size, installed model behavior, RAM/CPU limits, and grading reliability. Collect a small representative source fixture set next; it can reverse the Docling/reranker recommendation, but not the need to preserve originals and measure delayed learning.

Method note: the Experimental Design skill informed the proposed evaluation structure. Its requested attribution is Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), current record checked. This is workflow attribution, not evidence that TLDR improves learning.

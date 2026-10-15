# TLDR UI redesign checklist

Status: on October 15, 2026, the user selected **02 Cinema for Video mode** and **03 Margin for Notes/Text mode** from the new image mockups. The complete direction and shared behavior are recorded in [the project overview, section 16](PROJECT-OVERVIEW.md#16-frontend-design-directions). Implementation and usability acceptance remain pending. The current Focus Canvas interface is a functional prototype; the selected references replace it as the intended visual direction.

## First: establish the design direction

- [x] Record the selected two-mode direction and a brief for a serious study workspace, with real ECE224 and calculus material required for implementation checks.
- [ ] Audit Sources, Lessons, Chat and Study views for clutter, cramped reading areas, redundant headings and unclear actions.
- [x] Compare the new complete-screen image concepts and record the user's Cinema + Margin selection. Mockup content is illustrative; real-material acceptance checks remain below.
- [ ] Get feedback on the complete study flow before applying a new design throughout the app.

## High priority: layout and hierarchy

- [ ] Give the active document or lesson the largest, clearest area. Provide a focus mode for reading and watching.
- [ ] Make the tutor panel collapsible and resizable; preserve the user's chosen widths.
- [ ] Show extracted text on demand rather than permanently squeezing the original page into a third narrow column.
- [ ] Simplify the stacked course header, workspace navigation, source header and page toolbar. Remove repeated labels and competing headings.
- [ ] Consolidate Add source, Paste text and Import webpage into one clear intake flow.
- [ ] Move export and destructive actions into an appropriate secondary menu. Keep deletion separated from routine study actions.
- [ ] Replace numbered course entries and long sidebar descriptions with a compact course structure, search and clear selection states.

## High priority: visual system

- [ ] Define consistent typography, spacing, surfaces, borders, corner radii and icon sizes.
- [ ] Choose a restrained neutral palette and one interaction accent. Use semantic colors for meaningful states.
- [ ] Reduce outlined buttons, nested cards, badges and tiny uppercase labels.
- [ ] Establish readable sizes for body text, diagrams, equations and supporting information; avoid oversized repeated titles.
- [ ] Standardize primary, secondary, destructive, disabled, loading, hover and keyboard-focus states.
- [ ] Replace generic dashboard styling and filler copy with a consistent TLDR identity and direct language.

## Core requirement: LaTeX math throughout the study workflow

The functional math work was implemented independently of the deferred visual redesign. KaTeX formats browser text locally; a bounded MathJax-to-SVG path formats video equations. Automated and browser checks pass, and the tenth Lane call independently approved the bounded LaTeX feature after its equation-cache recovery finding was fixed. This does not constitute acceptance of the interface design.

- [x] Use one shared math-rendering component for inline and display equations across the app.
- [x] Format tutor message content/citation quotes, saved notes, scene narration/practice text, the app's caption panel and source-text previews. Native subtitle tracks remain plain text.
- [x] Render LaTeX on both the question and answer sides of flashcards, including after reveal, edit, save and reload.
- [x] Format quiz question/notes and answer-choice text. A dedicated worked-answer editor remains future study-tool work.
- [x] Preserve raw LaTeX while editing. Provide a preview without altering the saved expression.
- [x] Handle standard delimiters consistently; distinguish ordinary currency amounts from math delimiters.
- [x] Support standard KaTeX notation including fractions, powers, subscripts, roots, matrices, aligned equations, cases, integrals, sums, derivatives and units.
- [x] Contain equation overflow; the 390-pixel browser check has no horizontal page overflow. Wider-content and screen-reader review remain below.
- [x] Show invalid/unsupported formulas as original TeX with an explanatory tooltip.
- [x] Bundle math assets locally and render escaped source text without trusted HTML or remote-asset extensions. Bound formula size and expansion.
- [ ] Make math accessible to assistive technology; support selecting/copying the source expression.
- [ ] Preserve expressions through course export/import and use real equations from Paul's Online Math Notes as regression examples.
- [x] Typeset bounded `latex` equation objects in Manim videos through local MathJax SVG. The 63-second sample exercises a quadratic, derivative and matrix; arbitrary TeX programs are unsupported.
- [x] Keep typesetting distinct from mathematical verification; a rendered formula is not proof that its content is correct.

The real Paul's Online Math Notes extraction previews 48 formulas on its first part and five on its second part. Two unresolved `\eqref` references on the first part remain literal TeX; no equation numbers are fabricated. Source text and citation quotes are unchanged. Exported study titles, bodies and answer data match the saved records exactly. Import round trips and full assistive-technology review are still unchecked.

## Source viewer and annotation tools

- [ ] Make the PDF/image canvas feel like a document reader, with consistent zoom, fit-to-width, page navigation and rotation controls.
- [ ] Put manual normalized coordinates behind an advanced control; make drawing, moving and resizing regions the normal workflow.
- [ ] Make highlights, selection handles and citations clear without covering important labels or connections.
- [ ] Add a clean read/edit/preview treatment for OCR corrections and mathematical source text.
- [ ] Improve the source list with useful titles, file types, page counts, search and unobtrusive processing states.
- [ ] Show website provenance and extraction limitations where they help the student understand the source.

## Lesson player and tutor

- [ ] Design a wide player with clear chapter navigation, transcript, captions and playback speed controls.
- [ ] Keep practice questions and explanations readable without covering the instructional visual.
- [ ] Make Pause and ask, selected objects, source references and the attached timestamp feel like one coherent flow.
- [ ] Redesign chat typography, equation layout, citations, conversation selection and the composer together.
- [ ] Use compact attached-context chips with clear remove controls.
- [ ] Present paused, unavailable and failed answers in plain language. Put detailed provider setup instructions in settings/help rather than repeatedly in the conversation.
- [ ] Distinguish saved questions from generated answers and reviewed sample content.

## Study tools

- [ ] Give flashcards a focused review experience with clear question/answer states and legible LaTeX on both sides.
- [ ] Make decks, quizzes, checklists, bookmarks and confusing moments easy to find within a course.
- [ ] Improve creation/editing forms, empty states and feedback after saving.
- [ ] Show useful study progress without decorative or unsupported mastery claims.

## Acceptance checks before adopting the redesign

- [ ] Review complete source-to-question, lesson-to-question and flashcard-review flows with the user.
- [ ] Verify real dense ECE224 figures, a multi-page PDF, long source titles, mathematical chat and LaTeX flashcards.
- [ ] Check desktop layouts at 1280, 1440 and 1920 pixels, browser zoom and smaller windows. Keep desktop study as the primary experience.
- [ ] Confirm the page has no horizontal overflow; contain wide equations within their own scroll area.
- [ ] Verify keyboard navigation, visible focus, labels, contrast, reduced motion and screen-reader math output.
- [ ] Test loading, empty, error, paused, offline and long-content states.
- [ ] Add durable frontend regression coverage for composer recovery, conversation switching, math rendering and flashcard reveal/edit persistence.
- [ ] Confirm the redesign preserves course isolation, citation targets, annotation alignment and lesson context.
- [ ] Obtain an independent visual/accessibility review and user acceptance before calling the interface finished.

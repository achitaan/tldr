# Video and Notes workspace

The workspace implements the selected Cinema and Margin directions with real course content. The reference images remain visual references; their fictional textbook text and citations are not application data.

## Shared appearance

The light palette uses white paper, charcoal text, and one muted navy accent. The dark palette uses charcoal surfaces, light text, and restrained amber. Interface controls share Segoe UI; reading content and editorial headings use Georgia. Math retains its own local typesetting fonts.

**Light / Dark** in the header selects appearance independently of **Video / Notes**, which selects layout. Both layouts support both themes. The choice is saved in browser storage and persists across navigation, courses, and reloads. If storage is unavailable, the control still works for the current session.

Colors come from shared CSS tokens. Storyboards, study cards, course controls, menus, and Activity follow the chosen appearance. Original figures and rendered lesson media keep their instructional colors.

The left navigation is one mounted textbook outline with My Courses, source pages, Library shortcuts, and course creation. Its open/closed state applies to every workspace mode and is saved in browser storage. It defaults to open on desktop and closed below 900 pixels when there is no saved preference. On desktop it sits beside the content; closing it reclaims that space. Below 900 pixels it overlays the workspace with a backdrop and keyboard focus containment. Closing it never leaves a second Notes outline behind. Selection keeps it open on desktop and dismisses it on small windows.

The right study sidebar always has the same **Sources / Tutor / Flashcards** tabs and Notes-style appearance. Its selected tab and contents survive mode changes and hiding/reopening the sidebar. Sources follows the current Notes page or the recorded citations for the active video scene. A scene without resolvable citations explicitly falls back to course materials. Scene references are separate from question attachments: playback does not silently change a draft's attached timestamp or objects.

## Chats

Tutor has a Chats list, New chat, and a conversation view with Back to chats. Saved conversations show their titles and creation dates, newest first. New chats start as local drafts; their database record is created on the first send with a title derived from that question. No extra AI request generates the title.

Each conversation keeps its own unsent text and removable source/video context during the course session. Back to chats and Escape inside a conversation preserve that state; menus and overlays receive Escape first. Local unsent chats remain accessible from the list. Asynchronous fetches, sends, and response streams are associated with their originating conversation. Course changes clear session drafts and attachments; saved messages remain in the local database.

## Video

Open **Video** to watch the selected lesson in either light or dark appearance. Chapter thumbnails seek to the actual chapter boundaries; the full transcript exposes individual scenes. **Storyboard** opens the existing lesson editor, and **Watch** returns to playback.

An unrendered revision shows a static preview of its selected storyboard scene, using the existing source crop when available. Its caption distinguishes original source imagery from conceptual schematics. It does not display a fabricated playback duration. Selecting a draft chapter and attaching a question retain that selected scene and object context.

Practice questions, captions, named visual-object selection, and **Ask about this moment** retain their existing meaning. Attaching a moment pauses playback, opens the shared sidebar's Tutor tab, and focuses the composer with the revision, scene, selected objects, and timestamp attached. It does not submit a question automatically.

## Notes

Open **Notes** to read extracted source text in the chosen light or dark appearance. The source outline and page controls select actual imported material. Math uses the existing local LaTeX renderer.

The textbook sidebar groups actual material under **My Courses**, with expandable sources and pages, followed by **Library** shortcuts. The right margin provides **Sources / Tutor / Flashcards**. Source references track the selected page; preparing sources show their status instead of references from the previous page. Flashcards use saved course records and render math on both sides.

**Source tools** opens the original page/image viewer, region controls, and editable extraction. Editing extraction corrects the source record; it is not a separate personal note. **Read** returns to formatted text. Source actions retain file upload, pasted text, website import, and source removal.

An ordinary Video/Notes switch preserves independent lesson and source selections. Following an explicit citation navigates to its source and page. A marked-region citation opens the original source tools so the referenced visual can be inspected. The application does not infer a correspondence between an arbitrary paragraph and a video timestamp.

## Session continuity

Within the selected course, mode changes retain the mounted source workspace, lesson player, study tools, and one tutor instance. Leaving Video pauses playback without seeking; returning requires an explicit play action. Switching between Watch and Storyboard also retains the player session.

The interface retains source/page selection, zoom, unsaved extraction, tutor draft and attached context during mode switches. Hiding the tutor preserves the conversation and draft. Course changes create a separate workspace so another course's attached context cannot carry into a question.

These are in-session guarantees. Reloading the browser can discard unsaved edits, drafts, and playback position; save work before reloading. Saved records continue to use the existing local database.

## Verification

October 15, 2026 checks:

- Production build, lint, and 43 frontend tests passed, including nine chat-state tests, three scene-reference tests, and multiline-math preservation. The existing bundle-size advisory remains.
- The same loaded ECE224 video element retained approximately 2:00 through repeated Video/Notes and Watch/Storyboard switches. Leaving playback paused it; returning did not resume it. Source page 2 of 52, 120% zoom, unsaved extraction, and the tutor draft survived the switches.
- The actual endpoint checkpoint paused at 451.117124 seconds. Its answer began hidden; reveal/hide and selected-object question context survived mode changes. No AI question was submitted.
- The saved calculus webpage rendered 48 formulas. Desktop reading scroll returned to 620 pixels; a 390-pixel window restored a 3500-pixel document reading position after visiting Video.
- Both modes had no page overflow at widths of 1280, 1536, 1920, and 390 pixels. Keyboard Tab/Enter switching retained a visible 3-pixel focus outline. Hidden source controls were absent from the rendered focus path.
- A demo answer citation opened the correct source, original image tools, and marked region. Changing courses cleared the previous course's draft and attached video context.
- Closing the left navigation in Notes reclaimed 260 pixels and kept it closed across all three modes and reload. Its unfinished course form survived toggling. Closing the right study sidebar reclaimed 360 pixels; attaching a video moment reopened its Tutor tab and focused the composer.
- Practice text, storyboard inputs, Activity, and study cards follow the selected theme independently of the workspace mode. Inverse colors also cover the dark-mode skip link, notification, and destructive confirmation. These targeted contrast repairs do not establish a complete accessibility audit.
- Light/Dark persisted across navigation and reload, and synchronized between two open tabs. The shared right tab bar retained the same DOM element, 52-pixel height, theme surfaces, and Georgia font across modes. At 899 and 390 pixels the left navigation used an overlay with contained focus, backdrop dismissal, and focus restoration; at 900 it docked beside the content. No horizontal overflow was observed.
- A temporary read-only response fixture verified that a preparing source clears stale page references. Tutor drafts survived margin-tab changes. A saved flashcard rendered math before and after reveal; Manage opened the existing study tools.
- Draft revision 11 opens its original source image when selecting chapter 2; attaching the question retains that scene and selected object.
- Intercepted browser fixtures covered delayed create/send/fetch/stream responses, A-to-B-to-A switching, failed creation, newer drafts and attachments during sending, and leaving a course before creation completed. Each result remained with its originating chat. A natural course poll discovering a committed chat before its creation response left exactly one session after adoption.
- A real lesson question at 120 seconds captured revision 12, scene `takeaway`, and selected object `processor`. The same video element stayed paused at that position through mode changes. Source-region chips and viewer highlights restored per conversation and cleared together when removed.
- Activity, menus, and removal confirmations received Escape before chat navigation. A failed source-load fixture still allowed switching courses. The public demo's chat composer stayed disabled and made no API requests. Saved flashcards rendered math before and after reveal.

A fresh Lane reviewer approved the unified navigation, shared sidebar, and chat lifecycle after the duplicate-session and modal-Escape findings were corrected and checked again. Browser evidence came from the coordinator's Chromium session; chat writes and responses were intercepted, with no saved test conversations or live AI calls. The local API and idle worker were restored through the existing configuration loader after confirming no queued jobs. Screen-reader output and human usability acceptance remain untested. This UI change does not establish new AI-answer accuracy or lesson-content approval.

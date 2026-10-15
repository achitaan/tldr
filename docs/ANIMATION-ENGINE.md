# Animation engine and tutor extensions

TLDR already renders with **Manim Community 0.19.0**. Grant Sanderson's original [Manim repository](https://github.com/3b1b/manim) is maintained as ManimGL; [Manim Community](https://www.manim.community/) is the separate community fork. Both provide programmatic animation. Installing ManimGL does not automatically supply the scripts, explanation or choreography of a 3Blue1Brown video.

Keep Community as the working renderer while extending TLDR above it. Its existing fixed renderer, Windows dependencies, source-image path and media assembly have been exercised locally. A future ManimGL adapter should justify its added runtime and GPU requirements with a specific scene that needs it, rather than replacing a functioning engine for a visual resemblance.

## Current boundaries

The general lesson path is:

`course evidence → reviewed lesson JSON → validation/calculations → trusted Manim primitives → video + captions + interaction manifest`

The [teaching pipeline design](TEACHING-PIPELINE.md) expands the planning and review stages: evidence → learning goals/prerequisites → claim-backed scene contracts → accuracy checks → storyboard review → chapter production → playback and learning checks. It includes workflow diagrams and a worked ECE224 example. The additional planning records and gates are proposed architecture, not current automated enforcement.

An AI response can choose the supported lesson description. It cannot install extensions, execute Python, supply arbitrary expressions, choose filesystem paths or load remote assets. New renderer capabilities are reviewed project code with bounded input contracts.

| Tutor extension | Current state |
| --- | --- |
| Original diagram plus separate highlights | Implemented with revision-bound page/region snapshots, aspect-preserving images and normalized overlays. |
| Checked mathematical graphs | Implemented for server-sampled quadratics and Ohm's law, with explicit domains and units. Arbitrary input points remain conceptual illustrations. |
| Equation typesetting | Local MathJax-to-SVG conversion for a closed LaTeX notation subset, rendered by Manim. This formats notation; it does not verify arbitrary formulas or derivations. |
| Timing signals and bus teaching models | Implemented as bounded logical illustrations. These do not simulate an arbitrary processor protocol. |
| Object and scene identifiers | Included in the playback manifest and contextual questions. Selection currently uses the player's object list or image region, not automatic hit-testing of every animated pixel. |
| Pause and ask, separate follow-up | Implemented in the local application. Cloud answers and new storyboards still require the configured free project. |
| Narration-directed camera and object choreography | Demonstrated by the opening and full authored ECE224 sample, including original-image focus, checked interval transformations and a persistent ideal-read model with address/data token travel, storage and prediction replay. Stable object IDs and conceptual provenance reach contextual chat. This remains authored choreography, not a general lesson-generation capability. |
| Arbitrary 3D physics, circuit solvers and symbolic derivations | Not implemented. Add a verified domain tool and state its assumptions before animating its output. |

## Adding a capability

Each new visual should specify its supported subject, finite input bounds, object identifiers, evidence references and whether it is an original-source display, checked calculation or conceptual illustration. Its calculation must run independently of its drawing. Add known-answer checks for calculated behavior and inspect the rendered visual, narration and captions together. Keep unchanged scenes reusable through the existing cache.

The next useful addition is a general narration-cue choreography layer that exposes the authored sample's source-preserving focus and checked transformations through bounded lesson descriptions. It should reuse the existing course evidence and interaction manifest. A new engine is unnecessary. The authored programs record sentence-cue visual events for independent timing review; this does not establish automatically generated 10–20-minute lessons or equivalent teaching quality across subjects.

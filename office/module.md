---
description: "The office module — daily knowledge work: narrative and visual strategy, design extraction and style checking, and document/deck/email production."
---

<module>

# office

The `office/` module hosts the components that turn a raw brief into finished knowledge-work
deliverables — a locked narrative, an on-brand visual system, and the documents, decks, and
emails built from them. Voice, palette, templates, and terminology resolve at runtime from a
workspace brand pack (`.rbtv/config/office/`); the module itself ships no vault paths, owner
names, client names, or instance palettes.

## Components

| Component | What it is |
|-----------|-----------|
| `storytelling/` | Narrative and audience strategy: locks the story before anything visual is built (`narrative-lock`), plans how the locked narrative becomes visuals (`visual-strategist`), and researches the audience/content briefs both consume. |
| `design/` | Visual-system extraction, design-system creation, and style checking: pulls design tokens, subtle references, and reconstructable prompts from source material, captures exemplar screenshots, creates and governs project design systems (`design-system`), and runs deterministic + model-reviewed style checks (`visual-check`) against the brand pack. |
| `document/` | Deliverable production: the HTML standards library, HTML review, deck production (HTML deck + PDF), document conversion, deterministic document presentation (`posh`), email voice, and the `meeting-prep` and `presentation` workflows that chain the other two components into finished output. |

</module>

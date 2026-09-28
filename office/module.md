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

`office/document#office` is the module's parent skill. It routes document, deck, email, storytelling, and design requests; meeting summarization remains in its single-agent component.

## Components

| Component | What it is |
|-----------|-----------|
| `storytelling/` | Narrative and audience strategy: locks the story before anything visual is built (`narrative-lock`), plans how the locked narrative becomes visuals (`visual-strategist`), and researches the audience/content briefs both consume. |
| `design/` | Visual-system extraction, image generation, design-system creation, and style checking: pulls design tokens, subtle references, and reconstructable prompts from source material, captures exemplar screenshots, generates or edits images from a text prompt (`generate-image`), creates and governs project design systems (`design-system`), and runs deterministic + model-reviewed style checks (`visual-check`) against the brand pack. |
| `document/` | Deliverable production: the HTML standards library, HTML review, deck production (HTML deck + PDF), document conversion, deterministic document presentation (`posh`), email voice, and the `meeting-prep` and `presentation` workflows that chain the other two components into finished output. |
| `meeting-summarizer/` | Detects new meeting transcripts (Google Meet, Tactiq's Drive auto-save, Gemini notes), drives the summarizer skill to write one corrected summary per meeting, files and publishes it, and tracks doubts an owner must answer (`doubt-answer`) — through whichever reply mechanism the installing agent has; it carries no chat transport of its own. |

</module>

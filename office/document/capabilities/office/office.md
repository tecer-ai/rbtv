---
description: "Use for office work: make or review a document, convert to Word, create a deck or PDF, polish an email, prepare a meeting, extract design references, capture screenshots, or check HTML style. Routes to the office storytelling, design, and document skills and CLIs."
---

# office

Route by the requested result. A `module/component#part` ID names the `part-id` row in that component's `exposure.csv`; open its `entry-point` before running its CLI or workflow. Resolve paths from the rbtv repository that contains this file.

| Request | Child |
|---|---|
| Shape a brief, audience, or message before visual work | `office/storytelling#narrative-lock` |
| Plan how a locked narrative becomes slides, pages, or screens | `office/storytelling#visual-strategist` |
| Avoid formulaic copy or extract a writing voice | `office/storytelling#ai-anti-patterns` or `office/storytelling#tone-extraction` |
| Make a presentation or meeting preparation sheet | `office/document#presentation` or `office/document#meeting-prep` |
| Produce an HTML deck and PDF | `office/document#deck-production` |
| Convert a document, including Markdown to Word | `office/document#converter` — `converter-cli` |
| Render a structured plan as polished HTML | `office/document#posh` — `posh-cli` |
| Produce or review HTML | `office/document#html-standards`; use `office/document#html-review` for a review and `office/design#visual-check` for style checking |
| Polish an email in the brand voice | `office/document#email-voice` |
| Extract colors, type, spacing, or subtle references | `office/design#design-tokens` or `office/design#subtle-refs` — `subtle-refs-cli` |
| Capture exemplar screenshots | `office/design#screenshot-capture` — `screenshot-capture-cli` |
| Check HTML against the brand pack | `office/design#visual-check` — `visual-check-cli` |
| Reconstruct an image prompt, generate an image, or govern a design system | `office/design#vision-to-json`, `office/design#generate-image`, or `office/design#design-system` |

Meeting transcript summarization belongs to the single-agent `office/meeting-summarizer` capability.

---
description: "Read at the moment of producing or checking an HTML deck — the Presentation page-type profile to apply."
tags: [document]
---

# html-page-presentation — Presentation page-type

Production model: **agent-authored HTML**. The agent writes the HTML file itself. Deck production and the presentation workflow consume this profile; they do not redesign it.

Apply, do not restate: `html-quality.md`, `html-production.md`, `html-design-system.md` (as base). When a slide has a chart, also apply `html-charts.md`. A runtime brand pack may overlay palette and templates; this profile still binds.

## Allowed bends vs Review

State each. These are the only bends.

1. **Drop the left index** — a deck is not a long article.
2. **A per-subject motif and cover treatment** — one signature for this deck, still from the design-system tokens.
3. **A slide-sized canvas of 1280×720** with matching print settings: `@page { size: 1280px 720px; margin: 0 }`.

## Forbidden — state each

None of these is a bend. Each is a fail.

- A **second token vocabulary** — tokens live in `html-design-system.md`; this profile names none of its own.
- **jargon** — `html-quality.md` owns the bar; a deck does not get a pass.
- **JavaScript-built slide bodies** — slide content is static markup, never assembled at load.
- **base64-embedded decks** — never. Assets stay external per `html-production.md`.

## Numeric floors — run-time source

These named values are the run-time source of the numeric floors. A checker must read them here rather than carrying its own copy; never hardcode them.

| name | value | unit | what it constrains |
|---|---|---|---|
| canvas-width | 1280 | px | slide canvas width |
| canvas-height | 720 | px | slide canvas height |
| min-body-text | 18 | px | minimum body-text size |
| min-caption-text | 14 | px | minimum secondary/caption text size |
| max-grid-columns | 3 | columns | maximum number of columns in a slide grid |

Canvas dimensions are given. The other three are ruled here for a 1280×720 deck read at presentation distance:

- **min-body-text 18** — 16px is laptop-reading size and fails across a room; 18px is the common projected-slide floor.
- **min-caption-text 14** — one step below body, still legible at distance; 12px is caption-on-a-phone.
- **max-grid-columns 3** — four equal columns on 1280px leave ~280px after gutters, too narrow for 18px body with padding.

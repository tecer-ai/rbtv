---
description: Read at the moment an agent is about to write or restyle agent-authored HTML — the house look to apply.
tags: [document]
---

# html-design-system — the house look for agent-authored HTML

The default look for pages whose production model is **agent-authored HTML** (Review, Presentation). Apply this file; do not invent a parallel palette or type stack. Learning does not bind: its agent writes markdown page-source and never writes HTML, CSS, or JS.

This file is a DEFAULT, not a cage. Scale down (short pages drop the sidebar and most cards) and bend only to content the source genuinely demands.

## Authority

The library leads. This file is the standard. When it and the sb-tutor `styles.css` in the sb-os repo disagree, this file wins and that stylesheet is updated to match it, never the reverse.

A change to this file is incomplete until that stylesheet is updated to match. Nothing enforces this — no build check, no CI gate. It is a standing cross-repo obligation on whoever edits the library.

A runtime brand pack may overlay a user's own palette. This file is what runs when no pack is present.

## Tokens

Copied verbatim from the live Lumen `:root`. One gloss per token. Use each pair exactly as declared; do not rename, rescale, or approximate.

- `--bg:#F5F6FB` — tinted page ground (never flat white)
- `--panel:#FFFFFF` — white panel / card surface
- `--ink:#181A30` — near-ink headings (never pure black)
- `--ink-soft:#5B6080` — soft slate-navy body text
- `--violet:#5B4FE0` — primary accent
- `--violet-2:#8A7DF5` — secondary accent
- `--tint:#ECEAFC` — violet-tinted panel / card fill
- `--amber:#E29A12` — caution / highlight; Review flag: caution
- `--teal:#13A39B` — positive / resolved; Review flag: resolved
- `--line:#E5E7F2` — hairline / divider
- `--code:#1B1C30` — code-block ground (the one dark surface)

### Blocker / stop — build-time addition

- `--rose:#C2364A` — blocker / stop. **No source in the tutor stylesheet**; added here so Review's caution / blocker / resolved flags have a third colour.

Contrast (WCAG 2 relative luminance), held at WCAG AA:

| Ground | Ratio | Threshold held |
|---|---|---|
| `--panel` `#FFFFFF` | 5.36:1 | 4.5:1 text |
| `--tint` `#ECEAFC` | 4.53:1 | 4.5:1 text |
| `--code` `#1B1C30` | 3.12:1 | 3:1 border or large text |

Use `--rose` as text on light surfaces (`--panel`, `--tint`) and as the 5px card border on any of the three grounds. Do not use it as small text on `--code` (that use needs 4.5:1; 3.12:1 does not meet it).

## Page treatment

Tinted page background (`--bg`) with two soft radial accent washes behind the content — violet upper-right, warm upper-left — never flat white. White panels (`--panel`). Soft slate-navy body (`--ink-soft`) and near-ink headings (`--ink`), never pure black. Colour as accents AND as tinted panel/card fills (`--tint` and per-category washes), not only as borders. Gradients, radial washes, soft shadows, and pill shapes are the house look.

## Type

Three typefaces, loaded from Google Fonts, with `system-ui` fallbacks. No other typefaces.

- Headings: Space Grotesk, 600–700
- Body: Inter, 400–600
- Labels, tags, eyebrows, meta, code: Space Mono

```
https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap
```

Fallbacks: `"Space Grotesk", system-ui, sans-serif` / `"Inter", system-ui, sans-serif` / `"Space Mono", ui-monospace, monospace`. Do not replace this stack with a system-font stack.

## Adaptive left index

- Four or more navigable sections → fixed ~260px left sidebar with grouped jump-links; content in a right-offset `main`.
- Below ~900px the sidebar collapses to a horizontal top bar.
- Fewer than four sections → SKIP the sidebar.

The index is for jumping. It is not a second reading column.

## Category-coloured cards

5px coloured LEFT border plus a faintly tinted background from the category accent. Flag colours map directly:

| Flag | Token |
|---|---|
| caution | `--amber` |
| blocker | `--rose` |
| resolved | `--teal` |

## Linear reading path

The single most important layout rule. ONE top-to-bottom column. The index is for jumping; the content is linear. A two-column grid only for a genuine side-by-side pair. Never scatter flow with sticky filter bars, tab strips, or competing card types. Each section states its point first, then supports it.

## Density and restraint

Hierarchy and whitespace over cramming. At most ~3 accent colours (`--violet`, `--violet-2`, and one more) plus the flag colours (`--amber`, `--rose`, `--teal`). Cards for genuine groups; supporting text stays plain. Long sections use `<details>`, not more boxes. When two adjacent elements both shout (heavy border + tint + pill + shadow), strip one.

## Explicitly avoid

- Dark page backgrounds (code blocks may use `--code`; the page may not)
- Sticky top nav as primary navigation on these pages (the left index, or a deck's own navigation, is the nav)
- Multi-column grids as the default
- System-font stacks in place of Space Grotesk + Inter + Space Mono

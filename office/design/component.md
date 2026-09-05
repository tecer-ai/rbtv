---
description: "The design component — extracts a visual system (tokens, subtle references, reconstructable prompts, exemplar screenshots) from source material, creates and governs project design systems, and checks produced HTML against it, deterministically and by model review."
---

# design

Where `storytelling/` locks WHAT to say, `design/` locks what it LOOKS like. Four extraction
capabilities pull a visual system out of reference material — design tokens, subtle non-obvious
references, a reconstructable generation prompt from an image, and exemplar screenshots — one
creation capability turns that material (or an owner interview alone) into a governed project
design system, and two checking capabilities hold produced HTML to that system: fast deterministic
script checks, and a model review that actually looks at the rendered page.

## Entry points

| Part | What it is |
|---|---|
| `capabilities/design-tokens/design-tokens.md` | Extracts colour/type/spacing tokens from source material. |
| `capabilities/subtle-refs/subtle-refs.md` | Extracts subtle, non-obvious visual references. First-party CLI at `capabilities/subtle-refs/tool/extract.py`. |
| `capabilities/vision-to-json/vision-to-json.md` | Turns a reference image into a reconstructable generation prompt (JSON). |
| `capabilities/screenshot-capture/screenshot-capture.md` | Captures exemplar screenshots for the brand pack's `exemplars/` set. First-party CLI at `capabilities/screenshot-capture/tool/capture.py`. |
| `capabilities/design-system/design-system.md` | Creates and governs a project design system (principles, tokens, component recipes, patterns, views, governance, changelog) via a relentless owner interview, panel review, and an owner decision batch. Delegates extraction to `design-tokens` and verification to `visual-check`. Scaffold templates at `capabilities/design-system/templates.md`. |
| `capabilities/visual-check/visual-check.md` | Deterministic + model-reviewed style checking against the brand pack. Loadable directly by any HTML-producing agent, not only through `html-review` or presentation verification. First-party CLI at `capabilities/visual-check/tool/visual-check.py`. |
| `references/visual-ban-list.md` | Banned visual patterns checklist. |
| `references/visual-flaw-checklist.md` | Visual-flaw review checklist. |

Data-integrity and pitch-anti-pattern checks are narrative-quality judgements and stay in
`storytelling/` — never here, not even temporarily. This component consumes `web/browse`'s
Playwright surface as infrastructure for screenshot capture; it does not drive a browser as its own
job.

---
id: deck-production
description: Produce an HTML deck from a locked narrative, a visual-communication plan, and a picked art-direction brief, render it for inspection, and export a PDF. Purpose-independent — any host holding those three inputs can invoke it.
inputs: gated `narrative-lock.md` (required); `visual-communication-plan.md` (required); owner-picked art-direction brief (the visual contract); brand-pack palette and presentation template resolved from `.rbtv/config/office/`; optional reference-set findings and owner-gated real-provenance imagery
outcome: the caller holds an inspectable HTML deck and a matching PDF (one page per slide, nothing clipped), or this capability has refused because a required input was missing
outputs: caller-named `{name}.html`; sibling `{name}-assets/` only when real binaries exist; `{name}.pdf` via `converter`
---

# deck-production — agent-authored HTML deck

Produce an HTML deck against the library Presentation page-type, render it for inspection, export
PDF. Delivery in V1 is HTML + PDF. Any host that already holds the three inputs can invoke it.

## Hard precondition — refuse without both

This capability MUST REFUSE to run unless BOTH a gated `narrative-lock.md` AND a
`visual-communication-plan.md` are present. This is a hard precondition, not a warning. A missing
art-direction brief is also a refusal — the brief is the visual contract. Do not author a slide.

## Load — by load, never by copy

Before any markup, load `references/html-standards.md`. That router reaches quality + production +
design-system + the Presentation profile (`references/html-page-presentation.md`). Load
`references/html-charts.md` IFF a slide carries a chart.

MUST NEVER restate a design-system token or a Presentation-profile number. Tokens live in
`references/html-design-system.md`. Other numeric floors live in
`references/html-page-presentation.md`. Where a value is needed, read the file that owns it.

## Brand pack — runtime overlay

Palette and templates overlay at runtime from `.rbtv/config/office/`. Resolution is per-file, not
per-pack:

1. If this run carries a project slug, read `.rbtv/config/office/projects/<project-slug>/<file>`
   first; if present, it shadows.
2. If absent, fall back to `.rbtv/config/office/<file>`.
3. No project slug → workspace pack only. NEVER consult `projects/`.

Files this capability reads: `palette.json`, `templates/presentation.md`. This is a fixed-path read.
MUST NEVER search. MUST NEVER discover a brand folder.

A missing pack MUST trigger the guided setup whose one home is
`capabilities/email-voice/email-voice.md`. MUST NEVER halt. MUST NEVER run a discovery scan. MUST
NEVER invent a palette or a second token vocabulary. The pack overlays the design-system; it does
not replace it. `templates/presentation.md` informs structure; V1 still authors bespoke HTML.

## Format

Canvas MUST be 1280×720 (16:9). The HTML MUST carry `@page { size: 1280px 720px; margin: 0 }`. Both
halves are required and MUST agree — a canvas without the matching print rule clips the PDF.

Print CSS MUST also include `@media print`, `page-break-inside: avoid`, and `print-color-adjust`.

## Generate

1. Author static HTML. Output contract:
   - full-screen browser
   - one top-level `<section>` per slide
   - static markup — slide bodies MUST NEVER be JavaScript-built
   - charts hand-authored SVG or CSS, no charting library
   - binaries in a sibling `{name}-assets/` as ruled by `references/html-production.md`
2. Generate slice-by-slice: one slide per fresh-context worker; splice each section into the one
   deck file.
3. V1 builds bespoke. MUST NEVER use persona/XML menus, a rendered template-trio stage, a
   role-token or `assemble.py` slide-library engine, or a slide-library probe.
4. Imagery is owner-gated and real-provenance only. A deck with none is valid. MUST NEVER fabricate
   an image. MUST NEVER base64-embed a deck.
5. Jargon is not allowed — `references/html-quality.md` owns the bar.

## Surgical patch

To repair a flagged slide, rewrite ONLY that slide's `<section>`. Every other slide MUST stay
byte-identical.

## Render for review

Render MUST run over a local HTTP server. `file://` is BLOCKED — MUST NEVER open the deck via
`file://`.

When the render server is unavailable, start the local-server pattern: from the directory that holds
`{name}.html`, run `python3 -m http.server` and open the `http://` URL in a headed (visible)
browser. MUST NEVER fall back to `file://`. MUST NEVER inspect headless as the review render.

## PDF

PDF MUST be produced by invoking `converter` (`capabilities/converter/converter.md`) on the authored
HTML file — converter's HTML→PDF input; Marked is skipped because the deck is already HTML. MUST
NEVER stand up a second engine.

PDF contract: one page per slide, nothing clipped.

## Delivery layer

| Sink | V1 |
|---|---|
| HTML (browser) | yes — native output |
| PDF | yes — via converter |
| Google Slides | no — named future extension point: same locked deck, a different sink, built later. Not a V1 build item. |
| PPTX | NEVER |

MUST NEVER emit PPTX.

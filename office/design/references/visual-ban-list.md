---
description: "Load at the moment of writing or reviewing any visual artifact — an art-direction brief, generated HTML, a slide, a page — BEFORE the first layout or palette choice, and again when judging whether a rendered result is training-mean."
tags: [design]
---

# visual-ban-list

The catalogue of visual attractors every generated artifact MUST avoid. An attractor on this list reads as AI slop — generic, template-default, or off-brand — and MUST NEVER appear.

This file is visual craft only. Narrative quality, data integrity, source-research, and pitch anti-patterns live elsewhere. Page-box, print-pipeline numerics, and export-metadata live in the HTML standards library.

Each entry: the **banned attractor**, **why it reads as slop**, and **what to reach for instead**.

Art-direction briefs MUST be ban-list-clean before a lane is picked. Generation MUST NOT introduce a listed attractor.

---

## Model-default attractors (the training-mean look)

Unguided model defaults. Ban them by name at art-direction time.

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| A-1 | Purple-blue gradients | The single most over-produced default background; signals "generated with no brand input" at a glance | Real brand-pack tokens; a flat or token-grounded palette chosen in the art-direction brief |
| A-2 | Rounded-card-grid-of-three | The default "feature section" template; three identical rounded cards in a row reads as a stock layout, not a designed page | A grid principle chosen per direction; card counts and treatment driven by content density, NEVER a reflexive 3-up |
| A-3 | Default-font look | System/stock typeface with no pairing decision signals zero typographic intent | A deliberate type pairing from brand-pack tokens, stated in the brief; 1–2 fonts max |
| A-4 | Emoji as iconography | Unmistakable generated-content tell; inconsistent rendering, no brand alignment | A single icon library at brand weight/color from the brand pack; NEVER mix libraries on one semantic set |

---

## Visual consistency

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| V-1 | Title position drifting page-to-page (mixing centered and top-aligned content pages) | Floating titles read as un-templated; the eye re-hunts the title on every page | Top-aligned content pages; only cover and closing centered; titles anchored at one vertical position |
| V-2 | Differential team-card styling (accent border, extra shadow, highlight class on one card) | Uneven card treatment signals favoritism or sloppiness; breaks the parity a credible team block needs | Identical visual treatment on all cards; emphasis goes in callout text within the card, NEVER in card styling |
| V-3 | A dense cover (product definitions, value props, multi-sentence descriptions) | An overloaded cover reads as a content page mislabeled; defeats the title-card function | Cover = brand mark + one short category-positioning line; everything else moves to subsequent pages |
| V-4 | Cover and closing that differ in background, typography, or layout | A mismatched bookend breaks the visual frame and reads as inconsistent assembly | Identical background, typography, and layout on cover and closing; closing adds contact info only |

---

## Layout and density

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| L-1 | Globally centered content pages (title not top-anchored; content not sitting in the remaining space below) | Centered-as-a-whole content pages fight title anchoring and read as a cover clone | Content pages top-align the title; content occupies the remaining space below it. Only cover and closing center as a whole |
| L-2 | Grid overflow (3-col beyond 6 cards / 2 rows; 4-col with cells longer than 3 lines; switching grids mid-artifact without a visual reason) | Overfilled or inconsistent grids read as content dumped into a template | Respect the page-type profile's grid ceilings; richer content uses fewer columns; NEVER switch grids without a reason |
| L-3 | More than 3 content zones per page; zones with no label that merge visually | A page packed with undifferentiated zones reads as a wall, not a designed argument | Max 3 distinct content zones; split 4+ onto separate pages; label every zone on 3+-section pages |
| L-5 | More than 3 textured backgrounds per artifact; texture set without a `background-color` fallback or competing with text | Excess texture reads as decoration-for-decoration's-sake and harms readability | Max 3 textured backgrounds (cover, closing, one accent); ALWAYS set `background-color` fallback first; mute competing texture with a semi-transparent overlay |

---

## Typography and icons

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| T-1 | Sub-floor type; two-line stat labels | Tiny or wrapping labels read as cramped and unconsidered | Sizes MUST meet the page-type profile floors; shorten copy so stat labels fit one line |
| T-2 | Arbitrary per-page type sizes instead of one consistent scale | A different size recipe on every page signals no typographic system | One fluid scale held across the artifact; NEVER substitute ad-hoc sizes |
| T-3 | Sub-floor or muted feature-card icons | Small/faded icons add visual noise without function — a generated-artifact tell | Feature-card icons at the profile floor in the primary token; remove icons that cannot meet this rather than shrinking them |
| T-4 | Mixed icon libraries on one semantic set | Mixing libraries reads as unassembled clip-art, not a system | One icon library at brand weight/color; NEVER mix libraries on the same semantic set |

---

## Colour discipline

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| C-1 | Placeholder / training-mean color values left in `:root` | Stock palette values are the clearest "no brand input" signal | Replace every `:root` value with real brand-pack tokens |
| C-2 | Mixed stat colors within one semantic group; danger token used for non-negative values; mixed currency/time basis in one grid | Inconsistent stat coloring reads as random, not systematic; misused danger-red miscommunicates | One accent color per semantic stat group; reserve the danger token for genuinely negative values only; uniform currency and time basis across a grid |
| C-4 | Colored borders used diagonally or at random; red borders on decision / go-no-go boxes | Random colored borders destroy the system signal; red reads as danger, not rigor | Colored borders carry consistent, intentional logic; decision/kill-criteria boxes use NEUTRAL borders |

---

## Component patterns

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| CP-1 | Equal-weight competitive comparison grids (all cards rendered identically) | An even comparison signals lack of confidence in the product | Product card dominates (elevation, stronger shadow, brand border); competitors de-emphasized |
| CP-2 | Scenario tables colored ad hoc (floor / base / ceiling not mapped to the semantic danger / secondary / primary tokens) | A scenario table that invents its own colors reads as decoration, not a readable system | Floor / base / ceiling MUST use the semantic tokens consistently; deviation requires an explicit reason |
| CP-3 | Risk or decision-gate statements styled as footnotes | Burying failure modes and kill criteria reads as hiding them; they are first-class content | Danger-bordered callout for failure modes; warning-bordered callout for decision gates |
| CP-4 | 1px gray flow-diagram connectors | Thin gray connectors disappear in print and read as unfinished | Unicode arrows in brand color, minimum 2px weight |
| CP-5 | Equal-weight before/after columns | Rendering both sides identically loses the transformation the page exists to show | "After" column heavier (primary-dark token, weight 600); "before" de-emphasized (muted token, weight 400) |

---

## Print-unsafe CSS patterns

Numeric `@page` / slide-box / export-metadata rules are NOT here — they live in the HTML standards library. This list is the CSS *patterns* that silently break in the shipped PDF.

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| P-1 | Print-unsafe CSS on render-to-PDF elements (`aspect-ratio`, transforms on positioned elements, pseudo-elements for structural content, complex `clip-path`) | These silently break in the PDF the owner actually ships — fine in-browser, broken in the deliverable | Explicit `width`+`height`; `writing-mode: vertical-rl` for rotated text; real DOM elements for dividers; simple shapes or SVG for clipping |

---

## Marks and citations (visual placement)

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| E-6 | Recoloring a brand or third-party mark — knockout, inversion, tinting, or any color shift to make it fit | The mark MUST appear as the brand owns it; altering it reads as off-brand, and on a known brand it is an instant credibility hit | Render every logo in its ORIGINAL brand colors, even at aesthetic cost. On a dark background where it would disappear, use a supplied reversed/light logo if one exists, ELSE sit the original-color logo on a light backing panel — NEVER recolor, invert, or knock out the mark |
| F-5 | Source citations placed inline / mid-text | Inline citations interrupt the one-idea read and clutter the focal content | Anchor source citations as footnotes at the BOTTOM of the page, visually subordinate (small, muted), with a small marker beside the claim only if needed. Distinct from CP-3: risk/decision statements are first-class callouts, NEVER footnotes — this rule governs SOURCE CITATIONS only |

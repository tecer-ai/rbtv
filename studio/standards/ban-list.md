---
type: standard
module: studio
created: 2026-06-09
status: active
---

# Studio Ban-List — Default Attractors

The catalogue of attractors every studio output must avoid: the model's training-mean defaults plus the living corrections mined from the retired `deck-design` data files. An attractor on this list reads as AI slop — generic, template-default, or credibility-destroying — and must never appear in a generated artifact.

This is a **module-internal standard** — not a `.claude/` rule. The reference set and taste file are workspace-owned; this list is module-enforced.

## Binding

This ban-list binds two surfaces of the deck loop. Read `{rbtv_path}/studio/deck-loop-spec.md`:

- **Art-direction beat (Behavior Specification row 3)** — every direction mini-brief must be ban-list-clean before the owner picks; a banned attractor present in any brief fails the beat.
- **All generation (Behavior Specification rows 4–6)** — the template trio, every slice, and the fresh-eyes pass enforce this list; a banned attractor surfaced at fresh-eyes is a punch-list item.

Each entry below carries: the **banned attractor**, **why it reads as slop**, and **what to reach for instead**. Mined entries cite the mining-map row (`./mining-map.md`) they derive from.

---

## A. Model Default Attractors (H4 — the training-mean look)

These four are the model's unguided defaults — what the model produces when no art direction constrains it. They must be banned by name at the art-direction beat.

| # | Banned attractor | Why it reads as slop | Reach for instead |
|---|------------------|----------------------|-------------------|
| A-1 | **Purple-blue gradients** | The single most over-produced LLM-default background; signals "generated with no brand input" at a glance | The project's real `:root` brand tokens (color/type/spacing from the reference set); a flat or token-grounded palette chosen in the art-direction mini-brief |
| A-2 | **Rounded-card-grid-of-three** | The default "feature section" template; three identical rounded cards in a row reads as a stock layout, not a designed slide | A grid principle chosen per direction; card counts and treatment driven by content density, not a reflexive 3-up |
| A-3 | **Default-font look** | System/stock typeface with no pairing decision signals zero typographic intent | A deliberate type pairing from the reference-set tokens, stated in the direction mini-brief; 1–2 fonts max |
| A-4 | **Emoji icons** | Emoji as iconography is an unmistakable generated-content tell; inconsistent rendering, no brand alignment | A single icon library at brand weight/color (Font Awesome 6.5.1 primary); never mix libraries on one semantic set |

---

## B. Mined Corrections — Visual Consistency

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| B-1 | Title position drifting slide-to-slide (mixing centered and top-aligned content slides) | Floating titles read as un-templated, amateur; the eye re-hunts the title on every slide | `justify-content: flex-start` on all content slides; only cover and closing centered; titles anchored at one vertical position | V-1 |
| B-2 | Differential team/founder card styling (accent border, extra shadow, highlight class on one card) | Uneven card treatment signals favoritism or sloppiness; breaks the parity a credible team slide needs | Identical visual treatment on all cards; narrative emphasis goes in callout TEXT within the card, never in card styling | V-2 |
| B-3 | A dense cover slide (product definitions, value props, multi-sentence descriptions) | An overloaded cover reads as a content slide mislabeled; defeats the title-card function | Cover = brand mark + one short category-positioning line; everything else moves to subsequent slides | V-3 |
| B-4 | Cover and closing slides that differ in background, typography, or layout | A mismatched bookend breaks the deck's visual frame and reads as inconsistent assembly | Identical background, typography, and layout on cover and closing; closing adds contact info only | V-4 |
| B-5 | Uneven bio depth across founder cards (one card with 3 company-named highlights, another with one vague line) | A shallow card next to a rich one reads as padded or under-researched | Equal number and depth of career highlights on every card; if source is thin, ask the owner — never generate a shallow card | SR-2 |

---

## C. Mined Corrections — Data Integrity (credibility-destroying attractors)

These read as slop because they destroy trust the moment a reader checks — the worst failure mode for an investor or client deck.

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| C-1 | Fabricated titles or org structure (inferring CEO/COO/CTO not present in source) | An invented title is an instant credibility kill if the reader knows the team | Use ONLY titles present in source documents; if ambiguous or missing, ask the owner | D-1 |
| C-2 | Nicknames or informal names in an investor deck | Informal names read as unfinished or careless in a formal fundraising artifact | Full legal/professional names; resolve from CVs or ask the owner | D-2 |
| C-3 | A named fund or investor-partner quote in an outbound investor deck | Existing investors seeing another's endorsement creates social dynamics the founder must control, not the deck | Omit named investor quotes from outbound investor decks entirely | D-3 |
| C-4 | Relabeling a third-party stat's market category to fit the company's positioning | Misattributed data destroys credibility the instant an investor checks the source | Keep the honest label and flag the tension to the owner with options (keep / remove / find alternative data) | D-4 |
| C-5 | Unexplained market figures; bare SAM/TAM abbreviations | Numbers a reader cannot parse at a glance read as filler, not evidence | SAM/TAM spelled out on first use; every market number self-explanatory with one-line context | D-5 |

---

## D. Mined Corrections — Layout & Density

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| D-1 | Grid overflow (`.grid-3` beyond 6 cards / 2 rows; `.grid-4` with cells >3 lines; switching grids mid-deck without a visual reason) | Overfilled or inconsistent grids read as content dumped into a template | Respect the grid ceilings; use `.grid-3`/`.grid-2` for richer content; never switch grids mid-deck without a reason | L-2 |
| D-2 | More than 3 content zones per slide; zones with no `.zone-label` that merge visually | A slide packed with undifferentiated zones reads as a wall, not a designed argument | Max 3 distinct content zones; split 4+ into separate slides; add a `.zone-label` above every zone on 3+-section slides | L-3 |
| D-3 | More than 3 textured backgrounds per deck; texture set without a `background-color` fallback or competing with text | Excess texture reads as decoration-for-decoration's-sake and harms readability | Max 3 textured backgrounds (cover, closing, one accent); always set `background-color` fallback first; mute competing texture with a semi-transparent overlay | L-5 |

---

## E. Mined Corrections — Typography & Color

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| E-1 | Sub-13px content; two-line stat labels | Tiny or wrapping labels read as cramped and unconsidered | Body ≥15px, diagram nodes ≥14px, table cells ≥13px; no content below 13px; shorten copy so stat labels fit one line | T-1 |
| E-2 | Sub-24px or muted feature-card icons | Small/faded icons add visual noise without function — a generated-deck tell | Feature-card icons ≥24px in `var(--primary)`; remove icons that cannot meet this rather than shrinking them | T-3 |
| E-3 | Placeholder/training-mean color values left in `:root` | Stock palette values are the clearest "no brand input" signal | Replace every `:root` value with real brand tokens | C-1 |
| E-4 | Mixed stat colors within one semantic group; `var(--danger)` used for non-negative values; mixed currency/time basis in one grid | Inconsistent stat coloring reads as random, not systematic; misused danger-red miscommunicates | One accent color per semantic stat group; reserve `var(--danger)` for genuinely negative values only; uniform currency and time basis across a grid | C-2 |
| E-5 | Colored borders used diagonally or at random; red borders on decision/go-no-go boxes | Random colored borders destroy the system signal; red reads as danger, not rigor | Colored borders carry consistent, intentional logic across the deck; decision/kill-criteria boxes use NEUTRAL borders | C-4 |
| E-6 | **Recoloring a client's logo mark** — white/black knockout, inversion, tinting, or any color shift to make it fit a slide | The logo is the one asset that must appear exactly as the brand owns it; altering it reads as off-brand and careless, and on a known brand it is an instant credibility hit | Render every logo in its ORIGINAL brand colors, even at aesthetic cost. On a dark background where it would disappear, use a client-supplied reversed/light logo if one exists, ELSE sit the original-color logo on a light backing panel/container — NEVER recolor, invert, or knock out the mark | owner directive 2026-06-13 |

---

## F. Mined Corrections — Component Patterns

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| F-1 | Equal-weight competitive comparison grids (all cards rendered identically) | An even comparison signals lack of confidence in the product | Product card dominates (`.card--winner`: elevation, stronger shadow, brand `border-top`); competitors de-emphasized (`.card--loser`, opacity 0.75) | CP-1 |
| F-2 | Risk or decision-gate statements styled as footnotes | Burying failure modes and kill criteria reads as hiding them; they are first-class content | `.callout--risk` (danger-bordered) for failure modes; `.callout--gate` (warning-bordered) for decision gates | CP-3 |
| F-3 | 1px gray flow-diagram connectors | Thin gray connectors disappear in PDF and read as unfinished | Unicode arrows (→, ↓) in brand color, minimum 2px weight | CP-4 |
| F-4 | Equal-weight before/after columns | Rendering both sides identically loses the transformation the slide exists to show | "After" column heavier (`var(--primary-dark)`, weight 600); "before" de-emphasized (`var(--gray-600)`, weight 400) | CP-5 |
| F-5 | **Source citations placed inline / mid-text** — a `(Source: …)` or reference dropped beside the claim in the body | Inline citations interrupt the one-idea-per-slide read and clutter the focal content; they read as unpolished | Anchor source citations as **footnotes at the BOTTOM of the slide**, visually subordinate to the body (small, muted), with a small marker beside the claim only if needed. Distinct from F-2: risk/decision statements are first-class callouts, never footnotes — THIS rule governs SOURCE CITATIONS only | owner directive 2026-06-13 |

---

## G. Mined Corrections — Print/PDF Safety

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| G-1 | Print-unsafe CSS on render-to-PDF elements (`aspect-ratio`, transforms on positioned elements, pseudo-elements for structural content, complex `clip-path`) | These silently break in the PDF the owner actually ships — the slide looks fine in-browser, broken in the deliverable | Explicit `width`+`height`; `writing-mode: vertical-rl` for rotated text; real DOM elements for dividers; simple shapes or SVG for clipping | P-1 |
| G-2 | A deck with no mandatory `@media print` block | Without it, colors and page breaks are unreliable in Decktape/Chromium export | Mandatory `@media print`: `-webkit-print-color-adjust: exact`, `.slide { page-break-inside: avoid; }`, `@page { size: landscape; margin: 0; }` | P-3 |

---

## H. Mined Corrections — Pitch-Reference Anti-Patterns

| # | Banned attractor | Why it reads as slop | Reach for instead | Mining-map row |
|---|------------------|----------------------|-------------------|----------------|
| H-1 | Default templates; paragraphs of body text; product screenshots; complex "maze" diagrams; vague market sizing | Each is a documented common-mistake tell — illegible, generic, or unconvincing | Clean illustrations over screenshots; one focal element per slide; bottom-up market methodology; simple over complex diagrams | PR-6 |
| H-2 | A slide carrying more than one idea; a low-contrast or non-obvious slide | A slide a stranger cannot grasp at a glance fails the Legible/Simple/Obvious test | One idea per slide; high contrast, large type, key text at top; understandable at a glance | PR-4, SL-1 |
| H-3 | Label-style slide titles ("Traction", "Market") | A label states the topic, not the takeaway — wasted real estate | Title states the POINT ("$120K MRR, 40% MoM") — what the reader should conclude | ML-4 |
| H-4 | Exposed internal machinery in a client pitch (tech stack, AI model choices, infrastructure) | Kitchen details read as vendor-centric and invite irrelevant objections | Describe capabilities and outcomes only; never the machinery behind them | SC-3 |
| H-5 | Vendor-perspective, feature-dump framing in a client pitch | "We're the best at X" reads as self-serving; feature dumps lose the buyer | Frame everything from the client's perspective ("You'll gain X"); outcome-focused, in the client's language | SC-5 |

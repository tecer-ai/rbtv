# Hypresent-Friendly HTML Convention (02)

A FORMAT-AGNOSTIC convention expressed as editability **hints**, not document-type assumptions (decision D3). The editor is fully robust on conforming files and DEGRADES GRACEFULLY on non-conforming ones. This document doubles as the spec the upstream AI generator follows to emit maximally-editable HTML.

**Core principle:** a hint is a signal that makes an element easier and safer to edit. NEVER a structural requirement. The editor MUST work on a file with zero hints (e.g., both analyzed test files predate this convention) — hints only raise the ceiling on editability and reduce ambiguity.

---

## 1. What the Editor Detects WITHOUT Any Hints (baseline robustness)

These are derived from the live DOM and require nothing from the document:

| Capability | How the editor derives it (no hint needed) |
|------------|--------------------------------------------|
| Editable text | Leaf elements whose only children are text nodes / inline formatting (`<b>`, `<i>`, `<span>`, `<a>`) become text-editable on double-click. SVG `<text>` excluded; SVG `<path>` never treated as text. |
| Element selection | Any element resolvable by the registry can be selected (single click in select tool). |
| Layout role for resize/move | Computed style read at action time: flex child, grid child, `position:absolute`, or normal-flow block. Drives D1/D2 behavior. |
| Theme tokens | `:root` custom properties are enumerated by reading `document.documentElement`'s computed style for `--*` names found in the stylesheet text. |
| Inline colors | Elements carrying `style="color:…"` / `background:` / `fill:`/`stroke:` are discovered by scanning `style` attributes for color-valued properties. |
| Sections/regions | Top-level repeated structural containers are detected heuristically (see §4); NEVER by assuming a class name. |

Both test files are fully text-editable, recolorable, and resize/move-able under this baseline.

---

## 2. The Hints (what makes a file MAXIMALLY editable)

A generator SHOULD emit these. Each hint has a defined fallback (§3) so omission only degrades, never breaks.

| Hint | Form | What it buys |
|------|------|--------------|
| **H1 — Stable element hook** | `data-hyp-hook="<stable-name>"` on any element the author considers a meaningful edit target | Gives the editor a durable, human-meaningful handle that survives re-generation; comment anchors prefer it; resolves the "repeated siblings have no id" problem from both analyses. |
| **H2 — Colors via CSS variables** | Define all theme colors as `:root` custom properties and reference them with `var(--token)`; name tokens semantically (`--accent`, `--surface`, `--text`) | Palette editor recolors the whole document by mutating tokens (D6a). The more color flows through tokens, the fewer per-element overrides the user needs. |
| **H3 — Editable-region marker** | `data-hyp-region="<label>"` on each top-level content region (a slide, a report section, a card group) | Makes region detection exact instead of heuristic; powers an outline/navigator and scopes operations. Replaces guessing `.slide` vs `.block`. |
| **H4 — Editable-text opt-in/opt-out** | `data-hyp-text="true"` to force a node editable; `data-hyp-text="false"` to lock it (e.g., a generated counter, a legal line) | Resolves the structural-vs-content text ambiguity (report `.chip` labels, `.n` counters) deterministically. |
| **H5 — Resize axis hint** | `data-hyp-resize="width\|height\|both\|none"` on resizable elements | Tells the editor which sizing property to mutate without inferring from layout; `none` protects elements that must not resize. |
| **H6 — Move policy hint** | `data-hyp-move="free\|locked"` | `locked` suppresses the move handle on elements that must stay in flow (nav, fixed chrome). |
| **H7 — Decorative marker** | `data-hyp-decorative="true"` on purely decorative nodes (background SVG, overlay layers) | Editor skips them in selection/outline so users are not offered nonsense targets; complements `aria-hidden`. |
| **H8 — Asset base declaration** | `<meta name="hyp-asset-base" content="assets/">` | Documents where relative assets live so Save-As-to-a-different-folder can warn about asset portability. |
| **H9 — Palette manifest** | `<script type="application/json" id="hyp-palette">{ "tokens": ["--accent", …] }</script>` | Lists which `:root` tokens are user-facing theme colors (vs internal spacing/radius vars), so the palette editor shows only color tokens. |

Naming rule for all hints: attributes are `data-hyp-*`; embedded JSON manifests use `id="hyp-*"` and `type="application/json"` so they are inert and survive Save As (consistent with the comment island, D4).

---

## 3. Graceful-Degradation Rules (hint absent)

For every hint, the editor has a defined fallback. The editor NEVER refuses to operate because a hint is missing.

| Missing hint | Degraded behavior |
|--------------|-------------------|
| H1 stable hook | Editor injects a runtime-only `data-hyp-id`; comment anchors fall back to the collision-resistant anchor key defined in `01` §6.1 (tag+nth-of-type path + nearest native id + content hash + same-key sibling index — NOT a bare tag/nth fingerprint, which would collide on repeated identical siblings). Edits still work; cross-regeneration durability is reduced. |
| H2 variable colors | Recolor falls back to per-element overrides (D6b) and inline-`style` color mutation. Palette editor still lists whatever `:root` color tokens exist; if none, it shows "no theme tokens — use per-element color". |
| H3 region marker | Regions detected heuristically (§4). Outline still populated; may be coarser or include false regions the user can ignore. |
| H4 text opt-in/out | Editability inferred structurally (leaf text node test). Ambiguous nodes (a `<span>` that is both label and content) default to EDITABLE but are flagged in the inspector as "auto-detected". |
| H5 resize axis | Axis inferred from layout role: flex-row child → width (`flex-basis`); flex-column child → height; grid child → track; absolute → both. |
| H6 move policy | All elements movable by default; nav/fixed elements are NOT specially protected (user can still undo). |
| H7 decorative | Decorative nodes are selectable (no harm); `aria-hidden="true"` is used as a secondary signal to de-prioritize them in the outline. |
| H8 asset base | Save-As-to-different-folder shows a generic "relative assets may not resolve in the new location" warning. |
| H9 palette manifest | Palette editor shows ALL `:root` custom properties whose value parses as a color; non-color tokens are auto-filtered by value. |

---

## 4. Region Detection Heuristic (used when H3 absent)

Deterministic, class-agnostic algorithm (so the editor never presupposes `.slide`/`.block`):

1. Identify the primary content root: the element containing the most text-bearing descendants among `<body>`'s element children and their immediate wrappers (handles `<body>`-as-deck AND `<aside>+<main>+<footer>` cases).
2. Within the content root, a "region" is a direct child element that is either (a) a sectioning element (`<section>`, `<article>`, `<header>`, `<footer>`, `<main>`), or (b) a repeated sibling sharing the same tag+class signature with ≥1 peer.
3. Decorative nodes (`aria-hidden="true"` or H7) are excluded.
4. Result is an ordered region list for the outline; it is advisory only — selection/editing never depends on correct region segmentation.

---

## 5. Worked Examples (against the two test files)

| File | Hints present today | Editor behavior |
|------|---------------------|-----------------|
| The deck fixture (slide deck) | None (no ids, no `data-*`, colors mostly via `:root`) | Regions = the ~10 slide `<section>`s detected as repeated tag+class siblings (H3 fallback). Text fully editable (leaf-node test). Recolor via the existing `:root` tokens (H2 satisfied de-facto) + per-element overrides for the ~10 inline styles. Resize via flex/grid inference (H5 fallback). |
| The report fixture (report) | Partial (native ids on sections, native `data-*` content, own JS) | Regions = content `<section>`s with native ids detected as sectioning elements (H3 fallback) — native ids respected, NOT overwritten. Native `data-*` content preserved (never edited). Semantic absolutely-positioned nodes recognized as `position:absolute` SEMANTIC content → resize edits `left/top/width/height`, move uses transform. Inline `style="left:…%"` and legend `background:` colors handled by per-element/inline color path (H2 fallback). Inline SVG traversed without treating `<path>` as text. The document's own IIFE JS keeps running; editor classes are `hyp-`only so the document's own state classes are untouched. |

---

## 6. Generator Checklist (for the upstream AI)

To emit a maximally-editable file, the generator SHOULD:

- [ ] Route ALL theme colors through `:root` custom properties (H2) and publish them in a palette manifest (H9).
- [ ] Put `data-hyp-region` on every top-level content region (H3) and `data-hyp-hook` on every meaningful, individually-editable element, especially repeated siblings (H1).
- [ ] Mark decorative layers `data-hyp-decorative="true"` and/or `aria-hidden="true"` (H7).
- [ ] Set `data-hyp-text="false"` on generated/structural text (counters, legal lines) and `data-hyp-resize="none"` / `data-hyp-move="locked"` on elements that must not be resized/moved (H4–H6).
- [ ] Keep the document's own scripts self-contained and idempotent (the editor shares the DOM; avoid global side effects on classes the editor might read).
- [ ] Declare the asset base via `<meta name="hyp-asset-base">` (H8).
- [ ] NEVER rely on a hint for correctness of the document itself — hints are additive metadata; the file must render and run with them stripped (the editor strips all `data-hyp-*` on Save As except the inert JSON islands).

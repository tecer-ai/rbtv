# Fixture Profiles

hypresent was verified end-to-end against two HTML fixtures chosen to span the structural extremes a format-agnostic editor must survive. The fixtures themselves are private and live outside this repo; this file records ONLY the generic structural traits the editor must handle. Throughout the docs these fixtures are referred to as the **deck fixture** (DECK) and the **report fixture** (REPORT).

---

## Fixture A — the deck fixture (zero-JS flex/grid slide deck)

A static, paginated slide deck: ~10 sibling `<section>` slide elements, no wrapping container, print `break-after: page`.

| Trait | Detail the editor must handle |
|-------|-------------------------------|
| Sections | ~10 repeated `<section>` siblings of the same tag+class, detected as regions by the repeated-sibling heuristic — never by assuming a class name |
| Layout | Flexbox (primary) + CSS Grid (multi-column card grids); `position:absolute` used ONLY for decorative overlays, never for content |
| Styling | Single embedded `<style>` block + ~17 CSS custom properties driving the palette; ~10 incidental inline styles; no CSS framework |
| Repeated cards | Multiple identical sibling cards inside a grid, with NO `id` to distinguish them — positional/content-hash disambiguation required |
| Identifiers | NO `id` attributes and NO `data-*` anywhere — class-only targeting; the editor must inject its own additive handles |
| SVG / canvas / images | No inline SVG, no canvas; a handful of `<img>` with relative `assets/` paths and `onerror` fallbacks |
| Web fonts | Google Fonts + an icon font via CDN (network-dependent) |
| JavaScript | ZERO — no `<script>`, no handlers, no framework; nothing for an injected runtime to collide with |

**Editor lesson:** text editing and palette recolor (CSS-variable mutation) generalize cleanly; resize must be layout-aware (mutate `flex-basis`/`width`/grid tracks, NOT `top/left/width/height`); stable edit handles must be injected on load because the source has none.

---

## Fixture B — the report fixture (JS-driven scrolling report)

A long-form, single-scroll document with a fixed sidebar and live JavaScript — the structural opposite of Fixture A.

| Trait | Detail the editor must handle |
|-------|-------------------------------|
| Structure | Continuous scroll: fixed sidebar nav + `<main>` with a hero, several content `<section>` blocks (each with a native `id`), and a footer |
| Navigation | A fixed sidebar + scroll-spy driven by the document's OWN `IntersectionObserver` — the injected runtime must not interfere with it |
| Layout | Fixed sidebar + CSS Grid (hero/grids) + flexbox + normal-flow prose + **semantic absolutely-positioned nodes** (content positioned at percentage `left` values — layout-critical, NOT decorative) |
| Styling | Single embedded `<style>` block + ~13 CSS custom properties; MORE inline styles than the deck (~20+), several carrying layout-critical values that sit OUTSIDE the variable system |
| Repeated siblings | Multiple identical sibling cards in grids, no `id` — same disambiguation problem as the deck |
| Identifiers | ~9 native `id` attributes AND native `data-*` attributes that CARRY SEMANTIC CONTENT (tooltip/expansion data) — the editor must respect native ids and never overwrite native `data-*`, distinguishing them from its own `data-hyp-*` |
| Inline SVG | Present for both decoration and functional UI icons — must be traversed without corrupting `<path>` geometry or treating paths as editable text |
| Images | None |
| Web fonts | Google Fonts via CDN (network-dependent) |
| JavaScript | NON-TRIVIAL vanilla IIFE: mobile sidebar toggle, IntersectionObserver scroll-spy, reveal-on-enter animation, scroll progress bar, and expand/collapse cards — all mutate classes/inline styles on the live DOM the editor shares |

**Editor lesson:** an injected runtime SHARES the DOM and event loop with the document's own JS — class mutations can collide with JS-driven state, so all injected classes/ids/attributes must be `hyp-`namespaced and the document's own classes/ids/`data-*` treated read-only; recolor must reach inline-`style` colors, not only tokens; resize must treat semantic absolutely-positioned nodes as layout-critical, not free-to-move decoration; the content region and section pattern must be detected from the live DOM, never presupposed.

---

## Why two fixtures

Fixture A and Fixture B falsify each other's simplifying assumptions: zero-JS vs. heavy-JS, class-only vs. native-id+`data-*`, decorative-absolute vs. semantic-absolute, no-SVG vs. inline-SVG, variable-driven color vs. inline-style color. Any capability is "done" only when it survives BOTH — which is why the verification gate runs every check against both fixtures.

# R3 Live-Debug Evidence Summary (2026-06-05)

Instrumented live session: owner reproduced resize scenarios in `tecer-gsmm-introduction-test.html` while a capture-phase recorder logged pointer gestures + all inline-style mutations (old→new). Raw trace: `live-debug-raw.json` (16 gestures, 400 mutations). Console during all gestures: ZERO editor errors (only the known fixture-asset 404s).

## Gesture archetypes (the load-bearing evidence)

| G# | Element (hypId) | Layout context | Cursor ΔX | Result | Verdict |
|----|----------------|----------------|-----------|--------|---------|
| G0 | `.flow-node--accent` (hyp-39) | flex child `grow:1.4`, parent `justify-content:center` | +66 (E handle) | `flex-basis` 1141→1324 (**+183 = 2.77×**); rendered w +33.6, x shifted −33.6 (both sides) | **AMPLIFICATION** on the basis path |
| G2,G3,G5,G8,G9 | same hyp-39 | same | −182 … −800 (E) | basis moves **±1px**; rendered w UNCHANGED (1322.8) | **DEAD ZONE** — felt as "cannot resize" |
| G4,G10 | same hyp-39 | same | +645…+653 (W handle) | basis ±2px, rendered unchanged | dead zone both handles |
| G7 | same hyp-39 | same | dY +36 (NE corner) | height 94→88 (**−6 for 36 = 0.17×**) | height-axis anomaly, unexplained |
| G6,G11 | `.intro-anchor` (hyp-22) | grid middle column (gtc `408.5px 606px 408.5px` — side columns absorb), grid-centered | +61 / +71 (E) | inline `width` +60.7 / +71 — **exact 1:1**; x shifts left by Δ/2 (both sides) | width path healthy; both-sides = real grid centering |
| G12,G13 | `.heard-item` (hyp-59/69) | grid column, start-pinned | −160 / −161 (E) | width −159.5 / −158, x pinned | **CORRECT 1:1 one-sided** |
| G14,G15 | `.stage-card` (hyp-161/165) | grid `repeat(3, ~474px)` | −135 / −147 (E) | width tracks exactly, x pinned | **CORRECT 1:1 one-sided** |

## Live forensics

- Flow row (`.flow-diagram`, 1471px, flex, justify-center, gap 10): children = `flow-node{grow:1, basis:0%, w:104}`, `flow-arrow{grow:0, w:14}`, `flow-node--accent{grow:1.4, basis:1323px(inline), w:1322.81}`, `flow-arrow{grow:0, w:0}`. The accent node is the dominant grower → **rendered width = container leftovers, regardless of basis** (grow refills any basis decrease; increases can't exceed leftovers). This is the dead-zone mechanism, exactly.
- `.intro-anchors` grid: `gtc 408.5px 606px 408.5px` — middle column tracks the element's width; equal side columns = grid centering → both-sides visual growth with width edits.
- `.stage-grid`: 3 equal ~474px columns, `justify-items: normal` → explicit width start-aligns; one-sided.

## Mechanism hypotheses for diagnosis (confirm/refute in code)

1. **flex-basis path (R10 core):** the resize handler maps Moveable's requested width into `flex-basis` without solving for grow/shrink redistribution. With `grow>0`: slack ⇒ amplification (G0); no slack ⇒ dead zone (G2-G10). The dragged edge never tracks the cursor on flex-grow items.
2. **Centered contexts (R12/UX):** width edits are 1:1 (healthy) but the dragged edge moves Δ/2 — per D1 this stays (honest layout), Alt adds explicit symmetric.
3. **G7 height 0.17×:** unexplained — separate look needed (corner-handle axis math?).
4. **Guides during resize (R11):** none appeared in any gesture; README claims move-parity. Verify what `interaction.js` passes to Moveable `snappable` for resize vs drag.

## Test-file state (matters for verification)

- `tecer-gsmm-introduction-test.html` carries morning-session residue: inline `flex-basis: 1141px` on the accent node + 2 inline widths. Structure matches the pristine twin (`tecer-gsmm-introduction.html`, zero flex-basis) — use the PRISTINE twin for clean automated tests; the test file is the owner's living artifact.
- Open observation (unverified, low priority): live DOM after today's 16 gestures showed the flow row with only 4 children (trailing `flow-node` absent) while the saved file is structurally complete — possibly a stray re-parent during a corner-handle gesture today. Worth one look in R10 testing.

## Comment-feature facts (S4/S5, no live repro needed)

- Saved island: `<script type="application/json" id="hyp-comments">` with `anchor: {hook:null, path:"body:1/section:1/div:2", nativeId:null, contentHash:"a874e6e5", siblingIndex:0}`.
- Head block emits `anchor: body:1/section:1/div:2 | id="" | "<contextText>"` — path notation undefined for consumers; goes stale after the consuming agent's own first edit. D4 fixes via `data-hyp-agent` stamping.

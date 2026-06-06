# Research 03 — Flow Reorder Drag

**Date:** 2026-06-03
**Scope:** Combining Moveable free-drag (transform:translate) with same-parent flow reorder in Hypresent.
**This file is the sole write.**

---

## Executive Summary

Verdict: **hand-roll a ~150-line `reorder.js` module** — do not vendor SortableJS or dnd-kit.
Hit-test choice: **pointer Y (or X for row flex) vs. sibling midpoint** (50% threshold).
Live preview: **on-drop DOM mutation only** (no sibling shift during drag). Optional FLIP transition post-drop.
Top interop hazard: **Moveable uses `setPointerCapture`; a second drag system on the same element would race for pointer ownership** — hand-roll avoids this entirely.

---

## 1. Established Patterns: Free Drag + Flow Reorder

### How page builders split the two modes

| Tool | Free-drag trigger | Reorder trigger | Detection basis |
|------|------------------|-----------------|-----------------|
| GrapesJS (open-source) | `globalAbsolute: true` or element has `position:absolute` in computed style | Otherwise — always flow reorder | Mode is selected per-element on dragstart, not during drag [S4] |
| GrapesJS Studio SDK | Explicit "Absolute Mode" plugin, opt-in per component | Normal (default) | Same static decision on dragstart [S6] |
| Craft.js | Positioning logic ported from GrapesJS | Flow reorder is default | Per-node `position` prop [S7] |
| dnd-kit | Never free-drag; all reorder via virtual state | Collision detection continuously | `closestCenter` / `closestCorners` algorithms [S1] |
| SortableJS | No free-drag; list reorder only | Always reorder | Pointer vs. element midpoint [S2] |

**Pattern:** every serious page-builder makes the free-vs-reorder decision **once, at dragstart**, by inspecting a static property (element type, CSS position, explicit mode flag). No tool tries to re-classify mid-drag. For Hypresent this maps cleanly: if the element has siblings under the same parent AND the active tool is `move`, begin in free-drag mode; if a "reorder zone" hit is detected on `onDrag`, switch intent (not yet commit). Commit mode switch only on `onDragEnd`.

### Hit-testing approaches surveyed

| Approach | Used by | Accuracy | Complexity |
|----------|---------|----------|------------|
| Pointer Y (or X) vs. sibling midpoint — 50% threshold | SortableJS, Pragmatic DnD | Good for 1-axis lists | O(n) scan, ~10 lines |
| Pointer distance to element centroid (Euclidean) | Julik Tarkhanov article, dnd-kit `closestCenter` | Good for 2D grids | O(n) scan, ~15 lines |
| Dragged-element-center vs. sibling rect overlap (% area intersection) | dnd-kit `rectIntersection` | Highest accuracy but lags | O(n), expensive on every `mousemove` |
| `document.elementFromPoint` under pointer | Touch fallback in SortableJS, GrapesJS sorter | Accurate; DOM traversal | Single call, but misses hidden siblings |

**Recommendation for Hypresent:** pointer-position vs. sibling midpoint (50% threshold). Rationale: elements in a flex row or column are 1-axis lists; the 50% midpoint rule maps naturally to "am I closer to the left/top half or right/bottom half of this sibling". It is the approach with the most adoption [S2, S3, S8], is O(n) with cheap BoundingClientRect reads, and produces the same visual result as Google Slides object reorder. The `elementFromPoint` approach is disqualified because siblings with `pointer-events:none` (Moveable's wrapper div sits on top at z:999998) would intercept the test.

---

## 2. Live Preview: Sibling Shift During Drag vs. On-Drop Only

### Option A — Sibling shift during drag (Slides-like live preview)

Mechanics: on every `onDrag` event, re-evaluate hit, apply `transform: translateY/X(±itemSize)` to siblings that would shift, clear transforms on no-hit or on drag-end.

Implementations: tahazsh.com vanilla example [S8]; react-flip-move library.

Cost:
- Continuous `getBoundingClientRect` reads on every Moveable `onDrag` event (fires at pointer framerate).
- `requestAnimationFrame`-gating needed or layout thrash is guaranteed on large slides.
- Siblings need their own temporary transforms cleared reliably on drop/cancel; state management complexity doubles.
- Moveable emits `onDrag` at high frequency (~16ms); piggybacking sibling layout reads on every event is measurable overhead in a document with many elements.

### Option B — On-drop DOM mutation only (recommended)

On `onDragEnd`: compute hit once, call `insertBefore`, clear the dragged element's translate. Optional: run FLIP on affected siblings for a smooth settle animation (single 200ms transition, not continuous).

Cost: one `getBoundingClientRect` pass on `onDragEnd`. Zero layout reads during drag. No sibling state to manage.

**FLIP post-drop pattern:**
1. `FIRST`: snapshot all sibling `getBoundingClientRect()` before `insertBefore`.
2. `LAST`: call `insertBefore`, snapshot again.
3. `INVERT`: for each moved sibling, set `transform: translateX/Y(delta)` instantly (no transition).
4. `PLAY`: on next `rAF`, clear the invert transforms with a CSS `transition: transform 200ms ease` already set. Browser interpolates from inverted-to-zero.

This is the exact technique used by CSS-Tricks FLIP [S9], react-flip-move [S10], and Motion (Framer) layout animations. In vanilla JS it is ~30 lines and requires no library.

**Verdict: Option B.** On-drop only, with optional FLIP settle animation. Rationale: avoids layout thrash during drag, simpler state, reuses the already-committed `onDragEnd` hook that exists in `move.js`.

---

## 3. Concrete Algorithm for Hypresent

### Input contracts

- Moveable fires `onDrag(e)` with `e.translate = [dx, dy]` and `onDragEnd(e)`.
- Every element has `data-hyp-id`.
- Same-parent siblings are detected by `el.parentElement.children` filtered for `data-hyp-id`.
- History stack accepts `{do, undo, label}` commands via `history.push`.

### Algorithm pseudocode

```
// reorder.js — called from move.js

function getSiblings(el):
  return Array.from(el.parentElement.children)
    .filter(c => c !== el && c.dataset.hypId)

function getFlexDirection(el):
  return getComputedStyle(el.parentElement).flexDirection
  // returns 'row' | 'row-reverse' | 'column' | 'column-reverse' | ''

function detectReorderTarget(dragEl, pointerX, pointerY):
  // Returns {target, insertBefore} or null if no hit
  siblings = getSiblings(dragEl)
  dir = getFlexDirection(dragEl)
  isHorizontal = dir.startsWith('row') || isGridRow(dragEl.parentElement)

  for sibling of siblings:
    rect = sibling.getBoundingClientRect()
    if isHorizontal:
      mid = rect.left + rect.width / 2
      if pointerX >= rect.left && pointerX <= rect.right:
        return {target: sibling, insertBefore: pointerX < mid}
    else:
      mid = rect.top + rect.height / 2
      if pointerY >= rect.top && pointerY <= rect.bottom:
        return {target: sibling, insertBefore: pointerY < mid}

  return null  // pointer is not over any sibling → free move, keep translate

// Called from move.js onDragEnd handler:
function commitReorder(dragEl, pointerX, pointerY, prevTranslate):
  hit = detectReorderTarget(dragEl, pointerX, pointerY)
  if hit is null:
    // No reorder — keep existing translate behavior (no change to current move.js)
    return

  parent = dragEl.parentElement
  prevSiblingId = dragEl.previousElementSibling?.dataset.hypId ?? null
  nextSiblingId = dragEl.nextElementSibling?.dataset.hypId ?? null

  // FLIP — snapshot before DOM mutation
  snapshots = new Map()
  for child of getSiblings(dragEl):
    snapshots.set(child, child.getBoundingClientRect())

  // DOM reorder
  if hit.insertBefore:
    parent.insertBefore(dragEl, hit.target)
  else:
    parent.insertBefore(dragEl, hit.target.nextSibling)

  // Clear the translate that was applied during free drag
  dragEl.style.transform = ''  // or use CSS individual `translate` property (see §5)

  // FLIP — invert and play on siblings that moved
  requestAnimationFrame(() => {
    for [sibling, before] of snapshots:
      after = sibling.getBoundingClientRect()
      dx = before.left - after.left
      dy = before.top - after.top
      if dx !== 0 || dy !== 0:
        sibling.style.transition = 'none'
        sibling.style.transform = `translate(${dx}px, ${dy}px)`
        requestAnimationFrame(() => {
          sibling.style.transition = 'transform 200ms ease'
          sibling.style.transform = ''
        })
  })

  // Push undo command — capture sibling refs by data-hyp-id, not index
  cmd = {
    label: 'reorder element',
    do: () => {
      // Re-apply the same insertBefore computed above
      if hit.insertBefore: parent.insertBefore(dragEl, hit.target)
      else: parent.insertBefore(dragEl, hit.target.nextSibling)
      dragEl.style.transform = ''
    },
    undo: () => {
      // Restore to prevSiblingId / nextSiblingId
      prev = parent.querySelector(`[data-hyp-id="${prevSiblingId}"]`)
      next = parent.querySelector(`[data-hyp-id="${nextSiblingId}"]`)
      if next: parent.insertBefore(dragEl, next)
      else: parent.appendChild(dragEl)
    }
  }
  history.push(cmd)  // NOTE: history.push calls cmd.do() — do NOT call insertBefore twice
                     // Refactor: pass {do,undo} without calling do() inside commitReorder,
                     // OR use history.pushNoExec(cmd) if such a variant is added
```

**Note on history integration:** `history.push` currently calls `cmd.do()` immediately (per `history.js` line ~40). `commitReorder` already mutated the DOM. Options: (a) add `history.record(cmd)` that appends without calling `do()`, or (b) wrap the DOM mutation inside `cmd.do()` and call `history.push` before mutating — the latter is cleaner and matches existing command patterns in `commands.js`.

### No-hit behavior (alternative: revert vs. keep)

Two choices on drop with no sibling hit:

| Choice | Behavior | Pros | Cons |
|--------|----------|------|------|
| **Keep translate** (current `move.js` behavior) | Element stays at dragged position with `transform: translate()` | Consistent with existing move semantics; user can layer free-move on top of reorder | Out-of-flow translate persists; emits `out-of-flow` event |
| **Revert translate on no-hit** | If user drops into "empty space" inside the container, snap back | Cleaner for slide-box containers where free float is not desired | Loss of user intent; may feel broken |

Recommendation: **keep existing translate** on no-hit. This preserves D2 and is a pure extension, not a replacement, of the existing move behavior.

---

## 4. Library vs. Hand-Rolled

### Why vendoring SortableJS or dnd-kit is not worth it

**Event capture conflict — primary disqualifier.**
Moveable.js acquires pointer capture via `setPointerCapture` on `pointerdown` to track drag across the entire document [S11]. SortableJS uses `touchstart`/`mousemove` or its own `pointerdown` handler. If both attach to the same element, one of two outcomes occurs:
1. Moveable fires `pointercancel` when SortableJS calls `setPointerCapture` (browser cancels the first capture).
2. SortableJS's `dragstart` event fires but Moveable has already captured the pointer — SortableJS receives no subsequent `pointermove`, or vice versa.

This is a documented pointer-capture exclusivity rule [S11, S12]: once `setPointerCapture` is called on element A for pointer P, all `pointermove` and `pointerup` events for pointer P are routed to A, and other listeners receive nothing. Two independent drag systems cannot both own the same pointer simultaneously.

**Ghost element conflict.**
SortableJS creates a clone (`dragEl` ghost) and appends it to `document.body` or the container. Moveable also renders its own handle wrapper (`div.hyp-moveable-wrapper`) over the target. The ghost and the Moveable wrapper would overlap with competing z-indices and transform matrices.

**dnd-kit is React-only.**
dnd-kit is a React hooks library; Hypresent runtime is vanilla ES modules with no framework. Vendoring dnd-kit's core without React would require extracting ~3 packages and removing React dependencies — more work than writing the algorithm.

**What hand-roll costs:**
- `reorder.js`: ~150 lines (detection, FLIP, undo command). Estimated 2–3 hours.
- Integration into `move.js` `onDragEnd`: ~10 lines (call `commitReorder` before current commit path).
- No new dependencies, no new event systems, no pointer-capture conflict.

**What hand-roll does NOT need to implement:**
- Pointer capture (Moveable already owns it).
- Ghost element (Moveable's translate preview is the ghost).
- Cross-container drag (out of scope per requirements).
- Touch support (Moveable handles touch normalization).

**Verdict: hand-roll wins decisively.** The pointer-capture conflict alone is a hard blocker for SortableJS. dnd-kit is framework-incompatible. The algorithm is simple (one 50% midpoint test, one insertBefore, one FLIP).

---

## 5. Edge Cases

| Edge case | Behavior / Mitigation |
|-----------|----------------------|
| **Grid containers** | `detectReorderTarget` must check `display: grid` on parent. DOM `insertBefore` reorders source order, which CSS Grid respects (it lays out in DOM order by default unless `order` or explicit `grid-column/row` placement is used). If the grid uses explicit placement (`grid-column: 1` etc.), reorder changes DOM order but visual order may not shift — spec this as "grid reorder changes DOM order; visual result depends on grid template". No special case needed in the algorithm unless explicit placement is detected. |
| **Nested editable elements** | `data-hyp-id` is on the editable element, not its children. Moveable targets `el` by `hypId`; drag events are on `el`. A child click during move tool mode must not re-select — `selection.js` click delegation already handles this (it walks up to the nearest `data-hyp-id` ancestor). No new case needed. |
| **Dropping on self** | `getSiblings(dragEl)` explicitly filters out `dragEl` — impossible to hit-test against self. |
| **Dragging between different parents** | `detectReorderTarget` only looks at `el.parentElement.children` — cross-parent drops return null (treated as free move, translate is kept). Cross-parent reorder is explicitly out of scope. |
| **Elements with existing non-translate transforms** | `move.js` currently overwrites `el.style.transform` with `translate(x, y)` only, dropping any existing `rotate` or `scale` (known risk from recon section 14, Risk 3). **Mitigation (independent of reorder):** switch `move.js` to write `el.style.translate = '${x}px ${y}px'` using the CSS individual `translate` property. The individual `translate` property is fully independent of `transform` and does not overwrite `rotate`/`scale` set via `transform` or their individual CSS counterparts [S13]. Browser support: all modern browsers since August 2024 [S13]. On reorder commit, clear `el.style.translate = ''` instead of `el.style.transform = ''`. This fixes Risk 3 as a side-effect of implementing reorder. |
| **Elements with existing translate in `transform`** | If source HTML uses `transform: translateX(20px)` natively (not editor-applied), `move.js` already parses and accumulates it. On reorder drop, clearing `el.style.transform` restores the native transform. If the native transform is in the element's stylesheet (not inline), clearing `el.style.transform = ''` leaves the stylesheet rule intact — correct behavior. If it was inline, the editor should not have been allowed to move it without user intent — this is an existing gap not introduced by reorder. |
| **Undo after reorder** | `cmd.undo()` restores by `insertBefore` using captured `nextSiblingId` as anchor. If the sibling was also moved by a subsequent operation, the sibling may no longer be in the same position — this is standard undo stack non-commutativity, acceptable and consistent with how `resize.js` and `move.js` handle it (they capture absolute values, not relative). |
| **`history.push` calls `cmd.do()`** | Structural conflict noted in §3. Cleanest fix: add `history.record(cmd)` variant that only appends without executing. Alternative: construct the command first, pass it to `history.push`, and let `cmd.do()` perform the DOM mutation. Match existing `commands.js` pattern. |
| **No-hit on drop in flex gap** | Pointer lands in the gap between two siblings — both midpoint checks return false. Returns null → free move, translate is kept. Acceptable: user can drag again to land on a sibling if reorder was intended. |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

[S1] dnd-kit Sortable (new docs) — https://dndkit.com/concepts/sortable/ — 2026-06-03 — 2026 — TS:8.7 (AT:9 TR:9 TM:8)

[S2] SortableJS Wiki: Sorting with HTML5 DnD API — https://github.com/SortableJS/Sortable/wiki/Sorting-with-the-help-of-HTML5-Drag%27n%27Drop-API/ — 2026-06-03 — 2023 — TS:8.3 (AT:8 TR:9 TM:8)

[S3] Julik Tarkhanov: UI algorithms: drag-reordering — https://blog.julik.nl/2022/10/drag-reordering — 2026-06-03 — 2022-10 — TS:7.7 (AT:7 TR:8 TM:8)

[S4] GrapesJS Issue #1774: Feature Request: Drag and Drop Absolute Positioning — https://github.com/GrapesJS/grapesjs/issues/1774 — 2026-06-03 — 2021 — TS:7.3 (AT:8 TR:7 TM:7)

[S5] dnd-kit Collision Detection Algorithms (legacy docs) — https://docs.dndkit.com/api-documentation/context-provider/collision-detection-algorithms — 2026-06-03 — 2023 — TS:8.7 (AT:9 TR:9 TM:8)

[S6] GrapesJS Studio SDK: Absolute Mode — https://app.grapesjs.com/docs-sdk/plugins/canvas/absolute-mode — 2026-06-03 — 2025 — TS:8.0 (AT:8 TR:8 TM:8)

[S7] Craft.js GitHub — https://github.com/prevwong/craft.js/ — 2026-06-03 — 2024 — TS:7.7 (AT:8 TR:8 TM:7) (positioning logic ported from GrapesJS, per search result)

[S8] Taha Shashtari: Seamless drag-to-reorder with vanilla JS — https://tahazsh.com/blog/seamless-ui-with-js-drag-to-reorder-example/ — 2026-06-03 — 2024 — TS:7.0 (AT:7 TR:7 TM:7)

[S9] CSS-Tricks: Animating Layouts with the FLIP Technique — https://css-tricks.com/animating-layouts-with-the-flip-technique/ — 2026-06-03 — 2018 (technique is stable) — TS:8.3 (AT:8 TR:9 TM:8)

[S10] react-flip-move GitHub — https://github.com/joshwcomeau/react-flip-move — 2026-06-03 — 2023 — TS:7.7 (AT:8 TR:8 TM:7)

[S11] MDN: Element.setPointerCapture() — https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture — 2026-06-03 — 2026 — TS:9.7 (AT:10 TR:10 TM:9)

[S12] Pragmatic Drag and Drop (Atlassian) — https://blog.logrocket.com/implement-pragmatic-drag-drop-library-guide/ — 2026-06-03 — 2024 — TS:7.7 (AT:8 TR:7 TM:8)

[S13] MDN: CSS translate property — https://developer.mozilla.org/en-US/docs/Web/CSS/translate — 2026-06-03 — 2026 — TS:9.7 (AT:10 TR:10 TM:9)

[S14] Rob Hickman: Sortable list with pointer events — https://robehickman.com/js-drag-drop-sortable — 2026-06-03 — 2023 — TS:7.0 (AT:7 TR:7 TM:7)

---

## Sources Discarded

No sources discarded — all cited sources met TS >= 6 threshold.

---

## Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library vs. hand-roll | Hand-roll (~150 lines) | Pointer-capture conflict blocks SortableJS; dnd-kit is React-only; algorithm is simple |
| Hit-test | Pointer position vs. sibling midpoint (50% threshold) | Canonical approach [S2, S3], O(n), avoids `elementFromPoint` interference from Moveable wrapper |
| Live preview | On-drop DOM mutation + optional FLIP | Avoids layout thrash during drag; simpler state; FLIP is ~30 extra lines |
| Axis detection | `flexDirection` from `getComputedStyle(parent)` | Row flex → compare X; column flex / block → compare Y |
| No-hit behavior | Keep existing translate | Preserves D2; free move is still valid user intent |
| Transform composition | Switch `move.js` to CSS `translate` property | Fixes Risk 3 (transform overwrite) as side effect; independent of `transform:rotate/scale` [S13] |
| Undo/redo anchor | Capture `previousElementSibling` and `nextElementSibling` data-hyp-id | Stable across future mutations; consistent with existing command pattern |

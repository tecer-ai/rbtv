# V4-T4 Blocking Bug — R12 symmetric resize via `fixedDirection`

## Summary
The task-specified edits to `runtime/js/interaction.js` do **not** make the R12
 Alt-held symmetric-resize tests pass. Two of four R12 tests fail;
 the full suite has 2 failures (both R12), 126 passed, 1 skipped.

## Edit history

### Initial attempt (verbatim per original task spec)
1. `onResizeStart(e)`: after the capture block, inserted:
   ```js
   if (moveable) { moveable.fixedDirection = (e.inputEvent && e.inputEvent.altKey) ? [0, 0] : false; }
   ```
2. `onResizeEnd()`: above the `const el = byId(activeHypId)` early-return guard, inserted:
   ```js
   if (moveable) moveable.fixedDirection = false;
   ```
**Result:** 2 failed (E-R12-1, E-R12-4). Root cause: `moveable.fixedDirection` is not a
 dynamically settable top-level instance property in the vendored `moveable.min.js`.
 The correct API is `e.setFixedDirection([0,0])` on the resizeStart event object.

### ADX-3 follow-up (orchestrator override)
1. Replaced the inert assignment in `onResizeStart` with:
   ```js
   if (e.inputEvent && e.inputEvent.altKey) { e.setFixedDirection([0, 0]); }
   ```
2. Removed the dead `onResizeEnd` reset of `fixedDirection`.

**Result:** Still 2 failed (E-R12-1, E-R12-4). Behavior changed but not to passing:
  - E-R12-1: `right` now moves 120 px (expected 60). Width grows 120 px but the
    non-absolute block element (`#twin`) does not shift its `left` edge, so the
    dragged edge overshoots the cursor by 60 px.
  - E-R12-4: `right`, `left`, and `width` assertions pass (flex container
    `justify-content: center` redistributes the growth), but the `inlBasis`
    assertion fails because `applyVisualResize` computes
    `toContent(beforeRect.width + dist)` which for the content-box fixture
    subtracts padding (≈48 px), yielding 547.0 instead of the expected 594.6.

## Root-cause analysis
`setFixedDirection([0,0])` DOES activate Moveable's center-anchor resize
(`e.width` grows by 2Δ, `e.dist` arrives as the cursor delta). However,
`applyVisualResize` was written for one-sided (edge-opposite-handle) resize and
has no symmetric-resize position correction:

- For **non-flex / non-absolute** elements (E-R12-1, `#twin`), it sets
  `width = e.width` directly but never shifts `left`/`margin`/`transform` to
  keep the center fixed. The box therefore grows to the right only.
- For **flex children** (E-R12-4, `#node-accent`), it sets
  `flexBasis = toContent(beforeRect.width + dist)` which subtracts padding for
  content-box elements. The FROZEN test expects `inlBasis = before["w"] + 120`,
  ignoring the `toContent` padding adjustment.

## Impact
- R12 Alt-symmetric resize is **partially functional**: the width grows correctly
  (2Δ), but visual positioning is wrong for non-flex/non-absolute elements and
  the flex-basis inline value does not match the FROZEN test expectation.
- R10 and all other suites remain green (no regression).

## Recommended fix
`applyVisualResize` needs two symmetric-resize adaptations:
1. Track whether the current gesture is center-anchored (e.g. via a module-level
   flag set in `onResizeStart`).
2. In the non-flex branch, when center-anchored, shift the element by `-dw/2`
   horizontally and `-dh/2` vertically (via `translate`, `margin`, or `left`/`top`
   for absolute elements).
3. In the flex branch, the `toContent` padding subtraction is actually correct for
   content-box, but the FROZEN test expectation `before["w"] + 120` is wrong for
   content-box. Since tests cannot be edited, the code would need to set
   `flexBasis` to the border-box value (skip `toContent`) when center-anchored,
   or the fixture would need `box-sizing: border-box`.

Because tests are FROZEN and `applyVisualResize` was spec'd as unchanged,
resolving this requires either a test-fixture change or an ADX decision to
modify `applyVisualResize`.

## ADX-4 resolution
RESOLVED by ADX-4 (changelog row 197); flex-child translate-skip deviation flagged to review (row 201).

## D14 compliance
- Tests were **not** modified (frozen per V4-T3).
- No tests were weakened, xfailed, or skipped.
- Commit made after full-suite green (129 passed, 1 skipped, 0 failures).


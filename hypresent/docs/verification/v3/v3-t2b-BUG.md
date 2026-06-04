# V3-T2b Blocking Bug Report

**Date:** 2026-06-04
**Agent:** Kimi Code CLI (test-fix executor, V3-T2b)
**Context:** Product fixes V3-T1 + V3-T1b have landed. Test-side fixes per FIX SPEC (b) + D25 amendment were applied to the two allowlisted test files. Both suites were re-run fail-loud. Multiple hard assertions failed; per D14 this bug report is filed and execution stopped.

---

## Summary

Three distinct blocking issues were revealed after the test-side changes landed:

1. **V3-T1 pointer-events over-reach — `.moveable-origin` blocks target interaction** (primary product bug, new)
2. **Missing Escape-to-deselect in the runtime** (known product gap, now hard-asserted by D25)
3. **D25(c) ±8 px alignment tolerance is incompatible with Moveable's natural control-box padding** (test/design mismatch)

In addition, one flaky timeout on `wait_runtime_ready` was observed.

---

## 1. V3-T1 pointer-events over-reach — `.moveable-origin` blocks clicks / drags / dblclicks

### Evidence

- `test_double_click_edits_and_escape_resumes` (F2): **ERROR** — Playwright timeout on `dblclick`. Log shows:
  ```
  <div class="moveable-control moveable-origin"></div> from <div id="hyp-interaction-wrapper">…
  subtree intercepts pointer events
  ```
- `test_move_changes_translate_by_delta` (R2): **FAIL** — `style.translate` is empty after a 48×32 px real body drag.
- `test_reorder_changes_dom_index` (R2): **FAIL** — DOM index unchanged after real drag of sibling over sibling.
- `test_drag_shows_guidelines` (F2): **ERROR** — timeout on runtime ready (flaky), but when it does run it would hit the same intercept issue.

### Root cause

V3-T1 injects this rule into the iframe `<head>`:

```css
#hyp-interaction-wrapper .moveable-control-box,
#hyp-interaction-wrapper .moveable-control,
#hyp-interaction-wrapper .moveable-line,
#hyp-interaction-wrapper .moveable-area,
#hyp-interaction-wrapper .moveable-direction {
  pointer-events: auto;
}
```

The selector `.moveable-control` matches `.moveable-control.moveable-origin`. The origin handle is rendered at the geometric centre of the selected element (verified live: it sits directly over the target's `getBoundingClientRect()` centre). Because it now has `pointer-events: auto`, it swallows every real `mousedown`/`click`/`dblclick` that lands on the element centre — which is exactly where the tests (and users) click to drag, move, reorder, or double-click-to-edit.

Before V3-T1 the control box was off-screen (position:fixed bug), so the origin handle was harmless. After V3-T1b fixed the coordinate frame (position:absolute), the origin handle came on-screen and became a blocker.

### Why this is a product bug, not a test bug

The `.moveable-origin` is a purely visual indicator of the transform origin; it is not an interactive handle. Moveable's own base CSS scopes `pointer-events: none` to `.moveable-origin` (confirmed in the vendored stylesheet walk from the debug report). V3-T1's broad `.moveable-control` selector overrides that scoped `none` and turns the origin into an invisible shield.

The debug report §C noted that the SE handle's computed `pointer-events` was `auto` and concluded pointer-events was "fully fixed", but it never tested interaction paths that hit the element centre — so this secondary defect was invisible to the debug session.

### Required fix (product, outside allowlist)

Narrow the injected rule so `.moveable-origin` retains `pointer-events: none`:

```css
#hyp-interaction-wrapper .moveable-control-box,
#hyp-interaction-wrapper .moveable-control:not(.moveable-origin),
#hyp-interaction-wrapper .moveable-line,
#hyp-interaction-wrapper .moveable-area,
#hyp-interaction-wrapper .moveable-direction {
  pointer-events: auto;
}
#hyp-interaction-wrapper .moveable-control.moveable-origin {
  pointer-events: none;
}
```

Or, more minimally, add an explicit override after the existing rule:

```css
#hyp-interaction-wrapper .moveable-origin { pointer-events: none; }
```

File: `runtime/js/interaction.js` (`ensureInteractionStyle()`).

---

## 2. Missing Escape-to-deselect

### Evidence

- `test_escape_and_empty_click_deselect` (F2): **FAIL** — after pressing Escape:
  ```
  AssertionError: 1 != 0 : Escape should remove wrapper
  ```

### Root cause

The runtime has zero keydown listeners for Escape deselect:
- `text-edit.js:180-183` handles Escape only to call `commit()` when `activeHypId` is in text-edit mode.
- `selection.js` has no keyboard listener at all.
- `runtime-main.js` exposes a `clear-selection` bridge command, but it is only reachable from the parent shell, not from a physical Escape key.

### Required fix (product, outside allowlist)

Add a `keydown` listener in `selection.js` (or `runtime-main.js`) that calls `clear()` when `event.key === "Escape"`.

---

## 3. D25(c) alignment tolerance incompatible with Moveable natural padding

### Evidence

- `test_control_box_aligns_with_target` (R2): **FAIL**
  ```
  AssertionError: 22 not less than or equal to 8 :
  control-box left 102px is >8px from target left 80px (coordinate frame regression)
  ```

### Root cause

Moveable renders the `.moveable-control-box` container with built-in padding around the target (to accommodate direction handles, border lines, etc.). On `.research-card` the measured delta is **22 px** horizontally; the debug report's live-patch data implies a **~59 px** vertical delta is also normal. The D25(c) mandate of ±8 px on top-left fails on correctly-functioning Moveable output.

The ±8 px tolerance does successfully distinguish the `position:fixed` regression (delta ≈ 2910 px), but it is too strict for normal operation.

### Required fix (product or test spec)

Either:
- (a) Configure Moveable with `padding: 0` (or equivalent) so the control box edge-aligns with the target edge; **or**
- (b) Relax the test tolerance to a value that captures the regression without false-failing on normal Moveable padding (e.g. ±80 px, or assert that delta is `< 100` and `> -50`).

Because the task instructions forbid weakening tests, this is reported as a blocking discrepancy pending a product or spec decision.

---

## Flaky issue observed

- `test_drag_shows_guidelines` (F2) once hit a `TimeoutError` on `wait_runtime_ready` (8000 ms). This is likely a race between server cold-start and the first test in the suite. It is not consistently reproducible and is separate from the structural bugs above.

---

## Files modified (allowlist only)

- `tests/e2e/test_f2_select_guides.py`
- `tests/e2e/test_r2_resize_real.py`

`conftest_helpers.py` was **not** modified.

## Test outcome

| Suite | Run | Result |
|-------|-----|--------|
| R2 (`test_r2_*.py`) | 7 tests | 3 failures |
| F2 (`test_f2_*.py`) | 8 tests | 1 failure, 2 errors |

No tests were skipped (the D25 conditional skip path was never reached because the empty-click probe never got a chance to run in the failing test, and the R2 suite has no skips).

dispatchEvent count in both files: **0**.

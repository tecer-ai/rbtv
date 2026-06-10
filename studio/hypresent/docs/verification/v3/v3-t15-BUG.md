# V3-T15 — Blocking Product Bug Report

**Date:** 2026-06-04
**Task:** V3-T15 R7 test: alignment matrix + capability payload + disabled-state
**File under test:** `tests/e2e/test_r7_alignment.py` (port 8797)

## Summary
The R7 alignment feature does not apply the expected CSS properties when alignment toolbar buttons are pressed, and incorrectly disables vertical-alignment buttons for `display:table-cell` and fixed-height `display:block` elements. These are blocking product bugs; per D14 addendum the test file is created but product files are **not** patched.

## Evidence — per-test failures

### E-R7-1 / E-R7-2 — `test_h_block_center_and_undo`
- **Failure:** `AssertionError: 'start' != 'center'`
- **Meaning:** Clicking `#align-center` on a `display:block` element does **not** set `text-align:center`.
- **Expected:** `text-align` becomes `center`.
- **Actual:** `text-align` remains `start`.

### E-R7-3 / E-R7-4 — `test_flex_row`
- **Failure:** `AssertionError: 'normal' != 'center'`
- **Meaning:** Clicking `#align-middle` on a `display:flex;flex-direction:row` element does **not** set `align-items:center`.
- **Expected:** `align-items` becomes `center`.
- **Actual:** `align-items` remains `normal`.

### E-R7-5 — `test_flex_column`
- **Failure:** `AssertionError: 'normal' != 'flex-end'`
- **Meaning:** Clicking `#align-right` on a `display:flex;flex-direction:column` element does **not** set `align-items:flex-end`.
- **Expected:** `align-items` becomes `flex-end`.
- **Actual:** `align-items` remains `normal`.

### E-R7-6 — `test_grid`
- **Failure:** `AssertionError: 'normal' != 'center'`
- **Meaning:** Clicking `#align-center` on a `display:grid` element does **not** set `justify-items:center`.
- **Expected:** `justify-items` becomes `center`.
- **Actual:** `justify-items` remains `normal`.

### E-R7-7 — `test_table_cell`
- **Failure:** `playwright._impl._errors.TimeoutError: Page.click: Timeout 30000ms exceeded.`
- **Meaning:** `#align-bottom` is **disabled** on a `display:table-cell` element, so the click times out.
- **Expected:** `#align-bottom` is enabled and clicking it sets `vertical-align:bottom`.
- **Actual:** Button disabled; title tooltip says "Vertical alignment needs a fixed-height, flex, grid, or table-cell element" — yet the element **is** `table-cell`.

### E-R7-8 — `test_plain_block_vertical_disabled`
- **Result:** PASS
- **Note:** This test correctly verifies that vertical buttons are disabled on an auto-height block.

### E-R7-9 — `test_fixed_height_block_vertical`
- **Failure:** `playwright._impl._errors.TimeoutError: Page.click: Timeout 30000ms exceeded.`
- **Meaning:** `#align-middle` is **disabled** on a `display:block;height:200px` element.
- **Expected:** `#align-middle` is enabled and clicking it converts display to `flex` and sets `justify-content:center`.
- **Actual:** Button disabled; same tooltip as above. The capability-detection logic does not recognize a fixed-height block as supporting vertical alignment.

### E-R7-10 — `test_align_caps_payload`
- **Failure:** `SyntaxError: Identifier 'win' has already been declared` (test-side doc_eval variable collision).
- **Note:** This is a minor test-code issue, but the underlying product behavior is already covered by the disabled-state failures above.

### E-R7-11 — `test_no_console_errors`
- **Result:** PASS

## Regression count
- **FAIL:** 4 (assertion mismatch)
- **ERROR:** 3 (timeout on disabled buttons + SyntaxError)
- **PASS:** 2
- **SKIP:** 0

## Deterministic root-cause observation
Across all display modes (block, flex-row, flex-column, grid), clicking an alignment button does **not** mutate the target element's computed style. This suggests either:
1. The alignment command handlers are not wired to the toolbar buttons, or
2. The command execution path mutates a different element / property, or
3. The `alignCaps` payload sent on `selection-changed` is not being used to drive the toolbar state correctly (buttons disabled when they should be enabled for `table-cell` and fixed-height block).

## Action
STOP. Product fix required before V3-T15 can be accepted.

# V3-T18 — Blocking Product Bug Report

## Run summary
- **Full suite**: `python -m unittest discover -s tests -p "test_*.py" -v`
- **Unit tests**: 18 tests — all OK (zero skips, zero failures).
- **E2E tests**: 98 tests — **FAILED (failures=2, errors=3, skipped=1)**.
- **R1 ctypes z-order test**: **RAN and PASSED** on this interactive machine (`GetForegroundWindow() != 0`).

## Skips (accepted per D28 / D25)
| Test | Reason |
|------|--------|
| `test_escape_and_empty_click_deselect` (F2) | `fixture has no empty point (live-probed 191 candidates) — empty-click deselect unverifiable here; designed deselect path asserted` — D25-permitted conditional skip. |

**SKIPPED_LINES_COUNT**: 1  
No other skips observed.

## Failures (blocking — STOP)

### 1. EXIT smoke — R3 delete assertion
- **Test**: `tests.e2e.test_exit_smoke.ExitSmokeTests.test_full_smoke_zero_console_errors`
- **Line**: 166
- **Assertion**: `self.assertFalse(H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{del_id}\"]');"), "R3: element deleted")`
- **Error**: `AssertionError: True is not false : R3: element deleted`
- **Analysis**: After the preceding smoke steps (text edit, R8 font-size, R2 resize, move, color change, comment add, agent tag), clicking `#delete-btn` does **not** remove the selected `.research-card` / `.kicker` element from the DOM. The element with the captured `data-hyp-id` is still present after the delete click + 250 ms wait.
- **Reference**: The dedicated R3 suite (`tests/e2e/test_r3_delete.py`) passes in isolation, so this is an **integration/state bug** that surfaces only when delete is exercised after the full smoke sequence.

### 2. F2 — empty-click deselect
- **Test**: `tests.e2e.test_f2_select_guides.F2SelectGuidesTests.test_escape_and_empty_click_deselect`
- **Line**: 364
- **Assertion**: `self.assertEqual(wrapper_count2, 0, "click-empty-space should remove wrapper")`
- **Error**: `AssertionError: 1 != 0 : click-empty-space should remove wrapper`
- **Analysis**: When an empty point is successfully probed in the fixture, clicking that empty coordinate does **not** clear the `#hyp-interaction-wrapper` or the selection ring. Empty-space click deselect is broken in the product.

## Errors (blocking — STOP)

### 3. F5 — comment composer agent checkbox timeout
Three distinct F5 tests hit the **same** product UI stability bug:

- `tests.e2e.test_f5_comments.F5CommentTests.test_agent_block_escapes_body`
- `tests.e2e.test_f5_comments.F5CommentTests.test_agent_checkbox_on_submission`
- `tests.e2e.test_f5_comments.F5CommentTests.test_reply_appears_in_agent_block`
- `tests.e2e.test_f5_comments.F5CommentTests.test_round_trip_reopens_agent_thread`

**Common traceback**:
```
playwright._impl._errors.TimeoutError: Locator.check: Timeout 30000ms exceeded.
Call log:
  - waiting for locator(".hyp-composer-agent input")
    - locator resolved to <input type="checkbox"/>
    - attempting click action
      2 × waiting for element to be visible, enabled and stable
```

**Analysis**: The `.hyp-composer-agent input` checkbox resolves in the DOM but Playwright cannot interact with it because it never becomes "visible, enabled and stable". This indicates the composer agent toggle is either obscured, animating indefinitely, or incorrectly positioned in the product.

## Conclusion
The full suite is **NOT green**. The strengthened EXIT smoke surfaced an R3 delete integration gap, and pre-existing F2/F5 product bugs are also present. Per D14, no product files were patched.

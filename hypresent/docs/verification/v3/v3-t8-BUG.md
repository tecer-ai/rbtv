# V3-T8 R3 Delete Test — Blocking Product Bugs

Date: 2026-06-04

## Test Invocation Metrics

```
Command: python -m unittest discover -s tests/e2e -p "test_r3_*.py" -v
WALL_CLOCK_MS: 20257
EXIT_CODE: 1
SKIPPED_LINES_COUNT: 0
```

## Failed Tests (3 of 7)

### 1. `test_delete_then_undo` (E-R3-1 / E-R3-2)
**Failure:** Element is NOT removed from the DOM after clicking `#delete-btn`.

```
AssertionError: True is not false : element should be removed from the DOM after delete
```

The toolbar delete button click does not delete the selected element. The delete command itself is not executing or is failing silently.

### 2. `test_delete_blocked_while_editing` (E-R3-6)
**Failure:** Element IS deleted while a text edit is active — the edit-active guard is missing or broken.

```
AssertionError: False is not true : element must NOT be deleted while a text edit is active (V3-S10)
```

The double-click successfully enters text-edit mode (contenteditable), but the subsequent `#delete-btn` click still removes the element. The expected guard that blocks delete during active editing is not functioning.

### 3. `test_thread_unanchored_on_delete_and_reanchor_on_undo` (E-R3-3 / E-R3-4)
**Failure:** After undo, the thread remains in the Unanchored section instead of re-anchoring to the restored element.

```
AssertionError: 1 != 0 : thread must re-anchor after undo, not remain unanchored (RV10)
```

The thread correctly moves to Unanchored when its element is deleted, but after undo restores the element, the thread does not re-anchor. It stays in `#comment-unanchored` with count=1 instead of moving back to `#comment-threads`.

## Passing Tests (4 of 7)

- `test_last_region_block` (E-R3-5) — PASS
- `test_moveable_torn_down_after_delete` (E-R3-8) — PASS
- `test_no_console_errors` (E-R3-9) — PASS
- `test_no_keyboard_delete` (E-R3-7) — PASS

## Root-Cause Assessment

1. **Delete command is not working for normal selection** — the `#delete-btn` click either does not trigger the `delete-element` bridge command, or the command handler fails silently (possibly because the selected element lacks the expected registry state, or the command registration from V3-T7 is incomplete).

2. **Edit-active guard missing** — `runtime-main.js` may not check `document.activeElement.isContentEditable` before executing `delete-element`, or the guard logic is bypassed.

3. **Re-anchor on undo missing** — the undo path for `deleteElement` restores the DOM node but does not call `reanchorComments()` (or equivalent) to move threads from Unanchored back to the restored element.

## Action

STOP. Do not patch product files. These are pre-existing product bugs that must be fixed in the R3 feature implementation (V3-T7) before this test can pass.

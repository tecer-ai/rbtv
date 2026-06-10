# V4-T8 Blocking Bug Report

**Task:** V4-T8 – R13 Comment Edit / Delete  
**Date:** 2026-06-05  
**Status:** RESOLVED-AS-PLANNED – full suite is green when the sanctioned R11 RED set is excluded.

## Full-suite result (before sanctioned exclusion)

```
2 failed, 140 passed, 1 skipped in 196.50s (0:03:16)
```

## Failing tests

Both failures are in the R11 resize-guides test file and are unrelated to the R13 comment edit/delete changes.

| Test | Error |
|------|-------|
| `tests/e2e/test_r11_resize_guides_equal_size.py::R11ResizeGuidesEqualSizeTests::test_e_r11_2_equal_size_snap_lands_on_matched_dimension` | `AssertionError: 297 != 300 within 0.5 delta (3 difference)` |
| `tests/e2e/test_r11_resize_guides_equal_size.py::R11ResizeGuidesEqualSizeTests::test_e_r11_3_equal_size_hint_renders_during_snap` | `AssertionError: 0 not greater than or equal to 1` |

## Reproduction

```powershell
python -m pytest tests/e2e/test_r11_resize_guides_equal_size.py -v
```

Result: same two tests fail deterministically.

## Why this blocks V4-T8 commit

Per discipline D14: *On a blocking product bug, STOP and write `docs/verification/v4/v4-t8-BUG.md`. Never commit over a red full suite.*

The V4-T8 implementation (comment edit/delete) only touches:

- `runtime/js/comments.js`
- `runtime/js/runtime-main.js`
- `app/js/main.js`
- `app/js/shell/comment-composer.js`

None of those files implement resize guides or equal-size snapping. The R11 failures are pre-existing with respect to V4-T8, but because the full suite is not green the task is blocked from being committed.

## Targeted verification that is green

- `node --check` passes on all four modified JS files.
- Targeted R13 run: `8 passed`.
- Comment regression run (F5 + G2): `18 passed`.

## Scoped gate (sanctioned exclusion)

```powershell
python -m pytest tests/ --ignore=tests/e2e/test_r11_resize_guides_equal_size.py -q
```

Result: `137 passed, 1 skipped in 191.26s (0:03:11)` — zero failures.

## Resolution

RESOLVED-AS-PLANNED: the 2 failures are the R11 RED set (V4-T5), excluded by orchestrator sanction (changelog row 209); R11 GREEN lands in V4-T6.

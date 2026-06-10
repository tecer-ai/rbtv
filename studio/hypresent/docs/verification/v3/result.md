# V3-T18b EXIT Evidence — Result

Date: 2026-06-04
Attempt: 3 (full suite + clean server run)
Fix spec applied: v6 (FIX C-1, A-1, B-1)

## Fast feedback (Step 2)

| Suite | Command | Result | Wall | EXIT | Skipped lines |
|-------|---------|--------|------|------|---------------|
| F2 | `python -m unittest discover -s tests/e2e -p "test_f2_*.py" -v` | OK (skipped=1) | ~12s | PASS | 1 |
| F5 | `python -m unittest discover -s tests/e2e -p "test_f5_*.py" -v` | OK | ~24s | PASS | 0 |
| Exit smoke | `python -m unittest discover -s tests/e2e -p "test_exit_smoke*.py" -v` | OK | ~10s | PASS | 0 |

## Full suite (Step 3)

| Command | Result | Wall | EXIT | Skipped lines |
|---------|--------|------|------|---------------|
| `python -m unittest discover -s tests -p "test_*.py" -v` | Ran 116 tests in 140.347s — OK (skipped=1) | ~140s | PASS | 1 |

### Skips (accepted only)

1. **test_f2_select_guides.F2SelectGuidesTests.test_escape_and_empty_click_deselect**
   - Reason: `fixture has no empty point (live-probed 191 candidates) — empty-click deselect unverifiable here; designed deselect path asserted`
   - Category: D25 accepted skip (conditional fixture limitation)

2. **R1 z-order test** (`unit.test_r1_dialog_zorder.DialogZOrderTests.test_real_open_dialog_is_topmost_and_foreground`)
   - Result: **RAN and PASSED** (no skip; environment has a foreground window)

No other skips. No failures.

## Clean server run (Step 4)

Confirmation:
- `GET /app/` → HTTP 200 ✅
- `GET /runtime/js/runtime-main.js` → HTTP 200, Content-Type: text/javascript ✅
- Editor console errors (non-asset): **0** ✅
- Asset 404s (sample's own images): 8 — expected and allowed ✅

## Suite-to-state summary (R1–R9)

| Suite | Tests | State | Notes |
|-------|-------|-------|-------|
| R1 dialog seam | 5 | PASS | |
| R1 dialog z-order | 1 | PASS | ran (no foreground-window skip) |
| R2 select/guides | 8 | PASS (1 skip) | D25 empty-point skip |
| R3 delete/undo | 3 | PASS | Fix A-1 applied |
| R4/R9 chrome-free | 3 | PASS | |
| R5 comments | 13 | PASS | Fix C-1 applied |
| R6 save round-trip | 3 | PASS | |
| R7 palette | 3 | PASS | |
| R8 font size repeat | 5 | PASS | |
| Server dialogs | 8 | PASS | |
| Server save | 3 | PASS | |
| **Total** | **116** | **OK (skipped=1)** | |

## Files modified

- `app/js/shell/comment-composer.js` — Fix C-1 (viewport bottom-clamp/flip for composer)
- `tests/e2e/test_exit_smoke.py` — Fix A-1 (live-selection del_id)
- `tests/e2e/test_f2_select_guides.py` — Fix B-1 (empty-point excludes hyp- artifacts)
- `docs/verification/v3/result.md` — this file
- `docs/verification/v3/v3-t18b-run.txt` — raw outputs

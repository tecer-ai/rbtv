# Hypresent v2 — Verification Results

**Date:** 2026-06-03  
**Runner:** `python -m unittest discover -s tests -p "test_*.py" -v`  
**Environment:** Python 3.12, Playwright sync API, headless Chromium

## Suite Scorecard

| Suite | Tests | Result |
|-------|-------|--------|
| Unit — `test_server_dialogs` | 9 | **PASS** |
| Unit — `test_server_save` | 3 | **PASS** |
| E2E — `test_f1_dialogs` | 6 | **PASS** |
| E2E — `test_f2_select_guides` | 8 | **PASS** |
| E2E — `test_f3_reorder_reparent` | 10 | **PASS** |
| E2E — `test_f4_border` | 7 | **PASS** |
| E2E — `test_f5_comments` | 13 | **PASS** |
| E2E — `test_g1_panel_survival` | 3 | **PASS** |
| E2E — `test_g2_save_with_comments` | 5 | **PASS** |
| E2E — `test_exit_smoke` | 3 | **PASS** |
| **Total** | **67** | **PASS** |

### Exact Summary Line

```
Ran 67 tests in 75.841s
OK
```

- **Failures:** 0
- **Skips:** 0

## Clean Server Run

- `GET /app/` → 200 OK
- `GET /runtime/js/runtime-main.js` → 200, `Content-Type: application/javascript`
- Editor console errors during full smoke: **0** (after filtering expected asset 404s)

## EXIT Gate

**GREEN** — All suites pass; 0 failures, 0 non-permitted skips.

# V4-T11 EXIT Evidence — Result

Date: 2026-06-05
Attempt: 1 (full suite + clean server run + doc sync)

## Full suite

| Command | Result | Wall | EXIT | Skipped lines |
|---------|--------|------|------|---------------|
| `python -m pytest tests/ -q` | 155 passed, 1 skipped in 234.50s | ~235s | PASS | 1 |

### Skips (accepted only)

1. **test_f2_select_guides.F2SelectGuidesTests.test_escape_and_empty_click_deselect**
   - Reason: `fixture has no empty point (live-probed 191 candidates) — empty-click deselect unverifiable here; designed deselect path asserted`
   - Category: D25 accepted skip (conditional fixture limitation)

No other skips. No failures.

## Per-scorecard mapping (R10–R14)

| Suite | File | Tests | State |
|-------|------|-------|-------|
| R10 resize 1:1 | `test_r10_resize_flex.py` | 9 | PASS |
| R11 resize guides + equal-size | `test_r11_resize_guides_equal_size.py` | 6 | PASS |
| R12 Alt symmetric | `test_r12_alt_symmetric.py` | 7 | PASS |
| R13 comment edit/delete | `test_r13_comment_edit_delete.py` | 8 | PASS |
| R14 agent stamping | `test_r14_agent_stamping.py` | 8 | PASS |
| R14 fresh-agent legibility | `test_r14_legibility.py` | 2 | PASS |

## Clean server run

Confirmation:
- `GET /app/` on port 8799 → HTTP 200 ✅
- Server started cleanly, no port conflicts ✅

## Zero editor console errors (REG-8)

- `test_r10_resize_flex.py` + `test_r13_comment_edit_delete.py` both include `test_no_console_errors` assertions on synthetic fixtures (`flow-grow.html`, `agent-comments.html`) — green ✅
- Exit-smoke suite (`test_exit_smoke.py`) also asserts zero non-asset console errors — green ✅

## Orchestrator R14 fresh-agent legibility gate

The orchestrator recorded PASS for the R14 fresh-agent legibility gate (G-R14-LEGIBILITY-1/2 resolvable via head block alone, position-independence proof passed).

## Files modified (this task)

- `README.md` — usage deltas for R10/R11/R12/R13/R14 + known-limitation additions
- `docs/spec/03-module-map.md` — module deltas for interaction.js, comments.js, serializer.js, runtime-main.js, comment-composer.js
- `docs/decision-log.md` — appended D15..D19 (existing rows byte-identical)
- `docs/build-log.md` — appended v4 improvement cycle entry
- `docs/verification/v4/result.md` — this file
- `docs/verification/v4/v4-t11-run.txt` — raw run outputs

# V3-T15d Bug Report — R7 Test Suite Flaky Failure

## Summary
Full-suite run of `tests/e2e/test_r7_*.py` fails with 8/9 pass, 1 ERROR.
The failing test (`test_align_caps_payload`) passes when executed in
isolation. Failure is a **test-infrastructure flake** (cold-start timeout
in shared helper `wait_runtime_ready`), not a product bug.

## Affected Test
| Test | Result | Detail |
|------|--------|--------|
| `test_align_caps_payload` | **ERROR** in `setUp` | `playwright._impl._errors.TimeoutError: Page.wait_for_function: Timeout 8000ms exceeded.` |
| `test_fixed_height_block_vertical` | PASS | — |
| `test_flex_column` | PASS | — |
| `test_flex_row` | PASS | — |
| `test_grid` | PASS | — |
| `test_h_block_center_and_undo` | PASS | — |
| `test_no_console_errors` | PASS | — |
| `test_plain_block_vertical_disabled` | PASS | — |
| `test_table_cell` | PASS | — |

## Root-Cause Analysis
The error originates in `conftest_helpers.py::wait_runtime_ready` (line 79),
called from `open_via_dialog_ui` (line 74), which is invoked by the test's
`setUp` (line 31). The timeout is **not** in `test_r7_alignment.py` logic.

Observations:
- The test passes consistently when run individually (`python -m unittest …test_align_caps_payload`).
- It fails consistently when it is the **first** test executed in the full
  discover run (alphabetical order places it first).
- This indicates a cold-start race: the first test to open a document via
  the dialog UI occasionally exceeds the 8000 ms `wait_runtime_ready`
  timeout before the runtime signals readiness.

## Why This Is Not a Product Bug
- No product code is on the stack trace.
- The shell/app loads successfully (HTTP 200s visible in logs).
- The timeout is in the shared E2E helper that waits for a JS readiness
  predicate inside the iframe; the predicate may simply need more time on
  the first load.

## Why the Allowlist Cannot Fix It
Per task instructions, the only file I may modify is
`tests/e2e/test_r7_alignment.py`. The flakiness lives in
`tests/e2e/conftest_helpers.py` (`wait_runtime_ready` timeout), which is
outside the allowlist.

## Recommended Fix (for future task, outside this allowlist)
Increase the timeout in `conftest_helpers.py::wait_runtime_ready` from
8000 ms to 15000 ms, or add a short retry/back-off loop for the first
test in a suite run.

## Evidence
- Full run: see `docs/verification/v3/v3-t15d-run.txt`
- Isolated run: same file, section 4

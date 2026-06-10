You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding): record measured WALL_MS + EXIT + per-skip reasons. Implausible metrics → BUG + STOP.

Edit-anchoring rule: locate by exact strings, NEVER line numbers.

# PB-T15 — EX1: clean, error-free local server run

## Objective
Produce the EX1 evidence: the server boots cleanly, both pages load with no console errors and no server errors. Evidence only — no product changes.

## FILE ALLOWLIST
- ✚ create `html/hypresent/docs/verification/prez-v1/ex1-server-run.md` (+ any capture files in a sibling `html/hypresent/docs/verification/prez-v1/ex1-server-run/` folder)
- ✗ no product changes. If you find a product bug, write it BLOCKED and stop (addendum rule 1).

## Procedure
1. Start the server in the background capturing stdout+stderr to a temp file: `python html/hypresent/server/server.py 127.0.0.1 8801` (cwd = `html/hypresent`). Measure WALL_MS from launch to "Serving on" appearing.
2. With a headless (or headed, if available) Playwright Chromium: navigate to `http://127.0.0.1:8801/app/` and `http://127.0.0.1:8801/app/builder.html`. Collect `page.on("console")` errors for each (ignore document-asset 404 warnings as the live suites do — see test_f2's console filter: skip messages containing `assets/` with `404`/`Failed to load resource`). Assert ZERO unexpected console errors on both pages.
3. Capture: the server's stdout+stderr (must contain `Serving on http://127.0.0.1:8801` and NO tracebacks), a screenshot of each page (`page.screenshot(path=...)` into the sibling capture folder), and the measured WALL_MS.
4. Stop the server cleanly (`proc.terminate()`).

## Acceptance criteria
- Server prints `Serving on http://127.0.0.1:8801`, no traceback in stderr.
- Both pages return 200 and produce zero unexpected console errors.
- WALL_MS for server boot is plausible (a stdlib server boot is typically <2s but >0; record the measured value).

## Evidence file
`html/hypresent/docs/verification/prez-v1/ex1-server-run.md`:
```
EX1 — clean server run
CMD: python html/hypresent/server/server.py 127.0.0.1 8801   (cwd html/hypresent)
BOOT_WALL_MS: {measured}
SERVER_STDOUT+STDERR:
  {captured — must show "Serving on" and no traceback}
/app/ console errors: {list, expected []}
/app/builder.html console errors: {list, expected []}
SCREENSHOTS: ex1-server-run/editor.png, ex1-server-run/builder.png
VERDICT: PASS|FAIL
```

DONE means: server ran clean, both pages loaded error-free, evidence + screenshots written. Any error → BLOCKED section naming it + stop (do NOT fix product code).

# V3-T6b Verification Anomaly Report

## Observation Summary
The R1 z-order test did NOT execute any real dialog test. The entire test class was skipped because the current environment lacks an interactive desktop session (headless CI/agent context).

## Measurements
- **WALL_MS**: 117
- **EXIT**: 0
- **PS_PROCS_BEFORE**: 1
- **Tests run**: 0
- **Skipped lines in output**: 2

## Anomaly Details
1. **WALL_MS < 1000**: Measured wall time was 117 ms. A genuine R1 run that spawns a real PowerShell WinForms dialog, polls EnumWindows at 0.2 s intervals, and joins the process after WM_CLOSE cannot complete in 117 ms. The prior reported 528 ms is therefore physically impossible.
2. **No genuine "ok"**: The output contains `OK (skipped=1)`, but zero individual test methods executed. The only "ok" present is the unittest framework's summary for a skipped suite.
3. **Skipped count != 0**: Two lines in the output contain the word "skipped", and the suite itself was skipped.
4. **Root cause**: The test's `setUpClass` detects the absence of an interactive desktop (`GetForegroundWindow() == 0` or similar desktop session check) and raises `unittest.SkipTest`, causing the entire class to be skipped. No dialog was spawned, no `EnumWindows` polling occurred, and no process was joined.

## Conclusion
This run is **BLOCKED**. No trustworthy pass evidence can be produced in this headless environment. To obtain valid R1 z-order test evidence, the test must be executed on an interactive Windows desktop session (e.g., a logged-in Windows 11 workstation with a visible desktop).

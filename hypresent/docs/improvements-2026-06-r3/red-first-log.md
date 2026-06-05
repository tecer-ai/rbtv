## R10 red-first (V4-T1)

**Date:** 2026-06-05
**Command:** `python -m pytest tests/e2e/test_r10_resize_flex.py -v`
**Master baseline:** current master (R10 product fix NOT applied)

### Red-first gate results

| Test | Master observed | Post-fix expected | Status |
|------|-----------------|-------------------|--------|
| E-R10-1 | Δright ≈ +246 for +60 cursor sweep | Δright = +60 ±2 | **RED** ✓ |
| E-R10-2 | Δw ≈ 0 for −120 cursor sweep | Δw = −120 ±2 | **RED** ✓ |
| E-R10-2b | Δw ≈ 0 for −100 cursor sweep | Δw = −100 ±3 | **RED** ✓ |

### Healthy paths (expected GREEN)

| Test | Status |
|------|--------|
| E-R10-3 | PASSED ✓ |
| E-R10-4 | PASSED ✓ |
| E-R10-5 | PASSED ✓ |
| E-R10-6 | PASSED ✓ |
| G-R10-UNDO | PASSED ✓ |
| G-R10-REDO | PASSED ✓ |

### Notes
- E-R10-1: master writes `flexBasis = e.width`; the accent node’s basis re-inflates via flex-grow:1.4, causing massive width amplification (~4× the cursor delta).
- E-R10-2/E-R10-2b: on the dead-zone fixture (`grow:8` + inline `flex-basis:1100px`), master’s basis-write is immediately refilled by grow, leaving rendered width unchanged (Δ≈0) despite a −120/−100 cursor sweep.
- G-R10-UNDO passed on master; it locks the AD1 capture contract that undo must restore all three flex longhands (including absent inline `flex-grow`).

red-first-gate: **SATISFIED**

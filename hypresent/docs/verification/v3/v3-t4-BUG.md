# V3-T4 — R8 Blocking Bug Report

**Date:** 2026-06-04
**Fixture:** tecer-gsmm-introduction.html
**Port:** 8798

## Summary
The load-bearing 3-press font-size test (E-R8-1) fails because repeated presses on `#fmt-font-inc` spawn **multiple sibling spans** with the same inline `font-size` instead of bumping a single tracked span.

## Observed Failure

### E-R8-1: `test_three_increases_one_span_plus6_zero_empty`
```
AssertionError: 3 != 1 : expected exactly ONE font-size span after 3 presses, got 3 (sizes=[34, 34, 34])
```
- **count:** 3
- **sizes:** [34, 34, 34]
- **emptyCount:** not reached (count assertion failed first)

### E-R8-2: `test_three_decreases_one_span_minus6`
```
AssertionError: 3 != 1 : expected ONE span, got 3
```
- **count:** 3

### E-R8-3: `test_mix_inc_inc_dec`
```
AssertionError: 3 != 1 : expected ONE span, got 3
```
- **count:** 3

### E-R8-4: `test_lifecycle_clear_between_edits` — PASS
### E-R8-5: `test_no_console_errors` — PASS

## Interpretation
Each press creates a **new** `<span style="font-size:...">` around the selection rather than reusing the span created by the previous press. The resulting DOM contains three identical-size spans nested or siblinged, which is exactly the regression R8 was meant to prevent.

## Action
Product fix required in runtime text-format / selection code. **No test files patched.**

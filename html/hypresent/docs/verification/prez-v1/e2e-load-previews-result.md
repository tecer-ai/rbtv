# PB-T13 — e2e: library-load suite + previews suite

## D29 EVIDENCE-METRICS BLOCK

### Suite: test_pb2_library_load (port 8802)
- **WALL_MS**: 2005
- **EXIT**: 0
- **ran**: 4
- **passed**: 4
- **failed**: 0
- **SKIPPED**: 0
- **SKIPPED_LINES_COUNT**: 0

### Suite: test_pb3_previews (port 8803)
- **WALL_MS**: 3790
- **EXIT**: 0
- **ran**: 5
- **passed**: 3
- **failed**: 0
- **SKIPPED**: 2
- **SKIPPED_LINES_COUNT**: 2
- **Skip reasons**:
  1. `fixture lib has 4 fragments < MOUNT_CAP — cap unverifiable here`
  2. `fixture lib has 4 fragments < MOUNT_CAP — eviction never triggers, in-view-blanking unverifiable here`

## as-built.md verification
- **before SHA-256**: `289bbfaeb23c96d315c9833cc22c38f95f4e1f0e8fdd0feb7a0cb88349b6d59e`
- **after SHA-256**: `289bbfaeb23c96d315c9833cc22c38f95f4e1f0e8fdd0feb7a0cb88349b6d59e`
- **Result**: byte-identical — no assembly touched the committed fixture.

## BLOCKED / BUG
None.

## Rerun with synthesized over-cap library

Both previously-skipped assertions were converted to real coverage using a disposable temp library synthesized by `make_overcap_library(min_slides=30)` in `builder_helpers.py`. The helper copies the committed `builder-lib` fixture to `%TEMP%`, duplicates the `intro-e2e` fragment/row with suffixed IDs (`intro-e2e-pillars-d1`, `d2`, ...) until the slide count reaches at least `MOUNT_CAP + 6` (30), and returns the temp path. No committed fixture is ever modified.

### Full run output (PB2 + PB3)
```
test_invalid_library_state ... ok
test_language_filter ... ok
test_library_load_envelope ... ok
test_pick_and_render_groups ... ok
test_io_gated_mount ... ok
test_mount_cap ... ok
test_no_inview_blanking ... ok
test_renderable_unit_no_runtime ... ok
test_scale_applied ... ok
----------------------------------------------------------------------
Ran 9 tests in 10.833s
OK
```

### Updated D29 metrics
- **test_pb2_library_load**: 4 ran, 4 passed, 0 failed, 0 skipped
- **test_pb3_previews**: 5 ran, 5 passed, 0 failed, 0 skipped
- **Total**: 9 ran, 9 passed, 0 failed, 0 skipped

### as-built.md before/after hash pair
- **before SHA-256**: `289bbfaeb23c96d315c9833cc22c38f95f4e1f0e8fdd0feb7a0cb88349b6d59e`
- **after SHA-256**: `289bbfaeb23c96d315c9833cc22c38f95f4e1f0e8fdd0feb7a0cb88349b6d59e`
- **Result**: byte-identical — temp libraries are disposable; committed fixture untouched.

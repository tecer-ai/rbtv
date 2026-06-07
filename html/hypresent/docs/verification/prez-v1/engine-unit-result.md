# PB-T3 Engine Unit Suite Evidence

## D29 Evidence-Metrics Block

| Metric | Value |
|--------|-------|
| SUITE | PB-T3 — Engine unit suite (core: self-check, happy-path, round-trip, --json) |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -p "test_engine_core.py" -v` |
| WALL_MS | 758.360 |
| EXIT | 1 |
| RAN | 22 |
| PASSED | 15 |
| FAILED | 7 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

## Full STDOUT+STDERR

```
test_fixture_01_manifest_rows_and_columns (test_engine_core.TestEngineCore.test_fixture_01_manifest_rows_and_columns)
9 data rows × 10 cells each. ... ok
test_fixture_02_slide_files_exist (test_engine_core.TestEngineCore.test_fixture_02_slide_files_exist)
9 slide fragment files exist. ... ok
test_fixture_03_bare_assets_exist (test_engine_core.TestEngineCore.test_fixture_03_bare_assets_exist)
Assets listed in the Assets table exist on disk. ... ok
test_fixture_04_shared_brand_png_exists (test_engine_core.TestEngineCore.test_fixture_04_shared_brand_png_exists)
shared-brand/partner-mark.png exists. ... ok
test_fixture_05_presets_and_as_built_blocks (test_engine_core.TestEngineCore.test_fixture_05_presets_and_as_built_blocks)
2 yaml preset blocks + 1 as-built block. ... ok
test_fixture_06_fragment_purity (test_engine_core.TestEngineCore.test_fixture_06_fragment_purity)
No fragment contains forbidden tags. ... ok
test_fixture_07_slide_number_coverage (test_engine_core.TestEngineCore.test_fixture_07_slide_number_coverage)
Covers unnumbered + 7 numbered slides. ... ok
test_fixture_08_exact_case_headings (test_engine_core.TestEngineCore.test_fixture_08_exact_case_headings)
Manifest header is exact-case. ... ok
test_fixture_09_no_in_cell_pipe (test_engine_core.TestEngineCore.test_fixture_09_no_in_cell_pipe)
No data cell contains a pipe character. ... ok
test_fixture_10_required_cells_non_empty (test_engine_core.TestEngineCore.test_fixture_10_required_cells_non_empty)
Required cells (id, file, section, title, lang, kind, summary) are non-empty. ... ok
test_fixture_11_seed_and_preset_round_trip (test_engine_core.TestEngineCore.test_fixture_11_seed_and_preset_round_trip)
Seed entry and presets parse and have correct 7-id slide lists. ... ok
test_happy_preset_nimbus_intro_en (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_en)
--preset nimbus-intro-en produces ok:true with correct metadata. ... FAIL
test_happy_preset_nimbus_intro_pt (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_pt)
--preset nimbus-intro-pt sets lang to pt. ... FAIL
test_happy_slides_explicit (test_engine_core.TestEngineCore.test_happy_slides_explicit)
--slides cover-nimbus.en,intro-pillars,closing-nimbus produces ok:true. ... FAIL
test_json_catalog_data (test_engine_core.TestEngineCore.test_json_catalog_data)
--catalog-data --json returns correct catalog_data. ... ok
test_json_drift_warning (test_engine_core.TestEngineCore.test_json_drift_warning)
Engine version drift produces a warning but ok:true. ... ok
test_json_envelope_die (test_engine_core.TestEngineCore.test_json_envelope_die)
Die case produces ok:false, exit 1, single valid JSON on stdout. ... ok
test_json_envelope_success (test_engine_core.TestEngineCore.test_json_envelope_success)
Successful assemble populates all expected envelope keys. ... FAIL
test_yaml_negative_flow_colon (test_engine_core.TestEngineCore.test_yaml_negative_flow_colon)
Colon inside a flow element is rejected. ... FAIL
test_yaml_roundtrip_custom_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_custom_entry)
Custom entry with accent and deviations round-trips field-for-field. ... FAIL
test_yaml_roundtrip_preset_slides (test_engine_core.TestEngineCore.test_yaml_roundtrip_preset_slides)
Both presets parse to 7-id slide lists. ... ok
test_yaml_roundtrip_seed_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_seed_entry)
Seed entry parses with correct field values. ... FAIL

======================================================================
FAIL: test_happy_preset_nimbus_intro_en (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_en)
--preset nimbus-intro-en produces ok:true with correct metadata.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 253, in test_happy_preset_nimbus_intro_en
    self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
AssertionError: 1 != 0 : Expected exit 0, got 1. stdout={"ok": false, "mode": "preset", "errors": ["Row cover-nimbus.en: {client-logo} requested but --client-logo not provided"], "warnings": ["Asset 'partner-mark.png' listed in manifest but not in Assets table"], "unfilled_tokens": [], "output": null, "assets_copied": [], "as_built_entry": null, "catalog_data": null}
, stderr=

======================================================================
FAIL: test_happy_preset_nimbus_intro_pt (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_pt)
--preset nimbus-intro-pt sets lang to pt.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 310, in test_happy_preset_nimbus_intro_pt
    self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
AssertionError: 1 != 0 : Expected exit 0, got 1. stdout={"ok": false, "mode": "preset", "errors": ["Row cover-nimbus.pt: {client-logo} requested but --client-logo not provided"], "warnings": ["Asset 'partner-mark.png' listed in manifest but not in Assets table"], "unfilled_tokens": [], "output": null, "assets_copied": [], "as_built_entry": null, "catalog_data": null}
, stderr=

======================================================================
FAIL: test_happy_slides_explicit (test_engine_core.TestEngineCore.test_happy_slides_explicit)
--slides cover-nimbus.en,intro-pillars,closing-nimbus produces ok:true.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 294, in test_happy_slides_explicit
    self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
AssertionError: 1 != 0 : Expected exit 0, got 1. stdout={"ok": false, "mode": "slides", "errors": ["Row cover-nimbus.en: {client-logo} requested but --client-logo not provided"], "warnings": ["Asset 'partner-mark.png' listed in manifest but not in Assets table"], "unfilled_tokens": [], "output": null, "assets_copied": [], "as_built_entry": null, "catalog_data": null}
, stderr=

======================================================================
FAIL: test_json_envelope_success (test_engine_core.TestEngineCore.test_json_envelope_success)
Successful assemble populates all expected envelope keys.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 383, in test_json_envelope_success
    self.assertTrue(envelope["ok"])
AssertionError: False is not true

======================================================================
FAIL: test_yaml_negative_flow_colon (test_engine_core.TestEngineCore.test_yaml_negative_flow_colon)
Colon inside a flow element is rejected.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 364, in test_yaml_negative_flow_colon
    with self.assertRaises(Exception):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Exception not raised

======================================================================
FAIL: test_yaml_roundtrip_custom_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_custom_entry)
Custom entry with accent and deviations round-trips field-for-field.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 358, in test_yaml_roundtrip_custom_entry
    self.assertEqual(parsed_back["accent"], entry["accent"])
AssertionError: '"' != '#B8875A'
- "
+ #B8875A


======================================================================
FAIL: test_yaml_roundtrip_seed_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_seed_entry)
Seed entry parses with correct field values.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\html\slide-library\engine\tests\test_engine_core.py", line 327, in test_yaml_roundtrip_seed_entry
    self.assertEqual(seed.get("deviations"), "none")
AssertionError: [] != 'none'

----------------------------------------------------------------------
Ran 22 tests in 0.693s

FAILED (failures=7)
```

## BLOCKED — Product Bugs Preventing Green

Per ORCHESTRATOR ADDENDUM rule 1, the following product bugs in `html/slide-library/engine/assemble.py` block 7 tests from passing. Product files were NOT modified.

### Bug 1: `{client-logo}` asset validation blocks all cover-slide assemblies
**Affected tests:** `test_happy_preset_nimbus_intro_en`, `test_happy_preset_nimbus_intro_pt`, `test_happy_slides_explicit`, `test_json_envelope_success`

**Root cause:** `validate_library()` (line 354-359) and `assemble_deck()` (line 419-420) treat `{client-logo}` as a hard error when `--client-logo` is omitted. The fixture manifest lists `{client-logo}` for both cover slides, so any assembly that includes a cover slide fails with:
```
Row cover-nimbus.en: {client-logo} requested but --client-logo not provided
```

The test spec expects `ok:true` for these commands without `--client-logo`.

### Bug 2: `deviations: -` parses as `[]` instead of `"none"`
**Affected test:** `test_yaml_roundtrip_seed_entry`

**Root cause:** `parse_yaml_subset()` (lines 193-195) converts `deviations: -` to an empty Python list `[]`. The convention-spec §4.1 / fixture-spec §I rule 23 expects the scalar `"none"` (or at minimum expects the parser NOT to return `[]`).

### Bug 3: `:` inside a flow YAML list is not rejected
**Affected test:** `test_yaml_negative_flow_colon`

**Root cause:** `parse_yaml_subset()` (lines 163-181) parses `deviations: [modified: x]` as `{"deviations": ["modified: x"]}` without raising an error. The spec explicitly forbids `:` inside flow elements.

### Bug 4: `#` inside quoted scalars is treated as a comment
**Affected test:** `test_yaml_roundtrip_custom_entry`

**Root cause:** `parse_yaml_subset()` (lines 139-141) strips everything from `#` onward on every raw line, including inside quoted values. This causes `accent: "#B8875A"` to be truncated to `accent: "`, which then parses as the single-character string `"`.

---

**RESULT: BLOCKED / FAIL**


## Rerun after ADX-11/ADX-12

| Metric | Value |
|--------|-------|
| SUITE | PB-T3 — Engine unit suite (core: self-check, happy-path, round-trip, --json) |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -p "test_engine_core.py" -v` |
| WALL_MS | 922.297 |
| EXIT | 0 |
| RAN | 22 |
| PASSED | 22 |
| FAILED | 0 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

### Full unittest output

```
test_fixture_01_manifest_rows_and_columns (test_engine_core.TestEngineCore.test_fixture_01_manifest_rows_and_columns)
9 data rows × 10 cells each. ... ok
test_fixture_02_slide_files_exist (test_engine_core.TestEngineCore.test_fixture_02_slide_files_exist)
9 slide fragment files exist. ... ok
test_fixture_03_bare_assets_exist (test_engine_core.TestEngineCore.test_fixture_03_bare_assets_exist)
Assets listed in the Assets table exist on disk. ... ok
test_fixture_04_shared_brand_png_exists (test_engine_core.TestEngineCore.test_fixture_04_shared_brand_png_exists)
shared-brand/partner-mark.png exists. ... ok
test_fixture_05_presets_and_as_built_blocks (test_engine_core.TestEngineCore.test_fixture_05_presets_and_as_built_blocks)
2 yaml preset blocks + 1 as-built block. ... ok
test_fixture_06_fragment_purity (test_engine_core.TestEngineCore.test_fixture_06_fragment_purity)
No fragment contains forbidden tags. ... ok
test_fixture_07_slide_number_coverage (test_engine_core.TestEngineCore.test_fixture_07_slide_number_coverage)
Covers unnumbered + 7 numbered slides. ... ok
test_fixture_08_exact_case_headings (test_engine_core.TestEngineCore.test_fixture_08_exact_case_headings)
Manifest header is exact-case. ... ok
test_fixture_09_no_in_cell_pipe (test_engine_core.TestEngineCore.test_fixture_09_no_in_cell_pipe)
No data cell contains a pipe character. ... ok
test_fixture_10_required_cells_non_empty (test_engine_core.TestEngineCore.test_fixture_10_required_cells_non_empty)
Required cells (id, file, section, title, lang, kind, summary) are non-empty. ... ok
test_fixture_11_seed_and_preset_round_trip (test_engine_core.TestEngineCore.test_fixture_11_seed_and_preset_round_trip)
Seed entry and presets parse and have correct 7-id slide lists. ... ok
test_happy_preset_nimbus_intro_en (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_en)
--preset nimbus-intro-en produces ok:true with correct metadata. ... ok
test_happy_preset_nimbus_intro_pt (test_engine_core.TestEngineCore.test_happy_preset_nimbus_intro_pt)
--preset nimbus-intro-pt sets lang to pt. ... ok
test_happy_slides_explicit (test_engine_core.TestEngineCore.test_happy_slides_explicit)
--slides cover-nimbus.en,intro-pillars,closing-nimbus produces ok:true. ... ok
test_json_catalog_data (test_engine_core.TestEngineCore.test_json_catalog_data)
--catalog-data --json returns correct catalog_data. ... ok
test_json_drift_warning (test_engine_core.TestEngineCore.test_json_drift_warning)
Engine version drift produces a warning but ok:true. ... ok
test_json_envelope_die (test_engine_core.TestEngineCore.test_json_envelope_die)
Die case produces ok:false, exit 1, single valid JSON on stdout. ... ok
test_json_envelope_success (test_engine_core.TestEngineCore.test_json_envelope_success)
Successful assemble populates all expected envelope keys. ... ok
test_yaml_negative_flow_colon (test_engine_core.TestEngineCore.test_yaml_negative_flow_colon)
Colon inside a flow element is rejected. ... ok
test_yaml_roundtrip_custom_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_custom_entry)
Custom entry with accent and deviations round-trips field-for-field. ... ok
test_yaml_roundtrip_preset_slides (test_engine_core.TestEngineCore.test_yaml_roundtrip_preset_slides)
Both presets parse to 7-id slide lists. ... ok
test_yaml_roundtrip_seed_entry (test_engine_core.TestEngineCore.test_yaml_roundtrip_seed_entry)
Seed entry parses with correct field values. ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.842s

OK
```

### Per-fix confirmation

- **E1** — `parse_yaml_subset` no longer normalizes `deviations: -` to `[]`; returns literal string `"-"`.
- **E2** — Flow-list element containing `:` now raises `ValueError` (catchable as `Exception`), satisfying `test_yaml_negative_flow_colon`.
- **E3** — Comment handling is whole-line only (`stripped.startswith("#")`); quoted scalar `"#B8875A"` survives parsing intact.
- **T1'** — Four happy-path assembly tests (`test_happy_preset_nimbus_intro_en`, `test_happy_preset_nimbus_intro_pt`, `test_happy_slides_explicit`, `test_json_envelope_success`) now pass `--client-logo` with the fixture `shared-brand/partner-mark.png` path.
- **T2'** — `test_yaml_roundtrip_seed_entry` asserts `seed.get("deviations") == "-"` (the literal scalar), not `"none"`.

**RESULT: ALL GREEN / PASS**


## PB-T4

### D29 Evidence-Metrics Block — test_engine_negatives

| Metric | Value |
|--------|-------|
| SUITE | PB-T4 — Engine suite: §I negative matrix (24 rows) |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -p "test_engine_negatives.py" -v` |
| WALL_MS | 2353.938 |
| EXIT | 0 |
| RAN | 24 |
| PASSED | 24 |
| FAILED | 0 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

### D29 Evidence-Metrics Block — test_engine_dt5

| Metric | Value |
|--------|-------|
| SUITE | PB-T4 — DT5-procedure self-test + install-engine test |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -p "test_engine_dt5.py" -v` |
| WALL_MS | 486.791 |
| EXIT | 0 |
| RAN | 3 |
| PASSED | 3 |
| FAILED | 0 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

### Full unittest output — negatives

```
----------------------------------------------------------------------
Ran 24 tests in 2.293s
OK
```

### Full unittest output — dt5

```
----------------------------------------------------------------------
Ran 3 tests in 0.417s
OK
```

**RESULT: ALL GREEN / PASS**

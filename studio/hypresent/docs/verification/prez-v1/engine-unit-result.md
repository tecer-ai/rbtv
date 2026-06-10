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

## Writer fix (ADX-13)

**Fix:** `write_yaml_subset` in `assemble.py` now dispatches by value type instead of by key name:
- `list` → block-list emission (`key:` followed by `  - item` lines)
- `str` / scalar → single mapping line (`key: value`)
- Removed the special-casing for `key == "deviations"` (which mis-handled the string `'-'` as an iterable) and `key == "engine_version"` (which forced quoting).

**Regression test:** Added `test_yaml_writer_deviations_string_scalar` to `test_engine_core.py`. It verifies:
- `deviations: "-"` emits as the literal scalar line `deviations: -`
- `write→parse→write` round-trips field-for-field for both string and list values.

### D29 Evidence-Metrics Block — full engine suite (ADX-13)

| Metric | Value |
|--------|-------|
| SUITE | PB-T3 / PB-T4 / DT5 — Full engine unit suite (ADX-13 writer fix) |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -v` |
| WALL_MS | 3779.0 |
| EXIT | 0 |
| RAN | 50 |
| PASSED | 50 |
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
test_yaml_writer_deviations_string_scalar (test_engine_core.TestEngineCore.test_yaml_writer_deviations_string_scalar)
ADX-13: string deviations '-' emits as scalar; list deviations as block list. ... ok
test_dt5_procedure_self_test (test_engine_dt5.TestEngineDT5.test_dt5_procedure_self_test)
Re-assemble seed twice; assert order, skeleton, assets, tokens. ... ok
test_install_engine (test_engine_dt5.TestEngineDT5.test_install_engine)
install-engine copies assemble.py and syncs engine_version to 1.0. ... ok
test_install_engine_missing_library_json (test_engine_dt5.TestEngineDT5.test_install_engine_missing_library_json)
Missing target library.json → exit 1. ... ok
test_negative_01_delete_theme_css (test_engine_negatives.TestEngineNegatives.test_negative_01_delete_theme_css)
Rule 1 — Delete theme.css → ERROR containing 'theme.css not found'. ... ok
test_negative_02a_lowercase_slides_heading (test_engine_negatives.TestEngineNegatives.test_negative_02a_lowercase_slides_heading)
Rule 2a — Lowercase ## Slides → ERROR with slides/heading message. ... ok
test_negative_02b_header_id_to_Id (test_engine_negatives.TestEngineNegatives.test_negative_02b_header_id_to_Id)
Rule 2b — Rename header id→Id → ERROR 'header mismatch'. ... ok
test_negative_04_delete_one_cell (test_engine_negatives.TestEngineNegatives.test_negative_04_delete_one_cell)
Rule 4 — Delete one cell from a slide row (→9 cells) → ERROR expected 10. ... ok
test_negative_05_pipe_in_summary (test_engine_negatives.TestEngineNegatives.test_negative_05_pipe_in_summary)
Rule 5 — Insert literal | into cover-nimbus.en summary → ERROR. ... ok
test_negative_06_blank_title_cell (test_engine_negatives.TestEngineNegatives.test_negative_06_blank_title_cell)
Rule 6 — Blank intro-pillars title cell → ERROR empty required. ... ok
test_negative_07_kind_Template (test_engine_negatives.TestEngineNegatives.test_negative_07_kind_Template)
Rule 7 — Set cover-nimbus.pt kind to Template → ERROR invalid kind. ... ok
test_negative_08_lang_EN (test_engine_negatives.TestEngineNegatives.test_negative_08_lang_EN)
Rule 8 — Set intro-pillars lang to EN → ERROR invalid lang. ... ok
test_negative_09_section_proofs (test_engine_negatives.TestEngineNegatives.test_negative_09_section_proofs)
Rule 9 — Set proof-metrics section to proofs → ERROR unknown section. ... ok
test_negative_10_duplicate_id (test_engine_negatives.TestEngineNegatives.test_negative_10_duplicate_id)
Rule 10 — Duplicate intro-pillars id → ERROR duplicate id. ... ok
test_negative_11_delete_fragment_file (test_engine_negatives.TestEngineNegatives.test_negative_11_delete_fragment_file)
Rule 11 — Delete slides/proof-metrics.html → ERROR fragment missing. ... ok
test_negative_12_style_block_in_fragment (test_engine_negatives.TestEngineNegatives.test_negative_12_style_block_in_fragment)
Rule 12 — Add <style> inside intro-pillars.html → ERROR forbidden tag. ... ok
test_negative_13_delete_asset_file (test_engine_negatives.TestEngineNegatives.test_negative_13_delete_asset_file)
Rule 13 — Delete assets/nimbus-mark.png → ERROR asset not found. ... ok
test_negative_14_root_asset_null_extra (test_engine_negatives.TestEngineNegatives.test_negative_14_root_asset_null_extra)
Rule 14 — Add @root/x.png with extra_asset_root: null → ERROR. ... ok
test_negative_15_no_client_logo (test_engine_negatives.TestEngineNegatives.test_negative_15_no_client_logo)
Rule 15 — Assemble {client-logo} cover without --client-logo → ERROR. ... ok
test_negative_16_comma_in_asset_filename (test_engine_negatives.TestEngineNegatives.test_negative_16_comma_in_asset_filename)
Rule 16 — Comma inside asset filename → ERROR asset not found. ... ok
test_negative_17_remove_asset_table_row (test_engine_negatives.TestEngineNegatives.test_negative_17_remove_asset_table_row)
Rule 17 — Remove nimbus-mark.png from Assets table (file stays) → WARNING, proceeds. ... ok
test_negative_18_delete_slides_marker (test_engine_negatives.TestEngineNegatives.test_negative_18_delete_slides_marker)
Rule 18 — Delete <!-- {{SLIDES}} --> from base.html → ERROR missing marker. ... ok
test_negative_19_delete_theme_css_duplicate (test_engine_negatives.TestEngineNegatives.test_negative_19_delete_theme_css_duplicate)
Rule 19 — Delete theme.css (covered by rule 1) → ERROR theme.css not found. ... ok
test_negative_20_convention_2_0 (test_engine_negatives.TestEngineNegatives.test_negative_20_convention_2_0)
Rule 20 — convention_version: 2.0 → ERROR unsupported major version. ... ok
test_negative_21_convention_1_9 (test_engine_negatives.TestEngineNegatives.test_negative_21_convention_1_9)
Rule 21 — convention_version: 1.9 → WARNING, assembly proceeds. ... ok
test_negative_22_engine_version_9_9 (test_engine_negatives.TestEngineNegatives.test_negative_22_engine_version_9_9)
Rule 22 — engine_version: 9.9 → WARNING, assembly proceeds. ... ok
test_negative_23_flow_colon (test_engine_negatives.TestEngineNegatives.test_negative_23_flow_colon)
Rule 23 — Hand-write deviations: [modified: x] → parse error on colon in flow. ... ok
test_negative_24_check_unfilled_seed (test_engine_negatives.TestEngineNegatives.test_negative_24_check_unfilled_seed)
Rule 24 — Assemble seed, --check it → exit 1 listing template tokens. ... ok

----------------------------------------------------------------------
Ran 50 tests in 3.779s

OK
```

**RESULT: ALL GREEN / PASS**


## Writer fix #2 (empty-list sentinel)

**Fix:** `write_yaml_subset` in `assemble.py` now emits the `-` sentinel scalar for empty list values:
- Empty `list` → `key: -` (scalar line)
- Non-empty `list` → block-list emission (`key:` followed by `  - item` lines)
- `str` / scalar → single mapping line (`key: value`)

**Regression test:** Added `test_yaml_writer_empty_list_sentinel` to `test_engine_core.py`. It verifies:
- `{"deviations": []}` emits the literal scalar line `deviations: -`
- `write→parse→write` round-trips field-for-field for empty-list values.

### D29 Evidence-Metrics Block — full engine suite (empty-list sentinel fix)

| Metric | Value |
|--------|-------|
| SUITE | PB-T3 / PB-T4 / DT5 — Full engine unit suite (empty-list sentinel fix) |
| CMD | `python -m unittest discover -s html/slide-library/engine/tests -v` |
| WALL_MS | 4130.0 |
| EXIT | 0 |
| RAN | 51 |
| PASSED | 51 |
| FAILED | 0 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

### Tecer round-trip (all 12 as-built entries)

| Metric | Value |
|--------|-------|
| TARGET | `C:/Users/henri/Documents/second-brain/5-workbench/tecer-biz/slide-library/as-built.md` |
| BLOCKS | 12 |
| ROUNDTRIP | 12/12 |

**RESULT: ALL GREEN / PASS**

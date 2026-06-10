# PB-T4 — Engine suite: §I negative matrix + DT5 self-test + install-engine test

## Full run output

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
Ran 49 tests in 3.363s

OK
```

## D29 Evidence-Metrics Block

| Metric | Value |
|--------|-------|
| SUITE | PB-T4 — Full engine suite (core + negatives + DT5 + install-engine) |
| CMD | `python -m unittest discover -s tests -v` |
| WALL_MS | 4039.117 |
| EXIT | 0 |
| RAN | 49 |
| PASSED | 49 |
| FAILED | 0 |
| ERRORS | 0 |
| SKIPPED | 0 |
| SKIPPED_LINES_COUNT | 0 |
| SKIP_REASONS | (none) |

## Deliverables

### (a) §I negative-matrix rules implemented as programmatic fixture mutations

All 24 rows of fixture-spec §I are implemented as individual test methods in `test_engine_negatives.py`:

| § 8 rule | Test method name |
|---|---|
| 1 | `test_negative_01_delete_theme_css` |
| 2a | `test_negative_02a_lowercase_slides_heading` |
| 2b | `test_negative_02b_header_id_to_Id` |
| 4 | `test_negative_04_delete_one_cell` |
| 5 | `test_negative_05_pipe_in_summary` |
| 6 | `test_negative_06_blank_title_cell` |
| 7 | `test_negative_07_kind_Template` |
| 8 | `test_negative_08_lang_EN` |
| 9 | `test_negative_09_section_proofs` |
| 10 | `test_negative_10_duplicate_id` |
| 11 | `test_negative_11_delete_fragment_file` |
| 12 | `test_negative_12_style_block_in_fragment` |
| 13 | `test_negative_13_delete_asset_file` |
| 14 | `test_negative_14_root_asset_null_extra` |
| 15 | `test_negative_15_no_client_logo` |
| 16 | `test_negative_16_comma_in_asset_filename` |
| 17 | `test_negative_17_remove_asset_table_row` |
| 18 | `test_negative_18_delete_slides_marker` |
| 19 | `test_negative_19_delete_theme_css_duplicate` |
| 20 | `test_negative_20_convention_2_0` |
| 21 | `test_negative_21_convention_1_9` |
| 22 | `test_negative_22_engine_version_9_9` |
| 23 | `test_negative_23_flow_colon` |
| 24 | `test_negative_24_check_unfilled_seed` |

### (b) DT5 §4.4 5-check procedure self-test on the seeded entry

Implemented in `test_engine_dt5.TestEngineDT5.test_dt5_procedure_self_test`:
- Check 1: Order identity — both re-assembled decks' `as_built_entry["slides"]` exactly equal the 7 seed slide IDs.
- Check 2: Per-slide skeleton equality — HTML parsed into `(tag, sorted(classes))` tuples in document order; the two reproduction skeletons are identical (structural self-consistency, no committed golden).
- Check 3: Asset parity — the two `assets/` filename sets are equal; every file exists on disk; every `src="assets/..."` reference in the HTML resolves to a file in the assets directory.
- Check 4: Clean token report — `--check` on the reproduction reports exit 1 and the residual token set equals the expected template tokens (cover/problem/proof tokens plus the comment-held `{{TOKEN}}`).
- Check 5: Headed render sanity — deferred per convention-spec §4.4 (NOT in this task).

### (c) install-engine.py test

Implemented in `test_engine_dt5.TestEngineDT5`:
- `test_install_engine` — copies fixture to temp lib, sets `engine_version` to `"0.9"`, runs `install-engine.py --library {tmplib}`, asserts target `assemble.py` is byte-equal to source and `library.json` `engine_version` is synced to `"1.0"`.
- `test_install_engine_missing_library_json` — runs against a tempdir with no `library.json`, asserts exit code 1.

## Disclosure

No files were modified beyond the two test files created for this task.

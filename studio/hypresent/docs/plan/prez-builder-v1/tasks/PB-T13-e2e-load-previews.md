You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding): record measured WALL_MS + EXIT + ran/passed/failed/SKIPPED + SKIPPED_LINES_COUNT + each skip's exact reason string. Implausible WALL_MS (browser e2e <1s) or unexpected skip → BUG section + STOP.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T13 — e2e: library-load suite + previews suite

## Objective
Two Playwright suites verifying the library-load+browse+filter flow (port 8802) and the IO-gated previews (port 8803). REAL INPUT ONLY; measured-outcome assertions.

## FILE ALLOWLIST
- ✚ create `html/hypresent/tests/e2e/test_pb2_library_load.py`
- ✚ create `html/hypresent/tests/e2e/test_pb3_previews.py`
- ✗ do NOT edit helpers or product files.

## Reuse (from PB-T12 + the live harness)
`conftest_helpers` (start_server/stop_server/post_json/doc_eval) and `builder_helpers` (set_fake_folder, e2e_lib_path, make_temp_library, pick_library_ui). The e2e fixture library is at `tests/e2e/fixtures/builder-lib/` with the engine vendored in. Use the standard suite scaffold from PB-T12 (setUpClass starts the server with `test_dialog=True`, launches headless chromium). Ports: PB2=8802, PB3=8803.

## test_pb2_library_load.py (build-spec S-B3/S-B4; test-plan §2.2)
1. `test_pick_and_render_groups`: `pick_library_ui(page, base, builder_helpers.e2e_lib_path())`; assert `#browse-groups` has ≥2 `.browse-group` blocks in the library's `library.json` section order (read the order via `H.post_json(base, "/api/library-load", {"path": lib})` and compare the rendered group labels to `catalog_data.sections`); assert `.slide-card` count == the number of slides.
2. `test_language_filter`: after load, count visible `.slide-card`s; select a specific lang in `#lang-filter`; assert language-neutral ids (no `.{lang}` suffix) stay visible and a `.{lang}`-suffixed card whose lang ≠ the selection hides. MEASURED: visible-count before vs after differs as expected. (convention-spec §2.2 / §8.1 #14 filter semantics.)
3. `test_invalid_library_state`: make a broken temp lib (copy `builder-lib` to a tempdir, DELETE its `theme.css`, ensure its `assemble.py` is present); `set_fake_folder(base, broken_path)`; click `#pick-library-btn`; assert a `.builder-invalid` state appears listing an error mentioning `theme.css` and NO `.browse-group` rendered. (build-spec S-B11.2.)
4. `test_library_load_envelope`: `status, data = H.post_json(base, "/api/library-load", {"path": lib})`; assert `data` has `catalog_data` with `sections`, `slides`, `presets` (the server passes the engine envelope through — ADX-2).

## test_pb3_previews.py (build-spec S-B5; test-plan §2.3)
1. `test_io_gated_mount`: load the library; assert NOT all card iframes have a non-empty `srcdoc` initially (`page.eval_on_selector_all('.slide-thumb-wrapper iframe', 'els => els.filter(e => e.srcdoc && e.srcdoc.length>0).length')` is less than the total card count on a tall page). Scroll a specific card into view (`card.scroll_into_view_if_needed()`); wait; assert THAT card's iframe now has a non-empty `srcdoc` and `dataset.mounted === 'true'` (the IO gate fired). N≥2: repeat for a second card lower in the list.
2. `test_renderable_unit_no_runtime`: after a card mounts, read its `srcdoc`; assert it contains a known theme class (e.g. `.slide` or a class from the fixture theme) AND the fragment markup; assert it does NOT contain `runtime-main.js` (previews never inject the editor runtime — build-spec S-B5.2).
3. `test_mount_cap`: if the fixture lib has MORE fragments than the MOUNT_CAP, scroll through all and assert the count of iframes with non-empty `srcdoc` never exceeds the cap. CONDITIONAL SKIP with the exact reason string if the fixture has fewer fragments than the cap (D25): `f"fixture lib has {n} fragments < MOUNT_CAP — cap unverifiable here"`.
4. `test_no_inview_blanking` (build-spec S-B5.4 / RV2-5): with a fixture lib exceeding the MOUNT_CAP, perform a long top-to-bottom scroll in ≥3 steps; AT EACH step, collect every `.slide-thumb-wrapper iframe` whose bounding rect currently intersects the viewport (`page.eval_on_selector_all` with an in-viewport rect test) and assert EVERY such in-view iframe has a non-empty `srcdoc` — eviction must NEVER blank an in-view preview (it evicts LRU among non-intersecting only). MEASURED: at each of the ≥3 positions, the in-view set is non-empty and all have `srcdoc.length>0`. CONDITIONAL SKIP with the exact reason string if the fixture has fewer fragments than the cap (eviction never triggers): `f"fixture lib has {n} fragments < MOUNT_CAP — eviction never triggers, in-view-blanking unverifiable here"`.
5. `test_scale_applied`: assert a `.slide-thumb-wrapper` has computed `overflow: hidden` and its iframe's computed `transform` includes `scale(` (build-spec S-B5.3).

For scrolling + reading computed styles, use Playwright `page.eval_on_selector`/`eval_on_selector_all` and `locator.scroll_into_view_if_needed()`. Mounting is async (fetch + srcdoc) — use `page.wait_for_function` with a per-card predicate, not a fixed sleep where avoidable; a short `page.wait_for_timeout(300)` after scroll is acceptable to let the IO callback + fetch resolve.

## Acceptance criteria
Run each suite: `python -m unittest tests.e2e.test_pb2_library_load -v` and `python -m unittest tests.e2e.test_pb3_previews -v` (cwd = `html/hypresent`). ALL pass (test_mount_cap may SKIP with the exact reason). Record the D29 block for BOTH suites. WALL_MS ≥1s each.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/e2e-load-previews-result.md`: the D29 block for both suites.

DONE means: both suites created + green (cap skip allowed), D29 evidence written. Failure/implausible metric → BLOCKED/BUG + stop.

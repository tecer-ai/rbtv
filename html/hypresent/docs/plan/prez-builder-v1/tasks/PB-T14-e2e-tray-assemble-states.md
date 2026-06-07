You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding): record measured WALL_MS + EXIT + ran/passed/failed/SKIPPED + SKIPPED_LINES_COUNT + each skip's exact reason string. Implausible WALL_MS (browser e2e <1s) or unexpected skip → BUG section + STOP.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T14 — e2e: tray+reorder + assemble+handoff + states

## Objective
Three Playwright suites: the drag-reorder tray (port 8804, REAL pointer input — the highest-risk suite), assemble+editor-handoff (8805), and error/empty/invalid states (8806).

## FILE ALLOWLIST
- ✚ create `html/hypresent/tests/e2e/test_pb4_tray_reorder.py`
- ✚ create `html/hypresent/tests/e2e/test_pb5_assemble_handoff.py`
- ✚ create `html/hypresent/tests/e2e/test_pb6_states.py`
- ✗ do NOT edit helpers or product files (addendum rule 1 — if a product bug blocks a test, write BLOCKED evidence and stop).

## Reuse
`conftest_helpers` + `builder_helpers` (set_fake_folder, e2e_lib_path, make_temp_library, pick_library_ui) + the standard scaffold from PB-T12. Ports: PB4=8804, PB5=8805, PB6=8806. All start the server with `test_dialog=True`.

## REAL-INPUT mandate + the live pattern to copy (from test_f2_select_guides.py)
NO `dispatchEvent`, NO synthetic event injection, NO skip-as-green. Use `page.mouse.down/move/up` for the drag (these fire `pointerdown/pointermove/pointerup` — exactly what the hand-rolled sorter listens for; research-01-ui §1.1). Assert MEASURED OUTCOMES (the model/DOM order CHANGED), not just that a ghost appeared. The live suite computes on-screen coordinates like this — reuse the shape:
```python
def screen_xy_of(page, selector):
    fb = page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); ... }")  # for iframe elements
    # For the BUILDER (no iframe — the tray is in the top document), use the element rect directly:
def rect_of(page, selector):
    return page.evaluate("(sel)=>{const e=document.querySelector(sel); const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};}", selector)
```
(The builder tray lives in the TOP document, NOT inside an iframe, so use `rect_of` directly — simpler than the editor's iframe-offset math.)

## test_pb4_tray_reorder.py (build-spec S-B6/S-B7/S-B8; test-plan §2.4)
1. `test_click_to_tag`: `pick_library_ui(...)`; REAL-click a `.slide-card`; assert a `.tray-row` appears whose `data-slide-id` === the clicked card's `data-slide-id` (D30 selected==target — assert the tray row id IS the targeted card's id). Tag 3 distinct cards; assert 3 ordered `.tray-row`s numbered 1,2,3.
2. `test_remove_row`: click a row's `.tray-remove`; assert it is gone and remaining rows renumber.
3. `test_preset_preload`: select a preset in `#preset-select`; assert `.tray-row` ids in order equal the preset's `slides` (read the preset via `H.post_json(base,"/api/library-load",{path})` → `catalog_data.presets`).
4. `test_drag_reorder_real_mouse` (THE key test): tag ≥3 rows; record the order via `page.eval_on_selector_all('.tray-row', 'els=>els.map(e=>e.dataset.slideId)')`. Grab row 0 at its on-screen centre (`rect_of('.tray-row:nth-child(1)')`, hittability guard), `page.mouse.move(cx,cy)`, `page.mouse.down()`, then `page.mouse.move` in ≥2 steps DOWN past row 2's midpoint (the two-move requirement — research-01-ui §1.1), `page.mouse.up()`. Assert the new order (`eval_on_selector_all`) is the EXPECTED permutation (row 0 moved past row 1) — a MEASURED outcome (`assertNotEqual(before_order, after_order)` AND assert the dragged id is now at the expected later index). N≥2: do a second drag and assert again. D30: assert the row whose position changed is the one the pointer grabbed.
5. `test_no_native_dnd`: read `tray-sorter.js`'s on-page behavior indirectly — assert that dragging works via pointer (covered by test 4); additionally assert the tray rows do NOT have a `draggable="true"` attribute (`page.eval_on_selector_all('.tray-row','els=>els.every(e=>e.getAttribute("draggable")!=="true")')` is true). (build-spec S-B8.2.)
6. `test_drag_escape_cancel` (build-spec S-B8.1a / RV2-6) — REAL key press mid-drag: tag ≥3 rows; record `before_order` via `eval_on_selector_all('.tray-row','els=>els.map(e=>e.dataset.slideId)')`. Grab row 0 at its on-screen centre (`rect_of`), `page.mouse.move(cx,cy)`, `page.mouse.down()`, `page.mouse.move` in ≥2 steps DOWN past row 1's midpoint (so the DOM order visibly changes mid-drag), THEN `page.keyboard.press('Escape')` BEFORE `mouse.up`. Assert the order is RESTORED: `after_escape_order == before_order` (MEASURED). Then `page.mouse.up()` and assert the order is STILL `before_order` (Escape won, not the late pointerup) AND no `.tray-drag-ghost` class remains. N≥2 (a second drag+Escape).
7. `test_two_item_reorder` (build-spec S-B8 / RV2-8): tag EXACTLY 2 cards; record `before_order`; drag row 0 past row 1's midpoint (`mouse.down`, ≥2 `mouse.move`, `mouse.up`); assert the two rows SWAPPED — `after_order == list(reversed(before_order))` (MEASURED; the minimal permutation / common off-by-one site).
8. `test_scroll_during_drag` (build-spec S-B8 / RV2-8): use a fixture/tray tall enough that `#tray-list` scrolls (tag enough rows, or the suite skips with an exact reason if the tray cannot be made scrollable). Record `before_order`; begin a drag (`mouse.down` on a row + one `mouse.move`); scroll the tray container mid-drag (set `#tray-list.scrollTop` or `page.mouse.wheel(0, dy)` over the tray); continue with ≥2 more `mouse.move`s to a target row's current on-screen midpoint (read a FRESH `rect_of` AFTER the scroll, since the sorter recomputes insertion from live rects); `mouse.up`. Assert the resulting order is the expected permutation for the final pointer position (MEASURED, `assertNotEqual(before_order, after_order)` plus the dragged id at the expected index) — guards the captured-pointer-vs-shifting-rects case. CONDITIONAL SKIP with the exact reason string if the tray cannot be made to scroll.

If the sorter is genuinely undriveable via real mouse (e.g. rows not hittable), do NOT mark green — write a BLOCKED section with the exact blocker (this is the friction the testability-gap registry tracks; the orchestrator handles it).

## test_pb5_assemble_handoff.py (build-spec S-B9.4/S-B10; test-plan §2.5)
1. `test_assemble_writes_deck`: use `make_temp_library()` (a temp copy with the engine) so assembling is safe. Load it via the fake folder; tag a known order; pick a destination via the folder dialog seam (`set_fake_folder` for `#pick-dest-btn` returns a temp OUTPUT folder distinct from the library) and type a filename; click `#assemble-btn`; wait for success in `#builder-status`. Assert ON DISK: the deck exists at `{outfolder}/{name}.html`; a sibling `{outfolder}/assets/` holds copied assets; the temp library's `as-built.md` gained a new entry whose `slides` matches the tagged order (read the file).
2. `test_editor_handoff` (real): after a successful assemble, the builder navigates to `/app/?file=<deck>`; assert `page.url` contains `/app/?file=`; `H.wait_runtime_ready(page)` succeeds; assert a known fragment class from the deck is present in the editor iframe (`H.doc_eval(page, "return !!doc.querySelector('.slide');")`). This exercises the smallest-change handoff end-to-end (build-spec S-B10.3).
2b. `test_handoff_path_encoding` (build-spec S-B10.3 step 1 / RV2-3) — assemble to deck filenames covering the encoding edge cases and hand off for EACH, asserting the deck opens: (a) the accent/space case (deck filename e.g. `deck final ção` → `...ção.html`); (b) the `%`-bearing case (deck filename e.g. `deck 100%` → `deck 100%.html`). For each: set the destination + filename, assemble, then on success assert `page.url` contains `/app/?file=`, `H.wait_runtime_ready(page)` succeeds, and a known fragment class is present in the editor iframe. The `%` case is the regression guard — the single `URLSearchParams.get()` decode (NO second `decodeURIComponent`) opens it WITHOUT a `URIError`; a double-decode would throw/corrupt and the deck would fail to open. (Use `make_temp_library()` + temp OUTPUT folders so the `%`/accent decks are written safely.)
3. `test_invalid_assemble_passthrough`: force an engine error — inject a bogus id into the tray model (e.g. via the UI: there is no UI for a bogus id, so instead POST `/api/assemble` directly with `slides:["does-not-exist"]` and assert the response `ok:false` with `errors`; AND in the UI, if a way exists to surface it, assert the error banner). At minimum assert the endpoint passthrough returns `ok:false` (build-spec S-B11.4).

## test_pb6_states.py (build-spec S-B11; test-plan §2.6)
1. `test_empty_state`: `page.goto(base+"/app/builder.html")` with NO library picked; assert `#browse-empty` is visible and `#assemble-btn` is disabled.
2. `test_zero_presets`: point at a temp library with zero presets (copy `builder-lib`, blank its `presets.md` `## Presets` body so the engine returns `presets: []`); load it; assert `#preset-select` shows only the `(none)` option; assert tagging from browse still works (click a card → a tray row appears).
3. `test_engine_spawn_error`: point the fake folder at a temp dir that has NO `assemble.py`; click `#pick-library-btn`; assert an error state surfaces (the server returns 500/`error`; the builder shows it) — assert `#builder-status` or `.builder-invalid` shows an error and no `.browse-group`.

## Acceptance criteria
Run each: `python -m unittest tests.e2e.test_pb4_tray_reorder -v`, `... test_pb5_assemble_handoff -v`, `... test_pb6_states -v` (cwd = `html/hypresent`). ALL pass. Record the D29 block for all THREE suites. WALL_MS ≥1s each. Any conditional skip needs an exact reason string.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/e2e-tray-assemble-states-result.md`: the D29 block for all three suites. If the drag test hit friction, record the blocker + workaround used (the orchestrator collects testability gaps).

DONE means: three suites created + green, D29 evidence written. Any failure/implausible metric/undriveable drag → BLOCKED/BUG section + stop (do NOT weaken the real-mouse assertion to pass).

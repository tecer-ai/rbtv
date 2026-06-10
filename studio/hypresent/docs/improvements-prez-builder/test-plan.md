# prez-builder v1 — Test Plan

**Status:** authored 2026-06-06. Companion to `build-spec.md` (S-numbers) and the FROZEN `convention-spec.md` (§N) + `fixture-spec.md` (§I negative matrix). Defines: (1) the engine unit suite (pure Python); (2) the builder e2e suites (Playwright, REAL INPUT ONLY); (3) the DT1–DT5/EX1 done-boundary protocol (HEADED, on the MIGRATED tecer library — distinct from and NOT claimable by the dev suites).

**Mandates baked into EVERY test task (verbatim from learnings-kimi-worker S2.1 / D29 + D14):**
- Every test evidence file records: measured `WALL_MS` (Stopwatch/`time.perf_counter` around the command) + unittest `EXIT` + `SKIPPED_LINES_COUNT` + per-skip reason strings. Implausible metrics (browser e2e <1s, OS-dialog test <1.5s) = auto-reject + tripwired rerun (D29).
- REAL INPUT ONLY: NO `dispatchEvent`, NO synthetic in-page event injection for interactions, NO skip-as-green. Conditional skips are allowed ONLY with an exact reason string (D25 pattern, live `test_f2` skip at line 347). Assertions are MEASURED-OUTCOME (geometry/state deltas), never existence-only where an outcome is checkable (live `test_f2` `assertNotEqual(after, before)` pattern).
- N≥2 repeats where interaction-order-sensitive (D29).
- Hittability guards before clicking targets (live `test_f2` `screen_xy_of` + on-screen-centre click).
- D30 selected==target: wherever a test selects/clicks a target then asserts on "the selected element", assert that the element the UI treats as selected IS the element the test targeted (live `test_f2` ring-candidate match at lines 169-180).

**Ports:** new suites use 8801–8806 (D7-S4). The existing e2e suite occupies two clusters — 8781–8799 AND 8810–8815 (live-verified across `tests/e2e/*.py`; the reviewer's "≤8797"/"≤8799" both undercounted the 8810–8815 cluster, RV2-7). The 8801–8809 band is the free gap the new suites sit in, so there is NO collision; do NOT extend new suites past 8809 (8810+ is taken). Map below.
**Evidence root:** `docs/verification/prez-v1/` (under hypresent, D7-S4). One evidence file per suite run: `docs/verification/prez-v1/{suite}-result.md`.
**Harness:** match the live idioms in `tests/e2e/conftest_helpers.py` — `start_server(port, test_dialog)`, `copy_*`, `post_json`, `set_fake_dialog`, `wait_*`, `doc_eval`. Builder suites add builder-specific helpers in a NEW `tests/e2e/builder_helpers.py` (do NOT edit `conftest_helpers.py` unless a shared helper is genuinely missing — if so, that edit is serialized in the plan).

---

## 1. Engine unit suite (pure Python, NO browser)

Location: `html/slide-library/engine/tests/`. Framework: Python `unittest`. NO Playwright. Runs against the fixture library (`fixture-spec.md`, built verbatim by a task) — the engine's FIRST verification gate (`fixture-spec` purpose statement). Evidence: `docs/verification/prez-v1/engine-unit-result.md`.

### 1.1 Fixture self-check (no engine)
- Implement `fixture-spec §H` (11 structural checks) as a test module run BEFORE the engine tests: 9 data rows × 10 cells; 9 fragment files exist; bare assets exist; `../shared-brand/partner-mark.png` exists; 2 yaml preset blocks + 1 as-built block; fragment purity (no `<head`/`<style`/`<script`/`<html`/`<body`); cover unnumbered + 7 others numbered; exact-case headings; no in-cell pipe + non-empty required; round-trip of seed entry + both presets. Asserts the fixture is structurally valid before the engine exists.

### 1.2 Happy-path assembly (vs the fixture)
- Assemble `--preset nimbus-intro-en --out {tmp}` and assert (engine API or `--json`): 7 slides, correct order, `assets_copied` includes the union of referenced assets (incl. `partner-mark.png` from `@root`, S-A4.4), sequential `{{N}}` 1-based across numbered slides, `theme.css` inlined, unfilled `{{TOKEN}}`s = exactly the template tokens in the composed templates, and an as-built entry appended (S-A9.6) with resolved `lang/title/preset/slides`.
- Assemble `--slides cover-nimbus.en,intro-pillars,closing-nimbus --out {tmp}` (no preset) and assert order + `default_lang` fallback (S-A5.2 — `en`).
- `--preset nimbus-intro-pt` → resolved `lang: pt` (preset lang, S-A5.1).

### 1.3 §I negative-case matrix (programmatic mutations)
- Implement EVERY row of `fixture-spec §I` (24 rows) as a test: COPY the valid fixture to a tempdir, apply the in-memory/temp mutation, run the engine, assert the verdict + message pattern (regex) from the matrix. ERROR rows → exit 1 (`die()`/accumulated, S-A6.1a) with the pattern; WARNING rows (17, 21, 22) → proceeds AND emits the warning; report rows (24) → exit 1 listing tokens. NO broken library is left on disk (mutate→assert→discard, `fixture-spec §I`). Each maps to a `convention-spec §8` rule (S-A6.1).
- Cover specifically the NEW-engine-work rows the live engine lacks (`fixture-spec §I` note): purity (12), library.json checks (20-22), round-trip (23), `@root`-without-root (14), `{client-logo}`-without-flag (15), case-sensitive heading (2a) + enum (7/8) + section (9), pipe-in-cell (5), positional-separator behavior (covered by 1.1 9-row parse).
- **Collect-all in `--check`/`--catalog-data` (S-A6.1a / RV2-4):** build a temp fixture copy mutated with ≥2 INDEPENDENT §8 violations (e.g. one miscased `kind` on row X AND one undeclared `section` on row Y, on different rows so both are decidable in one pass). Run `--catalog-data --json` (and `--check --json` against a composed file with the analogous multi-error case): assert `ok:false` AND `len(errors) >= 2` AND that BOTH violation messages are present (regex per the matrix) — proving the engine does NOT die on the first error. Contrast: a HARD-FAULT mutation (delete `manifest.md` or write invalid JSON into `library.json`) → assert a SINGLE error and immediate abort (S-A6.1a hard-fault path) — accumulation does not apply where the manifest is unreadable. Assemble mode (`--slides --json`) on the multi-error copy → `ok:false`, errors carry at least the first, no deck written (fail-fast S-A6.4).

### 1.4 library-YAML round-trip property test
- For the seed as-built entry AND both presets: `parse(write(parse(text))) == parse(text)` field-for-field (`convention-spec §4.1` invariant, §8 rule 23, S-A9.5). Specifically assert: `deviations: -` → none (NOT `[]`/`['']`); `engine_version: "1.0"` → `1.0` (quotes stripped); wrapped `slides` flow list → 7 ids; a block-list deviation line with `:` and `—` round-trips as the verbatim string (NOT a sub-mapping). Add a constructed entry carrying `accent: "#B8875A"` + a `modified: x — y` deviation to prove the quote-unwrap + em-dash + colon cases (`convention-spec §4.5` example shape).
- NEGATIVE: a hand-written `deviations: [modified: x]` (`:` in a flow element) → parse/round-trip FAILURE (`fixture-spec §I` rule 23).

### 1.5 DT5-procedure self-test on the fixture's seeded entry
- Implement the `convention-spec §4.4` 5-check property bar against a FRESH re-assembly of the seed entry (`2026-06-06-seed-demo`, `deviations: -` — the cleanest case, `fixture-spec §D`): (1) order identity vs the entry's `slides`; (2) per-slide tag/class skeleton equality excluding token-bearing-node text — compare the re-assembled deck's element-tree+`class` skeleton against a re-assembly of the SAME ids (zero-deviation: the fixture ships NO committed expected-output, `convention-spec §4.4` zero-deviation case — so the comparison is structural-self-consistency: two re-assemblies of the same recorded input produce identical skeletons); (3) asset set parity by filename; (4) `--check` token report = the template tokens; (5) headed render sanity is deferred to the done-boundary (1.5 runs the first 4 mechanically; check 5 needs a browser and is covered in the e2e preview suite + the DT-protocol).
- This is the engine-side proof the as-built record is reproducible BEFORE tecer is touched.

### 1.6 `install-engine.py` test
- On a temp copy of the fixture with a stale `library.json` `engine_version: "0.9"`: run `install-engine.py --library {tmp}`; assert `{tmp}/assemble.py` now byte-equals `engine/assemble.py` AND `{tmp}/library.json` `engine_version == ENGINE_VERSION` (S-A15). Missing target `library.json` → exit 1.

### 1.7 `--json` envelope shape
- Assert the envelope keys (S-A12.2) on: a success assemble (`ok:true`, `as_built_entry` populated AND `as_built_entry.logged === true`, `output` set, `assets_copied` non-empty), a `die()`/error case (`ok:false`, `errors` non-empty, exit 1, stdout is a SINGLE valid JSON doc — S-A12.3), a `--catalog-data` call (`catalog_data` with `sections`/`slides`/`presets`, S-A12.4), and a drift case (`library.json engine_version: "9.9"` → `warnings` non-empty, `ok:true`, S-A8.3).
- **`--catalog-data` skips per-composition asset rules (S-A12.4 / RV2-9):** point `--catalog-data --json` at a temp fixture copy whose manifest carries a `{client-logo}`-bearing or `@root/`-bearing fragment with NO `--client-logo`/`extra_asset_root` satisfied; assert `ok:true` (rules 13/15 NOT fired at catalog-data time) — the browse pane loads for a valid library. Contrast: an ASSEMBLE of a composition INCLUDING that fragment → `ok:false` (rule 13/15 fires per composition).

### 1.8 `--no-log` replay flag (ADX-4 / RV2-1)
- **Append suppression, line-count delta (self-verifiable):** copy the fixture to a tempdir with its vendored `assemble.py`; record `as-built.md` line count. Run `--preset nimbus-intro-en --out {tmp1}/d.html` (NO `--no-log`) → assert `as-built.md` gained exactly ONE `### ` entry (line-count delta > 0). On a SECOND fresh temp copy, run the same assembly WITH `--no-log --json --out {tmp2}/d.html` → assert `as-built.md` line count is UNCHANGED (delta 0, no `### ` entry appended) AND the deck + sibling `assets/` were still written (full assembly performed).
- **Envelope marker:** the `--no-log --json` run's envelope has `as_built_entry` populated (the would-be entry, per S-A12.5) with `as_built_entry.logged === false`; the non-`--no-log` run has `as_built_entry.logged === true`.
- This is the engine-side proof that DT5/migration reproduction (PB-T19) can replay a deck without polluting the validated `as-built.md`.

---

## 2. Builder e2e suites (Playwright python — REAL INPUT ONLY)

Location: `html/hypresent/tests/e2e/`. Framework: Playwright via `unittest.TestCase`, real server subprocess (live `conftest_helpers.start_server`). Each suite starts its own server on a dedicated port (8801+). Tests run HEADLESS for the dev gate (the HEADED real-gesture exercise on the migrated library is the separate done-boundary, §3). A small VALID e2e fixture library is created under `tests/e2e/fixtures/builder-lib/` (a 3-5 fragment subset mirroring the convention; assets self-contained so `/api/library-asset` + `srcdoc` work without network — mirrors `copy_synthetic` "fully self-contained" note). The engine MUST be vendored into that fixture lib (its `assemble.py` copy) so `--catalog-data`/`--assemble` work (S-A1.3).

**Port map:**

| Suite | File | Port | Covers |
|-------|------|------|--------|
| Page + nav | `test_pb1_page_nav.py` | 8801 | S-B1, S-B2, zero-regression to editor boot |
| Library load + validate | `test_pb2_library_load.py` | 8802 | S-B3, S-B4 grouping/filter, S-B9.1/.2/.3 |
| Previews | `test_pb3_previews.py` | 8803 | S-B5 (IO-gated srcdoc, scale, cap) |
| Tag + tray + reorder | `test_pb4_tray_reorder.py` | 8804 | S-B6, S-B7, S-B8 (hand-rolled sorter) |
| Assemble + handoff | `test_pb5_assemble_handoff.py` | 8805 | S-B9.4, S-B10 (assemble + editor handoff) |
| Error/empty/invalid | `test_pb6_states.py` | 8806 | S-B11 |
| Editor regression | (reuse existing `test_exit_smoke.py` + add 1 case to `test_pb1`) | 8801 | S-B1.3/S-B10.3 absent-param boot unchanged |

### 2.1 Page + nav (`test_pb1`, 8801)
- `GET /app/builder.html` returns 200 and the builder shell mounts (top bar, browse pane, tray present). REAL navigation: load `/app/`, click the "Builder" nav `<a>`, assert `location.pathname == '/app/builder.html'`; click "Editor", assert back at `/app/`.
- ZERO-REGRESSION (S-B1.3/S-B10.3): load `/app/` with NO `?file=` param; assert the editor boots exactly as today (toolbar present, `#open-btn` wired — open a fixture via the existing fake-dialog path and assert runtime ready, reusing `open_via_dialog_ui`). This proves the nav + the new param-branch did not break the existing boot.

### 2.2 Library load + validate (`test_pb2`, 8802, test_dialog=True)
- Inject a fake folder via the `/api/dialog-folder` test seam (S-B9.1) pointing at the e2e fixture lib; click "Pick library…"; assert the browse pane renders with the correct section groups in `library.json` order and the slide cards present.
- Language filter (S-B4.2): toggle the filter; assert language-neutral ids stay visible and a `.{lang}`-suffixed id hides when its lang ≠ selection. MEASURED: count visible cards before/after.
- Invalid library (S-B3.3/S-B11.2): point the fake folder at a deliberately-broken temp lib (e.g. missing `theme.css`); assert the invalid state shows the engine `errors` text and NO browse pane.
- `POST /api/library-load` passthrough (S-B9.2): assert the response is the engine `--catalog-data` envelope (has `sections`/`slides`/`presets`).

### 2.3 Previews (`test_pb3`, 8803)
- Mounting (S-B5.1): assert NOT all card iframes have `srcdoc` on load; scroll a card into view; assert its iframe gains a non-empty `srcdoc` and `dataset.mounted==='true'` (the IO gate fired). N≥2 (scroll two different cards).
- Renderable unit (S-B5.2): assert a mounted iframe's `srcdoc` contains the `theme.css` marker (a known class from the fixture theme) AND the fragment HTML; assert it does NOT contain `/runtime/js/runtime-main.js` (previews never inject the runtime).
- Cap (S-B5.4): with a fixture lib exceeding the cap, scroll through all; assert the mounted-iframe count never exceeds the cap constant (count iframes with non-empty `srcdoc`). Conditional skip ONLY if the fixture has fewer fragments than the cap, with the exact reason string.
- No-in-view-blanking (S-B5.4 / RV2-5): during a long top-to-bottom scroll over a fixture exceeding the cap, at each scroll step assert that EVERY iframe currently intersecting the viewport has a non-empty `srcdoc` (an in-view preview is never blanked by eviction). MEASURED: at ≥3 scroll positions, collect the intersecting `.slide-thumb-wrapper iframe`s (via `getBoundingClientRect` in-viewport test) and assert all have `srcdoc.length>0`. Conditional skip with the exact reason string if the fixture has fewer fragments than the cap (eviction never triggers).
- Scale (S-B5.3): assert the iframe wrapper has `overflow:hidden` and the iframe computed `transform` includes `scale(`.

### 2.4 Tag + tray + reorder (`test_pb4`, 8804) — the highest-risk suite
- Click-to-tag (S-B6.1): REAL click a browse card; assert a tray row appears with that id; D30: assert the tray row's id === the targeted card's id. Tag 3 cards; assert 3 ordered rows numbered 1-2-3.
- Remove (S-B6.2): click a row's ✗; assert it is gone and remaining rows renumber.
- Preset preload (S-B7.1): select a preset; assert the tray equals the preset's `slides` in order (read from the fixture preset).
- DRAG-REORDER (S-B8, the hand-rolled pointer sorter) — REAL pointer input via `page.mouse.down/move/up` (which fires `pointerdown/move/up` — research-01-ui §1.1, the whole reason D4-S4 chose hand-rolled): tag ≥3 rows; record the order; grab row 1 at its on-screen centre (hittability guard via bounding rect), `mouse.down`, `mouse.move` in ≥2 steps past row 2's midpoint (research-01-ui §1.1 two-move requirement), `mouse.up`; assert the MODEL order changed to the expected permutation (MEASURED outcome, not just a ghost-appeared check — mirrors `test_f2` `assertNotEqual(after, before)`). N≥2 (two different drags). NO `draggable`/`dragstart`/`DataTransfer` anywhere (S-B8.2).
- D30 for the drag: assert the row being dragged (the one the pointer grabbed) is the one whose position changed.
- ESCAPE-CANCEL (S-B8.1a / RV2-6) — REAL key press mid-drag: tag ≥3 rows; record the order; grab row 0, `mouse.down`, `mouse.move` in ≥2 steps past row 1's midpoint (so the DOM order has visibly changed mid-drag), THEN `page.keyboard.press('Escape')` BEFORE `mouse.up`; assert the order is RESTORED to the pre-drag order (MEASURED: `after_order === before_order`), the ghost class is gone, and NO `onReorder`-driven model change persisted. Release the pointer afterward (`mouse.up`) and assert the order is STILL the pre-drag order (Escape won, not the late pointerup).
- 2-ITEM REORDER (S-B8 / RV2-8): tag exactly 2 cards; drag row 0 past row 1's midpoint; assert the two rows SWAP (`after_order` is the reverse of `before_order`) — the minimal permutation / common off-by-one site.
- SCROLL-DURING-DRAG (S-B8 / RV2-8): on a tray taller than its container (enough rows to scroll), begin a drag (`mouse.down` on a row, one `mouse.move`), scroll the tray container mid-drag (`#tray-list` `scrollTop` change or `mouse.wheel`), continue the drag with ≥2 more `mouse.move`s using FRESH `getBoundingClientRect` reads (the sorter recomputes midpoints from live rects, so a scrolled rect must still yield a correct insertion), then `mouse.up`; assert the resulting order is the expected permutation for the final pointer position (guards the captured-pointer-vs-shifting-rects case). Conditional skip with the exact reason string if the fixture cannot produce a scrollable tray.

### 2.5 Assemble + handoff (`test_pb5`, 8805, test_dialog=True)
- Assemble (S-B9.4/S-B10.2): load the fixture lib, tag a known order, set a destination (fake folder via `/api/dialog-folder` + a filename), click "Assemble"; assert success state shows the deck path + `assets_copied` count + `unfilled_tokens` count. Assert ON DISK: the deck file exists at `{folder}/{name}.html`, a sibling `{folder}/assets/` holds the copied assets, and the fixture lib's `as-built.md` gained a new entry (S-A9.6) — read it back and assert `slides` matches the tray.
- EDITOR HANDOFF (S-B10.3) — REAL: on assemble success the builder navigates to `/app/?file=<encoded deck path>`; assert the editor page loads, the new param-branch calls the open path, and the iframe shows the assembled deck (wait for runtime ready via the existing `wait_runtime_ready`). Assert the deck's slides rendered (a known fragment class present in the iframe doc). This exercises the smallest-change handoff end-to-end.
- HANDOFF PATH-ENCODING cases (S-B10.3 step 1 / RV2-3) — assemble to deck filenames covering the encoding edge cases, then hand off and assert the deck opens in the editor for EACH: (a) the existing accent/space case (e.g. `deck final ção.html`); (b) a `%`-bearing path (temp deck file named e.g. `deck 100%.html`). The single `URLSearchParams.get()` decode (no second `decodeURIComponent`) MUST open the `%` path WITHOUT a `URIError` — a double-decode would throw or corrupt the path. Assert for each: `page.url` contains `/app/?file=`, runtime ready, a known fragment class present in the iframe doc.
- Invalid-assemble passthrough (S-B11.4): force an engine error (e.g. an id not in the manifest injected into the tray model) and assert the error banner shows the engine `errors` and nothing opens.

### 2.6 Error/empty/invalid states (`test_pb6`, 8806)
- No library loaded → empty-state prompt; Assemble disabled (S-B11.1/.3).
- Zero-presets library → preset selector "(no presets)"; scratch tag flow still works (S-B11.5).
- Engine spawn error / non-JSON stdout (simulate by pointing at a folder with no `assemble.py`) → error banner (S-B9.2 failure path).

---

## 3. Done-boundary protocol (DT1–DT5 + EX1; orchestrator-exercised; NOT claimable by §1/§2)

This is the Fidelity Floor exercise on the MIGRATED tecer library (`5-workbench/tecer-biz/slide-library/` on `main` after S-C6). HEADED browser + real mouse/keyboard gestures (rbtv-done-gate Fidelity Floor; U1-S4 done-gate locked). The dev suites (§1, §2) run against the synthetic fixture/e2e-lib and are explicitly NOT a substitute. Evidence files under `docs/verification/prez-v1/dt{n}-*.md` + captures in a sibling folder.

| Criterion | Exercise (HEADED, migrated tecer library) | Evidence |
|-----------|-------------------------------------------|----------|
| DT1 | GUI preset flow end-to-end: pick the migrated tecer library, select a real preset, tweak the order in the tray (real drag), assemble | screenshots of each step + the assembled deck path |
| DT2 | GUI scratch flow: navigate the section groups, filter by language (pt/en), tag slides by clicking, real-drag reorder, assemble | screenshots + tray state captures |
| DT3 | Both flows: assert assets copied to sibling `assets/`, as-built entry written, deck opens in the editor rendering correctly (real handoff) | the `assets/` listing + the as-built entry + a headed editor screenshot showing rendered slides + unfilled tokens |
| DT4 | Cold-agent test: a fresh agent given ONLY the migrated library folder + a deck intent (audience, occasion, language) assembles a correct deck using `README-FOR-AGENTS.md` alone (`convention-spec §5`) | the agent's transcript + the resulting deck + `--check` token report |
| DT5 | Re-assemble jui-py + camu from their as-built records; run the `convention-spec §4.4` 5-check property bar; both pass with no excused diffs (post-migration empty "upgraded" class, S-C5.2) | the per-deck 5-check results + headed render captures |
| EX1 | Kimi-evidenced clean, error-free local server run (server boots, builder + editor pages load, no console/server errors) | the server stdout/stderr capture + WALL_MS + a page-load screenshot |
| EX2 | Independent COLD verifier re-exercises every DT criterion given ONLY the contract criteria + the running artifact (never the builder's tests/sheet) — verdicts must match (rbtv-done-gate Orchestrated Dispatches) | the verifier's own evidence sheet |

- **3.1** DT5 reuses the engine's deterministic re-assembly (S-A11) + the §4.4 property checks (implemented once in §1.5 and re-run here against the REAL tecer decks). The headed render-sanity (check 5) is HEADED here (vs deferred in §1.5).
- **3.2** The plan (`prez-builder-v1-plan.md`) marks which artifacts each DT consumes (also listed in build-spec §Done-boundary artifacts). The plan itself ENDS at "all §1 + §2 suites green + clean server run + migration validated+merged"; §3 is the orchestrator's gate after the plan completes.

---

## 4. Test-task evidence contract (every §1/§2 task writes this)

Each test task writes its evidence file at `docs/verification/prez-v1/{suite}-result.md` containing, per the D29 block:
```
SUITE: {name}
CMD: {exact command run}
WALL_MS: {measured}
EXIT: {unittest exit code}
TESTS: {ran}/{passed}/{failed}/{skipped}
SKIPPED_LINES_COUNT: {n}
SKIP_REASONS:
  - {exact reason string per skip}
STDOUT+STDERR:
  {full captured output}
```
A physically-implausible WALL_MS (browser e2e <1s; the done-boundary OS-dialog <1.5s) → the task self-checks, writes a BUG section, and STOPS (never reports green) — D29 tripwired rerun.

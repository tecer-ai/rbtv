# prez-builder v1 — Execution Plan

**Status:** authored 2026-06-06 (W2+W3+W4). Executes `build-spec.md` (S-numbers) + `test-plan.md` against the FROZEN `convention-spec.md` + `fixture-spec.md`. Task files: `docs/plan/prez-builder-v1/tasks/PB-T{n}-{slug}.md`, one self-contained file per task (learnings-kimi-worker §3). Supplements get letter suffixes at runtime (e.g. PB-T7b).

**Commit cadence (D7-S4 / changelog row 248):** feature-serial boundaries — one coherent deliverable + its tests → suite green → ONE commit. v3-style implement→suite-green→commit. NO RED/GREEN task pairs (avoids active-red-set contamination — learnings S3.3). Commits run via the `rbtv-commit` skill in a Claude sub-agent, LOCAL-ONLY unless the orchestrator says push (learnings §6). Tecer-biz commits/merge are a SEPARATE repo (tecer-biz `CLAUDE.md`).

**Dispatch invariants (every task file carries these VERBATIM):** the D14 ORCHESTRATOR ADDENDUM (3 rules, learnings §5); for test tasks, the D29 evidence-metrics block (learnings S2.1). Content anchors NEVER line numbers; per-task FILE ALLOWLIST (✚create/✎modify/✗delete); self-verifiable acceptance.

**Repos:** PB-T1..PB-T15 operate in the rbtv repo (`html/slide-library/`, `html/hypresent/`). PB-T16..PB-T19 operate in tecer-biz (`5-workbench/tecer-biz/`, separate git).

---

## Sequencing spine (hard constraints)

1. **Fixture before engine tests** — PB-T1 (fixture) → PB-T3/PB-T4 (engine unit suite).
2. **Engine verified-vs-fixture before anything that subprocesses it** — PB-T2+PB-T3+PB-T4 (engine green vs fixture) → PB-T5 (`install-engine`) → all builder-page tasks (PB-T6..PB-T14) AND migration (PB-T16..PB-T19).
3. **Migration before the done-boundary** — PB-T16..PB-T19 (migrate+validate+merge) → §3 DT-protocol (orchestrator, post-plan).
4. **Server endpoints before the builder JS that calls them** — PB-T7 (`builder_api.py` + routes) → PB-T8..PB-T11 (builder JS) → PB-T12..PB-T14 (e2e).
5. **Builder page shell before its feature modules** — PB-T6 (page+nav+shell) → PB-T8..PB-T11.

## Shared-file serialization (declared — learnings §3)

| Shared file | Order | Tasks |
|-------------|-------|-------|
| `html/slide-library/engine/assemble.py` | PB-T2 only (single author of the engine; PB-T2 includes `--json` + `--catalog-data` + `--no-log`) | PB-T2 |
| `html/hypresent/server/server.py` | PB-T7 only writes its do_POST additions; PB-T6 does NOT touch server.py | PB-T7 |
| `html/hypresent/app/index.html` | PB-T6 only (adds nav; ONE writer) | PB-T6 |
| `html/hypresent/app/js/main.js` | PB-T11 only (adds the `?file=` boot branch; ONE writer) | PB-T11 |
| `html/hypresent/app/builder.html` | PB-T6 creates; PB-T8..PB-T11 reference (do NOT modify) — builder JS is in separate files | PB-T6 |
| `html/hypresent/tests/e2e/builder_helpers.py` | PB-T12 creates; PB-T13/PB-T14 reference | PB-T12 |
| `5-workbench/tecer-biz/slide-library/*` | PB-T16 (branch+pre-commit) → PB-T17 (convert) → PB-T18 (vendor+self-describe) → PB-T19 (validate+merge) — strictly serial, single line | PB-T16→T17→T18→T19 |

Parallel groups have DISJOINT allowlists (verified in the self-check below).

---

## Task table

| Task | Deliverable | Allowlist (✚create ✎modify ✗delete) | Depends-on | Parallel-group | Commit boundary | Gate |
|------|-------------|--------------------------------------|------------|----------------|-----------------|------|
| PB-T1 | Fixture library built VERBATIM (`fixture-spec.md` A–G + README/CLAUDE) + §H self-check passes | ✚ `html/slide-library/tests/fixture-library/**` (all files per fixture-spec tree), ✚ `html/slide-library/tests/shared-brand/partner-mark.png` | — | G-A (with PB-T2) | C1 (after PB-T4 green) | §H 11-check self-check passes |
| PB-T2 | Engine `assemble.py` (single file): parser, library-YAML reader+writer, validation, assembly, as-built writer, catalog, CLI, `--json`, `--catalog-data` | ✚ `html/slide-library/engine/assemble.py` | — | G-A (with PB-T1) | C1 | `python -c` import + `--help` exits 0; `node`-style self-probe N/A (python) |
| PB-T3 | Engine unit suite part 1: fixture self-check (§H) + happy-path (1.2) + library-YAML round-trip (1.4) + `--json` shape (1.7) | ✚ `html/slide-library/engine/tests/test_engine_core.py`, ✚ `html/slide-library/engine/tests/__init__.py` | PB-T1, PB-T2 | G-B (with PB-T4) | C1 | suite green vs fixture; evidence file written |
| PB-T4 | Engine unit suite part 2: §I negative matrix (24 rows, 1.3) + DT5-procedure self-test (1.5) + `install-engine` test (1.6) | ✚ `html/slide-library/engine/tests/test_engine_negatives.py`, ✚ `html/slide-library/engine/tests/test_engine_dt5.py` | PB-T1, PB-T2 | G-B (with PB-T3) | C1 | both suites green; evidence file written |
| PB-T5 | Re-vendor tool `install-engine.py` | ✚ `html/slide-library/engine/install-engine.py` | PB-T2 | — | C1 | PB-T4's install-engine test passes (so T5 must precede T4's run — see note) |
| PB-T6 | Builder page shell: `builder.html`, `builder.css`, nav added to `index.html`, empty `builder-main.js` mount | ✚ `html/hypresent/app/builder.html`, ✚ `html/hypresent/app/css/builder.css`, ✚ `html/hypresent/app/js/builder/builder-main.js`, ✎ `html/hypresent/app/index.html` | PB-T2 | — | C2 (after PB-T14 green) | builder.html serves 200; editor boot unregressed (PB-T12 case) |
| PB-T7 | Server module `builder_api.py` + 4 routes wired into `server.py` (+ folder-dialog test seam) | ✚ `html/hypresent/server/builder_api.py`, ✎ `html/hypresent/server/server.py` | PB-T2 | — | C2 | unit probe: each route returns expected shape (PB-T12 covers) |
| PB-T8 | Builder JS: library pick+load+validate + section-grouped browse + language filter | ✚ `html/hypresent/app/js/builder/library-load.js`, ✚ `html/hypresent/app/js/builder/browse-pane.js`, ✎ `html/hypresent/app/js/builder/builder-main.js` | PB-T6, PB-T7 | — (serial on builder-main.js) | C2 | PB-T13 covers |
| PB-T9 | Builder JS: previews (IO-gated srcdoc, scale, cap) | ✚ `html/hypresent/app/js/builder/previews.js`, ✎ `html/hypresent/app/js/builder/browse-pane.js` | PB-T8 | — (serial on browse-pane.js) | C2 | PB-T13 covers |
| PB-T10 | Builder JS: tray (tag/remove/preset) + hand-rolled drag-reorder sorter | ✚ `html/hypresent/app/js/builder/tray.js`, ✚ `html/hypresent/app/js/builder/tray-sorter.js`, ✎ `html/hypresent/app/js/builder/builder-main.js` | PB-T8 | — (serial on builder-main.js after PB-T8) | C2 | PB-T14 covers |
| PB-T11 | Builder JS: assemble + editor handoff (incl. the `?file=` boot branch in main.js) | ✚ `html/hypresent/app/js/builder/assemble.js`, ✎ `html/hypresent/app/js/builder/builder-main.js`, ✎ `html/hypresent/app/js/main.js` | PB-T7, PB-T10 | — (serial on builder-main.js after PB-T10) | C2 | PB-T14 covers |
| PB-T12 | e2e: `builder_helpers.py` + page+nav suite + editor-regression case + e2e fixture lib | ✚ `html/hypresent/tests/e2e/builder_helpers.py`, ✚ `html/hypresent/tests/e2e/test_pb1_page_nav.py`, ✚ `html/hypresent/tests/e2e/fixtures/builder-lib/**` | PB-T6, PB-T7, PB-T5 | G-C (with PB-T13) | C2 | suites green; evidence written |
| PB-T13 | e2e: library-load suite + previews suite | ✚ `html/hypresent/tests/e2e/test_pb2_library_load.py`, ✚ `html/hypresent/tests/e2e/test_pb3_previews.py` | PB-T8, PB-T9, PB-T12 | G-C (with PB-T12 helpers first) | C2 | suites green; evidence written |
| PB-T14 | e2e: tray+reorder suite + assemble+handoff suite + states suite | ✚ `html/hypresent/tests/e2e/test_pb4_tray_reorder.py`, ✚ `html/hypresent/tests/e2e/test_pb5_assemble_handoff.py`, ✚ `html/hypresent/tests/e2e/test_pb6_states.py` | PB-T10, PB-T11, PB-T12 | — | C2 | suites green; evidence written |
| PB-T15 | EX1 clean server run evidence (boot, both pages load, no console/server errors) | ✚ `docs/verification/prez-v1/ex1-server-run.md` (+ captures) | PB-T6..PB-T14 | — | C2 | server boots clean; WALL_MS plausible |
| PB-T16 | tecer-biz: branch `slide-library-convention-migration` + COMMIT clean pre-state (U2-S4) | (tecer-biz git op; no file writes beyond the branch) | PB-T5 | — (tecer-biz repo) | T-C1 (tecer-biz) | branch exists; pre-commit recorded |
| PB-T17 | tecer-biz: `migrate_to_convention.py` + run it (manifest 9→10, title backfill, library.json, as-built extract, cross-root PNG, presets cleanup) + 57-title human review | ✚ `5-workbench/tecer-biz/slide-library/migrate_to_convention.py`, ✎ `5-workbench/tecer-biz/slide-library/manifest.md`, ✎ `.../presets.md`, ✚ `.../as-built.md`, ✚ `.../library.json`, ✎ `.../assets/**` (vendored PNG), (the human-review is an orchestrator gate) | PB-T16 | — (serial) | T-C2 | round-trip + pipe-scan pass; human review done |
| PB-T18 | tecer-biz: vendor engine (`install-engine.py`) + `README-FOR-AGENTS.md` + thin `CLAUDE.md` + regenerate `catalog.html` | ✎ `5-workbench/tecer-biz/slide-library/assemble.py` (vendored), ✎ `.../library.json` (stamp), ✚ `.../README-FOR-AGENTS.md`, ✎ `.../CLAUDE.md`, ✎ `.../catalog.html` | PB-T17 | — (serial) | T-C2 | engine `--catalog-data --json` ok:true on tecer lib |
| PB-T19 | tecer-biz: migration validation (round-trip + jui-py + camu §4.4 5-check bar) → merge branch to `main` (U2-S4) | ✚ `5-workbench/tecer-biz/slide-library/docs/migration-validation.md`, (merge = git op) | PB-T18 | — (serial) | T-C3 (merge) | both decks pass 5-check; merge gate conditions met |

> **Note on PB-T5 vs PB-T4:** PB-T4 includes the `install-engine` test (test-plan 1.6), so PB-T5 (`install-engine.py`) MUST land before PB-T4 RUNS its suite. Dispatch order: PB-T2 → PB-T5 → (PB-T3 ∥ PB-T4) → C1. PB-T5 is tiny; it rides into C1. Listed separately for allowlist clarity.

## Wave / dispatch order

```
Wave 1 (G-A, ∥):  PB-T1 (fixture)  ∥  PB-T2 (engine)        [disjoint: tests/fixture-library vs engine/assemble.py]
Wave 2:           PB-T5 (install-engine)                     [needs PB-T2]
Wave 3 (G-B, ∥):  PB-T3 (engine suite 1) ∥ PB-T4 (engine suite 2)  [disjoint test files; both need T1+T2+T5]
  → COMMIT C1  [prez-v1-c2: engine + fixture + engine suites green]   (rbtv master)
Wave 4:           PB-T6 (page shell) → PB-T7 (server endpoints)       [T6 index.html, T7 server.py — disjoint, MAY run ∥]
Wave 5 (serial on builder-main.js / browse-pane.js):
                  PB-T8 → PB-T9 → PB-T10 → PB-T11               [shared-file order per the table above]
Wave 6:           PB-T12 (helpers + page/nav + e2e fixture lib)
Wave 7 (G-C, ∥):  PB-T13 (load+previews) ∥ PB-T14 (tray+assemble+states)  [disjoint test files; both need T12 helpers]
Wave 8:           PB-T15 (EX1 server run)
  → COMMIT C2  [prez-v1-c3: builder page + endpoints + e2e green + clean server run]  (rbtv master)
Wave 9 (tecer-biz, serial):  PB-T16 → COMMIT T-C1 → PB-T17 → PB-T18 → COMMIT T-C2 → PB-T19 → MERGE T-C3
```

After Wave 9: the plan is COMPLETE (all suites green + clean server run + migration validated+merged). The orchestrator THEN runs the §3 done-boundary (DT1–DT5 + EX1 + EX2) on the merged tecer library — NOT part of this plan, NOT claimable by the suites above.

---

## Traceability — every S-requirement → ≥1 task, every task → ≥1 S-requirement

| build-spec S | Task(s) | test-plan |
|--------------|---------|-----------|
| S-A1 (artifact/layout/version stamp) | PB-T2 | 1.2 |
| S-A2 (library.json load) | PB-T2 | 1.7, 2.2 |
| S-A3 (manifest parser, all enum/case/pipe/empty) | PB-T2 | 1.1, 1.3 |
| S-A4 (asset resolution, @root prefix) | PB-T2 | 1.2, 1.3 (rules 13/14/16) |
| S-A5 (lang precedence) | PB-T2 | 1.2 |
| S-A6 (validation, §8 24-rule, purity, markers) | PB-T2 | 1.3 |
| S-A7 (assembly mechanics) | PB-T2 | 1.2 |
| S-A8 (version checks) | PB-T2 | 1.3 (20-22), 1.7 |
| S-A9 (as-built writer, library-YAML) | PB-T2 | 1.4, 1.2 |
| S-A10 (preset reader) | PB-T2 | 1.2 |
| S-A11 (DT5 reproduction hook; `--no-log` on replay) | PB-T2 | 1.5, 1.8 |
| S-A12 (`--json` / `--catalog-data` / `--no-log` replay; collect-all errors S-A6.1a) | PB-T2 | 1.7, 1.8, 2.2 |
| S-A13 (CLI surface) | PB-T2 | 1.2, 1.3 |
| S-A14 (catalog) | PB-T2 | (engine self; 1.2 may assert) |
| S-A15 (install-engine) | PB-T5 | 1.6 |
| S-B1 (page topology/nav) | PB-T6 | 2.1 |
| S-B2 (builder shell/css) | PB-T6 | 2.1 |
| S-B3 (library pick/load/validate) | PB-T8 | 2.2 |
| S-B4 (section grouping + lang filter) | PB-T8 | 2.2 |
| S-B5 (previews IO/scale/cap) | PB-T9 | 2.3 |
| S-B6 (tag + tray) | PB-T10 | 2.4 |
| S-B7 (preset preload) | PB-T10 | 2.4 |
| S-B8 (hand-rolled drag sorter) | PB-T10 | 2.4 |
| S-B9 (server endpoints) | PB-T7 | 2.2, 2.5, 2.6 |
| S-B10 (assemble + editor handoff) | PB-T11 | 2.5 |
| S-B11 (error/empty/invalid states) | PB-T8/PB-T10/PB-T11 | 2.2, 2.6 |
| S-C1 (branch + pre-commit) | PB-T16 | 3 (DT pre-req) |
| S-C2 (conversion script) | PB-T17 | 3.1 (DT5 uses converted as-built) |
| S-C3 (self-description) | PB-T18 | DT4 |
| S-C4 (engine vendoring) | PB-T18 | DT1-DT3 (assembly path) |
| S-C5 (migration validation) | PB-T19 | DT5, §C5 |
| S-C6 (merge gate) | PB-T19 | 3 (precondition) |

Every task PB-T1..PB-T19 maps to ≥1 S-requirement above (PB-T1=fixture for S-A* tests; PB-T3/T4/T12/T13/T14/T15 = the test-plan suites verifying S-A*/S-B*; PB-T16..T19 = S-C*). No task is orphan; no S-requirement is unowned.

## Done-boundary artifact map (which DT consumes what — build-spec §Done-boundary)

| DT | Consumes |
|----|----------|
| DT1/DT2 | migrated tecer lib (PB-T17/T18/T19) + builder page (PB-T6..T11) |
| DT3 | builder assemble path (PB-T11) + engine assets/as-built (PB-T2) + editor handoff (PB-T11) |
| DT4 | `README-FOR-AGENTS.md` (PB-T18) + vendored engine (PB-T18) |
| DT5 | engine re-assembly + §4.4 checks (PB-T2/PB-T19) on jui-py + camu |
| EX1 | clean server run (PB-T15) |
| EX2 | the verifier re-exercises DT1-DT5 against the same artifacts |

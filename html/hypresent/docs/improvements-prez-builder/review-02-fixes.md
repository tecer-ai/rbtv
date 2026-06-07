# Review 02 — Fix Map (Fix-Cycle Agent #2)

**Date:** 2026-06-07
**Source review:** `review-02-build.md` (NO-GO: 2 BLOCKER, 4 MAJOR, 6 MINOR).
**Binding contract:** `html/slide-library/docs/convention-spec.md` ADX-4 (implemented verbatim for `--no-log`).
**Scope of writes:** `build-spec.md`, `test-plan.md`, `prez-builder-v1-plan.md`, and the touched `PB-T*.md` task files ONLY. Convention-spec / fixture-spec / changelog / tecer-biz untouched. No web.

Every finding was applied per the BINDING ORCHESTRATOR DIRECTIONS (which override the reviewer where they differ). Verification notes are self-checks an executor can run.

---

## BLOCKERs

### RV2-1 — `--no-log` replay flag (ADX-4) entirely absent
**Fix:** PB-T2 (sole `assemble.py` writer) gains the global `--no-log` flag implementing convention-spec ADX-4 verbatim: full assembly, § 4 as-built append SUPPRESSED, `--json` envelope's `as_built_entry` carries the would-be entry marked `"logged": false` (normal assembly marks `"logged": true`).
**Where:**
- `build-spec.md`: new **S-A12.5** (`--no-log` mode); `logged` key added to **S-A12.2** envelope; **S-A13** CLI surface table gains the `--no-log` row; **S-A11.1** (DT5 hook) now requires `--no-log` on reproduction; build-spec **ADX-4** entry added.
- `PB-T2-engine-assemble.md`: CLI-surface section gains the `--no-log` subsection; as-built-writer append clause made conditional on `--no-log` (entry built once, appended-or-not by flag); envelope-keys note for `logged`; **acceptance criterion 5** added — run twice on separate temp fixture copies with/without `--no-log`, assert as-built `### ` heading delta == 1 (without) vs == 0 (with), deck still written, `as_built_entry.logged` == true/false.
- `test-plan.md`: new **§1.8** (`--no-log` replay: line-count delta + envelope marker).
- `prez-builder-v1-plan.md`: traceability S-A11/S-A12 rows updated (`--no-log`, test 1.8); shared-file `assemble.py` note + S-A12 row mention `--no-log`.
**Verify:** `grep "--no-log"` hits build-spec (5), PB-T2 (10), PB-T19 (7), test-plan (3) — all four. PB-T2 acceptance 5 is self-verifiable (line-count delta 1 vs 0).

### RV2-2 — PB-T19 reproduction pollutes the committed tecer `as-built.md`
**Fix:** PB-T19's jui-py + camu reproduction runs (incl. camu's twice-assembled self-consistency runs) ALL pass `--no-log`; added an explicit byte-identical self-check: `sha256(slide-library/as-built.md)` recorded before and after all reproduction runs, asserted IDENTICAL (a hash compare Kimi runs) — mismatch FAILS the gate.
**Where:** `PB-T19-tecer-validate-merge.md`: reproduction procedure mandates `--no-log` on every assemble run + argv shown; check-2 self-consistency runs marked `--no-log`; check-4 (`--check`) noted as no-append (no flag needed); new merge-gate condition 4 (hash byte-identical); acceptance criterion 3 (hash recorded); evidence + DONE updated. (Depends on RV2-1's flag.)
**Verify:** PB-T19 records both sha256 hashes; gate fails on mismatch; merge blocked if any condition fails.

---

## MAJORs

### RV2-3 — double-decode of `?file=`
**Fix:** the `?file=` value is read via `URLSearchParams.get()` ONLY (already decoded); the redundant `decodeURIComponent` is REMOVED from PB-T11's code-insert block. Builder-side `encodeURIComponent` retained. Live `api-client.js` confirmed single `JSON.stringify({path})` with no URL layer.
**Where:**
- `build-spec.md`: **S-B10.3 step 1** rewritten (`openFile(file, …)`, no second decode + rationale); build-spec **ADX-7** entry.
- `PB-T11-builder-assemble-handoff.md`: code block now `await openFile(fileParam, iframe)`; "Why this is correct" gains the single-decode note; acceptance probe 3 asserts `decodeURIComponent` absent from the param-read path.
- `test-plan.md` **§2.5** + `PB-T14` `test_handoff_path_encoding`: handoff e2e adds a `%`-bearing deck path (e.g. `deck 100%.html`) alongside the accent/space case.
**Verify:** `grep decodeURIComponent PB-T11` → 3 hits, ALL prohibitions (comment + acceptance assertion), zero in the code path. The `%` e2e proves no `URIError`.

### RV2-4 — `--check`/`--catalog-data` die-on-first vs collect-all
**Fix:** `--check` and `--catalog-data` ACCUMULATE all § 8 violations into `errors[]` (one run = full list), then exit 1. Assemble modes stay fail-fast (no partial output) but still emit `{ok:false, errors:[...]}` in `--json` with everything collected to the abort. `EngineDie` reserved for hard faults (unreadable/absent `library.json`/`manifest.md`) — these abort immediately in every mode. The GUI invalid-library state consumes the FULL list.
**Where:**
- `build-spec.md`: new **S-A6.1a** (accumulation by mode); **S-A12.3** rewritten (collect-vs-raise convergence); **S-A12.2** `errors` key note; **S-B11.2** + **S-B9.2** consume the full list; build-spec **ADX-5**.
- `PB-T2-engine-assemble.md`: Validation section gains "Error accumulation by mode"; `--json`/die section clarifies `EngineDie` is hard-fault-only (soft violations collected, not raised); `--catalog-data` paragraph; acceptance criterion 6 (≥2 errors in one run on a multi-error copy; single error + abort on hard fault).
- `PB-T8-builder-load-browse.md`: invalid-library render lists ALL errors (one `<li>` per error, not `errors[0]`).
- `test-plan.md` **§1.3** (collect-all: multi-error copy → `len(errors)>=2`; hard-fault → single error) + **§1.7** noted.
**Verify:** PB-T2 acceptance 6 + test-plan §1.3 assert ≥2 errors in one `--catalog-data` run; engine fixture §I mutations multi-error case yields ≥2.

### RV2-5 — preview eviction can blank an in-view iframe (FIFO escape)
**Fix:** eviction = LRU among NOT-currently-intersecting iframes ONLY; an in-view iframe is NEVER evicted; if every mounted iframe is in view at the cap, the cap raises TRANSIENTLY rather than blanking. The FIFO fallback is REMOVED.
**Where:**
- `build-spec.md`: **S-B5.4** rewritten (LRU-among-non-intersecting policy + transient cap raise + FIFO removed); build-spec **ADX-8**.
- `PB-T9-builder-previews.md`: mounted-count-cap section rewritten; acceptance criterion 4 (eviction filters to non-intersecting; no FIFO).
- `test-plan.md` **§2.3** + `PB-T13` `test_no_inview_blanking`: long-scroll e2e asserts every in-view iframe keeps a non-empty `srcdoc` at ≥3 scroll positions (conditional skip if fixture < cap).
**Verify:** PB-T13 test 4 asserts no in-view blanking during a long scroll; PB-T9 criterion 4 confirms the non-intersecting filter and FIFO absence.

### RV2-6 — Escape not wired for drag-cancel
**Fix:** Escape during an active drag cancels it — original DOM order restored, pointer capture released, transient listeners removed, `onReorder` NOT called. The `keydown` is wired ONLY while a drag is active (added on `pointerdown`, removed on drag end).
**Where:**
- `build-spec.md`: new **S-B8.1a** (Escape-cancel semantics); build-spec **ADX-9**.
- `PB-T10-builder-tray-sorter.md`: pointerdown snapshots pre-drag order + adds transient `keydown`; pointerup removes it; new Escape bullet (restore order, `releasePointerCapture`, no `onReorder`, Escape wins over late pointerup); acceptance criterion 2 greps `keydown`/`Escape`/`releasePointerCapture`.
- `test-plan.md` **§2.4** + `PB-T14` `test_drag_escape_cancel`: real `keyboard.press('Escape')` mid-drag, assert order restored, N≥2.
**Verify:** PB-T14 test 6 (real key press mid-drag, order == before_order); PB-T10 criterion 2 grep.

---

## MINORs (all 6 applied)

| ID | Fix | Where |
|----|-----|-------|
| RV2-7 | Stale port-bound prose corrected. Reviewer's "≤8799" was ITSELF stale — live e2e uses two clusters **8781–8799 AND 8810–8815** (live-verified). New suites at 8801–8806 sit in the free 8801–8809 gap (no collision); prose now states the true ceiling and forbids extending past 8809. | `test-plan.md` Ports line |
| RV2-8 | 2-item-tray reorder + scroll-during-drag e2e cases added. | `test-plan.md` §2.4; `PB-T14` `test_two_item_reorder`, `test_scroll_during_drag` (latter conditional-skips if tray can't scroll) |
| RV2-9 | `--catalog-data` runs LIBRARY-level §8 rules only (1,2,4-12,18-22), NOT per-composition asset rules 13/15 (no composition at catalog-data time). | `build-spec.md` S-A4.3 + S-A12.4 + ADX-6; `PB-T2` asset section + `--catalog-data` paragraph; `test-plan.md` §1.7 |
| RV2-10 | ≤~8-word title cap binds rule-4 (humanized-id) fallback too, not just rules 1-3. | `PB-T17-tecer-convert.md` step (2) title-backfill chain |
| RV2-11 | Engine subprocess pins `cwd=library_path` defensively. | `PB-T7-server-endpoints.md` `_run_engine` |
| RV2-12 | PB-T17's `git log -S` date queries run against HEAD (committed) BEFORE the `presets.md` rewrite, made deterministic (`-1` + a string unique to one entry; BLOCKED if non-unique/no match). | `PB-T17-tecer-convert.md` step (6) date-backfill |

---

## CROSS-ARTIFACT landings (each multi-artifact rule → every place it landed)

| Rule | build-spec | test-plan | plan (traceability/shared-file) | task file(s) |
|------|-----------|-----------|----------------------------------|--------------|
| **RV2-1 `--no-log`** | S-A12.5 (new), S-A12.2 (`logged` key), S-A13 (CLI row), S-A11.1, ADX-4 | §1.8 (new) | S-A11/S-A12 rows; `assemble.py` shared-file note | PB-T2 (CLI + writer + acceptance 5), PB-T19 (reproduction uses it) |
| **RV2-2 hash self-check** | (consumes S-A12.5) | — | — | PB-T19 (reproduction `--no-log` + sha256 gate cond. 4 + acceptance 3) |
| **RV2-3 single decode** | S-B10.3 step 1, ADX-7 | §2.5 (% case) | — | PB-T11 (code + acceptance 3), PB-T14 (`test_handoff_path_encoding`) |
| **RV2-4 collect-all** | S-A6.1a (new), S-A12.3, S-A12.2, S-B11.2, S-B9.2, ADX-5 | §1.3, §1.7 | — | PB-T2 (validation + acceptance 6), PB-T8 (render ALL errors) |
| **RV2-5 LRU eviction** | S-B5.4, ADX-8 | §2.3 (no-in-view-blanking) | — | PB-T9 (cap section + acceptance 4), PB-T13 (`test_no_inview_blanking`) |
| **RV2-6 Escape-cancel** | S-B8.1a (new), ADX-9 | §2.4 | — | PB-T10 (sorter + acceptance 2), PB-T14 (`test_drag_escape_cancel`) |
| **RV2-9 catalog-data scope** | S-A4.3, S-A12.4, ADX-6 | §1.7 | — | PB-T2 (asset section + `--catalog-data`) |
| **RV2-8 tray edge cases** | (S-B8 unchanged) | §2.4 | — | PB-T14 (`test_two_item_reorder`, `test_scroll_during_drag`) |

Single-artifact MINORs (RV2-7 test-plan; RV2-10/RV2-12 PB-T17; RV2-11 PB-T7) landed only in their one file — no cross-artifact propagation needed.

---

## Allowlist impact

No new tasks created; no allowlists widened beyond what the existing task scopes already cover. The new e2e cases (RV2-3/5/6/8) fold into the e2e files PB-T13/PB-T14 already create (`test_pb3_previews.py`, `test_pb4_tray_reorder.py`, `test_pb5_assemble_handoff.py`) — those files are already in the respective task allowlists. The `--no-log` flag, collect-all, and catalog-data scope are all internal to `assemble.py` (PB-T2's single allowlisted file). The `cwd` pin is internal to `builder_api.py` (PB-T7). The plan traceability table was updated for the `--no-log` S-requirement (S-A11/S-A12 rows → test 1.8).

---

## Self-verification (run by this agent)

1. `grep "--no-log"` → build-spec 5, PB-T2 10, PB-T19 7, test-plan 3 — hits all FOUR required artifacts. PASS.
2. `grep decodeURIComponent PB-T11` → 3 hits, all prohibitions (the "NOT used" comment + the acceptance-criterion assertion of its absence); ZERO in the code-insert path (the block passes `fileParam` directly to `openFile`). PASS.
3. PB-T2 acceptance criteria re-read as a cold executor: criterion 5 (`--no-log` delta) and 6 (collect-all) each specify exact commands, exact assertions (line-count/`### `-heading delta 1 vs 0; `len(errors)>=2`; `logged` true/false), and explicit skip conditions — self-verifiable without ambiguity. PASS.

# Review 02 — prez-builder v1 BUILD artifacts (Adversarial Reviewer #2)

**Date:** 2026-06-07
**Scope:** `build-spec.md`, `test-plan.md`, `prez-builder-v1-plan.md`, the 19 `PB-T*.md` task files.
**Contracts:** `convention-spec.md` (v1 + ADX-1..ADX-4), `fixture-spec.md` (incl. § I).
**Method:** every inlined excerpt verified character-for-character against live `html/hypresent/server/`, `app/`, `tests/`; migration facts verified against `5-workbench/tecer-biz/slide-library/` (read-only). No web tools.

---

## VERDICT: **NO-GO**

Two BLOCKERs gate execution. Both are narrow and mechanically fixable (one engine flag + its two consumers, one envelope-accumulation change). Once the BLOCKERs and the two MAJORs that touch product correctness (RV2-3 double-decode, RV2-2 die-on-first list) are resolved, the artifact set is GO-ready — the spine, allowlists, parallel-group disjointness, shared-file serialization, Kimi-discipline, and the live-source excerpts are otherwise accurate and well-anchored.

**Severity counts:** BLOCKER 2 · MAJOR 4 · MINOR 6.

---

## Findings table

| ID | Severity | Artifact / section / task | Live-source evidence | Fix direction |
|----|----------|---------------------------|----------------------|---------------|
| **RV2-1** | **BLOCKER** | Engine: ADX-4 `--no-log` entirely absent. `build-spec.md` S-A13 (line 3 declares authored "against ADX-1..3"); `PB-T2` CLI surface (line 212) lists `--out/--lang/--title/--accent/--client-logo/--json` and NO `--no-log`; grep across build-spec + test-plan + all 19 tasks → **zero** hits for `--no-log`/`no_log`/`logged`/replay. | `convention-spec.md` ADX-4 (2026-06-07) mandates a `--no-log` replay flag; `--json`+`--no-log` envelope must carry `as_built_entry` with `"logged": false`. PB-T2 is the SOLE writer of `assemble.py` (plan shared-file table) and is not instructed to add it → the flag will never exist. | Add `--no-log` to PB-T2: global flag; when set, run full assembly but SKIP the `as-built.md` append; in `--json` mode emit the would-be entry with `"logged": false` (per ADX-4 verbatim). Add the envelope key to S-A12.2. |
| **RV2-2** | **BLOCKER** | Migration validation: PB-T19 reproduction pollutes the committed tecer `as-built.md`. `PB-T19` reproduction procedure (lines 31, 35: re-assemble jui-py + camu, twice for check 2) via the vendored engine; depends on RV2-1's missing `--no-log`. | `PB-T2` line 186: as-built append target is `LIBRARY/as-built.md` where `LIBRARY = Path(__file__).resolve().parent` = the vendored engine's parent = `5-workbench/tecer-biz/slide-library/`. Each reproduction assemble appends; check 2 assembles twice/deck → up to 6 spurious `### ` entries written into the very `as-built.md` being validated, on-branch, pre-merge. ADX-4 names this exact scenario ("recording the replay would pollute the log it validates"). | Depends on RV2-1. PB-T19 MUST pass `--no-log` on every reproduction assemble. Until RV2-1 lands, PB-T19's gate is uncomputable/destructive. |
| **RV2-3** | MAJOR | Editor handoff: double-decode of `?file=`. `PB-T11` line 95-99 + `build-spec` S-B10.3 step 1. | `URLSearchParams(location.search).get("file")` ALREADY percent-decodes; PB-T11 then calls `decodeURIComponent(fileParam)` a SECOND time. Verified against live `api-client.js:1-15` (`open` does a single `JSON.stringify({path})`, no URL layer). For tecer deck names (spaces + PT accents é/ã/ç) this is idempotent and harmless, but a deck path containing a literal `%` (legal Windows filename char) → `decodeURIComponent` mis-decodes or throws `URIError` → handoff fails. | Drop the redundant `decodeURIComponent`. Use `URLSearchParams.get("file")` directly (it returns the decoded path); keep `encodeURIComponent` on the builder side. |
| **RV2-4** | MAJOR | Engine `--check`/`--catalog-data` die-on-first vs collect-all (Focus 3). `build-spec` S-A12.3 (line 107) + S-A6.1; `PB-T2` `die()` helper (lines 234-240) raises `EngineDie` on the FIRST error, caught at mode top → `{ok:false, errors:[<one msg>]}`. | Grep of build-spec for collect/accumulate/"full list" → only S-A12.3's single-message "collects the message into errors". `errors` is typed list[str] but will only ever hold ONE element in every mode. The GUI invalid-library state (S-B9/S-B11.2, PB-T8 line 54) renders `errors` — so the GUI shows only the first §8 failure, not the full list. ADX-2's stated rationale ("a GUI needs the full list") is unmet; inherits tecer's die-on-first. | For `--check` and `--catalog-data` (the GUI/diagnostic modes), accumulate §8 ERROR rows into `errors[]` and emit all of them (validation continues past the first failure where decidable), THEN exit 1. Assemble mode MAY keep die-on-first (no partial output). Update S-A12.4 + the §1.3/§1.7 test expectations to assert multi-error collection. |
| **RV2-5** | MAJOR | Preview cap eviction fallback (Focus 6). `PB-T9` line 38: "if computing distance is awkward, fall back to evicting the OLDEST in the Set (FIFO) — acceptable for v1." | FIFO can evict an IN-VIEW iframe (the oldest-mounted may still be on screen on a tall page), blanking a visible preview while a far off-screen one stays mounted — a visible regression and a divergent-implementation seam (two valid behaviors). The cap MATH is sound (24 × ~46KB ≈ 1.1MB vs the 2.6MB all-mounted ceiling). | Mandate the distance-based eviction (largest |rect-to-viewport-centre|); remove the FIFO escape, OR constrain FIFO to "never evict an iframe currently intersecting the viewport." Make PB-T13 `test_mount_cap` assert no in-view iframe is ever unmounted. |
| **RV2-6** | MAJOR | Drag cancel: Escape not wired (Focus 5 sweep). `PB-T10` line 45 cancels on `pointercancel`/`pointerleave`/`pointerup` only; no `keydown`/Escape handler. test-plan §2.4 + `PB-T14` test 4 do not exercise Escape or pointercancel mid-drag. | Convention-free but Focus 5 explicitly required "drag cancel (Escape / pointercancel)". `setPointerCapture`/release IS correctly mandated (PB-T10 lines 43,45) and the e2e asserts ORDER BY `data-slide-id` (PB-T14 line 41) — those parts are clean. Escape-to-cancel is the gap. | Add an Escape `keydown` handler in tray-sorter.js that releases capture, restores the pre-drag DOM order, and does NOT call `onReorder`. Add a PB-T14 case (drag, press Escape, assert order unchanged). |
| **RV2-7** | MINOR | Stale port-bound claim (Focus 10). `test-plan.md` line 12: "existing suite occupies ≤8797". | Live `tests/e2e/*.py` use ports up to **8799** (verified: `test_*` at 8798, 8799). New builder suites start at 8801, so NO actual collision (8800 gap) — but the stated invariant is factually wrong; a future suite trusting "≤8797" and taking 8798-8800 would clash. | Correct the bound to "≤8799"; the 8801+ allocation is fine as-is. |
| **RV2-8** | MINOR | Tray edge cases unswept (Focus 5 sweep). `PB-T10`/`PB-T14`: no 2-item-tray drag test, no tray-scroll-during-drag handling/test. | The sorter computes insertion via `getBoundingClientRect()` midpoints (PB-T10 line 44); scrolling the tray mid-drag shifts rects under a captured pointer — untested. 2-item reorder is the minimal permutation and a common off-by-one site. | Add PB-T14 cases: a 2-row reorder (assert swap), and (optional) a scroll-during-drag guard. Low blast radius. |
| **RV2-9** | MINOR | `--catalog-data` runs FULL validation but spec doesn't pin asset-resolution scope. `build-spec` S-A12.4 (line 108) "runs the FULL validation (S-A6) first". | §8 rule 13 (asset resolves) is per-COMPOSITION (resolved "for the requested composition" — §2.4); `--catalog-data` has no composition. If the engine runs rule 13/15 (`{client-logo}` needs `--client-logo`) at catalog-data time, a library with a `{client-logo}`-bearing fragment (e.g. the fixture covers) → spurious `ok:false` on load, breaking the browse pane for valid libraries. | Clarify S-A12.4: `--catalog-data` runs the LIBRARY-level rules (1,2,4-12,18-22) but NOT per-composition asset rules (13,15) — there is no composition. Confirm PB-T2 scopes rule 13/15 to assemble modes only. |
| **RV2-10** | MINOR | PB-T17 humanized-id fallback may exceed the ≤8-word title cap. `PB-T17` step 2 / `convention-spec` §9.5 chain rule 4 "humanized id". | Rules 1-3 cap length (rule 3 is ≤6 words); rule 4 (humanized id) has no cap. Tecer ids are short kebab so unlikely to breach, but unbounded by the chain text. | Note in PB-T17 that rule-4 output is also subject to the §2.2 ≤~8-word guidance (the human review covers it; titles are low blast radius). |
| **RV2-11** | MINOR | Engine subprocess sets no `cwd` (Focus 4). `PB-T7` `_run_engine` (lines 162-169) calls `subprocess.run([sys.executable, engine, *args], ...)` with no `cwd`. | Correct BY DESIGN — the engine resolves `LIBRARY = Path(__file__).resolve().parent` (PB-T2 line 22), so cwd is irrelevant; `--out` is an explicit (absolute) path from the builder. `sys.executable` + `encoding="utf-8"` + `rc is None` guard + malformed-JSON guard all PRESENT and correct. Logged only to confirm Focus 4 is otherwise clean. | None. (Optionally pass `cwd=library_path` defensively, but not required.) |
| **RV2-12** | MINOR | Migration date-backfill git command runs against a possibly-shallow/edited file. `PB-T17` step 6: `git -C 5-workbench/tecer-biz log -1 --format=%cs -S "<unique string>" -- slide-library/presets.md`. | The `-S` pickaxe finds the commit that introduced the string. But PB-T17 ALSO edits/removes `## As-built log` from `presets.md` in the SAME task (step 7) — order matters: the `-S` query MUST run BEFORE the presets.md rewrite, against committed history. The task lists extraction (step 6) before cleanup (step 7), so order is correct, but it's implicit. | Make explicit in PB-T17: run all `git log -S` date queries against HEAD (committed) state BEFORE writing the modified `presets.md`. (Pickaxe on committed history is unaffected by the working-tree edit, so this is belt-and-suspenders.) |

---

## Per-focus verdicts

| # | Focus | Verdict | One-liner |
|---|-------|---------|-----------|
| 1 | Handoff `?file=` | **PARTIAL** | Excerpts match live `main.js`/`file-controls.js` exactly; absent-param byte-identical boot is real (X4 confirmed). `/api/open` accepts an absolute path (`api.py:140` `pathlib.Path`); builder passes the engine's absolute `output`; encode→JSON round-trip is clean — EXCEPT the redundant second `decodeURIComponent` (RV2-3, MAJOR, fires on `%`-in-path). |
| 2 | `/doc/` singleton isolation | **REFUTED (clean)** | Only the editor handoff touches `/doc/` (correct); previews flow exclusively through `/api/library-asset` + `srcdoc` (S-B5.2, PB-T9). `_doc_root` re-point after handoff cannot affect self-contained `srcdoc` previews. No task routes a preview through `/doc/`. |
| 3 | `--check` + `--json` collect-all | **CONFIRMED** | The engine dies on the FIRST §8 error in ALL modes (`die()`→`EngineDie`, PB-T2:234-240); `errors[]` will hold one element; the GUI sees one error, not the full list ADX-2 demands (RV2-4, MAJOR). |
| 4 | Windows subprocess traps | **REFUTED (clean)** | `sys.executable`, `encoding="utf-8"`, nonzero/`rc is None` handling, malformed-JSON guard all concretely specced in PB-T7 `_run_engine`/`handle_*`. cwd correctly irrelevant (RV2-11). |
| 5 | Pointer-sorter | **PARTIAL** | `setPointerCapture` + release mandated (PB-T10:43,45); unique `data-slide-id` + assert-order-by-id e2e present (PB-T14:41). Gaps: Escape-cancel not wired (RV2-6, MAJOR), 2-item + scroll-during-drag unswept (RV2-8, MINOR). |
| 6 | Preview architecture (D5) | **PARTIAL** | theme read ONCE/library (PB-T9:32), `rootMargin:'200px'`, cap=24 with sound math, no runtime injection — all correct. The FIFO eviction fallback can blank an in-view iframe (RV2-5, MAJOR). |
| 7 | ADX-4 accommodation | **CONFIRMED** | `--no-log` absent everywhere (RV2-1, BLOCKER); PB-T19 reproduction pollutes the committed tecer `as-built.md` for lack of it (RV2-2, BLOCKER). e2e assembly correctly uses temp copies (PB-T14 `make_temp_library`), so suites don't dirty the repo — but DT5/migration does. |
| 8 | Plan integrity | **REFUTED (clean)** | Parallel groups G-A/G-B/G-C have disjoint allowlists (verified per-file); shared files (`assemble.py`, `server.py`, `index.html`, `main.js`, `builder-main.js`, `browse-pane.js`, `builder_helpers.py`, tecer `slide-library/*`) are single-writer or strictly serialized; traceability table maps every S→task and back; 4-requirement spot-check (S-A12, S-A6 engine; S-B5 experience; S-C5 migration) all resolve to the right task and test. |
| 9 | Migration tasks | **PARTIAL** | Live tecer facts VERIFIED: 57 rows; 9-col header exactly as quoted; `cover-investor` at row 48 with the exact `cover-bg.jpg, brand/logo/tecer-logo-white-transparent.png` cell; exactly **11** as-built entries (jui-py + camu both present); single cross-root cell. 57-title pass is an AGENT-drafted + orchestrator-reviewed gate (PB-T17, not owner-blocking). T-C1 pre-commit precedes mutation (PB-T16→T17). Merge gate conditions explicit + complete (PB-T19:45-48). Only blemish: RV2-2 (the `--no-log` pollution) + minor RV2-10/12. |
| 10 | Kimi-discipline sweep | **PARTIAL** | D14 ADDENDUM verbatim in all 19 files; D29 block in all 7 test/evidence tasks (T3,4,12,13,14,15,19); content-anchors (not line numbers) everywhere; evidence under `docs/verification/prez-v1/`; acceptance criteria self-verifiable; `node --check` accepts ES-module syntax (verified empirically). Every inlined live excerpt matches source character-for-character — NO stale anchors found. Only blemish: stale "≤8797" port claim (RV2-7, MINOR). |

---

## Stale-excerpt audit (Focus 10 — every inlined live excerpt re-verified)

All clean. Spot results:
- PB-T7's inlined `do_POST` (lines 22-55) == live `server/server.py:131-163` verbatim, incl. the `/api/_test/set-dialog` seam and the `try/except ImportError` api-import shape.
- PB-T7's folder-dialog idiom matches live `api.py` `_OPEN_PS`/`_ps_args`/`_run_ps_dialog_default` (`-STA -NoProfile -NonInteractive -Command`, `pwsh`→`powershell.exe`, `_DIALOG_LOCK`, hidden TopMost owner Form).
- PB-T11's inlined `openFile` == live `file-controls.js:22-25`; the unused-export claim is TRUE (main.js imports only `openViaDialog`).
- PB-T6's inlined `index.html` head/`do_GET` static-route excerpt matches live `server.py:114-115`.
- PB-T2's reused mechanics (`_split_row`, `TOKEN_RE`, `SLIDE_NUMBER_RE`, `renumber_slides`, preset regex) match the tecer parity shapes the spec authorizes; the divergence callouts (10-col, case-sensitive headings, positional separator, `@root/` prefix, `default_lang`, purity scan, library.json) all align with convention-spec §8.1.

---

## Minimal fix list by severity

**BLOCKER (must fix before dispatch):**
1. **RV2-1** — Add `--no-log` to PB-T2 (engine) per ADX-4: full assembly, skip as-built append; `--json` emits the would-be entry with `"logged": false`. Add the envelope key to build-spec S-A12.2.
2. **RV2-2** — PB-T19: pass `--no-log` on every jui-py/camu reproduction assemble (depends on RV2-1). Without it the migration gate writes spurious entries into the committed tecer `as-built.md` on-branch.

**MAJOR (fix before dispatch — product correctness / divergent implementation):**
3. **RV2-3** — PB-T11: remove the second `decodeURIComponent`; use `URLSearchParams.get("file")` directly.
4. **RV2-4** — Engine `--check`/`--catalog-data`: accumulate all §8 ERRORs into `errors[]` (don't die on first) so the GUI shows the full list; update §1.3/§1.7 tests.
5. **RV2-5** — PB-T9: mandate distance-based cap eviction (or forbid evicting an intersecting iframe); remove the FIFO escape; assert it in PB-T13.
6. **RV2-6** — PB-T10/PB-T14: wire Escape-to-cancel in tray-sorter.js (release capture, restore order, no `onReorder`) + a cancel test.

**MINOR (polish — may batch post-GO):**
7. RV2-7 correct the "≤8797" port bound to "≤8799".
8. RV2-8 add 2-item + scroll-during-drag tray cases.
9. RV2-9 scope `--catalog-data` validation to library-level rules (exclude per-composition asset rules 13/15).
10. RV2-10 note the ≤8-word cap also binds the humanized-id title fallback.
11. RV2-11 (optional) pass `cwd=library_path` to the engine subprocess defensively.
12. RV2-12 make explicit that PB-T17's `git log -S` date queries run against committed history before the presets.md rewrite.

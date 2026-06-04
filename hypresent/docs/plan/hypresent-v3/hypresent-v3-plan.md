---
name: hypresent-v3
overview: "Hypresent Session-2 improvement cycle — fix the gaps the owner hit in real use of v2: R1 dialogs appear on top (TopMost owner Form), R2 resize/move actually work (re-enable pointer-events on Moveable controls), R3 element delete (toolbar-button-only, full undo, threads→unanchored), R4 remove the redundant #color-btn, R5 palette-token tooltip, R6 per-token copy-HEX, R7 display-branched text alignment (H+V), R8 repeatable font-size (range snapshot/restore + tracked-span fallback), R9 remove the broken outline panel end-to-end. Executor: Kimi (non-reasoning); every task is one bounded, self-contained dispatch with a file allowlist enforced by post-run git diff. Commit boundaries are FEATURE-SERIAL (D24): each scorecard item is implemented + its tests, gated, committed, THEN the next starts."
---

# Hypresent v3 — Execution Plan

> Format mirrors `docs/plan/hypresent-v2/hypresent-v2-plan.md` (READ-ONLY reference) and `docs/spec/04-implementation-plan.md` (v1, READ-ONLY). This is a NEW plan; it never modifies v1/v2 artifacts.
> Per-task self-contained Kimi prompt bodies live in `tasks/V3-T*.md`. Each prompt assumes the executor reads NOTHING else.
> Grounding: `docs/improvements-2026-06-r2/spec.md` (V3-S1–S25), `docs/improvements-2026-06-r2/test-plan.md`, `changelog.md` Session-2 block (R1–R9, D15–D24, U11–U16, carried U1–U10a + D8/D12/D14), `docs/improvements-2026-06-r2/diagnosis.md`.

**Status legend:** ☐ TODO · ◐ DOING · ☑ DONE · ✗ BLOCKED. All start ☐.

**Branch:** `hypresent-v2` continues (per the session contract — NEVER create a new branch, never push/merge; commits are local-only via the `rbtv-commit` skill dispatched to a Claude sub-agent, per D9/D16).

**Kimi dispatch contract (every product-code task):** `kimi --work-dir "<hypresent-root>" --quiet --prompt "<contents of tasks/V3-Tn.md>"` with a positive `--max-ralph-iterations`. Exit 0=ok, 75=backoff+retry, 1=halt+surface. After each dispatch the orchestrator runs `git -C <repo> diff --stat` (D8 gate) and REJECTS the run if any changed path is outside the task's FILE ALLOWLIST. Kimi evidence goes to files under `docs/verification/v3/` (D12), read by the Registrar.

**D14 addendum (carried, binding on EVERY Kimi dispatch — restated verbatim in each task file):** On blocking product bugs STOP and write a bug-report file under `docs/verification/v3/` — never patch outside your allowlist; NEVER create files at the workspace root — scratch goes under a tempdir.

**Critical pre-read (flagged in spec §0):** the diagnosis line numbers have DRIFTED from the live `hypresent-v2` source (several v2-accepted fixes landed after the diagnosis read). Every task file edits by quoted CODE CONTENT, never by line number. Five reconciled contradictions (C1–C5) are in spec §0; none invalidates a fix.

---

## Feature-serial commit pipeline (D24)

Each boundary = implement the feature (+ its tests) → feature tests green → diff gate → ONE commit → next boundary starts. Kimi tasks parallelize ONLY within a boundary, and only on disjoint files. The chosen order and its justification:

**R2 → R8 → R1 → R3 → R4 → R5+R6 → R7 → R9 → docs-sync+EXIT.**

| # | Boundary | Why this position |
|---|----------|-------------------|
| C1 | **R2 (resize/move alive)** | The headline defect and a PREREQUISITE for honest tests of everything that selects an element (the F2 rewrite, R3 delete, R7 align, R8 font-size all REAL-click to select; with R2 dead, real-input selection still works but the resize/move tests cannot pass). Smallest surface (one injected style), highest leverage. First. |
| C2 | **R8 (font-size repeat)** | Independent of R2 (different module, text-format.js); small; unblocks the EXIT smoke's 3-press assertion. Early so the runtime text-format changes settle before R7 also touches text-format.js (R7 adds align logic to the same file → serialize R8 before R7 on text-format.js). |
| C3 | **R1 (dialogs on top)** | Server-only (api.py); fully disjoint from all runtime/shell work; its real-dialog ctypes test is OS-level and independent. Placed after the two highest-risk runtime fixes so the runtime is stable when the OS test runs. |
| C4 | **R3 (delete)** | Touches commands.js + runtime-main.js + index.html + main.js. Must land before R7 (which also touches commands.js, runtime-main.js, index.html, main.js) so the shared files serialize cleanly. Depends on nothing from R2/R8/R1. |
| C5 | **R4 (#color-btn removal)** | Tiny; touches index.html + main.js. Serialize after R3 on those two files (R3 added #delete-btn + its handler; R4 removes #color-btn + its handler — disjoint regions, but same files → ordered). |
| C6 | **R5+R6 (token tooltip + copy-HEX)** | SHARED boundary per D24 (same file color-popover.js, same UX surface). R5 is header markup; R6 is per-row button + handler + color.js export. color.js (R6) is disjoint from color-popover.js (R5+R6 UI) — but both UI edits are in one file, so R5 and R6 are ONE Kimi task (V3-T13), not two parallel ones. |
| C7 | **R7 (alignment)** | Largest runtime+shell feature. Touches commands.js, runtime-main.js, selection.js, text-format.js, index.html, main.js. Serialized LAST among feature work on every shared file (after R3 on commands.js/runtime-main.js/index.html/main.js; after R8 on text-format.js; after R4 on index.html/main.js). |
| C8 | **R9 (outline removal)** | Pure removal across index.html, main.js, shell.css, runtime-main.js, element-registry.js. Placed LAST among features so it removes outline code AFTER R7 added align code to main.js/index.html (disjoint regions; ordering avoids anchor churn). Independent of all feature logic. |
| C9 | **docs-sync + EXIT** | README + module-map + decision-log + build-log + the EXIT smoke + the full-suite run. After everything. |

**Why not R1 first?** R1 is server-only and independent — it COULD go first. It is placed third so the two runtime fixes that unblock honest interaction tests (R2, R8) land first; this keeps the highest-risk surface earliest and lets every later boundary's tests assume a working editor. (Alternative orderings that front-load R1 are valid but offer no leverage gain; the chosen order front-loads the prerequisite-for-testing fixes.)

### Shared-file serialization (the binding constraint within/across boundaries)

| File | Edited by (in commit order) | Serialization |
|------|------------------------------|---------------|
| `runtime/js/commands.js` | R3 (deleteElement), R7 (align) | R3 → R7 |
| `runtime/js/runtime-main.js` | R3 (delete-element reg), R8 (format-snapshot reg), R7 (align reg), R9 (drop regions/sections) | R8 → R3 → R7 → R9 (each ADDS/removes a distinct registration/import; R9's removal touches only the `ready` emit + the `regions` import, untouched by the others) |
| `runtime/js/text-format.js` | R8 (snapshot/restore/clear), R7 (computeAlignCaps/applyAlign) | R8 → R7 |
| `runtime/js/selection.js` | R7 (alignCaps in buildInfo) | R7 only |
| `runtime/js/color.js` | R6 (export rgbToHex + normalizeHex + token.hex) | R6 only |
| `runtime/js/element-registry.js` | R9 (remove regions + orphan helpers) | R9 only |
| `runtime/js/interaction.js` | R2 (inject pointer-events style) | R2 only |
| `app/index.html` | R3 (+#delete-btn), R4 (−#color-btn group), R7 (+6 align btns), R9 (−outline panel) | R3 → R4 → R7 → R9 |
| `app/js/main.js` | R3 (+delete wiring), R4 (−color-btn handler), R8 (+format-snapshot mousedown), R7 (+align wiring), R9 (−outline fns/wiring) | R8 → R3 → R4 → R7 → R9 (R8's mousedown edit is in the formatButtons loop; the others are disjoint regions; order avoids re-anchoring) |
| `app/js/shell/color-popover.js` | R5+R6 (one task) | single task |
| `app/css/shell.css` | R9 (−outline rules), R6 (+copy-btn style, optional) | R6 → R9 (disjoint rule blocks) |
| `runtime/js/comments.js` | NONE | R3 only CALLS `reanchorAfterMove` (already exported); does NOT edit comments.js |

Within a boundary, tasks parallelize only on DISJOINT files (e.g. R6's color.js vs color-popover.js could split, but R5+R6's UI is one file so it is one task). Test tasks run after their feature's product tasks within the same boundary, before that boundary's commit.

---

## Dependency graph (text)

```
(branch hypresent-v2 — continues; no V3-T0 branch task)

C1 R2  ── V3-T1 (interaction.js inject pointer-events style; .moveable-area KEPT — RV07 skip-confirmed via reorder.js classifyDrop scanner)
          └─ V3-T2 (tests: test_r2_resize_real :8792 incl. MOVE-delta + REORDER coverage + REWRITE test_f2_select_guides :8782) ◄ needs T1
          ── commit C1
C2 R8  ── V3-T3 (text-format.js snapshot/restore/clear + runtime-main format-snapshot reg + text-edit clear + main.js mousedown)
          └─ V3-T4 (tests: test_r8_font_size_repeat :8798) ◄ needs T3
          ── commit C2
C3 R1  ── V3-T5 (api.py TopMost owner Form in _OPEN_PS/_SAVE_PS; remove ShowHelp)
          └─ V3-T6 (tests: test_r1_dialog_zorder ctypes + test_r1_dialog_seam) ◄ needs T5
          ── commit C3
C4 R3  ── V3-T7 (commands.deleteElement + runtime-main delete-element reg + index.html #delete-btn + main.js wiring)
          └─ V3-T8 (tests: test_r3_delete :8793) ◄ needs T7
          ── commit C4
C5 R4  ── V3-T9 (index.html remove #color-btn+group; main.js remove handler)
          └─ V3-T10 (tests: test_r4_color_btn_removed :8794) ◄ needs T9
          ── commit C5
C6 R5+R6 ─ V3-T11 (color.js export rgbToHex + normalizeHex + token.hex)   ─┐ disjoint files → parallel
          ─ V3-T12 (color-popover.js: ⓘ tooltip + copy-HEX btn + handler + CSS) ◄ needs T11 (reads token.hex)
          └─ V3-T13 (tests: test_r5_token_tooltip :8795 + test_r6_copy_hex :8796) ◄ needs T11,T12
          ── commit C6
C7 R7  ── V3-T14 (text-format.js computeAlignCaps/applyAlign + commands.align + selection.js alignCaps + runtime-main align reg + index.html 6 btns + main.js wiring)
          └─ V3-T15 (tests: test_r7_alignment :8797) ◄ needs T14
          ── commit C7
C8 R9  ── V3-T16 (remove outline: index.html + main.js + shell.css + runtime-main + element-registry regions)
          └─ V3-T17 (tests: test_r9_outline_removed :8799) ◄ needs T16
          ── commit C8
C9 docs+EXIT ─ V3-T18 (update test_exit_smoke :8788 + run full suite + clean server run → docs/verification/v3/result.md)
             ─ V3-T19 (docs-sync: README, 03-module-map, decision-log append rows, build-log append) ◄ needs T18
             ── commit C9
```

---

## Boundary C1 — R2 (resize/move alive)

| ID | Goal | File allowlist (✎=modify ✚=create) | Depends on | Public contract | Acceptance (self-verifiable) | Status |
|----|------|-------------------------------------|-----------|-----------------|------------------------------|--------|
| **V3-T1** | R2 fix: inject a `hyp-`scoped `<style>` into the iframe that re-enables `pointer-events:auto` on Moveable's control elements under `#hyp-interaction-wrapper`. Wrapper stays `pointer-events:none`. Do NOT touch the onDragEnd hit-test toggle (C1/V3-S4). | ✎ `runtime/js/interaction.js` | — | A `hyp-`id'd `<style id="hyp-interaction-style">` is appended to the iframe `document.head` exactly once at wrapper creation, with the rule from V3-S3; removed in teardown. | `node --check` passes; the file contains the exact selector list for `.moveable-control-box/.moveable-control/.moveable-line/.moveable-area/.moveable-direction` scoped under `#hyp-interaction-wrapper` with `pointer-events:auto`; the wrapper's own `pointerEvents:"none"` is unchanged; the onDragEnd `el.style.pointerEvents` block is untouched. | ☑ (as amended: T1b document-sized absolute wrapper + T1c minimal direction-handles-only rule — see changelog rows 84–98 + `v3-t2-debug.md`/`v3-t2c-debug.md`) |
| **V3-T2** | Tests: NEW `test_r2_resize_real.py` (:8792, hittability guard + resize geometry outcome + twice-drag + MOVE translate-delta + REORDER DOM-index change + no-console) AND REWRITE `test_f2_select_guides.py` (:8782, real-input selection replacing the 3 synthetic clicks; convert the 3 skipTest to hard outcome assertions; add geometry-delta assertions to E-F2-4/5; dynamic empty-point discovery for the deselect click). | ✚ `tests/e2e/test_r2_resize_real.py`, ✎ `tests/e2e/test_f2_select_guides.py`, (✎ `tests/e2e/conftest_helpers.py` IF a shared `click_element` helper is added) | V3-T1 | Implements E-R2-1..6 (incl. orchestrator-added MOVE-delta + REORDER) + the rewritten E-F2-1..8 (test-plan). Real input only; no skip-as-green; coordinate math via `iframe_origin + doc_eval` (no `frame_locator.bounding_box()`); `wait_for_function` viewport sync (no fixed post-scrollIntoView timeout). | `python -m unittest discover -s tests/e2e -p "test_r2_*.py" -v` and `… test_f2_*.py -v` pass on :8792/:8782; no `dispatchEvent` for selection in either file; no `skipTest` in test_f2. | ☑ (as amended: T2b/T2c — R2 7/7, F2 8/8 with the single D25-permitted conditional skip; commit `7e43d21`) |

> **Commit C1** (after V3-T2 green + diff gate): `fix(hypresent): R2 — re-enable pointer-events on Moveable controls so resize/move work under real handle drag; real-input F2 tests`.

---

## Boundary C2 — R8 (repeatable font-size)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T3** | R8 fix: in `text-format.js` add `savedRange`/`currentFontSpan` module state, `snapshotSelection()`, `clearFontState()`, and the restore+fallback logic in `adjustFontSize` (V3-S20–S22). Register `format-snapshot` in `runtime-main.js`. Call `clearFontState()` in `text-edit.js` `commit()`. Add the `format-snapshot` mousedown fire in `main.js`'s formatButtons handler (before the focus call). | ✎ `runtime/js/text-format.js`, ✎ `runtime/js/runtime-main.js`, ✎ `runtime/js/text-edit.js`, ✎ `app/js/main.js` | — | `snapshotSelection`/`clearFontState` exported; `adjustFontSize` restores `savedRange` when the live selection collapsed at the editable root and the snapshot is still in the active editable; tracks the bumped/created span in `currentFontSpan`; falls back to bumping `currentFontSpan` when no usable range; `format-snapshot` registered; `commit()` clears font state; the formatButtons mousedown fires `format-snapshot` before `iframe.contentWindow.focus()`. | `node --check` passes on all four; the symbols exist; `adjustFontSize`'s `Math.max(8,…)` floor preserved; `git diff` confined to the four files. | ☑ (as amended T3b: `data-hyp-fontspan` marker tracking replaces node-identity — history's innerHTML round-trip detaches nodes; see `v3-t4-debug.md` + changelog rows 104–109; commit `bd81b32`) |
| **V3-T4** | Tests: NEW `test_r8_font_size_repeat.py` (:8798) — the 3-press → one span +6px zero-empties load-bearing test + decrease + mix + lifecycle-clear + no-console. | ✚ `tests/e2e/test_r8_font_size_repeat.py` | V3-T3 | Implements E-R8-1..5 (test-plan). Real dblclick + real word select + real toolbar clicks. | `… test_r8_*.py -v` passes on :8798; asserts span count==1, font-size delta==+6px, empty-span count==0. | ☑ 5/5 OK (commit `bd81b32`) |

> **Commit C2:** `fix(hypresent): R8 — font-size A+/A- repeatable on one selection (range snapshot/restore + tracked-span fallback)`.

---

## Boundary C3 — R1 (dialogs on top)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T5** | R1 fix: in `server/api.py`, add a hidden `TopMost`/minimized/no-taskbar/`Opacity=0` owner WinForms Form in BOTH `_OPEN_PS` and `_SAVE_PS`, `Show()` it, pass it to `$d.ShowDialog($owner)`, and `Close()/Dispose()` it. Remove the `$d.ShowHelp = $true` line from both (V3-S1). Everything else (launcher, fallback, filter, encoding) unchanged. | ✎ `server/api.py` | — | Both PS script constants create the owner Form, call `ShowDialog($owner)`, dispose the owner; neither contains `ShowHelp`. `_run_ps_dialog_default`/`_ps_args`/handlers unchanged. | `python -c "import py_compile; py_compile.compile('server/api.py', doraise=True)"` OK; both constants contain `ShowDialog($owner)` and a `TopMost` owner Form; neither contains `ShowHelp`; `handle_dialog_open()` with an injected `None` launcher still returns `(200,{'cancelled':True})`. | ☐ |
| **V3-T6** | Tests: NEW `test_r1_dialog_zorder.py` (ctypes, REAL dialog, EnumWindows→foreground/topmost→WM_CLOSE; documented headless skip) + NEW `test_r1_dialog_seam.py` (in-process seam regression + the V3-S1 static contract lock). | ✚ `tests/unit/test_r1_dialog_zorder.py`, ✚ `tests/unit/test_r1_dialog_seam.py` | V3-T5 | Implements U-R1Z-1..3 + U-R1S-1..5 (test-plan). The z-order test drives the real launcher; the seam test injects a fake. | `python -m unittest discover -s tests/unit -p "test_r1_*.py" -v` passes; the z-order test runs (not skipped) on an interactive desktop and asserts foreground/topmost + WM_CLOSE teardown; the seam test asserts the routes + the ShowHelp-removed/owner-present script shape. | ☐ |

> **Commit C3:** `fix(hypresent): R1 — native open/save dialogs appear on top of Chrome (TopMost owner Form); ctypes z-order test`.

---

## Boundary C4 — R3 (element delete)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T7** | R3 feature: `commands.deleteElement(hypId)` (capture parent/nextSibling hyp-id + node ref; do=removeChild; undo=re-insert before next, mirror `reorder.place()`); `runtime-main` `delete-element` registration with the edit-active + last-region guards, `reanchorAfterMove()` + `selection.clear()` on success; `#delete-btn` `🗑` in `index.html`; `main.js` wiring with status messages. | ✎ `runtime/js/commands.js`, ✎ `runtime/js/runtime-main.js`, ✎ `app/index.html`, ✎ `app/js/main.js` | — (does NOT depend on R2/R8/R1) | `deleteElement` factory; `delete-element {hypId}` → `{deleted}`/`{blocked:"editing"|"last-region"}`; runtime-main imports `reanchorAfterMove` from comments.js (NEW) + uses already-imported `clear`; `#delete-btn` present; shell wiring per V3-S6. | `node --check` on commands.js + runtime-main.js + main.js; `deleteElement(...).do()/undo()` round-trip on a synthetic element; `delete-element` returns `{blocked:…}` in the two guard cases; `#delete-btn` exists; `git diff` confined to the four files; comments.js NOT modified. | ☐ |
| **V3-T8** | Tests: NEW `test_r3_delete.py` (:8793) — delete outcome, undo, thread→unanchored + re-anchor, last-region block, edit guard, no-keyboard-path, Moveable teardown, no-console. | ✚ `tests/e2e/test_r3_delete.py` | V3-T7 | Implements E-R3-1..9 (test-plan). Real-click select; real button click; real keyboard for the no-path test. | `… test_r3_*.py -v` passes on :8793; asserts DOM node removal + undo restoration + thread unanchored flag + the two blocks. | ☐ |

> **Commit C4:** `feat(hypresent): R3 — delete the selected element (toolbar button only, full undo, threads go unanchored, last-region blocked)`.

---

## Boundary C5 — R4 (#color-btn removal)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T9** | R4: remove the `#color-btn` button AND its enclosing single-child `toolbar-group` wrapper from `index.html`; remove the `const colorBtn = …` handler block from `main.js` (V3-S11). | ✎ `app/index.html`, ✎ `app/js/main.js` | — (serialize after R3 on these files) | `#color-btn` and its empty group gone from index.html; the handler gone from main.js. | `document.getElementById("color-btn")` would be null; grep of `app/` for `color-btn` → zero hits; `node --check` main.js; `git diff` confined to the two files. | ☐ |
| **V3-T10** | Tests: NEW `test_r4_color_btn_removed.py` (:8794) — button null, no empty group, color UI intact. | ✚ `tests/e2e/test_r4_color_btn_removed.py` | V3-T9 | Implements E-R4-1..3 (test-plan). | `… test_r4_*.py -v` passes on :8794. | ☐ |

> **Commit C5:** `chore(hypresent): R4 — remove the redundant #color-btn toolbar button and its handler`.

---

## Boundary C6 — R5 + R6 (token tooltip + copy-HEX) — SHARED boundary (D24)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T11** | R6 data: in `color.js`, EXPORT `rgbToHex`; add `normalizeHex(value)` (hex passthrough/expand + computed-style fallback for named/hsl/rgb, V3-S14); add `hex: normalizeHex(token.value)` to each token in `readPalette().tokens`. | ✎ `runtime/js/color.js` | — | `rgbToHex` exported; `normalizeHex` exported; `readPalette` tokens carry `hex`. | `node --check`; `readPalette()` tokens include a `hex` `#rrggbb`; `normalizeHex('red')` → `#ff0000` (via computed style); `git diff` confined to color.js. | ☐ |
| **V3-T12** | R5+R6 UI: in `color-popover.js`, add the Palette-Tokens header `ⓘ` tooltip (R5/V3-S12, exact title) AND the per-row `.hyp-token-copy` button using `token.hex` + a delegated click handler (clipboard write + transient "Copied!") + discreet CSS (R6/V3-S13). | ✎ `app/js/shell/color-popover.js` | V3-T11 (reads `token.hex`) | Header ⓘ with the exact D18 title; each token row has a copy button with `data-hex`; a `container` click handler matches `.hyp-token-copy` and writes to the clipboard with a transient affordance. | `node --check`; the injected header contains the ⓘ with the exact title string; the token-row template contains `.hyp-token-copy` with `data-hex`; a click handler references `navigator.clipboard.writeText`; `git diff` confined to color-popover.js. | ☐ |
| **V3-T13** | Tests: NEW `test_r5_token_tooltip.py` (:8795) + NEW `test_r6_copy_hex.py` (:8796, clipboard permission granted). | ✚ `tests/e2e/test_r5_token_tooltip.py`, ✚ `tests/e2e/test_r6_copy_hex.py` | V3-T11, V3-T12 | Implements E-R5-1..3 + E-R6-1..4 (test-plan). | `… test_r5_*.py -v` and `… test_r6_*.py -v` pass on :8795/:8796; R6 asserts clipboard readback == normalized `#rrggbb`. | ☐ |

> **Commit C6:** `feat(hypresent): R5+R6 — palette-token doc-wide tooltip and per-token copy-HEX (normalized #rrggbb)`.

---

## Boundary C7 — R7 (text alignment)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T14** | R7 feature: `text-format.js` `computeAlignCaps(el)` + `applyAlign(el,axis,value)` (table-normative, never converts plain auto-height block); `commands.align(hypId,axis,value)` (capture-all undo); `selection.js` `buildInfo` adds `alignCaps`; `runtime-main` `align {axis,value}` registration; `index.html` 6 align icon buttons after the format group; `main.js` wiring + reactive disabled-state from `selection-changed`. | ✎ `runtime/js/text-format.js`, ✎ `runtime/js/commands.js`, ✎ `runtime/js/selection.js`, ✎ `runtime/js/runtime-main.js`, ✎ `app/index.html`, ✎ `app/js/main.js` | (serialize after R8 on text-format.js; after R3 on commands.js/runtime-main.js/index.html/main.js; after R4 on index.html/main.js) | `computeAlignCaps`/`applyAlign` per the table; `commands.align`; `alignCaps` in selection payload; `align` registration; 6 buttons; reactive disable. | `node --check` on all four JS; `applyAlign` writes `text-align` for block-H, `justify-content`/`align-items` for flex by direction, `justify-items`/`align-items` for grid, `vertical-align` for table-cell, and no-ops vertical on plain auto-height block; `align` undo restores captured inline state incl. `display`; the 6 buttons exist; `git diff` confined to the six files. | ☐ |
| **V3-T15** | Tests: NEW `test_r7_alignment.py` (:8797) — H on block, V on flex-row/column, grid, table-cell, plain-block-V-disabled, fixed-height-block-V, caps payload, undo, no-console. | ✚ `tests/e2e/test_r7_alignment.py` | V3-T14 | Implements E-R7-1..11 (test-plan). Injected controlled elements + real-click select. | `… test_r7_*.py -v` passes on :8797; asserts the written CSS property value per display and the `alignCaps` payload. | ☐ |

> **Commit C7:** `feat(hypresent): R7 — display-branched text alignment (H always, V where a real mechanism exists) with capability-reactive toolbar`.

---

## Boundary C8 — R9 (outline removal)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T16** | R9: remove the outline end-to-end (V3-S23/S24): `index.html` `.outline-panel` block; `main.js` `outlineRegions`/`activeOutlineHypId`/`renderOutline`/`setActiveOutline`/the `ready` `renderOutline(...)` call/the `selection-changed→setActiveOutline` wiring; `shell.css` `.outline-*` rules; `runtime-main.js` `sections: regions()` → `tokens` only + drop the `regions` import; `element-registry.js` `regions()` export + its orphan helpers (grep before removing each). | ✎ `app/index.html`, ✎ `app/js/main.js`, ✎ `app/css/shell.css`, ✎ `runtime/js/runtime-main.js`, ✎ `runtime/js/element-registry.js` | (serialize after R7 on index.html/main.js; after R8/R3/R7 on runtime-main.js) | Outline panel + all its wiring + `regions()`/`sections` removed; `ready` emits `{tokens}` only. | `node --check` on the three JS; grep of `app/`+`runtime/` for `outline`/`regions(`/`sections` (payload) → zero PRODUCT hits; `document.getElementById("outline-list")` would be null; the `ready` payload has no `sections`; `git diff` confined to the five files. | ☐ |
| **V3-T17** | Tests: NEW `test_r9_outline_removed.py` (:8799) + UPDATE `test_g1_panel_survival.py` (remove the outline assertions; keep the popover+comment survival invariant). | ✚ `tests/e2e/test_r9_outline_removed.py`, ✎ `tests/e2e/test_g1_panel_survival.py` | V3-T16 | Implements E-R9-1..4; g1 loses its outline sub-assertions, keeps the comment-panel survival witness. | `… test_r9_*.py -v` passes on :8799; `… test_g1_*.py -v` still passes (no outline assertions). | ☐ |

> **Commit C8:** `chore(hypresent): R9 — remove the non-functional outline panel and regions()/sections end-to-end`.

---

## Boundary C9 — docs-sync + EXIT

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Status |
|----|------|----------------|-----------|-----------------|-----------|--------|
| **V3-T18** | Update `test_exit_smoke.py` (:8788) to add a REAL resize (R2), a REAL delete+undo (R3), a REAL 3-press font-size (R8), and assert `#outline-list`/`#color-btn` absent (R9/R4); run the FULL suite + a clean server run on the sample; capture to `docs/verification/v3/result.md`. | ✎ `tests/e2e/test_exit_smoke.py`, ✚ `docs/verification/v3/result.md` | V3-T1..T17 | Implements the changed E-EXIT-1..3; runs `python -m unittest discover -s tests -p "test_*.py" -v`; confirms `/app/` 200 + zero editor console errors opening the sample. | Entire suite green (the R1 ctypes test runs, not skipped, on this machine); clean server run confirmed; results logged to result.md. | ☐ |
| **V3-T19** | Docs-sync: README (remove outline from usage §9; remove the "Font-size caret artifact" known-limitation now fixed; add R3 delete + R7 alignment + R5/R6 to usage; remove `#color-btn` mentions if any); `docs/spec/03-module-map.md` (the spec §"module map delta"); `docs/decision-log.md` APPEND-ONLY rows for outline removal, color-btn removal, alignment feature, delete feature; `docs/build-log.md` append a v3 cycle entry. | ✎ `README.md`, ✎ `docs/spec/03-module-map.md`, ✎ `docs/decision-log.md`, ✎ `docs/build-log.md` | V3-T18 | README usage reflects R3/R4/R5/R6/R7/R9; known-limitations drops the fixed font-size note; module-map reflects the changed modules; decision-log APPENDS rows (existing rows byte-identical); build-log appends. | README §9 no longer mentions the outline; the font-size known-limitation is gone; decision-log diff = additions only (existing rows untouched); module-map updated; build-log appended; `git diff` confined to the four docs. | ☐ |

> **Commit C9:** `docs(hypresent): sync v3 docs (usage, module map, decision log, build log) and close the Session-2 cycle`.

---

## Commit map (which tasks → which commit)

| Commit | Tasks | Proposed message |
|--------|-------|------------------|
| C1 | V3-T1, V3-T2 | `fix(hypresent): R2 — re-enable pointer-events on Moveable controls so resize/move work under real handle drag; real-input F2 tests` |
| C2 | V3-T3, V3-T4 | `fix(hypresent): R8 — font-size A+/A- repeatable on one selection (range snapshot/restore + tracked-span fallback)` |
| C3 | V3-T5, V3-T6 | `fix(hypresent): R1 — native open/save dialogs appear on top of Chrome (TopMost owner Form); ctypes z-order test` |
| C4 | V3-T7, V3-T8 | `feat(hypresent): R3 — delete the selected element (toolbar button only, full undo, threads go unanchored, last-region blocked)` |
| C5 | V3-T9, V3-T10 | `chore(hypresent): R4 — remove the redundant #color-btn toolbar button and its handler` |
| C6 | V3-T11, V3-T12, V3-T13 | `feat(hypresent): R5+R6 — palette-token doc-wide tooltip and per-token copy-HEX (normalized #rrggbb)` |
| C7 | V3-T14, V3-T15 | `feat(hypresent): R7 — display-branched text alignment (H always, V where a real mechanism exists) with capability-reactive toolbar` |
| C8 | V3-T16, V3-T17 | `chore(hypresent): R9 — remove the non-functional outline panel and regions()/sections end-to-end` |
| C9 | V3-T18, V3-T19 | `docs(hypresent): sync v3 docs (usage, module map, decision log, build log) and close the Session-2 cycle` |

Commits are executed by a dispatched Claude sub-agent invoking the `rbtv-commit` skill (D9/D16), LOCAL-ONLY (no push, no merge — owner's call), on `hypresent-v2`. The sample `tecer-gsmm-introduction.html` is gitignored (U10a) and never staged.

---

## Notes

- **Surgical-change fence:** no task modifies a file outside its allowlist. Test tasks touch ONLY `tests/` (+ `conftest_helpers.py` when a shared helper is added). Product bugs found by tests are REPORTED (a bug-report file under `docs/verification/v3/`), never patched outside the allowlist (D14).
- **Diagnosis line drift:** every task file is CONTENT-ANCHORED (quotes the live code around each edit), never line-numbered. Spec §0 documents the five reconciled contradictions (C1–C5); none invalidates a fix.
- **comments.js is NOT edited by any v3 task.** R3 only CALLS `reanchorAfterMove` (already exported in v2). If a task finds it missing, STOP and report (do not stub).
- **Dependency-free runtime:** Playwright + stdlib `ctypes` are the only dev/test surface; `ctypes` is stdlib (no new dependency). No vendored lib added.
- **PROTECTED (read-only, never modify):** `docs/spec/04-implementation-plan.md`; all of `docs/plan/hypresent-v1/` and `docs/plan/hypresent-v2/`; all of `docs/improvements-2026-06/`; `changelog.md` (Registrar-owned); `tecer-gsmm-introduction.html` (gitignored sample — tests READ/copy it to temp, never modify in place).

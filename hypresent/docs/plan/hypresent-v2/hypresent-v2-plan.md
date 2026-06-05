---
name: hypresent-v2
overview: "Hypresent v2 improvement cycle — native OS open/save dialogs (F1), modeless interaction with Google-Slides alignment guides (F2), move/reorder/re-parent on drop with FLIP (F3), border-color editing (F4), agent-tagged comments with a derived head instruction block (F5), plus verification+hardening of the already-fixed G1 panel-survival and G2 serializer-guard blockers. Executor: Kimi (non-reasoning); every task is one bounded, self-contained dispatch with a file allowlist enforced by post-run git diff."
---

# Hypresent v2 — Execution Plan

> Format mirrors `docs/spec/04-implementation-plan.md` (v1, READ-ONLY reference). This is a NEW plan; it never modifies v1 artifacts.
> Per-task self-contained Kimi prompt bodies live in `tasks/V2-T*.md`. Each prompt assumes the executor reads NOTHING else.
> Grounding: `docs/improvements-2026-06/spec.md` (S-decisions S0–S25), `docs/improvements-2026-06/test-plan.md`, `changelog.md` (D1–D10, U1–U10), `docs/decision-log.md` (D1–D6, A1–A12), `docs/spec/01..03,05`.

**Status legend:** ☐ TODO · ◐ DOING · ☑ DONE · ✗ BLOCKED. All start ☐.

**Kimi dispatch contract (every product-code task):** `kimi --work-dir "<hypresent-root>" --quiet --prompt "<contents of tasks/V2-Tn.md>"` with a positive `--max-ralph-iterations`. Exit 0=ok, 75=backoff+retry, 1=halt+surface. After each dispatch the orchestrator runs `git -C <repo> diff --stat` and REJECTS the run if any changed path is outside the task's FILE ALLOWLIST.

**Critical pre-read for all tasks (flagged in changelog §0 of spec.md):** G1 and G2 are ALREADY FIXED in the current source. V2-T1/V2-T2 below are verification+residual-hardening, NOT re-fixes. Do not rewrite already-correct `color-popover.js` container logic or `serializer.js` island-count math except for the named residual extensions.

---

## Dependency graph (text)

```
V2-T0 branch ───────┬─ V2-T1 (G1 verify)            ─┐
                    ├─ V2-T2 (G2 diagnose+agent-guard prep) ─┐
                    ├─ V2-T3 (F1 server dialogs)            │
                    │     └─ V2-T4 (F1 shell wiring)         │
                    ├─ V2-T5 (F4 border: color+commands)     │
                    │     └─ V2-T6 (F4 border: popover row)  │
                    ├─ V2-T7 (S1 translate migration in commands+serializer-safe) │
                    │                                                             │
                    ├─ V2-T9 (F5 comments data: flag+setAgent+buildBlock+reanchor) │
                    │     ├─ V2-T8 (F2/F3 interaction.js + reorder.js) ◄ needs T7 AND T9
                    │     │        (T8 CALLS comments.reanchorAfterMove → T9 first; R11)
                    │     ├─ V2-T10 (F5 serializer agent-block + revised guard) (needs T2,T9)
                    │     └─ V2-T11 (F5 composer + panel toggle shell)               │
                    └─────────────────────────────────────────────────────────────┘
                                                  │
   test tasks (after their feature lands):
     V2-T12 unit: server (after T4)
     V2-T13 e2e: F1 (after T4) · V2-T14 e2e: F2 (after T8) · V2-T15 e2e: F3 (after T8)
     V2-T16 e2e: F4 (after T6) · V2-T17 e2e: F5 (after T11) · V2-T18 e2e: G1 (after T6,T11)
     V2-T19 e2e: G2 (after T10)
                                                  │
   V2-T20 integration verification (full suite + clean server run on sample) ◄ all above
                                                  │
   V2-T21 docs-sync (build-log, decision-log incl. D6 supersession, module-map, README)
```

---

## Phase 0 — Branch

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance (self-verifiable) | Parallel-safe | Status |
|----|------|----------------|-----------|-----------------|------------------------------|---------------|--------|
| **V2-T0** | Create git branch `hypresent-v2`. The sample file is gitignored by user instruction (changelog U10a) and stays untracked — never staged. | git ops only (no source files; nothing staged) | — | Branch `hypresent-v2` exists and is checked out; sample remains ignored/untracked. | `git rev-parse --abbrev-ref HEAD` == `hypresent-v2`; `git check-ignore hypresent/tecer-gsmm-introduction.html` matches; `git status --porcelain` does not list the sample. | No (root) | ☑ |

---

## Phase 1 — Blocker verification + independent features (parallel band)

All Phase-1 tasks depend only on V2-T0 and touch DISJOINT files (except the shared `commands.js`/`runtime-main.js`/`main.js` extension points noted). Parallel-safe groups are flagged.

| ID | Goal | File allowlist (✎=modify, ✚=create, ✗=delete) | Depends on | Public contract | Acceptance (self-verifiable) | Parallel-safe | Status |
|----|------|-----------------------------------------------|-----------|-----------------|------------------------------|---------------|--------|
| **V2-T1** | G1: verify the already-applied panel-survival fix; NO code change to the container mechanism. (Verification artifact only; the locking test is V2-T18.) | ✎ none — produces `docs/verification/v2/g1-confirm.md` | V2-T0 | Confirm `color-popover.js` renders into `.hyp-color-popover-container` (firstChild) and never sets `panelEl.innerHTML`. Document the final `.shell-panel` DOM per spec §G1. | The verification note quotes `color-popover.js` lines 22–27 and confirms `#outline-list`/`#comment-threads` are never wiped. No source diff. | Yes | ☑ |
| **V2-T2** | G2: confirm the island-count fix; PREP the guard for the F5 agent block by adding the head agent-block comment-node sweep to `stripClone` and the `agentBlockCount` term wiring (set to 0 until T10 supplies the block). | ✎ `runtime/js/serializer.js` | V2-T0 | `stripClone` removes any `<head>` comment node whose text contains the sentinel `===== HYPRESENT AGENT INSTRUCTIONS =====` (counted in removedNodeCount); `serialize()` computes `expectedPostCount = preCount - removedNodeCount + islandCount + agentBlockCount` with `agentBlockCount=0` for now. Island math unchanged. | With no comments and no agent block, `serialize()` still returns valid HTML (guard passes); with a comment, save still succeeds (no regression). Verified behaviorally by V2-T19 later; self-check: file parses, guard formula present. | No (T10 also edits serializer.js — sequence T2→T10) | ☑ |
| **V2-T3** | F1 server: native dialog endpoints + open-path tracking + injectable launcher seam. | ✎ `server/api.py`, ✎ `server/server.py` | V2-T0 | `api.handle_dialog_open()`, `handle_dialog_save_as(payload)`, `handle_save(payload)`, `set_open_path/get_open_path`, `set_dialog_launcher(fn)`, `_run_ps_dialog_default(kind)`; routes `POST /api/dialog-open|dialog-save-as|save`. Reuses `handle_open`/`handle_save_as` internals (no duplication). Filter `*.html;*.htm`. | `python -c "import server.api as a; a.set_dialog_launcher(lambda k: None); print(a.handle_dialog_open())"` prints `(200, {'cancelled': True})`. `handle_save` with no open path returns `{'no_open_file': True}`. | Yes (with T5,T7,T9) | ☑ |
| **V2-T4** | F1 shell: rewire toolbar to dialog flow; remove both path inputs; add Save button. | ✎ `app/index.html`, ✎ `app/js/api-client.js`, ✎ `app/js/shell/file-controls.js`, ✎ `app/js/main.js` | V2-T3 | api-client `dialogOpen()/dialogSaveAs(html)/save(html)`; `file-controls.openViaDialog(iframe)`; `main.js` wires `#open-btn`→openViaDialog, NEW `#save-btn`, `#save-as-btn`→dialogSaveAs; `deriveSaveDefault` + input reads removed. | After load, `document.querySelector('#open-path-input')` is null; `#save-btn` exists. (Behaviorally locked by V2-T13.) | No (depends T3) | ☑ |
| **V2-T5** | F4 data: border-color routing + auto-1px command + border read. | ✎ `runtime/js/color.js`, ✎ `runtime/js/commands.js`, ✎ `runtime/js/runtime-main.js` | V2-T0 | `commands.colorBorder(hypId,value)` (captures border-color/-width/-style + per-side colors; do=auto-1px-or-color; undo=restore all); `color.applyElement` routes `border-color`→colorBorder; `color.readElementBorder(hypId)→{color,mixed}`; new `element-color-read {hypId}` command returns `{color,background,borderColor,borderMixed}`. | `colorBorder` undo restores captured state on a synthetic element; `element-color-read` returns an object with the four fields. | Yes (with T3,T7,T9) | ☑ |
| **V2-T6** | F4 UI: add the Border row to the per-element color popover; populate from `element-color-read`; mixed → placeholder. | ✎ `app/js/shell/color-popover.js` | V2-T5 | `renderElement` adds a third `.hyp-color-row data-prop="border-color"`; on selection, fills Text/Background/Border from one `element-color-read`; mixed → empty input + placeholder `mixed`. | The popover DOM after selecting an element shows three rows in order Text, Background, Border. (Locked by V2-T16.) | No (depends T5) | ☑ |
| **V2-T7** | S1 translate migration: rewrite `commands.move` to use the CSS `translate` property; add `commands.reorder`. (Serializer needs no change — translate is a preserved inline style.) | ✎ `runtime/js/commands.js` | V2-T0 | `commands.move(hypId,before,after)` sets/removes `el.style.translate` (not `transform`); `commands.reorder(hypId,oldParentHypId,oldPrevHypId,oldNextHypId,newParentHypId,newNextHypId,oldTranslate)` → `{do,undo,label}` re-resolving by hyp-id, clearing/restoring `translate`. | On a synthetic element, `move(...,'10px 20px').do()` sets `style.translate==='10px 20px'` and leaves `style.transform` untouched; `reorder` undo restores parent+position+translate. | No (T5 also edits commands.js — sequence T5→T7, OR assign all commands.js edits here and have T5 import; see Parallelization note) | ☑ |
| **V2-T8** | F2+F3 core: NEW `interaction.js` (single combined Moveable + snapping + guides + drop hit-test + commit + FLIP) and NEW pure `reorder.js`; DELETE `resize.js`/`move.js`; rewire runtime-main + text-edit + selection observer seam. | ✚ `runtime/js/interaction.js`, ✚ `runtime/js/reorder.js`, ✗ `runtime/js/resize.js`, ✗ `runtime/js/move.js`, ✎ `runtime/js/runtime-main.js`, ✎ `runtime/js/text-edit.js`, ✎ `runtime/js/selection.js` | V2-T7, V2-T9 | `interaction.mount/unmount/suspend/resume/isActive/remount`; `reorder.classifyDrop/isContainer/dominantAxis` + pure kernels `midpointBefore/axisFromDisplay`; selection.js observer registry `onSelectionChange(cb)`; text-edit calls suspend/resume; runtime-main maps select→mount via the `onSelectionChange` wiring in `boot()` (R09), keeps `set-tool` shim; `interaction.js` CALLS `comments.reanchorAfterMove` (defined by V2-T9, R11 — T8 does NOT touch comments.js). Drop below 3px = no-op (R05); FLIP excludes dragEl (R10). | Selecting an element creates exactly one `#hyp-interaction-wrapper` with a Moveable that is both draggable and resizable; `resize.js`/`move.js` files are deleted; `interaction.js` does not import `selection.js`; `node --check` passes on all touched JS. (Behaviorally locked by V2-T14/T15.) | No (large; depends T7 + T9; comments.js NOT in allowlist) | ☑ |
| **V2-T9** | F5 data: `agentInstruction` flag + `setAgentInstruction` + `buildAgentBlock` + `reanchorAfterMove` + island round-trip; runtime-main `tag-agent` command and `add-comment` flag pass-through. | ✎ `runtime/js/comments.js`, ✎ `runtime/js/runtime-main.js` | V2-T0 | `comments.add(hypId,body,author,agentInstruction=false)`; `setAgentInstruction(commentId,bool)` (undoable); `buildAgentBlock()→string|null` (research-04 Option A, single `escapeAgentBlock` applied to EVERY interpolated value incl. path/nativeId — R06, unresolved replies as `reply:` lines, resolved excluded); `reanchorAfterMove()` (multi-signal regen for ALL threads, unresolved→unanchored never deleted — R11/R14); `toJson/writeIsland/load` round-trip the flag; runtime-main registers `tag-agent` and passes `agentInstruction` to `add`. | `add(id,'x','A',true)` then `toJson()[0].agentInstruction===true`; `buildAgentBlock()` with one agent thread returns a string containing the sentinel; with none returns null; `comments.js` exports `reanchorAfterMove`. | No (sole owner of comments.js changes incl. `reanchorAfterMove`; MUST run before T8) | ☑ |
| **V2-T10** | F5 serializer: insert the agent block as first child of `<head>` and set `agentBlockCount=1`; wire to `comments.buildAgentBlock`. | ✎ `runtime/js/serializer.js` | V2-T2, V2-T9 | After island re-embed, call `buildAgentBlock()`; if non-null, `head.insertAdjacentHTML('afterbegin', block)` and `agentBlockCount=1`; guard uses the T2 formula; existing-block sweep (T2) prevents duplication. | With one agent thread, `serialize()` output contains the block as the first `<head>` child and returns non-null; with none, no block and still non-null. (Locked by V2-T19.) | No (depends T2,T9) | ☑ |
| **V2-T11** | F5 shell: NEW `comment-composer.js` anchored popover (replaces prompt for add AND reply); panel per-thread "For agents" checkbox → `tag-agent`. | ✚ `app/js/shell/comment-composer.js`, ✎ `app/js/main.js`, ✎ `app/css/shell.css` (NOT `app/index.html` — composer mounts at runtime) | V2-T9 | `openComposer({rect,mode,commentId?,onSubmit})`; keys Esc=cancel, Ctrl/Cmd+Enter=save, Enter=newline; `main.js` add/reply use it; `createThreadEl` gains a "For agents" checkbox calling `tag-agent`; minimal CSS for `.hyp-comment-composer`. | After clicking `#comment-btn` with a selection, a `.hyp-comment-composer` (not `window.prompt`) is in the parent DOM with a textarea + checkbox + Save/Cancel. (Locked by V2-T17.) | No (depends T9) | ☑ |

> **Parallelization note (shared files):** `commands.js` is edited by V2-T5 (colorBorder) and V2-T7 (move/reorder) — serialize as T5→T7 (or give T7 all commands.js edits). `comments.js` is edited ONLY by V2-T9 (agent flag/block + `reanchorAfterMove`); V2-T8 does NOT touch it — it only CALLS `comments.reanchorAfterMove`, so **V2-T9 MUST run before V2-T8** (R11) for the import to resolve. `runtime-main.js` is edited by T5 (`element-color-read`), T9 (`tag-agent`, `add-comment` flag, `setAgentInstruction` import), and T8 (interaction imports, `set-tool` shim, `onSelectionChange` wiring in `boot()`) — each ADDS distinct registrations/imports; serialize T5→T9→T8. `selection.js` is edited ONLY by T8 (observer registry). `text-edit.js` is edited ONLY by T8. `main.js` edited by T4 and T11 — serialize T4→T11. `app/index.html` edited ONLY by T4 (T11 does NOT edit index.html). The safe global order for the shared-file tasks is: **T3→T4, T5→T7, T9→T8, T5→T9→T8 (runtime-main.js), T9→T10, T9→T11**, with T1/T2/T3 freely parallel up front.

---

## Phase 2 — Test implementation (each after its feature lands)

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Parallel-safe | Status |
|----|------|----------------|-----------|-----------------|-----------|---------------|--------|
| **V2-T12** | Unit suite: server dialogs + save (test-plan Layer 1). | ✚ `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_server_dialogs.py`, `tests/unit/test_server_save.py` | V2-T4 | Implements U-DLG-1..8, U-SAVE-1..3 (test-plan §Layer 1). stdlib `unittest` only. | `python -m unittest discover -s tests/unit -p "test_*.py"` passes; no third-party import. | Yes | ☑ |
| **V2-T13** | Playwright F1 suite. | ✚ `tests/e2e/__init__.py`, `tests/e2e/conftest_helpers.py`, `tests/e2e/test_f1_dialogs.py` | V2-T4 | E-F1-1..6 (test-plan). Server with `HYP_TEST_DIALOG=1` + `/api/_test/set-dialog` seam; fixture-copy helper. | Suite passes headless on port 8781. | After T12 (shares conftest_helpers — T13 creates it) | ☑ |
| **V2-T14** | Playwright F2 suite. | ✚ `tests/e2e/test_f2_select_guides.py` | V2-T8, V2-T13 | E-F2-1..8. | Passes on port 8782. | Yes (vs T15-T19) | ☑ |
| **V2-T15** | Playwright F3 suite (incl. verbatim 3-box). | ✚ `tests/e2e/test_f3_reorder_reparent.py` | V2-T8, V2-T13 | E-F3-1..11. | Passes on port 8783. | Yes | ☑ |
| **V2-T16** | Playwright F4 suite. | ✚ `tests/e2e/test_f4_border.py` | V2-T6, V2-T13 | E-F4-1..7. | Passes on port 8784. | Yes | ☑ |
| **V2-T17** | Playwright F5 suite. | ✚ `tests/e2e/test_f5_comments.py` | V2-T11, V2-T13 | E-F5-1..13. | Passes on port 8785. | Yes | ☑ |
| **V2-T18** | Playwright G1 suite (panel survival across two opens). | ✚ `tests/e2e/test_g1_panel_survival.py` | V2-T6, V2-T11, V2-T13 | E-G1-1..3. | Passes on port 8786. | Yes | ☑ |
| **V2-T19** | Playwright G2 suite (save-with-comments + agent block guard). | ✚ `tests/e2e/test_g2_save_with_comments.py` | V2-T10, V2-T13 | E-G2-1..5. | Passes on port 8787. | Yes | ☑ |

---

## Phase 3 — Integration + docs

| ID | Goal | File allowlist | Depends on | Public contract | Acceptance | Parallel-safe | Status |
|----|------|----------------|-----------|-----------------|-----------|---------------|--------|
| **V2-T20** | Integration verification: run the FULL suite + a clean server run on the sample; capture results. | ✚ `tests/e2e/test_exit_smoke.py`, ✚ `docs/verification/v2/result.md` | V2-T12..T19 | Implements E-EXIT-1..3; run `python -m unittest discover -s tests -p "test_*.py" -v`; start the server once and confirm `GET /app/` 200 + zero editor-origin console errors opening the sample. | Entire suite green; results logged; clean server run confirmed. | No | ☑ 67/67 OK |
| **V2-T21** | Docs-sync: append build-log entry; append decision-log rows incl. the **D6 supersession row**; update `docs/spec/03-module-map.md` for new/changed modules; update README usage (F1 dialogs, F4 border, F5 agent comments, modeless F2/F3). | ✎ `docs/build-log.md`, ✎ `docs/decision-log.md`, ✎ `docs/spec/03-module-map.md`, ✎ `README.md` | V2-T20 | Build-log: one v2 entry per the existing format. Decision-log: APPEND-ONLY a new row recording D6 (CSS `translate` supersedes the LETTER of v1-D2, preserving intent) — never edit existing rows. Module-map: add `interaction.js`, `reorder.js`, `comment-composer.js`; mark `resize.js`/`move.js` removed; note comments/serializer/color/commands/api/server changes. README: update the "How to use" steps (Open/Save/Save As dialogs, modeless select→handles, Border row, agent comments) and the repository-layout table. | Decision-log has the new D6-supersession row, existing rows untouched (`git diff` shows only additions); module-map lists the new modules; README reflects the new UX. | No | ☑ |

---

## Notes

- **Surgical-change fence:** no task may modify a file outside its allowlist. G1/G2 tasks (V2-T1, V2-T2) do NOT re-fix already-correct code (spec §0); V2-T1 is verification-only; V2-T2 adds the agent-block guard term + head-comment sentinel sweep (S26) AND the `getCommentJson` empty-store authority fix (R04) — it still does NOT alter the correct `islandCount = countAllNodes(island)` line or the strip semantics.
- **Review-01 fixes applied:** all BLOCKER/MAJOR + small MINOR fixes from `docs/improvements-2026-06/review-01-spec-plan.md` are reflected here and in spec/test-plan/task files; the mapping is `docs/improvements-2026-06/review-01-fixes.md`. Key structural deltas: reanchor ownership moved entirely to V2-T9 (V2-T8 only calls it, comments.js out of T8's allowlist); the selection→interaction observer is wired in `runtime-main.boot()` to break the import cycle (V2-T8 no longer has interaction.js import selection.js); all task edits are content-anchored, never line-numbered.
- **D6 supersession** is recorded ONLY by appending a decision-log row in V2-T21 (never editing v1-D2). The translate migration itself lands in V2-T7/T8.
- **`docs/spec/04-implementation-plan.md` is never touched** (v1, read-only).
- **Dependency-free runtime:** Playwright is dev/test only (`tests/` tree). No vendored lib added to `app/js/vendor/`.

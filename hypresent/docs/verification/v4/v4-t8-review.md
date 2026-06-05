# V4-T8 Post-Commit Review — R13 Comment edit + delete (`9a0bd59`)

**Reviewer:** post-commit judge (read-only on code; sole write = this file).
**Commit:** `9a0bd59d846750b43382bd27d739b087a0490867` "[v4-t8] R13: comment edit + delete (comments & replies, atomic undo, island sync)".
**Sequencing:** R10→R12→R11→**R13**→R14 (spec L9); R14 not yet landed.
**Inputs read:** `git show 9a0bd59` (+ per-file diffs); `spec.md` R13 (contract 1–7, change map, edge cases, risk notes) + R14 (test list, for finding-3 severity calibration) + cross-cutting I1–I7 + Amendments; `test_r13_comment_edit_delete.py` (committed == subject of run); `tests/e2e/fixtures/agent-comments.html`; `v4-t8-run.txt`; `v4-t8-BUG.md`; current state of `comments.js`, `runtime-main.js`, `app/js/main.js`, `comment-composer.js`; `serializer.js` (to confirm untouched + trace the block-rebuild path); `history.js`; `commands.js::comment`; `test_f5_comments.py` (regression-collision check).
**Anchor discipline:** line numbers are hints against the tree as read 2026-06-05; edits are located by quoted content, not line number.

**OVERALL VERDICT: CLEAN.** All seven verification points are satisfied with file:line evidence. The four ops are undoable history commands via the `commands.comment` factory; delete-reply and delete-root undo are index-safe; `editedAt` is stamped on edits, persisted, and serialized; bridge registrations and panel affordances are reachable for BOTH roots and replies; the For-agents checkbox is hidden in edit mode; island + head agent-block rebuild on save from the live store; the serializer is untouched (R14 owns it); undo fidelity is asserted by tests; the F5+G2 regression evidence is consistent with the diff (button order and island shape preserved). Findings below are all **MINOR** (test-coverage gaps the spec already routes to R14 or accepts as bounded, plus one stale docstring) — none ship-blocking.

---

## 1. Four ops as UNDOABLE history commands via the factory — **PASS**

All four live in `comments.js` as exported functions, each building `do`/`undo` closures wrapped by `makeCommentCommand` (imported `comment as makeCommentCommand` from `commands.js`, `comments.js:18`) and pushed through `historyPush` (imported `push as historyPush` from `history.js`, `comments.js:17`). `commands.js:378` `comment(label, doFn, undoFn)` returns `{do, undo, label}` — a thin command object; `history.push` (`history.js:39-53`) runs `cmd.do()` once, appends, truncates redo tail. So each op applies exactly once on call and is undoable/redoable through the single linear stack (cross-cutting I4 — "all new mutating ops flow through the single linear history stack").

| Op | Location | Undoable? | editedAt | Index-safe undo |
|----|----------|-----------|----------|-----------------|
| `editComment` | `comments.js:522-543` | `historyPush(makeCommentCommand("edit-comment",…))` `:541` | `:528` sets `thread.editedAt = new Date().toISOString()` | n/a |
| `deleteComment` | `comments.js:545-563` | `:561` | n/a | `undo` `:556` `threadStore.splice(idx,0,saved)` then `reanchorAll()` `:558` — restores at ORIGINAL index, re-renders marker |
| `editReply` | `comments.js:565-587` | `:585` | `:574` sets `replies[i].editedAt` | n/a |
| `deleteReply` | `comments.js:589-610` | `:608` | n/a | `undo` `:603` `thread.replies.splice(replyIndex,0,saved)` — restores at ORIGINAL ordinal (S3-11) |

**editComment undo G4-compliance (the spec's most-flagged hazard):** `before = {body, editedAt}` captured at call time (`:525`); `undo` `:535` `if (before.editedAt === undefined) delete thread.editedAt; else thread.editedAt = before.editedAt` — DELETES the key when absent pre-edit rather than setting `undefined`, exactly per change-map G4. Asserted end-to-end by E-R13-2 (`assertNotIn("editedAt", thread)` after undo).

**editReply undo fidelity:** `before = {...thread.replies[replyIndex]}` (`:571`) is a shallow snapshot taken BEFORE `do` mutates the live object in place; `undo` `:580` reassigns `thread.replies[replyIndex] = before`. Restores the exact prior `{author, body, createdAt, editedAt?}`. Correct.

**deleteComment marker handling:** `do` `:550` `removeMarker(commentId)` then splice; `undo` `:558` `reanchorAll()` rebuilds markers for all live threads by `matchAnchor`, re-rendering the restored thread's marker (matches change-map "`reanchorAll()` (re-renders the marker)"). E-R13-4 asserts marker count returns to baseline after undo.

## 2. Bridge registrations + panel affordances; composer reuse + checkbox hidden — **PASS**

**Bridge (`runtime-main.js`).** Four new commands registered next to `reply-comment` (`runtime-main.js:230-256`), with the four fns imported `:16-19`:
- `edit-comment` requires `{commentId, body}` (`:230-235`); `delete-comment` requires `{commentId}` (`:237-242`); `edit-reply` requires `{commentId, replyIndex, body}` (`:244-250`); `delete-reply` requires `{commentId, replyIndex}` (`:252-257`).
- **G3 honored — no validator requires `author`** (the edit-mode `onSubmit(text)` passes none). **`replyIndex` validated as `typeof payload.replyIndex !== "number"`** (`:247`, `:254`), so index `0` does NOT throw (the spec's explicit falsy-check trap is avoided).

**Panel (`app/js/main.js` `createThreadEl`).** Edit/Delete reachable for BOTH levels:
- ROOT: Edit `:194-213` (opens composer `mode:"edit"`, `initialText: thread.body`, `onSubmit → bridge.command("edit-comment",…)` then `refreshCommentPanel()`); Delete `:215-227` (`bridge.command("delete-comment",…)` then refresh). Both `e.stopPropagation()`.
- REPLY (inside the replies loop, now index-tracked via `for (let i=…)` `:83`): per-reply Edit `:107-126` (`edit-reply` with `replyIndex: i`) and Delete `:128-140` (`delete-reply` with `replyIndex: i`). Both `e.stopPropagation()`.

**Composer reuse in prefilled edit mode (`comment-composer.js`).** `openComposer` gains `initialText=""` param (`:26`); `mode==="edit"` sets `textarea.value = initialText` (`:52-54`) and placeholder `"Edit comment"` (`:51`). E-R13-1/E-R13-6 assert prefill (`ta.input_value() == "original" / "r1"`). `submit()` (`:83-89`) calls `onSubmit(text, agent)`; in edit mode `agentCheckbox` is null so `agent` is `false` (irrelevant).

**For-agents checkbox HIDDEN in edit mode (Risk-12, contract 7).** The checkbox block is gated `if (mode === "new")` (`comment-composer.js:59-67`) — so it is absent in BOTH `edit` and `reply` modes, and `agentCheckbox` stays `null`. E-R13-7 asserts `.hyp-composer-agent` / `input[type=checkbox]` count === 0 in edit mode, AND that the composer stays in-viewport on a low anchor (the existing flip/clamp at `:115-126` is mode-independent — contract edge-case "edit-mode does not regress flip-clamp" holds).

## 3. Island sync + head agent-block REBUILD on save — **PASS** (test covers the edit case; see Finding A for the delete-case gap)

**Island round-trip.** `editedAt` was added to BOTH persisted serializers: `writeIsland` field set (`comments.js:269`) and `toJson` field set (`:397`). Every op's `do`/`undo` calls `writeIsland()` (e.g. `:529`, `:537`, `:552`, `:575`, `:598`), so edits/deletes persist into the `#hyp-comments` island immediately. On reopen, `load` spreads `{...t}` (`:381`) so `editedAt` survives the load→toJson cycle. E-R13-1 asserts the island body == `"edited body"` with `editedAt` truthy; E-R13-3/-5 assert deletes/reply-deletes in the island.

**Head agent-block rebuild mechanism (quoted).** The block is NOT mutated by the ops; it is **re-derived on every save** by the serializer:
> `serializer.js:281` `const agentBlockHtml = getAgentBlockHtml();` → `:74-80` `getAgentBlockHtml()` returns `buildAgentBlock()` → `:285` `headEl2.insertAdjacentHTML("afterbegin", agentBlockHtml)` (inserted as first child of `<head>` on each `serialize()`).

`buildAgentBlock` (`comments.js:618-648`) reads the **live store**: `:619` `threadStore.filter((t) => t.agentInstruction === true && t.resolved !== true)`, then `:639` `instruction: ${escapeAgentBlock(t.body)}` and `:641` `reply: …` from the live thread/reply objects. The island JSON re-embed is likewise live: `serializer.js:256/86-93` `getCommentJson()` → `comments.toJson()`. So an edit to `thread.body` re-emits the new `instruction:` on the NEXT save with NO extra wiring (S3-12), and a deleted/resolved agent thread vanishes from both the filter and the block (contract 6 + edge "Delete an agent-tagged root"). `buildAgentBlock` still emits the OLD `anchor:` line (`:638`) — correct: rewriting that line is **R14's** job (change-map: "No structural change for R13… R14 rewrites the anchor line").

**Test asserting agent-block content after an EDIT? — YES.** E-R13-8 (`test_e_r13_8_agent_block_reflects_edited_comment`) saves an agent-tagged comment (`assertIn("instruction: do X")`), edits body to "do Y", re-saves, and asserts `assertIn("instruction: do Y")` AND `assertNotIn("instruction: do X")`. This directly exercises the buildAgentBlock-reads-live-store rebuild. The gap the task flagged (no test for agent-block-after-edit) does **not** exist. The DELETE-of-agent-root → block-entry-gone case is NOT asserted by an R13 test — see Finding A (MINOR, R14 territory).

## 4. Serializer untouched in this commit — **PASS (confirmed)**

`git diff 9a0bd59~1 9a0bd59 -- hypresent/runtime/js/serializer.js hypresent/app/js/serializer.js` returns EMPTY. `serializer.js` is not in `--stat`. It already imported `buildAgentBlock` (`:24`) and calls it via `getAgentBlockHtml` (`:76`) from the pre-existing V2-T10 wiring. R13 relies on the serializer's existing rebuild path without modifying it; the R14 stamping rewrite (spec change-map: `serialize()` try/finally + `agentStampMap`) is correctly NOT present here.

## 5. Undo/redo: single undo restores prior body / restores deleted item at correct position — **PASS** (redo untested; spec accepts — Finding C)

Single-undo restoration asserted (quoted):
- **Edit undo** — E-R13-2: after `bridge_command(self.page, "undo")`, `self.assertEqual(thread["body"], "original")` and `self.assertNotIn("editedAt", thread)`.
- **Delete-root undo** — E-R13-4: after undo, `self.assertEqual(len(threads), 2)`, `assertIn(id0, ids)`, `assertIn(id1, ids)`, panel count `== 2`, and `after_markers == before_markers`.
- **Delete-reply undo restores at ORIGINAL index** — E-R13-5: deletes the FIRST of two replies (`assertEqual([…], ["r2"])`), undoes, then `self.assertEqual(bodies, ["r1", "r2"])` — index 0 restored ahead of `r2`, proving `splice(i,0,saved)` not append (Risk-5 guard).

`history.js` undo (`:55-61`) invokes `cmd.undo()` at cursor and steps back; one op == one command == one undo step (contract "One undoable history entry" per clause). Redo (`:63-69`) re-runs `cmd.do()`.

## 6. Regression: F5+G2 (18 passed) + add/reply/resolve behavior — **PASS** (evidence consistent; collision-checked)

`v4-t8-run.txt:37-64` shows `test_f5_comments.py` + `test_g2_save_with_comments.py` → **18 passed**, and `:66-71` the scoped full gate **137 passed, 1 skipped** (R11 RED set excluded by orchestrator sanction per `v4-t8-BUG.md:49-59`; the 2 failures are the pre-existing R11 V4-T5 RED set, R11 GREEN lands V4-T6 — not R13-caused; confirmed those tests live only in `test_r11_resize_guides_equal_size.py`).

**Spot-verified the one real collision risk — action-button ordering.** `test_f5_comments.py:232-234` does `btns = query_selector_all("#comment-threads .comment-action-btn"); resolve_btn = btns[1]  # second is Resolve (first is Reply)`. R13 inserts Edit/Delete into the SAME `actions` row, so I verified the append order in `createThreadEl`: Reply `:175` → Resolve `:192` → **Edit `:213` → Delete `:227`** → agent-label `:249`. Indices 0 (Reply) and 1 (Resolve) are unshifted; the new buttons append AFTER. The `repliesDiv` (each reply carries its own `.comment-action-btn` Edit/Delete) is BUILT before `actions` but APPENDED after it (`:251` actions, then `:252-254` `if (repliesDiv) div.appendChild(repliesDiv)`), so for a fresh single-thread (zero replies) `.first` and `btns[1]` are unambiguous — and even with replies present, root actions precede replies in DOM order, keeping `.first == Reply`. No existing assertion breaks. (Grep confirms only `test_f5_comments.py` and `test_r13_…py` reference `.comment-action-btn` across `tests/`.)

**Behavior change to add/reply/resolve flows?** One additive change: the `dirty-changed` bridge handler in `main.js` now calls `refreshCommentPanel()` (`:317-321`), where previously it only set the title. Effect: every store mutation (add/reply/resolve/tag + the four new ops, and their undos) now re-renders the panel. `refreshCommentPanel` (`:293-301`) is an idempotent read-render (`comments-read` → `renderCommentPanel`). This is necessary for edit/delete to reflect in the panel after a bridge op resolves, and is benign for the legacy flows (those already called `refreshCommentPanel()` explicitly in their button handlers; the extra dirty-changed refresh is redundant-but-harmless). F5/G2 green confirms no regression. No add/reply/resolve op semantics changed in `comments.js` (those functions are byte-identical pre/post in the diff).

## 7. The 8 R13 tests vs spec contracts — **PASS** (full contract-1..7 coverage; gaps are MINOR — Findings A–C)

| Spec contract | Covering test(s) | Strength |
|---------------|------------------|----------|
| 1 Edit root | E-R13-1 | body + `editedAt` truthy + panel body re-render |
| 2 Delete root | E-R13-3 | store len, surviving id, panel count, marker count −1 |
| 3 Edit reply | E-R13-6 | reply body + `editedAt` truthy + prefill |
| 4 Delete reply | E-R13-5 (delete half) | order after delete == `["r2"]` |
| 5 Undo fidelity | E-R13-2, -4, -5 | body+editedAt-absence; thread+marker; reply index |
| 6 Agent-block sync (edit) | E-R13-8 | `instruction:` flips X→Y, old gone |
| 7 Prefill + no checkbox | E-R13-1/-6 (prefill), E-R13-7 (no checkbox + viewport) | direct |

No assertion is weakened relative to the contract text it covers (e.g. E-R13-2 asserts the EXACT prior string and key ABSENCE, not mere truthiness; E-R13-5 asserts ORDER, not just length). Synthetic fixture only (`agent-comments.html`, native ids `p-lead`/`p-arch`/`li-2` used by `_select`) — I7 honored. Gaps below.

---

## Finding A — no test for DELETE-of-agent-root → block entry gone — **MINOR**

Contract 6 / edge "Delete an agent-tagged root" (block entry + `data-hyp-agent` residue gone) is NOT asserted by an R13 test. E-R13-8 covers only the EDIT case. **Severity held at MINOR** because (i) the mechanism is the same live-store filter (`buildAgentBlock` `:619-621` `filter(agentInstruction && !resolved)`) that E-R13-8 and the existing `test_f5_comments.py::test_resolved_agent_thread_removes_block` already prove drops a non-matching thread from the block; deleting splices the thread out of `threadStore` entirely, so the filter cannot include it. (ii) The `data-hyp-agent` stamping/residue assertions belong to **R14** — spec R14 contract 5 ("Resolved/deleted don't stamp") + edge "Edit/delete of an agent thread between saves (R13×R14)" + **E-R14-6** idempotence explicitly own the delete-of-agent stamp/residue verification. Flagging above MINOR would duplicate R14's chartered coverage. **No fix required for R13;** optionally R14's test set should include an explicit delete-agent-root save assertion (it already plans the edit/delete-between-saves case).

## Finding B — delete-reply marker-count decrement not directly asserted — **MINOR**

Contract 4 says delete-reply decrements the marker count (`1 + replies.length`). `deleteReply.do` calls `updateMarkerState(commentId)` (`comments.js:599`), which recomputes the badge `String(1 + thread.replies.length)` (`:343`). E-R13-5 asserts the island reply array shrinks but does NOT read the marker badge text. Low risk (the badge formula is shared with `reply`/`renderMarkerFor` and is exercised by F5). No fix required.

## Finding C — redo path untested; edit→undo→redo re-stamps a new `editedAt` — **MINOR (spec-accepted)**

No R13 test exercises `redo`. `history.redo` (`:63-69`) re-runs `cmd.do()`, so an edit redo re-applies `newBody` with a FRESH `new Date().toISOString()` (`editComment.do:528`). Spec edge "Edit then undo then redo" **explicitly accepts** this ("redo re-stamps… `editedAt` reflects the most recent application time; body content is deterministic"). Since the behavior is by-design and the command pattern guarantees redo correctness for body content, the missing redo test is a coverage gap only, not a defect. No fix required.

## Finding D — `comment-composer.js` docstring stale — **MINOR (doc-only, non-shipping)**

The header contract block (`comment-composer.js:7-13`) still documents `mode: 'new' | 'reply'` and omits both `initialText` and the `edit` mode that the function now implements (`:26`, `:51-54`). The code is correct; only the JSDoc drifted. Recommend (non-blocking): add `'edit'` to the mode list and document `initialText : prefill body when mode === 'edit'`. No behavioral impact; not a commit blocker.

---

## Cross-cutting invariant spot-check (I1–I7)

- **I3** (every injected attribute is `data-hyp-*`, classes `hyp-`): the composer's transient dataset keys `hypAnchorTop`/`hypBelowTop` are deleted before append (`:127-128`); no new persisted `hyp-`/`data-hyp-` surface added by R13. ✓
- **I4** (all mutations through the single history stack; serialize never pushes history): the four ops each `historyPush` once; none mutate outside a command; serializer unchanged (no history push). ✓
- **I6** (`test_r2_resize_real`, `test_f2_select_guides`, `test_f5_comments`, `test_g2_save_with_comments` stay green): F5+G2 green in run.txt; the scoped full gate is green except the sanctioned R11 RED set. ✓
- **I7** (synthetic fixtures only): `agent-comments.html`; no `tecer-*`. ✓

**FINAL: CLEAN — ship.** Findings A–D are MINOR (three are test-coverage gaps the spec routes to R14 or accepts as bounded; one is a stale docstring). No correctness defect, no contract violation, no regression.

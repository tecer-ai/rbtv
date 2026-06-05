---
name: hypresent-v4
overview: "Hypresent Session-3 improvement cycle (improvements-2026-06-r3) — fix the resize/comment/agent-anchor gaps the owner hit in real use of the v3 build: R10 resize amplification + dead-zone (dragged edge tracks the cursor 1:1 on flex-grow items, every layout context), R12 Alt-held symmetric resize (explicit center-origin via Moveable fixedDirection), R11 resize guides + equal-size matching (position guides return for free post-R10 + net-new equal-size snap/hint), R13 comment edit+delete (root + replies, island + agent-block sync), R14 data-hyp-agent stamping + rewritten head block + fresh-agent legibility. Executor: Kimi (non-reasoning); every task is one bounded, self-contained dispatch with a file allowlist enforced by post-run git diff. TDD AT TASK GRANULARITY: each R is a RED task (fixtures + tests, run against current master, asserted-RED demonstrated) then a GREEN task (product fix VERBATIM from spec, rerun targeted + full suite, local commit). Sequencing R10 → R12 → R11 → R13 → R14 (AD7), then T-final docs-sync + clean-server-run evidence."
---

# Hypresent v4 — Execution Plan

> Format mirrors `docs/plan/hypresent-v3/hypresent-v3-plan.md` (READ-ONLY reference). This is a NEW plan; it NEVER modifies any v1/v2/v3 artifact.
> Per-task self-contained Kimi prompt bodies live in `tasks/V4-T*.task.md`. Each prompt INLINES every spec contract, verbatim code block, helper body, and fixture HTML it needs — the executor reads NOTHING else.
> Grounding: `docs/improvements-2026-06-r3/spec.md` (S3-1..S3-17, R10–R14 change maps + verbatim code), `docs/improvements-2026-06-r3/test-plan.md` (E-R10..E-R14 + regression set + red-first gate), `docs/improvements-2026-06-r3/user-feedback.md` (D1–D6, AD7 sequencing, D5 scope). `review-01-fixes.md` is the conflict tiebreaker (already folded into the spec/test-plan as read).

**Status legend:** ☐ TODO · ◐ DOING · ☑ DONE · ✗ BLOCKED. All start ☐.

**Branch:** `master` continues (D6 — owner AFK; Kimi starts/owns the server; per-fix commits on `master`; NEVER push, NEVER merge, NEVER create a new branch).

**Approver:** the ORCHESTRATOR is the sole approver (no interactive user this run). Where `rbtv-planning` mandates an interactive user gate, it is satisfied by the orchestrator's per-R diff gate + Opus review below.

---

## Kimi dispatch contract (every task)

Dispatch each task via stdin-pipe (absorbs the ≤55KB self-contained bodies; avoids `--prompt` arg-length limits):

```powershell
Get-Content "docs/plan/hypresent-v4/tasks/<TASK>.task.md" -Raw |
  kimi --work-dir "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\hypresent" `
       --agent-file ".kimi-agent/code-agent.yaml" `
       --quiet --max-ralph-iterations 30 --print
$c = $LASTEXITCODE
if ($c -eq 75) { Start-Sleep 10; <re-dispatch> }     # retryable: rate-limit/timeout/5xx
elseif ($c -ne 0) { <halt + surface> }                # 1 = non-retryable: halt
```

`--quiet` = `--print --output-format text --final-message-only` (non-interactive, auto-approves every tool call; Kimi has NO native allowlist — confinement is the orchestrator's job). `--agent-file` strips web/fetch tools. After EVERY dispatch the orchestrator runs `git -C <repo> diff --stat` and REJECTS the run if any changed path is outside that task's `allowlist`. Kimi evidence files go under `docs/verification/v4/`.

**D14 discipline (binding, restated in every task body):** on a blocking product bug or a RED/GREEN mismatch, STOP and write a `…-BUG.md` under `docs/verification/v4/` naming the failing assertion + observed-vs-expected numbers — NEVER patch outside the allowlist, NEVER weaken a test to make it pass, NEVER create files at the workspace root (scratch → tempdir).

**Anchor discipline (binding):** every `file:line` hint is NON-BINDING (the live tree drifts). Every task locates each edit by the QUOTED CODE CONTENT inlined in its body, never by line number. If a quoted anchor is not found verbatim, STOP and report.

**Self-contained bodies:** the executor is non-reasoning and reads nothing outside the task file. Each task INLINES the relevant spec sections (contracts, verbatim change-map code, helper definitions, fixture HTML) into its Context Snapshot / Implementation Requirements. spec.md is NEVER referenced by path as the primary instruction — it is inlined.

---

## Per-R TDD cycle (the binding loop for every R10–R14)

Each R is two Kimi tasks plus two orchestrator gates:

1. **RED task** (`…-red`) — CREATE the synthetic fixtures (under `tests/e2e/fixtures/`) + the R's test file(s) + any `conftest_helpers.py` helper the tests need. Run the new tests against **CURRENT master** (the fix NOT yet applied). The task body lists EXPLICIT expected-RED assertions (citing the pre-fix numbers from spec/test-plan) and expected-GREEN assertions (healthy paths that must already pass). RECORD observed numbers to `docs/verification/v4/<task>-red.txt` (and append to `docs/improvements-2026-06-r3/red-first-log.md` for R10, the binding red-first gate). **If the observed RED/GREEN distribution mismatches the listed expectation → STOP + write `…-BUG.md` (D14).** NEVER weaken a test to pass. Test files touch ONLY `tests/` (+ `tests/e2e/fixtures/` + `conftest_helpers.py`).
2. **Orchestrator RED gate** — verify the diff is test-only + the recorded RED numbers match the task's expected-RED list. Approve → dispatch the GREEN task.
3. **GREEN task** (`…-green`) — apply the product fix VERBATIM from the inlined change-map blocks (product files only). Rerun the R's targeted tests, THEN the FULL suite (`python -m pytest tests/` or the unittest discover equivalent). On all-green, LOCAL git commit `[v4-t<N>] R<n>: <short description>` (local-only, never push). Return DONE / files-changed / tests-run / commit-hash / concerns.
4. **Orchestrator diff gate + Opus review** — confirm the GREEN diff is allowlist-confined, the targeted tests flipped RED→GREEN, the full suite is green, and the commit landed. Dispatch Opus (`reviewer: claude-opus`) for a fix-forward review of the landed diff. Any Opus finding → a fix-forward follow-up (never `git reset`, never amend — the vault/repo discipline is fix-history-forward).

The cycle repeats R10 → R12 → R11 → R13 → R14, each landing its own commit before the next R's RED task starts (no interleaving — R12 layers onto a verified-1:1 R10; AD7).

---

## Task table

| ID | R | Kind | Allowlist summary | test_command | Depends on |
|----|---|------|-------------------|--------------|-----------|
| **V4-T1** | R10 | RED | ✚ `tests/e2e/fixtures/{flow-grow,flow-grow-deadzone,grid-healthy}.html`, ✚ `tests/e2e/test_r10_resize_flex.py`, ✎ `tests/e2e/conftest_helpers.py` (+`copy_synthetic`/`SYN_DIR`), ✚ `docs/verification/v4/v4-t1-red.txt`, ✚/✎ `docs/improvements-2026-06-r3/red-first-log.md` | `python -m pytest tests/e2e/test_r10_resize_flex.py -v` (vs current master) | — |
| **V4-T2** | R10 | GREEN | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t2-run.txt` | targeted: `python -m pytest tests/e2e/test_r10_resize_flex.py -v` · full: `python -m pytest tests/ -q` | V4-T1 |
| **V4-T3** | R12 | RED | ✚ `tests/e2e/test_r12_alt_symmetric.py`, ✚ `docs/verification/v4/v4-t3-red.txt` (reuses `flow-grow.html`) | `python -m pytest tests/e2e/test_r12_alt_symmetric.py -v` (vs post-R10 master) | V4-T2 |
| **V4-T4** | R12 | GREEN | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t4-run.txt` | targeted: `… test_r12_alt_symmetric.py -v` · full: `python -m pytest tests/ -q` | V4-T3 |
| **V4-T5** | R11 | RED | ✚ `tests/e2e/test_r11_resize_guides_equal_size.py`, ✚ `docs/verification/v4/v4-t5-red.txt` (reuses `flow-grow.html`) | `python -m pytest tests/e2e/test_r11_resize_guides_equal_size.py -v` (vs post-R12 master) | V4-T4 |
| **V4-T6** | R11 | GREEN | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t6-run.txt` | targeted: `… test_r11_resize_guides_equal_size.py -v` · full: `python -m pytest tests/ -q` | V4-T5 |
| **V4-T7** | R13 | RED | ✚ `tests/e2e/test_r13_comment_edit_delete.py`, ✚ `docs/verification/v4/v4-t7-red.txt` (reuses `agent-comments.html` — created here) + ✚ `tests/e2e/fixtures/agent-comments.html` | `python -m pytest tests/e2e/test_r13_comment_edit_delete.py -v` (vs current master) | V4-T6 |
| **V4-T8** | R13 | GREEN | ✎ `runtime/js/comments.js`, ✎ `runtime/js/runtime-main.js`, ✎ `app/js/main.js`, ✎ `app/js/shell/comment-composer.js`, ✚ `docs/verification/v4/v4-t8-run.txt` | targeted: `… test_r13_comment_edit_delete.py -v` · full: `python -m pytest tests/ -q` | V4-T7 |
| **V4-T9** | R14 | RED | ✚ `tests/e2e/test_r14_agent_stamping.py`, ✚ `tests/e2e/test_r14_legibility.py`, ✚ `docs/verification/v4/v4-t9-red.txt` (reuses `agent-comments.html`) | `python -m pytest tests/e2e/test_r14_agent_stamping.py tests/e2e/test_r14_legibility.py -v` (vs current master) | V4-T8 |
| **V4-T10** | R14 | GREEN | ✎ `runtime/js/comments.js`, ✎ `runtime/js/serializer.js`, ✚ `docs/verification/v4/v4-t10-run.txt` | targeted: `… test_r14_agent_stamping.py test_r14_legibility.py -v` · full: `python -m pytest tests/ -q` | V4-T9 |
| **V4-T11** | — | docs | ✎ `README.md`, ✎ `docs/spec/03-module-map.md`, ✎ `docs/decision-log.md`, ✎ `docs/build-log.md`, ✚ `docs/verification/v4/result.md`, ✚ `docs/verification/v4/v4-t11-run.txt` | full suite: `python -m pytest tests/ -q` + clean server probe of `/app/` | V4-T10 (+ R14 legibility gate ☑) |

> **R14 fresh-agent legibility verification is an ORCHESTRATOR-EXECUTED gate, NOT a Kimi task** (see the gate below). `test_r14_legibility.py` (the deterministic CI harness) IS authored + run inside the R14 RED/GREEN tasks; the *fresh-agent* legibility judgement (the D4/S4 payoff that a zero-context agent can resolve every target from the head block alone) is the orchestrator's manual confirmation on the landed artifact, recorded in `result.md`.

---

## Dependency graph (text)

```
(branch master — continues; no branch task)

R10  ── V4-T1 RED   (fixtures flow-grow/flow-grow-deadzone/grid-healthy + test_r10 + copy_synthetic; run vs master; record red-first-log.md)
        └─ orchestrator RED gate (test-only diff + RED numbers match) ◄ needs T1
        ── V4-T2 GREEN (interaction.js: captureSizingState +grow/+shrink, onResize pass dist, applyVisualResize flex-child two-branch) ◄ needs T1
        └─ orchestrator diff gate + Opus review → commit [v4-t2] R10
R12  ── V4-T3 RED   (test_r12_alt_symmetric; run vs post-R10 master — Alt anchor absent → one-sided → mirror assertions RED) ◄ needs T2
        └─ orchestrator RED gate ◄ needs T3
        ── V4-T4 GREEN (interaction.js: onResizeStart fixedDirection set, onResizeEnd reset above early-return) ◄ needs T3
        └─ gate + review → commit [v4-t4] R12
R11  ── V4-T5 RED   (test_r11_resize_guides_equal_size; run vs post-R12 master — equal-size snap/hint absent → RED; position-guide verification may already GREEN post-R10) ◄ needs T4
        └─ orchestrator RED gate ◄ needs T5
        ── V4-T6 GREEN (interaction.js: sizeCandidates cache, equal-size match override, showSizeHint/clearSizeHint, teardown) ◄ needs T5
        └─ gate + review → commit [v4-t6] R11
R13  ── V4-T7 RED   (fixture agent-comments + test_r13_comment_edit_delete; run vs master — no edit/delete ops → RED) ◄ needs T6
        └─ orchestrator RED gate ◄ needs T7
        ── V4-T8 GREEN (comments.js 4 ops + writeIsland/toJson editedAt; runtime-main.js 4 regs; main.js createThreadEl affordances; comment-composer.js edit mode) ◄ needs T7
        └─ gate + review → commit [v4-t8] R13
R14  ── V4-T9 RED   (test_r14_agent_stamping + test_r14_legibility; run vs master — no data-hyp-agent stamping, stale path block → RED) ◄ needs T8
        └─ orchestrator RED gate ◄ needs T9
        ── V4-T10 GREEN (comments.js buildAgentBlock rewrite + agentStampMap; serializer.js serialize() transient stamp + stripClone exemption) ◄ needs T9
        └─ gate + review → commit [v4-t10] R14
        └─ ORCHESTRATOR R14 fresh-agent legibility gate (manual confirm on the landed saved artifact) ◄ needs T10
T-final ─ V4-T11 docs-sync + EXIT (README/module-map/decision-log append/build-log + full suite + clean server run → docs/verification/v4/result.md) ◄ needs T10 + legibility gate
        └─ gate + review → commit [v4-t11] docs: sync v4 docs and close the Session-3 cycle
```

---

## Per-R cycle definition (boundary tables)

### R10 — Resize amplification + dead-zone fix (dragged edge tracks cursor 1:1)

| ID | Goal | Allowlist (✎modify ✚create) | Depends | RED expectation (cite numbers) / GREEN acceptance | Status |
|----|------|------------------------------|---------|----------------------------------------------------|--------|
| **V4-T1** | RED: add `copy_synthetic`/`SYN_DIR` to `conftest_helpers.py`; create `flow-grow.html`, `flow-grow-deadzone.html`, `grid-healthy.html`; create `test_r10_resize_flex.py` (E-R10-1..6, G-R10-UNDO, G-R10-REDO). Run vs current master; record red-first numbers. | ✎ `tests/e2e/conftest_helpers.py`, ✚ `tests/e2e/fixtures/flow-grow.html`, ✚ `tests/e2e/fixtures/flow-grow-deadzone.html`, ✚ `tests/e2e/fixtures/grid-healthy.html`, ✚ `tests/e2e/test_r10_resize_flex.py`, ✚ `docs/verification/v4/v4-t1-red.txt`, ✚/✎ `docs/improvements-2026-06-r3/red-first-log.md` | — | **Expected RED on master:** E-R10-1 (slack: right-edge ≈+33 not +60 → fails delta=2), E-R10-2 (dead-zone `flow-grow-deadzone.html`: rendered Δ≈0 for −120 → fails delta=2 by ≈120px), E-R10-2b (Δ≈0 for −100 → fails delta=3 by ≈100px), G-R10-UNDO (inlGrow left "0" → fails). **Expected GREEN already on master:** E-R10-3/-4/-5 (healthy block/grid paths — the `else` branch is unchanged), E-R10-6 direction-only. If E-R10-1/-2/-2b do NOT fail → fixture invalid → STOP + BUG (red-first gate). | ☐ |
| **V4-T2** | GREEN: in `interaction.js` add `flex-grow`+`flex-shrink` capture to `captureSizingState` flex-child branch; pass `e.dist` through `onResize`; replace the `flex-child` branch body of `applyVisualResize` with the verbatim two-branch block. Rerun R10 targeted + full suite; commit. | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t2-run.txt` | V4-T1 | **GREEN:** all of `test_r10_resize_flex.py` pass (E-R10-1/-2/-2b flip RED→GREEN; healthy paths stay GREEN; G-R10-UNDO restores all three longhands incl. absent-inline); full suite green (REG-1, esp. `test_r2_resize_real.py`, `test_f2_select_guides.py`); commit `[v4-t2] R10: resize dragged edge tracks cursor 1:1 (grow-neutralized flex-basis from beforeRect+dist)`. | ☐ |

> **Commit C-R10** (after V4-T2 green + diff gate + Opus review): `[v4-t2] R10: resize dragged edge tracks cursor 1:1 (grow-neutralized flex-basis from beforeRect+dist)`.

### R12 — Alt-held symmetric resize (center-origin via fixedDirection)

| ID | Goal | Allowlist | Depends | RED expectation / GREEN acceptance | Status |
|----|------|-----------|---------|------------------------------------|--------|
| **V4-T3** | RED: create `test_r12_alt_symmetric.py` (E-R12-1..4) reusing `flow-grow.html`. Run vs post-R10 master. | ✚ `tests/e2e/test_r12_alt_symmetric.py`, ✚ `docs/verification/v4/v4-t3-red.txt` | V4-T2 | **Expected RED on post-R10 master:** E-R12-1 (no Alt anchor → left edge unchanged → mirror assertion `before.left−after.left ≈ 60` fails; width ≈60 not ≈120 → fails delta=4), E-R12-4 (same on the accent). **Expected GREEN already:** E-R12-2 (no-Alt one-sided — that is current behavior), E-R12-3 (a non-Alt gesture after a — currently no-op — Alt gesture is one-sided; may pass trivially pre-fix). If E-R12-1 does NOT fail → STOP + BUG. | ☐ |
| **V4-T4** | GREEN: in `interaction.js` `onResizeStart` set `moveable.fixedDirection = altKey ? [0,0] : false`; in `onResizeEnd` reset `false` ABOVE the `byId(activeHypId)` early-return guard (G10). Rerun R12 targeted + full suite; commit. | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t4-run.txt` | V4-T3 | **GREEN:** `test_r12_alt_symmetric.py` all pass (Alt → dragged edge 1:1 + mirror + width 2Δ; non-Alt one-sided; reset survives); R10 tests STILL green (E-R12-4 asserts grow still neutralized); full suite green; commit `[v4-t4] R12: Alt-held symmetric resize via Moveable fixedDirection center-origin`. | ☐ |

> **Commit C-R12:** `[v4-t4] R12: Alt-held symmetric resize via Moveable fixedDirection center-origin`.

### R11 — Resize guides + equal-size matching

| ID | Goal | Allowlist | Depends | RED expectation / GREEN acceptance | Status |
|----|------|-----------|---------|------------------------------------|--------|
| **V4-T5** | RED: create `test_r11_resize_guides_equal_size.py` (E-R11-1..5) reusing `flow-grow.html`. Run vs post-R12 master. | ✚ `tests/e2e/test_r11_resize_guides_equal_size.py`, ✚ `docs/verification/v4/v4-t5-red.txt` | V4-T4 | **Expected RED on post-R12 master:** E-R11-2 (equal-size snap absent → accent lands at raw cursor, not ON twin's 300px → fails delta=0.5), E-R11-3 (no `hyp-size-hint` overlay → count 0 → fails), E-R11-4 (nothing to strip — vacuous, may pass), E-R11-5 (no candidate logic at all → no snap → may pass trivially pre-fix; becomes load-bearing post-fix). **Expected GREEN already (post-R10):** E-R11-1 (position guides fire on the flex-grow element — R10 made the edge move; L4). If E-R11-1 is RED → R10 regressed → STOP + BUG. | ☐ |
| **V4-T6** | GREEN: in `interaction.js` cache `sizeCandidates` at `onResizeStart` (with the F5 flex-grow-sibling exclusion); run equal-size matching in/around `applyVisualResize` (4px override); add `showSizeHint`/`clearSizeHint` (scrollX/Y-positioned, `hyp-`namespaced); call from `onResize`; teardown at `onResizeEnd`. Rerun R11 targeted + full suite; commit. | ✎ `runtime/js/interaction.js`, ✚ `docs/verification/v4/v4-t6-run.txt` | V4-T5 | **GREEN:** `test_r11_resize_guides_equal_size.py` all pass (snap lands ON twin; hint renders over the match + torn down; serializer-exempt; NO phantom snap to grow siblings — E-R11-5); R10/R12 tests STILL green; `test_f2_select_guides.py::test_resize_shows_guidelines` green (REG-3); full suite green; commit `[v4-t6] R11: equal-size snap + hint overlay; position guides verified post-R10`. | ☐ |

> **Commit C-R11:** `[v4-t6] R11: equal-size snap + hint overlay; position guides verified post-R10`.

### R13 — Comment edit + delete (root + replies, island + agent-block sync)

| ID | Goal | Allowlist | Depends | RED expectation / GREEN acceptance | Status |
|----|------|-----------|---------|------------------------------------|--------|
| **V4-T7** | RED: create `agent-comments.html`; create `test_r13_comment_edit_delete.py` (E-R13-1..8). Run vs current master. | ✚ `tests/e2e/fixtures/agent-comments.html`, ✚ `tests/e2e/test_r13_comment_edit_delete.py`, ✚ `docs/verification/v4/v4-t7-red.txt` | V4-T6 | **Expected RED on master:** ALL of E-R13-1..8 fail — no Edit/Delete affordance exists in the panel (`createThreadEl` renders Reply/Resolve/For-agents only), no `edit-comment`/`delete-comment`/`edit-reply`/`delete-reply` bridge command, no composer `edit` mode. The tests fail at "click Edit" (locator not found) or the bridge command throwing. If any E-R13 PASSES on master → the feature partially exists → STOP + BUG (re-scope). | ☐ |
| **V4-T8** | GREEN: add `editComment`/`deleteComment`/`editReply`/`deleteReply` to `comments.js` (each via `makeCommentCommand`, `editedAt` stamp, G4 undo-delete-key); `editedAt` into `writeIsland`/`toJson`; register 4 commands in `runtime-main.js` (G3 — no `author` requirement, `replyIndex` typeof-number); Edit/Delete affordances in `main.js` `createThreadEl`; `edit` mode in `comment-composer.js`. Rerun R13 targeted + full suite; commit. | ✎ `runtime/js/comments.js`, ✎ `runtime/js/runtime-main.js`, ✎ `app/js/main.js`, ✎ `app/js/shell/comment-composer.js`, ✚ `docs/verification/v4/v4-t8-run.txt` | V4-T7 | **GREEN:** `test_r13_comment_edit_delete.py` all pass (edit/delete root+reply; undo fidelity incl. delete-reply at original index; agent-block reflects edited instruction; edit composer in-viewport + no For-agents checkbox); `test_f5_comments.py` (REG-4) + `test_g2_save_with_comments.py` (REG-5) green (`editedAt` additive); full suite green; commit `[v4-t8] R13: comment edit+delete for roots and replies (undoable, island + agent-block sync)`. | ☐ |

> **Commit C-R13:** `[v4-t8] R13: comment edit+delete for roots and replies (undoable, island + agent-block sync)`.

### R14 — Agent stamping + rewritten head block + fresh-agent legibility

| ID | Goal | Allowlist | Depends | RED expectation / GREEN acceptance | Status |
|----|------|-----------|---------|------------------------------------|--------|
| **V4-T9** | RED: create `test_r14_agent_stamping.py` (E-R14-1..8) + `test_r14_legibility.py` (G-R14-LEGIBILITY-1/-2) reusing `agent-comments.html`. Run vs current master. | ✚ `tests/e2e/test_r14_agent_stamping.py`, ✚ `tests/e2e/test_r14_legibility.py`, ✚ `docs/verification/v4/v4-t9-red.txt` | V4-T8 | **Expected RED on master:** E-R14-1/-2/-5/-8 fail — no `data-hyp-agent` attribute is ever emitted (`stripClone` removes every `data-hyp-*`; block emits the stale `anchor: ${path}` line, so `target: [data-hyp-agent~=…]` is absent and `querySelector('[data-hyp-agent~="…"]')` returns 0); legibility criteria 2/4 fail (selectors resolve nothing / path goes stale). E-R14-4 (live DOM clean) may pass vacuously (no stamp ever applied). If a `data-hyp-agent` already appears in a save on master → STOP + BUG. | ☐ |
| **V4-T10** | GREEN: rewrite `buildAgentBlock` anchor line → `target: [data-hyp-agent~="…"]` + `context:` + self-cleanup preamble; add exported `agentStampMap()` (high-confidence-only, G6); in `serializer.js` `serialize()` add the transient live-stamp (clear → stamp → clone → strip-exempt → finally-unstamp, S3-13) and exempt `data-hyp-agent` in `stripClone`. Rerun R14 targeted + full suite; commit. | ✎ `runtime/js/comments.js`, ✎ `runtime/js/serializer.js`, ✚ `docs/verification/v4/v4-t10-run.txt` | V4-T9 | **GREEN:** `test_r14_agent_stamping.py` + `test_r14_legibility.py` all pass (stamp + selector resolves the right element; multi-thread space-separated; resolved/deleted don't stamp; live DOM clean after save; block format complete; idempotent across saves; node-count guard safe; non-first element via markers-live; fresh-agent resolves every target incl. after DOM shift); `test_g2_save_with_comments.py` green (sentinel unchanged — REG-5); full suite green; commit `[v4-t10] R14: data-hyp-agent stamping + attribute-selector head block (fresh-agent legible)`. | ☐ |

> **Commit C-R14:** `[v4-t10] R14: data-hyp-agent stamping + attribute-selector head block (fresh-agent legible)`.

> **ORCHESTRATOR R14 fresh-agent legibility gate (after V4-T10, NOT a Kimi task):** open the saved artifact from an R14 E2E run (or produce one), extract ONLY the `<head>` agent block text, and confirm by inspection that a zero-project-context agent can resolve every `target:` selector to its intended element using the block alone — including after a simulated first-edit DOM shift. This is the D4/S4 payoff confirmation. Record PASS/FAIL + the inspected block in `docs/verification/v4/result.md`. The deterministic `test_r14_legibility.py` harness (run in V4-T9/T10) is the CI proxy; this gate is the human-judgement seal.

### T-final — docs-sync + EXIT

| ID | Goal | Allowlist | Depends | Acceptance | Status |
|----|------|-----------|---------|-----------|--------|
| **V4-T11** | Docs-sync + EXIT: README usage deltas (Alt symmetric resize, equal-size matching, comment edit/delete, agent-anchor attribute selectors); `03-module-map.md` deltas (interaction.js R10/R11/R12; comments.js R13 ops + R14 buildAgentBlock/agentStampMap; serializer.js R14 transient stamp; runtime-main.js R13 regs; comment-composer.js edit mode); `decision-log.md` APPEND-ONLY rows (next consecutive D-numbers — READ the live highest first); `build-log.md` append a v4 cycle entry. Then run the FULL suite + a clean server run on the synthetic fixtures → `docs/verification/v4/result.md`. | ✎ `README.md`, ✎ `docs/spec/03-module-map.md`, ✎ `docs/decision-log.md`, ✎ `docs/build-log.md`, ✚ `docs/verification/v4/result.md`, ✚ `docs/verification/v4/v4-t11-run.txt` | V4-T10 + legibility gate | Full suite green (the new R10–R14 suites + all carried suites); `GET /app/` → 200 with ZERO editor console errors on `flow-grow.html` + `agent-comments.html` (REG-8); README/module-map reflect every behavior change; decision-log diff = additions only (existing rows byte-identical); build-log appended; results to `result.md` mirroring v3's `docs/verification/v3/result.md`. Commit `[v4-t11] docs: sync v4 docs (usage, module map, decision log, build log) and close the Session-3 cycle`. | ☐ |

> **Commit C-final:** `[v4-t11] docs: sync v4 docs (usage, module map, decision log, build log) and close the Session-3 cycle`.

---

## Shared-file serialization (the binding constraint across boundaries)

The per-R sequence (AD7) makes shared-file edits serial by construction — only one R is in flight at a time, so no two tasks ever edit the same file concurrently.

| File | Edited by (in commit order) | Serialization |
|------|------------------------------|---------------|
| `runtime/js/interaction.js` | R10 (capture +grow/+shrink, onResize dist, applyVisualResize flex-child two-branch), R12 (onResizeStart/onResizeEnd fixedDirection), R11 (sizeCandidates cache, equal-size override, showSizeHint/clearSizeHint) | R10 → R12 → R11 (AD7; R12 must layer onto verified-1:1 R10; R11's equal-size override modifies the R10 dist-target term, so it lands last) |
| `runtime/js/comments.js` | R13 (4 ops + editedAt in writeIsland/toJson), R14 (buildAgentBlock rewrite + agentStampMap) | R13 → R14 (R13 adds ops; R14 rewrites the block anchor line + adds the stamp map — disjoint functions, ordered) |
| `runtime/js/runtime-main.js` | R13 (4 command registrations + imports) | R13 only |
| `runtime/js/serializer.js` | R14 (serialize transient stamp + stripClone exemption) | R14 only |
| `app/js/main.js` | R13 (createThreadEl Edit/Delete affordances) | R13 only |
| `app/js/shell/comment-composer.js` | R13 (edit mode) | R13 only |
| `tests/e2e/conftest_helpers.py` | R10 RED (copy_synthetic + SYN_DIR) | R10 RED only (additive helper; later RED tasks reuse it, never re-edit) |
| `tests/e2e/fixtures/*.html` | R10 RED (flow-grow, flow-grow-deadzone, grid-healthy), R13 RED (agent-comments) | created once; reused read-only by every later task |

`tests/e2e/fixtures/` is created by the R10 RED task (V4-T1) and `agent-comments.html` by the R13 RED task (V4-T7); R11/R12/R14 RED tasks REUSE the existing committed fixtures and never recreate them.

---

## Commit map (which tasks → which commit)

| Commit | Tasks | Message |
|--------|-------|---------|
| C-R10 | V4-T1 (RED, no commit), V4-T2 | `[v4-t2] R10: resize dragged edge tracks cursor 1:1 (grow-neutralized flex-basis from beforeRect+dist)` |
| C-R12 | V4-T3 (RED, no commit), V4-T4 | `[v4-t4] R12: Alt-held symmetric resize via Moveable fixedDirection center-origin` |
| C-R11 | V4-T5 (RED, no commit), V4-T6 | `[v4-t6] R11: equal-size snap + hint overlay; position guides verified post-R10` |
| C-R13 | V4-T7 (RED, no commit), V4-T8 | `[v4-t8] R13: comment edit+delete for roots and replies (undoable, island + agent-block sync)` |
| C-R14 | V4-T9 (RED, no commit), V4-T10 | `[v4-t10] R14: data-hyp-agent stamping + attribute-selector head block (fresh-agent legible)` |
| C-final | V4-T11 | `[v4-t11] docs: sync v4 docs (usage, module map, decision log, build log) and close the Session-3 cycle` |

RED tasks do NOT commit — their output (fixtures + tests + red logs) is staged into the SAME commit as their GREEN partner (the GREEN task commits the product fix; the RED task's test files are added by the GREEN commit, so each `[v4-t<N>]` commit carries the R's tests + fix + fixtures together). Commits are LOCAL-ONLY on `master` (D6 — no push, no merge). The synthetic fixtures are COMMITTED (not gitignored — unlike the v3 tecer sample); `tecer-gsmm-introduction*.html` is NEVER staged or referenced.

---

## Exit checklist (maps to the session exit condition)

The session exits when ALL of these hold (owner exit condition: all R10–R14 implemented + tested + committed individually on `master`; full suite green; clean error-free local server run on the synthetic fixtures — D5/D6):

- [ ] **R10 ☑** — `test_r10_resize_flex.py` green; commit C-R10 landed on `master`.
- [ ] **R12 ☑** — `test_r12_alt_symmetric.py` green; commit C-R12 landed.
- [ ] **R11 ☑** — `test_r11_resize_guides_equal_size.py` green; commit C-R11 landed.
- [ ] **R13 ☑** — `test_r13_comment_edit_delete.py` green; commit C-R13 landed.
- [ ] **R14 ☑** — `test_r14_agent_stamping.py` + `test_r14_legibility.py` green; commit C-R14 landed; orchestrator fresh-agent legibility gate PASS recorded.
- [ ] **Suite green** — the FULL suite (all `tests/e2e/` + `tests/unit/`) re-runs green after the final commit; the named regression watches stay green: `test_r2_resize_real.py` (REG-2), `test_f2_select_guides.py` (REG-3), `test_f5_comments.py` (REG-4), `test_g2_save_with_comments.py` (REG-5).
- [ ] **Red-first proven** — `docs/improvements-2026-06-r3/red-first-log.md` records the observed master failure numbers for E-R10-1/-2/-2b (and the R12 mirror-assertion reds) BEFORE their fixes landed.
- [ ] **Clean server run** — `GET /app/` → 200; ZERO editor-origin console errors opening `flow-grow.html` and `agent-comments.html` (asset 404s excluded — REG-8); recorded in `docs/verification/v4/result.md`.
- [ ] **Docs synced** — README usage + `03-module-map.md` reflect R10–R14; `decision-log.md` appended (existing rows byte-identical); `build-log.md` appended; C-final landed.

---

## Notes

- **Surgical-change fence:** no task modifies a file outside its allowlist. RED/test tasks touch ONLY `tests/` (+ `tests/e2e/fixtures/` + `conftest_helpers.py`) + their `docs/verification/v4/` evidence. Product bugs or RED/GREEN mismatches are REPORTED (a `…-BUG.md` under `docs/verification/v4/`), never patched outside the allowlist, never papered over by weakening a test (D14).
- **Live-code anchoring:** every task is CONTENT-ANCHORED (inlines + quotes the live code around each edit), never line-numbered. The spec's L1–L6 live-reconciliation table is already folded into the inlined change-map blocks.
- **Cross-cutting invariants (I1–I7, spec §Cross-cutting):** resize edits ONLY width/height/flex-basis/flex-grow/flex-shrink/grid tracks, NEVER position:absolute or translate (I1); R10/R12 never write translate (I2); every injected class/id is `hyp-`prefixed, every injected attribute `data-hyp-*` (I3); all new mutating ops flow through the single linear history stack, serialize NEVER pushes history (I4); the R2 pointer-events rule / onDragEnd toggle / R05 zero-distance guard / FLIP reorder / R8 font-span logic are UNTOUCHED (I5); the carried suite re-runs green (I6); new tests use SYNTHETIC fixtures only (I7).
- **PROTECTED (read-only, NEVER modify — forbidden_ops in every task):** all of `docs/plan/hypresent-v1/`, `docs/plan/hypresent-v2/`, `docs/plan/hypresent-v3/`; `docs/spec/04-implementation-plan.md`; all of `docs/improvements-2026-06/` and `docs/improvements-2026-06-r2/`; `changelog.md` (Registrar-owned); `tecer-gsmm-introduction*.html` (gitignored sample — never staged, never referenced; tests use synthetic fixtures only). No push; no `git reset --hard`/force; no destructive history rewrite (fix-forward only).
- **rbtv-planning headless note:** the `rbtv-planning` workflow is interactive-by-design (4 numbered steps, each HALTing at a menu for user Continue). With no user this run, the orchestrator is the approver: the workflow's gate semantics are honored by the per-R RED gate + GREEN diff gate + Opus review; its artifact set (plan + shape/learnings/deliverables) is reduced to this index + the task files under the binding v3-convention override. The companion `shape.md`/`learnings.md`/`deliverables.md` are intentionally NOT produced — the spec + test-plan + this index carry their content, and the binding override fixes the format to the v3 plan convention + Kimi task contract.

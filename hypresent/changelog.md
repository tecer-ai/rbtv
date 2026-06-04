# Hypresent Improvement Changelog — Session 2026-06

| Field | Value |
|-------|-------|
| Registrar | Orchestrator (lead product designer) |
| Workspace | `3-resources/tools/rbtv/hypresent` |
| Session artifacts | `docs/improvements-2026-06/` |
| Kimi contract | `kimi --work-dir "<rbtv-repo>" --quiet --prompt "<task>"` · exit 0=ok, 75=backoff+retry, 1=halt+surface · post-run `git diff` scope gate on every dispatch |
| Protected file | `docs/spec/04-implementation-plan.md` (original conception plan — read-only) |

## Exit Scorecard

| ID | Improvement | Status |
|----|-------------|--------|
| F1 | Native open/save via OS file dialogs (no filepath typing) | ☐ |
| F2 | Element resize reachable in UI + alignment guidelines (Google-Slides-style) | ☐ |
| F3 | Element move reachable in UI + same-hierarchy reorder on overlap | ☐ |
| F4 | Border/edge color editing | ☐ |
| F5 | Agent comments: per-comment tag + non-rendering instructions at top of HTML | ☐ |
| G1 | B-PANEL: verify already-applied fix + regression-lock by test (fix confirmed in source by orchestrator — `color-popover.js:21-26`) | ☐ |
| G2 | B-SERIALIZE: verify already-applied fix + guard hardening for F5 agent block + regression-lock by test (fix confirmed in source — `serializer.js:234,242`) | ☐ |
| EXIT | Kimi reports clean, error-free server run + automated tests pass on sample HTML | ☐ |

## Decision Register

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | G1/G2 blocker fixes added to scope | B-PANEL destroys any panel feature on open (blocks F5 + future panels); B-SERIALIZE blocks saving documents containing comments (blocks F5, EXIT) |
| D2 | Session artifacts live in `docs/improvements-2026-06/` | Matches existing `docs/verification/` session-folder convention; `docs/` is the project doc root |
| D3 | F1 = server-side native dialogs (PowerShell `-STA` subprocess from Python; new `POST /api/dialog-open`, `POST /api/dialog-save-as`) | FS Access API never exposes the disk path → breaks locked decision D5 (`/doc/` root re-point for relative assets). tkinter from handler thread deadlocks on Windows (CPython #11077/#33412). Evidence: `research-01-file-access.md` |
| D4 | F2 = Moveable 0.53.0 `snappable` (no lib upgrade; 0.53.0 is latest). Enable `center`/`middle` snap directions; reassign `elementGuidelines` on every activation | All required options exist in vendored version; guidelines auto-render inside existing wrapper. Evidence: `research-02-moveable-snapping.md` |
| D5 | F3 = hand-rolled `reorder.js` (~150 LOC) on Moveable drag events; pointer-midpoint hit-test on dominant axis; undo via captured sibling `data-hyp-id` refs | SortableJS/dnd-kit conflict with Moveable pointer capture or are framework-bound. Evidence: `research-03-reorder-drag.md` |
| D6 | Move mechanism migrates `transform: translate()` → CSS `translate` property | Composes independently with document-owned `transform:rotate/scale` → eliminates silent transform loss (recon Risk 3). Preserves locked D2 intent (non-destructive, reversible); spec must add a decision-log entry superseding D2's letter |
| D7 | F5 data model: comment island stays single source of truth with per-thread `agentInstruction: true`; top-of-file block is derived, regenerated on every save, removed when no agent comments remain; `-->` escaped in bodies | Round-trip safety; no duplication drift. Evidence: `research-04-agent-comments.md` |
| D8 | Registrar runs read-only git inspection (`git status`/`diff --stat`) after every Kimi dispatch as the confinement gate | Kimi headless auto-approves all tools; post-run diff is the only reliable write gate (CLI reference §9) |
| D9 | Milestone commits executed by a dispatched Claude sub-agent invoking the `rbtv-commit` skill; branch `hypresent-v2` created by Kimi task V2-T0 | Keeps orchestrator non-executing; rbtv-sub-agents rule mandates naming `rbtv-commit` on commit dispatches |
| D10 | Artifact placement: spec + test-plan in `docs/improvements-2026-06/`; executable plan + per-task Kimi prompt files in `docs/plan/hypresent-v2/` | Mirrors v1 convention (`docs/plan/hypresent-v1/`); original plan `docs/spec/04-implementation-plan.md` remains untouched |
| D11 | G1/G2 reframed verify+regression-lock, NOT re-fix (spec decision S0 adopted) | Opus flagged recon as stale; orchestrator independently confirmed both fixes at line level (`color-popover.js:21-26`, `serializer.js:234,242`). Re-fixing correct code = regression risk |

## User Decisions (question round, 2026-06-03 — round consumed)

| ID | Question | Decision |
|----|----------|----------|
| U1 | Tool interaction model | Modeless, Slides-style: select → handles; drag body = move/reorder, handles = resize, double-click = text edit |
| U2 | Flow drag w/o sibling target | Hybrid: sibling overlap → reorder; empty space → keep translate (out-of-flow badge) |
| U3 | Reorder feedback | On-drop DOM mutation + FLIP settle animation |
| U4 | Cross-parent drops | **Re-parenting IN SCOPE**: drop onto element of another container moves element into it |
| U5 | Save controls | Save (silent overwrite of open file) + Save As (native dialog) |
| U6 | Border color | Single all-sides "Border" row; auto-apply `1px solid <color>` on borderless elements |
| U7 | Comment composer | Replace `prompt()` with anchored popover composer incl. "For agents" toggle; panel toggle for existing threads |
| U8 | Agent block placement | Head-first-child derived block ACCEPTED with conditions: (a) in-editor anchored comment visibility unaffected, (b) block entries carry explicit anchors (DOM path + native id + context quote), (c) fallback to notice-only-in-head + tagged island if complexity spikes |
| U9 | Test tooling | Playwright (Python) approved as dev-only dependency; app stays dependency-free |
| U10 | Git policy | Feature branch `hypresent-v2`; milestone commits via `rbtv-commit`; include untracked sample file |
| U10a | **Amendment (user instruction, mid-session)** | Sample deck `tecer-gsmm-introduction.html` + any derived versions are GITIGNORED, never staged/committed — supersedes the "include sample file" clause of U10. Rule `hypresent/tecer-gsmm-introduction*.html` added to rbtv `.gitignore` (note: that file is installer-generated and itself untracked → rule is local-only) |

## Log

| # | Date | Actor | Type | Entry |
|---|------|-------|------|-------|
| 1 | 2026-06-03 | Orchestrator | session | Session opened. Roles: Opus=spec+test design, Sonnet=research, Kimi=exclusive engineering. Orchestrator never executes. |
| 2 | 2026-06-03 | Orchestrator | doc | Kimi CLI reference loaded (verified against v1.41.0). Headless invocation + exit-code retry policy adopted (see Kimi contract). |
| 3 | 2026-06-03 | Sonnet repo-analyst | recon | Completed: full codebase survey → `docs/improvements-2026-06/recon.md`. Architecture: parent shell + same-origin iframe; 5 shell + 13 runtime ES modules; Moveable.js, Coloris, DOMPurify vendored; stdlib Python server `server/server.py` (127.0.0.1:8765). |
| 4 | 2026-06-03 | Orchestrator | finding | Resize (T12) + move (T13) code-complete but unreachable — no shell toolbar affordance. No snapping/alignment guides anywhere. |
| 5 | 2026-06-03 | Orchestrator | finding | Blockers found: B-PANEL, B-SERIALIZE (see G1/G2). Move overwrites full `transform` → silent loss of rotation/scale on documents using them. |
| 6 | 2026-06-03 | Orchestrator | finding | Open/save = path text input → `POST /api/open` / `POST /api/save-as`. `border-color` already detected by `discoverInlineSites` but has no panel UI. Comments data layer complete + verified. |
| 7 | 2026-06-03 | Orchestrator | decision | D1, D2 registered. |
| 8 | 2026-06-03 | Sonnet ×4 | research | Dispatched: R1 File System Access API → `research-01-file-access.md` · R2 Moveable snapping/guides → `research-02-moveable-snapping.md` · R3 flow reorder-on-drag → `research-03-reorder-drag.md` · R4 agent-comment HTML conventions → `research-04-agent-comments.md`. |
| 9 | 2026-06-03 | Orchestrator | doc | `docs/kimi-cheatsheet.md` + `docs/decision-log.md` loaded. Locked decisions D1–D6/A1–A12 adopted as spec constraints. Runtime component `workflows/_shared/kimi-code-execution/` absent → CLI reference + cheatsheet govern. |
| 10 | 2026-06-03 | Sonnet ×4 | result | R1–R4 completed, all reports on file. Verdicts registered as decisions D3–D7. |
| 11 | 2026-06-03 | Orchestrator | decision | D3–D8 registered. |
| 12 | 2026-06-03 | Orchestrator | session | Single human question round opened: 10 questions (interaction model, reorder semantics, preview, reparenting, save UX, border UX, composer, agent-block placement, test deps, git policy). |
| 13 | 2026-06-03 | Human owner | decision | Question round answered in full → U1–U10 registered. Round consumed. Notable scope add: U4 re-parenting included. |
| 14 | 2026-06-03 | Orchestrator | decision | D9, D10 registered. |
| 15 | 2026-06-03 | Opus spec author | dispatch | Tasked: `spec.md` + `test-plan.md` (improvements-2026-06) + new execution plan `docs/plan/hypresent-v2/` + self-contained Kimi task files. Inputs: changelog, recon, research-01..04, decision-log, spec/01–05 (04 read-only). |
| 16 | 2026-06-03 | Opus spec author | result | Delivered: `spec.md` (S0–S25), `test-plan.md` (unit + Playwright suites mapped to scorecard), `hypresent-v2-plan.md` (22 tasks V2-T0–T21, dependency graph, shared-file serialization order), `tasks/V2-T0..T21.md`. Flagged CONTRADICTION: G1/G2 already fixed in source; recon stale. |
| 17 | 2026-06-03 | Orchestrator | finding | Contradiction verified by direct source read — G1 fix at `color-popover.js:21-26`, G2 fix at `serializer.js:234,242`. D11 registered; scorecard G1/G2 reworded to verify+lock. |
| 18 | 2026-06-03 | Human owner | decision | Mid-session instruction: gitignore the sample deck + derived versions → U10a. Orchestrator added rule to rbtv `.gitignore`, rewrote `tasks/V2-T0.md` (staging removed — `git add` on ignored file would fail), amended plan T0 row + graph label, removed one stray mislabeled line from plan. |
| 19 | 2026-06-03 | Sonnet adversarial reviewer | dispatch | Tasked: adversarial review of spec/test-plan/plan/all 22 task files → `review-01-spec-plan.md`. Orchestrator ran Kimi pre-flight in parallel. |
| 20 | 2026-06-03 | Orchestrator | test | Kimi pre-flight PASS: v1.41.0, agent spec v1, wire protocol 1.9. |
| 21 | 2026-06-03 | Sonnet adversarial reviewer | result | Verdict **NO-GO**: 7 BLOCKER (R02 pwsh hardcode, R03 stale line anchors in T8, R04 stale island re-embed, R05 spurious reorder on zero-distance click, R06 unescaped nativeId in agent block, R07 fixture-missing test collapse, R08 e2e import path), 6 MAJOR (incl. R09 circular module chain, R14 anchor drift on unmoved siblings), 6 MINOR. Full table: `review-01-spec-plan.md`. |
| 22 | 2026-06-03 | Opus spec author | dispatch | Fix cycle: apply all BLOCKER+MAJOR fixes (+ trivial MINORs) across spec/test-plan/plan/task files; fix map → `review-01-fixes.md`. Orchestrator-imposed fix directions: R07 fail-loud precondition (never skip-green), R02 pwsh→powershell.exe fallback, R03 anchor-based (not line-based) edit instructions, R11 `reanchorAfterMove` ownership moved to V2-T9 (T8 only calls it). |
| 23 | 2026-06-03 | Opus spec author | result | Fix cycle complete: 7/7 BLOCKER, 6/6 MAJOR fixed; 2 MINOR fixed, 4 deferred no-ops; R13 false positive (reviewer self-struck). Structural: import cycle broken (selection.js owns observer registry), T8 deps now T7+T9, allowlist mismatches corrected (comments.js out of T8; index.html out of T11 row), U-SAVE-2 un-skipped on port 8790. Map: `review-01-fixes.md`. |
| 24 | 2026-06-03 | Orchestrator | decision | GO. Spot-check passed: pwsh fallback in T3 ✓, Edit-anchoring rule in all 9 edit-tasks ✓, drag threshold in T8 ✓, escape+reanchor in T9 (18 refs) ✓, fail-loud fixture + sys.path bootstrap in T13 ✓. |
| 25 | 2026-06-03 | Kimi | dispatch | V2-T0 (create branch `hypresent-v2`). |
| 26 | 2026-06-03 | Kimi | result | V2-T0 PASS (exit 0). Gate: branch `hypresent-v2` checked out; zero file mutations; sample confirmed ignored. Correction to U10a note: `.gitignore` is tracked (self-ignore rule inert on tracked files) → rule is committable; installer regeneration remains the only overwrite risk. Plan status: T0 ☑. |
| 27 | 2026-06-03 | Kimi ×3 | dispatch | Wave A in parallel: V2-T1 (G1 verification artifact), V2-T2 (serializer guard prep), V2-T3 (F1 server dialog endpoints). Disjoint allowlists. |
| 28 | 2026-06-03 | Kimi | result | V2-T1 PASS (exit 0). Gate: only `docs/verification/v2/g1-confirm.md` created; artifact quotes live fix + final panel DOM + invariant. Scorecard G1 verification half done (regression test lands at V2-T18). Plan: T1 ☑. |
| 29 | 2026-06-03 | Kimi | result | V2-T2 PASS (exit 0). Gate: diff confined to `serializer.js` (+55/−7). Orchestrator verified guard math against `countAllNodes` (SHOW_ALL → comment nodes counted; ±1 per swept/inserted block is sound). R04 fix present (empty store → no island re-embed, no stale fall-through). Plan: T2 ☑. |
| 30 | 2026-06-03 | Kimi | dispatch | V2-T5 (F4 border data: color.js/commands.js/runtime-main.js) — parallel with still-running V2-T3 (disjoint files). |
| 31 | 2026-06-03 | Kimi | result | V2-T5 PASS (exit 0). Gate: diff confined to 3 allowlisted files (+103/−5); contract live: `colorBorder` export, `applyElement`→`colorBorder` routing, `readElementBorder`, `element-color-read` registered. Plan: T5 ☑. |
| 32 | 2026-06-03 | Kimi | result | V2-T3 PASS (exit 0). Gate: diff confined to `server/api.py` + `server/server.py`; contract live: 3 new routes, dialog handlers, `set_open_path`/`set_dialog_launcher`, `pwsh`→`powershell.exe` candidates (R02). Plan: T3 ☑. |
| 33 | 2026-06-03 | Kimi ×3 | dispatch | Wave B in parallel: V2-T4 (F1 shell rewire), V2-T7 (translate migration, commands.js), V2-T9 (F5 comments data layer). Disjoint allowlists; shared-file chains honored (T5 done before T7/T9; runtime-main chain T5→T9). |
| 34 | 2026-06-03 | Kimi | result | V2-T7 PASS (exit 0). Gate: commands.js only; `move` writes via `setProperty("translate")` (D6 ✓, no `transform` writes), `reorder` factory complete (re-parent capable; undo restores parent/position/translate). Plan: T7 ☑. Note: parallel uncommitted tasks make per-task diffs inseparable — gating by file-set + symbol inspection until milestone commit. |
| 35 | 2026-06-03 | Kimi | result | V2-T4 PASS (exit 0). Gate: 4 allowlisted app files; `dialogOpen`/`dialogSaveAs`/`save` + `openViaDialog` + `#save-btn` live; both path inputs and `deriveSaveDefault` removed (0 grep hits). Plan: T4 ☑. |
| 36 | 2026-06-03 | Kimi | result | V2-T9 PASS (exit 0). Gate: comments.js (+75) + runtime-main.js (+19) only; contract live: `agentInstruction` flag, `setAgentInstruction`, `buildAgentBlock`, `escapeAgentBlock`, `reanchorAfterMove`, `tag-agent` command. Plan: T9 ☑. |
| 37 | 2026-06-03 | Kimi ×4 | dispatch | Final product wave in parallel: V2-T8 (interaction.js + reorder.js, deletes resize/move.js), V2-T6 (border popover row), V2-T10 (serializer agent block), V2-T11 (composer + panel toggle). Disjoint allowlists; all deps ☑. |
| 38 | 2026-06-03 | Kimi | result | V2-T10 PASS (exit 0). Gate: serializer.js only; `buildAgentBlock` imported from comments.js, `getAgentBlockHtml` wired with fail-safe null (block failure never aborts save). Plan: T10 ☑. |
| 39 | 2026-06-03 | Kimi | result | V2-T6 PASS (exit 0). Gate: color-popover.js only; Border row (`data-prop="border-color"`), population via one `element-color-read`, mixed → empty + `mixed` placeholder. Plan: T6 ☑. |
| 40 | 2026-06-03 | Kimi | result | V2-T11 PASS (exit 0). Gate: composer module created; main.js add (L117) + reply (L467) use `openComposer`; `tag-agent` wired; composer CSS present; sole surviving `prompt()` is the one-time author-name ask (intentional, D4). Plan: T11 ☑. |
| 41 | 2026-06-03 | Kimi | result | V2-T8 PASS (exit 0). Gate: `interaction.js`+`reorder.js` created; `resize.js`/`move.js` deleted; selection observer registry live; R09 verified (interaction.js has zero selection.js imports); snappable/elementSnapDirections/threshold/reanchor present; no out-of-allowlist paths. Plan: T8 ☑. **PHASE 1 COMPLETE (T0–T11).** |
| 42 | 2026-06-03 | Claude sub-agent | dispatch | Milestone commit C1 via `rbtv-commit` (local only, no push): all Phase-1 product code + session artifacts on `hypresent-v2`. |

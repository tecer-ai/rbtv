# State Capsule — builder-open-deck

> **Mutable file — overwriting is the contract.** The orchestrator atomically overwrites this file at each batch close and each reviewer close. Holds in-flight resume state ONLY — never an audit log (that is `run-log.md`, append-only) and never a worker-facing decision (that is `decisions.md`, append-only). A WORKER never reads this file.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

---

## Resume Point

- **Last completed:** p3-1 (B7) CERTIFIED — kimi `8f7239c` (heterogeneous tray: uid identity, 3 row kinds existing/library/blank, duplicate, `getItems()`) + reviewer-fold `dc990dd` (blank-duplicate uid/id off-by-one). §1 gate clear (commit = EXACTLY the 4 allowlist files; conductor re-ran pb9+pb4 12-passed) + opus review DEFECTS_FIXED (p2-2 tray invariant verified INTACT via pb8 5-passed standalone; getItems/getOrder/library-only-dedup clean; kimi's 4 concerns all acceptable/pre-existing). Full suite pb9+pb4+pb8 17-passed EXIT 0. Statuses flipped (ADX-1). B7 CLOSED. (Phases 1 + 2 also CERTIFIED — Completed Batches; HR carry-forward = `phase-2/evidence/findings-p2.md`.)
- **RUN PAUSED — owner `html`→`studio` rename pending.** Safe boundary reached: NOTHING in flight, code tree committed (HEAD `dc990dd`). Per the owner's wait-for-safe-boundary choice, the conductor has signaled the owner to rename `rbtv/html/` → `rbtv/studio/` and is HOLDING. Do NOT dispatch p3-2 until BOTH: (a) owner confirms the rename is done, (b) conductor executes the "Rename handover" path-rewrite (Notes §). NOTE: a parallel mirror-install session also commits to rbtv master (it merged `[p4-0]` as `3566150` during p3-1) — its work is in `orchestration/` (disjoint from `html/`); the rename should land when both are quiescent.
- **Next after rename:** p3-2 (B8, kimi:default) in `studio/hypresent` — serial, plan order.
- **On resume:** rename NOT yet confirmed by owner → re-surface the rename ask, stay PAUSED (do not dispatch p3-2). Owner confirmed rename done → execute the Rename handover (Notes §), then dispatch p3-2 in `studio/hypresent`. Owner cancelled the rename → dispatch p3-2 in `html/hypresent` (no rewrite). This capsule itself moves to `studio/hypresent/docs/plan/...` after the rename — read it from the new location.
- **Last update:** 2026-06-09T23:31Z

## Run Configuration

- **Run mode:** end-to-end
- **Context-refresh:** suggest
- **Plan path:** html/hypresent/docs/plan/builder-open-deck/builder-open-deck-plan.md
- **Decisions file:** html/hypresent/docs/plan/builder-open-deck/decisions.md

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B7 | 3 | p3-1 | kimi:default | claude:opus after task | no |
| B8 | 3 | p3-2 | kimi:default | claude:opus after task | no |
| B9 | 3 | p3-3 | kimi:default | claude:opus after task | no |
| B10 | 3 | p3-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B11 | 4 | p4-1 | kimi:default | claude:opus after task | no |
| B12 | 4 | p4-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B13 | 5 | p5-refs | conductor (deterministic link check) | — | no |
| B14 | 5 | p5-compound | claude:opus | claude:opus review | no |
| B15 | 5 | p5-checkpoint | claude:sonnet (exercise) | claude:opus review — **HARD HALT, user approval required** | — |

> Original map (intake 2026-06-09, plan defaults, CLI-fleet code backend) approved by user. Phases 1–2 batches collapsed into Completed Batches.

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| B1–B3 | 1 | p1-1 · p1-2 · p1-checkpoint | kimi (cff2be0+4756b71, e9ce107) · claude:sonnet | Phase 1 CLOSED — builds CERTIFIED; checkpoint all-7-PASS, owner-approved 21:55Z | claude:opus — all clean |
| B4 | 2 | p2-1 | kimi (session 01b0dba3; commit b9aceef) | CERTIFIED — Open deck + ?file= + tray fill; pb2 regression green; spawned ADX-3 | claude:opus — DONE_WITH_NOTES, zero edits |
| B5 | 2 | p2-2 | kimi (session f44f82f6; 69cd7e2 + fold ea4efb3) | CERTIFIED — deck-themed thumbnails; ADX-3 stopgap removed; 5 e2e passed; headed proven; PB8-2b guard folded | claude:opus — DONE_WITH_NOTES, zero JS defects |
| B6 | 2 | p2-checkpoint | claude:sonnet exercise | CERTIFIED — all-6-PASS at floor, auto-passed (soft halt, end-to-end); HR = findings-p2.md | claude:opus — DONE_WITH_NOTES, all verdicts re-confirmed |
| B7 | 3 | p3-1 | kimi (session d41dcc3e; commit 8f7239c + fold dc990dd) | CERTIFIED — heterogeneous tray (uid identity, 3 kinds, duplicate, getItems); p2-2 tray invariant preserved (pb8 5-passed); full suite 17-passed | claude:opus — DEFECTS_FIXED (1 off-by-one folded), invariant verified |

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row. Format: ONE test-file path per row, relative to the work-dir root — EXACT paths only, never globs.

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** none functionally — but RUN is intentionally PAUSED (see below); p3-1 (B7) CERTIFIED, nothing in flight.
- **Checkpoint awaiting user approval:** none (next HARD halt is p5-checkpoint; p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS criteria)
- **ACTIVE PAUSE — html→studio rename handover (owner, separate plan):** safe boundary REACHED (p3-1 certified, tree committed, nothing in flight). Conductor has signaled the owner to rename `rbtv/html/` → `rbtv/studio/` and is HOLDING. **Do NOT dispatch p3-2** until (a) owner confirms rename done AND (b) conductor runs the "Rename handover" path-rewrite (Notes §). If owner cancels → dispatch p3-2 in `html/hypresent`, no rewrite.

## Notes for Resuming Conductor

Plan-backed run, all tasks SERIAL in plan order (no parallel waves). Shared-file serialization (ADX-3-updated): `builder-main.js`: p2-1→p2-2→**p3-1**→p3-2→p3-3→p4-1 · `tray.js`: p2-2→**p3-1** · `test_pb8_deck_open.py`: done. Hard-halt registry: p1-checkpoint (DONE) and p5-checkpoint NEVER auto-passed; p2 (DONE)/p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS criteria. Root decks (`tecer-gsmm-introduction*.html`) are READ-ONLY owner data.

**p3-1 BINDING INVARIANT (from B5 review — put in the p3-1 dispatch header):** tray.js exposes `setSrcdocProvider(fn)` where `fn(rec,index)=>Promise<string>`; the provider takes precedence over `libraryPath` in `render()`, and `setLibrary()` clears it. p3-1 adds row-manipulation (uid identity, 3 kinds, duplicate, getItems) and MUST preserve this precedence + the setLibrary-clears-provider invariant — reorder/remove already re-invoke the provider correctly (PB8-2b guards it). Known pre-existing scope gap (NOT a defect): tray renders thumbnails EAGERLY; spec's 30+-slide lazy-render edge unbuilt for both row kinds — flag at p5 if a large-deck target emerges.

Rulings in force: **ADX-1** (conductor does ALL status flips; executors write only within allowlist), **ADX-2 + D2** (recompose preserves inter-slide separators; spec erratum at the bottom of `specs/deck-save-spec.md` — point every deck-save-spec consumer at it: p3-3 + checkpoints), **ADX-3** (p2-2 builder-main.js stopgap removal — DONE), **D1** (kimi guidance-file check satisfied via `.kimi-agent/code-agent.yaml`).

Dispatch mechanics (validated this run): prompt files `_dispatch-{task}.md` = header (binding obligations, ADX-extended allowlist if any, path-mapping table, five-field return schema) + verbatim task payload; dispatch via Bash background: `cat <prompt> | kimi --work-dir "3-resources/tools/rbtv/html/hypresent" --print --input-format text --final-message-only > <plan>/_kimi-run-{task}.log 2>&1` + echo KIMI_EXIT. Pinned-flag gate before EVERY kimi dispatch (`kimi --help` grep; `--final-message-only` renders truncated as `--final-message…` — match on `final-message`). On return: §1 gate (commit hash in log, subject `[task-id]`, commit files == allowlist, tree clean, root decks clean, RE-RUN the test commands yourself), then opus review with pre-flagged brief (reviewer may fix in place, never commits — conductor folds reviewer fixes via explicit-path commit), then conductor flips statuses. Checkpoints: claude:sonnet COLD exercise (independent — no builder claims) → claude:opus findings audit → auto-pass on all-PASS (soft halts). e2e suite convention is HEADLESS (pb2–pb8, legitimate); headed fidelity floor lives in checkpoint exercises + task spot-checks.

Kimi sessions: p1-1 35fc3fde · p1-2 3be12714 · p2-1 01b0dba3-ba32-44f4-bc9a-44af4b998aad · p2-2 f44f82f6-69ff-4bd5-862e-19ea4d6416a9. Kimi commits land on rbtv `master` (kimi authed; exits: 0 ok, 1 non-retryable halt, 75 exit-75 recovery protocol in the kimi manual).

The rbtv repo working tree carries unrelated uncommitted changes from OTHER sessions (orchestration docs) — never `git add -A`; stage explicit paths only. The plan folder is TRACKED since commit 3766583; conductor bookkeeping edits show as tracked modifications and evidence + dispatch artifacts are untracked — committing the spine/evidence is a close-time decision via an rbtv-commit worker. Code commits so far: cff2be0, 4756b71, e9ce107, b9aceef, 69cd7e2, ea4efb3 (all on master, all `[task-id]`-prefixed). Run-log timestamps 20:05–20:16Z were ~10 min ahead of true clock; 22:00Z onward accurate.

Core-protocol availability line is stale on `claude` (live `models/claude/` package exists with manifest + manual; also `manus` present) — trust disk; mismatch logged 19:39Z.

**Rename handover (html→studio) — execute ONLY after p3-1 certifies, before p3-2.** Owner renames `rbtv/html/` → `rbtv/studio/` (first task of a separate plan). Gate: nothing in flight + tree committed. After the owner confirms the rename is done, rewrite `html/hypresent` → `studio/hypresent` in: (1) every remaining task frontmatter `work_dir:` + `allowed_workdir:` (phase-3/4/5 `.task.md`); (2) this capsule's `Plan path` + `Decisions file` + in-flight refs; (3) `run-log.md` `Spine location` + `Decisions file`; (4) the runtime launch commands (kimi `--work-dir`, the `cat` prompt path, the `> _kimi-run-*.log` redirect). UNCHANGED: `workspace: 3-resources/tools/rbtv`; `deliverables.md` + `_dispatch-*.md` path-mapping tables (work-dir-relative, carry no `html/hypresent` prefix). After rewrite, the rbtv repo's tracked paths are `studio/hypresent/...`; future kimi `[p3-x]` commits land there (allowlists are work-dir-relative — unchanged). Then dispatch p3-2 in `studio/hypresent`. Dispatch shell-cwd lesson: a prior diagnostic `cd` drifted the shell cwd and misfired the first p3-1 launch — ALWAYS use absolute paths in the kimi launch command (or `cd` to vault root first), never rely on the inherited cwd.

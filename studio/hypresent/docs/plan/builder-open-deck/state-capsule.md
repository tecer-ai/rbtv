# State Capsule — builder-open-deck

> **Mutable file — overwriting is the contract.** The orchestrator atomically overwrites this file at each batch close and each reviewer close. Holds in-flight resume state ONLY — never an audit log (that is `run-log.md`, append-only) and never a worker-facing decision (that is `decisions.md`, append-only). A WORKER never reads this file.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

---

## Resume Point

- **Last completed:** p3-checkpoint (B10) CERTIFIED — AUTO-PASS (soft halt, end-to-end, all-6-PASS genuine). claude:sonnet COLD HEADED exercise (own sheet `phase-3/evidence/findings-p3.md` + 14 captures: full restructure loop 10→reorder→remove→dup→blank→lib=12, saved-new reopens at 12 restructured; overwrite-chooser every save; saved output no hyp- tokens; pb4+pb5 regression 13-passed; owner decks SHA-256 unchanged; decisions.md shaped) → claude:opus findings audit ruled **ALL-PASS HOLDS** (`phase-3/evidence/findings-p3-opus-audit.md`): C2 identity-hash = ADX-2 consequence (overwrite shares C1's proven recompose path); C3 library-only asset-copy is spec-correct. §1 return-gate clean (criterion 4 conductor-re-run 13-passed EXIT 0; owner decks untouched). B10 CLOSED. **PHASE 3 COMPLETE** (build p3-1·p3-2·p3-3 + checkpoint). Forward finding `D-asset-colocation` recorded in decisions.md (deck saved to new dir won't resolve own assets/* — phase-4 cliff). (Earlier: phases 1-2 + all phase-3 build certified — Completed Batches; html→studio rename DONE `9288ede`. HR carry-forward = `phase-2/evidence/findings-p2.md` + now `phase-3/evidence/findings-p3.md`.)
- **NEXT:** B11 (p4-1, Phase 4 bridge) — Save-and-switch controls both directions (builder↔editor) + pb12 e2e. Read `phase-4/p4-1.task.md` for criteria.
- **REFRESH ACCEPTED — conductor STOPPED 2026-06-10T02:40Z.** Owner chose a fresh session at the phase-3→phase-4 boundary (B10 refresh-candidate=YES). Nothing in flight; phase 3 fully certified; spine + evidence committed (`cbd7dc7`, local-only, NOT pushed). **You (the fresh conductor) resume HERE: dispatch B11 (p4-1).** Reconcile the run-log tail vs disk FIRST — a parallel mirror/studio session also commits to rbtv master, so verify `git -C …/studio/hypresent log` shows `cbd7dc7` (this run's phase-3 close) and the certified p3-* commits as ancestors of HEAD before proceeding.
- **On resume (B11 / p4-1):** read `phase-4/p4-1.task.md` (Save-and-switch controls both directions builder↔editor + pb12 e2e). Route via the routing card; then dispatch-wrapper; code dispatch → opus review after task (map). Builder-main.js serialization reaches p4-1 (last writer). Carry `D-asset-colocation` (decisions.md) into the p4-1 dispatch context — the bridge opens saved decks in the editor, so a deck saved to a new dir risks missing own-asset refs. p4-checkpoint (B12) is the next SOFT halt; p5-checkpoint (B15) is the HARD halt.
- **⚠ WORKER NOTE for B11:** delegation map assigns p4-1 to `kimi:default`, but kimi 429-quota is exhausted this run. qwen proved itself for code in B9 (allowlist-perfect) and claude-cli is available — re-confirm the B11 worker at dispatch (likely qwen or claude-cli). If rerouting, log it like the B9 kimi→qwen reroute and update the delegation-map row.
- **Last update:** 2026-06-10T02:40Z (B10 CERTIFIED; phase 3 complete; owner chose fresh-session refresh — conductor STOPPED, resume at B11)

## Run Configuration

- **Run mode:** end-to-end
- **Context-refresh:** suggest
- **Plan path:** studio/hypresent/docs/plan/builder-open-deck/builder-open-deck-plan.md
- **Decisions file:** studio/hypresent/docs/plan/builder-open-deck/decisions.md

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B7 | 3 | p3-1 | kimi:default | claude:opus after task | no |
| B8 | 3 | p3-2 | kimi:default | claude:opus after task | no |
| B9 | 3 | p3-3 | qwen:default (RE-ROUTED from kimi 2026-06-10 — kimi 429 quota; owner chose qwen) | claude:opus after task | no |
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
| B8 | 3 | p3-2 | kimi (session 0e745997; commit 242a1e3 + fold e7f158e) | CERTIFIED — deck-mode library-add + blank-add (static button); regression pb8+pb9 green; suite 12-passed. [post-rename, in studio/hypresent] | claude:opus — DEFECTS_FIXED (latent null-libraryPath on deck-open folded + regression test) |
| B9 | 3 | p3-3 | **qwen** (RE-ROUTED from kimi; commit 4d55455 + fold 00e75d6) | CERTIFIED — Save-deck UI (new-file/overwrite); owner decks provably byte-unchanged; suite 19-passed. qwen's first code dispatch — allowlist-perfect | claude:opus — DEFECTS_FIXED (qwen had weakened test_pb11 reopen assertion to count-only; strengthened to disk-level restructure proof) |
| B10 | 3 | p3-checkpoint | claude:sonnet exercise | CERTIFIED — auto-pass (soft halt, all-6-PASS genuine); headed full restructure loop at floor; criterion-4 conductor-re-run 13-passed; owner decks SHA-256 unchanged. Evidence `phase-3/evidence/findings-p3.md`; forward finding D-asset-colocation. **PHASE 3 COMPLETE.** | claude:opus — ALL-PASS HOLDS (C2/C3 pre-flags resolved to genuine PASS vs spec+source); audit folded to findings-p3-opus-audit.md |

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row. Format: ONE test-file path per row, relative to the work-dir root — EXACT paths only, never globs.

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** none — PHASE 3 COMPLETE (build p3-1·p3-2·p3-3 + checkpoint B10 all certified). Next is B11 (p4-1). kimi 429 quota still exhausted; qwen proven for code (B9), claude-cli available — re-confirm B11 worker at dispatch.
- **Awaiting owner:** context-refresh offer at the phase-3→4 boundary (B10 refresh-candidate=YES). Owner to choose: fresh-session refresh before phase 4, or continue into B11. Do NOT dispatch B11 until answered. (Next HARD halt is p5-checkpoint; p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS — B10 met that bar.)
- **Rename handover:** COMPLETE (see Resume Point + the run-log rename event). Run continues in `studio/hypresent`; all forward paths rewritten.

## Notes for Resuming Conductor

Plan-backed run, all tasks SERIAL in plan order (no parallel waves). Shared-file serialization (ADX-3-updated): `builder-main.js`: p2-1→p2-2→**p3-1**→p3-2→p3-3→p4-1 · `tray.js`: p2-2→**p3-1** · `test_pb8_deck_open.py`: done. Hard-halt registry: p1-checkpoint (DONE) and p5-checkpoint NEVER auto-passed; p2 (DONE)/p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS criteria. Root decks (`tecer-gsmm-introduction*.html`) are READ-ONLY owner data.

**p3-1 BINDING INVARIANT (from B5 review — put in the p3-1 dispatch header):** tray.js exposes `setSrcdocProvider(fn)` where `fn(rec,index)=>Promise<string>`; the provider takes precedence over `libraryPath` in `render()`, and `setLibrary()` clears it. p3-1 adds row-manipulation (uid identity, 3 kinds, duplicate, getItems) and MUST preserve this precedence + the setLibrary-clears-provider invariant — reorder/remove already re-invoke the provider correctly (PB8-2b guards it). Known pre-existing scope gap (NOT a defect): tray renders thumbnails EAGERLY; spec's 30+-slide lazy-render edge unbuilt for both row kinds — flag at p5 if a large-deck target emerges.

Rulings in force: **ADX-1** (conductor does ALL status flips; executors write only within allowlist), **ADX-2 + D2** (recompose preserves inter-slide separators; spec erratum at the bottom of `specs/deck-save-spec.md` — point every deck-save-spec consumer at it: p3-3 + checkpoints), **ADX-3** (p2-2 builder-main.js stopgap removal — DONE), **D1** (kimi guidance-file check satisfied via `.kimi-agent/code-agent.yaml`).

Dispatch mechanics (validated this run): prompt files `_dispatch-{task}.md` = header (binding obligations, ADX-extended allowlist if any, path-mapping table, five-field return schema) + verbatim task payload; dispatch via Bash background with ABSOLUTE paths (shell-cwd-drift lesson): `cat "<ABS>/studio/hypresent/docs/plan/builder-open-deck/_dispatch-{task}.md" | kimi --work-dir "<ABS>/studio/hypresent" --print --input-format text --final-message-only > "<ABS>/…/_kimi-run-{task}.log" 2>&1` + echo KIMI_EXIT (where `<ABS>` = `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv`). Pinned-flag gate before EVERY kimi dispatch (`kimi --help` grep; `--final-message-only` renders truncated as `--final-message…` — match on `final-message`). On return: §1 gate (commit hash in log, subject `[task-id]`, commit files == allowlist, tree clean, root decks clean, RE-RUN the test commands yourself), then opus review with pre-flagged brief (reviewer may fix in place, never commits — conductor folds reviewer fixes via explicit-path commit), then conductor flips statuses. Checkpoints: claude:sonnet COLD exercise (independent — no builder claims) → claude:opus findings audit → auto-pass on all-PASS (soft halts). e2e suite convention is HEADLESS (pb2–pb8, legitimate); headed fidelity floor lives in checkpoint exercises + task spot-checks.

Kimi sessions: p1-1 35fc3fde · p1-2 3be12714 · p2-1 01b0dba3-ba32-44f4-bc9a-44af4b998aad · p2-2 f44f82f6-69ff-4bd5-862e-19ea4d6416a9. Kimi commits land on rbtv `master` (kimi authed; exits: 0 ok, 1 non-retryable halt, 75 exit-75 recovery protocol in the kimi manual).

The rbtv repo working tree carries unrelated uncommitted changes from OTHER sessions (orchestration docs) — never `git add -A`; stage explicit paths only. The plan folder is TRACKED since commit 3766583; conductor bookkeeping edits show as tracked modifications and evidence + dispatch artifacts are untracked — committing the spine/evidence is a close-time decision via an rbtv-commit worker. Code commits so far: cff2be0, 4756b71, e9ce107, b9aceef, 69cd7e2, ea4efb3, 8f7239c, dc990dd (all on master, all `[task-id]`-prefixed). Non-code: cab4285 (spine checkpoint), 9288ede (html→studio rename). Note `3566150` is the parallel mirror-install session's `[p4-0]` merge — NOT this run's. Run-log timestamps 20:05–20:16Z were ~10 min ahead of true clock; 22:00Z onward accurate.

Core-protocol availability line is stale on `claude` (live `models/claude/` package exists with manifest + manual; also `manus` present) — trust disk; mismatch logged 19:39Z.

**Rename handover (html→studio) — ✅ DONE 2026-06-10 (owner rename committed `9288ede`; spine checkpoint `cab4285` preceded it; path-rewrite executed; relocated code re-verified pb9+pb4+pb8 17-passed).** Record of what was rewritten — `html/hypresent` → `studio/hypresent` in: (1) every remaining task frontmatter `work_dir:` + `allowed_workdir:` (phase-3/4/5 `.task.md`); (2) this capsule's `Plan path` + `Decisions file` + in-flight refs; (3) `run-log.md` `Spine location` + `Decisions file`; (4) the runtime launch commands (kimi `--work-dir`, the `cat` prompt path, the `> _kimi-run-*.log` redirect). UNCHANGED: `workspace: 3-resources/tools/rbtv`; `deliverables.md` + `_dispatch-*.md` path-mapping tables (work-dir-relative, carry no `html/hypresent` prefix). After rewrite, the rbtv repo's tracked paths are `studio/hypresent/...`; future kimi `[p3-x]` commits land there (allowlists are work-dir-relative — unchanged). Then dispatch p3-2 in `studio/hypresent`. Dispatch shell-cwd lesson: a prior diagnostic `cd` drifted the shell cwd and misfired the first p3-1 launch — ALWAYS use absolute paths in the kimi launch command (or `cd` to vault root first), never rely on the inherited cwd.

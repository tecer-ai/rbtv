# State Capsule — builder-open-deck

> **Mutable file — overwriting is the contract.** The orchestrator atomically overwrites this file at each batch close and each reviewer close. Holds in-flight resume state ONLY — never an audit log (that is `run-log.md`, append-only) and never a worker-facing decision (that is `decisions.md`, append-only). A WORKER never reads this file.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

---

## Resume Point

- **Last completed:** Phase 1 build + verification — p1-1 CERTIFIED (commits cff2be0 + 4756b71), p1-2 CERTIFIED (commit e9ce107), p1-checkpoint EXERCISED with all 7 criteria PASS (evidence + findings.md in `phase-1/evidence/`)
- **Next dispatch:** ON RESUME, in order: (1) B3 reviewer — claude:opus review of the p1-checkpoint findings + evidence (review brief: audit `phase-1/evidence/findings.md` against the checkpoint task criteria and spot-check the evidence files; the exercise itself was conductor-gated §1-PASS); (2) obtain the OWNER's phase-1 approval — HARD HALT, never auto-passed (ask: "Approve phase 1 (save core) to proceed to phase 2?"); (3) on approval: flip p1-checkpoint statuses (plan checkbox, frontmatter, deliverables row ✅ per ADX-1), then dispatch p2-1 (kimi:default, B4) — compose its dispatch like `_dispatch-p1-2.md` (header + verbatim task payload, path-mapping table, ADX-2 spec-erratum pointer for any deck-save-spec consumer)
- **Last update:** 2026-06-09T20:33Z

## Run Configuration

- **Run mode:** end-to-end
- **Context-refresh:** suggest
- **Plan path:** html/hypresent/docs/plan/builder-open-deck/builder-open-deck-plan.md
- **Decisions file:** html/hypresent/docs/plan/builder-open-deck/decisions.md

## Approved Delegation Map

> User-approved 2026-06-09 (intake question round): plan defaults kept; CLI-fleet code backend confirmed.

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B3 | 1 | p1-checkpoint | claude:sonnet (exercise — DONE, all PASS) | claude:opus review PENDING — then **HARD HALT, user approval required** | yes (after approval) |
| B4 | 2 | p2-1 | kimi:default | claude:opus after task | no |
| B5 | 2 | p2-2 | kimi:default | claude:opus after task | no |
| B6 | 2 | p2-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS (end-to-end mode) | yes |
| B7 | 3 | p3-1 | kimi:default | claude:opus after task | no |
| B8 | 3 | p3-2 | kimi:default | claude:opus after task | no |
| B9 | 3 | p3-3 | kimi:default | claude:opus after task | no |
| B10 | 3 | p3-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B11 | 4 | p4-1 | kimi:default | claude:opus after task | no |
| B12 | 4 | p4-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B13 | 5 | p5-refs | conductor (deterministic link check) | — | no |
| B14 | 5 | p5-compound | claude:opus | claude:opus review | no |
| B15 | 5 | p5-checkpoint | claude:sonnet (exercise) | claude:opus review — **HARD HALT, user approval required** | — |

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| B1 | 1 | p1-1 | kimi:default (session 35fc3fde; commits cff2be0 + 4756b71) | CERTIFIED (incl. ADX-2 fix; identity recompose byte-identical, 26 tests) | claude:opus — review DONE_WITH_NOTES (fixed in place) + fix re-review DONE clean |
| B2 | 1 | p1-2 | kimi:default (session 3be12714; commit e9ce107) | CERTIFIED (45 tests + import EXIT 0; all 9 review pre-flags hold) | claude:opus — DONE, review clean, no edits |
| B3 | 1 | p1-checkpoint | claude:sonnet exercise | ALL 7 PASS — conductor §1-gated; opus review + user approval PENDING (see Resume Point) | pending |

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row. Format: ONE test-file path per row, relative to the work-dir root — EXACT paths only, never globs.

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** RUN PAUSED at user instruction (usage limit) — resume in a fresh session from this capsule
- **Checkpoint awaiting user approval:** p1-checkpoint (HARD HALT) — "Approve phase 1 (save core) to proceed to phase 2?" Findings: `phase-1/evidence/findings.md` (all 7 PASS; 2 accepted residuals: asset-copy-before-write orphan on mid-write crash; section tokens inside script bodies/attribute values out of v1 scope)

## Notes for Resuming Conductor

Plan-backed run, all tasks SERIAL in plan order (no parallel waves). Shared-file serialization per the plan's Orchestration table (`builder-main.js`: p2-1→p3-1→p3-2→p3-3→p4-1 · `tray.js`: p2-2→p3-1 · `test_pb8_deck_open.py`: p2-1→p2-2). Hard-halt registry: p1-checkpoint and p5-checkpoint NEVER auto-passed; p2/p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS criteria. Root decks (`tecer-gsmm-introduction*.html`) are READ-ONLY owner data.

Rulings in force: **ADX-1** (conductor does ALL status flips; executors write only within allowlist — erratum on all 8 build tasks), **ADX-2 + D2** (recompose preserves inter-slide separators; spec erratum at the bottom of `specs/deck-save-spec.md` — point every deck-save-spec consumer at it in dispatch headers), **D1** (kimi guidance-file check satisfied via `.kimi-agent/code-agent.yaml`).

Dispatch mechanics (validated this run): prompt files `_dispatch-{task}.md` in the plan folder = header (binding obligations, allowlist, path-mapping table, five-field return schema) + verbatim task payload; dispatch via Bash background: `cat <prompt> | kimi --work-dir "3-resources/tools/rbtv/html/hypresent" --print --input-format text --final-message-only > <plan>/_kimi-run-{task}.log 2>&1` + echo KIMI_EXIT. Pinned-flag gate before EVERY kimi dispatch (`kimi --help` grep; `--final-message-only` renders truncated as `--final-message…` — match on `final-message`). On return: §1 gate (commit hash in log, subject `[task-id]`, commit files == allowlist, tree clean, root decks clean, RE-RUN the test commands yourself), then opus review with pre-flagged brief (reviewer may fix in place, never commits), then conductor flips statuses.

Kimi sessions: p1-1 35fc3fde-9902-4ce9-b2f2-bc63a2ed6820 · p1-2 3be12714-e767-4ebf-9f5d-5cc82629c92b. Kimi commits land on rbtv `master` (kimi authed; exits: 0 ok, 1 non-retryable halt, 75 exit-75 recovery protocol in the kimi manual).

The rbtv repo working tree carries unrelated uncommitted changes from OTHER sessions (orchestration docs) — never `git add -A`; stage explicit paths only. The plan folder itself (spine, evidence, dispatch artifacts) is UNTRACKED and UNCOMMITTED by design so far — committing it is a close-time decision via an rbtv-commit worker. Run-log timestamps 20:05–20:16Z on 2026-06-09 were written ~10 min ahead of true clock (noted in-log); ordering correct.

Core-protocol availability line is stale on `claude` (live `models/claude/` package exists with manifest + manual; also `manus` present) — trust disk; mismatch logged 19:39Z.

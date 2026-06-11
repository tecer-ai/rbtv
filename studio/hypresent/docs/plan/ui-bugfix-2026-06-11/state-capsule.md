# State Capsule — ui-bugfix-2026-06-11

> Mutable file, atomic-overwrite per boundary. Planning decisions belong in `decisions.md`, not here.

> **Audience:** the next conductor session, resuming after interruption or context-refresh.

> **Regenerate, don't edit:** at each boundary write, re-instantiate from the skeleton with ONLY live values.

---

## Resume Point

- **Last completed:** ALL 8 fixes applied via codex + reconciled vs disk + verified (e2e 71-green baseline restored; `live_verify.py` + `live_verify_bug7.py` all-pass; cold review 0-critical). Regression fix-R1 done. 10 files modified + run folder.
- **Next dispatch:** FINAL — run COMPLETE PENDING USER ACTION. Awaiting owner commit decision (do NOT auto-commit). Open: FU-1 (D6 regression tests), FU-2 (bug-3 owner repro confirmation) — see `follow-ups.md`.
- **Last update:** 2026-06-11T19:55Z

## Run Configuration

- **Run mode:** end-to-end
- **Context-refresh:** suggest
- **Plan path:** NONE (plan-less — goal-prompt intake, conductor-led prep)
- **Decisions file:** `docs/plan/ui-bugfix-2026-06-11/decisions.md`

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| repro | diagnose | bug-3, bug-5 | opus (conductor) | n/a | no |
| fixes | execute | bug-1,2,4,7,8 + (3,5,6 after repro) | kimi-code 1.41.0 / default | opus cold-verify per fix | no |
| review | verify | all | opus (conductor) | n/a | no |

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| investigate | diagnose | bug-1..8 | opus + 3× sonnet | DONE | conductor-validated |

## Active Red Sets

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** none — resolved (kimi quota → codex executed all fixes).
- **Checkpoint awaiting user approval:** owner COMMIT decision. Uncommitted on HEAD `480596d`: 10 fix files (app/js/builder/builder-main.js, app/js/main.js, app/js/shell/{comment-composer,file-controls,shortcuts-help}.js, runtime/js/{comments,selection,shortcuts,text-edit}.js, tests/e2e/test_f5_comments.py) + the `docs/plan/ui-bugfix-2026-06-11/` run folder. EXCLUDE the 2 untracked `tecer-gsmm-introduction*.html` fixtures. Active parallel session in repo — NEVER amend; commit forward only.

## Notes for Resuming Conductor

- kimi work-dir = `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent`; git repo root one level up at `…\rbtv`.
- **Commit scope guard A:** repo has an unrelated uncommitted `orchestration/skills/orchestrating/core-protocol.md` — NEVER stage it with fix commits.
- **Commit scope guard B (parallel session):** `runtime/js/comments.js` carries a FOREIGN uncommitted hunk (buildAgentBlock text, ~line 666). Another session is live. Commit ONLY own hunks (git add -p / scoped); NEVER `git restore` comments.js or blanket-stage it. bug-2's region (~308-343) is disjoint from the foreign hunk.
- All 8 fixes are designed in `diagnosis.md` + `decisions.md`; fix-8 task at `tasks/fix-8-svg-editable.md`. Baseline = 71 green (targeted e2e set), exclude the 1 pre-existing marker-pixel fail.
- main.js touched by bugs 1,2,3,4; comments.js by bug 2 → sequence those edits, never parallel (D7).
- Owner decisions: D1 Ctrl+M · D2 clarify-dialog-only · D3 chip+hover path · D4 doc-order numbering · D7 Enter-submits · D8 coalesce-refresh.

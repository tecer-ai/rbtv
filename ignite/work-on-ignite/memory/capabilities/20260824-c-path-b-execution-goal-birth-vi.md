# 20260824-c-path-b-execution-goal-birth-vi — Path B execution-goal birth via scaffold

kind: creation
component: capabilities
date: 2026-08-24
commit: e9e0ac21
deployed: no
pin: ignite/planning/probes/probe-planning-path-b-materialize.py
components: team-kit

## Motivation
Approve in the approval thread is the only owner act that creates an execution goal [D12], and it must bind to plan artifacts at a recorded commit [T5-R5]. The old splice never birthed a second folder — it only re-nested seats into the same planning goal. spec-planning-door §2.2 required a validate-then-create handoff through existing `cmd_scaffold` plus Path-A-style atomic mint, with C-16 reclaim so a standing empty folder cannot burn the create-only name.

## Design
`path_b.py` `run_path_b` is the Path B caller. It validates (name free, roster unique, bound commit exists, artifacts resolvable at that commit, `_ref_target` refs if supplied) before any write, then injects scaffold/mint/reclaim into `supervised_materialize` on `PATH_B`. Scaffold is the existing `goal_cli.py` `cmd_scaffold` subprocess — the 5464-line monolith was not edited, because D23 would have required splitting it in the same change. The bound-commit pointer is written after a successful scaffold as `planning/bound-plan.json`. Mint reuses `planning_mint_argv` aimed at the NEW folder; `--goal-local` is never passed. Wrapper interface gained `record_goal_folder=` so D12 failure records land on the planning goal (there is no execution goal to stamp when birth fails). Rejected: extending `queue-request.js` / `--nested` onto a foreign goal; rewriting `cmd_scaffold`; a second door for D13.

## How it works
An approve-package names the execution-goal, planning-goal folder, goals root, lane, contract, bound commit, plan-artifacts path, roster, catalog, and sheet. `validate_mint_plan` refuses collisions as `roster-name-collision` before `rbtv-goal scaffold` runs. On success, `cmd_scaffold` creates the folder (no seat files); Path A argv mints the declared execution roster through the lock. If scaffold created a folder and mint then fails, `reclaim_execution_goal` tries catalogue teardown, always `rmtree`s the folder this wrapper created, and reindexes — today's teardown alone leaves the folder standing. Envelope refusal is still the wrapper's pre-validate stamp input.

## Consequences
Does not replace Path A or the goal-wide trigger. Does not Slack-post. `ignite/module.md` planning one-liner was left uncommitted because the file carried sibling hunks. `cmd_scaffold` still does not take `--plan-artifacts` as a flag; Path B records the pointer after the verb returns. impl-slack must call `run_path_b` on a genuine approve.

## Verification
`python -B ignite/planning/probes/probe-planning-path-b-materialize.py` EXIT 0 (folder created; planning `taskforce.csv` and `planning/current/` byte-identical; argv aims `--package` at the new folder). `python -B ignite/planning/probes/probe-planning-path-b-failure.py` EXIT 0 (name/roster collision records `origin-id`; scaffold-then-mint-fail reclaims the directory). Lock probe, failure-record probe, and `probe-queue-request-pass.js` still EXIT 0. KEEP extract of `_rewrite_in_place`, `append_taskforce_rows`, `registry-changed-underfoot`, and `check_acyclic(combined` vs `HEAD:ignite/team-kit/materialize-seats.py` is empty. Not deployed.

## ATTENTION
- Path B must not pass `--goal-local` or `--nested`; those target the same goal, never a foreign one.
- D12 failure records go to the planning goal via `record_goal_folder`. Writing them on the new folder would create `planning/current/` under a name that birth just refused or reclaimed.
- If `cmd_scaffold` returns non-zero after mkdir, Path B reclaims immediately — the wrapper only sets `scaffolded` after the callable returns.
- Teardown without a daemon cannot reclaim catalogue rows; the load-bearing half of birth-reclaim is folder removal plus reindex.
- A planning goal is untouched on the success path. Any write into its `planning/current/` is a Path B bug.
- D12 records land on the planning goal; never --goal-local

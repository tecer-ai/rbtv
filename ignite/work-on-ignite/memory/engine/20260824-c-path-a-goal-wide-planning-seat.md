# 20260824-c-path-a-goal-wide-planning-seat — Path A goal-wide planning-seat mint

kind: change
component: engine
date: 2026-08-24
commit: 88ac3206
deployed: no
pin: ignite/engine/probes/probe-queue-request-pass.js
components: planning,server

## Motivation
C5 planning non-termination is the IE-2 splice: `materializeArgv`'s `full` branch re-nested the whole `planning.csv` into the same goal, keyed per milestone. spec-planning-door §1 / §2.1 required that door deleted and Path A landed — a goal-wide mint of the five pipeline seats, once, through the supervised wrapper.

## Design
Admission is goal-keyed, not milestone-keyed: a `goal.md` frontmatter `role: planning` plus absence of the five seats on that goal's `taskforce.csv` is the only fire. The argv builder (`argv.py`) aims `--package` at the existing goal and never passes `--milestone-id`, `--nested`, or a `full`/`collapsed` branch. The mint goes through `supervised_materialize`; `uncast_in_sheet` moved into the wrapper and refuses the whole act. Unbuilt-seat repair was extracted to `unbuilt-seats.js` so the splice monolith is gone. Rejected: adapting `passesMinted` to a goal count (no analogue); keeping `--goal-local` on Path A (spec forbids); committing contended `ignite/module.md`.

## How it works
`server/index.js` still calls `runQueueRequestPass` before the lane watch. That function delegates to `planning/door.js` `runPlanningMintPass`, which walks daemon-lane goals, skips non-planning and already-minted (debug), and otherwise shells `path_a.py`. Path A builds argv, injects uncast into the wrapper, takes the lock, and runs one `materialize-seats.py` invocation. `goalLocalArgv` / `goalLocalSeatDir` stay on the unbuilt-seat lane only.

## Consequences
Deleted `planningMode`, `passesMinted`, `materializeArgv`, `uncastInSheet` (JS), `queueRequests`, and the per-milestone drain. Wrapper interface gained `uncast=` (callable) and `uncast_in_sheet`. Shared `ignite/module.md` planning one-liner is updated in the working tree but not pathspec-committed (sibling hunks from envelope/state-store). impl-pipeline must author the five seats named in `pipeline-seats.json` before a live mint succeeds against the catalog.

## Verification
`node ignite/engine/probes/probe-queue-request-pass.js` EXIT 0 (fires once / quiet no-op / second cadence mints nothing). `node --check` on every edited `.js` and `py_compile` on every edited `.py` exit 0. Wrapper probes still PASS. `git diff HEAD -- ignite/team-kit/materialize-seats.py` empty. Not deployed.

## ATTENTION
- A planning goal is `role: planning` in `goal.md` frontmatter. Any other goal is a quiet `not-planning-goal`.
- Already-minted means all five names in `pipeline-seats.json` are `taskforce.csv` seat rows. Partial sets re-fire.
- Do not pass `--nested` or `--milestone-id` on Path A. N single-seat mints have no rollback.
- `uncast` is the wrapper's job. A caller that mints without it can freeze a goal on one uncast row.
- `goalLocalArgv` is the unbuilt-seat lane, not this door. Path B must not use `--goal-local`.
- A planning goal is role: planning in goal.md frontmatter.
- Already-minted is all five pipeline-seats.json names on taskforce.csv.
- Do not pass --nested or --milestone-id on Path A.
- uncast is the wrapper's job.
- goalLocalArgv is the unbuilt-seat lane; Path B must not use --goal-local.

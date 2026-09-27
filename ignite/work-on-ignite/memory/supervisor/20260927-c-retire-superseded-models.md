# 20260927-c-retire-superseded-models — Retire opus-5, grok-4.6, gpt-5.6-sol, gpt-5.6-luna

kind: change
component: supervisor
date: 2026-09-27
commit: 035e39a6
deployed: no
pin: core/sub-agents/tool/test_cast.js
components: launch-profiles, envelope, bindings

## Motivation
Owner ruling 2026-09-24: only the newest models are used. 734866d3 had set the four superseded rows to `use=off` but kept them launchable, because ignite pinned them by name.

## Design
The four rows leave `core/sub-agents/tool/catalog.js` and `ignite/supervisor/models.csv`. Every live pin moves one-for-one to its successor: `claude-opus-5` -> `claude-opus-5-5`, `xai/grok-4.6` -> `xai/grok-4.7`, `gpt-5.6-sol` -> `gpt-6-sol`, `gpt-5.6-luna` -> `gpt-6-luna` (spawn-profiles.yaml profile keys and argv, bindings docs, help text, probe and selftest fixtures). Historical records keep the old names: memory entries, dated incident comments, and the D10 decision record in `meta/master/prompts/goal-master-prompt.md`. `grok-4.6-fast` and `gpt-5.6-terra` are out of scope and stay.

## Consequences
`cast` runs from the working tree, so the catalog change was live at once: vault goal pins (`.rbtv/goals/transcript-summarizer*/` seat.md, taskforce.csv, bindings.json) were moved in the same sitting. The running daemon reads the deployed worktree, so its spawn profiles still carry the old keys until a deploy. `cast -h` is back under 50 lines.

## Verification
`node core/sub-agents/tool/test_cast.js` and `node core/sub-agents/tool/test_route.js` pass. materialize-seats `--selftest`, `coord_selftest.py`, probe-binding-catalog, probe-spawn-refresh, probe-caged-settings, probe-chat-reply-leg, probe-master-profile, probe-goal-splice, probe-goal-lint-cage and probe-finish-edge pass. probe-foreground-carrier, probe-engine-library, probe-bindings and `goal_cli.py selftest` fail with the SAME failures on a HEAD copy of the probe (pre-existing, unrelated). `cast seat <seat> -p x --dry-run` on two moved vault seats resolves `claude-opus-5-5`.

## ATTENTION
1. A seat or profile that still names a retired model now fails at launch (cast refuses unknown models). Grep with `opus-5([^-.0-9]|$)|grok-4\.6([^-0-9]|$)|gpt-5\.6-(sol|luna)` before adding one back.

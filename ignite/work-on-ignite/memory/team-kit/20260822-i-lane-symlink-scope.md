# 20260822-i-lane-symlink-scope — lane-symlink-scope

kind: issue
component: team-kit
date: 2026-08-22
commit: d487c072
deployed: yes
pin: NONE
seeded: true

## Seen
Goal-local lane symlinks were reaching into directories they should never touch.

The symlinking step in `materialize-seats.py` that builds a goal-local lane was not scoped to module directories only — it could symlink `.git`, `.pytest_cache`, or `__pycache__` alongside the intended module dirs.

## Missed
None recorded in sources.

## Held
Goal-local lane symlinks now cover module directories only — never `.git`, `.pytest_cache`, or `__pycache__`.

Commit `d487c072` ("goal-local lane symlinks module dirs only — never .git/.pytest_cache/__pycache__") added an explicit exclusion in `materialize-seats.py`.

## commit
d487c072

## files
ignite/team-kit/materialize-seats.py

## deployed
yes

## pin
NONE

## ATTENTION
- If `materialize-seats.py`'s symlink step is touched again, keep the exclusion list explicit — a goal-local lane that symlinks `.git` risks cross-goal git state bleeding into an unrelated worktree; a symlinked `__pycache__`/`.pytest_cache` risks stale bytecode leaking between goals.
- Keep the exclusion list explicit; .git symlink risks cross-goal git bleed, cache symlinks risk stale bytecode leaking between goals

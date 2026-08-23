# 20260822-c-reopen-verb — reopen-verb

kind: creation
component: team-kit
date: 2026-08-22
commit: 17d75459
deployed: yes
pin: NONE
seeded: true

## What it is
D54/D66/D72: a `--reopen` verb — re-opens a `done` row by appending a new sitting with a recorded reason.

The original `done` row stands unrewritten; re-opening produces a new row, never an edit to history.

## Why
D54: a leader-written `done` may be re-opened by the leader on a late finding, by APPENDING a new sitting rather than mutating the closed row. D66: the D52 brake budget (per goal + seat + reason) must count a D54 re-open against it, and the brake ships BEFORE re-open so re-opening is never unbounded. D72: the re-open reason becomes a new column on the NEW sessions row, and the SYSTEM automatically flags downstream seats that ran on the now-retracted work (the graph walk-forward — the owner chose the fuller of two options here, effort L).

## How to use & where wired
`ignite/team-kit/coord.py` (the `--reopen` verb, +623 lines in the single commit), `ignite/team-kit/protocol.md` (documents the verb). Commit `17d75459` ("D54/D66/D72 — --reopen: re-open a done row by appending").

## commit
17d75459

## deployed
yes

## pin
NONE

## ATTENTION
- Never rewrite a closed `done` row in place to "fix" it after the fact — `--reopen` is the sanctioned path precisely because the append-only shape is what lets the D72 downstream-flagging graph walk find every seat that ran on retracted work. A hand-edited row breaks that walk silently.
- The D66 brake budget must be checked before assuming `--reopen` is safe to call repeatedly — it is bounded per (goal, seat, reason).
- Never hand-edit a closed done row; --reopen's append-only shape is what makes D72's downstream-flagging walk work
- D66 brake budget bounds --reopen per (goal, seat, reason); check before assuming repeat calls are safe

# 20260819-c-worktree-flow-propose-merge — worktree-flow-propose-merge

kind: creation
component: team-kit
date: 2026-08-19
commit: 7c829a91,f636b212
deployed: yes
pin: NONE
seeded: true

## What it is
Repo integration flow for worktree-based leader builds: the leader proposes (opens a merge request), the owner approves — `worktree-flow.py` gained self-rooting, a repos gate, `propose-merge`, and `--park` (fix-inventory D4).

## Why
D4: worktree changes must not land on the shared branch unreviewed. A leader working in its own worktree needed a way to hand its diff to the owner for approval instead of committing directly, and a way to park a worktree without losing it.

## How to use & where wired
`ignite/team-kit/worktree-flow.py` — self-roots against the caller's own worktree, gates on the repos it is allowed to touch, and exposes `propose-merge` (opens the merge request for owner approval) and `--park` (holds the worktree without merging). Commit `7c829a91` ("feat(worktree-flow): self-root, repos gate, propose-merge, --park") added ~500 lines. A same-day companion commit `f636b212` ("feat(spawn): scan both worktree roots in resolveSeatGrants") made `server/spawn/spawn.js`'s `resolveSeatGrants` scan both worktree roots so a seat grant resolves correctly regardless of which worktree root it launched from.

## commit
7c829a91,f636b212

## deployed
yes

## pin
NONE — fix-inventory flags this as weak attribution: `7c829a91` is P2's adoption of the shipped `worktree-flow.py`, not a purpose-built D4 commit, and no dedicated probe asserts the propose→approve gate; only an incidental RS-28 selftest reference to the unrelated `resolved_outputs` seed contract exists.

## ATTENTION
- No dedicated probe covers the propose→approve gate itself — a regression here would not be caught by the scheduled suite.
- `f636b212`'s `resolveSeatGrants` dual-root scan is a load-bearing companion to this creation: a worktree-flow change that assumes a single root will silently break seat-grant resolution for the other root.
- No dedicated probe covers the propose->approve gate
- resolveSeatGrants dual-root scan is a load-bearing companion

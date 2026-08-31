# 20260831-i-bound-commit-committed-inside — bound-commit committed inside the tree it names

kind: issue
component: planning
date: 2026-08-31
commit: 81e516275c6b29f74dfe3cb33dbc9563944d99ce
deployed: no
pin: ignite/planning/probes/probe-bound-commit.py
components: meta-leader,supervisor
register-id: G-leader-0828-1915

## Observed
`git show <bound>:<rel>/planning/bound-commit` printed a superseded hash while disk and the owner ask named `<bound>`. Measured on `stools-canvas-audio-elevenlabs-planning` (`d92e6350a` in-tree showed `303cdfacd`). `leader.md` claimed the file "is deliberately not inside the commit it names" while the three commands staged the whole `planning/` folder. Reproduced 2026-08-31 on a fixture vault following those commands: disk named HEAD, `git show HEAD:…/planning/bound-commit` printed the previous generation.

## Mechanism
`git commit -- <pathspec>` records the working-tree snapshot of those paths, not the index alone. Staging `planning/` then writing the new hash into `planning/bound-commit` after `rev-parse` leaves the previous pointer inside the tree the new hash names. A second commit to "fix" the pointer would name a tree that does not contain the second commit's content.

## Attempts
First attempt held — checked: `meta-planning/20260827-c-the-plan-declares-its-birth-th` ATTENTION ("bound-commit cannot be inside the commit it names. A future editor tempted to fix that by committing twice will produce a hash that names a tree without the second commit's content"). The stools goal was left unfixed on purpose because a live owner ask (`slack_ts 1787944024.138409`) named the disk hash. Filed `G-leader-0828-1915`, not fixed.

## Fix
`planning_bind.py` unlinks `planning/bound-commit` for the pathspec commit, then writes the new hash on disk. `git show <bound>:<rel>/planning/bound-commit` fails (absent). `leader.md` now runs that tool and the claim matches. Frozen once `approve-package.json` records `bound_commit`. Rejected: committing twice to make the in-tree copy equal the named hash; gitignoring the pointer in the vault (out of this repo); moving the pointer outside `planning/` (caged seats already read it there).

## Consequences
Anyone who resolves the approved tree and reads `bound-commit` out of it no longer gets a silently wrong hash — the path is absent, so they fall through to disk / `approve-package.json`. Old commits on finished goals are not rewritten.

## Verification
`ignite/planning/probes/probe-bound-commit.py` 156 red arm: a fixture vault following today's three-command bind printed a superseded hash from `git show <bound>:<rel>/planning/bound-commit` while disk named `<bound>`. Green arm: after `planning_bind.bind` the same `git show` fails (absent) and disk equals the new hash. Not deployed.

## ATTENTION
- Never re-bind a live owner-ask hash to "clean" an old in-tree copy. Readers of those goals already trust `approve-package.json`.
- Pathspec commit of `planning/` while `bound-commit` exists on disk reintroduces the lying file. Use the tool, do not restage the folder by hand.
- never re-bind a live owner-ask hash to clean an old in-tree copy
- pathspec commit of planning/ while bound-commit exists on disk reintroduces the lying file

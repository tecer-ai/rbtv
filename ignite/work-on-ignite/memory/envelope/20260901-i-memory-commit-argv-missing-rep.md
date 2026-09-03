# 20260901-i-memory-commit-argv-missing-rep — memory-commit argv missing --repo (repo-missing)

kind: issue
component: envelope
date: 2026-09-01
commit: a7d07241
deployed: no
pin: NONE

## Observed
`spawn-profiles.yaml`'s `memory-commit` fire-tool job (`ignite/envelope/spawn-profiles.yaml:1008`,
argv `python3 file-issue.py memory commit --json`) has refused `repo-missing` exit 2 on every
fire since 2026-08-25 (execs 32321/32622/32914, all exit 2; `G-leader-0827-1150`). No live
memory index has crossed the 60-line rotate trigger since (largest 25), so nothing was lost,
but the first over-threshold rotate would have written the memory tree with nothing to commit
it.

## Mechanism
`de9750a5` (2026-08-24, ported same-day to this checkout by the sibling live-repo commit
`3701c947`, see `team-kit/20260824-i-worktree-memory-default-live-r.md`) made `repo_root()`
walk up from cwd looking for `ignite/work-on-ignite/`, refusing `repo-missing` when cwd sits
inside no rbtv checkout, instead of falling back to the workspace's `rbtv.json` book. A daemon
fire-tool execution has no cwd inside the rbtv checkout (the daemon process's cwd is its own
working directory, not this repo), so every `memory-commit` fire after that commit landed
inherited the new refusal. The argv itself was never updated to carry `--repo` — the CLI grew
the flag (`--repo`, default the checkout enclosing cwd) but the caller that most needs it,
because it never runs with a checkout-rooted cwd, kept relying on the now-refused default.

## Attempts
First attempt held — checked: `G-leader-0827-1150`'s own suggested-action already named this
exact fix (add `--repo` to the argv) and had sat open since 2026-08-27 with no landing seat;
grepped `memory-commit` across the repo and the register for any earlier partial fix — none
found.

## Fix
Added `--repo /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv` to the `memory-commit`
argv in `spawn-profiles.yaml`, pinning the repo explicitly rather than trying to give the
fire-tool execution a checkout-rooted cwd (the daemon's spawn path does not offer per-job cwd
control here, and the CLI already exists to take an explicit override — using it is the
existing, no-new-surface fix). Rejected: reverting `de9750a5`'s cwd-strictness — that fix
exists specifically to stop memory writes silently landing in the wrong checkout from a
worktree, and weakening it back to a workspace-book fallback would reopen that defect for
every interactive caller, not just this one job.

## Consequences
No other argv row in `spawn-profiles.yaml` invokes a `file-issue memory` subcommand — grepped
the file and the repo for other `memory-commit`/memory-subcommand callers, none found, so this
is the only argv row this class of defect could hit. The register filing's suggested-action
also asked for a wider sweep of every argv row relying on an implicit cwd for reasons unrelated
to `repo_root` (other tools, other defaults) — left OUT of this fix as out of scope for the
register filing it closes; surfaced as a loose end for a future sweep.

## Verification
Red-first, current tree, cwd outside any checkout (`/tmp`): `python3 file-issue.py memory
commit --json` → `{"ok": false, "refusal": {"code": "repo-missing", ...}}` exit 2. Green,
same command with `--repo /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv --json`
→ `{"ok": true, "changed": [], "committed": null, ...}` exit 0 (memory tree clean today, so
nothing-to-commit; the CLI's own hermetic `file-issue.py selftest` arm
`memory-commit-pathspec` exercises the dirty-tree commit-then-noop path against a scratch
fixture repo and passed). Fixture fire of the exact fixed argv (same flags now in
`spawn-profiles.yaml`, run from `/`, simulating a daemon fire-tool cwd) also exited 0. Not yet
deployed — `spawn-profiles.yaml` is boot-read, so this commit needs `rbtv ignite daemon
deploy` (a restart) before the daemon's own fire picks it up; the live fire after deploy is
recorded separately, not in this memory entry.

## ATTENTION
- `spawn-profiles.yaml` is boot-cached — landing this commit does not arm it; the next daemon
  restart (deploy) does. Until then every fire keeps refusing `repo-missing`.
- Other argv rows in this same file may share the class "relies on an implicit cwd that
  `de9750a5` made load-bearing" — not swept here, register filing's suggested-action names it
  explicitly as a follow-up.
- `--repo` is hardcoded to this checkout's absolute path, not derived — if this rbtv checkout
  is ever relocated, this argv row (and every other absolute path already in the same file)
  needs updating together, not in isolation.
- spawn-profiles.yaml is boot-cached; this fix needs a restart to arm

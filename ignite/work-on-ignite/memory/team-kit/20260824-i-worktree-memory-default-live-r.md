# 20260824-i-worktree-memory-default-live-r — worktree-memory-default-live-repo

kind: issue
component: team-kit
date: 2026-08-24
commit: 3701c947,de9750a5
deployed: yes
pin: NONE

## Observed
Agents working inside 5-workbench/rbtv-redesign (a git worktree of the rbtv repo) ran
`file-issue memory file`/`memory commit` without --repo, and every entry landed in the
LIVE rbtv repo (3-resources/tools/rbtv) instead of the worktree they were sitting in. This
happened three times on 2026-08-24. In one of those occurrences an agent then ran
`git checkout -- <index-file>` in the live repo to undo its own stray line and wiped nine
other seats' uncommitted lines from that same index file in the process.

## Mechanism
`repo_root(cwd, override)` (file-issue.py) is the sole default-resolver behind
`memory_root`, `cmd_memory_file`, `cmd_memory_show/rotate/check/relint`, and
`cmd_memory_commit`. Without --repo it called `rbtv_repo(workspace_root(cwd))`, which walks
up from cwd only to find `.rbtv/config/`, then reads that WORKSPACE's `rbtv.json`
`rbtv_path` field — a single book-level pointer that always names the canonical LIVE repo.
cwd being inside a different rbtv checkout (a worktree/clone under 5-workbench/) was never
consulted: the workspace's book, not the actual checkout the agent stood in, decided the
target. Every write went to the live repo's memory tree regardless of which checkout the
agent's terminal was rooted in.

## Attempts
First attempt held — checked: no prior fix for this default existed (`repo_root` had not
changed since 2524e4c9/c80602d8 introduced the memory verbs; grep of team-kit's build memory
for repo_root/rbtv_path/workspace_root surfaced only unrelated capabilities/meta-leader
catalog-root entries, not this resolver).

## Fix
Added `enclosing_rbtv_repo(cwd)`: walks up from cwd (not from any workspace book) looking
for a directory containing `ignite/work-on-ignite/` — the signature of an rbtv checkout
itself. `repo_root` now calls this instead of `rbtv_repo(workspace_root(cwd))`. If cwd is
inside no rbtv checkout, it raises `Refuse("repo-missing", …)` naming --repo as the required
override — it never falls back to a hardcoded or workspace-book path. `--repo` stays the
explicit override for tests or off-checkout invocations; its `--help` text on all six memory
subcommands was reworded from "(tests only)" to "(default: the checkout enclosing cwd)" to
stop describing a now-inaccurate default. `register_root`/`rbtv_repo`/`workspace_root` (used
by the OPEN-side engine register and surface-scope validation, a different write target)
were left untouched — this fix is scoped to the memory-filing default only.

## Consequences
`file-issue memory file|show|rotate|check|relint|commit` invoked with no --repo now targets
whichever rbtv checkout the terminal's cwd sits inside, live repo or worktree alike. An
invocation from a directory that is inside no rbtv checkout (a vault scratch dir, a
non-rbtv repo) now refuses with `repo-missing` instead of silently resolving through
whatever workspace book happened to be above cwd. No caller in the existing selftest relied
on the old book-based default — every selftest memory call already passed --repo explicitly
— so no test needed reshaping.

## Verification
`python3 -m py_compile ignite/team-kit/file-issue.py` clean on both the live repo and the
5-workbench/rbtv-redesign worktree copies. `file-issue selftest` PASS on both (all green and
red arms, including memory-file/show/rotate/check/relint/commit). Manual three-location
probe with `memory commit --dry-run --json` (side-effect-free): run from inside the
worktree resolved repo=.../5-workbench/rbtv-redesign; run from inside the live repo
resolved repo=.../3-resources/tools/rbtv; run from an unrelated scratch directory returned
`{"ok": false, "refusal": {"code": "repo-missing", ...}}` exit 2, with no write in any case.

## ATTENTION
- register_root (the OPEN-side ignite-engine register write target) and normalize_surface's
  scope check still resolve through workspace_root/rbtv_repo/rbtv.json unchanged — that is a
  different, deliberately single-book target (one shared engine register), not a copy of
  this defect. Do not "fix" it the same way without separately confirming the register is
  meant to be per-checkout.
- This fix changes the default for six memory subcommands at once (file/show/rotate/check/
  relint/commit) because they all route through the same repo_root() default. A future
  agent adding a seventh memory subcommand gets the corrected default for free as long as it
  goes through repo_root/memory_root — bypassing that helper reopens this defect.

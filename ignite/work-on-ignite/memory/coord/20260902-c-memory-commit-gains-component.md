# 20260902-c-memory-commit-gains-component — memory commit gains --component pathspec scoping

kind: creation
component: coord
date: 2026-09-02
commit: da218a765d227534c8f330729908fd4c11db6d04
deployed: yes
pin: ignite/coord/file-issue.py selftest arm memory-commit-component-scope
components: work-on-ignite

## Motivation
`file-issue memory commit` stages/commits the whole `ignite/work-on-ignite/memory` tree by design —
the daily fire-tool sweep's designed scope (`team-kit/20260823-c-memory-commit-verb-daily-commi.md`),
kept unchanged. On a SHARED working tree, an ad-hoc `memory commit` run right after a console
session's own `memory file` swept every OTHER session's unrelated, uncommitted memory entries into
the caller's commit too — measured 2026-08-31: commit `ce89d759` carried three separate sessions'
entries under one author. The sweep's whole-tree scope was root-caused as DELIBERATE (a daily
scheduled job, ruled 2026-08-23 with console-session commits explicitly considered and rejected at
the time), so the fix adds narrower scoping as an option rather than removing or restricting the
sweep itself.

## Design
`--component` (repeatable) narrows the `git status`/`add`/`commit` pathspec from the whole memory
tree to just the named component folder(s) under it, so a session that just ran `memory file
--component X` can commit ONLY X, leaving every other component's in-flight, uncommitted work
untouched on the shared tree. Bare `memory commit` (no `--component`) is UNCHANGED — still the whole
tree, still the daily sweep's scope. Rejected: restricting the daily sweep itself to per-component
scans (would multiply the daily job into N separate invocations for no daily-sweep benefit, since the
sweep's whole point is committing everything at once); requiring every caller to pass `--component`
(would break the daily sweep's existing, ruled contract).

## How it works
`cmd_memory_commit` (`ignite/coord/file-issue.py`) builds its pathspec list `rels` as
`f"{root}/{c}"` for each `--component` value given, or `[root]` (the whole tree) when none are given.
Each named component directory is validated to exist before anything runs (`component-dir-missing`
refusal otherwise). `git status`/`add -A`/`commit` all take `rels` as their pathspec (via `--`,
re-resolved at commit time, following the "pathspec commit, not staging" discipline for a shared
index). The commit message's scope clause (`f"{len(changed)} file(s) under {scope} ..."`) names the
comma-joined component list, or the root path when unscoped, so the commit's own message states what
it was scoped to. The CLI's `--component` help text and the parser's description/epilog were updated
to document the new flag alongside the unchanged bare behaviour.

## Consequences
No change to the bare `memory commit` path or the daily fire-tool job's argv — the ruled daily sweep
scope is preserved exactly. A NEW capability exists for callers that want to commit only what they
just filed, but nothing currently calls it: no existing caller (the daily fire-tool job, or any
console-session helper) passes `--component` yet, so every existing caller still sweeps the whole
tree as before. This is the same "capability exists, nothing routes through it" pattern flagged by
the plan's judge as the THIRD instance seen this run (alongside `readiness-gate`'s gate-columns and
`cred-injection`'s planning-prompts) — worth judging as a class rather than three coincidences.

## Verification
Red-first in a scratch worktree reproduced the `ce89d759` cross-session sweep exactly (a bare commit
under one session's invocation swept a second session's unrelated, uncommitted component entry).
Green proven with TWO REAL PARALLEL invocations of `memory commit --component <X>`, each landing a
commit containing ONLY the files under its own named component and leaving the other's dirty. A new
`file-issue.py` selftest arm (`memory-commit-component-scope`) exercises this with a fixture repo:
two components each get an uncommitted entry, a `--component comp-a` commit lands only `comp-a`'s
file and leaves `comp-b`'s file dirty in the working tree. Deployed — `ignite/coord/file-issue.py`,
branch `ignite/core-daemon`, live on deploy tree `e8524c31`.

## ATTENTION
1. **The capability exists but nothing calls it yet.** `--component` is available on `memory commit`,
   but neither the daily fire-tool job's argv nor any console-session workflow passes it — every
   caller today still sweeps the whole tree, so THIS commit alone does not prevent a future
   `ce89d759`-shaped cross-session sweep. A caller must be updated to pass `--component` before this
   closes the loose end it was built for.
2. This is the third instance this run of a fix landing as an available-but-unwired capability
   (alongside `readiness-gate`'s gate-columns and `cred-injection`'s planning-prompts) — the plan's
   judge flagged it as a pattern, not a coincidence; a future audit of this run's fixes should check
   for wiring, not just existence.
3. Bare `memory commit` (no `--component`) is untouched and still commits the whole tree — do not
   assume adding `--component` support anywhere narrowed the DEFAULT behaviour of the daily sweep.
- no caller passes --component yet

# 20260823-c-memory-commit-verb-daily-commi — memory commit verb + daily commit job

kind: creation
component: team-kit
date: 2026-08-23
commit: dd271085
deployed: yes
pin: file-issue selftest memory-commit-pathspec
components: work-on-ignite,config

## Motivation
The daily `distill-ignite-memory` pass runs caged: it can write `ignite/work-on-ignite/memory/` (rw-paths grant) but cannot see the repo root, so its `_summary.md` rewrites and `memory rotate` moves would leave the rbtv repo dirty and uncommitted forever. Owner ruled (2026-08-23, goal-memory-management decisions.md, option a): a deterministic job OUTSIDE the cage commits, never a broad repo grant to the seat, never a human remembering.

## Design
`file-issue memory commit [--dry-run] [--message] [--json]` — the filing CLI already owns every memory write verb (file/show/rotate/check/relint), so the commit verb lives there rather than in a new tool (one CLI owns memory writes). It stages and commits ONLY the pathspec `ignite/work-on-ignite/memory`, exits 0 with "nothing to commit" when clean, refuses outside a git work tree. The trigger is a daemon fire-tool entry `memory-commit` (spawn-profiles.yaml tools:, argv = python3 + file-issue.py memory commit --json) plus a registered fire-tool job `memory-commit` and a cron-repeat queue row at 11:05Z daily, 32 min after the distill fire (10:33Z). Alternatives rejected: rw on the whole repo + .git for the seat (the grant the cage exists to avoid); console-session commits (repo goes dirty silently); a systemd user timer (would work, but the daemon queue already owns the cadence and its fire log is the evidence trail).

## How it works
Daily: 10:33Z the homed launch-agent job fires the distill seat (grok, caged, rw on memory); 11:05Z the fire-tool job runs the commit verb uncaged as the daemon user; the jobs_log row carries exit code + the verb JSON. Manual: `file-issue memory commit --dry-run` shows what would be committed. The tools table is boot-read FROM THE DEPLOY TREE: a new tool entry reaches the daemon only through `rbtv ignite daemon deploy` (a plain restart left it E_UNKNOWN_TOOL — measured dd271085).

## Consequences
Replaces nothing; adds one verb, one tool entry, one job, one queue row. First verification fire exec 31702 done/exit 0 (nothing to commit). The seat-side half was a second fix the same day: the seat model had to be the daemon pin `xai/grok-4.6` (alias `grok-4.6` was refused at spawn) and `rw-paths` had to grant the memory folder.

## Verification
`file-issue selftest` arm `memory-commit-pathspec` (fixture repo: dry-run reports, first commit lands only memory files while an outside change stays dirty, second run is a no-op); live `file-issue memory commit --dry-run --json`; jobs_log exec 31702 `done` exit 0 via the fire-tool path after deploy dd271085.

## ATTENTION
- A tool added to `spawn-profiles.yaml` `tools:` is invisible to the daemon until `rbtv ignite daemon deploy` — restart alone is not enough (the unit runs from ~/.local/state/rbtv-deploy).
- A daemon-launched seat needs the launch-spec PIN as model (`xai/grok-4.6`), not cast`s alias; cast`s dry-run does not catch it and the refused row parks the seat as live.
- The commit job commits whatever is under the memory tree at 11:05Z — a console session mid-edit there will see its half-done change committed; finish memory edits before that minute or commit them yourself first.

# 20260824-i-envelope-launch-unresolved-goa — envelope launch: unresolved goal scratch + 11GB shim copy

kind: issue
component: server
date: 2026-08-24
commit: 21aed149
deployed: no
pin: ignite/server/spawn/probes/probe-envelope-walls.js

## Observed
Every first launch of every goal died with `E_LAUNCH_REFUSED: unresolved <ws>/.rbtv/goals/<goal>/scratch`, and the launches that did compose wrote ~11 GB into goal scratch, filling `/` until the box had 0 MB free. 11 of 32 `server/spawn` probes and `probe-chat-live-session` were red on the first of the two.

## Mechanism
Two defects in the same launch step, both born in `ignite/envelope/`.

1. `envelope-template.yaml` family 4 (`scratch-temp`) bakes `{workspace}/.rbtv/goals/{goal}/scratch`, and `compiler.js#pushResolved` refuses any baked family path that does not resolve. Nothing on the launch path created that folder — `admitLaunch` compiled FIRST and only then called `writeConfigShims`, which is the one step that would have made it. The contract the compiler enforces (every baked path resolves) was violated at the producer: no launch step materialized the goal's own scratch.
2. `shims.js#HARNESS_STORES` listed store DIRECTORIES and `copyInto` had a recursive branch, so the scratch-config shim copied `~/.claude` (3.7 GB of transcripts) and `~/.local/share/opencode` (a 6.4 GB session database) whole. Spec §8's shim carries the config a tool READS; a store is config files sitting inside a data tree.

## Attempts
The prior sitting of this seat (Grok, killed mid-verification on a provider spending limit) treated the missing scratch as a fixture gap and added `mkdirSync(<runDir>/scratch)` to five `server/spawn` probe fixtures — uncommitted, and a symptom fix: it left every real first launch refusing. Those five edits were reverted here before the root fix landed. The 11 GB copy had no earlier attempt: the directory-shaped store list shipped in 7dd03133 and the disk filled the first time the suite ran it. Checked: 7dd03133, 0b08e042, be0458b9, 1d0f4903, spec-envelope.md §8.

## Fix
`admitLaunch` now calls `ensureGoalScratch(goalDir)` and writes the shims BEFORE `consumeLaunch` — the step that fills goal scratch is the step that creates it, and the compiler then sees a resolvable family-4 path. `HARNESS_STORES` and `TOOL_CONFIGS` are enumerated config FILES only (`~/.claude.json`, `~/.claude/settings.json`, `~/.claude/.credentials.json`, `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.config/opencode/opencode.json{,c}`, `~/.local/share/opencode/{auth,mcp-auth}.json`, stools/gtools `config.yaml`); the recursive-copy branch is deleted so a directory entry can no longer be added by accident.

## Consequences
`copyInto`'s recursive branch is deleted, so the shim can only ever copy a file. `probe-envelope-walls` leg 4 lost its subject (an unresolved `{goal}/scratch`) and was retargeted onto family 6's `{workspace}/.rbtv/mirror`; leg 6 is new and holds the materialization. Ten probe fixtures across `server/spawn`, `server/ticker` and `bridges/chat` needed a `.rbtv/mirror` and a workspace root outside `/tmp` for the same envelope model — filed separately. The tmux argv ceiling below is EXPOSED by this fix, not caused by it: those launches previously died at the compile.

## Verification
`node ignite/deploy/probe-suite.js --dir server/spawn/probes` went 20/32 to 30/32 (the residual two are the tmux argv ceiling, below). `probe-envelope-walls` leg 6 holds the materialization and leg 4 moved to family 6's `{workspace}/.rbtv/mirror`, the one baked path nothing creates. `envelope-shims.selftest.js`, `wall-report.selftest.js`, `envelope-launch.selftest.js`, `envelope-compiler.selftest.js` all exit 0.

## ATTENTION
- Never widen a `HARNESS_STORES`/`TOOL_CONFIGS` entry to a parent directory — one launch of the directory form wrote ~11 GB and filled the disk.
- The shim write is load-bearing for compile ORDER, not just for content: move it after `consumeLaunch` and every first launch refuses again.
- `cage.js#memoryMaskPaths` emits one `--tmpfs` per `~/.claude/projects/*/memory` — 689 entries / 67.8 KB of argv on this box — and tmux `new-window` refuses a command over roughly 16 KB. Every seat-door (tmux) launch now dies `E_CARRIER_FAILED: command too long`. Not fixed here (launch custody).

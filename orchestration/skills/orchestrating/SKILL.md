---
name: rbtv-orchestrating
description: "Orchestrate long-horizon, multi-agent work — route tasks to the right model/worker, dispatch with self-contained artifacts, verify every return against disk, and recover from halts. Use for any work that needs coordinated dispatches: executing a multi-step plan, running a goal end-to-end through worker agents, an AFK/long-horizon build, multi-worker or cross-repo coordination, or dispatching a CLI model (kimi, codex, claude-cli, opencode). Also the single front door for a standalone single dispatch to a named model (e.g. 'use kimi for X')."
---

# Orchestrating

**CRITICAL — load the core protocol FULLY before any orchestration action. Do not dispatch, route, or author artifacts before it is in context.**

This skill is the single front door for all orchestration in this workspace — from an all-night multi-agent build down to one minimal-ceremony dispatch to a named CLI model. There are no separate per-model skills; dispatch is `cast`.

1. Read `{rbtv_path}/orchestration/skills/orchestrating/core-protocol.md` IN FULL and keep it in context for the whole run. It carries the invariants, the situation table, and the static capability roster. The core does NOT bake in which rows are routable here; recall the catalog ∩ availability set on demand via `cast route --catalog`.
2. Follow the situation table in the core protocol: open the ONE card it names for the current situation (JIT), follow that card, and return to the table for the next situation. Open cards only as their situation arises — never front-load them.
3. For a CLI dispatch, compose `cast <harness> <model> <effort> <launch-root> -f <task file>` per the dispatch-wrapper card. Do not open anything under a models tree. `cast --dry-run` is the composition check.

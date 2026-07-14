# CLAUDE.md

RBTV plugin source repo. Components here are installed into target workspaces via `install.py`.

## Hard Rule — Keep Docs in Sync

When you create, rename, delete, or materially change ANY component in this repo (skill, command, rule, subagent, persona, workflow, task), you MUST in the SAME change:

1. Update `README.md` if the change affects what the README documents (component inventory, usage, install steps, module list).
2. Update the relevant file in `modules/` so the module's component list and descriptions reflect reality.
3. Update `admin/install/module-manifest.json` if a component was added, removed, or renamed.

A component change without a matching docs/module/manifest update is incomplete. Do not stop at the component edit.

## Hard Rule — RBTV Content Must Be General

RBTV is a self-contained toolkit; any workspace it installs into is just ONE instance of it. Every component (spec, workflow, standard, rule, persona, task) MUST be usable by ANY user. It MUST NOT contain anything specific to a single instance: no hardcoded vault/workspace paths, no client or project names, no build-time task IDs or hypothesis/decision markers. Per-instance inputs (a project's reference set, output location) are resolved at runtime — never baked into the file.

When carrying a file INTO this repo from an archive or an instance:

1. Read the original and CLASSIFY it: already general, or tweaked to one instance?
2. **Already general** → copy it verbatim to its analogous home in this repo.
3. **Tweaked to an instance** → NEVER generalize it silently or autonomously. Surface the instance-specific parts to the owner, propose how to generalize each (parameterize paths, drop build-history scaffolding, turn genuinely per-user inputs into a runtime fill-in), and build the generalized version together before writing it.

Precedent: `studio/deck-loop-spec.md` (carried + generalized 2026-06-13).

## ignite/ — Runnable Service Code (convention)

`ignite/` holds the source of the **ignite daemon** — runnable Node.js service code (server core, gateway, client CLI). It is the ONE sanctioned exception to this repo's markdown-only component inventory; runnable service code lives NOWHERE else in the repo.

Rules for `ignite/`:

1. **Not installed, deployed.** `install.py` never installs `ignite/` into a workspace's `.claude/` — it is deployed to a runtime host and run as a long-lived service (systemd). The install model above does not apply to it.
2. **The General rule applies in full.** No hardcoded workspace, vault, or host paths in the code; every per-instance input (workspace root, config, credentials) is resolved at runtime from the target workspace's `.rbtv/` runtime root or explicit configuration — never baked in.
3. **No runtime state in the repo.** The daemon's state (queues, job logs, per-workspace data) lives in the `.rbtv/` runtime root at the workspace it serves, never under `ignite/`.
4. **Self-contained subtree.** `ignite/` must stay relocatable as a plain folder/subtree move — no reach-outs into sibling module folders at import/require level. It consumes other rbtv capabilities via runtime interfaces, not source imports.
5. **Docs in sync.** When ignite components materialize or change, the Keep-Docs-in-Sync rule above applies (README, `modules/`, and — where applicable — the install manifest).

Development note: `ignite/` is developed on the `ignite/core-daemon` branch; it is absent from `master` until the repo-infrastructure ruling merges it.

## Module Files

`modules/` defines the installable bundles. Each module lists which skills, commands, rules, subagents, personas, workflows, and tasks ship with it. When a component's module membership changes, update both the old and new module files.

## Install Model — Just-in-Time

Installing and uninstalling components is fast and idempotent (`install.py`). Users install components just-in-time — only when a workflow needs them — so any given workspace carries only a SUBSET of RBTV components at once. A component absent from a workspace's `.claude/` is NORMAL, not a defect; confirm what is actually installed there before treating a component as missing.

> Codex mirror note: do not read the sibling `AGENTS.md`. It is an auto-generated mirror for Codex agents. This `CLAUDE.md` file is the source of truth.

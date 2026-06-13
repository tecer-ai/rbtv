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

## Module Files

`modules/` defines the installable bundles. Each module lists which skills, commands, rules, subagents, personas, workflows, and tasks ship with it. When a component's module membership changes, update both the old and new module files.

> Codex mirror note: do not read the sibling `AGENTS.md`. It is an auto-generated mirror for Codex agents. This `CLAUDE.md` file is the source of truth.

# CLAUDE.md

RBTV plugin source repo. Components here are installed into target workspaces via
`rbtv install` — `meta/installer/install.py`, which carried the name `install2.py`
until 2026-08-23.

## Hard Rule — Keep Docs in Sync

When you create, rename, delete, or materially change ANY component in this repo (skill, command, rule, subagent, persona, workflow, task), you MUST in the SAME change:

1. Update `README.md` if the change affects what the README documents (component inventory, usage, install steps, module list).
2. Update the `description` in the owning `<module>/<module>.json` and `<component>/<component>.json` when it no longer says what the module or component is. Those records ARE what `rbtv` lists.
3. Keep each unit in the folder that exposes it (`skills/`, `rules/`, `commands/`, `agents/`, `hooks/`, `mcp-servers/`, `capabilities/tools/<tool>/`, `folder-instructions/`), its frontmatter or record valid against the schema in `core/build/capabilities/templates/`. There is no central manifest: every inventory is read off the tree.

A component change without a matching docs/module/manifest update is incomplete. Do not stop at the component edit.

## Hard Rule — RBTV Content Must Be General

RBTV is a self-contained toolkit; any workspace it installs into is just ONE instance of it. Every component (spec, workflow, standard, rule, persona, task) MUST be usable by ANY user. It MUST NOT contain anything specific to a single instance: no hardcoded vault/workspace paths, no client or project names, no build-time task IDs or hypothesis/decision markers. Per-instance inputs (a project's reference set, output location) are resolved at runtime — never baked into the file.

When carrying a file INTO this repo from an archive or an instance:

1. Read the original and CLASSIFY it: already general, or tweaked to one instance?
2. **Already general** → copy it verbatim to its analogous home in this repo.
3. **Tweaked to an instance** → NEVER generalize it silently or autonomously. Surface the instance-specific parts to the owner, propose how to generalize each (parameterize paths, drop build-history scaffolding, turn genuinely per-user inputs into a runtime fill-in), and build the generalized version together before writing it.

Precedent: `studio/deck-loop-spec.md` (carried + generalized 2026-06-13).

## Hard Rule — Linux AND Windows

Every component MUST work on both Linux and Windows — rbtv runs on Linux servers and Windows desktops. When you can only run one, design for both and state in your done report which platform you actually verified. On a Windows machine, WSL (`wsl -d <distro>`) gives a real Linux run: clone the repo inside WSL rather than running over `/mnt/c`, so line endings and the home folder are Linux's. The installer selftest (`meta/installer/install.py selftest`) MUST pass on both before an installer change is committed.

The defects that have actually bitten (2026-09-28), each a rule:

1. **Text encoding is explicit.** Every text read/write passes `encoding="utf-8"` — Windows defaults to cp1252 and garbles any non-ASCII byte (`—` becomes `â€”`).
2. **Line endings are CRLF-tolerant.** A Windows checkout (`core.autocrlf`) delivers `\r\n`. Parse with `\r?\n` (never `startswith("---\n")` alone); decide "unchanged" by comparing the exact bytes you would write, not decoded text.
3. **A tool's `entry` names a runnable file** — a shebang or a known script extension. Windows needs an interpreter to build its `.cmd` shim, so a `.md` or extensionless data file refuses the whole install.
4. **No POSIX-only assumptions** — execute bits (`os.access X_OK` is always true on Windows), symlinks, `/tmp`, shell tools. Guard with `os.name` and give Windows its own path, or skip a POSIX-only selftest arm with `ctx.skip`, naming why.
5. **Windows file attributes.** Re-creating a Hidden or System file fails with a misleading `PermissionError`; rewrite in place (the installer's `lib/fsio.write_file`).
6. **`~/.rbtv/` is the per-user runtime** (`~/.rbtv/bin`), present on every machine — never a workspace marker. Walks that look for a workspace skip the home folder unless it holds a real install record (`.rbtv/config/install.json`).
7. **File and folder names are Windows-valid** — no `: * ? " < > | \`, no trailing dot or space, no reserved device names (`CON`, `NUL`, `COM1`…). Code that builds a name from a timestamp or user text sanitizes it.

## ignite/ — Runnable Service Code (convention)

`ignite/agents/` is Ignite 0.2: runnable Node code. A Slack message or a scheduled wake selects a primary-agent home under the workspace `.rbtv/agents/<slug>/`, runs one non-interactive turn, and the runtime delivers that turn's replies. It is deployed, not copied into a harness tree: `ignite/agents/tool/deploy.sh <commit>` (env `RBTV_DEPLOY`, `RBTV_WORKSPACE`) checks out the deploy worktree and restarts the user unit `rbtv-ignite-agents.service` (template `ignite/agents/units/rbtv-ignite-agents.service`). Operator steps are `ignite/agents/runbook.md`.

Rules for `ignite/agents/`:

1. **Not installed, deployed.** `install.py` does not install this service code into a workspace harness tree. What installs is the `create-primary-agent` skill and the `ignite-agent` tool's PATH link (`capabilities/tools/ignite-agent/`). The process runs from the deploy worktree.
2. **The General rule applies in full.** No hardcoded workspace, vault, or host paths. Every per-instance input (workspace root, Slack identity, token file, launch pin) is resolved at runtime from `<workspace>/.rbtv/agents/` or explicit configuration.
3. **No runtime state in the repo.** Agent homes, `state.sqlite`, and conversation history live under the workspace `.rbtv/agents/`, never under `ignite/agents/`.
4. **Self-contained subtree.** `ignite/agents/tool/` requires only its own files and Node built-ins. Other rbtv capabilities (`cast`, stools, audio) are runtime commands named in workspace config, never source imports.
5. **Docs in sync.** When this component changes, the Keep-Docs-in-Sync rule above applies.

## CLI Tool Placement (convention, owner-ruled 2026-07-26)

The destination for every rbtv CLI tool is inside its owning COMPONENT, in its own folder `<module>/<component>/capabilities/tools/<tool>/` with its `<tool>.json`; the `entry` names the program, and may climb out of the tool folder but never out of the component (a component not yet migrated keeps its program where it was). NEVER create a new interim CLI home (a `cli/` folder or ad-hoc scripts location).

## Module and component records

A module is a folder with its own `<module>/<module>.json`; a component is a folder inside it with its own `<component>/<component>.json`. Each carries a one-line `description` (a component also lists its outside `dependencies`). When a component moves between modules, move its folder and update both modules' records.

## Install Model — Just-in-Time

Installing and uninstalling components is fast and idempotent (`install.py`). Users install components just-in-time — only when a workflow needs them — so any given workspace carries only a SUBSET of RBTV components at once. A component absent from a workspace's `.claude/` is NORMAL, not a defect; confirm what is actually installed there before treating a component as missing.

> Codex mirror note: do not read the sibling `AGENTS.md`. It is an auto-generated mirror for Codex agents. This `CLAUDE.md` file is the source of truth.

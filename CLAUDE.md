# CLAUDE.md

RBTV plugin source repo. Components here are installed into target workspaces via
`rbtv install` — `meta/installer/install.py`, which carried the name `install2.py`
until 2026-08-23.

## Hard Rule — Keep Docs in Sync

When you create, rename, delete, or materially change ANY component in this repo (skill, command, rule, subagent, persona, workflow, task), you MUST in the SAME change:

1. Update `README.md` if the change affects what the README documents (component inventory, usage, install steps, module list).
2. Update the owning `<module>/module.md` so the module's component list and descriptions reflect reality — that file IS the module list `rbtv` reads.
3. Update the component's own `exposure.csv` if what it exposes changed. There is no central install manifest: `admin/install/module-manifest.json` was deleted with the predecessor installer on 2026-08-24, and every inventory is now read off the tree.

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
3. **A `path` row names a runnable file** — a shebang or a known script extension. Windows needs an interpreter to build its `.cmd` shim, so a `.md` or extensionless data file refuses the whole install.
4. **No POSIX-only assumptions** — execute bits (`os.access X_OK` is always true on Windows), symlinks, `/tmp`, shell tools. Guard with `os.name` and give Windows its own path, or skip a POSIX-only selftest arm with `ctx.skip`, naming why.
5. **Windows file attributes.** Re-creating a Hidden or System file fails with a misleading `PermissionError`; rewrite in place (the installer's `lib/fsio.write_file`).
6. **`~/.rbtv/` is the per-user runtime** (`~/.rbtv/bin`), present on every machine — never a workspace marker. Walks that look for a workspace skip the home folder unless it holds a real install record (`.rbtv/config/install.json`).
7. **File and folder names are Windows-valid** — no `: * ? " < > | \`, no trailing dot or space, no reserved device names (`CON`, `NUL`, `COM1`…). Code that builds a name from a timestamp or user text sanitizes it.

## ignite/ — Runnable Service Code (convention)

`ignite/agents/` is Ignite 0.2: runnable Node code. A Slack message or a scheduled wake selects a primary-agent home under the workspace `.rbtv/agents/<slug>/`, runs one non-interactive turn, and the runtime delivers that turn's replies. It is deployed, not copied into a harness tree: `ignite/agents/tool/deploy.sh <commit>` (env `RBTV_DEPLOY`, `RBTV_WORKSPACE`) checks out the deploy worktree and restarts the user unit `rbtv-ignite-agents.service` (template `ignite/agents/units/rbtv-ignite-agents.service`). Operator steps are `ignite/agents/runbook.md`.

Rules for `ignite/agents/`:

1. **Not installed, deployed.** `install.py` does not install this service code into a workspace harness tree. What installs is the `create-primary-agent` skill and the `ignite-agent` PATH link (`exposure.csv` `method=path`). The process runs from the deploy worktree.
2. **The General rule applies in full.** No hardcoded workspace, vault, or host paths. Every per-instance input (workspace root, Slack identity, token file, launch pin) is resolved at runtime from `<workspace>/.rbtv/agents/` or explicit configuration.
3. **No runtime state in the repo.** Agent homes, `state.sqlite`, and conversation history live under the workspace `.rbtv/agents/`, never under `ignite/agents/`.
4. **Self-contained subtree.** `ignite/agents/tool/` requires only its own files and Node built-ins. Other rbtv capabilities (`cast`, stools, audio) are runtime commands named in workspace config, never source imports.
5. **Docs in sync.** When this component changes, the Keep-Docs-in-Sync rule above applies.

## CLI Tool Placement (convention, owner-ruled 2026-07-26)

The settled destination for every rbtv CLI tool is inside its owning COMPONENT — `<module>/<component>/tool/` (a component whose main CLI it is: e.g. `meta/rbtv-cli/tool/rbtv`), or `<module>/<component>/capabilities/<name>/tool/` when the CLI is one capability of a larger component (e.g. `core/communication/capabilities/audio/audio.py`) — per the CMP-5 component-first layout (`system-definition/architecture/CMP-5-component-databases.md` in the merge-refactor campaign). NEVER create a new interim CLI home (a `cli/` folder or ad-hoc scripts location). The former off-tree CLIs under `orchestration/cli/` were moved into their components on 2026-08-23 (owner-directed), discharging the interim "stay in place until Phase-6" clause this paragraph used to carry. (`orchestration/team-monitor/`, this rule's original example, is itself deleted [T4-R8, del-observers].)

## Module Files

`modules/` defines the installable bundles. Each module lists which skills, commands, rules, subagents, personas, workflows, and tasks ship with it. When a component's module membership changes, update both the old and new module files.

## Install Model — Just-in-Time

Installing and uninstalling components is fast and idempotent (`install.py`). Users install components just-in-time — only when a workflow needs them — so any given workspace carries only a SUBSET of RBTV components at once. A component absent from a workspace's `.claude/` is NORMAL, not a defect; confirm what is actually installed there before treating a component as missing.

> Codex mirror note: do not read the sibling `AGENTS.md`. It is an auto-generated mirror for Codex agents. This `CLAUDE.md` file is the source of truth.

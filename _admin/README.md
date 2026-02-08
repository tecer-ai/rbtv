# RBTV — Admin Development Setup

Tools for developing and maintaining RBTV directly from its own repository, outside a BMAD installation.

---

## Why This Exists

RBTV is designed to run installed inside BMAD at `{project-root}/_bmad/rbtv/`. Its IDE configuration (`.cursor/` commands, agents, skills, rules) lives in `_config/.cursor/` and is normally copied to the BMAD project root by `_config/install-rbtv.py`.

When working directly from the `rbtv/` repository, those IDE tools don't work because:
- File paths in commands/skills/agents reference `{project-root}/_bmad/rbtv/...` which doesn't resolve from `rbtv/` root
- `_config/config.yaml` lacks standalone values (user name, language) since those are normally inherited from BMAD core

The admin install script solves both problems.

---

## Prerequisites

| Software | Purpose | Required |
|----------|---------|----------|
| **Python 3** | Runs the admin installation script | Yes |

---

## Setup

### Step 1: Run the Installation Script

From the rbtv root directory:

```bash
python _admin/install-admin-rbtv.py
```

The script prompts for your name and language preferences, then creates everything needed for standalone development.

### Step 2: Open Your IDE

Open Cursor in the `rbtv/` folder. All commands, agents, skills, and rules are now available.

**What the script does:**

1. Deletes existing `bmad-rbtv-*` and `admin-rbtv-*` files in `.cursor/`
2. Copies `_config/.cursor/` to `.cursor/` with path substitution (`{project-root}/_bmad/rbtv/` → removed, since `rbtv/` IS root)
3. Appends a path-resolution reinforcement to every command, agent, and skill file
4. Copies `_admin/.cursor/` to `.cursor/` (admin-only tools — commands, agents, skills, rules — no path transformation needed as they are authored for rbtv root)
5. Injects your name and language into the admin rule (`admin-rbtv-bmad-mirror.mdc`)
6. Ensures `.gitignore` at rbtv root contains required entries (additive — preserves existing content)

**Key points:**
- The script copies (not moves) files, so source files remain untouched
- Generated `.cursor/` content is gitignored
- Your name and language preferences are stored for future re-runs

---

## Understanding the Agentic System Framework

Before developing RBTV components, familiarize yourself with the agentic system framework. RBTV's framework is based on BMAD — both share the same architecture. RBTV has slight structural differences, but these do not affect the understanding of the documentation below.

**Read the following from `_admin/docs/benchmarks/bmad-agentic-system-study/`:**

| File | Content |
|------|---------|
| `02-agentic-system-architecture.md` | **Required.** Core architecture: layers, component roles, routing, state management |
| `03-component-patterns-and-templates.md` | **Required.** Patterns and templates for every component type (agents, workflows, steps, tasks, commands) |
| `01-bmad-architecture.md` | Optional. Higher-level BMAD overview — useful for additional context |

**Also read:** `workflows/build-rbtv-component/data/admin-restrictions.md` — hard restrictions that govern all RBTV development work.

---

## Generated Directory Structure

After installation, your directory structure will look like this:

```
rbtv/
├── .cursor/                    (generated, gitignored)
│   ├── commands/bmad-rbtv-*    (from _config/.cursor/, paths adjusted)
│   ├── commands/admin-rbtv-*   (from _admin/.cursor/, as-is)
│   ├── agents/bmad-rbtv-*      (from _config/.cursor/, paths adjusted)
│   ├── agents/admin-rbtv-*     (from _admin/.cursor/, as-is)
│   ├── skills/bmad-rbtv-*      (from _config/.cursor/, paths adjusted)
│   ├── skills/admin-rbtv-*     (from _admin/.cursor/, as-is)
│   ├── rules/bmad-rbtv-*       (from _config/.cursor/, as-is)
│   ├── rules/admin-rbtv-*      (from _admin/.cursor/, values injected)
│   └── mcp.json                (from _config/.cursor/, as-is)
├── .claude/                    (generated, gitignored)
├── .gitignore                  (entries added by script, preserves existing)
└── _admin-output/              (runtime output, gitignored)
```

---

## Output Folder

The admin rule sets `output_folder` to `_admin-output/`. This folder is **gitignored** — anything saved there is ephemeral and will not be committed.

**Managing output location:**
- **Before creation:** Instruct the agent to save to a specific rbtv path instead of the default output folder (e.g., `_admin_/`, `workflows/`, etc.). Some agents have pre-established output paths that already bypass the output folder.
- **After creation:** Move the file from `_admin-output/` to its intended location within the rbtv repo.

---

## Gitignore Rules

The install script ensures `.gitignore` at rbtv root contains required entries. It is **additive** — existing content is preserved, and only missing entries are appended.

| Ignored Path | What It Contains | Risk |
|-------------|-----------------|------|
| `.cursor/` | All generated IDE files (commands, agents, skills, rules, mcp.json) | **Any file you create directly inside `.cursor/` will NOT be tracked by git.** Personal cursor tools placed here are local-only. |
| `.claude/` | Generated Claude Code IDE files | Same as `.cursor/` — local-only. |
| `_admin-output/` | Runtime output from admin agents | **Anything saved here is ephemeral.** Move files to a tracked location before committing. |
| `.gitignore` | The repo .gitignore at rbtv root | The script adds this entry so the generated .gitignore ignores itself. |

> **Warning — files you may lose:**
>
> - If you create a personal cursor tool (e.g., `.cursor/commands/my-helper.md`), it lives only on your machine. Back it up elsewhere or add it to a tracked folder.
> - If an agent writes output to `_admin-output/`, that file will not appear in `git status`. Move it to a tracked path (e.g., `_admin/`, `workflows/`, `agents/`) before committing.
> - You can safely add your own rules to `.gitignore` — the script only appends missing entries and will not overwrite your additions.
---

## Updating RBTV (Re-sync)

After every `git pull`, re-run the script:

```bash
python _admin/install-admin-rbtv.py
```

It reads your existing configuration values as defaults (press Enter to keep them), then deletes and recreates all managed files.

> **Important:** The script deletes ALL files with `bmad-rbtv-` or `admin-rbtv-` prefixes in `.cursor/` subdirectories. See naming conventions below.

---

## Naming Conventions

The admin script manages files by prefix. Using a reserved prefix on your own files will cause them to be **deleted on re-sync**.

| Goal | Where to put it | Required prefix |
|------|-----------------|-----------------|
| Personal cursor tool (not synced, admin-only) | `.cursor/` directly at rbtv root | Any name **except** `bmad-rbtv-` or `admin-rbtv-` |
| Tool for BMAD instances (distributed to users) | `_config/.cursor/` | `bmad-rbtv-` |
| Tool for admin development (internal rbtv work) | `_admin/.cursor/` | `admin-rbtv-` |

**Examples:**
- `my-debug-helper.md` in `.cursor/commands/` — safe, won't be deleted
- `bmad-rbtv-my-tool.md` in `.cursor/commands/` — **will be deleted** on re-sync (put it in `_config/.cursor/commands/` instead)

> **Note:** Any personal cursor tools must be added to `.gitignore` for rbtv maintenance.

---

## How Path Resolution Works

RBTV source files use `{project-root}/_bmad/rbtv/...` paths designed for BMAD installations. In standalone mode, the admin system resolves them in two layers:

| Layer | What | How |
|-------|------|-----|
| **Layer 1** — `.cursor/` files | Paths rewritten at copy time | `{project-root}/_bmad/rbtv/` is stripped, so `{project-root}/_bmad/rbtv/agents/domcobb.md` becomes `agents/domcobb.md` |
| **Layer 2** — Agent/workflow source files | NOT copied; resolved at runtime by `admin-rbtv-bmad-mirror.mdc` | `{project-root}/_bmad/rbtv/...` → `./...` (this repo's root); `{project-root}/...` (everything else) → `./_admin/docs/BMAD-mirror/...` (the mirror) |
| **Config overrides** | Admin rule provides standalone values | `user_name`, `communication_language`, `document_output_language`, and `output_folder` take precedence over `_config/config.yaml` |

---

## Working on RBTV from BMAD Root

If you prefer to develop RBTV from within a BMAD installation instead of standalone, you can adjust workspace visibility.

**Default Configuration:**
The `_config/install-rbtv.py` installer creates `.vscode/settings.json` that hides `_bmad/` (including `_bmad/rbtv/`) from the Cursor sidebar. AI agents can still read these files.

```json
{
  "files.exclude": {
    "_bmad": true,
    "_bmad-output/archive": true,
    ".cursorignore": true,
    ".gitignore": true
  }
}
```

**Adjustment for RBTV development:**
Replace the `_bmad` exclusion with more specific entries that keep RBTV visible:

```json
{
  "files.exclude": {
    "_bmad/core": true,
    "_bmad/bmm": true,
    "_bmad/cis": true,
    "_bmad/_config": true,
    "_bmad-output/archive": true,
    ".cursorignore": true,
    ".gitignore": true
  }
}
```

**Key points:**
- This hides other BMAD modules while keeping `_bmad/rbtv/` visible in the sidebar
- The RBTV installer will not overwrite these changes — it only creates `.vscode/settings.json` if `.vscode/` does not exist
- No `.cursorignore` changes are needed — AI agents already have access to `_bmad/rbtv/`

---

## Content Duplication: CLAUDE.md & admin-rbtv-bmad-mirror.mdc

**Execution:** Agents must read exactly one canonical file for path resolution.

- **Claude Code:** Read `CLAUDE.md` only.
- **Cursor IDE:** Read `.cursor/rules/admin-rbtv-bmad-mirror.mdc` only.

**Editing:** When editing mirrored content, update both files to match.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Commands not appearing | Run `install-admin-rbtv.py` and restart Cursor |
| Path resolution errors | Re-run the install script to regenerate `.cursor/` files |
| Files deleted unexpectedly | Check naming conventions — `bmad-rbtv-*` and `admin-rbtv-*` are managed prefixes |
| Config values lost after re-sync | The script reads existing values as defaults — press Enter to keep them |
| Output files not persisting | `_admin-output/` is gitignored — move files to their intended location before committing |

---

*Built with the BMAD Method — structure reveals solutions.*

---
title: 'Change Point: BMAD CLAUDE.md as Installation Artifact'
docType: 'change-point'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted: []
inputDocuments:
  - _config/bootstrap.py
  - _config/claude/
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-13'
yoloMode: false
---

# BMAD CLAUDE.md as Installation Artifact

**Type:** Change Point
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Problem

`H:\BMAD\CLAUDE.md` is maintained manually and is not part of the RBTV installation pipeline. New BMAD installations have no CLAUDE.md, so Claude Code lacks the workspace context it needs to work effectively. The file must be authored once and deployed automatically.

---

## Desired Outcome

The installer (`bootstrap.py`, workspace mode) generates a correct `CLAUDE.md` at the BMAD project root (`{root}/CLAUDE.md`) during installation.

---

## Implementation Notes

### Source artifact

Store the canonical CLAUDE.md template at `_config/CLAUDE.md` (or `_config/claude-md/CLAUDE.md`).

Use `{placeholder}` syntax for dynamic values (consistent with existing RBTV convention):
- `{user_name}` — from BMAD core/config.yaml
- `{rbtv_version}` — from bmad-compat.yaml or manifest.yaml

### Git repo detection

The installer must detect which sub-directories inside the BMAD root are independent git repositories, and list them in the CLAUDE.md under the "Git Repositories" section.

Detection logic:
```python
import subprocess

def find_git_repos(root: Path) -> list[dict]:
    """Find all git repos nested inside root (excluding root itself)."""
    repos = []
    for d in root.rglob(".git"):
        if d.is_dir() and d.parent != root:
            repo_path = d.parent
            rel = repo_path.relative_to(root)
            # Get remote URL for description
            try:
                url = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(repo_path), text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                url = "(no remote)"
            repos.append({"path": str(rel).replace("\\", "/"), "remote": url})
    return repos
```

The detected repos populate the "Git Repositories" table in the generated CLAUDE.md.

### Installer integration

Add `workspace_generate_claude_md(root, rbtv_dir)` function to `bootstrap.py` and call it in `run_workspace_mode()`.

The function:
1. Reads the template from `_config/CLAUDE.md`
2. Detects git repos via `find_git_repos(root)`
3. Renders the repos table into the template
4. Writes to `root / "CLAUDE.md"` (overwrite — it's a generated artifact)

### Idempotency

Always overwrite — CLAUDE.md at the BMAD root is a generated file, not user-edited. Document this in CLAUDE.md itself with a header comment.

---

## Acceptance Criteria

- Running `python _config/bootstrap.py` generates `CLAUDE.md` at BMAD root
- Generated file includes correct git repo table with detected repos
- Re-running installer overwrites and re-generates correctly
- Installer prints status line: `Generating CLAUDE.md` / `Done`

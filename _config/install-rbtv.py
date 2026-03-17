#!/usr/bin/env python3
"""
RBTV Unified Installation Script

Three modes:
  workspace -- Full workspace setup: .cursor/.claude config, BMAD configs, help catalog (default)
  admin     -- Standalone dev setup: .cursor/ at rbtv root with path substitution + admin rules
  sync      -- BMAD config patching only: output paths, help catalog — no workspace artifacts

Usage:
    python _config/install-rbtv.py                          # workspace mode (default)
    python _config/install-rbtv.py --mode workspace
    python _config/install-rbtv.py --mode admin
    python _config/install-rbtv.py --mode sync
    python _config/install-rbtv.py --skip-version-check
"""

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────────

def get_paths():
    """Resolve source and destination paths from this script's location."""
    script_dir = Path(__file__).parent.resolve()   # rbtv/_config/
    rbtv_dir = script_dir.parent                   # rbtv/
    root = rbtv_dir.parent.parent                  # BMAD project root (workspace/sync modes)
    return {
        "config": script_dir,
        "rbtv": rbtv_dir,
        "root": root,                              # BMAD project root
        "config_claude": script_dir / "claude",
        "admin_claude": rbtv_dir / "_admin" / "claude",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Workspace mode: directories to search for bmad-rbtv* files before clean install
WORKSPACE_RBTV_SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
    ".claude/commands",
    ".claude/rules",
    ".claude/agents",
    ".claude/skills",
]

# Admin mode: managed file prefixes and extra managed files
ADMIN_MANAGED_PREFIXES = ("bmad-rbtv", "admin-rbtv")

ADMIN_SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
    ".claude/commands",
    ".claude/rules",
    ".claude/agents",
    ".claude/skills",
]

ADMIN_EXTRA_MANAGED_FILES = [
    ".cursor/mcp.json",
    ".claude/.mcp.json",
]

# Admin mode: path substitution for {project-root}/_bmad/rbtv/ → ""
ADMIN_PATH_FIND = "{project-root}/_bmad/rbtv/"
ADMIN_PATH_REPLACE = ""

# Reinforcement appended to commands/agents/skills in admin mode
ADMIN_REINFORCEMENT = (
    "\n\n> **ADMIN MODE:** Before proceeding, load and read "
    "`.claude/rules/admin-rbtv-bmad-mirror.md` for path resolution "
    "and config values. Key: `.claude/` and `tasks/` are at workspace root.\n"
)

ADMIN_RULE_FILE = "admin-rbtv-bmad-mirror.md"

ADMIN_GITIGNORE_ENTRIES = [
    "/.cursor/",
    "/.claude/",
    "/CLAUDE.md",
    ".gitignore",
]

# Legacy entries that must be replaced with anchored forms
ADMIN_GITIGNORE_LEGACY_MAP = {
    ".cursor/": "/.cursor/",
    ".claude/": "/.claude/",
}

ADMIN_CONFIG_DEFAULTS = {
    "user_name": "",
    "communication_language": "English",
    "document_output_language": "English",
}


# ─────────────────────────────────────────────────────────────────────────────
# Shared: BMAD version pre-flight check
# ─────────────────────────────────────────────────────────────────────────────

def _read_yaml_field(text: str, field: str) -> str:
    """Extract a simple YAML string field value using regex."""
    # Matches: field: "value" or field: value
    match = re.search(rf'^{re.escape(field)}:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _read_yaml_nested_field(text: str, parent: str, field: str) -> str:
    """Extract a nested YAML field (parent:\n  field: value)."""
    match = re.search(
        rf'^{re.escape(parent)}:.*?\n\s+{re.escape(field)}:\s+(\S+)',
        text, re.MULTILINE | re.DOTALL
    )
    return match.group(1).strip() if match else ""


def _parse_version(version_str: str):
    """
    Parse a version string like 6.0.0-Beta.4 into a comparable tuple.
    Returns (major, minor, patch, pre_label, pre_num).
    Pre-release: Beta < RC < (no pre-release).
    """
    # Normalize
    v = version_str.strip().lstrip("v")
    # Match: major.minor.patch[-pre_label.pre_num]
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?$', v)
    if not m:
        return (0, 0, 0, "z", 0)  # unparseable sorts last

    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_label = m.group(4).lower() if m.group(4) else ""
    pre_num = int(m.group(5)) if m.group(5) else 0

    # Stable > RC > Beta — invert label for comparison (lower char = older)
    label_order = {"beta": 0, "rc": 1, "": 2}
    label_key = label_order.get(pre_label, 0)

    return (major, minor, patch, label_key, pre_num)


def check_bmad_version(rbtv_dir: Path, root: Path) -> dict:
    """
    Pre-flight BMAD version check.
    Reads bmad-compat.yaml for target/min versions.
    Reads _bmad/_config/manifest.yaml for installed BMAD version.
    Returns: {"status": "ok"|"warn"|"strong_warn"|"unknown", "message": str}
    """
    # Read RBTV declared versions
    compat_file = rbtv_dir / "bmad-compat.yaml"
    if not compat_file.exists():
        return {"status": "unknown", "message": "bmad-compat.yaml not found — skipping version check"}

    compat_text = compat_file.read_text(encoding="utf-8")
    target_version = _read_yaml_field(compat_text, "bmad_target_version")
    min_version = _read_yaml_field(compat_text, "bmad_min_version")

    if not target_version:
        return {"status": "unknown", "message": "bmad_target_version not found in bmad-compat.yaml"}

    # Read installed BMAD version
    manifest_file = root / "_bmad" / "_config" / "manifest.yaml"
    if not manifest_file.exists():
        return {
            "status": "unknown",
            "message": (
                f"WARNING: _bmad/_config/manifest.yaml not found at {root}.\n"
                "         BMAD may not be installed. RBTV expects BMAD {target_version}.\n"
                "         Proceeding — run installer again after BMAD is installed."
            )
        }

    manifest_text = manifest_file.read_text(encoding="utf-8")
    installed_version = _read_yaml_nested_field(manifest_text, "installation", "version")
    if not installed_version:
        # Fallback: try top-level version field
        installed_version = _read_yaml_field(manifest_text, "version")

    if not installed_version:
        return {
            "status": "unknown",
            "message": "WARNING: Could not parse BMAD version from manifest.yaml — skipping check"
        }

    # Compare versions
    installed_v = _parse_version(installed_version)
    target_v = _parse_version(target_version)
    min_v = _parse_version(min_version) if min_version else (0, 0, 0, 0, 0)

    if installed_v == target_v:
        return {
            "status": "ok",
            "message": f"BMAD version {installed_version} matches target — compatible"
        }
    elif installed_v >= min_v:
        return {
            "status": "warn",
            "message": (
                f"WARNING: BMAD {installed_version} differs from RBTV target ({target_version}).\n"
                f"         RBTV was tested against {target_version}. Proceeding — some features may behave differently.\n"
                f"         Run tasks/check-bmad-compat.xml to evaluate compatibility before using RBTV."
            )
        }
    else:
        return {
            "status": "strong_warn",
            "message": (
                f"WARNING: BMAD {installed_version} is below RBTV minimum ({min_version}).\n"
                f"         RBTV requires at least {min_version}. Compatibility is not guaranteed.\n"
                f"         Run tasks/check-bmad-compat.xml to evaluate compatibility before proceeding."
            )
        }


def print_version_check_result(result: dict) -> None:
    """Print the version check result. Warnings are clearly flagged."""
    if result["status"] == "ok":
        print(f"  {result['message']}")
    else:
        for line in result["message"].splitlines():
            print(f"  {line}")


# ─────────────────────────────────────────────────────────────────────────────
# Shared: BMAD output-path normalization
# ─────────────────────────────────────────────────────────────────────────────

def _extract_output_folder_name(root: Path) -> str:
    """
    Read the output folder name from BMAD's core/config.yaml.
    Extracts the folder name from output_folder value (e.g., 'projects' from
    '{project-root}/projects' or '{project-root}/projects/{project-name}').
    Falls back to 'projects' if the config cannot be read.
    """
    core_config = root / "_bmad" / "core" / "config.yaml"
    if not core_config.exists():
        return "projects"
    try:
        content = core_config.read_text(encoding="utf-8")
        match = re.search(r'output_folder:\s*"([^"]*)"', content)
        if not match:
            return "projects"
        path_value = match.group(1)
        # Strip {project-root}/ prefix and any trailing /{project-name}
        folder = path_value.replace("{project-root}/", "").replace("/{project-name}", "")
        return folder if folder else "projects"
    except Exception:
        return "projects"


def normalize_bmad_output_paths(root: Path) -> dict:
    """
    Normalize BMAD module config output paths to {folder}/{project-name}/ pattern.
    Reads the existing output folder name from core/config.yaml and preserves it.
    Updates core/config.yaml and bmm/config.yaml.
    Returns stats dict.
    """
    stats = {"updated": 0, "errors": []}

    # Read the user-chosen output folder name before modifying anything
    folder_name = _extract_output_folder_name(root)

    # core/config.yaml — output_folder
    core_config = root / "_bmad" / "core" / "config.yaml"
    if core_config.exists():
        try:
            content = core_config.read_text(encoding="utf-8")
            content = re.sub(
                r'output_folder:\s*"[^"]*"',
                f'output_folder: "{{project-root}}/{folder_name}/{{project-name}}"',
                content
            )
            core_config.write_text(content, encoding="utf-8")
            stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(f"core/config.yaml: {e}")

    # bmm/config.yaml — output_folder + artifact sub-paths
    bmm_config = root / "_bmad" / "bmm" / "config.yaml"
    if bmm_config.exists():
        try:
            content = bmm_config.read_text(encoding="utf-8")
            content = re.sub(
                r'output_folder:\s*"[^"]*"',
                f'output_folder: "{{project-root}}/{folder_name}/{{project-name}}"',
                content
            )
            content = re.sub(
                r'planning_artifacts:\s*"[^"]*"',
                f'planning_artifacts: "{{project-root}}/{folder_name}/{{project-name}}/planning-artifacts"',
                content
            )
            content = re.sub(
                r'implementation_artifacts:\s*"[^"]*"',
                f'implementation_artifacts: "{{project-root}}/{folder_name}/{{project-name}}/implementation-artifacts"',
                content
            )
            bmm_config.write_text(content, encoding="utf-8")
            stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(f"bmm/config.yaml: {e}")

    # rbtv/_config/config.yaml — update bmad_output path variable
    rbtv_config = root / "_bmad" / "rbtv" / "_config" / "config.yaml"
    if rbtv_config.exists():
        try:
            content = rbtv_config.read_text(encoding="utf-8")
            content = re.sub(
                r'(bmad_output:\s*)"[^"]*"',
                f'\\1"{{project-root}}/{folder_name}"',
                content
            )
            rbtv_config.write_text(content, encoding="utf-8")
            stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(f"rbtv/_config/config.yaml: {e}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Shared: BMAD help catalog
# ─────────────────────────────────────────────────────────────────────────────

def add_rbtv_to_help_catalog(root: Path) -> dict:
    """
    Add RBTV entry to the BMAD help catalog (_bmad/_config/bmad-help.csv).
    Idempotent — checks for existing rbtv module entry before adding.
    Returns stats dict.
    """
    stats = {"added": 0, "errors": []}

    help_csv = root / "_bmad" / "_config" / "bmad-help.csv"
    if not help_csv.exists():
        stats["errors"].append("bmad-help.csv not found")
        return stats

    try:
        with open(help_csv, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            fieldnames = reader.fieldnames

        if any(row.get("module") == "rbtv" for row in existing_rows):
            return stats  # already present

        rbtv_rows = [
            {
                "module": "rbtv",
                "phase": "anytime",
                "name": "Business Innovation",
                "code": "BI",
                "sequence": "10",
                "workflow-file": "_bmad/rbtv/workflows/bi-business-innovation/workflow.md",
                "command": "bmad-rbtv-mentor",
                "required": "false",
                "agent-name": "mentor",
                "agent-command": "bmad-rbtv-mentor",
                "agent-display-name": "Mentor",
                "agent-title": "🚀 YC Mentor",
                "options": "",
                "description": "Guide users through 6-milestone business innovation lifecycle from idea to MVP",
                "output-location": "output_folder",
                "outputs": "project-memo",
            }
        ]

        with open(help_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows + rbtv_rows)

        stats["added"] = len(rbtv_rows)

    except Exception as e:
        stats["errors"].append(f"Failed to update help catalog: {e}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Workspace mode functions
# ─────────────────────────────────────────────────────────────────────────────

def workspace_delete_rbtv_files(root: Path) -> dict:
    """Delete files starting with 'bmad-rbtv' from workspace search directories."""
    stats = {"deleted": 0, "skipped": 0, "errors": []}
    for rel_dir in WORKSPACE_RBTV_SEARCH_DIRS:
        search_dir = root / rel_dir
        if not search_dir.exists():
            stats["skipped"] += 1
            continue
        for file_path in search_dir.rglob("bmad-rbtv*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    stats["deleted"] += 1
                except Exception as e:
                    stats["errors"].append(f"{file_path.relative_to(root)}: {e}")
    return stats


def workspace_copy_folder(src: Path, dst: Path, exclude_names: set = None) -> dict:
    """Copy folder from src to dst, merging on conflict. Skips files in exclude_names."""
    stats = {"copied": 0, "replaced": 0, "skipped": 0, "errors": []}
    if not src.exists():
        return {"skipped": 1, "reason": "source does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        if exclude_names and src_file.name in exclude_names:
            stats["skipped"] += 1
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def workspace_merge_mcp_json(src_mcp: Path, dst_mcp: Path) -> dict:
    """Merge MCP server configs from src into dst. src entries overwrite on conflict."""
    stats = {"merged": 0, "added": 0, "errors": []}
    if not src_mcp.exists():
        return {"skipped": 1, "reason": "source mcp.json does not exist"}
    try:
        with open(src_mcp, "r", encoding="utf-8") as f:
            src_config = json.load(f)
        dst_config = {"mcpServers": {}}
        if dst_mcp.exists():
            with open(dst_mcp, "r", encoding="utf-8") as f:
                dst_config = json.load(f)
        dst_config.setdefault("mcpServers", {})
        for name, cfg in src_config.get("mcpServers", {}).items():
            key = "merged" if name in dst_config["mcpServers"] else "added"
            stats[key] += 1
            dst_config["mcpServers"][name] = cfg
        dst_mcp.parent.mkdir(parents=True, exist_ok=True)
        with open(dst_mcp, "w", encoding="utf-8") as f:
            json.dump(dst_config, f, indent=2)
    except Exception as e:
        stats["errors"].append(f"mcp.json merge failed: {e}")
    return stats


def workspace_replicate_commands_to_cursor(root: Path) -> dict:
    """Replicate .claude/commands/ → .cursor/commands/ for Cursor (direct copy)."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "commands"
    dst = root / ".cursor" / "commands"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/commands/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def _convert_claude_rule_to_mdc(content: str) -> str:
    """
    Convert Claude .claude/rules/ .md frontmatter to Cursor .mdc frontmatter.

    Mapping:
      - paths (YAML array) → globs (comma-separated string)
      - adds alwaysApply: true (if no paths) or alwaysApply: false (if paths)
      - description retained as-is
    """
    if not content.startswith("---"):
        return content

    end = content.find("---", 3)
    if end == -1:
        return content

    front = content[3:end].strip()
    body = content[end + 3:]

    lines_out = []
    patterns = []
    in_paths_block = False

    for line in front.splitlines():
        stripped = line.strip()

        if stripped == "paths:":
            in_paths_block = True
            continue

        if in_paths_block:
            if stripped.startswith("- "):
                val = stripped[2:].strip().strip('"').strip("'")
                patterns.append(val)
                continue
            else:
                in_paths_block = False

        lines_out.append(line)

    if patterns:
        globs_str = ", ".join(patterns)
        lines_out.append(f'globs: "{globs_str}"')
        lines_out.append("alwaysApply: false")
    else:
        lines_out.append("alwaysApply: true")

    return "---\n" + "\n".join(lines_out) + "\n---" + body


def workspace_replicate_rules_to_cursor(root: Path) -> dict:
    """Replicate .claude/rules/*.md → .cursor/rules/*.mdc with frontmatter conversion."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "rules"
    dst = root / ".cursor" / "rules"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/rules/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_name = rel_path.with_suffix(".mdc") if rel_path.suffix == ".md" else rel_path
        dst_file = dst / dst_name
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            content = src_file.read_text(encoding="utf-8")
            if src_file.suffix == ".md":
                content = _convert_claude_rule_to_mdc(content)
            dst_file.write_text(content, encoding="utf-8")
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def _convert_claude_agent_to_cursor(content: str) -> str:
    """
    Convert Claude .claude/agents/ frontmatter to Cursor agent frontmatter.

    Mapping:
      - permissionMode: plan → readonly: true
      - strips Claude-only fields: tools, hooks, memory, maxTurns, mcpServers, skills, bypassPermissions
      - All other fields passed through (name, description, model are shared)
    """
    CLAUDE_ONLY_FIELDS = {
        "permissionMode", "tools", "hooks", "memory",
        "maxTurns", "mcpServers", "skills", "bypassPermissions",
    }
    if not content.startswith("---"):
        return content

    end = content.find("---", 3)
    if end == -1:
        return content

    front = content[3:end].strip()
    body = content[end + 3:]

    lines_out = []
    has_plan_mode = False

    for line in front.splitlines():
        stripped = line.strip()
        field_name = stripped.split(":")[0].strip() if ":" in stripped else ""

        if field_name == "permissionMode":
            val = stripped.split(":", 1)[1].strip().lower()
            if val == "plan":
                has_plan_mode = True
            continue

        if field_name in CLAUDE_ONLY_FIELDS:
            continue

        lines_out.append(line)

    if has_plan_mode:
        lines_out.append("readonly: true")

    return "---\n" + "\n".join(lines_out) + "\n---" + body


def workspace_replicate_agents_to_cursor(root: Path) -> dict:
    """Replicate .claude/agents/*.md → .cursor/agents/*.md with frontmatter conversion."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "agents"
    dst = root / ".cursor" / "agents"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/agents/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            content = src_file.read_text(encoding="utf-8")
            content = _convert_claude_agent_to_cursor(content)
            dst_file.write_text(content, encoding="utf-8")
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def workspace_replicate_skills_to_cursor(root: Path) -> dict:
    """Replicate .claude/skills/ → .cursor/skills/ (identical format, direct copy)."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "skills"
    dst = root / ".cursor" / "skills"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/skills/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def workspace_merge_vscode_settings(config_dir: Path, root: Path) -> dict:
    """Copy .vscode/settings.json to workspace root only if .vscode/ does not already exist."""
    src = config_dir / ".vscode" / "settings.json"
    dst_vscode = root / ".vscode"
    dst = dst_vscode / "settings.json"
    if not src.exists():
        return {"skipped": 1, "reason": "source .vscode/settings.json does not exist"}
    if dst_vscode.exists():
        return {"skipped": 1, "reason": ".vscode/ already exists — leaving untouched"}
    try:
        with open(src, "r", encoding="utf-8") as f:
            settings = json.load(f)
        dst_vscode.mkdir(parents=True, exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return {"created": 1}
    except Exception as e:
        return {"errors": [f".vscode/settings.json creation failed: {e}"]}


def workspace_merge_cursorignore(root: Path) -> dict:
    """Append RBTV-managed .cursorignore patterns if not already present."""
    stats = {"added": 0, "skipped": 0, "errors": []}
    dst = root / ".cursorignore"
    folder_name = _extract_output_folder_name(root)
    rbtv_patterns = [f"{folder_name}/archive/"]
    try:
        existing = set()
        content = ""
        if dst.exists():
            content = dst.read_text(encoding="utf-8")
            existing = {ln.strip() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")}
        to_add = [p for p in rbtv_patterns if p not in existing]
        if to_add:
            if content and not content.endswith("\n"):
                content += "\n"
            header = "\n# RBTV-managed patterns\n" if content else "# RBTV-managed patterns\n"
            with open(dst, "a", encoding="utf-8") as f:
                f.write(header)
                for p in to_add:
                    f.write(f"{p}\n")
            stats["added"] += len(to_add)
        else:
            stats["skipped"] += len(rbtv_patterns)
    except Exception as e:
        stats["errors"].append(f".cursorignore merge failed: {e}")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Admin mode functions
# ─────────────────────────────────────────────────────────────────────────────

def admin_delete_managed_files(rbtv_dir: Path) -> dict:
    """Delete files with managed prefixes from .cursor/ subdirs and extra managed files."""
    stats = {"deleted": 0, "errors": []}
    for rel_dir in ADMIN_SEARCH_DIRS:
        search_dir = rbtv_dir / rel_dir
        if not search_dir.exists():
            continue
        for file_path in search_dir.rglob("*"):
            if file_path.is_file() and any(file_path.name.startswith(p) for p in ADMIN_MANAGED_PREFIXES):
                try:
                    file_path.unlink()
                    stats["deleted"] += 1
                except Exception as e:
                    stats["errors"].append(f"{file_path.relative_to(rbtv_dir)}: {e}")
    for rel in ADMIN_EXTRA_MANAGED_FILES:
        fp = rbtv_dir / rel
        if fp.exists():
            try:
                fp.unlink()
                stats["deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel}: {e}")
    # Clean empty skill directories with managed prefixes
    for skills_parent in (".cursor", ".claude"):
        skills_dir = rbtv_dir / skills_parent / "skills"
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir(), reverse=True):
                if d.is_dir() and any(d.name.startswith(p) for p in ADMIN_MANAGED_PREFIXES):
                    try:
                        shutil.rmtree(d)
                    except Exception:
                        pass
    return stats


def _admin_should_transform(rel_path: Path) -> bool:
    """Return True if path substitution + reinforcement should be applied."""
    if rel_path.parts[0] == "rules":
        return False
    if rel_path.name == "mcp.json":
        return False
    return True


def _admin_transform(content: str) -> str:
    """Apply path substitution and append reinforcement reminder."""
    content = content.replace(ADMIN_PATH_FIND, ADMIN_PATH_REPLACE)
    return content.rstrip() + ADMIN_REINFORCEMENT


def admin_copy_folder(src: Path, dst: Path, transform: bool = False) -> dict:
    """Copy folder from src to dst. If transform=True, applies path sub + reinforcement."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    if not src.exists():
        return {"skipped": 1, "reason": f"{src} does not exist"}
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            if transform and _admin_should_transform(rel_path):
                content = src_file.read_text(encoding="utf-8")
                dst_file.write_text(_admin_transform(content), encoding="utf-8")
            else:
                shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def admin_read_existing_values(rbtv_dir: Path) -> dict:
    """Read existing admin config values from the installed admin rule (if present)."""
    values = dict(ADMIN_CONFIG_DEFAULTS)
    rule_file = rbtv_dir / ".claude" / "rules" / ADMIN_RULE_FILE
    if not rule_file.exists():
        return values
    content = rule_file.read_text(encoding="utf-8")
    for key in values:
        match = re.search(rf'{key}\s*\|\s*"([^"]*)"', content)
        if match:
            values[key] = match.group(1)
    return values


def admin_prompt_user_values(defaults: dict) -> dict:
    """Prompt user for admin config values. Enter keeps defaults."""
    values = {}
    print("Admin Configuration")
    print("-" * 40)
    for key, default in defaults.items():
        display = key.replace("_", " ").title()
        if default:
            answer = input(f"  {display} [{default}]: ").strip()
            values[key] = answer if answer else default
        else:
            while True:
                answer = input(f"  {display}: ").strip()
                if answer:
                    values[key] = answer
                    break
                print("    (required — please enter a value)")
    return values


def admin_inject_values(rbtv_dir: Path, values: dict) -> None:
    """Replace {admin_*} placeholders in the admin rule with user values."""
    rule_file = rbtv_dir / ".claude" / "rules" / ADMIN_RULE_FILE
    if not rule_file.exists():
        return
    content = rule_file.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{admin_" + key + "}", value)
    rule_file.write_text(content, encoding="utf-8")


def admin_ensure_gitignore(rbtv_dir: Path) -> dict:
    """Ensure required entries exist in rbtv root .gitignore. Additive only.
    Migrates legacy unanchored entries (e.g. '.cursor/') to anchored forms ('/.cursor/')."""
    gitignore = rbtv_dir / ".gitignore"
    stats = {"added": 0, "already_present": 0, "migrated": 0}
    content = ""
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")

    # Migrate legacy unanchored entries to anchored forms
    lines = content.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in ADMIN_GITIGNORE_LEGACY_MAP:
            new_lines.append(line.replace(stripped, ADMIN_GITIGNORE_LEGACY_MAP[stripped], 1))
            stats["migrated"] += 1
        else:
            new_lines.append(line)
    content = "".join(new_lines)

    existing = {ln.strip() for ln in content.splitlines()}
    missing = [e for e in ADMIN_GITIGNORE_ENTRIES if e not in existing]
    stats["already_present"] = len(ADMIN_GITIGNORE_ENTRIES) - len(missing)
    stats["added"] = len(missing)
    if missing or stats["migrated"]:
        if missing:
            if content and not content.endswith("\n"):
                content += "\n"
            header = "\n# Added by install-rbtv.py (admin mode)\n" if content else "# Generated by install-rbtv.py\n"
            content += header + "\n".join(missing) + "\n"
        gitignore.write_text(content, encoding="utf-8")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Mode entry points
# ─────────────────────────────────────────────────────────────────────────────

def run_workspace_mode(paths: dict, skip_version_check: bool) -> int:
    """Full workspace setup: .cursor/.claude config + BMAD configs + help catalog."""
    root = paths["root"]
    rbtv_dir = paths["rbtv"]
    config_dir = paths["config"]

    print(f"Source:      {rbtv_dir}")
    print(f"Destination: {root}")
    print()

    # Pre-flight version check
    print("Checking BMAD version compatibility")
    if skip_version_check:
        print("  Skipped (--skip-version-check)")
    else:
        result = check_bmad_version(rbtv_dir, root)
        print_version_check_result(result)
    print()

    # Clean existing RBTV files
    print("Deleting existing RBTV files (bmad-rbtv*)")
    del_stats = workspace_delete_rbtv_files(root)
    print(f"  Deleted: {del_stats['deleted']} files")
    _print_errors(del_stats.get("errors", []))
    print()

    # Copy _config/claude/ → .claude/ (canonical source, no dot prefix in source)
    total_copied = total_replaced = 0
    src = paths["config_claude"]
    dst = root / ".claude"
    print(f"Processing _config/claude/ -> .claude/ (canonical source)")
    stats = workspace_copy_folder(src, dst, exclude_names={".mcp.json"})
    if "reason" in stats:
        print(f"  Skipped ({stats['reason']})")
    else:
        print(f"  Copied: {stats['copied']}  |  Replaced: {stats['replaced']}")
        _print_errors(stats.get("errors", []))
        total_copied += stats["copied"]
        total_replaced += stats["replaced"]
    print()

    # Merge MCP for Claude Code (canonical)
    print("Merging MCP configuration for Claude Code")
    mcp_stats_claude = workspace_merge_mcp_json(
        config_dir / ".claude" / ".mcp.json",
        root / ".claude" / ".mcp.json",
    )
    _print_mcp_stats(mcp_stats_claude)
    print()

    # Merge MCP for Cursor (derived)
    print("Merging MCP configuration for Cursor")
    mcp_stats_cursor = workspace_merge_mcp_json(
        config_dir / ".claude" / ".mcp.json",
        root / ".cursor" / "mcp.json",
    )
    _print_mcp_stats(mcp_stats_cursor)
    print()

    # Replicate commands to .cursor/
    print("Replicating commands to .cursor/")
    cmd_stats = workspace_replicate_commands_to_cursor(root)
    if "reason" in cmd_stats:
        print(f"  Skipped ({cmd_stats['reason']})")
    else:
        print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
        _print_errors(cmd_stats.get("errors", []))
    print()

    # Replicate rules to .cursor/
    print("Replicating rules to .cursor/")
    rule_stats = workspace_replicate_rules_to_cursor(root)
    if "reason" in rule_stats:
        print(f"  Skipped ({rule_stats['reason']})")
    else:
        print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
        _print_errors(rule_stats.get("errors", []))
    print()

    # Replicate agents to .cursor/
    print("Replicating agents to .cursor/")
    agent_stats = workspace_replicate_agents_to_cursor(root)
    if "reason" in agent_stats:
        print(f"  Skipped ({agent_stats['reason']})")
    else:
        print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
        _print_errors(agent_stats.get("errors", []))
    print()

    # Replicate skills to .cursor/
    print("Replicating skills to .cursor/")
    skill_stats = workspace_replicate_skills_to_cursor(root)
    if "reason" in skill_stats:
        print(f"  Skipped ({skill_stats['reason']})")
    else:
        print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
        _print_errors(skill_stats.get("errors", []))
    print()

    # Normalize BMAD output paths (CP 2)
    print("Normalizing BMAD output paths")
    norm_stats = normalize_bmad_output_paths(root)
    print(f"  Updated: {norm_stats['updated']} config files")
    _print_errors(norm_stats.get("errors", []))
    print()

    # Add to help catalog
    print("Adding RBTV to BMAD help catalog")
    help_stats = add_rbtv_to_help_catalog(root)
    if help_stats.get("added", 0) > 0:
        print(f"  Added: {help_stats['added']} RBTV workflow(s)")
    elif help_stats.get("errors"):
        _print_errors(help_stats["errors"])
    else:
        print("  Status: RBTV already in catalog")
    print()

    # VS Code settings
    print("Checking .vscode/settings.json")
    vsc_stats = workspace_merge_vscode_settings(config_dir, root)
    if "reason" in vsc_stats:
        print(f"  Skipped ({vsc_stats['reason']})")
    elif vsc_stats.get("created"):
        print("  Created .vscode/settings.json")
    _print_errors(vsc_stats.get("errors", []))
    print()

    # .cursorignore
    print("Merging .cursorignore")
    ci_stats = workspace_merge_cursorignore(root)
    if ci_stats.get("added", 0) > 0:
        print(f"  Added: {ci_stats['added']} patterns")
    else:
        print(f"  Skipped: {ci_stats.get('skipped', 0)} patterns (already present)")
    _print_errors(ci_stats.get("errors", []))
    print()

    # Summary
    print("-" * 60)
    print("Summary")
    print("-" * 60)
    print(f"Total files copied:   {total_copied}")
    print(f"Total files replaced: {total_replaced}")
    if "added" in mcp_stats_cursor:
        print(f"Cursor MCP servers:      {mcp_stats_cursor['added'] + mcp_stats_cursor['merged']}")
    if "added" in mcp_stats_claude:
        print(f"Claude Code MCP servers: {mcp_stats_claude['added'] + mcp_stats_claude['merged']}")
    if "copied" in cmd_stats:
        print(f"Commands replicated (->.cursor):  {cmd_stats['copied'] + cmd_stats['replaced']}")
    if "copied" in rule_stats:
        print(f"Rules replicated (->.cursor):     {rule_stats['copied'] + rule_stats['replaced']}")
    if "copied" in agent_stats:
        print(f"Agents replicated (->.cursor):    {agent_stats['copied'] + agent_stats['replaced']}")
    if "copied" in skill_stats:
        print(f"Skills replicated (->.cursor):    {skill_stats['copied'] + skill_stats['replaced']}")
    print()
    print("Installation complete.")
    print()
    print("Next steps:")
    print("  1. Restart Cursor to load new MCP servers and commands")
    print("  2. Restart Claude Code to load new MCP servers, rules, and agents")
    print("  3. Run /bmad-help to see RBTV workflows in the catalog")
    print("  4. Run /bmad-rbtv-help to see RBTV-specific commands")
    print()
    print("Remember: Run this script after every 'git pull' or 'git fetch'")
    print()

    print("Admin mode sets up this repo for standalone RBTV development")
    print("(outside a BMAD project). It installs .claude/ and .cursor/ rules,")
    print("commands, agents, and CLAUDE.md at the rbtv root so AI agents can")
    print("work on RBTV files with full path resolution and BMAD context.")
    print()
    answer = input("Run admin update as well? [y/N]: ").strip().lower()
    if answer in ("y", "yes"):
        print()
        print("=" * 60)
        print("RBTV Installation Script — ADMIN mode")
        print("=" * 60)
        print()
        return run_admin_mode(paths)

    return 0


def run_admin_mode(paths: dict) -> int:
    """Standalone dev setup: .cursor/.claude/ at rbtv root with path substitution + admin rules."""
    rbtv_dir = paths["rbtv"]
    config_claude = paths["config_claude"]
    admin_claude = paths["admin_claude"]

    print(f"RBTV root: {rbtv_dir}")
    print()

    # Read existing values for defaults
    existing = admin_read_existing_values(rbtv_dir)
    values = admin_prompt_user_values(existing)
    print()

    # Clean managed files
    print("Cleaning existing managed files...")
    del_stats = admin_delete_managed_files(rbtv_dir)
    print(f"  Deleted: {del_stats['deleted']} files")
    _print_errors(del_stats.get("errors", []))
    print()

    # Copy _config/claude/ with path substitution + reinforcement (canonical source)
    print("Copying _config/claude/ (path substitution + reinforcement)...")
    cfg_stats = admin_copy_folder(config_claude, rbtv_dir / ".claude", transform=True)
    if "reason" in cfg_stats:
        print(f"  Skipped ({cfg_stats['reason']})")
    else:
        print(f"  Copied: {cfg_stats['copied']}  |  Replaced: {cfg_stats['replaced']}")
        _print_errors(cfg_stats.get("errors", []))
    print()

    # Copy _admin/.claude/ as-is (admin rules)
    print("Copying _admin/.claude/ (admin rules)...")
    adm_stats = admin_copy_folder(admin_claude, rbtv_dir / ".claude", transform=False)
    if "reason" in adm_stats:
        print(f"  Skipped ({adm_stats['reason']})")
    else:
        print(f"  Copied: {adm_stats['copied']}  |  Replaced: {adm_stats['replaced']}")
        _print_errors(adm_stats.get("errors", []))
    print()

    # Replicate commands to .cursor/
    print("Replicating commands to .cursor/")
    cmd_stats = workspace_replicate_commands_to_cursor(rbtv_dir)
    if "reason" in cmd_stats:
        print(f"  Skipped ({cmd_stats['reason']})")
    else:
        print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
        _print_errors(cmd_stats.get("errors", []))
    print()

    # Replicate rules to .cursor/
    print("Replicating rules to .cursor/")
    rule_stats = workspace_replicate_rules_to_cursor(rbtv_dir)
    if "reason" in rule_stats:
        print(f"  Skipped ({rule_stats['reason']})")
    else:
        print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
        _print_errors(rule_stats.get("errors", []))
    print()

    # Replicate agents to .cursor/
    print("Replicating agents to .cursor/")
    agent_stats = workspace_replicate_agents_to_cursor(rbtv_dir)
    if "reason" in agent_stats:
        print(f"  Skipped ({agent_stats['reason']})")
    else:
        print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
        _print_errors(agent_stats.get("errors", []))
    print()

    # Replicate skills to .cursor/
    print("Replicating skills to .cursor/")
    skill_stats = workspace_replicate_skills_to_cursor(rbtv_dir)
    if "reason" in skill_stats:
        print(f"  Skipped ({skill_stats['reason']})")
    else:
        print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
        _print_errors(skill_stats.get("errors", []))
    print()

    # Merge MCP for Claude Code (canonical)
    print("Merging MCP configuration for Claude Code")
    mcp_stats_claude = workspace_merge_mcp_json(
        config_claude / ".mcp.json",
        rbtv_dir / ".claude" / ".mcp.json",
    )
    _print_mcp_stats(mcp_stats_claude)
    print()

    # Merge MCP for Cursor (derived)
    print("Merging MCP configuration for Cursor")
    mcp_stats_cursor = workspace_merge_mcp_json(
        config_claude / ".mcp.json",
        rbtv_dir / ".cursor" / "mcp.json",
    )
    _print_mcp_stats(mcp_stats_cursor)
    print()

    # Inject admin values into rule
    print("Injecting admin values into rule...")
    admin_inject_values(rbtv_dir, values)
    print("  Done")
    print()

    # Copy CLAUDE.md from _admin/ to rbtv root
    print("Copying CLAUDE.md to rbtv root...")
    claude_src = rbtv_dir / "_admin" / "CLAUDE.md"
    claude_dst = rbtv_dir / "CLAUDE.md"
    if claude_src.exists():
        shutil.copy2(str(claude_src), str(claude_dst))
        print("  Done")
    else:
        print("  WARNING: _admin/CLAUDE.md not found — skipping")
    print()

    # Ensure .gitignore entries
    print("Ensuring .gitignore entries...")
    gi_stats = admin_ensure_gitignore(rbtv_dir)
    print(f"  Added: {gi_stats['added']}  |  Already present: {gi_stats['already_present']}  |  Migrated: {gi_stats['migrated']}")
    print()

    # Summary
    total_copied = (
        cfg_stats.get("copied", 0)
        + adm_stats.get("copied", 0)
        + cmd_stats.get("copied", 0)
    )
    total_replaced = (
        cfg_stats.get("replaced", 0)
        + adm_stats.get("replaced", 0)
        + cmd_stats.get("replaced", 0)
    )
    print("-" * 60)
    print("Summary")
    print("-" * 60)
    print(f"  Files copied:   {total_copied}")
    print(f"  Files replaced: {total_replaced}")
    if "copied" in cmd_stats:
        print(f"  Commands replicated: {cmd_stats['copied'] + cmd_stats['replaced']}")
    if "copied" in rule_stats:
        print(f"  Rules replicated:    {rule_stats['copied'] + rule_stats['replaced']}")
    if "copied" in agent_stats:
        print(f"  Agents replicated:   {agent_stats['copied'] + agent_stats['replaced']}")
    if "copied" in skill_stats:
        print(f"  Skills replicated:   {skill_stats['copied'] + skill_stats['replaced']}")
    if "added" in mcp_stats_claude:
        print(f"  Claude Code MCP servers: {mcp_stats_claude['added'] + mcp_stats_claude['merged']}")
    if "added" in mcp_stats_cursor:
        print(f"  Cursor MCP servers:      {mcp_stats_cursor['added'] + mcp_stats_cursor['merged']}")
    print(f"  Admin user:     {values.get('user_name', 'N/A')}")
    print(f"  Language:       {values.get('communication_language', 'N/A')}")
    print()
    print("Next steps:")
    print("  1. Restart Cursor to load new commands and rules")
    print("  2. Restart Claude Code to load new MCP servers, rules, and agents")
    print("  3. Run /bmad-rbtv-help to verify tools work")
    print()
    print("Remember: re-run this script after every 'git pull'")
    return 0


def run_sync_mode(paths: dict, skip_version_check: bool) -> int:
    """
    BMAD config patching only — no workspace artifacts.
    Patches BMAD output paths and adds RBTV to help catalog.
    Designed for nanobot workspace: RBTV is at _bmad/rbtv/, workspace root is root.
    """
    root = paths["root"]
    rbtv_dir = paths["rbtv"]

    print(f"RBTV source: {rbtv_dir}")
    print(f"BMAD root:   {root}")
    print()

    # Pre-flight version check
    print("Checking BMAD version compatibility")
    if skip_version_check:
        print("  Skipped (--skip-version-check)")
    else:
        result = check_bmad_version(rbtv_dir, root)
        print_version_check_result(result)
    print()

    # Normalize BMAD output paths (CP 2)
    print("Normalizing BMAD output paths")
    norm_stats = normalize_bmad_output_paths(root)
    print(f"  Updated: {norm_stats['updated']} config files")
    _print_errors(norm_stats.get("errors", []))
    print()

    # Add to help catalog
    print("Adding RBTV to BMAD help catalog")
    help_stats = add_rbtv_to_help_catalog(root)
    if help_stats.get("added", 0) > 0:
        print(f"  Added: {help_stats['added']} RBTV workflow(s)")
    elif help_stats.get("errors"):
        _print_errors(help_stats["errors"])
    else:
        print("  Status: RBTV already in catalog")
    print()

    print("-" * 60)
    print("Sync complete.")
    print()
    print("Next steps:")
    print("  1. Restart nanobot to pick up updated BMAD config")
    print("  2. Run tasks/check-bmad-compat.xml to verify compatibility")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _print_errors(errors: list) -> None:
    for err in errors:
        print(f"    Error: {err}")


def _print_mcp_stats(stats: dict) -> None:
    if "reason" in stats:
        print(f"  Skipped ({stats['reason']})")
    else:
        print(f"  Added: {stats['added']}  |  Merged: {stats['merged']}")
        _print_errors(stats.get("errors", []))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RBTV Unified Installation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  workspace  Full workspace setup: .cursor/.claude config + BMAD configs + help catalog (default)\n"
            "  admin      Standalone dev setup at rbtv root with path substitution + admin rules\n"
            "  sync       BMAD config patching only — for nanobot workspace integration\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["workspace", "admin", "sync"],
        default="workspace",
        help="Installation mode (default: workspace)",
    )
    parser.add_argument(
        "--skip-version-check",
        action="store_true",
        help="Skip BMAD version compatibility check (ide and sync modes)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"RBTV Installation Script — {args.mode.upper()} mode")
    print("=" * 60)
    print()

    paths = get_paths()

    if args.mode == "workspace":
        return run_workspace_mode(paths, args.skip_version_check)
    elif args.mode == "admin":
        return run_admin_mode(paths)
    elif args.mode == "sync":
        return run_sync_mode(paths, args.skip_version_check)

    return 0


if __name__ == "__main__":
    sys.exit(main())

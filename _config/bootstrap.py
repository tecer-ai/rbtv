#!/usr/bin/env python3
"""
BMAD Bootstrap Script

Centralizes all installation flows into a single entry point:
  1. RBTV module installation (workspace / admin / sync modes)
  2. Project-level bootstrapping — discovers projects in the BMAD output folder,
     reads each project's bootstrap.yaml, and installs declared skills, rules,
     and commands into the workspace .claude/ and .cursor/ directories.

Modes:
  workspace -- Full setup: RBTV install + project bootstrap (default)
               Offers admin install/uninstall at the end.
  admin     -- Standalone RBTV dev setup at rbtv root (no project bootstrap)
  sync      -- BMAD config patching only (no project bootstrap)

Usage:
    python _config/bootstrap.py                          # workspace mode (default)
    python _config/bootstrap.py --mode workspace
    python _config/bootstrap.py --mode admin
    python _config/bootstrap.py --mode sync
    python _config/bootstrap.py --skip-version-check
    python _config/bootstrap.py --skip-projects
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
    root = rbtv_dir.parent.parent                  # BMAD project root
    return {
        "config": script_dir,
        "rbtv": rbtv_dir,
        "root": root,
        "config_claude": script_dir / "claude",
        "admin_claude": rbtv_dir / "_admin" / "claude",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Constants — RBTV installation
# ─────────────────────────────────────────────────────────────────────────────

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

ADMIN_PATH_FIND = "{project-root}/_bmad/rbtv/"
ADMIN_PATH_REPLACE = ""

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
    "/workflows/build-rbtv-component/data/CLAUDE.md",
    ".gitignore",
    ".claude/memory/",
]

ADMIN_GITIGNORE_LEGACY_MAP = {
    ".cursor/": "/.cursor/",
    ".claude/": "/.claude/",
}

ADMIN_CONFIG_DEFAULTS = {
    "user_name": "",
    "communication_language": "English",
    "document_output_language": "English",
}

BOOTSTRAP_CONFIG_FILENAME = "bootstrap.yaml"

PROTECTED_SUBDIRS = {"memory"}


# ─────────────────────────────────────────────────────────────────────────────
# YAML parser (minimal, no external dependencies)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_simple_yaml(text: str) -> dict:
    """
    Parse a flat/one-level-nested YAML file into a dict.
    Handles: scalars, one-level nested dicts, and sequences (- item).
    Enough for bootstrap.yaml and config.yaml — not a general YAML parser.
    """
    result = {}
    current_key = None
    current_dict = None
    current_list = None

    for raw_line in text.splitlines():
        # Skip comments and blank lines
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        if indent == 0 and ":" in stripped:
            # Top-level key
            if current_key and current_dict is not None:
                result[current_key] = current_dict
            if current_key and current_list is not None:
                result[current_key] = current_list

            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val:
                result[key] = val
                current_key = None
                current_dict = None
                current_list = None
            else:
                current_key = key
                current_dict = {}
                current_list = None

        elif indent > 0 and current_key is not None:
            if stripped.startswith("- "):
                # List item
                if current_list is None:
                    current_list = []
                    current_dict = None
                item = stripped[2:].strip().strip('"').strip("'")
                current_list.append(item)
            elif ":" in stripped:
                # Nested key-value
                if current_dict is None:
                    current_dict = {}
                    current_list = None
                k, _, v = stripped.partition(":")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                current_dict[k] = v

    # Flush last pending key
    if current_key and current_dict is not None:
        result[current_key] = current_dict
    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Shared: BMAD version pre-flight check
# ─────────────────────────────────────────────────────────────────────────────

def _read_yaml_field(text: str, field: str) -> str:
    """Extract a simple YAML string field value using regex."""
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
    Pre-release: Beta < RC < (no pre-release).
    """
    v = version_str.strip().lstrip("v")
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?$', v)
    if not m:
        return (0, 0, 0, "z", 0)

    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_label = m.group(4).lower() if m.group(4) else ""
    pre_num = int(m.group(5)) if m.group(5) else 0

    label_order = {"beta": 0, "rc": 1, "": 2}
    label_key = label_order.get(pre_label, 0)

    return (major, minor, patch, label_key, pre_num)


def check_bmad_version(rbtv_dir: Path, root: Path) -> dict:
    """Pre-flight BMAD version check."""
    compat_file = rbtv_dir / "bmad-compat.yaml"
    if not compat_file.exists():
        return {"status": "unknown", "message": "bmad-compat.yaml not found — skipping version check"}

    compat_text = compat_file.read_text(encoding="utf-8")
    target_version = _read_yaml_field(compat_text, "bmad_target_version")
    min_version = _read_yaml_field(compat_text, "bmad_min_version")

    if not target_version:
        return {"status": "unknown", "message": "bmad_target_version not found in bmad-compat.yaml"}

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
        installed_version = _read_yaml_field(manifest_text, "version")

    if not installed_version:
        return {
            "status": "unknown",
            "message": "WARNING: Could not parse BMAD version from manifest.yaml — skipping check"
        }

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
        folder = path_value.replace("{project-root}/", "").replace("/{project-name}", "")
        return folder if folder else "projects"
    except Exception:
        return "projects"


def normalize_bmad_output_paths(root: Path) -> dict:
    """Normalize BMAD module config output paths to {folder}/{project-name}/ pattern."""
    stats = {"updated": 0, "errors": []}

    folder_name = _extract_output_folder_name(root)

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
    """Add RBTV entry to the BMAD help catalog. Idempotent."""
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
            return stats

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
# Shared: file copy / replication utilities
# ─────────────────────────────────────────────────────────────────────────────

def _is_protected_path(rel_path: Path) -> bool:
    """Check if a relative path falls under a protected subdirectory."""
    return any(part in PROTECTED_SUBDIRS for part in rel_path.parts)


def copy_folder(src: Path, dst: Path, exclude_names: set = None) -> dict:
    """Copy folder from src to dst, merging on conflict. Skips files in exclude_names
    and preserves protected subdirectories (e.g. memory/) at the destination."""
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
        if _is_protected_path(rel_path) and dst_file.exists():
            stats["skipped"] += 1
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def merge_mcp_json(src_mcp: Path, dst_mcp: Path) -> dict:
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


def _matches_prefix(name: str, prefixes: tuple) -> bool:
    """Check if a file or directory name starts with any of the given prefixes."""
    return any(name.startswith(p) for p in prefixes)


def replicate_commands_to_cursor(root: Path, prefixes: tuple) -> dict:
    """Replicate matching .claude/commands/ → .cursor/commands/."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "commands"
    dst = root / ".cursor" / "commands"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/commands/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        if not _matches_prefix(src_file.name, prefixes):
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
    """Convert Claude .md rule frontmatter to Cursor .mdc frontmatter."""
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


def replicate_rules_to_cursor(root: Path, prefixes: tuple) -> dict:
    """Replicate matching .claude/rules/*.md → .cursor/rules/*.mdc with frontmatter conversion."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "rules"
    dst = root / ".cursor" / "rules"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/rules/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        if not _matches_prefix(src_file.name, prefixes):
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
    """Convert Claude agent frontmatter to Cursor agent frontmatter."""
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


def replicate_agents_to_cursor(root: Path, prefixes: tuple) -> dict:
    """Replicate matching .claude/agents/*.md → .cursor/agents/*.md with frontmatter conversion."""
    stats = {"copied": 0, "replaced": 0, "errors": []}
    src = root / ".claude" / "agents"
    dst = root / ".cursor" / "agents"
    if not src.exists():
        return {"skipped": 1, "reason": ".claude/agents/ does not exist"}
    dst.mkdir(parents=True, exist_ok=True)
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        if not _matches_prefix(src_file.name, prefixes):
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


def replicate_skills_to_cursor(root: Path, prefixes: tuple) -> dict:
    """Replicate matching .claude/skills/ → .cursor/skills/ (direct copy).
    Matches on the top-level skill folder name (skills are directories)."""
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
        top_level_name = rel_path.parts[0]
        if not _matches_prefix(top_level_name, prefixes):
            continue
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            existed = dst_file.exists()
            shutil.copy2(str(src_file), str(dst_file))
            stats["replaced" if existed else "copied"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")
    return stats


def merge_vscode_settings(config_dir: Path, root: Path) -> dict:
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


def merge_cursorignore(root: Path) -> dict:
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
    """Delete files with managed prefixes from .cursor/ subdirs and extra managed files.
    Never touches protected subdirectories (e.g. memory/)."""
    stats = {"deleted": 0, "errors": []}
    for rel_dir in ADMIN_SEARCH_DIRS:
        search_dir = rbtv_dir / rel_dir
        if not search_dir.exists():
            continue
        for file_path in search_dir.rglob("*"):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(search_dir)
            if _is_protected_path(rel_path):
                continue
            if any(file_path.name.startswith(p) for p in ADMIN_MANAGED_PREFIXES):
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
    for skills_parent in (".cursor", ".claude"):
        skills_dir = rbtv_dir / skills_parent / "skills"
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir(), reverse=True):
                if d.name in PROTECTED_SUBDIRS:
                    continue
                if d.is_dir() and any(d.name.startswith(p) for p in ADMIN_MANAGED_PREFIXES):
                    try:
                        shutil.rmtree(d)
                    except Exception:
                        pass
    return stats


def _admin_should_transform(rel_path: Path) -> bool:
    if rel_path.parts[0] == "rules":
        return False
    if rel_path.name == "mcp.json":
        return False
    return True


def _admin_transform(content: str) -> str:
    content = content.replace(ADMIN_PATH_FIND, ADMIN_PATH_REPLACE)
    return content.rstrip() + ADMIN_REINFORCEMENT


def admin_copy_folder(src: Path, dst: Path, transform: bool = False) -> dict:
    """Copy folder from src to dst. If transform=True, applies path sub + reinforcement.
    Preserves protected subdirectories (e.g. memory/) at the destination."""
    stats = {"copied": 0, "replaced": 0, "skipped": 0, "errors": []}
    if not src.exists():
        return {"skipped": 1, "reason": f"{src} does not exist"}
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dst_file = dst / rel_path
        if _is_protected_path(rel_path) and dst_file.exists():
            stats["skipped"] += 1
            continue
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
    rule_file = rbtv_dir / ".claude" / "rules" / ADMIN_RULE_FILE
    if not rule_file.exists():
        return
    content = rule_file.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{admin_" + key + "}", value)
    rule_file.write_text(content, encoding="utf-8")


def admin_ensure_gitignore(rbtv_dir: Path) -> dict:
    gitignore = rbtv_dir / ".gitignore"
    stats = {"added": 0, "already_present": 0, "migrated": 0}
    content = ""
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")

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
            header = "\n# Added by bootstrap.py (admin mode)\n" if content else "# Generated by bootstrap.py\n"
            content += header + "\n".join(missing) + "\n"
        gitignore.write_text(content, encoding="utf-8")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Workspace: delete RBTV files
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


# ─────────────────────────────────────────────────────────────────────────────
# Project bootstrap — discover and install project-level components
# ─────────────────────────────────────────────────────────────────────────────

def _discover_projects(output_dir: Path) -> list:
    """
    Scan the BMAD output folder for projects containing a bootstrap.yaml.
    Returns a list of (project_name, project_dir, config_dict) tuples,
    sorted alphabetically by project name.
    """
    projects = []
    if not output_dir.exists():
        return projects

    for entry in sorted(output_dir.iterdir()):
        if not entry.is_dir():
            continue
        bootstrap_file = entry / BOOTSTRAP_CONFIG_FILENAME
        if not bootstrap_file.exists():
            continue
        try:
            text = bootstrap_file.read_text(encoding="utf-8")
            config = _parse_simple_yaml(text)
            projects.append((entry.name, entry, config))
        except Exception as e:
            print(f"  WARNING: Failed to parse {bootstrap_file}: {e}")
            print(f"           Skipping project '{entry.name}'")

    return projects


def _validate_bootstrap_config(project_name: str, config: dict) -> list:
    """
    Validate a project bootstrap config. Returns a list of error strings.
    Empty list = valid.
    """
    errors = []

    if "managed_prefix" not in config:
        errors.append(f"'{project_name}': missing required field 'managed_prefix'")

    prefix = config.get("managed_prefix", "")
    if prefix and not prefix.endswith("-"):
        errors.append(
            f"'{project_name}': managed_prefix '{prefix}' must end with '-' "
            f"(e.g. '{prefix}-')"
        )

    install = config.get("install")
    if install is not None and not isinstance(install, dict):
        errors.append(f"'{project_name}': 'install' must be a mapping of component types")

    return errors


def _check_prefix_conflicts(projects: list) -> list:
    """
    Check for duplicate managed_prefix values across projects.
    Returns list of error strings. Empty = no conflicts.
    """
    seen = {}
    errors = []
    for name, _, config in projects:
        prefix = config.get("managed_prefix", "")
        if not prefix:
            continue
        if prefix in seen:
            errors.append(
                f"Prefix conflict: '{prefix}' is used by both "
                f"'{seen[prefix]}' and '{name}'"
            )
        else:
            seen[prefix] = name
    return errors


def _delete_project_managed_files(root: Path, prefix: str) -> dict:
    """Delete files/folders matching the managed prefix from workspace IDE dirs."""
    stats = {"deleted": 0, "errors": []}
    search_dirs = [
        ".claude/skills",
        ".claude/rules",
        ".claude/commands",
        ".claude/agents",
        ".cursor/skills",
        ".cursor/rules",
        ".cursor/commands",
        ".cursor/agents",
    ]
    for rel_dir in search_dirs:
        target_dir = root / rel_dir
        if not target_dir.exists():
            continue
        for entry in target_dir.iterdir():
            if entry.name.startswith(prefix):
                try:
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()
                    stats["deleted"] += 1
                except Exception as e:
                    stats["errors"].append(f"{entry.relative_to(root)}: {e}")
    return stats


def _install_project_skills(project_dir: Path, source_rel: str, root: Path) -> dict:
    """Install skill folders from project source into .claude/skills/."""
    stats = {"installed": 0, "errors": []}
    src_dir = project_dir / source_rel
    if not src_dir.exists():
        stats["errors"].append(f"Skills source not found: {src_dir}")
        return stats

    for skill_dir in sorted(src_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        dst = root / ".claude" / "skills" / skill_dir.name
        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(str(skill_dir), str(dst))
            stats["installed"] += 1
        except Exception as e:
            stats["errors"].append(f"{skill_dir.name} → .claude/skills/: {e}")

    return stats


def _install_project_rules(project_dir: Path, source_rel: str, root: Path) -> dict:
    """Install rules from project source into .claude/rules/."""
    stats = {"installed": 0, "errors": []}
    src_dir = project_dir / source_rel
    if not src_dir.exists():
        stats["errors"].append(f"Rules source not found: {src_dir}")
        return stats

    for src_file in sorted(src_dir.iterdir()):
        if not src_file.is_file():
            continue
        claude_dst = root / ".claude" / "rules" / src_file.name
        claude_dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src_file), str(claude_dst))
            stats["installed"] += 1
        except Exception as e:
            stats["errors"].append(f"{src_file.name} → .claude/rules/: {e}")

    return stats


def _install_project_commands(project_dir: Path, source_rel: str, root: Path) -> dict:
    """Install commands from project source into .claude/commands/."""
    stats = {"installed": 0, "errors": []}
    src_dir = project_dir / source_rel
    if not src_dir.exists():
        stats["errors"].append(f"Commands source not found: {src_dir}")
        return stats

    for src_file in sorted(src_dir.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(src_dir)
        dst = root / ".claude" / "commands" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src_file), str(dst))
            stats["installed"] += 1
        except Exception as e:
            stats["errors"].append(f"{rel} → .claude/commands/: {e}")

    return stats


def _install_project_agents(project_dir: Path, source_rel: str, root: Path) -> dict:
    """Install agent files from project source into .claude/agents/."""
    stats = {"installed": 0, "errors": []}
    src_dir = project_dir / source_rel
    if not src_dir.exists():
        stats["errors"].append(f"Agents source not found: {src_dir}")
        return stats

    for src_file in sorted(src_dir.iterdir()):
        if not src_file.is_file():
            continue
        claude_dst = root / ".claude" / "agents" / src_file.name
        claude_dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src_file), str(claude_dst))
            stats["installed"] += 1
        except Exception as e:
            stats["errors"].append(f"{src_file.name} → .claude/agents/: {e}")

    return stats


INSTALL_HANDLERS = {
    "skills": _install_project_skills,
    "rules": _install_project_rules,
    "commands": _install_project_commands,
    "agents": _install_project_agents,
}


def bootstrap_project(project_name: str, project_dir: Path, config: dict, root: Path) -> dict:
    """
    Bootstrap a single project: clean managed files, then install declared components.
    Returns stats dict.
    """
    prefix = config.get("managed_prefix", "")
    stats = {"cleaned": 0, "installed": 0, "errors": [], "components": {}}

    # Clean existing files for this project's prefix
    if prefix:
        del_stats = _delete_project_managed_files(root, prefix)
        stats["cleaned"] = del_stats["deleted"]
        stats["errors"].extend(del_stats.get("errors", []))

    # Install declared components
    install = config.get("install", {})
    if not isinstance(install, dict):
        return stats

    for component_type, source_config in install.items():
        handler = INSTALL_HANDLERS.get(component_type)
        if not handler:
            stats["errors"].append(f"Unknown install type: '{component_type}'")
            continue

        source_rel = source_config if isinstance(source_config, str) else source_config.get("source", "")
        if not source_rel:
            stats["errors"].append(f"No source path for '{component_type}'")
            continue

        comp_stats = handler(project_dir, source_rel, root)
        installed = comp_stats.get("installed", 0)
        stats["installed"] += installed
        stats["components"][component_type] = installed
        stats["errors"].extend(comp_stats.get("errors", []))

    return stats


def run_project_bootstrap(root: Path) -> tuple:
    """Discover projects in BMAD output folder and bootstrap each one.
    Returns (list_of_managed_prefixes, exit_code)."""
    folder_name = _extract_output_folder_name(root)
    output_dir = root / folder_name
    collected_prefixes = []

    print(f"Scanning output folder: {output_dir}")
    print()

    projects = _discover_projects(output_dir)
    if not projects:
        print("  No projects with bootstrap.yaml found — skipping project bootstrap")
        return collected_prefixes, 0

    print(f"  Found {len(projects)} project(s) with bootstrap.yaml:")
    for name, _, _ in projects:
        print(f"    - {name}")
    print()

    # Validate all configs before installing anything
    all_errors = []
    for name, _, config in projects:
        all_errors.extend(_validate_bootstrap_config(name, config))

    prefix_errors = _check_prefix_conflicts(projects)
    all_errors.extend(prefix_errors)

    if all_errors:
        print("  VALIDATION ERRORS — aborting project bootstrap:")
        for err in all_errors:
            print(f"    ERROR: {err}")
        return collected_prefixes, 1

    # Install each project (to .claude/ only — replication happens later)
    total_installed = 0
    total_cleaned = 0
    for name, project_dir, config in projects:
        prefix = config.get("managed_prefix", "")
        if prefix:
            collected_prefixes.append(prefix)

        print(f"  Bootstrapping '{name}' (prefix: {prefix or 'N/A'})...")
        proj_stats = bootstrap_project(name, project_dir, config, root)
        total_cleaned += proj_stats["cleaned"]
        total_installed += proj_stats["installed"]

        if proj_stats["components"]:
            parts = [f"{k}: {v}" for k, v in proj_stats["components"].items() if v > 0]
            if parts:
                print(f"    Installed to .claude/: {', '.join(parts)}")
        if proj_stats["cleaned"]:
            print(f"    Cleaned: {proj_stats['cleaned']} old files")
        _print_errors(proj_stats.get("errors", []))

    print()
    print(f"  Project bootstrap complete: {total_installed} files installed to .claude/, {total_cleaned} old files cleaned")
    return collected_prefixes, 0


# ─────────────────────────────────────────────────────────────────────────────
# Admin detection and uninstall
# ─────────────────────────────────────────────────────────────────────────────

def _admin_is_installed(rbtv_dir: Path) -> bool:
    """Detect whether admin artifacts exist in the RBTV folder."""
    # Check for admin-specific files: CLAUDE.md, .claude/, .cursor/
    if (rbtv_dir / "CLAUDE.md").exists():
        return True
    if (rbtv_dir / ".claude").exists():
        return True
    if (rbtv_dir / ".cursor").exists():
        return True
    return False


def run_admin_uninstall(paths: dict) -> int:
    """Remove all admin-installed artifacts from the RBTV folder."""
    rbtv_dir = paths["rbtv"]

    # 1. Delete managed files (same cleanup as admin install's pre-clean step)
    print("Deleting managed files (bmad-rbtv*, admin-rbtv*)...")
    del_stats = admin_delete_managed_files(rbtv_dir)
    print(f"  Deleted: {del_stats['deleted']} files")
    _print_errors(del_stats.get("errors", []))
    print()

    # 2. Remove CLAUDE.md
    claude_md = rbtv_dir / "CLAUDE.md"
    if claude_md.exists():
        print("Removing CLAUDE.md...")
        claude_md.unlink()
        print("  Done")
    else:
        print("CLAUDE.md: not present (already clean)")
    print()

    # 3. Remove .claude/ and .cursor/ directories if they exist
    removed_dirs = 0
    for dirname in (".claude", ".cursor"):
        dirpath = rbtv_dir / dirname
        if dirpath.exists():
            print(f"Removing {dirname}/...")
            shutil.rmtree(dirpath)
            removed_dirs += 1
            print("  Done")
    if removed_dirs == 0:
        print(".claude/ and .cursor/: not present (already clean)")
    print()

    print("-" * 60)
    print("Admin uninstall complete.")
    print("-" * 60)
    print(f"  Files deleted:       {del_stats['deleted']}")
    print(f"  CLAUDE.md removed:   {'yes' if claude_md.exists() is False else 'no'}")
    print(f"  Directories removed: {removed_dirs}")
    print()
    print("RBTV admin artifacts have been cleaned from the rbtv folder.")
    print("Skills invoked from the BMAD workspace will no longer load")
    print("admin context (CLAUDE.md, rules, etc.).")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Mode entry points
# ─────────────────────────────────────────────────────────────────────────────

def run_workspace_mode(paths: dict, skip_version_check: bool, skip_projects: bool) -> int:
    """Full workspace setup: RBTV install to .claude/, project bootstrap to .claude/,
    then replicate managed files to .cursor/."""
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

    # ── Phase 1: Install RBTV to .claude/ ────────────────────────────────

    # Clean existing RBTV files
    print("Deleting existing RBTV files (bmad-rbtv*)")
    del_stats = workspace_delete_rbtv_files(root)
    print(f"  Deleted: {del_stats['deleted']} files")
    _print_errors(del_stats.get("errors", []))
    print()

    # Copy _config/claude/ → .claude/
    total_copied = total_replaced = 0
    src = paths["config_claude"]
    dst = root / ".claude"
    print("Installing RBTV to .claude/ (canonical source)")
    stats = copy_folder(src, dst, exclude_names={".mcp.json"})
    if "reason" in stats:
        print(f"  Skipped ({stats['reason']})")
    else:
        print(f"  Copied: {stats['copied']}  |  Replaced: {stats['replaced']}")
        _print_errors(stats.get("errors", []))
        total_copied += stats["copied"]
        total_replaced += stats["replaced"]
    print()

    # Merge MCP for Claude Code
    print("Merging MCP configuration for Claude Code")
    mcp_stats_claude = merge_mcp_json(
        config_dir / ".claude" / ".mcp.json",
        root / ".claude" / ".mcp.json",
    )
    _print_mcp_stats(mcp_stats_claude)
    print()

    # Merge MCP for Cursor
    print("Merging MCP configuration for Cursor")
    mcp_stats_cursor = merge_mcp_json(
        config_dir / ".claude" / ".mcp.json",
        root / ".cursor" / "mcp.json",
    )
    _print_mcp_stats(mcp_stats_cursor)
    print()

    # Normalize BMAD output paths
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
    vsc_stats = merge_vscode_settings(config_dir, root)
    if "reason" in vsc_stats:
        print(f"  Skipped ({vsc_stats['reason']})")
    elif vsc_stats.get("created"):
        print("  Created .vscode/settings.json")
    _print_errors(vsc_stats.get("errors", []))
    print()

    # .cursorignore
    print("Merging .cursorignore")
    ci_stats = merge_cursorignore(root)
    if ci_stats.get("added", 0) > 0:
        print(f"  Added: {ci_stats['added']} patterns")
    else:
        print(f"  Skipped: {ci_stats.get('skipped', 0)} patterns (already present)")
    _print_errors(ci_stats.get("errors", []))
    print()

    # Copy RBTV CLAUDE.md to Fernando's workflow data folder
    # Fernando (build-rbtv-component agent) needs RBTV context regardless of admin install state
    print("Installing RBTV context for Fernando (build-rbtv-component)...")
    fernando_claude_src = rbtv_dir / "_admin" / "CLAUDE.md"
    fernando_claude_dst = rbtv_dir / "workflows" / "build-rbtv-component" / "data" / "CLAUDE.md"
    if fernando_claude_src.exists():
        shutil.copy2(str(fernando_claude_src), str(fernando_claude_dst))
        print("  Copied _admin/CLAUDE.md → workflows/build-rbtv-component/data/CLAUDE.md")
    else:
        print("  WARNING: _admin/CLAUDE.md not found — skipping")
    print()

    print("-" * 60)
    print("RBTV Installation Summary")
    print("-" * 60)
    print(f"Files copied to .claude/:   {total_copied}")
    print(f"Files replaced in .claude/: {total_replaced}")
    if "added" in mcp_stats_cursor:
        print(f"Cursor MCP servers:         {mcp_stats_cursor['added'] + mcp_stats_cursor['merged']}")
    if "added" in mcp_stats_claude:
        print(f"Claude Code MCP servers:    {mcp_stats_claude['added'] + mcp_stats_claude['merged']}")
    print()

    # ── Phase 2: Project bootstrap to .claude/ ───────────────────────────

    # Collect managed prefixes — RBTV is always included
    managed_prefixes = ["bmad-rbtv"]

    if skip_projects:
        print("Project bootstrap: skipped (--skip-projects)")
        print()
    else:
        print("=" * 60)
        print("Project Bootstrap")
        print("=" * 60)
        print()
        project_prefixes, proj_exit = run_project_bootstrap(root)
        managed_prefixes.extend(project_prefixes)
        if proj_exit != 0:
            print()
            print("  Project bootstrap had errors — RBTV installation was successful")
        print()

    # ── Phase 3: Replicate managed files from .claude/ → .cursor/ ────────

    prefixes = tuple(managed_prefixes)
    print("=" * 60)
    print("Replicating to .cursor/")
    print(f"  Managed prefixes: {', '.join(prefixes)}")
    print("=" * 60)
    print()

    print("Replicating commands to .cursor/")
    cmd_stats = replicate_commands_to_cursor(root, prefixes)
    if "reason" in cmd_stats:
        print(f"  Skipped ({cmd_stats['reason']})")
    else:
        print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
        _print_errors(cmd_stats.get("errors", []))
    print()

    print("Replicating rules to .cursor/")
    rule_stats = replicate_rules_to_cursor(root, prefixes)
    if "reason" in rule_stats:
        print(f"  Skipped ({rule_stats['reason']})")
    else:
        print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
        _print_errors(rule_stats.get("errors", []))
    print()

    print("Replicating agents to .cursor/")
    agent_stats = replicate_agents_to_cursor(root, prefixes)
    if "reason" in agent_stats:
        print(f"  Skipped ({agent_stats['reason']})")
    else:
        print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
        _print_errors(agent_stats.get("errors", []))
    print()

    print("Replicating skills to .cursor/")
    skill_stats = replicate_skills_to_cursor(root, prefixes)
    if "reason" in skill_stats:
        print(f"  Skipped ({skill_stats['reason']})")
    else:
        print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
        _print_errors(skill_stats.get("errors", []))
    print()

    print("-" * 60)
    print("Replication Summary")
    print("-" * 60)
    if "copied" in cmd_stats:
        print(f"Commands replicated: {cmd_stats['copied'] + cmd_stats['replaced']}")
    if "copied" in rule_stats:
        print(f"Rules replicated:    {rule_stats['copied'] + rule_stats['replaced']}")
    if "copied" in agent_stats:
        print(f"Agents replicated:   {agent_stats['copied'] + agent_stats['replaced']}")
    if "copied" in skill_stats:
        print(f"Skills replicated:   {skill_stats['copied'] + skill_stats['replaced']}")
    print()

    # Final
    print("=" * 60)
    print("Installation complete.")
    print("=" * 60)
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
        print("Bootstrap — ADMIN mode")
        print("=" * 60)
        print()
        return run_admin_mode(paths)

    # Offer to uninstall admin if artifacts are detected
    if _admin_is_installed(paths["rbtv"]):
        print()
        print("Admin artifacts detected in RBTV folder (.claude/, .cursor/, CLAUDE.md).")
        print("These consume context window when RBTV skills are invoked from the workspace.")
        answer = input("Uninstall admin artifacts? [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            print()
            print("=" * 60)
            print("Uninstalling admin artifacts")
            print("=" * 60)
            print()
            return run_admin_uninstall(paths)

    return 0


def run_admin_mode(paths: dict) -> int:
    """Standalone dev setup: .cursor/.claude/ at rbtv root with path substitution + admin rules."""
    rbtv_dir = paths["rbtv"]
    config_claude = paths["config_claude"]
    admin_claude = paths["admin_claude"]

    print(f"RBTV root: {rbtv_dir}")
    print()

    existing = admin_read_existing_values(rbtv_dir)
    values = admin_prompt_user_values(existing)
    print()

    print("Cleaning existing managed files...")
    del_stats = admin_delete_managed_files(rbtv_dir)
    print(f"  Deleted: {del_stats['deleted']} files")
    _print_errors(del_stats.get("errors", []))
    print()

    print("Copying _config/claude/ (path substitution + reinforcement)...")
    cfg_stats = admin_copy_folder(config_claude, rbtv_dir / ".claude", transform=True)
    if "reason" in cfg_stats:
        print(f"  Skipped ({cfg_stats['reason']})")
    else:
        print(f"  Copied: {cfg_stats['copied']}  |  Replaced: {cfg_stats['replaced']}")
        _print_errors(cfg_stats.get("errors", []))
    print()

    print("Copying _admin/.claude/ (admin rules)...")
    adm_stats = admin_copy_folder(admin_claude, rbtv_dir / ".claude", transform=False)
    if "reason" in adm_stats:
        print(f"  Skipped ({adm_stats['reason']})")
    else:
        print(f"  Copied: {adm_stats['copied']}  |  Replaced: {adm_stats['replaced']}")
        _print_errors(adm_stats.get("errors", []))
    print()

    admin_prefixes = ADMIN_MANAGED_PREFIXES

    print("Replicating commands to .cursor/")
    cmd_stats = replicate_commands_to_cursor(rbtv_dir, admin_prefixes)
    if "reason" in cmd_stats:
        print(f"  Skipped ({cmd_stats['reason']})")
    else:
        print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
        _print_errors(cmd_stats.get("errors", []))
    print()

    print("Replicating rules to .cursor/")
    rule_stats = replicate_rules_to_cursor(rbtv_dir, admin_prefixes)
    if "reason" in rule_stats:
        print(f"  Skipped ({rule_stats['reason']})")
    else:
        print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
        _print_errors(rule_stats.get("errors", []))
    print()

    print("Replicating agents to .cursor/")
    agent_stats = replicate_agents_to_cursor(rbtv_dir, admin_prefixes)
    if "reason" in agent_stats:
        print(f"  Skipped ({agent_stats['reason']})")
    else:
        print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
        _print_errors(agent_stats.get("errors", []))
    print()

    print("Replicating skills to .cursor/")
    skill_stats = replicate_skills_to_cursor(rbtv_dir, admin_prefixes)
    if "reason" in skill_stats:
        print(f"  Skipped ({skill_stats['reason']})")
    else:
        print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
        _print_errors(skill_stats.get("errors", []))
    print()

    print("Merging MCP configuration for Claude Code")
    mcp_stats_claude = merge_mcp_json(
        config_claude / ".mcp.json",
        rbtv_dir / ".claude" / ".mcp.json",
    )
    _print_mcp_stats(mcp_stats_claude)
    print()

    print("Merging MCP configuration for Cursor")
    mcp_stats_cursor = merge_mcp_json(
        config_claude / ".mcp.json",
        rbtv_dir / ".cursor" / "mcp.json",
    )
    _print_mcp_stats(mcp_stats_cursor)
    print()

    print("Injecting admin values into rule...")
    admin_inject_values(rbtv_dir, values)
    print("  Done")
    print()

    print("Copying CLAUDE.md to rbtv root...")
    claude_src = rbtv_dir / "_admin" / "CLAUDE.md"
    claude_dst = rbtv_dir / "CLAUDE.md"
    if claude_src.exists():
        shutil.copy2(str(claude_src), str(claude_dst))
        print("  Done")
    else:
        print("  WARNING: _admin/CLAUDE.md not found — skipping")
    print()

    # Also copy to Fernando's workflow data folder
    print("Installing RBTV context for Fernando (build-rbtv-component)...")
    fernando_dst = rbtv_dir / "workflows" / "build-rbtv-component" / "data" / "CLAUDE.md"
    if claude_src.exists():
        shutil.copy2(str(claude_src), str(fernando_dst))
        print("  Copied _admin/CLAUDE.md → workflows/build-rbtv-component/data/CLAUDE.md")
    else:
        print("  WARNING: _admin/CLAUDE.md not found — skipping")
    print()

    print("Ensuring .gitignore entries...")
    gi_stats = admin_ensure_gitignore(rbtv_dir)
    print(f"  Added: {gi_stats['added']}  |  Already present: {gi_stats['already_present']}  |  Migrated: {gi_stats['migrated']}")
    print()

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
    """BMAD config patching only — no workspace artifacts."""
    root = paths["root"]
    rbtv_dir = paths["rbtv"]

    print(f"RBTV source: {rbtv_dir}")
    print(f"BMAD root:   {root}")
    print()

    print("Checking BMAD version compatibility")
    if skip_version_check:
        print("  Skipped (--skip-version-check)")
    else:
        result = check_bmad_version(rbtv_dir, root)
        print_version_check_result(result)
    print()

    print("Normalizing BMAD output paths")
    norm_stats = normalize_bmad_output_paths(root)
    print(f"  Updated: {norm_stats['updated']} config files")
    _print_errors(norm_stats.get("errors", []))
    print()

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
        description="BMAD Bootstrap Script — unified RBTV + project installation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  workspace  Full setup: RBTV install + project bootstrap (default)\n"
            "  admin      Standalone RBTV dev setup at rbtv root (no project bootstrap)\n"
            "  sync       BMAD config patching only (no project bootstrap)\n"
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
        help="Skip BMAD version compatibility check",
    )
    parser.add_argument(
        "--skip-projects",
        action="store_true",
        help="Skip project-level bootstrap (workspace mode only)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"BMAD Bootstrap — {args.mode.upper()} mode")
    print("=" * 60)
    print()

    paths = get_paths()

    if args.mode == "workspace":
        return run_workspace_mode(paths, args.skip_version_check, args.skip_projects)
    elif args.mode == "admin":
        return run_admin_mode(paths)
    elif args.mode == "sync":
        return run_sync_mode(paths, args.skip_version_check)

    return 0


if __name__ == "__main__":
    sys.exit(main())

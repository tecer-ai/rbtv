#!/usr/bin/env python3
"""
RBTV Admin Installation Script

Sets up .cursor/ at rbtv root for standalone development.
Copies IDE configuration from _config/.cursor/ and _admin/.cursor/,
adjusts file paths for standalone mode, injects admin config values,
and appends path-resolution reinforcement to commands, agents, and skills.

Ensures .gitignore at rbtv root contains required entries (additive, preserves existing).

Usage:
    cd _bmad/rbtv
    python _admin/install-admin-rbtv.py

Idempotent: always deletes old managed files before recreating.
Re-run after every git pull to re-sync.
"""

import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANAGED_PREFIXES = ("bmad-rbtv", "admin-rbtv")

SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
]

EXTRA_MANAGED_FILES = [
    ".cursor/mcp.json",
]

# Path substitution: In source files (under _config/.cursor/), paths use
# {project-root}/_bmad/rbtv/ because that's where RBTV lives when installed
# in a parent BMAD project. In admin/standalone mode, the rbtv repo IS the
# workspace root, so we strip this prefix to make paths relative to root.
#
# NOTE: Only {project-root}/_bmad/rbtv/ is substituted. Other {project-root}
# references (e.g. {project-root}/.cursor/) remain in tasks and workflows;
# these are resolved at runtime by the admin rule's Path Resolution table.
PATH_FIND = "{project-root}/_bmad/rbtv/"
PATH_REPLACE = ""

# Appended to commands, agents, and skills (not rules or mcp.json).
# Reminds the model to load the admin rule, which resolves the remaining
# {project-root} references not covered by PATH_FIND/PATH_REPLACE above.
REINFORCEMENT = (
    "\n\n> **ADMIN MODE:** Before proceeding, load and read "
    "`.cursor/rules/admin-rbtv-bmad-mirror.mdc` for path resolution "
    "and config values. Key: `.cursor/` and `tasks/` are at workspace root.\n"
)

ADMIN_RULE_FILE = "admin-rbtv-bmad-mirror.mdc"

GITIGNORE_ENTRIES = [
    ".cursor/",
    ".claude/",
    "_admin-output/",
    ".gitignore",
]

CONFIG_DEFAULTS = {
    "user_name": "",
    "communication_language": "English",
    "document_output_language": "English",
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_paths():
    """Get source and destination paths. rbtv root is one folder up from _admin/."""
    script_dir = Path(__file__).parent.resolve()      # _admin/
    rbtv_dir = script_dir.parent                       # rbtv root

    return {
        "admin": script_dir,
        "rbtv": rbtv_dir,
        "config_cursor": rbtv_dir / "_config" / ".cursor",
        "admin_cursor": script_dir / ".cursor",
    }


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

def delete_managed_files(rbtv_dir: Path) -> dict:
    """
    Delete files whose names start with a managed prefix in .cursor/ subdirs.
    Also deletes extra managed files (mcp.json, .gitignore).
    """
    stats = {"deleted": 0, "errors": []}

    # Prefix-based deletion in .cursor/ subdirs
    for rel_dir in SEARCH_DIRS:
        search_dir = rbtv_dir / rel_dir
        if not search_dir.exists():
            continue

        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                if any(file_path.name.startswith(p) for p in MANAGED_PREFIXES):
                    try:
                        file_path.unlink()
                        stats["deleted"] += 1
                    except Exception as e:
                        stats["errors"].append(f"{file_path.relative_to(rbtv_dir)}: {e}")

    # Extra managed files
    for rel in EXTRA_MANAGED_FILES:
        fp = rbtv_dir / rel
        if fp.exists():
            try:
                fp.unlink()
                stats["deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel}: {e}")

    # Clean empty skill directories left behind
    skills_dir = rbtv_dir / ".cursor" / "skills"
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir(), reverse=True):
            if d.is_dir() and any(d.name.startswith(p) for p in MANAGED_PREFIXES):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass

    return stats


# ---------------------------------------------------------------------------
# Copy with optional transformation
# ---------------------------------------------------------------------------

def should_transform(rel_path: Path) -> bool:
    """Return True if the file should receive path substitution + reinforcement."""
    parts = rel_path.parts
    # Rules and mcp.json are copied as-is
    if parts[0] == "rules":
        return False
    if rel_path.name == "mcp.json":
        return False
    return True


def transform_content(content: str) -> str:
    """Apply path substitution and append reinforcement."""
    content = content.replace(PATH_FIND, PATH_REPLACE)
    content = content.rstrip() + REINFORCEMENT
    return content


def copy_folder(src: Path, dst: Path, transform: bool = False) -> dict:
    """
    Copy folder contents from src to dst.
    If transform=True, applies path substitution + reinforcement to eligible files.
    """
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

            if transform and should_transform(rel_path):
                content = src_file.read_text(encoding="utf-8")
                content = transform_content(content)
                dst_file.write_text(content, encoding="utf-8")
            else:
                shutil.copy2(str(src_file), str(dst_file))

            if existed:
                stats["replaced"] += 1
            else:
                stats["copied"] += 1

        except Exception as e:
            stats["errors"].append(f"{rel_path}: {e}")

    return stats


# ---------------------------------------------------------------------------
# Admin values: read existing, prompt, inject
# ---------------------------------------------------------------------------

def read_existing_values(rbtv_dir: Path) -> dict:
    """Read existing admin values from the installed admin rule (if present)."""
    values = dict(CONFIG_DEFAULTS)

    rule_file = rbtv_dir / ".cursor" / "rules" / ADMIN_RULE_FILE
    if not rule_file.exists():
        return values

    content = rule_file.read_text(encoding="utf-8")
    for key in values:
        match = re.search(rf'{key}\s*\|\s*"([^"]*)"', content)
        if match:
            values[key] = match.group(1)

    return values


def prompt_user_values(defaults: dict) -> dict:
    """Prompt user for config values. Shows defaults; Enter keeps them."""
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


def inject_admin_values(rbtv_dir: Path, values: dict):
    """Replace {admin_*} placeholders in the installed admin rule with user values."""
    rule_file = rbtv_dir / ".cursor" / "rules" / ADMIN_RULE_FILE
    if not rule_file.exists():
        return

    content = rule_file.read_text(encoding="utf-8")

    for key, value in values.items():
        placeholder = "{admin_" + key + "}"
        content = content.replace(placeholder, value)

    rule_file.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------

def ensure_gitignore(rbtv_dir: Path) -> dict:
    """Ensure required entries exist in .gitignore. Adds only missing entries."""
    gitignore = rbtv_dir / ".gitignore"
    stats = {"added": 0, "already_present": 0}

    existing_lines: set[str] = set()
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        existing_lines = {line.strip() for line in content.splitlines()}
    else:
        content = ""

    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in existing_lines]
    stats["already_present"] = len(GITIGNORE_ENTRIES) - len(missing)
    stats["added"] = len(missing)

    if missing:
        if content and not content.endswith("\n"):
            content += "\n"
        if content:
            content += "\n# Added by install-admin-rbtv.py\n"
        else:
            content = "# Generated by install-admin-rbtv.py\n"
        content += "\n".join(missing) + "\n"
        gitignore.write_text(content, encoding="utf-8")

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("RBTV Admin Installation Script")
    print("=" * 60)
    print()

    paths = get_paths()
    rbtv_dir = paths["rbtv"]

    print(f"RBTV root: {rbtv_dir}")
    print()

    # ---- Read existing values for defaults ----
    existing = read_existing_values(rbtv_dir)
    values = prompt_user_values(existing)
    print()

    # ---- Step 1: Clean ----
    print("Cleaning existing managed files...")
    del_stats = delete_managed_files(rbtv_dir)
    print(f"  Deleted: {del_stats['deleted']} files")
    for err in del_stats["errors"]:
        print(f"    Error: {err}")
    print()

    # ---- Step 2: Copy _config/.cursor/ (with transforms) ----
    print("Copying _config/.cursor/ (path substitution + reinforcement)...")
    cfg_stats = copy_folder(
        paths["config_cursor"],
        rbtv_dir / ".cursor",
        transform=True,
    )
    if "reason" in cfg_stats:
        print(f"  Skipped: {cfg_stats['reason']}")
    else:
        print(f"  Copied: {cfg_stats['copied']}  |  Replaced: {cfg_stats['replaced']}")
        for err in cfg_stats["errors"]:
            print(f"    Error: {err}")
    print()

    # ---- Step 3: Copy _admin/.cursor/ (no transforms) ----
    print("Copying _admin/.cursor/ (admin rules)...")
    adm_stats = copy_folder(
        paths["admin_cursor"],
        rbtv_dir / ".cursor",
        transform=False,
    )
    if "reason" in adm_stats:
        print(f"  Skipped: {adm_stats['reason']}")
    else:
        print(f"  Copied: {adm_stats['copied']}  |  Replaced: {adm_stats['replaced']}")
        for err in adm_stats["errors"]:
            print(f"    Error: {err}")
    print()

    # ---- Step 4: Inject admin values ----
    print("Injecting admin values into rule...")
    inject_admin_values(rbtv_dir, values)
    print("  Done")
    print()

    # ---- Step 5: Ensure .gitignore entries ----
    print("Ensuring .gitignore entries...")
    gi_stats = ensure_gitignore(rbtv_dir)
    print(f"  Added: {gi_stats['added']}  |  Already present: {gi_stats['already_present']}")
    print()

    # ---- Summary ----
    total_copied = cfg_stats.get("copied", 0) + adm_stats.get("copied", 0)
    total_replaced = cfg_stats.get("replaced", 0) + adm_stats.get("replaced", 0)

    print("-" * 60)
    print("Summary")
    print("-" * 60)
    print(f"  Files copied:   {total_copied}")
    print(f"  Files replaced: {total_replaced}")
    print(f"  Admin user:     {values.get('user_name', 'N/A')}")
    print(f"  Language:        {values.get('communication_language', 'N/A')}")
    print()
    print("Next steps:")
    print("  1. Restart Cursor to load new commands and rules")
    print("  2. Run /bmad-rbtv-help to verify tools work")
    print()
    print("Remember: re-run this script after every 'git pull'")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

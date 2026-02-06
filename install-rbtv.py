#!/usr/bin/env python3
"""
RBTV Installation Script

Copies .cursor/ folder from rbtv/ to the project root (two folders up from this script).
Deletes old RBTV files (files starting with bmad-rbtv) under .cursor/ and .claude/
before copying to ensure a clean install.
Merges mcp.json configurations for Cursor IDE and Claude Code.
Creates .claude/commands/ and replicates Cursor commands for Claude compatibility.
Updates BMAD module configs to use project-specific output folders.
Adds RBTV to the BMAD help catalog.
Merges .vscode/settings.json to configure workspace file exclusions.
Merges .cursorignore to block AI access to archive folders.
Run this script after every git pull or fetch to sync IDE configuration.

Usage:
    cd _bmad/rbtv
    python install-rbtv.py
"""

import csv
import json
import re
import shutil
import sys
from pathlib import Path


def get_paths():
    """Get source and destination paths. Root is two folders up from this script."""
    script_dir = Path(__file__).parent.resolve()  # _bmad/rbtv/
    root = script_dir.parent.parent  # project root (two folders up)
    
    return {
        "rbtv": script_dir,
        "root": root,
        "folders": [".cursor"]
    }


RBTV_SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
    ".claude/commands",
]


def delete_rbtv_files(root: Path) -> dict:
    """
    Delete files whose names start with 'bmad-rbtv' in specified directories.
    Searches recursively within each directory.
    Returns stats about the operation.
    """
    stats = {"deleted": 0, "skipped": 0, "errors": []}
    
    for rel_dir in RBTV_SEARCH_DIRS:
        search_dir = root / rel_dir
        
        if not search_dir.exists():
            stats["skipped"] += 1
            continue
        
        # Find all files starting with bmad-rbtv
        for file_path in search_dir.rglob("bmad-rbtv*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    stats["deleted"] += 1
                except Exception as e:
                    stats["errors"].append(f"{file_path.relative_to(root)}: {e}")
    
    return stats


def copy_folder(src: Path, dst: Path) -> dict:
    """
    Copy folder contents from src to dst.
    If dst exists, merge contents (overwrite on conflict).
    Source files are left unchanged.
    Returns stats about the operation.
    """
    stats = {"copied": 0, "replaced": 0, "skipped": 0, "errors": []}
    
    if not src.exists():
        return {"skipped": 1, "reason": "source does not exist"}
    
    dst.mkdir(parents=True, exist_ok=True)
    
    for src_file in src.rglob("*"):
        if src_file.is_file():
            rel_path = src_file.relative_to(src)
            dst_file = dst / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if dst_file.exists():
                    stats["replaced"] += 1
                else:
                    stats["copied"] += 1
                shutil.copy2(str(src_file), str(dst_file))
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
    
    return stats


def merge_mcp_json(src_mcp: Path, dst_mcp: Path) -> dict:
    """
    Merge MCP server configurations from src to dst.
    If dst exists, merge mcpServers objects (src overwrites on conflict).
    Returns stats about the operation.
    """
    stats = {"merged": 0, "added": 0, "errors": []}
    
    if not src_mcp.exists():
        return {"skipped": 1, "reason": "source mcp.json does not exist"}
    
    try:
        # Load source configuration
        with open(src_mcp, 'r', encoding='utf-8') as f:
            src_config = json.load(f)
        
        # Load or create destination configuration
        if dst_mcp.exists():
            with open(dst_mcp, 'r', encoding='utf-8') as f:
                dst_config = json.load(f)
        else:
            dst_config = {"mcpServers": {}}
        
        # Ensure mcpServers key exists
        if "mcpServers" not in dst_config:
            dst_config["mcpServers"] = {}
        
        # Merge server configurations
        src_servers = src_config.get("mcpServers", {})
        for server_name, server_config in src_servers.items():
            if server_name in dst_config["mcpServers"]:
                stats["merged"] += 1
            else:
                stats["added"] += 1
            dst_config["mcpServers"][server_name] = server_config
        
        # Create parent directory if needed
        dst_mcp.parent.mkdir(parents=True, exist_ok=True)
        
        # Write merged configuration
        with open(dst_mcp, 'w', encoding='utf-8') as f:
            json.dump(dst_config, f, indent=2)
        
    except Exception as e:
        stats["errors"].append(f"mcp.json merge failed: {e}")
    
    return stats


def merge_mcp_to_claude_code(src_mcp: Path, bmad_path: Path) -> dict:
    """
    Merge MCP configuration to .claude/.mcp.json for Claude Code.
    Returns stats about the operation.
    """
    stats = {"merged": 0, "added": 0, "errors": []}
    
    if not src_mcp.exists():
        return {"skipped": 1, "reason": "source mcp.json does not exist"}
    
    dst_mcp = bmad_path / ".claude" / ".mcp.json"
    
    try:
        # Load source configuration
        with open(src_mcp, 'r', encoding='utf-8') as f:
            src_config = json.load(f)
        
        # Load or create destination configuration
        if dst_mcp.exists():
            with open(dst_mcp, 'r', encoding='utf-8') as f:
                dst_config = json.load(f)
        else:
            dst_config = {"mcpServers": {}}
        
        # Ensure mcpServers key exists
        if "mcpServers" not in dst_config:
            dst_config["mcpServers"] = {}
        
        # Merge server configurations
        src_servers = src_config.get("mcpServers", {})
        for server_name, server_config in src_servers.items():
            if server_name in dst_config["mcpServers"]:
                stats["merged"] += 1
            else:
                stats["added"] += 1
            dst_config["mcpServers"][server_name] = server_config
        
        # Create parent directory if needed
        dst_mcp.parent.mkdir(parents=True, exist_ok=True)
        
        # Write merged configuration
        with open(dst_mcp, 'w', encoding='utf-8') as f:
            json.dump(dst_config, f, indent=2)
        
    except Exception as e:
        stats["errors"].append(f".claude/.mcp.json merge failed: {e}")
    
    return stats


def replicate_commands_to_claude(bmad_path: Path) -> dict:
    """
    Replicate .cursor/commands/ to .claude/commands/.
    Returns stats about the operation.
    """
    stats = {"copied": 0, "replaced": 0, "errors": []}
    
    cursor_commands = bmad_path / ".cursor" / "commands"
    claude_commands = bmad_path / ".claude" / "commands"
    
    if not cursor_commands.exists():
        return {"skipped": 1, "reason": ".cursor/commands/ does not exist"}
    
    # Create .claude/commands/ directory
    claude_commands.mkdir(parents=True, exist_ok=True)
    
    # Copy all command files
    for cursor_file in cursor_commands.rglob("*"):
        if cursor_file.is_file():
            rel_path = cursor_file.relative_to(cursor_commands)
            claude_file = claude_commands / rel_path
            
            # Create parent directories
            claude_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if claude_file.exists():
                    stats["replaced"] += 1
                else:
                    stats["copied"] += 1
                
                # Copy the file
                shutil.copy2(str(cursor_file), str(claude_file))
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
    
    return stats


def update_bmad_config(bmad_path: Path) -> dict:
    """
    Update BMAD module configs to use project-specific output folders.
    Updates core and bmm config.yaml files.
    Returns stats about the operation.
    """
    stats = {"updated": 0, "errors": []}
    
    # Update core/config.yaml
    core_config = bmad_path / "_bmad" / "core" / "config.yaml"
    if core_config.exists():
        try:
            content = core_config.read_text(encoding='utf-8')
            
            # Update output_folder to use project-specific pattern
            content = re.sub(
                r'output_folder:\s*".*?"',
                'output_folder: "{project-root}/_bmad-output"',
                content
            )
            
            core_config.write_text(content, encoding='utf-8')
            stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(f"core/config.yaml: {e}")
    
    # Update bmm/config.yaml
    bmm_config = bmad_path / "_bmad" / "bmm" / "config.yaml"
    if bmm_config.exists():
        try:
            content = bmm_config.read_text(encoding='utf-8')
            
            # Update output_folder
            content = re.sub(
                r'output_folder:\s*".*?"',
                'output_folder: "{project-root}/_bmad-output"',
                content
            )
            
            # Update planning_artifacts to use project-specific pattern
            content = re.sub(
                r'planning_artifacts:\s*".*?"',
                'planning_artifacts: "{project-root}/_bmad-output/{project-name}/planning-artifacts"',
                content
            )
            
            # Update implementation_artifacts to use project-specific pattern
            content = re.sub(
                r'implementation_artifacts:\s*".*?"',
                'implementation_artifacts: "{project-root}/_bmad-output/{project-name}/implementation-artifacts"',
                content
            )
            
            bmm_config.write_text(content, encoding='utf-8')
            stats["updated"] += 1
        except Exception as e:
            stats["errors"].append(f"bmm/config.yaml: {e}")
    
    return stats


def add_rbtv_to_help_catalog(bmad_path: Path) -> dict:
    """
    Add RBTV workflows to the BMAD help catalog.
    Returns stats about the operation.
    """
    stats = {"added": 0, "errors": []}
    
    help_csv = bmad_path / "_bmad" / "_config" / "bmad-help.csv"
    
    if not help_csv.exists():
        stats["errors"].append("bmad-help.csv not found")
        return stats
    
    try:
        # Read existing catalog
        with open(help_csv, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            fieldnames = reader.fieldnames
        
        # Check if RBTV entries already exist
        has_rbtv = any(row.get('module') == 'rbtv' for row in existing_rows)
        
        if not has_rbtv:
            # Add RBTV entries
            rbtv_rows = [
                {
                    'module': 'rbtv',
                    'phase': 'anytime',
                    'name': 'Business Innovation',
                    'code': 'BI',
                    'sequence': '10',
                    'workflow-file': '_bmad/rbtv/workflows/bi-business-innovation/workflow.md',
                    'command': 'bmad-rbtv-mentor',
                    'required': 'false',
                    'agent-name': 'mentor',
                    'agent-command': 'bmad-rbtv-mentor',
                    'agent-display-name': 'Mentor',
                    'agent-title': '🚀 YC Mentor',
                    'options': '',
                    'description': 'Guide users through 6-milestone business innovation lifecycle from idea to MVP',
                    'output-location': 'output_folder',
                    'outputs': 'project-memo'
                }
            ]
            
            # Write updated catalog
            with open(help_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows + rbtv_rows)
            
            stats["added"] = len(rbtv_rows)
    
    except Exception as e:
        stats["errors"].append(f"Failed to update help catalog: {e}")
    
    return stats


def merge_vscode_settings(rbtv_path: Path, bmad_path: Path) -> dict:
    """
    Merge RBTV .vscode/settings.json with existing user settings at BMAD root.
    - Preserves all user data
    - Updates/overwrites only RBTV-managed keys in files.exclude
    Returns stats about the operation.
    """
    stats = {"merged": 0, "created": 0, "errors": []}
    
    src_settings = rbtv_path / ".vscode" / "settings.json"
    dst_settings = bmad_path / ".vscode" / "settings.json"
    
    if not src_settings.exists():
        return {"skipped": 1, "reason": "source .vscode/settings.json does not exist"}
    
    try:
        # Load RBTV settings
        with open(src_settings, 'r', encoding='utf-8') as f:
            rbtv_settings = json.load(f)
        
        # Load or create destination settings
        if dst_settings.exists():
            with open(dst_settings, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            stats["merged"] = 1
        else:
            existing = {}
            stats["created"] = 1
        
        # Ensure files.exclude exists
        if "files.exclude" not in existing:
            existing["files.exclude"] = {}
        
        # Merge: preserve user patterns, update RBTV patterns
        for pattern, value in rbtv_settings.get("files.exclude", {}).items():
            existing["files.exclude"][pattern] = value
        
        # Create parent directory if needed
        dst_settings.parent.mkdir(parents=True, exist_ok=True)
        
        # Write back
        with open(dst_settings, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)
    
    except Exception as e:
        stats["errors"].append(f".vscode/settings.json merge failed: {e}")
    
    return stats


def merge_cursorignore(rbtv_path: Path, bmad_path: Path) -> dict:
    """
    Merge RBTV .cursorignore patterns with existing .cursorignore at BMAD root.
    - Preserves all user patterns
    - Adds RBTV patterns if not already present
    Returns stats about the operation.
    """
    stats = {"added": 0, "skipped": 0, "errors": []}
    
    dst_cursorignore = bmad_path / ".cursorignore"
    
    # RBTV-managed patterns
    rbtv_patterns = [
        "_bmad-output/archive/",
    ]
    
    try:
        # Load existing patterns if file exists
        existing_patterns = set()
        if dst_cursorignore.exists():
            with open(dst_cursorignore, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        existing_patterns.add(line)
        
        # Determine which patterns to add
        patterns_to_add = []
        for pattern in rbtv_patterns:
            if pattern not in existing_patterns:
                patterns_to_add.append(pattern)
                stats["added"] += 1
            else:
                stats["skipped"] += 1
        
        # Append new patterns if any
        if patterns_to_add:
            with open(dst_cursorignore, 'a', encoding='utf-8') as f:
                # Add header if file is new or empty
                if not dst_cursorignore.exists() or dst_cursorignore.stat().st_size == 0:
                    f.write("# RBTV-managed patterns\n")
                elif existing_patterns:
                    f.write("\n# RBTV-managed patterns\n")
                
                for pattern in patterns_to_add:
                    f.write(f"{pattern}\n")
    
    except Exception as e:
        stats["errors"].append(f".cursorignore merge failed: {e}")
    
    return stats


def main():
    """Main installation routine."""
    print("=" * 60)
    print("RBTV Installation Script")
    print("=" * 60)
    print()
    
    paths = get_paths()
    root = paths["root"]
    
    print(f"Source:      {paths['rbtv']}")
    print(f"Destination: {root}")
    print()
    
    # Delete existing RBTV files before copying
    print("Deleting existing RBTV files (bmad-rbtv*)")
    delete_stats = delete_rbtv_files(root)
    print(f"  Deleted: {delete_stats['deleted']} files")
    if delete_stats["errors"]:
        for err in delete_stats["errors"]:
            print(f"    - {err}")
    print()
    
    total_copied = 0
    total_replaced = 0
    
    for folder in paths["folders"]:
        src = paths["rbtv"] / folder
        dst = root / folder
        
        print(f"Processing {folder}/")
        print(f"  From: {src}")
        print(f"  To:   {dst}")
        
        stats = copy_folder(src, dst)
        
        if "reason" in stats:
            print(f"  Status: Skipped ({stats['reason']})")
        else:
            print(f"  Copied: {stats['copied']} files")
            print(f"  Replaced: {stats['replaced']} files")
            total_copied += stats["copied"]
            total_replaced += stats["replaced"]
            
            if stats["errors"]:
                print(f"  Errors:")
                for err in stats["errors"]:
                    print(f"    - {err}")
        
        print()
    
    # Merge MCP configurations for Cursor
    print("Merging MCP configuration for Cursor")
    print(f"  From: {paths['rbtv'] / '.cursor' / 'mcp.json'}")
    print(f"  To:   {root / '.cursor' / 'mcp.json'}")
    
    cursor_mcp_stats = merge_mcp_json(
        paths["rbtv"] / ".cursor" / "mcp.json",
        root / ".cursor" / "mcp.json"
    )
    
    if "reason" in cursor_mcp_stats:
        print(f"  Status: Skipped ({cursor_mcp_stats['reason']})")
    else:
        print(f"  Added: {cursor_mcp_stats['added']} servers")
        print(f"  Merged: {cursor_mcp_stats['merged']} servers")
        
        if cursor_mcp_stats["errors"]:
            print(f"  Errors:")
            for err in cursor_mcp_stats["errors"]:
                print(f"    - {err}")
    
    print()
    
    # Merge MCP configurations for Claude Code
    print("Merging MCP configuration for Claude Code")
    print(f"  From: {paths['rbtv'] / '.cursor' / 'mcp.json'}")
    print(f"  To:   {root / '.claude' / '.mcp.json'}")
    
    claude_code_mcp_stats = merge_mcp_to_claude_code(
        paths["rbtv"] / ".cursor" / "mcp.json",
        root
    )
    
    if "reason" in claude_code_mcp_stats:
        print(f"  Status: Skipped ({claude_code_mcp_stats['reason']})")
    else:
        print(f"  Added: {claude_code_mcp_stats['added']} servers")
        print(f"  Merged: {claude_code_mcp_stats['merged']} servers")
        
        if claude_code_mcp_stats["errors"]:
            print(f"  Errors:")
            for err in claude_code_mcp_stats["errors"]:
                print(f"    - {err}")
    
    print()
    
    # Replicate commands to Claude
    print("Replicating commands to .claude/")
    print(f"  From: {root / '.cursor' / 'commands'}")
    print(f"  To:   {root / '.claude' / 'commands'}")
    
    claude_stats = replicate_commands_to_claude(root)
    
    if "reason" in claude_stats:
        print(f"  Status: Skipped ({claude_stats['reason']})")
    else:
        print(f"  Copied: {claude_stats['copied']} files")
        print(f"  Replaced: {claude_stats['replaced']} files")
        
        if claude_stats["errors"]:
            print(f"  Errors:")
            for err in claude_stats["errors"]:
                print(f"    - {err}")
    
    print()
    
    # Update BMAD configs
    print("Updating BMAD module configs")
    print(f"  Updating: {root / '_bmad' / 'core' / 'config.yaml'}")
    print(f"  Updating: {root / '_bmad' / 'bmm' / 'config.yaml'}")
    
    config_stats = update_bmad_config(root)
    
    if config_stats["errors"]:
        print(f"  Errors:")
        for err in config_stats["errors"]:
            print(f"    - {err}")
    else:
        print(f"  Updated: {config_stats['updated']} config files")
    
    print()
    
    # Add RBTV to help catalog
    print("Adding RBTV to BMAD help catalog")
    print(f"  Updating: {root / '_bmad' / '_config' / 'bmad-help.csv'}")
    
    help_stats = add_rbtv_to_help_catalog(root)
    
    if "reason" in help_stats:
        print(f"  Status: Skipped ({help_stats['reason']})")
    elif help_stats["errors"]:
        print(f"  Errors:")
        for err in help_stats["errors"]:
            print(f"    - {err}")
    else:
        if help_stats["added"] > 0:
            print(f"  Added: {help_stats['added']} RBTV workflows to catalog")
        else:
            print(f"  Status: RBTV already in catalog")
    
    print()
    
    # Merge .vscode/settings.json
    print("Merging .vscode/settings.json")
    print(f"  From: {paths['rbtv'] / '.vscode' / 'settings.json'}")
    print(f"  To:   {root / '.vscode' / 'settings.json'}")
    
    vscode_stats = merge_vscode_settings(paths["rbtv"], root)
    
    if "reason" in vscode_stats:
        print(f"  Status: Skipped ({vscode_stats['reason']})")
    elif vscode_stats["errors"]:
        print(f"  Errors:")
        for err in vscode_stats["errors"]:
            print(f"    - {err}")
    else:
        if vscode_stats["created"] > 0:
            print(f"  Status: Created new settings file")
        elif vscode_stats["merged"] > 0:
            print(f"  Status: Merged with existing settings")
    
    print()
    
    # Merge .cursorignore
    print("Merging .cursorignore")
    print(f"  To: {root / '.cursorignore'}")
    
    cursorignore_stats = merge_cursorignore(paths["rbtv"], root)
    
    if cursorignore_stats["errors"]:
        print(f"  Errors:")
        for err in cursorignore_stats["errors"]:
            print(f"    - {err}")
    else:
        if cursorignore_stats["added"] > 0:
            print(f"  Added: {cursorignore_stats['added']} patterns")
        if cursorignore_stats["skipped"] > 0:
            print(f"  Skipped: {cursorignore_stats['skipped']} patterns (already present)")
    
    print()
    print("-" * 60)
    print("Summary")
    print("-" * 60)
    print(f"Total files copied:   {total_copied}")
    print(f"Total files replaced: {total_replaced}")
    if "added" in cursor_mcp_stats:
        print(f"Cursor MCP servers:   {cursor_mcp_stats['added'] + cursor_mcp_stats['merged']}")
    if "added" in claude_code_mcp_stats:
        print(f"Claude Code MCP servers: {claude_code_mcp_stats['added'] + claude_code_mcp_stats['merged']}")
    if "copied" in claude_stats:
        print(f"Commands replicated:  {claude_stats['copied'] + claude_stats['replaced']}")
    if config_stats["updated"] > 0:
        print(f"BMAD configs updated: {config_stats['updated']}")
    if help_stats.get("added", 0) > 0:
        print(f"Help catalog entries: {help_stats['added']}")
    if vscode_stats.get("created", 0) > 0 or vscode_stats.get("merged", 0) > 0:
        print(f"VS Code settings:     Configured")
    if cursorignore_stats.get("added", 0) > 0:
        print(f".cursorignore:        {cursorignore_stats['added']} patterns added")
    print()
    print("Installation complete.")
    print()
    print("Next steps:")
    print("  1. Restart Cursor to load new MCP servers and commands")
    print("  2. Restart Claude Code to load new MCP servers")
    print("  3. Run /bmad-help to see RBTV workflows in the catalog")
    print("  4. Run /bmad-rbtv-help to see RBTV-specific commands")
    print()
    print("Remember: Run this script after every 'git pull' or 'git fetch'")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

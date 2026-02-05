#!/usr/bin/env python3
"""
RBTV Installation Script

Moves .cursor/ folder from rbtv/ to the parent _bmad/ folder.
Creates .claude/commands/ and replicates Cursor commands for Claude compatibility.
Run this script after every git pull or fetch to sync IDE configuration.

Usage:
    cd _bmad/rbtv
    python install-rbtv.py
"""

import shutil
import sys
from pathlib import Path


def get_paths():
    """Get source and destination paths."""
    script_dir = Path(__file__).parent.resolve()
    parent_dir = script_dir.parent
    
    return {
        "rbtv": script_dir,
        "bmad": parent_dir,
        "folders": [".cursor"]
    }


def move_folder(src: Path, dst: Path) -> dict:
    """
    Move folder contents from src to dst.
    If dst exists, merge contents (overwrite on conflict).
    Returns stats about the operation.
    """
    stats = {"moved": 0, "replaced": 0, "skipped": 0, "errors": []}
    
    if not src.exists():
        return {"skipped": 1, "reason": "source does not exist"}
    
    # Create destination if it doesn't exist
    dst.mkdir(parents=True, exist_ok=True)
    
    # Walk through all files in source
    for src_file in src.rglob("*"):
        if src_file.is_file():
            # Calculate relative path and destination
            rel_path = src_file.relative_to(src)
            dst_file = dst / rel_path
            
            # Create parent directories
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if dst_file.exists():
                    dst_file.unlink()
                    stats["replaced"] += 1
                else:
                    stats["moved"] += 1
                
                # Move the file
                shutil.move(str(src_file), str(dst_file))
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
    
    # Remove empty directories in source
    for src_dir in sorted(src.rglob("*"), reverse=True):
        if src_dir.is_dir():
            try:
                src_dir.rmdir()
            except OSError:
                pass  # Directory not empty
    
    # Remove the source folder if empty
    try:
        src.rmdir()
    except OSError:
        pass  # Directory not empty
    
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


def main():
    """Main installation routine."""
    print("=" * 60)
    print("RBTV Installation Script")
    print("=" * 60)
    print()
    
    paths = get_paths()
    
    print(f"Source:      {paths['rbtv']}")
    print(f"Destination: {paths['bmad']}")
    print()
    
    total_moved = 0
    total_replaced = 0
    
    for folder in paths["folders"]:
        src = paths["rbtv"] / folder
        dst = paths["bmad"] / folder
        
        print(f"Processing {folder}/")
        print(f"  From: {src}")
        print(f"  To:   {dst}")
        
        stats = move_folder(src, dst)
        
        if "reason" in stats:
            print(f"  Status: Skipped ({stats['reason']})")
        else:
            print(f"  Moved: {stats['moved']} files")
            print(f"  Replaced: {stats['replaced']} files")
            total_moved += stats["moved"]
            total_replaced += stats["replaced"]
            
            if stats["errors"]:
                print(f"  Errors:")
                for err in stats["errors"]:
                    print(f"    - {err}")
        
        print()
    
    # Replicate commands to Claude
    print("Replicating commands to .claude/")
    print(f"  From: {paths['bmad'] / '.cursor' / 'commands'}")
    print(f"  To:   {paths['bmad'] / '.claude' / 'commands'}")
    
    claude_stats = replicate_commands_to_claude(paths["bmad"])
    
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
    print("-" * 60)
    print("Summary")
    print("-" * 60)
    print(f"Total files moved:    {total_moved}")
    print(f"Total files replaced: {total_replaced}")
    if "copied" in claude_stats:
        print(f"Commands replicated:  {claude_stats['copied'] + claude_stats['replaced']}")
    print()
    print("Installation complete.")
    print()
    print("Next steps:")
    print("  1. Restart your IDE to load new commands")
    print("  2. Run /bmad-rbtv-help to see available commands")
    print()
    print("Remember: Run this script after every 'git pull' or 'git fetch'")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

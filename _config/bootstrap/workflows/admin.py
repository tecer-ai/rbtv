import re
import shutil
from pathlib import Path
from bootstrap.context import BootstrapContext
from bootstrap.core.constants import ADMIN_CONFIG_DEFAULTS, ADMIN_RULE_FILE, ADMIN_MANAGED_PREFIXES
from bootstrap.fs.cleanup import FileCleaner
from bootstrap.fs.copy import FileCopier
from bootstrap.fs.replicate import FileReplicator
from bootstrap.fs.merge import FileMerger
from bootstrap.utils import print_errors, print_mcp_stats
from bootstrap.workflows.base import BootstrapWorkflow

class AdminWorkflow(BootstrapWorkflow):
    def admin_is_installed(self) -> bool:
        rbtv_dir = self.ctx.rbtv
        if (rbtv_dir / "CLAUDE.md").exists():
            return True
        if (rbtv_dir / ".claude").exists():
            return True
        if (rbtv_dir / ".cursor").exists():
            return True
        if (rbtv_dir / ".agents").exists():
            return True
        return False

    def run_uninstall(self) -> int:
        rbtv_dir = self.ctx.rbtv

        print("Deleting managed files (bmad-rbtv*, admin-rbtv*)...")
        del_stats = FileCleaner.admin_delete_managed_files(rbtv_dir)
        print(f"  Deleted: {del_stats['deleted']} files")
        print_errors(del_stats.get("errors", []))
        print()

        claude_md = rbtv_dir / "CLAUDE.md"
        if claude_md.exists():
            print("Removing CLAUDE.md...")
            claude_md.unlink()
            print("  Done")
        else:
            print("CLAUDE.md: not present (already clean)")
        print()

        removed_dirs = 0
        for dirname in (".claude", ".cursor", ".agents"):
            dirpath = rbtv_dir / dirname
            if dirpath.exists():
                print(f"Removing {dirname}/...")
                shutil.rmtree(dirpath)
                removed_dirs += 1
                print("  Done")
        if removed_dirs == 0:
            print("IDE directories: not present (already clean)")
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

    def _read_existing_values(self) -> dict:
        values = dict(ADMIN_CONFIG_DEFAULTS)
        rule_file = self.ctx.rbtv / ".claude" / "rules" / ADMIN_RULE_FILE
        if not rule_file.exists():
            return values
        content = rule_file.read_text(encoding="utf-8")
        for key in values:
            match = re.search(rf'{key}\s*\|\s*"([^"]*)"', content)
            if match:
                values[key] = match.group(1)
        return values

    def _prompt_user_values(self, defaults: dict) -> dict:
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

    def _inject_values(self, values: dict) -> None:
        rule_file = self.ctx.rbtv / ".claude" / "rules" / ADMIN_RULE_FILE
        if not rule_file.exists():
            return
        content = rule_file.read_text(encoding="utf-8")
        for key, value in values.items():
            content = content.replace("{admin_" + key + "}", value)
        rule_file.write_text(content, encoding="utf-8")

    def run(self) -> int:
        rbtv_dir = self.ctx.rbtv
        config_claude = self.ctx.config_claude
        admin_claude = self.ctx.admin_claude

        print(f"RBTV root: {rbtv_dir}")
        print()

        existing = self._read_existing_values()
        values = self._prompt_user_values(existing)
        print()

        print("Cleaning existing managed files...")
        del_stats = FileCleaner.admin_delete_managed_files(rbtv_dir)
        print(f"  Deleted: {del_stats['deleted']} files")
        print_errors(del_stats.get("errors", []))
        print()

        print("Copying _config/claude/ (path substitution + reinforcement)...")
        cfg_stats = FileCopier.admin_copy_folder(config_claude, rbtv_dir / ".claude", transform=True)
        if "reason" in cfg_stats:
            print(f"  Skipped ({cfg_stats['reason']})")
        else:
            print(f"  Copied: {cfg_stats['copied']}  |  Replaced: {cfg_stats['replaced']}")
            print_errors(cfg_stats.get("errors", []))
        print()

        print("Copying _admin/.claude/ (admin rules)...")
        adm_stats = FileCopier.admin_copy_folder(admin_claude, rbtv_dir / ".claude", transform=False)
        if "reason" in adm_stats:
            print(f"  Skipped ({adm_stats['reason']})")
        else:
            print(f"  Copied: {adm_stats['copied']}  |  Replaced: {adm_stats['replaced']}")
            print_errors(adm_stats.get("errors", []))
        print()

        admin_prefixes = ADMIN_MANAGED_PREFIXES

        for ide in self.ctx.target_ides:
            if ide == "claude":
                continue # Already staged

            print(f"Replicating to {ide.upper()}")

            print(f"Replicating commands to {ide}...")
            cmd_stats = FileReplicator.replicate_commands(rbtv_dir, admin_prefixes, ide)
            if "reason" in cmd_stats:
                print(f"  Skipped ({cmd_stats['reason']})")
            else:
                print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
                print_errors(cmd_stats.get("errors", []))
            print()

            print(f"Replicating rules to {ide}...")
            rule_stats = FileReplicator.replicate_rules(rbtv_dir, admin_prefixes, ide)
            if "reason" in rule_stats:
                print(f"  Skipped ({rule_stats['reason']})")
            else:
                print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
                print_errors(rule_stats.get("errors", []))
            print()

            print(f"Replicating agents to {ide}...")
            agent_stats = FileReplicator.replicate_agents(rbtv_dir, admin_prefixes, ide)
            if "reason" in agent_stats:
                print(f"  Skipped ({agent_stats['reason']})")
            else:
                print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
                print_errors(agent_stats.get("errors", []))
            print()

            print(f"Replicating skills to {ide}...")
            skill_stats = FileReplicator.replicate_skills(rbtv_dir, admin_prefixes, ide)
            if "reason" in skill_stats:
                print(f"  Skipped ({skill_stats['reason']})")
            else:
                print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
                print_errors(skill_stats.get("errors", []))
            print()

        if "claude" in self.ctx.target_ides:
            print("Merging MCP configuration for Claude Code")
            mcp_stats_claude = FileMerger.merge_mcp_json(
                config_claude / ".mcp.json",
                rbtv_dir / ".claude" / ".mcp.json",
            )
            print_mcp_stats(mcp_stats_claude)
            print()

        if "cursor" in self.ctx.target_ides:
            print("Merging MCP configuration for Cursor")
            mcp_stats_cursor = FileMerger.merge_mcp_json(
                config_claude / ".mcp.json",
                rbtv_dir / ".cursor" / "mcp.json",
            )
            print_mcp_stats(mcp_stats_cursor)
            print()
            
        if "antigravity" in self.ctx.target_ides:
            print("Merging MCP configuration for Antigravity")
            mcp_stats_ag = FileMerger.merge_mcp_json(
                config_claude / ".mcp.json",
                rbtv_dir / ".agents" / "mcp.json",
            )
            print_mcp_stats(mcp_stats_ag)
            print()

        print("Injecting admin values into rule...")
        self._inject_values(values)
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

        print("Installing RBTV context for Fernando (build-rbtv-component)...")
        fernando_dst = rbtv_dir / "workflows" / "build-rbtv-component" / "data" / "CLAUDE.md"
        if claude_src.exists():
            shutil.copy2(str(claude_src), str(fernando_dst))
            print("  Copied _admin/CLAUDE.md → workflows/build-rbtv-component/data/CLAUDE.md")
        else:
            print("  WARNING: _admin/CLAUDE.md not found — skipping")
        print()

        print("Ensuring .gitignore entries...")
        gi_stats = FileMerger.admin_ensure_gitignore(rbtv_dir)
        print(f"  Added: {gi_stats['added']}  |  Already present: {gi_stats['already_present']}  |  Migrated: {gi_stats['migrated']}")
        print()

        total_copied = (
            cfg_stats.get("copied", 0)
            + adm_stats.get("copied", 0)
        )
        total_replaced = (
            cfg_stats.get("replaced", 0)
            + adm_stats.get("replaced", 0)
        )
        print("-" * 60)
        print("Summary")
        print("-" * 60)
        print(f"  Files generated/copied:   {total_copied}")
        print(f"  Files replaced: {total_replaced}")
        print(f"  Admin user:     {values.get('user_name', 'N/A')}")
        print(f"  Language:       {values.get('communication_language', 'N/A')}")
        print()
        print("Next steps:")
        print("  1. Restart active IDEs to load new commands and rules")
        print("  2. Run /bmad-rbtv-help to verify tools work")
        print()
        print("Remember: re-run this script after every 'git pull'")
        return 0

import shutil
from bootstrap.context import BootstrapContext
from bootstrap.core.version_check import check_bmad_version, print_version_check_result
from bootstrap.fs.cleanup import FileCleaner
from bootstrap.fs.copy import FileCopier
from bootstrap.fs.replicate import FileReplicator
from bootstrap.fs.merge import FileMerger
from bootstrap.utils import print_errors, print_mcp_stats
from bootstrap.workflows.base import BootstrapWorkflow
from bootstrap.workflows.project import ProjectBootstrapper
from bootstrap.workflows.admin import AdminWorkflow

class WorkspaceWorkflow(BootstrapWorkflow):
    def run(self) -> int:
        root = self.ctx.root
        rbtv_dir = self.ctx.rbtv
        config_dir = self.ctx.config

        print(f"Source:      {rbtv_dir}")
        print(f"Destination: {root}")
        print()

        print("Checking BMAD version compatibility")
        if self.ctx.skip_version_check:
            print("  Skipped (--skip-version-check)")
        else:
            result = check_bmad_version(rbtv_dir, root)
            print_version_check_result(result)
        print()

        print("Deleting existing RBTV files (bmad-rbtv*)")
        del_stats = FileCleaner.workspace_delete_rbtv_files(root)
        print(f"  Deleted: {del_stats['deleted']} files")
        print_errors(del_stats.get("errors", []))
        print()

        total_copied = total_replaced = 0
        src = self.ctx.config_claude
        dst = root / ".claude"
        print("Installing RBTV to .claude/ (canonical source)")
        stats = FileCopier.copy_folder(src, dst, exclude_names={".mcp.json"})
        if "reason" in stats:
            print(f"  Skipped ({stats['reason']})")
        else:
            print(f"  Copied: {stats['copied']}  |  Replaced: {stats['replaced']}")
            print_errors(stats.get("errors", []))
            total_copied += stats.get("copied", 0)
            total_replaced += stats.get("replaced", 0)
        print()

        if "claude" in self.ctx.target_ides:
            print("Merging MCP configuration for Claude Code")
            mcp_stats_claude = FileMerger.merge_mcp_json(
                config_dir / ".claude" / ".mcp.json",
                root / ".claude" / ".mcp.json",
            )
            print_mcp_stats(mcp_stats_claude)
            print()

        if "cursor" in self.ctx.target_ides:
            print("Merging MCP configuration for Cursor")
            mcp_stats_cursor = FileMerger.merge_mcp_json(
                config_dir / ".claude" / ".mcp.json",
                root / ".cursor" / "mcp.json",
            )
            print_mcp_stats(mcp_stats_cursor)
            print()
            
        if "antigravity" in self.ctx.target_ides:
            print("Merging MCP configuration for Antigravity")
            mcp_stats_ag = FileMerger.merge_mcp_json(
                config_dir / ".claude" / ".mcp.json",
                root / ".agents" / "mcp.json",
            )
            print_mcp_stats(mcp_stats_ag)
            print()

        print("Normalizing BMAD output paths")
        norm_stats = FileMerger.normalize_bmad_output_paths(root)
        print(f"  Updated: {norm_stats['updated']} config files")
        print_errors(norm_stats.get("errors", []))
        print()

        print("Adding RBTV to BMAD help catalog")
        help_stats = FileMerger.add_rbtv_to_help_catalog(root)
        if help_stats.get("added", 0) > 0:
            print(f"  Added: {help_stats['added']} RBTV workflow(s)")
        elif help_stats.get("errors"):
            print_errors(help_stats["errors"])
        else:
            print("  Status: RBTV already in catalog")
        print()

        print("Checking .vscode/settings.json")
        vsc_stats = FileMerger.merge_vscode_settings(config_dir, root)
        if "reason" in vsc_stats:
            print(f"  Skipped ({vsc_stats['reason']})")
        elif vsc_stats.get("created"):
            print("  Created .vscode/settings.json")
        print_errors(vsc_stats.get("errors", []))
        print()

        print("Merging .cursorignore")
        ci_stats = FileMerger.merge_cursorignore(root)
        if ci_stats.get("added", 0) > 0:
            print(f"  Added: {ci_stats['added']} patterns")
        else:
            print(f"  Skipped: {ci_stats.get('skipped', 0)} patterns (already present)")
        print_errors(ci_stats.get("errors", []))
        print()

        print("Installing RBTV context for Fernando (build-rbtv-component)...")
        fernando_claude_src = rbtv_dir / "_admin" / "CLAUDE.md"
        fernando_claude_dst = rbtv_dir / "workflows" / "build-rbtv-component" / "data" / "CLAUDE.md"
        if fernando_claude_src.exists():
            shutil.copy2(str(fernando_claude_src), str(fernando_claude_dst))
            print("  Copied _admin/CLAUDE.md → agents/fernando/workflows/create-component/data/CLAUDE.md")
        else:
            print("  WARNING: _admin/CLAUDE.md not found — skipping")
        print()

        managed_prefixes = ["bmad-rbtv"]

        if self.ctx.skip_projects:
            print("Project bootstrap: skipped (--skip-projects)")
            print()
        else:
            print("=" * 60)
            print("Project Bootstrap")
            print("=" * 60)
            print()
            project_prefixes, proj_exit = ProjectBootstrapper.run_project_bootstrap(root)
            managed_prefixes.extend(project_prefixes)
            if proj_exit != 0:
                print()
                print("  Project bootstrap had errors — RBTV installation was successful")
            print()

        prefixes = tuple(managed_prefixes)
        
        for ide in self.ctx.target_ides:
            if ide == "claude":
                continue # Already built in-place natively
                
            print("=" * 60)
            print(f"Replicating to {ide.upper()}")
            print(f"  Managed prefixes: {', '.join(prefixes)}")
            print("=" * 60)
            print()

            print(f"Replicating commands to {ide}...")
            cmd_stats = FileReplicator.replicate_commands(root, prefixes, ide)
            if "reason" in cmd_stats:
                print(f"  Skipped ({cmd_stats['reason']})")
            else:
                print(f"  Copied: {cmd_stats['copied']}  |  Replaced: {cmd_stats['replaced']}")
                print_errors(cmd_stats.get("errors", []))
            print()

            print(f"Replicating rules to {ide}...")
            rule_stats = FileReplicator.replicate_rules(root, prefixes, ide)
            if "reason" in rule_stats:
                print(f"  Skipped ({rule_stats['reason']})")
            else:
                print(f"  Copied: {rule_stats['copied']}  |  Replaced: {rule_stats['replaced']}")
                print_errors(rule_stats.get("errors", []))
            print()

            print(f"Replicating agents to {ide}...")
            agent_stats = FileReplicator.replicate_agents(root, prefixes, ide)
            if "reason" in agent_stats:
                print(f"  Skipped ({agent_stats['reason']})")
            else:
                print(f"  Copied: {agent_stats['copied']}  |  Replaced: {agent_stats['replaced']}")
                print_errors(agent_stats.get("errors", []))
            print()

            print(f"Replicating skills to {ide}...")
            skill_stats = FileReplicator.replicate_skills(root, prefixes, ide)
            if "reason" in skill_stats:
                print(f"  Skipped ({skill_stats['reason']})")
            else:
                print(f"  Copied: {skill_stats['copied']}  |  Replaced: {skill_stats['replaced']}")
                print_errors(skill_stats.get("errors", []))
            print()

            print("-" * 60)
            print(f"Replication Summary for {ide.upper()}")
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
            
        if "claude" not in self.ctx.target_ides:
            # We generated .claude as a staging branch, but user didn't want it installed.
            # Clean up the exact bmad-rbtv files we just put there so we don't pollute.
            del_stats = FileCleaner.workspace_delete_rbtv_files(root)
            print(f"Cleaned up temporary staging files from .claude/")

        print("=" * 60)
        print("Installation complete.")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Restart your active IDEs to load new MCP servers and commands")
        print("  2. Run /bmad-help to see RBTV workflows in the catalog")
        print("  3. Run /help to see RBTV-specific commands")
        print()
        print("Remember: Run this script after every 'git pull' or 'git fetch'")
        print()

        try:
            answer = input("Run admin update as well? [y/N]: ").strip().lower()
            if answer in ("y", "yes"):
                print()
                print("=" * 60)
                print("Bootstrap — ADMIN mode")
                print("=" * 60)
                print()
                admin_wf = AdminWorkflow(self.ctx)
                return admin_wf.run()
        except EOFError:
            pass

        admin_wf = AdminWorkflow(self.ctx)
        if admin_wf.admin_is_installed():
            print()
            print("Admin artifacts detected in RBTV folder (.claude/, .cursor/, CLAUDE.md).")
            print("These consume context window when RBTV skills are invoked from the workspace.")
            try:
                answer = input("Uninstall admin artifacts? [y/N]: ").strip().lower()
                if answer in ("y", "yes"):
                    print()
                    print("=" * 60)
                    print("Uninstalling admin artifacts")
                    print("=" * 60)
                    print()
                    return admin_wf.run_uninstall()
            except EOFError:
                pass

        return 0

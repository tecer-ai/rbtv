import argparse
from bootstrap.context import BootstrapContext
from bootstrap.workflows.workspace import WorkspaceWorkflow
from bootstrap.workflows.admin import AdminWorkflow
from bootstrap.workflows.sync import SyncWorkflow

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
    parser.add_argument(
        "--ides",
        help="Target IDEs to install (comma separated: claude, cursor, antigravity). If omitted, prompt the user.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"BMAD Bootstrap — {args.mode.upper()} mode")
    print("=" * 60)
    print()

    if args.ides is None and args.mode in ("workspace", "admin"):
        try:
            print("Select target IDEs to install/update.")
            print("Options: claude, cursor, antigravity")
            ans = input("Enter comma separated list [claude,cursor]: ").strip().lower()
            if not ans:
                args.ides = "claude,cursor"
            else:
                args.ides = ans
        except EOFError:
            args.ides = "claude,cursor"
    elif args.ides is None:
        args.ides = "claude,cursor"

    ctx = BootstrapContext.resolve(args)

    if args.mode == "workspace":
        wf = WorkspaceWorkflow(ctx)
        return wf.run()
    elif args.mode == "admin":
        wf = AdminWorkflow(ctx)
        return wf.run()
    elif args.mode == "sync":
        wf = SyncWorkflow(ctx)
        return wf.run()

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

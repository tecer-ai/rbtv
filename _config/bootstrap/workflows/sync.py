from bootstrap.context import BootstrapContext
from bootstrap.core.version_check import check_bmad_version, print_version_check_result
from bootstrap.fs.merge import FileMerger
from bootstrap.utils import print_errors
from bootstrap.workflows.base import BootstrapWorkflow

class SyncWorkflow(BootstrapWorkflow):
    def run(self) -> int:
        """BMAD config patching only — no workspace artifacts."""
        root = self.ctx.root
        rbtv_dir = self.ctx.rbtv

        print(f"RBTV source: {rbtv_dir}")
        print(f"BMAD root:   {root}")
        print()

        print("Checking BMAD version compatibility")
        if self.ctx.skip_version_check:
            print("  Skipped (--skip-version-check)")
        else:
            result = check_bmad_version(rbtv_dir, root)
            print_version_check_result(result)
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

        print("-" * 60)
        print("Sync complete.")
        print()
        print("Next steps:")
        print("  1. Restart nanobot to pick up updated BMAD config")
        print("  2. Run tasks/check-bmad-compat.xml to verify compatibility")
        return 0

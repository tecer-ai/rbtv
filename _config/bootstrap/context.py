import argparse
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BootstrapContext:
    config: Path
    rbtv: Path
    root: Path
    config_claude: Path
    admin_claude: Path
    target_ides: list[str]
    skip_version_check: bool = False
    skip_projects: bool = False

    @classmethod
    def resolve(cls, args: argparse.Namespace) -> "BootstrapContext":
        """Resolve source and destination paths based on the script's location."""
        # _config/bootstrap/context.py -> script_dir is _config/
        script_dir = Path(__file__).parent.parent.resolve()
        rbtv_dir = script_dir.parent
        root = rbtv_dir.parent.parent
        
        target_ides_str = getattr(args, "ides", "claude,cursor")
        target_ides = [x.strip() for x in target_ides_str.split(",") if x.strip() in ("claude", "cursor", "antigravity")]
        
        return cls(
            config=script_dir,
            rbtv=rbtv_dir,
            root=root,
            config_claude=script_dir / "claude",
            admin_claude=rbtv_dir / "_admin" / "claude",
            target_ides=target_ides,
            skip_version_check=getattr(args, "skip_version_check", False),
            skip_projects=getattr(args, "skip_projects", False)
        )

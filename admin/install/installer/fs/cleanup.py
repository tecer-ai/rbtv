import shutil
from pathlib import Path
from bootstrap.core.constants import (
    ADMIN_MANAGED_PREFIXES,
    ADMIN_SEARCH_DIRS,
    ADMIN_EXTRA_MANAGED_FILES,
    WORKSPACE_RBTV_SEARCH_DIRS,
    PROTECTED_SUBDIRS
)
from bootstrap.fs.copy import is_protected_path

class FileCleaner:
    @staticmethod
    def admin_delete_managed_files(rbtv_dir: Path) -> dict:
        stats = {"deleted": 0, "errors": []}
        for rel_dir in ADMIN_SEARCH_DIRS:
            search_dir = rbtv_dir / rel_dir
            if not search_dir.exists():
                continue
            for file_path in search_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel_path = file_path.relative_to(search_dir)
                if is_protected_path(rel_path):
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

    @staticmethod
    def workspace_delete_rbtv_files(root: Path) -> dict:
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

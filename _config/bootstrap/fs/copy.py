import shutil
from pathlib import Path
from bootstrap.core.constants import PROTECTED_SUBDIRS

def is_protected_path(rel_path: Path) -> bool:
    """Check if a relative path falls under a protected subdirectory."""
    return any(part in PROTECTED_SUBDIRS for part in rel_path.parts)

def matches_prefix(name: str, prefixes: tuple) -> bool:
    """Check if a file or directory name starts with any of the given prefixes."""
    return any(name.startswith(p) for p in prefixes)

class FileCopier:
    @staticmethod
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
            if is_protected_path(rel_path) and dst_file.exists():
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
    
    @staticmethod
    def admin_should_transform(rel_path: Path) -> bool:
        if rel_path.parts[0] == "rules":
            return False
        if rel_path.name == "mcp.json":
            return False
        return True

    @staticmethod
    def admin_transform(content: str) -> str:
        from bootstrap.core.constants import ADMIN_PATH_FIND, ADMIN_PATH_REPLACE, ADMIN_REINFORCEMENT
        content = content.replace(ADMIN_PATH_FIND, ADMIN_PATH_REPLACE)
        return content.rstrip() + ADMIN_REINFORCEMENT

    @classmethod
    def admin_copy_folder(cls, src: Path, dst: Path, transform: bool = False) -> dict:
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
            if is_protected_path(rel_path) and dst_file.exists():
                stats["skipped"] += 1
                continue
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                existed = dst_file.exists()
                if transform and cls.admin_should_transform(rel_path):
                    content = src_file.read_text(encoding="utf-8")
                    dst_file.write_text(cls.admin_transform(content), encoding="utf-8")
                else:
                    shutil.copy2(str(src_file), str(dst_file))
                stats["replaced" if existed else "copied"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
        return stats

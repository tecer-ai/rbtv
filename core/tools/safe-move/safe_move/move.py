"""Git-aware file and folder move primitive."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from safe_move import scope
from safe_move.consult import compute_git_move_method


class MoveError(Exception):
    """Raised when a move cannot be performed safely."""


# Retry budget for removing the source after a cross-device copy. A Windows
# file-watcher (Obsidian/indexer) can briefly hold a handle that blocks deletion
# but not reading, so a short retry usually clears it; a persistent lock is then
# reported as a warning rather than aborting an already-complete move.
_RMTREE_RETRIES = 3
_RMTREE_BACKOFF_SECONDS = 0.1


def perform_move(src: Path, dst: Path, scope_root: Path) -> tuple[str, list[dict[str, Any]]]:
    """Move ``src`` to ``dst`` and return the method used plus warnings.

    Works for both single files and whole folders. Folders are moved as a
    single ``git mv`` when tracked within one repository, otherwise with a
    plain ``mv``. Nested git repositories inside the folder are surfaced as
    warnings and never folded into an outer ``git mv``.
    """
    src = Path(src).resolve()
    dst = Path(dst).resolve()
    scope_root = Path(scope_root).resolve()

    if not src.exists():
        raise MoveError(f"source does not exist: {src}")
    if dst.exists():
        raise MoveError(f"destination already exists: {dst}")

    method, warnings = compute_git_move_method(src, dst, scope_root)

    if src.is_dir():
        nested = nested_repos(src)
        if nested:
            warnings.append(
                {
                    "kind": "nested-repo",
                    "message": (
                        "folder contains nested git repository(s) that were not "
                        "folded into the outer move: "
                        + ", ".join(_display_path(p, scope_root) for p in nested)
                    ),
                    "file": _display_path(src, scope_root),
                    "ref_id": None,
                }
            )
            if method == "git mv":
                method = "mv"
                warnings.append(
                    {
                        "kind": "history-loss",
                        "message": (
                            "falling back to plain mv because the folder contains "
                            "a nested git repository"
                        ),
                        "file": _display_path(src, scope_root),
                        "ref_id": None,
                    }
                )

        index_hint = _index_file_hint(src, dst)
        if index_hint is not None:
            warnings.append(
                {
                    "kind": "index-cascade",
                    "message": (
                        "folder contains an index file that may need renaming "
                        "after the folder rename"
                    ),
                    "file": _display_path(index_hint, scope_root),
                    "ref_id": None,
                }
            )

    dst.parent.mkdir(parents=True, exist_ok=True)

    if method == "git mv":
        _git_mv(src, dst)
        if src.is_dir() and src.exists():
            _move_leftovers(src, dst, scope_root, warnings)
    elif method == "mv":
        _plain_move(src, dst, scope_root, warnings)
    else:
        raise MoveError(f"unknown move method: {method}")

    return method, warnings


def _git_mv(src: Path, dst: Path) -> None:
    repo = scope.git_toplevel(src.parent if src.is_file() else src)
    if repo is None:
        raise MoveError(f"source is not inside a git repository: {src}")
    try:
        src_arg = src.relative_to(repo).as_posix()
        dst_arg = dst.relative_to(repo).as_posix()
    except ValueError as exc:
        raise MoveError("git mv requires source and destination inside one repository") from exc

    result = subprocess.run(
        ["git", "mv", "--", src_arg, dst_arg],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise MoveError(f"git mv failed: {detail}")


def nested_repos(path: Path) -> list[Path]:
    """Return top-level paths of git repositories nested inside ``path``.

    The repository that owns ``path`` itself (if any) is excluded.
    """
    return _nested_repos(path)


def _nested_repos(path: Path) -> list[Path]:
    """Implementation detail for :func:`nested_repos`."""
    own_repo = scope.git_toplevel(path)
    own_git = (own_repo / ".git").resolve() if own_repo is not None else None
    nested: list[Path] = []
    for git_dir in path.rglob(".git"):
        if not git_dir.is_dir():
            continue
        if own_git is not None and git_dir.resolve() == own_git:
            continue
        top = scope.git_toplevel(git_dir.parent)
        nested.append(top if top is not None else git_dir.parent)
    return nested


def _index_file_hint(src: Path, dst: Path) -> Path | None:
    """Return the path of a likely index file inside ``src`` when renaming."""
    if src.name == dst.name:
        return None
    candidate = src / (src.name + ".md")
    return candidate if candidate.is_file() else None


def _move_leftovers(
    src: Path, dst: Path, scope_root: Path, warnings: list[dict[str, Any]]
) -> None:
    """After ``git mv``, move any remaining untracked files and clean up."""
    leftovers = [p for p in src.rglob("*") if p != src]
    if not leftovers:
        try:
            src.rmdir()
        except OSError:
            pass
        return

    moved: list[str] = []
    for item in leftovers:
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            warnings.append(
                {
                    "kind": "leftover-collision",
                    "message": f"leftover item could not be moved; target exists: {target.name}",
                    "file": _display_path(item, scope_root),
                    "ref_id": None,
                }
            )
            continue
        shutil.move(str(item), str(target))
        moved.append(_display_path(item, scope_root))

    warnings.append(
        {
            "kind": "leftover-moved",
            "message": (
                f"git mv left {len(moved)} untracked item(s) behind; "
                "moved them manually to the destination"
            ),
            "file": _display_path(src, scope_root),
            "ref_id": None,
        }
    )

    try:
        src.rmdir()
    except OSError:
        pass


def _plain_move(
    src: Path, dst: Path, scope_root: Path, warnings: list[dict[str, Any]]
) -> None:
    """Move ``src`` to ``dst`` without git, resilient to a locked source.

    Tries an atomic rename first (same filesystem — no partial state is possible).
    On a cross-device move or a rename failure, copies to ``dst`` FIRST so the
    destination is always complete, then removes the source with brief retries.
    If the source cannot be fully removed (typically a Windows file-watcher lock),
    the leftover paths are reported via a ``partial-source-cleanup`` warning and
    NOT raised: the move itself succeeded, only cleanup of the old tree is
    incomplete. This replaces a bare ``shutil.move`` whose ``rmtree`` phase could
    abort the move with a ``PermissionError`` traceback after ``dst`` was already
    populated, leaving a half-deleted source and a misleading exit-1.
    """
    try:
        os.replace(src, dst)
        return
    except OSError:
        # Cross-device rename, or a transient lock on the rename — fall back to
        # copy-then-remove so the destination is guaranteed complete first.
        pass

    if src.is_dir():
        shutil.copytree(src, dst)
        _remove_source_after_copy(src, scope_root, warnings, is_dir=True)
    else:
        shutil.copy2(src, dst)
        _remove_source_after_copy(src, scope_root, warnings, is_dir=False)


def _remove_source_after_copy(
    src: Path,
    scope_root: Path,
    warnings: list[dict[str, Any]],
    *,
    is_dir: bool,
) -> None:
    """Remove the copied-from source, retrying briefly through transient locks.

    On a persistent lock, append a clear ``partial-source-cleanup`` warning that
    names how many source paths remain — never raise (the destination is already
    complete).
    """
    for attempt in range(_RMTREE_RETRIES):
        try:
            if is_dir:
                shutil.rmtree(src)
            else:
                src.unlink()
            return
        except OSError:
            if attempt + 1 < _RMTREE_RETRIES:
                time.sleep(_RMTREE_BACKOFF_SECONDS)

    remaining = sum(1 for _ in src.rglob("*")) if src.is_dir() else 0
    if src.exists():
        remaining += 1
    warnings.append(
        {
            "kind": "partial-source-cleanup",
            "message": (
                "destination is complete, but the source could not be fully "
                f"removed (likely a file lock); {remaining} path(s) remain at "
                f"{_display_path(src, scope_root)} and must be deleted manually "
                "once the lock releases"
            ),
            "file": _display_path(src, scope_root),
            "ref_id": None,
        }
    )


def _display_path(path: Path, scope_root: Path) -> str:
    try:
        return path.relative_to(scope_root).as_posix()
    except ValueError:
        return path.as_posix()

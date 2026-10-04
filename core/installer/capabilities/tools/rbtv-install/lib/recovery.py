"""Shared recovery wording for installer refusals."""
from __future__ import annotations

import os
import shlex
from pathlib import Path

from .constants import REPO_ROOT


def shell_quote(value: object) -> str:
    text = str(value)
    if os.name == "nt":
        return "'" + text.replace("'", "''") + "'"
    return shlex.quote(text)


def source_tree_root(tree: object, target: object) -> Path:
    """Derive a component's current source root instead of booking a path."""
    if tree == "mirror":
        return Path(target) / ".rbtv" / "mirror"
    return REPO_ROOT


def vanished_component_message(cid: str, tree: object, target: object) -> str:
    tree_root = source_tree_root(tree, target)
    remove = "rbtv remove " + shell_quote(cid)
    remove += " --target " + shell_quote(target)
    return (
        f"component {cid!r} is recorded as installed but no longer exists under "
        f"{str(tree_root)!r} (renamed or deleted upstream). Every run at this "
        "target refuses until the book agrees with the trees. Recover with "
        f"EITHER: restore the folder; or `{remove}`, which "
        "needs no tree — the book holds its files"
    )

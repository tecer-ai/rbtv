"""Shared recovery wording for installer refusals."""
from __future__ import annotations

import os
import shlex


def shell_quote(value: object) -> str:
    text = str(value)
    if os.name == "nt":
        return "'" + text.replace("'", "''") + "'"
    return shlex.quote(text)


def vanished_component_message(cid: str, tree_root: object,
                              target: object | None = None) -> str:
    remove = "rbtv install remove " + shell_quote(cid)
    if target is not None:
        remove += " --target " + shell_quote(target)
    return (
        f"component {cid!r} is recorded as installed but no longer exists under "
        f"{str(tree_root)!r} (renamed or deleted upstream). Every run at this "
        "target refuses until the book agrees with the trees. Recover with "
        f"EITHER: restore the folder; or `{remove}`, which "
        "needs no tree — the book holds its files"
    )

"""The one way the installer replaces a file's content."""
from __future__ import annotations

from pathlib import Path


def write_file(path: Path, data: str | bytes, newline: str | None = None) -> None:
    """Replace `path`'s content, keeping the file (and its attributes) in place.

    An existing file is rewritten through "r+" and truncated, never re-created
    through "w": Windows refuses to re-create a Hidden or System file
    (ACCESS_DENIED, surfacing as a misleading PermissionError) even under Full
    Control — observed on a hidden `.git/info/exclude`.
    """
    binary = isinstance(data, bytes)
    mode = ("r+" if path.is_file() else "w") + ("b" if binary else "")
    kw = {} if binary else {"encoding": "utf-8", "newline": newline}
    with open(path, mode, **kw) as f:
        f.write(data)
        f.truncate()

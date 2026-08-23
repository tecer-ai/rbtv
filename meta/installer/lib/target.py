"""Finding the install root when no --target was given."""
from __future__ import annotations

from pathlib import Path

from .constants import STATE_REL


DISCOVER_STATE = "state file"

DISCOVER_RBTV = ".rbtv/ directory"

DISCOVER_CWD = "cwd (no .rbtv/ found above)"

DISCOVER_FLAG = "--target"


def discover_target(start: Path) -> tuple[Path, str]:
    """Resolve the install root from `start` upward. Returns (root, why)."""
    here = start.resolve()
    chain = [here, *here.parents]
    for cand in chain:
        if (cand / STATE_REL).is_file():
            return cand, DISCOVER_STATE
    for cand in chain:
        if (cand / ".rbtv").is_dir():
            return cand, DISCOVER_RBTV
    return here, DISCOVER_CWD

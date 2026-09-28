"""Applies the red arm named in `$M7_MUTATION` before any probe runs."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import mutations  # noqa: E402

mutations.apply_from_env()

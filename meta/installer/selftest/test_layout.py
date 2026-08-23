"""The package's own shape: the repo root is still where the code counts it."""
from __future__ import annotations

from lib.constants import REPO_ROOT


def repo_root_is_the_repo(ctx) -> None:
    """D1's hazard, made loud.

    `REPO_ROOT` is a hardcoded number of directories above `lib/constants.py`.
    Move that file, or the package, without changing the number and every tree
    scan silently returns an empty catalog — a wrong answer, not an error. The
    expectations below are spelled out as literals on purpose: a check that
    re-derived them from `__file__` would move with the code and pass any
    change to it.
    """
    check = ctx.check
    check("D1 — REPO_ROOT holds the repo, not a folder inside it",
          (REPO_ROOT / "meta" / "installer" / "install.py").is_file()
          and (REPO_ROOT / "meta" / "installer" / "lib"
               / "constants.py").is_file()
          and (REPO_ROOT / "core").is_dir(),
          f"REPO_ROOT={REPO_ROOT}")
    check("D1 — the repo root is not the component folder",
          REPO_ROOT.name != "installer" and REPO_ROOT.name != "lib",
          f"REPO_ROOT={REPO_ROOT}")

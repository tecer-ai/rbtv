"""Consult disclosure for folder targets that contain a nested git repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from safe_move.consult import build_consult_result


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _all_files(path: Path) -> list[str]:
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file())


def test_consult_warns_and_excludes_nested_repo_contents(repo_builder):
    """A folder containing a nested git repo must:

    - emit a ``nested-repo`` warning,
    - exclude the nested repo's ``.git/`` and tracked files from
      ``folder_cascade.moved_files``,
    - fall back from ``git mv`` to ``mv`` and warn about history loss,
      matching the ``act``-side disclosure.
    """
    files = {
        "outer/old/tracked.txt": "outer tracked\n",
        "outer/old/regular.txt": "outer regular\n",
    }
    fix = repo_builder("consult-nested-repo", files, tracked=list(files))

    nested = fix.repo / "outer" / "old" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "inner.txt").write_text("inner\n", encoding="utf-8")
    _git(nested, "init")
    _git(nested, "config", "user.email", "test@example.com")
    _git(nested, "config", "user.name", "Test User")
    _git(nested, "add", "inner.txt")
    _git(nested, "commit", "-m", "nested seed")

    result = build_consult_result(
        "outer/old",
        "outer/new",
        scope_root=fix.repo,
    )

    # The outer folder is tracked in its repo, but the nested repo forces mv.
    assert result["git_move_method"] == "mv"

    warnings_by_kind = {w["kind"]: w for w in result["warnings"]}
    assert "nested-repo" in warnings_by_kind
    nested_warning = warnings_by_kind["nested-repo"]
    assert nested_warning["file"] == "outer/old"
    assert "nested" in nested_warning["message"]
    assert "history-loss" in warnings_by_kind

    # moved_files lists only the files the outer move will actually relocate.
    moved_files = result["folder_cascade"]["moved_files"]
    assert "outer/old/tracked.txt" in moved_files
    assert "outer/old/regular.txt" in moved_files
    assert "outer/old/nested/inner.txt" not in moved_files
    assert not any(".git" in p for p in moved_files)
    assert not any(p.startswith("outer/old/nested/") for p in moved_files)

    # Sanity: the nested repo really exists on disk.
    assert (nested / ".git").is_dir()
    assert (nested / "inner.txt").is_file()
    assert "inner.txt" in [p for p in _all_files(nested) if not p.startswith(".git/")]

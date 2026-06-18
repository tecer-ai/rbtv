"""Tests for the folder-aware extension of the git-aware move primitive."""

from __future__ import annotations

import subprocess

import pytest

from safe_move.move import MoveError, perform_move


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _all_files(path: Path):
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file())


from pathlib import Path


def test_tracked_folder_uses_git_mv_and_moves_whole_tree(repo_builder):
    files = {
        "docs/old/a.txt": "a\n",
        "docs/old/sub/b.txt": "b\n",
        "docs/old/sub/deep/c.txt": "c\n",
    }
    fix = repo_builder("move-folder-tracked", files, tracked=list(files.keys()))

    method, warnings = perform_move(
        fix.repo / "docs" / "old",
        fix.repo / "docs" / "new",
        fix.repo,
    )

    assert method == "git mv"
    assert not (fix.repo / "docs" / "old").exists()
    assert _all_files(fix.repo / "docs" / "new") == [
        "a.txt",
        "sub/b.txt",
        "sub/deep/c.txt",
    ]
    assert (fix.repo / "docs" / "new" / "a.txt").read_text(encoding="utf-8") == "a\n"

    _git(fix.repo, "commit", "-m", "move tracked folder")
    log = _git(
        fix.repo, "log", "--follow", "--format=%s", "--", "docs/new/a.txt"
    ).stdout
    assert "move tracked folder" in log
    assert "seed fixture" in log


def test_untracked_folder_uses_plain_mv(repo_builder):
    files = {
        "docs/old/a.txt": "a\n",
        "docs/old/sub/b.txt": "b\n",
    }
    fix = repo_builder("move-folder-untracked", files)

    method, warnings = perform_move(
        fix.repo / "docs" / "old",
        fix.repo / "docs" / "new",
        fix.repo,
    )

    assert method == "mv"
    assert not (fix.repo / "docs" / "old").exists()
    assert _all_files(fix.repo / "docs" / "new") == ["a.txt", "sub/b.txt"]


def test_mixed_tracked_untracked_folder_leaves_no_file_behind(repo_builder):
    files = {
        "docs/old/tracked.txt": "tracked\n",
        "docs/old/untracked.txt": "untracked\n",
        "docs/old/sub/also.txt": "also\n",
    }
    fix = repo_builder(
        "move-folder-mixed",
        files,
        tracked=["docs/old/tracked.txt", "docs/old/sub/also.txt"],
    )

    method, warnings = perform_move(
        fix.repo / "docs" / "old",
        fix.repo / "docs" / "new",
        fix.repo,
    )

    assert method == "git mv"
    assert not (fix.repo / "docs" / "old").exists()
    assert set(_all_files(fix.repo / "docs" / "new")) == {
        "tracked.txt",
        "untracked.txt",
        "sub/also.txt",
    }


def test_nested_repo_inside_folder_is_surfaced_not_folded(repo_builder):
    files = {
        "outer/old/tracked.txt": "outer\n",
    }
    fix = repo_builder("move-folder-nested", files, tracked=["outer/old/tracked.txt"])
    nested = fix.repo / "outer" / "old" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "inner.txt").write_text("inner\n", encoding="utf-8")
    _git(nested, "init")
    _git(nested, "config", "user.email", "test@example.com")
    _git(nested, "config", "user.name", "Test User")
    _git(nested, "add", "inner.txt")
    _git(nested, "commit", "-m", "nested seed")

    method, warnings = perform_move(
        fix.repo / "outer" / "old",
        fix.repo / "outer" / "new",
        fix.repo,
    )

    assert method == "mv"
    kinds = {w["kind"] for w in warnings}
    assert "nested-repo" in kinds
    assert "history-loss" in kinds

    assert not (fix.repo / "outer" / "old").exists()
    assert (fix.repo / "outer" / "new" / "tracked.txt").read_text(encoding="utf-8") == "outer\n"
    assert (fix.repo / "outer" / "new" / "nested" / "inner.txt").read_text(
        encoding="utf-8"
    ) == "inner\n"

    # The nested repo remains a real git repository after the move.
    nested_after = fix.repo / "outer" / "new" / "nested"
    assert (nested_after / ".git").is_dir()
    log = _git(nested_after, "log", "--format=%s").stdout
    assert "nested seed" in log


def test_destination_exists_folder_is_refused_without_moving_source(repo_builder):
    files = {
        "docs/old/a.txt": "a\n",
        "docs/existing/b.txt": "b\n",
    }
    fix = repo_builder(
        "move-folder-destination-exists",
        files,
        tracked=["docs/old/a.txt", "docs/existing/b.txt"],
    )

    with pytest.raises(MoveError, match="destination already exists"):
        perform_move(
            fix.repo / "docs" / "old",
            fix.repo / "docs" / "existing",
            fix.repo,
        )

    assert (fix.repo / "docs" / "old" / "a.txt").read_text(encoding="utf-8") == "a\n"
    assert (fix.repo / "docs" / "existing" / "b.txt").read_text(encoding="utf-8") == "b\n"


def test_empty_folder_move_is_valid(repo_builder):
    fix = repo_builder("move-folder-empty", {"docs/old/.keep": ""})
    # Remove the placeholder so the folder is really empty.
    (fix.repo / "docs" / "old" / ".keep").unlink()

    method, warnings = perform_move(
        fix.repo / "docs" / "old",
        fix.repo / "docs" / "new",
        fix.repo,
    )

    assert method == "mv"
    assert not (fix.repo / "docs" / "old").exists()
    assert (fix.repo / "docs" / "new").is_dir()
    assert _all_files(fix.repo / "docs" / "new") == []


def test_folder_rename_with_index_file_warns(repo_builder):
    files = {
        "notes/notes.md": "# Notes\n",
        "notes/other.md": "other\n",
    }
    fix = repo_builder("move-folder-index", files)

    method, warnings = perform_move(
        fix.repo / "notes",
        fix.repo / "journal",
        fix.repo,
    )

    assert method == "mv"
    assert any(w["kind"] == "index-cascade" for w in warnings)
    assert not (fix.repo / "notes").exists()
    assert (fix.repo / "journal" / "notes.md").read_text(encoding="utf-8") == "# Notes\n"

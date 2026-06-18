"""Tests for the git-aware move primitive."""

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


def test_tracked_same_repo_move_uses_git_mv_and_preserves_follow_history(repo_builder):
    fix = repo_builder(
        "move-tracked",
        {"docs/old.md": "old\n"},
        tracked=["docs/old.md"],
    )

    method, warnings = perform_move(
        fix.repo / "docs" / "old.md",
        fix.repo / "renamed" / "new.md",
        fix.repo,
    )

    assert method == "git mv"
    assert warnings == []
    assert not (fix.repo / "docs" / "old.md").exists()
    assert (fix.repo / "renamed" / "new.md").read_text(encoding="utf-8") == "old\n"

    _git(fix.repo, "commit", "-m", "move tracked file")
    log = _git(fix.repo, "log", "--follow", "--format=%s", "--", "renamed/new.md").stdout
    assert "move tracked file" in log
    assert "seed fixture" in log


def test_untracked_same_repo_move_uses_plain_mv(repo_builder):
    fix = repo_builder("move-untracked", {"docs/old.md": "old\n"})

    method, warnings = perform_move(
        fix.repo / "docs" / "old.md",
        fix.repo / "new" / "old.md",
        fix.repo,
    )

    assert method == "mv"
    assert warnings == []
    assert not (fix.repo / "docs" / "old.md").exists()
    assert (fix.repo / "new" / "old.md").read_text(encoding="utf-8") == "old\n"


def test_cross_repo_move_uses_plain_mv_and_warns_history_loss(repo_builder):
    source = repo_builder("move-source-repo", {"docs/old.md": "old\n"}, tracked=["docs/old.md"])
    dest = repo_builder("move-dest-repo", {"keep.md": "keep\n"}, tracked=["keep.md"])

    method, warnings = perform_move(
        source.repo / "docs" / "old.md",
        dest.repo / "incoming" / "old.md",
        source.repo,
    )

    assert method == "mv"
    assert [warning["kind"] for warning in warnings] == ["history-loss"]
    assert "history does not follow" in warnings[0]["message"]
    assert not (source.repo / "docs" / "old.md").exists()
    assert (dest.repo / "incoming" / "old.md").read_text(encoding="utf-8") == "old\n"


def test_destination_exists_is_refused_without_moving_source(repo_builder):
    fix = repo_builder(
        "move-destination-exists",
        {
            "docs/old.md": "old\n",
            "docs/existing.md": "existing\n",
        },
        tracked=["docs/old.md", "docs/existing.md"],
    )

    with pytest.raises(MoveError, match="destination already exists"):
        perform_move(
            fix.repo / "docs" / "old.md",
            fix.repo / "docs" / "existing.md",
            fix.repo,
        )

    assert (fix.repo / "docs" / "old.md").read_text(encoding="utf-8") == "old\n"
    assert (fix.repo / "docs" / "existing.md").read_text(encoding="utf-8") == "existing\n"

"""Pytest fixtures for the safe_move Tier-1 synthetic harness."""

import subprocess
from pathlib import Path

import pytest

from tests.harness import RepoFixture, snapshot


@pytest.fixture
def repo_builder(tmp_path):
    """Return a factory that builds a fresh git repo fixture from a case dict.

    The factory accepts:
        name: temp folder name for the repo
        files: dict of ``{relative_path: content}``
        tracked: optional list of paths to ``git add`` and ``git commit``

    Returns a ``RepoFixture`` with the repo path and the pre-change file
    snapshots, so later phases can compare exact before/after states.
    """

    def _make(name: str, files: dict[str, str], tracked: list[str] | None = None) -> RepoFixture:
        repo = tmp_path / name
        repo.mkdir(parents=True, exist_ok=False)

        for relpath, content in files.items():
            path = repo / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

        if tracked:
            subprocess.run(["git", "add"] + tracked, cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "seed fixture"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

        return RepoFixture(repo, snapshot(repo, list(files.keys())))

    return _make

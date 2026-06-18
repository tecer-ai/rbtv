"""Tier-1 synthetic-fixture harness helpers."""

from pathlib import Path


class RepoFixture:
    """A tiny synthetic repo plus its original file snapshots."""

    def __init__(self, repo: Path, before: dict[str, str]):
        self.repo = repo
        self.before = before


def snapshot(repo: Path, paths: list[str]) -> dict[str, str]:
    """Return a snapshot dict of the current content of ``paths`` under ``repo``."""
    return {p: (repo / p).read_text(encoding="utf-8") for p in paths}


def assert_untouched(repo: Path, paths: list[str], before: dict[str, str]) -> None:
    """Fail if any of ``paths`` under ``repo`` differs from ``before``.

    This is the generic "must-not-touch" assertion helper used by Tier-1
    fixtures: protected regions (transcripts, logs, quotes, excluded files,
    read-only areas, cross-repo references, generated files) must remain
    byte-identical after ``consult`` / ``act``.
    """
    for p in paths:
        after = (repo / p).read_text(encoding="utf-8")
        assert after == before[p], f"Protected file {p!r} was modified after act"

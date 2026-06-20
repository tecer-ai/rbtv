"""Tests for gitignore-aware scope walking."""

from safe_move.scope import iter_subtree_text_files, walk_scope


def _paths(walked) -> set[str]:
    return {w.path for w in walked}


def test_walk_scope_skips_gitignored_directory(repo_builder):
    fx = repo_builder(
        "gitignored_directory",
        {
            ".gitignore": ".venv-marker/\n",
            "notes/ref.md": "See old/path.md\n",
            ".venv-marker/one.md": "ignored old/path.md\n",
            ".venv-marker/nested/two.md": "ignored old/path.md\n",
        },
        tracked=[".gitignore", "notes/ref.md"],
    )

    paths = _paths(list(walk_scope(fx.repo)))

    assert "notes/ref.md" in paths
    assert not any(path.startswith(".venv-marker/") for path in paths)


def test_walk_scope_does_not_skip_unignored_directory(repo_builder):
    fx = repo_builder(
        "unignored_directory",
        {
            "notes/ref.md": "See old/path.md\n",
            ".venv-marker/one.md": "not ignored old/path.md\n",
            ".venv-marker/nested/two.md": "not ignored old/path.md\n",
        },
        tracked=["notes/ref.md"],
    )

    paths = _paths(list(walk_scope(fx.repo)))

    assert "notes/ref.md" in paths
    assert ".venv-marker/one.md" in paths
    assert ".venv-marker/nested/two.md" in paths


def test_walk_scope_outside_git_repo_does_not_filter_or_crash(tmp_path):
    root = tmp_path / "not-git"
    (root / ".venv-marker" / "nested").mkdir(parents=True)
    (root / "notes").mkdir()
    (root / "notes" / "ref.md").write_text("See old/path.md\n", encoding="utf-8")
    (root / ".venv-marker" / "one.md").write_text(
        "not ignored old/path.md\n",
        encoding="utf-8",
    )
    (root / ".venv-marker" / "nested" / "two.md").write_text(
        "not ignored old/path.md\n",
        encoding="utf-8",
    )

    paths = _paths(list(walk_scope(root)))

    assert "notes/ref.md" in paths
    assert ".venv-marker/one.md" in paths
    assert ".venv-marker/nested/two.md" in paths


def test_iter_subtree_text_files_skips_gitignored_directory(repo_builder):
    fx = repo_builder(
        "gitignored_subtree_directory",
        {
            ".gitignore": "moved/.venv-marker/\n",
            "moved/ref.md": "See moved/target.md\n",
            "moved/.venv-marker/one.md": "ignored moved/target.md\n",
            "moved/.venv-marker/nested/two.md": "ignored moved/target.md\n",
        },
        tracked=[".gitignore", "moved/ref.md"],
    )

    paths = _paths(list(iter_subtree_text_files(fx.repo / "moved", fx.repo)))

    assert "moved/ref.md" in paths
    assert not any(path.startswith("moved/.venv-marker/") for path in paths)

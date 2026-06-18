"""Tests for the scope layer: root resolution and file walking."""

import subprocess
from pathlib import Path

import pytest

from safe_move.scope import ScopeError, WalkedFile, resolve_scope_root, walk_scope


def _paths(walked: list[WalkedFile]) -> set[str]:
    return {w.path for w in walked}


def test_resolve_scope_root_from_git_toplevel(repo_builder):
    """Root resolves from the git top level of old."""
    fx = repo_builder(
        "root_from_git",
        {
            "src/old.md": "# Old\n",
            "README.md": "See src/old.md\n",
        },
        tracked=["src/old.md", "README.md"],
    )
    old = fx.repo / "src" / "old.md"
    assert resolve_scope_root(old) == fx.repo.resolve()


def test_resolve_scope_root_override_wins(repo_builder, tmp_path):
    """A provided scope-root override beats the git top level."""
    fx = repo_builder(
        "root_override",
        {
            "src/old.md": "# Old\n",
        },
        tracked=["src/old.md"],
    )
    override = tmp_path / "other-root"
    override.mkdir()
    (override / "file.md").write_text("x\n", encoding="utf-8")
    assert resolve_scope_root(fx.repo / "src" / "old.md", override) == override.resolve()


def test_resolve_scope_root_errors_when_not_in_git(tmp_path, monkeypatch):
    """old outside any git repo and no override asks for scope-root."""
    import safe_move.scope as scope_module

    monkeypatch.setattr(scope_module, "git_toplevel", lambda _cwd: None)
    old = tmp_path / "orphan.md"
    old.write_text("x\n", encoding="utf-8")
    with pytest.raises(ScopeError) as excinfo:
        resolve_scope_root(old)
    message = str(excinfo.value).lower()
    assert "not inside a git repository" in message
    assert "--scope-root" in message


def test_resolve_scope_root_errors_when_override_missing(tmp_path):
    """A non-existent scope-root produces a clear error."""
    old = tmp_path / "old.md"
    old.write_text("x\n", encoding="utf-8")
    with pytest.raises(ScopeError) as excinfo:
        resolve_scope_root(old, tmp_path / "missing")
    assert "does not exist" in str(excinfo.value).lower()


def test_walk_skips_git_deps_binary_and_lockfiles(repo_builder):
    """git, dependency/build dirs, binaries, and lockfiles are skipped."""
    fx = repo_builder(
        "skip_ignored",
        {
            "src/text.md": "hello\n",
            "node_modules/pkg/readme.md": "npm\n",
            "__pycache__/mod.cpython-312.pyc": "pyc\n",
            "dist/bundle.js": "bundle\n",
            "build/output.md": "build\n",
            "target/release/app": "rust\n",
            "binary.dat": b"hello\x00world".decode("latin-1"),
            "plain.lock": "{}\n",
            "deps/package-lock.json": "{}\n",
        },
    )
    walked = list(walk_scope(fx.repo))
    paths = _paths(walked)
    assert "src/text.md" in paths
    assert not any(p.startswith("node_modules/") for p in paths)
    assert not any("__pycache__" in p for p in paths)
    assert not any(p.startswith("dist/") for p in paths)
    assert not any(p.startswith("build/") for p in paths)
    assert not any(p.startswith("target/") for p in paths)
    assert "binary.dat" not in paths
    assert "plain.lock" in paths  # generic *.lock is not auto-skipped
    assert "deps/package-lock.json" not in paths


def test_walk_excludes_skipped_unless_include_archive(repo_builder):
    """Excluded paths are skipped unless include-archive is set."""
    fx = repo_builder(
        "exclude_archive",
        {
            "archive/old.md": "archived\n",
            "docs/readme.md": "docs\n",
        },
    )
    skipped = list(walk_scope(fx.repo, exclude=["archive"]))
    assert _paths(skipped) == {"docs/readme.md"}

    included = list(
        walk_scope(fx.repo, exclude=["archive"], include_archive=True)
    )
    assert _paths(included) == {"archive/old.md", "docs/readme.md"}


def test_walk_tags_nested_repo_as_boundary(repo_builder):
    """Files inside a nested git repo carry that repo top-level as boundary."""
    fx = repo_builder(
        "nested_repo",
        {
            "main.md": "hello\n",
            "sub/README.md": "nested\n",
        },
        tracked=["main.md"],
    )
    sub = fx.repo / "sub"
    subprocess.run(["git", "init"], cwd=sub, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=sub, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=sub, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=sub, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=sub,
        check=True,
        capture_output=True,
    )

    walked = list(walk_scope(fx.repo))
    by_path = {w.path: w for w in walked}
    assert "main.md" in by_path
    assert "sub/README.md" in by_path
    assert by_path["main.md"].boundary is None
    assert by_path["sub/README.md"].boundary == sub.resolve()


def test_walk_tags_read_only_and_generated(repo_builder):
    """Read-only and generated globs are tagged on matching files."""
    fx = repo_builder(
        "tagged",
        {
            "normal.md": "n\n",
            "protected/secret.md": "s\n",
            "generated.txt": "g\n",
        },
    )
    walked = list(
        walk_scope(
            fx.repo,
            read_only=["protected"],
            generated=["generated.txt"],
        )
    )
    by_path = {w.path: w for w in walked}
    assert by_path["normal.md"].read_only is False
    assert by_path["normal.md"].generated is False
    assert by_path["protected/secret.md"].read_only is True
    assert by_path["protected/secret.md"].generated is False
    assert by_path["generated.txt"].read_only is False
    assert by_path["generated.txt"].generated is True


def test_walk_scope_root_override_limits_walk(repo_builder, tmp_path):
    """Walking an overridden scope root only sees files under that root."""
    fx = repo_builder(
        "override_walk",
        {
            "a/b.md": "b\n",
            "a/c.md": "c\n",
            "d.md": "d\n",
        },
    )
    walked = list(walk_scope(fx.repo / "a"))
    assert _paths(walked) == {"b.md", "c.md"}


def test_walk_collects_unreadable_warning(repo_builder):
    """An unreadable file is skipped and produces a warning instead of crashing."""
    fx = repo_builder(
        "unreadable",
        {
            "readable.md": "ok\n",
            "locked.md": "secret\n",
        },
    )
    import safe_move.scope as scope_module

    original_is_binary = scope_module.is_binary

    def fake_is_binary(path: Path, chunk_size: int = 8192) -> bool:
        if path.name == "locked.md":
            raise PermissionError(13, "Access is denied", str(path))
        return original_is_binary(path, chunk_size)

    scope_module.is_binary = fake_is_binary
    try:
        warnings: list = []
        walked = list(walk_scope(fx.repo, warnings=warnings))
        assert _paths(walked) == {"readable.md"}
        assert len(warnings) == 1
        assert warnings[0].kind == "unreadable"
        assert "locked.md" in (warnings[0].file or "")
    finally:
        scope_module.is_binary = original_is_binary


def test_walk_cli_invocation_from_tool_directory(repo_builder):
    """The scope layer is importable and usable from the package context."""
    fx = repo_builder(
        "cli_smoke",
        {
            "x.md": "x\n",
        },
    )
    walked = list(walk_scope(fx.repo))
    assert len(walked) == 1
    assert walked[0].path == "x.md"

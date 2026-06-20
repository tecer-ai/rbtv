"""Tests for builder_api theme + repo-root-relative library-ref passthrough."""

import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

# Ensure studio/hypresent is importable regardless of invocation cwd.
_TEST_ROOT = pathlib.Path(__file__).resolve().parent
_HYPRESENT_ROOT = _TEST_ROOT.parent
if str(_HYPRESENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_HYPRESENT_ROOT))

from server.builder_api import _library_ref, _repo_root, handle_assemble

_RBTV_ROOT = _HYPRESENT_ROOT.parents[1]  # studio/hypresent -> studio -> rbtv
FIXTURE_LIBRARY = _RBTV_ROOT / "studio" / "slide-library" / "tests" / "fixture-library"
ENGINE_SRC = _RBTV_ROOT / "studio" / "slide-library" / "engine" / "assemble.py"
SHARED_BRAND = _RBTV_ROOT / "studio" / "slide-library" / "tests" / "shared-brand"


def _prepare_temp_library(tmp_path):
    """Create a temp git repo with a copy of fixture-library + engine + shared-brand."""
    repo = tmp_path / "git-repo"
    repo.mkdir()

    # Initialize a git repo so .git exists.
    subprocess.run(
        ["git", "init", str(repo)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    lib = repo / "fixture-library"
    shutil.copytree(FIXTURE_LIBRARY, lib)
    shutil.copy2(ENGINE_SRC, lib / "assemble.py")

    # extra_asset_root in fixture library.json is "../shared-brand".
    shared = repo / "shared-brand"
    shutil.copytree(SHARED_BRAND, shared)

    return repo, lib


# ---------------------------------------------------------------------------
# _repo_root
# ---------------------------------------------------------------------------


def test_repo_root_finds_git_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert _repo_root(str(nested)) == str(repo.resolve())


def test_repo_root_finds_git_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /elsewhere", encoding="utf-8")
    assert _repo_root(str(repo / "deck.html")) == str(repo.resolve())


def test_repo_root_no_git(tmp_path, monkeypatch):
    # This machine's user profile sits inside a git repo, so mask .git entries
    # to exercise the "no .git ancestor" branch deterministically.
    real_exists = os.path.exists

    def hide_git_exists(path):
        norm = str(path).replace("\\", "/")
        if norm.rstrip("/").endswith(".git") or "/.git/" in norm + "/":
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", hide_git_exists)
    no_git = tmp_path / "no-git"
    no_git.mkdir()
    nested = no_git / "a" / "b"
    nested.mkdir(parents=True)
    assert _repo_root(str(nested)) is None


# ---------------------------------------------------------------------------
# _library_ref
# ---------------------------------------------------------------------------


def test_library_ref_under_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    lib = repo / "libs" / "mylib"
    lib.mkdir(parents=True)
    out = repo / "decks" / "deck.html"
    out.parent.mkdir(parents=True)
    assert _library_ref(str(lib), str(out)) == "libs/mylib"


def test_library_ref_at_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    lib = repo / "mylib"
    lib.mkdir()
    out = repo / "deck.html"
    assert _library_ref(str(lib), str(out)) == "mylib"


def test_library_ref_outside_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    lib = tmp_path / "other" / "mylib"
    lib.mkdir(parents=True)
    out = repo / "deck.html"
    assert _library_ref(str(lib), str(out)) == ""


def test_library_ref_no_repo(tmp_path, monkeypatch):
    # Mask .git so the temp dir tree looks repo-free.
    real_exists = os.path.exists

    def hide_git_exists(path):
        norm = str(path).replace("\\", "/")
        if norm.rstrip("/").endswith(".git") or "/.git/" in norm + "/":
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", hide_git_exists)
    lib = tmp_path / "mylib"
    lib.mkdir()
    out = tmp_path / "deck.html"
    assert _library_ref(str(lib), str(out)) == ""


# ---------------------------------------------------------------------------
# handle_assemble passthrough
# ---------------------------------------------------------------------------


def test_handle_assemble_passthrough_theme_and_library_ref(tmp_path):
    repo, lib = _prepare_temp_library(tmp_path)
    out = repo / "deck.html"
    client_logo = lib / "assets" / "nimbus-mark.png"

    status, resp = handle_assemble(
        {
            "path": str(lib),
            "slides": ["cover-nimbus.en", "intro-pillars", "closing-nimbus"],
            "out": str(out),
            "theme": "graphite",
            "client_logo": str(client_logo),
        }
    )

    assert status == 200
    assert resp["ok"] is True
    assert out.exists()

    html = out.read_text(encoding="utf-8")
    assert 'data-theme="graphite"' in html

    match = re.search(r'data-theme-library="([^"]*)"', html)
    assert match is not None, "data-theme-library attribute missing"
    ref = match.group(1)
    assert ref, "data-theme-library is empty"
    assert ref == "fixture-library"


def test_handle_assemble_no_theme_omits_theme_flag(tmp_path):
    repo, lib = _prepare_temp_library(tmp_path)
    out = repo / "deck.html"

    status, resp = handle_assemble(
        {
            "path": str(lib),
            "slides": ["intro-pillars"],
            "out": str(out),
        }
    )

    assert status == 200
    assert resp["ok"] is True
    html = out.read_text(encoding="utf-8")
    # Default theme is "default" (theme.css).
    assert 'data-theme="default"' in html
    assert 'data-theme-library="fixture-library"' in html


def test_handle_assemble_non_repo_out_has_empty_library_ref(tmp_path, monkeypatch):
    # Library outside a git repo: ref stays empty but assembly still works.
    # Mask .git so the temp dir tree looks repo-free.
    real_exists = os.path.exists

    def hide_git_exists(path):
        norm = str(path).replace("\\", "/")
        if norm.rstrip("/").endswith(".git") or "/.git/" in norm + "/":
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", hide_git_exists)

    lib = tmp_path / "fixture-library"
    shutil.copytree(FIXTURE_LIBRARY, lib)
    shutil.copy2(ENGINE_SRC, lib / "assemble.py")
    shared = tmp_path / "shared-brand"
    shutil.copytree(SHARED_BRAND, shared)

    out = tmp_path / "deck.html"
    status, resp = handle_assemble(
        {
            "path": str(lib),
            "slides": ["intro-pillars"],
            "out": str(out),
            "theme": "graphite",
        }
    )

    assert status == 200
    assert resp["ok"] is True
    html = out.read_text(encoding="utf-8")
    assert 'data-theme="graphite"' in html
    assert 'data-theme-library=""' in html

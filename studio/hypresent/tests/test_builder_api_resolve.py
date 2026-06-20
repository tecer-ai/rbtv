"""Tests for /api/resolve-library and /api/copy-theme-assets handlers."""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

# Ensure studio/hypresent is importable regardless of invocation cwd.
_TEST_ROOT = pathlib.Path(__file__).resolve().parent
_HYPRESENT_ROOT = _TEST_ROOT.parent
if str(_HYPRESENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_HYPRESENT_ROOT))

from server.builder_api import handle_copy_theme_assets, handle_resolve_library


def _hide_git_exists(real_exists):
    """Factory for monkeypatching os.path.exists to hide .git entries."""

    def hide(path):
        norm = str(path).replace("\\", "/")
        if norm.rstrip("/").endswith(".git") or "/.git/" in norm + "/":
            return False
        return real_exists(path)

    return hide


def _make_repo_with_library(tmp_path):
    """Create a temp git repo with a library and a deck directory."""
    repo = tmp_path / "git-repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", str(repo)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    lib = repo / "lib"
    lib.mkdir()
    library_json = {
        "convention_version": "1.0",
        "name": "resolve-test-lib",
        "default_theme": "nimbus",
        "themes": [
            {
                "name": "nimbus",
                "file": "themes/nimbus.css",
                "label": "Nimbus",
                "contract_version": "1.0",
            }
        ],
    }
    (lib / "library.json").write_text(json.dumps(library_json), encoding="utf-8")
    (lib / "theme.css").write_text(":root{--bg:#fff}", encoding="utf-8")
    (lib / "assets").mkdir()
    (lib / "assets" / "bg.jpg").write_bytes(b"BG")
    (lib / "assets" / "already.png").write_bytes(b"ALREADY")
    (lib / "themes").mkdir()

    deck_dir = repo / "decks"
    deck_dir.mkdir()
    deck = deck_dir / "deck.html"
    deck.write_text("<html><body></body></html>", encoding="utf-8")

    return repo, lib, deck


# ---------------------------------------------------------------------------
# resolve-library
# ---------------------------------------------------------------------------


def test_resolve_library_success(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)

    status, resp = handle_resolve_library(
        {"deck_path": str(deck), "library_ref": "lib"}
    )

    assert status == 200
    assert resp["resolved"] is True
    assert resp["library_path"] == str(lib)
    assert resp["default_theme"] == "nimbus"
    assert len(resp["themes"]) == 2

    default_theme = resp["themes"][0]
    assert default_theme["name"] == "default"
    assert default_theme["label"] == "Default"
    assert default_theme["contract_version"] == "1.0"

    nimbus_theme = resp["themes"][1]
    assert nimbus_theme["name"] == "nimbus"
    assert nimbus_theme["label"] == "Nimbus"
    assert nimbus_theme["contract_version"] == "1.0"


def test_resolve_library_empty_ref():
    status, resp = handle_resolve_library(
        {"deck_path": r"C:\no\such\deck.html", "library_ref": ""}
    )
    assert status == 200
    assert resp["resolved"] is False
    assert "no library reference" in resp["reason"]


def test_resolve_library_no_repo(tmp_path, monkeypatch):
    real_exists = os.path.exists
    monkeypatch.setattr(os.path, "exists", _hide_git_exists(real_exists))

    no_git = tmp_path / "no-git"
    no_git.mkdir()
    deck = no_git / "deck.html"
    deck.write_text("<html></html>", encoding="utf-8")

    status, resp = handle_resolve_library(
        {"deck_path": str(deck), "library_ref": "lib"}
    )
    assert status == 200
    assert resp["resolved"] is False
    assert "deck not in a repo" in resp["reason"]


def test_resolve_library_bad_ref(tmp_path):
    repo, _lib, deck = _make_repo_with_library(tmp_path)

    status, resp = handle_resolve_library(
        {"deck_path": str(deck), "library_ref": "missing-lib"}
    )
    assert status == 200
    assert resp["resolved"] is False
    assert "library not found" in resp["reason"]


# ---------------------------------------------------------------------------
# copy-theme-assets
# ---------------------------------------------------------------------------


def test_copy_theme_assets_copies_missing_asset(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)
    css = ".slide { background: url('assets/bg.jpg'); }"
    (lib / "themes" / "nimbus.css").write_text(css, encoding="utf-8")

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "nimbus"}
    )

    assert status == 200
    assert "bg.jpg" in resp["copied"]
    assert resp["missing"] == []
    assert (repo / "decks" / "assets" / "bg.jpg").read_bytes() == b"BG"


def test_copy_theme_assets_skips_asset_already_beside_deck(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)
    css = ".cover { background-image: url(\"assets/already.png\"); }"
    (lib / "themes" / "nimbus.css").write_text(css, encoding="utf-8")

    deck_assets = repo / "decks" / "assets"
    deck_assets.mkdir()
    (deck_assets / "already.png").write_bytes(b"DECK")

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "nimbus"}
    )

    assert status == 200
    assert "already.png" not in resp["copied"]
    assert resp["missing"] == []
    assert (deck_assets / "already.png").read_bytes() == b"DECK"


def test_copy_theme_assets_reports_missing_asset(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)
    css = ".divider { background: url(assets/nowhere.png); }"
    (lib / "themes" / "nimbus.css").write_text(css, encoding="utf-8")

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "nimbus"}
    )

    assert status == 200
    assert resp["copied"] == []
    assert "nowhere.png" in resp["missing"]
    assert not (repo / "decks" / "assets" / "nowhere.png").exists()


def test_copy_theme_assets_default_theme(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)
    css = ".slide { background: url('assets/bg.jpg'); }"
    (lib / "theme.css").write_text(css, encoding="utf-8")

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "default"}
    )

    assert status == 200
    assert "bg.jpg" in resp["copied"]
    assert resp["missing"] == []


def test_copy_theme_assets_ignores_data_and_absolute_urls(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)
    css = (
        ".a { background: url(data:image/png;base64,ABC); }"
        ".b { background: url(https://example.com/x.png); }"
        ".c { background: url('assets/bg.jpg'); }"
    )
    (lib / "themes" / "nimbus.css").write_text(css, encoding="utf-8")

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "nimbus"}
    )

    assert status == 200
    assert resp["copied"] == ["bg.jpg"]
    assert resp["missing"] == []


def test_copy_theme_assets_missing_theme_css(tmp_path):
    repo, lib, deck = _make_repo_with_library(tmp_path)

    status, resp = handle_copy_theme_assets(
        {"deck_path": str(deck), "library_path": str(lib), "theme_name": "ghost"}
    )

    assert status == 200
    assert resp["copied"] == []
    assert resp["missing"] == []
    assert resp["error"] == "theme css not found"

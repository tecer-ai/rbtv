"""Tier-1 folder-move matrix gaps + required fixtures from p4-3."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from safe_move import classify
from safe_move.act import format_action_log, run_act
from safe_move.consult import build_consult_result


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _auto_refs(result: dict) -> list[dict]:
    return [ref for ref in result["references"] if ref["class"] == classify.CLASS_AUTO]


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# REQUIRED FIXTURE A — depth-change relative link inside the moved tree
# ═════════════════════════════════════════════════════════════════════════════

def test_depth_change_relative_link_is_recomputed(repo_builder):
    """A relative link that goes up-and-back into the moved folder is
    recomputed from the file's new, deeper location.

    Fixture: dir/a.md links to dir/sub/b.md via ``../dir/sub/b.md``.
    After ``dir/ -> a/b/dir/`` the correct relative path is ``sub/b.md``.
    """
    files = {
        "dir/a.md": "See [sibling](../dir/sub/b.md).\n",
        "dir/sub/b.md": "b\n",
    }
    fix = repo_builder("depth-change-relative", files, tracked=list(files))

    consulted = build_consult_result(
        "dir",
        "a/b/dir",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["file"] == "dir/a.md"
    assert ref["syntax"] == "markdown-link"
    assert ref["proposed"] == "[sibling](sub/b.md)"
    assert ref["class"] == classify.CLASS_AUTO

    result = run_act(
        "dir",
        "a/b/dir",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert not (fix.repo / "dir").exists()
    assert (
        fix.repo / "a" / "b" / "dir" / "a.md"
    ).read_text(encoding="utf-8") == "See [sibling](sub/b.md).\n"
    assert (
        fix.repo / "a" / "b" / "dir" / "sub" / "b.md"
    ).read_text(encoding="utf-8") == "b\n"


# ═════════════════════════════════════════════════════════════════════════════
# REQUIRED FIXTURE B — config-path value naming a folder by bare basename
# ═════════════════════════════════════════════════════════════════════════════

def test_config_path_bare_basename_folder_is_auto_fixed(repo_builder):
    """A YAML/JSON/TOML value that names the moved folder by bare basename is
    treated as a scope-root-relative path and auto-fixed to the new folder name.

    This pins the behavior that the ``resolves_to`` ambiguity bump applies to
    wikilink/frontmatter bare basenames but NOT to config-path values.
    """
    files = {
        "old/file.md": "body\n",
        "settings.yaml": "folder: old\n",
    }
    fix = repo_builder("config-bare-basename", files, tracked=list(files))

    consulted = build_consult_result(
        "old",
        "new",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["file"] == "settings.yaml"
    assert ref["syntax"] == "config-path"
    assert ref["match"] == "old"
    assert ref["proposed"] == "new"
    assert ref["class"] == classify.CLASS_AUTO

    result = run_act(
        "old",
        "new",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert not (fix.repo / "old").exists()
    assert (fix.repo / "new" / "file.md").exists()
    assert (
        fix.repo / "settings.yaml"
    ).read_text(encoding="utf-8") == "folder: new\n"
    log = format_action_log(result)
    assert "settings.yaml" in log


# ═════════════════════════════════════════════════════════════════════════════
# REQUIRED FIXTURE C — same-line identical-text references
# ═════════════════════════════════════════════════════════════════════════════

def test_same_line_identical_refs_are_not_collapsed_into_wrong_edit(repo_builder):
    """Two distinct references with the same match text on one line must not
    be silently deduplicated into a single replacement that leaves the second
    reference stale.
    """
    files = {
        "old/file.md": "body\n",
        "links.md": "See [link](old/file.md) and [link](old/file.md).\n",
    }
    fix = repo_builder("same-line-identical", files, tracked=list(files))

    consulted = build_consult_result(
        "old",
        "new",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    # Both occurrences must be discovered and applied, or surfaced safely.
    auto = _auto_refs(consulted)

    result = run_act(
        "old",
        "new",
        scope_root=fix.repo,
        apply=_apply_string(auto),
    )

    assert result.exit_code == 0
    after = (fix.repo / "links.md").read_text(encoding="utf-8")
    # Both references must point at the new path; no stale half-edit allowed.
    assert after == "See [link](new/file.md) and [link](new/file.md).\n"


# ═════════════════════════════════════════════════════════════════════════════
# REQUIRED FIXTURE D — symlink to a file outside the moved tree
# ═════════════════════════════════════════════════════════════════════════════

def test_symlink_to_outside_file_is_skipped_and_target_missed_not_corrupted(
    repo_builder,
):
    """A symlink inside the moved tree pointing outside the tree is skipped by
    the walker. References reachable only through that symlink are missed (not
    corrupted). This is the known, safe-failing limitation.
    """
    files = {
        "old/file.md": "body\n",
        ".ignored/outside.md": "See [link](old/file.md).\n",
    }
    fix = repo_builder("symlink-outside", files, tracked=list(files))
    link_path = fix.repo / "old" / "link.md"
    try:
        link_path.symlink_to("../.ignored/outside.md")
    except OSError as exc:
        pytest.skip(f"symlink creation not supported on this platform: {exc}")

    assert link_path.is_symlink()

    consulted = build_consult_result(
        "old",
        "new",
        scope_root=fix.repo,
        exclude=[".ignored"],
    )

    # The symlink itself is not discovered as a scanned file, and the excluded
    # target file is also not scanned, so the reference inside it is missed.
    assert not any(
        ref["file"] == ".ignored/outside.md" for ref in consulted["references"]
    )

    result = run_act(
        "old",
        "new",
        scope_root=fix.repo,
        exclude=[".ignored"],
        apply="",
    )

    assert result.exit_code == 0
    assert not (fix.repo / "old").exists()
    assert (fix.repo / "new" / "file.md").exists()

    # The symlink is moved verbatim; it still points at the same outside file.
    moved_link = fix.repo / "new" / "link.md"
    assert moved_link.is_symlink()
    assert os.readlink(moved_link) == "../.ignored/outside.md"

    # The outside file was never scanned or edited, so its stale reference
    # remains untouched (the "missed" part of the safe-failing behavior).
    assert (
        fix.repo / ".ignored" / "outside.md"
    ).read_text(encoding="utf-8") == "See [link](old/file.md).\n"

    log = format_action_log(result)
    assert "moved" in log
    assert "old -> new" in log

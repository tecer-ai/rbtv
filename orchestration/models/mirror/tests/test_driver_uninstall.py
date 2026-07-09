"""test_driver_uninstall.py — lock the mirror driver's uninstall/cleanup policy.

Policy (owner-confirmed 2026-06-13): an uninstall deletes ONLY the files rbtv
created (the recorded managed_files), then removes a worker dir that the deletion
leaves empty. A dir kept alive by a file rbtv did NOT create (a tool-written
leftover or a prior-install orphan) is left in place AND surfaced via
``UninstallResult.leftover_dirs`` so the owner can delete it by hand — rbtv never
deletes a file it did not create.

Exercises the real ``driver.render`` / ``driver.uninstall`` against scratch
workspaces (pytest ``tmp_path``) — no mocks. Run from the rbtv repo root:
    python -m pytest orchestration/models/mirror/tests/test_driver_uninstall.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the driver package: its parent (the mirror/ dir) must be on sys.path —
# the same reachability shim the driver's own cli.py uses for loose invocation.
_MIRROR_DIR = Path(__file__).resolve().parent.parent
if str(_MIRROR_DIR) not in sys.path:
    sys.path.insert(0, str(_MIRROR_DIR))

from driver import render, uninstall  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_workspace(root: Path) -> None:
    """Create the minimal .claude/ inputs the shared .agents/ library renders from."""
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "rules" / "r1.md").write_text("# rule one\nbody\n", encoding="utf-8")
    (root / ".claude" / "rules" / "r2.md").write_text("# rule two\nbody\n", encoding="utf-8")
    (root / ".claude" / "skills" / "s1").mkdir(parents=True)
    (root / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nbody\n", encoding="utf-8"
    )
    (root / "CLAUDE.md").write_text("# root guidance\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_full_teardown_removes_managed_dirs_and_reports_no_leftovers(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli", "kimi-code-cli", "opencode"])
    for d in (".codex", ".kimi", ".agents"):
        assert (tmp_path / d).is_dir(), f"{d} should exist after render"
    assert (tmp_path / "AGENTS.md").is_file()

    result = uninstall(tmp_path, ["codex-cli", "kimi-code-cli", "opencode"], [])

    for d in (".codex", ".kimi", ".agents"):
        assert not (tmp_path / d).exists(), f"{d} should be pruned (managed-only, now empty)"
    assert not (tmp_path / "AGENTS.md").exists()
    assert result.leftover_dirs == [], "no foreign files → no leftovers reported"


def test_configless_package_renders_guidance_only_and_refcounts(tmp_path):
    """opencode has config_dir=None — it renders guidance + the shared library but NO
    config dir, and its deselection keeps AGENTS.md alive while codex still needs it."""
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli", "opencode"])
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".agents").is_dir()
    assert not (tmp_path / ".opencode").exists(), "config-less package must render no config dir"

    result = uninstall(tmp_path, ["opencode"], ["codex-cli"])

    assert (tmp_path / "AGENTS.md").is_file(), "AGENTS.md kept (codex still maps to it)"
    assert (tmp_path / ".codex").is_dir(), "remaining codex dir kept"
    assert (tmp_path / ".agents").is_dir(), "shared library kept while a worker remains"
    assert result.leftover_dirs == []


def test_per_model_deselect_keeps_remaining_and_shared(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli", "kimi-code-cli"])

    result = uninstall(tmp_path, ["kimi-code-cli"], ["codex-cli"])

    assert not (tmp_path / ".kimi").exists(), "deselected kimi dir pruned"
    assert (tmp_path / ".codex").is_dir(), "remaining codex dir kept"
    assert (tmp_path / ".agents").is_dir(), "shared library kept while a worker remains"
    assert (tmp_path / "AGENTS.md").is_file(), "AGENTS.md kept (codex still needs it)"
    assert result.leftover_dirs == []


def test_foreign_file_keeps_worker_dir_and_is_reported(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli", "kimi-code-cli"])
    # kimi-tool leftovers rbtv never recorded.
    (tmp_path / ".kimi" / "skills" / "foo").mkdir(parents=True)
    (tmp_path / ".kimi" / "skills" / "foo" / "SKILL.md").write_text("foreign\n", encoding="utf-8")
    (tmp_path / ".kimi" / "settings.json.orig").write_text('{"foreign": true}\n', encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli", "kimi-code-cli"], [])

    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".agents").exists()
    assert (tmp_path / ".kimi").is_dir(), "foreign files keep .kimi alive"
    # rbtv's own .kimi/settings.json was deleted; only foreign files remain.
    assert not (tmp_path / ".kimi" / "settings.json").exists()
    entries = {e["dir"]: e for e in result.leftover_dirs}
    assert ".kimi" in entries, "the surviving .kimi must be surfaced"
    assert entries[".kimi"]["files"] == [
        ".kimi/settings.json.orig",
        ".kimi/skills/foo/SKILL.md",
    ]


def test_never_managed_stray_surfaced_on_full_teardown(tmp_path):
    # Real-vault shape: kimi NOT elected, but a stray .kimi/ exists on disk.
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli"])
    assert not (tmp_path / ".kimi").exists(), "kimi not elected → not rendered"
    (tmp_path / ".kimi").mkdir()
    (tmp_path / ".kimi" / "settings.json.orig").write_text("{}\n", encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".agents").exists()
    assert (tmp_path / ".kimi").is_dir(), "stray survives (rbtv never created its files)"
    dirs = {e["dir"] for e in result.leftover_dirs}
    assert ".kimi" in dirs, "a full teardown scans every known worker dir, surfacing the stray"


def test_agents_orphan_survives_and_is_reported(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli"])
    # Orphan rule from a prior, larger install — not in .claude/, so unmanaged.
    (tmp_path / ".agents" / "behavior-rules" / "orphan.md").write_text("stale\n", encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert (tmp_path / ".agents").is_dir(), "orphan keeps .agents alive"
    assert (tmp_path / ".agents" / "behavior-rules" / "orphan.md").is_file()
    dirs = {e["dir"] for e in result.leftover_dirs}
    assert ".agents" in dirs


def test_handauthored_guidance_is_spared(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli"])
    # Owner replaces the generated AGENTS.md with a hand-authored one (no banner).
    (tmp_path / "AGENTS.md").write_text("# my own agents file\n", encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert (tmp_path / "AGENTS.md").is_file(), "banner-less guidance is never deleted"
    assert "AGENTS.md" in result.spared

"""test_driver_uninstall.py — lock the mirror driver's uninstall/cleanup policy.

Policy (owner-confirmed 2026-06-13): an uninstall deletes ONLY the files rbtv
created (the recorded managed_files), then removes a worker dir that the deletion
leaves empty. A dir kept alive by a file rbtv did NOT create (a tool-written
leftover or a prior-install orphan) is left in place AND surfaced via
``UninstallResult.leftover_dirs`` so the owner can delete it by hand — rbtv never
deletes a file it did not create.

Exercises the real ``driver.render`` / ``driver.uninstall`` against scratch
workspaces (pytest ``tmp_path``) — no mocks. Run from the rbtv repo root:
    python -m pytest ignite/coord/mirror/tests/test_driver_uninstall.py -q
"""
from __future__ import annotations

import json
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
    render(tmp_path, ["codex-cli", "opencode"])
    for d in (".codex", ".agents"):
        assert (tmp_path / d).is_dir(), f"{d} should exist after render"

    result = uninstall(tmp_path, ["codex-cli", "opencode"], [])

    for d in (".codex", ".agents"):
        assert not (tmp_path / d).exists(), f"{d} should be pruned (managed-only, now empty)"
    assert result.leftover_dirs == [], "no foreign files → no leftovers reported"


def test_configless_package_renders_library_only(tmp_path):
    """opencode has config_dir=None — it renders the shared library but NO config dir
    (and, since the guidance retirement, nothing else)."""
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli", "opencode"])
    assert (tmp_path / ".agents").is_dir()
    assert not (tmp_path / ".opencode").exists(), "config-less package must render no config dir"

    result = uninstall(tmp_path, ["opencode"], ["codex-cli"])

    assert (tmp_path / ".codex").is_dir(), "remaining codex dir kept"
    assert (tmp_path / ".agents").is_dir(), "shared library kept while a worker remains"
    assert result.leftover_dirs == []


# test_per_model_deselect_keeps_remaining_and_shared was removed 2026-08-18:
# it deselected kimi-code-cli while codex-cli remained, to prove a per-model
# deselect keeps a remaining package's config dir plus the shared library.
# kimi-code-cli's config leg is retired (codex-cli is now the only package with
# a config dir), so the two-config-package scenario no longer exists.
# test_configless_package_renders_library_only below covers the same
# "remaining kept + shared kept" assertion with codex-cli as the survivor.


def test_foreign_file_keeps_worker_dir_and_is_reported(tmp_path):
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli"])
    # codex-tool leftovers rbtv never recorded.
    (tmp_path / ".codex" / "skills" / "foo").mkdir(parents=True)
    (tmp_path / ".codex" / "skills" / "foo" / "SKILL.md").write_text("foreign\n", encoding="utf-8")
    (tmp_path / ".codex" / "settings.json.orig").write_text('{"foreign": true}\n', encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert not (tmp_path / ".agents").exists()
    assert (tmp_path / ".codex").is_dir(), "foreign files keep .codex alive"
    # rbtv's own .codex/config.toml and .codex/rules/default.rules were deleted; only foreign files remain.
    assert not (tmp_path / ".codex" / "config.toml").exists()
    assert not (tmp_path / ".codex" / "rules" / "default.rules").exists()
    entries = {e["dir"]: e for e in result.leftover_dirs}
    assert ".codex" in entries, "the surviving .codex must be surfaced"
    assert entries[".codex"]["files"] == [
        ".codex/settings.json.orig",
        ".codex/skills/foo/SKILL.md",
    ]


def test_never_managed_stray_surfaced_on_full_teardown(tmp_path):
    # Real-vault shape: codex NOT elected, but a stray .codex/ exists on disk.
    _seed_workspace(tmp_path)
    render(tmp_path, ["opencode"])
    assert not (tmp_path / ".codex").exists(), "codex not elected → not rendered"
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml.orig").write_text("{}\n", encoding="utf-8")

    result = uninstall(tmp_path, ["opencode"], [])

    assert not (tmp_path / ".agents").exists()
    assert (tmp_path / ".codex").is_dir(), "stray survives (rbtv never created its files)"
    dirs = {e["dir"] for e in result.leftover_dirs}
    assert ".codex" in dirs, "a full teardown scans every known worker dir, surfacing the stray"


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


def test_banner_less_legacy_guidance_record_is_spared(tmp_path):
    """The banner-guard on the teardown arm survives the guidance RETIREMENT
    (d-hard-guard-retire-model-mirror): a render can no longer create a guidance
    record, but a workspace installed BEFORE the retirement still carries them, and
    a file without installer-1's banner must never be deleted."""
    _seed_workspace(tmp_path)
    render(tmp_path, ["codex-cli"])
    # Legacy record from a pre-retirement render + a file installer-1 did not write.
    (tmp_path / "AGENTS.md").write_text("# my own agents file\n", encoding="utf-8")
    state_path = tmp_path / "rbtv.json"
    doc = json.loads(state_path.read_text(encoding="utf-8"))
    doc["model_mirror"]["managed_files"].append(
        {"path": "AGENTS.md", "kind": "guidance", "owner": "agents-md"}
    )
    state_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert (tmp_path / "AGENTS.md").is_file(), "banner-less guidance is never deleted"
    assert "AGENTS.md" in result.spared

"""test_driver_check_drift.py — lock ``--check``'s content-drift detection.

Regression guard for the 2026-07-26 defect: a managed mirror file that existed
on disk but had fallen behind its source was reported ONLY by a print, never in
the exit code. ``render(..., check=True)`` derived ``RenderResult.stale`` solely
from ``_detect_drift``, which sees missing files and managed-set changes but
never re-composes expected content — so the single most common staleness case
(source edited, mirror present but out of date) check-PASSED with exit 0.

Each render module now appends its drifted paths to a ``stale_sink`` that
``render`` OR-s into ``stale`` and exposes as ``stale_paths``. These tests cover
every module that owns managed files — a rule, a skill, and a guidance file —
because the original bug was worst in ``library.py``, which discarded the write
status outright and so never even printed.

Exercises the real ``driver.render`` against scratch workspaces (pytest
``tmp_path``) — no mocks. Run from the rbtv repo root:
    python -m pytest orchestration/models/mirror/tests/test_driver_check_drift.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the driver package: its parent (the mirror/ dir) must be on sys.path —
# the same reachability shim the driver's own cli.py uses for loose invocation.
_MIRROR_DIR = Path(__file__).resolve().parent.parent
if str(_MIRROR_DIR) not in sys.path:
    sys.path.insert(0, str(_MIRROR_DIR))

from driver import render  # noqa: E402

_PACKAGES = ["codex-cli", "kimi-code-cli", "opencode"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_workspace(root: Path) -> None:
    """Create the minimal .claude/ inputs the shared .agents/ library renders from."""
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "rules" / "r1.md").write_text("# rule one\nbody\n", encoding="utf-8")
    (root / ".claude" / "skills" / "s1").mkdir(parents=True)
    (root / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nbody\n", encoding="utf-8"
    )
    (root / "CLAUDE.md").write_text("# root guidance\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_check_is_clean_immediately_after_render(tmp_path):
    """Baseline: a freshly rendered workspace must not report drift."""
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)

    result = render(tmp_path, _PACKAGES, check=True)

    assert result.stale is False, "a just-rendered mirror must be in sync"
    assert result.stale_paths == []


def test_edited_rule_source_makes_check_stale(tmp_path):
    """A .claude/rules/ edit must reach the exit code, not just a print.

    library.py discarded the write status entirely before the fix, so this case
    was completely invisible to --check.
    """
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)

    (tmp_path / ".claude" / "rules" / "r1.md").write_text(
        "# rule one\nEDITED body\n", encoding="utf-8"
    )
    result = render(tmp_path, _PACKAGES, check=True)

    assert result.stale is True, "an edited rule source must make --check stale"
    assert ".agents/behavior-rules/r1.md" in result.stale_paths


def test_edited_skill_source_makes_check_stale(tmp_path):
    """The exact shape of the observed incident: a SKILL.md edit re-stales the mirror."""
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)

    (tmp_path / ".claude" / "skills" / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: demo skill\n---\nEDITED body\n", encoding="utf-8"
    )
    result = render(tmp_path, _PACKAGES, check=True)

    assert result.stale is True, "an edited skill source must make --check stale"
    assert ".agents/skills/s1/SKILL.md" in result.stale_paths


def test_edited_claude_md_makes_guidance_check_stale(tmp_path):
    """A CLAUDE.md edit must re-stale its sibling AGENTS.md."""
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)

    (tmp_path / "CLAUDE.md").write_text("# root guidance\nEDITED\n", encoding="utf-8")
    result = render(tmp_path, _PACKAGES, check=True)

    assert result.stale is True, "an edited CLAUDE.md must make --check stale"
    assert "AGENTS.md" in result.stale_paths


def test_check_never_writes(tmp_path):
    """--check is read-only: a drifted mirror stays drifted after a check run."""
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)

    mirrored = tmp_path / ".agents" / "behavior-rules" / "r1.md"
    before = mirrored.read_bytes()
    (tmp_path / ".claude" / "rules" / "r1.md").write_text(
        "# rule one\nEDITED body\n", encoding="utf-8"
    )

    render(tmp_path, _PACKAGES, check=True)

    assert mirrored.read_bytes() == before, "check mode must not repair the mirror"


def test_stale_clears_after_a_refresh(tmp_path):
    """The drift signal must be actionable: a real render clears it."""
    _seed_workspace(tmp_path)
    render(tmp_path, _PACKAGES)
    (tmp_path / ".claude" / "rules" / "r1.md").write_text(
        "# rule one\nEDITED body\n", encoding="utf-8"
    )
    assert render(tmp_path, _PACKAGES, check=True).stale is True

    render(tmp_path, _PACKAGES)

    assert render(tmp_path, _PACKAGES, check=True).stale is False

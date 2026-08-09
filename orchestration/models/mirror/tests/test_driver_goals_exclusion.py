"""test_driver_goals_exclusion.py — lock the always-on ``.rbtv/goals`` exclusion.

Owner ruling Q18 (2026-08-09): the goals-tree scaffold owns a goal folder's
routers — BOTH ``CLAUDE.md`` and ``AGENTS.md`` — so the mirror walk must skip
``.rbtv/goals`` unconditionally. Before the exclusion the driver rendered its own
banner over the scaffold's ``AGENTS.md`` and recorded it as managed, and a
teardown then DELETED it (the scaffold's router header carries the same
DO-NOT-EDIT sentinel, so the banner-guard does not spare it).

Row 7.597 adds the uninstall-residual case: a workspace upgraded from a driver that
HAD recorded a goal router, torn down before its first post-upgrade render — the
record survives the upgrade, so ``uninstall`` must drop it from the delete set.

The last test is the RED control: with ``ALWAYS_EXCLUDED_PREFIXES`` emptied, the
same fixture IS overwritten — without it, the two green assertions above could
pass for a reason unrelated to the exclusion.

Runs under pytest (``tmp_path``) like its siblings, and — because a machine
without pytest must still be able to exercise this — as a plain script:
    python -m pytest orchestration/models/mirror/tests/test_driver_goals_exclusion.py -q
    python orchestration/models/mirror/tests/test_driver_goals_exclusion.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_MIRROR_DIR = Path(__file__).resolve().parent.parent
if str(_MIRROR_DIR) not in sys.path:
    sys.path.insert(0, str(_MIRROR_DIR))

from driver import render, uninstall  # noqa: E402
from driver import guidance  # noqa: E402

# The scaffold's router header, abbreviated — what matters is that it carries the
# banner sentinel (so the banner-guard would NOT spare this file) and is NOT what
# the mirror would compose.
SCAFFOLD_AGENTS_MD = (
    "<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. `CLAUDE.md` in this folder is the "
    "source of truth. -->\n\n---\n\n# demo-goal/ — goal folder\n"
)


def _seed(root: Path) -> Path:
    """Workspace root with a scaffolded goal under .rbtv/goals/. Returns its AGENTS.md."""
    (root / "CLAUDE.md").write_text("# root guidance\n", encoding="utf-8")
    goal = root / ".rbtv" / "goals" / "demo-goal"
    goal.mkdir(parents=True)
    (goal / "CLAUDE.md").write_text("# demo-goal/ — goal folder\n", encoding="utf-8")
    agents = goal / "AGENTS.md"
    agents.write_text(SCAFFOLD_AGENTS_MD, encoding="utf-8")
    return agents


def test_render_leaves_a_scaffolded_goal_router_untouched_and_unmanaged(tmp_path):
    agents = _seed(tmp_path)

    result = render(tmp_path, ["codex-cli"])

    assert agents.read_text(encoding="utf-8") == SCAFFOLD_AGENTS_MD
    assert not [r for r in result.managed_files if r["path"].startswith(".rbtv/goals/")]


def test_teardown_leaves_a_scaffolded_goal_router_on_disk(tmp_path):
    agents = _seed(tmp_path)
    render(tmp_path, ["codex-cli"])

    uninstall(tmp_path, ["codex-cli"], [])

    assert agents.is_file()
    assert agents.read_text(encoding="utf-8") == SCAFFOLD_AGENTS_MD


def test_uninstall_protects_a_pre_upgrade_recorded_goal_router(tmp_path):
    """The upgrade residual (row 7.597): a workspace whose rbtv.json ALREADY records
    a goal router (from a PRE-exclusion render) and that tears down BEFORE its first
    post-upgrade render. The record is still there, and the banner-guard cannot spare
    the file (the scaffold header carries the same sentinel) — uninstall must drop it
    from the delete set, while still deleting every non-goals managed file."""
    agents = _seed(tmp_path)
    (tmp_path / "normal-area").mkdir()
    (tmp_path / "normal-area" / "CLAUDE.md").write_text("# normal\n", encoding="utf-8")
    render(tmp_path, ["codex-cli"])

    # Simulate the pre-upgrade record the current walk no longer emits.
    state_path = tmp_path / "rbtv.json"
    doc = json.loads(state_path.read_text(encoding="utf-8"))
    doc["model_mirror"]["managed_files"].append(
        {"path": ".rbtv/goals/demo-goal/AGENTS.md", "kind": "guidance", "owner": "agents-md"}
    )
    state_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert agents.is_file(), "recorded goal router must survive --uninstall"
    assert agents.read_text(encoding="utf-8") == SCAFFOLD_AGENTS_MD, "byte-identical"
    assert result.protected == [".rbtv/goals/demo-goal/AGENTS.md"]
    assert not (tmp_path / "normal-area" / "AGENTS.md").exists(), \
        "non-goals managed guidance is still deleted"
    assert ".rbtv/goals/demo-goal/AGENTS.md" not in result.deleted
    # Protected records are dropped from state, exactly like spared ones.
    assert not [r for r in result.kept_records if r["path"].startswith(".rbtv/goals/")]


def test_red_control_without_the_exclusion_the_router_is_overwritten(tmp_path):
    agents = _seed(tmp_path)
    # setattr/restore rather than pytest's monkeypatch so this file also runs
    # as a plain script on a machine with no pytest.
    saved = guidance.ALWAYS_EXCLUDED_PREFIXES
    guidance.ALWAYS_EXCLUDED_PREFIXES = ()
    try:
        result = render(tmp_path, ["codex-cli"])
    finally:
        guidance.ALWAYS_EXCLUDED_PREFIXES = saved

    assert agents.read_text(encoding="utf-8") != SCAFFOLD_AGENTS_MD
    assert [r for r in result.managed_files if r["path"].startswith(".rbtv/goals/")]


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(
        (n, f) for n, f in list(globals().items()) if n.startswith("test_") and callable(f)
    ):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn(Path(tmp))
            except AssertionError as exc:
                failed += 1
                print(f"FAIL {name}: {exc}")
            else:
                print(f"PASS {name}")
    print("FAIL" if failed else "PASS", f"— {failed} failing")
    sys.exit(1 if failed else 0)

"""test_driver_goals_exclusion.py — lock the ``.rbtv/goals`` protection on TEARDOWN.

Owner ruling Q18 (2026-08-09): the goals-tree scaffold owns a goal folder's
routers — BOTH ``CLAUDE.md`` and ``AGENTS.md`` — so the mirror must never write
or delete one.

Since ``d-hard-guard-retire-model-mirror`` (2026-08-10) the driver renders NO
guidance file at all, so the render-side half of this guard is structural and its
tests (plus their RED control, which required a working guidance render) are gone.
What survives is the uninstall residual of row 7.597: a workspace installed BEFORE
the retirement still carries ``kind: "guidance"`` records in ``rbtv.json``, and a
teardown must drop the goal-router ones from its delete set — the banner-guard
cannot spare them (the scaffold's own header carries the same DO-NOT-EDIT
sentinel).

Runs under pytest (``tmp_path``) like its siblings, and — because a machine
without pytest must still be able to exercise this — as a plain script:
    python -m pytest ignite/team-kit/mirror/tests/test_driver_goals_exclusion.py -q
    python ignite/team-kit/mirror/tests/test_driver_goals_exclusion.py
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
from driver import state  # noqa: E402

# The scaffold's router header, abbreviated — what matters is that it carries the
# banner sentinel, so the banner-guard would NOT spare this file.
SCAFFOLD_AGENTS_MD = (
    "<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. `CLAUDE.md` in this folder is the "
    "source of truth. -->\n\n---\n\n# demo-goal/ — goal folder\n"
)


def _seed(root: Path) -> Path:
    """Workspace root with a scaffolded goal under .rbtv/goals/. Returns its AGENTS.md."""
    (root / "CLAUDE.md").write_text("# root guidance\n", encoding="utf-8")
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "rules" / "r1.md").write_text("# rule one\nbody\n", encoding="utf-8")
    goal = root / ".rbtv" / "goals" / "demo-goal"
    goal.mkdir(parents=True)
    (goal / "CLAUDE.md").write_text("# demo-goal/ — goal folder\n", encoding="utf-8")
    agents = goal / "AGENTS.md"
    agents.write_text(SCAFFOLD_AGENTS_MD, encoding="utf-8")
    return agents


def _record(state_path: Path, rel: str) -> None:
    """Append a pre-retirement ``kind: guidance`` record the current render never emits."""
    doc = json.loads(state_path.read_text(encoding="utf-8"))
    doc["model_mirror"]["managed_files"].append(
        {"path": rel, "kind": "guidance", "owner": "agents-md"}
    )
    state_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def test_render_leaves_a_scaffolded_goal_router_untouched_and_unmanaged(tmp_path):
    agents = _seed(tmp_path)

    result = render(tmp_path, ["codex-cli"])

    assert agents.read_text(encoding="utf-8") == SCAFFOLD_AGENTS_MD
    assert not [r for r in result.managed_files if r["path"].startswith(".rbtv/goals/")]


def test_uninstall_protects_a_pre_retirement_recorded_goal_router(tmp_path):
    """Row 7.597, now the pre-RETIREMENT residual: a workspace whose rbtv.json still
    records a goal router (from a render before the guidance retirement) and that
    tears down afterwards. The banner-guard cannot spare the file (the scaffold
    header carries the same sentinel), so uninstall must drop it from the delete
    set — while still deleting a legacy record whose file installer-1 DID write."""
    agents = _seed(tmp_path)
    (tmp_path / "normal-area").mkdir()
    ours = tmp_path / "normal-area" / "AGENTS.md"
    ours.write_text(SCAFFOLD_AGENTS_MD, encoding="utf-8")  # carries installer-1's sentinel
    render(tmp_path, ["codex-cli"])

    _record(tmp_path / "rbtv.json", ".rbtv/goals/demo-goal/AGENTS.md")
    _record(tmp_path / "rbtv.json", "normal-area/AGENTS.md")

    result = uninstall(tmp_path, ["codex-cli"], [])

    assert agents.is_file(), "recorded goal router must survive --uninstall"
    assert agents.read_text(encoding="utf-8") == SCAFFOLD_AGENTS_MD, "byte-identical"
    assert result.protected == [".rbtv/goals/demo-goal/AGENTS.md"]
    assert ".rbtv/goals/demo-goal/AGENTS.md" not in result.deleted
    assert not ours.exists(), "a non-goals legacy record with our banner is still torn down"
    # Protected records are dropped from state, exactly like spared ones.
    assert not [r for r in result.kept_records if r["path"].startswith(".rbtv/goals/")]


def test_red_control_without_the_exclusion_the_recorded_router_is_deleted(tmp_path):
    """With ``ALWAYS_EXCLUDED_PREFIXES`` emptied the same fixture IS deleted — without
    this, the assertion above could pass for a reason unrelated to the exclusion."""
    agents = _seed(tmp_path)
    render(tmp_path, ["codex-cli"])
    _record(tmp_path / "rbtv.json", ".rbtv/goals/demo-goal/AGENTS.md")

    saved = state.ALWAYS_EXCLUDED_PREFIXES
    state.ALWAYS_EXCLUDED_PREFIXES = ()
    try:
        result = uninstall(tmp_path, ["codex-cli"], [])
    finally:
        state.ALWAYS_EXCLUDED_PREFIXES = saved

    assert not agents.exists(), "control: without the exclusion the router is deleted"
    assert result.protected == []


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

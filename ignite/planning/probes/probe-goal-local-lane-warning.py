#!/usr/bin/env python3
"""probe-goal-local-lane-warning.py — every file build_goal_local_lane copies or
writes into planning/current/seat-lane/ carries an unmissable in-file DERIVED
warning naming its real source (build-ignite task 127).

  W1  copied prompt .md carries the warning as the first body line, AFTER the
      closing `---` of its frontmatter (never before it — that would corrupt
      `_goal_local_frontmatter` and every other `^---...---` reader)
  W2  copied task .md carries the same warning
  W3  frontmatter still parses after the warning is stamped in (id: readable)
  W4  seats.csv (a CSV — a comment line would be read back as a data row) has
      no in-file warning, but a README.md sidecar in the same directory does
  W5  the workflow CSV has the same sidecar treatment, in its own directory
  W6  the pre-existing root DERIVED.md marker is untouched (regression guard)

Red arm (manual, task 127 criterion 6): `git stash` the fix hunk in
`build_goal_local_lane`/`_copy_with_derived_warning` inside a scratch worktree
and re-run this probe — W1/W2/W4/W5 go red because `shutil.copyfile` carries no
warning and no README sidecar exists.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
PLANNING = ROOT / "ignite" / "planning"
OUT = HERE / "probe-goal-local-lane-warning.out"

lines, failures = [], []


def say(msg):
    lines.append(msg)
    print(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load_materialize():
    path = PLANNING / "materialize-seats.py"
    spec = importlib.util.spec_from_file_location("mseats_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture(root: Path):
    seat = root / "planning" / "current" / "seats" / "probeseat"
    seat.mkdir(parents=True)
    (root / "planning" / "current" / "manifest.csv").write_text(
        "Seat/workflow,after\nprobeseat,\n", encoding="utf-8")
    (root / "taskforce.csv").write_text("seat\n", encoding="utf-8")
    (seat / "prompt.md").write_text(
        "---\nid: probeseat-prompt\ndescription: \"probe fixture\"\n---\n\n"
        "<role>\ndo the probe thing\n</role>\n", encoding="utf-8")
    (seat / "task.md").write_text(
        "---\nid: probeseat-task\ndescription: \"probe fixture\"\n---\n\n"
        "<task-goal>\nfinish the probe thing\n</task-goal>\n", encoding="utf-8")


def main():
    if not (PLANNING / "materialize-seats.py").exists():
        check("W0", False, f"{PLANNING} missing materialize-seats.py")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1
    mseats = load_materialize()

    with tempfile.TemporaryDirectory(prefix="probe-goal-local-lane-") as td:
        pkg = Path(td) / "goal"
        pkg.mkdir()
        fixture(pkg)
        comp_root = ROOT / "meta" / "master"
        lane_module = mseats.build_goal_local_lane(pkg, comp_root)
        scomp = lane_module / "goal-local"

        prompt_text = (scomp / "prompts" / "probeseat-prompt.md").read_text(encoding="utf-8")
        task_text = (scomp / "tasks" / "probeseat-task.md").read_text(encoding="utf-8")

        head, _, prompt_body = prompt_text.partition("---\n", )  # first fence
        check("W1", "DERIVED" in prompt_text and "discarded" in prompt_text
              and "planning/current/seats/probeseat/prompt.md" in prompt_text,
              "copied prompt names the source path and 'discarded'")
        check("W2", "DERIVED" in task_text and "discarded" in task_text
              and "planning/current/seats/probeseat/task.md" in task_text,
              "copied task names the source path and 'discarded'")

        # W1/W2 must land AFTER the frontmatter fence, never before it.
        fence_end = prompt_text.index("---\n", prompt_text.index("---\n") + 4) + 4
        warn_pos = prompt_text.find("DERIVED")
        check("W1b", warn_pos > fence_end,
              "warning sits after the closing `---`, not before it"
              if warn_pos >= 0 else "no 'DERIVED' marker found in copied prompt at all")

        fm = mseats._goal_local_frontmatter(scomp / "prompts" / "probeseat-prompt.md")
        check("W3", fm.get("id") == "probeseat-prompt",
              f"frontmatter still parses after the warning is stamped in: id={fm.get('id')!r}")

        seats_csv = (scomp / "seats.csv").read_text(encoding="utf-8")
        seats_readme = (scomp / "README.md")
        check("W4", "DERIVED" not in seats_csv.splitlines()[0]
              and seats_readme.is_file() and "DERIVED" in seats_readme.read_text(encoding="utf-8"),
              "seats.csv carries no header (would corrupt the CSV reader); README.md sidecar does")

        wf_dir = scomp / "workflows" / mseats.GOAL_LOCAL_WORKFLOW
        wf_csv = (wf_dir / f"{mseats.GOAL_LOCAL_WORKFLOW}.csv").read_text(encoding="utf-8")
        wf_readme = wf_dir / "README.md"
        check("W5", "DERIVED" not in wf_csv.splitlines()[0]
              and wf_readme.is_file() and "DERIVED" in wf_readme.read_text(encoding="utf-8"),
              "workflow csv carries no header; its own README.md sidecar does")

        root_marker = lane_module.parent / "DERIVED.md"
        check("W6", root_marker.is_file() and "source: .." in root_marker.read_text(encoding="utf-8"),
              "pre-existing root DERIVED.md marker (write-refusal predicate) untouched")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        say(f"FAIL — {len(failures)} check(s): {', '.join(failures)}")
        return 1
    say("PASS — all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())

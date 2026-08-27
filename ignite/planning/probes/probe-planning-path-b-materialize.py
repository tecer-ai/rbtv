#!/usr/bin/env python3
"""probe-planning-path-b-materialize.py — approve-package births a NEW execution goal.

  P1  plan fixture at a recorded commit → execution goal folder created
  P2  planning goal taskforce.csv is byte-identical after
  P3  planning goal planning/current/ is byte-identical after
  P4  a package that DECLARES a workflow mints from the catalog: argv aims --package at the NEW
      folder, and carries no --goal-local/--milestone-id/--nested
  P5  a package that declares NO workflow is a one-off plan: the argv takes the --goal-local lane,
      the plan's own planning/current/ is copied into the born goal, and the contract the goal is
      born under is the BOUND COMMIT's, not the working tree's
  P6  the catalog root defaults to the rbtv `meta` tree through rbtv.json, and refuses when the
      book that records it is absent
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
PLANNING = ROOT / "ignite" / "planning"
OUT = HERE / "probe-planning-path-b-materialize.out"

lines, failures = [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load(name):
    path = PLANNING / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"planning_{name}_pbm", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def digest_tree(folder):
    folder = Path(folder)
    acc = []
    if not folder.exists():
        return ""
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            rel = p.relative_to(folder).as_posix()
            acc.append(rel + ":" + hashlib.sha256(p.read_bytes()).hexdigest())
    return "\n".join(acc)


def main():
    if not (PLANNING / "path_b.py").exists():
        check("P1", False, f"{PLANNING} missing path_b.py")
        return
    path_b = load("path_b")

    with tempfile.TemporaryDirectory(prefix="path-b-mat-") as tmp:
        tmp = Path(tmp)
        goals = tmp / "goals"
        goals.mkdir()
        plan_goal = goals / "plan-alpha"
        current = plan_goal / "planning" / "current"
        current.mkdir(parents=True)
        tf = plan_goal / "taskforce.csv"
        tf.write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,understand,,claude,opus,1,,m0\n",
            encoding="utf-8",
        )
        (current / "marker.txt").write_text("planning-pass-body\n", encoding="utf-8")
        tf_before = tf.read_bytes()
        current_before = digest_tree(current)

        artifacts = tmp / "artifacts"
        artifacts.mkdir()
        (artifacts / "contract.md").write_text("build the thing\n", encoding="utf-8")
        (artifacts / "roster.json").write_text(
            json.dumps(["build", "verify"]) + "\n", encoding="utf-8"
        )
        git(artifacts, "init")
        git(artifacts, "config", "user.email", "probe@example")
        git(artifacts, "config", "user.name", "probe")
        git(artifacts, "add", ".")
        git(artifacts, "commit", "-m", "plan")
        sha = git(artifacts, "rev-parse", "HEAD").stdout.strip()

        sheet = tmp / "sheet.json"
        sheet.write_text(
            json.dumps(
                {
                    "seats": {
                        "build": {"harness": "claude", "model": "opus"},
                        "verify": {"harness": "claude", "model": "opus"},
                    }
                }
            ),
            encoding="utf-8",
        )

        seen = {}

        def _mint(argv):
            seen["argv"] = list(argv)

        pkg = {
            "execution_goal": "exec-alpha",
            "planning_goal": str(plan_goal),
            "goals_root": str(goals),
            "lane": "daemon",
            "contract": "build the thing",
            "bound_commit": sha,
            "plan_artifacts": str(artifacts),
            "git_dir": str(artifacts),
            "roster": ["build", "verify"],
            "workflow": "plan-console",
            "catalog_root": str(tmp / "catalog"),
            "sheet": str(sheet),
            "origin_id": "thread-approve-1",
        }
        out, argv = path_b.run_path_b(pkg=pkg, mint=_mint)
        exec_dir = goals / "exec-alpha"
        check(
            "P1",
            bool(out.get("ok")) and exec_dir.is_dir() and (exec_dir / "goal.md").is_file(),
            f"ok={out.get('ok')} exists={exec_dir.is_dir()} record={out.get('record')}",
        )
        check(
            "P2",
            tf.read_bytes() == tf_before,
            "planning goal taskforce.csv changed" if tf.read_bytes() != tf_before else "unchanged",
        )
        check(
            "P3",
            digest_tree(current) == current_before,
            "planning/current/ changed" if digest_tree(current) != current_before else "unchanged",
        )
        used = seen.get("argv") or argv
        joined = " ".join(used)
        aimed = False
        if "--package" in used:
            aimed = used[used.index("--package") + 1] == str(exec_dir)
        check(
            "P4",
            aimed
            and "--goal-local" not in used
            and "--milestone-id" not in used
            and "--nested" not in used,
            f"aimed={aimed} argv={joined}",
        )

        # ── P5 · THE ONE-OFF PLAN ────────────────────────────────────────────────────────────
        # No `workflow` in the package. Before this fix the birth defaulted to a workflow named
        # `execute` that has never existed in any catalog, so every such approve died at the mint;
        # and `contract_file` was resolved against the process cwd, so it died at the scaffold
        # first. Both are measured here on the same act.
        plan_goal2 = goals / "plan-beta"
        pcur = plan_goal2 / "planning" / "current" / "seats" / "exec-one"
        pcur.mkdir(parents=True)
        (plan_goal2 / "planning" / "current" / "manifest.csv").write_text(
            "Seat/workflow,after,i/o,Modality\nexec-one,,\"in: the plan; out: the thing\",agentic\n",
            encoding="utf-8",
        )
        (pcur / "prompt.md").write_text(
            "---\nid: exec-one-role\ndescription: builds the thing\n---\n\n<role>\nAgent type: staff.\n</role>\n",
            encoding="utf-8")
        (pcur / "task.md").write_text(
            "---\nid: build-the-thing\ndescription: build it\n---\n\n<task-goal>\nBuild it.\n</task-goal>\n",
            encoding="utf-8")
        (plan_goal2 / "planning" / "current" / "bindings.json").write_text(
            json.dumps({"seats": {"exec-one": {"harness": "claude", "model": "opus"}}}) + "\n",
            encoding="utf-8")
        (plan_goal2 / "planning" / "execution-contract.md").write_text(
            "# exec-beta\n\nthe contract as the owner approved it\n", encoding="utf-8")
        git(goals, "init")
        git(goals, "config", "user.email", "probe@example")
        git(goals, "config", "user.name", "probe")
        git(goals, "add", "plan-beta")
        git(goals, "commit", "-m", "plan artifacts for approval")
        sha2 = git(goals, "rev-parse", "HEAD").stdout.strip()
        # …and the working tree moves on AFTER the bind, exactly as a live planning goal does.
        (plan_goal2 / "planning" / "execution-contract.md").write_text(
            "# exec-beta\n\nEDITED AFTER THE BIND — must not reach the born goal\n",
            encoding="utf-8")
        (plan_goal2 / "planning" / "current" / "manifest.csv").write_text(
            "Seat/workflow,after,i/o,Modality\nexec-one,,\"EDITED AFTER THE BIND\",agentic\n",
            encoding="utf-8")

        seen2 = {}
        pkg2 = {
            "execution_goal": "exec-beta",
            "planning_goal": str(plan_goal2),
            "goals_root": str(goals),
            "lane": "daemon",
            "contract_file": "planning/execution-contract.md",
            "bound_commit": sha2,
            "plan_artifacts": str(plan_goal2 / "planning"),
            "git_dir": str(goals),
            "roster": ["exec-one"],
            "catalog_root": str(tmp / "catalog"),
            "origin_id": "thread-approve-2",
        }
        out2, argv2 = path_b.run_path_b(pkg=pkg2, mint=lambda a: seen2.setdefault("argv", list(a)))
        beta = goals / "exec-beta"
        used2 = seen2.get("argv") or argv2
        wf2 = used2[used2.index("--workflow") + 1] if "--workflow" in used2 else ""
        bind2 = used2[used2.index("--bindings") + 1] if "--bindings" in used2 else ""
        check(
            "P5a",
            bool(out2.get("ok")) and "--goal-local" in used2 and wf2 == "goal-local"
            and bind2 == str(beta / "planning" / "current" / "bindings.json"),
            f"ok={out2.get('ok')} workflow={wf2!r} bindings={bind2} record={out2.get('record')}",
        )
        copied = beta / "planning" / "current"
        check(
            "P5b",
            (copied / "manifest.csv").is_file() and (copied / "seats" / "exec-one" / "prompt.md").is_file()
            and "EDITED AFTER THE BIND" not in (copied / "manifest.csv").read_text(encoding="utf-8"),
            f"copied={copied.is_dir()} manifest-from-bound-tree="
            f"{(copied / 'manifest.csv').is_file() and 'EDITED' not in (copied / 'manifest.csv').read_text(encoding='utf-8')}",
        )
        body = (beta / "goal.md").read_text(encoding="utf-8") if (beta / "goal.md").is_file() else ""
        check(
            "P5c",
            "the contract as the owner approved it" in body and "EDITED AFTER THE BIND" not in body,
            f"goal.md carries the bound contract={('the contract as the owner approved it' in body)}",
        )

        # ── P6 · THE CATALOG ROOT ────────────────────────────────────────────────────────────
        ws = tmp / "ws"
        (ws / ".rbtv" / "goals").mkdir(parents=True)
        (ws / "rbtv.json").write_text(json.dumps({"rbtv_path": "repo"}) + "\n", encoding="utf-8")
        resolved = path_b.meta_catalog_root(ws / ".rbtv" / "goals")
        bare = tmp / "bare" / ".rbtv" / "goals"
        bare.mkdir(parents=True)
        try:
            path_b.meta_catalog_root(bare)
            code = None
        except Exception as exc:
            code = getattr(exc, "code", None)
        check(
            "P6",
            resolved == (ws / "repo" / "meta") and code == "catalog-root-underivable",
            f"resolved={resolved} refusal={code!r}",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    sys.exit(1 if failures else 0)

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

        # ── P7-P9 · THE ENVELOPE, WRITTEN AT BIRTH (owner-flagged-birth-writes-no-envelope) ────
        # A `scaffold=` stub replaces the real `goal_cli.py` subprocess with a bare mkdir, so these
        # arms exercise only the envelope code path this fix adds, not the scaffold subprocess
        # already proven by P1-P6.
        ws2 = tmp / "ws2"
        goals2 = ws2 / ".rbtv" / "goals"
        goals2.mkdir(parents=True)
        fakerepo = ws2 / "fakerepo"
        (fakerepo / "sub").mkdir(parents=True)
        (ws2 / "rbtv.json").write_text(json.dumps({"rbtv_path": "fakerepo"}) + "\n", encoding="utf-8")
        (ws2 / "1-projects" / "demo").mkdir(parents=True)
        (ws2 / ".rbtv" / "mirror").mkdir(parents=True)  # install-time, not launch-bootstrapped

        def scaffold_mkdir(dest_dir):
            def _s(_pkg):
                dest_dir.mkdir(parents=True, exist_ok=True)
            return _s

        def scaffold_with_preexisting(dest_dir, body):
            def _s(_pkg):
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / "envelope.json").write_text(json.dumps(body) + "\n", encoding="utf-8")
            return _s

        def committed_plan(folder, envelope_body):
            folder.mkdir(parents=True)
            (folder / "contract.md").write_text("build the thing\n", encoding="utf-8")
            (folder / "envelope.json").write_text(json.dumps(envelope_body) + "\n", encoding="utf-8")
            git(folder, "init")
            git(folder, "config", "user.email", "probe@example")
            git(folder, "config", "user.name", "probe")
            git(folder, "add", ".")
            git(folder, "commit", "-m", "plan with envelope")
            return git(folder, "rev-parse", "HEAD").stdout.strip()

        def env_pkg(name, artifacts, sha):
            return {
                "execution_goal": name,
                "planning_goal": str(tmp / f"plan-goal-{name}"),
                "goals_root": str(goals2),
                "lane": "daemon",
                "contract": "build the thing",
                "bound_commit": sha,
                "plan_artifacts": str(artifacts),
                "git_dir": str(artifacts),
                "roster": ["build"],
                "workflow": "plan-console",
                "catalog_root": str(tmp / f"catalog-{name}"),
                "sheet": str(sheet),
                "origin_id": f"thread-approve-{name}",
            }

        # P7 · a declared extraPaths grant that COMPILES → <goal>/envelope.json exists, matches
        # the bound fill-ins, and `envelope/launch.js#loadFillIns` reads it back non-null.
        artifacts7 = tmp / "artifacts7"
        body7 = {"extraPaths": [{"path": "1-projects/demo", "access": "rw"}]}
        sha7 = committed_plan(artifacts7, body7)
        pkg7 = env_pkg("exec-envelope-ok", artifacts7, sha7)
        exec_dir7 = goals2 / "exec-envelope-ok"
        out7, _ = path_b.run_path_b(
            pkg=pkg7, mint=lambda argv: None, scaffold=scaffold_mkdir(exec_dir7)
        )
        env7 = exec_dir7 / "envelope.json"
        written7 = json.loads(env7.read_text(encoding="utf-8")) if env7.is_file() else None
        read_back7 = None
        if env7.is_file():
            node_check = subprocess.run(
                ["node", "-e",
                 "const {loadFillIns}=require(process.argv[1]);"
                 "process.stdout.write(JSON.stringify(loadFillIns(process.argv[2])));",
                 str(ROOT / "ignite" / "envelope" / "launch.js"), str(exec_dir7)],
                capture_output=True, text=True,
            )
            read_back7 = json.loads(node_check.stdout) if node_check.returncode == 0 else None
        check(
            "P7",
            bool(out7.get("ok")) and written7 == body7 and read_back7 == body7,
            f"ok={out7.get('ok')} written={written7} loadFillIns-read-back={read_back7}",
        )

        # P8 · a declared extraPaths grant that REFUSES at compile (rw inside the rbtv repo, no
        # carve) → the birth fails loudly (class envelope-refusal) and the folder is reclaimed —
        # never a goal minted with a crippled or absent envelope.
        artifacts8 = tmp / "artifacts8"
        body8 = {"extraPaths": [{"path": "fakerepo/sub", "access": "rw"}]}
        sha8 = committed_plan(artifacts8, body8)
        pkg8 = env_pkg("exec-envelope-refuse", artifacts8, sha8)
        exec_dir8 = goals2 / "exec-envelope-refuse"
        out8, _ = path_b.run_path_b(
            pkg=pkg8, mint=lambda argv: None, scaffold=scaffold_mkdir(exec_dir8)
        )
        rec8 = out8.get("record") or {}
        check(
            "P8",
            (not out8.get("ok")) and rec8.get("class") == "envelope-refusal" and not exec_dir8.exists(),
            f"ok={out8.get('ok')} class={rec8.get('class')!r} code={rec8.get('code')!r} "
            f"exists={exec_dir8.exists()}",
        )

        # P9 · an envelope.json ALREADY at the destination (a racing watcher, or hand-placed) is
        # left untouched — never clobbered by the plan's own bound fill-ins, and the birth still
        # succeeds.
        artifacts9 = tmp / "artifacts9"
        sha9 = committed_plan(artifacts9, body7)
        pkg9 = env_pkg("exec-envelope-preexisting", artifacts9, sha9)
        exec_dir9 = goals2 / "exec-envelope-preexisting"
        preexisting_body = {"note": "pre-existing, written by a racing watcher"}
        out9, _ = path_b.run_path_b(
            pkg=pkg9, mint=lambda argv: None,
            scaffold=scaffold_with_preexisting(exec_dir9, preexisting_body),
        )
        env9 = exec_dir9 / "envelope.json"
        content9 = json.loads(env9.read_text(encoding="utf-8")) if env9.is_file() else None
        check(
            "P9",
            bool(out9.get("ok")) and content9 == preexisting_body,
            f"ok={out9.get('ok')} content={content9}",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    sys.exit(1 if failures else 0)

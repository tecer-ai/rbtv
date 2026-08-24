#!/usr/bin/env python3
"""Path B: execution-goal birth (spec-planning-door §2.2)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from argv import planning_mint_argv
from failure import (
    CLASS_ATOMIC_CORE_REFUSAL,
    CLASS_ROSTER_NAME_COLLISION,
    CLASS_UNRESOLVABLE_REFERENCE,
    MaterializeFailure,
    ORIGIN_APPROVAL_THREAD,
)
from wrapper import PATH_B, supervised_materialize, uncast_in_sheet

GOAL_CLI = _HERE.parent / "capabilities" / "goals-tree" / "tool" / "goal_cli.py"
MATERIALIZE_PY = _HERE.parent / "team-kit" / "materialize-seats.py"
BOUND_PLAN_NAME = "bound-plan.json"
PASS_ID = "approve-birth"


def _run(argv, **kwargs):
    return subprocess.run(argv, check=False, capture_output=True, text=True, **kwargs)


def _git(repo, *args):
    return _run(["git", "-C", str(repo), *args])


def goal_name_taken(goals_root, name):
    root = Path(goals_root)
    if (root / name).exists():
        return True
    index = root / "goals.csv"
    if not index.is_file():
        return False
    text = index.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    header = lines[0].split(",")
    if "name" not in header:
        return False
    ni = header.index("name")
    for line in lines[1:]:
        cells = line.split(",")
        if ni < len(cells) and cells[ni].strip() == name:
            return True
    return False


def duplicate_seat_ids(roster):
    seen = set()
    dups = []
    for seat in roster:
        key = str(seat).strip()
        if not key:
            continue
        if key in seen:
            dups.append(key)
        else:
            seen.add(key)
    return dups


def commit_exists(git_dir, sha):
    out = _git(git_dir, "cat-file", "-t", sha)
    return out.returncode == 0 and out.stdout.strip() == "commit"


def artifacts_resolvable(git_dir, sha, plan_artifacts):
    artifacts = Path(plan_artifacts)
    if not artifacts.exists():
        return False
    listed = _git(git_dir, "ls-tree", "-r", "--name-only", sha)
    if listed.returncode != 0:
        return False
    names = [ln.strip() for ln in listed.stdout.splitlines() if ln.strip()]
    if not names:
        return False
    try:
        rel = artifacts.resolve().relative_to(Path(git_dir).resolve())
        prefix = "" if str(rel) == "." else str(rel).replace("\\", "/")
    except ValueError:
        prefix = artifacts.name
    if prefix in ("", "."):
        return True
    return any(n == prefix or n.startswith(prefix.rstrip("/") + "/") for n in names)


def resolve_ref_targets(exposes_refs, catalog_root=None):
    if not exposes_refs:
        return
    spec = __import__("importlib.util", fromlist=["spec_from_file_location"]).spec_from_file_location(
        "materialize_seats_ref", MATERIALIZE_PY
    )
    mod = __import__("importlib.util", fromlist=["module_from_spec"]).module_from_spec(spec)
    spec.loader.exec_module(mod)
    for item in exposes_refs:
        comp = Path(item["comp_dir"])
        ref = item["ref"]
        subject = item.get("subject") or ref
        try:
            mod._ref_target(comp, ref, subject)
        except Exception as exc:
            code = getattr(exc, "code", None) or "exposes-ref-dangling"
            raise MaterializeFailure(
                CLASS_UNRESOLVABLE_REFERENCE, code, str(exc), subject
            ) from exc


def validate_mint_plan(pkg):
    name = pkg["execution_goal"]
    goals_root = pkg["goals_root"]
    roster = list(pkg.get("roster") or [])
    if goal_name_taken(goals_root, name):
        raise MaterializeFailure(
            CLASS_ROSTER_NAME_COLLISION,
            "name-exists",
            f"{name}: already exists on the goals tree",
            name,
        )
    dups = duplicate_seat_ids(roster)
    if dups:
        raise MaterializeFailure(
            CLASS_ROSTER_NAME_COLLISION,
            "roster-clash",
            "duplicate seat-id(s): " + ", ".join(dups),
            name,
        )
    git_dir = pkg.get("git_dir") or pkg["plan_artifacts"]
    sha = pkg["bound_commit"]
    if not commit_exists(git_dir, sha):
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "bound-commit-missing",
            f"bound commit {sha} does not exist",
            name,
        )
    if not artifacts_resolvable(git_dir, sha, pkg["plan_artifacts"]):
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "plan-artifacts-unresolvable",
            f"plan artifacts at {sha} are not resolvable",
            name,
        )
    resolve_ref_targets(pkg.get("exposes_refs") or [], pkg.get("catalog_root"))


def run_scaffold(pkg, contract_file):
    name = pkg["execution_goal"]
    argv = [
        sys.executable,
        str(GOAL_CLI),
        "--root",
        str(pkg["goals_root"]),
        "--json",
        "scaffold",
        name,
        "--contract",
        str(contract_file),
        "--lane",
        str(pkg["lane"]),
    ]
    proc = _run(argv)
    if proc.returncode != 0:
        dest = Path(pkg["goals_root"]) / name
        if dest.exists():
            reclaim_execution_goal(pkg["goals_root"], name)
        reason = (proc.stderr or proc.stdout or "scaffold-refused").strip()[:600]
        raise MaterializeFailure(
            CLASS_ROSTER_NAME_COLLISION, "scaffold-refused", reason, name
        )
    dest = Path(pkg["goals_root"]) / name / "planning" / BOUND_PLAN_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "bound_commit": pkg["bound_commit"],
                "plan_artifacts": str(pkg["plan_artifacts"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def reclaim_execution_goal(goals_root, name):
    goal_dir = Path(goals_root) / name
    _run(
        [
            sys.executable,
            str(GOAL_CLI),
            "--root",
            str(goals_root),
            "teardown",
            name,
            "--yes",
        ]
    )
    if goal_dir.exists():
        shutil.rmtree(goal_dir)
    _run([sys.executable, str(GOAL_CLI), "--root", str(goals_root), "reindex"])


def run_path_b(*, pkg, mint=None, scaffold=None, reclaim=None, resolve_refs=None):
    name = pkg["execution_goal"]
    new_folder = Path(pkg["goals_root"]) / name
    planning_goal = Path(pkg["planning_goal"])
    roster = list(pkg.get("roster") or [])
    sheet = pkg.get("sheet")
    origin_id = pkg.get("origin_id") or "approval-thread"

    def _validate():
        if resolve_refs is not None:
            local = dict(pkg)
            local["exposes_refs"] = local.get("exposes_refs") or []
            validate_mint_plan({**local, "exposes_refs": []})
            if local.get("exposes_refs"):
                resolve_refs(local["exposes_refs"])
        else:
            validate_mint_plan(pkg)

    def _uncast():
        if not sheet:
            return []
        return uncast_in_sheet(sheet, roster)

    def _scaffold():
        if scaffold is not None:
            scaffold(pkg)
            return
        contract_text = pkg.get("contract")
        contract_file = pkg.get("contract_file")
        tmp = None
        if contract_file:
            src = Path(contract_file)
        else:
            tmp = tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8"
            )
            tmp.write(contract_text or "execution goal\n")
            tmp.close()
            src = Path(tmp.name)
        try:
            run_scaffold(pkg, src)
        finally:
            if tmp is not None:
                Path(tmp.name).unlink(missing_ok=True)

    argv = planning_mint_argv(
        goal_folder=str(new_folder),
        catalog_root=pkg.get("catalog_root") or str(pkg["goals_root"]),
        sheet=sheet or str(new_folder / "bindings.json"),
        workflow=pkg.get("workflow") or "execute",
    )

    def _mint():
        if mint is not None:
            mint(argv)
            return
        try:
            subprocess.run(
                [sys.executable, *argv],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            code = "materialize-refused"
            payload = exc.stdout or ""
            try:
                code = (json.loads(payload).get("refusal") or {}).get("code") or code
            except json.JSONDecodeError:
                pass
            reason = ((exc.stdout or "") + (exc.stderr or "")).strip()[:600]
            raise MaterializeFailure(
                CLASS_ATOMIC_CORE_REFUSAL, code, reason or code, name
            ) from exc

    def _reclaim():
        if reclaim is not None:
            reclaim()
            return
        reclaim_execution_goal(pkg["goals_root"], name)

    return supervised_materialize(
        path=PATH_B,
        goal_folder=str(new_folder),
        record_goal_folder=str(planning_goal),
        planning_pass_id=pkg.get("planning_pass_id") or PASS_ID,
        origin=ORIGIN_APPROVAL_THREAD,
        origin_id=origin_id,
        subject=name,
        validate=_validate,
        uncast=_uncast,
        scaffold=_scaffold,
        mint=_mint,
        reclaim=_reclaim,
        envelope_stamp=pkg.get("envelope_stamp"),
    ), argv


def load_package(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p = argparse.ArgumentParser(description="Path B supervised execution-goal birth.")
    p.add_argument("--package", required=True, help="approve-package JSON")
    args = p.parse_args(argv)
    pkg = load_package(args.package)
    out, _argv = run_path_b(pkg=pkg)
    json.dump({"ok": out["ok"], "record": out.get("record")}, sys.stdout)
    sys.stdout.write("\n")
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

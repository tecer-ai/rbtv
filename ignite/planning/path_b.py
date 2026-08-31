#!/usr/bin/env python3
"""Path B: execution-goal birth (spec-planning-door §2.2)."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "coord"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from argv import planning_mint_argv
from failure import (
    CLASS_ATOMIC_CORE_REFUSAL,
    CLASS_ENVELOPE_REFUSAL,
    CLASS_ROSTER_NAME_COLLISION,
    CLASS_UNRESOLVABLE_REFERENCE,
    MaterializeFailure,
    ORIGIN_APPROVAL_THREAD,
    class_for_code,
)
from identity import STAFF_SEATS, SUMMONED_SEATS  # noqa: E402  (the room's own vocabulary, F6)
from wrapper import PATH_B, supervised_materialize, uncast_in_sheet

GOAL_CLI = _HERE.parent / "operator" / "goals-tree" / "tool" / "goal_cli.py"
MATERIALIZE_PY = _HERE / "materialize-seats.py"
BOUND_PLAN_NAME = "bound-plan.json"
TASKFORCE_NAME = "taskforce.csv"
PASS_ID = "approve-birth"

# `envelope/launch.js#FILL_IN_NAME` — the SOLE reader of this filename, and the SOLE thing that
# makes a born goal's plan-declared write grants real. Nothing wrote it (owner-flagged
# `owner-flagged-birth-writes-no-envelope`, 2026-08-30); this birth is the fix, at the cause.
ENVELOPE_ARTIFACT_NAME = "envelope.json"
COMPILER_JS = _HERE.parent / "envelope" / "compiler.js"

# `materialize-seats.py#GOAL_LOCAL_SOURCE` — where a goal's OWN planning pass leaves the seats it
# authored, and therefore where `--goal-local` reads them from. Path B copies this ONE folder out
# of the planning goal's bound tree and into the goal it births; nothing else of the plan travels.
PLAN_CURRENT = ("planning", "current")

# The catalog root a birth mints from, as `unbuilt-seats.js#repoRootOf` + `PLANNING_MODULE` resolve
# it: the rbtv REPO's `meta` tree, addressed through the workspace's own book (`rbtv.json`'s
# `rbtv_path`), never a hardcoded path and never the goals tree. A catalog root that carries no
# staff component mints a goal with NO CHAIRS — see `refuse_if_chairless`.
META_MODULE = "meta"

# ⚠ THE BASE TEXTS A BRAND-NEW GOAL PACKAGE IS COMPLETED WITH, and they are the OWNER'S, not this
# module's. `plan_package_creation` refuses `create-inputs-missing` on a folder with no
# `taskforce.csv` unless both are named, because it "never invents run conventions and never
# defaults a floor" — and a birth is exactly that folder. The creation ROUTE answers the same
# question with the goal-generic starter set the owner authored and approved for this path
# (`d-owner-starter-set-approved-0808`), named in `spawn-profiles.yaml`'s `goal-creation-request`
# argv as `ignite/coord/starter-set/{CLAUDE.md,budget.json}`. A birth has no config surface and no
# human caller to name them, so it resolves the SAME two files out of the repo it ships in — a
# repo-relative address, never an instance path, and never invented content.
STARTER_SET = _HERE.parent / "coord" / "starter-set"


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


def _rbtv_repo_root(goals_root):
    """(workspace, rbtv repo root), resolved through the book — never hardcoded.

    ⚠ RESOLVED THROUGH THE BOOK, NEVER HARDCODED. `meta/` moved out of `.rbtv/mirror/` into the
    repo on 2026-08-22 and every reader that had composed the mirror path went stale in the same
    second (919e1595). `unbuilt-seats.js` `repoRootOf`/`buildGoalLocalSeats` — the JS twin of this
    act — reads `rbtv.json`'s `rbtv_path` at the workspace. This does the same, from the same book,
    so no two callers can address different repos. Shared by `meta_catalog_root` (joins `meta`) and
    the envelope compile-check (needs the bare repo root, the same one `envelope/launch.js` passes
    `compile()` as `rbtvRepo`).
    """
    workspace = Path(goals_root).resolve().parent.parent
    book = workspace / "rbtv.json"
    try:
        rbtv_path = str((json.loads(book.read_text(encoding="utf-8")) or {}).get("rbtv_path") or "").strip()
    except (OSError, ValueError) as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "catalog-root-underivable",
            f"{book} — the book that records `rbtv_path` — is not readable JSON ({exc}); the "
            "birth has no catalog to mint the goal's seats and chairs from",
        ) from exc
    if not rbtv_path:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "catalog-root-underivable",
            f"{book} carries no `rbtv_path` — the birth has no catalog to mint the goal's seats "
            "and chairs from",
        )
    root = Path(rbtv_path)
    if not root.is_absolute():
        root = (workspace / root).resolve()
    return workspace, root


def meta_catalog_root(goals_root):
    """The catalog a birth mints from: the rbtv repo's `meta` tree.

    ⚠ THE DEFECT THIS CLOSES (G-leader-0827-2224, measured on
    `scratch-tool-inventory-8`). This defaulted to `goals_root` — the GOALS TREE, which carries no
    component catalog at all, let alone a staff one. `mint_staff_chairs` skips a chair its catalog
    carries no row for (deliberately: a fixture catalog must render as it always did), so a birth
    against that default produced a goal with NO `leader` and NO `goal-master` and reported
    SUCCESS. A chairless goal has no chair for a routed FAIL, a mid-run ask or the session-closer's
    staff mail, and no seat an owner message in its channel can reach — it exists and can never
    finish.
    """
    _workspace, root = _rbtv_repo_root(goals_root)
    return root / META_MODULE


def _bound_repo_and_rel(pkg):
    """(repo, rel) placing `plan_artifacts` inside its own git repo.

    Shared by `stage_plan_artifacts` (extracts the whole tree) and `bound_envelope_fillins`
    (reads one optional file) so the two can never derive different repos for the same package.
    """
    git_dir = pkg.get("git_dir") or pkg["plan_artifacts"]
    top = _git(git_dir, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "plan-artifacts-unstageable",
            f"{git_dir} is not inside a git repository — the bound tree cannot be read",
        )
    repo = Path(top.stdout.strip())
    try:
        rel = Path(pkg["plan_artifacts"]).resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "plan-artifacts-unstageable",
            f"{pkg['plan_artifacts']} is not inside {repo} — the bound tree cannot be read",
        ) from exc
    return repo, rel


def bound_envelope_fillins(pkg):
    """The plan's declared write-grant fill-ins, read FROM THE BOUND COMMIT — never the working
    tree [T5-R5, the same discipline `bound_contract_file` already applies to the contract].

    ⚠ WHY A ONE-PATH `git show`, NOT `stage_plan_artifacts`. Most one-off plans declare NO write
    grant at all — `envelope.json` absent from the bound tree is the COMMON case — and
    `stage_plan_artifacts` pays for a full `git archive` extraction of the whole plan. Paying that
    cost on every birth just to test one optional file is the cost the staging design already
    rejected (`stage_plan_artifacts` itself only runs when `contract_file` or `goal_local` is set).
    A targeted `git show <sha>:<rel>` costs one process, win or lose.

    Returns `None` when the bound commit carries no `<plan_artifacts>/envelope.json` — not a
    refusal, because a plan that needs no write grant outside its own goal folder is legitimate and
    common, and the born goal still boots (under `compilePlanning`, exactly as it does today).
    """
    repo, rel = _bound_repo_and_rel(pkg)
    sha = pkg["bound_commit"]
    rel_path = (rel / ENVELOPE_ARTIFACT_NAME).as_posix() if str(rel) != "." else ENVELOPE_ARTIFACT_NAME
    tree_ref = f"{sha}:{rel_path}"
    exists = _git(repo, "cat-file", "-e", tree_ref)
    if exists.returncode != 0:
        return None
    show = _git(repo, "show", tree_ref)
    if show.returncode != 0:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "envelope-unreadable",
            f"{tree_ref} exists in the bound tree but `git show` could not read it: "
            f"{(show.stderr or '').strip()[:300]}",
            pkg["execution_goal"],
        )
    try:
        data = json.loads(show.stdout)
    except json.JSONDecodeError as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "envelope-invalid-json",
            f"{tree_ref}: not valid JSON ({exc})",
            pkg["execution_goal"],
        ) from exc
    if not isinstance(data, dict):
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "envelope-invalid-json",
            f"{tree_ref}: must be a JSON object carrying namedRepos/projectFolder/"
            "credentialNames/extraPaths",
            pkg["execution_goal"],
        )
    return data


def compile_check_envelope(*, goals_root, goal_id, fillins, name):
    """Run the plan's fill-ins through the DEPLOYED `compiler.compile()` shape, the way the
    planning seats measured it live (`evidence-b2-product-home.md`). A birth that would produce a
    refusing envelope FAILS LOUDLY here — never mints a goal that boots crippled and silent.

    ⚠ SCRATCH AND THE ENDING STORE MUST EXIST BEFORE THE COMPILE, ORDER IS LOAD-BEARING — the same
    ordering `envelope/launch.js#admitLaunch` documents for its own `ensureGoalScratch` and
    `ensureEndingStore` calls: template family 4 bakes `{goal}/scratch` and family 8 bakes
    `{workspace}/.rbtv/runtime/ignite`, and a compile-first order refuses `unresolved` on a fresh
    workspace or a fresh goal regardless of the plan's own fill-ins. These two mkdirs are the
    birth-side half of that same precondition (measured: `compile()` refused
    `unresolved …/.rbtv/runtime/ignite` on a fresh fixture workspace before this was added).
    """
    _workspace, rbtv_repo = _rbtv_repo_root(goals_root)
    workspace_root = Path(goals_root).resolve().parent.parent
    goal_dir = Path(goals_root) / name
    (goal_dir / "scratch").mkdir(parents=True, exist_ok=True)
    (workspace_root / ".rbtv" / "runtime" / "ignite").mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "workspaceRoot": str(workspace_root),
        "goalId": goal_id,
        "rbtvRepo": str(rbtv_repo),
        "namedRepos": fillins.get("namedRepos") or [],
        "projectFolder": fillins.get("projectFolder"),
        "credentialNames": fillins.get("credentialNames") or [],
        "extraPaths": fillins.get("extraPaths") or [],
    })
    proc = _run(
        [
            "node",
            "-e",
            "const {compile}=require(process.argv[1]);"
            "const raw=JSON.parse(require('fs').readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify(compile(raw)));",
            str(COMPILER_JS),
        ],
        input=payload,
    )
    if proc.returncode != 0:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "envelope-compile-unreachable",
            f"node {COMPILER_JS} did not run: {(proc.stderr or '').strip()[:400]}",
            name,
        )
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "envelope-compile-unreachable",
            f"node {COMPILER_JS} printed non-JSON: {proc.stdout[:400]}",
            name,
        ) from exc
    if not verdict.get("ok"):
        raise MaterializeFailure(
            CLASS_ENVELOPE_REFUSAL,
            "envelope-fillins-refused",
            f"the plan's declared fill-ins refuse at compile: {json.dumps(verdict.get('refuse'))}"[:600],
            name,
        )
    return verdict


def write_envelope_if_absent(goal_dir, fillins):
    """Write `<goal_dir>/envelope.json`, atomically, UNLESS one is already there.

    ⚠ TOLERATE A RACING WRITER, NEVER `tmp + rename` HERE. `land-envelope.sh` (the hand-armed
    workaround for the one goal blocked on this defect before this fix landed) polls for the same
    destination and may win the race. A plain `tmp + rename` unconditionally REPLACES whatever is
    at `dest` — exactly the silent clobber this must never do. `O_CREAT|O_EXCL` is the stronger
    primitive: open-and-create is one atomic syscall, so there is no window between "check it's
    absent" and "write it" for a second writer to land in, and the LOSER of the race gets
    `FileExistsError` instead of overwriting the winner. The payload itself is small enough that
    one `os.write()` cannot tear, so the exclusive-create doubles as the whole-file guarantee
    `tmp + rename` exists to provide.
    Returns `"written"` or `"already-present"`; never raises on the losing side of the race.
    """
    dest = Path(goal_dir) / ENVELOPE_ARTIFACT_NAME
    body = json.dumps(fillins, indent=2, sort_keys=True) + "\n"
    try:
        fd = os.open(str(dest), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return "already-present"
    try:
        os.write(fd, body.encode("utf-8"))
    finally:
        os.close(fd)
    return "written"


def stage_plan_artifacts(pkg, dest):
    """Extract the approved plan's artifacts AS THE BOUND COMMIT HOLDS THEM into `dest`.

    ⚠ THE TREE THE OWNER APPROVED IS THE TREE THE BIRTH READS [T5-R5]. `plan_artifacts` names a
    live folder that keeps changing after the approval is sent — a seat re-runs, a leader re-binds
    — so every byte this birth carries into the new goal (the contract that becomes its `goal.md`,
    the `planning/current/` its seats are minted from) is read out of the commit the approval names
    rather than off disk. `artifacts_resolvable` already proved that path exists at that sha; this
    is the same discipline one step further, from "resolvable" to "read".
    """
    repo, rel = _bound_repo_and_rel(pkg)
    sha = pkg["bound_commit"]
    tree = sha if str(rel) == "." else f"{sha}:{rel.as_posix()}"
    proc = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", tree],
        check=False, capture_output=True,
    )
    if proc.returncode != 0:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "plan-artifacts-unstageable",
            f"git archive {tree}: {(proc.stderr or b'').decode('utf-8', 'replace').strip()[:300]}",
        )
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        # `data` is the extraction filter that refuses absolute paths, `..` escapes, links out of
        # the destination and special files — the tree came out of a commit, but a commit is
        # content a seat authored, and an archive is exactly the shape that turns authored content
        # into a write outside the destination.
        tar.extractall(dest, filter="data")
    return dest


def bound_contract_file(pkg, staged, planning_goal):
    """The contract file, as the bound commit holds it. Refuses rather than defaulting.

    ⚠ THE DEFECT THIS CLOSES. `contract_file` was used BARE — `Path(pkg["contract_file"])`, a
    relative path resolved against whatever directory the daemon's python happened to be started
    in, never joined to the planning goal it is relative to. The live approve on
    `scratch-tool-inventory-8` therefore refused
    `--contract planning/execution-contract.md: No such file or directory` with the approval
    already spent. The path is relative TO THE PLANNING GOAL (that is how the seat that wrote the
    package spelled it), it must live under `plan_artifacts` (a contract outside the plan is not
    part of what the owner approved), and it is read from the bound tree.
    """
    src = Path(pkg["contract_file"])
    if not src.is_absolute():
        src = Path(planning_goal) / src
    artifacts = Path(pkg["plan_artifacts"]).resolve()
    try:
        rel = src.resolve().relative_to(artifacts)
    except ValueError as exc:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "contract-outside-plan-artifacts",
            f"{src} is not under the approved plan artifacts ({artifacts}) — a contract the "
            "approval did not bind is not this goal's to be born under",
        ) from exc
    landed = Path(staged) / rel
    if not landed.is_file():
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "contract-not-in-bound-tree",
            f"the bound commit {pkg['bound_commit']} carries no {rel.as_posix()} under the plan "
            "artifacts — the contract the goal would be born under is not in the tree the owner "
            "approved",
        )
    return landed


def taskforce_seats(goal_folder):
    """The seat ids a goal's registry carries."""
    path = Path(goal_folder) / TASKFORCE_NAME
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8", newline="") as fh:
        return {(row.get("seat") or "").strip() for row in csv.DictReader(fh)}


def refuse_if_chairless(goal_folder, name):
    """A goal born without its chairs is refused, and the birth is reclaimed.

    ⚠ WHY THE REFUSAL IS HERE AND NOT IN THE MINTER. `mint_staff_chairs` SKIPS a chair whose row
    the catalog does not carry, and that silence is correct where it lives: a materialize against a
    fixture or foreign catalog must render exactly as it did before. A BIRTH is the one caller for
    which the skip is fatal — nobody is watching, the goal is the daemon's from this second on, and
    a goal with no `leader` has no chair for a routed FAIL, a mid-run ask or the session-closer's
    staff mail to reach, while a goal with no `goal-master` has no seat an owner message in its
    channel can sit in. So the birth checks its own PRODUCT, which catches every reason a chair
    can be missing (no catalog row, no casting sheet, a standing ending) rather than only the one
    that was measured.
    """
    seats = taskforce_seats(goal_folder)
    missing = [c for c in (*STAFF_SEATS, *SUMMONED_SEATS) if c not in seats]
    if missing:
        raise MaterializeFailure(
            CLASS_ATOMIC_CORE_REFUSAL,
            "birth-chairless",
            f"the goal was minted without its chair(s): {', '.join(missing)} — a goal with no "
            f"leader has nothing to route a FAIL, an ask or staff mail to, and a goal with no "
            f"goal-master has no seat for an owner message in its channel. Check the catalog root "
            f"carries the staff component and that each chair is cast",
            name,
        )


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
        # ⚠ THE FLAG IS THE DECLARATION THAT THIS ACT MINTS, AND PATH B DOES.
        # `cmd_scaffold` refuses `daemon-lane-unmaterialized` on a daemon-lane goal without it,
        # because `scaffold` alone writes no `taskforce.csv` and `lane-watch.js#runLaneWatch`
        # adopts a daemon-lane goal only when one exists — a goal scaffolded and left is skipped on
        # every cadence forever. Path B mints in the SAME act (the `mint` step below, under the
        # goal's own lock), which is exactly what the flag declares. Without it every daemon-lane
        # birth refused, and the pipeline's only way past that refusal was to declare
        # `lane: console` — a goal the daemon never picks up at all.
        "--materialize-follows",
    ]
    # Carry the plan's declared per-goal owner-contact policy through, when it declared one.
    # `cmd_scaffold` already honors `--execution-mode` correctly (it derives none itself); the
    # birth defaulted to autonomous only because nothing on this path ever passed the flag —
    # G-plan-drafter-0828-1848.
    execution_mode = pkg.get("execution_mode")
    if execution_mode:
        argv.extend(["--execution-mode", str(execution_mode)])
    proc = _run(argv)
    if proc.returncode != 0:
        dest = Path(pkg["goals_root"]) / name
        if dest.exists():
            reclaim_execution_goal(pkg["goals_root"], name)
        # The CODE the door refused with, never the call site's guess at a class: `goal_cli.py`
        # prints `{"ok": false, "refusal": {"code": …}}` on stdout for every coded refusal under
        # `--json`, which this argv passes. `class_for_code` maps it; an uncoded refusal keeps the
        # generic code and lands in `atomic-core-refusal`, where a gate refusal belongs.
        code = "scaffold-refused"
        try:
            code = (json.loads(proc.stdout or "").get("refusal") or {}).get("code") or code
        except (json.JSONDecodeError, AttributeError):
            pass
        reason = (proc.stderr or proc.stdout or "scaffold-refused").strip()[:600]
        raise MaterializeFailure(class_for_code(code), code, reason, name)
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


# ── THE TWO MINT ROUTES, AND WHICH PACKAGE TAKES WHICH ───────────────────────────────────────
#
# A package that DECLARES a `workflow` (and the `sheet` that casts it) is minted from the COMPONENT
# CATALOG, exactly as before: its execution seats are cataloged definitions someone maintains.
#
# A package that declares NO workflow is a ONE-OFF PLAN, and there is no catalog workflow for it —
# the defaulted `"execute"` this used to fall back on names a workflow that has never existed
# (`meta/planning/workflows/` carries d13-replan, forge and plan-console), so every such birth
# refused at the catalog. Its seats are the ones THE PLAN ITSELF AUTHORED, and the materializer
# already has a lane for exactly that: `--goal-local` reads `planning/current/` (manifest.csv plus
# `seats/<seat>/` prompt+task pairs) instead of the catalog. So the birth copies that folder out of
# the planning goal's BOUND TREE into the goal it births, and mints the copy.
#
# ⚠ `--goal-local` READS THE PACKAGE'S OWN FOLDER, WHICH IS WHY THE COPY COMES FIRST. The lane is
# built at `<package>/planning/current/seat-lane/` from `<package>/planning/current/`, so aiming it
# at a goal that does not hold the plan would either find nothing or, worse, read a foreign goal's
# pass. `20260824-c-path-b-execution-goal-birth-vi` states it as "Path B must not pass --goal-local
# … those target the same goal, never a foreign one" — and after the copy the goal it targets IS
# the born goal, which is the only shape that satisfies that rule.
def run_path_b(*, pkg, mint=None, scaffold=None, reclaim=None, resolve_refs=None):
    name = pkg["execution_goal"]
    new_folder = Path(pkg["goals_root"]) / name
    planning_goal = Path(pkg["planning_goal"])
    roster = list(pkg.get("roster") or [])
    workflow = str(pkg.get("workflow") or "").strip()
    goal_local = not workflow
    origin_id = pkg.get("origin_id") or "approval-thread"
    # The plan, staged out of the bound commit, plus what validate derived from it. Filled by
    # `_validate` and read by `_uncast`, `_scaffold` and `_mint` — one staging, every reader.
    plan = {}

    def _validate():
        if resolve_refs is not None:
            local = dict(pkg)
            local["exposes_refs"] = local.get("exposes_refs") or []
            validate_mint_plan({**local, "exposes_refs": []})
            if local.get("exposes_refs"):
                resolve_refs(local["exposes_refs"])
        else:
            validate_mint_plan(pkg)
        # Staged only when something is READ out of it — the contract, the plan's own seats, or
        # both. A package that carries neither (a cataloged workflow with inline contract text)
        # reaches the same birth it always did, and never pays for a git archive.
        if pkg.get("contract_file") or goal_local:
            plan["staged"] = stage_plan_artifacts(pkg, Path(plan["tmp"]) / "plan")
        if pkg.get("contract_file"):
            plan["contract"] = bound_contract_file(pkg, plan["staged"], planning_goal)
        plan["catalog_root"] = (
            pkg.get("catalog_root") or str(meta_catalog_root(pkg["goals_root"]))
        )
        # The goal-local sheet is the plan's own, at the address it lands under IN THE BORN GOAL —
        # `planning/current/bindings.json`, the spelling `unbuilt-seats.js#GOAL_LOCAL_SHEET` already
        # uses for a goal's authored seats.
        default_sheet = (new_folder.joinpath(*PLAN_CURRENT) / "bindings.json" if goal_local
                         else new_folder / "bindings.json")
        mint_args = {
            "goal_folder": str(new_folder),
            "catalog_root": plan["catalog_root"],
            "sheet": str(pkg.get("sheet") or default_sheet),
            "goal_local": goal_local,
        }
        if workflow:
            mint_args["workflow"] = workflow
        # A birth completes a folder `rbtv-goal scaffold` has just created and that carries no
        # registry, so the two caller-supplied base texts are required. Path A mints into a goal
        # that already has one and passes neither.
        mint_args["creation_inputs"] = (STARTER_SET / "CLAUDE.md", STARTER_SET / "budget.json")
        plan["argv"] = planning_mint_argv(**mint_args)

    def _uncast():
        # Only a sheet that can be READ at this moment — before the first write. A declared sheet
        # is one; so is the plan's own, out of the staged bound tree. The born goal's copy is not:
        # the folder does not exist yet, which is why the defaulted path was never checked here.
        sheet = pkg.get("sheet")
        if not sheet and goal_local and plan.get("staged"):
            sheet = Path(plan["staged"]) / "current" / "bindings.json"
        if not sheet or not roster:
            return []
        return uncast_in_sheet(sheet, roster)

    def _scaffold():
        if scaffold is not None:
            scaffold(pkg)
            return
        tmp = None
        if plan.get("contract"):
            src = plan["contract"]
        else:
            tmp = tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8"
            )
            tmp.write(pkg.get("contract") or "execution goal\n")
            tmp.close()
            src = Path(tmp.name)
        try:
            run_scaffold(pkg, src)
        finally:
            if tmp is not None:
                Path(tmp.name).unlink(missing_ok=True)
        if goal_local:
            # The plan's own seats travel into the goal they staff, as the approved commit holds
            # them. Copied rather than referenced: the lane is rebuilt inside the package on every
            # invocation, and a born goal that reached back into the planning goal for its seat
            # definitions would re-read them after the plan moved on.
            shutil.copytree(
                Path(plan["staged"]) / "current",
                new_folder.joinpath(*PLAN_CURRENT),
                dirs_exist_ok=True,
            )

    def _mint():
        argv = plan["argv"]
        if mint is not None:
            mint(argv)
        else:
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
                    class_for_code(code), code, reason or code, name
                ) from exc
            # The mint reports SUCCESS with a chair missing (it degrades a chair refusal to a
            # warning so a materialized goal is never left half-registered). A birth cannot: the
            # check is on the product the real minter just wrote, and a chairless goal is
            # reclaimed.
            refuse_if_chairless(new_folder, name)
        # THE ENVELOPE, IN THE SAME ACT THAT MINTS — runs for both the real subprocess mint and an
        # injected stub, because writing the born goal's write grants is this birth's own remit,
        # never the minter's. `scaffolded` is already `True` in `supervised_materialize` by the
        # time `_mint` runs, so a refusal raised here reclaims the folder exactly as a chairless
        # mint does — never a goal minted crippled and silent.
        _land_envelope()

    def _land_envelope():
        fillins = bound_envelope_fillins(pkg)
        if fillins is None:
            return
        dest = new_folder / ENVELOPE_ARTIFACT_NAME
        if dest.exists():
            # A file is ALREADY here — a racing watcher, or a hand-placed one. Never judge it by
            # refusing the birth over OUR fill-ins failing to compile: the file already sitting on
            # disk is not this act's to overwrite or to gate on.
            print(
                f"path_b: {name}: {dest} already exists — left untouched, its content stands "
                "(the plan's bound fill-ins were not applied)",
                file=sys.stderr,
            )
            return
        compile_check_envelope(
            goals_root=pkg["goals_root"], goal_id=name, fillins=fillins, name=name
        )
        if write_envelope_if_absent(new_folder, fillins) == "already-present":
            print(
                f"path_b: {name}: {dest} appeared between the check and the write — left "
                "untouched, its content stands",
                file=sys.stderr,
            )

    def _reclaim():
        if reclaim is not None:
            reclaim()
            return
        reclaim_execution_goal(pkg["goals_root"], name)

    plan["tmp"] = tempfile.mkdtemp(prefix="path-b-plan-")
    try:
        out = supervised_materialize(
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
        )
    finally:
        shutil.rmtree(plan["tmp"], ignore_errors=True)
    return out, plan.get("argv") or []


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

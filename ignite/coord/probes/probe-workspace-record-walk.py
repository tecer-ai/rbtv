#!/usr/bin/env python3
"""probe-workspace-record-walk.py — a `.rbtv/` that does not root the install is not a workspace.

WHAT WAS BROKEN. Two walkers in this kit resolved the workspace by the presence of a bare `.rbtv/`
DIRECTORY: `ending_store.ending_store_db` (which then `mkdir(parents=True)`'d a `heart.db` under
whatever it landed on, and, finding nothing at all, CREATED one at the start dir) and
`ruling.workspace_root` (whose own docstring promised it resolved "the way
`ending_store.ending_store_db` resolves it" — a promise held by a comment). D27's definition, and
the one `ignite/ignite-cli/lib/config.js#findInstallRoot` implements, is the INSTALL RECORD:
the nearest ancestor holding `.rbtv/modules/ignite/server.json`. The same wrong rule at
`ignite/deploy/probe-suite-scheduled.py` and in the watchdog cost the false `probe-suite DOWN`
alarm of 2026-08-28 03:02–07:35Z; the stray `3-resources/tools/rbtv/.rbtv/runtime/ignite/heart.db`
found beside it that morning came from THIS kit's copy (5815fbaa, memory entry
`observation/20260828-i-a-rbtv-that-does-not-root-the`). The cost is silent by construction: a
stray `.rbtv/` is gitignored (`.gitignore:76 **/.rbtv/`), so no `git status` and no review shows
the decoy, and an ending written to a store no daemon reads reads exactly like a recorded one.

WHAT THIS MEASURES. The fixture is the outage in miniature — an install-rooted `<ws>`, a nested
`<ws>/sub/repo/.rbtv/runtime/` holding no record (the decoy a probe run from a repo root plants),
and the goal package four levels below it. From there:

  * the resolver answers `<ws>` and NOT the nested repo, names the bare `.rbtv/` it walked past,
    and creates nothing;
  * the RULING path — a real `supervise instruct … --go` — lands its inbox under `<ws>`, and the
    nested repo stays empty;
  * moving the record INTO the nested repo moves the answer with it (nearest-ancestor-wins is
    unchanged, and the answer tracks the record and nothing else);
  * a tree with no record anywhere and no env override REFUSES, at both doors, naming the record —
    and plants no `.rbtv/` anywhere in it, which is the whole point of the refusal;
  * `ENDING_STORE_DB` still wins outright, unvalidated, as the first branch.

RED CONTROLS, one per surface, both by MUTATED SOURCE rather than by argument: a copy of
`ending_store.py` with the record test swapped back to `os.path.isdir(d/'.rbtv')` resolves to the
nested repo and answers a `heart.db` path inside it; and a copy of the whole kit carrying that same
mutated module writes the leader's inbox into the nested repo through the real `supervise instruct`
— which is the ruling half riding the one shared walker, demonstrated rather than asserted.

FIXTURE SAFETY. Everything happens under the OS temp dir: its own workspaces, its own store, its
own copy of the kit. No live workspace, store, goal or daemon is read or written, and `node` is
reached only for the instruction-kind list and the store CLI, both against scratch paths.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
IGNITE = KIT.parent
ENDING_STORE_PY = KIT / "ending_store.py"
OUT = HERE / "probe-workspace-record-walk.out"
RECORD_REL = Path(".rbtv") / "modules" / "ignite" / "server.json"
INSTRUCTIONS_REL = Path(".rbtv") / "runtime" / "ignite" / "leader-instructions"
CHECKS = []
T0 = time.time()


def check(name, ok, evidence=None):
    CHECKS.append({"name": name, "pass": bool(ok), "evidence": evidence or {}})


def load_module(path, name):
    """Import one file as a module. `ending_store.py` is stdlib-only and takes nothing off
    `coord.py`'s namespace, so it loads standalone — which is what lets the mutant below be a
    MUTATED SOURCE rather than a monkeypatched attribute."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tree(root):
    """Every path under `root`, relative — the assertion surface for "created nothing"."""
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))


def seed_record(root):
    p = Path(root) / RECORD_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"machines": {}}\n', encoding="utf-8")
    return Path(root)


def seed_package(pkg, seats=("leader", "worker-a", "worker-b")):
    """A goal package `require_seat` accepts: a seat descriptor per seat and a taskforce."""
    for seat in seats:
        (pkg / "seats" / seat).mkdir(parents=True, exist_ok=True)
        (pkg / "seats" / seat / "seat.md").write_text(
            f"---\nseat: {seat}\nharness: bash\nmodel: probe\n---\n\nbody\n", encoding="utf-8")
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (pkg / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        + "".join(f"tf,{s},,bash,probe,high,35,\n" for s in seats), encoding="utf-8")
    return pkg


def make_fixture(root, nested_record=False):
    """The outage in miniature: `<ws>` roots the install, `<ws>/sub/repo/` holds a bare `.rbtv/`
    (the decoy), and the goal package sits below the decoy so every walk passes it."""
    ws = Path(root) / "ws"
    seed_record(ws)
    repo = ws / "sub" / "repo"
    (repo / ".rbtv" / "runtime").mkdir(parents=True)
    if nested_record:
        seed_record(repo)
    return ws, repo, seed_package(repo / "some" / "goal")


def supervise_instruct(supervise_py, pkg, seat="worker-a", to_seat="worker-b"):
    env = dict(os.environ)
    env.pop("ENDING_STORE_DB", None)
    env.pop("TMUX", None)
    proc = subprocess.run(
        [sys.executable, str(supervise_py), "--package", str(pkg), "--as", "leader",
         "instruct", seat, "reassign", "--to-seat", to_seat, "--go"],
        capture_output=True, text=True, cwd=str(pkg), env=env, timeout=180)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


ROOT = Path(tempfile.mkdtemp(prefix="probe-ws-record-"))
try:
    es = load_module(ENDING_STORE_PY, "probe_ending_store")

    # ---- A. THE RESOLUTION, from below the decoy -------------------------------------------
    ws, repo, pkg = make_fixture(ROOT / "a")
    err = io.StringIO()
    with redirect_stderr(err):
        resolved = es.workspace_root(pkg)
        db = es.ending_store_db(pkg)
    stderr_text = err.getvalue()

    check("A1: from a goal package four levels below a nested bare `.rbtv/`, the resolver answers "
          "the INSTALL-ROOTED `<ws>` and not the nested repo — the decoy is what the pre-fix walk "
          "stopped at, and it is the only difference between the two answers",
          resolved == ws, {"resolved": str(resolved), "ws": str(ws), "repo": str(repo)})

    check("A2: the ARTIFACT PATH follows the resolution — the store lands at "
          "`<ws>/.rbtv/runtime/ignite/heart.db`, the file the daemon reads, not at a path inside "
          "the nested repo where a reader would never look",
          db == ws / ".rbtv" / "runtime" / "ignite" / "heart.db"
          and str(repo) not in str(db), {"db": str(db)})

    check("A3: the bare `.rbtv/` walked past is NAMED on stderr as NOT a workspace — one line "
          "naming the directory and the record it lacks, so the next planting costs one journal "
          "line instead of two components silently disagreeing about which file is `heart.db`",
          str(repo) in stderr_text and str(RECORD_REL) in stderr_text
          and "NOT a workspace" in stderr_text, {"stderr": stderr_text.strip()[:400]})

    check("A4: RESOLVING CREATES NOTHING — after both calls the workspace still holds only its "
          "install record and the nested repo only the empty `runtime/` it started with. A "
          "resolver that creates as it looks is how the stray store was planted in the first place",
          tree(ws / ".rbtv") == [str(Path("modules")), str(Path("modules") / "ignite"),
                                 str(Path("modules") / "ignite" / "server.json")]
          and tree(repo / ".rbtv") == ["runtime"],
          {"ws_rbtv": tree(ws / ".rbtv"), "repo_rbtv": tree(repo / ".rbtv")})

    # ---- B. THE RULING PATH, end to end ----------------------------------------------------
    rc, text = supervise_instruct(IGNITE / "supervisor" / "supervise.py", pkg)
    landed = ws / INSTRUCTIONS_REL / f"{pkg.name}--worker-a.json"
    stray = list((repo / ".rbtv").rglob("*.json"))
    check("B1: the RULING half lands in the same workspace — a real `supervise instruct worker-a "
          "reassign --go`, run with its cwd INSIDE the nested repo, writes the leader's inbox at "
          "`<ws>/.rbtv/runtime/ignite/leader-instructions/<goal>--<seat>.json`, the path "
          "`drainLeaderInstructions` matches, and the nested repo gains no JSON at all",
          rc == 0 and landed.is_file() and stray == []
          and json.loads(landed.read_text())["kind"] == "reassign",
          {"rc": rc, "landed": landed.is_file(), "stray": [str(p) for p in stray],
           "out": text.strip()[-300:]})

    # ---- C. NEAREST WINS — the answer tracks the RECORD and nothing else -------------------
    ws2, repo2, pkg2 = make_fixture(ROOT / "c", nested_record=True)
    rc2, text2 = supervise_instruct(IGNITE / "supervisor" / "supervise.py", pkg2)
    landed2 = repo2 / INSTRUCTIONS_REL / f"{pkg2.name}--worker-a.json"
    check("C1: NEAREST-ANCESTOR-WINS IS UNCHANGED, and this row is the discriminating control for "
          "B1 — the ONLY edit to the fixture is an install record inside the nested repo, and the "
          "inbox moves there. So B1 passes because of the record, not because of the depth, the "
          "cwd or anything else about the shape",
          rc2 == 0 and landed2.is_file()
          and not (ws2 / INSTRUCTIONS_REL / f"{pkg2.name}--worker-a.json").exists(),
          {"rc": rc2, "landed_nested": landed2.is_file(), "out": text2.strip()[-300:]})

    # ---- D. NO RECORD ANYWHERE: both doors refuse, and nothing is planted -------------------
    bare = ROOT / "d" / "bare"
    (bare / ".rbtv" / "runtime").mkdir(parents=True)
    pkg3 = seed_package(bare / "some" / "goal")
    before = tree(ROOT / "d")
    raised = ""
    env_saved = os.environ.pop("ENDING_STORE_DB", None)
    try:
        with redirect_stderr(io.StringIO()):
            es.ending_store_db(pkg3)
    except es.EndingStoreError as exc:
        raised = str(exc)
    finally:
        if env_saved is not None:
            os.environ["ENDING_STORE_DB"] = env_saved

    check("D1: with a bare `.rbtv/` above it and NO install record anywhere, the store resolver "
          "REFUSES with one line naming the record it looked for — instead of the create-at-cwd "
          "fallback it used to have, which answered a path inside a folder nothing reads",
          "no workspace above" in raised and str(RECORD_REL) in raised
          and "findInstallRoot" in raised, {"raised": raised[:400]})

    rc3, text3 = supervise_instruct(IGNITE / "supervisor" / "supervise.py", pkg3)
    check("D2: the ruling door refuses the same tree by the same rule — nonzero, the record named, "
          "and NOTHING WAS WRITTEN said in as many words. A ruling that reached no inbox must say "
          "so: filed into a workspace the daemon never drains, it reads as ruled",
          rc3 != 0 and str(RECORD_REL) in text3 and "NOTHING WAS WRITTEN" in text3,
          {"rc": rc3, "out": text3.strip()[-400:]})

    check("D3: AND THE REFUSAL PLANTED NOTHING — the whole tree is byte-for-byte the file list it "
          "carried before either door was touched. This is the assertion the outage was made of: "
          "the pre-fix fallback would have created `<pkg>/.rbtv/runtime/ignite/heart.db` here, and "
          "a `.rbtv/` is gitignored, so nothing downstream would ever have shown it",
          tree(ROOT / "d") == before,
          {"added": sorted(set(tree(ROOT / "d")) - set(before))})

    # ---- E. THE ENV OVERRIDE IS THE FIRST BRANCH AND IS NOT SECOND-GUESSED ------------------
    explicit = ROOT / "e" / "explicit-store.db"
    os.environ["ENDING_STORE_DB"] = str(explicit)
    try:
        env_answer = es.ending_store_db(pkg3)
    finally:
        os.environ.pop("ENDING_STORE_DB", None)
    check("E1: `ENDING_STORE_DB` still wins OUTRIGHT — from the same tree that refuses without it, "
          "and answered without a walk. It is deliberately not validated against the record: "
          "probes and fixtures point it at scratch stores that root no install, and validating it "
          "would turn every one of them into a test of the refusal",
          env_answer == explicit, {"answer": str(env_answer)})

    # ---- F. RED CONTROL 1: the resolver's own source, mutated back --------------------------
    mut_dir = ROOT / "mutant"
    mut_dir.mkdir()
    mut_path = mut_dir / "ending_store.py"
    src = ENDING_STORE_PY.read_text(encoding="utf-8")
    mutated = src.replace("if (p / INSTALL_RECORD_REL).is_file():",
                          "if (p / '.rbtv').is_dir():", 1)
    mut_path.write_text(mutated, encoding="utf-8")
    ws4, repo4, pkg4 = make_fixture(ROOT / "f")
    mut = load_module(mut_path, "probe_ending_store_mutant")
    with redirect_stderr(io.StringIO()):
        mut_resolved = mut.workspace_root(pkg4)
    check("F1: RED CONTROL — the same source with the record test swapped back to "
          "`(p / '.rbtv').is_dir()` resolves to the NESTED REPO on the identical fixture. One "
          "line is the whole difference between A1 and this, so A1 cannot be passing for an "
          "unrelated reason",
          mutated != src and mut_resolved == repo4,
          {"mutant": str(mut_resolved), "repo": str(repo4), "ws": str(ws4)})

    bare5 = ROOT / "f" / "bare"
    (bare5 / ".rbtv" / "runtime").mkdir(parents=True)
    pkg5 = seed_package(bare5 / "some" / "goal")
    with redirect_stderr(io.StringIO()):
        mut_db = mut.ending_store_db(pkg5)
    check("F2: RED CONTROL — and on the no-record tree the mutant answers a `heart.db` INSIDE it "
          "rather than refusing, which is the stray "
          "`3-resources/tools/rbtv/.rbtv/runtime/ignite/heart.db` of 2026-08-28 reproduced in "
          "miniature: `ending_store_op` would `mkdir(parents=True)` that path on the next write",
          str(bare5) in str(mut_db) and mut_db.name == "heart.db", {"mutant_db": str(mut_db)})

    # ---- G. RED CONTROL 2: the RULING half, riding the mutated walker -----------------------
    # The whole kit is copied, not a slim subset: `supervise.py` reaches `coord/`, `supervisor/`
    # and `state-store/` by path off its own location, and a partial copy would fail for a reason
    # that is the copy's and not the mutation's. `__pycache__` is dropped — a stale `.pyc` serves
    # the previous source's verdict.
    kit_copy = ROOT / "kit" / "ignite"
    for part in ("coord", "supervisor", "state-store"):
        shutil.copytree(IGNITE / part, kit_copy / part,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
    (kit_copy / "coord" / "ending_store.py").write_text(mutated, encoding="utf-8")
    ws6, repo6, pkg6 = make_fixture(ROOT / "g")
    rc6, text6 = supervise_instruct(kit_copy / "supervisor" / "supervise.py", pkg6)
    mut_landed = repo6 / INSTRUCTIONS_REL / f"{pkg6.name}--worker-a.json"
    check("G1: RED CONTROL — a COPY OF THE KIT carrying only that one mutated line writes the "
          "leader's inbox into the NESTED REPO, where no reconcile pass drains it, while B1's "
          "unmutated run wrote it into `<ws>`. `ruling.py` carries no walk of its own any more, "
          "and this is the demonstration of it: mutating the store resolver moves the ruling "
          "verb's answer",
          rc6 == 0 and mut_landed.is_file()
          and not (ws6 / INSTRUCTIONS_REL / f"{pkg6.name}--worker-a.json").exists(),
          {"rc": rc6, "landed_nested": mut_landed.is_file(), "out": text6.strip()[-300:]})
finally:
    shutil.rmtree(ROOT, ignore_errors=True)

FAILED = [c["name"] for c in CHECKS if not c["pass"]]
EXIT = 1 if FAILED else 0
WALL = int((time.time() - T0) * 1000)
OUT.write_text(json.dumps({
    "summary": {"probe": "probe-workspace-record-walk", "pass": not FAILED, "checks": len(CHECKS),
                "failed": FAILED, "EXIT": EXIT, "WALL_MS": WALL, "SKIPPED_COUNT": 0},
    "checks": CHECKS,
}, indent=2) + "\n", encoding="utf-8")
for c in CHECKS:
    print(("PASS  " if c["pass"] else "FAIL  ") + c["name"])
    if not c["pass"]:
        print("      " + json.dumps(c["evidence"]))
print(f"PROBE probe-workspace-record-walk EXIT={EXIT} WALL_MS={WALL} PASS={str(not FAILED).lower()} "
      f"CHECKS={len(CHECKS)}")
sys.exit(EXIT)

#!/usr/bin/env python3
"""D45/F-8 check — corroborated staff claim, plus the CAGED impersonation refusal.

    python3 test_d45_staff_claim.py [module]

It RE-EXECS ITSELF under `systemd-run --user --unit=rbtv-worker-<uuid>` when it is not already
inside a carrier unit, because the whole subject is what this process's OWN cgroup names — a
run outside one would resolve to nothing and pass vacuously.  `module` defaults to `coord`;
pass a mutant module's name (a copy inside THIS directory — a /tmp copy dies at import) for
the red arm.

In-process arms stub `daemon_heart_db` so the caller resolves to `ignite-daemon` (D45).  The
F-8 CAGED arm does not: it runs coord.py as a subprocess inside a bwrap cage built by
production `composeCageFor`+`buildBwrapArgv` on a scratch package (never a live goal).  That
is the path production takes — `/run` tmpfs, no heart.db — where `actual` used to be '' and
the gate admitted `--as leader` as an uncaged console.
"""
import argparse, json, os, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path

MOD = sys.argv[1] if len(sys.argv) > 1 else "coord"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
coord = __import__(MOD)

FAIL = []
def check(label, cond, evidence=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    if evidence:
        print("        " + evidence.strip().replace("\n", "\n        "))
    if not cond:
        FAIL.append(label)

# ---- 1. the caller's OWN, unforgeable session id, off /proc/self/cgroup ----------------------
print("/proc/self/cgroup:", open("/proc/self/cgroup").read().strip())
SID = coord.carrier_self_session()
if not SID:
    # Not inside a carrier unit yet — become one.  `env -u TMUX` because a transient unit that
    # inherits $TMUX can take the operator's tmux server down with it.
    import uuid
    os.environ.pop("TMUX", None)
    os.execvp("systemd-run", [
        "systemd-run", "--user", f"--unit=rbtv-worker-{uuid.uuid4()}", "--pipe", "--wait",
        "--collect", f"--working-directory={os.path.dirname(os.path.abspath(__file__))}",
        sys.executable, os.path.abspath(__file__), MOD])
check("carrier_self_session() reads this process's own carrier unit", bool(SID), f"sid={SID}")

TD = Path(tempfile.mkdtemp(prefix="d45-"))
# ---- 2. a LIVE jobs_log turn for THIS unit -> the caller resolves to `ignite-daemon` ----------
DB = TD / "heart.db"
con = sqlite3.connect(DB)
con.execute("CREATE TABLE jobs_log (unit_name TEXT, status TEXT)")
con.execute("INSERT INTO jobs_log VALUES (?, 'running')", (coord.CARRIER_UNIT_PREFIX + SID,))
con.commit(); con.close()
coord.daemon_heart_db = lambda: str(DB)
check("the caller RESOLVES TO 'ignite-daemon' (F16, live jobs_log turn) — not to 'nothing'",
      coord.daemon_exec_identity() == coord.DAEMON_IDENTITY,
      f"daemon_exec_identity() = {coord.daemon_exec_identity()!r}")

# ---- 3. the packages ------------------------------------------------------------------------
ANCHOR = "p-crashy-655"

def make_pkg(name, roster_seat):
    """A goal with `leader` + `crashy`; `crashy` has a `done`-ruled ENDED row (so `--rerun`'s own
    state gate refuses AFTER both identity gates — the launch touches nothing).  `roster_seat`
    is the seat THIS PROCESS's own session id gets registered to, or None for no row at all."""
    pkg = TD / name / ".rbtv" / "goals" / "g45"
    (pkg / "coordination").mkdir(parents=True)
    for s in ("leader", "crashy"):
        (pkg / "seats" / s).mkdir(parents=True)
        (pkg / "seats" / s / "seat.md").write_text(f"---\nseat: {s}\n---\nbrief\n",
                                                   encoding="utf-8")
    (pkg / "budget.json").write_text(
        json.dumps({"floors": {"launch_refuse_mb": 100, "pressure_warn_mb": 100}}),
        encoding="utf-8")
    rows = []
    if roster_seat:
        rows.append({"session-id": SID, "seat": roster_seat, "started": "2026-08-20 20:00"})
    rows.append({"session-id": "crashy-1", "seat": "crashy", "started": "2026-08-20 19:00",
                 "ended": "2026-08-20 19:30", "disposition": "done", "disposition-writer": "kit"})
    coord.write_csv_table(coord.sessions_csv(pkg), coord.SESSIONS_COLS,
                          [[r.get(c, "") for c in coord.SESSIONS_COLS] for r in rows])
    for s in {roster_seat, "crashy"} - {None}:
        p = coord.build_parser()
        a = p.parse_args(["--package", str(pkg), "checkin", s, "d45 fixture"])
        coord.harness_outcome(a.func, a)
    return pkg

def run(pkg, *argv):
    p = coord.build_parser()
    try:
        a = p.parse_args(["--package", str(pkg), *argv])
    except SystemExit as e:            # a parse error is a FIXTURE bug, never a verdict
        raise AssertionError(f"argv did not parse: {argv} ({e})")
    out, err, code = coord.harness_outcome(a.func, a)
    return out + err, code

def roster(pkg):
    _, _, rws = coord.load_workers(pkg / "coordination")
    return [(r["agent"], r["pane"], r["active"]) for r in rws]

# ---- POSITIVE --------------------------------------------------------------------------------
pkg_ok = make_pkg("ok", "leader")
print("roster(ok):", roster(pkg_ok))
claim, pane = coord.asserted_launch_claim(argparse.Namespace(
    as_agent="leader", pane=None, package=str(pkg_ok), base=None, workers_dir=None, force=False))
check("F17 (D43's lane): the claim is CORROBORATED — nothing is left uncorroborated",
      claim == "" and pane == coord.SID_PANE_PREFIX + SID, f"({claim!r}, {pane!r})")
out, code = run(pkg_ok, "--as", "leader", "launch", "--only", "crashy", "--rerun", ANCHOR)
check("POSITIVE: ADMITTED past BOTH gates and reaches `--rerun`'s OWN state gate",
      "console-override: acting --as 'leader'" in out and "CORROBORATED (D45)" in out
      and "--rerun admits EXACTLY ONE from-state" in out and code == 1, out)

# ---- NEGATIVES (a)(b)(c) — through `send`, which reaches the STAFF GATE and not F17's bound,
#      and through `launch`, which is the end-to-end door.  Both must refuse.
def negatives(tag, pkg, extra=()):
    out_s, code_s = run(pkg, "--as", "leader", "send", "crashy", "d45", "--type", "note",
                        "--inline", *extra)
    check(f"NEGATIVE {tag} · staff gate (via `send`): REFUSED, exit 2",
          "STAFF CHAIR" in out_s and code_s == 2, f"exit={code_s}\n{out_s}")
    out_l, code_l = run(pkg, "--as", "leader", "launch", "--only", "crashy",
                        "--rerun", ANCHOR, *extra)
    check(f"NEGATIVE {tag} · end to end (via `launch --rerun`): REFUSED, exit 2, nothing opened",
          code_l == 2 and "ADMITTED by --rerun" not in out_l, f"exit={code_l}\n{out_l}")
    return out_s

negatives("(a) own session's roster row names a DIFFERENT seat", make_pkg("a", "crashy"))
negatives("(b) NO roster row for this session", make_pkg("b", None))
out_c = negatives("(c) with --force", make_pkg("c", "crashy"), extra=("--force",))
check("NEGATIVE (c): the refusal still says there is no --force for this one",
      "no --force for this one" in out_c)

# ---- NEGATIVE (d): the pre-existing daemon path, NO `--as`, unbroken -------------------------
out, code = run(make_pkg("d", None), "launch", "--only", "crashy", "--rerun", ANCHOR)
check("NEGATIVE (d): NO `--as` — the staff gate is never reached and the daemon path still "
      "launches (it proceeds to `--rerun`'s state gate)",
      "STAFF CHAIR" not in out and "--rerun admits EXACTLY ONE from-state" in out and code == 1,
      f"exit={code}\n{out}")

# ---- NEGATIVE (e): the three pre-existing admitted identities still pass ----------------------
for who in coord.STAFF_CLAIM_IDENTITIES:
    pkg_e = make_pkg("e-" + who, None)
    os.environ["COORD_AGENT"] = who
    try:
        out, code = run(pkg_e, "--as", "leader", "send", "crashy", "d45", "--type", "note",
                        "--inline")
    finally:
        os.environ.pop("COORD_AGENT", None)
    check(f"NEGATIVE (e): pre-existing admitted identity '{who}' STILL PASSES the staff gate",
          "console-override: acting --as 'leader'" in out and f"from '{who}'" in out
          and "CORROBORATED (D45)" not in out and "STAFF CHAIR —" not in out and code != 2,
          f"exit={code}\n{out}")

# ---- F-8 CAGED ARM: production composeCageFor + bwrap, same carrier unit, live coord.py ----
KIT = Path(os.path.dirname(os.path.abspath(coord.__file__)))
IGNITE = KIT.parent
COORD_PY = Path(os.path.abspath(coord.__file__))
COMPOSE_JS = r"""
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const ignite = process.env.F8_IGNITE;
const { composeCageFor } = require(path.join(ignite, 'server/spawn/spawn.js'));
const { buildBwrapArgv } = require(path.join(ignite, 'server/spawn/bwrap.js'));
const { parseSeatPath } = require(path.join(ignite, 'server/seat-identity/seat-folder.js'));
const seatDir = process.argv[2];
const inner = JSON.parse(process.argv[3]);
const cfg = yaml.load(fs.readFileSync(path.join(ignite, 'config/spawn-profiles.yaml'), 'utf8'));
const sandbox = { SeatBinds: cfg.cage.SeatBinds, MasterBinds: cfg.cage.MasterBinds };
const parsed = parseSeatPath(seatDir);
if (!parsed) { process.stderr.write('parseSeatPath failed\n'); process.exit(2); }
const flags = composeCageFor(sandbox, parsed, seatDir, '127.0.0.1:7431');
process.stdout.write(JSON.stringify(buildBwrapArgv({
  argv: inner, workdir: seatDir, harness: null, seatBinds: flags })));
"""

def run_caged(pkg, seat_name, extra_argv):
    """Exec coord.py inside a production-composer bwrap cage. FIXTURE scratch, not a live goal."""
    seat_dir = str(pkg / "seats" / seat_name)
    inner = [sys.executable, str(COORD_PY), "--package", str(pkg), *extra_argv]
    js = Path(tempfile.mkdtemp(prefix="f8-compose-")) / "compose.js"
    js.write_text(COMPOSE_JS, encoding="utf-8")
    env = dict(os.environ)
    env["NODE_PATH"] = str(IGNITE / "node_modules")
    env["F8_IGNITE"] = str(IGNITE)
    env.pop("COORD_AGENT", None)
    env.pop("TMUX", None)
    comp = subprocess.run(
        ["node", str(js), seat_dir, json.dumps(inner)],
        cwd=str(IGNITE), capture_output=True, text=True, timeout=60, env=env)
    if comp.returncode != 0:
        return (comp.stdout or "") + (comp.stderr or ""), comp.returncode, "compose-failed"
    argv = json.loads(comp.stdout)
    r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
    return (r.stdout or "") + (r.stderr or ""), r.returncode, "caged-composeCageFor-FIXTURE"

pkg_f8 = make_pkg("f8-caged", "crashy")
out_f8, code_f8, klass = run_caged(
    pkg_f8, "crashy",
    ["--as", "leader", "send", "crashy", "f8-impersonation", "--type", "note", "--inline"])
check("F-8 CAGED: uncorroborated --as leader on send is REFUSED in-cage "
      f"(evidence-class={klass}; production composeCageFor; scratch package, not a live goal)",
      "STAFF CHAIR" in out_f8 and code_f8 == 2
      and "console-override: acting --as 'leader'" not in out_f8
      and "an uncaged console — no identity resolves" not in out_f8,
      f"exit={code_f8}\n{out_f8}")

shutil.rmtree(TD, ignore_errors=True)
print(f"\nD45 FIXTURE: {'PASS' if not FAIL else 'FAIL — ' + '; '.join(FAIL)}")
sys.exit(1 if FAIL else 0)

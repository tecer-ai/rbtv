#!/usr/bin/env python3
"""probe-leader-hold.py — the leader's THIRD ruling act, at its own door.

WHAT WAS BROKEN. `supervisor/owed-from-endings.js` turns any `failed` ending into a `nonterm` owed
row and `supervisor/reconcile.js` answers such a row by launching the LEADER — every ~5-min pass.
`supervise accept` and `supervise instruct` stop that because both END the row. The leader's third
legitimate verdict — "I have read this and it cannot be ruled until X happens" — was a message and
nothing else, and the pass reads rows, never mail. So every HOLD sitting looked exactly like a
sitting that did nothing: it was counted as a burned recovery attempt, the lane disarmed at N=3,
and the next code-deploy re-arm bought three more. Nine identical HOLD verdicts on
`goal-memory-management`, 2026-08-28, nine paid opus-5 sittings, none of them honoured.

WHAT THIS MEASURES — the DOOR only. That the verb refuses what it must refuse, writes what it
says it writes, and is idempotent. What the daemon then DOES with the row is
`supervisor/reconcile.selftest.js`'s four hold arms, and the two files deliberately do not overlap.

FIXTURE SAFETY. Everything happens inside one temp workspace under the OS temp dir: its own
`.rbtv/` root (which is what `ending_store.ending_store_db` walks up to find), its own goal
package, its own `heart.db`. Nothing here reads or writes the live workspace, the live store or
any live goal, and no daemon is contacted.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPERVISE = HERE.parent.parent / "supervisor" / "supervise.py"
OUT = HERE / "probe-leader-hold.out"
CHECKS = []
T0 = time.time()


def check(name, ok, evidence=None):
    CHECKS.append({"name": name, "pass": bool(ok), "evidence": evidence or {}})


def fixture():
    root = Path(tempfile.mkdtemp(prefix="probe-leader-hold-"))
    # THE FIXTURE ROOT IS A WORKSPACE, and it says so with the INSTALL RECORD — D27's
    # definition (`ignite-cli/lib/config.js#findInstallRoot`), never a bare `.rbtv/`.
    # `ending_store` resolves the store by that record and REFUSES above a folder that roots no
    # install, rather than minting a `.rbtv/` at the start dir — the fallback that planted the
    # stray `<repo>/.rbtv/runtime/ignite/heart.db` of 2026-08-28 [5815fbaa].
    _rec = root / ".rbtv" / "modules" / "ignite" / "server.json"
    _rec.parent.mkdir(parents=True, exist_ok=True)
    _rec.write_text('{"machines": {}}\n', encoding="utf-8")
    pkg = root / ".rbtv" / "goals" / "g1"
    for seat in ("leader", "worker-a"):
        (pkg / "seats" / seat).mkdir(parents=True, exist_ok=True)
        (pkg / "seats" / seat / "seat.md").write_text(
            f"---\nseat: {seat}\nharness: bash\nmodel: probe\n---\n\nbody\n", encoding="utf-8")
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (pkg / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf,leader,,bash,probe,high,35,\ntf,worker-a,,bash,probe,high,35,\n", encoding="utf-8")
    return root, pkg


def run(pkg, *argv):
    proc = subprocess.run(
        [sys.executable, str(SUPERVISE), "--package", str(pkg), "--as", "leader", *argv],
        capture_output=True, text=True, cwd=str(pkg))
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def store_db(root):
    return root / ".rbtv" / "runtime" / "ignite" / "heart.db"


def holds(root):
    """Read the hold rows back through the STORE's own door, never with a second SQL reader."""
    db = store_db(root)
    if not db.exists():
        return []
    cli = HERE.parent.parent / "state-store" / "cli.js"
    proc = subprocess.run(
        ["node", str(cli), "--db", str(db), "--op", "listSeatHolds",
         "--payload", json.dumps({"goal": "g1"})], capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    return json.loads(proc.stdout or "null") or []


root, pkg = fixture()
try:
    # ── A · THE DRY RUN WRITES NOTHING ────────────────────────────────────────────────────────
    rc, out = run(pkg, "hold", "worker-a", "--until", "release", "--anchor", "messages.md #18")
    # ⚠ "WRITES NOTHING" IS ABOUT THE ROW, NOT THE FILE. A dry run READS the seat's current ending
    # to report what it would hold, and the store's own door creates an empty `heart.db` on any
    # read — `accept`'s dry run has always done the same. The claim under test is that no HOLD is
    # recorded, and asserting the file's absence instead would be asserting something untrue of
    # every sibling verb.
    check("A1: bare (no --go) REPORTS and records NO hold — the same convention `accept` and "
          "`instruct` carry",
          rc == 0 and "WOULD HOLD" in out and holds(root) == [],
          {"rc": rc, "rows": holds(root), "head": out.splitlines()[:1]})

    # ── B · THE CLOSED VOCABULARY, REFUSED WITH THE LIST IN THE MESSAGE ───────────────────────
    rc, out = run(pkg, "hold", "worker-a", "--until", "frozen", "--anchor", "x")
    check("B1: a `--until` word outside the closed list is REFUSED, and the refusal NAMES every "
          "word — a leader that guessed must not have to read the source to find the right one",
          rc == 2 and "not a hold release condition" in out
          and all(w in out for w in ("new-ending", "ask-answered", "release"))
          and "NOTHING WAS WRITTEN" in out,
          {"rc": rc, "text": out.splitlines()[:1]})

    rc, out = run(pkg, "hold", "worker-a", "--until", "ask-answered", "--anchor", "x")
    check("B2: `ask-answered` without an ask id is REFUSED — a hold whose release nobody can "
          "observe is a stall",
          rc == 2 and "must NAME the ask" in out, {"rc": rc, "text": out.splitlines()[:1]})

    rc, out = run(pkg, "hold", "worker-a", "--until", "ask-answered:no-such-ask", "--anchor", "x", "--go")
    check("B3: an ask id that names no OPEN ask is REFUSED — the liveness predicate fails open by "
          "design, so such a hold would release on the very next pass and hold nothing",
          rc == 1 and "not an OPEN ask" in out, {"rc": rc, "text": out.splitlines()[:1]})

    rc, out = run(pkg, "hold", "worker-a", "--until", "release")
    check("B4: a hold citing nothing is REFUSED — `--anchor` is mandatory and recorded, never "
          "verified, exactly as `accept`'s is",
          rc == 2 and "--anchor carries" in out, {"rc": rc, "text": out.splitlines()[:1]})

    rc, out = run(pkg, "hold", "no-such-seat", "--until", "release", "--anchor", "x", "--go")
    check("B5: a well-formed name that names no seat is REFUSED — the same wall `accept` and "
          "`instruct` put there",
          rc == 1 and "staffs no seat named" in out, {"rc": rc})

    check("B6: not one refusal above left a hold behind — every `NOTHING WAS WRITTEN` is true",
          holds(root) == [], {"rows": holds(root)})

    # ── C · `--go` WRITES THE ROW, AND A SECOND HOLD IS IDEMPOTENT ────────────────────────────
    rc, out = run(pkg, "hold", "worker-a", "--until", "release",
                  "--anchor", "messages.md #18 — owner escalation unanswered", "--go")
    rows = holds(root)
    check("C1: `--go` writes ONE live hold, carrying the release condition, the anchor and who "
          "ruled it",
          rc == 0 and out.startswith("held:") and len(rows) == 1
          and rows[0]["seat"] == "worker-a" and rows[0]["until"] == "release"
          and rows[0]["held_by"] == "leader" and "#18" in rows[0]["anchor"],
          {"rc": rc, "rows": rows})
    first_at = rows[0]["held_at"] if rows else None

    rc, out = run(pkg, "hold", "worker-a", "--until", "release",
                  "--anchor", "messages.md #18 — owner escalation unanswered", "--go")
    rows2 = holds(root)
    check("C2: the SAME hold again is IDEMPOTENT — one row, and `held_at` does not restart (two "
          "sittings reading the same mail reach the same verdict; the clock must not move)",
          rc == 0 and len(rows2) == 1 and rows2[0]["held_at"] == first_at
          and "ALREADY HELD" in out,
          {"first_at": first_at, "now": rows2[0]["held_at"] if rows2 else None})

    rc, out = run(pkg, "hold", "worker-a", "--until", "new-ending",
                  "--anchor", "re-run ordered", "--go")
    rows3 = holds(root)
    check("C3: a hold on DIFFERENT terms REPLACES it — one hold per (goal, seat), never two "
          "rulings racing over one row",
          rc == 0 and len(rows3) == 1 and rows3[0]["until"] == "new-ending",
          {"rows": [f"{r['seat']}:{r['until']}" for r in rows3]})

    # ── D · RELEASE ───────────────────────────────────────────────────────────────────────────
    rc, out = run(pkg, "release", "worker-a")
    check("D1: `release` bare REPORTS the hold it would end and writes nothing",
          rc == 0 and "WOULD RELEASE" in out and len(holds(root)) == 1, {"rc": rc})

    rc, out = run(pkg, "release", "worker-a", "--go")
    check("D2: `release --go` removes the hold — the row is owed again on the next pass",
          rc == 0 and out.startswith("released:") and holds(root) == [], {"rc": rc})

    rc, out = run(pkg, "release", "worker-a", "--go")
    check("D3: releasing an unheld seat is NOT an error — the hold may already have been released "
          "by the change it named, and the leader asked for the state it has",
          rc == 0 and "not held" in out, {"rc": rc, "text": out.splitlines()[:1]})

    # ── E · THE AUDIENCE BOUND IS THE DOOR ────────────────────────────────────────────────────
    coordinate = HERE.parent / "coord.py"
    proc = subprocess.run(
        [sys.executable, str(coordinate), "--package", str(pkg), "--as", "leader",
         "hold", "worker-a", "--until", "release", "--anchor", "x", "--go"],
        capture_output=True, text=True, cwd=str(pkg))
    text = (proc.stdout or "") + (proc.stderr or "")
    check("E1: `coordinate hold` is refused BY NAME at the parser — a remedial verb sits on the "
          "supervision door only, the same bound `accept` and `instruct` carry",
          proc.returncode != 0 and "invalid choice: 'hold'" in text and holds(root) == [],
          {"rc": proc.returncode})
finally:
    shutil.rmtree(root, ignore_errors=True)

FAILED = [c["name"] for c in CHECKS if not c["pass"]]
EXIT = 1 if FAILED else 0
WALL = int((time.time() - T0) * 1000)
OUT.write_text(json.dumps({
    "summary": {"probe": "probe-leader-hold", "pass": not FAILED, "checks": len(CHECKS),
                "failed": FAILED, "EXIT": EXIT, "WALL_MS": WALL, "SKIPPED_COUNT": 0},
    "checks": CHECKS,
}, indent=2) + "\n", encoding="utf-8")
for c in CHECKS:
    print(("PASS  " if c["pass"] else "FAIL  ") + c["name"])
    if not c["pass"]:
        print("      " + json.dumps(c["evidence"]))
print(f"PROBE probe-leader-hold EXIT={EXIT} WALL_MS={WALL} PASS={str(not FAILED).lower()} "
      f"CHECKS={len(CHECKS)}")
sys.exit(EXIT)

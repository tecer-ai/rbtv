#!/usr/bin/env python3
"""probe-overlap-sittings.py — two OVERLAPPING sittings of ONE seat cannot mint a permanent
disagreement about that seat's ending (build tasks 95 + 135).

WHAT IT PINS, and why each arm is here rather than in the kit self-test:

  A. THE OVERLAP ITSELF. Two sittings of one seat, the second opened before the first closed.
     The NEWER sitting declares `done`; the OLDER one then ends — by its own check-out and by the
     daemon-lane closer. Neither may replace the newer sitting's ending. The measured incident
     (G-leader-0823-1317, stools `goal-master`, 2026-08-23 13:01→13:15 vs 13:12→13:15) was exactly
     this: the older sitting's kit-attested ending landed on top of the newer's `done` in a
     SEAT-KEYED live surface, and the pair then disagreed with `sessions.csv` forever.

  B. THE ARM THAT PREVENTS IT, mutated. `supervisor/death-stamp.js#declaredEndingIsStale` is the
     one place that asks whether the stored ending could possibly belong to THIS dying sitting. Its
     RED is built here — the guard forced to report every row stale — and the overwrite comes back.
     Without this arm the green above is unfalsifiable: it would also read green on a build where
     nothing stamps at all.

  C. NO SECOND ENDING WRITER IS LEFT TO DISAGREE WITH (task 95). `ready.py#terminal_disposition`
     answers off the ONE ending store and its `skew` element is structurally `None`;
     `spec-state-store §4.1` deleted `awaiting-close.json`, the surface an out-of-package check-out
     used to write with no matching `sessions.csv` row. This arm pins BOTH halves of that: the
     unregistered-sitting shape produces no SKEW, and a genuinely absent ending still reads as
     absent rather than as agreement.

The kit self-test cannot host A or B: both need a real ending store, a real `node` supervisor call
and a mutated copy of a JS module, which `coord.py selftest` deliberately does not reach for."""

import os as _os, sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents
                             if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
IGNITE = KIT.parent
COORD = KIT / "coord.py"
RESULTS = []


def check(claim, ok):
    RESULTS.append((claim, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'}  {claim}")


class _NoTmux:
    """tmux is not part of what this probe measures; every pane call answers cleanly."""
    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(self, *_a, **_k):
        return self._R()

    def __getattr__(self, name):
        return getattr(subprocess, name)


def load_coord(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.subprocess = _NoTmux()
    return mod


def make_package(root, seats):
    pkg = Path(root)
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    for seat in seats:
        d = pkg / "workers" / seat
        d.mkdir(parents=True, exist_ok=True)
        (d / "agent.md").write_text(
            f"---\nagent: {seat}\ncwd: {d}\n---\n\n# {seat}\nbrief\n", encoding="utf-8")
    return pkg


def ns(mod, pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None, "as_agent": None,
         "force": False, "evidence": ""}
    d.update(kw)
    return argparse.Namespace(**d)


def sit_down(mod, pkg, seat, pane):
    """One SITTING starts: the seat takes the roster row and opens its own `sessions.csv` row."""
    mod.harness_outcome(mod.cmd_checkin,
                        ns(mod, pkg, agent=seat, summary="sitting", pane=pane, force=False))
    mod.session_open(ns(mod, pkg),
                     {"agent": seat, "harness": "probe", "model": "opus",
                      "cwd": str(Path(pkg) / "workers" / seat)},
                     since=time.time(), wait=0.0)


def checkout(mod, pkg, seat, **kw):
    d = {"agent": seat, "no_export": True, "renew": False, "handoff": None,
         "handoff_file": None, "incomplete": None, "pane": None}
    d.update(kw)
    out, err, code = mod.harness_outcome(mod.cmd_checkout, ns(mod, pkg, **d))
    return out + err, (0 if code is None else code)


def session_rows(pkg):
    p = Path(pkg) / "sessions.csv"
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def ending_of(mod, pkg, seat):
    try:
        return mod.ending_store.get_current_ending(pkg, seat)
    except Exception:
        return None


# ---- ARM B's mutant: `declaredEndingIsStale` forced to report EVERY stored row stale -----------
#
# The two relative `require`s are re-pointed at the REAL tree rather than copied, so the mutant is
# one file and stays one file when death-stamp.js grows a third dependency: what is under test is
# the guard, and a probe that also forks its dependencies measures the fork.
MUTANT_ANCHOR = "function declaredEndingIsStale(current, evidence) {"


def build_stale_guard_mutant(dest_dir):
    src_path = IGNITE / "supervisor" / "death-stamp.js"
    src = src_path.read_text(encoding="utf-8")
    if MUTANT_ANCHOR not in src:
        return None, f"mutation seam NOT FOUND, mutant not built: {MUTANT_ANCHOR!r}"
    src = src.replace(MUTANT_ANCHOR, MUTANT_ANCHOR + "\n  return true;  // MUTANT", 1)
    seams = [("require('./registry')",
              f"require({str(IGNITE / 'supervisor' / 'registry.js')!r})"),
             ("require('../runtime/seat-identity/csv')",
              f"require({str(IGNITE / 'runtime' / 'seat-identity' / 'csv.js')!r})")]
    for old, new in seams:
        if old not in src:
            return None, f"require seam NOT FOUND, mutant not built: {old!r}"
        src = src.replace(old, new, 1)
    dest = Path(dest_dir) / "death-stamp-mutant.js"
    dest.write_text(src, encoding="utf-8")
    return dest, ""


DRIVER = r"""
const stamp = require(process.argv[2]);
const { bind, openEndingStore } = require(process.argv[3]);
const store = bind(openEndingStore(process.argv[4]));
const evidence = JSON.parse(process.argv[5]);
const res = stamp.stampDeath(evidence, {
  store: {
    getCurrentEnding: (q) => store.getCurrentEnding(q),
    stampSystem: (f) => store.stampSystem(f),
  },
  registryFile: process.argv[6],
});
process.stdout.write(JSON.stringify(res));
"""


def drive_death_stamp(module_js, db, evidence, registry, where):
    """Run ONE `stampDeath` through `module_js` against the real store at `db`.

    ⚠ `where` IS THE FIXTURE DIRECTORY AND IS NOT DERIVED FROM `module_js`. The green half of arm
    B drives the SHIPPED module, and a driver written beside its subject would land a `drive.js`
    inside `ignite/supervisor/` — a probe writing into the tree it measures."""
    driver = Path(where) / "drive.js"
    driver.write_text(DRIVER, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(driver), str(module_js), str(IGNITE / "state-store" / "index.js"),
         str(db), json.dumps(evidence), str(registry)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout).strip()
    return json.loads(proc.stdout or "null"), ""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-overlap-"))
    # The fixture root ROOTS AN INSTALL — D27's definition, never a bare `.rbtv/`. `ending_store`
    # refuses above a folder that roots none rather than minting one, which is what keeps a probe
    # from planting the stray store of 2026-08-28 [5815fbaa].
    rec = tmp / ".rbtv" / "modules" / "ignite" / "server.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text('{"machines": {}}\n', encoding="utf-8")
    registry = tmp / "registry.json"
    registry.write_text("{}\n", encoding="utf-8")
    try:
        mod = load_coord(COORD, "coord_subject")
        db = tmp / ".rbtv" / "runtime" / "ignite" / "heart.db"

        # ---- ARM A1: the older sitting's own CHECK-OUT cannot replace the newer's `done` -------
        pkg = make_package(tmp / "test-overlap-checkout", ["goal-master"])
        sit_down(mod, pkg, "goal-master", "%1")
        time.sleep(1.1)                      # distinct minted session ids, distinct `started`
        sit_down(mod, pkg, "goal-master", "%2")
        rows = session_rows(pkg)
        check("A1: two OVERLAPPING sittings are on record — two rows, both open",
              len(rows) == 2 and all(not r["ended"].strip() for r in rows))
        _out, code_b = checkout(mod, pkg, "goal-master")
        newer = ending_of(mod, pkg, "goal-master")
        check("A1: the NEWER sitting declares `done`",
              code_b == 0 and newer is not None and newer["ending"] == "done"
              and newer["who_stamped"] == "seat")
        stamped_at = newer["stamped_at"] if newer else ""
        out_a, code_a = checkout(mod, pkg, "goal-master",
                                 incomplete="older sitting ran out of context")
        after = ending_of(mod, pkg, "goal-master")
        check("A1: the OLDER sitting's later check-out is REFUSED, not silently applied",
              code_a != 0 and "no ACTIVE roster row" in out_a)
        check("A1: the newer sitting's `done` is byte-for-byte the ending still stored",
              after is not None and after["ending"] == "done"
              and after["stamped_at"] == stamped_at)

        # ---- ARM A2: the older sitting DIES and the daemon-lane closer runs on ITS id ----------
        import attest
        pkg2 = make_package(tmp / "test-overlap-death", ["goal-master"])
        sit_down(mod, pkg2, "goal-master", "%3")
        older_sid = session_rows(pkg2)[0]["session-id"]
        time.sleep(1.1)
        sit_down(mod, pkg2, "goal-master", "%4")
        checkout(mod, pkg2, "goal-master")
        newer2 = ending_of(mod, pkg2, "goal-master")
        steps, _seat, verdict = attest.close_session_seat(ns(mod, pkg2), older_sid, "goal-master")
        after2 = ending_of(mod, pkg2, "goal-master")
        check("A2: the closer STAMPS NOTHING — the newer sitting's own `done` stands",
              verdict == "done"
              and any("the seat's own `done` stands" in s for s in steps))
        check("A2: the stored ending is untouched by the older sitting's death",
              after2 is not None and newer2 is not None
              and after2["ending"] == "done"
              and after2["stamped_at"] == newer2["stamped_at"])
        check("A2: the older sitting's OWN session row is the one closed",
              any(r["session-id"] == older_sid and r["ended"].strip()
                  for r in session_rows(pkg2)))

        # ---- ARM B: the RED — force `declaredEndingIsStale` true and the overwrite returns -----
        mutant, why = build_stale_guard_mutant(tmp)
        check(f"B: stale-guard mutant built{'' if mutant else ' — ' + why}", bool(mutant))
        if mutant:
            evidence = {"goal": mod.ending_store.goal_id_of(pkg2), "seat": "goal-master",
                        "session": older_sid, "checkedIn": True, "pid": None,
                        "exitCode": 1, "detail": "probe: older sitting died"}
            red, err = drive_death_stamp(mutant, db, evidence, registry, tmp)
            check(f"B: RED — the mutated guard STAMPS OVER the newer `done`{'' if red else ' — ' + err}",
                  bool(red) and red.get("stamped") is True and red.get("ending") == "failed")
            # And the same evidence through the REAL module leaves the row alone: the two runs
            # differ in the guard and in nothing else, so the green above is attributable to it.
            mod.ending_store.stamp_seat_declare(pkg2, "goal-master", "done",
                                                declared_outputs=None, evidence="probe:restore")
            green, err2 = drive_death_stamp(IGNITE / "supervisor" / "death-stamp.js", db,
                                            evidence, registry, tmp)
            check(f"B: GREEN — the SHIPPED guard refuses the same stamp{'' if green else ' — ' + err2}",
                  bool(green) and green.get("stamped") is False
                  and green.get("ending") == "done")

        # ---- ARM C: no second ending writer is left to disagree with (task 95) -----------------
        import ready
        pkg3 = make_package(tmp / "test-unregistered", ["audio-live-prober"])
        # The G-leader-0822-2342 shape: an EARLIER crashed sitting is the newest `sessions.csv`
        # row under this seat name, and the sitting that is actually running checked out from
        # OUTSIDE the package, so it minted no row of its own.
        sit_down(mod, pkg3, "audio-live-prober", "%5")
        checkout(mod, pkg3, "audio-live-prober", incomplete="crashed sitting")
        mod.ending_store.stamp_seat_declare(
            pkg3, "audio-live-prober", "incomplete",
            diagnostic="out-of-package sitting", evidence="checkout:audio-live-prober")
        value, source, skew = ready.terminal_disposition(pkg3, mod.base_dir(ns(mod, pkg3)),
                                                         "audio-live-prober")
        check("C: the unregistered-sitting shape reports NO skew — one writer cannot disagree",
              skew is None and source == "ending-store" and value == "incomplete")
        _v2, _s2, skew2 = ready.terminal_disposition(pkg3, mod.base_dir(ns(mod, pkg3)), "nobody")
        check("C: an ABSENT ending reads absent, never as agreement",
              (_v2, _s2, skew2) == (None, "", None))
        # The G-leader-0822-2342 sitting itself: an ending in the store and NO `sessions.csv` row
        # of its own, because the check-out came from outside the package and `session_close` is a
        # no-op with no open row. Nothing may read that missing row as a defect — the ending IS
        # recorded, on the one surface that records endings.
        pkg4 = make_package(tmp / "test-out-of-package", ["audio-live-prober"])
        mod.ending_store.stamp_seat_declare(
            pkg4, "audio-live-prober", "incomplete",
            diagnostic="out-of-package sitting", evidence="checkout:audio-live-prober")
        check("C: an out-of-package sitting is NOT reported as an undeclared ending",
              mod.undeclared_endings(pkg4) == {}
              and not (Path(pkg4) / "sessions.csv").exists())
        check("C: a skewed row would still stall only ITSELF — clause A is a per-row term",
              ready.conjunction_admits(
                  {"skew": ["done", "incomplete"], "disposition": None, "active": False,
                   "built": True, "undeclared-session": None,
                   "row-outcome": {"stop": []}, "unmet-after": []}) is False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [c for c, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

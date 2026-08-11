#!/usr/bin/env python3
"""probe-checkout-disposition.py — task 7.676: `coordinate checkout` gets an HONEST ending, and
VERIFIES before it asserts a verified one.

WHAT THIS SCORES OVER, stated per arm, because "probes pass" reads as a clean class and is not:

  A1 (GREEN, the criterion)  A seat whose DECLARED output exists checks out `done`, and a seat
      that produced NOTHING does not — it is REFUSED, its roster row is left ACTIVE and no
      disposition record is written at all. This is the whole of the 2026-08-09 incident inverted:
      the two seats are now DISTINGUISHABLE at their ending.
  A2 (the honest ending)     The barren seat's `--incomplete "<reason>"` SUCCEEDS, and the
      durable record carries disposition `incomplete` WITH the seat's reason. Without this arm A1
      would be satisfied by a checkout that simply cannot be completed, which is a worse tool.
  A3 (RED, and the point)    The SAME barren seat, against a MUTANT coord.py carrying the
      pre-7.676 seams, checks out `done` — silently, with no refusal. An assertion that cannot go
      red is not an assertion; this is the old behaviour, executed, not described.
  A4 (no silent advancement) `incomplete` is NOT in the fast path's advancing set: the edge fast
      path gates on equality with `done` alone, so the honest ending cannot advance a DAG edge.
      Scored on the CONSTANT the executor reads, not on a comment.
  A5 (the enum invariants)   The three closure properties the in-file self-test asserts for this
      domain — the record enum's writer bounds, the deferral-class closure, and the bridge to
      `LIFECYCLE_INTENT_OF`. ⚠ THEY ARE RE-ASSERTED HERE ON PURPOSE: `coord.py selftest` ABORTS
      on Windows at check 12 (`tmux` is absent — `FileNotFoundError: [WinError 2]`), identically
      before and after this change, so every self-test row for this domain is UNREACHABLE on a
      Windows box. A guard that only runs on one of the two machines this kit is developed on is
      half a guard.

WHAT IT DELIBERATELY DOES NOT SCORE: the tmux half of a check-out (the transcript export, the
pane kill, the renewal fork). Those need a live tmux and this probe runs where there is none —
`--no-export` is the sanctioned escape and it is what every arm here uses. The renew arm is
untouched by this task and is left to the self-test.

Every write lands in a temp package. The LIVE run package is never touched, and `coord.py` is
imported as a MODULE (never re-saved) — this probe reads the kit, it never installs into it.

Run: python probe-checkout-disposition.py   ->  exit 0 all green, exit 1 on any failure.
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"

RESULTS = []


def check(claim, ok):
    RESULTS.append((claim, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'}  {claim}")


class _NoTmux:
    """A `subprocess` stand-in: every call SUCCEEDS with empty output.

    ⚠ IT REPLACES THE MODULE ATTRIBUTE, NOT INDIVIDUAL `tmux_*` HELPERS. There are ~20 scattered
    `subprocess.run(["tmux", ...])` call sites in coord.py and stubbing them one by one is a list
    that rots the day a twenty-first lands — the seam every one of them passes through is the
    module reference. What this probe scores is the BOOKKEEPING of a check-out (which disposition
    is recorded, and whether it is recorded at all); the pane manipulation is not its subject and
    is not available on this platform anyway.
    """

    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(self, *_a, **_k):
        return self._R()

    def __getattr__(self, name):                       # DEVNULL, PIPE, TimeoutExpired, …
        import subprocess as _s
        return getattr(_s, name)


def load_coord(path, name):
    """Import a coord.py (the real one or a mutant) as its own module object."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.subprocess = _NoTmux()
    return mod


def make_package(root, seats):
    """A minimal run package: `coordination/` plus one descriptor per (seat, outputs) pair."""
    pkg = Path(root)
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    for seat, outputs in seats.items():
        d = pkg / "workers" / seat
        d.mkdir(parents=True, exist_ok=True)
        decl = f"outputs: {outputs}\n" if outputs else ""
        (d / "agent.md").write_text(
            f"---\nagent: {seat}\n{decl}cwd: {d}\n---\n\n# {seat}\nbrief\n", encoding="utf-8")
    return pkg


def ns(mod, pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None, "as_agent": None, "force": False}
    d.update(kw)
    return argparse.Namespace(**d)


def checkin(mod, pkg, seat, pane):
    mod.harness_outcome(mod.cmd_checkin,
                        ns(mod, pkg, agent=seat, summary="probe pass", pane=pane, force=False))


def checkout(mod, pkg, seat, **kw):
    """(combined output, exit code) — 0 means the command RETURNED rather than refusing."""
    d = {"agent": seat, "no_export": True, "renew": False, "handoff": None,
         "handoff_file": None, "incomplete": None, "pane": None}
    d.update(kw)
    out, err, code = mod.harness_outcome(mod.cmd_checkout, ns(mod, pkg, **d))
    return out + err, (0 if code is None else code)


def disposition_of(pkg, seat):
    """The seat's durable disposition record, or None when the check-out wrote none."""
    p = Path(pkg) / "coordination" / f"disposition-{seat}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def active(mod, pkg, seat):
    _, _, rows = mod.load_workers(mod.base_dir(ns(mod, pkg)))
    row = mod.current_row(rows, seat)
    return bool(row) and row["active"] == "yes"


def build_mutant(dest_dir):
    """coord.py with the TWO 7.676 seams reverted — the pre-fix program, reconstructed.

    ⚠ IT IS BUILT BY SURGERY ON THE LIVE FILE, never by reading an old commit: after this task
    commits, `HEAD` IS the fix, so a git-sourced mutant would silently become a copy of the
    subject and the red arm would go green forever while reading as a mutation test. Both
    replacements assert they matched — a mutation that did not apply is scored as a probe failure,
    not as a passing red arm (a no-op mutant is the classic false catch).
    """
    src = COORD.read_text(encoding="utf-8")
    seams = [
        # (1) the verification gate never runs — the pre-7.676 check-out opened nothing
        ("    if not renew and not incomplete:\n        _declared, _missing",
         "    if False:\n        _declared, _missing"),
        # (2) the disposition collapses to the old two-arm expression
        ('checkout_disposition = "renew" if renew else ("incomplete" if incomplete else "done")',
         'checkout_disposition = "renew" if renew else "done"'),
    ]
    for old, new in seams:
        if old not in src:
            return None, f"mutation seam NOT FOUND, mutant not built: {old[:60]!r}"
        src = src.replace(old, new, 1)
    dest = Path(dest_dir) / "coord.py"
    dest.write_text(src, encoding="utf-8")
    for sib in KIT.glob("*.py"):                        # a mutant runs only beside its siblings
        if sib.name != "coord.py":
            shutil.copyfile(sib, Path(dest_dir) / sib.name)
    return dest, ""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-7676-"))
    try:
        mod = load_coord(COORD, "coord_subject")

        # ---- A1 + A2: the live subject -------------------------------------------------------
        pkg = make_package(tmp / "live", {"produced": "deliverable.md", "barren": "deliverable.md"})
        (pkg / "workers" / "produced" / "deliverable.md").write_text("the work\n", encoding="utf-8")

        checkin(mod, pkg, "produced", "%1")
        out_p, code_p = checkout(mod, pkg, "produced")
        rec_p = disposition_of(pkg, "produced")
        check("A1(green): a seat whose DECLARED output exists checks out cleanly and records "
              "`done` — the fix does not break the path that was already honest",
              code_p == 0 and rec_p is not None and rec_p["disposition"] == "done")
        check("A1(green): and the record SAYS the outputs were verified, so a reader can tell a "
              "CHECKED `done` from an asserted one without trusting it",
              rec_p is not None and "verified" in rec_p.get("outputs-verified", ""))

        checkin(mod, pkg, "barren", "%2")
        out_b, code_b = checkout(mod, pkg, "barren")
        check("A1(RED-SIDE, the criterion): a seat that produced NOTHING is REFUSED a plain "
              "check-out — it does not end the same way as the seat that produced its output",
              code_b != 0)
        check("A1: the refusal NAMES the missing declared path and teaches the honest ending, so "
              "the seat is told what to do rather than merely told no",
              "deliverable.md" in out_b and "--incomplete" in out_b)
        check("A1: and the refusal COSTS THE SEAT NOTHING — its roster row is still ACTIVE and NO "
              "disposition record was written, so a refused check-out is re-runnable",
              active(mod, pkg, "barren") and disposition_of(pkg, "barren") is None)

        out_i, code_i = checkout(mod, pkg, "barren", incomplete="the spec I was to review "
                                                               "was never written")
        rec_i = disposition_of(pkg, "barren")
        check("A2: the same seat's `--incomplete \"<reason>\"` SUCCEEDS and records disposition "
              "`incomplete` — the honest ending EXISTS and is what the record carries",
              code_i == 0 and rec_i is not None and rec_i["disposition"] == "incomplete")
        check("A2: the seat's REASON is on the durable record, not only on its screen — an ending "
              "whose reason lives in a terminal nobody read is an ending nobody can act on",
              rec_i is not None and "never written" in rec_i.get("incomplete-reason", ""))
        check("A2: and the roster row is CLOSED by it — the honest ending really ends the seat "
              "rather than leaving it half-checked-out",
              not active(mod, pkg, "barren"))

        # ---- A3: the mutant — the pre-7.676 behaviour, EXECUTED --------------------------------
        mdir = tmp / "mutant"
        mdir.mkdir()
        mpath, merr = build_mutant(mdir)
        if mpath is None:
            check(f"A3(red): the mutant could not be built — {merr}", False)
        else:
            mut = load_coord(mpath, "coord_mutant")
            mpkg = make_package(tmp / "mutant-run", {"barren": "deliverable.md"})
            checkin(mut, mpkg, "barren", "%3")
            out_m, code_m = checkout(mut, mpkg, "barren")
            rec_m = disposition_of(mpkg, "barren")
            check("A3(RED): against the pre-7.676 seams the SAME barren seat — no declared output "
                  "on disk — checks out SUCCESSFULLY and records `done`. This is the measured "
                  "2026-08-09 behaviour, run rather than described, and it is what makes every "
                  "green arm above a real assertion",
                  code_m == 0 and rec_m is not None and rec_m["disposition"] == "done")

        # ---- A4: the honest ending cannot advance an edge --------------------------------------
        spec = importlib.util.spec_from_file_location("edge_runner_job", mod.EDGE_RUNNER_JOB_PATH)
        edge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(edge)
        fired = edge.checkout_fastpath(mod, Path(pkg), "barren", "incomplete")
        check("A4: the edge fast path REFUSES to fire on `incomplete` — called for real, not "
              "grepped. Gate 1 is an equality against `done` alone, so the honest ending cannot "
              "advance a DAG edge; this is the property that makes `incomplete` safe to offer",
              isinstance(fired, dict) and not fired.get("fired")
              and edge.ADVANCES_EDGE == "done")
        # ⚠ A4b IS A DISCLOSURE ARM, AND IT ASSERTS THE SAFE HALF ONLY. `edge-runner-job.py` keeps
        # its OWN hardcoded copy of coord's record enum (`EXPECTED_ENUM`), and 7.676 could not
        # widen it — that file is outside this task's allowlist. The consequence is BENIGN BUT
        # WRONG-WORDED: an `incomplete` seat grades as UNDECIDED ("outside coord's closed enum …
        # cannot have been written through the kit") rather than as the declared not-done ending
        # it is. Nothing advances either way, which is why this is a follow-up and not a blocker.
        # The arm below scores the SAFETY property, which holds before AND after that copy is
        # widened — an arm that went red the day someone fixed the drift would be a guard against
        # the repair.
        check("A4b: whatever the second enum copy in `edge-runner-job.py` says about it, "
              "`incomplete` is not the advancing value — the ONE property this task must not "
              "leave to a hardcoded mirror",
              edge.ADVANCES_EDGE != "incomplete")

        # ---- A5: the closure properties the Windows-aborted self-test cannot reach --------------
        check("A5: `incomplete` is admitted from the SEAT and from nobody else — the kit may not "
              "put this word in a seat's mouth, because only the occupant witnesses it",
              mod.RECORD_DISPOSITION_WRITER["incomplete"] == frozenset({mod.DISPOSITION_WRITER_SEAT}))
        refused = []
        for writer in (mod.DISPOSITION_WRITER_KIT, mod.DISPOSITION_WRITER_LEADER):
            try:
                mod.validate_disposition("incomplete", writer)
            except ValueError:
                refused.append(writer)
        check("A5: and the WRITE BOUNDARY enforces that — both the kit and the leader are refused "
              "the value, loudly, at the moment they would write it",
              len(refused) == 2)
        check("A5: every value the write boundary admits has a deferral class — set equality, so "
              "a disposition minted without a class cannot silently read as `terminal-unenumerated`",
              set(mod._DEFERRAL_BY_DISPOSITION) == set(mod.RECORD_DISPOSITION_WRITER))
        check("A5: every deferral class has a verdict, `declared-incomplete` included — the class "
              "map is what routes this ending to the leader",
              set(mod._DEFERRAL_BY_DISPOSITION.values()) <= set(mod.CLASS_TO_VERDICT)
              and "declared-incomplete" in mod.CLASS_TO_VERDICT)
        # ---- A6 (7.711): a MALFORMED `outputs:` is refused by name, not left unsatisfiable -------
        # The pre-7.711 program had no arm here and none of the 16 above reach it: every one of them
        # declares a WELL-FORMED value. The three shapes below all parsed to a path that can never
        # exist, so the seat was hard-blocked out of `done` forever — and the block-YAML case is the
        # cruel one, because the author DID produce the file the block declares.
        for shape, decl, produced in (
                ("block-YAML",     "\n  - plan.md", "plan.md"),
                ("bracket-list",   "[a.md, b.md]",  "a.md"),
                ("inline-comment", "plan.md  # the plan", "plan.md")):
            mp = make_package(tmp / f"malformed-{shape}", {"author": decl})
            (mp / "workers" / "author" / produced).write_text("delivered\n", encoding="utf-8")
            checkin(mod, mp, "author", "%9")
            out_x, code_x = checkout(mod, mp, "author")
            check(f"A6({shape}): the descriptor is REFUSED BY NAME at check-out — the author is "
                  f"told the declaration is malformed, not handed an unsatisfiable missing-path "
                  f"list for a file they already produced",
                  code_x != 0 and "refused [coord input]" in out_x and "outputs:" in out_x
                  and "MISSING (or empty)" not in out_x
                  and active(mod, mp, "author") and disposition_of(mp, "author") is None)

        bridge = [v for vs in mod.LIFECYCLE_INTENT_OF.values()
                  if vs is not mod.LIFECYCLE_INTENT_ABSENT for v in vs]
        check("A5: the bridge holds — every checkout intent the executor's argv maps to is a "
              "member of the record enum, and `close` admits `incomplete` so an honestly-ended "
              "seat is still CLOSABLE (without this the honest ending would be unclosable, which "
              "is how a tool teaches its seats to lie again)",
              bridge and all(v in mod.RECORD_DISPOSITION_WRITER for v in bridge)
              and "incomplete" in mod.LIFECYCLE_INTENT_OF["close"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} green")
    if failed:
        print(f"FAILED {len(failed)}:")
        for c in failed:
            print(f"  - {c}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""probe-g188-daemon-identity.py — the daemon-restart detector, and the trap it must not fall into.

WHAT IS UNDER TEST (run issue G-188): the run had no detector for "the ignite daemon restarted".
It tracked MainPID in prose, in a handoff doc, by hand — and prose does not execute. Twice on
2026-07-27 an owner-side restart was invisible to the run; the second cost ~50 minutes of a false
picture and an owner brief that had to be withdrawn.

WHY A PROBE AND NOT A SELFTEST CASE. Two of the four properties below are about what the code does
with an answer it CANNOT GET — a shape that is invisible to any test which only exercises the happy
path, and which was the failure mode of the feature this one is modelled on.

⚠⚠ THE PROPERTY THIS PROBE EXISTS FOR (arm B). The unit is USER-scoped. Asking the SYSTEM bus for
it returns, measured on this box against the live daemon:
      LoadState=not-found  ActiveState=inactive  SubState=dead  MainPID=0   exit 0
which is BYTE-IDENTICAL to what the user bus returns for a unit that genuinely does not exist. Exit
status is 0 both times. So "the daemon is gone" and "I asked the wrong bus" ARE THE SAME ANSWER.
A detector that reports `not-found` as ABSENT is therefore asserting a fact it cannot hold, and it
would state it most confidently at the exact moment it is wrong. The reasonable-looking
implementation — trust LoadState, report absent — passes every happy-path check and fails here.

RUN IT:  python3 probes/probe-g188-daemon-identity.py
Exit 0 = all arms pass. Exit 1 = a property is broken. Exit 2 = the probe could not run (never a
pass: a probe that cannot execute has proven nothing, and reporting that as green is the very
absence-reads-as-health shape under test).
"""

import json
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

try:
    import coord  # noqa: E402
    import watch  # noqa: E402
except Exception as exc:  # noqa: BLE001 — a probe that cannot import proves nothing
    print(f"INOPERATIVE: could not import the kit ({exc})")
    sys.exit(2)

FAILED = []
PASSED = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


SEEN_ARGV = []


def fake_systemctl(stdout, returncode=0, stderr=""):
    """Substitute the ONE call daemon_identity makes. The point is to hand it answers this box
    cannot be made to produce on demand — a stopped daemon, an unreadable one — without touching
    the live unit, which is running the run's own jobs."""
    class R:
        pass
    r = R()
    r.stdout, r.returncode, r.stderr = stdout, returncode, stderr

    def run(*a, **k):
        # The argv is CAPTURED, not merely answered. Without this the substitution hides the one
        # thing that matters most: a version of the code that dropped `--user` would be handed the
        # user-bus answer anyway and would pass every other check in this file. The probe would
        # then certify the exact defect it was written for.
        SEEN_ARGV.append(list(a[0]) if a and isinstance(a[0], (list, tuple)) else [])
        return r
    return run


SYSTEM_SCOPE_ANSWER = (  # verbatim shape of the WRONG-BUS answer, measured 2026-07-28
    "LoadState=not-found\nActiveState=inactive\nSubState=dead\n"
    "ActiveEnterTimestamp=\nInvocationID=\nMainPID=0\n")

RUNNING_ANSWER = (
    "LoadState=loaded\nActiveState=active\nSubState=running\n"
    "ActiveEnterTimestamp=Tue 2026-07-28 03:45:03 UTC\n"
    "InvocationID=68bb9e190b2141c187e290e0a510bd55\nMainPID=2561514\n")

STOPPED_ANSWER = (
    "LoadState=loaded\nActiveState=inactive\nSubState=dead\n"
    "ActiveEnterTimestamp=\nInvocationID=\nMainPID=0\n")


def main():
    orig_run = watch.subprocess.run
    try:
        print("\nARM A — a determinate running unit is read as running (the control).")
        watch.subprocess.run = fake_systemctl(RUNNING_ANSWER)
        a = watch.daemon_identity()
        check("state is running", a.get("state") == "running", repr(a.get("state")))
        check("pid is the unit's MainPID as an int", a.get("pid") == 2561514, repr(a.get("pid")))
        check("invocation is carried (the restart key)",
              a.get("invocation") == "68bb9e190b2141c187e290e0a510bd55")
        check("the reading carries the unit it asked about",
              a.get("unit") == watch.IGNITE_UNIT, repr(a.get("unit")))
        # ⚠ ASSERTED AGAINST THE ARGV THE CODE ACTUALLY BUILT, not against the answer it got back.
        # The substitution would happily hand a user-bus answer to a query that never asked the
        # user bus, and every other check here would still pass.
        check("the query is USER-scoped — the flag is in the argv, not in a comment",
              bool(SEEN_ARGV) and "--user" in SEEN_ARGV[-1],
              " ".join(SEEN_ARGV[-1]) if SEEN_ARGV else "no call captured")
        check("and it asks about the unit it reports on",
              bool(SEEN_ARGV) and watch.IGNITE_UNIT in SEEN_ARGV[-1])

        print("\nARM B — THE ONE THAT MATTERS: the wrong-bus answer is UNKNOWN, never absent.")
        watch.subprocess.run = fake_systemctl(SYSTEM_SCOPE_ANSWER)
        b = watch.daemon_identity()
        check("state is unknown", b.get("state") == "unknown", repr(b.get("state")))
        check("state is NOT stopped/absent — the claim it cannot hold",
              b.get("state") not in ("stopped", "absent", "gone"))
        check("the reason names the ambiguity rather than asserting absence",
              "indistinguishable" in (b.get("why") or ""), repr(b.get("why"))[:90])

        print("\nARM C — a unit that answered FOR ITSELF is reportable as stopped.")
        watch.subprocess.run = fake_systemctl(STOPPED_ANSWER)
        cc = watch.daemon_identity()
        check("state is stopped (loaded + inactive is determinate)",
              cc.get("state") == "stopped", repr(cc.get("state")))
        check("arm B and arm C reach DIFFERENT verdicts from a near-identical answer",
              cc.get("state") != b.get("state"),
              "both say inactive/dead/MainPID=0; only LoadState differs")

        print("\nARM D — the call failing is UNKNOWN, and never a crash of the watch loop.")
        watch.subprocess.run = fake_systemctl("", returncode=1, stderr="Failed to connect to bus")
        d = watch.daemon_identity()
        check("non-zero exit yields unknown", d.get("state") == "unknown")

        def boom(*a, **k):
            raise OSError("no systemctl on this box")
        watch.subprocess.run = boom
        e = watch.daemon_identity()
        check("a raising systemctl yields unknown, not an exception",
              e.get("state") == "unknown", repr(e.get("why"))[:70])

        print("\nARM E — the restart comparison: claimed only between DETERMINATE readings.")
        r1 = {"state": "running", "pid": 1, "invocation": "aaa"}
        r2 = {"state": "running", "pid": 2, "invocation": "bbb"}
        unk = {"state": "unknown", "why": "x"}
        check("a changed invocation IS a restart", watch._daemon_change(r1, r2) is not None)
        check("an unchanged invocation is NOT", watch._daemon_change(r1, dict(r1)) is None)
        check("running -> unknown is NOT claimed as a restart",
              watch._daemon_change(r1, unk) is None, "a measurement failing is not an event")
        check("unknown -> running is NOT claimed as a restart",
              watch._daemon_change(unk, r2) is None)
        check("running -> stopped IS a change worth recording",
              watch._daemon_change(r1, {"state": "stopped", "why": "y"}) is not None)
        chg = watch._daemon_change(r1, r2)
        check("the record carries both sides and a timestamp",
              chg.get("from") == r1 and chg.get("to") == r2 and bool(chg.get("at")))

        print("\nARM F — the reader: absence is UNKNOWN at the reader too, and stickiness holds.")
        fold, loud = coord._heartbeat_daemon_lines({}, False)
        check("a heartbeat with no daemon key renders UNKNOWN, not silence",
              fold == "" and any("UNKNOWN" in ln for _, ln in loud), repr(loud)[:80])
        fold, loud = coord._heartbeat_daemon_lines({"daemon": a}, False)
        check("a running daemon folds into the ok line and takes no line of its own",
              "2561514" in fold and not loud, repr(fold))
        fold, loud = coord._heartbeat_daemon_lines({"daemon": b}, False)
        check("the reader's UNKNOWN line teaches the --user check",
              any("--user" in ln for _, ln in loud))
        check("the reader's UNKNOWN line refuses to call it absent",
              all("is absent" not in ln.replace("NOT a report that the daemon is absent", "")
                  for _, ln in loud))
        fold, loud = coord._heartbeat_daemon_lines({"daemon": a, "daemon_change": chg}, False)
        check("a recorded restart prints even while the daemon is healthy NOW",
              any("RESTARTED" in ln for _, ln in loud),
              "the sticky record is the whole point: both real restarts were noticed hours late")
        fold, loud = coord._heartbeat_daemon_lines({"daemon": a}, True)
        check("a STALE watcher's reading is qualified as stale, never sold as live",
              "STALE" in fold, repr(fold))

        print("\nARM G — end to end on a real package: write a heartbeat, read it back.")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            watch.subprocess.run = fake_systemctl(RUNNING_ANSWER)
            watch.save_heartbeat(base, 10)
            hb1 = json.loads((base / "watch-heartbeat.json").read_text())
            check("the heartbeat carries the daemon reading",
                  hb1.get("daemon", {}).get("pid") == 2561514)
            check("no change is claimed on the first pass ever",
                  hb1.get("daemon_change") is None)
            watch.subprocess.run = fake_systemctl(
                RUNNING_ANSWER.replace("MainPID=2561514", "MainPID=9999")
                              .replace("68bb9e190b2141c187e290e0a510bd55", "ffff" * 8))
            watch.save_heartbeat(base, 10)
            hb2 = json.loads((base / "watch-heartbeat.json").read_text())
            check("the second pass records the restart",
                  (hb2.get("daemon_change") or {}).get("to", {}).get("pid") == 9999)
            watch.save_heartbeat(base, 10)
            hb3 = json.loads((base / "watch-heartbeat.json").read_text())
            check("and it STICKS across a later unchanged pass",
                  (hb3.get("daemon_change") or {}).get("to", {}).get("pid") == 9999,
                  "a signal that expires after one pass reproduces the original miss")
            watch.subprocess.run = fake_systemctl(SYSTEM_SCOPE_ANSWER)
            watch.save_heartbeat(base, 10)
            hb4 = json.loads((base / "watch-heartbeat.json").read_text())
            check("an UNKNOWN pass does not erase the recorded restart",
                  (hb4.get("daemon_change") or {}).get("to", {}).get("pid") == 9999)
            check("nor does it overwrite it with a fabricated change",
                  hb4["daemon"]["state"] == "unknown")
    finally:
        watch.subprocess.run = orig_run

    print(f"\nCHECKS {len(PASSED)}/{len(PASSED) + len(FAILED)}")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 31:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 31")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

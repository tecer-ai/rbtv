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
        print("\nARM H — the PUSH flag: it earns its interruption or it stays quiet.")
        # Sequences are driven through check_daemon directly with a persistent sysstate, which is
        # exactly how the pass drives it. The assertions were written in DESIGN-daemon-push-flag.md
        # BEFORE this code existed, so they cannot have been shaped to fit what got built.
        RUN = {"state": "running", "unit": "u", "pid": 1, "invocation": "aaa"}
        RUN2 = {"state": "running", "unit": "u", "pid": 2, "invocation": "bbb"}
        DOWN = {"state": "stopped", "unit": "u", "why": "ActiveState=inactive"}
        UNK = {"state": "unknown", "unit": "u", "why": "wrong bus"}

        st, notes = {}, []
        for _ in range(3):
            watch.check_daemon(st, DOWN, None, notes)
        check("DOWN across three passes raises exactly ONE flag", len(notes) == 1, f"{len(notes)}")
        check("and the flag says the daemon is down", "DOWN" in (notes[0] if notes else ""))

        watch.check_daemon(st, RUN, None, notes)
        check("recovery with no change record clears the episode silently", len(notes) == 1)
        # ⚠ THE CHECK ABOVE WAS ONCE THE ONLY ONE HERE, AND IT WAS A FIXTURE SHAPED TO DODGE THE
        # REAL PATH. It passes `change=None`, but a real recovery ALWAYS carries a change record —
        # stopped -> running is a determinate transition, so `_daemon_change` records it. Measured
        # in live-fire against a real systemd unit: the recovery pass DID flag, and it should, since
        # a room that was told the daemon died must be told it came back. The probe said otherwise
        # only because its fixture could not happen.
        st2, notes2 = {}, []
        watch.check_daemon(st2, DOWN, None, notes2)
        watch.check_daemon(st2, RUN, {"at": "T", "from": DOWN, "to": RUN}, notes2)
        check("a REAL recovery (which always carries a change) ANNOUNCES the return",
              len(notes2) == 2, "the room that heard it died must hear it is back")
        check("and the down-episode is cleared so a later outage flags again",
              "notified_daemon_down" not in st2)
        for _ in range(2):
            watch.check_daemon(st, DOWN, None, notes)
        check("a SECOND outage flags again (the episode re-armed)", len(notes) == 2)

        st, notes = {}, []
        chg = {"at": "T", "from": RUN, "to": RUN2}
        for _ in range(4):
            watch.check_daemon(st, RUN2, chg, notes)
        check("a restart flags ONCE even though the change record is sticky",
              len(notes) == 1, f"{len(notes)} — keyed on the invocation, not on the record existing")
        check("the restart flag carries both pids", "1 -> 2" in (notes[0] if notes else ""))
        check("and it repeats the bound rather than implying more",
              "never WHICH CODE" in (notes[0] if notes else ""))
        chg2 = {"at": "T2", "from": RUN2, "to": {**RUN, "invocation": "ccc", "pid": 3}}
        watch.check_daemon(st, {**RUN, "invocation": "ccc", "pid": 3}, chg2, notes)
        check("a genuinely NEW restart flags again", len(notes) == 2)

        st, notes = {}, []
        for d in (UNK, UNK, UNK):
            watch.check_daemon(st, d, None, notes)
        check("UNKNOWN never pushes, in any sequence position", not notes, repr(notes)[:60])
        st, notes = {}, []
        watch.check_daemon(st, DOWN, None, notes)
        watch.check_daemon(st, UNK, None, notes)
        watch.check_daemon(st, DOWN, None, notes)
        check("an UNKNOWN pass does NOT re-arm a live DOWN episode",
              len(notes) == 1, f"{len(notes)} — an unreadable pass must not manufacture a repeat")

        st = {"notified_pressure": True, "windows": {"w": 1}, "notified_daemon_down": True}
        notes = []
        watch.check_daemon(st, RUN, None, notes)
        check("foreign sysstate keys are left byte-untouched",
              st.get("notified_pressure") is True and st.get("windows") == {"w": 1})
        check("and only the daemon's own key is cleared on recovery",
              "notified_daemon_down" not in st)

        st, notes = {}, []
        line = watch.check_daemon(st, RUN, None, notes)
        check("a healthy first pass on virgin state is SILENT", not notes)
        check("the report row still renders it", "daemon" in line and "ok" in line, line.strip())
        check("a DOWN row renders DOWN, not ok",
              "DOWN" in watch.check_daemon({}, DOWN, None, []))
        check("an UNKNOWN row renders UNKNOWN rather than looking healthy",
              "UNKNOWN" in watch.check_daemon({}, UNK, None, []))

        print("\nARM J — the CRASH LOOP, which is the shape the real incident took.")
        # 2026-07-27 16:15: the daemon was down with `NRestarts=32 and climbing every 5 seconds`,
        # and the run learned it from a seat noticing BY HAND. A steady outage is binary and gets
        # one flag; a crash loop is MONOTONIC and is PROP-9's deterioration case. This arm is the
        # difference, and it exists because the run's own history refuted the first design.
        def down(n):
            return {"state": "stopped", "unit": "u", "why": "ActiveState=failed", "restarts": n}

        st, notes = {}, []
        watch.check_daemon(st, down(30), None, notes)
        check("a first DOWN pass flags once", len(notes) == 1)
        watch.check_daemon(st, down(30), None, notes)
        check("a STEADY outage (count unmoved) does NOT re-flag", len(notes) == 1)
        watch.check_daemon(st, down(32), None, notes)
        check("a CLIMBING restart count DOES re-flag — deterioration, not repetition",
              len(notes) == 2, "PROP-9's ruling, not my binary argument")
        check("and the flag names it as a crash loop with both counts",
              "CRASH-LOOPING" in notes[-1] and "30 -> 32" in notes[-1], notes[-1][-60:])
        watch.check_daemon(st, down(32), None, notes)
        check("then goes quiet again while the count holds still", len(notes) == 2)

        st, notes = {}, []
        watch.check_daemon(st, {**RUN, "restarts": 32}, None, notes)
        check("a unit that crash-looped BEFORE this code landed is seeded QUIETLY",
              not notes, "a fix whose first act is a false alarm teaches the room to discount it")
        check("and the seed is the systemd count, not zero",
              st.get("daemon_restarts_flagged") == 32)
        watch.check_daemon(st, down(32), None, notes)
        check("a later genuine outage still flags", len(notes) == 1)

        st, notes = {}, []
        watch.check_daemon(st, down(None), None, notes)
        watch.check_daemon(st, down(None), None, notes)
        check("an UNREADABLE restart count never fabricates a climb",
              len(notes) == 1, "None must mean no comparison, never 0")
        # ⚠ THE CHECK ABOVE IS NOT ENOUGH AND A MUTANT PROVED IT: it hands check_daemon a None it
        # constructed itself, so it never exercises the PARSER that has to produce that None. A
        # mutant defaulting an unreadable NRestarts to 0 passed all 60 checks. The property has to
        # be asserted where it is DECIDED — 0 is a real, healthy value here, so returning it on a
        # failed read reports the best possible answer at the moment the read broke.
        watch.subprocess.run = fake_systemctl(STOPPED_ANSWER)   # carries NO NRestarts line
        parsed = watch.daemon_identity()
        check("an ABSENT NRestarts parses to None, never to 0",
              parsed.get("restarts") is None, repr(parsed.get("restarts")))
        watch.subprocess.run = fake_systemctl(RUNNING_ANSWER.replace(
            "MainPID=2561514", "NRestarts=notanumber\nMainPID=2561514"))
        check("an UNPARSEABLE NRestarts also parses to None",
              watch.daemon_identity().get("restarts") is None)
        watch.subprocess.run = fake_systemctl(RUNNING_ANSWER.replace(
            "MainPID=2561514", "NRestarts=0\nMainPID=2561514"))
        check("a genuine zero still parses as 0, not None — the two are different facts",
              watch.daemon_identity().get("restarts") == 0)
        line = watch.check_daemon({}, {**RUN, "restarts": 7}, None, [])
        check("the report row surfaces a non-zero restart count", "restarts: 7" in line, line.strip())
        line = watch.check_daemon({}, RUN, None, [])
        check("and stays terse at zero", "restarts" not in line, line.strip())

        print("\nARM I — one reading per pass: the flag and the heartbeat cannot disagree.")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            SEEN_ARGV.clear()
            watch.subprocess.run = fake_systemctl(RUNNING_ANSWER)
            d1, c1 = watch.daemon_reading(base)
            watch.save_heartbeat(base, 10, d1, c1)
            check("daemon_reading + save_heartbeat issue exactly ONE systemctl call",
                  len(SEEN_ARGV) == 1,
                  f"{len(SEEN_ARGV)} — two calls per pass can straddle a restart and disagree")
            hb = json.loads((base / "watch-heartbeat.json").read_text())
            check("and the heartbeat records the very reading the flag saw",
                  hb["daemon"] == d1)
    finally:
        watch.subprocess.run = orig_run

    print(f"\nCHECKS {len(PASSED)}/{len(PASSED) + len(FAILED)}")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 65:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 65")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

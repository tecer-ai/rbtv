#!/usr/bin/env python3
"""probe-g188-daemon-identity.py — the daemon's four systemd verdicts, and the traps they must
not fall into. REPOINTED at the daemon-watchdog capability (task 7.35, run decision D8) when
`ignite/team-kit/watch.py`, its original subject, was deleted.

WHAT IS UNDER TEST (run issue G-188): the run had no detector for "the ignite daemon restarted".
It tracked MainPID in prose, in a handoff doc, by hand — and prose does not execute. Twice on
2026-07-27 an owner-side restart was invisible to the run; the second cost ~50 minutes of a false
picture and an owner brief that had to be withdrawn. The four verdicts now live in the watchdog
(`daemon_identity` · `_daemon_change` · `identity_verdict` · `daemon_code_state` ·
`check_daemon` · `daemon_verdicts`), because the watchdog's own `daemon` row asks the GATEWAY and
the gateway's answer carries no identity that can be correlated across passes.

WHY A PROBE AND NOT A SELFTEST CASE. Most of the properties below are about what the code does
with an answer it CANNOT GET — a shape invisible to any test that only exercises the happy path,
and the failure mode of the feature this one is modelled on.

⚠⚠ THE PROPERTY THIS PROBE EXISTS FOR (arm B). The unit is USER-scoped. Asking the SYSTEM bus for
it returns, measured on this box against the live daemon:
      LoadState=not-found  ActiveState=inactive  SubState=dead  MainPID=0   exit 0
which is BYTE-IDENTICAL to what the user bus returns for a unit that genuinely does not exist.
Exit status is 0 both times. So "the daemon is gone" and "I asked the wrong bus" ARE THE SAME
ANSWER. A detector reporting `not-found` as ABSENT asserts a fact it cannot hold, and states it
most confidently at the exact moment it is wrong.

FIXTURE-DRIVEN, so it runs on ANY host (run decision D4): every systemd answer is substituted,
every file it touches is in a temp dir. It never calls systemctl, never touches the live unit,
never writes into the real `.rbtv/runtime/`.

RUN IT:  python3 probes/probe-g188-daemon-identity.py
  RBTV_WATCHDOG_TOOL_PATH=<path>  point it at another copy of the tool — this is how the
  red-first control runs it against the PRE-CHANGE watchdog.
Exit 0 = all arms pass. Exit 1 = a property is broken. Exit 2 = the probe could not run (never a
pass: a probe that cannot execute has proven nothing, and reporting that as green is the very
absence-reads-as-health shape under test).
"""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = os.environ.get("RBTV_WATCHDOG_TOOL_PATH") or str(HERE.parent / "tool" / "rbtv-ignite-watchdog")

try:
    # The tool is an extensionless executable, so it is loaded by path rather than imported.
    _spec = importlib.util.spec_from_loader(
        "rbtv_ignite_watchdog", SourceFileLoader("rbtv_ignite_watchdog", TOOL))
    W = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(W)
except Exception as exc:  # noqa: BLE001 — a probe that cannot import proves nothing
    print(f"INOPERATIVE: could not load the watchdog tool at {TOOL} ({exc})")
    sys.exit(2)

FAILED = []
PASSED = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


SEEN_ARGV = []


def fake_systemctl(stdout, returncode=0, stderr=""):
    """Substitute the ONE call daemon_identity makes, at the watchdog's own `run()` helper.
    The point is to hand it answers this box cannot be made to produce on demand — a stopped
    daemon, an unreadable one — without touching the live unit."""
    out = ((stdout or "") + (stderr or "")).strip()

    def run(*a, **k):
        # The argv is CAPTURED, not merely answered. Without this the substitution hides the one
        # thing that matters most: a version that dropped `--user` would be handed the user-bus
        # answer anyway and would pass every other check in this file. The probe would then
        # certify the exact defect it was written for.
        SEEN_ARGV.append(list(a[0]) if a and isinstance(a[0], (list, tuple)) else [])
        return returncode, out
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

# ⚠ THE RED-FIRST CONTROL, and it is a check rather than a crash. Run against a watchdog that
# does not carry the verdicts (RBTV_WATCHDOG_TOOL_PATH=<pre-change copy>), an unguarded call
# would die at the first AttributeError and report ONE traceback for FOUR missing verdicts.
# Each verdict is named and reported red on its own line instead.
VERDICT_MEMBERS = [
    ("RESTARTED — a new InvocationID across passes", ("daemon_identity", "_daemon_change",
                                                      "check_daemon")),
    ("CRASH-LOOP — systemd's NRestarts climbing across passes", ("check_daemon",)),
    ("IDENTITY — the running daemon compared, not merely printed", ("identity_verdict",)),
    ("STALE CODE — the boot marker correlated InvocationID-first", ("daemon_code_state",)),
    ("one reading per pass, persisted for the next one", ("daemon_verdicts",
                                                          "load_daemon_state",
                                                          "save_daemon_state")),
    ("the daemon row's RESTART GATE — liveness, 3 strikes, backoff (2026-08-14)",
     ("daemon_restart_gate", "load_failcount", "clear_failcount", "write_json_atomic")),
]


def main():
    missing = {n for _, ns in VERDICT_MEMBERS for n in ns if not hasattr(W, n)}
    if missing:
        print("\nThe watchdog under test carries NONE of the daemon verdicts.")
        for verdict, names in VERDICT_MEMBERS:
            gone = [n for n in names if n in missing]
            if gone:
                check(verdict, False, "watchdog has no " + ", ".join(gone))
        print(f"\nCHECKS {len(PASSED)}/{len(PASSED) + len(FAILED)}")
        print("FAILED: " + "; ".join(FAILED))
        return 1

    orig_run = W.run
    orig_gateway_call = W.gateway_call
    try:
        print("\nARM A — a determinate running unit is read as running (the control).")
        W.run = fake_systemctl(RUNNING_ANSWER)
        a = W.daemon_identity()
        check("state is running", a.get("state") == "running", repr(a.get("state")))
        check("pid is the unit's MainPID as an int", a.get("pid") == 2561514, repr(a.get("pid")))
        check("invocation is carried (the restart key)",
              a.get("invocation") == "68bb9e190b2141c187e290e0a510bd55")
        check("the reading carries the unit it asked about",
              a.get("unit") == W.DAEMON_UNIT, repr(a.get("unit")))
        # ⚠ ASSERTED AGAINST THE ARGV THE CODE ACTUALLY BUILT, not against the answer it got
        # back. The substitution would happily hand a user-bus answer to a query that never
        # asked the user bus, and every other check here would still pass.
        check("the query is USER-scoped — the flag is in the argv, not in a comment",
              bool(SEEN_ARGV) and "--user" in SEEN_ARGV[-1],
              " ".join(SEEN_ARGV[-1]) if SEEN_ARGV else "no call captured")
        check("and it asks about the unit it reports on",
              bool(SEEN_ARGV) and W.DAEMON_UNIT in SEEN_ARGV[-1])

        print("\nARM B — THE ONE THAT MATTERS: the wrong-bus answer is UNKNOWN, never absent.")
        W.run = fake_systemctl(SYSTEM_SCOPE_ANSWER)
        b = W.daemon_identity()
        check("state is unknown", b.get("state") == "unknown", repr(b.get("state")))
        check("state is NOT stopped/absent — the claim it cannot hold",
              b.get("state") not in ("stopped", "absent", "gone"))
        check("the reason names the ambiguity rather than asserting absence",
              "indistinguishable" in (b.get("why") or ""), repr(b.get("why"))[:90])

        print("\nARM C — a unit that answered FOR ITSELF is reportable as stopped.")
        W.run = fake_systemctl(STOPPED_ANSWER)
        cc = W.daemon_identity()
        check("state is stopped (loaded + inactive is determinate)",
              cc.get("state") == "stopped", repr(cc.get("state")))
        check("arm B and arm C reach DIFFERENT verdicts from a near-identical answer",
              cc.get("state") != b.get("state"),
              "both say inactive/dead/MainPID=0; only LoadState differs")

        print("\nARM D — the call failing is UNKNOWN, and never a crash of the pass.")
        W.run = fake_systemctl("", returncode=1, stderr="Failed to connect to bus")
        d = W.daemon_identity()
        check("non-zero exit yields unknown", d.get("state") == "unknown")
        # ⚠ THE VERDICT ALONE IS VACUOUS AND THE GUARD SWEEP PROVED IT. With `if rc != 0`
        # neutralized, empty stdout falls through to the NO-LoadState guard and STILL returns
        # `unknown` — the arm would pass while the guard it names was gone. ⇒ Assert the REASON,
        # which only the intended guard can produce.
        check("...and the REASON names the exit status, so a fallback path cannot satisfy it",
              "exited 1" in (d.get("why") or ""), repr(d.get("why"))[:70])

        def boom(*a, **k):
            raise OSError("no systemctl on this box")
        W.run = boom
        e = W.daemon_identity()
        check("a raising systemctl yields unknown, not an exception",
              e.get("state") == "unknown", repr(e.get("why"))[:70])

        print("\nARM E — the restart comparison: claimed only between DETERMINATE readings.")
        r1 = {"state": "running", "pid": 1, "invocation": "aaa"}
        r2 = {"state": "running", "pid": 2, "invocation": "bbb"}
        unk = {"state": "unknown", "why": "x"}
        check("a changed invocation IS a restart", W._daemon_change(r1, r2) is not None)
        check("an unchanged invocation is NOT", W._daemon_change(r1, dict(r1)) is None)
        check("running -> unknown is NOT claimed as a restart",
              W._daemon_change(r1, unk) is None, "a measurement failing is not an event")
        check("unknown -> running is NOT claimed as a restart",
              W._daemon_change(unk, r2) is None)
        check("running -> stopped IS a change worth recording",
              W._daemon_change(r1, {"state": "stopped", "why": "y"}) is not None)
        chg = W._daemon_change(r1, r2)
        check("the record carries both sides and a timestamp",
              chg.get("from") == r1 and chg.get("to") == r2 and bool(chg.get("at")))

        print("\nARM N — IDENTITY: the running daemon is COMPARED, never merely printed.")
        # The gap this closes, measured: the watchdog's gateway row PRINTS a pid and compares it
        # to nothing, so a swapped-out process reads as continuous health.
        check("an unchanged identity says SAME, and names what it compared",
              "SAME" in W.identity_verdict(r1, dict(r1))
              and "invocation" in W.identity_verdict(r1, dict(r1)),
              W.identity_verdict(r1, dict(r1)))
        check("a changed identity says CHANGED with both sides",
              "CHANGED" in W.identity_verdict(r1, r2) and "1 -> 2" in W.identity_verdict(r1, r2),
              W.identity_verdict(r1, r2))
        # ⚠ A pid that moved under an UNCHANGED InvocationID is an anomaly, not a match. Folding
        # it into SAME would be the printed-not-compared defect wearing a comparison's clothes.
        check("a moved pid under the SAME invocation is NOT reported as SAME",
              "SAME" not in W.identity_verdict(r1, {**r1, "pid": 99}),
              W.identity_verdict(r1, {**r1, "pid": 99}))
        check("no determinate CURRENT reading yields no comparison, never a match",
              "no comparison" in W.identity_verdict(r1, unk), W.identity_verdict(r1, unk))
        check("no determinate PREVIOUS reading yields no comparison either",
              "no comparison" in W.identity_verdict(None, r1), W.identity_verdict(None, r1))
        check("...and an unknown previous is not silently treated as a first pass",
              "no comparison" in W.identity_verdict(unk, r1), W.identity_verdict(unk, r1))

        print("\nARM H — the PUSH note: it earns its interruption or it stays quiet.")
        # Sequences are driven through check_daemon directly with a persistent state dict, which
        # is exactly how the pass drives it.
        RUN = {"state": "running", "unit": "u", "pid": 1, "invocation": "aaa"}
        RUN2 = {"state": "running", "unit": "u", "pid": 2, "invocation": "bbb"}
        DOWN = {"state": "stopped", "unit": "u", "why": "ActiveState=inactive"}
        UNK = {"state": "unknown", "unit": "u", "why": "wrong bus"}

        st, notes = {}, []
        for _ in range(3):
            W.check_daemon(st, DOWN, None, notes)
        check("DOWN across three passes raises exactly ONE note", len(notes) == 1, f"{len(notes)}")
        check("and the note says the daemon is down", "DOWN" in (notes[0] if notes else ""))

        W.check_daemon(st, RUN, None, notes)
        check("recovery with no change record clears the episode silently", len(notes) == 1)
        # ⚠ THE CHECK ABOVE WAS ONCE THE ONLY ONE HERE, AND IT IS A FIXTURE THAT CANNOT HAPPEN:
        # a real recovery ALWAYS carries a change record, since stopped -> running is a
        # determinate transition that `_daemon_change` records. The real path is asserted too.
        st2, notes2 = {}, []
        W.check_daemon(st2, DOWN, None, notes2)
        W.check_daemon(st2, RUN, {"at": "T", "from": DOWN, "to": RUN}, notes2)
        check("a REAL recovery (which always carries a change) ANNOUNCES the return",
              len(notes2) == 2, "the reader that heard it died must hear it is back")
        check("and the down-episode is cleared so a later outage notes again",
              "notified_daemon_down" not in st2)
        for _ in range(2):
            W.check_daemon(st, DOWN, None, notes)
        check("a SECOND outage notes again (the episode re-armed)", len(notes) == 2)

        st, notes = {}, []
        chg = {"at": "T", "from": RUN, "to": RUN2}
        for _ in range(4):
            W.check_daemon(st, RUN2, chg, notes)
        check("a restart notes ONCE even though the change record is handed back every pass",
              len(notes) == 1, f"{len(notes)} — keyed on the invocation, not on the record existing")
        check("the restart note carries both pids", "1 -> 2" in (notes[0] if notes else ""))
        check("and it repeats the bound rather than implying more",
              "never WHICH CODE" in (notes[0] if notes else ""))
        # ⚠ THE DEDUPE KEY MUST BE IN THE HEAD OF THE ALERT. The pass-level dedupe fingerprints
        # on the text before the em-dash; without the invocation there, a SECOND restart inside
        # the re-alert window reads as an unchanged repeat and is suppressed.
        check("the restart note carries its invocation BEFORE the em-dash (the dedupe key)",
              "bbb" in notes[0].split(" —")[0], notes[0].split(" —")[0])
        chg2 = {"at": "T2", "from": RUN2, "to": {**RUN, "invocation": "ccc", "pid": 3}}
        W.check_daemon(st, {**RUN, "invocation": "ccc", "pid": 3}, chg2, notes)
        check("a genuinely NEW restart notes again", len(notes) == 2)
        check("and its dedupe head DIFFERS from the previous restart's",
              notes[0].split(" —")[0] != notes[1].split(" —")[0],
              notes[1].split(" —")[0])

        st, notes = {}, []
        for dd in (UNK, UNK, UNK):
            W.check_daemon(st, dd, None, notes)
        check("UNKNOWN never pushes, in any sequence position", not notes, repr(notes)[:60])
        st, notes = {}, []
        W.check_daemon(st, DOWN, None, notes)
        W.check_daemon(st, UNK, None, notes)
        W.check_daemon(st, DOWN, None, notes)
        check("an UNKNOWN pass does NOT re-arm a live DOWN episode",
              len(notes) == 1, f"{len(notes)} — an unreadable pass must not manufacture a repeat")

        st = {"notified_pressure": True, "windows": {"w": 1}, "notified_daemon_down": True}
        notes = []
        W.check_daemon(st, RUN, None, notes)
        check("foreign state keys are left byte-untouched",
              st.get("notified_pressure") is True and st.get("windows") == {"w": 1})
        check("and only the daemon's own key is cleared on recovery",
              "notified_daemon_down" not in st)

        st, notes = {}, []
        line = W.check_daemon(st, RUN, None, notes)
        check("a healthy first pass on virgin state is SILENT", not notes)
        check("the report row still renders it", "daemon" in line and "ok" in line, line.strip())
        check("a DOWN row renders DOWN, not ok", "DOWN" in W.check_daemon({}, DOWN, None, []))
        check("an UNKNOWN row renders UNKNOWN rather than looking healthy",
              "UNKNOWN" in W.check_daemon({}, UNK, None, []))

        print("\nARM J — the CRASH LOOP, which is the shape the real incident took.")
        # 2026-07-27 16:15: the daemon was down with `NRestarts=32 and climbing every 5 seconds`,
        # and the run learned it from a seat noticing BY HAND. A steady outage is binary and gets
        # one note; a crash loop is MONOTONIC and is the deterioration case.
        def down(n):
            return {"state": "stopped", "unit": "u", "why": "ActiveState=failed", "restarts": n}

        st, notes = {}, []
        W.check_daemon(st, down(30), None, notes)
        check("a first DOWN pass notes once", len(notes) == 1)
        W.check_daemon(st, down(30), None, notes)
        check("a STEADY outage (count unmoved) does NOT re-note", len(notes) == 1)
        W.check_daemon(st, down(32), None, notes)
        check("a CLIMBING restart count DOES re-note — deterioration, not repetition",
              len(notes) == 2, "the deterioration ruling, not the binary argument")
        check("and the note names it as a crash loop with both counts",
              "CRASH-LOOPING" in notes[-1] and "30 -> 32" in notes[-1], notes[-1][-60:])
        check("the climbing count is in the dedupe head, so the re-note is not suppressed",
              notes[0].split(" —")[0] != notes[1].split(" —")[0],
              notes[1].split(" —")[0])
        W.check_daemon(st, down(32), None, notes)
        check("then goes quiet again while the count holds still", len(notes) == 2)

        st, notes = {}, []
        W.check_daemon(st, {**RUN, "restarts": 32}, None, notes)
        check("a unit that crash-looped BEFORE this code landed is seeded QUIETLY",
              not notes, "a fix whose first act is a false alarm teaches its reader to discount it")
        check("and the seed is the systemd count, not zero",
              st.get("daemon_restarts_flagged") == 32)
        W.check_daemon(st, down(32), None, notes)
        check("a later genuine outage still notes", len(notes) == 1)

        st, notes = {}, []
        W.check_daemon(st, down(None), None, notes)
        W.check_daemon(st, down(None), None, notes)
        check("an UNREADABLE restart count never fabricates a climb",
              len(notes) == 1, "None must mean no comparison, never 0")
        # ⚠ THE CHECK ABOVE IS NOT ENOUGH AND A MUTANT PROVED IT: it hands check_daemon a None it
        # constructed itself, so it never exercises the PARSER that has to produce that None. A
        # mutant defaulting an unreadable NRestarts to 0 passed every other check. The property
        # has to be asserted where it is DECIDED — 0 is a real, healthy value here.
        W.run = fake_systemctl(STOPPED_ANSWER)   # carries NO NRestarts line
        parsed = W.daemon_identity()
        check("an ABSENT NRestarts parses to None, never to 0",
              parsed.get("restarts") is None, repr(parsed.get("restarts")))
        W.run = fake_systemctl(RUNNING_ANSWER.replace(
            "MainPID=2561514", "NRestarts=notanumber\nMainPID=2561514"))
        check("an UNPARSEABLE NRestarts also parses to None",
              W.daemon_identity().get("restarts") is None)
        W.run = fake_systemctl(RUNNING_ANSWER.replace(
            "MainPID=2561514", "NRestarts=0\nMainPID=2561514"))
        check("a genuine zero still parses as 0, not None — the two are different facts",
              W.daemon_identity().get("restarts") == 0)
        line = W.check_daemon({}, {**RUN, "restarts": 7}, None, [])
        check("the report row surfaces a non-zero restart count", "restarts: 7" in line,
              line.strip())
        line = W.check_daemon({}, RUN, None, [])
        check("and stays terse at zero", "restarts" not in line, line.strip())

        print("\nARM K — the boot marker OUTLIVES its process, so identity is checked before bytes.")
        # ⚠ The binding bar. The marker is a FILE: if the daemon dies it survives, carrying the
        # last boot's fingerprint, and a reader trusting it standalone would report "code is
        # current" about a daemon that is not running. Three outcomes must stay distinct;
        # collapsing any two IS the defect. Everything here happens in a TEMP workspace — writing
        # a marker into the real .rbtv/runtime/ would plant false data about the live daemon.
        import hashlib as _h

        def _mk(ws, invocation, files, root=None):
            """Write a marker as the daemon's code-fingerprint.js would, without importing it."""
            src = ws / "srv"
            src.mkdir(parents=True, exist_ok=True)
            entries = {}
            for name, text in files.items():
                (src / name).write_text(text)
                entries[name] = _h.sha256(text.encode()).hexdigest()
            dd = ws / ".rbtv" / "runtime"
            dd.mkdir(parents=True, exist_ok=True)
            (dd / "daemon-code.json").write_text(json.dumps({
                "pid": 1234, "invocation": invocation, "root": str(root or src),
                "code": {"files": len(entries), "digest": "x", "entries": entries}}))
            return src

        LIVE = {"state": "running", "unit": "u", "pid": 1, "invocation": "INV-LIVE", "restarts": 0}
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            src = _mk(ws, "INV-LIVE", {"a.js": "one\n", "b.js": "two\n"})
            v, why = W.daemon_code_state(ws, LIVE)
            check("a matching marker with matching bytes is CURRENT", v == "current", f"{v}: {why}")
            (src / "b.js").write_text("CHANGED\n")
            v, why = W.daemon_code_state(ws, LIVE)
            check("a matching marker with changed bytes is STALE", v == "stale", f"{v}: {why}")
            check("and the drifted file is NAMED, not just counted", "b.js" in why, why)

            # THE BAR: same bytes, but the marker is from a boot that is gone.
            _mk(ws, "INV-OLD", {"a.js": "one\n", "b.js": "two\n"})
            v, why = W.daemon_code_state(ws, LIVE)
            check("a marker from a DIFFERENT boot is UNKNOWN — never current",
                  v == "unknown", f"{v}: {why}")
            check("and the reason says it describes a process that is gone",
                  "DIFFERENT boot" in why or "gone" in why, why)

            # The same non-matching marker must not be readable as STALE either.
            (src / "b.js").write_text("CHANGED AGAIN\n")
            v, _ = W.daemon_code_state(ws, LIVE)
            check("nor is a stale-looking foreign marker reported as STALE", v == "unknown", v)

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            v, why = W.daemon_code_state(ws, LIVE)
            check("no marker at all is UNKNOWN, said out loud", v == "unknown", why[:60])
            (ws / ".rbtv" / "runtime").mkdir(parents=True)
            (ws / ".rbtv" / "runtime" / "daemon-code.json").write_text("{not json")
            v, why = W.daemon_code_state(ws, LIVE)
            check("a CORRUPT marker is UNKNOWN, never a crash", v == "unknown", why[:50])
            # A bare list PARSES but is not an object — the one input that reaches the isinstance
            # guard, which the JSON-decode guard otherwise shadows.
            (ws / ".rbtv" / "runtime" / "daemon-code.json").write_text("[]")
            # Wrapped so a REGRESSION here reads as a clean FAIL rather than taking the probe
            # down: INOPERATIVE and FAILED are different claims and must look different.
            try:
                v, why = W.daemon_code_state(ws, LIVE)
            except Exception as exc:  # noqa: BLE001
                v, why = "raised", f"{exc.__class__.__name__}: {exc}"
            check("a marker that parses but is NOT an object is UNKNOWN, not a crash",
                  v == "unknown" and "not an object" in why, f"{v}: {why[:44]}")
            (ws / ".rbtv" / "runtime" / "daemon-code.json").write_text(json.dumps(
                {"invocation": "INV-LIVE", "root": str(ws), "code": {"entries": {}}}))
            v, why = W.daemon_code_state(ws, LIVE)
            check("an EMPTY entries map is UNKNOWN — the state that lies is refused",
                  v == "unknown", why[:50])
            (ws / ".rbtv" / "runtime" / "daemon-code.json").write_text(json.dumps(
                {"invocation": "INV-LIVE", "code": {"entries": {"a.js": "deadbeef"}}}))
            v, why = W.daemon_code_state(ws, LIVE)
            check("a marker with NO root is UNKNOWN rather than guessing this install's layout",
                  v == "unknown", why[:60])

        # ⚠ THE OBVIOUS FORM OF THIS CHECK IS VACUOUS AND A MUTANT PROVED IT. Passing a workspace
        # with NO marker returns UNKNOWN through the missing-marker path, so deleting the
        # not-running guard entirely left the probe GREEN. The guard has to be ISOLATED: a
        # workspace whose marker WOULD otherwise verify clean, with the live state as the only
        # thing that differs.
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            _mk(ws, "INV-LIVE", {"a.js": "one\n"})
            v, _ = W.daemon_code_state(ws, LIVE)
            check("control: with this marker a RUNNING daemon does verify clean", v == "current", v)
            for state in ({"state": "stopped", "why": "x", "invocation": "INV-LIVE"},
                          {"state": "unknown", "why": "y", "invocation": "INV-LIVE"}):
                v, why = W.daemon_code_state(ws, state)
                check(f"a {state['state']} daemon yields UNKNOWN even though the marker WOULD verify",
                      v == "unknown", f"{v}: {why[:52]}")

        print("\nARM L — the stale-code note: once per deploy, and UNKNOWN never pushes.")
        st, notes = {}, []
        for _ in range(3):
            W.check_daemon(st, LIVE, None, notes, ("stale", "b.js"))
        check("STALE CODE notes exactly once across three passes", len(notes) == 1, str(len(notes)))
        check("and the note names the file and the remedy",
              "b.js" in notes[0] and "7.68" in notes[0])
        W.check_daemon(st, LIVE, None, notes, ("stale", "b.js, c.js"))
        check("a DIFFERENT drift set notes again — a second deploy is a second event",
              len(notes) == 2)
        W.check_daemon(st, LIVE, None, notes, ("current", "ok"))
        check("returning to current raises no note of its own", len(notes) == 2)
        # ⚠⚠ THIS PAIR WAS VACUOUS AND A GUARD-NEUTRALIZATION SWEEP CAUGHT IT: the re-note check
        # used a DIFFERENT drift set either side of the return-to-current, so the later note was
        # explained by the SET CHANGING and not by the state being cleared. ⇒ The drift set is now
        # IDENTICAL across the transition, so ONLY the clearing can explain a second note.
        W.check_daemon(st, LIVE, None, notes, ("stale", "b.js, c.js"))
        check("the SAME drift set notes again ONLY because current cleared the state",
              len(notes) == 3, "identical set either side — the clear is the only explanation")
        st, notes = {}, []
        for _ in range(3):
            W.check_daemon(st, LIVE, None, notes, ("unknown", "no marker"))
        check("an UNKNOWN code verdict NEVER pushes", not notes, repr(notes)[:50])
        line = W.check_daemon({}, LIVE, None, [], ("current", "12 files match"))
        check("the row says 'running current code' even when healthy",
              "running current code" in line, line.strip())
        line = W.check_daemon({}, LIVE, None, [], ("unknown", "no marker"))
        check("and an UNKNOWN row says so rather than looking healthy", "UNKNOWN" in line)

        print("\nARM G — end to end through daemon_verdicts: ONE reading, persisted for the next.")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            statef = base / "daemon.json"
            os.environ["RBTV_WATCHDOG_DAEMON_STATE"] = str(statef)
            orig_ws = W.WORKSPACE
            W.WORKSPACE = str(base)          # no marker here: the code verdict is UNKNOWN
            try:
                SEEN_ARGV.clear()
                W.run = fake_systemctl(RUNNING_ANSWER)
                rows, notes = W.daemon_verdicts()
                check("a pass issues exactly ONE systemctl call",
                      len(SEEN_ARGV) == 1,
                      f"{len(SEEN_ARGV)} — two calls per pass can straddle a restart and disagree")
                check("the first pass ever announces nothing", not notes, repr(notes)[:60])
                check("the row set carries the verdict row and the identity row",
                      len(rows) == 2 and "daemon-id" in rows[0] and "ident" in rows[1],
                      " || ".join(r.strip() for r in rows)[:110])
                check("the identity row says there is no comparison yet, not that it matched",
                      "no comparison" in rows[1], rows[1].strip())
                on_disk = json.loads(statef.read_text())
                check("and the reading is PERSISTED for the next pass",
                      on_disk.get("daemon", {}).get("pid") == 2561514,
                      json.dumps(on_disk.get("daemon"))[:70])

                W.run = fake_systemctl(
                    RUNNING_ANSWER.replace("MainPID=2561514", "MainPID=9999")
                                  .replace("68bb9e190b2141c187e290e0a510bd55", "ffff" * 8))
                rows, notes = W.daemon_verdicts()
                check("a NEW invocation on the next pass is announced exactly once",
                      len(notes) == 1 and "RESTARTED" in notes[0], repr(notes)[:70])
                check("and the identity row reports it CHANGED", "CHANGED" in rows[1],
                      rows[1].strip())
                rows, notes = W.daemon_verdicts()
                check("the same identity a pass later announces nothing further",
                      not notes, repr(notes)[:60])
                check("and the identity row now reports SAME", "SAME" in rows[1], rows[1].strip())

                W.run = fake_systemctl(SYSTEM_SCOPE_ANSWER)
                rows, notes = W.daemon_verdicts()
                check("an UNREADABLE pass announces nothing", not notes, repr(notes)[:60])
                check("and it does not overwrite the record with a fabricated identity",
                      json.loads(statef.read_text())["daemon"]["state"] == "unknown")
                check("the row stays LOUD rather than looking healthy", "UNKNOWN" in rows[0],
                      rows[0].strip())

                # A --dry-run must not CONSUME the event: it reads, it persists nothing.
                W.run = fake_systemctl(RUNNING_ANSWER)
                before = statef.read_text()
                W.daemon_verdicts(persist=False)
                check("a non-persisting pass leaves the record byte-untouched",
                      statef.read_text() == before)
            finally:
                W.WORKSPACE = orig_ws
                os.environ.pop("RBTV_WATCHDOG_DAEMON_STATE", None)

        print("\nARM M — the daemon RESTART GATE (owner ruling 2026-08-14, daemon-issues §2).")
        # Driven through main(), not through daemon_restart_gate alone: the gate returning the
        # right verdict and main() OBEYING it are two different claims, and on 2026-08-14 the
        # tool held the disproving datum already — one step downstream of the act. So the
        # observation is the ARGV of the operator call, captured at the same `run` seam.
        # The gateway is pointed at a port nothing listens on, so every pass grades `down`.
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            env_saved = {k: os.environ.get(k) for k in (
                "RBTV_WATCHDOG_FAILCOUNT", "RBTV_WATCHDOG_DAEMON_STATE", "RBTV_WATCHDOG_STATE",
                "RBTV_WATCHDOG_NOTIFY_FILE", "RBTV_WATCHDOG_TARGETS", "IGNITE_WATCHDOG_TOKEN")}
            os.environ.update({
                "RBTV_WATCHDOG_FAILCOUNT": str(base / "failcount.json"),
                "RBTV_WATCHDOG_DAEMON_STATE": str(base / "daemon.json"),
                "RBTV_WATCHDOG_STATE": str(base / "state.json"),
                "RBTV_WATCHDOG_NOTIFY_FILE": str(base / "notify.jsonl"),
                "RBTV_WATCHDOG_TARGETS": "daemon",
                "IGNITE_WATCHDOG_TOKEN": "probe-token-never-accepted-by-anything"})
            orig_ws, orig_gw = W.WORKSPACE, W.GATEWAY
            W.WORKSPACE, W.GATEWAY = str(base), "http://127.0.0.1:1/"

            def pass_():
                """One whole watchdog pass. Returns (stdout, [operator argv]).
                `restart_via_operator` goes through the same faked `run`, so a fired restart is
                an argv in hand rather than a real systemctl call."""
                SEEN_ARGV.clear()
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    W.main([])
                return buf.getvalue(), [a for a in SEEN_ARGV if "restart" in a]

            try:
                # (a) ALIVE per systemd + a dead gateway. THE 57-RESTART CASE.
                W.run = fake_systemctl(RUNNING_ANSWER)
                for i in (1, 2, 3, 4):
                    out, fired = pass_()
                    check(f"pass {i}: an ALIVE daemon with an unanswerable gateway is NOT restarted",
                          not fired, "operator called with %s" % (fired[0] if fired else ""))
                check("and the withheld pass ALARMS instead of going quiet",
                      "THE GATEWAY IS UNANSWERABLE BUT THE DAEMON IS ALIVE" in out, out[:90])
                check("four failed passes did not spend the gate — strikes never authorize a "
                      "restart while systemd says the process is there",
                      json.loads((base / "failcount.json").read_text()).get("strikes") == 4)

                # (b) GENUINELY DEAD + strikes spent. The lever MUST still fire.
                (base / "failcount.json").unlink()
                W.run = fake_systemctl(STOPPED_ANSWER)
                out1, fired1 = pass_()
                out2, fired2 = pass_()
                check("a DEAD daemon is not restarted on the first failed pass (strike 1)",
                      not fired1, "operator called")
                check("nor on the second (strike 2)", not fired2, "operator called")
                check("and the held passes say which strike they are on",
                      "strike 1 of 3" in out1 and "strike 2 of 3" in out2)
                out3, fired3 = pass_()
                check("⚠ THE LEVER SURVIVES: on the third consecutive failed pass a DEAD daemon "
                      "IS restarted", bool(fired3), "no operator call — the gate swallowed the "
                                                    "one case monitoring exists for")
                check("and the restart is routed through the daemon-operator (PRIN-11)",
                      bool(fired3) and "rbtv-ignite-daemon" in fired3[0][0], repr(fired3[:1])[:80])

                # (c) backoff: the same remedy is not re-applied once it demonstrably did not
                # change the verdict. ⚠ MEASURED AT THE DECISION, not one pass after the restart:
                # the restart resets the strike counter, so the immediately-following passes are
                # withheld by the STRIKES gate and would report backoff working while it was
                # deleted (mutation-checked — `if False:` on the backoff branch left an
                # any-pass-after-restart check green). So the strikes are SPENT AGAIN first, and
                # only the pass that clears them can be explained by the backoff.
                for _ in range(W.STRIKES - 1):
                    out_c, fired_c = pass_()
                    check("still no second restart while the strikes re-accumulate", not fired_c)
                out_c, fired_c = pass_()
                check("⚠ with the strikes SPENT AGAIN, a still-down verdict inside the backoff "
                      "window is NOT re-restarted — the strikes gate cannot explain this one",
                      not fired_c, "operator called again")
                check("and it says the restart did not restore it",
                      "RESTART DID NOT RESTORE THE GATEWAY" in out_c, out_c[-120:])

                # (d) one `up` pass ends the streak.
                W.gateway_call = lambda t: ("ok", {"result": {"pid": 1}})
                pass_()
                check("an `up` verdict resets the consecutive-failure counter",
                      json.loads((base / "failcount.json").read_text()).get("strikes") == 0)
            finally:
                W.WORKSPACE, W.GATEWAY = orig_ws, orig_gw
                W.gateway_call = orig_gateway_call
                for k, v in env_saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
    finally:
        W.run = orig_run

    print(f"\nCHECKS {len(PASSED)}/{len(PASSED) + len(FAILED)}")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 112:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 112")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

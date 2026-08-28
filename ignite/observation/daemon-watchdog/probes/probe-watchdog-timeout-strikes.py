#!/usr/bin/env python3
"""probe-watchdog-timeout-strikes — a gateway TIMEOUT reaches the owner only after N consecutive
timing-out passes, and every OTHER gateway failure still reports on the first pass.

THE DEFECT THIS PINS (acceptance test 15, finding A-1; owner ruling 2026-08-28, option c). Between
2026-08-27 15:40Z and 2026-08-28 05:25Z the unit-alive arm of `daemon_restart_gate` sent the owner
29 "THE GATEWAY IS UNANSWERABLE ... a human is needed" messages. All 29 were false: systemd
reported the daemon active on every one of them, no restart was ever taken, and
`seats/diag-gateway-stall/report.md` §1.1 measured the whole window — `inspect daemon` latency is
ONE continuous heavy-tailed distribution (112 of 862 SUCCESSFUL passes over 5 s, slowest success
10.21 s) whose tail straddles the 10 s socket timeout. A single sample above the cutoff therefore
distinguishes nothing, and the arm concluded "a human is needed" from it once a minute.

WHAT IS SIMULATED. The `daemon` row of the probe table, whose gateway result this probe chooses,
driven through the tool's real `main()` in-process. `daemon_identity` is stubbed to a unit systemd
reports RUNNING — the exact condition of all 29 pages — and `daemon_verdicts` is stubbed away
because it shells out to systemd for facts no arm here reads. A scratch workspace per run, the
notify sink armed so no DM and no Slack post can leave the box, and the alarm shim reached over
`node` exactly as a live pass reaches it. No real unit is named, started, stopped or restarted, and
no real gateway is called. A restart attempt of any kind raises.

THE TWO DELIVERY SURFACES ARE COUNTED SEPARATELY, because the fix moves the condition from one to
the other: the owner-DM leg writes JSON lines to `RBTV_WATCHDOG_NOTIFY_FILE`, while the emitter
writes an `alarm` record into `.rbtv/runtime/ignite/outbox.json` and a row into
`.rbtv/runtime/ignite/alarm-registry.json`. "One message reached the owner" is asserted as one
outbox record, never as the absence of both.

RED-FIRST, IN THE SAME RUN. Arm F loads a MUTATED COPY of the tool with both strike branches
disabled — the pre-fix arm, restored exactly — and asserts the failure: one timeout, one owner DM,
no registry row.

Exit 0 = every assertion held. Exit 1 = at least one failed.
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "tool", "rbtv-ignite-watchdog")
SHIM = os.path.join(os.path.dirname(HERE), "tool", "watchdog-alarm.js")
OUT = os.path.join(HERE, "probe-watchdog-timeout-strikes.out")

ROW = "daemon"
UNIT = "rbtv-watchdog-timeout-strikes-probe.service"   # named, never touched
PID = 424242
# What `gateway_call` hands the gate for each failure kind, verbatim in its own format
# (`type(ex).__name__ + ": " + str(ex)`), plus its one non-exception form.
TIMEOUT = "TimeoutError: timed out"
REFUSED = "URLError: <urlopen error [Errno 111] Connection refused>"


def load_watchdog(path=TOOL, name="rbtv_ignite_watchdog_under_probe"):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stub(wd):
    """The probe table cut to one row, and the two systemd readers replaced.

    `daemon_identity` answers RUNNING on every pass: that is the condition of all 29 false pages
    and it is what keeps the run inside the unit-alive arm, so nothing here can reach the restart
    lever even if the gate were wrong about it. `daemon_verdicts` is stubbed because it runs
    `systemctl show` for the RESTARTED / CRASH-LOOP / IDENTITY verdicts, none of which this probe
    grades."""
    wd.ROWS = {ROW: (lambda: (wd._probe_state, wd._probe_detail),
                     lambda: (_ for _ in ()).throw(AssertionError("no restart may be attempted")),
                     lambda: "restarted %s" % UNIT)}
    wd.ROW_UNITS = {ROW: UNIT}
    wd.daemon_identity = lambda: {"state": "running", "pid": PID,
                                  "since": "Fri 2026-08-28 03:55:58 UTC",
                                  "invocation": "probe"}
    wd.daemon_verdicts = lambda persist=True: ([], [])
    return wd


def drive(wd, state, detail, argv=()):
    """One full pass whose daemon row returns exactly what this call names."""
    wd._probe_state, wd._probe_detail = state, detail
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = wd.main(list(argv))
    return rc, buf.getvalue()


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    log, fails = [], []

    def say(s):
        log.append(s)

    def check(name, ok, detail=""):
        say("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratches = []

    def workspace(strikes=None):
        """A fresh scratch workspace, its env installed, and a freshly imported tool bound to it.

        Re-imported per arm and not reset in place: TIMEOUT_STRIKES, DAEMON_UNIT and every other
        knob is a module-level constant read from the environment AT IMPORT, so an arm that wants a
        different N has to load the module again.

        ⚠ RBTV_WATCHDOG_WORKSPACE IS PART OF THE CONFINEMENT, not housekeeping. Every
        `<WORKSPACE>/.rbtv/runtime/…` path the tool writes lands wherever this points, and on
        2026-08-28T03:02:15Z a sibling probe run from the rbtv repo root with this unset planted
        `<repo>/.rbtv/`, which then hijacked another component's workspace walk for four hours
        (wave test 15). The scratch carries no install record, so an unset value is a REFUSAL and a
        red probe rather than a silent planting."""
        s = tempfile.mkdtemp(prefix="rbtv-watchdog-timeout-strikes-")
        scratches.append(s)
        os.environ.update({
            "RBTV_WATCHDOG_WORKSPACE": s,
            "RBTV_WATCHDOG_TARGETS": ROW,
            "RBTV_WATCHDOG_DAEMON_UNIT": UNIT,
            "RBTV_WATCHDOG_LEDGER": os.path.join(s, "outage-ledger.jsonl"),
            # The sink is this tool's "send nothing, write what you would have sent" wall, and the
            # shim checks it BEFORE any token — so an ambient SLACK_BOT_TOKEN in the operator's
            # shell cannot turn this probe into a post in the owner's real workspace.
            "RBTV_WATCHDOG_NOTIFY_FILE": os.path.join(s, "notify.jsonl"),
            "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-SYSTEM",
            "RBTV_WATCHDOG_ALARM_SHIM": SHIM,
        })
        for k in ("RBTV_WATCHDOG_ROW_ALARMS", "RBTV_WATCHDOG_STATE",
                  "RBTV_WATCHDOG_FAILCOUNT", "RBTV_WATCHDOG_DAEMON_STATE"):
            os.environ.pop(k, None)
        if strikes is None:
            os.environ.pop("RBTV_WATCHDOG_TIMEOUT_STRIKES", None)
        else:
            os.environ["RBTV_WATCHDOG_TIMEOUT_STRIKES"] = str(strikes)
        paths = {
            "registry": os.path.join(s, ".rbtv", "runtime", "ignite", "alarm-registry.json"),
            "outbox": os.path.join(s, ".rbtv", "runtime", "ignite", "outbox.json"),
            "row_alarms": os.path.join(s, ".rbtv", "runtime", "watchdog", "row-alarms.json"),
            "failcount": os.path.join(s, ".rbtv", "runtime", "watchdog", "failcount.json"),
            "state": os.path.join(s, ".rbtv", "runtime", "watchdog", "state.json"),
            "ledger": os.path.join(s, "outage-ledger.jsonl"),
            "notify": os.path.join(s, "notify.jsonl"),
        }
        return stub(load_watchdog()), paths

    def dms(p):
        return read_jsonl(p["notify"])

    def alarm_posts(p):
        return [r for r in (read_json(p["outbox"], {}) or {}).get("records", [])
                if r.get("kind") == "alarm"]

    def open_rows(p):
        return [r for r in (read_json(p["registry"], {}) or {}).get("rows", [])
                if r.get("state") == "open"]

    def strikes(p):
        return (read_json(p["failcount"], {}) or {}).get("timeout_strikes")

    try:
        say("# probe-watchdog-timeout-strikes — the 29 false pages of 2026-08-27/28")
        say("# unit named but never touched: %s" % UNIT)
        say("")

        # --- A. TIMEOUT x2 THEN A SUCCESS: nothing reaches the owner, the counter resets -----
        wd, p = workspace()
        check("A0 the shipped default is 3 consecutive timing-out passes",
              wd.TIMEOUT_STRIKES == 3, "TIMEOUT_STRIKES=%s" % wd.TIMEOUT_STRIKES)
        rc, out = drive(wd, "down", TIMEOUT)
        check("A1 pass 1 exits 0", rc == 0, "rc=%s" % rc)
        check("A2 pass 1 names the strike and says it did not page",
              "gateway timeout — strike 1/3, no page" in out,
              next((l.strip() for l in out.splitlines() if "strike" in l), "<absent>")[:130])
        check("A3 pass 1 counted one timeout strike", strikes(p) == 1, str(strikes(p)))
        rc, out = drive(wd, "down", TIMEOUT)
        check("A4 pass 2 counted the second strike", strikes(p) == 2, str(strikes(p)))
        check("A5 pass 2 still says no page", "strike 2/3, no page" in out)
        check("A6 no owner DM after two timing-out passes", dms(p) == [],
              "%d notification(s)" % len(dms(p)))
        check("A7 no alarm was posted after two timing-out passes", alarm_posts(p) == [],
              "%d alarm post(s)" % len(alarm_posts(p)))
        check("A8 no registry row was opened", not os.path.exists(p["registry"]), p["registry"])
        check("A9 the DM-dedupe state holds no fingerprint",
              (read_json(p["state"], {}) or {}).get("alert") is None,
              str((read_json(p["state"], {}) or {}).get("alert")))
        check("A10 the withheld pass does NOT report all green",
              "all green" not in out and "nothing delivered on this pass" in out,
              out.strip().splitlines()[-1][:130])
        check("A11 every withheld pass is on the outage ledger",
              len([r for r in read_jsonl(p["ledger"])
                   if r.get("decision") == "page-withheld" and r.get("arm") == "timeout-strikes"]) == 2,
              str([r.get("decision") for r in read_jsonl(p["ledger"])]))
        rc, out = drive(wd, "up", "pid=%s uptime_ms=1 last_tick=1" % PID)
        check("A12 the answered pass resets the counter to 0", strikes(p) == 0, str(strikes(p)))
        check("A13 the answered pass reports all green and sends nothing",
              "all green" in out and dms(p) == [] and alarm_posts(p) == [])

        # --- B. TIMEOUT x3: exactly one delivery and exactly one registry row ----------------
        wd, p = workspace()
        drive(wd, "down", TIMEOUT)
        drive(wd, "down", TIMEOUT)
        rc, out = drive(wd, "down", TIMEOUT)
        check("B1 pass 3 exits 0", rc == 0, "rc=%s" % rc)
        check("B2 pass 3 says it is paging", "strike 3/3, PAGING" in out,
              next((l.strip() for l in out.splitlines() if "PAGING" in l), "<absent>")[:130])
        rows = open_rows(p)
        check("B3 exactly ONE open registry row", len(rows) == 1, "rows=%d" % len(rows))
        row = rows[0] if rows else {}
        check("B4 the row is the daemon row's own condition class",
              row.get("signature_class") == "watchdog-daemon-alarm", str(row.get("signature_class")))
        check("B5 subject is the daemon row and its unit",
              row.get("subject") == {"type": ROW, "id": UNIT}, str(row.get("subject")))
        check("B6 the condition states the consecutive count and the live pid",
              "on 3 consecutive passes" in (row.get("condition") or "")
              and str(PID) in (row.get("condition") or ""), (row.get("condition") or "")[:120])
        check("B7 exactly ONE message reached the owner, through the emitter",
              len(alarm_posts(p)) == 1, "%d alarm post(s)" % len(alarm_posts(p)))
        check("B8 that message is durable (pending-delivery under the sink)",
              alarm_posts(p) and alarm_posts(p)[0].get("state") == "pending-delivery",
              str(alarm_posts(p)[0].get("state")) if alarm_posts(p) else "-")
        # ONE DELIVERY. The condition must not ALSO travel the owner-DM leg [§9.2].
        check("B9 the owner-DM leg was not used as well", dms(p) == [],
              "%d notification(s)" % len(dms(p)))
        check("B10 the pass reports the standing alarm, not all green",
              "all green" not in out and "standing alarm" in out,
              out.strip().splitlines()[-1][:130])
        # --- B'. a 4th timing-out pass mints no second row and no second message -------------
        rc, out = drive(wd, "down", TIMEOUT)
        check("B11 pass 4 still has exactly one open row", len(open_rows(p)) == 1,
              "rows=%d" % len(open_rows(p)))
        check("B12 pass 4 sent nothing more", len(alarm_posts(p)) == 1 and dms(p) == [],
              "%d alarm post(s), %d DM(s)" % (len(alarm_posts(p)), len(dms(p))))
        check("B13 pass 4 says the row is already open", "already open" in out)

        # --- C. TIMEOUT x3, a success, then a TIMEOUT: the counter really reset --------------
        wd, p = workspace()
        for _ in range(3):
            drive(wd, "down", TIMEOUT)
        check("C1 setup: one row open and one message sent",
              len(open_rows(p)) == 1 and len(alarm_posts(p)) == 1)
        rc, out = drive(wd, "up", "pid=%s uptime_ms=1 last_tick=1" % PID)
        check("C2 the answered pass CLOSED the standing condition", len(open_rows(p)) == 0,
              "%d still open" % len(open_rows(p)))
        check("C3 the answered pass reset the counter", strikes(p) == 0, str(strikes(p)))
        posts_before, dms_before = len(alarm_posts(p)), len(dms(p))
        rc, out = drive(wd, "down", TIMEOUT)
        check("C4 the next timeout is strike 1 again, not 4",
              strikes(p) == 1 and "strike 1/3, no page" in out,
              "timeout_strikes=%s" % strikes(p))
        check("C5 it delivered nothing",
              len(alarm_posts(p)) == posts_before and len(dms(p)) == dms_before,
              "%d alarm post(s), %d DM(s)" % (len(alarm_posts(p)), len(dms(p))))
        check("C6 no registry row was re-opened", len(open_rows(p)) == 0)

        # --- D. A NON-TIMEOUT FAILURE IS NOT A STRIKE: the owner hears on pass 1 -------------
        wd, p = workspace()
        rc, out = drive(wd, "down", REFUSED)
        check("D1 pass 1 exits 0", rc == 0, "rc=%s" % rc)
        check("D2 connection refused paged on the FIRST pass", len(dms(p)) == 1,
              "%d notification(s)" % len(dms(p)))
        check("D3 the DM is the unchanged unit-alive text",
              dms(p) and "THE GATEWAY IS UNANSWERABLE BUT THE DAEMON IS ALIVE" in dms(p)[0]["text"]
              and "Connection refused" in dms(p)[0]["text"],
              dms(p)[0]["text"][:110] if dms(p) else "-")
        check("D4 it did NOT count as a timeout strike", strikes(p) == 0, str(strikes(p)))
        check("D5 it did not open a registry row (the DM leg owns this one)",
              not os.path.exists(p["registry"]))
        check("D6 no strike line was printed for it", "no page" not in out)
        # A non-timeout failure BREAKS a timeout run: the rule is CONSECUTIVE timing-out passes.
        wd, p = workspace()
        drive(wd, "down", TIMEOUT)
        drive(wd, "down", TIMEOUT)
        check("D7 setup: two timeout strikes stand", strikes(p) == 2, str(strikes(p)))
        rc, out = drive(wd, "down", REFUSED)
        check("D8 a non-timeout failure resets the timeout counter", strikes(p) == 0, str(strikes(p)))
        rc, out = drive(wd, "down", TIMEOUT)
        check("D9 the run restarts at strike 1", strikes(p) == 1 and "strike 1/3" in out,
              "timeout_strikes=%s" % strikes(p))

        # --- E. THE THRESHOLD IS THE DOCUMENTED ENV VAR, not a baked-in 3 --------------------
        wd, p = workspace(strikes=2)
        check("E0 the env var moved N", wd.TIMEOUT_STRIKES == 2, str(wd.TIMEOUT_STRIKES))
        rc, out = drive(wd, "down", TIMEOUT)
        check("E1 pass 1 counts against the new N", "strike 1/2, no page" in out)
        rc, out = drive(wd, "down", TIMEOUT)
        check("E2 pass 2 pages at the new N",
              "strike 2/2, PAGING" in out and len(open_rows(p)) == 1 and len(alarm_posts(p)) == 1,
              "%d row(s), %d post(s)" % (len(open_rows(p)), len(alarm_posts(p))))

        # --- F. RED CONTROL: the pre-fix arm, in the same run --------------------------------
        # The mutation disables both branches the fix added, which leaves the arm exactly as it
        # stood through the 29 false pages: one timeout, one owner DM, no registry row.
        red_src = os.path.join(tempfile.mkdtemp(prefix="rbtv-watchdog-timeout-strikes-red-src-"),
                               "rbtv-ignite-watchdog")
        src = open(TOOL).read()
        targets = ["        if timed_out and timeout_strikes < TIMEOUT_STRIKES:\n",
                   "        if timed_out:\n"]
        missing = [t for t in targets if src.count(t) != 1]
        if missing:
            check("F0 both mutation targets are present exactly once in the tool", False,
                  "re-point the mutation: %r" % missing)
        else:
            red = src
            for t in targets:
                red = red.replace(t, t.replace("if ", "if False and ", 1))
            open(red_src, "w").write(red)
            _, p = workspace()
            redwd = stub(load_watchdog(red_src, "rbtv_ignite_watchdog_pre_fix"))
            rc, out = drive(redwd, "down", TIMEOUT)
            check("F1 pre-fix: ONE timeout paged the owner immediately", len(dms(p)) == 1,
                  "%d notification(s)" % len(dms(p)))
            check("F2 pre-fix: the page is the false 'a human is needed' verdict",
                  dms(p) and "a human is needed" in dms(p)[0]["text"],
                  dms(p)[0]["text"][:100] if dms(p) else "-")
            check("F3 pre-fix: no registry row, so no standing-condition surface carried it",
                  not os.path.exists(p["registry"]), p["registry"])
            # The counter is still WRITTEN by the mutated copy (only the two branches that read
            # it are disabled), so the assertion is on what the owner sees: no strike line, no
            # threshold, just the verdict — which is what the 29 pages looked like.
            check("F4 pre-fix: no strike line and no threshold in the pass output",
                  "no page" not in out and "PAGING" not in out,
                  next((l.strip() for l in out.splitlines() if "held" in l), "<absent>")[:110])
            shutil.rmtree(os.path.dirname(red_src), ignore_errors=True)
    finally:
        for s in scratches:
            shutil.rmtree(s, ignore_errors=True)

    say("")
    say("%d checks, %d failed" % (len([l for l in log if l[:4] in ("PASS", "FAIL")]), len(fails)))
    text = "\n".join(log)
    print(text)
    with open(OUT, "w") as f:
        f.write(text + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

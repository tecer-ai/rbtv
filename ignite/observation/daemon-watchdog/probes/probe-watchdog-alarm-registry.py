#!/usr/bin/env python3
"""probe-watchdog-alarm-registry — an `alarm` verdict reaches the ONE alarm registry, and a row
that recovers CLOSES it again.

THE DEFECT THIS PINS (wave test 2, 2026-08-26). A `probe-suite` row reading `alarm` — "the suite
is LIVE but the correctness verdict is RED" — had stood for hours, printed every 60 seconds by
this tool. Asked in a live owner DM whether anything was standing, the channel master answered
"No standing warnings", faithfully, because the ONE standing-condition surface every reader
consults (`<workspace>/.rbtv/runtime/ignite/alarm-registry.json`, read by the §5 system digest's
"Open conditions" and by `ignite status`) DID NOT EXIST on that box. The `alarm` branch of
`main()` appended to the owner-DM list and returned; it never called `emit_alarm`. The DM was not
the alarm surface — it was the only one that had been wired.

WHAT IS SIMULATED. One row in the probe table, whose verdict this probe chooses, driven through
the tool's real `main()` in-process. A scratch workspace per run, the notify sink armed so no DM
and no Slack post can leave the box, and the alarm shim reached over `node` exactly as a live pass
reaches it. No real unit is named, started, stopped or restarted, and no real gateway is called.

RED-FIRST, IN THE SAME RUN. Arm F loads a MUTATED COPY of the tool with the pre-fix branch
restored (`alerts.append(...)` in place of the emit) and asserts the failure: no registry row, the
condition delivered to the DM sink alone. Same input, old path blind, new path registered.

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
OUT = os.path.join(HERE, "probe-watchdog-alarm-registry.out")

ROW = "probe-suite"
UNIT = "rbtv-watchdog-alarm-registry-probe.timer"   # named, never touched
RED = "suite is LIVE but the correctness verdict is RED: 16 genuine probe failure(s)"


def load_watchdog(path=TOOL, name="rbtv_ignite_watchdog_under_probe"):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def open_rows(registry):
    doc = read_json(registry, {}) or {}
    return [r for r in doc.get("rows", []) if r.get("state") == "open"]


def drive(wd, verdict, detail, argv=()):
    """One full pass with the probe table stubbed to a single row of our choosing."""
    wd.ROWS = {ROW: (lambda: (verdict, detail),
                     lambda: (_ for _ in ()).throw(AssertionError("no restart may be attempted")),
                     lambda: "restarted %s" % UNIT)}
    wd.ROW_UNITS = {ROW: UNIT}
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = wd.main(list(argv))
    return rc, buf.getvalue()


def main():
    log, fails = [], []

    def say(s):
        log.append(s)

    def check(name, ok, detail=""):
        say("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-alarm-registry-")
    registry = os.path.join(scratch, ".rbtv", "runtime", "ignite", "alarm-registry.json")
    outbox = os.path.join(scratch, ".rbtv", "runtime", "ignite", "outbox.json")
    row_alarms = os.path.join(scratch, ".rbtv", "runtime", "watchdog", "row-alarms.json")
    state_file = os.path.join(scratch, ".rbtv", "runtime", "watchdog", "state.json")
    ledger_file = os.path.join(scratch, "outage-ledger.jsonl")
    notify_file = os.path.join(scratch, "notify.jsonl")

    os.environ.update({
        "RBTV_WATCHDOG_WORKSPACE": scratch,
        "RBTV_WATCHDOG_TARGETS": ROW,
        "RBTV_WATCHDOG_LEDGER": ledger_file,
        # The sink is this tool's "send nothing, write what you would have sent" wall, and the shim
        # checks it BEFORE any token — so an ambient SLACK_BOT_TOKEN in the operator's shell cannot
        # turn this probe into a post in the owner's real workspace.
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-SYSTEM",
        "RBTV_WATCHDOG_ALARM_SHIM": SHIM,
    })
    os.environ.pop("RBTV_WATCHDOG_ROW_ALARMS", None)
    os.environ.pop("RBTV_WATCHDOG_STATE", None)

    try:
        wd = load_watchdog()

        # --- A. --dry-run RAISES NOTHING -----------------------------------------------------
        rc, out = drive(wd, "alarm", RED, argv=["--dry-run"])
        check("A1 dry pass exits 0", rc == 0, "rc=%s" % rc)
        check("A2 dry pass writes NO alarm registry", not os.path.exists(registry), registry)
        check("A3 dry pass writes NO row-alarms record", not os.path.exists(row_alarms))
        check("A4 dry pass says it would raise, and did not",
              "would raise" in out and "--dry-run" in out,
              next((l.strip() for l in out.splitlines() if "would raise" in l), "<absent>")[:120])

        # --- B. an `alarm` verdict opens EXACTLY ONE registry row ----------------------------
        rc, out = drive(wd, "alarm", RED)
        rows = open_rows(registry)
        check("B1 pass exits 0", rc == 0, "rc=%s" % rc)
        check("B2 exactly one OPEN registry row", len(rows) == 1, "rows=%d" % len(rows))
        row = rows[0] if rows else {}
        check("B3 signature class is the row's own",
              row.get("signature_class") == "watchdog-%s-alarm" % ROW, str(row.get("signature_class")))
        check("B4 subject is the row and its unit",
              row.get("subject") == {"type": ROW, "id": UNIT}, str(row.get("subject")))
        check("B5 condition carries the observation verbatim", RED in (row.get("condition") or ""),
              (row.get("condition") or "")[:90])
        check("B6 evidence points at the artifact a human opens",
              row.get("evidence_pointer") == os.path.join(scratch, ".rbtv", "runtime", "probe-suite", "latest.json"),
              str(row.get("evidence_pointer")))
        check("B7 what_would_clear_it names the green reading",
              "reads the %s row `up`" % ROW in (row.get("what_would_clear_it") or ""),
              str(row.get("what_would_clear_it")))
        check("B8 immediate=true (system health is digest-exempt)", row.get("immediate") is True)
        recs = (read_json(outbox, {}) or {}).get("records", [])
        check("B9 the alarm is durable in the outbox, pending-delivery under the sink",
              len([r for r in recs if r.get("kind") == "alarm"]) == 1
              and recs[0].get("state") == "pending-delivery",
              "records=%d" % len(recs))
        # ONE DELIVERY. The condition must NOT also travel the owner-DM leg.
        check("B10 no owner DM was sent for the alarm", not os.path.exists(notify_file))
        check("B11 state.json carries no DM fingerprint for it",
              (read_json(state_file, {}) or {}).get("alert") is None,
              str((read_json(state_file, {}) or {}).get("alert")))
        check("B12 the pass does NOT report all green",
              "all green" not in out and "standing alarm" in out, out.strip().splitlines()[-1][:120])
        check("B13 the decision is on the outage ledger",
              any(r.get("decision") == "alarmed" and r.get("row") == ROW for r in read_jsonl(ledger_file)))

        # --- C. a second pass on the same condition mints NO second row ----------------------
        rc, out = drive(wd, "alarm", RED)
        rows = open_rows(registry)
        check("C1 still exactly one OPEN row", len(rows) == 1, "rows=%d" % len(rows))
        check("C2 the emitter was not asked twice (emission_count still 1)",
              rows and rows[0].get("emission_count") == 1,
              str(rows[0].get("emission_count")) if rows else "-")
        check("C3 the pass says the row is already open", "already open" in out,
              out.strip().splitlines()[-2][:120] if len(out.strip().splitlines()) > 1 else out[:120])

        # --- D. the row reads `up` again → the condition is CLOSED ---------------------------
        rc, out = drive(wd, "up", "verdict=GREEN")
        check("D1 no OPEN row remains", len(open_rows(registry)) == 0)
        cleared = [r for r in (read_json(registry, {}) or {}).get("rows", []) if r.get("state") == "cleared"]
        check("D2 the row is cleared, not deleted (the history survives)", len(cleared) == 1)
        check("D3 cleared_at is stamped", bool(cleared and cleared[0].get("cleared_at")))
        check("D4 the row-alarms record is empty again", read_json(row_alarms, {}) == {},
              str(read_json(row_alarms, {})))
        check("D5 the clear is on the outage ledger",
              any(r.get("decision") == "alarm-cleared" and r.get("row") == ROW for r in read_jsonl(ledger_file)))
        check("D6 clearing posted NOTHING", not os.path.exists(notify_file))

        # --- E. a green pass with nothing open costs no shim call at all ---------------------
        before = len(read_jsonl(ledger_file))
        rc, out = drive(wd, "up", "verdict=GREEN")
        check("E1 green pass exits 0 and says all green", rc == 0 and "all green" in out)
        check("E2 nothing was cleared and nothing was ledgered",
              len(read_jsonl(ledger_file)) == before, "ledger grew by %d" % (len(read_jsonl(ledger_file)) - before))
        check("E3 the registry is untouched", len(open_rows(registry)) == 0)

        # --- F. RED CONTROL: the pre-fix branch, in the same run -----------------------------
        # The mutation is the exact line the fix replaced: the `alarm` verdict appended to the
        # owner-DM list and returned, reaching the emitter never.
        red_scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-alarm-registry-red-")
        red_tool = os.path.join(red_scratch, "rbtv-ignite-watchdog")
        src = open(TOOL).read()
        fixed = """            alarming.append(name)
            lines.append(raise_row_alarm(name, detail, dry))
            continue"""
        pre_fix = """            alerts.append("%s: %s (no restart can fix this — human needed)" % (name, detail))
            continue"""
        if fixed not in src:
            check("F0 the mutation target is present in the tool", False,
                  "the `alarm` branch no longer reads as this probe expects — re-point the mutation")
        else:
            open(red_tool, "w").write(src.replace(fixed, pre_fix))
            red_registry = os.path.join(red_scratch, ".rbtv", "runtime", "ignite", "alarm-registry.json")
            red_notify = os.path.join(red_scratch, "notify.jsonl")
            os.environ.update({"RBTV_WATCHDOG_WORKSPACE": red_scratch,
                               "RBTV_WATCHDOG_LEDGER": os.path.join(red_scratch, "ledger.jsonl"),
                               "RBTV_WATCHDOG_NOTIFY_FILE": red_notify})
            red = load_watchdog(red_tool, "rbtv_ignite_watchdog_pre_fix")
            drive(red, "alarm", RED)
            check("F1 pre-fix: the alarm registry is never written", not os.path.exists(red_registry),
                  red_registry)
            check("F2 pre-fix: the condition went to the owner-DM leg alone",
                  os.path.exists(red_notify) and RED in open(red_notify).read())
            shutil.rmtree(red_scratch, ignore_errors=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    say("")
    say("%d checks, %d failed" % (len([l for l in log if l[:4] in ("PASS", "FAIL")]), len(fails)))
    text = "\n".join(log)
    print(text)
    with open(OUT, "w") as f:
        f.write(text + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

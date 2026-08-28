#!/usr/bin/env python3
"""probe-watchdog-bit7-silence — the BIT-7 regression: a daemon outage the identity read
cannot resolve determinately must now ALARM and LEDGER, where it used to do neither.

THE INCIDENT THIS PINS. 2026-08-19, 18:18:44Z→21:24:59Z: the ignite daemon was down for
3h05m, `.rbtv/runtime/watchdog/daemon.json` read `restarts: 0` the whole way through, and
no owner alarm fired. `restarts` is systemd's own NRestarts — an event counter that reads
CLEAN through a straight outage nobody tried to restart — and the four identity verdicts
only ever fired on a DETERMINATE `stopped`, so an `unknown` reading produced no note (no
alert, no DM) and no change record (no ledger row, `restarts` frozen). Both halves of the
watchdog were silent at once.

WHAT IS SIMULATED. `daemon_identity()` is replaced with a fixed non-determinate reading
carrying NO restart count — the shape of the incident — and the pass is driven directly.
Nothing on this box is probed, started, stopped or restarted: no real unit is named, no
real gateway is called, and the dead-man's configured URL points at a closed local port so
that a ping which should never happen would be VISIBLE as a failure rather than silent.

RED-FIRST, IN ONE RUN. The pre-fix path is still present and is asserted STILL SILENT:
`check_daemon()` emits no note on an `unknown` reading (that calibration is deliberate — a
failed measurement must never be dressed up as an outage). The green half is the new
`daemon_health_streak()` row next to it. The pair is the regression: same input, old path
silent, new path alarms and ledgers.

Exit 0 = every assertion held. Exit 1 = at least one failed.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import time
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "tool", "rbtv-ignite-watchdog")
OUT = os.path.join(HERE, "probe-watchdog-bit7-silence.out")

# A closed port, never a real endpoint. If the dead-man ever fires from a dry pass this is
# what makes it show up as `failed` instead of passing unnoticed.
NEVER_PINGED = "http://127.0.0.1:9/rbtv-watchdog-probe-must-never-be-pinged"
UNIT = "rbtv-watchdog-bit7-probe.service"   # named, never touched


def load_watchdog():
    spec = importlib.util.spec_from_loader(
        "rbtv_ignite_watchdog_under_probe",
        importlib.machinery.SourceFileLoader("rbtv_ignite_watchdog_under_probe", TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def main():
    log, fails = [], []

    def say(s):
        log.append(s)

    def check(name, ok, detail=""):
        say("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-bit7-")
    ledger_file = os.path.join(scratch, "outage-ledger.jsonl")
    notify_file = os.path.join(scratch, "notify.jsonl")
    registry = os.path.join(scratch, ".rbtv", "runtime", "ignite", "alarm-registry.json")
    outbox = os.path.join(scratch, ".rbtv", "runtime", "ignite", "outbox.json")
    daemon_json = os.path.join(scratch, ".rbtv", "runtime", "watchdog", "daemon.json")

    os.environ.update({
        "RBTV_WATCHDOG_WORKSPACE": scratch,
        "RBTV_WATCHDOG_LEDGER": ledger_file,
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_WATCHDOG_DEADMAN_URL": NEVER_PINGED,
        "RBTV_WATCHDOG_DAEMON_UNIT": UNIT,
        "RBTV_WATCHDOG_STRIKES": "3",
        "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-SYSTEM",
    })

    try:
        wd = load_watchdog()
        n = wd.STRIKES

        # The incident's own shape: the unit did not answer determinately, and NO restart count
        # came back with it — which is exactly why `restarts: 0` stayed clean for three hours.
        outage = {"state": "unknown", "unit": UNIT,
                  "why": "LoadState=not-found — indistinguishable from asking the wrong bus"}
        wd.daemon_identity = lambda: outage
        wd.daemon_code_state = lambda root, daemon: None

        rows_seen, notes_seen = [], []
        for _ in range(n):
            rows, notes = wd.daemon_verdicts(persist=True)
            rows_seen.append(rows)
            notes_seen.extend(notes)

        # --- 1. the OLD path is still silent on `unknown` (the calibration is kept) -----------
        check("pre-fix path still silent on an unknown reading",
              notes_seen == [],
              "check_daemon notes: %r" % (notes_seen,))

        # --- 2. the ledger records EVERY non-healthy pass ------------------------------------
        led = read_jsonl(ledger_file)
        unhealthy = [r for r in led if r["decision"] == "observed-not-healthy"]
        check("ledger carries one row per non-healthy pass",
              len(unhealthy) == n,
              "%d rows for %d passes" % (len(unhealthy), n))
        check("each non-healthy ledger row carries a reason and the consecutive count",
              all(r.get("reason") and r.get("consecutive_passes") for r in unhealthy),
              json.dumps(unhealthy[:1]))

        # --- 3. N consecutive non-healthy passes raised exactly ONE alarm --------------------
        alarmed = [r for r in led if r["decision"] == "alarmed"]
        emit_failed = [r for r in led if r["decision"] == "alarm-emit-failed"]
        check("N consecutive non-healthy passes raised exactly one alarm",
              len(alarmed) == 1 and not emit_failed,
              "alarmed=%d emit-failed=%r" % (len(alarmed), emit_failed))

        # --- 4. it went through the ONE emitter, not a second one ----------------------------
        reg = read_json(registry, {})
        open_rows = [r for r in (reg.get("rows") or []) if r.get("state") == "open"]
        check("exactly one OPEN row in the emitter's signature registry",
              len(open_rows) == 1, json.dumps(reg)[:300])
        check("the registry row is the watchdog's own signature class, system-health immediate",
              bool(open_rows)
              and open_rows[0].get("signature_class") == "watchdog-daemon-unhealthy"
              and open_rows[0].get("immediate") is True
              and open_rows[0].get("emission_count") == 1,
              json.dumps(open_rows[:1])[:400])
        check("the emitter's four required fields are all present and non-empty",
              bool(open_rows) and all(open_rows[0].get(f) for f in
                                      ("condition", "evidence_pointer", "what_would_clear_it"))
              and bool((open_rows[0].get("subject") or {}).get("id")),
              json.dumps(open_rows[:1])[:400])

        # --- 5. it reached the durable outbox as a pending-delivery alarm [C-17] -------------
        box = read_json(outbox, {})
        alarms = [r for r in (box.get("records") or box.get("rows") or []) if r.get("kind") == "alarm"]
        check("one durable outbox alarm record, held pending-delivery",
              len(alarms) == 1 and alarms[0].get("state") == "pending-delivery",
              json.dumps(box)[:300])

        # --- 6. the dead-man never pinged, and said what it would have sent -----------------
        notified = read_jsonl(notify_file)
        would = [r for r in notified if r.get("deadman") == "would-have-pinged"]
        check("no dead-man ping was attempted during the outage",
              would == [], "unexpected would-have-ping rows: %r" % (would,))

        # --- 7. RECOVERY: the outage duration is recorded as a first-class field ------------
        # Age the streak to the incident's own length. The passes above run in milliseconds, so
        # without this the recorded duration would be 0 and the assertion would prove only that a
        # field exists — not that it carries the three hours nobody could see.
        BIT7_SECONDS = 3 * 3600 + 5 * 60 + 15          # 18:18:44Z -> 21:24:59Z on 2026-08-19
        st = read_json(daemon_json, {})
        st["unhealthy_since"] = time.time() - BIT7_SECONDS
        with open(daemon_json, "w") as f:
            json.dump(st, f)

        wd.daemon_identity = lambda: {"state": "running", "unit": UNIT, "pid": 4242,
                                      "restarts": 0, "since": "probe", "invocation": "probe-inv"}
        wd.daemon_verdicts(persist=True)
        led = read_jsonl(ledger_file)
        recovered = [r for r in led if r["decision"] == "recovered"]
        check("recovery writes one ledger row carrying the outage duration",
              len(recovered) == 1 and recovered[0].get("outage_seconds") >= BIT7_SECONDS
              and recovered[0].get("unhealthy_passes") == n,
              json.dumps(recovered[:1]))
        dj = read_json(daemon_json, {})
        check("daemon.json carries last_outage_seconds — the field task #113 asked for",
              dj.get("last_outage_seconds", 0) >= BIT7_SECONDS and dj.get("last_outage_passes") == n
              and dj.get("unhealthy_streak") == 0,
              json.dumps(dj)[:300])
        check("daemon.json still reports systemd's own restarts as 0 — the field that lied",
              (dj.get("daemon") or {}).get("restarts") == 0,
              json.dumps(dj.get("daemon"))[:200])

        # --- 8. DEAD-MAN DRY MODE: a healthy pass writes a would-have-ping, never a ping -----
        notified = read_jsonl(notify_file)
        would = [r for r in notified if r.get("deadman") == "would-have-pinged"]
        check("a healthy pass wrote exactly one would-have-pinged record, and pinged nothing",
              len(would) == 1 and would[0].get("url") == NEVER_PINGED,
              json.dumps(would)[:300])
        state, detail = wd.deadman_ping()
        check("deadman_ping reports `dry` while RBTV_WATCHDOG_NOTIFY_FILE is set",
              state == "dry" and notify_file in detail, "%s / %s" % (state, detail))
        os.environ.pop("RBTV_WATCHDOG_NOTIFY_FILE")
        state_off, _ = wd.deadman_ping()
        check("with the sink removed the closed-port URL FAILS — proving the dry arm was a wall, "
              "not an absent endpoint", state_off == "failed", state_off)
        os.environ["RBTV_WATCHDOG_NOTIFY_FILE"] = notify_file

        # --- 9. the restart GATE ledgers every withheld arm, with its reason ----------------
        os.remove(ledger_file)
        wd.daemon_identity = lambda: outage
        # Three-valued since 2026-08-28 (A-1): the third member is the ROUTE the held condition
        # takes — `dm`, `alarm` (already delivered through the emitter) or `silent` (a gateway
        # timeout below RBTV_WATCHDOG_TIMEOUT_STRIKES). None of the arms below is a timeout
        # against a LIVE unit, so every one of them still routes `dm`, exactly as before.
        allow1, note1, route1 = wd.daemon_restart_gate("simulated: gateway timed out")
        allow2, _, _ = wd.daemon_restart_gate("simulated: gateway timed out")
        allow3, _, _ = wd.daemon_restart_gate("simulated: gateway timed out")
        led = read_jsonl(ledger_file)
        withheld = [r for r in led if r["decision"] == "restart-withheld"]
        allowed = [r for r in led if r["decision"] == "restart-allowed"]
        check("the first N-1 passes withhold the restart and each writes a reasoned ledger row",
              allow1 is False and allow2 is False and len(withheld) == n - 1
              and all(r.get("reason") and r.get("arm") == "strikes" for r in withheld),
              json.dumps(withheld))
        check("the withheld rows name the strike and the threshold",
              all(r.get("threshold") == n for r in withheld), json.dumps(withheld[:1]))
        check("spending the strikes writes a restart-allowed decision row",
              allow3 is True and len(allowed) == 1 and allowed[0].get("arm") == "strikes-spent",
              json.dumps(allowed))

        # the unit-alive arm — a restart WITHHELD forever, the arm that alarms and never acts
        os.remove(ledger_file)
        wd.daemon_identity = lambda: {"state": "running", "unit": UNIT, "pid": 4242,
                                      "restarts": 0, "since": "probe", "invocation": "probe-inv"}
        allow4, _, route4 = wd.daemon_restart_gate("simulated: gateway unanswerable")
        alive = [r for r in read_jsonl(ledger_file) if r.get("arm") == "unit-alive"]
        check("the unit-alive arm withholds and ledgers its reason",
              allow4 is False and len(alive) == 1 and alive[0]["decision"] == "restart-withheld"
              and alive[0].get("reason"),
              json.dumps(alive))
        check("neither arm above is a timeout against a LIVE unit, so both still route to the "
              "owner-DM leg on pass 1 (route1: timeout, unit NOT alive; route4: unit alive, not a "
              "timeout)",
              route1 == "dm" and route4 == "dm", "route1=%s route4=%s" % (route1, route4))

        # --- 10. no second alarm path survives in this component ---------------------------
        # ⚠ The tokens are ASSEMBLED, never written literally, and this file is skipped: a
        # checker that greps for a name it also contains reports itself and turns a real signal
        # into a permanent red.
        tokens = ("goal-" + "stall-" + "alarm", "alarm" + "OnStall")
        offenders = []
        for root, _dirs, files in os.walk(os.path.dirname(HERE)):
            if "__pycache__" in root:
                continue
            for fn in files:
                fp = os.path.join(root, fn)
                if os.path.abspath(fp) == os.path.abspath(__file__):
                    continue
                try:
                    body = open(fp, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                if any(t in body for t in tokens):
                    offenders.append(fp)
        check("no reference to the deleted stall-alarm pager anywhere in daemon-watchdog/",
              offenders == [], repr(offenders))

    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    verdict = "PROBE PASS — %d checks" % (len(log)) if not fails else \
              "PROBE FAIL — %d of %d checks failed: %s" % (len(fails), len(log), ", ".join(fails))
    body = "\n".join(log) + "\n\n" + verdict + "\n"
    sys.stdout.write(body)
    with open(OUT, "w") as f:
        f.write(body)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

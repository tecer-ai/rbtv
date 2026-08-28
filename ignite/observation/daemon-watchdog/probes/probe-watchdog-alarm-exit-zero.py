#!/usr/bin/env python3
"""probe-watchdog-alarm-exit-zero — an ALARM is not a systemd failure (owner ruling R1).

R1 (2026-08-15): a standing alarm exits 0 and records itself; the unit shows FAILED only when the
watchdog ITSELF breaks. Before it, an alarm exited 1 and — the timer re-firing every ~60s —
systemd logged a unit failure once a minute for as long as the alarm stood, so
`systemctl --user --failed` was useless for exactly the window something was wrong.

Four assertions over ONE staged alarm (a scratch workspace with a fake probe-suite artifact
graded RED, only the `probe-suite` row enabled — no systemd unit is read, started or stopped, and
the live registry, row-alarms and dedupe state are never touched):

  1. the alarm was actually GRADED — without this the exit-0 assertion is vacuous, since a
     pass that found nothing also exits 0;
  2. it exits 0;
  3. the standing alarm is RECORDED (R1's other half: exit 0 with no record is the alarm going
     silent, which is not what was ruled). Since a5b57bc0 that record is the alarm-registry row
     plus `row-alarms.json`, NOT `state.json` — an `alarm` no longer travels the DM leg whose
     fingerprint `state.json` holds (daemon-watchdog.md:180);
  4. the owner-DM leg does NOT fire beside it — one delivery, never two (daemon-watchdog.md:76,
     spec-owner-io §9.2).

Plus the NON-VACUITY control: a genuinely broken pass (the row-alarms store unwritable, so the
tool raises where it records the alarm it has just raised) still exits NONZERO — the property
that keeps a failed unit worth reading (daemon-watchdog.md:252-258 — exit 0 means the pass RAN,
anything else means the watchdog itself broke).

Exit 0 = all assertions held. Exit 1 = at least one failed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHDOG = os.path.join(os.path.dirname(HERE), "tool", "rbtv-ignite-watchdog")
OUT = os.path.join(HERE, "probe-watchdog-alarm-exit-zero.out")


def main():
    log, fails = [], []

    def check(name, ok, detail=""):
        log.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                                  ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-alarm-")
    workspace = os.path.join(scratch, "ws")
    notify_file = os.path.join(scratch, "notify.jsonl")
    state_file = os.path.join(scratch, "state.json")
    artifact = os.path.join(workspace, ".rbtv", "runtime", "probe-suite", "latest.json")
    registry = os.path.join(workspace, ".rbtv", "runtime", "ignite", "alarm-registry.json")
    row_alarms = os.path.join(workspace, ".rbtv", "runtime", "watchdog", "row-alarms.json")
    env = dict(os.environ)
    env.update({
        "RBTV_WATCHDOG_TARGETS": "probe-suite",
        "RBTV_WATCHDOG_WORKSPACE": workspace,
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_WATCHDOG_STATE": state_file,
        "RBTV_WATCHDOG_NOTIFY_PREFIX": "",
        # The shim refuses an alarm with no system channel, and a refused alarm records nothing —
        # stage 3 would then fail for the fixture's reason, not the tool's. The channel is a fake
        # id and nothing reaches Slack: the shim checks the notify sink above BEFORE any token.
        "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-ALARM-EXIT-ZERO",
    })
    # The dedupe record must resolve INSIDE the scratch workspace: an ambient override in the
    # operator's shell would aim this fixture's writes at the live one.
    env.pop("RBTV_WATCHDOG_ROW_ALARMS", None)

    def watchdog(over=None):
        e = dict(env)
        e.update(over or {})
        p = subprocess.run([sys.executable, WATCHDOG], capture_output=True, text=True, env=e)
        return p.returncode, (p.stdout + p.stderr).strip()

    def read_json(path, default=None):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default

    def open_registry_rows():
        return [r for r in (read_json(registry, {}) or {}).get("rows", [])
                if r.get("state") == "open"]

    try:
        log.append("# probe-watchdog-alarm-exit-zero — %s"
                   % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        log.append("")
        os.makedirs(os.path.dirname(artifact))
        with open(artifact, "w") as f:
            json.dump({"fired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "stale_after_seconds": 7200, "verdict": "RED", "failed": 3}, f)

        rc, out = watchdog()
        log.append("--- pass 1: staged ALARM (exit=%s) ---" % rc)
        log.append(out)
        log.append("")
        check("stage 1: the staged alarm was GRADED (exit 0 is not vacuous)",
              "alarm" in out, out.splitlines()[0])
        check("stage 2: a standing alarm exits 0", rc == 0, "exit=%s" % rc)

        rows = open_registry_rows()
        opened = read_json(row_alarms, {}) or {}
        check("stage 3: the standing alarm is RECORDED — one open registry row, named in row-alarms",
              len(rows) == 1
              and rows[0].get("signature_class") == "watchdog-probe-suite-alarm"
              and "probe-suite" in opened,
              "open row(s)=%d, row-alarms=%s" % (len(rows), json.dumps(opened)))
        notes = [json.loads(l) for l in open(notify_file)] if os.path.exists(notify_file) else []
        check("stage 4: the owner-DM leg does NOT fire beside it (one delivery, never two)",
              notes == [] and (read_json(state_file, {}) or {}).get("alert") is None,
              "%d notification(s), state alert=%s"
              % (len(notes), (read_json(state_file, {}) or {}).get("alert")))

        # ── the control: the watchdog BREAKING is still nonzero ─────────────
        # The break is provoked where this path actually writes: `row-alarms.json` under a
        # regular file, so `write_json_atomic` raises when the tool records the row it just
        # raised. (Before a5b57bc0 the same arm used an unwritable RBTV_WATCHDOG_STATE — an
        # `alarm` no longer writes state.json at all, so that provocation stopped provoking.)
        rc2, out2 = watchdog({"RBTV_WATCHDOG_ROW_ALARMS": os.path.join(artifact, "nope.json")})
        log.append("--- pass 2 (control): unwritable row-alarms path, the tool RAISES (exit=%s) ---" % rc2)
        log.append(out2[-400:])
        log.append("")
        check("stage 5: CONTROL — the watchdog itself breaking exits NONZERO",
              rc2 != 0 and "Error" in out2, "exit=%s" % rc2)
    except Exception as ex:
        check("probe ran to completion", False, "%s: %s" % (type(ex).__name__, ex))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.append("")
    log.append("PROBE %s (%d failure%s)" % ("PASS" if not fails else "FAIL",
                                            len(fails), "" if len(fails) == 1 else "s"))
    text = "\n".join(log) + "\n"
    with open(OUT, "w") as f:
        f.write(text)
    sys.stdout.write(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

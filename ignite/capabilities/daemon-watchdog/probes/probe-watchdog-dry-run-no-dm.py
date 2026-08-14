#!/usr/bin/env python3
"""probe-watchdog-dry-run-no-dm — a --dry-run can never DM the owner.

An `alarm` row (up, but a human is needed) reaches the notify block WITHOUT passing
the --dry-run branch in main(), so for a while `--dry-run` still sent a real Slack DM
on any alarm. This proves the guard: under --dry-run the send leg does not fire, the
alert is still SHOWN, and the dedupe state is not consumed.

The alarm is staged entirely in a scratch workspace (RBTV_WATCHDOG_WORKSPACE + a fake
probe-suite artifact graded RED) with only the `probe-suite` row enabled — no systemd
unit is read, started or stopped, and the live dedupe state is never touched.

The CONTROL arm runs the same fixture WITHOUT --dry-run and requires the notification
to land in RBTV_WATCHDOG_NOTIFY_FILE. Without it the dry assertion would pass for the
wrong reason (a fixture that never reaches the notify leg at all).

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
OUT = os.path.join(HERE, "probe-watchdog-dry-run-no-dm.out")


def main():
    log, fails = [], []

    def check(name, ok, detail=""):
        log.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-dryrun-")
    notify_file = os.path.join(scratch, "notify.jsonl")
    state_file = os.path.join(scratch, "state.json")
    artifact = os.path.join(scratch, "ws", ".rbtv", "runtime", "probe-suite", "latest.json")
    env = dict(os.environ)
    env.update({
        "RBTV_WATCHDOG_TARGETS": "probe-suite",
        "RBTV_WATCHDOG_WORKSPACE": os.path.join(scratch, "ws"),
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_WATCHDOG_STATE": state_file,
        "RBTV_WATCHDOG_NOTIFY_PREFIX": "",
    })

    def watchdog(*args):
        p = subprocess.run([sys.executable, WATCHDOG, *args],
                           capture_output=True, text=True, env=env)
        return p.returncode, (p.stdout + p.stderr).strip()

    def notifications():
        if not os.path.exists(notify_file):
            return []
        with open(notify_file) as f:
            return [json.loads(l) for l in f if l.strip()]

    try:
        log.append("# probe-watchdog-dry-run-no-dm — %s"
                   % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        log.append("")

        os.makedirs(os.path.dirname(artifact))
        with open(artifact, "w") as f:
            json.dump({"fired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "stale_after_seconds": 7200, "verdict": "RED", "failed": 3}, f)

        # ── 1. the dry arm ──────────────────────────────────────────────────
        rc, out = watchdog("--dry-run")
        log.append("--- pass 1: --dry-run over a staged ALARM (exit=%s) ---" % rc)
        log.append(out)
        log.append("")
        check("stage 1: the staged alarm was graded", "alarm" in out, out.splitlines()[0])
        check("stage 2: --dry-run sent NOTHING", notifications() == [],
              "%d notification(s) in the sink" % len(notifications()))
        check("stage 3: the alert is still SHOWN, not swallowed",
              "NOT sent" in out and "verdict is RED" in out)
        check("stage 4: --dry-run did not consume the dedupe state",
              not os.path.exists(state_file))

        # ── 2. the control: the same fixture DOES notify for real ───────────
        rc2, out2 = watchdog()
        log.append("--- pass 2 (control): same fixture, no --dry-run (exit=%s) ---" % rc2)
        log.append(out2)
        log.append("")
        check("stage 5: CONTROL — without --dry-run the notify leg fires",
              len(notifications()) == 1, "%d notification(s)" % len(notifications()))
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

#!/usr/bin/env python3
"""probe-watchdog-alarm-exit-zero — an ALARM is not a systemd failure (owner ruling R1).

R1 (2026-08-15): a standing alarm exits 0 and records itself in the state file; the owner
DM is unchanged; the unit shows FAILED only when the watchdog ITSELF breaks. Before it, an
alarm exited 1 and — the timer re-firing every ~60s — systemd logged a unit failure once a
minute for as long as the alarm stood, so `systemctl --user --failed` was useless for
exactly the window something was wrong.

Four assertions over ONE staged alarm (a scratch workspace with a fake probe-suite
artifact graded RED, only the `probe-suite` row enabled — no systemd unit is read, started
or stopped, and the live dedupe state is never touched):

  1. the alarm was actually GRADED — without this the exit-0 assertion is vacuous, since a
     pass that found nothing also exits 0;
  2. it exits 0;
  3. the state file names the alarm (R1's other half: exit 0 with no record is the alarm
     going silent, which is not what was ruled);
  4. the owner DM still fires (through RBTV_WATCHDOG_NOTIFY_FILE, never Slack).

Plus the NON-VACUITY control: a genuinely broken pass (an unwritable state path, so the
tool raises) still exits NONZERO — the property that keeps a failed unit worth reading.

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

    def watchdog(over=None):
        e = dict(env)
        e.update(over or {})
        p = subprocess.run([sys.executable, WATCHDOG], capture_output=True, text=True, env=e)
        return p.returncode, (p.stdout + p.stderr).strip()

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

        state = json.load(open(state_file)) if os.path.exists(state_file) else {}
        check("stage 3: the state file records the standing alarm",
              "probe-suite" in (state.get("alert") or ""), json.dumps(state))
        notes = [json.loads(l) for l in open(notify_file)] if os.path.exists(notify_file) else []
        check("stage 4: the owner DM leg still fires on an alarm",
              len(notes) == 1 and "RED" in notes[0].get("text", ""),
              "%d notification(s)" % len(notes))

        # ── the control: the watchdog BREAKING is still nonzero ─────────────
        rc2, out2 = watchdog({"RBTV_WATCHDOG_STATE": os.path.join(state_file, "nope.json")})
        log.append("--- pass 2 (control): unwritable state path, the tool RAISES (exit=%s) ---" % rc2)
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

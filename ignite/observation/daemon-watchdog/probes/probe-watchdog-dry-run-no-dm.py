#!/usr/bin/env python3
"""probe-watchdog-dry-run-no-dm — a --dry-run delivers NOTHING, on any surface.

An `alarm` row (up, but a human is needed) reaches the delivery block WITHOUT passing the
--dry-run branch in main(), so for a while `--dry-run` still sent a real Slack DM on any
alarm. Since a5b57bc0 that condition is delivered ONCE, through the alarm registry, and the
owner-DM leg beside it is gone — "one delivery, never two" (daemon-watchdog.md:76 and :180,
spec-owner-io §9.2). The guard moved with the delivery: under --dry-run NO registry row is
raised and NO DM is sent, the alert is still SHOWN, and the per-row dedupe record is not
consumed.

The alarm is staged entirely in a scratch workspace (RBTV_WATCHDOG_WORKSPACE + a fake
probe-suite artifact graded RED) with only the `probe-suite` row enabled — no systemd unit is
read, started or stopped, and the live registry, row-alarms and dedupe state are never touched.

The CONTROL arm runs the same fixture WITHOUT --dry-run and requires the registry row to be
raised for real. Without it the dry assertions would pass for the wrong reason (a fixture that
never reaches the delivery leg at all).

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
        # The shim refuses an alarm with no system channel, which would make the control arm
        # green for the wrong reason. The channel is a fake id and nothing reaches Slack: the
        # notify sink above is checked by the shim BEFORE any token, so an ambient
        # SLACK_BOT_TOKEN cannot turn this probe into a post in the owner's workspace.
        "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-DRY-RUN",
    })
    # The dedupe record must resolve INSIDE the scratch workspace: an ambient override in the
    # operator's shell would aim this fixture's writes at the live one.
    env.pop("RBTV_WATCHDOG_ROW_ALARMS", None)

    def watchdog(*args):
        p = subprocess.run([sys.executable, WATCHDOG, *args],
                           capture_output=True, text=True, env=env)
        return p.returncode, (p.stdout + p.stderr).strip()

    def notifications():
        if not os.path.exists(notify_file):
            return []
        with open(notify_file) as f:
            return [json.loads(l) for l in f if l.strip()]

    def open_registry_rows():
        try:
            with open(registry) as f:
                doc = json.load(f)
        except Exception:
            return []
        return [r for r in doc.get("rows", []) if r.get("state") == "open"]

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
        check("stage 2: --dry-run delivered NOTHING — no DM, no registry row",
              notifications() == [] and not os.path.exists(registry),
              "%d notification(s), registry written=%s"
              % (len(notifications()), os.path.exists(registry)))
        check("stage 3: the alert is still SHOWN, not swallowed",
              "would raise" in out and "--dry-run" in out
              and "verdict is RED" in out and "all green" not in out)
        check("stage 4: --dry-run did not consume the dedupe record",
              not os.path.exists(row_alarms) and not os.path.exists(state_file),
              "row-alarms written=%s, state written=%s"
              % (os.path.exists(row_alarms), os.path.exists(state_file)))

        # ── 2. the control: the same fixture DOES raise the registry row ────
        rc2, out2 = watchdog()
        log.append("--- pass 2 (control): same fixture, no --dry-run (exit=%s) ---" % rc2)
        log.append(out2)
        log.append("")
        check("stage 5: CONTROL — without --dry-run the registry row IS raised, and ONLY it",
              len(open_registry_rows()) == 1 and notifications() == [],
              "%d open registry row(s), %d notification(s)"
              % (len(open_registry_rows()), len(notifications())))
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

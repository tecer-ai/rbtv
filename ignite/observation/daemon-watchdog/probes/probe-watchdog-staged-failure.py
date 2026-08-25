#!/usr/bin/env python3
"""probe-watchdog-staged-failure — CMP-28's done check, run as a probe.

Stages a real failure and proves the whole chain end to end: down -> detected ->
restarted -> notified -> recovered, then proves a clean pass is SILENT — and that the
silence has a CEILING: an unchanged alert is suppressed, but past the re-alert window
it is re-sent marked as standing, so a condition that never clears can never read as
a healthy system.

It runs against a THROWAWAY unit it creates and removes, reached through the
watchdog's documented env override (RBTV_WATCHDOG_TARGETS + the per-row unit var) —
never by editing the real probe table. The three live units (rbtv-ignite,
rbtv-chat-bridge, rbtv-probe-suite) are never started, stopped or restarted by this
probe, exactly as `rbtv-ignite-daemon selftest` never touches the configured unit.

Notify goes to RBTV_WATCHDOG_NOTIFY_FILE, a test double. A real owner DM is a
one-time manual confirmation, never part of a repeatable automated check.

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
OUT = os.path.join(HERE, "probe-watchdog-staged-failure.out")
UNIT = "rbtv-watchdog-selftest.service"
UNIT_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                        "systemd", "user")
UNIT_FILE = os.path.join(UNIT_DIR, UNIT)


def sc(*args, check=False):
    p = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError("systemctl %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.returncode, (p.stdout + p.stderr).strip()


def is_active():
    return sc("is-active", UNIT)[1].strip()


def main():
    log, fails = [], []

    def say(s):
        log.append(s)

    def check(name, ok, detail=""):
        say("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-probe-")
    notify_file = os.path.join(scratch, "notify.jsonl")
    state_file = os.path.join(scratch, "state.json")
    env = dict(os.environ)
    env.update({
        # The whole confinement of this probe is these two lines: ONE row, pointed at
        # the throwaway unit. Nothing else in the probe table is even evaluated.
        "RBTV_WATCHDOG_TARGETS": "bridge",
        "RBTV_WATCHDOG_BRIDGE_UNIT": UNIT,
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_WATCHDOG_STATE": state_file,
        # The operator verb is a sibling COMPONENT since the component-first move: the
        # watchdog is `observation/`'s, `daemon-operator/` is `operator/`'s.
        "RBTV_WATCHDOG_OPERATOR": os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
            "operator", "daemon-operator", "tool", "rbtv-ignite-daemon"),
        "RBTV_IGNITE_SETTLE_SECONDS": "2",
    })

    def watchdog(**overrides):
        t0 = time.time()
        e = dict(env, **overrides)
        p = subprocess.run([sys.executable, WATCHDOG], capture_output=True, text=True, env=e)
        return p.returncode, (p.stdout + p.stderr).strip(), int((time.time() - t0) * 1000)

    def stage_failure():
        sc("kill", "--signal=SIGKILL", UNIT)
        time.sleep(1)

    def notifications():
        if not os.path.exists(notify_file):
            return []
        with open(notify_file) as f:
            return [json.loads(l) for l in f if l.strip()]

    try:
        say("# probe-watchdog-staged-failure — %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        say("# throwaway unit: %s   (the three live rbtv units are never touched)" % UNIT)
        say("")

        os.makedirs(UNIT_DIR, exist_ok=True)
        with open(UNIT_FILE, "w") as f:
            f.write("[Unit]\n"
                    "Description=throwaway unit for the CMP-28 watchdog staged-failure probe\n"
                    "[Service]\n"
                    "Type=simple\n"
                    "ExecStart=/bin/sh -c 'while :; do sleep 5; done'\n")
        sc("daemon-reload", check=True)
        sc("reset-failed", UNIT)
        sc("start", UNIT, check=True)
        time.sleep(1)
        check("stage 0: throwaway unit is active", is_active() == "active", is_active())

        # ── 1. bring it down ────────────────────────────────────────────────
        stage_failure()
        down = is_active()
        check("stage 1: unit is DOWN before the pass", down != "active", "is-active=%s" % down)

        # ── 2. one watchdog pass: detect -> restart -> notify -> recover ─────
        rc, out, ms = watchdog()
        say("")
        say("--- watchdog pass 1 (staged failure) exit=%s wall_ms=%s ---" % (rc, ms))
        say(out)
        say("")
        check("stage 2: the pass DETECTED the failure", "down" in out.splitlines()[0])
        check("stage 3: RESTART fired and the unit is back",
              is_active() == "active", "is-active=%s" % is_active())
        n1 = notifications()
        check("stage 4: NOTIFY fired exactly once", len(n1) == 1, "%d notification(s)" % len(n1))
        if n1:
            check("stage 4b: the notification is an ACTED message",
                  "is back" in n1[-1]["text"] and UNIT in n1[-1]["text"],
                  n1[-1]["text"].replace("\n", " ")[:160])
        check("stage 5: pass exits 0 once the subject is restored", rc == 0, "exit=%s" % rc)

        # ── 3. a clean pass must be SILENT (CMP-28 invariant 3) ─────────────
        rc2, out2, ms2 = watchdog()
        say("--- watchdog pass 2 (subject healthy) exit=%s wall_ms=%s ---" % (rc2, ms2))
        say(out2)
        say("")
        n2 = notifications()
        check("stage 6: an ALL-GREEN pass sends NO notification",
              len(n2) == len(n1), "%d before, %d after" % (len(n1), len(n2)))
        check("stage 7: an all-green pass exits 0", rc2 == 0, "exit=%s" % rc2)
        check("stage 8: the all-green pass says so on stdout", "all green" in out2)

        # ── 4. the repeat ceiling: suppressed, but NOT forever ──────────────
        # Dedupe alone would let a condition that never clears go permanently silent,
        # which is indistinguishable from health on the only channel that pushes.
        stage_failure()
        rc3, out3, _ = watchdog()
        n3 = notifications()
        check("stage 9: a fault recurring after a green pass DOES notify",
              len(n3) == len(n2) + 1, "%d -> %d" % (len(n2), len(n3)))

        stage_failure()
        rc4, out4, _ = watchdog()
        n4 = notifications()
        check("stage 10: the SAME alert on the next pass is suppressed",
              len(n4) == len(n3) and "[repeat]" in out4, "%d -> %d" % (len(n3), len(n4)))

        stage_failure()
        rc5, out5, _ = watchdog(RBTV_WATCHDOG_REALERT_SECONDS="0")
        n5 = notifications()
        check("stage 11: past the re-alert ceiling the SAME alert is re-sent",
              len(n5) == len(n4) + 1, "%d -> %d" % (len(n4), len(n5)))
        if len(n5) > len(n4):
            check("stage 11b: the re-alert is marked as standing, not new",
                  "STILL UNRESOLVED" in n5[-1]["text"],
                  n5[-1]["text"].splitlines()[0])

    except Exception as ex:
        check("probe ran to completion", False, "%s: %s" % (type(ex).__name__, ex))
    finally:
        # ── 4. teardown: the throwaway unit must not survive this probe ─────
        sc("stop", UNIT)
        sc("reset-failed", UNIT)
        if os.path.exists(UNIT_FILE):
            os.remove(UNIT_FILE)
        sc("daemon-reload")
        shutil.rmtree(scratch, ignore_errors=True)
        gone = sc("show", UNIT, "-p", "LoadState", "--value")[1].strip() != "loaded"
        check("stage 12: throwaway unit removed", gone and not os.path.exists(UNIT_FILE))

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

#!/usr/bin/env python3
"""probe-watchdog-goal-watcher-arm — the goal-watcher arm reads the LIVE job, and a
missing queue row ALARMS.

Guards the two ways this arm has already failed silently:

  1. It was keyed on `selfheal-watch`, a job deregistered 2026-08-11. Every pass after
     that logged "no queue row — not scheduled" and the arm was PERMANENTLY INERT. A
     retired id in this arm's config is therefore a hard FAIL here, by source scan —
     the default alone is not enough, the string must be gone.
  2. That inert state read as `skip`, which main() treats exactly like `up`: no DM, no
     failed unit. So the arm's ONE hard failure was indistinguishable from health. No
     row now returns `alarm` (report, human needed) — never `down`, because no restart
     creates a queue row.

`gateway_call` is stubbed, so this needs no daemon, no gateway, no systemd and no
network — it runs on any host, unlike its sibling probe-watchdog-staged-failure.

Exit 0 = all assertions held. Exit 1 = at least one failed.
"""
import importlib.machinery
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHDOG = os.path.join(os.path.dirname(HERE), "tool", "rbtv-ignite-watchdog")
OUT = os.path.join(HERE, "probe-watchdog-goal-watcher-arm.out")


def load_watchdog():
    """The tool is extensionless (it is an executable, not a module), so the loader is
    named explicitly rather than inferred from the suffix."""
    spec = importlib.util.spec_from_loader(
        "rbtv_ignite_watchdog",
        importlib.machinery.SourceFileLoader("rbtv_ignite_watchdog", WATCHDOG))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stamp(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def main():
    log, fails, ran = [], [], []

    def check(name, ok, detail=""):
        ran.append(name)
        log.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    # The arm must not be keyed on a retired id ANYWHERE — default, comment or fallback.
    with open(WATCHDOG) as f:
        src = f.read()
    check("retired 'selfheal-watch' id absent from the watchdog tool",
          "selfheal-watch" not in src)

    os.environ.pop("RBTV_WATCHDOG_WATCH_JOB", None)
    wd = load_watchdog()
    check("default watch job is the live catalogue entry", wd.WATCH_JOB == "goal-watcher-job",
          "WATCH_JOB=%s" % wd.WATCH_JOB)

    def with_rows(rows):
        wd.gateway_call = lambda target: ("ok", {"result": {"rows": rows}})
        return wd.probe_goal_watcher()

    row = lambda **kw: dict({"job_id": wd.WATCH_JOB, "interval_seconds": 1800}, **kw)

    # RED-FIRST: the row is gone. This is the state that used to read as health.
    state, detail = with_rows([])
    check("no queue row -> alarm (not skip, not down)", state == "alarm",
          "got %s: %s" % (state, detail))

    # A row for some OTHER job must not satisfy the arm — that is the exact shape of the
    # 2026-08-11 defect seen from the other side.
    state, _ = with_rows([row(job_id="goal-creation-request", run_at=stamp(+600))])
    check("a foreign job's row does not satisfy the arm", state == "alarm")

    # GREEN: the live row, due in the future.
    state, detail = with_rows([row(run_at=stamp(+600))])
    check("live row due -> up", state == "up", "got %s: %s" % (state, detail))

    # Overdue by more than one whole interval -> down (a restart is the lever).
    state, detail = with_rows([row(run_at=stamp(-3600))])
    check("row overdue by > interval -> down", state == "down", "got %s: %s" % (state, detail))

    # One interval of slack: a single slow fire must not read as death.
    state, _ = with_rows([row(run_at=stamp(-60))])
    check("row overdue by < interval -> still up", state == "up")

    # Queue unreadable stays a skip: the daemon row owns that cause and its only lever.
    wd.gateway_call = lambda target: ("down", "connect refused")
    state, _ = wd.probe_goal_watcher()
    check("queue unreadable -> skip (the daemon row owns it)", state == "skip")

    log.append("")
    log.append("%d checks, %d failed" % (len(ran), len(fails)))
    text = "\n".join(log) + "\n"
    with open(OUT, "w") as f:
        f.write(text)
    print(text, end="")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

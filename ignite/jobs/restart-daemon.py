#!/usr/bin/env python3
"""Restart a systemd --user unit as a `fire-tool` job (ruling `r-restart-daemon-job`).

WHY THIS EXISTS. A config change reached the daemon only when a human typed the restart.
On 2026-08-04 the owner ruled that away: the restart becomes a job the run's `leader` may
enqueue, fired by the daemon's own machinery, with no classifier in the path and every
firing queue-recorded and attributable.

CONTAINMENT IS THE SCRIPT'S OWN, and it is NOT re-derived here. A `fire-tool` exec is
unsandboxed and uncapped (`runToolLikeExec` builds its carrier request with literal
`caps: {}` / `sandbox: {}`), so `jobcontain.py` — which already holds all three duties and
records the two traps that produced them — is reused verbatim: `contain()` for the wall
clock, `single_instance()` for the lock, `detach_argv()` + `child_preexec()` for the act.

THE ACT RUNS IN ITS OWN TRANSIENT UNIT, AND THAT IS NOT CONDITIONAL ON THE MEASUREMENT.
Measured 2026-08-04 on this box: the daemon is
`/user.slice/user-1000.slice/user@1000.service/app.slice/rbtv-ignite.service`, and a
`systemd-run --user` transient unit lands at `.../app.slice/<unit>.service` — a SIBLING,
not a child. The carrier is `systemd` (required, D48), so a fire-tool exec would in fact
survive `systemctl --user restart rbtv-ignite` on its own. The wrap is applied anyway:
wrapping costs nothing, and being wrong about it costs a daemon that is down with nothing
running to bring it back. The wrap also buys systemd's own `--unit=` refusal as a second
double-start guard under the flock.

STATED BOUND — THIS SCRIPT DISPATCHES THE RESTART, IT DOES NOT AWAIT IT. `detach_argv`
produces a `systemd-run` invocation without `--wait`, so this process learns only whether
the transient unit STARTED, never what the restart itself returned. A non-zero exit here
means the dispatch failed; a zero exit means the restart was handed to systemd, which owns
its outcome from that point. Awaiting it would need `--wait`, which `jobcontain` does not
offer and which this script does not re-implement.

NO POLICY NUMBER IS INVENTED HERE. `--unit` and `--budget-s` are both REQUIRED; the caller
(the `tools:` entry in spawn-profiles.yaml) supplies them. The address-space cap is
`jobcontain.contain()`'s own, not a second copy of it.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobcontain  # noqa: E402  — self-containment; a fire-tool exec gets none (G-30)


def log(msg):
    print(f"restart-daemon: {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Restart a systemd --user unit, contained.")
    ap.add_argument("--unit", required=True,
                    help="the systemd --user unit to restart (e.g. rbtv-ignite)")
    ap.add_argument("--budget-s", type=int, required=True,
                    help="this job's own wall-clock cap, in seconds; no default is invented here")
    args = ap.parse_args()

    jobcontain.contain(seconds=args.budget_s)

    # Keyed on the target unit, as selfheal-room keys on its session: two different targets
    # are two different jobs and must not block each other.
    lock_path = Path(tempfile.gettempdir()) / f"restart-daemon.{args.unit}.lock"
    held = jobcontain.single_instance(str(lock_path))
    if held is None:
        log(f"ANOTHER INSTANCE HOLDS {lock_path} — refusing to restart '{args.unit}'.")
        return 4

    systemctl = shutil.which("systemctl")
    if not systemctl:
        log("systemctl NOT FOUND on PATH — cannot restart anything.")
        return 5

    act = [systemctl, "--user", "restart", args.unit]
    transient = jobcontain.unit_name("rbtv-restart", args.unit)
    launch, unit = jobcontain.detach_argv(act, transient)
    if unit is None:
        log("systemd-run UNAVAILABLE — running the restart in THIS process's cgroup, "
            "which the restart may itself take down. Proceeding, loudly.")

    log(f"dispatching {' '.join(act)} via {'unit ' + unit if unit else 'a bare exec'}")
    proc = subprocess.run(launch, preexec_fn=jobcontain.child_preexec,
                          capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if out:
        log(f"stdout: {out}")
    if err:
        log(f"stderr: {err}")
    if proc.returncode != 0:
        log(f"DISPATCH FAILED (exit {proc.returncode}) — '{args.unit}' was NOT restarted.")
        return proc.returncode

    log(f"restart of '{args.unit}' DISPATCHED (not awaited — see this file's docstring).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

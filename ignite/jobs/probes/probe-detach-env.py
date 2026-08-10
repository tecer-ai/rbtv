#!/usr/bin/env python3
"""probe-detach-env.py — `jobcontain`'s detached-launch contract: the PATH crosses the inner hop,
and the fallback that is NOT a launcher is never waited on.

WHAT IT SCORES (task 7.551). `detach_argv` wraps a command in its OWN `systemd-run --user`
transient unit so it outlives the job that started it. That inner hop goes back through the systemd
USER MANAGER, whose environment is NOT the calling process's — so the PATH `server/spawn/carrier.js`
`toolExecEnv()` composed for the fired tool (the F1 fix, `d-owner-f1-carrier-env-0808`) was dropped
at the hop, and the detached process, plus everything it later starts, ran on the manager PATH.
`~/.local/bin` and `~/.opencode/bin` are NOT on that PATH, so `claude` / `codex` / `opencode` /
`coordinate` / `scaffold-seats` do not resolve there — and `selfheal-room` -> `recover-room.py` ->
`coord.py` boots the harness BY BARE NAME. `detach_argv` therefore FORWARDS `os.environ["PATH"]`.

⚠ THE ASSERTION IS ABOUT THE ENVIRONMENT, NEVER ABOUT argv[0] RESOLUTION. `systemd-run` (259 here)
resolves `argv[0]` CLIENT-side against the CALLER's PATH, so a bare-named argv through `detach_argv`
runs today, fix or no fix — an arm asserting that would be green both ways and would measure nothing.

⚠ ONE COMPOSER (PRIN-11). The value is FORWARDED, never re-derived: under the daemon
`os.environ["PATH"]` IS `toolExecEnv()`'s output byte-for-byte (measured), and from a human shell it
is that shell's own PATH — both correct, neither a second composer. Arm R2 is what makes a
re-derivation inside `jobcontain.py` fail even though it would look right.

ARMS
  C0  CONTROL — the same child through a BARE inner hop (no --setenv) must NOT see the marker dir
      and must NOT resolve the marker by name. If it does, the manager already carries the caller's
      environment on this box and R1/R2 cannot discriminate: INOPERATIVE, exit 2, never a pass.
  R1  the detached process RESOLVES a marker binary BY NAME that exists only on the caller's PATH
      (the F1 failure mode itself). Kills a fix that never threads the env.
  R2  the detached process's PATH is BYTE-EQUAL to the caller's `os.environ["PATH"]`.
      Kills a fix that RE-DERIVES a PATH inside `jobcontain.py` — that would pass R1 and fail here.
  R3  with `systemd-run` reported ABSENT, the returned argv is the caller's argv UNCHANGED and
      carries no `--setenv` (the shell fallback stays a bare exec). Kills an unconditional append.
  R4  in the returned argv `--setenv=PATH=` appears EXACTLY ONCE and BEFORE `--unit=` and before the
      caller's own argv[0]. `detach_argv` emits no `--` separator, so ordering is positional: a flag
      after the command is passed TO THE CHILD as an argument instead of setting the environment,
      which a substring check alone would not catch.
  B1  RED ARM (task 7.527) — the OLD shape, `subprocess.run(launch, timeout=T)`, on the bare
      fallback whose child never exits: it blocks for the whole timeout and then KILLS the child.
      This is the defect, pinned so the fix cannot be mistaken for a no-op.
  B2  the NEW shape, `jobcontain.launch_detached`, returns AT ONCE on that same argv and the
      loop-forever child is still alive afterwards.

TWO EXECUTION TRAPS, both hit while designing this (dossier §5) — every arm reads the CAPTURE FILE
the child wrote, never the launcher's exit code: `systemd-run --collect --quiet` returns 0 as soon
as the unit STARTS, and `--collect` garbage-collects the unit immediately, so a later
`systemctl show` returns defaults. A launcher exit != 0 means the unit never started: INOPERATIVE.

Run it through the suite — `node deploy/probe-suite.js --only detach-env` — never by hand (`G-163`).
Exit 0 = every property holds · 1 = a property is broken · 2 = INOPERATIVE (could not run, or the
control proved an arm could not have failed).
"""

import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe-detach-env.out"
MARKER = "probe-detach-env-marker"
CAPTURE_TIMEOUT_S = 20

lines = []
failures = []
inoperative = []


def say(s):
    lines.append(s)


def check(arm, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {arm}  {detail}")
    if not ok:
        failures.append(arm)


def stop(arm, why):
    say(f"INOPERATIVE  {arm}  {why}")
    inoperative.append(arm)


def alive(token):
    """pids of live processes carrying `token` in their argv — this probe's stand-in children.

    Read straight from /proc rather than through `pgrep`: arms B1/B2 deliberately strip PATH down
    to a stub directory, where no external binary resolves at all. A reaped child leaves an empty
    cmdline, so a zombie never counts as alive.
    """
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/cmdline", "rb") as fh:
                if token.encode() in fh.read():
                    out.append(int(d))
        except OSError:
            continue
    return out


def load_jobcontain():
    """Import the jobcontain.py sitting beside this probe's parent — no package, no sys.path games.

    Resolving it by LOCATION rather than by name is what lets the red-first proof run this same
    file against a PRE-FIX copy of jobcontain.py in a throwaway tree, with no flag or env knob."""
    path = HERE.parent / "jobcontain.py"
    spec = importlib.util.spec_from_file_location("jobcontain_under_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def run_and_capture(launch, cap):
    """Fire the launcher, then WAIT ON THE CAPTURE FILE. Returns (parsed, why_inoperative)."""
    res = subprocess.run(launch, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        return None, f"launcher exited {res.returncode}: {(res.stderr or '').strip()[:200]}"
    deadline = time.time() + CAPTURE_TIMEOUT_S
    while time.time() < deadline:
        if cap.exists() and cap.read_text().endswith("\n"):
            break
        time.sleep(0.1)
    if not cap.exists():
        return None, f"the unit started but wrote no capture within {CAPTURE_TIMEOUT_S}s"
    parsed = {}
    for line in cap.read_text().splitlines():
        key, _, val = line.partition("=")
        parsed[key] = val
    return parsed, None


def main():
    jc, jc_path = load_jobcontain()
    say(f"jobcontain under probe: {jc_path}")

    if not shutil.which("systemd-run"):
        stop("ALL", "systemd-run is not on this PATH — detach_argv's systemd branch is unreachable")
        return

    with tempfile.TemporaryDirectory(prefix="probe-detach-env-") as tmp:
        tmp = Path(tmp)
        bindir = tmp / "bin"
        bindir.mkdir()
        (bindir / MARKER).write_text("#!/bin/sh\necho marker\n")
        (bindir / MARKER).chmod(0o755)

        # The caller's PATH gains a directory the systemd MANAGER cannot possibly know about. That
        # is the whole discriminator: anything the detached process sees of it came across the hop.
        os.environ["PATH"] = f"{bindir}:{os.environ['PATH']}"
        caller_path = os.environ["PATH"]
        say(f"caller PATH  : {caller_path}")

        def child(cap):
            return ["/bin/sh", "-c",
                    f'printf "PATH=%s\\nWHICH=%s\\n" "$PATH" "$(command -v {MARKER})" > {cap}']

        # ---- C0: the same child through a BARE hop --------------------------------------------
        cap0 = tmp / "c0.txt"
        bare = ["systemd-run", "--user", "--collect", "--quiet",
                f"--unit=probe-detach-env-c0-{os.getpid()}", *child(cap0)]
        got0, why = run_and_capture(bare, cap0)
        if got0 is None:
            stop("C0", why)
            return
        say(f"C0 detached PATH: {got0.get('PATH')}")
        if str(bindir) in (got0.get("PATH") or "").split(":") or got0.get("WHICH"):
            stop("C0", "a BARE inner hop already carries the caller's PATH on this box — R1/R2 "
                       "would pass with or without the fix and score nothing")
            return
        say("PASS  C0  a bare inner hop loses the caller's PATH — R1/R2 can discriminate")

        # ---- R1 / R2: the real detach_argv ------------------------------------------------------
        cap1 = tmp / "r1.txt"
        launch, unit = jc.detach_argv(child(cap1), f"probe-detach-env-r1-{os.getpid()}")
        say(f"detach_argv argv: {launch}")
        if unit is None:
            stop("R1/R2", "detach_argv took its no-systemd-run fallback despite systemd-run present")
            return
        got1, why = run_and_capture(launch, cap1)
        if got1 is None:
            stop("R1/R2", why)
            return
        say(f"R1 detached PATH: {got1.get('PATH')}")
        check("R1", bool(got1.get("WHICH")),
              f"detached process resolves {MARKER!r} by name -> {got1.get('WHICH')!r} "
              "(empty = the composed PATH was lost at the hop)")
        check("R2", got1.get("PATH") == caller_path,
              "detached PATH is byte-equal to the caller's os.environ['PATH'] "
              f"(forwarded, not re-derived){'' if got1.get('PATH') == caller_path else ' — DIFFERS'}")

        # ---- R3: the shell fallback stays bare --------------------------------------------------
        real_which = shutil.which
        shutil.which = lambda name, *a, **k: None if name == "systemd-run" else real_which(name, *a, **k)
        try:
            fallback, fb_unit = jc.detach_argv(["/bin/true", "x"], "probe-detach-env-r3")
        finally:
            shutil.which = real_which
        check("R3", fallback == ["/bin/true", "x"] and fb_unit is None
              and not any(str(a).startswith("--setenv") for a in fallback),
              f"systemd-run absent -> bare argv unchanged, no --setenv: {fallback!r}, unit={fb_unit!r}")

        # ---- R4: positional ordering ------------------------------------------------------------
        setenvs = [i for i, a in enumerate(launch) if str(a).startswith("--setenv=PATH=")]
        unit_ix = [i for i, a in enumerate(launch) if str(a).startswith("--unit=")]
        argv0_ix = launch.index("/bin/sh")
        ok4 = len(setenvs) == 1 and len(unit_ix) == 1 and setenvs[0] < unit_ix[0] < argv0_ix
        check("R4", ok4,
              f"--setenv=PATH= at {setenvs}, --unit= at {unit_ix}, caller argv[0] at {argv0_ix} "
              "(must be exactly one --setenv, before --unit and before the command)")

        # ---- B1 / B2: the loop-forever fallback is DETACHED, never waited on (task 7.527) --------
        # `systemd-run` is PATH-SHADOWED BY A STUB that is present but NOT EXECUTABLE, so
        # `shutil.which` genuinely returns None — no monkeypatch — and `detach_argv` takes its bare
        # fallback, the shape whose child is the long-lived process itself rather than a launcher.
        # The stand-in child is a plain sleep, never `watch.py`: nothing real is launched, no unit
        # is created, and both arms reap their own children.
        stub = bindir / "systemd-run"
        stub.write_text("#!/bin/sh\nexit 1\n")
        stub.chmod(0o644)
        token = f"probe-detach-blocking-{os.getpid()}"
        forever = [sys.executable, "-c", f"import time  # {token}\ntime.sleep(600)"]
        saved_path = os.environ["PATH"]
        os.environ["PATH"] = str(bindir)
        try:
            if shutil.which("systemd-run"):
                stop("B1/B2", "systemd-run still resolves under the stubbed PATH — the bare "
                              "fallback is unreachable and neither arm could fail")
                return
            blaunch, bunit = jc.detach_argv(forever, "probe-detach-blocking-never-created")
            if bunit is not None or blaunch != forever:
                stop("B1/B2", f"expected the bare fallback, got unit={bunit!r} argv={blaunch!r}")
                return

            # B1 — THE OLD SHAPE, reproduced verbatim except for the timeout NUMBER: 3s instead of
            # the shipped 60 purely so the probe is quick. The SHAPE is what the fix removes.
            t0 = time.time()
            timed_out = False
            try:
                subprocess.run(blaunch, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, timeout=3)
            except subprocess.TimeoutExpired:
                timed_out = True
            b1_wall = time.time() - t0
            b1_survivors = alive(token)
            check("B1", timed_out and b1_wall >= 3 and not b1_survivors,
                  f"OLD shape blocked {b1_wall:.1f}s on a loop-forever child and then KILLED it "
                  f"(timed_out={timed_out}, survivors={b1_survivors})")

            # B2 — THE NEW SHAPE on the SAME argv and the same absent systemd-run.
            t0 = time.time()
            out, rc = jc.launch_detached(blaunch, bunit)
            b2_wall = time.time() - t0
            time.sleep(1.0)
            b2_survivors = alive(token)
            check("B2", b2_wall < 2 and bool(b2_survivors) and rc == 0,
                  f"NEW shape returned in {b2_wall:.1f}s (rc={rc}, out={out!r}) and the "
                  f"loop-forever child is STILL ALIVE: pid(s) {b2_survivors}")
        finally:
            os.environ["PATH"] = saved_path
            for pid in alive(token):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-detach-env  ({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)

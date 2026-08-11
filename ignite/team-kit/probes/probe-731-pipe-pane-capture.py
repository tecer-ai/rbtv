#!/usr/bin/env python3
"""probe-731-pipe-pane-capture.py — 7.31: the transcript is captured at pane BIRTH, and it
SURVIVES THE DEATH OF THE TMUX SERVER.

WHAT THIS GUARDS. The task's criterion is deliberately not satisfiable by reading a config: the
backup exists for the case where the tmux server dies, and tmux scrollback dies WITH it — so a
close-time `capture-pane` returns nothing exactly when it matters. This probe proves the property
the only way it can be proven: it kills a tmux server and reads the log afterwards.

THE ARMS, and the reason each one is here:

  P1  the two helpers exist and the transcript home is R31's — the seat's own
      `sessions/<session-id>/transcript.log`, under the goals tree, never the per-machine root
  P2  arming a real pane and making it speak puts bytes in that file WHILE the server is alive
  P3  ⚠⚠ THE KILL ARM — `kill-server`, then the file is still there and still NON-EMPTY. This is
      the criterion "proven by killing it, not by reading the config"
  P4  `recorded` is written AT BIRTH by the session writer and RESOLVES to the file P2/P3 proved —
      one transcript per session, pointed at from the run-level trace, no second index
  P5  ⚠ THE ORDER ARM — `launch_seat` arms the capture BEFORE it wakes the harness. Proven by
      stubbing `wake` and asking, from inside the stub, whether the transcript file already
      exists. A later pass would arm it after, and this arm is what tells the two apart

⚠ IT NEVER TOUCHES A LIVE ROOM. `TMUX_TMPDIR` is redirected into this probe's own temp dir before
coord is imported and before any tmux call, so every tmux server reachable from this process —
including the ones `coord.py` opens with its own bare `tmux` calls — lives on a socket path inside
that temp dir and cannot be a server anyone else is using. Every tmux command this file issues
ALSO names its socket explicitly (`-L default`); the name is `default` deliberately, because that
is the socket `coord.py`'s own calls use, and the isolation comes from the redirected TMUX_TMPDIR,
not from the name. The goal tree is a scratch tree under the same temp dir; nothing under `.rbtv/`
is read or written.
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
OUT = Path(__file__).resolve().parent / "probe-731-pipe-pane-capture.out"

TMUX = ["tmux", "-L", "default"]   # see the docstring: isolation is TMUX_TMPDIR's, not the name's
MARK = "PROBE-731-SPOKE-HERE"

failures = []
checks = 0
lines = []


def check(label, ok, detail=""):
    global checks
    checks += 1
    row = f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  — {detail}" if detail else "")
    print(row, flush=True)
    lines.append(row)
    if not ok:
        failures.append(label)


def tmux(*a, **kw):
    return subprocess.run(TMUX + list(a), capture_output=True, text=True, timeout=20, **kw)


def main():
    with tempfile.TemporaryDirectory(prefix="probe731-") as td:
        td = Path(td)
        sock = td / "tmuxtmp"
        sock.mkdir()
        os.environ["TMUX_TMPDIR"] = str(sock)
        os.environ.pop("TMUX", None)
        os.environ.pop("TMUX_PANE", None)

        import coord  # noqa: E402 — imported after the isolation is installed

        coord.NATIVE_ID_WAIT = 0.0     # the boot timeout, not a behaviour under test here

        goal = td / "ws" / ".rbtv" / "goals" / f"zz-probe731-{os.getpid()}"
        pkg = goal                      # 7.607 E2b — the package IS the goal folder
        (pkg / "coordination").mkdir(parents=True)
        (pkg / "seats" / "alpha").mkdir(parents=True)
        (pkg / "seats" / "beta").mkdir(parents=True)
        (pkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after\ntf-1,alpha,\ntf-1,beta,\n", encoding="utf-8")

        room = f"probe731-{os.getpid()}"
        tmux("new-session", "-d", "-s", room, "-c", str(pkg))
        pane = tmux("list-panes", "-t", room, "-F", "#{pane_id}").stdout.strip().splitlines()[0]

        armed = False
        tpath = None
        try:
            # ── P1 — the helpers, and R31's home ──────────────────────────────────────────────
            mint = getattr(coord, "mint_session_id", None)
            spath = getattr(coord, "session_transcript_path", None)
            arm = getattr(coord, "start_pane_capture", None)
            check("P1a the 7.31 surface EXISTS on the module — `mint_session_id`, "
                  "`session_transcript_path`, `start_pane_capture`",
                  callable(mint) and callable(spath) and callable(arm),
                  f"mint={bool(mint)} path={bool(spath)} arm={bool(arm)}")
            if not (callable(mint) and callable(spath) and callable(arm)):
                raise SystemExit(finish())

            sid = mint(pkg, "alpha")
            tpath = spath(pkg, "alpha", sid)
            check("P1b the transcript lands at R31's home — the seat's own "
                  "`sessions/<session-id>/` subtree, WORKSPACE-SIDE under the goals tree, and "
                  "never in a per-machine ignite root",
                  tpath == pkg / "seats" / "alpha" / "sessions" / sid / "transcript.log"
                  and str(goal) in str(tpath), str(tpath))
            check("P1c ONE transcript per session BY CONSTRUCTION — a different session-id is a "
                  "different folder, so no two sessions can share a file",
                  spath(pkg, "alpha", "sid-x") != spath(pkg, "alpha", "sid-y"))

            # ── P2 — arm it, make the pane speak ──────────────────────────────────────────────
            armed, aerr = arm(pane, tpath)
            check("P2a arming a live pane succeeds and creates the transcript's folder",
                  armed and tpath.parent.is_dir(), aerr)
            tmux("send-keys", "-t", pane, f"echo {MARK}", "Enter")
            for _ in range(40):
                if tpath.exists() and MARK in tpath.read_text(errors="replace"):
                    break
                time.sleep(0.25)
            body_live = tpath.read_text(errors="replace") if tpath.exists() else ""
            check("P2b what the pane produced is ON DISK while the server is still alive — the "
                  "capture is a live pipe, not a buffer waiting for a close",
                  MARK in body_live, f"{len(body_live)} bytes")

            # ── P5 — the ORDER: launch_seat arms BEFORE it wakes the harness ──────────────────
            pane2 = tmux("split-window", "-d", "-t", pane, "-c", str(pkg),
                         "-P", "-F", "#{pane_id}").stdout.strip()
            seen = {}
            real_wake = coord.wake
            real_arm = coord.start_pane_capture
            armed = []

            def spy_arm(pane_id, logpath):
                armed.append(str(logpath))
                return real_arm(pane_id, logpath)

            def stub_wake(p, cmd):
                # 7.717: prove the ORDER deterministically. `launch_seat` calls
                # `start_pane_capture` BEFORE `wake`, so snapshot what it armed by the time wake
                # fires. Globbing the FS for transcript.log here raced `tmux pipe-pane`'s async
                # `cat >> file` shell — the file is created AFTER the arm call returns, and under
                # box load that spawn lags past this point, emptying the glob and reddening
                # P5b/P5c/P3c even though the arm, the marker and the substrate log are all fine.
                seen["armed_at_wake"] = list(armed)
                return True, ""

            w = {"agent": "beta", "harness": "claude", "model": "opus", "effort": "medium",
                 "cwd": str(pkg / "seats" / "beta"), "window": False,
                 "folder": pkg / "seats" / "beta",
                 "briefing": str(pkg / "seats" / "beta" / "seat.md"),
                 "ephemeral": False, "mechanical_close": False}
            (pkg / "seats" / "beta" / "seat.md").write_text("probe seat\n", encoding="utf-8")
            import argparse
            la = argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                    as_agent=None, force=True)
            coord.wake = stub_wake
            coord.start_pane_capture = spy_arm
            real_up, real_rename = coord.wait_harness_up, coord.schedule_session_rename
            coord.wait_harness_up = lambda p: (None, "")
            coord.schedule_session_rename = lambda p, a: None
            try:
                lpane, lerr = coord.launch_seat(w, la, pane2, pane=pane2)
            finally:
                coord.wake, coord.wait_harness_up = real_wake, real_up
                coord.schedule_session_rename = real_rename
                coord.start_pane_capture = real_arm
            check("P5a `launch_seat` returned without error on the stubbed harness", lerr == "",
                  lerr)
            aw = seen.get("armed_at_wake") or []
            beta_dir = pkg / "seats" / "beta"
            check("P5b ⚠ CAPTURE STARTS IN THE SAME STEP THAT COMPOSES THE PANE COMMAND: "
                  "`launch_seat` ARMED the transcript pipe for this seat BEFORE it called `wake` "
                  "— a later pass would have armed nothing by this point",
                  len(aw) == 1 and beta_dir in Path(aw[0]).parents, repr(seen))
            hdr, rows = coord.read_csv_table(coord.sessions_csv(pkg), coord.SESSIONS_COLS)
            ix = {c: i for i, c in enumerate(hdr)}
            brow = [r for r in rows if coord.pad_row(r, hdr)[ix["seat"]] == "beta"]
            check("P5c the launch wrote ONE session row for the seat and its `recorded` marker "
                  "names the very file the pipe was armed on — written at BIRTH, by the launch, "
                  "with nobody invoking a writer by hand",
                  len(brow) == 1
                  and brow[0][ix["recorded"]] in aw,
                  brow[0][ix["recorded"]] if brow else "(no row)")
            check("P5d the marker RESOLVES through the module's own resolver for that row's "
                  "session-id — the trace points at the transcript, and no second index exists",
                  len(brow) == 1
                  and Path(brow[0][ix["recorded"]])
                  == spath(pkg, "beta", brow[0][ix["session-id"]]))

            # ── P4 — the marker on a directly-driven session row ──────────────────────────────
            seat4 = {"agent": "alpha", "harness": "claude", "model": "opus", "effort": "medium",
                     "cwd": str(pkg / "seats" / "alpha"), "window": False,
                     "folder": pkg / "seats" / "alpha"}
            sid4, _note = coord.session_open(la, seat4, since=time.time(), wait=0.0,
                                             session_id=sid, recorded=str(tpath))
            hdr, rows = coord.read_csv_table(coord.sessions_csv(pkg), coord.SESSIONS_COLS)
            ix = {c: i for i, c in enumerate(hdr)}
            arow = [r for r in rows if coord.pad_row(r, hdr)[ix["seat"]] == "alpha"][0]
            check("P4a the row keeps the id minted at pane BIRTH, so the marker cannot drift from "
                  "the folder the pipe is writing into", sid4 == sid, f"{sid4} vs {sid}")
            check("P4b `recorded` is the transcript path — no longer the empty cell 7.37 left "
                  "behind", arow[ix["recorded"]] == str(tpath), arow[ix["recorded"]])
            check("P4c CONTROL — a session opened with NO capture armed still leaves the cell "
                  "BLANK: the writer names a file nothing writes only when one exists",
                  coord.session_open(la, seat4, since=time.time(), wait=0.0) and
                  [coord.pad_row(r, hdr)[ix["recorded"]] for r in
                   coord.read_csv_table(coord.sessions_csv(pkg), coord.SESSIONS_COLS)[1]
                   if coord.pad_row(r, hdr)[ix["seat"]] == "alpha"][-1] == "")

            # ── P3 — THE KILL ARM ─────────────────────────────────────────────────────────────
            before = tpath.read_text(errors="replace")
            tmux("kill-server")
            time.sleep(1.0)
            gone = subprocess.run(TMUX + ["has-session", "-t", room],
                                  capture_output=True, timeout=20).returncode != 0
            check("P3a the tmux server is GONE — the arm is a real kill, not a detach", gone)
            after = tpath.read_text(errors="replace") if tpath.exists() else ""
            check("P3b ⚠⚠ THE CRITERION: killing the tmux server mid-run leaves a NON-EMPTY log on "
                  "disk for the seat that had produced output. Scrollback died with the server; "
                  "the substrate-level backup did not",
                  tpath.exists() and after.strip() != "" and MARK in after,
                  f"{len(after)} bytes after kill (was {len(before)})")
            btrans = [Path(f) for f in aw]
            check("P3c the SECOND seat's transcript survived the same kill — the property is the "
                  "launch step's, not one hand-armed pane's",
                  bool(btrans) and all(p.exists() for p in btrans),
                  repr([str(p) for p in btrans]))
        finally:
            subprocess.run(TMUX + ["kill-server"], capture_output=True)
    return finish()


def finish():
    tail = (f"\nprobe-731: {checks - len(failures)}/{checks} PASS"
            + (f" — {len(failures)} FAILURE(S)" if failures else " — ALL GREEN"))
    print(tail, flush=True)
    OUT.write_text("\n".join(lines) + tail + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

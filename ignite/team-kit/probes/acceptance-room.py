#!/usr/bin/env python3
"""acceptance-room — a THROWAWAY run package with its OWN tmux server, its own stub harnesses, and
a `state.json` produced by a REAL `team_monitor.py` capture against it.

Task `s4-09`. The evidence substrate `s4-10` / `s4-11` / `s4-12` run their Stage 4 acceptance on.
It is a SUBSTRATE, not a probe: it is imported and driven by those tasks. Its own `--selftest`
scores the six controls `s4-09` § Acceptance names, each with a red arm that is really run.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WAY-STATION (role.md §1.1 — the team-kit → ignite boundary). This lives on the RETIRING side
because its SUBJECT is the retiring side: it exercises `coord.py` and `budget.py`,
which is where the Stage 4 revival arm is being built. When revival moves into ignite
(`goal-watcher-job`, CMP-21), THIS FILE MOVES WITH IT — the switch is cheap by construction and
that cheapness is the whole reason building it here is allowed: it takes no path, no constant and
no caller assumption from the kit except the four module paths in KIT_* below, each resolved from
`__file__` and each overridable at construction. Nothing imports it; deleting it breaks nothing.
Superseded by: whatever acceptance substrate the ignite-side revival component ships.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TERMINOLOGY (PRIN-10, and this is not pedantry). `harness` is a SETTLED term of this system —
"the software that runs the loop and polices the model's reads/writes" (`sd-graph show harness`):
Claude Code, Codex, OpenCode. The stub executables this module puts on PATH ARE harnesses in that
exact sense, which is why `is_harness_argv` and `ctx_monitor.HARNESSES` match them. This MODULE is
NOT one, so it is not called one anywhere in its own surface — it is a ROOM (build vocabulary,
resolves to no KG record, already used by `ignite/jobs/recover-room.py`). The `s4-09` task text
calls the deliverable "the acceptance harness"; that is build-ledger wording, and adopting it in
code would have put a second meaning on a term that has one.

──────────────────────────────── ISOLATION — read this before editing ─────────────────────────

The room runs on a PRIVATE TMUX SERVER, reached by a private `TMUX_TMPDIR`, not by `-L` alone.
This is a DELIBERATE SUBSTITUTION for the `tmux -L <socket>` form the task text specifies, and it
is stronger on both axes that matter:

  1. `-L` alone does NOT isolate the children. `team_monitor.py` inherits the room's raw-pane
     reading from `ctx_monitor.py`, which shells out to BARE `tmux` (`ctx_monitor.py:512`,
     `:605`) and exposes no socket parameter. A session created with `tmux -L wt-revival-x` is
     therefore INVISIBLE to the real sensor — which would make the `s4-09` §1 bar ("a state.json
     produced by a real team_monitor.py") unmeetable, and would push the work back onto the
     hand-authored snapshot that same bar forbids. Measured, not assumed.
  2. `TMUX_TMPDIR` also closes the hazard `-L` leaves open. `recover-room.py:12-19` records that
     with `TMUX`/`TMUX_PANE` unset, tmux resolves an EMPTY target to the most recent session —
     measured, it answered `build-core-daemon-mvp`, the LIVE room. Under `-L`, a bare `tmux`
     command (one that forgot the flag) still reaches the live server. Under a private
     `TMUX_TMPDIR`, a bare `tmux` command can only reach a socket inside this room's own
     directory; the live server is not addressable from this environment at all.

  3. ⚠ AND THAT LAST CLAUSE HOLDS ONLY BECAUSE `env()` POPS `TMUX`. The pop is NOT a redundant
     second layer behind the private server — the pop is what makes `TMUX_TMPDIR` work AT ALL.
     `TMUX` carries a socket PATH, so a client that finds `TMUX` in its environment connects
     THERE and never consults `TMUX_TMPDIR`. MEASURED 2026-07-29, on two throwaway private
     servers so the live one was never touched: with `TMUX` naming server A and `TMUX_TMPDIR`
     naming server B's directory, `tmux display-message -p '#{socket_path}'` answered A's socket,
     and a bare `tmux new-window` LANDED ON A; with `TMUX` popped and nothing else changed, the
     same command answered B's socket.
     THE CONSEQUENCE, which is the reason this point exists: a fixture that builds its environment
     BY HAND and forgets to pop `TMUX` acts on the LIVE tmux server while every isolation check it
     runs reads GREEN — `TMUX_TMPDIR` being SET is not evidence that it took effect, and
     `#{socket_path}` is the only thing that is. Two read-only diagnostics did exactly that during
     the B4 acceptance batch, 2026-07-29. `env()` below is the ONLY sanctioned builder of this
     room's environment, and this is the property it holds that hand-rolling loses first.

So: socket directory `<tmpdir>/tt/tmux-<uid>/`, socket name `default` (the name a child's bare
`tmux` resolves to — that is the point), session `wt-revival-<stamp>`, and the WHOLE directory is
removed at teardown. `TMUX_TMPDIR` is not in `coord.py`'s `LIFECYCLE_SCRUB_ENV`
(`coord.py:3990`), so it survives into every subprocess the room starts, including a detached
lifecycle executor. ⚠ IF A FUTURE CALLER HANDS `Popen` AN ALLOWLIST `env=`, `TMUX_TMPDIR` MUST BE
IN IT — otherwise that child silently reaches the LIVE server.

`HOME` is redirected into the room too — and that is a SAFETY property, not hygiene. MEASURED
2026-07-29, and it is the trap this fixture class is born into: tmux starts each pane's shell as a
LOGIN shell, which sources `~/.profile` / `~/.bashrc`, which PREPENDS `$HOME/.local/bin` to PATH —
ahead of the room's stub directory. `/home/henri/.local/bin/claude` is the REAL Claude Code. With
the real `HOME`, a room that believed it was launching a stub launched a REAL HARNESS: `ps` showed
`comm=claude args=claude`, and the "no model, no cost" bar of `s4-09` was silently false while
every check stayed green. `open_seat` therefore does not trust the redirect either — it ASSERTS
that the process it started is executing from inside this room's own bin (`_assert_stub`).

A second consequence of the redirect, stated because it looks like a defect otherwise:
`ctx_monitor` finds no harness transcripts under the redirected `HOME`, so every seat's `ctx_pct`
is `None`. That is correct — a stub harness has no transcript.

──────────────────────────────── CONCURRENCY — the s4-10/11/12 contract ───────────────────────

`s4-10`, `s4-11` and `s4-12` are mutually unordered in the DAG, and they MAY RUN CONCURRENTLY
against this module. Safety is by CONSTRUCTION, not by convention: every `AcceptanceRoom()` mints
its own stamp (pid + monotonic clock) and therefore its own tmpdir, its own tmux server, its own
package, its own `budget.json`, its own `HOME` and its own stub PATH. Two rooms share NOTHING that
either writes.

THE ONE EXCEPTION, named rather than buried: `leak_check()` compares the LIVE default socket's
full inventory before/after, so two runs doing that at the same instant would each see the other's
(unrelated) churn. Consumers wanting a concurrency-safe isolation assertion call
`leak_scan()` instead — it is stamp-scoped and cannot see another room. `--selftest` uses the full
comparison AND creates a deliberately-stray session on the default socket for its red arm, so
**`--selftest` must not be run concurrently with another `--selftest`**. Consumer runs have no
such restriction.

──────────────────────────────── USE ──────────────────────────────────────────────────────────

  python3 /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit/probes/acceptance-room.py --selftest

  # from a consumer task (the filename has a hyphen, so import it by path — the pattern
  # team_monitor.py itself uses for ctx_monitor):
  import importlib.util
  P = "/home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit/probes/acceptance-room.py"
  spec = importlib.util.spec_from_file_location("acceptance_room", P)
  ar = importlib.util.module_from_spec(spec); spec.loader.exec_module(ar)

  with ar.AcceptanceRoom() as room:              # teardown is in a finally, always
      room.open_seat("s-int-claude")             # stub harness in its own window
      snap = room.capture()                      # REAL team_monitor.py capture
      pid = room.harness_pid("s-int-claude")
      room.kill_harness("s-int-claude")          # kill -9, pid read from the SNAPSHOT
      snap = room.capture()                      # roster_absent is now non-empty
      room.set_floor(99999999)                   # budget.json floors.launch_refuse_mb
      room.age(300)                              # captured_at only, on a real capture

Every subprocess helper runs under `room.env()`: `TMUX`, `TMUX_PANE`, `COORD_AGENT` and
`COORD_LAUNCH_TARGET` are removed, `TMUX_TMPDIR`/`HOME` are redirected, and the stub bin is
prepended to `PATH`. Never build the environment by hand.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent                                     # ignite/team-kit
KIT_COORD = KIT / "coord.py"
KIT_BUDGET = KIT / "budget.py"
KIT_MONITOR = (KIT.parent.parent / "orchestration" / "cli" / "team-monitor" / "team_monitor.py")

# ── The stub harness, and why it is shaped like this. Every clause below is a MEASUREMENT. ─────
#
# FOUR consumers read a running harness, by FOUR different means, and a stub has to satisfy all
# four or some check downstream goes vacuously green:
#
#   ctx_monitor.pane_records  `pane_current_command` — tmux reads /proc/<fg-pgrp>/cmdline and takes
#                             argv[0]'s BASENAME. A plain `#!/bin/bash` script named `claude` has
#                             argv[0] == "/bin/bash", so tmux reports "bash", the pane is
#                             classified as a SHELL, and the seat's `harness` field comes back "".
#   team_monitor.capture      `comm` from ps — the exec'd FILE's basename. A bash COPY named
#                             `claude` gives comm "claude"; a symlink to bash gives "bash".
#   coord.py is_harness_argv  argv[0] basename, then argv[1:4] (`coord.py:1536`).
#   the room itself           it must accept ARBITRARY FLAGS, because a consumer driving
#                             `coordinate launch` starts it as `claude --model … --permission-mode …`
#                             and a stub that exits on an unknown option is a harness that "died".
#
# The shape that satisfies all four: a bash COPY at `bin/.hb/<name>` used as the SHEBANG
# INTERPRETER of a script at `bin/<name>`. The kernel then execs the copy, so `comm` is the
# harness name; argv[0] is the copy's path, so tmux reports the harness name; the script body
# runs, so flags are ignored; and `read -t` is a builtin, so there is NO CHILD PROCESS and the
# foreground process group is the stub itself.
# ⚠ THE EMPTY-INPUT REFUSAL (2026-08-12, IPH-24). This stub shape used to exist in THREE copies, and
# the standing trigger on them said to revisit unification on the first DIVERGENCE. It never fired:
# the guard landed in all three in ONE commit (`02141759`), and the other two copies —
# `goal-creation-request/probes/probe-planning-entry.py` and `probe-sensor-start.py` — were DELETED
# outright hours later by the goal-creation-request rework, taking their `make_shims` with them.
# THIS IS NOW THE ONLY COPY, so the trigger has nothing left to compare against; if a second copy is
# ever cut again, re-arm it there and keep the two byte-identical.
#
# WHY IT EXISTS: until now the stub ignored argv entirely and accepted a launch line the REAL binary
# REFUSES, so a 177-check suite stayed green while every real daemon-lane seat died on empty input.
# Measured on this box 2026-08-12 — `claude --model M </dev/null` and `claude -p --model M "" </dev/null`
# BOTH print the line below and exit 1. AN OPERAND is a non-empty argument that is neither a flag NOR
# a flag's value, so `--model M` and `--effort high` are never mistaken for a turn.
#
# ⚠⚠ THE `-p` GATE IS NOT HOUSE STYLE — IT IS A MEASUREMENT, AND `open_seat` BELOW IS WHAT FORCED IT.
# The guard was written UNGATED first, on the reasoning that the real binary refuses without `-p`
# too and that this lane never composes a promptless launch. THE SECOND HALF IS FALSE, and this file
# is where it is false: `open_seat` starts a seat with `send-keys <harness> Enter` — the BARE binary
# name, no arguments, on a pane TTY. Measured on a real pty, 2026-08-12:
#
#   the REAL binary, bare, stdin = pty  ->  opens its REPL and WAITS (no error, still alive at 8 s)
#   the ungated stub, bare, stdin = pty  ->  refused, exit 1
#
# So ungated the stub was STRICTER THAN THE THING IT IMPERSONATES, and `open_seat`'s 20 s wait for
# `pane_current_command == <harness>` would have raised `RoomError` on every seat this room opens.
# The `-p` gate is the ruled fallback for exactly that finding.
# ⚠ KNOWN AND ACCEPTED CONSEQUENCE: `-p` never appears in a tmux-lane launch, so this guard is INERT
# in all three probes that carry it — it bites only the daemon/stdin lane's shape. That is the cost
# of not breaking `open_seat`; a guard that fires here cannot also let a bare TTY launch live.
# ponytail: the prev-token rule stands in for claude's real flag table. Two known ceilings, neither
# reachable from `harness_command`: a BOOLEAN flag placed immediately before the prompt reads as its
# value, and a subcommand-first line (`opencode run … P`) reads the subcommand as the operand.
# Upgrade to an explicit value-taking-flag list if either shape ever gets composed.
STUB_GUARD = ('op=; pf=0; pr=\n'
              'for a in "$@"; do\n'
              '  case $a in\n'
              '    -p|--print) pr=1; pf=1 ;;\n'
              '    -*) pf=1 ;;\n'
              '    "") pf=0 ;;\n'
              '    *) [ "$pf" = 0 ] && op=1\n'
              '       pf=0 ;;\n'
              '  esac\n'
              'done\n'
              'if [ -n "$pr" ] && [ -z "$op" ] && ! read -rt 1 _; then\n'
              '  echo "Error: Input must be provided either through stdin or as a prompt argument'
              ' when using --print" >&2\n'
              '  exit 1\n'
              'fi\n')

STUB_BODY = ("#!{interp}\n"
             "# stub harness for acceptance-room — no model, no network, no cost.\n"
             "# Flags are ignored (a launcher may pass --model/--permission-mode), but an argv\n"
             "# carrying NO user turn is REFUSED exactly as the real binary refuses it.\n"
             + STUB_GUARD +
             "while :; do read -rt 3600 _ || true; done\n")

# The seat set `s4-09` §3 requires. `mode:` is Stage 3/4 vocabulary the descriptor declares and
# `s4-10`'s mode gate reads; the no-`mode:` seat is `s4-04` control 4's subject and its ABSENCE is
# the whole point — never give it a default here.
DEFAULT_SEATS = (
    {"seat": "s-int-claude", "harness": "claude", "mode": "interactive"},
    {"seat": "s-oneshot-claude", "harness": "claude", "mode": "one-shot"},
    {"seat": "s-int-opencode", "harness": "opencode", "mode": "interactive"},
    {"seat": "s-nomode", "harness": "claude", "mode": None},
)

WORKERS_HEADER = (
    "# workers — agent sessions (script-managed, do not edit by hand)\n\n"
    "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
    "|-------|--------|-----------|------------|------------|-------------|-----------|\n"
)

# Fields ONLY a real team_monitor.py capture writes. `writer_pid`/`written_at*` are stamped by
# write_snapshot (team_monitor.py:668-674); `sensor` and `captured_at_iso` by capture()
# (:581-586). A hand-authored snapshot has to forge all four AND keep written_at != captured_at.
REAL_SNAPSHOT_FIELDS = ("writer_pid", "captured_at", "captured_at_iso",
                        "written_at", "written_at_iso", "sensor", "schema")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RoomError(RuntimeError):
    """Anything the room could not do. Loud by construction (R-8): never swallowed, never a
    warning, and every message names the command whose output produced it."""


class AcceptanceRoom:
    """One throwaway room. Use as a context manager — teardown lives in `__exit__`, which runs on
    the exception path too, which is the whole of acceptance control 4."""

    def __init__(self, stamp=None, seats=DEFAULT_SEATS, base="/tmp"):
        # Short by necessity, not by taste: the tmux socket path is a unix socket and the kernel
        # caps it at ~108 bytes. A stamp under the session-scratch directory (~90 chars) already
        # overflows it — measured, `error connecting to ... (File name too long)`.
        self.stamp = stamp or f"{os.getpid()}-{int(time.monotonic() * 1000) % 1000000}"
        self.session = f"wt-revival-{self.stamp}"
        self.tmp = Path(base) / f"accroom-{self.stamp}"
        self.goal = self.tmp / "goals" / self.session
        self.pkg = self.goal / "runs" / "run-1"
        self.bin = self.tmp / "bin"
        self.home = self.tmp / "home"
        self.tmuxtmp = self.tmp / "tt"
        self.seats = [dict(s) for s in seats]
        self._up = False

    # ---------- environment ----------

    def env(self, extra=None):
        """The hermetic environment. Every subprocess this room starts uses it, and nothing else
        may build one by hand — the four popped names are what let an inherited pane act as
        somebody else (`coord.py:3990` LIFECYCLE_SCRUB_ENV, each consequence measured there)."""
        e = dict(os.environ)
        for v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET"):
            e.pop(v, None)
        e["TMUX_TMPDIR"] = str(self.tmuxtmp)
        e["HOME"] = str(self.home)
        e["PATH"] = f"{self.bin}:{e.get('PATH', '')}"
        e.update(extra or {})
        return e

    def sh(self, cmd, check=True, timeout=120, env_extra=None, cwd=None):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=self.env(env_extra), cwd=str(cwd) if cwd else None)
        if check and r.returncode != 0:
            raise RoomError(f"{' '.join(str(c) for c in cmd)} -> exit {r.returncode}\n"
                            f"stdout: {r.stdout.strip()}\nstderr: {r.stderr.strip()}")
        return r

    def tmux(self, *args, check=True):
        """tmux against THIS room's private server — private BECAUSE `env()` pops `TMUX` first, not
        merely because `TMUX_TMPDIR` is set (module docstring, ISOLATION point 3: `TMUX` outranks
        `TMUX_TMPDIR`, measured). Every call still names its target explicitly; THAT explicitness
        is the defence in depth here, and the private server is never a licence to omit it."""
        return self.sh(["tmux", *[str(a) for a in args]], check=check)

    # ---------- lifecycle ----------

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, *exc):
        self.teardown()
        return False

    def setup(self):
        for d in (self.bin, self.home, self.tmuxtmp, self.pkg / "coordination",
                  self.pkg / "seats"):
            d.mkdir(parents=True, exist_ok=True)
        self.tmuxtmp.chmod(0o700)

        hb = self.bin / ".hb"
        hb.mkdir(parents=True, exist_ok=True)
        for name in ("claude", "opencode"):
            interp = hb / name
            shutil.copy2("/bin/bash", interp)
            interp.chmod(0o755)
            p = self.bin / name
            p.write_text(STUB_BODY.format(interp=interp), encoding="utf-8")
            p.chmod(0o755)

        (self.pkg / "coordination" / "workers.md").write_text(WORKERS_HEADER, encoding="utf-8")
        (self.pkg / "coordination" / "messages.md").write_text(
            "# messages — throwaway acceptance room\n\n", encoding="utf-8")
        (self.pkg / "coordination" / "injections.log").write_text("", encoding="utf-8")
        (self.pkg / "seed.md").write_text(
            f"# {self.session} — throwaway acceptance room (s4-09). Deleted at teardown.\n",
            encoding="utf-8")

        rows = ["taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id"]
        for s in self.seats:
            self._write_descriptor(s)
            rows.append(f"tf-acc,{s['seat']},,{s['harness']},stub-model,medium,40,acc")
        (self.pkg / "taskforce.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

        self.set_floor(2000)
        self.tmux("new-session", "-d", "-s", self.session, "-n", "room")
        self._up = True
        return self

    def _write_descriptor(self, s):
        d = self.pkg / "seats" / s["seat"]
        d.mkdir(parents=True, exist_ok=True)
        fm = [f"seat: {s['seat']}",
              f"description: acceptance-room stub seat ({s['harness']})",
              f"cwd: {d}",
              f"harness: {s['harness']}",
              "model: stub-model",
              "effort: medium",
              "agent_type: worker",
              "ctx-refresh: 40"]
        if s.get("mode") is not None:
            fm.append(f"mode: {s['mode']}")
        (d / "seat.md").write_text("---\n" + "\n".join(fm) + "\n---\n\n"
                                   "Stub seat. No agent ever reads this; the executable on PATH "
                                   "is a `read -t` loop.\n", encoding="utf-8")

    def teardown(self):
        """Unconditional. Kills the private server's session BY EXPLICIT TARGET, then removes the
        whole tree. Never `kill-server`, never an empty target."""
        errs = []
        if self._up:
            try:
                self.tmux("kill-session", "-t", self.session, check=False)
            except Exception as e:                              # noqa: BLE001 — teardown is total
                errs.append(f"kill-session: {e}")
        try:
            shutil.rmtree(self.tmp, ignore_errors=True)
        except Exception as e:                                  # noqa: BLE001
            errs.append(f"rmtree: {e}")
        self._up = False
        if errs:
            raise RoomError("teardown incomplete: " + "; ".join(errs))

    def alive(self):
        """(session_present, tmpdir_present) — the leak detector control 4 scores."""
        r = self.sh(["tmux", "has-session", "-t", self.session], check=False, timeout=20)
        return r.returncode == 0, self.tmp.exists()

    # ---------- seats ----------

    def open_seat(self, seat, active=True):
        """Open one window on the private server, start the seat's stub harness in it, register
        the roster row, and return the pane id.

        The pane runs a SHELL and the harness is a child of it — the shape `coord.py`'s own launch
        produces. It is what makes the post-kill state observable: kill the harness and the pane
        SURVIVES as a shell, which is `absent_rows`' second and more dangerous case ("pane present
        but no harness", team_monitor.py `absent_rows`) rather than the trivial vanished-pane one.
        """
        s = self._seat(seat)
        pane = self.tmux("new-window", "-d", "-t", f"{self.session}:", "-n", seat,
                         "-c", str(self.pkg / "seats" / seat),
                         "-P", "-F", "#{pane_id}").stdout.strip()
        if not pane.startswith("%"):
            raise RoomError(f"new-window returned no pane id for {seat}: {pane!r}")
        self.tmux("send-keys", "-t", pane, s["harness"], "Enter")
        deadline = time.time() + 20
        while time.time() < deadline:
            cmd = self.tmux("list-panes", "-t", pane, "-F",
                            "#{pane_current_command}").stdout.strip()
            if cmd == s["harness"]:
                break
            time.sleep(0.2)
        else:
            raise RoomError(f"stub harness {s['harness']} never became the foreground command in "
                            f"{pane} for seat {seat}")
        self._assert_stub(pane, s["harness"], seat)
        s["pane"] = pane
        self._roster_row(seat, pane, active)
        return pane

    def _assert_stub(self, pane, harness, seat):
        """The "no model, no cost" bar, ASSERTED rather than assumed.

        The PATH prepend is not enough on its own and this is measured, not defensive: the pane's
        LOGIN shell sources the profile, which prepends `$HOME/.local/bin`, where a REAL harness
        lives. A room that only prepended PATH launched the real Claude Code and every check
        stayed green. So: the process now running under this pane MUST be executing from inside
        this room's own bin, or the seat does not open."""
        root = int(self.tmux("list-panes", "-t", pane, "-F", "#{pane_pid}").stdout.strip())
        rows = subprocess.run(["ps", "-eo", "pid=,ppid=,comm=,args="],
                              capture_output=True, text=True, timeout=30).stdout.splitlines()
        for ln in rows:
            parts = ln.split(None, 3)
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            if int(parts[1]) == root and parts[2] == harness:
                if str(self.bin) in parts[3]:
                    return parts[3]
                raise RoomError(
                    f"REFUSING {seat}: the process claiming to be `{harness}` under {pane} is NOT "
                    f"this room's stub — it runs `{parts[3]}`. A real harness was about to be "
                    f"driven by an acceptance fixture. Check that HOME is redirected and that the "
                    f"room's bin is first on PATH.")
        raise RoomError(f"no `{harness}` process under {pane} for {seat} after it became the "
                        f"foreground command — the stub died on start")

    def _seat(self, seat):
        for s in self.seats:
            if s["seat"] == seat:
                return s
        raise RoomError(f"no such seat in this room: {seat}")

    def _roster_row(self, seat, pane, active):
        wm = self.pkg / "coordination" / "workers.md"
        stamp = time.strftime("%Y-%m-%d %H:%M")
        wm.write_text(wm.read_text(encoding="utf-8") +
                      f"| {seat} | {'yes' if active else 'no'} | {pane} | acceptance room | "
                      f"{stamp} |  | 0 |\n", encoding="utf-8")

    def harness_pid(self, seat):
        """The seat's harness pid READ FROM THE SNAPSHOT — never from a pid this process
        remembered. A remembered pid is a claim about the past; the snapshot is the evidence the
        acceptance is scored on, and if the two ever disagree the snapshot is right."""
        snap = self.snapshot()
        pane = self._seat(seat).get("pane")
        for row in snap.get("seats") or []:
            if row.get("pane") == pane:
                return row.get("harness_pid")
        return None

    def kill_harness(self, seat, sig=signal.SIGKILL):
        pid = self.harness_pid(seat)
        if not pid:
            raise RoomError(f"no harness pid in the snapshot for {seat} — nothing to kill; "
                            f"capture() first, and check the seat is open")
        os.kill(pid, sig)
        deadline = time.time() + 10
        while time.time() < deadline:
            if not Path(f"/proc/{pid}").exists():
                return pid
            time.sleep(0.1)
        raise RoomError(f"pid {pid} survived {sig!r} for 10s")

    # ---------- the snapshot ----------

    def capture(self):
        """One REAL `team_monitor.py once` against this room's private session. Writes
        `state.json` at the package root and returns it."""
        self.sh([sys.executable, str(KIT_MONITOR), "once",
                 "--package", str(self.pkg), "--session", self.session], timeout=180)
        return self.snapshot()

    def snapshot(self):
        p = self.pkg / "state.json"
        if not p.exists():
            raise RoomError(f"no snapshot at {p} — capture() first")
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def snapshot_is_real(snap):
        """(ok, why). The 'not hand-authored' gate: every field only a real capture writes, plus
        the one relation a forger has to get right — team_monitor stamps written_at SEPARATELY and
        NEVER re-stamps captured_at (team_monitor.py:17-18, :668), so the two are never equal."""
        missing = [f for f in REAL_SNAPSHOT_FIELDS if f not in snap]
        if missing:
            return False, f"missing fields only a real capture writes: {missing}"
        if snap.get("written_at") == snap.get("captured_at"):
            return False, "written_at == captured_at — no real capture produces that"
        if not str(snap.get("sensor", "")).endswith("ctx_monitor.py"):
            return False, f"sensor is not the inherited raw sensor: {snap.get('sensor')!r}"
        return True, "real capture"

    def age(self, seconds):
        """Push a REAL capture's `captured_at` back by `seconds`. Only the two capture stamps move;
        every other field stays exactly as the sensor wrote it.

        Stated rather than implied, because `team_monitor.py:17-18` promises it NEVER re-stamps
        `captured_at`: the re-stamp is done HERE, by this room, deliberately, and it leaves
        `_aged_by_acceptance_room` in the file so no reader can mistake an aged snapshot for a
        naturally stale one."""
        snap = self.snapshot()
        ok, why = self.snapshot_is_real(snap)
        if not ok:
            raise RoomError(f"refusing to age a snapshot that is not a real capture: {why}")
        orig = snap["captured_at"]
        snap["captured_at"] = round(orig - float(seconds), 3)
        snap["captured_at_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime(snap["captured_at"]))
        snap["_aged_by_acceptance_room"] = {"seconds": seconds, "original_captured_at": orig,
                                            "why": "s4-09 §3 snapshot ageing — the sensor never "
                                                   "re-stamps captured_at, so the room does"}
        (self.pkg / "state.json").write_text(json.dumps(snap, indent=1), encoding="utf-8")
        return snap

    def census(self):
        """`budget.census` over THIS room's budget.json + state.json. The `stale` verdict
        (`budget.py` STALE_AFTER_S = 120) is what `check_revival` freezes its debounce counters
        on, so a consumer that never checks it can be proving nothing."""
        budget = _load(KIT_BUDGET, "budget")
        return budget.census(json.loads((self.pkg / "budget.json").read_text(encoding="utf-8")),
                             self.snapshot())

    # ---------- policy + actuation ----------

    def set_floor(self, mb):
        """Write `floors.launch_refuse_mb`. R-10 (`r-floor-single-source`): the number reaches
        every consumer through THIS FILE, never through argv."""
        p = self.pkg / "budget.json"
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
            "schema": "run-budget/1",
            "_readme": "throwaway acceptance room (s4-09) — never the live run's budget",
            "cap": {"agent_panes": 10},
            "counting": {"counts_toward_cap": ["staff", "worker", "verifier"]},
        }
        doc.setdefault("floors", {})
        doc["floors"]["launch_refuse_mb"] = mb
        doc["floors"].setdefault("pressure_warn_mb", mb)
        p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    def coord(self, *args, check=False, timeout=180):
        return self.sh([sys.executable, str(KIT_COORD), "--package", str(self.pkg), *args],
                       check=check, timeout=timeout)

    # ---------- proofs ----------

    def no_agent_proof(self, pid):
        """Evidence that whatever ran at `pid` had NO agent in its path.

        Three independent readings, because each alone is defeatable: the /proc ppid ancestry (an
        agent would appear as a harness process above it), this room's `messages.md` (an agent
        acting would have posted), and `injections.log` (an agent would have been prompted)."""
        chain, cur, seen = [], int(pid), set()
        while cur and cur > 1 and cur not in seen:
            seen.add(cur)
            try:
                stat = Path(f"/proc/{cur}/stat").read_text(encoding="utf-8", errors="replace")
                comm = stat[stat.find("(") + 1:stat.rfind(")")]
                ppid = int(stat[stat.rfind(")") + 1:].split()[1])
                argv = Path(f"/proc/{cur}/cmdline").read_bytes().replace(b"\0", b" ").decode(
                    "utf-8", "replace").strip()
            except (OSError, ValueError, IndexError):
                break
            chain.append({"pid": cur, "comm": comm, "argv": argv})
            cur = ppid
        harnesses = {"claude", "codex", "opencode", "kimi", "gemini", "aider", "goose", "amp"}
        msgs = (self.pkg / "coordination" / "messages.md").read_text(encoding="utf-8")
        inj = (self.pkg / "coordination" / "injections.log").read_text(encoding="utf-8")
        return {
            "ancestry": chain,
            "harness_in_ancestry": [c for c in chain if c["comm"] in harnesses],
            "message_rows": len([ln for ln in msgs.splitlines() if ln.startswith("#")]),
            "injection_lines": len([ln for ln in inj.splitlines() if ln.strip()]),
        }

    # ---------- isolation ----------

    @staticmethod
    def default_socket_inventory():
        """The LIVE default socket's full session/window/pane inventory, or the explicit
        no-server case. Volatile per-pane fields (title, activity, current command) are excluded
        on purpose: they change under an unrelated agent's keystrokes, and a control that goes red
        on somebody else's typing is noise, not evidence."""
        e = dict(os.environ)
        for v in ("TMUX", "TMUX_PANE", "TMUX_TMPDIR"):
            e.pop(v, None)
        r = subprocess.run(
            ["tmux", "list-panes", "-a", "-F",
             "#{session_name}\t#{window_index}\t#{window_name}\t#{pane_id}\t#{pane_pid}"],
            capture_output=True, text=True, env=e, timeout=30)
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            if "no server running" in err or "error connecting" in err:
                return "NO-SERVER: the default socket has no tmux server and therefore no sessions"
            raise RoomError(f"could not read the default socket inventory: {err}")
        return "\n".join(sorted(r.stdout.splitlines()))

    def leak_scan(self):
        """Concurrency-safe isolation assertion: this room's stamp appears NOWHERE on the live
        default socket. Two rooms running at once cannot see each other through it."""
        inv = self.default_socket_inventory()
        hits = [ln for ln in inv.splitlines() if self.stamp in ln or "wt-revival" in ln]
        return (not hits), hits

    @staticmethod
    def leak_check(before, after):
        """(ok, diff). Full before/after equality — the strong form, and NOT concurrency-safe:
        another room's `--selftest`, or a human opening a window, moves it."""
        if before == after:
            return True, []
        b, a = set(before.splitlines()), set(after.splitlines())
        return False, sorted([f"+ {x}" for x in a - b] + [f"- {x}" for x in b - a])


# ══════════════════════════════ the six controls, each with a red arm ═════════════════════════

def _selftest():
    failures, names = [], []

    def check(name, cond, note=""):
        print(("ok  " if cond else "FAIL") + f"  {name}" + (f"\n        {note}" if note else ""))
        names.append(name)
        if not cond:
            failures.append(name)

    print("acceptance-room selftest — s4-09 §Acceptance, six controls, every red arm really run\n")

    # ---- 6 first: the two suites the room must not have broken, and they take the longest. ----
    #
    # THE INVOCATION SHAPE IS LOAD-BEARING, and getting it wrong is a green-looking red:
    # `coord.py` takes a SUBCOMMAND (`coordinate selftest`). `coord.py --selftest` does not run
    # the suite at all — argparse refuses it for a missing <command> and exits 2, which reads as
    # "the suite failed" while nothing ever ran. And `coord.py` must be run from INSIDE the kit
    # (team-kit/CLAUDE.md: it aborts on missing sibling assets otherwise). The sibling
    # `watch.py --selftest` invocation was removed with that file (task 7.35).
    for label, cmd, cwd in (("coord.py selftest", [str(KIT_COORD), "selftest"], KIT),):
        r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, timeout=1800,
                           cwd=str(cwd) if cwd else None)
        tail = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()][-1:] or [""]
        check(f"6. `{label}` exits 0", r.returncode == 0, tail[0])

    before = AcceptanceRoom.default_socket_inventory()
    no_server = before.startswith("NO-SERVER")
    print(f"\n   default socket at start: "
          f"{'NO SERVER — the no-sessions case, recorded explicitly' if no_server else str(len(before.splitlines())) + ' pane row(s)'}")

    room = AcceptanceRoom()
    print(f"   room stamp {room.stamp}   session {room.session}   tmpdir {room.tmp}\n")
    live_positive = None
    try:
        room.setup()
        pane = room.open_seat("s-int-claude")

        # ---- 1. the snapshot is REAL, and the test can tell ----
        snap = room.capture()
        ok, why = AcceptanceRoom.snapshot_is_real(snap)
        check("1. the capture is a REAL team_monitor.py snapshot (writer_pid, captured_at_iso, "
              "written_at_iso, sensor block, written_at != captured_at)", ok, why)
        check("1. the snapshot really describes THIS room",
              snap.get("session") == room.session and snap.get("session_alive") is True
              and any(s.get("pane") == pane for s in snap.get("seats") or []),
              f"session={snap.get('session')} seats={len(snap.get('seats') or [])}")
        # red arm — a hand-authored snapshot MUST be rejected. Without this the "no hand-authored
        # snapshot" bar is a sentence, not a check.
        forged = {"schema": snap["schema"], "captured_at": time.time(),
                  "session": room.session, "seats": snap["seats"], "roster_absent": []}
        red_ok, red_why = AcceptanceRoom.snapshot_is_real(forged)
        check("1. RED ARM — a hand-authored snapshot is REJECTED", red_ok is False, red_why)
        # and the near-miss: every field present, but forged with written_at == captured_at.
        near = dict(snap)
        near["written_at"] = near["captured_at"]
        check("1. RED ARM — a forgery carrying every field but written_at == captured_at is "
              "REJECTED", AcceptanceRoom.snapshot_is_real(near)[0] is False)

        # ---- 2. roster_absent goes non-empty for real ----
        check("2. CONTROL — before the kill, roster_absent is empty",
              (snap.get("roster_absent") or []) == [],
              f"roster_absent={snap.get('roster_absent')}")
        hpid = room.harness_pid("s-int-claude")
        check("2. the seat's harness pid is READ FROM THE SNAPSHOT", bool(hpid), f"pid={hpid}")
        room.kill_harness("s-int-claude")
        after_kill = room.capture()
        absent = after_kill.get("roster_absent") or []
        check("2. after `kill -9`, roster_absent is NON-EMPTY — the goal's first live positive",
              len(absent) >= 1, json.dumps(absent))
        if absent:
            live_positive = absent
            check("2. the absent row is the dangerous case (pane present, harness gone), not the "
                  "trivial vanished-pane one",
                  absent[0].get("liveness") == "no-harness", absent[0].get("reason", ""))

        # ---- 5. ageing works and is honest ----
        check("5. CONTROL — a fresh capture is NOT stale",
              room.census().get("stale") is False, f"snapshot_age_s={room.census().get('snapshot_age_s')}")
        aged = room.age(300)
        check("5. an aged snapshot IS stale to budget.census (STALE_AFTER_S=120)",
              room.census().get("stale") is True,
              f"captured_at moved back {aged['_aged_by_acceptance_room']['seconds']}s")
        check("5. ageing is HONEST — it touched only the capture stamps and said so",
              aged["written_at"] == after_kill["written_at"]
              and aged["writer_pid"] == after_kill["writer_pid"]
              and "_aged_by_acceptance_room" in aged
              and AcceptanceRoom.snapshot_is_real(aged)[0])

        # ---- 3. isolation is proven, not assumed ----
        during = AcceptanceRoom.default_socket_inventory()
        ok3, diff3 = AcceptanceRoom.leak_check(before, during)
        check("3. the LIVE default socket is byte-identical while the room runs"
              + (" (no-server case: the room created no server there either)" if no_server else ""),
              ok3, "\n        ".join(diff3))
        ok_scan, hits = room.leak_scan()
        check("3. no session/window/pane carrying this room's stamp exists on the default socket",
              ok_scan, str(hits))
        # red arm. The arm the task specifies — "run one command with TMUX_PANE inherited" — CANNOT
        # go red here and would have been a vacuous green: under a private TMUX_TMPDIR an inherited
        # TMUX_PANE addresses a pane on a socket that does not exist, so nothing can reach the live
        # server to be detected. SUBSTITUTED with the leak it is actually defending against: a
        # command that lost TMUX_TMPDIR and therefore lands on the live default socket. Uniquely
        # named, created and destroyed by explicit target, never near the live room.
        leak_name = f"accroom-leak-{room.stamp}"
        e = dict(os.environ)
        for v in ("TMUX", "TMUX_PANE", "TMUX_TMPDIR"):
            e.pop(v, None)
        pre = subprocess.run(["tmux", "has-session", "-t", leak_name],
                             capture_output=True, text=True, env=e, timeout=20)
        if pre.returncode == 0:
            check("3. RED ARM — precondition: the leak-probe name is free", False,
                  f"{leak_name} already exists; refusing to touch it")
        else:
            subprocess.run(["tmux", "new-session", "-d", "-s", leak_name, "sleep 60"],
                           capture_output=True, text=True, env=e, timeout=30, check=True)
            try:
                leaked = AcceptanceRoom.default_socket_inventory()
                ok_red, diff_red = AcceptanceRoom.leak_check(before, leaked)
                check("3. RED ARM — a session that leaked onto the live default socket IS "
                      "DETECTED (the isolation check goes RED)", ok_red is False,
                      "\n        ".join(diff_red))
                check("3. RED ARM — and the stamp-scoped scan catches it too",
                      any(leak_name in ln for ln in leaked.splitlines()))
            finally:
                subprocess.run(["tmux", "kill-session", "-t", leak_name],
                               capture_output=True, text=True, env=e, timeout=30)
            restored = AcceptanceRoom.default_socket_inventory()
            ok_rest, diff_rest = AcceptanceRoom.leak_check(before, restored)
            check("3. RED ARM CLEANUP — the live default socket is byte-identical again",
                  ok_rest, "\n        ".join(diff_rest))

        # ---- the "no model, no cost" guard must be able to REFUSE ----
        # `_assert_stub` is what turns "we launched a stub" from a hope into a claim, so it needs
        # its own red arm: a guard that cannot refuse proves nothing, and this one is guarding
        # against a REAL harness being driven by an acceptance fixture (it happened — see the
        # module docstring). The mutation moves the guard's notion of "inside this room" away from
        # the running stub, which is exactly the shape of the failure it exists to catch.
        # A LIVE seat is required — `s-int-claude`'s harness was killed two controls ago, and
        # running the arm against it would have refused for the wrong reason ("no process") while
        # reading like a pass.
        guard_pane = room.open_seat("s-int-opencode")
        real_bin, refused = room.bin, None
        try:
            room.bin = Path("/nowhere/that/is/not/this/room")
            room._assert_stub(guard_pane, "opencode", "s-int-opencode")
        except RoomError as e:
            refused = str(e)
        finally:
            room.bin = real_bin
        check("   (substrate) RED ARM — the anti-real-harness guard REFUSES when the running "
              "process is not this room's stub",
              refused is not None and "REFUSING" in (refused or ""),
              (refused or "the guard did NOT refuse")[:200])
        check("   (substrate) and it ACCEPTS the genuine stub (so the arm proves a DIFFERENCE, "
              "not a blanket refusal)",
              str(room.bin) in room._assert_stub(guard_pane, "opencode", "s-int-opencode"))

        # ---- no-agent proof works on a pid this room owns ----
        proof = room.no_agent_proof(os.getpid())
        check("   (substrate) no_agent_proof walks a real /proc ancestry and reads the room's "
              "messages.md + injections.log",
              len(proof["ancestry"]) >= 1 and proof["message_rows"] == 1
              and proof["injection_lines"] == 0,
              f"ancestry depth {len(proof['ancestry'])}, "
              f"harness_in_ancestry={[c['comm'] for c in proof['harness_in_ancestry']]}")
    finally:
        sess_before_teardown, _ = room.alive()
        room.teardown()

    # ---- 4. teardown is unconditional ----
    tmp_gone = not room.tmp.exists()
    check("4. after teardown the throwaway package is gone", tmp_gone, str(room.tmp))
    check("4. the session existed right up to teardown (so its removal is a real removal, not a "
          "vacuous check on something that was never there)", sess_before_teardown)

    # 4, the exception path: teardown must run when the body raises.
    crash = AcceptanceRoom()
    try:
        with crash:
            crash.open_seat("s-int-opencode")
            raise RuntimeError("deliberate mid-run exception")
    except RuntimeError:
        pass
    sess, tmpd = crash.alive()
    check("4. a mid-run EXCEPTION still tears the room down (session gone, package gone)",
          (not sess) and (not tmpd))

    # 4 red arm: the same room WITHOUT the finally — the leak must be detected.
    leaky = AcceptanceRoom()
    leaky.setup()
    leaky.open_seat("s-int-claude")
    sess_l, tmp_l = leaky.alive()
    check("4. RED ARM — with no teardown the leak IS detected (session and package both still "
          "present)", sess_l and tmp_l)
    leaky.teardown()
    check("4. RED ARM CLEANUP — the leaked room is gone", not any(leaky.alive()))

    final = AcceptanceRoom.default_socket_inventory()
    ok_f, diff_f = AcceptanceRoom.leak_check(before, final)
    check("3. FINAL — the live default socket is byte-identical after every arm", ok_f,
          "\n        ".join(diff_f))

    if live_positive:
        print("\n  ⚑ FIRST LIVE POSITIVE — `roster_absent` observed NON-EMPTY, produced by a real\n"
              "    team_monitor.py capture against a real killed harness. Until now it had only\n"
              "    ever been `[]` in run-2 and the candidate set was verified by code reading:\n"
              f"    {json.dumps(live_positive)}")

    print(f"\n{'PASS' if not failures else 'FAIL'} — {len(names)} check(s), "
          f"{len(failures)} failure(s)")
    for f in failures:
        print(f"  FAILED: {f}")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(
        prog="acceptance-room",
        description="Throwaway acceptance room for the Stage 4 revival controls (s4-09).")
    ap.add_argument("--selftest", action="store_true",
                    help="run the s4-09 acceptance controls, each with its red arm")
    args = ap.parse_args()
    if not args.selftest:
        ap.print_help()
        return 2
    return _selftest()


if __name__ == "__main__":
    sys.exit(main())

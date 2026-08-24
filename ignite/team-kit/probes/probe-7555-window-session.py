#!/usr/bin/env python3
"""probe-7555-window-session.py — task 7.555 (5): a `--tmux-target` naming a WINDOW id still
resolves to the RIGHT session for `ensure_team_monitor`.

WHAT THIS GUARDS, and why it had no guard. Task 7.552 made `cmd_launch` hand the room's session to
the sensor: `ensure_team_monitor(args, session=tmux_session_name(target))`. `target` is whatever
`--tmux-target` carried, and that flag MAY name a WINDOW id (`@N`) rather than a pane id (`%N`).
`tmux_session_name` resolves a session from EITHER, so the shipped fix holds — 7.552's certified
review measured it (`display-message -t @1 '#{session_name}'` -> rc 0, the session name). But
NOTHING PINNED IT. The whole guarantee rests on one format string inside one helper with four
callers, and a future change to that resolution breaks SENSOR START SILENTLY: the launch still
exits 0, still opens its panes, and the room simply runs with no sensor — which is the state whose
capacity term reads `CAP UNENFORCEABLE` and defers every counted candidate. That was 7.552's open
question 2, carried into 7.555 unanswered by anything executable.

⚠ WHY THE END-TO-END ARM IS NOT A RESTATEMENT OF THE UNIT ARM. W1 asks tmux; W2 asks what actually
lands on the sensor's argv. They can disagree, and the way they disagree is the reason W4 exists:
`ensure_team_monitor` carries a COLD-BOOT FALLBACK (`session = session or pkg.name`, 7.607 E4b), so
a resolution that returns EMPTY still produces a plausible-looking `--session` on the wire. An arm
that only asserted "`--session` is present and non-empty" would pass with the resolution completely
broken. W4 measures the fallback's OWN value first, and W2 asserts the wire carries the ROOM name
and NOT that value — which is why the fixture's room name and goal name are deliberately different
strings. A probe whose green survives its subject's removal is not a guard.

THE ARMS.

  W0  fixture integrity — the tmux server is really isolated and carries EXACTLY the two fixture
      rooms. TWO of them, and the ORDER is load-bearing: `roomB` is created LAST, so it is the
      "most recent" session an empty/blank target resolves to (7.552's measured footgun). A
      one-room fixture cannot tell "resolved roomA correctly" from "resolved whatever was there".
  W1  THE UNIT: a WINDOW id (`@N`) resolves to its session — and so does the PANE id (`%N`) of the
      same window, which is the shape the fix was written for. Both asserted, so this cannot pass
      by the two forms having silently collapsed into one.
  W2  THE CALL SITE, END TO END: the value `tmux_session_name(<window id>)` produces is what
      `ensure_team_monitor` puts on `team_monitor.py`'s argv as `--session`.
  W3  RED-FIRST, BY MUTATING THE RESOLUTION: `tmux_session_name` replaced with the plausible wrong
      one — `#{window_name}` instead of `#{session_name}`, the single-token edit most likely to be
      made by accident in this helper — and the wire must NOT then carry the room. If the mutant
      still produces the room name, this probe cannot discriminate and says INOPERATIVE rather than
      reporting a green it did not earn.
  W4  THE DISCRIMINATION FLOOR: the cold-boot fallback's value is measured directly, and it is NOT
      the room name — so W2's green cannot have been produced by the fallback.

⚠ IT NEVER TOUCHES A REAL ROOM. Every tmux command runs against an ISOLATED server (`TMUX_TMPDIR`
redirected into this probe's own temp dir AND `mkdir`ed before the first tmux call — tmux SILENTLY
falls back to the default socket dir when `TMUX_TMPDIR` names a directory that does not exist, and
an "isolated" fixture then drives the box's live rooms; `TMUX`/`TMUX_PANE` unset in the PROCESS
environment so children inherit the isolation). Sessions are `w7555-` prefixed, targeted by name,
and the server is killed at teardown. No sensor is started and no `.rbtv/` path is read or written:
`subprocess.run` is stubbed inside `coord` for the two call-site arms, so `team_monitor.py` never
executes — the argv is the measurement.

Run it through the suite — `node ignite/deploy/probe-suite.js --only 7555-window-session` — never
by hand (`G-163`).
Exit 0 = every arm green · 1 = an arm failed · 2 = INOPERATIVE (the probe could not run at all).
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

KIT = Path(__file__).resolve().parent.parent
MONITOR = KIT.parent.parent / "orchestration" / "team-monitor" / "tool" / "team_monitor.py"
OUT = Path(__file__).resolve().parent / "probe-7555-window-session.out"

lines, failures, inoperative = [], [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    say(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def capture_session(coord, args, session):
    """The argv `ensure_team_monitor` hands `team_monitor.py`, with the child never executed.

    Returns the `--session` operand, or '' when the flag is absent / no call was made. Stubbing
    `coord.subprocess.run` is the same instrument `probe-sensor-cold-boot.py`'s S4 arm uses.
    """
    seen = []
    real_run, real_script = coord.subprocess.run, coord.team_monitor_script
    try:
        coord.subprocess.run = lambda a, *x, **k: (
            seen.append(list(a)) or subprocess.CompletedProcess(a, 0, "", ""))
        coord.team_monitor_script = lambda: MONITOR
        coord.ensure_team_monitor(args, session=session)
    finally:
        coord.subprocess.run = real_run
        coord.team_monitor_script = real_script
    argv = seen[0] if seen else []
    if "--session" not in argv:
        return ""
    return argv[argv.index("--session") + 1]


def main():
    if not (KIT / "coord.py").is_file():
        stop("W0", f"{KIT / 'coord.py'} does not exist — an absent target IS the failure, not a skip")
        return
    if not MONITOR.is_file():
        stop("W0", f"{MONITOR} does not exist — the call site's script target is absent")
        return
    sys.path.insert(0, str(KIT))
    import coord                                                            # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="probe-7555-") as td:
        td = Path(td)
        sock = td / "sock"
        sock.mkdir()                       # BEFORE the first tmux call — the fallback footgun
        os.environ["TMUX_TMPDIR"] = str(sock)
        os.environ.pop("TMUX", None)
        os.environ.pop("TMUX_PANE", None)
        # The room name and the goal name are DELIBERATELY DIFFERENT STRINGS: the goal name is what
        # the cold-boot fallback substitutes, so identical names would make W2 unfalsifiable.
        room_a = f"w7555-roomA{os.getpid()}"
        room_b = f"w7555-roomB{os.getpid()}"
        goal = f"zzgoal{os.getpid()}"
        pkg = td / "ws" / ".rbtv" / "goals" / goal
        (pkg / "coordination").mkdir(parents=True)
        args = type("A", (), {"package": str(pkg), "base": None, "workers_dir": None,
                              "run": None})()
        try:
            made_a = tmux("new-session", "-d", "-s", room_a)
            made_b = tmux("new-session", "-d", "-s", room_b)   # LAST = the "most recent" session
            sessions = sorted(tmux("list-sessions", "-F", "#{session_name}").stdout.split())
            check("W0", made_a.returncode == 0 and made_b.returncode == 0
                  and sessions == sorted([room_a, room_b]),
                  f"the isolated server carries EXACTLY the two fixture rooms "
                  f"(rc={made_a.returncode}/{made_b.returncode}, sessions={sessions}) — a fixture "
                  f"reading the DEFAULT server would drive the box's live rooms, and a ONE-room "
                  f"fixture could not tell a correct resolution from a lucky one")
            if failures:
                return
            win = tmux("list-windows", "-t", room_a, "-F", "#{window_id}").stdout.split()
            pane = tmux("list-panes", "-t", room_a, "-F", "#{pane_id}").stdout.split()
            if not win or not pane:
                stop("W1", f"the fixture room yielded no window/pane id (windows={win}, "
                            f"panes={pane}) — nothing to resolve FROM, so every arm below would be "
                            f"measuring an empty string")
                return
            window_id, pane_id = win[0], pane[0]
            by_window = coord.tmux_session_name(window_id)
            by_pane = coord.tmux_session_name(pane_id)
            check("W1", by_window == room_a and by_pane == room_a,
                  f"a WINDOW id resolves to its own session ({window_id} -> {by_window!r}) and so "
                  f"does the PANE id of that same window ({pane_id} -> {by_pane!r}); expected "
                  f"{room_a!r} for both. `--tmux-target` may carry either form, and 7.552's fix "
                  f"holds only because ONE helper answers both")
            fallback = capture_session(coord, args, "")
            check("W4", fallback == goal and fallback != room_a,
                  f"the cold-boot fallback substitutes the GOAL name ({fallback!r}) when the "
                  f"resolution is empty — measured, not assumed. It is NOT the room name "
                  f"({room_a!r}), which is what makes W2 falsifiable: an arm asserting only that "
                  f"`--session` is present and non-empty would pass with the resolution destroyed")
            on_wire = capture_session(coord, args, coord.tmux_session_name(window_id))
            check("W2", on_wire == room_a,
                  f"the call site carries the WINDOW id's session onto `team_monitor.py`'s argv: "
                  f"--session {on_wire!r} (expected {room_a!r}). This is the sensor's actual "
                  f"input, not tmux's answer restated")
            real = coord.tmux_session_name
            try:
                # THE MUTATION: `#{session_name}` -> `#{window_name}`. One token, inside the one
                # helper, and it is the edit this resolution is most likely to lose to.
                coord.tmux_session_name = lambda t: subprocess.run(
                    ["tmux", "display-message", "-p", "-t", t, "#{window_name}"],
                    capture_output=True, text=True).stdout.strip()
                mutant_unit = coord.tmux_session_name(window_id)
                mutant_wire = capture_session(coord, args, coord.tmux_session_name(window_id))
            finally:
                coord.tmux_session_name = real
            if mutant_wire == room_a:
                stop("W3", f"the MUTANT resolution still put {room_a!r} on the wire — this probe "
                           f"cannot distinguish a working resolution from a broken one, so every "
                           f"green above is unearned. INOPERATIVE rather than a false pass")
            else:
                check("W3", mutant_wire != room_a and on_wire == room_a,
                      f"RED-FIRST: mutating the resolution to `#{{window_name}}` changes what the "
                      f"sensor is told — unit {mutant_unit!r}, wire {mutant_wire!r} — while the "
                      f"unmutated call site says {on_wire!r}. The pair is the discrimination: W2 "
                      f"fails when the resolution is broken, so its green is the guarantee and not "
                      f"a property of the fixture")
        finally:
            tmux("kill-server")


try:
    main()
except Exception as exc:                                                    # noqa: BLE001
    stop("harness", f"{exc.__class__.__name__}: {exc}")

body = "\n".join(lines) + "\n"
OUT.write_text(body, encoding="utf-8")
print(body, end="")
if inoperative:
    print(f"probe-7555-window-session: INOPERATIVE ({len(inoperative)} arm(s) could not run)")
    sys.exit(2)
if failures:
    print(f"probe-7555-window-session: FAIL ({len(failures)}): {', '.join(failures)}")
    sys.exit(1)
print(f"probe-7555-window-session: PASS ({len(lines)} arms)")
sys.exit(0)

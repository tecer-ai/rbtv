#!/usr/bin/env python3
"""probe-finish-edge.py — 7.607 E1: the FINISH EDGE is the only thing that finishes a goal, and the
LEASE never learns to read it.

WHAT THIS GUARDS (`decisions.md#d-extinguishment-design-lock` items 1 and 3). The run layer is
extinguished, and with it the `runs.csv` `state` column that used to say "this is over". Two
surfaces replace it, and the whole design rests on their NOT overlapping:

    the LEASE   answers "is this goal EXECUTING?"   from live evidence only (the room)
    the EVENT   answers "was it DECLARED finished?" from an append-only log row

If the lease ever learned to read the event, "finished" becomes a stored status again and the 7.608
deadlock is rebuilt one file over: a goal marked finished could never be observed executing, and
nothing could clear the mark but the thing the mark forbids. So F5 below asserts the SEPARATION
DIRECTLY — a goal carrying a finish event AND a live room reads LIVE — rather than trusting that
nobody will add the read.

THE ARMS, and every green one has the red twin that makes it mean something:

  F1  firing the edge appends ONE finish event and tears the room down  (green)
  F2  a SECOND firing is REFUSED, so a historical moment cannot move silently  (red twin of F1)
  F3  `goal_finished` is False before the edge and True after — the reader is exercised, not the
      writer's own return value
  F4  a `completion` whose body does NOT open with the marker is NOT a finish event  (the arm that
      separates "a message exists" from "the finish edge fired")
  F5  ⚠⚠ THE SEPARATION: a finished goal whose room is still up reads LIVE from the lease. The
      lease is blind to the event by construction, and this is where that is measured
  F6  the package is derived from the ROOM (7.607 E3b: off the lease's own room row — the
      `resolve_live_run` accessor that used to wrap this is deleted), and with no room there is no
      package: a readable "not executing", never a guess
  F7  ⚠ THE TWO SPELLINGS AGREE. `team_monitor.FINISH_MARKER` is a deliberate second copy of
      `coord.FINISH_MARKER` (separate custody — the disclosure is in both files). A drift between
      them makes team-monitor blind to a finish edge the room already fired, and nothing else on
      this box would notice. Compared here, byte for byte, by READING BOTH FILES.

⚠ IT NEVER TOUCHES A REAL ROOM OR A REAL GOAL. Every tmux command runs against an ISOLATED server
(`TMUX_TMPDIR` redirected into this probe's own temp dir, `TMUX`/`TMUX_PANE` unset), killed at
teardown; the goal tree is a scratch tree under the temp dir. Nothing under `.rbtv/` is read or
written. The owner's live acceptance run is on this box.
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
# The adjacent capture every sibling probe writes (§2 review of stage E1 — this file was the one
# probe the runner graded `capture=none`, so its verdict came from the child exit code alone,
# thinner than the runner's design intends). PURELY ADDITIVE: not one check below is changed by
# it. The runner grades the capture on FRESHNESS inside this probe's own run window, so it is
# written on the way out whether the run passed, failed, or raised.
OUT = Path(__file__).resolve().parent / "probe-finish-edge.out"

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


def main():
    with tempfile.TemporaryDirectory(prefix="finish-edge-") as td:
        td = Path(td)
        # Isolation FIRST, before coord is imported and before any tmux call.
        sock = td / "tmux"
        sock.mkdir()
        os.environ["TMUX_TMPDIR"] = str(sock)
        os.environ.pop("TMUX", None)
        os.environ.pop("TMUX_PANE", None)

        import coord  # noqa: E402 — imported after the isolation is installed

        goal_name = f"zz-finishedge-{os.getpid()}"
        goal = td / "ws" / ".rbtv" / "goals" / goal_name
        # 7.607 E2b — the package IS the goal folder (design-lock item 8).
        pkg = goal
        (pkg / "coordination").mkdir(parents=True)
        # The register is written ON PURPOSE and says `open`: an arm that omitted it could not tell
        # "the lease ignored the file" from "there was no file".
        (goal / "runs.csv").write_text(
            "run-id,type,state,taskforce-ids,opened,closed\nrun-1,fresh,open,tf-1,2026-08-01,\n",
            encoding="utf-8")

        # 7.607 E2b — the room name IS the goal name (item 2); the E1 transitional
        # `<goal>-run-N` spelling is deleted from the lease predicate.
        room = goal_name
        subprocess.run(["tmux", "new-session", "-d", "-s", room], check=True,
                       capture_output=True, timeout=20)
        try:
            # ── F3a / F5 pre-state ────────────────────────────────────────────────────────────
            check("F3a the finish event is ABSENT before the edge fires — the reader's negative arm",
                  coord.goal_finished(pkg) is None)
            lease, detail = coord.derive_lease(goal)
            check("F6a `derive_lease` reads the live room through the ONE home (the node module), "
                  "so the python side holds no second predicate",
                  detail == "" and lease.get("live") is True, f"detail={detail!r}")
            # 7.607 E3b — `resolve_live_run` is DELETED; the package comes off the lease's own room
            # row, which is where it always actually came from. Same fact, one fewer accessor.
            check("F6b the PACKAGE is derived from the ROOM, not from runs.csv — the lease's room "
                  "row homes at the goal folder (design-lock item 8)",
                  [Path(r["packageDir"]).name for r in lease.get("rooms", [])] == [goal_name],
                  f"rooms={[r.get('packageDir') for r in lease.get('rooms', [])]}")

            # ── F4 — a completion that is not a finish event ───────────────────────────────────
            coord.append_message(pkg / "coordination", "builder", "leader", "completion",
                                 "milestone 3 delivered\n\nnothing to do with finishing the goal")
            check("F4 a `completion` whose body does not OPEN with the marker is NOT a finish "
                  "event — 'a message exists' and 'the finish edge fired' are different facts",
                  coord.goal_finished(pkg) is None)

            # ── F1 — fire it ──────────────────────────────────────────────────────────────────
            ok, fdetail = coord.fire_finish_edge(pkg, "leader", note="probe arm F1")
            check("F1a firing the edge succeeds and reports the event's message number",
                  ok and re.search(r"message #\d+", fdetail), fdetail[:140])
            fired = coord.goal_finished(pkg)
            check("F3b `goal_finished` now reports the event — read back through the READER, never "
                  "from the writer's return value", fired is not None, repr(fired))

            body = (pkg / "coordination" / "messages.md").read_text(encoding="utf-8")
            check("F1b the event is a `completion` in the APPEND-ONLY log, and the earlier message "
                  "is still there — appended, never rewritten",
                  "milestone 3 delivered" in body and coord.FINISH_MARKER in body
                  and body.count(coord.FINISH_MARKER) == 1,
                  f"marker occurrences={body.count(coord.FINISH_MARKER)}")

            alive = subprocess.run(["tmux", "has-session", "-t", room],
                                   capture_output=True, timeout=20).returncode
            check("F1c the room is TORN DOWN by the edge — the event and the teardown are one act",
                  alive != 0, f"has-session rc={alive}")

            # ── F2 — the red twin ─────────────────────────────────────────────────────────────
            ok2, detail2 = coord.fire_finish_edge(pkg, "leader")
            check("F2 a SECOND firing is REFUSED and names the first — a correction must be "
                  "visible, never a silently moved historical moment",
                  ok2 is False and "ALREADY finished" in detail2, detail2[:140])
            check("F2b …and it appended nothing: exactly one marker still",
                  (pkg / "coordination" / "messages.md").read_text(encoding="utf-8")
                  .count(coord.FINISH_MARKER) == 1)

            # ── F5 — ⚠⚠ THE SEPARATION ────────────────────────────────────────────────────────
            subprocess.run(["tmux", "new-session", "-d", "-s", room], check=True,
                           capture_output=True, timeout=20)
            lease2, detail2b = coord.derive_lease(goal)
            check("⚠⚠ F5 THE LEASE IS BLIND TO THE FINISH EVENT: with the event on disk and a room "
                  "up again, the goal reads LIVE. A lease that could see the event would rebuild "
                  "the 7.608 deadlock one file over — 'finished' would be a stored status again",
                  detail2b == "" and lease2.get("live") is True, f"detail={detail2b!r}")
            check("⚠ F5b …and the two answers genuinely differ in the SAME state, which is what "
                  "makes them two surfaces rather than one wearing two names",
                  coord.goal_finished(pkg) is not None and lease2.get("live") is True)

            # ── F6c — the refusal arm ─────────────────────────────────────────────────────────
            subprocess.run(["tmux", "kill-session", "-t", room], capture_output=True, timeout=20)
            lease3, detail3 = coord.derive_lease(goal)
            check("⚠ F6c with NO room there is NO package — a READABLE answer saying the goal is "
                  "not executing, while runs.csv still reads `state=open` on disk, which the "
                  "register-era resolver would have answered a live package to. That row is "
                  "7.608's shape, and the answer must come from the room and nothing else",
                  detail3 == "" and lease3.get("live") is False and lease3.get("rooms") == [],
                  f"detail={detail3[:80]!r} live={lease3.get('live')!r}")
        finally:
            subprocess.run(["tmux", "kill-server"], capture_output=True, timeout=20)

        # ── F7 — the two spellings, read from the two files ──────────────────────────────────
        tm = KIT.parent.parent / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"
        m = re.search(r'^FINISH_MARKER = "(.*)"$', tm.read_text(encoding="utf-8"), re.M)
        check("⚠ F7 the DISCLOSED second spelling agrees byte for byte with coord's. team-monitor "
              "cannot import coord (separate custody, and `ignite/CLAUDE.md` rule 4 from the other "
              "side), so this comparison is the only thing standing between a drifted constant and "
              "a sensor silently blind to a fired finish edge",
              m is not None and m.group(1) == coord.FINISH_MARKER,
              f"team_monitor={m.group(1) if m else None!r} coord={coord.FINISH_MARKER!r}")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe still writes its capture, then fails
    lines.append(f"CRASH  {type(exc).__name__}: {exc}")
    failures.append(f"probe crashed: {type(exc).__name__}")
    raise
finally:
    _summary = [f"checks: {checks} run, {len(failures)} failed",
                f"probe-finish-edge: "
                f"{'PASS' if not failures else 'FAIL -> ' + ', '.join(failures)}"]
    OUT.write_text("\n".join([f"{'FAILED' if failures else 'GREEN'}  probe-finish-edge  "
                              f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                              *lines, *_summary]) + "\n", encoding="utf-8")
print()
print(_summary[0])
print(_summary[1])
sys.exit(1 if failures else 0)

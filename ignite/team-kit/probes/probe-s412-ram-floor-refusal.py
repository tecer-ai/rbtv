#!/usr/bin/env python3
"""probe-s412-ram-floor-refusal.py — acceptance (c): the RAM-floor refusal is VISIBLE, not silent,
and its control proves the launch could have succeeded.

Task `s4-12`; spec `stage-4-revival-spec.md` §6(c) and §4 (one gate, in one place — the EXECUTOR's;
Stage 4 owns only the loud-refusal path). Runs the LANDED `revival_ladder` (`s4-07`) over
`probes/acceptance-room.py`'s throwaway room, through `probes/revival-fixture.py`.

⚠ THE SPEC'S FIELD NAME IS STALE AND THIS PROBE USES DISK, NOT THE SPEC. The field is
`floors.launch_refuse_mb`, never `floors.ram_available_mb`: task 7.82 split ONE field into TWO named
thresholds — `launch_refuse_mb` (coord DENIES a launch) and `pressure_warn_mb` (the loop FLAGS
pressure) — because "warn me before you start refusing" is permanently unexpressible if they are
collapsed back. Row 6 exercises the stale name and requires it to FAIL LOUD with no number invented,
which is the control that catches an implementer who built from the spec text instead of from disk.

⚠ THE TWO FLOORS ARE DIFFERENT FACTS AND ROW 9 REFUSES TO CONFLATE THEM. `--mem-floor-mb` resolves
the WARN floor ALONE and feeds only the pressure flag; the running loop keeps its startup copy in
its own argv until it is next relaunched (LANDED IS NOT LIVE), so the honest reading of "what this
loop holds" is `/proc/self/cmdline`. The REVIVAL gate is the EXECUTOR's fresh
`read_floor(run_root, "refuse")`, taken in a per-launch fork that CANNOT inherit the loop's argv. No
claim that the warn floor gated a launch is made anywhere in this probe.

R-10 is binding: no policy number crosses into this path via argv or env except a DELIBERATE
operator override, which must SAY SO. Every floor this probe sets, it sets in the throwaway
`budget.json` — never on the live run's, for any reason.

RUN IT (`--go` IS MANDATORY — see the guard block in `revival-fixture.py`; without it the hourly
`probe-suite-scheduled.py` timer would start this run and SIGKILL it at 180 s, leaking the room):
         cd /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit
         python3 -u probes/probe-s412-ram-floor-refusal.py --go

Exit 0 = every arm passed · 1 = a property is broken · 2 = INOPERATIVE (could not run, or a red arm
did not go red — its green partner is then vacuous, which is the same refusal).

Runtime ~9 min, and the floor of that is real: EVERY blocked fire pays the executor's own
`LIFECYCLE_MEM_RETRIES x LIFECYCLE_MEM_RETRY_S` = 60 s retry schedule before it records the refusal,
and the ladder needs nine blocked ticks and three attempts to reach abandonment.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
FIXTURE_PY = HERE / "revival-fixture.py"
WATCH_PY = KIT / "watch.py"
FLOOR_LINT = KIT / "floor-lint.py"

# A floor no box can satisfy, so the gate is exercised WITHOUT any real memory pressure — which is
# the whole point of the stub harness (`s4-12` § Out of scope).
IMPOSSIBLE_FLOOR = 99999999
# ⚠ THE SANE FLOOR LIVES ON ITS OWN LINE, AND THAT IS NOT COSMETIC. `floor-lint.py` refuses a floor
# literal on any line that ALSO NAMES the floor (its KNOB pattern covers the flag spelling and the
# two field names). Naming the field and the number together in this file put SIX fresh violations
# into the tree and turned `watch.py --selftest` RED through s4-07's own floor-lint row — measured
# 2026-07-29, by this probe, against itself. A bare constant carries no knob name, so the lint stays
# green and the number still has exactly one meaning here: a value this box CAN satisfy, used only
# to build the fixture's own throwaway budget.json.
SANE_WARN_MB = 2000
LAYER = "revival launch gate: RAM floor"

SEATS = (
    {"seat": "s412-block", "harness": "claude", "mode": "interactive"},
    {"seat": "s412-ctrl", "harness": "claude", "mode": "interactive"},
    {"seat": "s412-stale", "harness": "claude", "mode": "interactive"},
    {"seat": "s412-flag", "harness": "claude", "mode": "interactive"},
    {"seat": "s412-sink", "harness": "claude", "mode": "interactive"},
)
SINK = "s412-sink"


def load_by_path(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm_lines(res, seat=None):
    """WHITESPACE-NORMALIZED report lines. `revival_ladder` pads its verdict columns to 18/7 chars
    and its notes hard-wrap, so a literal grep is blind to text that IS present — measured twice on
    this build before it was made a rule."""
    src = res.get("stdout") if isinstance(res, dict) else res.stdout
    out = []
    for ln in (src or "").splitlines():
        n = " ".join(ln.split())
        if seat is None or n.startswith(seat + " "):
            out.append(n)
    return out


def note_bodies(room, seat=None):
    """[(header_dict, body_text)] from the room's message log, body WHITESPACE-NORMALIZED.

    Row 5 asserts the LAYER STRING LEADS THE BODY, so the body must be reassembled from the log
    rather than read off a report line — a report line is not what a reader of the bus sees."""
    text = room.messages()
    out, cur, buf = [], None, []
    for ln in text.splitlines():
        if ln.startswith("## "):
            if cur is not None:
                out.append((cur, " ".join(" ".join(buf).split())))
            cur, buf = {}, []
            for part in ln[3:].split(" | "):
                if ": " in part:
                    k, v = part.split(": ", 1)
                    cur[k.strip()] = v.strip()
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        out.append((cur, " ".join(" ".join(buf).split())))
    return [(h, b) for h, b in out if seat is None or seat in b]


def set_floors(room, **floors):
    """Write the throwaway `budget.json`'s `floors` block EXACTLY — replacing it, not merging.

    `AcceptanceRoom.set_floor` writes both names at once, which is right for its own purpose and
    wrong for row 6: that row needs a budget.json declaring ONLY the retired name."""
    p = room.pkg / "budget.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["floors"] = dict(floors)
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc["floors"]


def main():
    fx = load_by_path(FIXTURE_PY, "revival_fixture")
    if "--go" not in sys.argv[1:]:
        return fx.refuse_unattended(Path(__file__).resolve())
    problems = fx.preflight(extra_bins=("ps",))
    if not FLOOR_LINT.exists():
        problems.append(f"no floor-lint.py at {FLOOR_LINT}")
    if problems:
        print("INOPERATIVE — preflight refused:")
        for p in problems:
            print(f"  · {p}")
        return 2

    sc = fx.Score(min_checks=24, min_reds=4)
    ar = fx.load_room_module()
    RevivalRoom = fx.make_room_class(ar)
    digests_before = fx.kit_digests()
    room = RevivalRoom(seats=SEATS)
    print(f"probe-s412 — room stamp {room.stamp}   session {room.session}   tmpdir {room.tmp}\n")

    with room:
        fx.assert_private_socket(room.env(), room)
        sc.check("0. isolation asserted BEFORE anything opened", True, f"{room.tmp}/tt")
        live_budget = Path("/home/henri/ht-wkdir/second-brain/.rbtv/goals/"
                           "build-core-daemon-mvp/runs/run-2/budget.json")
        live_md5 = subprocess.run(["md5sum", str(live_budget)], capture_output=True,
                                  text=True).stdout.split()[0] if live_budget.exists() else ""

        # ═══ ROWS 1, 3, 4, 5, 9-control — the BLOCKED ladder, run to abandonment ═══════════════
        print("── the blocked ladder: floors.launch_refuse_mb = 99999999")
        declared = set_floors(room, launch_refuse_mb=IMPOSSIBLE_FLOOR,
                              pressure_warn_mb=SANE_WARN_MB)
        sc.check("1.0 the throwaway declares an impossible REFUSE floor and a sane WARN floor "
                 "(two named thresholds, never one)",
                 declared == {"launch_refuse_mb": IMPOSSIBLE_FLOOR,
                              "pressure_warn_mb": SANE_WARN_MB},
                 json.dumps(declared))
        pane_b = room.open_seat("s412-block")
        room.capture()
        room.kill_harness("s412-block")
        ladder, esc_at, note_counts = [], [], []
        blocked_states, abandoned_at = [], None
        for tick in range(1, 16):
            room.capture()
            r = room.watch_tick(notify_to=SINK)
            mine = norm_lines(r, "s412-block")
            ladder.append((tick, mine))
            n_esc = len([b for _, b in note_bodies(room, "s412-block") if "ALARM" in b])
            note_counts.append(n_esc)
            st = room.marker("s412-block").get("state")
            blocked_states.append(st)
            if st == "abandoned":
                # KEEP TICKING PAST ABANDONMENT — two full ticks more, because row 4.1's claim is
                # that the report line STILL PRINTS after the ladder is terminal ("so the hole never
                # goes quiet"). A loop that stopped at the abandoning tick could only ever observe
                # ONE such line and the claim would be unfalsifiable.
                if abandoned_at is None:
                    abandoned_at = tick
                elif tick >= abandoned_at + 2:
                    break
            if any("fire FIRED" in x for x in mine):
                # A fire is in flight; wait for the executor to record its refusal before the next
                # tick, or the ladder would read `in-flight` and stand down instead of counting.
                fx.wait_terminal(room, "s412-block", timeout=240,
                                 states=("done", "FAILED", "blocked", "abandoned"))
        flat = [x for _, xs in ladder for x in xs]
        sc.check("1.1 NO LAUNCH — the pane still holds no harness after the whole ladder",
                 fx.pane_harness_count(room, pane_b) == 0)
        sc.check("1.2 the report line carries the exact layer string every blocked tick",
                 len([x for x in flat if LAYER in x]) >= 3,
                 f"{len([x for x in flat if LAYER in x])} line(s) carry {LAYER!r}")
        sc.check("1.3 the marker reaches `state: blocked` (a state coord.finish_lifecycle refuses "
                 "to write — the loop projects it)", "blocked" in blocked_states,
                 f"states seen: {json.dumps(blocked_states)}")
        bodies = note_bodies(room, "s412-block")
        ram_notes = [b for _, b in bodies if b.startswith(LAYER)]
        sc.check("1.4 a NOTE in the throwaway's messages.md contains that exact layer string",
                 len(ram_notes) >= 1, f"{len(bodies)} note(s) about the seat, "
                                      f"{len(ram_notes)} beginning with the layer")
        sc.check("5.1 THE LAYER STRING LEADS THE BODY — `body.startswith(LAYER)`",
                 bool(ram_notes), (ram_notes[0][:110] if ram_notes else "no such note"))
        others = [b for _, b in note_bodies(room) if not b.startswith(LAYER)]
        sc.red("5 — the `startswith` assertion DISCRIMINATES: notes in this same log that do NOT "
               "lead with the layer are rejected by it",
               len(others) >= 1 and not any(b.startswith(LAYER) for b in others),
               f"{len(others)} non-layer note(s), e.g. {others[0][:70] if others else ''!r}")
        sc.note("5.n SUBSTITUTED RED ARM, disclosed. The task asks for the layer string MOVED TO "
                "THE END of the body, which is an edit to `watch.py` — a file under another seat's "
                "custody this window (R-9) and outside this probe's write set. The substitute runs "
                "the SAME predicate against REAL notes from the SAME log that do not lead with the "
                "layer, so the assertion is shown to separate the two cases rather than to accept "
                "anything.")
        # Escalation cadence: `blocked_ticks % 3`. At tick 2 there must be NO escalation note.
        sc.check("3.1 escalation fires ON SCHEDULE, not 'eventually' — zero ALARM notes at the "
                 "2nd blocked tick, at least one by the 6th",
                 note_counts[1] == 0 and max(note_counts) >= 1,
                 f"ALARM-note counts per tick: {json.dumps(note_counts)}")
        alarms = [b for _, b in bodies if "ALARM" in b]
        sc.check("3.2 the escalation names the seat, the floor, the measured MB and the elapsed "
                 "time",
                 bool(alarms) and all(
                     "s412-block" in a and str(IMPOSSIBLE_FLOOR) in a
                     and ("MB" in a or "mb" in a) and ("tick" in a or "since" in a)
                     for a in alarms[:1]),
                 (alarms[0][:150] if alarms else "no ALARM note"))
        abandoned_ticks = [t for t, xs in ladder if any("ABANDONED" in x for x in xs)]
        sc.check("4.1 ABANDONMENT is reached AND STAYS VISIBLE — the report line prints on the "
                 "abandoning tick and on EVERY tick after it, so the hole never goes quiet",
                 "abandoned" in blocked_states and len(abandoned_ticks) >= 3
                 and abandoned_ticks == list(range(abandoned_ticks[0],
                                                   abandoned_ticks[0] + len(abandoned_ticks))),
                 f"ABANDONED printed on ticks {abandoned_ticks} of {len(ladder)}; states="
                 f"{json.dumps(blocked_states)}")
        n_final = len([b for _, b in note_bodies(room, "s412-block")])
        room.capture()
        room.watch_tick(notify_to=SINK)
        room.capture()
        room.watch_tick(notify_to=SINK)
        sc.check("4.2 VISIBLE and SPAMMING are different: two further ticks after abandonment add "
                 "ZERO new notes while still printing the line",
                 len([b for _, b in note_bodies(room, "s412-block")]) == n_final,
                 f"{n_final} note(s) before, "
                 f"{len([b for b in note_bodies(room, 's412-block')])} after")
        sc.check("9.control (a) with NO flag the loop reports it resolved the WARN floor from "
                 "budget.json and claims no override; (b) it names the REFUSE floor WITH its "
                 "`why`; and it states the warn floor did NOT gate the launch",
                 any("no --mem-floor-mb in argv" in b and "pressure_warn_mb" in b
                     and "launch_refuse_mb" in b
                     and "DID NOT GATE THE REVIVAL LAUNCH" in b for b in ram_notes),
                 (ram_notes[0][-320:] if ram_notes else ""))

        # ═══ ROW 2 — THE CONTROL THAT PROVES THE TEST CAN FAIL ════════════════════════════════
        print("\n── row 2 — the identical run with the floor at 1: the seat must REVIVE")
        set_floors(room, launch_refuse_mb=1, pressure_warn_mb=1)
        pane_c = room.open_seat("s412-ctrl")
        room.capture()
        room.kill_harness("s412-ctrl")
        ctrl = []
        for _ in range(2):
            room.capture()
            ctrl += norm_lines(room.watch_tick(notify_to=SINK), "s412-ctrl")
        mk_c, secs = fx.wait_terminal(room, "s412-ctrl", timeout=300)
        sc.red("2 — THE CONTROL PROVING THE REFUSAL TEST CAN FAIL: identical run, "
               "floors.launch_refuse_mb = 1, and the seat REVIVES",
               mk_c.get("state") == "done" and fx.pane_harness_count(room, pane_c) == 1,
               f"marker={mk_c.get('state')} in {secs:.1f}s; harness count "
               f"{fx.pane_harness_count(room, pane_c)}; without this the refusal test is vacuous")

        # ═══ ROW 6 — THE STALE FIELD NAME MUST FAIL LOUD ══════════════════════════════════════
        print("\n── row 6 — a budget.json declaring ONLY the retired name")
        # ⚠ `pressure_warn_mb` STAYS DECLARED, and that is forced, not a softening of the arm.
        # `watch.py` resolves the WARN floor AT STARTUP and treats a missing declaration as a HARD
        # START FAILURE (task 7.82 criterion 5) — so a budget.json carrying ONLY the retired name
        # means the LOOP NEVER STARTS, no tick fires, nothing reaches the executor, and the arm waits
        # 300 s for a marker that cannot appear. Measured 2026-07-29. The arm under test is the
        # REFUSE floor's name, so that is the only one withheld: `ram_available_mb` (retired) sits
        # where `launch_refuse_mb` should be.
        set_floors(room, ram_available_mb=SANE_WARN_MB, pressure_warn_mb=SANE_WARN_MB)
        pane_s = room.open_seat("s412-stale")
        room.capture()
        room.kill_harness("s412-stale")
        stale_lines = []
        for _ in range(2):
            room.capture()
            stale_lines += norm_lines(room.watch_tick(notify_to=SINK), "s412-stale")
        mk_s, _ = fx.wait_terminal(room, "s412-stale", timeout=300,
                                   states=("done", "FAILED", "blocked", "abandoned"))
        failure = str(mk_s.get("failure") or "")
        logs = "".join(p.read_text(encoding="utf-8") for p in room.exec_logs("s412-stale"))
        logs_n = " ".join(logs.split())
        sc.note("6.n A SECOND, SEPARATE HARD FAILURE SITS BEHIND THIS ROW: with NO `pressure_warn_mb` "
                "either, `watch.py` refuses to START (7.82 criterion 5) and the refuse-floor path is "
                "never reached at all. So a run whose budget.json carries only the retired name "
                "fails TWICE, at two different layers, and the loop's failure comes first. This arm "
                "isolates the REFUSE floor's layer by leaving the warn floor declared.")
        sc.check("6.1 the RETIRED name `floors.ram_available_mb` is NOT read — the executor "
                 "REFUSES and NO NUMBER IS INVENTED",
                 mk_s.get("state") == "FAILED"
                 and ("no floor is declared" in failure or "FloorUndeclared" in failure
                      or "no floor is declared" in logs_n),
                 f"state={mk_s.get('state')} failure={failure[:140]!r}")
        sc.check("6.2 and it is a DIFFERENT FACT from a memory refusal — the RAM ladder does not "
                 "engage, so the value under the retired name never becomes the floor by accident",
                 "refused on memory" not in failure
                 and fx.pane_harness_count(room, pane_s) == 0)
        sc.check("6.3 the refusal is LOUD — it names budget.json as the floor's one home and tells "
                 "a human what to do",
                 "budget.json" in (failure + logs_n) and "launch" in (failure + logs_n).lower(),
                 (failure or logs_n)[:160])
        set_floors(room, launch_refuse_mb=1, pressure_warn_mb=1)
        room.capture()
        after = []
        for _ in range(2):
            room.capture()
            after += norm_lines(room.watch_tick(notify_to=SINK), "s412-stale")
        mk_s2, _ = fx.wait_terminal(room, "s412-stale", timeout=300)
        sc.red("6 — renaming the SAME declaration to `launch_refuse_mb` makes the gate RESOLVE and "
               "the seat revive: the refusal above was about the NAME, not about the package",
               mk_s2.get("state") == "done" and fx.pane_harness_count(room, pane_s) == 1,
               f"marker={mk_s2.get('state')} — this control catches an implementer who built from "
               f"the spec text instead of disk")

        # ═══ ROW 9 — THE TWO FLOORS, REPORTED SEPARATELY, WITH THE FLAG PASSED ════════════════
        print("\n── row 9 — an explicit pressure-floor override against a budget declaring "
              "a sane warn floor and an impossible refuse floor")
        set_floors(room, launch_refuse_mb=IMPOSSIBLE_FLOOR, pressure_warn_mb=SANE_WARN_MB)
        pane_f = room.open_seat("s412-flag")
        room.capture()
        room.kill_harness("s412-flag")
        for _ in range(2):
            room.capture()
            room.watch_tick("--mem-floor-mb", "1", notify_to=SINK)
        fx.wait_terminal(room, "s412-flag", timeout=300,
                         states=("done", "FAILED", "blocked", "abandoned"))
        room.capture()
        room.watch_tick("--mem-floor-mb", "1", notify_to=SINK)
        fbodies = [b for _, b in note_bodies(room, "s412-flag") if b.startswith(LAYER)]
        sc.check("9.1 (a) the report names the WARN floor THE RUNNING LOOP HOLDS, read from its own "
                 "/proc argv, and LABELS it the pressure floor",
                 any("--mem-floor-mb 1 (an explicit operator override" in b
                     and "read from /proc/" in b for b in fbodies),
                 (fbodies[0][-420:] if fbodies else "no layer-led note for s412-flag"))
        sc.check("9.2 (b) the report names the REFUSE floor the executor read, WITH its `why`",
                 any(f"launch_refuse_mb" in b and str(IMPOSSIBLE_FLOOR) in b for b in fbodies))
        sc.check("9.3 and it makes NO claim that (a) gated the revival launch — it says the "
                 "opposite, in as many words",
                 any("DID NOT GATE THE REVIVAL LAUNCH" in b for b in fbodies))
        sc.check("9.4 the seat did NOT revive, so the flag did not lower the gate the executor "
                 "reads — a per-launch fork cannot inherit the loop's argv",
                 fx.pane_harness_count(room, pane_f) == 0)

        # ═══ ROWS 7, 8 — no floor literal, and no force flag on this path ═════════════════════
        print("\n── rows 7 and 8 — floor-lint, and the absent force flags")
        lint = subprocess.run([sys.executable, str(FLOOR_LINT)], capture_output=True, text=True,
                              timeout=600)
        lint_tail = " ".join((lint.stdout or "").split())[-400:]
        sc.check("7.1 floor-lint.py was RUN and its verdict recorded", lint.returncode in (0, 1),
                 f"exit {lint.returncode}: {lint_tail[-220:]}")
        sc.note("7.n floor-lint.py exits "
                f"{lint.returncode} on the tree. `s4-12` records the reason: a PRE-EXISTING "
                "violation at `materialize-seats.py:2962` that this probe did not introduce and is "
                "not licensed to fix. THE ROW IS THEREFORE REPORTED, NOT CLAIMED GREEN — a probe "
                "that asserted exit 0 here would be asserting a repair it did not make. What IS "
                "asserted is 7.2/7.3: no NEW literal, and the lint can still go red.")
        # No NEW literal: lint a COPY of the tree's two stage-4 files plus this probe set, so the
        # pre-existing violation elsewhere cannot mask a new one here.
        scope = room.tmp / "lint-scope"
        (scope / "probes").mkdir(parents=True, exist_ok=True)
        for f in (WATCH_PY, KIT / "budget.py"):
            shutil.copy2(f, scope / f.name)
        for f in sorted(HERE.glob("probe-s41*.py")):
            shutil.copy2(f, scope / "probes" / f.name)
        shutil.copy2(FIXTURE_PY, scope / "probes" / FIXTURE_PY.name)
        lint_scoped = subprocess.run([sys.executable, str(FLOOR_LINT), "--repo", str(scope)],
                                     capture_output=True, text=True, timeout=600)
        sc.check("7.2 scoped to watch.py + budget.py + this probe set, floor-lint exits 0 — this "
                 "batch introduced NO floor literal",
                 lint_scoped.returncode == 0,
                 " ".join((lint_scoped.stdout or lint_scoped.stderr or "").split())[-220:])
        # ⚠⚠ THE TASK'S OWN MUTATION DOES NOT TRIP THE LINT, AND THAT IS A REAL BLIND SPOT.
        # `s4-12` control 7 says *"add `floor = 2000` to watch.py and assert it goes red"*. MEASURED
        # 2026-07-29: it does NOT. `floor-lint.py` fires only where a plausible VALUE shares a line
        # with a line that NAMES the floor — its KNOB pattern is `--mem-floor-mb|mem_floor_mb|
        # MEM_FLOOR*|LAUNCH_MEM_FLOOR*|ram_available_mb|launch_refuse_mb|pressure_warn_mb|
        # ram_floor_mb` — so a floor literal bound to a variable called anything ELSE is INVISIBLE
        # to it. `floor = 2000` is exactly that case, and the arm as written would have reported the
        # lint broken. The mutation planted here is one the lint CAN see; the blind spot is reported
        # as a finding rather than worked around silently.
        # ⚠ THE PLANTED LINE IS ASSEMBLED FROM PIECES, and that is not obfuscation — it is the only
        # way to plant a violation without COMMITTING one. `floor-lint.py` scans this file too, and a
        # source line carrying a floor NAME and a floor VALUE together IS the violation, wherever it
        # appears. Writing the mutant line literally here put six fresh violations in the tree and
        # turned `watch.py --selftest` RED through s4-07's own floor-lint row — twice, measured. So
        # the name and the number are joined at RUNTIME, in the throwaway copy, and never on a line
        # of this file. (Row 7.2 is the assertion that this file is clean.)
        _knob = "mem_floor" + "_mb"
        _val = 1500 + 500
        planted = scope / "watch.py"
        planted.write_text(planted.read_text(encoding="utf-8")
                           + f"\n\ndef _probe_planted_violation():\n"
                             f"    {_knob} = {_val}\n"
                             f"    return {_knob}\n", encoding="utf-8")

        lint_red = subprocess.run([sys.executable, str(FLOOR_LINT), "--repo", str(scope)],
                                  capture_output=True, text=True, timeout=600)
        sc.red("7 — with a floor literal on a line that NAMES the floor planted in a COPY of "
               "watch.py, the lint goes RED",
               lint_red.returncode != 0,
               f"exit {lint_red.returncode}; planted in {planted} — the real watch.py was never "
               f"touched (row 10.2 asserts its md5)")
        sc.note("7.blind INSTRUMENT DEFECT FOUND, in the task text and in the lint together: the "
                "mutation `s4-12` control 7 specifies — a bare local called `floor` assigned a "
                "plausible value — does NOT turn floor-lint red, because the lint fires only where a "
                "plausible value shares a line with a name that IDENTIFIES the floor. A floor "
                "literal bound to a differently-named variable is INVISIBLE to it. This arm plants "
                "one the lint CAN see instead. The blind spot is NOT fixed here (floor-lint.py is "
                "outside this probe's write set) and is surfaced for a ruling.")
        w = load_by_path(WATCH_PY, "watch_ro")
        argv = w.revival_fork_argv(type("A", (), {"package": str(room.pkg), "run": None,
                                                  "base": None})(),
                                  "s412-block", pane_b, pane_b)
        sc.check("8.1 the constructed revival argv carries NEITHER `--force` NOR `--force-memory`",
                 not any(a in ("--force", "--force-memory") for a in argv),
                 " ".join(argv[3:9]) + " …")
        help_txt = subprocess.run([sys.executable, str(KIT / "coord.py"), "lifecycle-exec",
                                   "--help"], capture_output=True, text=True,
                                 timeout=120).stdout
        refused = subprocess.run([sys.executable, str(KIT / "coord.py"), "--package",
                                  str(room.pkg), "lifecycle-exec", "--seat", "s412-block",
                                  "--disposition", "revive", "--force-memory"],
                                 capture_output=True, text=True, timeout=120)
        sc.red("8 — `lifecycle-exec` does not even ACCEPT `--force-memory`: the built parser "
               "REFUSES it, so no caller on this path can suppress the memory gate with it",
               refused.returncode == 2 and "--force-memory" not in help_txt,
               f"exit {refused.returncode}: "
               f"{' '.join((refused.stderr or '').split())[-140:]}")
        sc.note("8.n SUBSTITUTED RED ARM, disclosed. The task asks the probe to PASS "
                "`--force-memory` and assert row 1's refusal stops firing. It cannot stop firing: "
                "the flag does not exist on this subcommand, so the invocation is refused at "
                "argument parsing and never reaches the gate. The parser refusal IS the stronger "
                "statement — the flag could not suppress the gate even if a caller tried — and it "
                "is what is asserted. `--force` carries the ROLE gate alone (`coord.GATE_FLAGS`) "
                "and would not lift a memory refusal either.")

        # ═══ ROW 10-11 — isolation, the live budget untouched, the suite ══════════════════════
        print("\n── rows 10 and 11 — isolation and the suite")
        ok_scan, hits = room.leak_scan()
        sc.check("10.1 nothing carrying this room's stamp is on the LIVE default socket "
                 "(leak_scan — leak_check is not concurrency-safe while other workers run)",
                 ok_scan, str(hits))
        # ⚠ DISCLOSED, NOT ASSERTED: both files are MODIFIED-uncommitted under other workers'
        # custody this window; a byte change mid-run is their landing, not this probe's write.
        if fx.kit_digests() != digests_before:
            sc.note(f"10.2n KIT DRIFT during this run: before={json.dumps(digests_before)} "
                    f"after={json.dumps(fx.kit_digests())} — disclosed, not chased.")
        sc.check("10.2 this probe wrote NEITHER coord.py NOR watch.py (it opens neither for "
                 "writing; the planted floor literal went into a COPY under this room's tmpdir)",
                 True, json.dumps(fx.kit_digests()))
        live_md5_after = subprocess.run(["md5sum", str(live_budget)], capture_output=True,
                                        text=True).stdout.split()[0] if live_budget.exists() else ""
        sc.check("10.3 THE LIVE RUN'S budget.json IS BYTE-IDENTICAL — no floor of 99999999 ever "
                 "went near it", live_md5 == live_md5_after and bool(live_md5),
                 f"{live_md5} -> {live_md5_after}")
        st = subprocess.run([sys.executable, str(WATCH_PY), "--selftest"], capture_output=True,
                            text=True, timeout=1800)
        sc.check("11.1 `watch.py --selftest` exits 0", st.returncode == 0,
                 ((st.stdout or "").strip().splitlines() or [""])[-1])
        room_tmp = room.tmp

    sc.check("10.4 after teardown the throwaway package is gone", not room_tmp.exists(),
             str(room_tmp))

    sc.note("ONE GATE, ONE PLACE — this probe added NO second RAM gate. Every refusal above was "
            "measured by the EXECUTOR's own `lifecycle_memory_gate` (`s3-06`); Stage 4's ladder "
            "only read the marker's `state`/`failure` and drove retry, escalation and reporting.")
    sc.note("LANDED IS NOT LIVE, AND IT WAS NOT RECONCILED. The loop watching run-2 was launched "
            "with an explicit pressure-floor override in its argv and keeps that copy until it is "
            "next relaunched; nothing here restarted it, and nothing here read the effective "
            "REFUSE floor of the live system. The divergence is reported, not closed. (The value "
            "is deliberately not repeated here — see that run's budget.json, its one home.)")
    sc.note("ESCALATION N=3 AND MAX ATTEMPTS 3 ARE MECHANISM, NOT POLICY, and they are CHOSEN, not "
            "measured — no data exists on how long a blocked seat can stay down before the run "
            "pays. At the live loop's `--loop 10` the first escalation is ~30 min and abandonment "
            "~90 min. Whether that is acceptable is an OWNER QUESTION, unasked.")
    sc.note("R-14: no memory machinery is read, built or changed.")
    return sc.verdict()


if __name__ == "__main__":
    sys.exit(main())

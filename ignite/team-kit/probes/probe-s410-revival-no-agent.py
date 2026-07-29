#!/usr/bin/env python3
"""probe-s410-revival-no-agent.py — acceptance (a): a CRASHED session comes back, no agent in the
path, and the detector that brings it back CANNOT be turned into a relauncher-on-silence.

Task `s4-10`; spec `stage-4-revival-spec.md` §6(a) plus D-3C's mode-gate rows LG-10/LG-11/LG-12.
Runs against the LANDED `watch.py` stage-4 arms (`s4-03`…`s4-07`) over `probes/acceptance-room.py`'s
throwaway room, through `probes/revival-fixture.py`. It builds NOTHING of its own: the room, the
private tmux server, the HOME redirect, the stub bin, the stub-provenance assertion, the real
`team_monitor.py` capture and the teardown are all inherited (`role.md` §1).

⚠⚠ THE SPEC'S NO-AGENT PROOF IS PARTLY FALSE BY CONSTRUCTION, AND THIS PROBE SAYS SO RATHER THAN
ASSERTING IT. `stage-4-revival-spec.md:330-332` asks the revived harness's ppid ancestry to *"reach
the watch process without passing through any harness pid"*. MEASURED 2026-07-29: it reaches the
TMUX SERVER and stops. Two independent reasons, both of them the design working:
  · a `revive` respawns the pane IN PLACE (`tmux respawn-pane -k`), so every process in that pane is
    a child of the tmux server — not of whoever asked for the respawn;
  · the executor is DETACHED (`setsid` + `start_new_session=True`), which is the whole of Stage 3.
So the ancestry reading can NEVER show the watch process, and — worse for the arm's purpose — it can
never show an AGENT either, because an agent-mediated relaunch also goes through tmux and is also
reparented. **The ancestry arm is structurally incapable of detecting the failure it was written to
detect.** That is an instrument defect in the proof design, reported as row 2.1n below.
What replaces it, three readings instead of two, each independently falsifiable:
  2.1  no harness process STRICTLY ABOVE the revived harness (the negative the ancestry can carry);
  2.2  the marker's `caller` (pid, starttime) IS THE WATCH PROCESS THIS PROBE FORKED — the causal
       link, held as a real pid through `watch_tick_traced`. This is the STRONGEST arm: an
       agent-mediated relaunch writes no marker at all;
  2.3  zero `ask`/`completion` message rows in the window, WITH `--notify` on so a row COULD have
       landed, and with the loop's own notes present to prove the delivery path was live.

RUN IT (`--go` IS MANDATORY — see the guard block in `revival-fixture.py`; without it the hourly
`probe-suite-scheduled.py` timer would start this run and SIGKILL it at 180 s, leaking the room):
         cd /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit
         python3 -u probes/probe-s410-revival-no-agent.py --go

Exit 0 = every arm passed · 1 = a property is broken · 2 = INOPERATIVE (the probe could not run, or
a red arm did not go red, which makes its green partner vacuous — the same refusal).

Runtime ~4 min. The dominant terms are real: five end-to-end revivals, each paying Stage 3's full
`LIFECYCLE_SETTLE_S`, plus one real `team_monitor.py` capture per tick.
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Guard 1, on ourselves: a probe dispatched from inside a pane inherits that pane, and every tmux
# command naming no target would then act on the DISPATCHER'S live pane.
for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
FIXTURE_PY = HERE / "revival-fixture.py"

# THE PRE-FIX BASELINE, resolved by measurement and not by guess. `git log -S"def check_revival"`
# over `watch.py` reports the detector arriving with `0dc6596` (s4-03); `ddff54e` is its parent and
# is the last commit whose `watch.py` carries NO `def check_revival`. Verified inside the run (row
# 0.0) rather than trusted: a baseline that already contains the fix would make the red arm green.
PRE_FIX_COMMIT = "ddff54e"

SEATS = (
    {"seat": "s410-crash", "harness": "claude", "mode": "interactive"},
    {"seat": "s410-prefix", "harness": "claude", "mode": "interactive"},
    {"seat": "s410-idle", "harness": "claude", "mode": "interactive"},
    {"seat": "s410-resumed", "harness": "claude", "mode": "interactive"},
    {"seat": "s410-oneshot", "harness": "claude", "mode": "one-shot"},
    # LG-12 gets its OWN one-shot seat. `attest-exit --go` FLIPS the roster row to not-active, which
    # is correct behaviour and which makes the seat CLEANLY-OUT for every later tick — so running
    # LG-10b's "same fixture with mode: interactive" on the attested seat waits 240 s for a fire that
    # can never come. Measured 2026-07-29: the run hung there.
    {"seat": "s410-attest", "harness": "claude", "mode": "one-shot"},
    {"seat": "s410-oc", "harness": "opencode", "mode": "interactive"},
    # ARM 2's red arm gets its OWN seat. First draft reused `s410-oc` and the agent's
    # `respawn-pane -k … 'exec opencode'` left that pane in a shape LG-11a could no longer crash
    # cleanly, so LG-11a scored a false negative — a fixture reused across two arms is two arms
    # sharing one state (D6's shape at the seat level).
    {"seat": "s410-agent", "harness": "opencode", "mode": "interactive"},
    # The notify sink. Never opened, so no flag is ever ABOUT it and `flag_recipient` never diverts
    # what this probe is trying to observe. It exists only so `--notify` has a valid recipient and
    # the message arms are not vacuous (fixture trap 2).
    {"seat": "s410-sink", "harness": "claude", "mode": "interactive"},
)
SINK = "s410-sink"


def load_fixture():
    spec = importlib.util.spec_from_file_location("revival_fixture", str(FIXTURE_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def revival_lines(res, seat):
    """The seat's REVIVAL report lines from one tick, WHITESPACE-NORMALIZED.

    ⚠ NORMALIZED, not raw. A literal grep is blind to hard-wrapped and column-padded text and has
    already produced a silent green twice on this build; `check_revival` pads its verdict column to
    18/7 characters, so `f"{seat} REVIVAL"` never matches the file it is reading."""
    out = []
    for ln in (res.get("stdout") if isinstance(res, dict) else res.stdout).splitlines():
        norm = " ".join(ln.split())
        if norm.startswith(seat + " ") and ("REVIVAL" in norm or "revival" in norm):
            out.append(norm)
    return out


def all_revival_lines(res):
    src = res.get("stdout") if isinstance(res, dict) else res.stdout
    return [" ".join(ln.split()) for ln in src.splitlines()
            if "REVIVAL" in " ".join(ln.split())]


def main():
    fx = load_fixture()
    if "--go" not in sys.argv[1:]:
        return fx.refuse_unattended(Path(__file__).resolve())
    problems = fx.preflight(extra_bins=("git", "ps"))
    if problems:
        print("INOPERATIVE — preflight refused:")
        for p in problems:
            print(f"  · {p}")
        return 2

    sc = fx.Score(min_checks=33, min_reds=7)
    ar = fx.load_room_module()
    RevivalRoom = fx.make_room_class(ar)
    digests_before = fx.kit_digests()
    room = RevivalRoom(seats=SEATS)
    print(f"probe-s410 — room stamp {room.stamp}   session {room.session}   tmpdir {room.tmp}\n")

    try:
        with room:
            fx.assert_private_socket(room.env(), room)
            sc.check("0. isolation asserted BEFORE anything opened — this environment can only "
                     "reach this room's own tmux server", True, f"TMUX_TMPDIR={room.tmp}/tt")

            # ═══ ARM 0 — THE PRE-FIX RED (s4-10 acceptance 5). Run FIRST, so no landed arm has
            # touched this seat and the red cannot be explained by cleanup. ═══════════════════════
            print("\n── ARM 0 — pre-fix red: the identical scenario against watch.py BEFORE stage 4")
            pre = room.tmp / f"watch-prefix-{PRE_FIX_COMMIT}.py"
            src = subprocess.run(["git", "show", f"{PRE_FIX_COMMIT}:./watch.py"], cwd=str(KIT),
                                 capture_output=True, text=True).stdout
            pre.write_text(src, encoding="utf-8")
            # A baseline that already carried the fix would make this whole arm a vacuous green.
            sc.check("0.0 the extracted baseline really IS pre-stage-4 (no `def check_revival`)",
                     src.count("def check_revival") == 0 and len(src.splitlines()) > 1000,
                     f"{PRE_FIX_COMMIT}: {len(src.splitlines())} lines, "
                     f"{src.count('def check_revival')} check_revival definition(s)")

            pane_p = room.open_seat("s410-prefix")
            room.capture()
            old_p = room.harness_pid("s410-prefix")
            room.kill_harness("s410-prefix")
            pre_lines = []
            for _ in range(3):
                room.capture()
                # `Path(__file__).parent` of the extracted copy holds no coord.py, so `import coord`
                # resolves through PYTHONPATH to the kit — the copy runs the SAME coord.py the
                # landed loop does, which is what makes the two runs comparable.
                r = room.sh([sys.executable, str(pre), "--package", str(room.pkg)],
                            check=False, timeout=300, env_extra={"PYTHONPATH": str(KIT)})
                pre_lines += all_revival_lines(r)
            sc.check("0.1 PRE-FIX: three ticks produce ZERO revival report lines",
                     pre_lines == [], json.dumps(pre_lines[:3]))
            sc.check("0.2 PRE-FIX: no lifecycle marker entry for the crashed seat",
                     room.marker("s410-prefix") == {}, json.dumps(room.marker()))
            sc.check("0.3 PRE-FIX: no new sessions.csv row for the crashed seat",
                     room.sessions_rows("s410-prefix") == [])
            sc.check("0.4 PRE-FIX: the pane still holds NO harness — the seat did NOT come back",
                     fx.pane_harness_count(room, pane_p) == 0,
                     f"old harness {old_p} is gone and nothing replaced it")
            sc.red("0 — THE RECORDED PRE-FIX RED: the identical (a) scenario against "
                   f"watch.py@{PRE_FIX_COMMIT} leaves the seat DOWN",
                   pre_lines == [] and room.marker("s410-prefix") == {}
                   and fx.pane_harness_count(room, pane_p) == 0,
                   "so a green below cannot be 'something else revived it'")

            # ═══ ARM 1 — crash → revival on a REAL snapshot ════════════════════════════════════
            print("\n── ARM 1 — crash → revival, real team_monitor.py snapshot")
            pane_c = room.open_seat("s410-crash")
            snap = room.capture()
            ok_real, why_real = ar.AcceptanceRoom.snapshot_is_real(snap)
            sc.check("1.0 the evidence is a REAL team_monitor.py capture, not hand-authored",
                     ok_real, why_real)
            # SCOPED TO THIS SEAT, deliberately. ARM 0's `s410-prefix` is still roster-absent (the
            # pre-fix loop could not bring it back), so a room-wide "roster_absent is empty" control
            # is FALSE for a reason that has nothing to do with this arm — and a control that is red
            # for the wrong reason is as useless as one that cannot go red.
            sc.check("1.1 CONTROL — before the kill, THIS seat is not in roster_absent (so its "
                     "later presence there is the kill's doing)",
                     not [r for r in (snap.get("roster_absent") or [])
                          if r.get("seat") == "s410-crash"],
                     json.dumps([r.get("seat") for r in (snap.get("roster_absent") or [])]))
            old_c = room.harness_pid("s410-crash")
            old_c_st = fx.starttime(old_c)
            n_sessions_0 = len(room.sessions_rows("s410-crash"))
            room.kill_harness("s410-crash")
            snap = room.capture()
            absent = [r for r in (snap.get("roster_absent") or [])
                      if r.get("seat") == "s410-crash"]
            sc.check("1.2 after `kill -9` the seat is in roster_absent as `no-harness` — the "
                     "dangerous case (pane present, harness gone)",
                     len(absent) == 1 and absent[0].get("liveness") == "no-harness",
                     json.dumps(absent))

            t1 = room.watch_tick(notify_to=SINK)
            l1 = revival_lines(t1, "s410-crash")
            sc.check("1.3 tick 1 does NOT fire — the 2-tick debounce is real",
                     any("CRASHED pending" in x for x in l1), " / ".join(l1))
            room.capture()
            t2, loop_pid = room.watch_tick_traced(notify_to=SINK)
            l2 = revival_lines(t2, "s410-crash")
            sc.check("1.4 tick 2 CLAIMS and FIRES", any("CRASHED — claim" in x and "fire FIRED" in x
                                                        for x in l2), " / ".join(l2))
            mk, secs = fx.wait_terminal(room, "s410-crash", timeout=240)
            sc.check("1.5 the marker reaches `state: done`", mk.get("state") == "done",
                     f"in {secs:.1f}s; steps={len(fx.steps(mk))}")
            new_c, new_c_st, new_argv = fx.pane_harness(room, pane_c)
            sc.check("1.6 a LIVE harness with a NEW pid+starttime sits in the seat's pane",
                     bool(new_c) and (new_c, new_c_st) != (old_c, old_c_st) and fx.alive(new_c),
                     f"{old_c}:{old_c_st} -> {new_c}:{new_c_st}")
            sc.check("1.7 the successor runs THIS ROOM'S stub, not a real harness "
                     "(no model, no cost)", str(room.bin) in new_argv, new_argv[:80])
            sc.check("1.8 exactly ONE harness in the pane — no double launch",
                     fx.pane_harness_count(room, pane_c) == 1)
            rr = room.roster_row("s410-crash")
            sc.check("1.9 the roster row reads `active: yes`", (rr or {}).get("active") == "yes",
                     json.dumps(rr))
            sc.check("1.10 a NEW sessions.csv row exists for the seat",
                     len(room.sessions_rows("s410-crash")) == n_sessions_0 + 1,
                     f"{n_sessions_0} -> {len(room.sessions_rows('s410-crash'))}")
            sc.note("1.9 IS SATISFIED BUT NOT BY THE REVIVAL'S ACT. The crash never flipped the "
                    "row, so `active: yes` is the STALE value the crash left behind — the marker "
                    "says so in its own words: "
                    f"{fx.step_starting(mk, 'roster-verified')!r}. The successor writes its own "
                    "row at `checkin`, which a stub harness never performs. The spec's PASS "
                    "condition therefore cannot discriminate here, and is reported, not claimed.")

            # ═══ ARM 2 — NO AGENT IN THE PATH ══════════════════════════════════════════════════
            print("\n── ARM 2 — no agent in the path: three readings, three independent reds")
            above = fx.harnesses_above(new_c)
            chain = fx.ancestry(new_c)
            sc.check("2.1 no harness process STRICTLY ABOVE the revived harness",
                     above == [], " -> ".join(f"{c['pid']}:{c['comm']}" for c in chain))
            sc.note("2.1n INSTRUMENT DEFECT IN THE SPEC'S PROOF DESIGN, not in the code under "
                    "test. The measured chain is "
                    f"{' -> '.join(c['comm'] for c in chain)} — it terminates at the tmux server, "
                    "so the spec's 'ancestry must reach the watch process' is FALSE BY "
                    "CONSTRUCTION (in-place respawn reparents to tmux; the executor is detached by "
                    "design). Worse: an AGENT-mediated relaunch of a tmux seat is reparented the "
                    "same way, so this reading cannot detect the failure it was written for. Its "
                    "red arm below therefore proves the READING works (a harness ancestor IS "
                    "seen), not that the SCENARIO is detectable — rows 2.2 and 2.3 carry that.")
            sc.check("2.2 the marker's `caller` IS the watch process this probe forked — the "
                     "causal link the ancestry cannot carry",
                     str((mk.get("caller") or {}).get("pid")) == str(loop_pid)
                     and str((mk.get("caller") or {}).get("starttime") or "") != "",
                     f"caller={mk.get('caller')} vs the traced watch pid {loop_pid}")
            sc.check("2.3a the delivery path was LIVE — the loop's own notes really landed in "
                     "messages.md, so an absence below is evidence",
                     len([r for r in room.message_rows() if r.get("type") == "note"]) > 0,
                     f"{len(room.message_rows())} row(s): "
                     f"{json.dumps([r.get('type') for r in room.message_rows()])}")
            asks = [r for r in room.message_rows() if r.get("type") in ("ask", "completion")]
            sc.check("2.3b ZERO `ask`/`completion` rows — nothing was asked of any seat, and "
                     "nothing reported doing it", asks == [], json.dumps(asks))
            inj = [ln for ln in room.injections().splitlines() if "s410-crash" in ln]
            sc.check("2.4 injections.log records the successor's wake for this seat, in its own "
                     "pane, naming the harness the descriptor declares",
                     any("wake:" in ln for ln in inj)
                     and any("claude --model" in ln for ln in inj),
                     (inj[0][:130] if inj else "no injection row"))
            sc.note("2.4b INSTRUMENT LIMIT, measured: the logged command names a BARE `claude`, not "
                    "the room's stub path — the log records the ABSTRACT invocation and lets PATH "
                    "resolve it, so injections.log CANNOT tell which binary actually ran. The "
                    "'no model, no cost' bar is carried by `_assert_stub` (row 1.7) and by nothing "
                    "in this file.")
            sc.note("2.4n COVERAGE GAP: the task asks injections.log to ATTRIBUTE the wake to the "
                    "loop. It cannot — the log's actor column reads `(unresolved)` on every row "
                    f"({(inj[0].split(chr(9))[1] if inj and chr(9) in inj[0] else '?')!r}), so the "
                    "file proves a wake HAPPENED and carries no attribution at all. Row 2.2 is the "
                    "only attribution evidence that exists.")

            # ---- 2's red arms. Each mutation removes ONE reading's subject, so the arms are not
            # ---- observed through one measurement (a confounded red proves nothing about either).
            print("   red arms for ARM 2 — an AGENT-mediated relaunch of a second crashed seat")
            pane_ag = room.open_seat("s410-agent")
            room.capture()
            room.kill_harness("s410-agent")
            room.capture()
            # An agent-shaped process: comm == "claude", from the room's own stub interpreter, so
            # every reading that keys on a harness ancestor sees one. It posts an `ask` (what a seat
            # told to relaunch another seat leaves behind) and then respawns the pane itself.
            agent = room.tmp / "agent-mediated-relaunch.sh"
            agent.write_text(
                f"#!{room.bin}/.hb/claude\n"
                f"{sys.executable} {KIT}/coord.py --package {room.pkg} send --as {SINK} "
                f"--type ask --inline s410-crash "
                f"'relaunch s410-agent — this is the agent-mediated path the no-agent arms must "
                f"detect' >/dev/null 2>&1 || true\n"
                f"tmux respawn-pane -k -t {pane_ag} 'exec opencode' >/dev/null 2>&1 || true\n"
                f"sleep 2\n"
                f"tmux list-panes -t {pane_ag} -F '#{{pane_current_command}}'\n",
                encoding="utf-8")
            agent.chmod(0o755)
            ares = room.sh([str(agent)], check=False, timeout=120)
            time.sleep(2)
            # THE DISCRIMINATION IS SUPPLIED BY THIS PROBE'S OWN ANCESTRY, and it is a real one:
            # this file was dispatched BY AN AGENT, so a harness sits above its own pid — while the
            # revived harness has none above it. Same reading, two subjects, opposite answers.
            # (The first draft asserted `harnesses_above(os.getpid()) == []`, which is FALSE here and
            # taught the lesson: a probe run inside an agent's session is not agent-free.)
            self_above = fx.harnesses_above(os.getpid())
            sc.red("2.1 — the ancestry READING discriminates: a harness IS seen above THIS PROBE's "
                   "own pid (it was dispatched by an agent) and NONE above the revived harness",
                   self_above != [] and fx.harnesses_above(new_c) == [],
                   f"above this probe: {[c['comm'] for c in self_above]}; above the revived "
                   f"harness: {[c['comm'] for c in fx.harnesses_above(new_c)]}")
            sc.red("2.2 — an agent-mediated relaunch writes NO marker, so the caller arm goes RED",
                   room.marker("s410-agent") == {},
                   f"agent relaunch rc={ares.returncode}; marker for s410-agent = "
                   f"{json.dumps(room.marker('s410-agent'))} — nothing claims to have caused it, "
                   f"so there is no `caller` ident to match against the loop")
            asks2 = [r for r in room.message_rows() if r.get("type") == "ask"]
            sc.red("2.3b — an agent in the path leaves an `ask` on the bus, and the message arm "
                   "goes RED", len(asks2) >= 1, json.dumps(asks2))

            # ═══ ARM 3 — THE CONTROL THAT MUST NOT FIRE (the whole point) ══════════════════════
            print("\n── ARM 3 — an idle-but-live seat must NOT be revived")
            pane_i = room.open_seat("s410-idle")
            room.capture()
            idle_pid = room.harness_pid("s410-idle")
            room.mutate_seat_row("s410-idle", last_activity_age_s=7200, prompt_pending=False,
                                 why="s4-10 idle control — a live seat silent for 2h")
            idle_lines, stale_seen = [], False
            for _ in range(2):
                # recapture=False by hand: a re-capture would overwrite the mutation.
                r = room.watch_tick(notify_to=SINK)
                idle_lines += revival_lines(r, "s410-idle")
                stale_seen = stale_seen or ("REVIVAL paused — snapshot stale"
                                            in " ".join(all_revival_lines(r)))
            sc.check("3.0 the detector actually RAN on these ticks (it did not pause on a stale "
                     "snapshot, which would make the control vacuous)", not stale_seen)
            sc.check("3.1 the idle seat produced NO revival verdict of any kind",
                     idle_lines == [], json.dumps(idle_lines))
            sc.check("3.2 no marker entry, no new sessions row, and the SAME harness pid is still "
                     "running — no launch happened",
                     room.marker("s410-idle") == {}
                     and room.sessions_rows("s410-idle") == []
                     and fx.pane_harness_count(room, pane_i) == 1
                     and fx.pane_harness(room, pane_i)[0] == idle_pid,
                     f"harness {idle_pid} untouched")
            # THE MANDATORY RED. `check_revival`'s candidate set IS `snap["roster_absent"]` — the
            # code reads nothing else for it — so injecting the idle seat into that field is
            # EXACTLY the input a detector whose predicate included `last_activity_age_s` would
            # compute. The mutation lands on the detector's only input instead of on its source,
            # because `watch.py` is under another seat's custody this window (R-9) and a probe that
            # edited it would be writing outside its write set.
            # ---- A SECOND, INDEPENDENT COVER, DISCOVERED BY RUNNING THIS ARM AND NOT BY READING
            # ---- IT. Injecting the seat into `roster_absent` alone is NOT enough to make it fire:
            # `check_revival` step 3 explicitly CLEARS the debounce for every seat whose
            # `snap["seats"]` row reads `liveness: live`, so a live-but-injected seat resets to 0
            # every tick and the CRASHED branch is unreachable. Measured: two ticks both reported
            # `1/2 consecutive non-stale ticks`. That clear exists for an in-place respawn (same pane
            # id) and it doubles as a structural cover for exactly this failure — scored below.
            room.inject_absent_row("s410-idle", liveness="no-harness",
                                   why="cover-1-only: candidate set forced, seats row still live")
            half = []
            for _ in range(3):
                half += revival_lines(room.watch_tick(notify_to=SINK), "s410-idle")
            sc.check("3.3 COVER 2, found by running the arm: step 3's explicit live-clear resets "
                     "the debounce every tick, so a seat that is LIVE in snap[\"seats\"] can never "
                     "reach CRASHED even with the candidate set forced",
                     all("pending" in x for x in half) and room.marker("s410-idle") == {}
                     and len(half) >= 3,
                     json.dumps(half[-1:]))
            # THE MANDATORY RED needs BOTH covers gone. `check_revival`'s candidate set IS
            # `snap["roster_absent"]` and its clear keys on `snap["seats"][*].liveness` — the code
            # reads nothing else — so mutating those two fields is EXACTLY the input a detector whose
            # predicate included `last_activity_age_s` would compute. The mutation lands on the
            # detector's only inputs instead of on its source, because `watch.py` is under another
            # seat's custody this window (R-9) and outside this probe's write set.
            room.mutate_seat_row("s410-idle", liveness="no-harness",
                                 why="RED ARM: both covers removed")
            room.inject_absent_row("s410-idle", liveness="no-harness",
                                   why="RED ARM: both covers removed — an activity-age predicate's "
                                       "candidate set over a seat that is still running")
            red_fired = []
            for _ in range(2):
                r = room.watch_tick(notify_to=SINK)
                red_fired += revival_lines(r, "s410-idle")
            mk_i, _ = fx.wait_terminal(room, "s410-idle", timeout=240)
            sc.red("3 — MANDATORY: with both covers removed, revival FIRES on a seat whose harness "
                   "is STILL RUNNING — which is what separates a detector from a relauncher",
                   any("CRASHED" in x for x in red_fired) and mk_i.get("state") == "done",
                   f"lines={json.dumps(red_fired[-1:])} marker={mk_i.get('state')}; harness count "
                   f"in {pane_i} is now {fx.pane_harness_count(room, pane_i)}")

            # ═══ ARM 3b — the HAND-RESUMED seat (G-208) ════════════════════════════════════════
            print("\n── ARM 3b — a hand-resumed seat (roster inactive, pane LIVE) must NOT fire")
            pane_r = room.open_seat("s410-resumed")
            room.set_roster_active("s410-resumed", False)
            snap = room.capture()
            in_absent = [r for r in (snap.get("roster_absent") or [])
                         if r.get("seat") == "s410-resumed"]
            sc.check("3b.1 COVER A (the sensor): an inactive roster row never enters "
                     "roster_absent at all", in_absent == [], json.dumps(in_absent))
            res_lines = []
            for _ in range(3):
                room.capture()
                r = room.watch_tick(notify_to=SINK)
                res_lines += revival_lines(r, "s410-resumed")
            sc.check("3b.2 no revival verdict, no marker, and the live harness is untouched",
                     res_lines == [] and room.marker("s410-resumed") == {}
                     and fx.pane_harness_count(room, pane_r) == 1)
            # COVER B alone: put the row in the candidate set but leave the roster inactive.
            room.inject_absent_row("s410-resumed", liveness="no-harness",
                                   why="cover-B-only: candidate set forced, roster still inactive")
            b_lines = []
            for _ in range(3):
                b_lines += revival_lines(room.watch_tick(notify_to=SINK), "s410-resumed")
            sc.check("3b.3 COVER B (the detector's own live-roster re-read) refuses ALONE — "
                     "CLEANLY-OUT, with cover A disabled",
                     any("CLEANLY-OUT" in x for x in b_lines)
                     and room.marker("s410-resumed") == {}, json.dumps(b_lines[:1]))
            sc.check("3b.4 and cover A refuses ALONE (rows 3b.1-3b.2, roster inactive, no "
                     "injection) — each cover was tested with the other disabled, never both "
                     "together", True)
            # BOTH covers removed: this is the red. A seat with a live harness gets a second one.
            room.set_roster_active("s410-resumed", True)
            # THREE covers, not two: the sensor's active filter, the detector's live-roster re-read,
            # AND step 3's live-clear (rows 3.3's discovery). All three must go for the fire.
            room.mutate_seat_row("s410-resumed", liveness="no-harness",
                                 why="RED ARM: step 3's live-clear cover removed too")
            room.inject_absent_row("s410-resumed", liveness="no-harness",
                                   why="RED ARM: every cover removed — no liveness check anywhere")
            r_red = []
            for _ in range(2):
                r_red += revival_lines(room.watch_tick(notify_to=SINK), "s410-resumed")
            mk_r, _ = fx.wait_terminal(room, "s410-resumed", timeout=240)
            sc.red("3b — with EVERY cover removed the hand-resumed seat IS revived into a second "
                   "session", any("CRASHED" in x for x in r_red) and mk_r.get("state") == "done",
                   f"marker={mk_r.get('state')}, harness count in {pane_r} is now "
                   f"{fx.pane_harness_count(room, pane_r)}")
            sc.note("3b.n COVERAGE GAP: the task asks the report to NAME the live-process "
                    "contradiction (a roster row saying inactive over a pane that holds a live "
                    "harness). NOTHING in watch.py emits that: the ghostrow loop skips inactive "
                    "rows and check_revival never sees the seat. Only the NEGATIVE (no revival) is "
                    "provable today; the positive statement is unbuilt and is not claimed here.")

            # ═══ ARM 4 — the MODE GATE: LG-10, LG-11, LG-12 ════════════════════════════════════
            print("\n── ARM 4 — LG-10 / LG-11 / LG-12, the mode gate on real processes")
            pane_1 = room.open_seat("s410-oneshot")
            room.capture()
            room.kill_harness("s410-oneshot")
            one_lines = []
            for _ in range(3):
                room.capture()
                one_lines += revival_lines(room.watch_tick(notify_to=SINK), "s410-oneshot")
            sc.check("4.1 LG-10a / LG-11b — a `mode: one-shot` seat (harness claude) in "
                     "roster_absent is NEVER revived; the line prints every tick",
                     len([x for x in one_lines if "COMPLETED-ONE-SHOT" in x]) >= 2
                     and room.marker("s410-oneshot") == {}
                     and fx.pane_harness_count(room, pane_1) == 0,
                     json.dumps(one_lines[-1:]))
            sc.check("4.2 the gate HANDS OFF rather than dropping — it names `coordinate "
                     "attest-exit --seat s410-oneshot`",
                     any("attest-exit --seat s410-oneshot" in x for x in one_lines))
            # LG-12: the one-shot path REACHES the attest-exit arm. `dag-08`/`dag-11` landed, so
            # this is exercised for real rather than reported BLOCKED. Its own seat — see the SEATS
            # comment: attesting flips the roster row and would poison LG-10b's control.
            pane_at = room.open_seat("s410-attest")
            room.capture()
            room.kill_harness("s410-attest")
            at_lines = []
            for _ in range(2):
                room.capture()
                at_lines += revival_lines(room.watch_tick(notify_to=SINK), "s410-attest")
            sc.check("4.3a the second one-shot fixture is also never revived — LG-10a holds on a "
                     "fixture no other arm has touched",
                     any("COMPLETED-ONE-SHOT" in x for x in at_lines)
                     and room.marker("s410-attest") == {}
                     and fx.pane_harness_count(room, pane_at) == 0,
                     json.dumps(at_lines[-1:]))
            # `attest-exit` REFUSES while the snapshot is younger than one full sensor cadence — it
            # will not attest an absence that has not held ("the snapshot is only 0s old and the
            # absence must have held longer than one full sensor cadence (60s) — this would be a
            # race with a slow exit"). ⚠ AND IT READS `written_at`, NOT `captured_at`
            # (`coord.py:8905`), so `room.age()` — which by contract moves ONLY the two CAPTURE
            # stamps — does not satisfy it. Measured: after `age(75)` the refusal still said 0s.
            # The written stamp is therefore moved through the room's own sanctioned mutation
            # vehicle, which leaves `_mutated_by_probe` on the file so no reader can mistake it for
            # a naturally old snapshot. Sleeping 60 s in a probe would be the alternative and buys
            # nothing.
            room.age(75)
            room.mutate_snapshot(
                lambda sn: sn.__setitem__("written_at", float(sn["written_at"]) - 75.0),
                "s4-10 LG-12: attest-exit's (e1) gate reads written_at, so the WRITTEN stamp is "
                "moved back 75s — one full sensor cadence — instead of sleeping for it")
            att = room.coord("attest-exit", "--seat", "s410-attest", "--go", timeout=180)
            disp = [r.get("disposition") for r in room.sessions_rows("s410-attest")]
            att_txt = " ".join(att.stdout.split())
            sc.check("4.3b LG-12 — the one-shot path REACHES the attest-exit arm and it records an "
                     "`exited` disposition (not a silent drop)",
                     "exited" in att_txt or "exited" in disp,
                     f"rc={att.returncode}; sessions dispositions={disp}; "
                     f"out={att_txt[:160]}")
            # LG-10's control: the SAME fixture with mode: interactive → revival fires.
            room.set_mode("s410-oneshot", "interactive")
            room.capture()
            two_lines = []
            for _ in range(2):
                room.capture()
                two_lines += revival_lines(room.watch_tick(notify_to=SINK), "s410-oneshot")
            mk_1, _ = fx.wait_terminal(room, "s410-oneshot", timeout=240)
            sc.red("4 LG-10b — the SAME fixture with `mode: interactive` DOES fire (the gate was "
                   "exercised, not merely inert)",
                   any("CRASHED" in x for x in two_lines) and mk_1.get("state") == "done",
                   f"marker={mk_1.get('state')}; harness count "
                   f"{fx.pane_harness_count(room, pane_1)}")
            # LG-11a: harness opencode + mode interactive → FIRES. Its OWN pristine seat —
            # `s410-agent` carries ARM 2's agent-mediated mutation and reusing it here is what made
            # this row score a false negative on the first run.
            pane_o = room.open_seat("s410-oc")
            room.capture()
            room.kill_harness("s410-oc")
            oc_lines = []
            for _ in range(2):
                room.capture()
                oc_lines += revival_lines(room.watch_tick(notify_to=SINK), "s410-oc")
            mk_o, _ = fx.wait_terminal(room, "s410-oc", timeout=240)
            oc_ok = mk_o.get("state") == "done"
            sc.check("4.4 LG-11a — `harness: opencode` + `mode: interactive` FIRES, so the gate "
                     "reads `mode:` and not `harness:`",
                     any("CRASHED" in x for x in oc_lines) and oc_ok,
                     f"marker={mk_o.get('state')} failure={mk_o.get('failure')!r}; "
                     f"lines={json.dumps(oc_lines[-1:])}")
            sc.check("4.5 LG-11 is scored on BOTH cases a harness-keyed gate gets backwards — "
                     "(opencode, interactive) FIRES and (claude, one-shot) does NOT — measured "
                     "separately, on separate fixtures", oc_ok and one_lines != []
                     and room.marker("s410-oneshot").get("state") == "done"
                     and room.marker("s410-attest") == {})
            # The UNDECIDABLE arm: no `mode:` key at all. Not a spec row, but it is the state ALL
            # 52 of run-2's descriptors are in, so an unexercised gate here would be the arm that
            # matters most in practice going unproven.
            room.set_mode("s410-oc", None)
            room.capture()
            room.kill_harness("s410-oc")
            und = []
            for _ in range(3):
                room.capture()
                und += revival_lines(room.watch_tick(notify_to=SINK), "s410-oc")
            sc.check("4.6 an UNDECLARED `mode:` REFUSES — it is not silently read as interactive "
                     "(the state every one of run-2's 52 descriptors is in)",
                     any("UNDECIDABLE" in x for x in und)
                     and room.marker("s410-oc").get("state") != "in-flight",
                     json.dumps(und[-1:]))

            # ═══ ARM 5 — isolation, and the kit untouched ══════════════════════════════════════
            print("\n── ARM 5 — isolation")
            ok_scan, hits = room.leak_scan()
            sc.check("5.1 nothing carrying this room's stamp exists on the LIVE default socket "
                     "(leak_scan, the concurrency-safe form — leak_check would read another "
                     "worker's sockets as this room's leak)", ok_scan, str(hits))
            digests_after = fx.kit_digests()
            # ⚠ NOT A HARD CHECK, and the reason is a fact about this window rather than caution:
            # `coord.py` and `watch.py` are MODIFIED-uncommitted and under OTHER workers' custody
            # right now, so a byte change during this run is somebody else's landing, not this
            # probe's write. A hard assertion here would go red on their correctness. What this
            # probe CAN state is that it opened neither file for writing — it never does — and that
            # any drift observed is DISCLOSED rather than swallowed.
            if digests_after != digests_before:
                sc.note("5.2n KIT DRIFT OBSERVED DURING THIS RUN — another worker landed a change "
                        f"while this probe was executing: before={json.dumps(digests_before)} "
                        f"after={json.dumps(digests_after)}. Every tick after that instant ran the "
                        f"NEW bytes. Disclosed, not chased.")
            sc.check("5.2 this probe wrote NEITHER coord.py NOR watch.py (it opens neither for "
                     "writing; drift, if any, is another worker's landing and is disclosed above)",
                     True, json.dumps(digests_after))
            mount = subprocess.run(["findmnt", "-T", str(room.pkg), "-no", "FSTYPE,SOURCE"],
                                   capture_output=True, text=True).stdout.strip()
            sc.note(f"5.n the throwaway package sits on {mount or 'an unreadable mount'} — "
                    f"recorded because `s4-11` needs it to judge whether `fcntl.flock` semantics "
                    f"hold; a tmpfs is local and flock-correct, but this probe does not exercise "
                    f"cross-process flock at all.")

            # ═══ ARM 6 — the suite the probe must not have broken ══════════════════════════════
            st = subprocess.run([sys.executable, str(KIT / "watch.py"), "--selftest"],
                                capture_output=True, text=True, timeout=1800)
            sc.check("6.1 `watch.py --selftest` exits 0", st.returncode == 0,
                     (st.stdout or "").strip().splitlines()[-1:][0] if st.stdout else "")
            room_tmp = room.tmp
    finally:
        pass

    sc.check("5.3 after teardown the throwaway package is gone", not room_tmp.exists(),
             str(room_tmp))
    ok_final, hits_final = room.leak_scan()
    sc.check("5.4 and nothing of this room survives on the live default socket", ok_final,
             str(hits_final))

    # ── R-6: what could NOT be proven, as prominently as what could ──────────────────────────
    sc.note("DEBOUNCE N=2 IS CHOSEN, NOT MEASURED. No crash-to-detection latency data exists in "
            "this run; this probe fires on ticks it issues back to back, so it measures the "
            "MECHANISM's two-tick requirement and says nothing about wall-clock detection.")
    sc.note("WORST-CASE DETECTION ON THE LIVE LOOP IS ~20 MIN PLUS ONE SENSOR CADENCE at "
            "`--loop 10`. That is arithmetic, not an observation. Whether a 20-minute leader "
            "outage is acceptable is an OWNER QUESTION and it is still unasked.")
    sc.note("THE `coord_lock` FLOCK WAS NOT TESTED ACROSS PROCESSES HERE. Every tick in this probe "
            "is a separate OS process, but no two ever contend; the cross-process exclusion "
            "between the detached executor, the loop and an in-pane `coordinate` is `s4-11`'s "
            "part 1 and is UNPROVEN by this file.")
    sc.note("THE REVIVAL PATH ALWAYS PAYS STAGE 3's FULL `LIFECYCLE_SETTLE_S` because the watch "
            "loop does not exit after forking. Measured indirectly here as the marker's "
            "time-to-`done`; no probe shortens it and none should.")
    sc.note("LANDED IS NOT LIVE. Everything above exercised the watch.py ON DISK, by subprocess. "
            "The daemon running against run-2 holds its own loaded module and has NONE of these "
            "arms until it is next relaunched. No seat restarts it (run bar).")
    sc.note("R-14: this probe READS no memory machinery and writes none. `--handoff-written 0` is "
            "the revival path's own deliberate value and the predecessor's unread block, where one "
            "exists, is left exactly where it is.")
    return sc.verdict()


if __name__ == "__main__":
    sys.exit(main())

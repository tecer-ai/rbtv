#!/usr/bin/env python3
"""probe-s411-revival-renewal-mutex.py — acceptance (b): a revival and a normal renewal racing in
the SAME window produce EXACTLY ONE seat.

Task `s4-11`; spec `stage-4-revival-spec.md` §6(b) and §2 (the interlock). Two parts, and they test
different things:

  PART 1 — THE MUTEX. 20 GENUINELY CONCURRENT, GENUINELY CROSS-PROCESS claimants (10 `revive`, 10
  `renew`) against ONE seat, all through `watch.py`'s `claim_revival` under `coord.coord_lock`.
  Exactly 1 claims, 19 stand down. Then the same burst with the flock FORCED TO FAIL: the claim must
  REFUSE rather than race (fail-closed — with a single shared marker file the lock is the ONLY
  mutex, so a lockless claim IS the double-launch).

  PART 2 — END-TO-END. The seat runs `checkout --renew --handoff …` under STAGE 3's OWN SIGKILL test
  wrapper (`probe-lifecycle-exec.run_caller`, imported — a second wrapper would be a second
  definition of "the instant the marker appears" and the two would disagree). The caller dies, the
  detached executor proceeds alone, and there is a REAL window in which the pane is dead AND the
  marker is `in-flight` with a LIVE executor. A watch tick inside it must say MID-RENEWAL, and at
  settle exactly ONE harness and exactly ONE new `sessions.csv` row.

⚠ WHY ROW 1 ALONE PROVES NOTHING ABOUT CONCURRENCY, measured here rather than assumed. Re-run the
same 20 claimants SERIALISED and the answer is still 1/19 — the first claim leaves a marker entry
and every later claimant stands down on the ENTRY, never on the lock. So "1 success, 19 stand-downs"
is insensitive to whether the claimants overlapped at all. What IS concurrency-sensitive is the pair
in rows 1.5/1.6: with the `held` check removed, CONCURRENT claimants produce MORE THAN ONE claim
while SERIALISED ones still produce exactly one. That pair, and not row 1, is the evidence that the
flock is what produced the one.

⚠ THE MID-RENEWAL VERDICT DEPENDS ON PLAIN pid+starttime EQUALITY, never `ident_is_live_harness`
(`coord.py:1574`): `is_harness_argv` (`:1492`) matches only claude/codex/opencode basenames and the
lifecycle executor is a PYTHON process, so the harness predicate reports every live executor DEAD
and turns MID-RENEWAL into CRASHED. Row 3's red arm swaps exactly that predicate and shows the
double launch appear.

RUN IT (`--go` IS MANDATORY — see the guard block in `revival-fixture.py`; without it the hourly
`probe-suite-scheduled.py` timer would start this run and SIGKILL it at 180 s, leaking the room):
         cd /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit
         python3 -u probes/probe-s411-revival-renewal-mutex.py --go

Exit 0 = every arm passed · 1 = a property is broken · 2 = INOPERATIVE (could not run, or a red arm
did not go red — its green partner is then vacuous, which is the same refusal).

Self-invocation modes, used by this probe's own arms and not by a human:
  --claim   one claimant: load watch.py, optionally break the lock or lie about `held`, call
            `claim_revival`, write the outcome as JSON. This is what makes a claimant a REAL,
            SEPARATE OS PROCESS rather than a thread pretending to be one.
  --tick    one watch pass, optionally with `_executor_ident_live` swapped for the harness
            predicate — row 3's red arm. Runs `watch.main()`, so the real argument parser and the
            real pass are exercised, not a hand-built namespace.

Runtime ~6 min. Peak memory is the 20-claimant burst; the probe MEASURES available memory first and
REFUSES (exit 2) below a floor, because this box has an uncontained memory-runaway failure mode.
"""

import argparse
import importlib.util
import json
import os
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

N_CLAIMANTS = 20                 # the spec's number: 10 revive + 10 renew
# The burst is 20 python processes each importing coord.py + watch.py. Refuse below this rather than
# contribute to the box's uncontained OOM failure mode (six global kills, 2026-07-28/29).
MIN_FREE_MB_FOR_BURST = 1200

SEATS = (
    {"seat": "s411-mutex", "harness": "claude", "mode": "interactive"},
    {"seat": "s411-e2e", "harness": "claude", "mode": "interactive"},
    {"seat": "s411-red", "harness": "claude", "mode": "interactive"},
    {"seat": "s411-cover", "harness": "claude", "mode": "interactive"},
    {"seat": "s411-sink", "harness": "claude", "mode": "interactive"},
)
SINK = "s411-sink"
HANDOFF = "s4-11 probe handoff: exists only to prove the renewal path wrote one."


def load_by_path(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═════════════════════════════ self-invocation: ONE CLAIMANT ═════════════════════════════════════

def claim_worker(a):
    """Call `claim_revival` once, in this process, and write the outcome as JSON.

    The two mutations are applied AT THE SEAM and nowhere else:
      --break-lock  `coord._acquire_flock` raises, which is precisely how a read-only package
                    behaves (`coord.py:540-541`) and is the fallback `coord.py`'s own selftest row
                    T5 already forces. `coord_lock` then yields False and the claim must REFUSE.
      --lie-held    `coord.coord_lock` is wrapped to yield True regardless — i.e. THE `held` CHECK
                    REMOVED from the claim's point of view, with no real lock underneath. An
                    implementation that ignored `held` would pass the locked run and fail only here.
    """
    import contextlib
    w = load_by_path(WATCH_PY, "watch_probe")
    if a.break_lock or a.lie_held:
        def _boom(fh):
            raise OSError("probe: flock FORCED to fail (s4-11 row 1.4 / 1.5)")
        w.coord._acquire_flock = _boom
    if a.lie_held:
        _orig = w.coord.coord_lock

        @contextlib.contextmanager
        def _liar(base):
            with _orig(base) as _held:
                yield True
        w.coord.coord_lock = _liar
        # ⚠ AND THE READ→WRITE WINDOW IS WIDENED, DELIBERATELY, because without it this red arm is a
        # COIN FLIP. Measured across three runs of the identical burst: 2 claims, 1, 2. With no lock
        # the critical section's read-modify-write is ~100 µs on tmpfs and 20 processes share 4
        # cores, so whether a second claimant reads "no entry" before the first writes is pure
        # scheduling — and a red arm that goes red only sometimes is not a red arm.
        #
        # THE DELAY GOES IMMEDIATELY BEFORE THE WRITE, not at the first read, and the placement is
        # the whole point: a delay at `coord.load_workers` (the section's FIRST read) still lets a
        # slow claimant's MARKER read land after a fast one's write — measured, that variant gave 2
        # of 20. Sleeping inside `coord.atomic_write` puts every claimant's READ before any
        # claimant's WRITE, which is exactly the interleaving a missing mutex permits, and makes the
        # arm deterministic instead of lucky. Applied ONLY in `--lie-held` mode; the SERIALISED
        # counterpart runs with the SAME delay, so the multiplicity is attributable to the missing
        # lock and not to the delay.
        _aw = w.coord.atomic_write

        def _slow_atomic_write(path, text, *args, **kw):
            time.sleep(0.5)
            return _aw(path, text, *args, **kw)
        w.coord.atomic_write = _slow_atomic_write
    base = Path(a.package) / "coordination"
    if a.barrier:
        deadline = time.time() + 60
        while not Path(a.barrier).exists() and time.time() < deadline:
            time.sleep(0.002)
    notes = []
    t0 = time.monotonic()
    try:
        outcome, why = w.claim_revival(base, a.seat, a.pane, notes, {},
                                      disposition=a.disposition)
    except Exception as exc:                                     # noqa: BLE001 — reported, not hidden
        outcome, why = "BROKE", repr(exc)
    # THE NOTE BODY RIDES BACK, not just its count. R-8's bar is that the REFUSAL NAMES ITS LAYER,
    # and the layer string leads the NOTE — `claim_revival`'s return `why` is a short internal
    # reason ("lock unavailable — fail-closed, no claim written") and carries no layer at all.
    # Asserting the layer against `why` scored a false FAIL on the first run; the note is where the
    # reader of the bus actually sees it. (`Flag` subclasses `str`, watch.py:851.)
    rec = {"outcome": outcome, "why": why, "disposition": a.disposition, "pid": os.getpid(),
           "notes": len(notes), "note0": (str(notes[0]) if notes else ""),
           "t": round(time.monotonic() - t0, 4), "started": round(time.time(), 4)}
    Path(a.out).write_text(json.dumps(rec) + "\n", encoding="utf-8")
    print(json.dumps(rec))
    return 0


def tick_worker(a):
    """One real `watch.main()` pass, optionally with the executor-liveness predicate SWAPPED."""
    w = load_by_path(WATCH_PY, "watch_probe")
    if a.swap_liveness:
        def _harness_predicate(entry):
            ex = (entry or {}).get("executor") or {}
            try:
                return w.coord.ident_is_live_harness((ex.get("pid"), ex.get("starttime")))
            except Exception:                                     # noqa: BLE001
                return False
        w._executor_ident_live = _harness_predicate
    sys.argv = ["watch.py", "--package", a.package, "--notify",
                "--notify-to", SINK, "--notify-fallback", SINK]
    w.main()
    return 0


# ═════════════════════════════ helpers ═══════════════════════════════════════════════════════════

def revival_lines(res, seat):
    """The seat's REVIVAL lines from one tick, WHITESPACE-NORMALIZED — `check_revival` pads its
    columns to 18/7 chars, so a literal `f'{seat} REVIVAL'` grep never matches."""
    src = res.get("stdout") if isinstance(res, dict) else res.stdout
    out = []
    for ln in (src or "").splitlines():
        norm = " ".join(ln.split())
        if norm.startswith(seat + " ") and "REVIVAL" in norm.upper():
            out.append(norm)
    return out


def burst(room, seat, pane, n=N_CLAIMANTS, concurrent=True, break_lock=False, lie_held=False,
          tag="run"):
    """`n` claimants against ONE seat. Returns (records, kinds).

    HOW THE CLAIMANTS ARE MADE CROSS-PROCESS, and why three kinds and not one (row 2): 18 are plain
    `Popen` children, ONE is DETACHED (`setsid` + `start_new_session`, the shape Stage 3's executor
    has), and ONE runs IN A TMUX PANE inside the room — the in-pane `coordinate` claimant the task
    requires, because 20 identical in-process calls would leave the cross-process claim untested.
    A barrier file releases them together, so `concurrent=True` really overlaps."""
    d = room.tmp / f"claims-{tag}"
    d.mkdir(parents=True, exist_ok=True)
    go = d / "GO"
    procs, kinds = [], {}
    for i in range(n):
        disp = "revive" if i < n // 2 else "renew"
        out = d / f"c{i:02d}.json"
        argv = [sys.executable, str(Path(__file__).resolve()), "--claim",
                "--package", str(room.pkg), "--seat", seat, "--pane", pane or "",
                "--disposition", disp, "--out", str(out)]
        if concurrent:
            argv += ["--barrier", str(go)]
        if break_lock:
            argv.append("--break-lock")
        if lie_held:
            argv.append("--lie-held")
        if i == 0:
            kinds["detached"] = True
            procs.append((out, subprocess.Popen(["setsid", *argv], env=room.env(),
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL,
                                                start_new_session=True)))
        elif i == 1:
            # IN-PANE: a real tmux pane on this room's private server runs the claimant, so the
            # claim crosses a pane boundary as an in-pane `coordinate` would.
            kinds["in_pane"] = True
            room.tmux("new-window", "-d", "-t", f"{room.session}:", "-n", f"claim{tag}",
                      "-c", str(room.pkg))
            room.tmux("send-keys", "-t", f"{room.session}:claim{tag}",
                      " ".join(f"'{x}'" if " " in str(x) else str(x) for x in argv), "Enter")
            procs.append((out, None))
        else:
            kinds["subprocess"] = True
            procs.append((out, subprocess.Popen(argv, env=room.env(),
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL)))
        if not concurrent:
            # SERIALISED: wait for this one to finish before starting the next. The control that
            # shows row 1 is insensitive to overlap.
            go.write_text("go", encoding="utf-8")
            dl = time.time() + 60
            while not out.exists() and time.time() < dl:
                time.sleep(0.01)
    if concurrent:
        time.sleep(1.5)                       # let every claimant reach the barrier
        go.write_text("go", encoding="utf-8")
    for out, p in procs:
        if p is not None:
            try:
                p.wait(timeout=120)
            except subprocess.TimeoutExpired:
                p.kill()
    dl = time.time() + 90
    while time.time() < dl and sum(1 for o, _ in procs if o.exists()) < n:
        time.sleep(0.05)
    recs = []
    for out, _ in procs:
        if out.exists():
            try:
                recs.append(json.loads(out.read_text(encoding="utf-8")))
            except ValueError:
                pass
    return recs, kinds


def clear_marker(room):
    p = room.pkg / "coordination" / "lifecycle-inflight.json"
    if p.exists():
        p.unlink()


def main():
    ap = argparse.ArgumentParser(prog="probe-s411", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claim", action="store_true")
    ap.add_argument("--tick", action="store_true")
    ap.add_argument("--package")
    ap.add_argument("--seat")
    ap.add_argument("--pane", default="")
    ap.add_argument("--disposition", default="revive")
    ap.add_argument("--out")
    ap.add_argument("--barrier")
    ap.add_argument("--break-lock", action="store_true")
    ap.add_argument("--lie-held", action="store_true")
    ap.add_argument("--swap-liveness", action="store_true")
    ap.add_argument("--go", action="store_true",
                    help="MANDATORY for the acceptance run — see revival-fixture.py's guard block")
    a = ap.parse_args()
    if a.claim:
        return claim_worker(a)
    if a.tick:
        return tick_worker(a)
    return run(a)


def run(a):
    fx = load_by_path(FIXTURE_PY, "revival_fixture")
    if not a.go:
        return fx.refuse_unattended(Path(__file__).resolve())
    problems = fx.preflight(extra_bins=("ps", "setsid"))
    free_mb = 0
    try:
        for ln in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ln.startswith("MemAvailable:"):
                free_mb = int(ln.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        problems.append("cannot read /proc/meminfo, so the burst's memory cost is unmeasurable")
    if free_mb and free_mb < MIN_FREE_MB_FOR_BURST:
        problems.append(f"only {free_mb} MB available; the {N_CLAIMANTS}-claimant burst needs "
                        f"≥{MIN_FREE_MB_FOR_BURST} MB and this box has an uncontained memory-"
                        f"runaway failure mode — REFUSING rather than contributing to it")
    if problems:
        print("INOPERATIVE — preflight refused:")
        for p in problems:
            print(f"  · {p}")
        return 2

    sc = fx.Score(min_checks=22, min_reds=4)
    ar = fx.load_room_module()
    exec_probe = fx.load_exec_probe()             # Stage 3's SIGKILL wrapper, imported not rebuilt
    RevivalRoom = fx.make_room_class(ar)
    digests_before = fx.kit_digests()
    room = RevivalRoom(seats=SEATS)
    print(f"probe-s411 — room stamp {room.stamp}   session {room.session}   tmpdir {room.tmp}")
    print(f"             {free_mb} MB available before the burst\n")

    with room:
        fx.assert_private_socket(room.env(), room)
        sc.check("0. isolation asserted BEFORE anything opened", True, f"{room.tmp}/tt")

        # ═══ PART 1 — THE MUTEX ════════════════════════════════════════════════════════════════
        print("── PART 1 — the mutex: 20 concurrent cross-process claimants, one seat")
        pane_m = room.open_seat("s411-mutex")
        room.capture()
        recs, kinds = burst(room, "s411-mutex", pane_m, tag="locked")
        claimed = [r for r in recs if r["outcome"] in ("CLAIMED", "RE-CLAIMED")]
        stood = [r for r in recs if r["outcome"] == "STOOD-DOWN"]
        sc.check("1.1 all 20 claimants reported", len(recs) == N_CLAIMANTS,
                 f"{len(recs)}/{N_CLAIMANTS}: "
                 f"{json.dumps(sorted({r['outcome'] for r in recs}))}")
        sc.check("1.2 LOCKED run — exactly 1 success and 19 stand-downs",
                 len(claimed) == 1 and len(stood) == N_CLAIMANTS - 1,
                 f"{len(claimed)} claimed / {len(stood)} stood down; winner "
                 f"disposition={claimed[0]['disposition'] if claimed else '-'}")
        sc.check("1.3 the winner's disposition is on the marker and there is exactly ONE entry",
                 list(room.marker().keys()) == ["s411-mutex"]
                 and room.marker("s411-mutex").get("state") == "in-flight",
                 json.dumps(room.marker()))
        sc.check("2.1 the claimants are genuinely cross-process AND of three kinds — ≥1 plain "
                 "subprocess, ≥1 DETACHED, ≥1 IN A TMUX PANE (20 identical in-process calls would "
                 "leave the cross-process claim untested)",
                 kinds.get("subprocess") and kinds.get("detached") and kinds.get("in_pane")
                 and len({r["pid"] for r in recs}) == len(recs),
                 f"kinds={sorted(kinds)}, {len({r['pid'] for r in recs})} distinct pids")
        spread = (max(r["started"] for r in recs) - min(r["started"] for r in recs)) if recs else 0
        sc.check("2.2 and they genuinely OVERLAPPED — every claimant entered the critical section "
                 "inside one short window after the barrier released",
                 spread < 15, f"first-to-last claim start spread {spread:.3f}s")

        # ---- 1.4 the LOCKLESS-FORCED run: fail-closed, not racing ----
        clear_marker(room)
        recs_l, _ = burst(room, "s411-mutex", pane_m, break_lock=True, tag="lockless")
        claimed_l = [r for r in recs_l if r["outcome"] in ("CLAIMED", "RE-CLAIMED")]
        refused_l = [r for r in recs_l if r["outcome"] == "REFUSED"]
        sc.check("1.4 LOCKLESS-FORCED run — ZERO successes; every claimant REFUSES rather than "
                 "racing, and each pushes exactly ONE note",
                 len(claimed_l) == 0 and len(refused_l) == len(recs_l)
                 and all(r["notes"] == 1 for r in refused_l),
                 f"{len(claimed_l)} claimed / {len(refused_l)} refused; "
                 f"notes={sorted({r['notes'] for r in recs_l})}; "
                 f"why[0]={(refused_l[0]['why'] if refused_l else '')[:90]}")
        sc.check("1.4b and the refusal NAMES ITS LAYER in the NOTE the room will read (R-8: a "
                 "reader must not mistake a tool gate for the harness permission classifier). ⚠ NOT "
                 "in the returned `why`, which is a short internal reason with no layer — measured",
                 bool(refused_l)
                 and all(r.get("note0", "").startswith("revival claim gate") for r in refused_l),
                 (refused_l[0].get("note0", "")[:120] if refused_l else "no refusal recorded"))
        sc.check("1.4c nothing was written — no marker entry exists after 20 lockless claims",
                 room.marker() == {}, json.dumps(room.marker()))

        # ---- 1.5 / 1.6 THE CONCURRENCY-SENSITIVE PAIR — the real evidence ----
        clear_marker(room)
        recs_r, _ = burst(room, "s411-mutex", pane_m, lie_held=True, concurrent=True, tag="red")
        claimed_r = [r for r in recs_r if r["outcome"] in ("CLAIMED", "RE-CLAIMED")]
        sc.red("1.5 — with the `held` check removed (no real lock, `held` forced True) CONCURRENT "
               "claimants produce MORE THAN ONE claim",
               len(claimed_r) > 1,
               f"{len(claimed_r)} claims from {len(recs_r)} claimants — an implementation that "
               f"ignored `held` passes the LOCKED run and fails only here (the read->write window "
               f"is widened 0.5 s in this mode; see claim_worker's note on why an un-widened arm is "
               f"a coin flip)")
        clear_marker(room)
        recs_s, _ = burst(room, "s411-mutex", pane_m, lie_held=True, concurrent=False, tag="serial")
        claimed_s = [r for r in recs_s if r["outcome"] in ("CLAIMED", "RE-CLAIMED")]
        sc.red("2 — SERIALISED, the same lock-less burst yields exactly ONE claim, so row 1.2 is "
               "insensitive to overlap and is VACUOUS ON ITS OWN",
               len(claimed_s) == 1,
               f"serialised {len(claimed_s)} claim(s) vs concurrent {len(claimed_r)} — SAME "
               f"mutation, SAME 0.5 s widening, only the overlap differs, so the multiplicity is "
               f"the missing lock's and not the delay's. Rows 1.5/1.6 are the pair that "
               f"discriminates, not row 1.2")
        sc.note("1.n WHAT ROW 1.2 ACTUALLY PROVES is that a claimant stands down on an EXISTING "
                "marker ENTRY. The flock's contribution is proven only by the 1.5/1.6 pair "
                "(concurrent-without-lock → many; serialised-without-lock → one). Reported this "
                "way because the spec's row, read literally, would have been scored green by an "
                "implementation with no lock at all.")

        # ═══ PART 2 — END-TO-END: exactly one seat ═════════════════════════════════════════════
        print("\n── PART 2 — end-to-end: the caller dies mid-renewal, the executor proceeds alone")
        clear_marker(room)
        pane_e = room.open_seat("s411-e2e")
        room.capture()
        old_e = room.harness_pid("s411-e2e")
        n_sess_0 = len(room.sessions_rows("s411-e2e"))
        exec_probe.AR = ar
        res = exec_probe.run_caller(room, "s411-e2e", True, "marker", timeout=240)
        sc.check("3.1 the caller was SIGKILLed WHILE ALIVE, the instant the marker appeared — "
                 "measured from its wait status, not assumed from timing",
                 res["killed_while_alive"] is True and res["rc"] == -9,
                 f"rc={res['rc']} killed_while_alive={res['killed_while_alive']} "
                 f"at {res['kill_at']}s")
        # ⚠ THE WINDOW IS NARROW AND IT MUST BE HUNTED, NOT ASSUMED. Two measured facts shape this:
        #   (a) at the instant the marker APPEARS the `executor` ident is still ABSENT — the CALLER
        #       stamps the entry before forking and the CHILD stamps its own (pid, starttime) at its
        #       guard 5, so a reading taken 0.3 s after the kill sees `executor={}` (measured);
        #   (b) the seat only enters `roster_absent` once the executor has KILLED the pane, and it
        #       leaves again the moment the pane is respawned — a sub-second-to-few-second slice of a
        #       ~10 s renewal.
        # So this POLLS: capture + tick, repeatedly, for as long as the marker reads `in-flight`,
        # recording the executor ident seen at each tick. Asserting on a single hand-timed reading
        # would have been a coin flip dressed as a control.
        seen_mid, ex_seen, ticks_taken = [], {}, 0
        deadline = time.time() + 90
        while time.time() < deadline:
            mk_live = room.marker("s411-e2e")
            if mk_live.get("state") != "in-flight":
                break
            ex = (mk_live.get("executor") or {})
            if ex.get("pid") and fx.alive(ex.get("pid")):
                ex_seen = ex
            # ⚠ AND THE CANDIDATE SET HAS TO BE SUPPLIED, because the NATURAL one is uncatchable
            # here — measured: 23 capture+tick cycles inside a live window never caught it. A
            # `renew` respawns the pane with `tmux respawn-pane -k`, which replaces the pane's
            # process ATOMICALLY, so the only instant at which the pane exists with NO harness is
            # the sub-second gap before the harness comes up, while one capture+tick costs ~4 s.
            # `check_revival`'s candidate set is `snap["roster_absent"]` and NOTHING ELSE, and the
            # snapshot is by design up to one SENSOR CADENCE stale — which is exactly the condition
            # the MID-RENEWAL branch exists to survive. So the row is scored on a snapshot that
            # carries the seat as absent WHILE a genuinely live executor holds the marker: a real
            # stale snapshot over a real in-flight renewal, with the injection stamped on the file.
            room.capture()
            room.inject_absent_row("s411-e2e", liveness="no-harness",
                                   why="a snapshot one sensor cadence stale, taken while a LIVE "
                                       "executor holds the marker — the MID-RENEWAL condition")
            ticks_taken += 1
            seen_mid += revival_lines(room.watch_tick(notify_to=SINK), "s411-e2e")
            if any("MID-RENEWAL" in x for x in seen_mid):
                break
        sc.check("3.2 there IS a real window: while the marker read `in-flight` its executor was a "
                 "LIVE process, observed by this probe from /proc",
                 bool(ex_seen) and str(ex_seen.get("starttime") or "") != "",
                 f"executor={ex_seen} over {ticks_taken} tick(s) inside the window")
        lines_e = seen_mid
        # ⚠⚠ THE SPEC NAMES THE WRONG LINE, AND THE SYSTEM IS RIGHT. `stage-4-revival-spec.md:347`
        # expects `MID-RENEWAL` from a tick inside a renewal window. MEASURED: the tick stands down
        # with **CLEANLY-OUT**, twice over — `cmd_checkout` writes the seat into
        # `awaiting-close.json` AND flips its roster row BEFORE the marker is ever consulted, and
        # CLEANLY-OUT is evaluated BEFORE MID-RENEWAL in the disposition order. So on a real
        # `checkout --renew` the marker branch is UNREACHABLE — not broken, PRE-EMPTED by two
        # cheaper covers. The PROPERTY the row exists for (exactly one successor) holds; the LINE
        # the row predicts does not appear, and a probe that asserted the line would have reported a
        # correct system as broken. Rows 3.3b / red arm 3 below then prove MID-RENEWAL is reachable
        # and load-bearing on the shape where it IS the only cover.
        sc.check("3.3 a watch tick INSIDE the window STANDS DOWN — no CRASHED verdict, no claim, no "
                 "fire, so no second successor can appear",
                 bool(lines_e) and not any("CRASHED" in x for x in lines_e)
                 and room.marker("s411-e2e").get("disposition") == "renew",
                 json.dumps(lines_e[-2:]))
        sc.check("3.3a and the branch that fires is CLEANLY-OUT, NOT the MID-RENEWAL the spec "
                 "predicts — `cmd_checkout`'s awaiting-close debt and roster flip pre-empt the "
                 "marker branch entirely on a real renewal",
                 any("CLEANLY-OUT" in x for x in lines_e),
                 "spec §6(b) expects MID-RENEWAL here; the system emits CLEANLY-OUT and is correct")
        sc.note("3.3n DISCLOSED: the candidate-set membership for rows 3.2/3.3 is INJECTED into the "
                "real capture, not waited for. The natural window — pane present, harness not yet up "
                "during an in-place `respawn-pane -k` — is sub-second and was NOT caught in 24 "
                "consecutive capture+tick cycles against a live executor. The injected condition is "
                "the one the branch is written for (a snapshot up to one sensor cadence stale) and "
                "the executor holding the marker was a REAL live process read from /proc.")
        mk_e, secs_e = fx.wait_terminal(room, "s411-e2e", timeout=300)
        sc.check("3.4 the executor completed alone", mk_e.get("state") == "done",
                 f"in {secs_e:.1f}s, {len(fx.steps(mk_e))} steps")
        sc.check("3.5 EXACTLY ONE live harness in the seat's pane at settle",
                 fx.pane_harness_count(room, pane_e) == 1,
                 f"old {old_e} -> {fx.pane_harness(room, pane_e)[0]}")
        sc.check("3.6 EXACTLY ONE new sessions.csv row",
                 len(room.sessions_rows("s411-e2e")) == n_sess_0 + 1,
                 f"{n_sess_0} -> {len(room.sessions_rows('s411-e2e'))}")
        sc.check("3.7 the handoff block the renewal exists to carry IS in the seat's memory.md",
                 exec_probe.HANDOFF in (room.pkg / "seats" / "s411-e2e" /
                                        "memory.md").read_text(encoding="utf-8")
                 or HANDOFF in (room.pkg / "seats" / "s411-e2e" /
                                "memory.md").read_text(encoding="utf-8"))

        # ---- 3.3b + RED ARM 3: the shape where MID-RENEWAL IS the only cover ------------------
        # A REVIVE-initiated claim leaves NO awaiting-close record and does NOT flip the roster
        # (`revival_fork_argv` passes `--handoff-written 0` precisely because no checkout preceded
        # it), so for that shape the marker branch is the ONLY thing standing between a live
        # executor and a second launch. That is the shape this arm builds, and the green and the red
        # differ in the PREDICATE and nothing else.
        print("   3.3b + red arm 3 — MID-RENEWAL as the ONLY cover, then the predicate swapped")
        pane_x = room.open_seat("s411-red")
        room.capture()
        room.kill_harness("s411-red")
        room.capture()
        # A GENUINELY LIVE executor ident that is genuinely NOT a harness: this probe's own process.
        # `_executor_ident_live` (plain pid+starttime) must call it alive; `ident_is_live_harness`
        # must call it dead, because `is_harness_argv` matches only claude/codex/opencode basenames
        # and this is python. That divergence IS the defect under test.
        marker_body = {"s411-red": {
            "disposition": "revive", "state": "in-flight", "pane": pane_x,
            "stamped-at": time.strftime("%Y-%m-%d %H:%M"),
            "executor": {"pid": os.getpid(), "starttime": fx.starttime(os.getpid())},
            "caller": {"pid": os.getpid(), "starttime": fx.starttime(os.getpid())},
            "steps-completed": []}}
        (room.pkg / "coordination" / "lifecycle-inflight.json").write_text(
            json.dumps(marker_body, indent=2) + "\n", encoding="utf-8")
        green_lines = []
        for _ in range(3):
            room.capture()
            green_lines += revival_lines(room.watch_tick(notify_to=SINK), "s411-red")
        sc.check("3.3b MID-RENEWAL IS REACHABLE AND IS LOAD-BEARING: on a revive-shaped in-flight "
                 "claim (no awaiting-close record, roster still active) the loop stands down on the "
                 "MARKER alone, with a live non-harness executor",
                 any("MID-RENEWAL" in x for x in green_lines)
                 and not any("CRASHED" in x for x in green_lines)
                 and fx.pane_harness_count(room, pane_x) == 0,
                 json.dumps(green_lines[-1:]))
        # Restore the same fixture (the ticks above may have annotated it) and swap the predicate.
        (room.pkg / "coordination" / "lifecycle-inflight.json").write_text(
            json.dumps(marker_body, indent=2) + "\n", encoding="utf-8")
        lines_x = []
        for _ in range(3):
            room.capture()
            red_tick = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--tick", "--swap-liveness",
                 "--package", str(room.pkg)], capture_output=True, text=True, timeout=600,
                env=room.env())
            lines_x += revival_lines({"stdout": red_tick.stdout}, "s411-red")
            if any("CRASHED" in x for x in lines_x):
                break
        time.sleep(2)
        n_h = fx.pane_harness_count(room, pane_x)
        sc.red("3 — with `ident_is_live_harness` in place of plain pid+starttime equality the tick "
               "reports the LIVE executor DEAD and classifies the seat CRASHED — the exact "
               "double-launch this group exists to disprove",
               any("CRASHED" in x for x in lines_x)
               and not any("MID-RENEWAL" in x for x in lines_x),
               f"lines={json.dumps(lines_x[-1:])}; harness count in {pane_x} after the mutant tick "
               f"= {n_h} (the seat had none before it)")
        sc.note("3.rn THE MUTANT'S SECOND SUCCESSOR IS REPORTED, NOT ASSERTED. What the arm asserts "
                "is the MIS-CLASSIFICATION — CRASHED over a live executor — because that is the "
                "fault; whether a second harness is observable at one instant depends on which "
                "in-place respawn lands last, and an assertion on the count would be an assertion "
                "on a race.")

        # ═══ PART 3 — THE TWO RACE COVERS, each with the other disabled ════════════════════════
        print("\n── PART 3 — the two race covers, tested one at a time")
        clear_marker(room)
        pane_c = room.open_seat("s411-cover")
        room.capture()
        room.kill_harness("s411-cover")
        # ⚠ ORDER IS THE ARM. Capture FIRST, WITH the roster row still ACTIVE, and only THEN flip it
        # — because that is the race the cover exists for: `cmd_close_seat` flips the row BEFORE it
        # kills the pane, so the SNAPSHOT (up to one sensor cadence old) can still carry the seat in
        # `roster_absent` while the LIVE roster already reads not-active. Flipping before the capture
        # instead would keep the seat out of `roster_absent` altogether (`absent_rows` skips
        # inactive rows) and the detector's re-read would never be reached — a green produced by the
        # SENSOR's filter, scored as if the detector had refused. Measured on the s4-10 run, where
        # the same shape made an arm pass for the wrong reason.
        room.capture()
        room.set_roster_active("s411-cover", False)
        cov_a = []
        for _ in range(3):
            # recapture=False by hand: a re-capture would drop the seat out of roster_absent and the
            # detector would have nothing to refuse.
            cov_a += revival_lines(room.watch_tick(notify_to=SINK), "s411-cover")
        sc.check("4.1 COVER A ALONE (snapshot still carries the seat as absent, LIVE roster already "
                 "flipped active:no, marker ABSENT) — the detector's in-section roster re-read says "
                 "CLEANLY-OUT: no claim, no fire",
                 any("CLEANLY-OUT" in x for x in cov_a) and room.marker("s411-cover") == {},
                 json.dumps(cov_a[-1:]))
        # COVER B alone: roster back to ACTIVE, and a fresh in-flight marker whose executor is a
        # LIVE process (this probe's own pid, which is genuinely alive and genuinely not a harness).
        room.set_roster_active("s411-cover", True)
        room.capture()
        base = room.pkg / "coordination"
        (base / "lifecycle-inflight.json").write_text(json.dumps({"s411-cover": {
            "disposition": "renew", "state": "in-flight", "pane": pane_c,
            "stamped-at": time.strftime("%Y-%m-%d %H:%M"),
            "executor": {"pid": os.getpid(), "starttime": fx.starttime(os.getpid())},
            "caller": {"pid": os.getpid(), "starttime": fx.starttime(os.getpid())},
            "steps-completed": []}}, indent=2) + "\n", encoding="utf-8")
        cov_b = []
        for _ in range(3):
            cov_b += revival_lines(room.watch_tick(notify_to=SINK), "s411-cover")
        sc.check("4.2 COVER B ALONE (roster ACTIVE, fresh in-flight marker with a LIVE executor) — "
                 "MID-RENEWAL, no claim, no fire",
                 any("MID-RENEWAL" in x for x in cov_b)
                 and room.marker("s411-cover").get("disposition") == "renew",
                 json.dumps(cov_b[-1:]))
        sc.check("4.3 each cover was scored with the OTHER disabled — testing both together would "
                 "have proven neither", True)
        # RED: BOTH covers removed — roster active, marker gone. The seat IS claimed and fired.
        clear_marker(room)
        cov_r = []
        for _ in range(2):
            cov_r += revival_lines(room.watch_tick(notify_to=SINK), "s411-cover")
        mk_c, _ = fx.wait_terminal(room, "s411-cover", timeout=300)
        sc.red("4 — with BOTH covers removed the seat IS claimed and revived, so each cover's "
               "refusal above was a refusal and not an inert path",
               any("CRASHED" in x for x in cov_r) and mk_c.get("state") == "done",
               f"marker={mk_c.get('state')}; lines={json.dumps(cov_r[-1:])}")

        # ═══ PART 4 — the filesystem the flock lives on, and isolation ═════════════════════════
        mount = subprocess.run(["findmnt", "-T", str(room.pkg), "-no", "FSTYPE,SOURCE,TARGET"],
                               capture_output=True, text=True).stdout.strip()
        sc.check("5.1 the package's filesystem is RECORDED", bool(mount), mount)
        sc.note("5.n FLOCK SEMANTICS ON THIS MOUNT — an UNPROVEN assumption, labelled as one. The "
                f"throwaway package sits on `{mount}`. `fcntl.flock` is correct on local ext4/xfs "
                "and on tmpfs; it degrades on some network filesystems. Rows 1.2-1.6 above ARE the "
                "first cross-process evidence in this goal that the exclusion holds — 20 separate "
                "OS processes, one of them detached and one of them in a tmux pane, all contending "
                "on the same `.lock` — but they prove it FOR THIS MOUNT ONLY. The LIVE run package "
                "is on a different filesystem and was NOT tested; carrying this result there is a "
                "`Convenience` assumption and is not made here.")
        ok_scan, hits = room.leak_scan()
        sc.check("6.1 nothing carrying this room's stamp is on the LIVE default socket "
                 "(leak_scan — leak_check is not concurrency-safe while other workers run)",
                 ok_scan, str(hits))
        # ⚠ DISCLOSED, NOT ASSERTED: `coord.py` and `watch.py` are MODIFIED-uncommitted under other
        # workers' custody this window, so a byte change mid-run is their landing, not this probe's
        # write. A hard assertion would go red on somebody else's correctness.
        if fx.kit_digests() != digests_before:
            sc.note(f"6.2n KIT DRIFT during this run: before={json.dumps(digests_before)} "
                    f"after={json.dumps(fx.kit_digests())} — another worker landed while this probe "
                    f"executed; later claimants ran the NEW bytes. Disclosed, not chased.")
        sc.check("6.2 this probe wrote NEITHER coord.py NOR watch.py (it opens neither for "
                 "writing; drift, if any, is disclosed above)", True,
                 json.dumps(fx.kit_digests()))
        for label, cmd, cwd in (("watch.py --selftest", [str(WATCH_PY), "--selftest"], None),
                                ("coord.py selftest", [str(KIT / "coord.py"), "selftest"], KIT)):
            st = subprocess.run([sys.executable, *cmd], capture_output=True, text=True,
                                timeout=1800, cwd=str(cwd) if cwd else None)
            tail = [l for l in (st.stdout or "").splitlines() if l.strip()][-1:] or [""]
            sc.check(f"7. `{label}` exits 0", st.returncode == 0, tail[0])
        room_tmp = room.tmp

    sc.check("6.3 after teardown the throwaway package is gone", not room_tmp.exists(),
             str(room_tmp))

    sc.note("R-14: part 2's `--handoff` is Stage 2's existing mechanism exercised as-is. This probe "
            "neither extends nor builds memory machinery.")
    sc.note("LANDED IS NOT LIVE: every tick above ran the watch.py ON DISK by subprocess. The "
            "daemon watching run-2 holds its own loaded module and has none of these arms until it "
            "is next relaunched. No seat restarts it (run bar).")
    return sc.verdict()


if __name__ == "__main__":
    sys.exit(main())

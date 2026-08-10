#!/usr/bin/env python3
"""probe-goal-watcher-revival.py — the seat-revival ACTUATOR lives in the watcher job (7.662).

WHAT IT SCORES. `watch.py`'s `fire_revival` was the system's ONLY deterministic seat-recovery
actuator, and owner ruling `decisions.md#d-seat-revival-kept-in-watcher-job` moved it into
`goal-watcher-job.py`, acting through the exec door that file already owns. Task 7.35 deletes
`watch.py`; if the actuator did not actually land here first, the system loses its only means of
restarting a seat whose pane is down and NOTHING in the suite would say so — the three probes
that covered the old home (`probe-s410-revival-no-agent`, `probe-s411-revival-renewal-mutex`,
`probe-lifecycle-exec`) all point at `watch.py` and all go away with it.

⚠ THE FOUR PROPERTIES, AND WHY EACH IS A SEPARATE ARM RATHER THAN ONE "REVIVAL WORKS":
  · the ACT is here at all (R1);
  · it is DERIVED from the door declaration and not fired at everything (R2) — reviving a DOOR
    severs the channel its human is reachable through (`r-owner-afk-liaison-parked`, G-176);
  · the exec surface did NOT grow to make room for it (R3) — `INLINE_FIX_SCRIPTS` is what makes
    this file's act-identity claim enforceable, and widening it to fit the revival would have
    traded the whole property for the feature;
  · NO RAW SENSING came with it (R4) — `revival_fork_target` called tmux directly three times,
    and team-monitor being the sole raw sensor is the architecture, not a preference.

RED-FIRST. Set `RBTV_PROBE_TREE` to an alternative rbtv repo root and every arm re-runs against
THAT tree's `goal-watcher-job.py`. Pointed at a pre-7.662 tree, R1/R2/R3/R4 go red and C0 stays
green — which is what makes the green run a measurement rather than a restatement. The knob has
exactly one purpose and it is this one; `TARGET` derives solely from it, with no fallback path
to the live tree, so pointing it at an empty directory fails C0 rather than silently passing.

ARMS
  C0  THE FIXTURE IS REAL: a non-door roster-ACTIVE row whose pane holds no harness still gets
      its GHOSTROW leader flag carrying `close-seat <seat> --renew`, and ONE reading still gets
      only `GHOSTROW-PENDING`. Both hold in EITHER tree — this arm is what proves the fixture
      reaches the row the R arms then measure, and that the revival is ADDITIVE rather than a
      row that moved.
  R1  THE ACT IS HERE: the debounced non-door ghost ALSO yields a `REVIVAL` decision whose
      `fix` execs the `--coord` path with `lifecycle-exec --disposition revive
      --handoff-written 0`, carrying the caller (pid, starttime) PAIR and no `--force`.
  R2  DERIVED, NOT BLANKET: the SAME fixture with that seat declaring `relays:` yields NO
      revival row at all, WHILE the non-door one does — both halves in one arm, so the arm
      cannot pass on a tree that simply never revives anything.
  R3  THE SAME DOOR, UNWIDENED: `INLINE_FIX_SCRIPTS` is exactly `("team_monitor.py",
      "coord.py")` AND the detached door refuses a non-allowlisted program with the SAME
      refusal text the inline door gives — one gate, two doors.
  R4  NO RAW SENSING FOLLOWED IT: the target is derived from the snapshot — a row whose pane
      left the room and a snapshot with no live pane yield an EMPTY target and a refusal, never
      a guess — and the module CALLS none of `watch.py`'s three tmux reads (measured over its
      AST, not its text: the file NAMES all three in the prose explaining their absence).

⚠ AN ABSENT TARGET IS THE FAILURE, NEVER A SKIP. If `goal-watcher-job.py` is missing or will not
import, this probe FAILS. INOPERATIVE (exit 2) is for the probe itself being unable to run.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-revival` —
never by hand (`G-163`). Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import ast as _ast
import importlib.util
import os
import sys
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# The target's module-level imports are POSIX-only (`jobcontain` -> fcntl + resource). Neither is
# touched by the pure predicates under test, so on a non-POSIX host they are stubbed rather than
# letting the probe report INOPERATIVE — a probe that can only run on one OS measures nothing on
# the other, and `ModuleNotFoundError` reads as evidence while measuring exactly nothing.
for _m, _attrs in (("fcntl", {"LOCK_EX": 2, "LOCK_NB": 4, "flock": lambda *a: None}),
                   ("resource", {"RLIMIT_AS": 9, "RLIMIT_CPU": 0, "RLIM_INFINITY": -1,
                                 "getrlimit": lambda k: (-1, -1),
                                 "setrlimit": lambda k, v: None})):
    try:
        __import__(_m)
    except ImportError:
        _mod = types.ModuleType(_m)
        _mod.__dict__.update(_attrs)
        sys.modules[_m] = _mod

HERE = Path(__file__).resolve().parent
# HERE = <root>/ignite/jobs/probes -> parents[2] is the rbtv repo root. `RBTV_PROBE_TREE` is the
# RED-FIRST knob (see the docstring): it re-points every arm at another tree's sources.
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "jobs" / "goal-watcher-job.py"
OUT = HERE / "probe-goal-watcher-revival.out"

# The three raw tmux reads `watch.py`'s `revival_fork_target` made. They are what MUST NOT follow
# the actuator into a file whose whole architecture is "team-monitor is the sole raw sensor".
TMUX_READS = ("live_panes", "tmux_pane_window_name", "tmux_find_window_pane")

SEAT = "worker-ghost"
COORD = "/nonexistent/co ord.py"
PKG = "/nonexistent/pk g"

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


def load_target():
    spec = importlib.util.spec_from_file_location("gwj_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gwj_under_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def fixture(now):
    """ONE snapshot: a ghost row (pane present, no harness) plus a live pane to anchor onto."""
    return {
        "captured_at": now, "captured_at_iso": "fixture",
        "headless": [], "headless_source": {"readable": True, "reason": ""},
        "roster_absent": [
            {"seat": SEAT, "pane": "%1", "liveness": "no-harness",
             "reason": "roster row active, pane present but no harness process"},
        ],
        "seats": [
            {"seat": "bystander", "pane": "%9", "roster_active": True, "liveness": "live",
             "last_activity_age_s": 1, "ctx_pct": None},
        ],
    }


def drive(gwj, doors, now, passes):
    """Run `passes` consecutive evaluations over ONE state, returning the LAST decision set.

    Consecutive passes are required by construction: GHOSTROW is debounced, so a single pass
    reaches the PENDING row and never the fired one.

    `ident` is the caller (pid, starttime) pair the job resolves ONCE in `main` and passes on
    `args` — supplied here as a FIXTURE so this probe needs no `/proc` and runs on any host."""
    args = gwj._ns(door_seats=set(doors), coord=COORD, package=PKG,
                   caller_ident=(4242, "99"))
    state, decisions = {}, []
    for _ in range(passes):
        decisions = gwj.evaluate(fixture(now), args, state, {}, now)[0]
    return decisions


def rows(decisions, cls, seat=SEAT):
    return [d for d in decisions if d["class"] == cls and d["subject"] == seat]


def main():
    if not TARGET.exists():
        # ⚠ NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist — the actuator cannot live in a file "
                           f"that is gone")
        return
    src = TARGET.read_text(encoding="utf-8")
    gwj = load_target()
    now = time.time()
    passes = getattr(gwj, "GHOSTROW_DEBOUNCE_PASSES", 2)
    fired = drive(gwj, set(), now, passes)
    one = drive(gwj, set(), now, 1)
    door = drive(gwj, {SEAT}, now, passes)

    # ---- C0: the fixture reaches the row, in EITHER tree, and the flag is not replaced.
    ghost = rows(fired, "GHOSTROW")
    ghost_rem = " || ".join(d.get("remedy") or "" for d in ghost)
    pending = rows(one, "GHOSTROW-PENDING")
    check("C0", bool(ghost) and "close-seat" in ghost_rem and "--renew" in ghost_rem
          and bool(pending) and not rows(one, "GHOSTROW"),
          f"debounced ghost still carries its leader flag (remedy={ghost_rem[-60:]!r}); one "
          f"reading is still PENDING only ({[d['class'] for d in one if d['subject'] == SEAT]})")

    # ---- R1: the ACT is here.
    rev = rows(fired, "REVIVAL")
    fix = rev[0].get("fix") if rev else None
    argv = list(fix[1]) if fix else []

    def operand(flag):
        return argv[argv.index(flag) + 1] if flag in argv else None

    check("R1", len(rev) == 1 and fix is not None and fix[0] == COORD
          and argv[:1] == ["lifecycle-exec"]
          and operand("--disposition") == "revive"
          and operand("--handoff-written") == "0"
          and operand("--seat") == SEAT
          and operand("--tmux-target") == "%1"
          and operand("--caller-pid") == "4242" and operand("--caller-starttime") == "99"
          and not [t for t in argv if t.startswith("--force")],
          f"{len(rev)} REVIVAL row(s); fix program={(fix or ('', []))[0]!r}; argv={argv}")

    # ---- R2: derived from the declaration, and BOTH halves in one arm so it cannot pass on a
    # tree that never revives anything at all.
    check("R2", not rows(door, "REVIVAL") and len(rev) == 1,
          f"the SAME seat declaring `relays:` yields {len(rows(door, 'REVIVAL'))} revival "
          f"row(s) while the un-declared one yields {len(rev)}; the door's classes are "
          f"{[d['class'] for d in door if d['subject'] == SEAT]}")

    # ---- R3: one gate, two doors, and the allowlist is the SAME two programs.
    allow = getattr(gwj, "INLINE_FIX_SCRIPTS", None)
    detached = getattr(gwj, "run_revival", None)
    if detached is None:
        check("R3", False, "this tree has no `run_revival` — there is no detached door, so the "
                           "revival either does not exist or reaches its program another way")
    else:
        out, why = detached("/usr/bin/ignite", ["lifecycle-exec"], "unit-never-created")
        _, inline_why = gwj.run_inline("/usr/bin/ignite", ["add-job"])
        check("R3", allow == ("team_monitor.py", "coord.py") and out == "REFUSED"
              and why == inline_why,
              f"INLINE_FIX_SCRIPTS={allow}; detached door -> {out}; refusal identical to the "
              f"inline door's: {why == inline_why}")

    # ---- R4: the target is snapshot-derived and refuses rather than guessing.
    target_fn = getattr(gwj, "revival_target", None)
    if target_fn is None:
        check("R4", False, "this tree has no `revival_target` — nothing derives a target from "
                           "the snapshot, so the no-raw-sensing half cannot hold")
    else:
        gone, why_gone = target_fn({"seat": SEAT, "pane": "", "liveness": "absent"},
                                   {"seats": []})
        anchored, _ = target_fn({"seat": SEAT, "pane": "%1", "liveness": "absent"},
                                fixture(now))
        # ⚠ OVER THE AST, NEVER OVER THE TEXT, and the distinction is the same one the door
        # probe makes about command forms vs bare verbs: this file NAMES all three reads in the
        # prose that explains why they did not follow the actuator, so a substring scan would
        # fire on the fix's own account of itself. What must be absent is a CALL, not a word.
        called = {getattr(n, "attr", None) or getattr(n, "id", None)
                  for n in _ast.walk(_ast.parse(src))
                  if isinstance(n, (_ast.Attribute, _ast.Name))}
        raw = sorted(t for t in TMUX_READS if t in called)
        check("R4", gone == "" and "NO ANCHOR" in why_gone.upper() and anchored == "%9"
              and not raw,
              f"no pane and no live anchor -> target={gone!r} (refusal: {why_gone[:48]!r}…); a "
              f"departed pane re-places onto the snapshot's live pane -> {anchored!r}; "
              f"watch.py's raw tmux reads present in this file: {raw}")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-revival  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)

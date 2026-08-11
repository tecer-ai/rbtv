#!/usr/bin/env python3
"""probe-goal-watcher-homings.py — the three behaviours task 7.35 moved INTO the watcher job.

WHAT IT SCORES. `watch.py` is deleted by 7.35. Three of its behaviours were ruled HOME here rather
than retired (owner ratification of the Phase-A dossier, run decision D7), and each one is
invisible to every other probe in the suite:

  B3   the DECLARED-CAP census — `watch.py:1486 check_budget`. Three states that must stay three:
       no budget declared (SILENT), declared and readable (a verdict), declared and UNREADABLE
       (LOUD — the room has NO capacity signal). Collapsing the third into the first is the exact
       defect the loud branch exists to prevent, and it is what hid a wrong path for a whole run.
  B17  a FLAG IS NEVER SENT TO THE SEAT IT IS ABOUT — `watch.py:flag_recipient`. Found as a special
       case (a context warning about the LEADER delivered to the leader, which holds its own
       close/renew/approve with no seat above it and an AFK owner) and closed as a general rule,
       because pointing the flags at any single named seat moves the hole to that seat.
  L    the REVIVAL ATTEMPT LADDER — `watch.py:2436 revival_ladder`. The substitutes 7.662 named
       (`armed`, systemd's unit-name refusal, coord's entry guard 3) cover DOUBLE-LAUNCH well and
       cover RUNAWAY not at all: a flag whose delivery fails is left UNARMED by design, so one
       episode can reach the fire repeatedly. This arm measures the cap and its re-arm.

RED-FIRST. `RBTV_PROBE_TREE` re-points every arm at another rbtv repo root. Pointed at a tree from
before this change, B3-*, B17-DIVERT and L-* go red while C0 stays green — which is what makes the
green run a measurement rather than a restatement. `TARGET` derives SOLELY from that knob, with no
fallback to the live tree, so an empty directory fails C0 rather than silently passing.

FIXTURE-DRIVEN (run decision D4): every arm runs off dicts and a temp directory. No tmux, no
/proc, no room, no systemd — it runs on any host, which is what lets a red-first control be run
next to the green one.

ARMS
  C0  THE FIXTURE IS REAL: the same snapshot still produces the pass's ordinary rows in EITHER
      tree, so the arms below measure an ADDITION and not a fixture that reaches nothing.
  B3-SILENT   a package with NO budget.json emits NO capacity row at all.
  B3-LOUD     a package whose budget.json is UNREADABLE emits a row saying the check is DOWN —
              and it is a DIFFERENT row from silence, both halves scored in one arm.
  B3-BREACH   a readable cap of 1 against 2 counted live panes emits OVER CAPACITY; the SAME
              fixture under a cap of 9 emits nothing. Both halves, so the arm cannot pass on a
              tree that flags everything or nothing.
  B17-DIVERT  a judgment row ABOUT the primary recipient resolves to the FALLBACK; a row about
              anyone else still resolves to the primary. Both halves.
  B17-ORPHAN  when subject, primary and fallback are one seat the flag is delivered ANYWAY and
              the reason SAYS SO — a monitor with nowhere impartial to report must say that.
  L-CAP       the ladder allows exactly `len(REVIVAL_ATTEMPTS)` attempts and refuses the next,
              and the refused attempt does NOT advance the counter.
  L-REARM     a pass in which the seat no longer asks to be revived drops its spent attempts, so
              the cap bounds ONE episode and not the seat's whole life.

Run it through the suite — `node ignite/deploy/probe-suite.js --only goal-watcher-homings`.
Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

# The target's module-level imports are POSIX-only (`jobcontain` -> fcntl + resource). Nothing
# under test here touches either, so they are stubbed rather than reporting INOPERATIVE: a probe
# that can only run on one OS measures nothing on the other.
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
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "jobs" / "goal-watcher-job.py"
OUT = HERE / "probe-goal-watcher-homings.out"

LEADER = "leader"
DEPUTY = "deputy"
SEAT = "worker-a"

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


def snapshot(now, live_panes=2):
    """A FRESH snapshot with `live_panes` counted agent panes and nothing else wrong."""
    seats = [{"seat": f"w{i}", "pane": f"%{i}", "roster_active": True, "liveness": "live",
              "harness_pid": 1000 + i, "harness": "claude", "agent_type": "worker",
              "agent_type_source": "descriptor", "last_activity_age_s": 1, "ctx_pct": None}
             for i in range(live_panes)]
    return {
        "captured_at": now, "captured_at_iso": "fixture",
        "headless": [], "headless_source": {"readable": True, "reason": ""},
        "roster_absent": [], "seats": seats,
        "box": {"available_mb": 8000, "cores": 4, "load5": 0.1, "swap_used_mb": 0},
    }


def budget(cap):
    return {"schema": "run-budget/1", "cap": {"agent_panes": cap},
            "counting": {"counts_toward_cap": ["staff", "worker", "verifier"]},
            "floors": {"launch_refuse_mb": 2000}}


def evaluate_in(gwj, pkg, now, live_panes=2):
    args = gwj._ns(door_seats=set(), coord="/nonexistent/coord.py", package=str(pkg),
                   room_package=str(pkg), caller_ident=(4242, "99"))
    return gwj.evaluate(snapshot(now, live_panes), args, {}, {}, now)[0]


def capacity_rows(decisions):
    return [d for d in decisions if d["class"] == "BUDGET"]


def main():
    if not TARGET.exists():
        # NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist")
        return
    gwj = load_target()
    now = time.time()

    with tempfile.TemporaryDirectory() as td:
        silent = Path(td) / "silent"
        loud = Path(td) / "loud"
        breach = Path(td) / "breach"
        roomy = Path(td) / "roomy"
        for d in (silent, loud, breach, roomy):
            d.mkdir()
        (loud / "budget.json").write_text("{ this is not json", encoding="utf-8")
        (breach / "budget.json").write_text(json.dumps(budget(1)), encoding="utf-8")
        (roomy / "budget.json").write_text(json.dumps(budget(9)), encoding="utf-8")

        d_silent = evaluate_in(gwj, silent, now)
        d_loud = evaluate_in(gwj, loud, now)
        d_breach = evaluate_in(gwj, breach, now)
        d_roomy = evaluate_in(gwj, roomy, now)

        # ---- C0: the fixture reaches the pass at all, in EITHER tree.
        check("C0", isinstance(d_silent, list) and not [x for x in d_silent
                                                        if x["class"] == "STALE-SENSOR"],
              f"a fresh snapshot evaluates to {len(d_silent)} row(s) and is NOT gated by the "
              f"staleness tripwire (classes={sorted({x['class'] for x in d_silent})})")

        # ---- B3-SILENT
        check("B3-SILENT", not capacity_rows(d_silent),
              f"no budget.json -> {len(capacity_rows(d_silent))} capacity row(s); a package that "
              f"declares nothing must stay silent or this row cannot ship kit-wide")

        # ---- B3-LOUD: declared-but-unreadable is a DIFFERENT fact from declared-nothing.
        loud_rows = capacity_rows(d_loud)
        loud_txt = " ".join((r["action"] + " " + r["detail"]) for r in loud_rows)
        check("B3-LOUD", len(loud_rows) == 1 and "DOWN" in loud_txt.upper()
              and "NO CAPACITY SIGNAL" in loud_txt.upper() and not capacity_rows(d_silent),
              f"an UNREADABLE budget.json -> {len(loud_rows)} row(s) saying the check is down, "
              f"while ABSENCE stays silent — the two are not collapsed "
              f"({loud_txt[:90]!r})")

        # ---- B3-BREACH: both halves, so the arm cannot pass on a tree that flags everything.
        br = capacity_rows(d_breach)
        br_txt = " ".join((r["action"] + " " + r["detail"]) for r in br)
        check("B3-BREACH", len(br) == 1 and "OVER CAPACITY" in br_txt.upper()
              and "2" in br_txt and not capacity_rows(d_roomy),
              f"2 counted live panes against a cap of 1 -> {len(br)} OVER CAPACITY row; the SAME "
              f"two panes against a cap of 9 -> {len(capacity_rows(d_roomy))} row(s) "
              f"({br_txt[:90]!r})")

    # ---- B17: routing. `room_snap` carries both candidate recipients LIVE, so the divert can
    # only come from the rule and never from one of them being unreachable.
    room = {"seats": [
        {"seat": LEADER, "liveness": "live", "harness_pid": 11},
        {"seat": DEPUTY, "liveness": "live", "harness_pid": 12},
        {"seat": SEAT, "liveness": "live", "harness_pid": 13},
    ]}
    a2 = gwj._ns(to=LEADER, fallback_to=DEPUTY)
    about_leader = {"class": "CTX", "subject": LEADER, "nudge": "leader"}
    about_other = {"class": "CTX", "subject": SEAT, "nudge": "leader"}
    to_a, why_a = gwj.resolve_recipient(room, a2, about_leader)
    to_b, why_b = gwj.resolve_recipient(room, a2, about_other)
    check("B17-DIVERT", to_a == DEPUTY and to_b == LEADER,
          f"a judgment row ABOUT '{LEADER}' resolves to {to_a!r} ({why_a[:70]!r}); a row about "
          f"'{SEAT}' still resolves to {to_b!r} — the divert is the SUBJECT's, not a fallback "
          f"that fires for everything")

    a1 = gwj._ns(to=LEADER, fallback_to=LEADER)
    to_c, why_c = gwj.resolve_recipient(room, a1, about_leader)
    check("B17-ORPHAN", to_c == LEADER and "ORPHAN" in why_c.upper(),
          f"subject, primary and fallback are one seat -> delivered to {to_c!r} AND the reason "
          f"records it: {why_c[-90:]!r}")

    # ---- L: the attempt ladder. Pure over `state`, so the bound is measured without firing.
    ladder = getattr(gwj, "revival_ladder", None)
    prune = getattr(gwj, "prune_revival_attempts", None)
    cap_tuple = getattr(gwj, "REVIVAL_ATTEMPTS", None)
    if ladder is None or prune is None or cap_tuple is None:
        check("L-CAP", False, "this tree carries no `revival_ladder`/`prune_revival_attempts`/"
                              "`REVIVAL_ATTEMPTS` — the revival path has NO attempt bound, which "
                              "is the runaway the port exists to close")
        check("L-REARM", False, "no ladder to re-arm")
    else:
        st = {}
        got = [ladder(st, SEAT) for _ in range(len(cap_tuple) + 2)]
        allowed = [g[0] for g in got]
        spent_after = (st.get("_revival_attempts") or {}).get(SEAT)
        check("L-CAP", allowed[:len(cap_tuple)] == [True] * len(cap_tuple)
              and set(allowed[len(cap_tuple):]) == {False}
              and spent_after == len(cap_tuple)
              and len(cap_tuple) == len(set(cap_tuple)),
              f"attempts allowed={allowed} against a cap of {len(cap_tuple)} "
              f"({cap_tuple}); the counter stopped at {spent_after} rather than climbing past "
              f"the bound")

        prune(st, {"someone-else"})
        after = ladder(st, SEAT)
        check("L-REARM", (st.get("_revival_attempts") or {}).get(SEAT) == 1 and after[0] is True,
              f"a pass with no revival row for '{SEAT}' drops its spent attempts, so the next "
              f"episode starts at 1 again (allowed={after[0]}, spent="
              f"{(st.get('_revival_attempts') or {}).get(SEAT)})")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-goal-watcher-homings  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)

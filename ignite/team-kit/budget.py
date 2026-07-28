#!/usr/bin/env python3
"""Compare a run's DECLARED capacity against the LIVE census, and refuse to guess.

    budget.py [--package DIR] [--json] [--selftest]

Two inputs, both already owned by someone else:

    {run}/budget.json   the DECLARED cap + counting convention   (writer: master)
    {run}/state.json    the LIVE census                          (writer: team-monitor)

This module OBSERVES NOTHING ITSELF. It never reads tmux, /proc, or a harness
file. team-monitor is the room's only raw-source sensor (settle ledger R24), and
a second pane-reader would be a second sensor -- the exact failure that
architecture exists to prevent. Everything here is arithmetic over the snapshot.

WHY IT EXISTS: run-2 spent a night at 1-2 executors against an "executor budget
of 2" that appeared in no ruling surface. It was a past census, written into a
seat's memory.md, carried across a renewal, and read by the successor as live
policy. A capacity number with no home decays into folklore. This turns the
number into something a machine recomputes every pass instead of remembering.

THREE THINGS IT REFUSES TO DO, each because the run got burned by the opposite:

  1. It never reports a confident number off a STALE snapshot. A stale
     state.json means the sensor is the incident; headroom computed from a
     frozen room would authorize launches into a room that no longer exists.
     Verdict goes UNKNOWN, loudly, and UNKNOWN is not a synonym for zero.

  2. It never silently absorbs an UNCLASSIFIED seat. An aggregate over a
     partly-unclassified population must report its own incompleteness rather
     than a whole-looking number.

  3. It never lets a live agent harness hide behind "no descriptor" -- but
     "no descriptor" is NOT the predicate, and getting that wrong is what the
     first draft of this module did.

     state.json's `class_source: no-seat` means "no descriptor IN THIS RUN".
     It does NOT mean "no descriptor anywhere". The staffer is summoned on
     demand, is deliberately not a run member, and is declared in its OWN
     goal folder -- so the first draft flagged it as an undeclared agent, and
     would have done so ON EVERY SUMMONS, BY CONSTRUCTION. That is standing
     bar 20's measured failure (11 of 12 per-seat flags were false positives)
     and G-194's cost: a usually-wrong flag trains its reader to ignore the
     real one. The flag would have been worse than no flag.

     The predicate is ACCOUNTABILITY, not run membership, and it names nobody:

         a live agent pane is UNACCOUNTED when its cwd does not resolve to a
         seat folder holding a seat.md -- in ANY goal, not just this run.

     The staffer resolves (.rbtv/goals/staffer-goal/seats/staffer/seat.md), so
     it is accounted. No name list, no staffer special case, and it generalizes
     to any future on-demand seat from any goal.

     This reads a DECLARATION (a descriptor file at a path the snapshot already
     carries), never a raw observation source, so R24's single-sensor invariant
     is untouched -- same category of read as budget.json itself.

     ⚠ AND IT IS STILL NOT ENOUGH TO FLAG ON, WHICH IS THE FINDING. The
     predicate must survive at least three legitimate descriptor-less agent
     panes: the staffer (resolves -- fine), the owner door (carries class
     master -- fine), and THE OWNER'S OWN CLAUDE SESSION ON THIS BOX, whose cwd
     is the vault root and resolves to nothing. MEASURED, not reasoned:
     resolve_descriptor("/home/henri/ht-wkdir/second-brain") -> None.

     An owner session and a leaked agent pane are OBSERVATIONALLY IDENTICAL in
     the snapshot: live agent harness, no roster row, no descriptor. Nothing in
     state.json separates them, so no predicate over state.json can. UNDECLARED
     and UNOWNED are different claims and this data cannot tell them apart.

     ⇒ SO THE UNACCOUNTED SET IS REPORTED, NEVER FLAGGED. It prints for a human
     who asks; it never wakes anyone. Shipping it as a flag would have coached
     the chief-of-staff to close the owner's own session -- which is G-176,
     already fixed once in this system. The BREACH flag (more agent panes live
     than declared) carries no such ambiguity and is the only thing watch.py
     pushes.

BINDING BAR, inherited from task 7.80 and restated because this is exactly the
module that would breach it: NOTHING HERE MAY EVER GATE A PERMISSION ON `class`.
The field is a sensor's observation of a descriptor's claim, never an
authorization; the identity gate is the only authorization. The moment anything
keys a permission on it, editing a descriptor becomes granting a privilege.
This module reports capacity. It launches nothing, refuses nothing, kills
nothing.
"""

import argparse
import json
import os
import sys
import time

# Harnesses that make a pane an AGENT pane. A live process from this set with no
# seat descriptor is undeclared, never uncounted.
AGENT_HARNESSES = {"claude", "codex", "opencode", "kimi", "gemini", "aider"}

# A snapshot older than this is not evidence. team-monitor's cadence is seconds;
# a minute of silence already means something is wrong with the sensor.
STALE_AFTER_S = 120


def find_package(start=None):
    """Walk up for the run folder, the way coordinate and teamview do."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, "state.json")) and os.path.exists(
            os.path.join(d, "budget.json")
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def resolve_descriptor(cwd):
    """Does this pane's cwd resolve to a declared seat? Returns the seat.md path or None.

    Accepts the seat folder itself or any child of it, and walks up to the goals
    root so a seat working in a subfolder still resolves. Reads a DECLARATION,
    never a raw observation source.
    """
    if not cwd:
        return None
    d = os.path.abspath(cwd)
    for _ in range(8):  # bounded: never walk to /
        cand = os.path.join(d, "seat.md")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    return None


def _load(path, what):
    if not os.path.exists(path):
        return None, "%s is ABSENT at %s" % (what, path)
    try:
        with open(path) as fh:
            return json.load(fh), None
    except Exception as exc:  # corrupt beats silently-empty
        return None, "%s is UNREADABLE at %s: %s" % (what, path, exc)


def census(budget, state, now=None, resolver=resolve_descriptor):
    """Arithmetic over the snapshot. Returns a dict; raises nothing."""
    now = now if now is not None else time.time()
    counting = budget.get("counting", {})
    counts_toward = set(counting.get("counts_toward_cap") or [])
    cap = (budget.get("cap") or {}).get("agent_panes")
    floor = (budget.get("floors") or {}).get("ram_available_mb")

    captured = state.get("captured_at")
    age = None if captured is None else round(now - float(captured), 1)
    stale = age is None or age > STALE_AFTER_S

    counted, unaccounted, cross_goal, unclassified, free = [], [], [], [], []
    for s in state.get("seats") or []:
        name = (s.get("seat") or "").strip()
        cls = s.get("class")
        src = s.get("class_source")
        harness = (s.get("harness") or "").strip().lower()
        live = s.get("liveness") == "live"
        row = {
            "seat": name or None,
            "pane": s.get("pane"),
            "class": cls,
            "class_source": src,
            "harness": harness or None,
            "liveness": s.get("liveness"),
            "cwd": s.get("cwd"),
        }
        if not live:
            free.append(row)  # a dead pane spends nothing
        elif cls in counts_toward:
            counted.append(row)
        elif src == "no-seat" and harness in AGENT_HARNESSES:
            # Rule 3. NOT "no descriptor in this run" -- that fires on every
            # staffer summons. Ask whether ANY goal declares it.
            desc = resolver(s.get("cwd"))
            if desc:
                row["descriptor"] = desc
                cross_goal.append(row)  # accounted elsewhere; ruled not to count here
            else:
                unaccounted.append(row)  # nothing anywhere explains this pane
        elif cls == "unclassified":
            # Rule 2: a descriptor exists and is silent. Neither counted nor
            # dropped -- surfaced, so the aggregate declares its own hole.
            unclassified.append(row)
        else:
            free.append(row)

    # cross_goal is deliberately NOT in in_use: an on-demand seat from another
    # goal is ruled not to count against this run's cap. It still spends RAM,
    # which is why it is reported and why the RAM floor -- not the cap -- is the
    # gate that actually protects the box.
    in_use = len(counted) + len(unaccounted)
    complete = not unclassified and not stale

    if stale:
        verdict = "UNKNOWN"
        headroom = None
    elif cap is None:
        verdict = "UNKNOWN"
        headroom = None
    elif in_use > cap:
        verdict = "BREACH"
        headroom = cap - in_use
    else:
        verdict = "OK" if complete else "OK-INCOMPLETE"
        headroom = cap - in_use

    box = state.get("box") or {}
    avail = box.get("available_mb")
    ram_ok = None if (avail is None or floor is None) else avail >= floor

    return {
        "verdict": verdict,
        "cap": cap,
        "in_use": in_use,
        "headroom": headroom,
        "complete": complete,
        "snapshot_age_s": age,
        "stale": stale,
        "stale_after_s": STALE_AFTER_S,
        "ram_available_mb": avail,
        "ram_floor_mb": floor,
        "ram_ok": ram_ok,
        "counted": counted,
        "unaccounted": unaccounted,
        "cross_goal": cross_goal,
        "unclassified": unclassified,
        "not_counted": free,
    }


def render(c):
    """One block a human or a watch loop can paste. Never a bare number."""
    out = []
    head = "budget: %s -- %s of %s agent panes in use" % (
        c["verdict"],
        c["in_use"],
        c["cap"] if c["cap"] is not None else "?",
    )
    if c["headroom"] is not None:
        head += ", %d free" % c["headroom"]
    out.append(head)

    if c["stale"]:
        out.append(
            "  ** SNAPSHOT STALE (%s s, limit %s) -- THE SENSOR IS THE INCIDENT. "
            "No headroom figure is offered; UNKNOWN is not zero. Restart team-monitor."
            % (c["snapshot_age_s"], c["stale_after_s"])
        )
    if c["verdict"] == "BREACH":
        out.append(
            "  ** OVER THE CAP by %d -- more agent panes are live than the run declared."
            % (-c["headroom"])
        )
    if c["unclassified"]:
        out.append(
            "  ** %d seat(s) UNCLASSIFIED (descriptor exists and is silent) -- "
            "counted in NEITHER direction, so the figure above is INCOMPLETE: %s"
            % (
                len(c["unclassified"]),
                ", ".join((r["seat"] or r["pane"] or "?") for r in c["unclassified"]),
            )
        )
    if c["unaccounted"]:
        # REPORTED, NEVER FLAGGED -- see the module docstring, rule 3. An owner
        # session looks exactly like this and must never be coached toward close.
        out.append(
            "  note: %d UNACCOUNTED agent pane(s) -- live agent harness whose cwd resolves to "
            "NO seat.md in any goal. Counted (they spend a pane and RAM). MAY BE LEGITIMATE: "
            "an owner session is indistinguishable from a leak here, so this is information, "
            "never an alarm: %s"
            % (
                len(c["unaccounted"]),
                ", ".join(
                    "%s(%s @ %s)" % (r["pane"], r["harness"], r.get("cwd") or "?")
                    for r in c["unaccounted"]
                ),
            )
        )
    if c["cross_goal"]:
        # Reported, never flagged: this is the staffer's normal shape.
        out.append(
            "  note: %d cross-goal seat(s) live -- declared in another goal, ruled NOT to "
            "count against this run's cap, but real RAM: %s"
            % (
                len(c["cross_goal"]),
                ", ".join("%s(%s)" % (r["pane"], r["harness"]) for r in c["cross_goal"]),
            )
        )
    if c["ram_ok"] is False:
        out.append(
            "  ** RAM %s MB is BELOW the %s MB floor -- the cap is not the binding "
            "constraint right now, memory is." % (c["ram_available_mb"], c["ram_floor_mb"])
        )
    if c["counted"]:
        out.append(
            "  counted: "
            + ", ".join(
                "%s[%s]" % (r["seat"] or r["pane"], r["class"]) for r in c["counted"]
            )
        )
    if c["verdict"].startswith("OK") and c["headroom"] and c["ram_ok"] is not False:
        out.append(
            "  -> %d slot(s) free and RAM admits. Capacity only: whether a READY row "
            "exists is the sweep's question, not this module's." % c["headroom"]
        )
    return "\n".join(out)


def _selftest():
    """Every branch this module refuses to guess on. Exits 0 clean, 1 on failure."""
    b = {
        "cap": {"agent_panes": 10},
        "floors": {"ram_available_mb": 2800},
        "counting": {"counts_toward_cap": ["staff", "worker", "verifier"]},
    }
    now = 1000.0
    fails = []

    def seat(**kw):
        d = {
            "seat": "x",
            "class": "staff",
            "class_source": "descriptor",
            "harness": "claude",
            "liveness": "live",
            "pane": "%1",
        }
        d.update(kw)
        return d

    def check(label, got, want):
        if got != want:
            fails.append("%s: got %r want %r" % (label, got, want))

    # fresh room, all classified
    c = census(b, {"captured_at": now, "seats": [seat(), seat(seat="y")]}, now=now)
    check("counts staff", c["in_use"], 2)
    check("headroom", c["headroom"], 8)
    check("verdict", c["verdict"], "OK")

    # the master door never counts
    c = census(b, {"captured_at": now, "seats": [seat(**{"class": "master"})]}, now=now)
    check("door uncounted", c["in_use"], 0)

    # a non-agent pane with no descriptor is genuinely free
    c = census(
        b,
        {
            "captured_at": now,
            "seats": [seat(seat="", **{"class": "unclassified", "class_source": "no-seat", "harness": "python3"})],
        },
        now=now,
    )
    check("watch loop uncounted", c["in_use"], 0)

    # THE PREDICATE, both directions. A live agent with no run descriptor is
    # NOT automatically undeclared -- ask whether any goal declares it.
    nameless = seat(
        seat="",
        **{"class": "unclassified", "class_source": "no-seat", "harness": "claude", "cwd": "/somewhere"}
    )

    # (a) the staffer's shape: declared in ANOTHER goal -> accounted, NOT counted,
    #     and never flagged. This is the case whose absence would have fired a
    #     false positive on every summons.
    c = census(b, {"captured_at": now, "seats": [nameless]}, now=now, resolver=lambda cwd: "/g/seats/staffer/seat.md")
    check("cross-goal seat not counted", c["in_use"], 0)
    check("cross-goal seat reported", len(c["cross_goal"]), 1)
    check("cross-goal seat not flagged", len(c["unaccounted"]), 0)

    # (b) a genuine leak: resolves to nothing anywhere -> counted AND named
    c = census(b, {"captured_at": now, "seats": [nameless]}, now=now, resolver=lambda cwd: None)
    check("unaccounted counted", c["in_use"], 1)
    check("unaccounted named", len(c["unaccounted"]), 1)

    # the two must never collapse: same input, different world, opposite verdicts
    check(
        "predicate discriminates",
        census(b, {"captured_at": now, "seats": [nameless]}, now=now, resolver=lambda c_: "/x/seat.md")["in_use"]
        != census(b, {"captured_at": now, "seats": [nameless]}, now=now, resolver=lambda c_: None)["in_use"],
        True,
    )

    # a silent descriptor makes the aggregate declare itself incomplete
    c = census(
        b,
        {"captured_at": now, "seats": [seat(**{"class": "unclassified", "class_source": "descriptor"})]},
        now=now,
    )
    check("unclassified not counted", c["in_use"], 0)
    check("aggregate incomplete", c["complete"], False)
    check("verdict incomplete", c["verdict"], "OK-INCOMPLETE")

    # a dead pane spends nothing
    c = census(b, {"captured_at": now, "seats": [seat(liveness="no-harness")]}, now=now)
    check("dead pane uncounted", c["in_use"], 0)

    # stale snapshot offers NO number -- and UNKNOWN is not zero
    c = census(b, {"captured_at": now - 999, "seats": [seat()]}, now=now)
    check("stale verdict", c["verdict"], "UNKNOWN")
    check("stale offers no headroom", c["headroom"], None)

    # over the cap reports the breach with its size
    many = [seat(seat="s%d" % i, pane="%%%d" % i) for i in range(12)]
    c = census(b, {"captured_at": now, "seats": many}, now=now)
    check("breach verdict", c["verdict"], "BREACH")
    check("breach size", c["headroom"], -2)

    # a missing cap is UNKNOWN, never a default
    c = census({"counting": {"counts_toward_cap": ["staff"]}}, {"captured_at": now, "seats": [seat()]}, now=now)
    check("no cap declared", c["verdict"], "UNKNOWN")

    # render never raises on any of the above
    for st in (
        {"captured_at": now, "seats": many},
        {"captured_at": now - 999, "seats": []},
        {"seats": []},
    ):
        try:
            render(census(b, st, now=now))
        except Exception as exc:
            fails.append("render raised on %r: %s" % (st, exc))

    if fails:
        print("SELFTEST FAILED (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("selftest: 16 checks OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Declared capacity vs the live census.")
    ap.add_argument("--package", help="run folder (default: walk up from cwd)")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    pkg = a.package or find_package()
    if not pkg:
        print(
            "error: no run folder found (walked up from %s looking for a directory "
            "holding BOTH budget.json and state.json). Pass --package." % os.getcwd(),
            file=sys.stderr,
        )
        return 2

    budget, err1 = _load(os.path.join(pkg, "budget.json"), "budget.json")
    state, err2 = _load(os.path.join(pkg, "state.json"), "state.json")
    for err in (err1, err2):
        if err:
            # Loud, and never a fabricated zero: an absent input is not an empty room.
            print("budget: UNKNOWN -- %s" % err, file=sys.stderr)
            return 2

    c = census(budget, state)
    print(json.dumps(c, indent=2) if a.json else render(c))
    return 1 if c["verdict"] in ("BREACH", "UNKNOWN") else 0


if __name__ == "__main__":
    sys.exit(main())

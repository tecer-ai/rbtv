#!/usr/bin/env python3
"""probe-d13-verify-notify — D13'S VERIFY SEAT IS NOTIFY-ONLY (owner ruling 2026-08-25, option (a)).

WHAT THIS PROBE IS FOR. The ruling's load-bearing word is NOTIFY-ONLY: `verify-patch` reports what
it finds and the replan finishes either way. Prose in a task file cannot enforce that — the two
mechanisms that COULD halt a replan are both mechanical, and this probe measures both against the
seat as the catalog actually declares it:

  1. THE LOOP RE-FIRE. `coord/messages.py#on_fail_relaunch_route` reads the `on-fail-relaunch:`
     frontmatter key off the ISSUING seat's own `seat.md` (materialized from `seats.csv`) and
     re-dispatches exactly the seats it names. An empty declaration is an empty route: nothing
     re-fires, so a problem the verify seat finds cannot re-run the drafter or withhold a product.
  2. THE ESCALATION GATE. `coord`'s escalation refusal only lets a seat send `--type escalation`
     when it HAS such a route (or is the leader). With the route empty, the D13 verify seat cannot
     open a halt — which is the same fact as (1), read from the enforcement side.

And the notification itself must still work: `note` addressed to `owner` is the goal's ordinary
owner-contact path (`chat/bus-ferry.js` ferries `to: owner` rows into the owner's Slack surface),
so the report rides an existing transport rather than a new one.

evidence-class: FIXTURE. A scratch package directory holding a `seat.md` MATERIALIZED FROM THE REAL
`meta/planning/seats.csv` row, read by the REAL `on_fail_relaunch_route`. No daemon, no Slack, no
goals tree. NEVER run against the daemon.
"""

import csv
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
IGNITE = HERE.parent.parent
REPO = IGNITE.parent


def _load_coord():
    """`messages.py` is not importable on its own — `coord.py` `exec`s the split modules into ONE
    namespace (`SPLIT_MODULES`), so a bare `import messages` meets a name defined in a sibling.
    The CLI's own entry point is therefore the only honest door to the real reader, and loading it
    is what makes this probe measure production code rather than a copy of it."""
    spec = importlib.util.spec_from_file_location("coord_for_probe", IGNITE / "coord" / "coord.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_coord = _load_coord()
ON_FAIL_RELAUNCH_KEY = _coord.ON_FAIL_RELAUNCH_KEY
on_fail_relaunch_route = _coord.on_fail_relaunch_route

OUT = HERE / "probe-d13-verify-notify.out"
_lines = []
_checks = []


def out(*rows):
    _lines.extend(rows)


def check(name, passed, detail=""):
    _checks.append(passed)
    out(f"{'PASS' if passed else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def catalog_row(seat_id):
    with open(REPO / "meta" / "planning" / "seats.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("seat-id") or "").strip() == seat_id:
                return row
    return None


def materialize_seat_md(base, seat_id, row):
    """The frontmatter half of what `materialize-seats.py` emits for a seat: the route column,
    split on commas, dropped as a block list. Empty column -> the key carries nothing, which is
    exactly what the reader is being asked about."""
    route = [e.strip() for e in str(row.get(ON_FAIL_RELAUNCH_KEY) or "").split(",") if e.strip()]
    body = ["---", f"id: {seat_id}", f"task: {row.get('task')}"]
    body.append(f"{ON_FAIL_RELAUNCH_KEY}:")
    body.extend(f"  - {e}" for e in route)
    body += ["---", "", "briefing body"]
    d = Path(base).parent / "seats" / seat_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "seat.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    return route


def main():
    out(f"COMMAND: python3 {Path(__file__).relative_to(REPO)}")
    out("evidence-class: FIXTURE scratch package; seat.md materialized from the REAL"
        " meta/planning/seats.csv row and read by the REAL coord on_fail_relaunch_route")

    repl = catalog_row("repl-verifier")
    plan = catalog_row("plan-verifier")
    check("C0: the catalog still rosters both verify seats", repl is not None and plan is not None)
    if repl is None or plan is None:
        return finish()

    # ── T. THE TASK CONTRACT ────────────────────────────────────────────────────────────────────
    check("T1: D13's verify seat is paired with its OWN task, not the pipeline's `verify-plan` —"
          " the ruling's first half", repl["task"] == "verify-patch", repl["task"])
    check("T2: and the pipeline's verify seat keeps `verify-plan` — one ruling, two contracts, not"
          " a shared one bent to fit both", plan["task"] == "verify-plan", plan["task"])
    task = (REPO / "meta" / "planning" / "tasks" / "verify-patch.md").read_text(encoding="utf-8")
    check("T3: the D13 task's product is a NOTICE, not a plan-approval digest — a digest offering"
          " approve/reject-* is a gate, which is the thing notify-only forbids",
          "planning/replan/replan-notice.md" in task
          and "approval-digest" not in task,
          repl["goal-writes"])
    check("T4: the task forbids the verdict verb by name — the ONE door that arms the escalation"
          " gate and halts the milestone's contract",
          "No verdict is recorded" in task and "verdict verb" in task)
    check("T5: the task states the notice is written and sent on BOTH arms — nothing withheld on a"
          " problem", "check: problems` exactly as it is on `check: pass" in task)

    # ── L. THE LOOP RE-FIRE, MEASURED AT THE READER ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "coordination"
        base.mkdir(parents=True)
        repl_route = materialize_seat_md(base, "repl-verifier", repl)
        plan_route = materialize_seat_md(base, "plan-verifier", plan)

        seen_repl = on_fail_relaunch_route(base, "repl-verifier")
        seen_plan = on_fail_relaunch_route(base, "plan-verifier")

        check("L1: the catalog declares NO relaunch route for D13's verify seat", repl_route == [],
              f"seats.csv cell -> {repl_route!r}")
        check("L2: and coord's REAL reader resolves it to the empty route — a problem this seat"
              " finds re-dispatches NOTHING, so the replan is not halted and not re-run",
              seen_repl == [], f"on_fail_relaunch_route -> {seen_repl!r}")
        # The enforcement side, read where it is enforced rather than restated: coord admits an
        # `escalation` only from the leader or from a seat that HAS a route. Both halves are
        # measured — the guard is still in the source, and the expression it evaluates is False
        # for this seat.
        guard = (IGNITE / "coord" / "messages.py").read_text(encoding="utf-8")
        guard_present = re.search(
            r'args\.type == "escalation" and sender != "leader" and not on_fail_relaunch_route',
            guard) is not None
        repl_may_escalate = ("repl-verifier" == "leader") or bool(seen_repl)
        plan_may_escalate = ("plan-verifier" == "leader") or bool(seen_plan)
        check("L3: the escalation gate is closed to it — coord's live guard admits an `escalation`"
              " only from the leader or from a seat holding a route, and this seat is neither, so"
              " it cannot open a halt either",
              guard_present and repl_may_escalate is False,
              f"guard-in-source={guard_present} may-escalate={repl_may_escalate}")
        check("L3b: RED ARM for the same guard — the pipeline's verify seat DOES clear it, so L3"
              " measures a discriminating predicate rather than a constant False",
              plan_may_escalate is True, f"may-escalate={plan_may_escalate}")

        # THE DISCRIMINATING ARM. Without it L2 would pass on a broken reader, a missing file, or a
        # fixture that never wrote frontmatter at all — every one of which also answers `[]`.
        check("L4: RED ARM — the SAME reader, the SAME fixture, on the pipeline's verify seat"
              " returns its two-seat loop, so the empty answer above is this seat's declaration"
              " and not a reader that always says nothing",
              seen_plan == ["plan-reviewer", "plan-verifier"], f"-> {seen_plan!r}")

    # ── N. THE NOTIFICATION RIDES AN EXISTING SURFACE ───────────────────────────────────────────
    check("N1: the notify is one `note` addressed to `owner` — the address `chat/bus-ferry.js`"
          " ferries into the owner's Slack surface; no new transport is minted",
          "`note` addressed to `owner`" in task and "never a second transport" in task)
    ferry = (IGNITE / "chat" / "bus-ferry.js").read_text(encoding="utf-8")
    check("N2: and that address still exists on the ferry as the one it carries",
          "const OWNER_TOKEN = 'owner';" in ferry)
    check("N3: the task forbids a direct Slack call and a direct outbox record — the seat hands the"
          " row to the bus and the bridge does the posting",
          "Never a Slack call, never an outbox record" in task)

    # ── W. THE MANIFEST AND THE WORKFLOW DOC AGREE WITH THE CATALOG ─────────────────────────────
    man = (REPO / "meta" / "planning" / "workflows" / "d13-replan" / "d13-replan.csv").read_text(encoding="utf-8")
    check("W1: the workflow manifest's verify row declares the notice and the notify-only shape",
          "planning/replan/replan-notice.md" in man and "NOTIFY-ONLY" in man)
    doc = (REPO / "meta" / "planning" / "workflows" / "d13-replan" / "workflow.md").read_text(encoding="utf-8")
    check("W2: and `workflow.md` no longer documents a regression loop that the catalog does not"
          " declare — the doc and the mechanism cannot disagree here",
          "There is no regression loop" in doc
          and not re.search(r"`repl-drafter,repl-verifier`", doc))
    return finish()


def finish():
    passed = sum(1 for c in _checks if c)
    out("", f"{passed}/{len(_checks)} PASS")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
    print("\n".join(_lines))
    return 0 if passed == len(_checks) else 1


if __name__ == "__main__":
    sys.exit(main())

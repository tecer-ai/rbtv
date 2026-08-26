---
id: master-bootstrap
description: "Read at the moment a master has established that the goal in front of it is BOOTSTRAPPED — opened from ground, materialized into being by no seat and no workflow — and is about to act on it: opening milestone 0, picking the planning mode, giving the goal its taskforce with `scaffold-seats --workflow`, verifying at the product, and stopping at REGISTERED."
---

<reference>
Form: NORMATIVE. Enforcement: binding. Reach: one master seat, at one bootstrapped goal, once.
Every step below is a duty of that single act. Skipping one is a defect, never a permission.

## The condition, and it is the whole condition

A goal is BOOTSTRAPPED when NO SEAT and NO WORKFLOW materialized it into being — it was opened
from ground.

This act fires when, and ONLY when, that test holds. A goal that some seat or workflow already
produced NEVER takes this path, and running it there is a defect: it re-materializes a taskforce
that already exists.

**Why it is the master's, and why only here.** At bootstrap the goal has NO TASKFORCE YET.
Someone MUST create the first seat folders before the team exists, and at that moment there is
nobody else. That absence is the whole warrant, and it expires the instant the goal has a
taskforce.

## 1 — OPEN MILESTONE 0

Planning and staffing ARE milestone 0 — the milestone whose outcome is that the goal has a plan
and a staffed taskforce. Every bootstrapped goal has one, and the master is the one who opens it.

## 2 — PICK THE PLANNING MODE: COLLAPSED or EXPANDED

This pick is a JUDGMENT CALL, and it MAY be subjective. It is NEVER a task-count estimate and
NEVER any other mechanical threshold.

- **COLLAPSED** — pick it when the milestone's shape is ALREADY UNDERSTOOD: an unambiguous goal
  contract, no new seat kinds expected, and open questions that are refinements rather than
  decompositions.
- **EXPANDED** — pick it when the milestone OPENS NEW GROUND: dependencies not yet mapped, new
  seat kinds likely, cross-cutting design questions still open, or parallelism worth designing
  for.

**In doubt, EXPANDED.** The collapse is the OPTIMIZATION, NEVER the default: a milestone wrongly
expanded costs one planning pass, and a milestone wrongly collapsed loses the decomposition
nobody goes back to do.

**The pick is the master's ONLY outside a run**, and for one structural reason: there is no
`leader` yet, because there is no run yet. Once the goal has a taskforce this pick is NEVER the
master's again — from then on it belongs to the `leader`.

State which mode was picked in what you report at step 5.

## 3 — GIVE THE GOAL ITS TASKFORCE

A bootstrapped goal has no `taskforce.csv`, and the ONE command that writes one is
`scaffold-seats`, over the plan workflow ALREADY PRESENT for this goal — pre-placed, neither
authored by the master nor fetched by the master:

```
scaffold-seats --package <ABSOLUTE goal folder> --workflow <plan workflow> --catalog-root <component catalog root>
```

It materializes the WHOLE workflow into the goal: each seat's descriptor first, then that seat's
`taskforce.csv` row. `--package` is the GOAL FOLDER itself, absolute, and is NEVER inferred;
`--catalog-root` is required and never guessed. MUST reach it by its PATH name `scaffold-seats`,
NEVER by the script path behind it.

**The COMMAND writes the seat folders and their contents.** No agent hand-writes one, and the
master's duty here is ONE COMMAND INVOCATION and no carpentry: NEVER build anything for the command
first. Where it REFUSES for an operand it will not guess, read the refusal and supply what it names
— NEVER invent one to get past a refusal, because it refuses precisely where a guess would silently
materialize the wrong thing.

The first executor BINDINGS come from the plan workflow definition's OWN staffing hints — the
`staffing-hints` column of its `seats.csv` and the `staffing-recommendations` of its
`prompts.csv`. Bind NOTHING by hand; the staffer stage re-binds as usual once it exists.

**`rbtv goal materialize` is NOT this step, and ordering it here was this section's own defect.**
That verb is the `goal-materialize` step (`sd-graph show goal-materialize`) — it ASSEMBLES seat
folders FROM a taskforce that already exists, and with the file absent it REFUSES outright
(`taskforce.csv: absent — nothing to materialize`,
`ignite/operator/goals-tree/tool/goal_cli.py:2886`), which is exactly the state that triggers this
reference. Reach it only where a taskforce is already registered and its seat folders are not yet
assembled, and NEVER as the act that brings a taskforce into being.

**ONE MORE SEAT, LATER.** A goal that already has a taskforce and needs one more seat gets a
single-seat `scaffold-seats --seat <seat>` call — never a second `rbtv goal materialize`, which
refuses to regenerate an existing `seats/` tree without `--force`, and forcing it re-assembles seats
that may already have run. **THE MASTER RUNS THAT CALL** where this goal's authority is the
master's (owner ruling 2026-08-26): naming whose call it is and stopping there is NOT the answer.
Where a `leader` holds the goal's authority, the call is the leader's and never yours to run into
that goal — the bound is WHOSE AUTHORITY the goal is under, never a rule that this door runs none
of it.

## 4 — VERIFY AT THE PRODUCT, NEVER AT THE COMMAND'S OWN SUCCESS LINE

Read the folders and the files the command claims to have written. **A tool reporting on itself
certifies nothing about the state it claims to have produced.**

A FAILED run is REPORTED, with what it wrote before it failed. **Completing its work by hand is
the one recovery NEVER available**: a hand-finished tree looks materialized to every later reader
and is not, and no seat downstream can tell the difference until one of them breaks on it.

## 5 — STOP AT REGISTERED

What was materialized is REGISTERED — NOT launched, and NOT planned. Report it in exactly those
terms; calling it launched or planned tells the owner a taskforce is working when nothing is.

**Nothing is queued and nothing is delayed.** A goal advances on its LANE: the daemon's watch pass
reads the `execution-lane` marker before every tick and seeds a daemon-lane goal off it, and a
console-lane goal waits for the owner to type `rbtv run`. There is NO job to enqueue at this door
and NO scheduled start to time — a hand-queued launch is a row nothing consumes.

The master authors NO milestone plan, NO task DAG, NO seat definition, and NO cognitive unit.
Running the command is not doing the planning: the seats just registered ARE the ones that plan.
</reference>

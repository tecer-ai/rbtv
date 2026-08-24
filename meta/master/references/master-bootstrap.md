---
id: master-bootstrap
description: "Read at the moment a master has established that the goal in front of it is BOOTSTRAPPED — opened from ground, materialized into being by no seat and no workflow — and is about to act on it: opening milestone 0, picking the planning mode, running the materialize command, verifying at the product, and stopping at REGISTERED."
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

## 3 — RUN THE MATERIALIZE COMMAND

`rbtv goal materialize <goal-name>` runs over the plan workflow that is ALREADY PRESENT in the
goal folder — pre-placed, neither authored by the master nor fetched by the master.

**The COMMAND writes the seat folders and their contents into the GOAL FOLDER.** No agent
hand-writes one, and the master's duty here is ONE COMMAND INVOCATION and no carpentry: NEVER
build anything for the command first, and NEVER treat a folder's absence as a blocker. Creating
what is missing under the goal folder IS materialization, done by the command itself.

The first executor BINDINGS come from the plan workflow definition's OWN staffing hints — the
`staffing-hints` column of its `seats.csv` and the `staffing-recommendations` of its
`prompts.csv`. Bind NOTHING by hand; the staffer stage re-binds as usual once it exists.

Where the command REFUSES for an operand it will not guess, read the refusal and supply what it
names. NEVER invent an operand to get past a refusal: the command refuses precisely where a guess
would silently materialize the wrong thing.

**It runs ONCE PER GOAL.** `materialize` refuses to regenerate an existing `seats/` tree without
`--force`, and there is no later materialize call for anyone to own. A goal that later needs ONE
MORE seat gets a `scaffold-seats` call from the seat holding that goal's authority — the
`leader` — and NEVER a second materialize from this door. A second materialize here is a defect,
not a courtesy.

That later call is named `scaffold-seats` and is resolved on PATH by that ruled name, NEVER by
the script path behind it. Its `--package` takes the ABSOLUTE GOAL-FOLDER path, because the
package IS the goal folder, and it is NEVER inferred. The master runs NONE of it: asked for one
more seat, the master names whose call it is and NEVER reaches for `materialize` a second time.

## 4 — VERIFY AT THE PRODUCT, NEVER AT THE COMMAND'S OWN SUCCESS LINE

Read the folders and the files the command claims to have written. **A tool reporting on itself
certifies nothing about the state it claims to have produced.**

A FAILED run is REPORTED, with what it wrote before it failed. **Completing its work by hand is
the one recovery NEVER available**: a hand-finished tree looks materialized to every later reader
and is not, and no seat downstream can tell the difference until one of them breaks on it.

## 5 — STOP AT REGISTERED

What was materialized is REGISTERED — NOT launched, and NOT planned. Report it in exactly those
terms; calling it launched or planned tells the owner a taskforce is working when nothing is.

The master authors NO milestone plan, NO task DAG, NO seat definition, and NO cognitive unit.
Running the command is not doing the planning: the seats just registered ARE the ones that plan.
</reference>

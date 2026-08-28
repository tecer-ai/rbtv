# 20260828-c-laneispaused-two-pause-writers — laneIsPaused: two pause writers, and either one holds

kind: change
component: supervisor
date: 2026-08-28
commit: 4a032354
deployed: no
pin: ignite/supervisor/lane-skip.selftest.js
components: gateway,state-store,engine

## Motivation
a0d7e42c converged the two records of "is this goal paused" onto the goal-state ROW: the row's
EXISTENCE decided, and the `execution-lane` marker became a shim for goals the store had never
recorded. That was right for the defect it fixed — a stale `paused` marker on disk beating a row
that had actually been updated, freezing a goal against the record that changed — and it had a
second-order consequence nobody could reach until the fifteenth gateway intent landed.

MEASURED, not inferred: `select count(*) from goal_states` on the live `heart.db` returned 0 at
2026-08-28 02:19Z. NO goal on this instance carries a row. Nine of the sixteen live goals carry
`paused daemon` in `execution-lane`, written by the console's `rbtv goal pause` — including every
test goal the orchestrator deliberately parked during the acceptance wave. With the row deciding on
its existence, the FIRST Slack `pause` or `resume` on a goal MINTS a row, and that row then
overrides the console marker permanently: a Slack `resume` would silently un-park a goal an
operator parked (each woken leader is a real, paid sitting), and a later `rbtv goal pause` would be
ignored while the row read `running`.

## Design
The gate is an OR: PAUSED IF EITHER SURFACE SAYS SO. A `running` row falls THROUGH to the file
instead of returning, and only a goal both surfaces call unpaused runs.

That re-opens exactly the possibility a0d7e42c closed — a stale marker outliving a row — and the
answer is NOT to make the gate guess which writer is fresher (it cannot know, and a gate with a
heuristic is a third reading of the same state). It is to make the disagreement VISIBLE at the only
moment it can be acted on: `state-store/heart/pause-resume.js`'s resume refuses when the lane file
still parks the goal, names the marker, names `rbtv goal resume <goal>` as the lift, and reports
`applied: false` while still listing the acts it really performed. a0d7e42c's defect was a goal
frozen against a record NOBODY COULD SEE; a goal frozen with the reason in the same Slack message
is a second writer honestly reported.

Rejected: retiring the lane-file writer, which collapses this to one record properly. That deletes
an owner-facing console verb and is OWNER-GATED, not an implementation seat's call.

## How it works
`lane-watch.js#laneIsPaused(goalFolder, heartStore)` binds through `ending-reads.js#bindEnding`,
reads `getGoalState(goalNameOf(goalFolder))`, and returns TRUE only on `stored === 'paused'`;
anything else — a `running` row, no row, an unreadable store — falls through to the raw first token
of `execution-lane`. Absent or unreadable is NOT paused on both surfaces, the pre-existing fail-safe
direction. It remains the ONE reader both pause gates spend (`reconcile.js`'s gate and the lane pass
at `lane-watch.js`), and `goal_cli.py#lane_is_paused` is still its DEC-1 Python twin.

`isGoalPaused` still cannot carry the store leg: it flattens "the row says running" and "there is no
row at all" into one `false`, and the OR needs to tell them apart to know whether the row is in the
conversation at all.

## Consequences
NO BEHAVIOUR CHANGES ON THE CURRENT INSTANCE, and that is worth stating precisely: with zero
`goal_states` rows the store leg contributes nothing today, so every goal's pause answer is
byte-identical before and after. The change is load-bearing from the first Slack verb onward — it
is a guard installed BEFORE the writer that needs it, not a repair.

`reconcile.selftest.js`'s "one pause record" row asserted the OPPOSITE rule (a `running` row beating
a `paused` marker must not skip) and was rewritten; it gained a third, discriminating leg (both
surfaces running -> the pass runs), because two paused legs alone are satisfied by a gate that
returns `true` unconditionally.

## Verification
`supervisor/lane-skip.selftest.js` gains a four-combination arm over `laneIsPaused` itself — no row
+ unpaused marker (false), row running + marker daemon (false), row running + marker `paused daemon`
(TRUE — the leg this change exists for), row paused + marker daemon (true). Red-proven on the LIVE
file, not assumed: with the pre-change `if (row && row.stored) return row.stored === 'paused';`
restored, that arm fails on exactly the third leg with its own message and the suite goes 5/6;
restored, 6/6. `probe-pause-resume.js` R3 runs the same mutation on a discarded copy inside its own
run, plus g4/g5/g6 asserting the gate from the lane file, from neither, and from the store row
alone.

`reconcile.selftest.js`'s rewritten row proven to pass on a mutant copy that skips the file's
pre-existing `:392` red (BOOT-PROMPT-BODY); that red and a second one behind it (the counter-brake
arm at `:1017`) both reproduce identically on a pristine `git archive HEAD` tree, so neither is this
change's. Supervisor selftests 12/13 before AND after; `probe-daemon-lane-watch` red is the same
single L9 M9 check before and after. NOT DEPLOYED at filing (commit 4a032354).

## ATTENTION
1. THIS IS A DELIBERATE PARTIAL REVERSAL OF a0d7e42c AND ITS OWN DEFECT IS BACK, ON PURPOSE. A stale `paused` marker CAN now outlive a `running` row and freeze a goal. What makes that acceptable is the resume executor's refusal naming the marker — delete that refusal and the freeze becomes silent again, which is the exact failure a0d7e42c existed to fix.
2. THE GATE KEYS THE GOAL-STATE ROW ON THE FOLDER BASENAME, not on any goal argument — `laneIsPaused` takes no goal name and derives it with `goalNameOf(goalFolder)`. On a real goal the two are the same string by construction; in a flat fixture they are not, and a row written under the caller's `goal` argument is invisible to the gate.
3. THERE ARE TWO LIVE WRITERS OF ONE FACT AND RETIRING ONE IS OWNER-GATED. Anyone "simplifying" this back to a single surface is deleting either the owner's Slack verb or the console's `rbtv goal pause`, both of which the owner uses.
4. A TWO-LEG ARM CANNOT TELL AN OR FROM A CONSTANT `true`. Any future edit to these selftests must keep the leg where BOTH surfaces read running and the pass must NOT skip, or the whole row stops discriminating.
- A stale execution-lane marker can freeze a goal again on purpose — the resume executor's refusal naming the marker is what keeps that visible

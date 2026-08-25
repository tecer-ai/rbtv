# 20260825-c-d13-verify-becomes-notify-only — D13 verify becomes notify-only

kind: change
component: meta-planning
date: 2026-08-25
commit: 37f2e9a9,b0fc52ee
deployed: no
pin: ignite/planning/probes/probe-d13-verify-notify.py
components: planning,coord

## Motivation
The D13 replan mini-pipeline landed with its verify seat REUSING the main pipeline's `verify-plan`
task, on the reasoning that its check (b) — every milestone id still present with its done-criteria
unbroken — IS the unchanged-contract check D13 needs. That landing's own entry disclosed the misfit
and refused to fix it: `verify-plan` and the `verifier` prompt belong to another seat, and the entry's
ATTENTION said explicitly not to edit them "without a ruling on who owns the D13 verify contract".
The owner ruled on 2026-08-25, option (a): D13 gets its own dedicated NOTIFY-ONLY verify task.

The check was right and the CONTRACT AROUND IT was wrong in kind. `verify-plan` issues a FAIL verdict
that re-fires the drafter and WITHHOLDS its product until a two-pass cap is reached, and it composes a
plan-APPROVAL digest offering `approve` / `reject-close` / `reject-pause` / `reject-retry`. Both are
GATES. D13's whole design is a lane that closes a gate failure WITHOUT stopping the goal — it
continues autonomously and notifies, and the owner intervenes only by choice.

## Design
A new task `verify-patch`, paired with the same `verifier` prompt. Two checks, no third: (a) the
milestone's contract is unchanged — the patch may change how the milestone is met, never what meeting
it means; (b) the patch stayed inside `patch-draft`'s two walls (one milestone, envelope unwidened),
or, under `disposition: escalate`, carries zero patch content and names the crossing. The product is
`planning/replan/replan-notice.md`, first line `REPLAN-NOTICE`, second line `check: pass` or
`check: problems` — one authored word its reader keys on, the same mechanization `patch-draft`'s
disposition line uses.

NOTIFY-ONLY is enforced at the two mechanisms that could halt a replan, not asserted in prose. The
`on-fail-relaunch` cell is EMPTY, so `coord`'s loop re-fire — `on_fail_relaunch_route`, which reads
that frontmatter key off the issuing seat's own `seat.md` — resolves to the empty route and
re-dispatches nothing. And the task forbids the verdict verb by name, because `coordinate verdict` is
the ONE door that arms the escalation gate; with no route declared, `coord` also refuses `--type
escalation` from this seat, so it cannot open a halt from the other side either. The notice is written
AND sent on both arms: nothing is withheld on a problem.

The notification rides the surface that already exists — one `note` addressed to `owner` on the
coordination bus, which `chat/bus-ferry.js` ferries into the owner's Slack surface through the durable
outbox. No Slack call from the seat, no outbox record from the seat, no new transport.

Rejected: keeping the approval digest as D13's product with the outcomes removed. A digest is the
plan-approval lane's artifact and its reader expects those outcomes; a half-digest is a shape that
lies about which lane produced it. Rejected: keeping the two-pass regression loop and only removing the
verdict — the loop IS the gate (it withholds the product), so removing the verdict alone would leave
notify-only true in name and false in mechanism.

## How it works
`seats.csv`'s `repl-verifier` row now reads `verifier` + `verify-patch`, `goal-writes`
`planning/replan/replan-notice.md`, `on-fail-relaunch` empty. `d13-replan.csv`'s third row and
`workflow.md`'s procedure, regression-loop and reuse paragraphs were rewritten to match — the doc now
states there is NO regression loop and why, so the doc and the mechanism cannot disagree.
`patch-draft.md`'s outcome map lost its "fix pass relaunched by the verify seat" bullet, which named a
loop that no longer exists.

The shared `verifier` prompt was the remaining contradiction: it hardcoded one task's contract. It now
defers to the paired task in five places — step 3 is skipped entirely where the task declares itself
notify-only, step 5 composes the product the task's Write clause names with the digest field list
scoped to the digest, the Run and Write permissions read from the task, and "send on no channel"
admits exactly the ONE message a task's Send clause names.

## Consequences
`verify-plan`, `understander`, `drafter`, `gap-understand` and the two D13 artifacts under
`planning/replan/` are otherwise untouched; the pipeline's `plan-verifier` keeps `verify-plan` and its
two-seat loop, so one ruling produced two contracts rather than one contract bent to fit both. The
two-failed-replan cap remains DAEMON policy documented in `workflow.md` and implemented in no seat —
it is now explicitly the only cap in the lane. The `d13-replan` DAG is unchanged: three rows, two
edges, acyclic.

## Verification
`probe-d13-verify-notify.py`, new, 16 checks EXIT 0 — it materializes a `seat.md` from the REAL
`seats.csv` row and reads it with the REAL `on_fail_relaunch_route` (loaded through `coord.py`, since
`messages.py` is `exec`d into one namespace by `SPLIT_MODULES` and is not importable alone). L2 shows
the empty route, L3 shows the escalation guard still in the source and evaluating False for this seat,
and L4/L3b are RED ARMS: the same reader and the same guard on `plan-verifier` return
`['plan-reviewer','plan-verifier']` and True, so the empty answers are this seat's declaration and not
a reader that always says nothing. `goal_cli.py check-acyclic` on `d13-replan.csv`: 3 rows, 2 edges,
clean. On `plan-console.csv`: 5 rows, 4 edges, clean, strictly linear.
`materialize-seats.py --selftest` full completion 62/62 rows both arms, 0 FAIL. All 7 planning probes
green. Suite 207/193/11/3 vs the 205/190/12/3 census baseline, every delta attributed.
Not deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. THE EMPTY `on-fail-relaunch` CELL IS THE MECHANISM, NOT AN OVERSIGHT. Filling it "so a failed check
   gets fixed" re-creates the gate the ruling removed: the route is what `coord`'s loop re-fire
   re-dispatches on, and it is also what lets the seat send an `escalation` at all. Both halves come
   back together.
2. NEVER GIVE THIS TASK THE VERDICT VERB. `coordinate verdict` is the one door that arms the escalation
   gate and halts the milestone's contract until the owner answers. A "just record the FAIL for the
   record" edit stops the goal, which is precisely what D13 exists to avoid.
3. THE NOTICE IS NOT A DIGEST AND MUST NEVER GROW APPROVAL OUTCOMES. `approve` / `reject-close` /
   `reject-pause` / `reject-retry` belong to the plan-approval lane. Offering them here makes the
   replan wait on an owner reply, which is the gating this contract forbids.
4. THE `verifier` PROMPT IS SHARED BY TWO SEATS WITH DIFFERENT CONTRACTS. Every clause in it that
   names a cap, a product or a send must stay conditioned on the PAIRED TASK. Re-hardcoding one task's
   contract into it silently orders the other seat to violate its own ruling — which is exactly the
   defect this entry fixed.
5. THE TWO-FAILED-REPLAN CAP IS STILL THE DAEMON'S AND STILL IMPLEMENTED NOWHERE. Now that the verify
   seat holds no cap of its own, the temptation to "put the cap back somewhere" lands on a seat that
   cannot see its own predecessors and would reset the count on every mint.
- The empty on-fail-relaunch cell IS the notify-only mechanism; filling it restores the gate the ruling removed

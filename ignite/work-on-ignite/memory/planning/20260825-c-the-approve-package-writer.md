# 20260825-c-the-approve-package-writer — The approve-package writer

kind: creation
component: planning
date: 2026-08-25
commit: b2449ebe
deployed: no
pin: ignite/planning/probes/probe-approve-package.js
components: state-store,meta-planning

## Motivation
`planning/approve-package.json` was a CONVENTION WITH NO WRITER. The fourteenth gateway intent
(`start-execution`, owner ruling 2026-08-24 (b)) landed its daemon-side executor —
`state-store/heart/start-execution.js` — reading that file to learn WHAT the owner approved, and its
own creation entry disclosed the gap as an honest, loud one: every genuine `approve` in the approval
thread refused `no-approve-package` and said so in the thread, because nothing anywhere produced the
package. `spec-planning-door` puts the plan's verification in the pipeline's verify step, and the
verify seat is where the facts the package needs — the execution-goal name, the lane, the roster, the
plan artifacts, and the git commit it just recorded — actually converge. The owner ruled the writer
into that step on 2026-08-25, bundled with the D13 verify contract.

## Design
`approve_package.py` beside the door's other modules, with `write_approve_package()` and a CLI the
verify seat runs once after its two checks. THE READER DEFINES THE CONTRACT and nothing else does:
every required field exists because `start-execution.js#readApprovePackage` or
`path_b.py#run_path_b` consumes it, and the two validations are the reader's own rules re-spoken —
`execution_goal` through `bus-ferry.js#isSafeName` (it becomes a path segment under `.rbtv/goals/`)
and `bound_commit` through the reader's `COMMIT_RE` (lowercase hex 7-64; a ref name is a MOVING
binding [T5-R5]). The refusal is placed at the WRITER on purpose: there a seat can still fix its
input, whereas at the gate it is an owner reading a refusal in Slack.

`planning_goal`, `goals_root` and `origin_id` are REFUSED rather than filled. That is the fourteenth
intent's own ATTENTION-4 implemented rather than quoted: the reader derives all three and refuses
`package-not-bound-here` when a package disagrees, so a writer that emits them can only ever agree by
accident and, when a package is copied between goals, hides the copy that refusal exists to catch.

Rejected: the verify seat hand-writing the JSON. A closed schema an LLM types is a schema that drifts
the first time a field is renamed, and the two validations would exist nowhere. Rejected: a second
`goal-writes` declaration on `plan-verifier` — the column names ONE product by construction (D9), and
`planning/` is already read-write to every seat through `bind:{goalDir}` (D3), so the package needs no
grant of its own. Rejected: writing it from the daemon at approve time — the daemon does not hold the
plan, which is the whole reason the package exists.

## How it works
`write_approve_package(goal_dir, ...)` validates, then writes `<goal>/planning/approve-package.json`
through coord's `records.atomic_write` — tmp+rename AND the derived-tree refusal in one door. The
guard is EXPECTED to pass here and is walked anyway: `approve-package.json` is planning state, not a
derived lane (the marked tree is `planning/current/seat-lane/`, and this file sits one level above it
beside Path B's own `bound-plan.json`), so the call is insurance against a future regenerator marking
`planning/`, not a live refusal path. `sort_keys=True` so two writes of the same facts are the same
bytes.

The seat reaches it as an instrument: `exposure.csv` gains a `tool`/`path` row `approve-package`
(no `write-roots` — its target is the GOAL folder, never a repo path), `prompts/verifier.md` gains
`rbtv:ignite/planning/approve-package` to `exposes:` and a step 6 ordering one run after the checks,
and `tasks/verify-plan.md` carries the done clause plus the arm for a writer refusal: the refusal
becomes a red flag on the digest and the package is NOT hand-written.

## Consequences
Nothing was deleted. `start-execution.js`, `path_b.py` and `wrapper.py` are byte-unchanged — the
package is written to fit them, never the reverse. The fourteenth intent's gate now transitions:
`no-approve-package` before this writer runs, a supervised Path-B birth after. `probe-start-execution`
is unaffected (it hand-writes its own package to reach refusals ABOVE the read, which is still the
right fixture for that probe).

## Verification
`probe-approve-package.js`, new, 16 checks EXIT 0 — one fixture carrying the whole transition: G1
refuses `no-approve-package` with zero births attempted, W1-W5 write and quote the package and prove
no `.tmp` residue, A1-A3 admit the SAME approval and show the birth receiving the daemon-stamped trio
plus the writer's optional fields intact, R1-R3 refuse a ref-name commit and a traversing goal name
with nothing left on disk, D1-D2 refuse under a `DERIVED.md`. Red-before proven on the LIVE file by
mutation: with the writer's target filename changed, W2 and A1 go red and A1 reads back the exact
`no-approve-package` refusal; restored, 16/16 and the file diffs byte-identical.
`materialize-seats.py --selftest` full completion, 62/62 rows both arms, 0 FAIL. Every planning probe
green (7/7). Suite 207 discovered / 193 passed / 11 failed / 3 inoperative against the 205/190/12/3
census baseline: +2 discovered and +2 passed are these two new probes, and the third pass is
`probe-trace-header`, which status.md already records as PASS with the ridered `RBTV_IGNITE_SRC` env.
Not deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. THE READER IS THE SCHEMA, AND IT IS IN JAVASCRIPT. `readApprovePackage` in
   `state-store/heart/start-execution.js` is the only definition of what this file must contain; a
   field added here that it does not read is decoration, and a field it starts requiring must be added
   here in the SAME change or every approve refuses. Read that function before touching this writer.
2. NEVER MAKE THIS WRITER EMIT `planning_goal`, `goals_root` OR `origin_id`. The daemon stamps all
   three and refuses a package that disagrees with its own derivation. Emitting them looks like
   completeness and deletes the guard that catches a package copied from another goal.
3. THE DERIVED-TREE GUARD PASSING IS NOT THE GUARD BEING ABSENT. `approve-package.json` is planning
   state and the marked tree is `planning/current/seat-lane/`, so `refuse_if_derived` never fires in
   production today. An editor who "simplifies" `atomic_write` down to a plain write here removes both
   the guard and the tmp+rename, and an interrupted truncate-write leaves a zero-byte package that
   reads as `bad-approve-package` at the gate.
4. A WRITER REFUSAL IS A RED FLAG ON THE DIGEST, NEVER A HAND-WRITTEN PACKAGE. `verify-plan` says this
   in its done contract because the tempting repair — typing the JSON when the CLI refuses — produces
   a package that claims a plan nobody checked, which is the one lie this file must not be able to
   tell.
- The reader (start-execution.js#readApprovePackage) IS the schema; never emit planning_goal/goals_root/origin_id

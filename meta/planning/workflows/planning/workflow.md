---
name: planning
default-execution-mode: interactive
four-letters: plan
---

# planning — the workflow

**Four letters (`plan`).** The prefix every NESTED INSTANCE of this workflow is named through
(`materialize-seats.py#read_workflow_prefix` → `compose_seat_name`): a second pass materializes as
`plan-<seat>`, a third as `plan-2-<seat>`, and its taskforce id as `tf-<n>-plan<m>`. Declared
because W7's wave re-entry splices each newly-unblocked milestone's pass as ONE nested
materialization, and without this key that materialization refuses `workflow-prefix-undeclared`.
It is REQUIRED, not cosmetic: `taskforce.csv` is keyed by seat NAME, a goal that already ran pass 1
carries `plan-planner` (and its siblings), and a bare re-splice of the same names hits the
materializer's own pinned `seat-exists` refusal and would refuse forever.

**Default execution mode.** `interactive` — declared above, in this workflow's own scaffolding. It is the value a goal created from this workflow is BORN with: goal creation writes it into `.rbtv/goals/<goal>/execution-mode`, and from there the control plane gates every agent-initiated owner contact on it. Declared rather than left to derivation because derivation would reach the same answer here (`planning.csv` carries an `interactive` Modality seat, `plan-interviewer`) and the DECLARATION is what lets a later owner ruling say otherwise without rewriting the manifest. Resolution when a workflow declares NO `default-execution-mode:` — any manifest row whose Modality reads `interactive` → `interactive`, none → `autonomous`. A per-goal value supplied in the creation request overrides this default; this is the floor, never a lock.

**Goal.** Turn a planning request — an ad-hoc goal, an optimize, a port, or a scaffold ask — into an owner-ratified definition of done, a milestone DAG, and, per unblocked milestone, a checked, bound, materialization-verified execution plan. Only use case 1 outputs a taskforce (ephemeral, in its goal folder); cases 2–4 output a workflow into the scaffolding.

**Scope.** Planning plans — it never executes the plan and never opens/materializes anything itself (the daemon does). The interview is the one deliberately interactive moment: the first pass waits at the owner channel (questions sent as messages addressed to the reserved `owner` token, which the chat bridge carries to the owner's goal channel) for a ratified DoD — a disclosed block-and-queue, never a silent stall, and the ONE sanctioned hard gate (a goal seed already carrying an owner-ratified DoD skips the wait); every later pass runs autonomous.

**Procedure (two phases, `planning.csv` is the DAG).**

1. **Goal-level phase — runs once per goal:** `plan-interviewer` (goal.md + DoD) → `plan-splitter` (pieces scratch) → `plan-dag-structurer` (`milestones.csv`, each row stamped `planning-mode: full | collapsed`).
2. **Per-milestone phase — one team per unblocked milestone, in parallel; later passes start here:** `plan-task-definer` → `plan-resource-definer` → `plan-assembler` → check swarm (six single-dimension checkers in parallel — seven when the goal's `use-case:` reads optimize, port, or scaffold, adding the mechanization checker) → `plan-check-assembler` → `plan-binder`. A `collapsed`-stamped milestone runs `plan-planner` alone instead — same contracts, one seat.

**The loop.** Every trial verdict the produced taskforce's dod-judge records fires the pass-opener (the unblock-checker seat): a PASS queues one planning pass per newly unblocked milestone; a FAIL below the goal's retry threshold queues ONE gap-filling pass at the same done contract, seeded from the verdict's per-clause gaps; a FAIL at the threshold queues NOTHING — the halt — until the owner answers the escalation. The count is derived from the run's verdict message log, never stored; the threshold it is measured against is per-goal configuration with an optional per-milestone override (`rbtv-goal retry-threshold`, default 2), and both seats read it off the one `coordinate fail-status` verb rather than deriving or typing it. Inside a pass, the check-assembler loops route-backs and re-checks by appending relaunch rows to the run's `taskforce.csv` (finding delivered at `planning/current/route-back-<seat-id>.md` — never in the routed seat's folder, which no peer can write or read). A route-back file is written for an AUTHORING seat ONLY — task-definer, resource-definer, assembler; a relaunched CHECKER receives no file and re-derives its dimension fresh from the amended plan, which is the point of re-checking it at all.

Any planning seat may fan out `plan-researcher` / `plan-diagnoser` as sub-agents (no taskforce row; results return to the dispatcher).

**Interims (R22, flagged):** the unblock-checker (stage D) still runs as an AGENT seat until its deterministic CLI exists. ⚠ The former "passes run serially until the daemon supports N parallel passes" clause is RETIRED as a doc artifact, not a fixed limit: the consumer drains EVERY open request of a goal in one cadence (`engine/queue-request.js`, the request loop — no bound, no per-goal pass cap) and no concurrency cap exists anywhere in `engine/` or the ticker. A milestone whose PASS unblocks four successors opens four passes in the same cadence; the flagship `meet-transcript-summarizer` is exactly that 4-parallel case. Its output is no longer an interim, though: as of W7 it mints a real `queue-request` message per queued pass and the daemon drains it (`coordinate queue-requests --json`), and each pass is spliced as ONE nested materialization of this workflow. What remains interim is the OCCUPANT, not the mechanism.

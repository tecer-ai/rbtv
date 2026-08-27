---
name: plan-console
default-execution-mode: interactive
four-letters: plan
---

# plan-console — the workflow

**Four letters (`plan`).** The prefix every seat-id in `plan-console.csv` shares (`plan-understander`,
`plan-designer`, …) — mechanically required by the bindings capability's `workflow_code()`, which
REFUSES a manifest whose rows share no single four-letter prefix. It names this workflow's casting
sheet (`.rbtv/config/modules/meta/planning/bindings/plan.json`) and is the prefix this workflow's
seats carry inside a goal.

**Default execution mode.** `interactive` — declared above, in this workflow's own scaffolding. It
is the value a goal created from this workflow is BORN with: goal creation writes it into
`.rbtv/goals/<goal>/execution-mode`, and from there the control plane gates every agent-initiated
owner contact on it. Declared rather than left to derivation because derivation would reach the
same answer here (every row below carries Modality `interactive`) and the DECLARATION is what lets
a later owner ruling say otherwise without rewriting the manifest. Resolution when a workflow
declares NO `default-execution-mode:` — any manifest row whose Modality reads `interactive` →
`interactive`, none → `autonomous`. A per-goal value supplied in the creation request overrides
this default; this is the floor, never a lock.

**Goal.** Turn a planning request — an ad-hoc goal, an optimize, a port, or a scaffold ask — into an
owner-approved plan: a full milestone list, the execution seats/workflow that will run it, and a
digest the owner approves from a phone. Rolling planning is dead: planning runs once to completion,
then stops for approval — it never executes the plan and never opens or materializes anything
itself (the daemon does, on approval). Whether the plan lands as a durable workflow (scaffolding,
reusable) or a one-off taskforce (in the goal's own folder) is the owner's declaration at goal
creation, honoured by the draft stage — no agent mints durable scaffolding on its own, and no seat
in this DAG branches on it.

**Approval is a BIRTH, and the plan must say what is born.** The owner's `approve` runs a Path-B
birth: it scaffolds a NEW goal folder under `.rbtv/goals/` and MINTS its roster. There is no
"execute in place" inside the planning goal, and no seat — here or in the born goal — ever casts an
execution seat by hand. So the draft carries an EXECUTION DECLARATION naming what the birth needs
and nothing more: the `execution-goal` name (a bare safe name, `^[A-Za-z0-9][A-Za-z0-9._-]*$`, never
`owner`), the `lane`, the `roster` of seat ids, and `workflow` + `sheet` where the plan lands as a
durable workflow (omitted, explicitly, for a one-off taskforce), plus `contract-file` where the plan
names one. Those are exactly the fields `ignite/planning/approve_package.py` takes; the review stage
makes a missing or invalid declaration a `blocking` finding, and the verify stage passes them
through to the writer rather than authoring any of them.

**Scope.** Four lean stages, one seat each, plus a fifth verification seat — five seats, one linear
pass, no per-milestone teams and no goal-level/per-milestone split. Every stage seat is an
orchestrator of sub-agents (`plan-researcher` / `plan-diagnoser`, fanned out with no manifest row —
results return to the dispatcher and die with the step). All five seats may ask the owner; none has
an ask-cap and none has a wall-clock deadline (a planning seat's only clock is the daemon's shared
~30-min no-progress kill).

**Procedure (`plan-console.csv` is the whole DAG — five rows, linear, no forks, no guards).**

1. `plan-understander` — reads the goal seed and every artifact it names, grounds itself with
   `plan-researcher` / `plan-diagnoser` where needed, and writes `planning/facts-brief.md`: the
   goal restated, its constraints, a salvage inventory (existing work products this re-plan may
   reuse), and a credentials/preferences inventory (names only, never values).
2. `plan-designer` — reads the facts brief, picks ONE approach, and writes `planning/design.md`:
   why that approach, and the FULL milestone list (not a first slice) with per-milestone
   done-criteria — each an observable, a probe, and a threshold.
3. `plan-drafter` — reads the design and the facts brief, and writes `planning/draft-plan.md`:
   every milestone from the design detailed, the EXECUTION DECLARATION (above), the execution
   seats/workflow, a permission-envelope section and a credential-name section (sections, never
   compiled — planning seats themselves run under the shipped standard planning envelope), per-seat
   interact flags, declared outputs, and a relaunch budget. Every produced execution seat carries
   the six `workflow-authoring-checklist` declarations.
4. `plan-reviewer` — trials the draft ONCE against the frozen milestone list, the six
   declarations and the execution declaration, emits a findings list tagged `blocking` /
   `non-blocking`, revises ONLY the blocking findings (non-blocking ships as accepted residue), and
   writes `planning/review-package.md`: the tagged findings, the revised plan, and the approval
   package (what the owner is being asked to bind, and that approval binds at a git commit).

   **The 4→5 edge is where the plan is BOUND.** No seat in this DAG can record the binding: every
   one runs caged and `.git` is a default mask (`ignite/supervisor/spawn/private-scope.js`), so
   `git rev-parse HEAD` inside one answers "not a repository". The goal's `leader` performs it — it
   is uncaged and holds git. When it ACCEPTS `plan-reviewer`'s row it commits the goal's `planning/`
   folder to the vault BY PATHSPEC (`git -C <vault root> add .rbtv/goals/<goal>/planning` then
   `git -C <vault root> commit -m "<goal>: plan artifacts for approval" -- .rbtv/goals/<goal>/planning`,
   never `add -A`, never `--amend`) and writes the hash `git rev-parse HEAD` prints, alone on one
   line, to `planning/bound-commit`. That file is the ONE source `plan-verifier` reads the binding
   from, and the verifier REFUSES to compose the ask without it — a refusal that wakes the `leader`
   to bind and relaunch it. The act and its exact commands live in `meta/leader/prompts/leader.md`
   §4, as a generic rule over ANY accepted seat whose `goal-writes` lands under `planning/`.
5. `plan-verifier` — runs exactly two checks (closed findings addressed; the design's milestone
   list still unbroken), caps regression fix passes at TWO (`REGRESSION-PASS` lines in its own
   `memory.md`), and composes `planning/approval-digest.md`: milestones, seat count, envelope
   summary, which seats are interactive, credential-resolve result, red flags (including
   `unresolved regression` if the cap was hit), artifact paths, the plan's execution declaration
   and the bound commit read from `planning/bound-commit` — then
   SENDS it to the owner as the APPROVAL ASK: one `coordinate send owner --type note
   --approve-commit <the bound commit>` row on the goal's own bus, which the chat bridge turns
   into an approval thread in the goal's Slack channel. It does NOT author the owner's reply
   tokens (the thread publishes them from the parser's vocabulary) and it never parses a reply —
   the owner's `approve` in that thread starts execution through the daemon's `start-execution`
   intent, and this workflow is over.

**The regression loop.** `plan-verifier` is the only seat with an `on-fail-relaunch` entry —
`plan-reviewer,plan-verifier` — declared on the seat that ISSUES the verdict, per
`workflow-authoring-checklist`. A failed check re-fires the reviewer (fix the named items only,
never a new findings pass) then the verifier itself (re-run the same two checks, nothing more). At
most two such fix passes; a third failure ships the digest with the `unresolved regression` red
flag instead of failing again.

**Reject-and-retry, after approval.** A `reject-and-retry` owner reply is NOT this workflow's `after` DAG —
it is a fresh relaunch of `plan-reviewer` + `plan-verifier` only (the owner's comments become the
closed findings list), fired by whatever consumes the approval-thread reply. An owner-declared
approach rethink instead reruns the full five-seat pipeline; this workflow's own manifest is
identical either way.

**Inadequate input, any stage.** Repair the gap yourself, log it in `input-gaps` and the goal's
`decisions.md` (or `doubts.md` if unclosable), and continue. No stage re-entry, no rejection
verdict — a stage that receives a markerless or thin upstream artifact never re-enters the seat
that should have produced it.

**Next-stage launch** is the ordinary task-graph `after` edge — no splice, no new mechanism. The old
17-row per-milestone splice (a goal-level phase plus a per-milestone team) is GONE, not merely
unused: its seventeen seat rows and their orphaned prompt/task files were deleted from `seats.csv`
and the pools on 2026-08-24. Nothing in this component defines an interviewer, a splitter, a
dag-structurer, a per-milestone definer/assembler/binder, a check swarm, or a collapsed-mode
planner any more, and no `planning-mode` fork exists to choose between them.

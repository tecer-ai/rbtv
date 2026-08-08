# run folder — this run's router

Run folder (KG `run folder`): this run's mortal working state. Shipped as the goal-generic STARTER
SET and byte-copied here at scaffold time (`scaffold-seats --claude-md`); from that copy onward it is
THIS run's own router.

**This file is a ROUTER (PRIN-3) — auto-loaded by folder, just-in-time.** It carries the run's
surfaces, ownership map, roster and navigation, and **never the run's conduct, state, or log.**
What binds every seat's behavior lives in `conduct.md`; what only some seats need lives behind a
reference. A router that inlines what a folder artifact should carry taxes every seat for content
only some need — the predecessor router that did reached 338,676 characters, 3.8% of it rules, before
it was split.

**Read `conduct.md` next.** Terminology is king (PRIN-10): `sd-graph show <term>` before using ANY
system term.

## Where things are

Paths are relative to this run folder. The goal root is `../../`.

| Path | What it is |
|------|-----------|
| `../../goal.md` | the goal's contract and its done radius |
| `../../decisions.md` | GOAL-DURABLE rulings (`r-*`/`d-*`) — owner rulings, contract amendments, plan rationale |
| `./decisions.md` | this run's own PROVISIONAL rulings (`p-*`), mortal with the run |
| `../../runs.csv` | the run register — the ONLY answer to "is this run live?" |
| `../../doubts.md` · `../../issues.md` · `../../ideas.md` | owner-decision queue · open questions · framed-but-unruled |
| `3-resources/tools/rbtv/ignite/team-kit/protocol.md` | the coordination protocol — messaging, identity, lifecycle mechanics (workspace-root-relative) |
| `3-resources/tools/rbtv/ignite/team-kit/communication.md` | how this run talks |

**Resolve a cited anchor; never scan a ledger.** `r-*`/`d-*` resolve in `../../decisions.md`; `p-*` in
this folder's `decisions.md`. No seat has a whole-file read duty on either.

## Coordination

A seat's cwd is its own seat folder, so a bare `coordinate <cmd>` resolves this package by walk-up.
Give `--package <absolute path to this run folder>` only when invoking from outside it. **Never write
an absolute package path into a standing file** — resolve it at the instant of use.

## What exists in this folder, and who writes it

Created by the scaffold act. Everything else is minted by its own writer when first needed — an
absent file below is NORMAL at run birth, not a defect.

| Surface | Present at creation | Writer — write ONLY inside your row |
|---------|--------------------|--------------------------------------|
| `conduct.md` | yes (caller-supplied) | frozen; an amendment is a run-authority ruling recorded in `./decisions.md` |
| `CLAUDE.md` (this file) | yes (caller-supplied) | the run authority; amendments are rulings |
| `budget.json` | yes (caller-supplied) | the run authority — **a number here without a ruling is a defect** |
| `taskforce.csv` | yes, HEADER-ONLY — `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id` | the materialize command only. **No agent hand-writes a seat folder or a taskforce row.** No `status` column exists: run-state is DERIVED from the check-out record |
| `state.csv` | yes, HEADER-ONLY — `stamped-at,run-state,seat,session-id,note` | the run authority — the run cursor: **APPEND-ONLY, one row per run-state ADVANCE**, never per turn or per commit. Position only; narrative goes elsewhere |
| `seats/<seat>/` | yes, empty | the materialize command only |
| `coordination/` | yes, empty | scripts only — `coord.py` state lands here on demand |
| `sessions.csv` · `state.json` | no | script-managed — `coord.py`'s launch/close hooks and the `team-monitor` sensor. **Never hand-edited** |
| `./decisions.md` | no | the run authority (PROVISIONAL `p-*` rulings) |
| `milestones.csv` · `planning/` | no | the planning DAG's seats — see the roster below |
| `handoff-log.md` | no | any seat APPENDS its own sitting block; groomed at milestone close. **Append-only, never corrected in place** — corrections arrive as later blocks. Never edit another seat's block |
| `bars.md` | no | the run authority, minted only if needed. A bar goes there only if it binds EVERY seat whatever its task is; a bar binding ONE role belongs in that role's own `seat.md` |
| `seed.md` · `passes.csv` | no | minted by the act that needs them, which names its writer in the same change |

**Any write outside your row: claim by message first, and wait.** A surface not listed above has no
writer yet — name one before you write to it.

## Roster — the planning DAG

This run opens with the **planning workflow: 9 seats**, materialized whole at scaffold. The entry
seat is **`elicitator`**; downstream seats exist so readiness can advance over their rows. A live
census is RESOLVED at the instant of use from `coordinate workers` / `taskforce.csv` — **never
written into this file and never into any other.**

| Seat | after | Produces |
|------|-------|----------|
| `elicitator` | — (root, entry seat) | the elicitation brief: unambiguous done contract, final-milestone statement, task-store review |
| `planning-strategist` | `elicitator` | milestone rows + the milestone spine (per-milestone done contracts) |
| `execution-strategist` | `elicitator` | the execution strategy — loop, branch, verification-swarm and resource-lane patterns with their application criteria |
| `execution-tactical-designer` | `planning-strategist`, `execution-strategist` | the next milestone as a task DAG — after sets, per-task i/o, guards, per-task done contracts |
| `execution-tactical` | `execution-tactical-designer` | task-store rows via the `sb-task` CLI + the pass manifest; a DRAFT workflow manifest |
| `workflow-designer` | `execution-tactical` | the milestone's execution workflow as a DAG of seat references |
| `seat-designer` | `execution-tactical` | the seat definitions that workflow orders — one roster row per seat plus its prompt and task cognitive units |
| `staffer` | `workflow-designer`, `seat-designer` | the executor binding per seat (harness, model, effort, ctx-refresh). **Writes no seat folder and no taskforce row** — the materialize command does |
| `ledger-groomer` | — (root, parallel) | `../../issues.md` deduped and rated, with a computed proof that every cited id still resolves |

`workflow-designer` and `seat-designer` are a PARALLEL PAIR and **neither names the other** — they
interact by message; an edge would serialize them. `ledger-groomer` neither blocks nor is blocked by
the planning of the next milestone.

**A scaffolded planning run rosters no meta seat** — no authority seat, and **no `chief-of-staff` or
`closer`, which are RETIRED roles**. If a meta seat is added later, its definition is materialized
from its own component folder under `.rbtv/mirror/meta/`, never hand-written here. `conduct.md` § 4
governs what happens to an escalation while no authority seat is rostered.

## Who resumes from what

**Every seat boots from its own DESCRIPTOR + `conduct.md` (+ `bars.md` once minted), and does NOT
read `handoff-log.md`.** A seat's resume contract is its OWN seat folder: the durable half in its
`seat.md`, the dated working half in that folder's `memory.md`. If a seat needs a fact it does not
have, **its `seat.md` is incomplete — the fix goes in the `seat.md`**, and it is the staffing stage's.
No seat resumes from another seat's state.

**HOW the descriptor reaches you depends on your harness, and you do NOT go looking for it.** On
`claude` your `seat.md` is appended to your SYSTEM PROMPT — it is already above this file; act on it.
On `codex`, `opencode` and `kimi` your seat folder carries a generated `AGENTS.md` whose ONLY job is
to send you to `seat.md` **before your first word**; obey it. A seat launched by hand or by
`coordinate launch` gets no system-prompt append on any harness: read your `seat.md` yourself, first,
and do not ask whether to.

The normative home of the `memory.md` / `handoff-log.md` write contract is the team-kit
`protocol.md` § Memory — this section cites it and restates nothing.

## Closing this run

Closing is TWO writes in ONE act, per `.rbtv/goals/CLAUDE.md`: set `state=closed` + the timestamp in
`../../runs.csv`, AND put the frozen banner at the VERY TOP of this file, above the title. Do not
split them: a run marked closed in the register with no banner is a trap — the next agent seated here
reads live-sounding instructions and acts on them.

# goal folder — this goal's router

The goal folder: this goal's working state, and the goal's package. Shipped as the goal-generic
STARTER SET and byte-copied here at scaffold time (`scaffold-seats --claude-md`); from that copy
onward it is THIS goal's own router.

**This file is a ROUTER (PRIN-3) — auto-loaded by folder, just-in-time.** It carries the goal's
surfaces, ownership map, roster and navigation, and **never the goal's conduct, state, or log.**
What binds every seat's behavior lives in `conduct.md`; what only some seats need lives behind a
reference. A router that inlines what a folder artifact should carry taxes every seat for content
only some need — the predecessor router that did reached 338,676 characters, 3.8% of it rules, before
it was split.

**Read `conduct.md` next.** Terminology is king (PRIN-10): `sd-graph show <term>` before using ANY
system term.

## Where things are

Paths written `./` are relative to THIS folder, which IS the goal root — a goal's working content
sits directly under it (`decisions.md#d-runs-extinguished`,
`#d-extinguishment-design-lock` item 8), so this file is the goal folder's CLAUDE.md and its ledgers
are its siblings.

| Path | What it is |
|------|-----------|
| `./goal.md` | the goal's contract and its done radius |
| `./decisions.md` | the goal's rulings — owner rulings, contract amendments, plan rationale, and PROVISIONAL `p-*` anchors (which are DURABLE and pruned by hand, design-lock item 6) |
| `./doubts.md` · `./issues.md` · `./gotchas.md` · `./ideas.md` | owner-decision queue · open questions · validated patterns and traps worth carrying forward · framed-but-unruled |
| `3-resources/tools/rbtv/ignite/team-kit/protocol.md` | the coordination protocol — messaging, identity, lifecycle mechanics (workspace-root-relative) |
| `3-resources/tools/rbtv/ignite/team-kit/communication.md` | how this run talks |

**Resolve a cited anchor; never scan a ledger.** Every anchor — `r-*`, `d-*`, `p-*` — resolves in
this folder's `decisions.md`. No seat has a whole-file read duty on it.

**"Is this goal executing?" has no stored answer at all** — it is DERIVED at ask time from the goal's
tmux room and its live seat processes (`#d-extinguishment-design-lock` item 1).

## Coordination

A seat's cwd is its own seat folder, so a bare `coordinate <cmd>` resolves this package by walk-up.
Give `--package <absolute path to this goal folder>` only when invoking from outside it. **Never write
an absolute package path into a standing file** — resolve it at the instant of use.

## What exists in this folder, and who writes it

Created by the scaffold act. Everything else is minted by its own writer when first needed — an
absent file below is NORMAL at goal birth, not a defect.

| Surface | Present at creation | Writer — write ONLY inside your row |
|---------|--------------------|--------------------------------------|
| `conduct.md` | yes (caller-supplied) | frozen; an amendment is a run-authority ruling recorded in `./decisions.md` |
| `CLAUDE.md` (this file) | yes (caller-supplied) | the run authority; amendments are rulings |
| `budget.json` | yes (caller-supplied) | the run authority — **a number here without a ruling is a defect** |
| `taskforce.csv` | yes, HEADER-ONLY — `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id` | the materialize command only. **No agent hand-writes a seat folder or a taskforce row.** No `status` column exists: run-state is DERIVED from the check-out record |
| `state.csv` | yes, HEADER-ONLY — `stamped-at,execution-stamp,goal-state,seat,session-id,note` (the KG `state-cursor` column list; `execution-stamp` ADDED and `run-state` RENAMED `goal-state` by owner ruling `d-runs-extinguished-transcription`, 2026-08-09) | the run authority — the goal cursor: **APPEND-ONLY, one row per goal-state ADVANCE**, never per turn or per commit. Position only; narrative goes elsewhere |
| `seats/<seat>/` | yes, empty | the materialize command only. Inside its OWN seat folder each seat keeps `memory.md` and, **created the first time it is needed and never speculatively**, the three standard folders `downloads/` (fetched files) · `scratchpad/` (working scratch) · `outputs/` (finished artifacts). The names are fixed so a reader finds them without asking; the folders are absent until used. An in-process probe a seat fans out writes ONLY under its own dispatch subfolder `scratchpad/probes/<short-name>-<n>/` — one folder per dispatch, so concurrent probes never collide on a filename and every return traces to the dispatch that produced it |
| `coordination/` | yes, empty | scripts only — `coord.py` state lands here on demand |
| `addressable.csv` | yes — the register that makes the standing owner door a legal address before any authority seat is rostered, so `conduct.md`'s tier-2 escalation resolves. Carries a PATH ONLY, relative to this folder; the name and the role word come from the descriptor the correspondent itself owns, which must declare `addressable: non-member` AND `relays:`. ⚠ **The ONE OPTIONAL creation surface** (7.569): `scaffold-seats --addressable <file>` byte-copies a supplied register, and a bootstrap creation WITHOUT the flag DERIVES the rows from the standing-seat homes that declare the opt-in themselves — so a goal born under a goals root that offers no door simply has no register, exactly as before. Optional and not a fourth REQUIRED input deliberately: a required one would make every caller that does not pass the flag — the armed goal-creation loop included — start refusing `create-inputs-missing`. ⚠ The starter set ships NO copy of this file: `starter-set/addressable.csv` was DROPPED 2026-08-10 by owner ruling `d-r2-addressable-dropped`, not repaired — its one row spelled a three-level walk-up to the `_channel-master` seat file, written for the extinct run-layer compartment, that resolves to nothing. A shipped row carries a FROZEN depth; the 7.569 bootstrap derivation (`derive_addressable_register`) computes the depth against the actual layout and is now the SINGLE source of these rows | the run authority; a row added here is a ruling |
| `sessions.csv` · `state.json` | no | script-managed — `coord.py`'s launch/close hooks and the `team-monitor` sensor. **Never hand-edited** |
| `./decisions.md` | no | the run authority (PROVISIONAL `p-*` rulings) |
| `milestones.csv` · `planning/` | no | the planning DAG's seats — see the roster below |
| `handoff-log.md` | no | any seat APPENDS its own sitting block; groomed at milestone close. **Append-only, never corrected in place** — corrections arrive as later blocks. Never edit another seat's block |
| `bars.md` | no | the run authority, minted only if needed. A bar goes there only if it binds EVERY seat whatever its task is; a bar binding ONE role belongs in that role's own `seat.md` |
| `seed.md` · `passes.csv` | no | minted by the act that needs them, which names its writer in the same change |

**Any write outside your row: claim by message first, and wait.** A surface not listed above has no
writer yet — name one before you write to it.

## Roster — the planning DAG

This goal opens with the **planning workflow: 9 seats**, materialized whole at scaffold. The entry
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
| `ledger-groomer` | — (root, parallel) | `./issues.md` deduped and rated, with a computed proof that every cited id still resolves |

`workflow-designer` and `seat-designer` are a PARALLEL PAIR and **neither names the other** — they
interact by message; an edge would serialize them. `ledger-groomer` neither blocks nor is blocked by
the planning of the next milestone.

**A scaffolded planning workflow rosters no meta seat** — no authority seat, and **no `chief-of-staff` or
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
On `codex`, `opencode` and `kimi` your seat folder carries a generated `AGENTS.md` whose first job is
to send you to `seat.md` **before your first word**; obey it. (It closes with one standing rule for
every harness — where a tooling-gap finding is filed; the goal folder's router carries the same
text.) A seat launched by hand or by
`coordinate launch` gets no system-prompt append on any harness: read your `seat.md` yourself, first,
and do not ask whether to.

The normative home of the `memory.md` / `handoff-log.md` write contract is the team-kit
`protocol.md` § Memory — this section cites it and restates nothing.

## Finishing this goal

**A goal is finished by ONE act** — the deterministic FINISH EDGE (`#d-extinguishment-design-lock`
item 3), fired as `coordinate finish-goal`. There is nothing else to close and no register to stamp.
Firing it is what shuts the watchers off, and nothing else does: an absent room is a
CRASH the watcher RECOVERS by relaunching, never a finished goal. Do not write a status anywhere to
mean "over" — a stored status that outlives what it describes is the exact defect the register was
extinguished for (it deadlocked every fresh goal, 7.608).

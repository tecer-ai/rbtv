---
description: The meta module — home of every meta agent and meta workflow of the rbtv system (the agents and workflows that operate the system itself, not any user goal).
---

<module>

# meta

The `meta/` module hosts the system's own agents and workflows.

**Minted convention (owner, 2026-07-26):** every META agent and every META workflow — an agent or workflow whose subject is the rbtv system itself (intake, planning, staffing, oversight) rather than a user goal's content — is hosted in the `meta/` module. No meta agent or meta workflow may be homed in another module.

**Extension (owner, 2026-08-14):** a CAPABILITY-ONLY component — one holding no seats and no workflow, only `component.md` + `exposure.csv` + its capabilities — is admitted here on the SAME subject test: what the capability operates ON is the rbtv system itself, not a user goal's content. The convention above states what MUST be homed in `meta/`; it never said only agents and workflows MAY be. The shape is not new to the mirror either — `web/browse/` is a capability-only component — this line only records that `meta/` admits one. First instance: `providers/`.

Status: registered in the system-definition ledger — `1-projects/rbtv-sb-merge-refactor/system-definition/decisions.md#d-meta-module-hosting` (2026-07-26); the convention's registry home is `concepts/meta.md` § Module home.

## Components

| Component | What it is |
|-----------|-----------|
| `master/` | The master — the system-plane agent that sees the whole system and is the single request door. **THREE seats** since `d-master-in-run-seat` (2026-07-28): `channel-master`, `console-master`, and a third that LAUNCHES FROM INSIDE A RUN AND HOLDS A SEAT THERE (a `console master` variant, reached when the owner is directly inside the tmux session the run occupies; formerly the seat-id `owner-liaison`). That third seat's KG TERM is UNMINTED and is owed to the registry — it is referred to descriptively here, never by a coined name (`PRIN-10`; `master/component.md` § Open design point 1). |
| `chief-of-staff-agent/` | **RETIRED — tombstone row; the component folder is DELETED.** `chief-of-staff` and `closer` are RETIRED ROLES (`ignite/team-kit/starter-set/conduct.md` § 4): never wake, spawn, address, or fall back to one, and any code, config or prompt that does is built against a dead spec — flag it, never extend it. Where its duties went: the stewardship and ENGINE half (ready-SEAT sweep, ready-TASK sweep, launch, context-refresh nudging) to the **ignite engine**, which is what it stood in for until the core existed (`d-cos-engine-bounds`); the materialize half is DISSOLVED — `rbtv-goal materialize` runs once per goal and refuses to regenerate (without `--force`), and a goal needing one more seat later gets a `scaffold-seats` call from the seat holding that goal's authority (the `leader`). |
| `planning/` | **LIVE.** The planning-and-staffing meta-workflow component (planning-v4) — successor to `planner-workflow/`, renamed 2026-08-09 so `planning` resolves uniquely here (`01f60de16`, R11/D6). Carries `component.md`, `seats.csv`, `exposure.csv` and the `capabilities/`, `prompts/`, `references/`, `tasks/`, `workflows/` pools. |
| `rbtv-cli/` | The ONE system-wide `rbtv` CLI — the disclosure drill (modules → components → entry points) plus the action-verb router that delegates to the surfaces that already ship. Moved here 2026-08-23 from the retired `core/capabilities/rbtv-cli/` (owner ruling: the rbtv CLIs live in `meta/`, each command a component — the CLI operates on the rbtv system, `meta`'s subject test). |
| `teambuild/` | The staffing-discovery browse (`rbtv teambuild`) — list or semantically search the component databases (agent cards, cognitive units, seats, tasks, workflows), binding nothing. Moved here 2026-08-23 from `core/capabilities/teambuild/` (same ruling as `rbtv-cli/`). |
| `embed-search/` | Standalone folder search (`rbtv embed-search`) — index markdown sections and rank by meaning, keyword, or substring; purpose-free, binding nothing. Moved here 2026-08-23 from `core/capabilities/embed-search/` (same ruling as `rbtv-cli/`). |
| `providers/` | **COMPONENT FOLDER RELOCATED 2026-08-21 — tombstone row.** Moved whole (`component.md` + `exposure.csv` + `capabilities/acct/`) to `core/providers/` — `meta/` no longer hosts it. Created 2026-08-14 (owner-directed) as the seam between this workspace and whoever supplies its compute; `cast` had already relocated out to its own component at `core/sub-agents/` on 2026-08-20 before the rest of `providers/` followed it out of `meta/` the next day. Why one component: `PRIN-6` is agnostic to the HARNESS that runs the loop and to the PROVIDER that supplies the model and the entitlement, both abstracted and neither decomposed (amended 2026-08-14, `system-definition/decisions.md#d-prin6-provider-abstraction`) — this is where that interface is implemented. Prior content lives in git history. |
| `leader-agent/` | **COMPONENT FOLDER DELETED 2026-08-10 — tombstone row** (owner-directed, vault commit `d2268e6f8`, 15 files). Only the folder was removed; the `leader` ROLE is NOT retired (it still holds a goal's authority — see the `chief-of-staff-agent/` row). Prior content — REACTIVE judgment over ONE goal's taskforce (asks, relayed approvals, arbitration, acceptance with a same-turn done mark, provisional rulings, closing routed `exited` rows) plus exactly ONE proactive lane, the plan-blocking briefing, agents-only contact routing leader → master → owner (`d-comm-topology-correction`, `d-leader-reactive-plus-briefing`) — lives in git history. |
| `watcher-agent/` | **RETIRED 2026-07-28** (`d-watcher-agent-retired`) — tombstone only. Its duties went to `chief-of-staff-agent/` (stewardship, DAG-unblock launching) — itself RETIRED since, see the row above, so those duties are now the ignite engine's — and topic-1's seat lifecycle (deputy standby superseded); prior content lives in git history (commit `864e54a1a`). |
| `scientist-agent/` | **COMPONENT FOLDER DELETED 2026-08-09 — tombstone row**, removed in the owner-directed meta-mirror deletion sweep (vault commit `a17b28147`, task 7.589/Q20). No retirement of the scientist ROLE was ruled — the folder is what is gone. Prior content (in-run compounding: harvests what a live run teaches the system; feeds, never curates) lives in git history. |
| `planner-workflow/` | **RENAMED, THEN FOLDER DELETED — tombstone row.** Renamed `planner-workflow/` → `planning-deprecated/` on 2026-08-09 (`01f60de16`, R11/D6 — killing the workflow-`planning` ambiguity), and `planning-deprecated/` was dropped in the 2026-08-10 meta-mirror sync (`ea3691d9b`). **The live component is `planning/` (row above)**; prior content lives in git history. Its design, unchanged by the rename: **Planning AND staffing — ONE meta-workflow** (`d-planning-staffing-one-workflow`), authored as a true **nine-seat DAG**, not a chain (`d-planner-dag-with-collapse-mode`): `elicitator` fans out to `planning-strategist` + `execution-strategist`, which fan in at `execution-tactical-designer` (the micro-planner) → `execution-tactical`, which fans out to the PARALLEL DESIGNER PAIR `workflow-designer` + `seat-designer` (interacting by message, never by edge), which fan in at the `staffer` — the FINAL executor-binding stage. Eight of the nine are rows of `workflows/planning/planning.csv`; the ninth, `planner`, is the COLLAPSED MODE's single seat and is deliberately not a manifest row. Output = `milestones.csv` + `taskforce.csv` (`d-planning-output-is-the-two-csvs`), with the intermediate products on the run's per-milestone planning surface. |
| `staffer-workflow/` | **DISSOLVED** (`d-planning-staffing-one-workflow`, 2026-07-28) **and COMPONENT FOLDER DELETED 2026-08-10** (`ea3691d9b`) — tombstone row. The separate one-seat staffing workflow folded into the planning workflow's final executor-binding stage, occupied by the `staffer` seat now living in `planning/`. Its first-draft reference text and superseded-by `component.md` live in git history. |

**Currency of this table (step-1 checker, 2026-07-28; phantom-row repair, 2026-08-10 — task 7.687).**
The 2026-08-10 pass reconciled every row against an `ls` of `3-resources/tools/rbtv/meta/`: only `master/`
and `planning/` exist on disk, `planning/` had no row (added), and `leader-agent/`, `scientist-agent/`,
`planner-workflow/` and `staffer-workflow/` were phantom rows describing deleted folders — each is now
a tombstone naming its deletion commit, matching the treatment `chief-of-staff-agent/` got in `e58da3dd0`.
The rows above were first brought to current truth
by the checker that closed the topic-2 design wave. Three of them were stale: `chief-of-staff-agent/`
was missing outright (the component is new and fell outside every authoring agent's write set),
`planner-workflow/` was described as a "five-role" sequential chain, and `staffer-workflow/` was listed
as live. Two divergences are RECORDED, NOT RESOLVED, because resolving either needs a ruling this file
may not make:

- **`watcher-agent/` overlap — RESOLVED 2026-07-28.** The owner retired the component
  (`d-watcher-agent-retired`, ruling A-34): files deleted after verifying the folder was clean at
  git HEAD (`864e54a1a`), tombstone `component.md` maps each former duty to its ruled home. The
  same sitting stripped the dissolved `staffer-workflow/` catalogs (`d-staffer-catalog-stripped`,
  A-35), ending the four `staffer*` id collisions with `planner-workflow/`.
- **The master's third seat has no KG term.** `master` alone is unambiguous only inside a run folder.
  The mint is owed to the registry as an appended `F-` row (`d-ledger-cleanup-wave` scope (c)) and is
  never coined here.

</module>

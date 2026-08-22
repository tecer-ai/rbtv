---
description: Primer addendum, read at the moment of structuring a workflow DAG, authoring its manifest, or binding its taskforce — the workflow/graph mechanics the primer under-covers.
tags: [planning]
---

# Workflow anatomy — the graph side, in practice

Companion page to `system-definition/primer.md` (orientation; read it first — this page adds the workflow/graph mechanics it under-covers). You are structuring a DAG, defining task edges, assembling a manifest, or binding executors — the same mechanics serve an ad-hoc goal, an optimize pass, a port, and a scaffold build. `sd-graph show <term>` every term before use. Component-side artifacts (pools, `seats.csv`, capability folders) are `component-anatomy.md`'s (sibling) — nothing component-side is decided here.

## 1 — Where the definition lands (two inscriptions)

- **Scaffolding** (a cataloged product — an optimize, port, or scaffold output, or explicit owner intent): a workflow folder `workflows/<workflow>/` in its owning component, pairing `workflow.md` (the entry point — the workflow's OWN goal · scope · procedure prose, its body, never assembled from units) with `<workflow>.csv` (`sd-graph show "workflow folder"`).
- **Goal folder** (ephemeral — the default for an ad-hoc goal's product): NO workflow folder, no catalog rows; the run's `taskforce.csv` plus each produced seat's FULL-content `seat.md` IS the inscription (`d-planning-ephemeral-default`). A reused cataloged seat is named by its source prompt/task ids in `seat.md` frontmatter.

## 2 — The manifest (`<workflow>.csv`)

One row = one seat REFERENCE — a seat-id minted in `seats.csv` (the manifest ORDERS seats, never joins executor to task), or a nested workflow. Columns — Seat/workflow · `after` · i/o · Modality — per `sd-graph show "workflow manifest"`. There is no Order column: order is derived from the DAG, and authoring one is a defect.

## 3 — `after` sets: an edge is data moving, nothing else

- Author an edge ONLY where a datum actually crosses: the upstream seat's OUTPUT is the downstream seat's SEED. No datum, no edge — birth order, narrative sequence, and caution mint no edges.
- Empty `after` = a root; independent rows run in parallel; the graph MUST be acyclic (goal-lint rejects cycles).
- Routing without judgment: an `after` entry may carry a guard `ref[field=value]`, evaluated deterministically by the edge-runner against the predecessor's validated output; `a|b` is a whichever-ran join. Judgment lives at seats; edges only verify and route.

## 4 — Seed flow and edge checks (what your authoring must survive)

- The entry seat's seed comes from the workflow's entry capability; every other seed is machine-fed from an upstream output. A seat starts when its `after` set is satisfied AND its declared inputs exist — so every seat declares its i/o, and an undeclared input is a seat that never starts.
- On each seat finish, the edge job runs the check derived from that seat's done contract. Author every done contract MACHINE-CHECKABLE — an edge job cannot verify prose intent; a contract you cannot state as a runnable check is not finished being authored.

## 5 — `taskforce.csv`: the run's binding

- ONE per run (`sd-graph show "taskforce-descriptor"`); each planning pass APPENDS its team's rows — never a file per milestone.
- A row binds one seat to its executor: harness + model + effort + ctx-refresh for an agent; capability→tool for a deterministic seat. Binding is LATE: no static file names a model or harness — recommendations live as hints (the seat catalog's per-pairing staffing-hints override the prompt's frontmatter), bound only here.
- **The taskforce also carries the goal's STAFF CHAIRS, and a workflow declares which it wants.** `leader` is MANDATORY — every taskforce staffs one — and `consultant` is OPTIONAL, decided per workflow. Neither holds a manifest node or an `after` set: they are ON-DEMAND chairs reached by mail, minted into `taskforce.csv` by `goal-materialize` itself, so no seat you author declares them and no edge points at one. Declaring one = CASTING it: the chair is minted only where a casting sheet exists at `.rbtv/config/modules/<module>/<component>/bindings/<chair>.json`. An absent `consultant.json` is the workspace stating it staffs none, and everything routed there falls back to the `leader`; an absent `leader` sheet is a materialize WARNING, because the goal then has no chair for a routed FAIL, a mid-run ask or the session-closer's staff mail to reach.
- `after` (guards included) is FROZEN-copied from the manifest at instantiation — a mid-run manifest edit never rewires a live run. No status column exists: run state is DERIVED from disk artifacts, never stored here.

## 6 — The pipeline gate (who acts)

Registered plan → goal-lint exit 0 → `goal-materialize` (deterministic, queue-fired) → launch → deterministic edge jobs advance the DAG. You author and register; the daemon opens, materializes, and advances. Your closing act is VERIFYING ON DISK what materialize produced — never trusting the registration.

## Stop rule

A graph need the manifest/taskforce contracts cannot express (a cycle you think you need, a non-deterministic guard, a status column): STOP and surface it — the contract is the constraint, not a suggestion.

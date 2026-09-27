---
id: write-seat
description: "Author the seeded seat piece's declarations inside the assigned probe folder — its catalog row, its manifest row where it holds a node, and the six declarations a produced seat must carry"
---

<task-goal>
Deliver one complete set of seat declarations for the seeded piece, authored to the graph law and the six-declaration checklist this task names.
</task-goal>

<scope>
- **Read:** the seeded piece row; the graph law, the declaration checklist, and the prose law in the guides named in this task's Guides bullet; the target component's `seats.csv` header and its workflow manifests, as the exact column formats the declarations must follow; the prompt and task the seat pairs.
- **Write:** the assigned filename inside the assigned probe folder — nothing else. Landing the rows in the live catalog and manifest belongs to the dispatching seat.
- **Guides — read whole before writing:** `references/workflow-anatomy.md`; `references/exposure.md`; `references/workflow-authoring-checklist.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- A file exists at the assigned filename inside the assigned probe folder, carrying the seat's `seats.csv` row in the LIVE header's exact column order and — where the piece row says the seat holds a workflow node — its manifest row in that manifest's exact column order.
- The seat's executor names a prompt file that exists in the target component's pool, and its task names a task file that exists there.
- The seat declares AT MOST ONE `goal-writes` output, as one path relative to the goal folder. It is never `sessions.csv`, `state.csv`, another seat's folder, `seat.md`, an absolute path, or a path climbing out with `..`. An empty cell is a deliberate statement that the product stays in the seat's own folder, and the return says so.
- Every instrument the seat must reach is declared in the paired prompt's `exposes:`, and every entry there satisfies `references/exposure.md` — the declaration law this criterion is scored against, key by key and reference by reference.
- Every one of those entries under `path`, `skill`, or `sub-agent` ALSO carries its own bullet in the paired prompt's `<resources>`, naming the part-id and saying in at most 280 characters how the occupant uses it. Exempt: the `rbtv:ignite/team-kit/coordinate` checkout grant, and every `command`, `rule`, and `hook` entry. Declaration 2 of `references/workflow-authoring-checklist.md` is what this criterion is scored against.
- Where the seat's role includes reaching the human, all three hold together: `human-interactive: yes` on the paired prompt, a typed `fallback`, and a manifest Modality of `interactive`.
- Every `after` entry names a datum that actually crosses — the named predecessor's declared OUTPUT is this seat's declared INPUT — and the manifest's i/o cell names that datum; no edge exists for birth order, narrative sequence, or caution.
- The manifest row's Modality is one of `deterministic`, `agentic`, `interactive`, and the row declares no Order column.
- A seat that holds NO manifest node is sanctioned by a `method=sub-agent` or `method=pool` row on its executor prompt, and the return names that row.
- The seat's `on-fail-relaunch` cell is filled ONLY where the seat ISSUES a FAIL verdict that re-fires a loop, and then it names — spelled exactly, in fire order — seats of this same workflow's `seats.csv`, including the issuing seat itself where the contract must be re-tried. Anywhere else the cell is EMPTY: an undeclared FAIL routes to the goal's `leader` chair, and a task id, milestone id, or staff chair in this cell is a well-formed name that names no relaunchable seat.
- No owner-specific value appears in any declaration — a channel id, path, account, host, or credential is run-time configuration.
- The return `{piece-id, kind, probe-path, self-check: pass|fail, evidence}` reached the dispatcher, its evidence naming, per declaration of the checklist, the drafted line that satisfies it.

Outcome map:

- **self-check pass** → the dispatching seat re-reads the declarations and lands them in the live catalog and manifest.
- **self-check fail** → the return still reaches the dispatcher, naming every failing declaration. Feedback schema: {piece-id, the declaration, the drafted line that fails it}.
- **The role needs two goal-folder outputs** → return `self-check: fail`; that is two roles, or one product not yet named. Feedback schema: {piece-id, the two products, which successor reads each}.
- **An instrument no exposure method fits** → return `self-check: fail` naming the instrument; never invent a method, a null value, or a side-channel column. Feedback schema: {piece-id, the instrument, how the seat would otherwise reach it}.
</done-contract>

---
id: write-capability
description: "Walk the capability existence ladder for the seeded piece, then author its in-place instruction file inside the assigned probe folder — or return the CLI routing that says no body is drafted here"
---

<task-goal>
Deliver either one complete capability instruction file for the seeded piece or the ladder result that refuses it, so the dispatching seat lands a capability only where one is warranted.
</task-goal>

<scope>
- **Read:** the seeded piece row; the capability law, the exposure law, and the prose law in the guides named in this task's Guides bullet; the target component's existing capabilities and its `exposure.csv`, to see what the scaffolding already carries.
- **Write:** the assigned filename inside the assigned probe folder — nothing else. Landing the file, registering it and exposing it belong to the dispatching seat.
- **Guides — read whole before writing:** `references/kind-capability.md`; `references/exposure.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- The existence ladder was walked in the guide's order and its result stated in the return, rung by rung: whether the scaffolding already carries the ability; whether this is a capability at all rather than a workflow (it owns a lifecycle) or a reference (it is applied rather than executed); whether the file would restate a surface that already documents itself, such as a CLI's own help output.
- Where the capability's executable core is a CLI, NO body is drafted: the return reads `self-check: fail` with the reason that the piece routes to the `create-cli` capability, and the dispatching seat builds it through that capability instead.
- Otherwise a file exists at the assigned filename inside the assigned probe folder, carrying the procedure as its BODY — entry point, ordered steps, failure modes, written for a consumer holding zero context — and the i/o spec as its FRONTMATTER: inputs, outcome, outputs, declared in place.
- The draft names its form and the reason: `<name>.md` at the component root where that component holds ONE capability carrying no tool and no sub-structure, `capabilities/<name>/<name>.md` where it holds more than one or where the capability carries a tool.
- The return names the registration and exposure act the piece row's exposure decision orders, which the dispatching seat performs in the same act that lands the file — a capability is never left goal-local.
- Nothing in the body names a consuming workflow's purpose, restates tool help or record content, or carries a done contract; no owner-specific value appears.
- The return `{piece-id, kind, probe-path, self-check: pass|fail, evidence}` reached the dispatcher, its evidence naming, per rung and per rule, what satisfies it.

Outcome map:

- **self-check pass** → the dispatching seat re-reads the file, lands it at the piece row's target path, and registers and exposes it in that same act.
- **self-check fail, reason "routes to create-cli"** → the dispatching seat builds the tool through the `create-cli` capability and writes its first-party inventory row. Feedback schema: {piece-id, the tool's jobs, the machine-readable output it must emit}.
- **self-check fail, reason "the scaffolding already has it"** → the piece is dropped and the existing capability named. Feedback schema: {piece-id, the existing capability's path, what the request wanted that it already serves}.
- **self-check fail, reason "not a capability"** → the piece is reclassified. Feedback schema: {piece-id, the kind it actually is, the evidence — the lifecycle it owns, or the fact that it is applied rather than executed}.
</done-contract>

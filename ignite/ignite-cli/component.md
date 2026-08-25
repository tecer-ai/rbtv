---
description: Read before adding a verb, a flag or a router skill to the rbtv ignite front door - what the CLI owns, what it only routes to, and where its client seam ends.
---

# ignite-cli

The `rbtv ignite` front door. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 and §7 under
[D22], [T4-R11], [C-15]. Named `ignite-cli` by owner ruling at CP1; it is the same
tree that used to sit at `ignite/ignite-cli/`.

Audience: **dual** - an owner console and an agent both invoke it (§7.1).

## What it owns

| Part | File | What it is |
|---|---|---|
| entry | `ignite.js` | Argument parsing and verb dispatch |
| verbs | `commands/` | `inspect`, `status`, `kill`, `snooze`, and the job register/deregister/add/remove pair set |
| client seam | `lib/` | Gateway client, config and token resolution, output rendering, typed usage errors |

It owns the FUNCTION-bundle router skills of §7 (`daemon-ops`, `goal-ops`,
`observe`, `staffing`, `coord-ops`) - those land with impl-cli-skills, not here.
It does NOT own the tools those skills route to: each stays a `method=path` row on
its own component (`operator/`, `runtime/`, `observation/`, `coord/`).

## What it does not do

No behavior of its own beyond argument handling and rendering: every verb reaches
the daemon through `runtime/internal-api/` over the gateway. A verb that needs new
behavior grows it in the owning component, never here.

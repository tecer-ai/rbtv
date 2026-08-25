---
description: Read before adding a verb, a flag or a router skill to the rbtv ignite front door - what the CLI owns, what it only routes to, and where its client seam ends.
---

# ignite-cli

The `rbtv ignite` front door. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 and §7 under
[D22], [T4-R11], [C-15]. Named `ignite-cli` by owner ruling at CP1; it is the same
tree that used to sit at `ignite/cli/`.

Audience: **dual** - an owner console and an agent both invoke it (§7.1).

## What it owns

| Part | File | What it is |
|---|---|---|
| entry | `ignite.js` | Argument parsing and verb dispatch |
| verbs | `commands/` | `inspect`, `status`, `kill`, `snooze`, and the job register/deregister/add/remove pair set |
| client seam | `lib/` | Gateway client, config and token resolution, output rendering, typed usage errors |
| audience map | `cli-audience-map.md` | The §7.1 transcription: every shell-invocable rbtv entry point, its owning component and its pinned audience |
| router skills | `daemon-ops.md`, `goal-ops.md`, `observe.md`, `staffing.md`, `coord-ops.md` | The five §7.2 FUNCTION bundles: one decision table each, routing to tools that live in other components. Each carries a `method=skill` row on this component's `exposure.csv`, from which the installer emits the thin `SKILL.md` loader |
| role table | `cli-role-bundles.md` | The §7.4 transcription: which roles load which bundles, and the caged-worker caveat |

It owns the FUNCTION-bundle router skills of §7.2 (`daemon-ops`, `goal-ops`,
`observe`, `staffing`, `coord-ops`) and the §7.4 per-role table beside them - the
front door owns routing. It does NOT own the tools those skills route to: each stays
a `method=path` row on its own component (`operator/`, `runtime/`, `observation/`,
`coord/`, `deploy/`, `planning/`, `teambuild/`). A router file never restates a
tool's `-h`; it only decides WHICH tool.

## What it does not do

No behavior of its own beyond argument handling and rendering: every verb reaches
the daemon through `runtime/internal-api/` over the gateway. A verb that needs new
behavior grows it in the owning component, never here.

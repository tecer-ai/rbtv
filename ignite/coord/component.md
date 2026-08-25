---
description: Read before touching the coordination kit — the `coordinate` CLI and its split modules, addressing, declared outputs, tmux viewports, messages, the checkout write API, and the kit's shipped skills, mirror driver and starter set.
---

# coord

The **coordination kit**: the team mechanics a seat, a leader and the daemon all reach
through one CLI. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 under [D22], [T4-R11],
[C-15]; this component is the map's `coordination kit` row.

It answers *who is addressed*, *what a seat declared it would produce*, *what was said on
the bus*, and *what a seat wrote when it checked out*. It does not answer whether a sitting
is alive (`supervisor/`), what an ending means (`state-store/`), what an alarm says
(`observation/`), or what a cage admits (`envelope/`).

## Entry points, and which doc answers what

| Read this | For |
|---|---|
| `CLAUDE.md` | The hard rules binding any agent editing this folder — the save gate, the no-run-state rule, the designer-only marker on `system-design.md` |
| `team-kit.md` | The kit index: what the toolkit is and how a run uses it |
| `protocol.md`, `communication.md`, `roles.md` | The run-time protocol, the addressing table and the seat roles |
| `system-design.md` | Design rationale — **designers only**, never a run seat's pre-read |
| `coord.py -h` | The command surface itself; a second copy in prose drifted and was deleted |

## What lives here

| Part | File | What it is |
|---|---|---|
| the CLI entry | `coord.py` | The `coordinate` front door and the thin re-export shim: constants, the shared namespace, and the `SPLIT_MODULES` load |
| split modules | `addressing.py`, `outputs.py`, `tmux.py`, `records.py`, `identity.py`, `checkout.py`, `messages.py`, `closeout.py`, `cli_main.py` | Bodies moved verbatim out of `coord.py` by the move-only split [D23, T4-R12]; one shared runtime namespace, never separate imports |
| kit doors onto other components | `ending_store.py`, `supervisor_door.py`, `liveness.py`, `gateway_client.py` | Thin Python doors onto `state-store/`, `supervisor/` and the gateway — no second implementation of either |
| shipped tools | `file-issue.py`, `floor-lint.py`, `owed-answers.py`, `worktree-flow.py`, `save-coord.py`, `budget.py`, `overview-compact.py`, `provider-usage.py`, `statusline-usage.py`, `tmux-overview` | The kit's first-party CLIs; each is an `exposure.csv` `method=path` row |
| injection ladder | `injection-ladder/` | The ONE per-harness injection ladder (CMP-9) the spawn path resolves a rung through |
| skills | `skills/` | The kit's shipped skill loaders (`team-kit`, `file-system-issue`) |
| mirror driver | `mirror/` | The scaffolding-repo mirror driver and its tests |
| starter set | `starter-set/` | The goal-generic files a scaffold byte-copies into a new package |
| selftest | `coord_selftest.py` | The kit's own suite — test module, excluded from the product-source budget |

## Where its parts came from

The former `ignite/team-kit/` whole, plus `ignite/injection-ladder/` and `ignite/skills/` — moved
with history per `spec-component-map` §2. Two files left the kit in the same move:
`cagespec.py` to `envelope/` and the intact `materialize-seats.py` to `planning/`.

⚠ The six §3 modules whose named landing is `supervisor/` (`process`, `lifecycle_exec`,
`ready`, `launch`, `attest`, `carrier`) are still here. `coord.py` **execs its
`SPLIT_MODULES` siblings out of its own directory** into one shared namespace, and two
probes derive their file list the same flat way, so moving those six would require
redesigning the loader rather than re-pointing a caller. That is a spec-vs-disk conflict
recorded for a ruling, not a silent decision — see the seat report for
`impl-structure-moves-py`.

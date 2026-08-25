# 20260825-c-the-claude-md-monolith-becomes — the CLAUDE.md monolith becomes two link-only entry docs

kind: change
component: work-on-ignite
date: 2026-08-25
commit: c209cfcc,ae1d2c26
deployed: no
pin: NONE
components: deploy,state-store,envelope,coord,supervisor,chat,operator,runtime,ignite-cli,planning

## Motivation
`ignite/CLAUDE.md` was a 383-line doc monolith: it summarised every subsystem's contract in one
file that Claude Code auto-injects, so the file both duplicated the per-component contract docs
and went stale the moment the tree moved. [D23] forbids the monolith; [T4-R14] makes a stale home
in a doc a defect of the change that made it stale; `spec-component-map` §5 names the replacement
shape. After three component-first move seats nothing under `ignite/` had been swept, so hundreds
of prose cites still named `server/ engine/ capabilities/ bridges/ team-kit/ cli/ config/
gateway/ jobs/ lib/ launch-profiles/ injection-ladder/ skills/`.

## Design
Two audience-split entry points, LINKS ONLY per §5: `ignite/working-on-ignite.md` for an agent or
human editing ignite source, `ignite/working-in-a-goal.md` for a seat working inside a goal. Each
names the other. Neither restates a component body — every row points at the `component.md` that
owns the answer, which is what keeps them from becoming the next monolith.

`ignite/CLAUDE.md` becomes a 12-line stub rather than being deleted. Deletion was rejected: the
harness auto-injects `CLAUDE.md` into every agent editing under this tree, and that injection is
the only mechanism that puts the build-memory tripwire in front of an agent who never opens
`module.md`. `module.md` links both docs as well, so discovery works from either door.

The bodies that had no component home were absorbed one-body-one-home rather than copied into the
two docs: the deploy model and installation model and the probe-suite discipline into
`deploy/component.md`; the two state roots and the whole module Terminology into
`state-store/component.md`; the fence allow-list and secrets into `envelope/component.md`; ledger
custody into `coord/component.md`; "the goal watcher is reconcile.js, not a job" into
`supervisor/component.md`. The sections whose bodies already lived in a contract doc
(`operator/*/*.md`, `observation/daemon-watchdog/`, `supervisor/launch-profiles/README.md`,
`runtime/jobs/README.md`, `coord/component.md`) were dropped, not re-homed — the monolith was a
second copy of them.

## How it works
The sweep was mechanical, not by eye. A script extracts every backticked path-shaped token from
every `.md`/`.csv` under `ignite/` (excluding `node_modules/`, `probes/` and the memory store),
keeps only tokens that resolve NOWHERE against the file's own directory, the repo root or
`ignite/`, maps them through the §2 old→new prefix table, and rewrites ONLY when the mapped path
does resolve. A name that is history — a deleted capability, a deleted script — resolves neither
way and is therefore left standing as history rather than given an invented home. 158 rewrites
across 28 files. Bare `server/` was excluded from the map and the six prose claims that used it
("requires nothing under `server/`") were rephrased by hand to "the daemon tree (`runtime/`)",
because that tree is now three components and a blind prefix swap would have narrowed the claim.

The 14 cites of `ignite/CLAUDE.md` itself were repointed to the component that now carries the
body (`ignite/state-store/component.md` § State layout / § Terminology,
`ignite/deploy/component.md` § Installation model / § Probes) or, for the relocatable-subtree rule,
to the repo-root `CLAUDE.md` § "ignite/ — Runnable Service Code", which is where that rule always
actually lived.

## Consequences
`ignite/CLAUDE.md` no longer carries the fence, ledger custody, the capability roster, the
launch-spec resolver note, the probe discipline, the deploy and install models, the state layout or
the terminology — a reader who used to grep that one file now goes through
`working-on-ignite.md`. Five `component.md` files grew (deploy 30→135, state-store 32→135,
envelope 64→101, coord 54→63, supervisor 583→602); all stay far under the §3 2000-line budget.
Six source files took comment-only cite edits (`chat/gateway-forwarder.js`,
`chat/probes/probe-chat-boundary.js`, `ignite-cli/lib/config.js`,
`supervisor/spawn/live-sessions.js`, `supervisor/launch-profiles/profiles.js`,
`operator/goals-tree/tool/goal_cli.py`) — no symbol and no behaviour changed.

## Verification
T4-R14 check: `rg -n` per moved old home (all 13 old top-level names plus `meta/teambuild`, in both
`ignite/<home>/` and backticked bare-`<home>/` form) over `working-on-ignite.md`,
`working-in-a-goal.md`, `module.md` and every README — zero stale homes; the single surviving
`capabilities/` string is the explicitly-marked deleted `goal-launch-delay`, which has no home to
resolve to. Every markdown link in the three new/stubbed files resolves (18 + 14 + 3 targets, all
`test -e` OK). `node --check` green on the five edited JS files, `py_compile` green on
`goal_cli.py`. `python -B ignite/coord/floor-lint.py --repo <worktree>` exit 0, VIOLATIONS none.
Repo-wide probe suite run in 10 chunks by `--dir`: 205 discovered / 205 attempted / 188 passed /
14 failed / 3 inoperative, `SUITE-COMPLETE` on every chunk. Not deployed: this is the
`ignite/core-redesign` worktree and the cutover seat owns the restart.

## ATTENTION
1. `ignite/CLAUDE.md` is deliberately a stub, not deleted — the harness auto-injects it, and that
   injection is what puts the build-memory gate in front of an agent who never opens `module.md`.
   Deleting it silently removes the only always-on tripwire on this tree.
2. Do not put a component body back into either entry-point doc. They are links-only by
   `spec-component-map` §5; the moment one restates a contract it becomes the monolith that was
   just dismantled, and it will go stale exactly the way the old file did.
3. A prose path cite is only stale if the OLD path resolves nowhere AND a mapped NEW one resolves.
   Rewriting a name that resolves neither way (a deleted script, a retired capability) invents a
   home for something that does not exist — leave it as history and mark it deleted.
4. The module's Terminology now lives in `state-store/component.md`, not at the module root. A spec
   or commit reaching for the canonical word for a `jobs_log.status` value, a `session_mode`, or a
   core noun looks there; there is no second copy, and a second copy is how D23 was violated before.
- ignite/CLAUDE.md is a stub on purpose: the harness auto-injects it and that is the only always-on build-memory tripwire on this tree

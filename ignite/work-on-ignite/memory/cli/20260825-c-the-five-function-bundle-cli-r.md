# 20260825-c-the-five-function-bundle-cli-r — the five function-bundle CLI routers land in the front door

kind: creation
component: cli
date: 2026-08-25
commit: 8679b7b5,22bd9753,d7951fd8,7f987a2e
deployed: no
pin: NONE
components: coord,deploy,operator,planning

## Motivation
Agents discovered ignite's CLIs one skill per CLI, or not at all: 44 shell-invocable entry
points, no function-level index, and no statement of which role should load which. Owner
rulings A-a / B-a settled the shape — routers bundled BY FUNCTION, plus a per-role pointer
table — and `spec-component-map.md` §7.2 / §7.4 pinned the five bundles and the six role
rows. This entry records landing them.

## Design
Five browse-pattern router capability files in `ignite/ignite-cli/` (`daemon-ops.md`,
`goal-ops.md`, `observe.md`, `staffing.md`, `coord-ops.md`), each carrying frontmatter
`id`/`description`/`inputs`/`outcome`/`outputs` and a cheapest-rung-first decision table,
plus `cli-role-bundles.md` for the §7.4 role→bundle assignment. The front door owns
routing because §7.2 says so; the tools themselves stay `method=path` rows on their own
components (`operator/`, `runtime/`, `observation/`, `coord/`, `deploy/`, `planning/`,
`teambuild/`). Rejected on the way: a wrapper CLI per bundle (it would duplicate each
tool's `-h`, which is the thing the `browse` component built and deleted the same day), and
audience-shaped bundles (rulings A-a/B-a chose FUNCTION, and a bundle may legitimately
route to a tool a given role is not granted).

## How it works
Each router file is a source capability, never a loader: the installer emits the thin
`SKILL.md` from a `method=skill` row on `ignite/ignite-cli/exposure.csv`, shape
`part-id,capability,skill,exhibit,<file>.md,"<description>",`. An agent invoking the skill
reads the router file at its absolute path and follows its decision table to a tool it then
runs by PATH name — the PATH name being the part-id of the tool's own `method=path` row,
never the entry-point basename. Every bundle also carries an explicit "deliberately not in
this bundle" table transcribing §7.2's exclusion column, so a reader learns why the
internal-daemon and owner-gate tools are absent rather than assuming an oversight.

## Consequences
Nothing was replaced or deleted: this is additive. `ignite-cli/component.md` stopped
forward-declaring the routers as future work and now claims them, and its stale
self-reference to the pre-CP1 path was corrected in the same commit set.
`ignite/working-in-a-goal.md` gained a need-to-file routing table, without which a seat
never reaches the routers at all. No wrapper script and no `package.json` were added — no
bundle needs an external binary today.

## Verification
`meta/installer/install.py add -c ignite-cli --dry-run --json --target <disposable>` exits 0
and plans exactly five `SKILL.md` loaders (`coord-ops`, `daemon-ops`, `goal-ops`, `observe`,
`staffing`), writing nothing under the workspace. `component_lint.py --component
ignite/ignite-cli --check exposure-canon` reports zero findings against the five new rows —
its three remaining findings sit on the two pre-existing `method=path` rows and pre-date
this change. Not deployed: worktree-only, on branch `ignite/core-redesign`.

## ATTENTION
- A router file is DISCOVERY, not a grant: a caged worker still runs only what its seat's exposed-clis: block names, so adding coord-ops to a prompt grants nothing on its own.
- The PATH name of a routed tool is the part-id of its exposure row, NOT the entry-point basename - coordinate is coord.py, probe-suite is probe-suite.js. Routing by basename produces a command that does not exist.
- Never hand-write SKILL.md for these: install.py emits the loader from the method=skill row, and a hand-written one is overwritten on every install run.

# 20260824-c-rename-the-planning-workflow-t — rename the planning workflow to plan-console

kind: change
component: meta-planning
date: 2026-08-24
commit: 86c9667c,a2607f9b
deployed: no
pin: NONE
components: engine,capabilities,config,team-kit,server

## Motivation

The name `planning` was overloaded three ways at once: the meta COMPONENT `meta/planning`, the goal
folder subtree `planning/` every plan pass writes into, and the WORKFLOW whose manifest sat at
`meta/planning/workflows/planning/planning.csv`. A reader grepping `planning` could not tell which
of the three a hit belonged to, and the daemon's own planning door named the workflow by the bare
string `planning` in three places. Owner-directed 2026-08-24, after the five-seat one-pass pipeline
(`67f93286`), the D13 replan mini-pipeline (`32ad68a8`) and the rolling-planning retirement
(`6318207d`) had finished rewriting the workflow — renaming earlier would have been redone.

## Design

The WORKFLOW alone is renamed to `plan-console`. The component keeps its name, because the component
is not the workflow; the goal-folder `planning/` subtree keeps its name, because it is an output
path, not an identity; and the workflow CODE stays `plan`, because `references/seat-id-naming.md`
rules the code DERIVED from the manifest's shared seat-id prefix and explicitly independent of the
workflow's name — so every `plan-*` seat-id and the casting sheet `bindings/plan.json` are untouched.
A `git mv` carries the folder and the manifest together, because `materialize-seats.py --workflow W`
resolves exactly `<component>/workflows/<W>/<W>.csv` — folder and file name are one identity.
Alternative rejected: a compatibility alias accepting both names, which would have kept the ambiguity
this rename exists to kill.

## How it works

`meta/planning/workflows/planning/` became `workflows/plan-console/` and `planning.csv` became
`plan-console.csv`. Route surfaces repointed: `references/build.md`'s route-rule row, `component.md`'s
entry points, `references/seat-id-naming.md`'s precedent sentence, forge's and d13-replan's
cross-workflow mentions, and `seats.csv`'s `forg-intake` escalation description. `exposure.csv` named
the workflow nowhere and is unchanged.

On the ignite side the identity is a string in four live places, all repointed: the
`goal-creation-request` argv value in `config/spawn-profiles.yaml` (`--workflow plan-console`),
`planning/argv.py` `PLANNING_WORKFLOW`, `engine/queue-request.js` `PLANNING_WORKFLOW`, and the probe
suites that name the real workflow (`capabilities/bindings/probes/probe-bindings.py`'s
`LIVE_MANIFEST` and its materialize argv, `goal-creation-request`'s two probes,
`server/ticker/probes/probe-argv-template.js`, `server/heart/probes/probe-workdir-governance.js`).
`goal_cli.py` `cmd_scaffold` needed no edit: it derives no workflow and names none — its own comment
at the `scaffold` verb says the verb derives nothing, and the workflow comes from the request layer.

Two stale comments were CLARIFIED rather than repointed, because their `workflows/planning/` paths
belong to the DELETED `planning-deprecated` component (pre-rename `planner-workflow`), not to the
live one: `meta/module.md`'s tombstone row and `team-kit/materialize-seats.py`'s Q8 second-carrier
note.

## Consequences

`--workflow planning` is now a hard `workflow-unknown` refusal against the catalog; nothing accepts
the old name. The rename is confined to the worktree branch `ignite/core-redesign` — the live repo
and the running daemon still fire `--workflow planning`, and CUTOVER is what carries this across.
Until cutover, a live daemon reading a repointed spawn-profiles.yaml would refuse every
master-created goal at `create-package`; the two must move together.

## Verification

`git log --follow` on `workflows/plan-console/plan-console.csv` reaches `67f93286` and `49c03d35`, so
history survived the move. `rbtv-goal check-acyclic` on the renamed manifest with `--id-col
Seat/workflow` reports clean, five rows, four edges — byte-identical to the pre-rename run.
A discriminating materialize pair against the worktree catalog: `--workflow planning` refused
`workflow-unknown` where before the rename it reached `exposes-ref-dangling`, and `--workflow
plan-console` now reaches `exposes-ref-dangling` where before it refused `workflow-unknown` — the
two refusals swapped, which is exactly manifest resolution following the rename.
`exposes-ref-dangling` is the pre-existing worktree wall: the component catalog scan is pinned to
the live repo and mirror roots, so no worktree materialize can go further.
Green after the change: all four `ignite/planning/probes/*.py`, `engine/probes/probe-queue-request-pass.js`
(the Path A door), `server/heart/probes/probe-workdir-governance.js`, and
`server/ticker/probes/probe-argv-template.js` — whose check S3c byte-compares the LIVE
spawn-profiles argv and now shows `--workflow plan-console`. `python3 -m py_compile` and `node --check`
clean on every edited file; `yaml.safe_load` clean on spawn-profiles.yaml. Not deployed: a
pre-cutover tree edit on `ignite/core-redesign`.

## ATTENTION

- The workflow CODE stays `plan` and every seat-id stays `plan-*`. A future reader seeing workflow
  `plan-console` with seats `plan-*` may assume a mismatch and "fix" it — `seat-id-naming.md` rules
  the code independent of the workflow name, and the bindings capability's `workflow_code()` refuses
  any prefix that is not exactly four letters, so `plan-console-*` would be rejected on deploy.
- Folder name and manifest file name are ONE identity: `--workflow W` resolves
  `<component>/workflows/<W>/<W>.csv`. Renaming one without the other yields a silent
  `workflow-unknown` at the door, not a load error.
- The live repo and the running daemon still name `planning`. This branch and the live side disagree
  until cutover, and a partial deploy of spawn-profiles.yaml alone breaks every master-created goal.
- `capabilities/bindings/probes/probe-bindings.py` was already stale before this rename: it asserts
  on the seat-id `plan-binder`, which the manifest lost at `67f93286`. Its path was repointed here;
  its staleness was not touched and it will still read RED for that reason.
- `config/spawn-profiles.yaml` and `capabilities/goal-creation-request/goal-creation-request.md` both
  still say the workflow has "16 manifest seats". It has five since `67f93286`. The path beside that
  count was repointed; the count was left, and it is wrong.
- workflow code stays plan and seat-ids stay plan-*; the code is independent of the workflow name
- folder name and manifest file name are one identity: --workflow W resolves <component>/workflows/<W>/<W>.csv
- live repo and daemon still name planning; cutover carries this, and a partial spawn-profiles deploy breaks goal creation

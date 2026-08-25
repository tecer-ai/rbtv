---
description: Read when deciding who a CLI is for — the pinned audience label of every shell-invocable rbtv entry point, and the component that owns it.
---

# CLI audience map

Every shell-invocable rbtv entry point, with the audience it is pinned to. A CLI is a
shell-invocable entry point, not a library: library rows on a component's
`exposure.csv` are inventory, not commands, and are out of this table.

Law: `1-projects/build-ignite/redesign/specs/spec-component-map.md` **§7.1**, which pins
the audience of every ignite and teambuild row and rules that rows outside those two
modules keep the audience the census gave them. The census is the plan folder's
`authoring/cli-landscape/q1-inventory.md` (44 rows, read-only evidence). This file is the
transcription of §7.1 onto the component-first tree — it invents no label and moves no
tool. Paths below are re-located by content after the component-first migration; the
census paths are pre-migration and have drifted.

## The four labels

| Label | Means |
|---|---|
| `agent-facing` | A seat invokes it. It may carry a router-skill row and a seat `exposes: path:` grant. |
| `owner-console` | A human at a console invokes it. Never granted to a caged seat by default. |
| `internal-daemon` | Only the daemon, a systemd timer or a harness hook invokes it. Never a router-skill target. |
| `dual` | Both a console and a seat already invoke it. Allowed only for a front door (§7.1). |

`gone` is not a label: it records a census row whose tool no longer exists on this branch.

## ignite

| Invocation | Path | Audience |
|---|---|---|
| `rbtv ignite <cmd>` / `ignite <cmd>` | `ignite/ignite-cli/ignite.js` | **dual** — front door |
| `rbtv run <goal>` | `ignite/operator/attached-execution/tool/rbtv-execution` | agent-facing |
| `rbtv ignite daemon <verb>` | `ignite/operator/daemon-operator/tool/rbtv-ignite-daemon` | owner-console |
| `rbtv ignite ticker <verb>` | `ignite/operator/ticker-settings/tool/rbtv-ignite-ticker` | owner-console |
| `rbtv goal <verb>` | `ignite/operator/goals-tree/tool/rbtv-goal` | agent-facing |
| `rbtv-goal-request` | `ignite/operator/goal-creation-request/tool/rbtv-goal-request` | agent-facing |
| `rbtv-bindings` | `ignite/operator/bindings/tool/rbtv-bindings` | agent-facing |
| `rbtv-master-profile` | `ignite/operator/master-profile/tool/rbtv-master-profile` | agent-facing |
| `rbtv-seat-identity` | `ignite/runtime/seat-identity/rbtv-seat-identity` | agent-facing |
| `rbtv-ignite-watchdog` | `ignite/observation/daemon-watchdog/tool/rbtv-ignite-watchdog` | internal-daemon |
| `coordinate` | `ignite/coord/coord.py` | agent-facing — the seat-facing half of the split front door (check in, check out, message, records, groups) |
| `supervise` | `ignite/supervisor/supervise.py` | **dual** — `owner-console` for a leader's remedial acts, `internal-daemon` for `lifecycle-exec` / `renewal-state` / `surface-refusal`, which no seat ever types. The other half of the `coordinate` entry point, split by AUDIENCE on owner ruling 2026-08-25 |
| `owed-answers` | `ignite/coord/owed-answers.py` | agent-facing |
| `materialize-seats` | `ignite/planning/materialize-seats.py` | agent-facing |
| `scaffold-seats` (alias of the row above) | `ignite/planning/materialize-seats.py` | agent-facing |
| `worktree-flow` | `ignite/coord/worktree-flow.py` | agent-facing |
| `file-issue` | `ignite/coord/file-issue.py` | agent-facing |
| `floor-lint` | `ignite/coord/floor-lint.py` | agent-facing — authoring lint; unlabeled in the census, resolved by §7.1 |
| `budget` | `ignite/coord/budget.py` | owner-console — capacity vs census; unlabeled in the census, resolved by §7.1 |
| `save-coord` | `ignite/coord/save-coord.py` | owner-console |
| `tmux-overview` | `ignite/coord/tmux-overview` | owner-console |
| `overview-compact` | `ignite/coord/overview-compact.py` | owner-console |
| `provider-usage` | `ignite/coord/provider-usage.py` | owner-console |
| `statusline-usage` | `ignite/coord/statusline-usage.py` | internal-daemon |
| `python3 …/nudge.py` | `ignite/coord/nudge.py` | internal-daemon — retired timer; no router skill |
| `python -m driver.cli` (worker mirror) | `ignite/coord/mirror/driver/cli.py` | owner-console |
| `python3 …/link-tools.py` | `ignite/deploy/link-tools.py` | owner-console |
| `node …/probe-suite.js` | `ignite/deploy/probe-suite.js` | owner-console |
| `python3 …/probe-suite-scheduled.py` (systemd timer) | `ignite/deploy/probe-suite-scheduled.py` | internal-daemon |
| `node …/goal-channel-cli.js` | `ignite/chat/goal-channel-cli.js` | **dual** — `ensure` is internal-daemon, `post`/`retire` owner-console; unlabeled in the census, resolved by §7.1 |
| `rbtv teambuild` | `ignite/teambuild/tool/rbtv-teambuild` | agent-facing |

## Gone — census rows with no tool on this branch

| Census invocation | Why | Consequence |
|---|---|---|
| `teamview` | ARCHIVE-MOVED out of the repo (§2 extra-module dispositions) | no audience, no skill, no PATH keep |
| `team-monitor` | deleted with the observer batch (D19 code-path archive) | no audience, no skill, no remap |
| `ctx-monitor` | deleted with the observer batch (D19 code-path archive) | no audience, no skill, no remap |

## Outside ignite and teambuild — census audience kept unchanged

§7.1: these rows keep the audience the census gave them; the CLI-consolidation work
neither moves nor re-skills them.

| Invocation | Path | Audience |
|---|---|---|
| `rbtv` | `meta/rbtv-cli/tool/rbtv` | agent-facing |
| `rbtv install <verb>` | `meta/installer/install.py` | owner-console |
| `rbtv embed-search` | `meta/embed-search/tool/rbtv-embed-search` | agent-facing |
| `capability-cards` | `meta/planning/capabilities/capability-cards/tool/capability_cards.py` | agent-facing |
| `component-lint` | `meta/planning/capabilities/component-lint/tool/component_lint.py` | agent-facing |
| `delta-anchors` | `meta/planning/capabilities/delta-anchors/tool/delta_anchors.py` | agent-facing |
| `cast` | `core/sub-agents/tool/cast.js` | agent-facing |
| `rbtv-commit` | `core/coding/tool/commit.py` | agent-facing |
| `acct` | `core/providers/capabilities/acct/tool/acct.py` | agent-facing |
| `audio` | `core/communication/capabilities/audio/audio.py` | agent-facing |
| `capture-cli` | `web/capture/capabilities/capture/capture.py` — the `web/` module is not on this branch | agent-facing |

## Reachability — why five of these were declared but unreachable

The census found `rbtv-bindings`, `rbtv-master-profile`, `rbtv-goal-request`,
`rbtv-seat-identity` and `rbtv-ignite-watchdog` declared `method=path` yet absent from
the shared bin dir, while the coordination kit's names were present. The cause was the
MANIFEST HOME, never the row: those five were declared on the module-root
`ignite/exposure.csv`, and installer discovery treats a directory at depth 2 holding an
`exposure.csv` as the component — so it never saw them. `coord/` and `work-on-ignite/`
already had their own depth-2 manifests, which is exactly why their names were linked.

The component-first move gave each of the five a depth-2 component home, so the
declaration is now what the installer walks and links. The fix is that link — never a
second copy of a binary anywhere on PATH, and never a hand-made symlink.

## What this table is not

Not a grant. A label says who a tool is FOR; what a seat may actually run is its
generated `seat.md` `exposed-clis:` block, and for a caged seat the sandbox built from
it. Not a router-skill list either: the function bundles and the per-role pointer table
are §7.2 and §7.4, and they live beside this file in this component.

# 20260824-c-plan-in-session-run-renamed-to — plan-in-session-run renamed to plan; skill re-minted

kind: change
component: meta-planning
date: 2026-08-24
commit: 98f47aac
deployed: no
pin: NONE

## Motivation
The owner ruled (2026-08-24) that the plan format for console-orchestrated seat plans is named `plan`, not `plan-in-session-run` — both the reference file and the skill that exposes it carry that name.

## Design
Rename in place, not a rewrite: `meta/planning/references/plan-in-session-run.md` → `references/plan.md` via `git mv`, the format's name replaced inside the body, and a standalone `plan` skill re-minted as an `exposure.csv` row (`plan,reference,skill,,references/plan.md,…`). Re-minting partially reverses the 2026-08-21 fold-into-`build` ruling for this one skill, at explicit owner direction; `build` keeps its route row, now pointing at the new name.

## How it works
The skill row installs a thin loader (`.claude/skills/plan/SKILL.md`, `.agents/skills/plan/SKILL.md`) that reads `meta/planning/references/plan.md` in place. Pointers updated inline: `references/build.md` (route rule §1, guide table §3), `component.md` (entry points). Installed via `rbtv install add -c planning -xs`.

## Consequences
The name `plan-in-session-run` no longer names a live file; historical records (build/_done trees, decisions logs) keep the old spelling and are not rewritten. `build.md` and `component.md` state the rename with its date so old references stay resolvable.

## Verification
`grep -rn plan-in-session-run meta/` returns only the two dated rename notes; `rbtv install add -c planning -xs` wrote `.claude/skills/plan/SKILL.md` whose loader path resolves; committed as `98f47aac` on `ignite/core-daemon`.

## ATTENTION
- Historical plan folders and decisions logs still say `plan-in-session-run` on purpose — do not "fix" them; the rename notes in build.md/component.md are the bridge.
- Historical records keep the old name deliberately

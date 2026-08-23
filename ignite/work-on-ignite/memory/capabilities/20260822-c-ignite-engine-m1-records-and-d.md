# 20260822-c-ignite-engine-m1-records-and-d — ignite-engine-m1-records-and-door

kind: creation
component: capabilities
date: 2026-08-22
commit: 2b00b593
deployed: yes
pin: server/spawn/probes/probe-register-door.js
components: server,team-kit,meta-leader
seeded: true

## What it is
`ignite-engine` m1 "records-and-door": the cage admits the register write root, and the filing CLI grew a status vocabulary, a validating doctor, and schema/history verbs.

Masters' issue-filing now routes through the filing CLI (`file-issue`) instead of ad hoc writes. m1 is the first milestone of the `ignite-engine` goal — the standing daemon-lane goal that is becoming the only door for changes to `ignite/` and `meta/` besides the owner at a terminal.

## Why
E20 (owner, 2026-08-22 18:26Z): m1 runs on the CONSOLE lane now — settles the register entry format, the status vocabulary, and the HISTORY entry shape, and proves the filing CLI writes from a real cage. Before this, `goalsTreeRefusal` was a blanket rule-3 refusal that admitted no register writes at all from a caged seat; this milestone replaces the blanket rule with a walled-set that specifically admits the register write root. m1 is DONE, judged PASS, committed, and deployed (per `engine-goal.md` §1 / `status.md` 2026-08-22 23:52Z).

## How to use & where wired
`ignite/capabilities/goals-tree/tool/goal_cli.py` (register write-root admission), `ignite/server/spawn/probes/probe-register-door.js` (new, 230 lines — the pin), `ignite/server/spawn/seat-grants.js` (write-root grant logic), `ignite/server/spawn/spawn.js`, `ignite/team-kit/file-issue.py` (status vocabulary + validating doctor + schema/history verbs, +533 lines), `ignite/team-kit/skills/file-system-issue/SKILL.md`, `meta/leader/prompts/leader.md`, `meta/master-agent/prompts/goal-master-prompt.md`, `meta/master-agent/prompts/channel-master-prompt.md` (masters' filing routed to the filing CLI, router routing line added). Commit `2b00b593` ("ignite-engine m1 records-and-door").

## commit
2b00b593

## deployed
yes

## pin
server/spawn/probes/probe-register-door.js

## ATTENTION
- This milestone is what the `file-issue-cli-skill` creation (team-kit, D78, 2026-08-22) later grew a `memory` subcommand on top of — the `file-issue.py` this touched is the SAME binary this seat is using right now to file this very entry. Any change to its status vocabulary or schema verbs risks breaking the `memory file`/`memory check` subcommands added afterward.
- The `goalsTreeRefusal` walled-set replaces a blanket refusal — if the walled-set is ever widened carelessly, it re-opens the write surface the blanket rule was protecting.
- The ignite-engine goal was later PAUSED (E23, 2026-08-23 01:58Z) pending this very memory program's completion and a rewire — m2–m4 (intake, seed, triage-contract) had NOT started as of that pause; do not assume this milestone's successors have landed.
- Same file-issue.py binary the memory subcommand (file-issue-cli-skill) grew on top of afterward; check schema/vocabulary changes don't break memory file/check
- goalsTreeRefusal walled-set replaces a blanket rule; widening it carelessly re-opens the write surface
- ignite-engine was PAUSED (E23, 2026-08-23) before m2-m4; do not assume successors have landed

# 20260822-c-file-issue-cli-skill — file-issue-cli-skill

kind: creation
component: team-kit
date: 2026-08-22
commit: 2524e4c9
deployed: yes
pin: NONE
components: meta-leader
seeded: true

## What it is
D78: any goal-master or leader may file a system issue (consultants may not).

A new skill + CLI (`file-issue.py`) that registers a system issue in the engine goal's register — "file, don't fix" restricts what a master DOES, not who may file.

## Why
D78 (`redesign-plan/decisions.md`): the engine goal (`ignite-engine`) then polls/reads its own register — no new message type is needed. This is the proto issue-tracker design described in `handoff-engine-goal-2026-08-22.md`, the culminating handoff of the redesign-plan seed material (seed-digests/engine-goal.md §3).

## How to use & where wired
`ignite/team-kit/file-issue.py` (670-line new CLI), `ignite/team-kit/exposure.csv` (2 new rows exposing the CLI), `ignite/team-kit/skills/file-system-issue/SKILL.md` (44-line skill, read-before/file-after procedure). Wired into `meta/leader/prompts/leader.md` and `meta/master-agent/prompts/goal-master-prompt.md` (each +5 lines pointing seats at the skill). Commit `2524e4c9` ("D78 file-issue CLI + skill for goal-master and leader").

## commit
2524e4c9

## deployed
yes

## pin
NONE

## ATTENTION
- This CLI is the SAME `file-issue` binary this seat used to file this very memory entry — `file-issue memory file` and `file-issue file` (the open-register side) are two verbs on one tool; do not confuse the OPEN-side register this creation built with the CLOSED-side memory the `memory` subcommand later grew (m1 of `ignite-engine`, see `ignite-engine-m1-records-and-door` under capabilities).
- A later gap was found and filed against this same CLI: `history append` (built in m1) had no declared cli-write-root, so no caged seat could execute it (engine-goal.md §3, issues.md 2026-08-22) — check current write-root grants before relying on any write verb here.
- This is the same file-issue binary that later grew the memory subcommand (see ignite-engine-m1-records-and-door)
- history append (m1) had no declared cli-write-root; check write-root grants before relying on write verbs

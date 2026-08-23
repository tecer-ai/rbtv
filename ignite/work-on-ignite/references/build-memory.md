---
description: Read for the full mechanics of the ignite build memory — layout, kinds, entry/index shape, and distillation.
tags: [ignite, memory]
---

# work-on-ignite — how ignite build memory works

## Purpose

Ten days of agents fixing ignite patch-by-patch kept surfacing new defects. The loop turned around only when agents read git history, then a file derived from that history (`system-problems/fixinv/fix-inventory.csv`: ruling → commit → files → pinning probe), then seeded each batch's history into the next. That was brute force; this memory makes it structural and still usable at the current commit rate in 30 days.

What broke the patch loop was amnesia: prose-only rules, KEEP lists that forbade reversing a fix, and no closed record of what was seen, which trials missed, and what held, cited against the deployed tree. The four seed digests are the evidence: `/home/henri/ht-wkdir/second-brain/1-projects/build-ignite/build/build-memory/seed-digests/engine-goal.md`, `/home/henri/ht-wkdir/second-brain/1-projects/build-ignite/build/build-memory/seed-digests/redesign-plan-and-precedents.md`, `/home/henri/ht-wkdir/second-brain/1-projects/build-ignite/build/build-memory/seed-digests/redesign-plan-seed.md`, `/home/henri/ht-wkdir/second-brain/1-projects/build-ignite/build/build-memory/seed-digests/system-problems.md`.

## Layout

Everything lives under `ignite/work-on-ignite/` and travels with the rbtv repo:

```
ignite/work-on-ignite/
  component.md               ← orientation entry point
  CLAUDE.md                  ← 3-line pointer
  AGENTS.md                  ← same 3 lines
  references/
    work-on-ignite.md        ← the skill (read before, file after)
    build-memory.md          ← this file (the ONE reference)
  memory/
    _templates/issue.md
    _templates/creation.md
    <component>/
      _issues.md             ← live issue index (newest last)
      _creations.md          ← live creation/change index (newest last)
      _summary.md            ← distilled; empty until first rotation
      _issues-archive.md     ← rotated index lines (issues and creations)
      yyyymmdd-i-<name>.md   ← one issue entry
      yyyymmdd-c-<name>.md   ← one creation or change entry
```

The 19 components are the 15 top-level folders under `ignite/` except `node_modules` (`bridges`, `capabilities`, `cli`, `config`, `deploy`, `engine`, `gateway`, `injection-ladder`, `jobs`, `launch-profiles`, `lib`, `server`, `skills`, `team-kit`, `work-on-ignite`) plus the four `meta/` trees named `meta-installer`, `meta-leader`, `meta-master-agent`, `meta-planning`.

Rule: component = top-level folder. A cross-component entry is filed once, under the component where the fix landed; the other components it touched are named on its index line.

## Kinds

Two kinds only.

- **issue** — one loose end or bug. Filed only when fixed. A fix is always filed.
- **creation** — something new added. Refactors, removals, and renames are creations with `kind=change`.

Missed trials live inside the eventual issue entry (`## Missed`). Open items stay in the goal's `issues.md` / `loose-ends.md`. They never enter memory.

## Entry files

Naming: `yyyymmdd-i-<name≤30 kebab>.md` for issues, `yyyymmdd-c-<name≤30 kebab>.md` for creations and changes. Same-day same-name clash → `-2` suffix (`20260823-i-cage-grant-2.md`).

The filing command writes one title line `# <stem> — <title>`, then the body sections below (it copies `memory/_templates/issue.md` / `memory/_templates/creation.md`).

Issue body (mandatory):

- **Seen** — what was observed
- **Missed** — trials that failed, and why
- **Held** — the solution that stuck
- **commit** — hash that landed the fix
- **files** — `path:lines` against the DEPLOYED tree where it differs from HEAD
- **deployed** — `yes` | `no` | `at` (the deploy that carries it)
- **pin** — probe path, or `NONE` (allowed, must be visible)
- **ATTENTION** — bullets that say what to watch for and why

Creation body (mandatory; also used for `kind=change`):

- **What it is**
- **Why** — motivation / decision served
- **How to use & where wired**
- **commit** · **deployed** · **pin** · **ATTENTION** — same meaning as the issue body

ATTENTION bullets name what to watch for and why. The banned wording that forbids reversing a fix is never used.

## Index lines

What agents actually read. Field order, separated by ` · `:

`date · kind · title · symptom→cause · commit · other-components · ⚠`

- `date` — `YYYY-MM-DD` (the fix/creation date; backdated when `--date` is passed)
- `kind` — `issue` | `creation` | `change`
- `title` — short name
- `symptom→cause` — one clause
- `commit` — hash, or `pending` until committed
- `other-components` — space-separated component names, or `—` if none
- `⚠` — present iff the entry has ATTENTION bullets
- `seeded` — extra token after `kind` on backfilled entries only: `date · kind · seeded · title · …`

Target 280 characters, hard cap 400, enforced by the filing command. One entry = one line. Newest LAST (append-only). Never rewrite a prior index line.

## Per-component files

| file | holds | who writes |
|---|---|---|
| `_issues.md` | heading + live issue index lines | filing command only |
| `_creations.md` | heading + live creation/change index lines | filing command only |
| `_summary.md` | design intent, component map, standing ATTENTION, superseded fixes, pointers to archived ids | `goal-memory-management` distillation workflow |
| `_issues-archive.md` | index lines rotated off either live index | the same distillation workflow |

Never hand-edited. Each index file opens with one heading line naming the component and the grammar. Until the first distillation, `_summary.md` is exactly: `No distillation yet — read the live index.`

## Read step

Before editing component X (and every other component you will touch):

1. Read `memory/X/_summary.md` + `_issues.md` + `_creations.md` (and the same three files for every other component you will edit).
2. `rbtv embed-search query` over `ignite/work-on-ignite/memory/` for the symptom and for the files you will touch. Availability ladder: semantic → keyword → grep.
3. Grep of **all** `_issues.md` and `_creations.md` for the component names and the paths you will touch is the deterministic floor.
4. CITE the consulted entry ids (the entry filenames) in your proposal and in the commit message.

The `work-on-ignite` skill (`references/work-on-ignite.md`) is the when; this file is the what.

## Write step

After any fix or creation, before closing the sitting, file:

```
file-issue memory file \
  --component <name> \
  --kind issue|creation|change \
  --title "<title>" \
  --body-file <path> \
  --commit <hash> \
  --deployed yes|no|at \
  --pin <probe-path|NONE> \
  --components <other,other> \
  --attention "<bullet>" \
  --date YYYY-MM-DD \
  --seeded
```

`--date` backdates (seeding). `--seeded` marks a backfilled entry. `--components` lists the *other* components touched (not the home component). `--attention` may repeat. The command writes the entry file and appends one ≤400-char index line; it refuses a bad shape, a name over 30, a missing required field, and an unknown component.

Who writes: the ignite-engine goal at build/closure, **and** any ignite-editing session (owner at a terminal, console agents) at its close. The command guarantees shape; the `work-on-ignite` skill says when.

## Distillation

Count-triggered, not calendar-triggered. When a live `_issues.md` passes 60 lines, the `goal-memory-management` goal's workflow rewrites `_summary.md` (design intent, component map, standing ATTENTION, superseded fixes, pointers to archived ids) and moves all but the newest 30 lines to `_issues-archive.md`. `_creations.md` rotates the same way at 60, into the same `_issues-archive.md` (kind is already on the line). This memory is that goal's first.

## Vocabulary

Reuse; never coin a synonym for a thing that has a name.

- **memory** — box-② craft memory about building a component, versioned with the code at `ignite/work-on-ignite/memory/` (`sd-graph show memory`)
- **register / file / filing** — the `file-issue` register is the OPEN-defect side; memory is the CLOSED side
- **Seen / Missed / Held** — the three issue-body fields
- **decision-log** — the per-goal `decisions.md`; not this memory
- **dreamers** — the curating role the KG names; `goal-memory-management` realizes it for this memory

## What memory is not

Not a task list. Not the register. Not a place for open questions. If it is still open, it does not belong here.

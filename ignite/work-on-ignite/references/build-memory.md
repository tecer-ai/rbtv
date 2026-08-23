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

Missed trials live inside the eventual issue entry (`## Attempts`). Open items stay in the goal's `issues.md` / `loose-ends.md`. They never enter memory.

## Entry files

Naming: `yyyymmdd-i-<name≤30 kebab>.md` for issues, `yyyymmdd-c-<name≤30 kebab>.md` for creations and changes. Same-day same-name clash → `-2` suffix (`20260823-i-cage-grant-2.md`).

The filing command writes one title line `# <stem> — <title>` and the header block ONCE: `kind`, `component`, `date`, `commit`, `deployed`, `pin`, `components`, `seeded`. The body NEVER repeats commit, deployed, pin, or files as sections.

## Entry content contract

The body exists so a later agent building on rbtv knows what was already done, what mistakes were made, what was built, and the reasoning. Reader test: a stranger with no memory of the event can reconstruct the problem, the cause, what was tried, what was built and why, and what it broke.

Each heading below is a prose section with evidence (commits, dates, doc citations) INLINE. NEVER a list of files. Files and functions appear only as citations where the prose needs them. Length is whatever the substance needs — padding and restatement are defects. A body that could have been written from the index line alone is a defect.

### Issue headings (this order, all mandatory)

- `## Observed` — the symptom as it was measured: what, where (component/function), when, by whom/which goal; the deployed-vs-HEAD note when they differ.
- `## Mechanism` — the root cause: what the code actually did, and why that produced the symptom. NEVER the symptom restated.
- `## Attempts` — every earlier fix or trial of THIS problem: what it changed, when (commit), and WHY it did not hold. If nothing was tried before, write `First attempt held — checked: <the commits/docs you looked at>`. The literal phrase `none recorded` is FORBIDDEN.
- `## Fix` — what was built, and WHY this design rather than the alternatives (the ruling/decision it serves, the trade-off taken, what was rejected).
- `## Consequences` — what the fix changed elsewhere: what it deleted or replaced, regressions or new bugs it introduced, follow-up fixes it required (cite the later commits/entries).
- `## Verification` — how it was proven (probe/selftest by name, inline), and when it was deployed.
- `## ATTENTION` — what a future editor MUST know before touching this area: the trap, and why it is a trap. 1–5 bullets, each self-contained, no duplicates. NEVER the banned wording that forbids reversing a fix.

### Creation / change headings (this order, all mandatory)

- `## Motivation` — the problem or decision it serves.
- `## Design` — what was built and why this shape; alternatives rejected.
- `## How it works` — mechanism, wiring, how to use it.
- `## Consequences` — what it replaced/deleted, what it broke, follow-ups.
- `## Verification` — how it was proven, and when it was deployed.
- `## ATTENTION` — same rule as the issue heading.

### Quality gate

Before filing, the writer (or a judge seat of a different model) MUST answer the questions below against the body. Any "no" sends the body back. NEVER file a body that fails a question.

Issue (seven questions, one per heading):

1. Observed — can a stranger reconstruct the symptom as measured (what, where, when, by whom/which goal), with deployed-vs-HEAD when they differ?
2. Mechanism — does the body name what the code actually did and why that produced the symptom, rather than restating Observed?
3. Attempts — does it account for every earlier trial of THIS problem (what, when, why it failed), or write `First attempt held — checked: …`? NEVER `none recorded`?
4. Fix — does it say what was built AND why this design rather than the alternatives?
5. Consequences — does it say what the fix changed elsewhere (deleted/replaced, regressions, follow-ups)?
6. Verification — does it name how it was proven (probe/selftest) and when it was deployed?
7. ATTENTION — are there 1–5 self-contained trap bullets, each with why it is a trap, and no duplicates?

Creation / change (six questions, one per heading):

1. Motivation — does it name the problem or decision this creation serves?
2. Design — does it say what was built, why this shape, and what was rejected?
3. How it works — can a stranger operate or rewire it from the mechanism and wiring in the prose?
4. Consequences — does it say what it replaced/deleted, what it broke, and what follow-ups it required?
5. Verification — does it name how it was proven and when it was deployed?
6. ATTENTION — are there 1–5 self-contained trap bullets, each with why it is a trap, and no duplicates?

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
- **Observed / Mechanism / Attempts / Fix / Consequences / Verification / ATTENTION** — the issue-body headings (creation: Motivation / Design / How it works / Consequences / Verification / ATTENTION)
- **decision-log** — the per-goal `decisions.md`; not this memory
- **dreamers** — the curating role the KG names; `goal-memory-management` realizes it for this memory

## What memory is not

Not a task list. Not the register. Not a place for open questions. If it is still open, it does not belong here.

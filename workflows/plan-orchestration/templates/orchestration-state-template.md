# Orchestration State Template

Use this template to create the `orchestration-state.md` companion file for each orchestrated plan. The orchestrator creates it on first run (step-02) and overwrites it after every batch return and every reviewer return (step-03).

This file is the orchestrator's mutable state — separate from `shape.md` (which is append-only and reserved for planning decisions).

---

## Template

```markdown
# Orchestration State — {Plan Name}

> **Mutable file.** The orchestrator overwrites this file at each batch close and each reviewer close. Holds in-flight orchestration state ONLY — never planning decisions (those go in shape.md, append-only).

> **Audience:** the next orchestrator session, picking up after interruption. Everything here exists to make resumption clean.

---

## Resume Point

**Last completed:** {phase / batch / task ids — e.g., "Phase 2, batch B2C, p2-4"}
**Next dispatch:** {phase / batch / task ids — e.g., "Phase 2, batch B2D, p2-7" — OR "FINAL — orchestration complete"}
**Last update:** {ISO 8601 timestamp}

## Run Configuration

**Run mode:** {halt | end-to-end | autonomous}
**Context refresh mode:** {suggest | off}
**Plan path:** {absolute plan path}
**Shape path:** {absolute shape path or NONE}

## Approved Delegation Map

| Batch ID | Phase | Tasks | Executor Model | Reviewer Timing | Refresh Candidate |
|----------|-------|-------|----------------|-----------------|-------------------|
| {B1A} | {1} | {p1-1, p1-2} | {sonnet} | after Phase 1 | {no / yes: reason} |

## Completed Batches

| Batch ID | Phase | Tasks | Executor Model | Executor Status | Reviewer Status |
|----------|-------|-------|----------------|-----------------|-----------------|
| {B1A} | {1} | {p1-1, p1-2} | {sonnet} | {DONE} | {pending / CLEAN / FIXED} |

## Active State

**Doubt escalated:** {none, or: question + what was tried + why unresolved}
**Blocker:** {none, or: what blocked + what would unblock}
**Checkpoint awaiting user approval:** {none, or: phase id}

## Resume Capsule

**Next orchestrator action:** {dispatch next batch / dispatch reviewer / ask user / finalize}
**Reload required:** plan, shape if present, this orchestration state, plus docs listed in the next dispatch row
**User overrides:** {model overrides, run-mode choices, refresh choices, or none}
**Do not redo:** {completed batches/phases already reviewed clean/fixed}

## Notes for Resuming Agent

{Free-form. The orchestrator writes whatever the next session needs to pick up cleanly: critical context, irreversibility warnings, user overrides, model-tier exceptions, etc. Keep entries short. Replace stale notes when they no longer apply — this section is overwritten, not appended.}
```

---

## Usage

| Event | Orchestrator action |
|-------|---------------------|
| First run on this plan | Copy template body to `{plan_dir}/orchestration-state.md`, fill plan name + timestamp, leave Resume Point empty |
| Delegation approval | Write Run Configuration, Approved Delegation Map, refresh candidates, and initial Resume Capsule |
| Resume on existing plan | Read this file BEFORE batching. Use Resume Point + Approved Delegation Map + Completed Batches to skip done work |
| After each executor returns | Append batch row to Completed Batches with executor status; update Resume Point + timestamp |
| After reviewer returns | Update reviewer-status cells for that phase's batches; advance Resume Point; refresh Resume Capsule; refresh timestamp |
| Context refresh accepted | Leave Resume Point on the next dispatch, record the refresh checkpoint in Active State, and STOP |
| Doubt or blocker | Fill Active State; STOP |
| Plan complete | Set Resume Point to "FINAL — orchestration complete" |

## Boundaries

- NEVER write orchestration state to shape.md
- NEVER treat this file as append-only — overwriting is the contract
- NEVER use this for planning decisions — those go in shape.md (append-only)
- NEVER create separate handoff artifacts for context refresh — this file is the resume artifact

## Write Atomicity

The orchestrator MUST perform overwrites atomically:

1. Write the new content to a sibling temp file `orchestration-state.md.tmp`
2. Verify the temp file is well-formed (parses, contains required sections)
3. Replace the live file with the temp file (rename / atomic move)
4. If a `.tmp` sibling is found at start of a session, treat it as evidence of a previous interrupted write — surface to user before proceeding (per step-02 case "non-conforming")

If the live file is missing at session start, treat as missing and re-initialize per step-02. If the live file exists but is malformed or old-template, follow step-02's non-conforming-file choice gate.

## Size Management

At every overwrite, count lines. If >180:

1. Collapse rows from phases older than the previous phase into a single summary row: `| Phases 1-N | (completed) | — | — | summary | all CLEAN/FIXED |`
2. Keep the previous phase + current phase rows intact (full detail)
3. NEVER drop the Run Configuration, Active State, Resume Capsule, or Notes for Resuming Agent sections, regardless of size

The cap protects orchestrator context budget. If a plan needs full audit history beyond the cap, spawn a sibling `orchestration-audit.md` (append-only, no cap) and reference it from Notes for Resuming Agent — do not stuff audit detail into this file.

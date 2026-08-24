---
description: "Read at the moment the brainstorm turns on a plan or project the user has ALREADY committed to — the pre-mortem method: assume it has failed, reconstruct the causes, and land a failure-mode → cause → mitigation table."
tags: [functions]
---

# Pre-mortem

The project is COMMITTED. The decision to do it is settled and you NEVER relitigate it. You assume it has already failed, reconstruct how, and hand back mitigations the user can start today.

You are the teammate who finds the ways this goes sideways before it does.

> Boundary: `idea-sparring` (sibling reference) asks whether to build the thing at all and may kill it. This asks how a committed build fails and how to stop that. If the user turns out to still be deciding whether to commit, say so and switch to sparring — NEVER drift into should-we-build inside a pre-mortem.

## The sequence

### 1. Capture the project

Four things before ANY analysis: what it is meant to do, who it is for, the deadline, and the tricky parts. Any of the four missing → ask for it. Then reflect the project back in one or two sentences and confirm you have it right. NEVER pre-mortem a project you cannot describe back.

### 2. Declare it dead

State the framing out loud: *"It's {deadline} and this project is a disaster. It failed."* Then surface the most likely reasons it tanked. Aim for the handful that matter, NEVER an exhaustive list. Pull them from the tricky parts, the dependencies, the untested assumptions, and the people involved.

### 3. Drive each reason to its specific cause

For EACH failure reason, name the concrete things, choices, or mistakes behind it — a missed handoff, an untested assumption, an overloaded owner, a dependency that slipped a week. "Bad execution" and "scope creep" are symptoms, not causes: push to what exactly, by whom, triggered by what. One generic cause is the signal to dig further, NEVER to move on.

Where a cause turns on a fact neither of you holds — how a dependency actually behaves, what a comparable project's post-mortem found, whether a stated limit is real — DELEGATE the lookup to a sub-agent and keep the conversation moving while it runs. NEVER stall the exercise on research, and NEVER guess a number into the table.

### 4. Mitigate every cause

EVERY failure point ends with an action the user can start NOW — concrete and owned. "Add a two-week buffer before the integration date", "validate assumption X with a one-day test", "assign a backup owner for Y". "Be more careful", "monitor closely", and "communicate better" are NEVER mitigations.

### 5. Land the table

The exercise is incomplete until this table exists, with exactly these three columns:

| Potential failure reason | Specific failure points | Mitigation strategies |
|---|---|---|
| What might go wrong? | What exactly would cause that? | What do we do now to prevent it? |

One row per failure reason. Present it, then ask whether the user wants to deepen a row or add a failure reason you both missed.

## Done when

The table is complete, every row carries a mitigation the user can start today, and the user has no row left to deepen and no failure reason left to add.

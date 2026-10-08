# Pre-mortem

The result: a table of failure reasons, their specific failure points and their mitigations for a project the user has committed to, in which every row has a mitigation the user can start today.

Inputs: the committed project, with four things known about it: what it is meant to do, who it is for, the deadline, and the tricky parts. When one of the four is missing, ask the user for it before any analysis.

The decision to do the project is settled; do not reopen it. [Idea sparring](idea-sparring.md) asks whether to build the thing at all and may kill it; a pre-mortem asks how a committed build fails and how to prevent that. When the user turns out to be still deciding whether to commit, say so and switch to idea sparring. Do not discuss whether to build inside a pre-mortem.

## 1. Capture the project

With the four inputs in hand, describe the project back to the user in one or two sentences and confirm that you have it right. Do not run a pre-mortem on a project you cannot describe back.

## 2. State the failure

Say the framing to the user: *"It's {deadline} and this project is a disaster. It failed."* Then name the most likely reasons it failed: the few that matter, not an exhaustive list. Take them from the tricky parts, the dependencies, the untested assumptions and the people involved.

## 3. Trace each reason to its specific cause

For each failure reason, name the concrete things, choices or mistakes behind it: a missed handoff, an untested assumption, an overloaded owner, a dependency that slipped a week. "Bad execution" and "scope creep" are symptoms, not causes: ask what exactly, by whom, and triggered by what. When a cause is still generic, keep asking; do not move to the next reason.

When a cause depends on a fact neither of you holds (how a dependency behaves, what a comparable project's post-mortem found, whether a stated limit is real), the lookup goes to a sub-agent. Do not put a guessed number in the table.

## 4. Mitigate every cause

Every failure point ends with an action the user can start now, concrete and with an owner: "add a two-week buffer before the integration date", "validate assumption X with a one-day test", "assign a backup owner for Y". "Be more careful", "monitor closely" and "communicate better" are not mitigations.

## 5. Land the table

The pre-mortem is incomplete until this table exists, with exactly these three columns and one row per failure reason:

| Potential failure reason | Specific failure points | Mitigation strategies |
|---|---|---|
| What might go wrong? | What exactly would cause that? | What do we do now to prevent it? |

Present it, then ask whether the user wants to deepen a row or add a failure reason you both missed.

## Done when

The table is complete, every row has a mitigation the user can start today, and the user has no row left to deepen and no failure reason left to add.

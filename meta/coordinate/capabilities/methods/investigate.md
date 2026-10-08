# Investigate

Staged work for a question or problem whose shape is not yet known: wide machine passes (swarms) alternate with interviews of the user, and each stage feeds the next. The result is a set of specs and a plan that rest on evidence, with the user's intent and your own assumptions tested before anything is built.

This page is a way to structure the work, not a procedure to copy. The sequence below is one that worked; shape yours to the question. What stays fixed is the alternation and its reason: a decision made before the evidence is in is a guess, and an investigation run before the user's intent is pinned answers the wrong question.

## Why alternate

- A swarm is cheap, wide and fast, and it cannot ask what you mean. An interview is slow, narrow and expensive in the user's time, and it is the only source of intent.
- Run in sequence, each repairs the other's blind spot: the swarm turns the interview's vague terms into facts on disk, and the interview turns the swarm's facts into what the user actually wants done with them.
- A swarm runs while you interview. Your context holds the conversation; the sub-agents hold the files. Neither waits for the other.

## A sequence that worked

1. **Ground yourself.** Read the main documents (the entry point, the governing guides, the files the question names) and ask the user a few simple questions, enough to know what to send the first swarm after. Do not interview deeply yet: you do not know enough to ask the right questions.
2. **First swarm, wide and cheap.** One lane per facet of the question, on the cheapest models that can read and report ([Swarm](swarm.md)). Its job is facts: where things are, what they do, what changed.
3. **Interview while it runs.** With the first facts arriving, interview the user deeply on what they mean and want. The `thinking-partner` skill's interview mode, when installed, carries the question protocol. Challenge inconsistencies as they appear.
4. **Second swarm, pointed at the assumptions.** Now the problem has a shape and a diagnosis has formed. Send a second, smaller wave to fine-tune it and to look for what is wrong in it: the assumptions you and the user settled on, each one a lane with the files that would contradict it. This is the stage most often skipped and the one that finds the expensive mistakes.
5. **Closing interview.** Present the evidence and the diagnosis, surface what the second swarm contradicted, and close the specs with the user.
6. **Plan.** Turn the settled specs into a workflow the `plan` skill can execute, when installed; otherwise into tasks with scopes and done contracts.

## Choices at each stage

- **Pass discipline.** An investigation gathers and reports evidence and stops before naming a cause; a diagnosis lands on a defended cause with a falsifying test. Keep the two passes separate across your stages.
- **Judgment across a swarm's outputs** (a diagnosis, a verdict on which assumption fell) is a [panel](panel.md), not your own read of the lane files.
- **A stage that produces a long document** (a transcript, a log) to read is a [digest](digest.md).
- **A result the plan rests on** gets a [checker](checker.md) before it is written into the specs.
- **Depth.** Balanced by default: the wave sizes the question needs. The user asks for deep; it widens the investigator waves, not the synthesis.

## When this is the wrong page

- The question and its scope are already pinned: run one swarm, or one agent.
- The user wants ideas rather than an investigation of what exists: the `thinking-partner` skill, when installed.
- There is no user to interview (a headless seat): the interviews cannot run, so the stages collapse to a swarm plus a panel, and the specs are reported as open questions rather than closed.

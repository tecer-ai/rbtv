---
id: research-decision-spine
description: "Walk the deciding research spine in order — themes, options, segments, implications, insights, connections — each stage starting from the previous stage's insight artifact"
---

<task-goal>
Produce the decision-research chain the locking seat can freeze a thesis on: the six deciding stages walked in order, each one reasoning from the stage before it, every return key answered with its sources or named as an open gap.
</task-goal>

<scope>
- **Read:** the decision-research briefs under `planning/` (first line `RESEARCH-BRIEF`); the executor's own per-stage insight artifacts under `scratchpad/`; the external sources those briefs send the executor to.
- **Write:** `planning/decision-research.md`.
- **Out of scope:** the full materials corpus, the interview seed, any narrative lock, any visual or design artifact, the HTML standards library, and all owner contact.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/decision-research.md` exists and its first line is exactly `DECISION-RESEARCH`. The file is created empty at spawn, so existence proves nothing: a missing or misspelled marker is a non-report and fails this contract.
- The body carries one section per stage that ran, in the order themes, options, segments, implications, insights, connections. No stage appears out of that order, and no stage appears whose predecessor is absent without an explicit statement of why it was not owed.
- Each stage section names its brief by path, carries one entry per return key that brief declared, and states which prior-stage insight it started from.
- Every external-facing claim or number carries a source. A claim with no source appears as an open gap, never as a statement.
- Where sources conflict, both are reported and the conflict is flagged. The chain picks no winner and makes no recommendation about the narrative.
- The chain contains no thesis, spine of beats, slide number, or design language, and no markup tag.
- The chain contains no owner name, account, channel id, host, credential, or absolute machine path.
- A brief present under `planning/` whose first line is not exactly `RESEARCH-BRIEF` was not executed and is recorded in the goal's `issues.md`.
- Completeness: zero briefs present produces the artifact with its marker, an explicit statement that no decision-research was owed and that no stage ran, and an entry in the goal's `issues.md`; a brief naming a stage twice yields one section for that stage; a stage whose brief is absent is stated as not owed rather than silently skipped; a key answerable by no reachable source is an open gap, not an inference; every in-process dispatch wrote under its own `scratchpad/probes/` subfolder and nothing at this seat's folder root.

Outcome map:

- **Complete** → the chain feeds the locking seat's evidence map.
- **Partial chain** → stages that ran appear in order; every stage not owed is stated as not owed. The artifact still completes.
- **Keys unanswerable** → they are named as open gaps, and any key that blocks the lock is also recorded in the goal's `issues.md`. This seat never contacts the owner in any outcome.
</done-contract>

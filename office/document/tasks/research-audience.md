---
id: research-audience
description: "Execute the audience-intel briefs and return sourced findings keyed to each brief's own return keys, reading the briefs and nothing else"
---

<task-goal>
Produce the audience-intel findings the locking seat folds into the narrative: every return key each brief declared, answered with its sources or named as an open gap.
</task-goal>

<scope>
- **Read:** the audience-intel research briefs under `planning/` (first line `RESEARCH-BRIEF`) and the external sources those briefs send the executor to. Nothing else under `planning/` is in scope.
- **Write:** `planning/audience-intel.md`.
- **Out of scope:** the interview seed, the run brief's materials corpus, any narrative lock, any visual or design artifact, and all owner contact.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/audience-intel.md` exists and its first line is exactly `AUDIENCE-INTEL`. The file is created empty at spawn, so existence proves nothing: a missing or misspelled marker is a non-report and fails this contract.
- The body carries one section per executed brief, each naming that brief by path.
- Inside each section, every return key that brief declared has its own entry. The count of entries equals the count of declared keys; a key that could not be answered has an entry that says so and names what was searched.
- Every external-facing claim or number in the findings carries a source. A claim with no source appears as an open gap, never as a statement.
- Where sources conflict, both are reported and the conflict is flagged. The findings pick no winner and make no recommendation about the narrative.
- The findings contain no thesis, spine, beat, slide number, or design language, and no markup tag.
- The findings contain no owner name, account, channel id, host, credential, or absolute machine path.
- A brief present under `planning/` whose first line is not exactly `RESEARCH-BRIEF` was not executed and is recorded in the goal's `issues.md`.
- Completeness: zero briefs present produces the artifact with its marker and an explicit statement that no audience-intel was owed; a brief that is not self-contained is recorded in `issues.md` rather than answered by widening the read set; two briefs declaring the same key each get their own entry under their own section; a key answerable by no reachable source is an open gap, not an inference; every in-process dispatch wrote under its own `scratchpad/probes/` subfolder and nothing at this seat's folder root.

Outcome map:

- **Complete** → the findings feed the locking seat's evidence map.
- **Keys unanswerable** → they are named as open gaps; the artifact still completes, and any key that blocks the lock is also recorded in the goal's `issues.md`.
- **No brief owed** → the artifact records that and completes. This seat never contacts the owner in any outcome.
</done-contract>

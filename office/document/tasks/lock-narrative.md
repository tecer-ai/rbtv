---
id: lock-narrative
description: "Build the annotated spine from the excavation and the research findings, agree it with the owner, and freeze the narrative lock at the capability's completeness floor"
---

<task-goal>
Produce the gated narrative lock: one annotated spine of beats, agreed with the owner against the lock definition the excavation sitting established, carrying every section the locking capability's output contract requires.
</task-goal>

<scope>
- **Read:** under `planning/`, the interview seed (first line `INTERVIEW-SEED`), the decision-research chain (first line `DECISION-RESEARCH`) and the audience-intel findings (first line `AUDIENCE-INTEL`), each research artifact legally absent when its stage was not owed; the research briefs those artifacts reference; the locking capability's procedure and output contract; the machine-writing tells checklist; the owner, live on the goal's own channel.
- **Write:** `planning/narrative-lock.md`.
- **Out of scope:** re-interviewing, emitting new research briefs, renegotiating the audience; grouping beats into slides; the HTML standards library, the brand pack's palette, any slide list, and every other design surface.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/narrative-lock.md` exists and its first line is exactly `NARRATIVE-LOCK`. The file is created empty at spawn, so existence proves nothing: a missing or misspelled marker is a non-report and fails this contract.
- Every section the locking capability's output contract requires is present and non-empty. A lock missing a required section is incomplete and does not pass this gate.
- The thesis section carries exactly one sentence.
- Every beat in the spine carries all four of: a point-title stating the takeaway rather than labelling a topic; its role in the arc; a claim-or-observation-or-opinion annotation; and, per datum, the communication intent plus its source or its named gap.
- No beat carries two points. Where the excavation held two, the spine shows the split or the rethink.
- Every load-bearing external-facing claim is either sourced to the owner or to a named research finding, or listed in the open-data-gaps section as blocked. No such claim appears sourced to the executor's own inference.
- Every return key of every brief the run emitted is accounted for: folded into a beat, or listed as an open gap. A key that reached no finding is stated, not dropped.
- The artifact contains no slide number, no layout, palette value, hex colour, typeface name, grid, motif, chart style, or component name, and no markup tag.
- The artifact contains no owner name, account, channel id, host, credential, or absolute machine path.
- The lock-definition section states either mutual agreement with the owner, or `NOT AGREED` with the reason recorded.
- Completeness: a research artifact absent because its stage was not owed is stated as not owed rather than waited for; a present-but-markerless input is recorded in the goal's `issues.md` and treated as absent; a finding that contradicts an excavated claim is resolved in the spine or listed as a gap, never both dropped; a claim with two conflicting sources is annotated with the conflict; a run in which every stage was guarded off still produces every required section from the seed alone.

Outcome map:

- **Agreed** → the lock is gated and every downstream stage builds on it.
- **Nobody reachable** → the ratification ask parks; the spine is derived from the seed and the findings, every required section is present, the lock definition reads `NOT AGREED`, every unconfirmed beat is marked `owner-unconfirmed`, and the derivations, the unclosed ratification and the disclosure are recorded in the goal's `decisions.md`, `doubts.md` and `issues.md`. The artifact still completes and the run continues on a lock it knows is unratified.
- **Kill question unanswerable** → no thesis is frozen; the seat records a FAIL to the leader chair naming the unanswerable question. Refusing to proceed is a valid outcome of this gate.
</done-contract>

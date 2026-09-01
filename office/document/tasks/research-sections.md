---
id: research-sections
description: "Execute every per-beat fill brief through its own in-process probe and return sourced findings keyed to the brief's return keys, failing upward on a falsified must-have claim"
---

<task-goal>
Fill an already-locked narrative with evidence: run each `content-facts` and `competitive-context` brief the run emitted, and return one sourced answer per return key that brief declared. The narrative is settled before this work starts and stays settled — this act supplies facts, and it never regroups beats, retitles anything, or improves the argument. A claim the locked narrative marks must-have that the evidence contradicts stops the run rather than quietly reshaping it.
</task-goal>

<scope>
Read surface: the run's fill briefs in the goal's shared `planning/` workspace — the files whose first line is the marker `RESEARCH-BRIEF` and whose purpose type is `content-facts` or `competitive-context`; and the locked narrative, for its must-have claim list alone.

Explicitly outside the read surface: the visual-communication plan, the art-direction briefs, the brand pack, and the HTML standards library. None of them changes what a fact is.

Write surface: the seat's one declared goal output; the seat's own `scratchpad/probes/<brief-id>-<n>/`, one folder per dispatch; appends to the goal's five ledgers.

Parallelism is IN-PROCESS and belongs to this act. One catalog row covers the whole stage because the number of beats is unknown when the catalog is written; the fan-out over briefs is created here, at run time, and never as extra seats.

Not in scope: authoring briefs, editing the lock, deciding slide grouping, judging visual form, or contacting the owner.
</scope>

<done-contract>
1. The declared output exists and its FIRST LINE is exactly `FILL-RESEARCH`.
2. For every brief file under the goal's `planning/` workspace whose first line is `RESEARCH-BRIEF` and whose purpose type is `content-facts` or `competitive-context`, the output carries one section headed by that brief's id. Brief count and section count are equal.
3. Within each such section, every return key the brief declared appears exactly once. No declared return key is missing from the output.
4. Every return-key entry is either (a) an answer carrying both a source and the probe folder it came from, or (b) the literal token `unresolved` with a stated reason. No entry is an answer without a source.
5. Every probe folder cited in the output exists under `scratchpad/probes/` and no two dispatches cite the same folder. No file was written at the scratchpad root.
6. A brief set that is empty still yields an output carrying the `FILL-RESEARCH` first line and a `no-briefs` note, with the fact recorded in the goal's `doubts.md`. An empty declared output file is a non-report and fails this contract.
7. The locked narrative is byte-identical to what it was at the start of this act.
8. If any probe's evidence contradicts a claim the lock marks must-have: the seat recorded a FAIL to the leader chair, the goal's `issues.md` carries an entry naming the claim, the contradicting evidence and its source, and the output does NOT contain a rewritten or softened version of that claim.
9. No message was sent to the owner.
</done-contract>

---
id: pick-direction
description: "Run the one combined design gate — slide list, visual-communication plan and art-direction lanes presented together — and record the owner's direction pick without rendering anything"
---

<task-goal>
Get one decision from the owner: which visual direction this piece takes. The slide list, the visual-communication plan and every art-direction lane are presented TOGETHER as a single question, because they are one decision and splitting them would spend three owner touchpoints on it. The answer is recorded machine-readably so downstream acts read the pick rather than re-interpret a conversation. Where no owner answer is available, the ask is parked durably and the record says plainly that no pick exists — an invented direction would silently become the run's visual contract.
</task-goal>

<scope>
Read surface: the visual-communication plan (its slide grouping section is the slide list; its design handoff constraints and emphasis map are what an autonomous recommendation is derived from) and the art-direction briefs, both in the goal's shared `planning/` workspace.

Explicitly outside the read surface: deck source, rendered output, and screenshots. None exists at this point in the run.

Write surface: the seat's one declared goal output; appends to the goal's five ledgers; the seat's own working folder.

Owner contact: this act is the ONE owner gate between the narrative lock and the deck build. It is a single combined gate, never three; neither the visual-strategist act nor the art-direction act adds one.

Not in scope: rendering, previewing, or building anything; editing or merging a lane; rewriting the visual-communication plan; generating replacement lanes after a rejection.
</scope>

<done-contract>
1. The declared output exists and its FIRST LINE is exactly `BLUEPRINT`.
2. The output carries, each on its own line: `status:` with a value in {`picked`, `awaiting-owner-pick`, `rejected-all`}; `picked-direction:` with either a lane id present in the art-direction briefs or the literal `none`; and `plan-pointer:` with a path that resolves to the visual-communication plan carrying its first-line marker.
3. `status: picked` holds if and only if `picked-direction:` names a lane id from the art-direction briefs. `status: awaiting-owner-pick` and `status: rejected-all` each require `picked-direction: none`.
4. Where `status:` is `rejected-all`, the output also carries `rejection-round:` with an integer, plus one stated reason per rejected lane, and the goal's `issues.md` carries a matching entry.
5. Where `status:` is `awaiting-owner-pick`: an owner ask is on record in parked form; the output carries a `recommendation:` block naming, per lane, which design handoff constraint it satisfies or breaks and which plan section says so; the goal's `decisions.md` carries that same derivation with its provenance; the goal's `doubts.md` records that the run has no owner pick; and the seat ended as incomplete naming the unanswered pick. A `recommendation:` written as an assertion with no plan-section citation fails this clause.
6. Exactly one owner-facing decision message was sent for this act. Two or more owner asks fail this contract — the gate is combined, not split.
7. That message referenced the slide list, the visual-communication plan and every art-direction lane by its stable id. A lane present in the briefs and absent from the message fails this contract.
8. No HTML, image, screenshot, deck or preview file was produced by this act, and no deck source or screenshot was read.
9. The visual-communication plan and the art-direction briefs are byte-identical to what they were at the start of this act.
10. Both inputs carried their first-line markers before the gate was assembled. Absent either, no gate was assembled, the gap was recorded, and the seat ended incomplete.
11. An empty declared output file is a non-report and fails this contract.
</done-contract>

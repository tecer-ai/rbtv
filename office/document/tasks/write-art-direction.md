---
id: write-art-direction
description: "Produce two to three distinct, ban-list-clean art-direction lanes from a completed visual-communication plan, and regenerate genuinely new lanes exactly once after a full rejection"
---

<task-goal>
Give the owner a real choice of visual directions for a locked story: two or three lanes a stranger could tell apart, each covering the six mandatory art-direction axes, each drawn from real brand tokens, each clean against the banned-pattern catalog. The visual-communication plan is implemented here, never redefined. The picked lane becomes the run's visual contract — but the pick itself happens at the combined design gate, not in this act.
</task-goal>

<scope>
Read surface: the visual-communication plan and the locked narrative in the goal's shared `planning/` workspace; the run's brand pack palette and typography, resolved at run time from the workspace configuration; the Presentation page-type constraints reached through the HTML standards router; the reference set index when a run produced one; the banned-visual-pattern catalog; the art-direction persona this act sits in; and the blueprint record, read ONLY to learn the rejection round.

Explicitly outside the read surface: the fill-research corpus and the deterministic checker scripts.

Write surface: the seat's one declared goal output; appends to the goal's five ledgers; the seat's own working folder.

Sequencing: the visual-strategist act runs to completion and checks out first; this act consumes its finished plan. The two are never concurrent, and this act proves the plan is finished rather than assuming it.

Rejection allowance: exactly ONE regeneration. A first full rejection buys genuinely new lanes; a second full rejection ends the attempt and fails upward.

Not in scope: writing HTML or print CSS, presenting lanes to the owner, picking a lane, altering the locked narrative, or rewriting the visual-communication plan.
</scope>

<done-contract>
1. The declared output exists and its FIRST LINE is exactly `ART-DIRECTION-BRIEFS`.
2. The output carries at least two and at most three lane sections, each with a stable lane id unique within the output, and states the round number this set belongs to.
3. Every lane section covers all six mandatory axes — type pairing, palette within tokens, grid principle, signature motif, chart style, cover treatment — each present and non-empty.
4. Exactly one lane is named as the one this act believes in, and a more daring alternative is named beside the safe choice.
5. Every colour value and every font name appearing in the output is traceable to the brand pack or to the reference set. A value present in neither fails this contract.
6. The output contains no numeric floor copied from the standards library — no body sizing number, no canvas dimension, no print page setting. Those are read from the Presentation profile at run time by the acts that need them.
7. The output contains no HTML markup and no print CSS rule.
8. No banned visual pattern from the catalog appears in any lane.
9. The output does not restate, re-derive, or contradict the visual-communication plan's emphasis map, slide grouping, or per-slide form.
10. The locked narrative and the visual-communication plan are byte-identical to what they were at the start of this act.
11. The visual-communication plan carried its first-line marker and all six sections before any lane was generated. Absent that, nothing was written to the declared output, the gap was recorded, and the seat ended incomplete.
12. Where the brand pack carries no real tokens, the declared output names that gap and no lane was generated. An invented palette fails this contract.
13. Where the blueprint record shows a full rejection at round 2 or later, no new lane set was generated at all: the seat recorded a FAIL to the leader chair and an entry in the goal's `issues.md` naming the two rejected sets.
14. Where the blueprint record shows a full rejection at round 1, the new set shares no lane id with the rejected set and differs from it on grid principle, signature motif and cover treatment. A set differing only in palette fails this contract.
15. No message was sent to the owner.
</done-contract>

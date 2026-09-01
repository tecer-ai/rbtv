---
id: extract-visual-references
description: "Route each visual-reference brief to the one extraction capability its named input type selects, build the reference set with real provenance, and index it for the art-direction act"
---

<task-goal>
Turn written visual-reference asks into observed evidence — a live site's tokens, how a page moves, what one static image actually contains, or a curated set of exemplar images — and land it as a reference set with an index a downstream act opens first. Every artifact traces to a real source; a blocked, empty or unreachable target is reported as the result it is, never filled in.
</task-goal>

<scope>
Read surface: the run's visual-reference briefs in the goal's shared `planning/` workspace — the files whose first line is the marker `RESEARCH-BRIEF` and whose purpose type is `visual-references`; the asks section of the visual-communication plan, as a pointer to those paths; and any static reference image a brief names.

Explicitly outside the read surface: the narrative dump and the art-direction briefs. Neither changes what a live page measures.

Write surface: the seat's one declared goal output — the index — plus the reference set under the goal's `planning/reference-set/`, parts of that same one product; appends to the goal's five ledgers; the seat's own working folder.

Routing is by the input type the brief NAMES, one capability per brief. Firing every available extraction capability on every brief is out of scope and is the failure this routing exists to prevent.

Not in scope: judging whether an extracted reference is good design, authoring briefs, annotating the reference set for taste, or contacting the owner.
</scope>

<done-contract>
1. The declared output exists and its FIRST LINE is exactly `VISUAL-REFERENCES`.
2. For every brief file under the goal's `planning/` workspace whose first line is `RESEARCH-BRIEF` and whose purpose type is `visual-references`, the index carries one section headed by that brief's id. Brief count and section count are equal.
3. Each section states the input type the brief named, the capability that was fired, and either the artifact paths produced or an explicit `unroutable`, `blocked` or `empty` result with its reason.
4. Exactly one extraction capability is named per routable brief section. A section naming two or more fired capabilities fails this contract.
5. Every artifact path cited in the index exists under the goal's `planning/reference-set/`, and every path that exists under that reference set is cited by some section of the index.
6. Every produced artifact records the real URL or the real image file it came from, and the date. No artifact cites a source that was not actually reached.
7. Where an exemplar capture ran, the reference set's exemplars manifest carries one row per successful capture, and the index's capture count equals that row count.
8. Where a tool exited non-zero, no artifact for that target appears in the reference set and no index section claims one. A hand-written stand-in for a failed extraction fails this contract.
9. A brief naming no input type is recorded as `unroutable` in the index and as an entry in the goal's `issues.md`, and no capability was fired for it.
10. An empty or wholly unroutable brief set still yields an index carrying the `VISUAL-REFERENCES` first line and a `no-references` note, with the reason recorded in the goal's `doubts.md`. An empty declared output file is a non-report and fails this contract.
11. No message was sent to the owner.
</done-contract>

---
id: inspect-deck
description: "Inspect the rendered deck from actual screenshots in a fresh context, against the picked visual contract, the visual-flaw checklist and the copy tells, and produce the punch-list that blocks the owner gate."
---

<task-goal>

Catch, before the owner ever looks, every defect a fresh reader of the RENDERED pages can see and no
script can — and hand the builder a punch-list precise enough to fix each one without a conversation.

This act exists because a deck can pass every deterministic assertion and still fail on screen, and
because an occupant that watched the deck get built cannot see it any more. Fresh eyes on real
renders is the only mechanism that catches this class, and it is not optional.

</task-goal>

<scope>

**Inspection works from ACTUAL SCREENSHOTS, never from source text alone.** The pass renders the deck
over a local server, captures one image per slide, and makes every judgment by looking at those
images. The source may be consulted only to locate something the render already showed; a finding
that could not have been seen in a rendered page does not belong to this act. The `file` protocol
scheme is blocked for the review render and is never the fallback.

**Read surfaces.** The rendered deck as captured images; the style-check result, whose violation list
must be EMPTY before this act begins; the blueprint naming the owner's picked art-direction brief;
that brief itself; and the visual-communication plan stating what each slide is for. The builder's
working context and the full research corpus are deliberately not read.

**What this act asserts.** One idea per slide. The title states the takeaway rather than labelling a
topic. The motif the picked brief specifies is actually present on the page. Charts carry action
titles and communicate the point they were built for. Brand and third-party marks keep their identity
in spirit. The machine-writing tells in the titles and body copy as read off the rendered slides.
Every row of the visual-flaw checklist that no script can settle.

**What this act asserts NOTHING about.** Token hex equality, declared type families, numeric size
floors, banned source patterns, grid and zone counts, and cover-closing style identity are the
deterministic check's, already settled before this act runs; a finding in any of those classes is a
duplicate and does not belong on the punch-list. Aesthetic and distinctiveness judgment belongs to
the owner at the gate that follows; this act never substitutes for it.

**Sequencing.** This act always runs before the owner's review, and never concurrently with an
unpassed style check. The owner sees the floor-raised deck, never the raw first pass.

**Out of scope, deliberately.** This act never repairs the deck: it reports, and the builder patches.
Scoring, taxonomies, and any gating critic are not part of it.

**Loop route.** An open punch-list is a FAIL that re-fires the deck build, then the style check, then
this inspection — a visual patch can break a token assertion, so the checker always runs again before
this act sees the deck a second time. Roughly three bounces on one slide ends the polishing and FAILs
to the leader with a message-level rethink recommendation.

**Cleanup obligation.** The captures are throwaways. They are deleted at the end of the pass except
where a punch-list item attaches one as its evidence.

</scope>

<done-contract>

1. `planning/punch-list.md` exists, is non-empty, and its FIRST line is `PUNCH-LIST`. The file is
   created empty when the seat spawns, so its presence proves nothing — a missing or wrong first line
   is a non-report and fails this contract.
2. The style-check result carried an EMPTY violation list before this act began. Running against a
   non-empty list fails this contract.
3. A capture exists for every slide named in the visual-communication plan's slide list, and each
   punch-list item names the slide it belongs to. An item naming no slide, or a slide with no
   capture, fails this contract.
4. Every punch-list item carries three parts: the slide, a one-sentence statement of the defect that a
   stranger can act on, and the clause it violates — a named visual-flaw checklist row, a named clause
   of the picked art-direction brief, a named copy-tell category, or an explicit one-line spotting cue
   for a structural flaw the checklist does not cover. An item missing any of the three fails.
5. No item belongs to a class the deterministic check owns. A punch-list carrying a token-equality,
   declared-font, size-floor, banned-source-pattern, grid-count, or cover-closing-identity finding
   fails this contract.
6. No item is a taste or distinctiveness preference. Those are the owner's at the gate that follows.
7. The deck source, its assets, and every upstream artifact are unmodified by this act. Any change to
   them fails this contract.
8. The verdict is explicit and routed: an empty item list is recorded as a PASS clearing the owner
   gate; any open item is routed as a FAIL that re-fires the build, the style check, and this
   inspection in that order. A deck forwarded to the owner gate with an open item fails this contract.
9. Throwaway captures not attached as evidence to a punch-list item are deleted at the end of the
   pass. Captures left behind unattached fail this contract.

</done-contract>

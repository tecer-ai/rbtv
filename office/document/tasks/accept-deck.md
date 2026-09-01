---
id: accept-deck
description: "Put the verified, rendered deck in front of the owner in a visible browser and record their verdict — accepted, or bounced with actionable notes — together with an explicit handover decision."
---

<task-goal>

Capture the one signal no upstream mechanism can produce: whether the owner considers this deck
right. Everything before this act asserted conformance to a contract; this act asks the person the
contract was written for.

It exists because taste is not checkable and must not be simulated. Its whole value is that the
answer recorded here came from the owner, so an answer that did not come from the owner is worse than
no answer at all.

</task-goal>

<scope>

**Preconditions that BLOCK this act.** The deck must open with the HTML agent-note the standards
library requires; the style-check result must carry an EMPTY violation list; the punch-list must
carry NO open item. An open punch-list item blocks this act outright — the bar is near zero defect
and a deck that is mostly right is not shown. The owner sees the floor-raised deck, never the raw
first pass.

**Read surfaces.** The rendered deck, served locally and shown in a visible browser; the style-check
result; the closed punch-list. The design-extraction tools and the research corpus are not read.

**The contact.** Two decisions asked once, together: accept or bounce with notes, and whether the
owner wants the handover package. Both are stated plainly, with what follows from each choice. No
third question is added and no second contact is opened — this workflow has three owner gates and
this is the last of them.

**Autonomous behaviour.** Owner contact fires only when this seat's interactive mark and the goal's
interactive execution mode both hold. Where they do not, the ask parks durably for the owner's return
and the act does NOT decide on their behalf: a final acceptance cannot be defaulted, because
accepting on the owner's behalf fabricates the exact signal this act exists to capture. What the act
does instead is derive and record the verification state — the empty violation list, the closed
punch-list, the deck's agent-note — each with the artifact it came from, record the verdict as parked
and the handover decision as a disclosed default of no, and write the same derivation with the same
provenance into the goal's decisions ledger.

**Out of scope, deliberately.** This act never repairs the deck, never patches a slide, never edits an
upstream artifact, and never recommends for or against the deck. A bounce goes back to the builder.

**Loop route.** A bounce is a FAIL that re-fires the deck build, the style check, the render
inspection, and this act again, in that order. The owner then sees a patched deck, never a new
direction: no bounce re-opens the narrative lock, the visual plan or the picked direction.

**Refusal.** Stakes or novelty beyond what this pipeline can carry may be refused outright rather
than walked through an acceptance the workflow should not be asking for. Bail is a valid outcome.

</scope>

<done-contract>

1. `planning/acceptance.md` exists, is non-empty, and its FIRST line is `ACCEPTANCE`. The file is
   created empty when the seat spawns, so its presence proves nothing.
2. The file records exactly one verdict, and it is one of `accepted`, `bounced`, or `parked`. Any
   other value, more than one verdict, or a verdict stated only in prose fails this contract.
3. The file records the handover decision as an explicit `yes` or `no`. An absent handover decision
   fails this contract, because the seat downstream is guarded on it and absence reads as a silent no.
4. A verdict of `accepted` is recorded only where the owner accepted in their own words. A verdict of
   `accepted` recorded on any autonomous path fails this contract.
5. A verdict of `bounced` carries at least one note, each note naming the slide it concerns and a
   defect specific enough for the builder to act on without a further question. A bounce carrying no
   note, or a note naming no slide, fails this contract.
6. A verdict of `parked` carries the derived verification state with the artifact each fact came from
   — the empty violation list citing the style-check result, the closed punch-list citing the
   punch-list, the agent-note citing the deck — and states that its handover `no` is a disclosed
   default rather than the owner's word. The same derivation with the same provenance appears in the
   goal's decisions ledger. A `parked` verdict missing either the citations or the ledger entry fails.
7. The preconditions held when the contact was opened: an empty violation list and no open punch-list
   item. A contact opened over an open punch-list item fails this contract regardless of its verdict.
8. The deck source, its assets, and every upstream artifact are unmodified by this act.
9. A verdict of `bounced` is routed as a FAIL that re-fires the build, the style check, the
   inspection, and this act, in that order. A bounce recorded without that route fails this contract.

</done-contract>

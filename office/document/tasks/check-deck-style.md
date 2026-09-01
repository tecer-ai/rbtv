---
id: check-deck-style
description: "Run the deterministic style check over the built deck's source against the brand-pack tokens and the library page-type profile, and emit the machine-readable violation list that gates render inspection."
---

<task-goal>

Assert, without any model judgment, that the built deck's own source conforms to the brand-pack
tokens and to the library page-type profile — and hand the next stage a machine-readable verdict it
can gate on.

This act exists because the cheap, exact half of verification must run before the expensive,
judgment-bearing half. Every assertion here is one a script can settle from the source text, so no
reasoning is spent on it and no reviewer's attention is wasted re-deriving it.

</task-goal>

<scope>

**The mechanism is a tool, not an occupant.** This act is fully deterministic: the seat binds the
`design/visual-check` capability to its `design/visual-check-cli` executable and runs it. There is no
persona, no interpretation of the result, and no owner contact of any kind.

**Read surfaces.** The built deck's HTML source in the goal's shared `planning/` workspace; the brand
pack's token file, resolved at run time from workspace configuration; and the library page-type
profile for the Presentation type. Those three arrive as the checker's three required flags. Per-user
brand values arrive ONLY through the token flag and page-type floors and ceilings ONLY through the
profile flag — no numeric floor, token, or typeface is supplied from anywhere else, and a remembered
number is never substituted for one read at run time.

**What this act asserts.** Exactly the checker's own catalog: that every colour in the deck's style
and vector source is a brand-pack token or a tint the profile allows; that declared type families are
a subset of the brand-pack pairing; that declared sizes meet the floors the profile names; that the
named banned source patterns are absent; that skin values go through the profile's token contract
where it requires one; that card, zone, and column counts sit within the profile's ceilings; and that
the cover and closing declared styles match.

**What this act asserts NOTHING about.** It makes no assertion whatever about hierarchy, about the
distinctiveness of the picked art direction, about chart communication beyond the numeric size
floors, about team-card bio-depth parity, about aesthetic taste, or about whether the deck looks like
the picked motif. Those are render inspection's, from rendered screenshots, and a clean result here
is never evidence about any of them. Flattening the two mechanisms into one is a defect.

**Model applies.** These pages are agent-authored markup: the agent wrote the source, so a
deterministic style check here means the deck's own style, vector, and markup source against tokens
and the profile. Under a schema-plus-builder production model the same phrase would mean schema and
builder-output checks instead. The two are not interchangeable.

**Out of scope, deliberately.** The narrative lock, the research briefs, the art-direction briefs, and
the rendered screenshots are not read here.

**Loop route.** A non-empty violation list is a FAIL that re-fires the deck build and this check
again — the fixer alone would never close the loop. The list of check ids and locations is the whole
instruction the re-fired build gets.

</scope>

<done-contract>

1. `planning/style-check.json` exists, is non-empty, and parses as one JSON object carrying a
   `violations` array. The file is created empty when the seat spawns, so its presence alone proves
   nothing — a file that does not parse into that object is a non-report and fails this contract.
2. An EMPTY `violations` array is the pass convention: empty means the deck conformed, and it is the
   only representation of a pass. A pass is never expressed as a missing file, an absent key, a null,
   or prose.
3. Every entry in a non-empty `violations` array carries all four of `check_id`, `location`,
   `observed`, and `expected`, and every `check_id` is one the checker's own catalog defines. An
   entry missing a field, or naming a check id outside that catalog, fails this contract.
4. The checker was invoked with all three of its required inputs — the deck source, the brand-pack
   token file, and the library page-type profile — each resolved at run time. An invocation that
   substituted a remembered floor, token, or typeface for one of those files fails this contract.
5. The verdict matches the run: exit 0 with an empty array, or exit 1 with at least one entry. A
   usage or input-file error is exit 2 and produces NO success artifact — it is surfaced as a failure
   naming the unreadable input, never written out as a clean pass.
6. A profile that omits a floor a check needs causes that sub-assertion to be SKIPPED and the skip to
   be visible in the result. A defaulted, invented, or remembered floor standing in for an absent one
   fails this contract.
7. A non-empty violation list is routed as a FAIL that re-fires the deck build and this check, with
   the check ids and locations carried as the payload. A non-empty list recorded as a pass, or routed
   to the build without this check following it, fails this contract.
8. No owner contact was made and no artifact outside `planning/style-check.json` was written.

</done-contract>

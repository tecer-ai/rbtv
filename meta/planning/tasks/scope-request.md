---
id: scope-request
description: "Turn the seeded forge request into a ratified build spec — one enumerated piece per artifact with its destination, guide, done clauses and exposure decision — or into an escalation carrying a planning-ready goal seed"
---

<task-goal>
Deliver one executable build spec for the seeded component-part request, in which every ordered artifact is named, destined, guided, done-defined and exposure-decided.
</task-goal>

<scope>
- **Read:** the seeded request and every artifact it names; the target components' trees — their manifests, pools and existing parts; the authoring, destination and exposure law in the guides named in this task's Guides bullet.
- **Write:** `forge-spec.md` in the goal folder — nothing else. The goal's ledgers take appends as always; no component artifact is touched.
- **Guides — read whole before writing:** `references/authoring-style.md`; `references/component-anatomy.md`; `references/exposure-choice.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `forge-spec.md` exists in the goal folder and its first line reads exactly `disposition: forge` or `disposition: escalate`. (The file may exist EMPTY from spawn — existence is not the artifact; the disposition line is.)
- On `disposition: escalate`: the file names the trigger that fired, the evidence that fired it, and a goal seed carrying the request VERBATIM plus every user story elicited; it enumerates no piece.
- On `disposition: forge`: one row per ordered artifact, each carrying all seven fields — piece-id (unique within the spec); kind (one of reference · prompt · task · seat · capability · exposure entry · sub-agent definition); mode (create · edit · parse); an ABSOLUTE target path; the authoring guide the writer holds as its law, reading exactly `none — registration-only` on a row the spec marks registration-only (a row carrying no body, which no writer drafts and the building seat's registration act performs in full); at least one observable done clause; and an exposure decision that is either a named method plus the exact rows and frontmatter entries to write, or `none` with the reason it is none.
- The file states the JOB the request is hired for — the job itself, what the requester does today instead, and what makes that current way inadequate.
- Every done clause traces by name to a ratified user story (create mode) or to the confirmed intent (edit and parse mode), and every ratified story and confirmed intent is served by at least one done clause.
- Every target path lands under a component that already exists on disk, and under no `.claude/` installed copy.
- The file carries a ratification record: either the owner's explicit approval, or the derived-and-unratified mark with the parked ask cited.

Outcome map:

- **`disposition: forge`** → the building seat executes the rows; the spec is its denominator.
- **`disposition: escalate`** → the building and judging seats each record a no-work run, and the goal seed enters the planning workflow. Feedback schema: {trigger, the evidence that fired it, the path the seed was written to}.
- **A target path the write-destination rule cannot resolve** → REFUSE that piece back to the requester with the ambiguity named; no spec is written on a guessed destination. Feedback schema: {piece-id, the candidate destinations, the fact that would settle the choice}.
- **No owner answer available** → the spec is written with every unanswered point derived from the request and the grounding returns, each marked derived-and-unratified with its derivation. Feedback schema: {the point, the derivation, the parked ask}.
</done-contract>

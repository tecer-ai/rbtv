---
id: write-run-brief
description: "Produce the run brief — brief restated, audience, materials inventory, brand-pack status, stakes — resolving or guided-setting up the pack first"
---

<task-goal>
Produce the run brief the whole run starts from: the seeded ask restated, the audience as a role, an inventory of the materials already in hand, the runtime brand pack's status, and the stakes.
</task-goal>

<scope>
- **Read:** the goal seed and every artifact it names; any prior artifact the seed supplies, as content input only; the runtime brand pack at the workspace office configuration path; owner replies on the goal's own channel.
- **Write:** `planning/run-brief.md`.
- **Out of scope:** the HTML standards library, the design extraction tools, any narrative lock, any slide list. No thesis, no spine, no beat, no visual choice.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/run-brief.md` exists and its first line is exactly `RUN-BRIEF`. The file is created empty at spawn, so existence proves nothing: a missing or misspelled marker is a non-report and fails this contract.
- The body carries five named sections: brief restated; audience; materials; brand-pack status; stakes.
- The brand-pack status section lists every pack element (voice, palette, templates, glossary) and gives each exactly one status: `present`, `captured` (guided setup with the owner), `derived` (with the named material it was derived from), or `unresolved`. No element is missing from the list.
- No pack element carries a value whose origin is neither the pack, the owner, nor a named material. Every `derived` element names its source in the same line.
- The materials section lists one entry per material, each with a pointer and one line on what it supplies, or the single word `none`. A material that could not be opened appears with its gap named.
- The stakes section carries the seeded stakes or the single word `none`.
- Where the seed gives the audience as "everyone" or the objective as "to inform", the brief marks it unresolved rather than repairing or accepting it.
- The file contains no palette value, hex colour, typeface name, grid, motif, chart style, slide number, or markup tag.
- The file contains no owner name, account, channel id, host, credential, or absolute machine path.
- Completeness: every material the seed names appears in the inventory or as a named gap; every pack element has a status; a missing pack produces guided setup or a recorded derivation with provenance, never a default value; one material the seed names twice is one entry; a material named nowhere in the seed and present at no supplied path is not invented; a run with no materials, no prior artifact and no stakes still produces all five sections, three of them reading `none`.

Outcome map:

- **Complete** → the run brief seeds the excavation stage.
- **Pack missing, owner reachable** → guided setup captures the elements; the brief records them `captured`, and the run continues.
- **Pack missing, nobody reachable** → the ask parks; elements evidenced by the materials are recorded `derived` with provenance in the goal's `decisions.md`; elements no material evidences are recorded `unresolved` and appended to the goal's `doubts.md`. The brief still completes.
- **Seed inadequate** → repair forward what the materials support, name the rest unresolved, complete. Never reject, never re-enter.
</done-contract>

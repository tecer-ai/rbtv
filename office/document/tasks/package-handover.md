---
id: package-handover
description: "Assemble the accepted deck, its rationale document and its provenance-carrying asset library into one optional handover package inside the goal, or record a skip with the evidence behind it."
---

<task-goal>

Leave the run with one self-explaining package a stranger can pick up: the accepted deck, why it is
the way it is, and the assets behind it — or a plain record that the package was skipped and why.

This act exists because the reasoning behind a finished deck evaporates the moment the run ends, and
because the package is an OPTION the owner already answered. A truthful skip is a complete outcome of
this act, never a failure of it.

</task-goal>

<scope>

**Guarded and optional.** This act runs only where the owner's final review recorded that the package
was wanted. It never re-asks and never initiates owner contact of its own.

**Read surfaces.** The goal's shared workspace, marker-verified: the acceptance record and its
verdict, the accepted deck and its exported PDF, the deck's asset folder, the gated narrative lock,
the blueprint naming the picked direction, and the art-direction briefs. The research scratch is not
read.

**What is assembled.** Under the goal's handover folder: the accepted deck and its PDF; the asset
library, every binary naming where it genuinely came from; a rationale document explaining WHY the
deck is the way it is, drawn only from what the run already decided and citing the artifact behind
each statement; and a README that is the door to all of it.

**Provenance rule.** An asset whose provenance cannot be stated is left OUT of the package and named
as excluded with its reason. Nothing is fabricated, generated, or substituted to complete a set.

**Autonomous behaviour.** Where a required piece is missing — no accepted verdict, a deck without its
agent-note first line, or any input opening without its marker — this act does not wait, does not
ask, and does not assemble a partial package that presents itself as complete. It proceeds on the
stated default: SKIP the package and record the skip, naming what was missing, which artifact
established that, and which seat owed it, with the same record appended to the goal's decisions
ledger.

**Out of scope, deliberately.** Nothing is copied out of the goal folder and nothing is published
anywhere. No upstream artifact is modified. No design, narrative, or taste judgment is made or
revised here, and no rationale is inferred that nobody recorded.

</scope>

<done-contract>

1. `planning/handover/README.md` exists, is non-empty, and its FIRST line is `HANDOVER`. The file is
   created empty when the seat spawns, so its presence proves nothing.
2. The README records exactly one outcome, and it is either `packaged` or `skipped`.
3. On the `packaged` outcome the handover folder holds all four: the accepted deck, its exported PDF,
   the asset library, and the rationale document. A folder missing any of the four fails this
   contract.
4. On the `packaged` outcome every statement in the rationale document names the upstream artifact it
   came from — the narrative lock, the visual-communication plan, the blueprint, or the picked
   art-direction brief. A statement citing nothing fails this contract.
5. On the `packaged` outcome every binary in the asset library names its real provenance, and every
   asset excluded for want of provenance is listed in the README with its reason. A binary with no
   stated provenance fails this contract.
6. On the `skipped` outcome the README names what was missing, which artifact was checked to establish
   that, and which seat owed it, and the same record with the same provenance appears in the goal's
   decisions ledger. A skip missing any of those fails this contract.
7. No partial package exists: the outcome is `packaged` with clauses 3 through 5 met, or `skipped`
   with clause 6 met. A handover folder holding some of the four pieces under a `packaged` outcome
   fails this contract.
8. The accepted deck, its assets, and every upstream artifact are byte-identical to their state before
   this act. Any modification to them fails this contract.
9. Nothing was written outside the goal's handover folder and the goal's ledgers, and nothing was
   copied out of the goal folder or published anywhere.

</done-contract>

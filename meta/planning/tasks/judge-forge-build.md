---
id: judge-forge-build
description: "Try the finished forge build on evidence — every spec piece against its own done clauses and the ratified user stories, over components whose lint finding set is unchanged — and record the verdict durably"
---

<task-goal>
Deliver an evidence-grounded, durably recorded verdict on the seeded forge build, piece by piece against the spec that ordered it.
</task-goal>

<scope>
- **Read:** the seeded `forge-spec.md` and `forge-build.md`; every artifact at the target paths the spec declares; every component the build ledger names as touched; the run's coordination message log.
- **Write:** appended verdict rows in the run's coordination message log — nothing else. No file under the run package or under any touched component is written or edited by this trial.
</scope>

<done-contract>
Done criteria — all must hold:

- `component-lint` was RUN over every component the build ledger names as touched, and its finding set is identical to the pre-build baseline that ledger records — exit 0 where that baseline is empty. A finding present now and absent from that baseline is NEW.
- Each lint run's census line is credible: its printed prompt, task, seat, manifest-row and exposure-row counts match what is on disk in that component. An incredible census is a FAIL of the whole run, because a green lint over files it never discovered proves nothing.
- Every piece the spec enumerates was tried against BOTH its own done clauses and the acceptance the spec records for its mode — the ratified user stories on a create-mode spec, the confirmed intent on an edit- or parse-mode spec — and each carries the observation that decides it.
- The standing FAIL rules were applied without exception: a spec piece the ledger shows unbuilt is FAIL as a coverage gap; a piece the ledger claims built whose file is ABSENT at its declared target path is FAIL with that path named, never SKIP; a NEW lint finding against a touched component FAILs every piece of that component.
- The whole verdict was appended as ONE typed verdict message row to the run's coordination message log through the coordination tooling, exactly as the paired prompt's procedure states — the typed PASS or FAIL line first, then the per-piece verdicts with their evidence.
- Where the seeded `forge-spec.md` carries `disposition: escalate`: the trial records the run closed with no pieces — one verdict row naming the escalation trigger and stating that no artifact was built — and runs no lint and tries no piece.

Outcome map:

- **PASS** → the forge request is accepted; the built artifacts stand as the run's product.
- **FAIL below the goal's retry threshold** → the verdict seeds ONE gap-filling pass at the SAME spec. Feedback schema: per failed piece — {piece-id, declared target path, the clause or story it failed, the evidence observed, what is missing}.
- **FAIL at the goal's retry threshold** → the escalation row stands and nothing further runs at this spec until the owner answers. Feedback schema: {the failing verdicts' message numbers, the per-piece gaps that stand}.
- **An evidence surface unreachable** — a declared target path unreadable, or the lint unrunnable against a touched component → the affected pieces are FAIL with the exact surface named; the trial still completes and is recorded. Feedback schema: {the surface, the pieces it decides, what made it unreachable}.
</done-contract>

---
id: judge-milestone
description: "Try the seeded finished milestone against its done contract on evidence and record the clause-by-clause verdict durably in the run's message log"
---

<task-goal>
Deliver an evidence-grounded, durably recorded PASS/FAIL verdict on the seeded finished milestone against its own done contract.
</task-goal>

<scope>
- **Read:** the seeded milestone's done contract and the evidence surfaces it names (artifact homes, probe commands); the run's coordination message log; the run's goal artifacts (`goal.md`, `milestones.csv`).
- **Write:** appended verdict rows — and, once the consecutive-FAIL count reaches the goal's retry threshold, the escalation verb's single row — in the run's coordination message log; nothing else.
</scope>

<done-contract>
Done criteria — all must hold:

- A `verdict` message row for the seeded milestone exists in the run's coordination log, why-clause `milestone-<id>`, first body line exactly `verdict: PASS` or `verdict: FAIL`, carrying one evidence-grounded verdict per done-contract clause — every clause exercised; a clause whose evidence surface is missing or unexercisable reads FAIL, never SKIP.
- The consecutive-FAIL count is derived, never stored: a renewed judge seat and a restarted daemon both re-derive the same count from the run's message log — asserted by re-deriving across the restart or renewal, never by reading a stored value.
- Once the consecutive-FAIL count reaches the goal's retry threshold, exactly one escalation row for the milestone exists, carrying the recipient the escalation pins — `owner`, never the pass-opener the trial row itself is addressed to — a re-run of the trial appends no second one.
- No retry, attempt, or status column is added anywhere: every `.csv` header under the run package is byte-identical through a pass in which an escalation fires.

Outcome map:

- **PASS** → the milestone is accepted; the pass-opener (unblock-checker seat) acts next on this verdict.
- **FAIL below the retry threshold** → the verdict seeds ONE gap-filling planning wave at the SAME done contract, queued by the pass-opener. Feedback schema: per failed clause — the clause, the observed evidence, the gap.
- **FAIL at the retry threshold** → the escalation row stands; the pass-opener queues nothing at this contract until the owner answers. Feedback schema: the milestone id, the failing verdicts' message numbers, the per-clause gaps.
- **Evidence surface unreachable** → the affected clause is FAIL with the exact surface named in the verdict body; the trial still completes and is recorded.
</done-contract>

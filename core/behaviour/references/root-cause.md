---
description: "Read on every turn, and applied the moment a change is a FIX — a bug, an error, a wrong value, a failing run: fix at the cause never the symptom, ask why down to it, sweep siblings for the same cause, and write the root cause down BEFORE the first edit."
tags: [behaviour]
---

# Root cause

Fix at the CAUSE, NEVER at the symptom. Investigate before fixing. A solution MUST prevent recurrence, not restore the last good state. Ask "why" repeatedly down to the cause, and look for the same cause across similar problems — a defect that appears once in the place you were pointed at usually exists in every sibling that shares the cause.

**Tripwire — before editing a fix.** Write the root cause, and the file and line where the wrong value or behaviour is BORN, in the transcript BEFORE the first edit. A fix whose cause was never written down is a patch, not a fix.

**Where a value is born — the test when several points look plausible.** The origin is the earliest in-scope point where the actual state first violates the established contract; establish that contract from the callers, the schema, the tests, and the external-interface documentation. If the contract permits absence, the wrong behaviour is born at the first consumer that rejects absence; if the contract requires the value, it is born at the producer or validation boundary that first let it through. Name the contract evidence in the root-cause statement.

## Scope

All work, every turn. The code PROCEDURE of the fix that follows — where the edit lands, what is deleted, the signs of a patch — is the `coding` skill's `no-patches` reference.

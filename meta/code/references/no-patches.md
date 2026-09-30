---
description: "Read at the moment a change is a FIX — a bug, an error, a wrong value, a failing run — to rule the EDIT: it lands at the origin your root-cause statement named, the band-aid is deleted, a default is legal only where the contract permits absence, and the patch signs that stop an edit."
tags: [coding]
---

# no-patches

What arrives is a SYMPTOM — "this crashed", "this value is wrong", "this run failed". A fix lands where the wrong value or behaviour is BORN, never where it was noticed. The always-on `root-cause` rule already made you write the root cause, the origin (file + line), and the contract evidence BEFORE this edit; this reference governs the EDIT that follows that statement.

## Mandatory

| # | Rule |
|---|------|
| 1 | **The fix lands at the origin.** Edit the place your root-cause statement named. NEVER the crash site, the caller, or the output — unless the statement named that place as the origin. No statement → no edit: go back and write it. |
| 2 | **Delete the band-aid.** Any prior workaround for the SAME symptom — a special-case branch, a swallowed exception, a retry, a default that masks a missing value, a value recomputed because the caller's was wrong — is removed in the same change. A fix that leaves the band-aid in place has two fixes for one bug. |
| 3 | **A default is legal ONLY where the contract permits absence** and the default is the specified meaning of absence — and your root-cause statement names that contract evidence. Where the contract requires the value, a `.get(key, default)`, an `or fallback`, or any substitute at the consumer is FORBIDDEN: fix the producer or the validation boundary instead. |

## Patch signs — each one STOPS the edit until the root-cause statement is re-run

- a new `if` that special-cases the failing input
- a `try/except` (or the language's equivalent) that swallows the error
- a retry or a sleep around the failing call
- recomputing or re-fetching a value the caller already had
- a fix that touches ONLY the line in the traceback
- a default substituted for a value the contract requires (rule 3)
- "works now", with no sentence on why it failed

## Pre-existing

A band-aid you find that masks a DIFFERENT symptom than the one you are fixing is pre-existing: name it (file, line, what it masks) in your closing message; NEVER remove it unasked.

---
description: "Read at the moment a change introduces a second copy of anything — a value, a data source, a function, a code path — to rule the one authored source, what may derive from it by code, and what is a forbidden hand-maintained copy."
tags: [coding]
---

# no-duplicate

Every fact and every behaviour has exactly ONE authored source. Two sources for one thing is how a codebase stops being controllable: they drift, and the code then reads whichever one it happens to reach.

## What counts as duplicate

- Two places the code reads the same fact from — two config files, a constant and a literal, a table and a hand-filled cache.
- Two code paths doing the same thing in separate hands — a second helper doing what an existing one does, a copy-pasted block with one name changed, a second script for a job a script already does.
- A value kept equal in two files by a human remembering to.

## Rules

| # | Rule |
|---|------|
| 1 | Before writing a function, a value, a script, or a data file, you MUST search for the thing that already does it — by file extension, library calls, delimiters, output field names, and caller-visible behaviour, not by symbol name alone. Two pieces of code are THE SAME THING when they accept materially the same input contract and perform any of the same parsing, validation, or normalization steps; a different output shape alone does NOT make them separate. It exists → reuse or extend it; NEVER author a second one beside it. Extending existing code solely to serve the requested behaviour is part of the requested change, not an unasked cleanup. |
| 2 | A copy is legal ONLY when it is DERIVED BY CODE from the one source — a generated file, a build artifact, a cache the code fills and invalidates, a mirror a script writes. A hand-maintained copy is a violation, whatever comment sits on it. |
| 3 | When your change needs the same thing in two places, it lives in ONE, and the other reaches it by reference (import, call, read) — never by copy. |
| 4 | A copy that already existed before your change is pre-existing: name both paths in your closing message; fix it only if your change created it. |
| 5 | **An explicit no-touch boundary wins.** When the existing thing lives in a file you were told not to touch: reuse its interface without editing it if you can; otherwise STOP and ask the owner to authorize extending or extracting it. NEVER create a second implementation to route around the boundary. |

## Tripwire

Before closing: does any value, function, data source, or script you wrote now exist somewhere else too? If yes, one of the two goes.

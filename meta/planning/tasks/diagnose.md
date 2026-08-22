---
id: diagnose
description: "Probe the seeded local/system subject and return its observed state together with the probes run"
---

<task-goal>
Report the seeded subject's observed state — every fact backed by a probe run in this dispatch, never by a document's claim.
</task-goal>

<scope>
- **Read:** the seeded subject's files and system surfaces, via read-only probes.
- **Write:** none — the report returns to the dispatcher; the probed subject is never modified.
</scope>

<done-contract>
Done criteria — all must hold:

- Every reported fact is paired with the probe (command or read) that observed it, with the probe's actual output cited.
- Every claim taken from documentation is probe-verified or labeled unverified.
- The report returns to the dispatcher and to nothing else; the probed subject's state is unchanged.

Outcome map:

- **Complete** → the dispatcher folds the report in; the dispatch ends with the return.
- **The subject is unreachable** → return the failing probe and its exact error — observed state too. Feedback schema: the probe, its error output.
- **The seed names a subject absent on disk** → return the existence probe's output; never infer what "should" be there. Feedback schema: the path or name probed, the probe, its output.
</done-contract>

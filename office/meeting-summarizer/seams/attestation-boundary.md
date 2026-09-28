# attestation-boundary — constraint entry (no schema, no instance)

This seam is a boundary, not a payload: nothing crosses it at runtime, and no code in
this workflow may look across it.

The two facts on the far side are settled by OWNER ATTESTATION — `goal.md` clause 17
names them (the owner-amended attestation sentence of its final clause). Because they are
settled, they MUST NOT be probed, re-verified, or restated anywhere in this workflow's
tree: not by m2's verification pass, not by any later build, not by documentation. A
check of an owner-attested fact is a defect, not a safeguard.

Enforcement is mechanical: the `validate-seams` grep arm scans every file under
`workflows/transcript-summarizer/` and fails the seam set on any probe of these facts.
This document deliberately does not name them — one fact, one home: `goal.md` clause 17.

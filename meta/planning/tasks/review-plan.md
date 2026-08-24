---
id: review-plan
description: "Trial the draft plan once, tag findings blocking/non-blocking, revise only blocking, and ship the approval package"
---

<task-goal>
Trial the seeded draft plan once against its frozen milestone list and the six seat declarations, emit findings tagged blocking or non-blocking, revise only the blocking findings, and produce the review package a verifier can check.
</task-goal>

<scope>
- **Read:** the design and the facts brief; the draft plan; every artifact those name; on a verify FAIL relaunch, the FAIL body as the closed findings list.
- **Write:** `planning/review-package.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/review-package.md` exists and its first line is exactly `REVIEW-PACKAGE`.
- The body carries a findings list, each entry tagged `blocking` or `non-blocking`, emitted exactly once — a second findings pass on the same run is a fail.
- Only findings tagged `blocking` were revised; every `non-blocking` finding remains, untouched, as accepted residue.
- The revised plan still carries every milestone id the design froze, unbroken.
- The approval package section names what the owner is being asked to bind: the plan artifacts, and that approval binds at a recorded git commit — never at a canvas.
- An `input-gaps` list is present (may be empty).
- Completeness: every one of the six workflow-authoring-checklist declarations was trialed against every produced execution seat in the draft; a failed declaration is `blocking`; two findings naming the same defect are collapsed to one; a finding with no plan location is not a finding.

Outcome map:

- **Complete** → the review package seeds verify.
- **Markerless or thin draft** → repair forward, log the gap, complete. Never reject. Never re-enter draft or design.
- **Verify FAIL relaunch** (this task's seat is on verify's `on-fail-relaunch`) → treat the FAIL body as the closed findings list; do not emit a new findings list; apply a targeted fix for those items only; rewrite the review package (same first-line marker); complete. Feedback schema: each closed finding paired with the fix applied.
</done-contract>
</output>

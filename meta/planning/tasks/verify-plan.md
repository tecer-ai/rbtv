---
id: verify-plan
description: "Check closed findings and the unbroken milestone list, cap regression fix passes at two, and compose the approval digest — do not post"
---

<task-goal>
Run exactly two contract checks against the seeded review package and the design's frozen milestone list, cap regression fix passes at two, and compose the phone-sized approval digest naming the four owner outcomes.
</task-goal>

<scope>
- **Read:** the review package; the design; the draft plan, if the package points at it; this seat's own `memory.md` regression-pass lines.
- **Write:** `planning/approval-digest.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/approval-digest.md` exists and its first line is exactly `APPROVAL-DIGEST`.
- Exactly two checks were run: (a) every `blocking`-tagged finding in the review package is addressed in the revised plan; (b) every milestone id in the design is still present with its done-criteria unbroken. No third check was added.
- Where either check failed and this seat's `memory.md` carries fewer than two `REGRESSION-PASS` lines: a `REGRESSION-PASS <n>` line was appended, a FAIL was recorded naming only the failed check's items (the closed findings list for the revision seat), and no digest was composed this pass.
- Where either check failed and two `REGRESSION-PASS` lines already exist: no third FAIL was issued; the digest was composed carrying the red flag `unresolved regression`.
- Where both checks passed: the digest was composed carrying no `unresolved regression` flag.
- The digest names: milestones (ids + one-line aims), seat count, envelope summary (deltas vs the shipped planning envelope), which seats are interactive, credential-resolve result per declared credential name, red flags, paths to every on-disk artifact (facts brief, design, draft, review package, this digest), the recorded git commit the plan artifacts bind to, and the four owner outcomes verbatim — `approve` / `reject-close` / `reject-pause` / `reject-retry`.
- The digest was composed only — never sent; no Slack post, no owner-channel message from this task.
- An `input-gaps` list is present (may be empty).

Outcome map:

- **Both checks pass** → the digest ships for a later Slack seat to post.
- **A check fails, cap not reached** → FAIL recorded; the revision seat then this task re-fire. Feedback schema: the failed check's items only, as the closed findings list.
- **A check fails, cap already reached** (two prior `REGRESSION-PASS` lines) → no further FAIL; the digest ships with the `unresolved regression` red flag instead.
- **Markerless review package** → repair enough to run the two checks from what is on disk, log the gap among the digest's red flags, complete. Never reject. Never re-enter an earlier stage.
</done-contract>
</output>

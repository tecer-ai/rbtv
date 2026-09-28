---
id: verify-plan
description: "Check closed findings and the unbroken milestone list, cap regression fix passes at two, and write the approval digest. The file is the ask."
---

<task-goal>
Run exactly two contract checks against the seeded review package and the design's frozen milestone list, cap regression fix passes at two, and write the phone-sized approval digest. The file is the ask. Do not send a bus message.
</task-goal>

<scope>
- **Read:** the review package; the design; the draft plan, if the package points at it — including its EXECUTION DECLARATION, which supplies every field the approve-package writer takes; `planning/bound-commit`, the one line holding the commit the plan artifacts bind to; this seat's own `memory.md` regression-pass lines.
- **Write:** `planning/approval-digest.md`. Do not run `approve-package` — that CLI was
  deleted with Ignite 0.1.
- **Ask:** the digest file is the approval ask. Do not send it. There is no coordination CLI.
  Write every required field into `planning/approval-digest.md`. Never drop a required field.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/approval-digest.md` exists and its first line is exactly `APPROVAL-DIGEST`.
- Exactly two checks were run: (a) every `blocking`-tagged finding in the review package is addressed in the revised plan; (b) every milestone id in the design is still present with its done-criteria unbroken. No third check was added.
- Where either check failed and this seat's `memory.md` carries fewer than two `REGRESSION-PASS` lines: a `REGRESSION-PASS <n>` line was appended, a FAIL was recorded naming only the failed check's items (the closed findings list for the revision seat), and no digest was composed this pass.
- Where either check failed and two `REGRESSION-PASS` lines already exist: no third FAIL was issued; the digest was composed carrying the red flag `unresolved regression`.
- Where both checks passed: the digest was composed carrying no `unresolved regression` flag.
- The digest names: milestones (ids + one-line aims), seat count, envelope summary (deltas vs the shipped planning envelope), which seats are interactive, credential-resolve result per declared credential name, red flags, paths to every on-disk artifact (facts brief, design, draft, review package, this digest), the plan's execution declaration (the goal name it will be born under, its lane, its roster), and the bound commit the plan artifacts bind to.
- The bound commit was READ from `planning/bound-commit`, never derived and never typed. This seat is caged with `.git` masked, so no `git` command here can answer. Where the file is absent, empty, or not a lowercase hex sha of 7-64 characters: write `planning/approval-digest.md` as the single line `incomplete: missing binding` naming the file, and stop. Do not send a bus message.
- The binding is FRESH, not merely present. `planning/bound-commit` must be NEWER than `planning/review-package.md` (compare their modification times — `ls -l` or `stat` on the two files, both of which sit in the goal's shared `planning/` workspace this seat can read). A bound-commit OLDER than the review package names a tree that does not contain the review package. The after-edge holds this seat at `bind=stale` until a fresh bind lands; this check is the caged refusal so you never compose against a dead tree. Where the binding is STALE: write `planning/approval-digest.md` as the single line `incomplete: awaiting re-bind` naming both files and their times, and stop. Do not send a bus message. NEVER compose against a stale binding and NEVER carry the shortfall as a red flag: a digest that describes one tree while `planning/bound-commit` names another is the exact disagreement the owner cannot see from the approval thread, and by the time it is noticed every planning seat has departed.
- The execution declaration was read, not authored here. An absent or invalid declaration is NOT defaulted: write `incomplete: missing execution declaration` as the digest's first line and stop.
- The digest does NOT list the owner's reply tokens. The approval thread publishes them itself,
  from the parser's own vocabulary (`ignite/chat/approval-thread.js` composes the posted message:
  the goal name, the irreversible warning, this digest, the bound commit, then the token line).
  A digest that names its own token list is a SECOND source for the words the parser accepts, and
  it drifted: this file asked for `reject-close` / `reject-pause` / `reject-retry`, none of which
  the parser accepts — a NACK for every rejection the owner tried to type.
- `approve-package` is not run. That CLI was deleted with Ignite 0.1.
- The digest file is the ask. It was not sent. There is no coordination CLI.
- An `input-gaps` list is present (may be empty).

Outcome map:

- **Both checks pass** → the digest file is the approval ask. Do not send it.
- **The bound commit is missing** (`planning/bound-commit` absent, empty, or not a sha) → write
  `incomplete: missing binding` and stop. Never `commit: uncommitted`, and never a guessed sha.
- **The bound commit is STALE** (older than `planning/review-package.md`) → write
  `incomplete: awaiting re-bind` naming both files and their times, and stop.
- **The plan declares no execution goal** (or an invalid one) → write that as the digest's first line and stop. Never a default and never a name of
  this seat's own invention.
- **Do not run `approve-package`.** That CLI was deleted with Ignite 0.1.
- **A check fails, cap not reached** → FAIL recorded; the revision seat then this task re-fire. Feedback schema: the failed check's items only, as the closed findings list.
- **A check fails, cap already reached** (two prior `REGRESSION-PASS` lines) → no further FAIL; the digest ships with the `unresolved regression` red flag instead.
- **Markerless review package** → repair enough to run the two checks from what is on disk, log the gap among the digest's red flags, complete. Never reject. Never re-enter an earlier stage.
</done-contract>

---
id: verify-plan
description: "Check closed findings and the unbroken milestone list, cap regression fix passes at two, write the approve-package the daemon reads on approve, and send the approval digest to the owner as the approval ask"
---

<task-goal>
Run exactly two contract checks against the seeded review package and the design's frozen milestone list, cap regression fix passes at two, compose the phone-sized approval digest, and SEND it to the owner as the approval ask — the one message that lets him start execution with a single word.
</task-goal>

<scope>
- **Read:** the review package; the design; the draft plan, if the package points at it — including its EXECUTION DECLARATION, which supplies every field the approve-package writer takes; `planning/bound-commit`, the one line holding the commit the plan artifacts bind to; this seat's own `memory.md` regression-pass lines.
- **Write:** `planning/approval-digest.md`; `planning/approve-package.json`, through the
  `approve-package` writer only.
- **Send:** the digest to the owner, ONCE, as the APPROVAL ASK — one `note` addressed to `owner`
  on the coordination bus carrying the bound commit, which the bus ferry turns into the owner's
  approval thread:
  `coordinate send owner --file planning/approval-digest.md --type note --approve-commit <the bound commit>`
  Never a Slack call, never an outbox record, never a second transport. The `--approve-commit`
  flag is what makes this an APPROVAL rather than an ordinary question, and `coordinate` refuses
  it unless this seat is `human-interactive:` and `planning/approve-package.json` records that
  exact `bound_commit` — so the package is written BEFORE the send, always.
  This one send carries NO length cap: the required digest fields below do not fit the ordinary
  2,000-character body cap, and an approval row is exempt from it because the bridge builds the
  owner's thread out of this body. So never `--force` here, and never drop a required field to fit:
  `--force` waives every OTHER gate on this path too, and the cap is no longer one of them.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/approval-digest.md` exists and its first line is exactly `APPROVAL-DIGEST`.
- Exactly two checks were run: (a) every `blocking`-tagged finding in the review package is addressed in the revised plan; (b) every milestone id in the design is still present with its done-criteria unbroken. No third check was added.
- Where either check failed and this seat's `memory.md` carries fewer than two `REGRESSION-PASS` lines: a `REGRESSION-PASS <n>` line was appended, a FAIL was recorded naming only the failed check's items (the closed findings list for the revision seat), and no digest was composed this pass.
- Where either check failed and two `REGRESSION-PASS` lines already exist: no third FAIL was issued; the digest was composed carrying the red flag `unresolved regression`.
- Where both checks passed: the digest was composed carrying no `unresolved regression` flag.
- The digest names: milestones (ids + one-line aims), seat count, envelope summary (deltas vs the shipped planning envelope), which seats are interactive, credential-resolve result per declared credential name, red flags, paths to every on-disk artifact (facts brief, design, draft, review package, this digest), the plan's execution declaration (the goal name it will be born under, its lane, its roster), and the bound commit the plan artifacts bind to.
- The bound commit was READ from `planning/bound-commit`, never derived and never typed. This seat is caged with `.git` masked, so no `git` command here can answer; the goal's `leader` writes that file when it accepts the review seat's row. Where the file is absent, empty, or not a lowercase hex sha of 7-64 characters: NOTHING is composed and NOTHING is sent — the missing binding is this task's outcome and the check-out is `--incomplete` naming the file, which wakes the `leader` whose disposition 1 is to perform the commit and relaunch this seat.
- The binding is FRESH, not merely present. `planning/bound-commit` must be NEWER than `planning/review-package.md` (compare their modification times — `ls -l` or `stat` on the two files, both of which sit in the goal's shared `planning/` workspace this seat can read). A bound-commit OLDER than the review package names a tree that does not contain the review package: the `after` edge spawns this seat the moment the review seat checks out, while the `leader` is only woken by that same check-out and binds a moment later, so an unlucky order hands this seat a binding short by the file the approval is about. Where the binding is STALE: NOTHING is composed and NOTHING is sent. Check out `--incomplete "awaiting re-bind"` naming both files and their times — the `leader`'s disposition 1 is to re-bind and relaunch this seat, and the relaunch reads a fresh file. NEVER compose against a stale binding and NEVER carry the shortfall as a red flag routed at the leader: a digest that describes one tree while `planning/bound-commit` names another is the exact disagreement the owner cannot see from the approval thread, and by the time it is noticed every planning seat has departed.
- Every field handed to the `approve-package` writer came from the plan's EXECUTION DECLARATION (`--execution-goal`, `--lane`, `--roster`, `--contract-file`, and `--workflow` / `--sheet` where declared), plus the bound commit and the `planning/` artifacts path. No field was authored here. An absent or invalid declaration is NOT defaulted: nothing is composed, nothing is sent, and the missing declaration is this task's outcome — approval births a goal under that name, and inventing one approves a goal the plan never described.
- The digest does NOT list the owner's reply tokens. The approval thread publishes them itself,
  from the parser's own vocabulary (`ignite/chat/approval-thread.js` composes the posted message:
  the goal name, the irreversible warning, this digest, the bound commit, then the token line).
  A digest that names its own token list is a SECOND source for the words the parser accepts, and
  it drifted: this file asked for `reject-close` / `reject-pause` / `reject-retry`, none of which
  the parser accepts — a NACK for every rejection the owner tried to type.
- `planning/approve-package.json` exists and was written by the `approve-package` writer — never
  by hand and never by a second writer. It is what the daemon reads when the owner types `approve`,
  and until this task writes one every approval refuses `no-approve-package`, loudly, in the thread.
  It carries the execution-goal name the plan declares, the bound commit recorded above, the lane
  the plan declares, and the path to the plan artifacts; it names NO planning goal and NO goals
  root, because the daemon derives both and refuses a package that disagrees with its derivation.
- Where the writer refuses (a name that is not a bare safe name, a bound commit that is a ref name
  rather than a hex sha), the refusal is carried as a red flag on the digest and the package is
  NOT hand-written. A hand-written package is the one way this file can claim a plan nobody checked.
- The digest was SENT, exactly once, by the Send clause's command, and the command exited 0. A
  refusal from that command is a red flag on the digest and a FAIL of this task — never a hand-
  written Slack post and never a second attempt through another transport.
- An `input-gaps` list is present (may be empty).

Outcome map:

- **Both checks pass** → the approve-package is written, then the digest is sent to the owner as
  the approval ask. The owner's `approve` in that thread starts execution; nothing else in this
  workflow runs after it.
- **The bound commit is missing** (`planning/bound-commit` absent, empty, or not a sha) → nothing is
  composed and nothing is sent. Report the missing binding, check out `--incomplete` naming the file,
  and let the `leader` bind and relaunch. Never `commit: uncommitted`, which asserts something this
  seat cannot know, and never a guessed sha.
- **The bound commit is STALE** (older than `planning/review-package.md`) → the same outcome, for the
  same reason: nothing composed, nothing sent, check out `--incomplete "awaiting re-bind"` naming both
  files and their times. The re-bind is the `leader`'s act and the relaunch is how this seat receives
  it — never a red flag on a digest that ships anyway.
- **The plan declares no execution goal** (or an invalid one) → nothing is composed and nothing is
  sent. Report it; the review stage supplies the declaration. Never a default and never a name of
  this seat's own invention.
- **The approve-package writer refuses** → the digest is written to disk carrying the refusal as a
  red flag, and it is NOT sent: with no package the send is refused at `coordinate` anyway, and an
  approval the daemon would answer `no-approve-package` is worse than no ask. Nothing is
  hand-written. Report the refusal as this task's outcome so a later pass can fix the input the
  writer named.
- **A check fails, cap not reached** → FAIL recorded; the revision seat then this task re-fire. Feedback schema: the failed check's items only, as the closed findings list.
- **A check fails, cap already reached** (two prior `REGRESSION-PASS` lines) → no further FAIL; the digest ships with the `unresolved regression` red flag instead.
- **Markerless review package** → repair enough to run the two checks from what is on disk, log the gap among the digest's red flags, complete. Never reject. Never re-enter an earlier stage.
</done-contract>

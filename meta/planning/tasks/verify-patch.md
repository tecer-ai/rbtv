---
id: verify-patch
description: "Check the replan patch against the milestone's unchanged done contract and NOTIFY the owner of what you found — never a verdict, never a relaunch, never a gate"
---

<task-goal>
Run the unchanged-contract check over the replan's patch (or its escalation analysis) and write ONE
owner-facing notice saying what the check found. The notice is the product on every outcome. This
task NOTIFIES and never gates: a problem it finds is reported, and the replan continues [D13].
</task-goal>

<scope>
- **Read:** `planning/replan/patch-plan.md`; `planning/replan/gap-brief.md`; the failed milestone's
  done contract, as written and unchanged; the milestone's plan and seats; the goal's compiled
  permission envelope; owner replies on the goal channel.
- **Write:** `planning/replan/replan-notice.md`.
- **Send:** the notice to the owner, once, through the goal's ordinary owner-contact path — one
  `note` addressed to `owner` on the coordination bus, which the bus ferry carries into the owner's
  Slack surface. Never a Slack call, never an outbox record, never a second transport.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/replan/replan-notice.md` exists and its first line is exactly `REPLAN-NOTICE`.
- The second line is exactly `check: pass` or `check: problems` — one authored word the notice's
  reader keys on, never an inference over prose.
- Exactly two checks were run, and no third was added:
  - **(a) The contract is unchanged.** Every milestone id the goal's plan carries is still present
    with its done-criteria unbroken, and the failed milestone's own contract is byte-identical to
    the one the gate judged. The patch is allowed to change how the milestone is met; it is never
    allowed to change what meeting it means.
  - **(b) The patch is inside its two walls.** Under `disposition: patch`: no milestone but the
    failed one is amended, and the patch adds no bind, path, host, tool, credential name or grant
    the compiled envelope does not already carry. Under `disposition: escalate`: the file carries
    zero patch content and names the crossing.
- The notice names, for each check, the result and the evidence it rests on — for a problem, the
  clause or wall breached and the patch element that breaches it, quoted. A problem stated without
  the element it names is not a finding.
- The notice names the milestone, the disposition line it read, and the path of every artifact it
  read.
- **NOTIFY-ONLY, and every clause here is a prohibition on gating:**
  - No verdict is recorded. This task never runs the verdict verb, in either clause. A FAIL verdict
    arms the escalation gate and halts the milestone's contract, which is the opposite of this
    task's job.
  - No relaunch is routed. This seat declares no `on-fail-relaunch` route, so no seat re-fires from
    what it finds and there is no fix pass to count. A problem is reported once, in the notice.
  - No stage is re-entered, no seat is re-dispatched, no lane is stamped, and nothing is withheld:
    the notice is written and sent on `check: problems` exactly as it is on `check: pass`.
  - No approval outcome is offered. This notice is not a plan-approval digest and carries none of
    `approve` / `reject-close` / `reject-pause` / `reject-retry`. Nothing downstream waits on an
    owner reply to it — the owner reads it and intervenes only by choice [D13].
- The notice was SENT exactly once, as one `note` addressed to `owner`, with the notice file as its
  body. Sending twice is a defect; sending zero times is an unmet done criterion, because an
  unsent notice notifies nobody.
- An `input-gaps` list is present (may be empty).
- No credential *value*, owner-specific channel, host, account, or vault path appears in the file.

Outcome map:

- **Both checks pass** → `check: pass`; the notice says so and is sent; the replan is finished and
  the milestone re-runs.
- **Either check finds a problem** → `check: problems`; the notice names every problem with its
  evidence and is sent; the replan is STILL finished and the milestone STILL re-runs. The owner
  decides what to do about the problem, on his own clock.
- **Markerless or thin patch plan** → repair enough to run the two checks from what is on disk, log
  the gap in `input-gaps`, name it among the problems, complete. Never reject. Never re-enter the
  draft stage.
- **A milestone whose contract WAS changed** → the strongest problem this task can find, and still
  a notification: name the clause before and after, verbatim, and send. The two-failed-replan cap
  is the daemon's, derived from the milestone's verdict history; this seat can neither see it nor
  enforce it, and must not try.
</done-contract>

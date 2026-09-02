# 20260902-i-mail-to-departed-asleep-seat-a — mail to departed/asleep seat auto-redirects to leader

kind: issue
component: coord
date: 2026-09-02
commit: 6d1d004651d3a1a945781902fd0745b305aa8748
deployed: yes
pin: NONE

## Observed
Two separate mail-drain defects in `cmd_send` (`ignite/coord/messages.py`), fixed together because
both left an owner-addressed message unread with no path to a reader. Task 111: sending mail to a
DEPARTED seat was accepted with only a stderr warning telling the SENDER to resend to `leader` by
hand — nothing acted on that advice, so an owner deliverable addressed to an empty chair could sit
unread indefinitely. Task 53 (owner ruling `d-53-redirect-to-leader`): mail addressed to
`goal-master` — the one `SUMMONED_SEATS` chair — while it held no live pane had NO drain path at all,
by design (D24: mail is not `goal-master`'s wake term). This once ate the owner's own Slack asks (bus
#33266/#33306, measured 2026-08-20).

## Mechanism
For task 111: the warning printed when `args.to in departed` was purely informational — it told the
sender what to do, but `cmd_send` still completed the send to the departed recipient and stopped.
Nobody read that stderr line as an action item; the message simply sat in a departed seat's inbox.
For task 53: `goal-master` is summoned only by the owner's own action (a goal-channel message or
`@rbtv` tag) — by design it does not wake on ordinary mail. A sender addressing it while it held no
live pane hit no check that redirected the message anywhere; it queued in `goal-master`'s inbox with
no mechanism that would ever read it, since the only thing that reads a summoned chair's inbox is the
chair itself, once summoned.

## Attempts
First attempt at both — checked: the existing departed-seat warning in `cmd_send` (informational only,
confirmed by reading the surrounding code) and `SUMMONED_SEATS`/D24's own design note (mail is
deliberately not the wake term). No earlier attempt at either fix was found.

## Fix
d-53: before the unknown-recipient/departed checks, if `args.to` is a summoned seat (`is_summoned_seat`)
and its roster row is not both `active: yes` AND holding a live tmux pane, `args.to` is reassigned to
`leader` and a hint is printed — so every later gate in `cmd_send` judges the RESOLVED recipient. A
`goal-master` currently summoned (active row + live pane) is still reached directly; the redirect only
fires while asleep. d-111: after the send completes, if the (possibly-redirected) recipient is in
`departed`, the same message body is auto-copied to `leader` as a `note` (never the original `--type`,
since some types like `ask`/`escalation` are sender-restricted and a copy is not the sender re-asking)
via a second `append_message` + `deliver_wakes` call in the same `cmd_send` invocation. `leader` can
never itself be in `departed` (`send_recipients` subtracts `STAFF_SEATS`), so this never
double-copies a message already addressed to leader. Owner-accepted consequence, stated explicitly in
the fix: `leader` now receives some mail that is not strictly its business — not a defect to design
around.

## Consequences
Both fixes land in the SAME `cmd_send` function, ordered so d-53's redirect happens first (before the
unknown-recipient/departed checks) and d-111's auto-copy happens after the send completes — a
message redirected by d-53 to `leader` cannot ALSO trigger d-111's departed-seat copy, since `leader`
is never departed. The seat's own two selftest arms proving each behaviour were NOT committed in this
commit — the file carried roughly 300 lines of sibling seats' uncommitted work at commit time, and the
seat correctly refused to publish them under this message. The orchestrator verified the outcome
independently instead: the d-111 arm landed as a BYSTANDER inside a later, unrelated sibling commit
(`a6b946cc`); the d-53 arm was LOST entirely to a sibling's working-tree clobber. The product code (this
commit, `6d1d0046`) is confirmed safe in HEAD by direct inspection, but the RULED d-53 redirect has
NO selftest pin as of this commit.

## Verification
Red-first in a scratch worktree against clean HEAD (both defects reproduced: mail to a departed seat
sat unread with only a stderr hint; mail to an asleep `goal-master` had no drain path). Green,
same scratch worktree, 6/6 checks after the fix (per the seat's own report). The orchestrator
separately, adversarially confirmed the d-53 product code IS present in `cmd_send` and confirmed it
is UNPINNED (no selftest arm covers it as of this commit). Deployed — `ignite/coord/messages.py`,
branch `ignite/core-daemon`, live on deploy tree `e8524c31`.

## ATTENTION
1. **NEITHER fix has a selftest pin as of this commit.** The two arms the seat wrote and verified
   live were both lost to shared-tree collisions before they could be committed under this message —
   d-111's arm rode along as a bystander in `a6b946cc` (a different commit's message, not
   discoverable by searching for `6d1d0046`), and d-53's arm was overwritten entirely. A future
   change to `cmd_send`'s recipient-resolution order could silently regress either fix with nothing
   to catch it.
2. d-53's redirect fires ONLY while `goal-master` is asleep (no active roster row + live pane) — a
   future change to how "awake" is detected for a summoned chair must keep this check in sync, or a
   genuinely awake `goal-master` will have its mail wrongly redirected away from it.
3. d-111's auto-copy always sends as `--type note`, regardless of the original message's type — a
   future reader of `leader`'s inbox should not assume every `note` there originated as a note; some
   are auto-copies of a departed-seat send that failed to reach its real recipient.
- neither fix has a selftest pin — proof arms lost to shared-tree collisions

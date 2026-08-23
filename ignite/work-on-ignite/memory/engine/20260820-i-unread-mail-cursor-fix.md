# 20260820-i-unread-mail-cursor-fix — Unread mail cursor fix

kind: issue
component: engine
date: 2026-08-20
commit: 2233233a
deployed: yes
pin: engine/probes/probe-reconcile.js (D35 arms)
seeded: true

## Seen
A writer/reader type mismatch made every chair's mail always read "unread".

coord.py wrote a checkin timestamp as a string; reconcile.js read it via `Number(checkin)`, which produced `NaN` — every chair's mail then always read as unread. Per the system-problems digest §4: "caused a 356-sitting, 806M-token burn on 2026-08-20."

## Missed
none recorded in sources beyond the type mismatch itself.

The fix-inventory notes system-problems.md#5 covers this exact checkinOf NaN-cursor bug (D35), but the underlying burn CLASS recurred under a different driver afterward (dead-sittings-diagnosis-2026-08-21.md) — a separate, later fix outside this seat's rows.

## Held
Derive unread mail from a direct timestamp comparison; delete the numeric cursor.

reconcile.js now derives "unread mail" from a direct timestamp comparison (messages after last check-in time), not a numeric cursor — the numeric cursor field is deleted.

## commit
2233233a

## files
ignite/engine/reconcile.js

## deployed
yes

## pin
engine/probes/probe-reconcile.js (D35 arms)

## ATTENTION
- Fixing this bug did NOT end the token-burn class it caused — dead-sittings-diagnosis-2026-08-21.md found the same 806M-token-burn SHAPE recurring under a different driver days later. Don't treat this as closing the whole "watcher burns tokens without progress" problem.
- Writer (coord.py) and reader (reconcile.js) agree on this timestamp's format only by convention, not a shared schema — a future writer-side change to the checkin field silently reopens this exact class of bug.
- fixing this did not end the token-burn class; it recurred under a different driver later
- writer/reader agree on timestamp format only by convention, not schema

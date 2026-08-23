# 20260821-i-cast-spawn-drift-probe-fix — cast-spawn-drift-probe-fix

kind: issue
component: launch-profiles
date: 2026-08-21
commit: 69760b69
deployed: yes
pin: self-pinning (scheduled)
seeded: true

## Seen
`probe-cast-spawn-drift.js` joined its comparison on the wrong key — carrier instead of catalog mode.

D48: this probe was one of 6 red probes bundled into one owner-approved fix batch (decision-review-2026-08-21), alongside F-8's companions and the D-6 wide-cage/append-only-secret-writes direction.

## Missed
None recorded in sources.

## Held
The probe now joins on catalog mode, not carrier.

Commit `69760b69` ("join cast-spawn-drift on catalog mode, not carrier") changed `launch-profiles/probes/probe-cast-spawn-drift.js` (comparison key) and `modules/orchestration.md` (doc note on the correct join key).

## commit
69760b69

## files
ignite/launch-profiles/probes/probe-cast-spawn-drift.js

## deployed
yes

## pin
self-pinning (scheduled) — the probe fix is itself the pin, auto-discovered and in the scheduled probe suite.

## ATTENTION
- This was one of an 8-commit fix batch (69760b69, 0c505934, f00aba41, bb13d3a9, 4d47c796, cfdc49e4, d27c44f4, 3303c80e, plus 92e7156c for the wide-cage/tmpfs direction) approved together under D48 — the other 7 commits touch team-kit, engine, server, bridges, deploy and are filed under those components' own memory, not here.
- If cast/spawn's mode vocabulary changes again, re-verify the join key is still catalog mode — carrier and catalog mode drifted apart once already.
- One of an 8-commit D48 fix batch; the other 7 commits are filed under their own components
- Re-verify join key is catalog mode if cast/spawn mode vocabulary changes again

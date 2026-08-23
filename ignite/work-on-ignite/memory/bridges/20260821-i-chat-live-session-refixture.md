# 20260821-i-chat-live-session-refixture — chat-live-session-refixture

kind: issue
component: bridges
date: 2026-08-21
commit: cfdc49e4
deployed: yes
pin: self-pinning (scheduled)
seeded: true

## Seen
`probe-chat-live-session`'s harness gate arm broke when kimi stopped being a launch-specs harness.

D48 probe-fix batch (owner-approved, 2026-08-21): kimi is no longer a launch-specs harness, so the synthetic resume profile never injected and the arm got `E_UNMAPPED_BINDING` instead of the intended refusal.

## Missed
none recorded in sources.

## Held
Re-fixture the arm under opencode with a resume `{session_ref}` slot, so the refusal still reads as harness-not-live-capable.

Inject the synthetic resume profile under `opencode` (which still has a resume `{session_ref}` slot) instead of kimi, so the arm's assertion — harness-not-live-capable refusal — is exercised the same way it was before kimi's launch-specs status changed.

## commit
cfdc49e4

## files
ignite/bridges/chat/probes/probe-chat-live-session.js

## deployed
yes — rbtv HEAD ac1c08d8, deployed 2026-08-21 18:14:37Z.

## pin
self-pinning (scheduled) — this IS the probe.

## ATTENTION
- The arm's harness choice (`opencode`) is load-bearing on that harness continuing to expose a resume `{session_ref}` slot in its launch-specs — if opencode's launch-specs shape changes, this arm needs re-fixturing the same way kimi's did.

# 20260821-i-chat-live-session-refixture — chat-live-session-refixture

kind: issue
component: bridges
date: 2026-08-21
commit: cfdc49e4
deployed: yes
pin: self-pinning (scheduled)
seeded: true

## Observed
On 2026-08-21 strand B of the decision-review pass, `probe-chat-live-session.js` arm 1 was one of six red probes: the check that a seat cast to a non-claude harness whose profile still has a `resume:` template is refused with `/harness-not-live-capable/` (`redesign-plan/seed/decision-review-2026-08-21.md`). After 699a78fc (2026-08-18, "retire kimi harness"), `eligible()` on that fixture returned `uncastable-seat:E_UNMAPPED_BINDING` instead — the same refusal the neighboring "pair no profile carries" check already owns. The probe is scheduled and self-pinning; the later same-day deploy (ac1c08d8, 18:14:37Z) put HEAD and the deployed tree on the same commit.

## Mechanism
`scratchWorkspace` copies the live `spawn-profiles.yaml` and regex-appends a synthetic model under a harness key, then recasts the scratch seat as that pair (`NONCLAUDE_CAST`). The synthetic is load-bearing: every shipped non-claude spec lacks `resume:`, so `live-sessions.js#eligible` would stop at `profile-has-no-resume-template` and the harness gate (`LIVE_HARNESSES` is only `claude`) would never be the thing that refuses. c69e1ab2 (2026-08-12, 7.787) had already moved that inject off the old flat `profiles:` slot (just before `tools:`, now uncastable `jobs:`) into the then-existing `kimi:` block, with `NONCLAUDE_CAST` pinned to `harness: kimi` / `model: probe-kimi-model`. 699a78fc deleted the `kimi:` launch-specs key (kimi models ride opencode) and did not touch this file. `^(  kimi:\n)` stopped matching, the synthetic model was never written, and `launchSpecForSeat` threw `E_UNMAPPED_BINDING`. `eligible()` catches resolver throws as `uncastable-seat:${err.code}` and never reaches the harness set.

## Attempts
First attempt held — checked: `git log` on this probe (df65147e 2026-08-10 created the warm-path probe; 21f9dd1e 2026-08-11 drove gates through the seat's cast after D2; c69e1ab2 re-keyed the inject for 7.787 and that re-fixture held; 4f0e99b0 2026-08-17 dropped an unrelated faster-second-turn check; 699a78fc retired kimi without a follow-up here). map.csv names no missed-trials source. The decision-review note records detection, not a prior patch.

## Fix
cfdc49e4 (2026-08-21 16:09:53Z), one of the six D48-approved red-probe fixes, retargeted `NONCLAUDE_CAST` to `harness: opencode` / `model: probe-opencode-live` and the inject regex to `^(  opencode:\n)`, appending `probe-opencode-live` inside the existing `opencode:` block with `resume.argv` carrying `--session {session_ref}`. Opencode was chosen because it still exposes that resume slot and is already where kimi models live after 699a78fc. Rejected: a second top-level harness key (duplicate YAML mapping is a parse error — the same reason c69e1ab2 injected inside `kimi:`); a shipped non-claude spec (no `resume:`, vacuous); restoring `kimi:` (harness retired).

## Consequences
The commit is eight insertions and eight deletions in this probe only. `git log --since=2026-08-21` on the file is cfdc49e4 alone — no revert, no follow-up. Sibling D48 probe fixes (69760b69 and the rest of that eight-commit batch) live under their own components; `launch-profiles/20260821-i-cast-spawn-drift-probe-fix.md` names this hash in that batch list.

## Verification
The corrected arm is the pin (`self-pinning (scheduled)` in the D48 fix-inventory row: the six probe-fix commits are themselves the probes). No separate selftest was added. Deployed yes with the rest of the D48 batch at rbtv HEAD ac1c08d8, 2026-08-21 18:14:37Z. No post-fix probe-suite run log was located.

## ATTENTION
- The arm's harness is load-bearing on `opencode` still exposing a `resume {session_ref}` slot. If that shape drops, `eligible()` stops at `profile-has-no-resume-template` and the harness-gate assertion goes vacuous the same way a shipped non-claude spec would.
- The inject is a silent regex (`^(  opencode:\n)`). Rename or remove that key and the synthetic model never lands; arm 1 then fails as `uncastable-seat:E_UNMAPPED_BINDING` — the wrong refusal — instead of erroring at fixture build. The inject site has already had to move twice: off the retired flat `profiles:`/`tools:` slot in c69e1ab2, then off retired `kimi:` here, because 699a78fc did not carry this file.

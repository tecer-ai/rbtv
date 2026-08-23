# 20260821-c-caged-identity-corroboration — caged-identity-corroboration

kind: creation
component: team-kit
date: 2026-08-21
commit: 2138307d,70eb50de,23de241f,70328baa,b6c64a25
deployed: yes
pin: team-kit/test_d45_staff_claim.py (D43/D45/F-8-annotated, STANDALONE not scheduled)
components: server
seeded: true

## What it is
F-6/D43/D45/F-8: the launch identity gate corroborates a paneless leader via a kernel-observable session id, not a name lookup.

A caged seat can no longer act `--as` any staff chair by asserting a name the roster happens to contain.

## Why
D42 built the crashed-row door (`launch --only <seat> --rerun <leader-anchor>`), but the identity gate corroborated a caller's `--as leader` claim only by matching a tmux pane id against the roster — and a caged leader has no pane, so `--rerun` was unreachable from the daemon lane at all. D43 added a paneless corroboration lane reading the caller's own carrier unit out of `/proc/self/cgroup`; D45 extended `_staff_claim_gate` to admit a claim the D43 lane had corroborated; F-8 then closed the remaining hole where a caged seat could still assert `--as` ANY staff chair on every command except launch.

## How to use & where wired
`ignite/team-kit/coord.py` (`carrier_self_session`, `_staff_claim_gate`, the paneless corroboration lane); `ignite/server/spawn/bwrap.js` (drops `--unshare-cgroup` so a caged process can read its own carrier unit name from `/proc/self/cgroup`). Commits: `2138307d` (F-6 fix, owner ruling option a — cage stops hiding cgroup, paneless check-in registers a provable session id, D46), `70eb50de` (D45 — a corroborated staff claim is admitted), `23de241f` (D43 paneless launch identity + D44 stuck-becomes-a-brake), `70328baa` (F-8 — refuse uncorroborated `--as` claims from inside a cage), `b6c64a25` (D49 — secret-add, mediated append-only env write for masters, same-day companion).

## commit
2138307d,70eb50de,23de241f,70328baa,b6c64a25

## deployed
yes

## pin
team-kit/test_d45_staff_claim.py (D43/D45/F-8-annotated) — STANDALONE pytest file, NOT under a probes/ folder, NOT discovered by probe-suite.js.

## ATTENTION
- The pin is UNSCHEDULED: `test_d45_staff_claim.py` exists and is correct but never runs automatically (loose-ends.md F-9 remainder). A regression here will not be caught by the scheduled probe suite — run it by hand after touching identity-gate code.
- D43's own docstring (`coord.py:16810-16813`) asserts `session-id` and `native-session-id` are always the same string — measured false for 10 of 403 rows (all in the paneless lane this fix serves). Correct or delete that docstring in any future change, or the next reader re-derives the same wrong premise.
- Any re-test of this door must run INSIDE a real bwrap cage on a unit minted by the real carrier — self-exec'd fixtures that name their own unit satisfy the check by construction and prove nothing (this is exactly how D43/D45 shipped "verified" and were still refused in production before this fix).
- `--unshare-cgroup` was dropped deliberately as part of this fix (was D3/D8 hardening) — do not silently re-add it without re-opening this defect.
- Pin is UNSCHEDULED; run test_d45_staff_claim.py by hand after touching identity-gate code
- D43 docstring wrongly claims session-id == native-session-id always; false for paneless lane
- Re-test must run inside a real bwrap cage on a real carrier unit or it proves nothing

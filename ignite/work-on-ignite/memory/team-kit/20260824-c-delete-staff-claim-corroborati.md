# 20260824-c-delete-staff-claim-corroborati — delete staff-claim corroboration gate

kind: change
component: team-kit
date: 2026-08-24
commit: 855f4290
deployed: yes
pin: NONE

## Motivation

Redesign batch D19 (authority/grant machinery) [T2-R10, D24, F-simplicity-7]: the baseline rules
that exactly two identity gates survive coord.py's rewrite — the cage envelope, and the send-time
owner-ask refusal (W8 arm 3, D-7). Every other per-verb authority gate in this batch is being
deleted across sibling commits (2c5e20e7 credential-pierce role, 35bdffd4 widen-cage, 7b978663
rule-disposition verb, d067928a the whole per-verb role-gate layer, 149faf9a --force/gate_forced
override machinery). `_staff_claim_gate` (W3/D-2, built 2026-08-20/21 across D43/D45/D46/F-8 — see
`20260821-c-caged-identity-corroboration.md`) is the one this entry closes: the second gate that
stood inside `resolve_agent` and refused an `--as <staff-chair>` claim unless the caller's actual
identity corroborated it. The ruling reclassifies a mismatched `--as` as an ordinary input error,
not a security refusal — this entry is that reclassification, not a replacement mechanism.

## Design

`resolve_agent` used to do two things: resolve who is calling, and (for a claim naming a STAFF_SEAT
— `leader`/`consultant`) refuse the claim unless the caller's actual, corroborated identity was in
`STAFF_CLAIM_IDENTITIES` (`channel-master`, `goal-master`, `console-master`) or was itself proven
via `carrier_corroborated_seat` (a daemon-cgroup-to-roster lookup). Deleted the refusal, kept the
resolution: `--as <name>` is now trusted as an ordinary parameter with no extra corroboration step,
exactly like every other `--as` claim already was for non-staff seats. The pane-vs-claim
contradiction check a few lines below (`registered != claimed` → refuse unless `--force`) is a
DIFFERENT, unrelated gate — general to any `--as` usage, not staff-specific — and was left alone.

Considered keeping a lighter validation (e.g. still checking the claimed name is a recognized
seat), but `resolve_agent` already returns a bare string with no existence check for any other
claimed identity, so adding one here only for staff names would be new, asymmetric behavior nobody
asked for. Went with the minimal, conservative shape: delete the corroboration/refusal layer,
change nothing else.

`carrier_corroborated_seat` (the shared corroboration helper `_staff_claim_gate` called) was NOT
deleted — it has two other legitimate callers unrelated to the staff-claim refusal:
`asserted_launch_claim` (F17, the surviving `launch --rerun` paneless-corroboration bound) and
`_secret_add_authority` (the `secret-add` command's own identity ladder). Only the call from
`_staff_claim_gate` is gone, because `_staff_claim_gate` itself is gone.

`STAFF_CLAIM_IDENTITIES` had exactly one purpose — the corroboration admission set — and no other
reader in the file, so it was deleted outright (not just unhooked). Confirmed distinct from
`STAFF_SEATS` (`leader`, `consultant`, subsystem-11 territory) and `STAFF_CHAIRS`/`consultant`
machinery, which this change does not touch.

## How it works

`resolve_agent` now walks: `--as NAME` (trusted) > `COORD_AGENT` env > the calling pane's
registered roster row > the daemon-exec lane (F16) — same ladder as before, minus the staff-claim
detour. A caller asserting `--as leader` from anywhere (uncaged console, caged cgroup with no
roster row, another seat's identity) is admitted exactly as any other `--as` claim is: no
corroboration, no refusal, no audit-log announcement (the `console-override` print line is gone
with the function that emitted it).

## Consequences

Deleted: `_staff_claim_gate` (the whole function, ~90 lines), its ~35-line W3 explanatory comment
block, `STAFF_CLAIM_IDENTITIES`, `CONSOLE_OVERRIDE_MARKER` (only consumer was the deleted print),
the call site in `resolve_agent`, and `test_d45_staff_claim.py` (210 lines, the dedicated D45/F-8
regression fixture — its entire subject is gone). Updated two comments that described the gate as
live: the `SUMMONED_SEATS` comment (`goal-master stays in STAFF_CLAIM_IDENTITIES` → `stays out of
STAFF_SEATS`) and `carrier_corroborated_seat`'s own docstring (`ONE CORROBORATION, TWO GATES` →
`SHARED CALLERS`, naming the two survivors and noting the deleted third).

Also deleted one selftest arm: `_selftest_checks` W8 arm 1 (adv, C79), which asserted a caged,
off-pane, non-leader seat claiming `--as leader` was refused at the identity door. Kept ONE line
from that arm — the "control" send that legitimately lands an escalation — because W8 arm 2 (the
at-most-once dedup check) needs one escalation already open on the log to dedup against; deleting
it wholesale would have starved arm 2's fixture.

Baseline selftest count drops from 1064 ok to 1063 ok (one check removed, no new failures) — `PASS
0 failure(s)` before and after.

No downstream break found: grepped `_staff_claim_gate`, `STAFF_CLAIM_IDENTITIES`,
`carrier_corroborated_seat` across `ignite/` and `meta/` post-edit — only surviving hits are one
explanatory comment I wrote and archival memory-entry citations (this component's own build log,
exempt by design — memory here is the closed/historical side, never live-behavior prose).
`protocol.md`, `roles.md`, `communication.md`, `team-kit.md` carried no prose describing the
corroboration refusal, so no doc update was needed there.

## Verification

`test_d45_staff_claim.py` run BEFORE the edit: `D45 FIXTURE: PASS` (all positive/negative arms
green against the live gate). Run AFTER the edit: the `send`-path negative arms that used to assert
REFUSAL now read `[FAIL]` (the refusal no longer fires), and the script crashes with
`AttributeError: module 'coord' has no attribute 'STAFF_CLAIM_IDENTITIES'` at its own line 140 —
direct evidence the corroboration mechanism and its admission-set constant are both gone, not
renamed. File then deleted (`git rm`).

`python3 -B -c "import py_compile; py_compile.compile('ignite/team-kit/coord.py', doraise=True)"`
clean. Full `coord.py selftest`: PASS, 0 failures, 1063 ok (baseline 1064, minus the one deleted
arm). Committed `855f4290` on `ignite/core-redesign` in the `rbtv-redesign` worktree; `coord.py` is
live on commit (no JS/deploy step for this file).

## ATTENTION

- `carrier_corroborated_seat` is still live and still shared — it now has exactly two callers
  (`asserted_launch_claim`/F17 for `launch --rerun`, and `_secret_add_authority` for `secret-add`).
  Do not assume it is dead code because its third caller (this entry's subject) is gone; deleting it
  would break both survivors.
- The pane-vs-claim contradiction check inside `resolve_agent` (`registered and registered !=
  claimed and not getattr(args, "force", False)`) was deliberately left untouched — it is a
  different, non-staff-specific gate. Note `--force` was already deleted as a flag in 149faf9a (a
  sibling commit), so `getattr(args, "force", False)` now always reads `False` there; that is a
  pre-existing condition from the prior subsystem's work, not something this change introduced or
  is responsible for resolving.
- `STAFF_CLAIM_IDENTITIES` is gone but `STAFF_SEATS` (`leader`, `consultant`) and
  `SECRET_ADD_MASTERS` (`goal-master`, `channel-master`, `console-master` — a THIRD, separately
  defined tuple with the same string values as the deleted `STAFF_CLAIM_IDENTITIES`, local to
  `_secret_add_authority`) both remain live. Do not conflate the three name lists when reading
  nearby code — they now look more alike (same-ish membership) than before, since the deleted one
  is no longer there to contrast against.
- carrier_corroborated_seat stays live for asserted_launch_claim/F17 and _secret_add_authority — do not delete it as dead code

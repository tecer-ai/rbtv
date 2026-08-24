# 20260824-c-delete-gate-forced-gate-flags — delete gate_forced/GATE_FLAGS override machinery

kind: change
component: team-kit
date: 2026-08-24
deployed: no
pin: NONE
components: jobs

## Motivation
Subsystem 6 of an 11-part deletion batch [T2-R10, D24, F-simplicity-7]: exactly two refusal
points survive in coord.py (the cage envelope; the send-time refusal of an owner-ask from a
non-designated seat), and neither may be flag-overridable. Subsystem 5 (`d067928a`) deleted the
per-verb ROLE gate (`is_leader`/`is_authorized_launcher`/etc.) but deliberately left
`gate_forced`/`GATE_FLAGS`/`--force`/`--force-memory` for this subsystem, because the mapping's
sole purpose — stopping `--force` from ever also carrying the MEMORY gate — depended on a ROLE
gate that no longer exists to be recombined with.

## Design
`gate_forced`/`GATE_FLAGS`/`cmd_gates` (the `coordinate gates` verb) are deleted whole: the
invariant they enforced (no flag ever carries both role and memory) is now structurally
impossible, since there is only one gate (the memory/RAM floor) and one flag (`--force-memory`)
left. `--force-memory` itself, and the memory-floor check it overrides (`launch_gates` /
`memory_gate`), are KEPT — the RAM-capacity gate is not one of the two authority gates this
ruling names, and is a resource-safety mechanism, not an authority mechanism. `--force` is also
KEPT on every verb: a full audit of every raw `getattr(args, "force", False)` read in coord.py
(13 sites, outside `gate_forced`) found each protects an UNRELATED, still-live, non-authority
check — identity mismatch (`resolve_agent`), a zombie double-launch guard (`checkin`), window
drift (`launch_seat`), a relay-to-human refusal (`close-seat`), roster-still-active
(`kill-pane`/`relaunch-pane`), shell-substitution (`send`/`verdict`), and several input/state
validations (`send`, `remove-from-group`, `refuse_special_case_members`, `check_bindings`). None
of these were role-gate residue; all are kept untouched.

## How it works
`launch_gates` now reads `mem_forced = getattr(args, "force_memory", False)` directly — no
indirection layer. `jobs/recover-room.py`'s `gate_split_violation()` (which asserted the deleted
mapping via `coord.py gates --json` before every unattended firing) is deleted along with its
call site; the daemon-fired recovery still passes `--force --force-memory` on every firing
(load-neutral memory override + silencing the unrelated window-drift/identity checks), but no
longer verifies a "split" that cannot be violated anymore. `probe-defect-fix.py`'s S-6(a)
mutation-testing leg (which mutated `GATE_FLAGS` and asserted recover-room.py refused) is deleted
along with its now-dead `copy_local_siblings`/`RECOVER`/`ast`/`shutil`/`json` support code.

## Consequences
Deleted: `gate_forced()`, `GATE_FLAGS`, `cmd_gates()`, the `coordinate gates` verb (+ its
HELP_EPILOG line), 2 S-6(a) selftest checks in coord.py, the whole S-6(a) probe leg in
`probe-defect-fix.py`, `gate_split_violation()` in `recover-room.py`. Updated (not deleted):
`memory_gate()`'s refusal wording, `launch_gates()`'s docstring, 4 `--force`/`--force-memory`
argparse help strings, `add_identity_flags`'s help text, one selftest check (`O3-3`) that
additionally asserted `GATE_FLAGS` alongside its still-valid behavioural assertion. No behavior
change to any verb's actual refusal/override logic — only the now-vestigial split-verification
scaffolding is gone.

## Verification
`python3 -B -c "import py_compile; ..."` clean on all 3 touched files. Full selftest:
`python3 -B ignite/team-kit/coord.py selftest` → PASS, 1064 ok (was 1066 pre-change; -2 matches
the 2 deleted S-6(a) checks that referenced the removed symbols by name). Deployed: no (commit
only in this worktree at authoring time).

## ATTENTION
1. `--force` and `--force-memory` remain LIVE, WORKING flags on many verbs — do not read their
   continued presence in the grep floor as leftover role-gate residue; each surviving use was
   individually verified against a distinct, non-authority check.
2. If a future change deletes the memory/RAM-floor gate too, `jobs/recover-room.py`'s
   `launch_argv()`/`disclose_overrides()` need a matching edit (currently document + pass
   `--force-memory` for a load-neutral recovery override).
- --force/--force-memory stay live on many verbs for unrelated non-authority checks; do not treat their presence as role-gate residue

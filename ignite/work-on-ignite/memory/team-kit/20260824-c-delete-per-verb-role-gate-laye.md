# 20260824-c-delete-per-verb-role-gate-laye — delete per-verb role gate layer

kind: change
component: team-kit
date: 2026-08-24
commit: PENDING
deployed: no
pin: NONE

## Motivation
D19 (redesign ruling [T2-R10, D24, F-simplicity-7]): the per-verb role-gate machinery is
superseded — coord.py now enforces exactly two refusal points, the cage envelope (fixed at plan
time, never widened at runtime) and the send-time refusal of an owner-ask from a non-designated
seat. `is_leader`, `is_leader_or_closer`, `is_authorized_launcher` (the three predicates that used
to decide "who may run this verb") and the `role_verdict()`/`gate()`/`launch_gates()` mechanism
that enforced them implemented exactly the superseded per-verb role model and had to go with it.

## Design
Full deletion of the role-CHECK, not a stub or a flag-gated bypass: `is_leader`,
`is_leader_or_closer`, `is_authorized_launcher`, `gate_role_names`, `gate_roles_help`,
`gate_roles_desc` (the renderers that turned a predicate into a gated command's `-h` parenthetical
or refusal text — dead the moment their only callers, the three predicates, were gone), and
`role_verdict()` (the role-verdict builder `gate()`/`launch_gates()` both called) are deleted
whole, along with the refusal-message constants that existed only to feed `role_verdict`
(`ROLE_CASE_DEFAULT`, `CLOSE_OTHER_CASE`, `CLOSE_OTHER_REMEDY`, `ROLE_CASE_SELF`,
`ROLE_REMEDY_SELF`). `gate()` and `launch_gates()` themselves are KEPT — not deleted — because
several call sites depend on the CALLER IDENTITY they resolve for non-gating purposes (an
authorization record's "authorized by", a self-act warning, a `ruled-by` stamp): `gate()` is now a
thin wrapper over `resolve_agent(args, required=False)`, and `launch_gates()` now evaluates the
MEMORY gate alone (unchanged logic, `budget_mod.floor_source` + `memory_gate`), dropping every
role-verdict computation, its "role gate: PASS/REFUSED" report line, and the two-flag "neither
carries the other" refusal shape (now a single-gate refusal). `REFUSAL_LAYERS` and
`ROLE_GATE_LAYER_NOTE` are KEPT — `_secret_add_authority` (D49's `secret-add` master-identity
check, a hand-rolled gate that never used `gate()`/`role_verdict()`) still emits a `"role gate"`
layer refusal independently and was explicitly out of this task's scope.

`STAFF_SEATS`/`STAFF_CHAIRS`, `gate_forced`/`GATE_FLAGS`/`--force`, `_staff_claim_gate`/
`STAFF_CLAIM_IDENTITIES`, and `is_leader_or_closer`'s non-gating uses (there were none found —
every one of its call sites was a `gate()`/`launch_gates()` role-check argument) were confirmed
untouched by grep before editing and left exactly as they stood.

## How it works
Every verb previously gated by one of the three deleted predicates — `finish-goal`,
`advance-state`, `owner`, `add-to-group`, `remove-from-group`, `surface-refusal`, `rule-guard`,
`launch`, `close`, `close-seat`, `panel`, `reap --go`, `kill-pane`, `terminate-pid`,
`relaunch-pane` — is now callable by any resolved identity, `""` (unresolvable) included. Two
verbs that carried an INLINE lambda predicate through the same `gate()` mechanism rather than a
named function (`owner`: `lambda who: who in ("leader", "")`; `rule-guard`:
`lambda name: name == seat`) lost their role check too, because the check lived in `gate()`
itself, not in the predicate object — deleting the mechanism's role-check body affected every
caller uniformly, named-predicate or inline-lambda alike.

## Consequences
- Every call site that passed `allow`/`allowed_desc`/`target`/`self_legal`/`remedy`/`case` to
  `gate()`/`launch_gates()` was rewritten to the two-argument form (`gate(args, "<verb>")` or
  `launch_gates(args, "<verb>", n_seats)`); `role_desc` local variables that existed only to build
  the deleted refusal text were removed at each site.
- `relaunch-pane`'s `-h` text (`gate_roles_help(is_leader_or_closer)` → `(leader/closer-*) Relaunch
  a seat's harness…`) lost its derived role parenthetical; the surrounding prose about the
  chief-of-staff (a RETIRED role, unrelated to this deletion) was left untouched.
- A large selftest surface tested role-gate refusal behavior end to end and had to be deleted or
  rewritten: the whole `s12-02` self/other-threading block, `s12-04`'s ignite-daemon-widening
  block, `s12-12`'s chief-of-staff-off-kill-pane/relaunch-pane block, and the `C5.2 GD-*`
  `gate_roles_desc`-rendering block are deleted wholesale (their subject no longer exists); `S1-h`
  and `L-a` (general "every refusal names its layer" / "every layer token is one of the five"
  hygiene checks, unrelated to role gates specifically) were KEPT. Several OTHER role-gate rows
  scattered outside the s12-* blocks (`kill-pane`'s, `terminate-pid`'s arm B, `relaunch-pane`'s,
  `remove-from-group`'s, `reap --go`'s, one `T6` block covering `launch`/`panel`/`add-to-group`/
  `close-seat`/`owner`, and two F17/`#230` rows) were found only by RUNNING the selftest — each
  used a non-privileged caller (`zeta`/`beta`/`watcher`) expecting a role refusal that no longer
  fires; several of these calls are NOT dry-run and would have PERFORMED the act for real (killed
  a pane, removed a group member, reaped a debt) as a side effect of merely proving the refusal is
  gone, corrupting fixture state for every check behind them in the same block — those call sites
  were deleted outright rather than merely having their assertion patched.
- `#230`'s two-gate ("BOTH verdicts, neither flag carries the other") block is now a
  memory-gate-only block; the row that used to prove `--force` alone still gets refused by memory
  (because the role override no longer hides the memory verdict) now proves the same refusal for a
  different reason (there is no role override left to hide anything behind).

## Verification
`python3 -B -c "import py_compile; py_compile.compile('ignite/team-kit/coord.py', doraise=True)"`
— clean. `python3 -B ignite/team-kit/coord.py selftest` — iterated from the pre-existing 1105
checks down through several rounds of fixture-corruption cascades (42 failures on the first full
run after the mechanical deletion, then 2, then 0) to a clean `selftest: PASS (0 failure(s))` on
the final run. Grep floor: `git grep -n -E 'is_leader\b'`, `git grep -n -F 'is_leader_or_closer'`,
`git grep -n -F 'is_authorized_launcher'` against `ignite meta` — zero definitions or call sites;
remaining hits are all past-tense/historical prose (this entry's own future citations, and a few
comments explaining what the deleted mechanism used to do). `gate_roles_desc`/`gate_role_names`/
`gate_roles_help` — zero remaining callers; `launch_gates` — 3 call sites (`launch`, `close`,
`relaunch-pane`), all rewritten to the 3-argument form.

## ATTENTION
1. `meta/leader/prompts/leader.md` and other cross-component docs were NOT checked in this pass
   (out of the `team-kit` component's scope) — if they instruct the leader chair that certain
   verbs are "leader-only" as an ENFORCED rule rather than a convention, that is now stale the same
   way the earlier `widen-cage` deletion left `leader.md` stale (see
   `20260824-c-delete-widen-cage-verb.md`'s ATTENTION #1).
2. `protocol.md`/`roles.md` were updated to state the two surviving refusal points and reframe
   "leader only" labels as a role CONVENTION, not a coord.py-enforced rule — but the per-command
   `# leader only` inline comments in `protocol.md`'s command-reference block were left as-is
   (covered by one blanket clarifying sentence immediately below that block) rather than rewritten
   line by line; a reader skimming only the command list without reading past it could still
   misread them as enforced.
3. GATE_FLAGS is untouched (`--force`→`("role",)`, `--force-memory`→`("memory",)`) per this task's
   explicit boundary — `--force` therefore still nominally "carries the role gate" in the flag map
   even though no code path checks that binding anymore. Whoever eventually retires `--force`
   itself (a different subsystem, per the redesign plan) should grep this file for
   `GATE_FLAGS\["--force"\]` and `gate_forced\(.*"role"\)` — the latter now has ZERO live callers
   (only `gate_forced(..., "memory")` is still called, inside `launch_gates`), which is itself a
   signal the `"role"` half of GATE_FLAGS may be dead weight worth a future look.
4. `_secret_add_authority` (D49's `secret-add` master-identity gate) is a SEPARATE, hand-rolled
   authority check that never went through `gate()`/`role_verdict()` — it was explicitly left
   untouched as out of this task's scope, and it still refuses with a `"role gate"` layer token.
   Do not assume "role gate: gone from coord.py" includes it.

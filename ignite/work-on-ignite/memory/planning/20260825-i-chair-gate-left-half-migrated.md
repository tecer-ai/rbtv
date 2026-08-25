# 20260825-i-chair-gate-left-half-migrated — Chair gate left half-migrated off awaiting-close

kind: issue
component: planning
date: 2026-08-25
commit: e8f4a487
deployed: no
pin: NONE
components: coord,state-store

## Observed

`materialize-seats.py` aborted with `NameError: name 'debts' is not defined` at
`mint_staff_chairs`, in the SUMMONED-chair loop, on any goal that declares a summoned chair
(today `goal-master`) the taskforce does not yet carry — that is every `--root --workflow`
materialize with a goal-master casting sheet, the invocation the creation job and a console
materialize both take. Found 2026-08-25 in the redesign worktree (branch `ignite/core-redesign`)
by the orchestrator's residue sweep, not by a user, because the arm had no selftest row. A second
symptom rode with it: the dag-05 acceptance row `SC-1 setup` read
`coordination/awaiting-close.json` and got `{}`, so it FAILED. Both were invisible until
`37fdba78` repaired the stale `coord.py` path that had been aborting the suite before dag-05 ran
at all. Deployed vs HEAD: neither defect is deployed — the live `ignite/core-daemon` tree is not
this branch, and the summoned-chair NameError would have fired there on the next goal birth.

## Mechanism

ONE gate existed as TWO copies, and only one was migrated.

Both chair loops read `debts`, the result of a single `load_awaiting(package)` call over
`coordination/awaiting-close.json`. spec-state-store §4.1 Row A deleted that file together with
the second ending writer; `coord/closeout.py`, `coord/ready.py` and `coord/checkout.py` each
carry a comment recording it as gone and `load_awaiting` as answering a permanent `{}`. The
retarget onto the ONE ending store (`ending_store.get_current_ending`) was applied to the STAFF
loop — the shared `debts` lookup became a per-seat store call — and the `load_awaiting` line that
produced `debts` went away with it. The SUMMONED loop, thirty lines further down and reading the
same variable, was not swept. Python resolves a module global at call time, so the file compiled
and every arm that never reached a summoned chair kept passing.

The selftest could not catch it. Its only coverage of this gate (SM-10/SM-11/SM-12) built its
fixture by writing `awaiting-close.json` — a file nothing reads any more — so all three arms
exercised the staff loop against a surface that no longer participates, and none of them touched
the summoned loop at all.

## Attempts

First attempt held — checked: `git log` over `materialize-seats.py` and the three ending-store
migration entries (`20260824-i-attest-exit-becomes-the-superv`, which records
`awaiting-close.json` going away with its writer `awaiting_path` and leaving stub readers and
dead callers; `20260824-c-kit-endings-via-store-client`; `20260825-c-the-selftest-speaks-the-ending`,
which did this same retarget for the KIT's selftest). No earlier trial of the summoned arm exists —
it was never migrated, never reverted, and never reported.

## Fix

One reader, called by both loops: `_chair_current_ending(package, seat)` returns the standing
ending or None, and `_chair_ending_warning(kind, seat, ending)` composes the one skip message.
The duplication is what the fix removes; replacing `debts.get(seat)` with a second copy of the
store call would have left the same defect one migration away from firing again.

The spec reading the fix turns on: §4.1 Row A kills the debt LEDGER and its settlement
vocabulary — `close-seat` / `reap` discharging an entry — and spec-component-map §3 gives the
`AWAITING-CLOSE debt` banner no landing module. So the ledger is dead. But the gate's QUESTION
survives, retargeted: does a current ending already stand under this chair's NAME, which a chair
minted over it would inherit as its own and be born terminal by? That is exactly what the staff
arm had already been rewritten to ask. DELETE-the-gate was therefore rejected: it would have
removed a guard the same spec's migration had just kept on the sibling path, and reopened the
2026-08-14 born-DONE chair on `meet-transcript-summarizer`.

Two smaller design points. An unreachable store still reads as "no ending" — the contract the
deleted ledger carried — because a fixture or foreign catalog with no `state-store` beside it
must materialize exactly as it did before, and a gate that refused whenever it could not answer
would block every one of them. And the warning names the ending and its stamp but NO verb that
settles it, because §4.1 deleted that verb with the ledger; telling a reader to run `close-seat`
would send them at a command that no longer discharges anything.

## Consequences

The selftest changed in the same commit, three ways. `SC-1 setup` reads the ending back through
the store instead of the deleted JSON. `SM-10` is restated in the store's vocabulary. `SM-11`
used to discriminate a DEAD debt from a LIVE one by pid and pane; an ending carries neither, and
liveness is the supervisor registry's fact rather than an ending's [T4-R8], so that arm was
retargeted at a genuinely equivalent discrimination — a NON-`done` ending (`incomplete`, armed)
must block the mint too, or a guard narrowed to `done` would mint a chair born mid-relaunch.
`SM-12`'s control now uses a FRESH fixture instead of clearing the ledger, because the store is
append-only by design and a minter (or a suite) that deleted endings would be the second writer
the gate's own rule forbids. NEW arm `SM-10b` covers the summoned chair and joins the
`staff-mint-debt` rollup row, which now reads red 3/3.

Nothing else changed: the mint's behaviour on a goal with an empty store is byte-identical, and
no new refusal was introduced — both branches still SKIP and WARN, because a warning is read and
an absorbing ending is not.

## Verification

`materialize-seats.py --selftest` reaches FULL completion for the first time on this branch:
exit 0, `PASS — 0 failed check(s), 0 failed row(s) of 62`, 347 `ok` rows (up from 320 rows and an
abort). `staff-mint-debt` rollup row: `PASS green 1/1 red 3/3`. `py_compile` clean.

Non-vacuity proven by mutation on a full scratch copy of `ignite/` + `meta/`: disabling the
summoned loop's gate (`ending = None`) reds exactly `SM-10b red` and its rollup row and nothing
else — `FAIL — 1 failed check(s), 1 failed row(s) of 62`. Commit `e8f4a487`. Not deployed —
worktree only, ahead of cutover.

## ATTENTION

- The standing-ending gate is ONE helper for BOTH chair loops on purpose. Inlining the store call
  back into either loop recreates the exact two-copy shape that let §4.1's retarget migrate one
  and leave the other on a deleted surface.
- `_chair_current_ending` swallows `EndingStoreError` to None deliberately. A fixture or foreign
  catalog with no `state-store` beside it must still materialize; turning that into a refusal
  blocks every hermetic test package in the suite.
- The gate is keyed on an ending STANDING, never on WHICH ending. Narrowing it to `done` mints a
  chair over an `armed incomplete` row and the chair is born mid-relaunch — SM-11 is that arm.
- Never build a chair-gate fixture by writing `coordination/awaiting-close.json`. The file has no
  reader; a suite that writes it tests nothing and reads as coverage. Stamp through
  `ending_store.stamp_seat_declare` / `stamp_system`, and get a clean goal by building a fresh
  fixture rather than deleting rows.
- The rollup key `staff-mint-debt` predates §4.1 and still says "debt". It is a rollup key
  readers already know, not a claim about a live surface; renaming it silently breaks anyone
  grepping the acceptance table.
- one helper for both chair loops — inlining it recreates the two-copy shape that shipped this

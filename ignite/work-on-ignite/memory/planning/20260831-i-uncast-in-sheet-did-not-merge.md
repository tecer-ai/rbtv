# 20260831-i-uncast-in-sheet-did-not-merge — uncast_in_sheet did not merge sheet defaults

kind: issue
component: planning
date: 2026-08-31
commit: 2e533bb1
deployed: no
pin: ignite/planning/probes/probe-planning-path-b-materialize.py
register-id: G-leader-0828-2214-2

## Observed
`wrapper.py#uncast_in_sheet` did not merge the casting sheet's `defaults` block.

On `meet-transcript-summarizer-planning`, the plan's `bindings.json` declared `harness` once, inside `defaults`, and left every seat's own entry empty; `uncast_in_sheet` returned all twelve seat names as missing, so `approve` refused `atomic-core-refusal/uncast-in-sheet` after the owner had already approved. `materialize-seats.py#effective_binding` and `load_bindings`, the sibling readers of the same file, DID merge defaults and reported the same sheet `ok: true` — two readers of one casting sheet disagreeing about whether it was cast. Manually patched at the time by writing `harness: claude` onto every seat in `planning/current/bindings.json`. Filed `G-plan-reviewer-0828-2203-2` on the goal's own `issues.md`; re-filed to the ignite-engine register as `G-leader-0828-2214-2` because the plan-reviewer's own cage refused a direct write. Task 160 (`build-ignite-tasks.md` / `redesign-continue-1`).

## Mechanism
The gate never read the field the loader downstream treats as legal.

`uncast_in_sheet` (`ignite/planning/wrapper.py:33-62` pre-fix) read `entry = seats.get(name) or {}` and checked `entry["harness"]`/`entry["model"]` directly — nothing in the function ever looked at `sheet["defaults"]`. `materialize-seats.py#load_bindings` (line 1278: `data.get("defaults", {})`) and `#effective_binding` (lines 1353-1358: `merged = dict(bindings["defaults"]); merged.update(bindings["seats"][seat])`) establish the contract for what a seat's binding IS: `defaults ∪ per-seat entry`. `uncast_in_sheet` is the gate that runs before that same merge is ever read, so any sheet that puts harness/model only in `defaults` — a legal shape by the loader's own contract — reads every seat as uncast at the gate while the loader downstream reads it fully cast.

## Attempts
First attempt held — checked `git log -S uncast_in_sheet -- ignite/planning/wrapper.py` and the function's own docstring ("Cast = harness and model both non-empty"); nothing before this fix ever merged defaults in this function. The manual bindings.json patch on the live goal masked the symptom for that one goal without touching the function, so it was not a prior fix attempt of the underlying defect — the same shape recurs on the next plan that uses `defaults` for harness/model.

## Fix
`uncast_in_sheet` now performs the same merge `effective_binding` does.

It reads `defaults = (sheet or {}).get("defaults") or {}` (refusing `uncast-in-sheet` if `defaults` is present but not a mapping, mirroring `load_bindings`'s own type check), and for each seat computes `merged = {**defaults, **entry}` before checking `harness`/`model` on `merged`. Rejected: refusing at `load_bindings` instead (would move the contradiction to the wrong side — the loader was already correct); rejected: patching every existing bindings.json to duplicate defaults onto each seat (treats a symptom on one goal, leaves the gate wrong for the next one).

## Consequences
Nothing deleted; the function's signature and callers (`path_a.py:31`, `path_b.py:677`) are unchanged. A sheet that truly has no `defaults` key and a seat with no harness/model still refuses — the merge with an empty `{}` default degrades to the old per-seat-only check. `supervisor/launch-profiles/catalog.js#declaresBinding`, cited in the function's own docstring as "the same predicate," was NOT checked for the same gap in this change — surfaced, not fixed, per the coding rule's own-change-vs-pre-existing split.

## Verification
`ignite/planning/probes/probe-planning-path-b-materialize.py` (scheduled via `rbtv-probe-suite.timer`/`probe-suite-scheduled.py`) gained P10/P11, both PASS at commit `2e533bb1`.

P10: a sheet with harness/model only in `defaults` reads cast (`missing == []`). P11: a sheet with no `defaults` and no per-seat harness/model still refuses (`missing == ["understand"]`). Red-first: reverted the fix in a scratch worktree (`git worktree add --detach HEAD` at `/tmp/wrapper-red-check`, probe copied in) — P10 FAILs (`missing=['understand', 'build']`) while P11 still PASSes, confirming the arm is discriminating. Full probe: 11/11 PASS. `probe-planning-path-b-failure.py`: 3/3 PASS, unaffected. NOT DEPLOYED — commit `2e533bb1` on `ignite/core-daemon`, HEAD only.

## ATTENTION
- UNCAST_IN_SHEET AND EFFECTIVE_BINDING ARE TWO SEPARATE READERS OF ONE FILE. Any future change to either merge order (`defaults` first vs per-seat first) must land in both in the same change, or the disagreement this task fixed comes back in the other direction.
- `catalog.js#declaresBinding`, cited by `uncast_in_sheet`'s own docstring as "the same predicate," was NOT verified to merge defaults in this change — a THIRD reading of the same casting sheet that may still disagree with the other two.
- CLOSING THE REGISTER FILINGS IS BLOCKED BY TOOLING, NOT BY THIS FIX. `file-issue.py` has no `close`/status-transition subcommand (only `file list show doctor schema memory selftest`); `register/open/` vs `register/closed/` is a directory split with no CLI mover. `G-leader-0828-2214-2` and the goal-ledger source `G-plan-reviewer-0828-2203-2` remain open pending that gap (task 155's territory) or an owner-authorized hand edit.
- catalog.js#declaresBinding, the third reader, was not checked for the same gap

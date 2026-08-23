# 20260822-i-goal-master-auto-mint — goal-master-auto-mint

kind: issue
component: team-kit
date: 2026-08-22
commit: ab650991,513a013c
deployed: yes
pin: NONE
seeded: true

## Observed

D79 (owner, 2026-08-22, `redesign-plan/decisions.md`) required auto-mint of `goal-master` at goal creation so the engine goal D51 would birth with a chair the owner's Slack channel could reach immediately. Before `ab650991` (2026-08-22 13:25:38Z), `mint_staff_chairs` in `ignite/team-kit/materialize-seats.py` only minted `STAFF_SEATS` (leader/consultant). The `--root --workflow` path the creation job and a console materialize both take therefore left `goal-master` absent: an owner message in the new goal's channel had nobody to sit.

Thirty-three minutes later the human write plan in `main()` still printed only `staff chair(s): leader/consultant` and stayed silent about `result['summoned']`, so a reader of the plan concluded the D79 chair was not minted (`513a013c` message, 13:58:00Z). Live-tree Python — re-read on every invocation, no daemon deploy — and HEAD still carries both loops; deployed-vs-HEAD do not differ.

## Mechanism

`goal-master` is a summoned chair (`_coord_summoned_seats()` imports `coord.SUMMONED_SEATS`), not a staff chair. D24 (2026-08-19 23:05Z) had already refused widening `STAFF_SEATS` because that tuple is read at `is_staff_seat`, the staff-mail arm, launch admission, and `--route` — putting `goal-master` there would have made it READY-to-dispatch. So `mint_staff_chairs` had no loop over summoned names: a `--root --workflow` materialize ran the staff pass, wrote `result['staff']`, and returned. The early-return was `args.seat in staff or nested`, which never treated `goal-master` as a staff identity either.

After `ab650991` added the summoned loop and `result['summoned']`, `main()` still iterated only `result.get("staff")`. The JSON path dumped the whole result; the human path did not. A silent mint on the write plan reads as "not minted" — the same class of undisclosed write the staff line was added to prevent.

## Attempts

First attempt held — checked: `missed_trials_source` NONE; `fix-inventory.csv` D9–D30 (D24/D26/D29 lineage, no D79 row); `git log --before=2026-08-22T13:25:38 --grep=goal-master -- ignite/team-kit/materialize-seats.py` returning `aa1920a8` (2026-08-20, "summoned seats join first taskforce") and `265c0ff7` (unrelated AGENTS.md descriptor). The D24 lineage (`20260820-c-goal-master-mint-door`, commits `1dd5d907, aa1920a8, 61ce15d9, 288de5d3, eda7e4c7`) made an already-minted `goal-master` IDLE until summoned and join the first taskforce; a human or script still had to pass `--seat goal-master`. That is the mint-door, not auto-mint-at-creation.

## Fix

`ab650991` appends a sibling loop over `_coord_summoned_seats()` inside `mint_staff_chairs`, after the staff loop, with the same four skips (already-existing row / catalog-missing / unsettled awaiting-close debt / no casting sheet) and the same `argparse.Namespace` recurse into `run(sub)` that degrades `(Refuse, CatalogRefusal)` to a warning so the already-written main rows stay retryable. Results land in `result['summoned']`, never `result['staff']`, so SM-1's `added_seats==[["leader"]]` contract stays intact.

Widening `STAFF_SEATS` was the rejected alternative (D24 option (c)): readiness would flip from IDLE to READY and staff-mail, admission, and route would all change. The early-return now also treats `args.seat in summoned` because a dry-run writes no row, so the `existing`-based skip cannot break recursion on `--seat goal-master`. A missing summoned sheet is a WARNING (the owner-message path has nobody to sit), unlike the consultant whose absent sheet is silence. Debt-skip copies the staff wording: a chair minted over an unsettled `awaiting-close` record is born DONE.

`513a013c` adds one `print` loop in `main()` mirroring the staff line: `{verb} summoned chair(s): …`.

## Consequences

The disclosure gap is the first commit's own follow-up, 33 minutes later — not a later regression. Same-day later edits of `materialize-seats.py` (`0563266b` D86 shared discovery, `d487c072` lane-symlink hygiene) do not mention summoned chairs or D79. No later commit grepped for summon/goal-master/SM-14 after 13:58Z touches this logic. D79's other half — auto-map of the Slack channel at goal creation — is not in either commit. No other memory entry cites these shas.

## Verification

`run_staff_mint_acceptance` gained SM-14 green and SM-15 red in the same commit as the mint (`ab650991`), registered as `ROW_ARMS["staff-mint-summoned"]`. SM-14: a `--root --workflow` materialize writes `seats/goal-master/seat.md`, empty `after`, first-taskforce join, `"goal-master" in summoned` and not in `staff_ids`, and `result['summoned']`/`result['staff']` stay `[["goal-master"]]` / `[["leader"]]`. SM-15: same fixture with the goal-master casting sheet deleted → no chair, exactly one warning naming the sheet path. Header `pin: NONE` matches — the pins live inside this file's selftest, not a standalone probe. `deployed: yes` is live-tree reload; no separate daemon-deploy stamp exists.

## ATTENTION

- `result['summoned']` is a sibling of `result['staff']` on purpose (SM-1 stays leader-only). Any consumer that asks "what got minted" and only reads `staff` will silently miss `goal-master` — the same class of bug `513a013c` closed on the human print path.
- D24 forbids widening `STAFF_SEATS` to absorb `goal-master`. Merging the two sets would flip readiness from IDLE to READY and change staff-mail, launch admission, and `--route` at once.
- The early-return includes summoned seats only because a dry-run writes no row, so `existing` cannot stop `--seat goal-master` from recursing. Changing dry-run to write a row (or dropping this guard) reopens that recursion.
- `main()` discloses summoned chairs in a separate print loop added 33 minutes after the mint. If the human write-plan format changes, re-check that a `result['summoned']` mint still prints; a silent mint reads as not minted.

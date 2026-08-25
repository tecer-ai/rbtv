# 20260825-i-two-probes-assumed-the-pre-spl — Two probes assumed the pre-split door and kit shape

kind: issue
component: coord
date: 2026-08-25
commit: 505ddfd5
deployed: no
pin: ignite/coord/probes/probe-checkout-disposition.py
components: supervisor,chat,planning

## Observed
The full 207-probe suite, run chunked after the front door split in two, came back with two reds
that the DoD-named checks had all missed: `chat/probes/probe-owner-ask-hold.js` died on
`TypeError: Cannot read properties of null (reading 'find')`, and
`coord/probes/probe-checkout-disposition.py` died on `FileNotFoundError:
/tmp/probe-*/supervisor/process.py`. The seat's own selftest, `materialize-seats --selftest` and
the two probes named in its definition of done were all green at the time.

## Mechanism
Two different faces of one cause — a caller that still assumed the pre-split shape.

`probe-owner-ask-hold` shelled `ready-seats` at `coord.py`, which refuses that verb by name since
the audience split. The refusal never surfaced AS a refusal: the probe `JSON.parse`s the output,
got `null` from the refusal text, and handed `null` to a `.find`. A wrong door reported itself as
a null-dereference three frames away.

`probe-checkout-disposition` builds a mutant kit by copying the kit folder FLAT into a temp dir.
The product spans two component folders now, so the mutant `coord.py` resolved
`<parent>/../supervisor/process.py`, which was never staged, and died while building
`PRODUCT_SOURCE`. The A3 mutation arm — the one that proves the outputs gate is what stamps
`done` — never executed at all.

## Attempts
Attribution was measured, not argued: a detached worktree at the baseline commit 3624dda2 ran
every non-green probe. Eleven failures and three inoperative reproduced there with byte-identical
failing rows, including `probe-daemon-lane-watch`'s L9 M9 mutation row, which looked like a prime
suspect because this seat had edited that probe. Only the two above were new.

## Fix
`probe-owner-ask-hold` gained one `runDoor()` with a `coord` / `supervise` pair, so each verb goes
to the door that accepts it and `checkin` / `checkout` stay where they were. A null-guard was
rejected as the fix: it would have converted a wrong-door refusal into a quiet skip.
`probe-checkout-disposition` stages the sibling `supervisor/` WHOLE, off disk, so a seventh module
arriving there needs no edit. Separately, three `materialize-seats.py` acceptance labels reading
`coordinate launch --dry-run` and the two `ROW_ARMS` prefixes that match them moved together to
`supervise launch`.

## Consequences
The suite is back to its reference baseline exactly: 207 discovered, 193 passed, 11 failed, 3
inoperative. `probe-save-gate` had already been repaired for the identical two-folder class, but
that repair was derived from `SPLIT_MODULES` — which is why the grep for that tuple found it and
missed `probe-checkout-disposition`, which names no tuple and copies by glob.

## Verification
Nine chunks, every one under 10 minutes, `--dir` per directory: 33/33, 27/28, 27/27, 20/23, 25/25,
16/18, 16/19, 20/20, 9/14 — discovered 207, attempted 207, passed 193, failed 11, inoperative 3,
not-attempted 0, every chunk carrying SUITE-COMPLETE. `probe-checkout-disposition` 11/11 green
with the A3 arm reporting a real behavioural difference, so it is live rather than vacuous.
`materialize-seats --selftest` PASS, 0 failed rows of 62, `row SC-1 green 3/3 red 3/3` and
`row CP-6 green 2/2 red 2/2`. Not deployed: worktree branch `ignite/core-redesign` only.

## ATTENTION
- A PROBE THAT SHELLS THE KIT PICKS A DOOR. After the audience split, `coord.py` refuses the 16
  supervision verbs BY NAME, and a probe that JSON-parses its output turns that refusal into a
  null-dereference several frames away rather than a readable verdict. Grep probes for the verb,
  never only for the door constant.
- A MUTATION-SCRATCH KIT MUST STAGE BOTH COMPONENT FOLDERS. `coord.py` reads every product file to
  build `PRODUCT_SOURCE`, so a flat copy dies at LOAD and the arm the probe exists for never runs
  — it reads as a probe failure, not as lost coverage.
- Attribution of a suite red is CHEAP AND DECISIVE with a detached worktree at the baseline commit
  (`git worktree add --detach /tmp/... <sha>`, symlink `node_modules`, run `--only`). Reasoning
  from the changed-file list alone would have been wrong about `probe-daemon-lane-watch`, whose
  probe this seat HAD edited and whose failure is nonetheless carried.
- a mutation-scratch kit must stage BOTH component folders — a flat copy dies at load and the arm never runs

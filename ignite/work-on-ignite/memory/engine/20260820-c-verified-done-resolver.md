# 20260820-c-verified-done-resolver — Verified done resolver

kind: creation
component: engine
date: 2026-08-20
commit: feba5fba,d813ebcc,3a112282
deployed: yes
pin: engine/probes/probe-reconcile.js; team-kit/probes/probe-checkout-disposition.py
components: team-kit
seeded: true

## Motivation
On 2026-08-20 a root-cause investigation of the two end-of-build handoffs (meet, stools) measured 11 `incomplete` last-rows stranded — 9 meet, 2 stools — after the only recovery door had been deleted. `incomplete`/`done`/`exited` were overloaded state words, and the redesign had rebuilt sensing plus one effector (start a sitting) with no resolver: no verb whose correct next act is rule/close/update rather than launch (`rca-resolve-and-refresh-2026-08-20.md` RC-2; `fix-inventory.csv` D32/D33).

D5 (`88f1b361`, 2026-08-19) refused an unverifiable `done` but recorded it as `incomplete` with a stamped reason `outputs-unverified: <note>`, because the ruled word `exited` is kit-only-writable and checkout's writer is `seat`. Measured that day: seven of those rows were genuinely finished work (files on disk, md5 re-verified by the leader) sitting owed, and `incomplete` was the one disposition outside `RULED_FLIP_FROM_STATES` (then just `exited` and `""`), so no actor held a verb for them. Pre-D12 the only recovery was the leader minting `rule-relaunch` + `launch --relaunch-ruled` (12 grants on meet; task-definer 5×). D12 (`e5a8e0de`) deleted that machinery on the commit's claim that reconcile "is live and relaunching seats on both goals" — false for class A: reconcile launched only the leader on a plain boot prompt; the stranded seat's name never reached `launchSitting`. CP4 never exercised a non-leader incomplete seat. D15's strike counter accumulated only on launch refusal; a successful launch cleared it, so 59/59 + 71/71 leader sittings exited `done` with zero strike rows in `heart.db`. Owner rulings D32–D33 (console session 2026-08-20; design `seed/design-resolve-and-refresh-2026-08-20.md`) are the decision this creation serves.

## Design
Three pieces, landed the same day, deliberately narrower than restoring D12.

D32 (`3a112282`): the discriminator is the word itself — no reason column, no side file. Checkout's D5 refusal now records `unverified` (writer `seat`): "the seat claimed done; the gate could not verify". `incomplete` keeps its single meaning (the seat said unfinished). `exited` stays kit-only so a seat cannot merge "process died" with "claimed done". Reconcile already treated `unverified` as non-terminal, so this is additive. Supersedes D5's literal wording ("exited, outputs unverified"); D5's substance (refuse, owed, routed, rulable) is unchanged (`redesign-plan/decisions.md` D32).

D33(a): the watcher relaunches a seat-written `incomplete` row by name (mechanical, D1 acts-first), bounded by D34 (2 no-progress attempts; D15's 3 counted on launch never fired), then types `stuck` to the leader. `unverified`/`exited`/empty rows are not relaunchable by the watcher — nobody but the leader has a verb for them — and instead wake the leader once per pass with a payload that names each owed row. The class-A split itself landed in companion `2233233a` (same window; not in this entry's `commit:` list — inventory D33 names the three header hashes). Nothing grant-shaped (D12 intact).

D33(b) (`3a112282`): `rule-disposition` admits exactly four from-states (`exited`, `""`, `unverified`, `incomplete`) and two destinations (`done` with an anchor quoting on-disk evidence, or `""`/clear). `done` stays unrulable as a from-state.

D39 (`d813ebcc` + wording-only `feba5fba`) corrected D33(b)'s first sentence that a CLEAR "re-arms an ordinary relaunch through seeding". A cleared row lands `ready-seats` verdict `UNDECLARED`; `seeding.js` `CLASSIFIED_VERDICTS` maps that to `not-waitable`; the daemon never re-seeds it. Ruled: clearing and relaunching stay two deliberate acts. Option B — teach the daemon to auto-seed cleared rows — rejected: it touches `seeding.js` (every current seat was walled off), needs its own seat plus a deploy, and its blast radius reaches every `UNDECLARED` row, not just the 11 owed. Option C — forbid clearing — rejected: genuinely superseded rows (meet's `plan-planner`) need an honest word to close under.

D40 (same `d813ebcc`): the retry signature dropped `:${ended}` so the count survives re-checkout. Rejected: leaving the spec as written (open-ended relaunch forever on both live goals); raising the limit above 2 (the bound was already ruled; the defect was that it never fired).

## How it works
In `coord.py` `cmd_checkout`, the D5 branch sets boolean `outputs_unverified` instead of stuffing the seat's `incomplete` reason string. `checkout_disposition` is computed once: `"renew" if renew else "unverified" if outputs_unverified else "incomplete" if incomplete else "done"`. The unverified arm sits inside `if not renew and not incomplete`, so a seat that declared its own unfinished ending never reaches the flag.

`RECORD_DISPOSITION_WRITER` gains `"unverified": frozenset({"seat"})`. `_DEFERRAL_BY_DISPOSITION` maps it to its own class `claimed-unverified` — not folded into `declared-incomplete`, because both route to the leader so folding would look free and would erase the evidentiary split (seat says unfinished vs. seat claimed done and the kit could not grade it). `CLASS_TO_VERDICT["claimed-unverified"] = "DONE"` is the admission verdict ("this session ended, so it is not a launch candidate"), never a statement the work is done; the class is what routes, and it routes to the leader's `rule-disposition`.

`RULED_FLIP_FROM_STATES = (RULED_FLIP_FROM, "", "unverified", "incomplete")`. `session_rule_disposition` refuses any current cell not in that four-tuple. Destination `""` is admitted at `validate_disposition` for the leader alone and is deliberately not a key of `RECORD_DISPOSITION_WRITER` (an empty cell is the absence of an ending; adding it would mint a deferral class for "no class"). `--anchor` is still mandatory. No grant, flag, latch, or new verb.

In `reconcile.js` `deriveOwed`, every non-terminal last-row with an `ended` stamp (and no later `hold-anchor`) becomes class A. The word is the split: `disp === 'incomplete'` → `reason: 'incomplete'`; everything else non-terminal → `reason: 'nonterm'`. Incomplete items are pushed onto `launchTargets` as `{seat, reason: 'incomplete', signature: 'incomplete:<seat>'}` — that is the by-name relaunch. The nonterm remainder folds into one leader wake whose `promptFn` appends `nontermPayload(rows)` after the existing boot prompt (if the boot prompt cannot be built the launch fails first; nothing is invented in its place). The payload names each owed row, its disposition, its `ended` stamp, and the two `rule-disposition` destinations, plus — after D39, later amended by D42 — the second-act `launch --only <seat> --declare-only <anchor>` for a cleared row and `--rerun` for a crashed `exited` row. `STRIKE_LIMIT` is 2, counted on "the owed signature is unchanged" (D34); `clearAttempt` no longer fires on a clean launch. That counter is the same machinery as `20260820-i-watcher-retry-policy`.

`feba5fba` is wording only in `coord.py` (eight textual statements of CLEAR≠relaunch, including user-facing `rule-disposition --help`). coord.py is read live per invocation (D6), so it is effective on commit.

## Consequences
Did not restore D12's grant machinery. Did not add a reason column. D5's substance survived; only the recorded word changed.

`d813ebcc` corrected the leader-wake payload that had promised "ordinary relaunch" after CLEAR, and stopped the retry counter resetting on every re-checkout (D40; sibling `20260820-i-watcher-retry-policy` owns the counter's later tuning).

`23578584` (2026-08-22, D81, entry `20260822-c-unverified-into-dispositions`) found `reconcile.js`'s `RECORD_DISPOSITIONS` still omitted `unverified` even though coord.py's writer dict had it as one of six real keys; the word had been smuggled into `EXTRA_NON_TERMINAL` next to a synthetic label coord.py never writes (`renew-interrupted`). Commit message: model-accuracy fix, not a behavior change — `isNonTerminal()` unchanged. The same latent inaccuracy was in `reconcile.selftest.js`'s own literal assertion.

D42 later amended D39 consequence 2: `--declare-only` is the cleared row's door only; a crashed (`exited`) row is re-run in one act with `--rerun` and is never cleared first, because CLEAR would destroy the `exited` word. That wording is now in `nontermPayload`; sibling `20260820-c-relaunch-instrument-rerun`.

No revert of D32/D33/D39/D40 through 2026-08-22. Sibling entries sharing this landing: `20260820-i-cleared-row-relaunch-is-two-ac` (`feba5fba,d813ebcc`), `20260820-i-watcher-retry-policy` (`d813ebcc,2233233a` and later), `20260820-c-stuck-becomes-a-brake` (the terminal of the same loop).

## Verification
`3a112282` reports coord.py selftest PASS (0 failures, 1065 ok), `probe-verdict-vocabulary.js` 6/6, `probe-checkout-disposition.py` 16/16. That probe's A3 mutation seam was re-typed to the new `checkout_disposition` expression and went red with "seam NOT FOUND" before the fix — the seam assertion working.

`d813ebcc` added a D33(a) selftest arm asserting the payload names the second act and no longer promises ordinary relaunch; a D40 arm driving two passes with different `ended` stamps asserting attempts=2 + one stuck; and a red arm restoring the end-time component on a compiled copy, showing attempts `[1,1,1]` with zero stuck. Those arms live in `reconcile.selftest.js`, wrapped by `engine/probes/probe-reconcile.js`. `2233233a` added the by-name relaunch payload arms and two red-by-mutation arms (restoring `clearAttempt`-on-success and the numeric `checkinOf` cursor).

coord.py changes (`3a112282`, `feba5fba`) are live-on-commit (D6 exception), no daemon restart. reconcile.js changes (`2233233a`, `d813ebcc`) needed `rbtv ignite daemon deploy`; `fix-inventory.csv` D33 records rbtv HEAD `ac1c08d8` deployed 2026-08-21 18:14:37Z as the deploy point.

## ATTENTION
- `unverified` later moved again by D81 (`23578584`, entry `20260822-c-unverified-into-dispositions`) from an ad-hoc extra list into `RECORD_DISPOSITIONS` — grep the string rather than assuming one home if changing disposition vocabulary.
- The retry bound (`STRIKE_LIMIT = 2`, counted on no-progress) is the same counter as `20260820-i-watcher-retry-policy` and the terminal of `20260820-c-stuck-becomes-a-brake`; changing the count here changes when `stuck` fires there.
- D39's two-act split (CLEAR ≠ relaunch) is a ruling, not a missing convenience: auto-seeding a cleared row was option B, rejected because it touches `seeding.js` and would hit every `UNDECLARED` row, not just the 11 owed. A wrapper that auto-relaunches after a clear reopens D39. Sibling `20260820-i-cleared-row-relaunch-is-two-ac` owns this primarily; `feba5fba`/`d813ebcc` are shared.
- D12 (`e5a8e0de`) deleted `rule-relaunch` on the claim that reconcile already relaunched stranded seats — A6 measured that false for class A (leader-only wake, never the seat by name). The watcher relaunches `incomplete` only; `unverified`/`exited`/empty still wake the leader. Restoring grant-shaped machinery would violate D33(b)'s "D12 intact".

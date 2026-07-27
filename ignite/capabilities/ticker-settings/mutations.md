# Discriminating power of the 7.66 probes — MEASURED, not asserted

`p-green-harness-over-a-broken-mechanism`: a probe that cannot fail proves nothing, and "I read my
code and it looks right" produces no evidence. So each mutation below was APPLIED to the real tree,
the probe RUN, and the result recorded — with a control run before and after.

Reproduce any row by making the edit, running the probe, and restoring.

| # | Mutation | Probe | Result |
|---|---|---|---|
| **M1** | remove the settings overlay from `server/index.js` | cadence-flow | ⚠ **INVALID — see below** |
| **M1′** | overlay `settings.DEFAULTS.ticker` instead of the machine's block (`server/index.js`) — daemon HEALTHY, adoption BROKEN | cadence-flow | **RED: 12/15**, exit 1 |
| **M2** | `from` hardcoded to `null` in `setValue` (the installer's defect, transplanted) | ticker-settings | **RED: 37/39**, exit 1 |
| **M3** | `validateMachine` returns `[]` unconditionally | ticker-settings | **RED: 34/39**, exit 1 |
| — | control, unmutated, before and after every row above | both | **GREEN: 39/39 and 15/15**, exit 0 |

## ⚠ M1 was INVALID and is kept here rather than deleted

The first mutation deleted the line `mergedConfig.ticker = {...}`. The probe went red — and **for the
wrong reason**: the daemon crashed at boot on `TypeError: Cannot read properties of undefined
(reading 'tick_interval_ms')` from the log line immediately below the deleted assignment, so the
unit never started and every leg failed on the precondition.

**A probe that goes red because the subject died has discriminated nothing.** It was rerun as M1′,
which keeps the daemon healthy and breaks only adoption. Recorded because reading M1's red as
success is exactly the mistake this file exists to prevent — the same shape as `G-121`, one layer
up: an artifact that looks conclusive because it STOPPED.

## What M1′ proves, and the part worth keeping

Under M1′ the daemon is `ActiveState=active`, ticks keep firing, and **"supervision resumed" still
PASSES**. Only three checks go red:

```
FAIL  the RESTARTED daemon resolves the new cadence FROM settings.json  [{"ms":10000,"source":"settings.json"}]
FAIL  ⚠ the OBSERVED tick interval matches the NEW cadence  [median gap=10000ms; gaps=10000,10000]
FAIL  ...and it is decisively NOT the 10s default it booted with       [median=10000ms]
```

⚠ **Read the first line closely: `source` still reported `settings.json` while `ms` was the OLD
value.** A check that asserted only "the daemon says it read settings.json" would have PASSED under
a mutation that breaks the entire feature. **The check that actually caught it is the one measuring
the interval between real ticks in the journal** — behaviour, not self-report.

That is `p-green-harness` demonstrated inside this task's own evidence, and it is the argument for
the behavioural leg existing at all.

## M2's second consequence, which was not designed for

M2 turned two checks red, not one: the `from`-computation check, and *"setting the SAME value writes
no history line"*. The no-op detection compares the stored value against the new one, so hardcoding
`from` to `null` also destroys the ability to notice that nothing changed — **the installer's defect
does not stop at a wrong audit field; it would also append a line for a change that did not
happen.** Filed as `G-168`.

## Not proven by any mutation here

- ~~**The boot refusal has never fired on a REAL daemon start.**~~ **NAMED, THEN RUN, THEN CLOSED.**
  It was written here as an unproven seam — the two halves proven separately, the composition never
  taken, `G-124`'s exact shape — and then exercised rather than left on the list. The cadence-flow
  probe now hand-edits `tick_interval_ms: 250` PAST the surface and restarts the real unit:
  `ActiveState=failed`, with the journal carrying `REFUSES TO START` and `is below the floor`.
  Restoring a legal value starts it again, so the refusal is not sticky. Three checks, live.
- **Concurrent writers.** `setValue` is read-modify-write with an atomic rename, so two simultaneous
  edits can lose one. No probe exercises it. Not a defect today (the surface is a human typing a
  command), and stated so it is not mistaken for proven.

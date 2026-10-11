# Timer check

A timer may name a check tool. A check tool is one executable that decides, without a model, whether the timer's firing has anything for the agent. This page states what Ignite stores for a check, how a timer wake is identified, and the store calls that fire a timer. `ignite schedule add -h` and `ignite connect -h` own the option and the JSON key.

## The stored check

`schedules.check_tool` in the agent's `state.sqlite` holds the check, and is null for a timer without one. `ignite schedule add --check`, `ignite schedule change --check` and the `check` key of `ignite connect --schedule-json` write it; `ignite schedule list --json` returns it as `check_tool`. All three writers pass the value through `checkTool` in `store.js`, and `upsertSchedule` applies it again, so one rule decides what is stored:

| Value | Meaning | Stored as |
|---|---|---|
| Holds `/` or `\` | A path relative to the agent home, such as `tools/mail-check.js` or `./mail-check.js` | The same text with `\` written as `/` |
| Holds neither | A command found on PATH, such as a tool rbtv installs | The same text |
| Absolute (`/…`, a drive letter), a `..` part, a trailing separator, empty, more than one line, not text | Refused; nothing is written | |

The value is one executable. Ignite never splits it into arguments. A tool in the agent's folder is named by its path and is never put on PATH. Ignite does not check that the file exists when the timer is written.

A timer keeps its check when its cadence, note, report mode or enabled state changes and when it advances. `schedule change` has no option that removes a check: cancel the timer and add it again. A `connect` re-run whose JSON has no `check` keeps the check of the timer already bound.

Opening a database written before the check existed adds the column as null and drops the index `queue_one_pending_schedule`. Its timers behave as before.

## The three answers

A check tool gives one of three answers:

| Answer | Form |
|---|---|
| Nothing new | Exit 0 and `{"new":false}` on standard output |
| Something new | Exit 0 and `{"new":true,"details":…}` on standard output |
| Failed | A nonzero exit |

`ignite schedules-due` runs no check. It reports a due timer that has one with the reason `check` and leaves it due.

## One wake per timer and occurrence

A timer wake is a queue row of kind `schedule` with the id `schedule:<timer id>:<occurrence>`, where the occurrence is the timer's `next_at` in epoch milliseconds when it fired. The row's payload is `{"scheduleId":"<timer id>"}`, with `"details"` added when the wake carries a check's details. The payload stays on the row through retries, a hold and its repair.

`enqueueScheduleWake` answers `duplicate` and inserts nothing when a row with that id already exists, in any state. A pending wake of another timer blocks nothing, so every timer due in one tick gets its own wake.

## Firing a timer from code

| Call | Use | Result |
|---|---|---|
| `store.dueSchedules(now)` | The enabled timers whose `next_at` has passed | Rows with `check_tool` |
| `store.fireSchedule({ schedule, nextAt, details })` | Wake the agent for the occurrence `schedule.next_at`. `schedule` is a row from `dueSchedules`; `nextAt` is the next occurrence, or null for a one-time timer; `details` is the check's details, left out for a timer without a check | `{ inserted, reason, advanced }`. One transaction records the wake, then advances the timer. `agent_hold` and `refused` record nothing and leave the timer due. `duplicate` records nothing and advances |
| `store.advanceSchedule(id, occurrence, nextAt)` | Advance a timer without a wake, as for the answer nothing new | True when the timer moved. It moves only while its `next_at` equals `occurrence`; a null `nextAt` disables it |

`nextOccurrence(cadence, timezone, now)` in `schedule.js` computes `nextAt`.

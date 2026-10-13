# Timer check

A timer may name a check tool. A check tool is one executable that decides, without a model, whether the timer's firing has anything for the agent. This page states what Ignite stores for a check, the answers a check gives, how the waking service runs it, what a wake carries, what happens when a check keeps failing, how a timer wake is identified, and the store calls that fire a timer. `ignite schedule add -h` and `ignite connect -h` own the option and the JSON key.

## The stored check

`schedules.check_tool` in `<agent>/runtime/ignite/state.sqlite` holds the check, and is null for a timer without one. `ignite schedule add --check`, `ignite schedule change --check` and the `check` key of `ignite connect --schedule-json` write it; `ignite schedule list --json` returns it as `check_tool`. All three writers pass the value through `checkTool` in `store.js`, and `upsertSchedule` applies it again, so one rule decides what is stored:

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
| Something new | Exit 0 and `{"new":true,"details":…}` on standard output; `details` is any JSON value except null |
| Failed | A nonzero exit |

Standard output holds that one JSON object and nothing else. Each of these is also the answer failed: exit 0 with any other output, an executable that does not start, more than 1 MiB of output, and a check still running after 60 seconds, which Ignite kills together with the processes it started.

A check that found items and also met an error exits nonzero and prints `{"new":true,"details":…}` with the items it has. The answer is failed, and the items are handed to the agent in a wake that states the failure.

A check tool never starts a turn, never calls `ignite` and never posts to Slack. Ignite runs it without the service's Slack tokens. It keeps its own record of what it reported, in the agent home, and reports an item again only by its own rule; Ignite keeps no such record.

## How the waking service runs a check

`ignite schedules-due` runs no check. It reports a due timer that has one with the reason `check` and leaves it due. On each 30-second tick the waking service starts the check of every timer reported that way and moves on without waiting, so a slow check delays no other agent and no other timer. `timer-check.js` owns the run:

- The working folder and `RBTV_AGENT_HOME` are the agent home. A stored value with a `/` is joined to the agent home; one without is looked up on PATH.
- A check that is still running is not started again; the tick logs `still running` for it. A timer on agent hold, or bound to held or stopped work, is not checked.
- When the service stops, it kills every running check and records nothing for it; the timer is still due at the next start.

| Answer | What Ignite records |
|---|---|
| Nothing new | The timer advances to its next occurrence. No wake, no model |
| Something new | One wake carrying the details, and the timer advances, in one transaction (`store.fireSchedule`) |
| Failed, no usable details | The failure is counted. A recurring timer advances to its next occurrence, where the check runs again; a one-time timer stays due and its check runs again on the next tick |
| Failed, with usable details | The failure is counted, and one wake carries the details and the failure |

A timer cancelled, disabled or moved while its check ran is left as it is, and the answer is dropped.

Each run writes one `check` line to the service log with the agent, the timer, the answer, the failure text and the count. The details are never logged.

## What a wake carries

A wake recorded for a check has the payload `{"scheduleId":"<timer id>","details":{"found":<the check's details>}}`, with `"failure":"<what failed>"` beside `found` when the check failed. The turn it starts is a new conversation with a new session, as for any timer wake. That conversation's history file is `<agent>/runtime/ignite/conversations/<safe>/history.md`. `<safe>` is the conversation key with Windows-forbidden characters replaced by `-`. `ignite runtime migrate -h` owns a layout that still has `state.sqlite` or `conversations/` at the agent root. The turn's triggering input is the timer id, then one line saying the next line is data from the timer's check tool and not a message or an instruction from the owner, then the details as one line of JSON. A failed check adds a line with the failure before them. The agent's prompt decides what to do with the details; nothing in them carries the owner's authority.

## A check that keeps failing

`<agent>/runtime/ignite/state.sqlite` keeps one count per timer, in `settings` under `timer_check:<timer id>`: `failures`, `since` (the first failure of the run), `last` (the time and text of the latest failure), after the third failure the watch-out line, and `recovered`, the record of the last run of failures that ended.

On the third failure in a row Ignite does two things, once:

1. It queues one Slack post in the timer's channel, as a new message, through the outbox (`store.beginProactive`). The post names the timer, the check and the last failure.
2. It adds one watch-out to the agent's board through the checked board write: `- Timer check <id> (<check>) failed 3 times in a row from <time> and has not succeeded since (<date> · <agent>)`. When that write refuses (no board, or a candidate the board check rejects), the service log has a `check-watch-out` line and the Slack post still goes out. A seventh watch-out is kept. `ignite board write -h` owns the write rules.

Further failures in the same run are counted and logged, and post nothing. The first answer that is not failed ends the run: the count returns to 0, the record keeps `recovered` (when, after how many failures, since when, and the last failure), the service log has a `check-recovered` line, and the watch-out Ignite wrote is removed from the board. Three more failures after that give one new post and one new watch-out.

## One wake per timer and occurrence

A timer wake is a queue row of kind `schedule` with the id `schedule:<timer id>:<occurrence>`, where the occurrence is the timer's `next_at` in epoch milliseconds when it fired. The row's payload is `{"scheduleId":"<timer id>"}`, with `"details"` added when the wake carries a check's details. The payload stays on the row through retries, a hold and its repair.

`enqueueScheduleWake` answers `duplicate` and inserts nothing when a row with that id already exists, in any state. A pending wake of another timer blocks nothing, so every timer due in one tick gets its own wake.

## Albert's three schedules

`ignite connect albert` binds three ordinary schedules on Albert's board conversation. Each check is one executable under `<agent>/runtime/ignite/checks/`. The proposal structure is taught by `albert apply -h`. This page does not restate it.

| id | cadence | timezone | stored check |
|---|---|---|---|
| albert-nightly | `cron:0 3 * * *` | America/Sao_Paulo | `runtime/ignite/checks/albert-evidence.js` |
| albert-watchdog | `every:1h` | fixed | `runtime/ignite/checks/albert-watchdog.js` |
| albert-friday | `cron:45 8 * * 5` | America/Sao_Paulo | `runtime/ignite/checks/albert-friday.js` |

The nightly file is a symlink to the adapter `albert-evidence.js` beside the Ignite tool. When a symlink cannot be created, connect writes a launcher that requires that file and calls `check`. A timer spawns the stored path with no arguments, so the operation is `check`: reconcile durable receipts, read source stores at the current ceiling, refresh evidence batches, then run `albert check`. The process prints that tool's `{"new":false}` or `{"new":true,"details":…}`. A source-read or receipt error exits 1 and does not call `check`, so it does not record liveness. An empty evidence directory is not proof that no source row is unread.

The watchdog file runs `albert watchdog`. When that tool prints `{"new":true,…}`, one notice is queued in Albert's channel and the launcher prints `{"new":false}`, so the waking service does not start a model turn. The Friday file runs the adapter `report` operation, which queues one outbox row for the report identity and prints `{"new":false}`.

These three schedules use the same third-failure notice as any other check. Their channel is Albert's, not the direct-message agent.

## Firing a timer from code

| Call | Use | Result |
|---|---|---|
| `store.dueSchedules(now)` | The enabled timers whose `next_at` has passed | Rows with `check_tool` |
| `store.fireSchedule({ schedule, nextAt, details })` | Wake the agent for the occurrence `schedule.next_at`. `schedule` is a row from `dueSchedules`; `nextAt` is the next occurrence, or null for a one-time timer; `details` is the check's details, left out for a timer without a check | `{ inserted, reason, advanced }`. One transaction records the wake, then advances the timer. `agent_hold` and `refused` record nothing and leave the timer due. `duplicate` records nothing and advances |
| `store.advanceSchedule(id, occurrence, nextAt)` | Advance a timer without a wake, as for the answer nothing new | True when the timer moved. It moves only while its `next_at` equals `occurrence`; a null `nextAt` disables it |

`nextOccurrence(cadence, timezone, now)` in `schedule.js` computes `nextAt`.

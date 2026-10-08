'use strict';

// API — PAGES maps a group or one of its verbs to its help text: 'schedule', 'schedule add', ...
// helpPage(command, tail) → the page for tail[0] when it is a verb of the group, else the group page,
// or undefined when the command has no page here.
// A usage form appears only on the page of the command it invokes; a group page lists its verbs and
// points to their pages.

const { DREAMER_MODEL } = require('./config.js');

const HOME = 'Home: RBTV_AGENT_HOME, otherwise --agent <slug> --installation <path>.';

const SCHEDULE_CONTEXT = `${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.`;

const SCHEDULE_COMMIT = `If SQLite commits but board refresh fails, exit 0 reports the id and "committed; board refresh pending"
(--json adds warning). Do not repeat the mutation. The next board write or turn refreshes Timers from SQLite.`;

const UNKNOWN_OPTION = 'An option this command does not have is refused, and nothing changes.';

const CADENCE = `Cadence (exactly one of --at, --cron, --every; an empty cadence is refused):
  --at <ISO datetime with offset>
      One time, for example 2026-10-09T09:00:00-03:00. The offset or Z is required, so
      --tz is refused. The timer is disabled after it fires.
  --cron "<5-field>" --tz <IANA zone>
      Recurring. Cron requires an explicit --tz. The next occurrence is timezone-aware.
  --every <duration>
      A fixed-interval recurrence: 30s, 5m, 2h or 1d. It is elapsed time with no
      timezone, so DST does not move it and --tz is refused.`;

const PAGES = {
  schedule: `ignite schedule — timers

Add, list, change, or cancel a timer. A timer wakes the agent in a fresh conversation when it is due.
Timers on _artifacts/board.md show enabled schedules with a next fire and pending/running wakes.

Commands
  add     Add a timer: one time (--at), a cron schedule (--cron --tz) or a fixed interval (--every).
  list    List this agent's timers.
  change  Change a timer's cadence, note, report mode or enabled state.
  cancel  Cancel a timer.

Next: ignite schedule COMMAND -h
`,

  'schedule add': `ignite schedule add — add a timer

usage: ignite schedule add (--at <ISO datetime with offset> | --cron "<5-field>" --tz <IANA zone> | --every <duration>)
                           --note <text> [--subject <title>] [--report always|when-useful]
                           [--conversation <key>] [--json]

Adds one enabled timer to this agent.

${CADENCE}

Other options:
  --note <text>
      Required, non-empty. What the timer is for; ignite schedule list shows it.
  --subject <title>
      Links the timer to a board subject. A non-empty one-line title. Omitted means none.
  --report always|when-useful
      Report mode stored with the timer. Default: when-useful.
  --conversation <key>
      The conversation the timer belongs to. Default: IGNITE_CONVERSATION, which the waking
      program sets inside a turn. It must be a conversation in this agent's history; outside
      a turn, pass it.

${SCHEDULE_CONTEXT}
Writes this agent's state.sqlite and refreshes Timers on _artifacts/board.md. A valid
<home>/_artifacts/board.md must exist before SQLite is opened; otherwise the command refuses
and changes nothing.
${SCHEDULE_COMMIT}
Success: exit 0, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>"; --json {schedule, warning?}.
Refusal: exit 1, reason on stderr, with or without --json. An option given twice is refused
("duplicate flag --<name>"). ${UNKNOWN_OPTION}
No Slack request or prompt.

Example: ignite schedule add --cron "0 9 * * 1-5" --tz America/Sao_Paulo --note "Check the inbox"
Next: ignite schedule list
`,

  'schedule list': `ignite schedule list — list this agent's timers

usage: ignite schedule list [--json]

Prints one line per timer, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>
enabled=<true|false> <note>", or "no schedules" when there are none. --json prints {schedules}.
A read: it changes no timer, but it creates state.sqlite when the agent has none.

${SCHEDULE_CONTEXT}
Exit 0, or 1 with the reason on stderr when the home cannot be resolved. ${UNKNOWN_OPTION}

Example: ignite schedule list
Next: ignite schedule change -h
`,

  'schedule change': `ignite schedule change — change a timer

usage: ignite schedule change <id> [--at <ISO datetime with offset> | --cron "<5-field>" [--tz <IANA zone>] | --every <duration>]
                              [--note <text>] [--report always|when-useful] [--enabled true|false] [--json]

Changes the timer <id>, as printed by ignite schedule list. An option left out keeps the timer's value.
The board subject the timer is linked to is kept.

Cadence: give one of --at, --cron, --every to replace it, with the rules of ignite schedule add -h.
With none of them the cadence is kept. --tz alone changes the zone of a cron timer; on an at or
every timer it is refused. --cron alone keeps the zone of a cron timer; turning an at or every timer
into a cron timer needs --tz. A recurring timer cannot be left without a cadence.

Other options:
  --note <text>                 Replace the note. Non-empty, as on ignite schedule add.
  --report always|when-useful   Replace the report mode.
  --enabled true|false          Turn the timer on or off. Any other value is refused.

${SCHEDULE_CONTEXT}
Writes this agent's state.sqlite and refreshes Timers on _artifacts/board.md. A valid
<home>/_artifacts/board.md must exist before SQLite is opened; otherwise the command refuses
and changes nothing. A missing <id> is refused: "schedule change requires an id"; an unknown one:
"unknown schedule: <id>".
${SCHEDULE_COMMIT}
Success: exit 0, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>"; --json {schedule, warning?}.
Refusal: exit 1, reason on stderr, with or without --json. An option given twice is refused
("duplicate flag --<name>"). ${UNKNOWN_OPTION}

Example: ignite schedule change 7f3c2a10 --every 2h --enabled true
`,

  'schedule cancel': `ignite schedule cancel — cancel a timer

usage: ignite schedule cancel <id> [--json]

Deletes the timer <id>, as printed by ignite schedule list, and refreshes Timers on
_artifacts/board.md.

${SCHEDULE_CONTEXT}
A valid <home>/_artifacts/board.md must exist before SQLite is opened; otherwise the command refuses
and changes nothing. A missing <id> is refused: "schedule cancel requires an id"; an unknown one:
"unknown schedule: <id>".
${SCHEDULE_COMMIT}
Success: exit 0, "cancelled <id>"; --json {cancelled, warning?}.
Refusal: exit 1, reason on stderr, with or without --json. ${UNKNOWN_OPTION}

Example: ignite schedule cancel 7f3c2a10
`,

  'schedules-due': `ignite — schedules-due help

usage: ignite schedules-due --now <ISO datetime>

Enqueue a fresh conversation with no thread or resumed session; input is the schedule id only.
While one schedule wake is pending, further dues are de-duplicated. Never enqueues for a held or stopped schedule, and never clears a hold.
${UNKNOWN_OPTION}
`,

  work: `ignite work — assignments and holds

Show, retry, resume, or stop an assignment. An assignment is one piece of work the agent carries
across turns. A hold stops the agent's queue after repeated technical failures, for one assignment
or for the whole agent.

Commands
  status  Show the agent hold and every assignment with its state.
  retry   Clear a hold so the held work runs again.
  resume  The same as retry.
  stop    Stop an assignment.

Next: ignite work COMMAND -h
`,

  'work status': `ignite work status — show holds and assignments

usage: ignite work status [--conversation <key>] [--json]

Prints "agentHold=yes" or "agentHold=no", then one line per assignment,
"<id> <state> <conversation key>", the most recently updated first. State is one of open, continue,
held, stopped, completed, waiting_owner or waiting_workers. --conversation <key> lists only that
conversation's assignments. --json prints {agentHold, works}: agentHold is the hold record
{reason, at} or null, and works holds one record per assignment. A read: it changes no assignment,
but it creates state.sqlite when the agent has none. An option given twice is refused
("duplicate flag --<name>"). ${UNKNOWN_OPTION}

${HOME}
Exit 0, or 1 with the reason on stderr when the home cannot be resolved.

Example: ignite work status
Next: ignite work retry -h
`,

  'work retry': `ignite work retry — clear a hold

usage: ignite work retry [<id>] [--json]

With an id, clears only that assignment's hold: the assignment is open again and its held queue
items run again. With no id, clears only the agent hold. Set a launch setting that does not use
the failed model before retrying. ignite work resume does the same.

<id> is an assignment id printed by ignite work status.

${HOME}
Success: exit 0, "cleared <id>" or "cleared agent hold"; --json {cleared} with the id or "agent".
Refusal: exit 1, reason on stderr: "work <id> is not held", or "no agent hold" when no id was given.
Nothing is changed on a refusal. ${UNKNOWN_OPTION}
No Slack request or prompt.

Example: ignite work retry
Next: ignite work status
`,

  'work resume': `ignite work resume — clear a hold

usage: ignite work resume [<id>] [--json]

The same command as ignite work retry. With an id, clears only that assignment's hold: the
assignment is open again and its held queue items run again. With no id, clears only the agent hold.

<id> is an assignment id printed by ignite work status.

${HOME}
Success: exit 0, "cleared <id>" or "cleared agent hold"; --json {cleared} with the id or "agent".
Refusal: exit 1, reason on stderr: "work <id> is not held", or "no agent hold" when no id was given.
Nothing is changed on a refusal. ${UNKNOWN_OPTION}
No Slack request or prompt.

Example: ignite work resume 4d1e9b
Next: ignite work status
`,

  'work stop': `ignite work stop — stop an assignment

usage: ignite work stop <id> [--json]

Stops the assignment <id>, as printed by ignite work status, and cancels its pending continue,
wake and schedule queue items. It does not cancel the assignment's schedules (use
ignite schedule cancel) and does not clear an agent hold.

${HOME}
Success: exit 0, "stopped <id>"; --json {work}.
Refusal: exit 1, reason on stderr: "work stop requires an id", or "unknown work" for an id this
agent does not have. ${UNKNOWN_OPTION}

Example: ignite work stop 4d1e9b
Next: ignite work status
`,

  wake: `ignite — wake help

usage: ignite wake --conversation <key> --note <text> [--work <id>]

Worker completion. Enqueues a continuation. Does not clear a hold.
${UNKNOWN_OPTION}
`,

  post: `ignite — post help

usage: ignite post (--text <text> | --text-file <path> | --file <path>)... [--audio] [--thread <thread>]

Without --thread, opens a new thread in the agent's channel. --thread selects an existing conversation in this agent's stored history: its full team:channel:root-ts key or a unique root timestamp. Unknown or ambiguous targets are refused.
The post joins that conversation's history after delivery; its session and prior history stay intact.
Enqueues delivery and activates the target. Prints "<conversation key> activated"; --json returns conversationKey, outboxId, clientMsgId, activated and channel. Exit 0 means queued; errors go to stderr with exit 1. ${UNKNOWN_OPTION} No Slack request or interactive prompt in this command.
Example: ignite post --thread T1:C1:123.456 --text "Check complete"
`,

  board: `ignite board — checked short-term memory

Write or close a subject on the agent's board, <home>/_artifacts/board.md. The board is checked
short-term memory: every change is validated first, and an invalid or over-cap change is refused,
never truncated.

Commands
  write  Replace the board's subjects and watch-outs from a complete Markdown candidate file.
  close  Remove one subject and record its outcome under Recently closed.

Next: ignite board COMMAND -h
`,

  'board write': `ignite board write — write the board from a candidate file

usage: ignite board write --file <path> [--json]

Reads a complete UTF-8 Markdown candidate; creates or updates <home>/_artifacts/board.md.
Exactly one --file <path> is required.

Keep all four headings in order: ## What matters now, ## Watch-outs,
## Timers, ## Recently closed. Empty sections keep their headings.
Each subject: a unique ### Title, 1–3 state lines, then these three lines:
  - Threads: none OR [label](https://example.com/thread) links separated by " · "
  - Detail: none OR a Markdown page path/link (agent detail: ../memory/<slug>.md)
  - Flags: none OR answered YYYY-MM-DD OR idle since YYYY-MM-DD
Watch-outs: - Rule (YYYY-MM-DD · agent[/[label](URL)])
Temporary facts end with until YYYY-MM-DD, before any provenance tail.
Only subjects and watch-outs may change. Keep Timers, Recently closed and
existing Flags unchanged; new Flags must be none. Remove subjects with ignite board close.
Caps: 90 non-empty lines excluding the Timers table; 8 subjects, 6 watch-outs,
6 closed entries. Invalid or over-cap writes are refused, never truncated.

${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack access. Reads an existing state.sqlite to refresh Timers and Flags as part of the
write; never creates a database. -- ends options. ${UNKNOWN_OPTION}
Success: exit 0, "written <path>" or "unchanged <path>". Failure: exit 1, reason on stderr; fix
the candidate and retry. Validation leaves the board unchanged. --json emits {path, changed} or
{path, error} on stdout; path is null if home resolution failed. No interactive prompts.

Example: ignite board write --file "board candidate.md"
Next: ignite board close -h
`,

  'board close': `ignite board close — close a subject

usage: ignite board close <subject> <outcome> [thread] [--json]

Use the exact title; quote arguments containing spaces. Outcome is one line.
Optional thread is a "[label](URL)" link. Removes the subject and appends its
outcome with today's UTC date and agent slug to Recently closed.
A full closed section refuses the whole change; archive old entries first.
Nothing is pruned automatically.

${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack access. Reads an existing state.sqlite to refresh Timers and Flags as part of the
change; never creates a database. -- ends options, so a subject or outcome may begin with a dash.
${UNKNOWN_OPTION}
Success: exit 0, "closed <subject> in <path>". Failure: exit 1, reason on stderr; the board
stays unchanged. --json emits {path, changed, subject} or {path, error} on stdout; path is null
if home resolution failed. No interactive prompts.

Example: ignite board close "Printer toner reorder" "Order confirmed"
Next: ignite board write -h
`,

  dreamer: `ignite dreamer — memory consolidation for the whole installation

Run one memory consolidation, or enable or disable the nightly consolidation. The Dreamer
consolidates the agents' memory for the whole installation, not for one agent.

Enable and disable affect automatic Dreamer operation for the entire
installation, not only the calling agent. Agents must use these commands only
when explicitly requested by the owner. Do not disable Dreamer as a workaround
for an individual agent's problem.

Commands
  run      Run the nightly consolidation path once and exit.
  enable   Turn on the nightly consolidation and the 48-hour watchdog for every agent.
  disable  Turn them off for every agent.

Next: ignite dreamer COMMAND -h
`,

  'dreamer run': `ignite dreamer run — run one consolidation now

usage: ignite dreamer run [--installation PATH]

Runs the nightly consolidation path once and exits. Never loops and never
waits for 03:00. Does not mark or consume that slot, so the daemon can still
run it the same night.
Takes the installation lock .rbtv/runtime/ignite/memory.lock for checks,
snapshot reads and publication. Releases it before every model call.
Contention at entry waits 5 seconds, then prints a busy result and does not start a run.
A run with nothing to consolidate is quiet: it calls no model.
A digest or failure notice is queued on the direct-message agent's outbox.
digestQueued reports a queued digest; noticeQueued reports a queued failure
notice. Both are false for quiet, busy, or setup-failure results.
The running daemon delivers it. Reported conflicts are saved only after
delivery is confirmed. This command does not confirm delivery, so it leaves
new conflicts unsaved, the same as an unconfirmed nightly digest.
Runs even when dreamer.enabled is false, and does not enable it. The result
says so. Uses dreamer.model; without that key the run is refused.

Installation: --installation, otherwise the installation containing RBTV_AGENT_HOME,
or the walk up to .rbtv/config/ignite/config.json. No Slack call.
Output: one JSON line and nothing else, with the fields ok, busy, quiet, changed, alert,
digestQueued, noticeQueued, delivered (always false here), conflictsSaved, error, enabled
and note. Exit 0 when the run finished without an alert. Exit 1 when the run failed or the
lock was busy. A failure before the run (no installation, an invalid configuration, no
dreamer.model) is the same line, with ok false and the reason in error, and exit 1.
--agent and --json are accepted and have no effect. Any other option is refused with
exit 1 and nothing run.

Example: ignite dreamer run --installation /path/to/installation
Next: ignite dreamer enable -h
`,

  'dreamer enable': `ignite dreamer enable — turn the nightly consolidation on

usage: ignite dreamer enable [--installation PATH] [--json]

Enable affects automatic Dreamer operation for the entire installation, not only the
calling agent. Agents must use this command only when explicitly requested by the owner.

Sets dreamer.enabled to true in .rbtv/config/ignite/config.json. The running
service reads it on its next tick and turns on the nightly consolidation
(03:00 America/Sao_Paulo) and the 48-hour watchdog for every agent.
When dreamer.model is absent, records ${DREAMER_MODEL.harness} ${DREAMER_MODEL.model} effort ${DREAMER_MODEL.effort} there.
The result names the model in use. To change it, edit dreamer.model
(harness, model, effort) in that file.
Already enabled: nothing is written, and the result says so.
Only dreamer.enabled, and dreamer.model when it is recorded, change. Every other setting and
the schedule stay as they are.

Installation: --installation, otherwise the installation containing RBTV_AGENT_HOME,
or the walk up to .rbtv/config/ignite/config.json. No Slack call. --agent is accepted and
has no effect.
Success: exit 0, the new state in plain text, or with --json
{installation, config, enabled, changed, model, modelRecorded}.
Refusal: exit 1, reason on stderr, nothing written. An unreadable or invalid
configuration is refused, and so is any option other than --installation, --json and --agent.

Example: ignite dreamer enable --installation /path/to/installation
Next: ignite dreamer run -h
`,

  'dreamer disable': `ignite dreamer disable — turn the nightly consolidation off

usage: ignite dreamer disable [--installation PATH] [--json]

Disable affects automatic Dreamer operation for the entire installation, not only the
calling agent. Agents must use this command only when explicitly requested by the owner.
Do not disable Dreamer as a workaround for an individual agent's problem.

Sets dreamer.enabled to false in .rbtv/config/ignite/config.json. The nightly consolidation and
the watchdog stop for every agent on the service's next tick. A consolidation already in
progress is not cancelled, and ignite dreamer run still runs one. dreamer.model is kept.
Already disabled: nothing is written, and the result says so.
Only dreamer.enabled changes. Every other setting and the schedule stay as they are.

Installation: --installation, otherwise the installation containing RBTV_AGENT_HOME,
or the walk up to .rbtv/config/ignite/config.json. No Slack call. --agent is accepted and
has no effect.
Success: exit 0, the new state in plain text, or with --json
{installation, config, enabled, changed, model, modelRecorded}.
Refusal: exit 1, reason on stderr, nothing written. An unreadable or invalid
configuration is refused, and so is any option other than --installation, --json and --agent.

Example: ignite dreamer disable --installation /path/to/installation
Next: ignite dreamer enable -h
`,
};

function helpPage(command, tail) {
  return PAGES[`${command} ${tail[0]}`] || PAGES[command];
}

module.exports = { PAGES, helpPage };

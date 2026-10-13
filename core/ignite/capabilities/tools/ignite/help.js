'use strict';

// API — PAGES maps a group or one of its verbs to its help text: 'schedule', 'schedule add', ...
// helpPage(command, tail) → the page for tail[0] when it is a verb of the group, else the group page,
// or undefined when the command has no page here.
// A usage form appears only on the page of the command it invokes; a group page lists its verbs and
// points to their pages.

const { MIGRATION_COMMAND } = require('./config.js');

const HOME = `Home: RBTV_AGENT_HOME, otherwise --agent <slug> --installation <path>. A home that is not an
existing folder is refused, and nothing is created.`;

const SCHEDULE_CONTEXT = `${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.`;

const SCHEDULE_COMMIT = `If SQLite commits but board refresh fails, exit 0 reports the id and "committed; board refresh pending"
(--json adds warning). Do not repeat the mutation. The next board write or turn refreshes Timers from SQLite.`;

const REFUSED_WORDS = `An option this command does not have, an option whose value is empty or only spaces, and a word
beyond those in the usage line are each refused, and nothing changes.`;

const CADENCE = `Cadence (exactly one of --at, --cron, --every; an empty cadence is refused):
  --at <ISO datetime with offset>
      One time, for example 2026-10-09T09:00:00-03:00. The offset or Z is required, so
      --tz is refused. The timer is disabled after it fires.
  --cron "<5-field>" --tz <IANA zone>
      Recurring. Cron requires an explicit --tz. The next occurrence is timezone-aware.
  --every <duration>
      A fixed-interval recurrence: 30s, 5m, 2h or 1d. It is elapsed time with no
      timezone, so DST does not move it and --tz is refused.`;

const CHECK = `  --check <path or command>
      A check tool the waking service runs when the timer is due, before any model starts. It
      answers nothing new, something new with details, or failed; only something new wakes the
      agent. One executable and no arguments. With a / or \\ it is a path relative to the agent
      home, for example tools/mail-check.js or ./mail-check.js; an absolute path or one holding
      .. is refused. Without one it is a command found on PATH. Stored with / separators.`;

const PAGES = {
  schedule: `ignite schedule — timers

Add, list, change, or cancel a timer. A timer wakes the agent in a fresh conversation when it is due.
Timers on _artifacts/board.md show enabled schedules with a next fire and pending/running wakes.

Commands
  add     Add a timer: one time (--at), a cron schedule (--cron --tz) or a fixed interval (--every).
  list    List this agent's timers.
  change  Change a timer's cadence, note, report mode, check tool or enabled state.
  cancel  Cancel a timer.

Next: ignite schedule COMMAND -h
`,

  'schedule add': `ignite schedule add — add a timer

usage: ignite schedule add (--at <ISO datetime with offset> | --cron "<5-field>" --tz <IANA zone> | --every <duration>)
                           --note <text> [--subject <title>] [--report always|when-useful]
                           [--check <path or command>] [--conversation <key>] [--json]

Adds one enabled timer to this agent.

${CADENCE}

Other options:
  --note <text>
      Required, non-empty. What the timer is for; ignite schedule list shows it.
  --subject <title>
      Links the timer to a board subject. A non-empty one-line title. Omitted means none.
  --report always|when-useful
      Report mode stored with the timer. Default: when-useful.
${CHECK}
      Omitted means none: every firing wakes the agent.
  --conversation <key>
      The conversation the timer belongs to. Default: IGNITE_CONVERSATION, which the waking
      program sets inside a turn. It must be a conversation in this agent's history; outside
      a turn, pass it.

${SCHEDULE_CONTEXT}
Writes this agent's runtime/ignite/state.sqlite and refreshes Timers on _artifacts/board.md. A valid
<home>/_artifacts/board.md must exist before SQLite is opened; otherwise the command refuses
and changes nothing.
${SCHEDULE_COMMIT}
Success: exit 0, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>"; --json {schedule, warning?}.
Refusal: exit 1, reason on stderr, with or without --json. An option given twice is refused
("duplicate flag --<name>").
${REFUSED_WORDS}
No Slack request or prompt.

Example: ignite schedule add --cron "0 9 * * 1-5" --tz America/Sao_Paulo --note "Check the inbox"
Next: ignite schedule list
`,

  'schedule list': `ignite schedule list — list this agent's timers

usage: ignite schedule list [--json]

Prints one line per timer, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>
enabled=<true|false> <note>", or "no schedules" when there are none. A timer with a check tool
prints "check=<path or command>" before its note. --json prints {schedules}; each has check_tool,
null for none.
A read: it changes no timer, but it creates runtime/ignite/state.sqlite when the agent has none.

${SCHEDULE_CONTEXT}
Exit 0, or 1 with the reason on stderr when the home cannot be resolved.
${REFUSED_WORDS}

Example: ignite schedule list
Next: ignite schedule change -h
`,

  'schedule change': `ignite schedule change — change a timer

usage: ignite schedule change <id> [--at <ISO datetime with offset> | --cron "<5-field>" [--tz <IANA zone>] | --every <duration>]
                              [--note <text>] [--report always|when-useful] [--check <path or command>]
                              [--enabled true|false] [--json]

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
${CHECK}
      Replaces or adds the check tool. No option removes one: cancel the timer and add it again.

${SCHEDULE_CONTEXT}
Writes this agent's runtime/ignite/state.sqlite and refreshes Timers on _artifacts/board.md. A valid
<home>/_artifacts/board.md must exist before SQLite is opened; otherwise the command refuses
and changes nothing. A missing <id> is refused: "schedule change requires an id"; an unknown one:
"unknown schedule: <id>".
${SCHEDULE_COMMIT}
Success: exit 0, "<id> <cadence> <timezone> next=<next fire in epoch milliseconds>"; --json {schedule, warning?}.
Refusal: exit 1, reason on stderr, with or without --json. An option given twice is refused
("duplicate flag --<name>").
${REFUSED_WORDS}

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
Refusal: exit 1, reason on stderr, with or without --json.
${REFUSED_WORDS}

Example: ignite schedule cancel 7f3c2a10
`,

  'schedules-due': `ignite — schedules-due help

usage: ignite schedules-due --now <ISO datetime>

Enqueue a fresh conversation with no thread or resumed session; input is the schedule id only.
One wake per timer and occurrence: a wake already recorded is "duplicate" and is not recorded again, and
another timer's pending wake never blocks one. A timer advances only once its wake is recorded.
A timer with a check tool is reported as "check" and left due: this command runs no check.
Never enqueues for a held or stopped schedule, and never clears a hold.
${REFUSED_WORDS}
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
but it creates runtime/ignite/state.sqlite when the agent has none. An option given twice is refused
("duplicate flag --<name>").
${REFUSED_WORDS}

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
Nothing is changed on a refusal.
${REFUSED_WORDS}
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
Nothing is changed on a refusal.
${REFUSED_WORDS}
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
agent does not have.
${REFUSED_WORDS}

Example: ignite work stop 4d1e9b
Next: ignite work status
`,

  wake: `ignite — wake help

usage: ignite wake --conversation <key> --note <text> [--work <id>]

Worker completion. Enqueues a continuation. Does not clear a hold.
${REFUSED_WORDS}
`,

  post: `ignite — post help

usage: ignite post (--text <text> | --text-file <path> | --file <path>)... [--audio] [--thread <thread>]

Without --thread, opens a new thread in the agent's channel. --thread selects an existing conversation in this agent's stored history: its full team:channel:root-ts key or a unique root timestamp. Unknown or ambiguous targets are refused.
The post joins that conversation's history after delivery; its session and prior history stay intact.
Enqueues delivery and activates the target. Prints "<conversation key> activated"; --json returns conversationKey, outboxId, clientMsgId, activated and channel. Exit 0 means queued; errors go to stderr with exit 1.
${REFUSED_WORDS}
No Slack request or interactive prompt in this command.
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

usage: ignite board write --file <path> [--revision REVISION] [--json]

Reads a complete UTF-8 Markdown candidate; creates or updates <home>/_artifacts/board.md.
Exactly one --file <path> is required. --revision is the revision from the checked read.
When it is set, a stale revision is refused and the board is not written. Omit it only
when the caller has no revision to send.

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
A seventh watch-out, subject or closed line is kept. The turn receives a derived
board view of at most 6,000 Unicode code points. Omitted watch-outs stay on the
canonical board; the view names them and requires a read before acting. Invalid
writes are refused, never truncated. There is no 6-item board quota and no
3,000-character knowledge cap. Profile is 4,000 code points. Learned rules are
30. On-demand knowledge warns at 100 nonempty lines and splits at 300.

${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack access. Reads an existing runtime/ignite/state.sqlite to refresh Timers and Flags as part of the
write; never creates a database. -- ends options.
${REFUSED_WORDS}
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
A closed line is kept. board close appends; it does not refuse because a count
was reached. Nothing is pruned automatically.

${HOME}
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack access. Reads an existing runtime/ignite/state.sqlite to refresh Timers and Flags as part of the
change; never creates a database. -- ends options, so a subject or outcome may begin with a dash.
${REFUSED_WORDS}
Success: exit 0, "closed <subject> in <path>". Failure: exit 1, reason on stderr; the board
stays unchanged. --json emits {path, changed, subject} or {path, error} on stdout; path is null
if home resolution failed. No interactive prompts.

Example: ignite board close "Printer toner reorder" "Order confirmed"
Next: ignite board write -h
`,

  runtime: `ignite runtime — move one agent's Ignite records

Moves this agent's database, conversations and turn records from the agent
folder root into runtime/ignite/. A new agent already uses that folder.

Commands
  migrate   Copy, check and publish this agent's Ignite runtime.

Next: ignite runtime migrate -h
`,

  albert: `ignite albert — fence, drain and migrate the legacy publisher

usage: ignite albert <fence|drain|migrate|report|cleanup|probe|verify|recover>
       [--installation PATH] [--dry-run]

fence writes the legacy fence and stops a later publisher from being treated as
the only writer. drain refuses while the publication lock is held. migrate
reads each source agent's settings key dreamer and transfers its cursor.
migrate --dry-run prints that plan and writes nothing. cleanup removes the
legacy dreamer section from the Ignite config. probe prints "dreamer keys absent"
only when that section is gone. recover disables Albert's schedules and removes
the fence. It does not start a publisher. The proposal structure is taught by
albert apply -h, and only there.

Example: ignite albert fence --installation /path/to/installation
`,

  'runtime migrate': `ignite runtime migrate — publish this agent's Ignite runtime

usage: ${MIGRATION_COMMAND}

Copies the database, its sidecars, conversations/ and turns/ from the agent
folder root into runtime/ignite/. Refuses when the waking service holds
.rbtv/runtime/ignite/daemon.lock, when the layout is ambiguous, or when an
active run or outbox row has a path that cannot be moved. After a successful
publish the old files are in runtime/ignite-premigration/.

A new agent needs no migration. Its database is runtime/ignite/state.sqlite.

Home: RBTV_AGENT_HOME, otherwise --agent SLUG --installation PATH.
Success: exit 0, "migrated <agent>". Refusal: exit 1, reason on stderr, and the
old files stay where they were. No Slack request.

Example: ${MIGRATION_COMMAND} --agent master --installation /path/to/installation
`,
};

function helpPage(command, tail) {
  return PAGES[`${command} ${tail[0]}`] || PAGES[command];
}

module.exports = { PAGES, helpPage };

# Ignite agents — operator runbook

One process per installation, unit `rbtv-ignite-agents.service`. It runs from the deploy folder (a git worktree of its own, named in the unit's `ExecStart` line), not from a working tree other sessions edit. Config is `<installation>/.rbtv/config/ignite/config.json`. It names the environment variables that contain Slack's tokens (`appTokenEnv`, `botTokenEnv`, `ownerTokenEnv`); the values live in the process environment or `<installation>/.rbtv/config/env/.env`, never in the config file. An unset variable the daemon needs refuses startup and names the variable; the value is never printed. Nothing under `.rbtv/modules/ignite/` is read or created.

## Deploy

```
ignite deploy --dry-run
ignite deploy
```

`ignite deploy [COMMIT]` deploys the service at a commit and confirms the result; `ignite deploy -h` owns its options. Run the dry run first: it prints the commit, the installation, the deploy folder, the exact script command and the deploy log it would append to, and it runs and writes nothing. Linux only.

- **Commit.** `COMMIT`, or the HEAD commit of the repository that holds the `ignite` program that was run. The command prints the full id.
- **Installation.** `--installation`, or the installation that holds the current folder.
- **Deploy folder.** `--deploy-folder`, or the environment variable `RBTV_DEPLOY`, or the folder the installed unit file already runs from. A first deploy has no installed unit, so it names the folder: `ignite deploy --deploy-folder <worktree>`. The folder is an existing git worktree that has the commit.

The command then runs `deploy.sh`, the script beside the `ignite` program, with those three values. The script checks the deploy folder out detached at the commit, fills the unit template (`EnvironmentFile` is `<installation>/.rbtv/config/env/.env`), runs `systemctl --user daemon-reload`, enables and restarts `rbtv-ignite-agents.service`, and prints the commit. The env file must exist or the script refuses. Running a deploy again at the same commit is safe.

After the script, the command waits up to 30 seconds for the service to answer active three times in a row with the deploy folder at the commit, then prints the commit before, the commit now and the service state. When the script fails or the service does not stay active, it exits 1 with the last 20 journal lines. The restart reaches every agent of the installation; a turn in progress is left running (Stop and start, below).

**From inside an agent's turn.** A deploy restarts the service, so an agent never runs it inside its own turn. It runs `ignite deploy COMMIT --after-turn`, which checks the commit at once and records the request. The daemon then runs the deploy once no turn of any agent is running, as a `systemd-run` job that outlives the restart and carries the service's own PATH. The deploy log line comes back to the conversation that asked: as a wake when its work waits for workers (end the turn with `waiting_workers` and a worker of kind `deploy`), otherwise as a post. One request waits at a time.

**Undo.** When the deploy folder's commit changed, the output of a success and of a failure ends with one line to copy: `to undo: ignite deploy <full id of the commit before> --deploy-folder <folder> --installation <installation>`. Running it deploys the commit that was there before, to the same folder and installation. No undo line is printed when the commit did not change. With `--json` the same command is the field `undo`, `null` when there is none.

**Deploy log.** Every deploy that ran the script appends one line to `<installation>/.rbtv/runtime/ignite/deploys.jsonl`, and the output names that file once. A refusal and a dry run write nothing. Each line is one JSON object:

| Field | Value |
|---|---|
| `time` | When the result was known, ISO 8601 in UTC |
| `commitBefore` | The full id the deploy folder held before |
| `commitAsked` | The full id of the commit the deploy asked for |
| `commitAfter` | The full id the deploy folder holds afterwards; `null` when it could not be read |
| `deployFolder` | The deploy folder |
| `outcome` | `ok`, or `failed` when the script failed or the service did not stay active |
| `reason` | Only on `failed`: the reason, in one line |

When the line cannot be written, the command prints a warning on stderr that names the file, and its exit code does not change: a deploy that succeeded still exits 0. No command reads the log; read it with `cat` or `tail`.

## Status

```
systemctl --user status rbtv-ignite-agents.service
journalctl --user -u rbtv-ignite-agents.service -f
```

Log lines are JSON on stdout. `event` is `ready`, `turn`, `schedules-due`, `turn-left`, `stop`, `board`, `check`, `memory-alert-failed`, `payments` (the payment gate's service side, with an `action`) or `payment-webhook` (each withdrawal validation answer).

Stop and start:

```
systemctl --user stop rbtv-ignite-agents.service
systemctl --user start rbtv-ignite-agents.service
```

Stop sends SIGTERM. The process stops claiming, logs any in-flight run (`turn-left`), and exits without killing that child. `KillMode=process` leaves the child in place. The next start treats a still-live child as the active run and does not launch a second one. A dead child is recovered as a failed attempt. A second process exits non-zero: `daemon already running`.

## Agents

Managing an agent's files and launch values uses `rbtv agent`; connecting and disconnecting it uses `ignite connect|disconnect`. Flags: see `ignite -h`.

## Memory consolidation

Albert consolidates memory. The waking service does not run a separate consolidation and has no `ignite dreamer` verb. Albert's schedules are `albert-nightly` at 03:00 America/Sao_Paulo, `albert-watchdog` every hour, and `albert-friday` at 08:45 America/Sao_Paulo on Friday. Use the ordinary schedule commands for those timers. `ignite remember` still appends one line to the shared inbox.

A configuration that still carries a `dreamer` section loads. Nothing acts on those keys. The next write of `.rbtv/config/ignite/config.json` omits the section. `ignite albert cleanup --installation <installation>` does that write and prints `cleaned`. `ignite albert probe --installation <installation>` prints `dreamer keys absent` only when the section is gone. Until cleanup, leave the section in place.

`ignite albert recover` disables Albert's three schedules and removes the fence. It does not start a publisher. If this candidate must be undone after deploy, redeploy the common candidate, which still contains the retired runner, and do not run cleanup first.

The agent's database is `<home>/runtime/ignite/state.sqlite`. Conversations and turns are under `<home>/runtime/ignite/` as well. A layout that still has those files at the agent root is migrated with `ignite runtime migrate`, not by copying them by hand.

Publication, `remember` and every board write share `.rbtv/runtime/ignite/memory.lock`. Exclusive creation takes the lock; contenders retry with a short backoff for about five seconds, then fail visibly and can be retried. The lock records its holder pid, hostname and unique token. Reclaim requires all three: age greater than 60 seconds, the same hostname, and `process.kill(pid, 0)` failing with `ESRCH`. A live holder is never displaced. No lock spans a model call. Board writes, `remember` and the board refresh in `schedules-due` keep the lock only for their own read, modify and write.

Profile is at most 4,000 characters. Learned rules are at most 30. On-demand knowledge warns at 100 nonempty lines and splits at 300 complete records. A record that does not fit is left unchanged and reported; it is not split, trimmed or truncated to evade a cap. A whole proposal with a wrong shape is refused with its real reason. Limits live in `core/memory/capabilities/tools/memory/lib/`.

## Inspect

```
ignite --agent <slug> --installation <installation> work status
```

Entry point, if the PATH link is not installed yet: `node <deploy>/core/ignite/capabilities/tools/ignite/cli.js`.

## Post into an existing thread

Use a full conversation key from the agent's stored history, or its root timestamp when unique:

```
ignite --agent <slug> --installation <installation> post --thread <team>:<channel>:<root-ts> --text "Check complete"
```

The command prints `<conversation key> activated` and queues delivery; `--json` returns `conversationKey`, `outboxId`, `clientMsgId`, `activated` and `channel`. Exit 0 means queued, not delivered. The confirmed post joins that thread's history. Unknown or ambiguous targets fail with exit 1 and an error on stderr; use the exact key in this agent's history to resolve ambiguity. Omitting `--thread` starts a new conversation. `--text-file`, `--file` and `--audio` also work with a thread target.

Each timer wake starts with a new conversation key and harness session, with no thread or earlier conversation history. Its input is only the schedule id. A later wake stays fresh even after an earlier result opens a Slack thread; schedules are never moved during that binding.

Timers that are due together each get their own wake: a wake is identified by its timer and occurrence, and a timer advances only once its wake is recorded. A timer may name a check tool with `schedule add --check` or the `check` key of `connect --schedule-json`; `ignite schedule list` prints it as `check=`. Read [Timer check](timer-check.md) for the stored form, the three answers and the store calls before changing or debugging a timer that has one.

## Write or close a board subject

Use `ignite board write -h` for the checked form. Copy `<home>/_artifacts/board.md` to a candidate file, edit its subjects or watch-outs, then submit it:

```
ignite --agent <slug> --installation <installation> board write --file "board candidate.md"
ignite --agent <slug> --installation <installation> board close "Subject title" "One-line outcome" "[discussion](https://example.com/thread)"
```

The close thread is optional. All four sections must be present, even when empty. Keep Timers, Recently closed and existing Flags unchanged in a candidate. New subjects use Flags `none`. `write` reports the board path and whether bytes changed; `close` reports the title and path. `--json` returns `{path, changed, subject?}` on success or `{path, error}` with exit 1 on failure (`path` is null before a home is resolved). Validation refuses malformed input without changing the board. Close records a dated outcome. A seventh closed entry and a seventh watch-out are kept. There is no item quota. No entry is truncated or automatically pruned. The turn receives a derived board view of at most 6,000 Unicode code points; omitted watch-outs stay on the canonical board. Legacy boards require reshaping before using the checked commands; runtime board commands never read or copy the legacy path.

`connect` first turns on the `ignite` pack through `rbtv agent add <home> --pack ignite`, then creates missing working files: the four-section board at `<home>/_artifacts/board.md`, and `state.sqlite`, `conversations/` and `turns/` under `<home>/runtime/ignite/`, before it makes a Slack request. Its working-file setup may copy `<home>/board.md` once, preserving its bytes and leaving the old file untouched. Once the new path exists, Ignite reads and writes only that path. `disconnect` removes the Slack route and timers first, then turns the pack off through `rbtv agent remove <home> --pack ignite`; it keeps the agent folder and working files.

Schedule add/change/cancel and connection timer binding require an existing, valid `<home>/_artifacts/board.md` and safe write path before they open SQLite. A missing or invalid board refuses with a message naming that path; SQLite remains unchanged, and an absent database is not created. Disconnect timer changes use the same board check before changing schedules. If SQLite commits but the subsequent board refresh fails (including lock contention), the command still exits 0 and reports `<id> committed; board refresh pending`. Disconnect lists all cancelled timer ids. JSON retains the normal success fields (`schedule`, `cancelled`, `scheduleId` or `timers`) and adds `warning` with the same message and id(s). Do not repeat the mutation: the next successful board write/close, schedule tick or turn refreshes from SQLite.

Ignite regenerates the Timers table from schedules after add/change/cancel, connect/disconnect timer changes, board write/close with an existing agent database, every schedule tick, and before a turn reads its board. Board write/close validates the supplied runtime fields against the current board, then refreshes Timers and Flags under the same lock before saving. It never creates a database. Columns are `Fires | Timer | For | Subject`: next fire as `YYYY-MM-DD HH:MM <IANA zone>`, schedule id, note, and subject. Cron uses its configured zone; elapsed intervals and one-shot offsets display in UTC. Rows are ordered by fire time and id, and are outside the board's line cap. Enabled timers with a next fire are shown. A disabled timer with a pending or running wake keeps its row and scheduled fire time until that wake finishes, so a one-shot wake can still read its note. Otherwise disabled, spent and cancelled timers are omitted.

`schedule add --subject "Subject title"` stores an optional subject association; without it, Subject is `none`. Schedule changes and recurring fires preserve the association. For example:

```
ignite schedule add --every 1h --note "Check the draft is ready" --subject "Draft review"
```

The runtime sets subject Flags through `board.js`, using owner replies stored for linked Slack threads. A reply sets `answered YYYY-MM-DD`; after seven elapsed days without another owner reply it becomes `idle since YYYY-MM-DD`, dated from that last reply. With no reply yet, the clock starts at the latest linked thread root. Dates are UTC. A newer owner reply clears idle; bot messages, other users and synthetic transcript rows do not reset it. A subject with several threads uses the latest owner reply across them. Links may use Slack permalinks or a permalink with `thread_ts`; subjects without a dated Slack thread retain their flags. Refresh runs on owner ingress even while the agent is held, and on ticks even when no timer is due. No subject is automatically closed or deleted. A refused runtime refresh preserves the board and reports its failure. Turn-start checks recover broken boards as described below; a valid board whose refresh fails is injected with a visible warning.

## Turn memory and recovery

Every turn, including a timer wake and a resumed harness session, rereads and injects:

- `<installation>/.rbtv/memory/profile.md`
- `<home>/memory/learned.md`
- `<home>/_artifacts/board.md`
- `<installation>/.rbtv/memory/_artifacts/index.md`
- `<installation>/.rbtv/memory/inbox.md`

Here installation means the rbtv installation folder containing `.rbtv/agents/<slug>`, resolved from the agent home, never the deploy checkout or the shell's current directory. General memory has one fixed location per installation. A file at `.rbtv/memory/workspaces/<slug>.md` is injected only when the turn's working directory equals or is below one of its installation-relative `paths:`. Paths accept a YAML inline list or indented string list, including quoted paths with spaces; absolute paths and `..` are refused. Prefix siblings do not match. Turns currently start in the resolved agent home. A matching file deleted from the working tree can still be discovered in HEAD.

The check in `memory.js` accepts UTF-8 with LF or CRLF. Profile uses `Who`, `Working with <owner>` and `Now` sections, dated fact bullets, and at most 4,000 characters. Learned rules have at most 30 bullets, each starting with `[correction]` or `[inferred]`, a `Why:` clause and dated provenance; inferred rules need two distinct conversation links. Workspace notes require their frontmatter, dated bullets and at most 3,000 characters. The root index requires an `Open | When` table with no row cap. Inbox records have dated provenance, with an optional heading and no enforced length cap. The board uses `board.js`'s checked form.

When a file is missing, unreadable or fails its check, Ignite saves readable rejected bytes beside it as `<file>.broken-<uuid>` before trying `git show HEAD:<repo-relative-path>`. The HEAD copy must pass the same check. It is injected without overwriting the working file, preserving uncommitted inbox records and other evidence. Recovered boards still render current timers and flags in the prompt. If git, HEAD or a valid committed copy is unavailable, the prompt contains a visible `MISSING MEMORY` note. The turn continues and an owner alert is queued through the current conversation's outbox. Failure to save the broken copy is reported and leaves the original untouched. If the alert cannot be queued, the prompt asks the agent to tell the owner and the runtime logs the delivery failure. None of these memory failures creates a hold. Workspace notes with no readable paths in either copy are never injected; their failure is still reported.

## Remember an owner fact

```
ignite remember "Prefers afternoon appointments"
ignite --agent <slug> --installation <installation> remember "Prefers afternoon appointments"
```

`remember` appends one UTF-8 line to `.rbtv/memory/inbox.md` with the UTC date, agent slug and current Slack thread link when available. Newlines in the supplied text become spaces. The shared installation lock and a single append write preserve concurrent agents' lines; an absent inbox starts as a headerless list. Existing bytes are never rewritten, even if the inbox is malformed or missing its final newline. The command never writes `learned.md` and never refuses for length or inbox format. Above 20 bullet lines (lines starting with `- `; headings, blanks and other prose do not count), it queues an owner alert in the current conversation, or the agent's configured channel/DM outside a turn. Alert setup or delivery-queue failure leaves the append successful and produces a visible warning.

Success prints `remembered in <path>` followed by any warning and exits 0. `--json` returns `{path, appended, lines, warning}`; `lines` counts bullet lines, `warning` is null when none, and `lines` is null if counting fails after append. Missing text, text empty after newline normalization and trimming, a home that is not an existing folder, an unresolved installation root or a filesystem write failure exits 1, with an error on stderr or `{path, error}` on stdout in JSON mode. Empty text reports `remember requires non-empty text` before resolving the installation or writing files. `path` is null if no inbox path was resolved. `--help` works without configuration; use `--` before literal option-like text. Repeating the command appends another record.

## Watch-outs and unread messages

An inbox line is the owner's explicit remember request. Albert files supported lines into profile, knowledge or entities and removes only what it filed or verified as already known. A watch-out stays on the board until Albert folds it into a learned correction with the required owner evidence. A seventh watch-out is kept. The turn's board view is at most 6,000 Unicode code points and is not the board.

Each source agent's settings key `dreamer` still holds `{ cursor, lastSuccessAt, commit, reportedConflicts }` until `ignite albert migrate` has transferred the cursor. Do not delete that key by hand before migrate. After migrate, Albert's own cursors are the writer state.

## Repair a hold

A hold survives ticks and restarts. Set a launch setting that does not use the failed model, then retry. `work retry` with no id clears only an agent hold; with an id it clears only that work hold.

```
rbtv agent configure <slug> --harness <harness> --model <cast short name> --effort <rung word>
ignite --agent <slug> --installation <installation> work retry
ignite --agent <slug> --installation <installation> work retry <work-id>
```

The setting applies from the next turn in every conversation of that agent.

## Agent panel

`/agent` opens, for the owner only, a modal about the agent of the channel it is typed in: the agent `routes` maps the channel to, or `dmAgent` in a direct message. Its tabs read the agent's `agent.json`, `prompt.md`, `_artifacts/board.md`, its store (schedules, open work, the running turn, the `notes` table `ignite status --note` writes) and cast's handle registry (`~/.cast/handles.jsonl`, the launches whose `launcher` is the agent's folder), and change nothing. A launch made before cast recorded `launcher` is not listed as anyone's sub-agent. Approvals shows the agent's payment requests with the payment panel's own Approve and Refuse buttons: an approval asks for the PIN there and the gate decides, exactly as in `/payments`; after it the agent panel is drawn again. A form pushed before a service restart redraws `/payments` instead, since the agent panel it came from is remembered only in memory. Docs lists the agent's recent Markdown outputs; Open in canvas writes one into the agent's channel canvas (one per channel on Slack's free plan), refused while that canvas holds edits nobody saved or something Ignite did not open (`ignite docs open PATH --force` replaces it). Save canvas (or `ignite docs save`) writes an edited canvas to the agent's tracked `output/ignite/canvas/<time>-<name>.md`, headed by the document it came from; Docs lists each save until the agent brings it into that document and deletes it. The open document is the agent store's `settings` row `docs_canvas`. A link to another repository file goes in escaped (Slack refuses it as a link), and Markdown Slack refuses, such as a bullet list inside a numbered list, fails the open with Slack's reason and leaves the canvas as it was; lines of one paragraph come back in a save joined by spaces. The bot token needs `canvases:write` and `files:read`; the direct-message agent has no channel canvas, so its Docs tab cannot open a document. Anyone else, and a channel no agent answers in, gets a one-line refusal. **Owner setup:** in the Slack app (api.slack.com), under Slash Commands, create `/agent` with no request URL, as for `/payments`; reinstall the app if Slack asks. A Slack call that fails is logged as `{ event: 'agent-panel', action: 'failed' }`; another user's tab button as `{ event: 'agent-panel', action: 'refused' }`.

## Payments

The [payment gate](../../../glossary/payment-gate.md)'s service side runs when `config.json` has a `payments` section: `"payments": {}` takes the defaults, port 8787, the connector `asaas`, the time zone `America/Sao_Paulo` and the currency `BRL` (keys `webhookPort`, `connectors`, `timeZone`, `currency`; `providers` is the older spelling of `connectors`, accepted until the next deploy). Add it, then restart the service; the service reads it at start. Without it, `ignite payment` refuses and `/payments` answers that payments are not set up. A connector with no withdrawal validation adapter is logged at start as `{ event: 'error', what: 'payment-connector' }`, and Ignite sends nothing through it.

**Owner setup.** Acts only the owner can do:

1. **Slack app** (api.slack.com, the app Ignite runs as): under Slash Commands, create `/payments` (no request URL is needed over Socket Mode); turn Interactivity on (no URL either); reinstall the app if Slack asks.
2. **Token.** Put the connector's token variable, `ASAAS_WEBHOOK_TOKEN=<long random value>` for asaas (its adapter names it), in `<installation>/.rbtv/config/env/.env`, and the same value in the bank's webhook settings. The service reads it on every call.
3. **Bank.** Asaas: User menu > Integrations > Security mechanisms: the withdrawal validation webhook at the public address that reaches `http://127.0.0.1:<port>/asaas/withdrawal-validation`, with the token; the IP whitelist with the server's address; "Evento crítico em requisições de saque" off. The public address (a reverse proxy passing only that path) is installation setup, not part of Ignite.
4. **PIN and settings.** Run `/payments` in Slack: it asks for a PIN of 4 to 12 digits on first use, then shows the panel. The mode is off until the owner saves settings.

**Inspect.** The ledger is `<installation>/.rbtv/runtime/ignite/payments.sqlite`, table `payments`; the settings (with their revision) and the PIN lockout are its table `gate`; the keys of the owner's handled Slack interactions are its table `interactions`. An agent reads its own requests with `ignite payment list` and `ignite payment show <id>`. Read the ledger, never edit it: a row's state decides what the withdrawal validation approves.

**Forgotten PIN.** Delete `<installation>/.rbtv/config/ignite/payments-pin.json` on the server; the next `/payments` asks for a new one. Five wrong PINs in a row lock every PIN form for 15 minutes; waiting is the only unlock.

**An uncertain request.** A send whose answer was lost (the tool timed out or crashed), a send a stop cut off (logged at the next start as `{ event: 'payments', action: 'interrupted' }`), and any request with an operation id or a withdrawal approval that would otherwise fail become `uncertain`: the money may have left, so the request keeps counting toward the limits and `/payments` lists it. The runner reads it with `pay status` every minute once it has an operation id (its own, or the one the withdrawal validation approved) and makes it `sent`, or `failed` when the bank ended it so. One with no operation id stays uncertain, counted in its own day, week and month; check `asaas statement` before the agent asks again.

**The listener.** `{ event: 'payment-webhook', action: 'listening', port }` at start; `{ event: 'error', what: 'payment-webhook' }` when the port is taken; then no call reaches Ignite and Asaas cancels each operation after three failed calls. Each answer is logged with the request id, `APPROVED` or `REFUSED`, and the reason. The listener runs in its own thread with its own ledger connection; a ledger another process still holds 600 ms after a call arrived is answered `REFUSED` with `the ledger is busy`, and Asaas cancels that operation.

**A request Ignite could not check.** The service resolves each pending request's recipient through the connector before posting it; after three failed tries 30 s apart the request is posted with the failure and Refuse alone, and it can never be approved or sent. Refuse it; the agent can ask again. A request the owner approved under an earlier release, before any check, is failed by the runner instead of sent.

**Slack.** Ignite acknowledges every Socket Mode envelope as it arrives and processes it after. A submitted PIN or settings form shows "Checking…" and then its outcome; when Slack refuses that update, the form shows the outcome as text ending "The panel could not refresh". A form left on "Checking…" means no update reached Slack: reopen `/payments`, which shows the ledger's state. An owner message whose processing fails after its acknowledgement is logged as `event failed after its ack` and is not delivered again by Slack.

## Known behaviour

Queued turns. One primary turn per agent. Agents do not wait on each other. A message saved while that agent is busy stays in its queue and is claimed when the turn ends. Owner input is claimed before an automatic continuation. Saving a message is not the same as starting the turn. The latest message of each conversation's thread, a reply included, shows the conversation's [live status](../../../glossary/live-status.md) as reactions: the system state on the left, then the agent state while its work runs or the task state once its replies are delivered. When a newer message arrives the reactions move there, and the message they leave keeps only the task emoji it shows. The emoji are in the Slack connector's `capabilities/tools/slack/lib/live-status.js`. `/legend` in Slack opens, for whoever types it, a modal that explains each reaction, built from those emoji and the states and meanings in `live-status.js`; the Slack app needs the `/legend` slash command, created under Slash Commands with no request URL over Socket Mode, as `/payments` is. A legend that cannot open is logged as `{ event: 'legend', action: 'open-failed' }`. The store's `live_status` table holds one row per message Ignite knows about in a conversation: its state, in `kept` the task it keeps once the status leaves it (with `kept_for`, the owner message that task, or the reply the message belongs to, answers), and in `shown` the reactions the service's ticker has put on it (with any whose call went unanswered as `unsure`), so a reaction that looks wrong is checked there first: `SELECT channel, ts, system, agent, task, kept, run_id, shown FROM live_status ORDER BY rev DESC LIMIT 5`. A reply's text and each of its files are separate Slack messages: its outbox row's `posted` lists the ts of each, and the newest carries the status. A restarted service brings each message from its `shown` to its state; a NULL `shown` (a row made before the column) is unknown, and every live status reaction is removed from that message before its state is shown; and keeps the shared reaction budget and Slack's 429 pause in `.rbtv/runtime/ignite/live-status-pace.json`. A scheduled wake shows nothing. A reaction error never stops a turn or a delivery: it is logged as `reaction-failed`, a store write that fails as `status-failed`, and an HTTP 429 from Slack as `reactions-paused`, after which no reaction call is made until its Retry-After passes.

Steering between turns. There is no mid-turn interruption. An owner message that arrives during a turn is saved and processed on a later turn.

Voice notes. If transcription fails, Ignite replies: `I could not transcribe that voice note; please send it as text.` The technical error is written only to the service log.

Attachments. When a file attached to an owner message is not downloaded, the turn still runs: the turn message lists the files that were saved and states how many were not, so the agent tells the owner.

Long threads. The prompt carries a bounded recent window (20 messages) plus the path of the full history file under the agent home. The folder name is the conversation key with colons replaced by hyphens. A folder left under the raw key is renamed on first access. The file is regenerated from the store. The store is authoritative.

The unit starts at boot when user lingering is on. Check with `systemctl --user is-enabled rbtv-ignite-agents.service`.

rbtv puts `~/.rbtv/bin` on the user shell PATH. A deploy also prepends it to the service unit's PATH (in `deploy.sh`), since a boot-time user service may not source a shell profile; it adds the directory only when absent. rbtv links `ignite` there. After installing a harness or a tool in a new location, redeploy. Startup refuses to go ready if `ignite` is not on that PATH.

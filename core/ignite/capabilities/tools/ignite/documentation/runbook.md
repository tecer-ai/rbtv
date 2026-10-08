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

Log lines are JSON on stdout. `event` is `ready`, `turn`, `schedules-due`, `turn-left`, `stop`, `dreamer`, `dreamer-watchdog`, `dreamer-alert`, `board`, or `memory-alert-failed`.

Stop and start:

```
systemctl --user stop rbtv-ignite-agents.service
systemctl --user start rbtv-ignite-agents.service
```

Stop sends SIGTERM. The process stops claiming, logs any in-flight run (`turn-left`), and exits without killing that child. `KillMode=process` leaves the child in place. The next start treats a still-live child as the active run and does not launch a second one. A dead child is recovered as a failed attempt. A second process exits non-zero: `daemon already running`.

## Agents

Managing an agent's files and launch values uses `rbtv agent`; connecting and disconnecting it uses `ignite connect|disconnect`. Flags: see `ignite -h`.

## Dreamer

The Dreamer's settings are in the existing `.rbtv/config/ignite/config.json`:

```json
"dreamer": {
  "enabled": true,
  "model": { "harness": "codex", "model": "gpt-6.1-sol", "effort": 3 }
}
```

`dreamer.model` is the proposal model. It must supply all three fields: `harness` is `codex`, `opencode` or `claude`; `model` is a nonempty cast model name without whitespace or a leading dash; `effort` is a JSON integer from 1 to 5. Unknown fields and invalid values are refused. Ignite has no built-in model at run time: while `dreamer.enabled` is true the configuration is refused without `dreamer.model`, and the refusal names the key and an example value. `ignite dreamer run` is refused the same way when the key is absent. To use another model, edit `dreamer.model` in that file. Cast runs from the installation folder, so the installation's model selection applies, and the model works in a temporary launch folder whose task text is `task.md`. Cast checks model availability and its supported effort mapping when called. Manual and nightly runs use the same setting; the daemon reloads it on each tick. Agent `agent.json` settings are independent.

Dreamer ships disabled: omit `dreamer` or keep `"dreamer": { "enabled": false }` for the initial deploy. Both nightly consolidation and the 48-hour watchdog stay off. After `ready`, verify one fresh timer wake has a new threadless conversation and harness session, input equal to its schedule id, and all five checked memory files in its prompt. Only after that proof, with the owner present for the first consolidation, run:

```
ignite dreamer enable --installation <installation>
```

It sets `dreamer.enabled` to true and, when `dreamer.model` is absent, records `codex gpt-6.1-sol 3` there; the result names the model in use. The daemon reloads the configuration on the next tick (normally within 30 seconds); enabling during the 03:00 hour can run consolidation immediately. Otherwise attend the next nightly slot. To turn both the nightly consolidation and the watchdog off:

```
ignite dreamer disable --installation <installation>
```

It sets `dreamer.enabled` to false and keeps `dreamer.model`. It does not cancel a consolidation already in progress. Both commands change only those keys, leave every other setting and the schedule as they are, and write nothing when the requested state is already in force; the result says so. An unreadable or invalid configuration is refused with nothing written. `--json` prints `{installation, config, enabled, changed, model, modelRecorded}`.

Enable and disable affect automatic Dreamer operation for the entire installation, not only the calling agent. Agents must use these commands only when explicitly requested by the owner. Do not disable Dreamer as a workaround for an individual agent's problem.

To consolidate once without waiting for 03:00, and without marking that slot consumed, run:

```
ignite dreamer run --installation <installation>
```

It is one shot: it runs the same quiet-or-consolidation path as the nightly pass, then exits. It does not loop. It takes `.rbtv/runtime/ignite/memory.lock` for the initial work check, each snapshot read and publication, releasing it before every model call. Contention during the initial check prints a busy result and does not start a run. It runs even when `dreamer.enabled` is false, does not enable the nightly run, and the result says so. Use it for the owner-present first consolidation, or for a deliberate catch-up, including while the nightly runner is still off. It queues a digest or failure notice on the direct-message agent's outbox; the running daemon delivers that row. It does not confirm delivery itself, so it does not save new reported conflicts. Ordinary daemon outbox delivery saves the thread key but has no conflict metadata. Only a later consolidation whose own digest delivery is confirmed saves those conflicts. The result is one JSON line, including installation, config, and run-setup failures. Exit 0 means the run finished without an alert or error. A required digest or failure notice that cannot be queued returns `ok: false`, a non-null `error`, and exit 1; this includes a missing `dmAgent` or DM agent store. See `ignite dreamer run -h`.

The JSON result distinguishes `digestQueued` (a consolidation digest was queued) from `noticeQueued` (a failure notice was queued). Both are false for quiet, busy, or setup-failure results, or when enqueueing fails. `delivered` says whether the digest or notice was confirmed delivered; it is always false for the manual command. The daemon's `dreamer-watchdog` JSON log uses the same queue fields for watchdog notices: `digestQueued: false`, `noticeQueued: true` after enqueueing.

When cast fails, the returned `alert`, owner notice and daemon's `dreamer` log `message` contain only a fixed cause: `model out of credits or spending limit` for stderr matching `spending-limit`, `credits`, `insufficient balance` or `quota`; `model rate limited` for `rate limit` or `429`; `model timed out` for a timeout or terminated call; `model authentication failed` for `401`, `403`, `unauthori` or `invalid api key`; otherwise `model failed (exit <code>)`, with `unknown` when no safe exit code is available. Matching is case-insensitive, in that order. Raw stderr, command errors and model stdout are never copied into those surfaces.

Each Dreamer proposal prompt lists current file sizes, caps and remaining room for every writable existing file and the fixed general-memory destinations, plus starting budgets for new files. Counts match validation: Unicode code points including line endings for character caps, rules for learned memory, lines for timelines, and board lines/subjects/watch-outs/closed entries with Timers excluded from the line count. Uncapped files are identified explicitly. The model must stay within each cap; when a fact cannot fit, it must leave the destination unchanged and report a conflict instead of rewriting, compressing, truncating or splitting the file. A cap refusal includes the relative file path and proposed count/cap in the JSON `alert`, owner notice and daemon log `message`, for example `Dreamer failed: .rbtv/memory/knowledge/facts.md: knowledge cap exceeded (3120/3000 characters).` These diagnostics never include file content or the model's explanation.

The watchdog starts a new 48-hour grace period when enabling, retains that start across enabled daemon restarts, and resets it when the daemon observes disabled config. A later success restarts the liveness interval. Disabled time never counts. Let the daemon observe a disable before shutting it down if it will later restart enabled.

An inbox line or board watch-out that repeats an existing fact can be removed as a duplicate. The model cites the existing destination path and exact bullet; code verifies the bullet exists in the snapshot and remains in the result. No new record is written for that duplicate, and the digest lists the removed line as `already known` with its destination. Inbox duplicates use profile, knowledge or entities; watch-outs use the agent's learned rules. Missing citations refuse the run and leave the line in place. The proposal form is documented under Dreamer watch-outs and cursors in `architecture.md`.

When enabled, the existing `rbtv-ignite-agents.service` checks one shared Dreamer slot per daemon process in each 03:00 `America/Sao_Paulo` hour, never as a second service. A busy attempt leaves the slot available for the next tick in that hour after the lock is released. An eligible owner message newer than its agent cursor, an inbox line, or an expired memory record triggers a cast proposal call using `dreamer.model`. Expiry requires a final valid `until YYYY-MM-DD` (with an optional period) in the body before the **last** dated provenance tail, or at the end of a board state line without provenance; the date must be earlier than today's Sao Paulo date.

A slot is quiet when there is no unread owner row, no due expiry, the inbox is empty, and no watch-out can be folded with available owner thread evidence. The daemon directly updates every configured agent's `lastSuccessAt`, keeping its cursor, commit and reported conflicts unchanged. It calls no model, makes no commit, and posts no digest. Deferred watch-outs stay on the board. Consolidation posts a digest only when files changed or a new conflict appears; `settings.dreamer.reportedConflicts` retains conflicts only when that consolidation confirms its own digest delivery, so saved conflicts are not repeated. Unconfirmed delivery leaves new conflicts unsaved; the next consolidation that finds them reports them again. A quiet slot does not retry consolidation. Digests, failures, and a watchdog warning when the last successful run is older than 48 hours are posted in one persisted thread for the configured direct-message agent. Every confirmed Dreamer outbox delivery, including a manually queued notice delivered by the daemon drain or turn pump, saves its conversation key for later notices. Check that `dmAgent` remains configured and that its home is present before you enable memory consolidation.

Dreamer publication, `remember`, migration and every board write share `.rbtv/runtime/ignite/memory.lock`. Exclusive creation takes the lock; contenders retry with a short backoff for about five seconds, then fail visibly and can be retried. The lock records its holder pid, hostname and unique token. Reclaim requires all three: age greater than 60 seconds, the same hostname, and `process.kill(pid, 0)` failing with `ESRCH` (no such process). A live holder is never displaced; foreign-host or unknown owner records and other liveness errors stay busy. `ignite dreamer run`, the nightly pass and direct consolidation all lock each snapshot read, release before every model call, then reacquire for the unchanged-since-read comparison, writes, commit, cursor updates and any rollback. If files changed meanwhile, publication releases the lock and retries once with a fresh snapshot. The installed runner also locks its initial work check and any quiet success update. No lock spans model calls or outbox delivery. Board writes, `remember` and the board refresh in `schedules-due` keep it only for their own read/modify/write, so they can finish while the model is running. Inbox and board paths must contain ordinary directories/files: symlink or junction parents and leaves are refused, with no-follow opens where supported.

Before a commit, a failed memory write restores the original bytes, including when writing, truncating, or closing changed bytes before throwing. Newly created files from the failed run are removed. Rollback preserves later concurrent edits whose bytes differ from those left by the run.

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

## Write or close a board subject

Use `ignite board write -h` for the checked form. Copy `<home>/_artifacts/board.md` to a candidate file, edit its subjects or watch-outs, then submit it:

```
ignite --agent <slug> --installation <installation> board write --file "board candidate.md"
ignite --agent <slug> --installation <installation> board close "Subject title" "One-line outcome" "[discussion](https://example.com/thread)"
```

The close thread is optional. All four sections must be present, even when empty. Keep Timers, Recently closed and existing Flags unchanged in a candidate. New subjects use Flags `none`. `write` reports the board path and whether bytes changed; `close` reports the title and path. `--json` returns `{path, changed, subject?}` on success or `{path, error}` with exit 1 on failure (`path` is null before a home is resolved). Validation refuses malformed or over-cap input without changing the board. Close records a dated outcome; when six closed entries already exist, archive old entries before trying again. No entry is truncated or automatically pruned. Legacy boards require reshaping before using the checked commands; runtime board commands never read or copy the legacy path.

`connect` first turns on the `ignite` pack through `rbtv agent add <home> --pack ignite`, then creates missing working files: the four-section board at `<home>/_artifacts/board.md`, `state.sqlite`, and `conversations/`, before it makes a Slack request. Its working-file setup may copy `<home>/board.md` once, preserving its bytes and leaving the old file untouched. Once the new path exists, Ignite reads and writes only that path. `disconnect` removes the Slack route and timers first, then turns the pack off through `rbtv agent remove <home> --pack ignite`; it keeps the agent folder and working files.

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

Success prints `remembered in <path>` followed by any warning and exits 0. `--json` returns `{path, appended, lines, warning}`; `lines` counts bullet lines, `warning` is null when none, and `lines` is null if counting fails after append. Missing text, text empty after newline normalization and trimming, an unresolved installation root or a filesystem write failure exits 1, with an error on stderr or `{path, error}` on stdout in JSON mode. Empty text reports `remember requires non-empty text` before resolving the installation or writing files. `path` is null if no inbox path was resolved. `--help` works without configuration; use `--` before literal option-like text. Repeating the command appends another record.

## Dreamer watch-outs and unread messages

An inbox line is the owner's explicit remember request and can be filed into profile, knowledge or entities without an unread owner message. The proposal cites the exact inbox line as a source on the destination and inbox operations, preserves its provenance (including a bare agent name when no thread exists), and maps its removal to the filed record. Each agent files its own lines. Other existing memory is not evidence for new facts or learned rules.

A watch-out without a provenance link can become a learned correction when the dreamer has unread owner messages with Slack thread evidence. The learned rule retains the watch-out's date, includes `Why:`, and cites only this agent's threads supported by the fold operation's owner sources. Linked provenance stays unchanged and requires matching unread owner thread evidence. A watch-out without the required evidence stays on the board; during consolidation it produces a conflict only if that conflict was not reported before. Other valid work can still commit. A foldable watch-out left unfolded refuses the run.

The dreamer advances an agent's cursor after a successful commit or after applied writes already match HEAD, and when that agent submitted an operation or had no unread owner rows. Another agent's writes do not consume unread rows for an agent that returned no operations. Those rows remain available for the next run. A run without applied writes advances no cursors, even when it reports a conflict.

Removing an uncommitted duplicate can leave no net change against HEAD. When all written paths match HEAD and none is untracked, the dreamer skips the commit, records success with the current HEAD, and keeps the digest, including `already known` entries. A real commit failure leaves cursors and success timestamps unchanged and reports a fixed category: `nothing to commit`, `index lock`, or `other`. Git output is never copied into the alert.

## Repair a hold

A hold survives ticks and restarts. Set a launch setting that does not use the failed model, then retry. `work retry` with no id clears only an agent hold; with an id it clears only that work hold.

```
rbtv agent configure <slug> --harness <harness> --model <cast short name> --effort <rung word>
ignite --agent <slug> --installation <installation> work retry
ignite --agent <slug> --installation <installation> work retry <work-id>
```

The setting applies from the next turn in every conversation of that agent.

## Known behaviour

Queued turns. One primary turn per agent. Agents do not wait on each other. A message saved while that agent is busy stays in its queue and is claimed when the turn ends. Owner input is claimed before an automatic continuation. Saving a message is not the same as starting the turn: the eyes reaction is added when the turn starts.

Steering between turns. There is no mid-turn interruption. An owner message that arrives during a turn is saved and processed on a later turn.

Voice notes. If transcription fails, Ignite replies: `I could not transcribe that voice note; please send it as text.` The technical error is written only to the service log.

Attachments. When a file attached to an owner message is not downloaded, the turn still runs: the turn message lists the files that were saved and states how many were not, so the agent tells the owner.

Long threads. The prompt carries a bounded recent window (20 messages) plus the path of the full history file under the agent home. The folder name is the conversation key with colons replaced by hyphens. A folder left under the raw key is renamed on first access. The file is regenerated from the store. The store is authoritative.

The unit starts at boot when user lingering is on. Check with `systemctl --user is-enabled rbtv-ignite-agents.service`.

rbtv puts `~/.rbtv/bin` on the user shell PATH. A deploy also prepends it to the service unit's PATH (in `deploy.sh`), since a boot-time user service may not source a shell profile; it adds the directory only when absent. rbtv links `ignite` there. After installing a harness or a tool in a new location, redeploy. Startup refuses to go ready if `ignite` is not on that PATH.

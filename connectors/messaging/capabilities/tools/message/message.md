# message

`message` is the [port command](../../../../../core/rbtv/capabilities/glossary/port-command.md) of the messaging [port](../../../../../core/rbtv/capabilities/glossary/port.md): an agent sends a message to one address as itself (`send`), replies inside a thread it has (`reply`) and reads a thread (`history`). It holds the port's policy, checks who may be messaged and picks the connector, then hands the delivery to that connector's messaging adapter (`connectors/<name>/capabilities/tools/<name>/lib/messaging.js`, the [messaging contract](../../methods/messaging-contract.md)'s Adapter section) in its own process. `message -h` and each verb's `-h` are the interface reference; the specification it was built to is the connector architecture's `spec-message.md` (phase 2, 2026-10-16).

## What each verb returns

- `send --to ADDRESS --via CONNECTOR TEXT`: three lines, `Sent` (the recipient, `direct` for a contact or `group ID`, the connector, the agent's name), `Ref` (the message reference) and `Reply` (the command that replies in the thread it started). `--json`: `{connector, account, to, conversation, thread, id, ref, as, files}`. A text over 12,000 characters is sent as a file named `message.md` and the `Sent` line says so. Files go after the text, no caption, in order, each a message of the thread the text started. A file the connector refused beside a delivered text is a partial: stdout keeps what happened, stderr names the file (`why` the connector's sentence, `error` in `--json` the service's bare answer such as `file_too_large`), exit 1. A send that delivered nothing (a files-only send whose upload failed, a connector that did not answer for its account) is a failure: no reference, three stderr lines ending `nothing was sent`, exit 1.
- `reply --thread REF TEXT`: `Sent` and `Ref`. A reply takes no address and no connector: the reference says where the thread lives. REF may name the thread's root or any reply inside it: the connector resolves the root and posts there, and `--json` carries that root as `thread` (`to` null).
- `history --thread REF [--full]`: the thread's messages oldest first as a table (time in UTC, sender as the service names them, text shortened to 80 columns, with a line that names `--full` when one was); `--full` prints one labelled block per message. `--json`: `{ref, events}`, each event in the contract's inbound event shape, `raw` included.

The message reference is `connector:account:conversation:id`, four parts the connector fills as it names things (Slack: team id, channel id, `ts`); copy it, never build it.

## Who may be messaged

Until the permission ladder exists (phase 3), both `send` and `reply` allow the owner (`slack.ownerUserId` of Ignite's `config.json`) and this agent's own channel (the `routes` entries that name the agent of `RBTV_AGENT_HOME`), in `slack.team` only. A run with no agent home may message the owner only. Other connectors cannot borrow those Slack permissions.

Both verbs check policy before loading the adapter or calling its address, account or operation functions. Slack address-shape errors are classified locally in the port. A reply's reference must name the configured team and an authorized conversation. Own channels come from routes; a DM is authorized only when a read-only `conversations.info` lookup confirms that its id matches the reference, `is_im` is true and `user` is the configured owner. Stored conversation/message rows and message authors do not grant permission. This lookup uses `SLACK_BOT_TOKEN` from the environment or `.rbtv/config/env/.env`, read literally through Ignite's `envValue`, and the adapter's endpoint (`SLACK_API_URL`, else Slack's API). A failed lookup refuses before adapter loading. The owner contact lookup requires Slack's `im:read` scope.

After authorization, the adapter's `account()` must match the configured account and, for a reply, the reference's account, before any delivery. Non-root references still go through the adapter's thread resolution. `history` checks the reference against the configured account when present, and against the adapter's actual account, before reading; it retains its existing read access to other conversations the service allows.

## The connector

`--via` is required on every send, even with one messaging connector installed; the refusal lists the installed ones. A candidate is a component under `connectors/` of the installation's merged catalog (the repository's `connectors/`, then the installation's `.rbtv/mirror/connectors/`, whose record of the same name replaces the repository's whole, as the installer merges them) whose record is of the messaging port and provides `message.send`, installed here (the installation's `install.json`) and with a messaging adapter beside its record; a connector installed without its adapter is refused by name (WhatsApp and Google until phase 3a builds theirs). The connector's adapter decides whether an address is its form (`address(value)`), names the account the reference carries (`account()`) and performs the operations after the port authorizes the recipient.

## One send function

`lib/send.js` is the one send function: Ignite's `outbox.js` and `message send` both deliver through it (post the text once, a long text as a file, each file after the text with no caption into the text's thread, report each file the connector refused, fail as a whole with the original typed error when nothing was delivered) and both name the sender through its `senderOf` (the agent's `external_name`, else its name with a capital first letter). Ignite's `test_outbox.js` invokes both callers through the intercepted function and fails when either stops using it or names the sender its own way.

## The closed doors

A message to a contact never goes through `slack send` (which refuses a user id or a DM channel) or `ignite post` (which refuses a new thread in the owner's direct conversation); both keep their service and conversation-store jobs.

## Maintenance

- `test_message.js` beside the program runs the specification's result matrix and policy regressions against stub adapters and the real Slack adapter with intercepted HTTP in synthetic installations: `node test_message.js`, one `PASS` line per test, exit 0.
- The program is one file on Node's standard library; `main(argv, deps)` takes `root` (the folder holding `connectors/`), `cwd`, `env`, `stdout` and `stderr` so the tests run it in process.
- Exit codes: 0 sent or read; 1 refused or failed; 2 invalid words. Every refusal is three stderr lines, `message: WHAT`, `  why:`, `  fix:`, with or without `--json`.

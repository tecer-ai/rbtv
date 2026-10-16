# message

`message` is the [port command](../../../../../core/rbtv/capabilities/glossary/port-command.md) of the messaging [port](../../../../../core/rbtv/capabilities/glossary/port.md): an agent sends a message to one address as itself (`send`), replies inside a thread it has (`reply`) and reads a thread (`history`). It holds the port's policy, checks who may be messaged and picks the connector, then hands the delivery to that connector's messaging adapter (`connectors/<name>/capabilities/tools/<name>/lib/messaging.js`, the [messaging contract](../../methods/messaging-contract.md)'s Adapter section) in its own process. `message -h` and each verb's `-h` are the interface reference; the specification it was built to is the connector architecture's `spec-message.md` (phase 2, 2026-10-16).

## What each verb returns

- `send --to ADDRESS --via CONNECTOR TEXT`: three lines, `Sent` (the recipient, `direct` for a contact or `group ID`, the connector, the agent's name), `Ref` (the message reference) and `Reply` (the command that replies in the thread it started). `--json`: `{connector, account, to, conversation, thread, id, ref, as, files}`. A text over 12,000 characters is sent as a file named `message.md` and the `Sent` line says so. Files go after the text, no caption, in order; a file the connector refused leaves the text delivered: stdout keeps what happened, stderr names the file, exit 1, and `--json` carries `{path, id: null, error}` for it.
- `reply --thread REF TEXT`: `Sent` and `Ref`. A reply takes no address and no connector: the reference says where the thread lives. `--json` as `send`, with `to` null and `thread` the thread's id.
- `history --thread REF [--full]`: the thread's messages oldest first as a table (time in UTC, sender as the service names them, text shortened to 80 columns, with a line that names `--full` when one was); `--full` prints one labelled block per message. `--json`: `{ref, events}`, each event in the contract's inbound event shape, `raw` included.

The message reference is `connector:account:conversation:id`, four parts the connector fills as it names things (Slack: team id, channel id, `ts`); copy it, never build it.

## Who may be messaged

Until the permission ladder exists (phase 3), `send` allows the owner (`slack.ownerUserId` of Ignite's `config.json`) and this agent's own channel (the `routes` entries that name the agent of `RBTV_AGENT_HOME`), and refuses every other address before any connector runs. A run with no agent home may message the owner only. `reply` and `history` take the thread as given.

## The connector

`--via` is required on every send, even with one messaging connector installed; the refusal lists the installed ones. A candidate is a component under `connectors/` whose record is of the messaging port and provides `message.send`, installed here (the installation's `install.json`) and with a messaging adapter; a connector installed without its adapter is refused by name (WhatsApp and Google until phase 3a builds theirs). The connector's adapter decides whether an address is its form (`address(value)`), names the account the reference carries (`account()`) and performs the operations; `message` classifies nothing.

## One send function

`lib/send.js` is the one send function: Ignite's `outbox.js` and `message send` both deliver through it (post the text once, a long text as a file, each file after the text with no caption, report each file the connector refused). Ignite's `test_outbox.js` fails when either caller stops using it.

## The closed doors

A message to a contact never goes through `slack send` (which refuses a user id or a DM channel) or `ignite post` (which refuses a new thread in the owner's direct conversation); both keep their service and conversation-store jobs.

## Maintenance

- `test_message.js` beside the program runs every cell of the specification's result matrix against stub Slack and WhatsApp adapters in a synthetic installation: `node test_message.js`, one `PASS` line per test, exit 0.
- The program is one file on Node's standard library; `main(argv, deps)` takes `root` (the folder holding `connectors/`), `cwd`, `env`, `stdout` and `stderr` so the tests run it in process.
- Exit codes: 0 sent or read; 1 refused or failed; 2 invalid words. Every refusal is three stderr lines, `message: WHAT`, `  why:`, `  fix:`, with or without `--json`.

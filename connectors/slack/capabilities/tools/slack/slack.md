# Slack

`slack` reads and searches messages, transfers files, sends messages, manages reactions and edits canvases. Run `slack --help` and the selected verb's help for arguments and outcomes.

Install with `rbtv add --component connectors/slack`. The installer clones the branch in `slack.json` when missing and sets up its Python environment. Repeating installation does not pull updates; `rbtv update repositories` explicitly updates selected external repositories and refuses checkouts with local changes.

The wrapper runs this component's `repository/stools.py`. `SLACK_TOOLS_ROOT` overrides the checkout; `SLACK_TOOLS_CONFIG` overrides `.rbtv/config/slack/config.yaml` in the installation. Run from inside the installation so account selection and grants resolve there. Credentials follow the external repository's configuration contract.

## Messages and preview

Write messages in standard Markdown. Send and upload dry runs show the complete message fields used for delivery; this is an outgoing-content preview, not a rendering of Slack's interface. Each message is limited to 12,000 characters. Attach longer documents instead of truncating them.

Text uses Slack's native `markdown_text` field. Upload captions use a `markdown` block, without `initial_comment`, which would override it. Broadcast uploads post the caption once through the text path. The tool does not guess a second input format or silently retry a failed write in another format. Slack determines visual rendering; headings share one size and Markdown images become links. Maintainers should check [chat messages](https://docs.slack.dev/reference/methods/chat.postMessage/), [Markdown blocks](https://docs.slack.dev/reference/block-kit/blocks/markdown-block/) and [upload completion](https://docs.slack.dev/reference/methods/files.completeUploadExternal/) before changing these fields.

Reply in the thread the request belongs to. File conversion is handled by its connector, such as `elevenlabs`; Slack transfers the resulting local file. Ignite replies go through `replies[].text` and `replies[].files`, not a second manual post; Ignite owns that delivery contract.

## Messages to a contact

A message to a contact, a user id (`U…`, `W…`) or a direct conversation (`D…`), is not sent by `slack send`: the wrapper refuses it (exit 2) and names `message send --to ADDRESS --via slack TEXT`, the port command that checks who may be messaged. `slack send` keeps channel posts, threads in channels and Slack's own features; `slack send -h` ends with that sentence.

## Messaging adapter for Ignite and the message command

`lib/messaging.js` is this connector's messaging adapter, the module the `message` port command loads in process to deliver through Slack, shaped as the [messaging contract](../../../../messaging/capabilities/methods/messaging-contract.md)'s Adapter section says: `operations` for `message.send`, `message.file`, `message.history`, `message.react`, `group.manage` and `approval.secure` over `slack.com/api`, `message.receive` refusing until phase 4 moves Ignite's listener here, and the helpers `address(value)` and `account()`. A thread given by the id of any of its messages is posted to, uploaded into and read at its root: one `conversations.replies` call on that id says whether it is the root or a reply (`thread_ts`), and both `message.send` and file sending answer with that root as `thread`. A Slack error is `slack answered <code>` with `reason` the bare code. The token is the variable `SLACK_BOT_TOKEN`, read inside each call from the environment, then from the installation's `.rbtv/config/env/.env`, literally; it is never printed. `adapter-check slack` passes on it. Its tests are `test_messaging.js` beside the wrapper (`node test_messaging.js`), against a local stub of the API (`SLACK_API_URL`), with sentinel tokens.

## Write identity

An account label does not prove the Slack identity. Use the account and recipient authorized by the request. Writes on accounts configured with `writes: false` additionally require a matching active grant in `.rbtv/config/slack/write-grants.yaml`. Preserve existing grants and record only the approved account, verbs and working-folder scope. The command's send help links the grant format.

The matcher checks account, verb, active status and working-folder scope. It does not enforce a thread, message count, expiry or consent authorship. A grant is not consent, `--yes` only skips interactive recipient confirmation, and a dry run does not establish permission or grant coverage. Missing account metadata fails closed for writes. Reads are not subject to write grants. Help requires no grants; no Slack operation occurs while showing help.

## Live status for Ignite

`lib/live-status.js` shows a message's Ignite [live status](../../../../../core/ignite/capabilities/glossary/live-status.md) as reactions. It holds the Slack emoji of each state and the rules that keep them readable: the system emoji on the left at every moment (on a system change the emoji on its right is removed first and added again after the new system emoji; a system emoji that goes with none in its place is removed alone, and a task beside it stays), the agent frame replaced remove first then add, two adds on one message at least a second apart. A reaction is gone only once Slack acknowledges its removal: a call that fails leaves its name uncertain, the name is removed before anything is added beside it, and the message waits, longer after each failure in a row, before its next call; HTTP 429 and 5xx pause every call. It is pure logic: the caller passes the add and remove reaction functions, the clock and a record function that keeps what each message shows across a restart (a message with no record may hold any of its names, and each is removed before its state is shown), and decides when to apply, so it runs with any Slack client. Its `legendView` builds the modal behind Ignite's `/legend` command: one row per state of the meanings Ignite passes in, in Ignite's order, with that state's emoji from the same mapping (an agent state's frames in order), so the legend follows the mapping and the states without a second copy. It lives here, beside the wrapper, because it is Slack's half of a contract whose states Ignite owns; Ignite's waking service requires it by relative path, as it requires cast's `lib/`. It is JavaScript, run by Ignite's Node; the wrapper above does not use it. Its tests are Ignite's `test_live_status.js`.

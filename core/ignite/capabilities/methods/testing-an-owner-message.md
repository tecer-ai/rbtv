# Testing an owner message

A live test of anything an owner message triggers (a turn, a capture into memory, a reply, a schedule the owner asks for) is a message sent as the owner, through the Slack connector's owner-identity account. That is the supported way. `ignite post` queues a bot post. A message from the bot account is ignored: the service log shows `"event":"ignored","reason":"bot"`. Neither is a substitute.

The installation names the agent those tests run against in `.rbtv/config/ignite/test-agent.md`. Read that file. It is not produced by a command. It holds these lines:

```
test-agent: <agent name>
channel: <#name>
channel-id: <channel id>
owner-account: <account name>
```

`test-agent` is the agent name. `channel` is the channel name and `channel-id` is the id passed to `--channel`. `owner-account` is the configured account name of the owner-identity account. When the file is missing, stop and report that the installation has not named a test agent. Do not choose an agent.

Confirm that account before sending. `slack workspaces` lists each configured account and the Slack user it sends as (`User  : <name> (<user id>)`); it contacts Slack. The owner is `slack.ownerUserId` in `.rbtv/config/ignite/config.json`. The owner-identity account is the listed account whose user id equals that value. Send only when the file's `owner-account` is that account, and only to the channel id in the file. An account label does not prove the Slack identity. Run the command from a folder the grant under Authority covers:

```
slack send --workspace "<owner-account>" --channel "<channel-id>" --message "<text>"
```

Keep the quotes around the account name: an unquoted `<account>` is a shell redirection. Use `--message-file` when the text contains `$`. `--dry-run` prints the resolved recipient and does not post; it may contact Slack, and it does not check the grant. `--yes` skips only the recipient prompt. It is not the approval under Authority.

The message arrived as the owner when the agent's store has a `queue` row with `kind` `owner` and a `runs` row with state `running` or already `finished`. The store is `<agent>/runtime/ignite/state.sqlite`, the database [architecture](../tools/ignite/documentation/architecture.md) names. A bot send does not produce those rows.

When the check is finished, send in that thread with `--thread-ts`, as the same owner-identity account, that the message was a test. For an item that added a record, `albert reverse --item RUN#N` archives it. It exits 0. The record path is gone. The archive holds the file in a verbatim fence, `Reason: reversed. Source: RUN#N`, and the capture line. The index row and the timeline line are gone. The capture line is gone from `inbox.md`. A request line that does not cite the record by URL stays. Other rows and episodes are unchanged. An owner's "forget" told to the agent is handed to the memory agent, who publishes an archived removal. Do not leave the test fact in place. Revoke the grant as Authority says.

## Authority

A send as the owner is that send. The owner must have approved the account, the verb, the working folder and the purpose before a grant is recorded. Record only that approval. The grant procedure and record format are in `connectors/slack/repository/scripts/slack_send.md`, the page `slack send -h` names; do not copy them here. [Slack](../../../../connectors/slack/capabilities/tools/slack/slack.md) states that an account name does not prove the identity, and that a write on an account configured with `writes: false` needs an active grant in `.rbtv/config/slack/write-grants.yaml`. Without a grant that covers the verb for the folder the command runs from, the wrapper exits 2 and prints `slack: as-owner-write-refused` with `no active grant covers '<verb>' for this sitting`. Disclose, before the send, that the message will appear as the owner, which account and channel it uses, and the purpose the owner approved. When the test is over, revoke that grant by appending a revoked fact, as the header of `.rbtv/config/slack/write-grants.yaml` describes. Do not rewrite an existing grant. `--dry-run` does not check the grant and is not approval. A revoked row appended to the grants file does not end the grant: the wrapper honours the first active row.

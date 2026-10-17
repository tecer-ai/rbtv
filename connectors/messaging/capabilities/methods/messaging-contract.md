# Messaging contract

The messaging contract states what Ignite performs through a messaging [connector](../../../../core/rbtv/capabilities/glossary/connector.md) today, as the [operations](../../../../core/rbtv/capabilities/glossary/operation.md) of the messaging [port](../../../../core/rbtv/capabilities/glossary/port.md), and the shape in which inbound events reach Ignite. It is written from the calls Ignite makes on its Slack client (`core/ignite/capabilities/tools/ignite/slack.js`), not from what Slack offers: every call is tagged `message` (an operation of this port), `panel` (the payment panel, operation `approval.secure`) or `ignite-internal` (the client's own session, no operation), and a part only some services have is marked optional. A connector's [adapter](../../../../core/rbtv/capabilities/glossary/adapter.md) meets this contract; `message`, the port command, will call the same operations (phase 2 of the connector architecture). Read it when writing a messaging adapter, when changing a call Ignite makes on its Slack client, or when adding a connector whose record `provides` a `message.*` or `group.*` operation.

`core/ignite/capabilities/tools/ignite/test_messaging_contract.js` keeps this page true, and parses no JavaScript: every occurrence of the word `slack` in a production file under `core/ignite/` is listed in `messaging-contract/slack-uses.json` with its kind, every `call:` entry there has a tagged row in the call-site table and every row has a `call:` entry, every occurrence of the word `payload` in the panel's files is listed in `messaging-contract/payload-uses.json` with the field paths it reads, each named in the Slash command or Buttons and forms table, every file that binds the client or the payload to a name matches the hash the list recorded, and the fixtures beside this page fit the inbound event table. A new occurrence, or a change to a bound file, fails until an author lists or restates its entries (the Checks section).

## Words

A **group** is a place several people talk: a Slack channel, a WhatsApp group, a mail thread with several recipients. A **contact** is one person as the service names them: a user id, a phone number, a mail address. A **thread** is a chain of replies under one message: a Slack thread, a WhatsApp reply chain, a mail thread. A direct conversation is between the agent and one contact; it has no group. An email domain is a filter in the routing rules, not a group.

## Operations

| Operation | Tag | What Ignite does today | Presence | Slack class methods |
|---|---|---|---|---|
| `message.send` | message | Posts text to a group or a contact, inside a thread when the conversation has one, shown as the agent (its name and avatar), with a stable client id so a retry does not post twice; returns the conversation and the id of the posted message. A contact as the recipient is resolved by the connector to the direct conversation with that contact, never addressed by id. The text is standard Markdown and holds at most 12,000 characters; a longer text is sent as a file | required | `postMessage`, `openIm` |
| `message.receive` | message | Delivers each inbound event to Ignite's [listener](../../../../core/ignite/capabilities/glossary/listener.md) in the shape of the Inbound event table, plus the slash-command and button payloads below to the panel. The connector keeps the session (Slack: Socket Mode, acknowledged on arrival, reconnected with backoff) and drops nothing silently | required | `connect` |
| `message.history` | message | Reads a thread's messages, oldest first, each in the inbound event shape: Ignite rebuilds a conversation from the thread when the owner replies inside a thread it had not followed | optional: a service without threads returns an empty list | `threadHistory` |
| `message.react` | message | Adds or removes a named reaction on a message; [live status](../../../../core/ignite/capabilities/glossary/live-status.md) shows Ignite's states this way, through the connector's own mapping of states to its medium, within the service's rate budget | optional: a service without reactions reports it cannot, and live status shows nothing there | `addReaction`, `removeReaction` |
| `message.file` | message | Sends a file into a conversation as the agent, with no caption, returning the message id it made; fetches the files of a message into a folder, each with the id the event named, so an audio file can be transcribed | optional | `uploadFile`, `downloadFile` |
| `group.manage` | message | Creates a group, joins it, invites a contact to it and archives it: `ignite connect` makes an agent's channel and `ignite disconnect` archives it | optional: a service whose groups only people can make reports it cannot, and the agent's group is made by hand | `createChannel`, `joinChannel`, `inviteUser`, `archiveChannel` |
| `approval.secure` | panel | The payment gate's owner side: a form only the owner can open and submit (`/payments`, with the PIN), buttons in the request's thread message (Approve and Refuse, replaced by the outcome once decided), a text seen by one user only, and views stacked on the form. Blocks, modals and views belong here, not to messaging; a messaging connector that cannot carry a secure approval (WhatsApp) does not provide it, and payments refuse that connector. The `/legend` modal, which explains live status, rides this same medium | required for payments, never for messaging | `postBlocks`, `updateMessage`, `postEphemeral`, `openView`, `pushView`, `updateView` |
| none | ignite-internal | The client's own session: the identity Ignite uses to recognise its own messages (`auth`) and the stop of the socket when the service stops (`stop`). The adapter does both for itself; no port command or listener asks for them | — | `auth`, `stop` |

Methods of the Slack class that Ignite never calls are not part of the contract: `canvasCreate` and `canvasEdit` are Slack-only features of the `slack` command, and `api`, `normalize`, `stools` and `tolerated` are the client's internals.

## Call sites

One row per production file under `core/ignite/` and Slack class method it reaches, through whatever name holds the client; each row is backed by a `call:` entry of `messaging-contract/slack-uses.json` (the Checks section), and the file is written relative to `core/ignite/capabilities/tools/ignite/`. The test program reads this table; keep its first three cells in this form.

| File | Slack call | Tag | Operation and note |
|---|---|---|---|
| `daemon.js` | `auth` | ignite-internal | The identity (team, bot user, bot id) that marks Ignite's own messages |
| `daemon.js` | `connect` | message | `message.receive`: starts the listener with the event handler and the panel's acknowledgement and handlers |
| `daemon.js` | `stop` | ignite-internal | Closes the socket when the service stops |
| `outbox.js` | `postMessage` | message | `message.send`: the reply text, as the agent, with the stored client id |
| `outbox.js` | `openIm` | message | `message.send` to a contact: the connector resolves the direct conversation |
| `outbox.js` | `uploadFile` | message | `message.file`: each file of the reply, and a synthesized voice file |
| `turn-loop.js` | `downloadFile` | message | `message.file`: the owner message's files, before transcription |
| `ingress.js` | `threadHistory` | message | `message.history`: the thread an owner reply arrived in |
| `listener.js` | `threadHistory` | message | `message.history`: the thread an owner reply arrived in, when the socket event is a reply in a group |
| `connect.js` | `createChannel` | message | `group.manage`: the agent's channel |
| `connect.js` | `joinChannel` | message | `group.manage` |
| `connect.js` | `inviteUser` | message | `group.manage`: the owner joins the agent's channel |
| `connect.js` | `archiveChannel` | message | `group.manage`: `ignite disconnect` |
| `status-ticker.js` | `addReaction` | message | `message.react`: live status, called as `client[method]` |
| `status-ticker.js` | `removeReaction` | message | `message.react` |
| `payment-runner.js` | `postBlocks` | panel | The request's message in its agent's thread, with Approve and Refuse |
| `payment-runner.js` | `updateMessage` | panel | The same message once the request is decided: the buttons go |
| `payment-panel.js` | `postEphemeral` | panel | A refusal seen by the one who pressed a button in a thread |
| `payment-panel.js` | `openView` | panel | `/payments` opens the panel or the PIN form |
| `payment-panel.js` | `pushView` | panel | A form on top of the panel |
| `payment-panel.js` | `updateView` | panel | The form becomes its outcome, or the form again with the reason |
| `legend.js` | `openView` | panel | `/legend` opens the live status legend |
| `agent-panel.js` | `openView` | panel | `/agent` opens the agent panel |
| `agent-panel.js` | `updateView` | panel | A tab button redraws the agent panel on that tab |

## Inbound event

The one shape every messaging connector delivers an inbound message in, for the listener and for `message.history`. The test program reads this table and checks the fixtures beside this page, `messaging-contract/inbound-email.json` and `messaging-contract/inbound-whatsapp.json`, against it: every required field with its type, no field outside the table. A type cell names one JSON type, or two joined by `or`.

| Field | Type | Presence | Meaning | Slack today |
|---|---|---|---|---|
| `connector` | string | required | The component that delivered the event: `slack`, `whatsapp`, `google` | implicit, Ignite has one connector |
| `account` | string | optional | The account the event came through, when the connector serves more than one: the Slack team id, the WhatsApp number, the mail address | `team` |
| `id` | string | required | The message's id in the service, unique within the account | `ts` |
| `at` | number | required | When it was sent, in milliseconds since the epoch | `ts`, read as seconds |
| `from` | string | required | The contact who sent it, as the service names them: user id, phone number, mail address | `user` |
| `fromName` | string | optional | The sender's display name | not read |
| `group` | string or null | required | The group it arrived in; `null` in a direct conversation with the contact | `channel`, `null` when `channel_type` is `im` |
| `conversation` | string | optional | The service's own id for the conversation, when it differs from the group and the contact: a Slack DM's channel id | `channel` of an `im` |
| `thread` | string or null | required | The id of the thread the message is a reply in; `null` for a message that is not a reply (it starts a thread named by its own id) | `thread_ts` when it differs from `ts` |
| `text` | string | required | The text, empty when the message carries only files | `text` |
| `files` | array | optional | The files attached, each `{ id, name, mimetype }` with any of the three absent; fetched through `message.file` | `files` |
| `mentionsAgent` | boolean | optional | The text addresses the agent (Slack: `<@bot>` outside code) | `mentionsBot` |
| `isSelf` | boolean | optional | Sent by the agent itself, or an echo of its own edit, deletion or join; the listener drops it. Absent means `false` | `isBotOrSelf` |
| `raw` | object | optional | The service's event as received, for the adapter's own use; routing never reads it | the Socket Mode event |

The listener treats `connector`, `account`, `from` and `group` as the facts admission and routing read ([Ignite's dispatch order](../../../../core/ignite/capabilities/glossary/subscription.md)); a connector must not put the owner's identity anywhere else.

## Slash command

An inbound command the owner or a user types in the service, delivered to the panel's `ack` and `handle` (Slack: a `slash_commands` envelope). Ignite reads these fields of the payload; a connector without commands delivers none, and `/payments`, `/legend` and `/agent` are then unreachable there. The test program reads the Field column of this table and of the next section's: every path `messaging-contract/payload-uses.json` lists as read by the panel's files must appear in one of them as written (`trigger_id`, `view.callback_id`, `actions[0].action_id`; a computed index ends a path: `view.state.values[blockId]` is `view.state.values`).

| Field | Presence | Read for |
|---|---|---|
| `command` | required | Which command: `/payments`, `/legend` or `/agent` |
| `trigger_id` | required | Opening a view in answer; valid for seconds, so the acknowledgement is immediate and the view is opened after it |
| `user_id` | required | The owner check for `/payments` and `/agent` (`/legend` is for any user) |
| `team_id` | required | The owner check: the user id counts only within the configured team |
| `channel_id` | required for `/agent` | The channel it was typed in: the agent `routes` maps it to |
| `channel_name` | required for `/agent` | `directmessage` in a direct message: the panel shows `dmAgent` |
| the acknowledgement's `text` | optional | A refusal shown to the one who typed, returned by `ack` before any work |

## Buttons and forms

The panel's interactive payloads (Slack: an `interactive` envelope). Ignite reads these fields; a connector that cannot deliver them does not provide `approval.secure`.

| Payload | Field | Presence | Read for |
|---|---|---|---|
| button (`block_actions`) | `type` | required | `block_actions` |
| button | `user.id`, `user.team_id` or `team.id` | required | The owner check |
| button | `actions[0].action_id` | required | `payments_approve`, `payments_refuse` or `payments_settings`; in the agent panel, `agent_tab_` and the tab |
| button | `actions[0].value` | required for approve, refuse and an agent panel tab | The request id, or the tab to show |
| button | `actions[0].action_ts` | required | The key a replayed press is recognised by |
| button | `trigger_id` | required | Opening the PIN form or the settings form |
| button | `view.id` | optional | Present when pressed inside a panel: a payment form is pushed on top of it; the agent panel redraws that view |
| button | `view.callback_id`, `view.private_metadata` | required in the agent panel | `agent_panel`, and the agent the panel shows |
| button | `channel.id` | optional | Present when pressed in a thread message: a refusal is shown there to that user |
| form (`view_submission`) | `type` | required | `view_submission` |
| form | `user.id`, `user.team_id` or `team.id` | required | The owner check |
| form | `view.id`, `view.hash` | required | The key a replayed submission is recognised by |
| form | `view.callback_id` | required | `payments_set_pin`, `payments_approve` or `payments_settings` |
| form | `view.private_metadata` | required for approve and settings | The request id, or the settings revision the form showed |
| form | `view.state.values` | required | The PIN (`payments_pin`), the mode and the limits, by block id |
| form | `view.root_view_id` | optional | The panel under the form, refreshed once the outcome is shown; absent when the form was opened on its own |
| form | the acknowledgement's errors or next view | optional | Field errors, or a "Checking" view, returned by `ack` before any work |

## Adapter

A messaging connector's adapter is the Node module Ignite loads in-process by the connector's name, at the file the adapter file rule of [Building a connector](../../../../core/rbtv/capabilities/methods/building-a-connector.md) names for the messaging port; that page places it and checks its shape. It exports `operations`: an object with one async function per operation of this contract the record `provides`, keyed by the operation's name. Each function takes one object and returns one object, in this contract's words; a service's own id travels inside the named field (`conversation`, `id`, `group`, `contact`), and Ignite never names a field of the service. A token is read by its environment variable name inside the function, never when the module loads. An operation the connector does not provide has no key, and a call on a missing key is the port layer's to refuse.

| Operation | Input | Result |
|---|---|---|
| `message.send` | `{ group, contact, thread, text, as, clientId }`: one of `group` or `contact`; `thread` optional, the id of any message of the thread (its root, or a reply inside it: the connector posts to the root); `as` optional, `{ name, avatar }`; `clientId` the stable id | `{ conversation, id, thread }`: `thread` the root of the thread the message joined, `null` for a message that starts one |
| `message.receive` | `{ onEvent, interactions }`: `onEvent(event)` receives each inbound event; `interactions` optional, `{ ack(type, payload), handle(type, payload) }` for the slash-command and interactive payloads | `{ stop() }`, which closes the session |
| `message.history` | `{ conversation, thread }` | `{ events }`, oldest first, each an inbound event |
| `message.react` | `{ conversation, id, name, add }`: `add` true adds the reaction, false removes it | `{}` |
| `message.file` | `{ send }` or `{ fetch }`: `send` is `{ conversation, thread, file, as }`, or `{ contact, thread, file, as }` for a file that opens a direct conversation with no text before it; `thread` as in `message.send`, posted to at its root; `fetch` is `{ conversation, id, thread, dir }` | `{ id, conversation, thread }` for a send (`thread` the resolved root, or `null` for a file that starts one); `{ files }` for a fetch, each `{ id, name, path }` |
| `group.manage` | One of `{ create: { name } }`, `{ join: { group } }`, `{ invite: { group, contact } }`, `{ archive: { group } }` | `{ group }` |
| `approval.secure` | One of `{ post: { conversation, thread, text, blocks } }`, `{ update: { conversation, id, text, blocks } }`, `{ whisper: { conversation, contact, text } }`, `{ open: { trigger, view } }`, `{ push: { trigger, view } }`, `{ change: { viewId, view } }` | `{ conversation, id }` for a post or an update; `{}` otherwise |

Beside `operations`, the module exports two helpers the port command `message` uses and Ignite does not: `address(value)` → `{ contact: value }` or `{ group: value }`, saying which of the two an address in the connector's own form is, or throwing an `Error` whose `code` is `address` and whose message is the sentence `message` prints as the refusal's reason (the port may classify an address-shape error locally, but authorizes both outbound verbs before loading or calling the adapter); and `account()` → the account id the message reference carries (Slack: the team id). An operation that fails throws an `Error` whose message names the service and its answer (`slack answered thread_not_found for 1792000000.000001 in D0OWNERDM1`) and whose `reason` is the service's bare answer when it gives one (`thread_not_found`, `file_too_large`: what `message --json` carries as `error`); a thread the service does not find carries `code: 'thread'`, so the port command can say so. `message` and Ignite's `outbox.js` deliver through one send function, `connectors/messaging/capabilities/tools/message/lib/send.js`, which posts the text once, sends a text over 12,000 characters as a file, uploads each file after the text with no caption as a message of the text's thread, fails as a whole when nothing was delivered and names the sender (`as`) through its one `senderOf` routine; an adapter does none of that policy.

Slack's `capabilities/tools/slack/lib/messaging.js` is its messaging adapter: `message.send`, `message.file`, `message.history`, `message.react`, `group.manage` and `approval.secure` over `slack.com/api` with the token the variable `SLACK_BOT_TOKEN` names (read inside each call from the environment, then the installation's `.rbtv/config/env/.env`), and `message.receive`, which refuses until phase 4 moves Ignite's listener onto it; `test_messaging.js` beside the wrapper runs it against a local stub. Its `capabilities/tools/slack/lib/live-status.js` is the mapping `message.react` shows live status with, the mapping `message.react` shows live status with, required by Ignite's `status-ticker.js`; Ignite moves onto the adapter itself behind this contract last, after the port commands and the listener have run for real.

## Checks

Run `node core/ignite/capabilities/tools/ignite/test_messaging_contract.js`: it exits 0 and prints the call sites it found. The program parses no JavaScript. Two lists beside this page, `messaging-contract/slack-uses.json` and `messaging-contract/payload-uses.json`, name every occurrence of one word and what it is; the program finds the occurrences with one regular expression per word and compares them with the list, so a new occurrence fails until an author lists it with its kind, and a listed occurrence whose line is gone fails as stale. A list is an object: `uses`, one entry per occurrence, and `files`, the hashes below. An entry is the file (relative to `core/ignite/capabilities/tools/ignite/`), the line's text trimmed, and `nth`, the 0-based occurrence of that text in the file (two words on one line, or two equal lines, are distinct entries).

`slack-uses.json` lists every occurrence of the word `slack` (whole word; in code, a string or a comment) in every production file under `core/ignite/`: every `.js` file other than `slack.js` and the `test_*.js` programs. Its `kind` is one of:

| Kind | Meaning |
|---|---|
| `call:<Method>` | The Slack class methods reached from this occurrence: called on this line (`await slack.auth()`), or through the name this line binds the client to (`socket = slack;`, then `socket.connect(…)` below). Several are joined by commas: `call:connect,stop`. Each method must be a method of the `Slack` class and have a row in the call-site table for this file, and every row must have at least one such entry |
| `config` | The `slack` section of Ignite's config: a read by a key (`config.slack.team`, `raw.slack`) or the section's name as a key (`['slack', 'tools'`) |
| `path` | A module path or a web address (`./slack.js`, `app.slack.com`) |
| `message` | Text in a thrown or logged message, a label or a log field (`'slack.openIm required'`, `event: 'slack'`) |
| `binding` | The client itself with no call on this line: assigned, tested, returned, or handed to a name, parameter or key (`const s = deps.slack;`, `if (deps.slack)`, `function f(store, slack)`, `{ slack, log }`) |
| `comment` | The word in a comment |

`payload-uses.json` lists every occurrence of the word `payload` in the files the call-site table tags `panel`. Its `reads` is the list of payload field paths the line reads, directly (`payload.trigger_id` reads `trigger_id`) or through the name the line binds (`const view = payload.view || {}` reads what its function then reads through `view`: `view.callback_id`, `view.state.values`); a line that reads no field has `[]`. Every path must appear in the Field column of the Slash command or Buttons and forms table as written, and `trigger_id`, `actions[0].action_id`, `view.callback_id` and `view.state.values` must each be read somewhere.

A file that binds the client or the payload to a name can gain a call or a read through that name on a line that holds neither word, so each list's `files` maps every such file (a file with a `binding`, `call:` or `"?"` entry; every panel file for `payload`) to the sha256 of its content, read with CRLF as LF, and the program fails when a file's content differs from its hash. `--write-fixture` then records the new hash and resets that file's `binding`, `call:` and `reads` entries to `"?"`, printing each, so the test keeps failing until the author restates by hand what the bound name reaches.

When a production file gains or loses a use of either word, or a hashed file changes, run `node core/ignite/capabilities/tools/ignite/test_messaging_contract.js --write-fixture`: it rewrites both lists from the files, keeps every known entry's kind or reads except on a changed file, drops stale entries and writes `"?"` on each new one; fill each `"?"` in, since the test refuses it. When Ignite gains a call on its Slack client, add its row to the call-site table with a tag; when a call is removed, remove the row. When the panel reads a new payload field path, add it to the Slash command or Buttons and forms table. When the inbound shape changes, change the table and the two `inbound-*.json` fixtures together, and the adapters that deliver it. A connector's adapter passes the shape check of Building a connector.

A kind and a reads list are the author's statement, checked in review: the program proves that every occurrence is listed and that no bound file changed since its entries were stated, not that a kind is right. The case to look for is the restated entries of a changed file: whether the name it binds reaches only the methods and fields they say.

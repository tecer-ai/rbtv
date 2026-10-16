# Messaging contract

The messaging contract states what Ignite performs through a messaging [connector](../../../../core/rbtv/capabilities/glossary/connector.md) today, as the [operations](../../../../core/rbtv/capabilities/glossary/operation.md) of the messaging [port](../../../../core/rbtv/capabilities/glossary/port.md), and the shape in which inbound events reach Ignite. It is written from the calls Ignite makes on its Slack client (`core/ignite/capabilities/tools/ignite/slack.js`), not from what Slack offers: every call is tagged `message` (an operation of this port), `panel` (the payment panel, operation `approval.secure`) or `ignite-internal` (the client's own session, no operation), and a part only some services have is marked optional. A connector's [adapter](../../../../core/rbtv/capabilities/glossary/adapter.md) meets this contract; `message`, the port command, will call the same operations (phase 2 of the connector architecture). Read it when writing a messaging adapter, when changing a call Ignite makes on its Slack client, or when adding a connector whose record `provides` a `message.*` or `group.*` operation.

`core/ignite/capabilities/tools/ignite/test_messaging_contract.js` keeps this page true: it reads the Slack class methods, finds every place a production file under `core/ignite/` reaches one through any name that holds the client, and fails on a call site this page does not tag or a row here that no call site backs. It fails closed on the word `slack`: every use of it in those files must be one of the forms the Checks section lists, or the test names the line as an unsupported client use. It also checks that the Slash command and Buttons and forms sections name every path the panel's files read from a payload, nested ones included (`view.callback_id`, `actions[0].action_id`), directly or through a name assigned from the payload, and the fixtures beside this page against the inbound event table.

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

One row per production file under `core/ignite/` and Slack class method it reaches, through whatever name holds the client (`slack`, `deps.slack`, `slack()`, a name assigned from one, `client[method]`, a method taken out by destructuring); the file is written relative to `core/ignite/capabilities/tools/ignite/`. The test program reads this table; keep its first three cells in this form.

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

An inbound command the owner or a user types in the service, delivered to the panel's `ack` and `handle` (Slack: a `slash_commands` envelope). Ignite reads these fields of the payload; a connector without commands delivers none, and `/payments` and `/legend` are then unreachable there. The test program reads the Field column of this table and of the next section's: every path the panel's files read from a payload must appear in one of them as written, whether read directly (`payload.trigger_id` is `trigger_id`) or through a name assigned from the payload (`const view = payload.view` then `view.callback_id` is `view.callback_id`; `payload.actions?.[0]` then `act.action_id` is `actions[0].action_id`). A computed index ends a path: `view.state.values[blockId]` is `view.state.values`.

| Field | Presence | Read for |
|---|---|---|
| `command` | required | Which command: `/payments` or `/legend` |
| `trigger_id` | required | Opening a view in answer; valid for seconds, so the acknowledgement is immediate and the view is opened after it |
| `user_id` | required | The owner check for `/payments` (`/legend` is for any user) |
| `team_id` | required | The owner check: the user id counts only within the configured team |
| the acknowledgement's `text` | optional | A refusal shown to the one who typed, returned by `ack` before any work |

## Buttons and forms

The panel's interactive payloads (Slack: an `interactive` envelope). Ignite reads these fields; a connector that cannot deliver them does not provide `approval.secure`.

| Payload | Field | Presence | Read for |
|---|---|---|---|
| button (`block_actions`) | `type` | required | `block_actions` |
| button | `user.id`, `user.team_id` or `team.id` | required | The owner check |
| button | `actions[0].action_id` | required | `payments_approve`, `payments_refuse` or `payments_settings` |
| button | `actions[0].value` | required for approve and refuse | The request id |
| button | `actions[0].action_ts` | required | The key a replayed press is recognised by |
| button | `trigger_id` | required | Opening the PIN form or the settings form |
| button | `view.id` | optional | Present when pressed inside the panel: the form is pushed on top of it |
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
| `message.send` | `{ group, contact, thread, text, as, clientId }`: one of `group` or `contact`; `thread` optional; `as` optional, `{ name, avatar }`; `clientId` the stable id | `{ conversation, id }` |
| `message.receive` | `{ onEvent, interactions }`: `onEvent(event)` receives each inbound event; `interactions` optional, `{ ack(type, payload), handle(type, payload) }` for the slash-command and interactive payloads | `{ stop() }`, which closes the session |
| `message.history` | `{ conversation, thread }` | `{ events }`, oldest first, each an inbound event |
| `message.react` | `{ conversation, id, name, add }`: `add` true adds the reaction, false removes it | `{}` |
| `message.file` | `{ send }` or `{ fetch }`: `send` is `{ conversation, thread, file, as }`; `fetch` is `{ conversation, id, thread, dir }` | `{ id }` for a send; `{ files }` for a fetch, each `{ id, name, path }` |
| `group.manage` | One of `{ create: { name } }`, `{ join: { group } }`, `{ invite: { group, contact } }`, `{ archive: { group } }` | `{ group }` |
| `approval.secure` | One of `{ post: { conversation, thread, text, blocks } }`, `{ update: { conversation, id, text, blocks } }`, `{ whisper: { conversation, contact, text } }`, `{ open: { trigger, view } }`, `{ push: { trigger, view } }`, `{ change: { viewId, view } }` | `{ conversation, id }` for a post or an update; `{}` otherwise |

Slack's `capabilities/tools/slack/lib/live-status.js` is the one piece of its adapter built today, the mapping `message.react` shows live status with, required by Ignite's `status-ticker.js`; Ignite moves onto the adapter itself behind this contract last, after the port commands and the listener have run for real.

## Checks

Run `node core/ignite/capabilities/tools/ignite/test_messaging_contract.js`: it exits 0 and prints the call sites it found. When Ignite gains a call on its Slack client, add its row to the call-site table with a tag; when a call is removed, remove the row. When the panel reads a new payload field path, add it to the Slash command or Buttons and forms table. When the inbound shape changes, change the table and the two fixtures together, and the adapters that deliver it. A connector's adapter passes the shape check of Building a connector.

The test program fails closed on the word `slack`: every occurrence of the identifier in a production file's code, as a property, a variable, a key, a parameter or inside a string, must be a form it understands, or it fails with `unsupported client use <file>:<line>: <the text>`. Write a use of the client in one of these forms:

| Form | Examples |
|---|---|
| A call on the client through a holder: bare `slack`, a property (`deps.slack`, `ctx.slack`, `this.slack`) or a getter call (`slack()`), then the method, with any spacing or line break between | `await slack.auth();`, `deps.slack?.openIm`, `slack().openView(…)` |
| A name assigned from a holder, from `new Slack(` or from a function of the same file that returns a holder; that name is then a holder | `const s = deps.slack;`, `let slack = opts.slack \|\| null;`, `const client = slack();`, `typeof slack === 'function' ? slack() : null`, `const slack = slackClient(config, deps);` |
| A method taken out of a holder by destructuring, under its own name or renamed | `const { canvasCreate: create } = deps.slack; create({});` |
| A parameter named `slack`, plain or destructured | `function f(store, slack)`, `(slack) => …`, `createLegend({ slack, log })` |
| The holder passed to a function of the same file whose parameter at that position is named `slack` | `activateThread(store, ctx.slack, route)` |
| The key `slack` of an object, shorthand, or with a holder or a getter of one as its value | `{ config, slack, log }`, `slack: () => slack` |
| A truthiness or `typeof` test, a `return` of a holder, a holder stored under `slack` | `if (deps.slack)`, `!opts.slack`, `return deps.slack;`, `ctx.slack = slack;`, `slack = new Slack({` |
| A read of the `slack` section of Ignite's config by one of its keys (`SLACK_KEYS` in `config.js`) | `config.slack.team`, `config?.slack?.ownerUserId` |
| A string that is a module path, a web address, a config key or the message thrown when the client lacks a method | `'./slack.js'`, `https://app.slack.com/…`, `'slack.team'`, `'slack.openIm required'` |

Not understood, so refused: destructuring the client itself (`const { slack: client } = deps`; write `const client = deps.slack;`), a computed key (`deps['slack']`; write `deps.slack`), a holder passed to a parameter of another name (name the parameter `slack`), and a `slack` property followed by a name that is neither a Slack method nor a config key. A use of the word that is not the client and fits no form above (a config section's name, a log field, a label) is added to the program's `NON_CLIENT_USES` list by exact text with its reason; the program names the list in its message.

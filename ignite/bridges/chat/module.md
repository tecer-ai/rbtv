# bridges/chat — module inventory (append-only)

## reply-grammar

`reply-grammar.js` — parse an owner Slack reply into a canonical first-token
outcome plus comments, or a parse-failure that names which verbatim §4.5 NACK
applies. Law: `spec-owner-io` §4. Pure function. Probe:
`probes/probe-chat-reply-grammar.js`.

## outbox

`outbox.js` — durable Slack outbox [C-17]: every post starts `pending-delivery`
and flips `delivered` only on Slack ack. Query by state / kind / channel_id /
goal_id / ask_id (newest-first) and get-by-`outbox_id`. Store:
`.rbtv/runtime/ignite/outbox.json`. Probe: `probes/probe-chat-outbox.js`.

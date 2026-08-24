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

## ask-thread

`ask-thread.js` — thread-per-ask posting and the ONE door that releases an ask
(`spec-owner-io.md` §2.1, §2.4, §3). Every ask batch opens a NEW thread in the
goal's channel [D18, T5-R8]; the opening message's `thread_ts` IS the ask id
[D-8], so the message is posted and then rewritten (`transport.updateMessage`,
`chat.update`) to carry the §3 line `{marker} {display_suffix} · {seat_name} ·
{label}` — the suffix cannot be composed before Slack mints the id. Only ❓ mints
a record (through `ask-store.js`, the `record-owner-ask` gateway sender); 💭
mints none. A non-interact seat's ask is refused at this door [T2-R14].

Release is §2.4 in order: the reply must be in the EXACT thread and its sender
must be in the instance-config authorized set (never repo content) — anything
else is a silent no-op; an unrecognized first token gets the verbatim NACK
in-thread through the outbox and the ask stays `open`; a recognized outcome
persists the reply beside the daemon's ask copy
(`.rbtv/goals/<goal>/coordination/asks/<ask>.reply.txt`, what the relaunched
seat reads) and reaps the wait + fires the relaunch in ONE act. The pre-D89
"oldest still open ask" and `re: <n>` release doors are DELETED [D-4-ruling,
C-3, T1-R12] — a reply that names no thread this module owns releases nothing.
Probe: `probes/probe-chat-ask-release.js`.

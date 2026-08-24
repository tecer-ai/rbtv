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

**How it is reached in production.** `chat-bridge.js` constructs the module and
holds the one map it needs: `askThreads`, `<channel>:<threadTs>` → the ask's goal,
seat and id, persisted additively in the bridge state file (`STATE_VERSION`
unchanged). No ask STATE lives there — state is `open_asks`, daemon-side.

Outbound: the bus ferry posts every `to: owner` row through the bridge's
`postOwnerAsk`, which resolves the goal's channel and calls `postAsk`. The three
park rungs that used to swallow such a row are deleted (see the README's gate
section); the ONE outcome that posts nothing is the [T2-R14] refusal, which is
logged and leaves the row on the bus rather than sweeping it away.

Inbound: `onChatMessage` checks `askThreads` BEFORE every other leg. A message in
an ask's thread is handled at the release door and does not fall through — a
fall-through would mint a sitting on an unauthorized remark and answer an
authorized one twice.

## approval-thread

`approval-thread.js` — the §3 approval first message and the §4.2 post-parse
dispatch (`spec-owner-io.md`; law `DESIGN-BASELINE.md` v2 §Planning approval
rows). `composeApprovalBody` puts the **GOAL NAME** and the **IRREVERSIBLE
EFFECT** on their own bold lead lines before any other body, then the digest, the
bound `commit_id` [T5-R5], the canvas link and the six accepted tokens; it
refuses to compose without a goal name or a commit.

`createApprovalDispatch` forks on the ask's `kind`, never on the token
[D-5-ruling, CF-7]: `approve` in a `kind=approval` thread is the D12 trigger, the
same word elsewhere is an outcome delivered to the seat. reject-and-close /
close close the planning goal; reject-and-pause pauses it and keeps the thread as
the sole door out, whose only later exits are `retry with:` / `approve` / `close`
[T3-R22]; reject-and-retry and `retry with:` relaunch draft + verify with the
comments as the findings list [T3-R21]. Every effect is an injected port — the
bridge may not spawn `planning/path_b.py` or write a lane — and a refusing or
unwired port reports back into the SAME approval thread [C-16]. Probe:
`probes/probe-chat-approval.js`.

## pause-resume

`pause-resume.js` — the mechanical door (`spec-owner-io.md` §4.2/§4.4/§4.5) and
the resume-semantics table (`spec-recovery.md` §4 [C-14]). A first token of
`pause`/`resume` is the daemon's and bypasses the goal master [T5-R14]. A bare
verb in a goal channel targets that goal; elsewhere the slug is required, and
zero or several matches get the verbatim §4.5 mechanical NACK with no state
change. `pause` flips `running` → `paused` and nothing else. `resume` applies
every matching row: goal `paused` → `running`; counter-exhausted lane re-armed
via the `named-external-input` named event without spending the relaunch budget;
blocked-on-human and gate-cap lanes refused and pointed at their asks. Neither
verb flips an ask off `open`. The ending-store API and the lane enumerator are
injected — no store handle lives here. Probe:
`probes/probe-chat-pause-resume.js`.

⚠ Both doors are constructed and routed by `chat-bridge.js` but their production
ports (`approvalPorts`, `endingStore`) are NOT wired by `index.js#main()`: the
gateway intent set carries no materialize / goal-word intent, and minting one is
an owner act. Until then both degrade loudly, never silently.

## system-digest

`system-digest.js` — the ONE changed-only SYSTEM digest (`spec-owner-io.md` §5
[T5-R13, C-12]). Checks the ten America/Sao_Paulo slots (00, 06, 08, 10, 12, 14,
16, 18, 20, 22 — no check in 00:00–06:00 beyond the 24:00 slot itself); builds the
§5 snapshot of `(open ask ids + one_liners + open condition signatures)` and posts
only when it differs from the last DELIVERED payload. Age is rendered but is not in
the snapshot, so an ageing ask alone never posts. Unchanged → nothing is posted.
The baseline is persisted and moves only on Slack's ack, so a restart does not
re-post an unchanged digest and an unacked digest is re-offered at the next slot.
One post, system channel only, `kind=digest` through the outbox, ordered asks →
conditions → links. Open conditions come from an injected READ port over the
alarm-signature registry (impl-alarms owns the emitter, `ignite/observation/`);
with that interface absent the digest reads an empty set and renders `• none open`.
No emitter and no stand-in registry here. Probe: `probes/probe-chat-glance.js`.

## status-line

`status-line.js` — the one standing glance surface (`spec-owner-io.md` §6
[T4-R5, D-6-ruling]). Renders exactly `N waiting · oldest Xh · M blocked` (zero
case `0 waiting · oldest 0h · 0 blocked`) from injected readers: open ask-records
across all goals, and blocked-on-human lanes plus paused goals as one count.
`Xh` is floored whole hours since the oldest open ask. It NEVER posts — it writes
the bot's Slack status text through an injected port, and only on the seven §6
triggers (ask minted / answered / closed, blocked-on-human stamp / clear, pause
success, resume success). Any other event is refused. Unwired port → a warn, never
a silent no-op. Probe: `probes/probe-chat-glance.js`.

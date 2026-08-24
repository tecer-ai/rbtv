# ignite chat bridge — outbound-only thin sender

The owner interacts with the running ignite system from anywhere via chat. The
bridge receives messages over an **outbound-only** connection (no public ingress),
allowlists the chat-user identity, and forwards validated requests to the gateway
as an **ordinary authenticated sender** — never a privileged path.

Design authority: `…/phase-7-plan/specs/chat-bridge-spec.md` (**ruled**, D105). Realizes
DEC-3's chat clause. This module is the task-7.2 build.

## What it is (and is not)

- One authenticated gateway **sender** — a `kind: bridge` row in the daemon's
  senders registry; its per-sender token is the primary gate (D89). It holds a
  bridge token and the gateway client, and **NOTHING else**: no queue handle, no
  spawn path, no store connection (chat-bridge-spec.md Behavior #5).
- **Outbound-only.** It opens ONLY outbound connections — a WebSocket to Slack
  (Socket Mode) and outbound HTTP to the gateway (loopback/tailnet). It adds **no
  inbound public listener**; the daemon stays loopback/tailnet-bound (Behavior #4).
- The chat-user **allowlist + DM pairing** is the bridge's OWN admission gate
  (D77(B)). It decides which chat principals may drive the bridge; it mints no
  daemon-side principal and does not repair the deliberately-weak v1 authz (D65(B)).

## Transport — Slack Socket Mode (v1, ruled D105)

Slack **Socket Mode**: `apps.connections.open` (app-level token) returns a `wss://`
URL; the bridge opens an outbound WebSocket to it and receives events, acking each.
Owner output is delivered outbound via `chat.postMessage` (bot token). Telegram
(`getUpdates` long-poll) is additive later — a second transport behind the same
`onMessage`/`sendToOwner` shape (DEC-3 "and/or"); not built here.

Turn-boundary ceiling (notes §7b): chat rides the headless model — turn-boundary
dialogue only, no mid-turn interrupt / live TUI (that was the ttyd surface, retired at task 7.29 — a live TUI is now a tmux pane reached over SSH, not a daemon intent).

### Slack event dedupe (at-least-once redelivery guard, D108(C))

Slack Socket Mode delivers events AT-LEAST-ONCE — after a reconnect or slow ack,
the same message event is re-pushed with a NEW envelope id. The bridge drops
redelivered duplicates BEFORE the forward path (allowlist/thread-map/forward),
so one chat message can never enqueue two jobs.

The dedupe key is the message EVENT's identity: `client_msg_id` when present,
else `(channel, event_ts)`. The envelope id is never the key (redelivery mints
a new envelope for the same event). The cache is a bounded in-memory insertion-
ordered `Map` (max ~500 entries, oldest evicted) — consistent with the bridge's
in-memory-by-design architecture (sessions-are-cattle; no persistence).

## One channel per goal (task 7.58, owner ruling `d-channel-per-goal`) — `goal-channel-map.js`

A goal's Slack surface is a **dedicated channel per goal**; the goal `thread` maps 1:1
onto it. The former per-goal chat-THREAD surface is superseded.

**Which surface a message arrived on decides how it routes**, and the bridge decides
that first (`chat-bridge.js` `routeOf`):

| Inbound | Route | Conversation id |
|---------|-------|-----------------|
| **DM** to the bot (`channel_type: 'im'`) | **master** traffic — cold contact, unchanged by the ruling. A DM has no goal, so it can never be attributed to one. | the Slack thread `channel:thread_ts` |
| Message in a **mapped goal channel** | **goal** traffic | the **channel id** — the goal thread IS the channel; sharding by `thread_ts` would split one goal thread into many |
| Reply inside a thread of a mapped goal channel that **this bridge anchored for a named agent** | **agent** traffic (*thread per agent*, ratified 2026-08-09) — homed at that agent's own seat | the Slack thread `channel:thread_ts`. The ONE admitted exception to the row above, and it does not weaken it: the thread exists only because that agent opened it. An **unknown** thread in a goal channel is still **goal** traffic |
| Message **mentioning the bot** (`<@BOTID>`) in an **unmapped** channel or group | **master** traffic (the *mention route*, owner ruling 2026-08-06). A mention **MINTS** the conversation. Replies always post **in-thread**, so each thread is its own parallel sitting and a new thread is a new sitting. | the Slack thread `channel:thread_ts` |
| An **unmentioned** message in an unmapped channel whose thread **already is a conversation** (`threadMap.has(channel:thread_ts)`) | **master** traffic — membership **CONTINUES** the sitting (it takes the follow-up leg). | the same Slack thread `channel:thread_ts` |
| An **unmentioned** message in a channel mapping to no goal and to no known conversation, or a group DM (`mpim`) | **refused**, nothing enqueued | — |

**Mint vs continue.** A mention is what makes traffic attributable, so it is what
*starts* a sitting — but requiring one on every subsequent turn made the owner re-mention
the bot to answer its own question (observed 2026-08-06, minutes after the mention route
deployed: the reply fell into the unmapped-channel refusal and got silence). So: a
**mention MINTS a conversation; membership in an existing one CONTINUES it**. The
continuation test is exactly `threadMap.has(<the id the mention route would assign>)`,
which is self-limiting by construction — a **top-level** message's conversation id is its
own `ts`, always brand new, so it can never match. Only replies inside a thread that
already IS a sitting continue without a mention; an unknown thread, a top-level message,
and the same `thread_ts` in a different channel all stay refused.

> ✅ **Sittings survive a restart when `state_file` is set** (owner ruling 2026-08-06;
> see *Conversation state across restarts* below). The thread map and the reply
> addresses are written to that file on every mutation and rebuilt before the transport
> listens, so an un-mentioned reply in a pre-restart thread still **continues** its
> sitting. The re-mention-after-restart caveat is **retired for deployments that set the
> key**. With `state_file` unset the old limit stands unchanged: the map is in-memory,
> and after a restart such a reply is refused until a re-mention re-mints it.

The mention route **fails closed**. The bot's own user id is resolved once at `start()`
via Slack `auth.test` on the bot token; if that fails the route is never armed and an
unmapped channel behaves exactly as it did before the ruling (refused) — a bot that
cannot say who it is must not guess who was meant. `app_mention` events stay ignored:
member-channel `message` events already carry the traffic, so **the bot must be a member
of the channel** for a mention there to reach the bridge. `mpim` (group DM) stays
refused even when mentioned — it is neither a goal channel nor the 1:1 owner DM the
master path assumes.

The surface gate runs **after** admission, not before: refusing earlier is no weaker,
but it would stop a non-admitted principal from ever reaching the allowlist's pairing
queue, and that queue is the DM-pairing feature (DEC-6).

**The two formerly-open points are settled** — reasoning, alternatives and the
registry-transcription flags are in `goal-channel-design.md`:

- **(a) Creation** — the **bridge** creates the channel, at **goal registration**,
  through one idempotent **name-derived** call (`bridge.registerGoal(goalId)` →
  `ensureChannel`). Only the bridge holds a chat credential. Name-derivation
  (`{prefix}{goalId}`, a bijection) is load-bearing, not cosmetic: the bridge's state
  is in-memory, so a restart rebuilds every binding from `conversations.list` alone
  (`recover()`, run at `start()`) — no persistence, no store handle. Slack's
  `name_taken` is therefore the **adopt** path, not an error. A goal id that does not
  derive cleanly is **refused, never sanitized** — sanitizing would break the inverse
  and let two goals share one channel.
- **(b) Close-time** — **archive, never delete** (`bridge.closeGoal(goalId)` →
  `retire`), idempotent (`already_archived` / `channel_not_found` are success). A
  refused archive **keeps** the binding: the channel is still live, and dropping it
  would leave goal traffic pointed at a channel nobody believes is in use.

**The OWNER — and nobody else — is invited when a REAL goal channel is RESOLVED** (owner
ruling 2026-08-10, issue C-3; supersedes the former never-invite-by-construction bound;
widened from creation-only to created+adopted arms by task 7.680 the same day, because
channels created before the invite shipped were permanently ownerless and re-running
`ensure` was a silent no-op while a live goal sat blocked). Four conjunctive conditions,
all asserted by `probe-chat-goal-channel`: the one configured `owner_user` (default: the
first allowlist entry) · never under a `test-`/`test_` prefix · the created AND adopted
arms of `ensureChannel` (idempotent — `already_in_channel` is benign; `recover()` still
never invites) · and an invite refusal is logged loudly, carried in the result
(`ownerInvited` / `invite`), and never gates creation or message flow. Rationale and the
superseded text: `goal-channel-design.md` § Membership.

**Reaching the current phase-owner voice** (CMP-8 § Thread-model routing) is the
SERVER's derivation, not the bridge's: a sender types its message and never addresses a
recipient. The bridge reaches that voice **by not addressing one** — it enqueues a
`send-message` carrying the goal thread. v1 has no phase-owner router yet, so the goal
thread collapses to the chain-stable `exec-<first exec_id>` (`concepts/thread.md` § v1
interim handle) and delivery reaches that chain's current turn.

**Operator surface:** `goal-channel-cli.js` (`whoami` · `ensure` · `list` · `members` ·
`post` · `retire`) is the stand-in caller until the goal-registration hook exists (task
7.63 `rbtv goal scaffold`). Same functions, same idempotence, invoked by hand rather
than by an event.

**Required Slack bot scopes:** `channels:manage` (create + archive), `channels:read`
(+ `groups:read`, for list/members), `chat:write`, `channels:history`, `im:history`,
`files:read` — not used by the bridge itself, but the SAME bot token is what agents
use (via stools) to download the attachments the bridge's pointer lines announce; without
it every download fails with a scope error. **Optional:** `channels:write.invites` (+
`groups:write.invites` for private channels) — the owner auto-invite above; without it
channel creation still succeeds and one loud warning per creation names the fix. **Optional:** `reactions:write` — the ⏳
pending marker the bridge puts on an owner message while its turn runs and removes when
the answer lands (chat-bridge.js § pending marker). Without it every reaction call fails,
one info line is logged for the whole run, and nothing else changes: message handling and
reply delivery never read the result.

## Thread per agent in a goal channel (ratified 2026-08-09) — `chat-bridge.js` + `bus-ferry.js`

An agent that needs the owner gets its **own Slack thread in its goal's channel**; the first
message of that thread states which agent is talking, and the owner's reply **in that thread
reaches that agent** — with **no LLM in the middle**. The whole store is one map in the bridge:

| | |
|---|---|
| **Key** | `<goalId>#<agent>` → `{ threadTs }`. **Never a run id** — an agent's conversation with the owner is not a property of the run it started in, and the goals layout moves under it. |
| **The channel is NOT stored** | resolved at use time via `goalChannels.resolveChannel(goalId)` — the in-memory read, and on a miss one `conversations.list` lookup for the derived name, since a channel created after this process booted is invisible to the boot-time `recover()`. So a channel re-adoption cannot leave a stale id here, and a miss is never mistaken for an absence. The map holds the one fact only Slack can tell us: which **thread** is this agent's. |
| **Persistence** | additive `agentThreads` key in the existing `state_file`; `version` stays `1`. Losing the map would orphan every open thread — the owner's reply would be handled as ordinary goal traffic by the goal-master. |

**Outbound (agent → owner).** For every gated `to: owner` row the ferry calls the bridge's
`routeToAgentThread`. No thread yet for that `(goal, agent)` → the row is posted **top-level**
and *that post is the thread anchor*, its header led by the agent's name
(`*🧵 <agent>* — <goal> · <type> · #<id>`). A thread already exists → the row is a **reply** on
it. **No sitting is minted by any of this**: the agent already exists and is homed at its seat;
a sitting is minted only when the *owner* replies. When the goal has **no channel at all** the
call first **re-asks Slack** for the derived name (`goalChannels.resolveChannel` — the in-memory map
is filled by `recover()` at boot, and every goal channel is created by a throwaway CLI subprocess
this process never observes) and binds what it finds. Still nothing → `no-channel`, which since
2026-08-12 is an ordinary post failure: the row is **held on the bus and retried**, never downgraded
into the owner's DM. Every other post failure takes that same bounded retry, so a rate limit is
never silently downgraded to another surface either.

**Inbound (owner → agent).** `routeOf` resolves `kind: 'agent'` and `forward-path.js` homes the
session at **that agent's seat** (`resolveGoalSeat(workspaceRoot, goalId, agent)`) — the seat's own
CAST decides harness/model, no profile argument is passed (`#d-abolish-profile-names`,
2026-08-12): a new conversation is a `session-create` there — which **revives** the seat
headless with the owner's reply as its bare prompt — and an existing one is the unchanged
`send-message` follow-up on the chain the seat already holds. If a live turn still holds that
seat, the daemon's idempotent door suppresses the create and the owner gets the existing
seat-busy notice; if the seat is **gone** (its run closed, or it was never materialized under
the currently-open run) nothing is enqueued and the thread gets the fixed notice
`⚠ that agent's seat is no longer open — its thread can't be answered`.

### The two gates on agent-initiated contact — ⛔ DELETED (core redesign, 2026-08-24)

⚠ **BOTH GATES AND THE PARK ARE GONE** [D24, T2-R17, D-7-ruling, T2-R14]. They are described below
only so a reader of older code, an older probe, or the `messages.md` history knows what the deleted
rungs were. **Nothing in `bus-ferry.js` reads either gate any more**, and the module emits no
`PARKED` line at all.

What they were: the ferry reversed its "fail toward delivery" default here — an agent *opening* a
conversation at the owner defaulted to **zero pings**, and two declarations earned one. A row that
earned neither was **swallowed**: nothing posted, cursor advanced, nothing ever re-delivering it.
That is the silence the redesign exists to end — work-content questions died there.

What replaced each rung, none of them a gate:

| Deleted rung | What answers it now |
|---|---|
| **1 — the seat is human-interactive** | Interactivity is a **per-seat** property and a non-interact seat never knows a human exists; its work-content question becomes a **daemon-posted ask** labelled `work-content` [T2-R17, D-7-ruling] — a real ❓ thread, not a park. The flag still binds at the seat's own **send door**: `ask-thread.js#postAsk` REFUSES a non-designated seat's owner-ask and says so [T2-R14]. A refusal is reported; a park was not. |
| **2 — the goal is interactive** | Goal-level interactive/autonomous mode is **dead** [D24] — a goal can no longer mute a seat. `goalExecutionMode` is still exported and still read by other consumers; the ferry asks it nothing. |
| **the seat's `fallback: park` arm** | `park` described what a seat did when the owner was **unreachable**. Under thread-per-ask he is reachable, so the arm survives as a **render mark only** (and `park` carries none) — see the arm table below. |

The two gates, as they were declared while they existed:

| Gate | Where it was declared | Absent meant |
|------|----------------------|--------------|
| **1 — the seat is human-interactive** | `human-interactive: yes\|true` in the sending seat's `seat.md` **frontmatter** — the first `---`-fenced block only, so a briefing line in the BODY that quotes the flag cannot open the gate (one file read, memoized per pass) | not human-interactive |
| **2 — the goal is interactive** | a THREE-RUNG ladder (owner ruling 2026-08-10, issue C-4): **(1)** one word in `.rbtv/goals/<goal>/execution-mode` if that file is there — the PER-RUN POSTURE, which always wins, because the console flow writes `autonomous` there when the owner walks away and a birth attribute must not override a human saying "not now" (`goal_creation_request.py` also writes this file at creation now, per the same 2026-08-10 ruling — a workflow declares a default, creation writes it, a requester may override per goal); **(2)** file absent → the goal's BIRTH ATTRIBUTE, `goal-kind: interactive` in `goal.md` frontmatter (rung 1 covers every daemon-created goal today, but a goal born some other way can still land here); **(3)** neither → `autonomous` | **`autonomous`** — an unreadable file and any other word read that way at rung 1, and so does any `goal-kind` that is not exactly `interactive`, no key, no frontmatter or no `goal.md` at rung 2. A goal nobody declared reachable is not reachable; the owner flips it when he is |

⛔ **THE PARK IS DELETED.** A blocked row used to be disposed of *by policy*: nothing posted
anywhere, the cursor advanced, and no retry, replay or queue ever surfaced it again. Every
`to: owner` row now **travels** — as a real ❓ ask thread where `postAsk` is wired, and otherwise
down the agent-thread / DM legs it always had. The ONE outcome that still posts nothing is the
[T2-R14] refusal at `ask-thread.js#postAsk`, and that is not a park: the caller is told, and the
row stays on the bus for the bounded retry instead of being swept past.

### The ask door, wired (spec-owner-io §2/§3)

`chat-bridge.js` builds `ask-thread.js` and holds ONE map for it — `askThreads`,
`<channel>:<threadTs>` → `{ goalId, seat, askId, label }`, persisted additively in the state file
(`STATE_VERSION` unchanged). It carries no ask **state**: state is `open_asks`, daemon-side, and a
second copy of it in this process would be a second source of one fact.

| Direction | Path |
|---|---|
| **Outbound** | the bus ferry's injected `postAsk` → `postOwnerAsk` → resolve the goal channel (`resolveChannel`, shared with `routeToAgentThread` via `goalChannelFor`) → `askDoor.postAsk` → record the map entry and the reply address. A 💭 note is **not** entered in the map: it mints no record [§2.1], so there is nothing to release. |
| **Inbound** | `onChatMessage` looks the thread up in `askThreads` **before every other leg**, keyed off the raw event (`_channel`/`_threadTs`) because for goal traffic the routed conversation id IS the channel and cannot tell one ask thread from another. A hit is handled at the release door and **does not fall through** — a fall-through would mint a sitting on an unauthorized remark and answer an authorized one twice. |

The map entry is dropped **only on an actual release**. Wrong thread, unauthorized sender,
unparsed token and a mechanical verb all leave the ask `open` — and an ask still open whose thread
the bridge has forgotten is an ask that can never be answered.

**Every `to: owner` row is carried** — that address IS agent-initiated contact. Owner-initiated flows were untouched by
construction even while the gates existed — that address IS agent-initiated contact, so there is no nobody-home precondition. Owner-initiated flows are untouched by
construction: DMs, mentions, owner replies, and a row answering **into** a thread the owner
wrote in — the latter carries a `[chat-thread:]` token and takes the return leg *before* either
gate is read.

### The seat's fallback arm — now a RENDER MARK ONLY (task 7.626, owner ruling `d-s19-fallback-rides-goal-channels`; `park` retired by D-7-ruling, 2026-08-24)

A `human-interactive:` seat is REQUIRED to declare, in the same frontmatter, what it does when the
owner is not standing at a terminal — `fallback: park | default-and-disclose | block-and-queue`
(planning-v4 D14 via D19). On the **daemon lane** that is always the case, and the ruling is that no
terminal is needed: **this channel, with its thread per agent, is the owner surface.** Until 7.626
the field was validated at materialize time (`component-lint --check interactive-fallback`) and read
at run time by nothing, so all three arms behaved identically. They now differ **here**:

| `fallback:` | the row | the seat |
|---|---|---|
| `park` | ⛔ **NO LONGER A DISPOSITION.** The row is **delivered unmarked**, exactly like an absent arm — the mark table deliberately carries no entry for `park`. The word described an owner who could not be reached; under thread-per-ask he can be [D-7-ruling] | proceeds |
| `default-and-disclose` | delivered into the seat's thread, header marked `· ℹ proceeding on its default` | proceeds |
| `block-and-queue` | delivered into the seat's thread, header marked `· ⏸ WAITING ON YOU` | **is HELD — mechanically.** Its dependents do not start until it is answered; see below |
| **absent** | delivered **unmarked** — the header is byte-identical to the pre-7.626 one | proceeds |

⛔ **WHAT "PARKS ON THE BUS" MEANT — kept only so the deleted behaviour is legible.** The cursor
advanced and nothing ever re-delivered the row: no retry, no replay when the mode or the arm
changed, no queue that surfaced it — `owner` is a reserved address with no seat, so `coord.py`'s
pending-message view could never show it either. A parked row was discoverable from the
`messages.md` log and from the asking seat's own live session, and nowhere else. **That is the
defect, not the design**, and it is why nothing in this module parks any more.

**`block-and-queue`'s answer leg is not new — it is § *The loop, end to end* above.** The owner
replies in that thread → `kind: 'agent'` → a `session-create` at the asking seat's own home with his
words as the prompt. That revival **is** "the seat proceeds", which is why this shipped as a gate
rung and a marker rather than machinery.

**Absent is not a fourth arm, deliberately.** A flagged seat with no `fallback:` is a lint violation;
letting it *acquire* an arm would be a behaviour bought with a defect. `engine/lane-watch.js` warns
about exactly that case on the daemon lane and names the check.

**The reader is `seatFallback` in `bus-ferry.js`**, beside the two gate readers and scoped to the
same first `---`-fenced block — a line in a seat's PROSE cannot arm anything. The daemon lane imports
it rather than parsing the descriptor a second time. ⚠ **The arm is the SEAT's declaration and this
module has no lane** — which now costs nothing, since the arm only decides a header mark.

⚠ **AN UNANSWERED OWNER-ASK HOLDS THE SEAT — and NOT because of the arm** (W2, superseding
`d-block-and-queue-mechanical-hold`, 2026-08-10). The arm's one-home definition
(`meta/planning/references/file-prompt.md` § `fallback`: *"hold the seat, queue the question for
review"*) still **stands**; what changed is that the hold stopped being conditional on it. A seat
with an open `to: owner` ask is held whether or not it declared `block-and-queue`, whether or not it
is `human-interactive`, and whether or not the ferry delivered the ask — **those three gates were
the incident**, each one a way for a real unanswered question to release the DAG anyway.

**Where the hold lives — one verdict, in `coord.py`.** `ready-seats` reports `HELD` for any seat
carrying an open ask to the owner, above `DONE` in its own precedence, so a seat that checked out
while its question was unanswered cannot mask it. It is computed by the surface that already knows
what every seat declared, from the bus it already parses; **nothing in JS parses that question
again**. `engine/execution-record.js#blockAndQueueVerdict`, `#askParkedAtGate` and `#outcomeForSeat`
are **deleted**.

**And it is NOT in the execution record.** The process record publishes **no work outcome at all**:
`clean | crashed | killed` are killed as work words (spec-state-store §1.7, §4.4 Row D), because
they said what became of a PROCESS while readers took them for what became of the WORK. What the
observer saw survives as the `evidence_pointer` and the required `reason_class` on a `failed`
ending — a crash is `failed` / `crash` carrying the exit code and transcript tail, never a bare
outcome word with no reason. `blocked` is not an outcome word either, for the same collision.

The engine's role is CONSUMPTION — `engine/seeding.js#recordView` folds the DERIVED wait (§2.1: an
`open_asks` row that is `posted` and still `open`, which `ready-seats` renders as `HELD`) into
`view.blocked` and the ending store's `ending: done` rows into `view.done`, and every downstream
reader (`seatState`, `attached-execution.js#evaluateExit`, `--status`) inherits that one view.

**What releases it: the owner's answer, recorded onto the bus** — § *The answer goes back onto the
bus* below. Once the ask carries an `answer` row naming it, `ready-seats` stops reporting `HELD` and
`coord.py cmd_checkout` (which refuses a `done` while the ask is open) admits the check-out that
satisfies the successors' `after` members. The reply also mints a `session-create` at the seat's own
home, so the seat can finish its work; while that revived session runs, the record's **last** row is
open and the dependents wait through it.

⚠ **ONLY A `type: answer` ROW COUNTS.** A `note` addressed to the seat does not release it: the
closed CMP-8 vocabulary has a word for answering and a different word for remarking, and a peer's
aside must not release a wave. Unlike the deleted mechanism, an answer arriving **after** the seat
exited works — the hold is recomputed from the bus on every `ready-seats` call rather than frozen
into a cell at close time.

⚠ **THE REVIVAL FIRES ON THE NEXT TICK**, so something must be ticking. The daemon is; an attached
run that returned `blocked` has already exited, and the operator must re-run `rbtv run` after
answering. The hold is on disk, not in the process, so nothing is lost by the gap.

### The parked ask: the SEAT is held either way, the DEPENDENTS still are not

Owner ruling **`d-parked-ask-autonomous-workaround`** (2026-08-10), correcting the framing this
section carried as its "one standing hazard": *"the autonomous mechanism does not exist to prevent
me from getting messages; it exists to make agents complete workflows fully autonomously."*

**AUTONOMOUS MEANS THE WORKFLOW COMPLETES.** ⚠ **W2 SPLIT WHAT THIS RULING USED TO DECIDE IN ONE
PLACE, and reading the old single row will now mislead you.** `ready-seats`' `HELD` verdict consults
**no** gate — the seat is held on an open ask either way. What still consults them is a *different*
door: `coord.py cmd_checkout` calls `ask_parked_at_gate`, so whether the seat's `done` check-out is
admitted — and therefore whether its **successors** advance — still turns on delivery.

| the seat's `to: owner` ask | the SEAT | its DEPENDENTS |
|---|---|---|
| **delivered** (both gates open) | **HELD** — never offered by `ready-seats`, reported `blockedOnOwner` | **wait** — the `done` check-out is REFUSED while the ask is open; `--relaunch <seat>` is the escape |
| **parked** (gate 1 or gate 2 shut) | **HELD** just the same — the verdict has no gate | **advance** — the check-out is admitted, and the wave runs on to completion |

⚠ **THE BOTTOM-RIGHT CELL IS A MEASURED RESIDUAL, NOT A DESIGN CLAIM** — pinned at
`engine/probes/probe-owner-ask-hold.js` arms U1/U2 and recorded there as a FINDING. Whether the
dependents advancing on a parked ask is the intended shape of this ruling or a surviving limb of the
incident W2 closes is an **owner call**; the probe records it and rules nothing.

In the parked case the seat executes its **authored autonomous workaround** (`d-s14-autonomous-dod`
+ planning-v4 D16): derive the answer, record it with provenance in the goal's own ledgers
(`decisions.md` / `doubts.md`), proceed. The parked ask stays on the bus and the derivation is in
the ledgers, so both are there for the owner on return. Holding instead would stall a goal on an
answer that cannot exist — which is what a previous version of this build filed as a dead end and
the owner ruled is simply the autonomous path.

⚠ **THE OBLIGATION IS THE SEAT'S, AND ITS ENFORCEMENT IS THIN.** Nothing in the engine derives an
answer or writes a ledger. `component-lint`'s `interactive-fallback` check (M9) enforces only that a
flagged prompt **names** an arm from the vocabulary — it does not check that the prompt's procedure
carries a workaround at all. Two authoring prompts do state the duty (`planner.md` and
`task-definer.md`: *"an INTERACTIVE task is never load-bearing for correctness… its done contract
MUST carry the autonomous fallback arm"*), so the gap is enforcement, not doctrine.

⚠ **HOW DELIVERY IS DERIVED, with no new state.** The ferry's park decision writes nothing — no
state file, no bus row, no marker — it is a pure function of three files, evaluated per row in the
`gate` ladder above. ⚠ **THE ENGINE NO LONGER RE-DERIVES IT AT ALL** — `askParkedAtGate`, its
second reading of these gates, is deleted with W2; the one surviving reader is `coord.py`'s own
`ask_parked_at_gate`, at the check-out door. The skew is one tick: an owner who flips
`execution-mode` between the ask and the seat's exit gets the mode in force at the close, and both
directions are safe.

⚠ **THERE IS NO `--relaunch` ESCAPE ANY MORE (D12, 2026-08-20).** The one-shot grant that used to
release a held seat is deleted with the rest of the grant machinery. A seat held on an unanswered
owner ask is released by the ANSWER — mechanically, by the reap of its `open_asks` row, which the
daemon performs in the SAME transaction that signals the seat's relaunch (`spec-state-store` §2.8:
no orphan ask, no twin relaunch). The hold itself is DERIVED and never stored (§2.1: an ask that is
`posted` and still `open`), so there is no held-flag to clear.
`rule-disposition`, the leader verb that used to release a
seat nobody would answer, is itself deleted [T2-R12, T1-R9] — that release path does not currently
exist; owner authorization is now an answer to a live ask, and that door is not wired here yet.

✅ **THE REVIVAL NO LONGER RACES THE DEPENDENTS (7.626 review F6, CLOSED).** The revival still mints
a second `executions.csv` row for the seat — and since W2 the two facts come from **different
surfaces**, which makes the independence structural rather than incidental: done-ness is the seat's
check-out disposition on coord's answer, and *not finished* is the record's **LAST** row (still
open) plus coord's `HELD`. `finished` is the set that reconciles them, so `--status` reports the
seat `live` while a live session runs in its home instead of `done`, and the dependents stay held.
The concurrency this section previously disclosed as *"safe but real"* is gone rather than accepted.
Measured by `engine/probes/probe-owner-ask-hold.js` (arms H\*/P\*, plus the § F control/treatment
pair for this row specifically).

### The return leg into a goal channel

⚠ **The token is VERIFIED before it counts** (S-13 owner ruling `d-s13-chat-thread-token-verified`).
A `[chat-thread:]` token is text an agent wrote in a bus row, and until this ruling it was obeyed on
sight — which made it an instruction to post into any Slack thread the sender cared to name, and to
mint a channel-master sitting on it. The bridge now vouches for it or it does not count: a token is
honoured only when it names a thread **the bridge already knows** — present in `replyAddr`, the
**thread map**, or the **agent threads** (any of the three; an anchored agent thread is in the set
by construction, so the leg below keeps working unchanged).

**An UNKNOWN token is treated as if the row carried none.** Not dropped, nothing posted to the
invented thread, nothing minted: the row falls back to the ordinary path — `to: owner` → the two
gates → the agent's thread or a PARK; anything else → cursor advance. One info line names the
ignored token. The check sits at the ferry's hand-over as an injected `knowsThread` predicate (the
same shape as `routeToMaster`), because only there is the ordinary path still available — the ferry
itself holds no map.

**The restart case is covered by PERSISTENCE, not by trust.** `state_file` restores all three tables
before the transport listens, so a token naming a pre-restart conversation is known. With no
`state_file` the bridge forgets and therefore declines — the honest answer, and the reason the old
*derive the reply address from the token's text* branch is **deleted** rather than disabled.

A bus row whose `[chat-thread: <channel>:<ts>]` token names a channel that **maps to a goal** is
posted into that thread **verbatim, minting nothing**. The DM-thread mint exists to give the
*channel master* a sitting for a row the owner would otherwise triage; a thread inside a goal
channel is already an agent's conversation, and minting a `kind: 'master'` sitting for it would
home a channel-master at the master workdir on a goal's surface — exactly the widening the
`CHAT_THREAD_RE` note in `bus-ferry.js` warns against. A **failed** post there returns the
failure rather than falling through to the DM leg (which would mint that wrong seat on a
transient rate limit); the ferry retries it bounded and then gives up loudly, like any other
undeliverable row.

### `[deliver: post|wake]` — what the named thread DOES with the row

The token above answers *where* a row goes. `[deliver: …]`, read only beside it, answers *what
happens there* — because an async job's settled outcome and a seat's answer want opposite things
from the same thread. Design: `live-session-design.md` §3.

| token | at a DM/master thread | why |
|---|---|---|
| *(absent)* | the sitting is minted, **nothing posted** | the ruled 2026-08-07 behaviour, unchanged. A seat answering the owner wants the channel-master to handle its row, not the raw row pushed at him. Every producer that predates the token keeps its behaviour with no edit |
| `post` | the row is **posted verbatim**, nothing minted | a settled job's outcome is a fact already composed by the tool. Routing it through an LLM turn costs the whole spawn pipeline (~12s) to re-say one line, and `i-no-completion-nudge` is that the owner is *not told* — not that nobody paraphrased it |
| `wake` | posted verbatim **and** a sitting minted with the row as its prompt | a settled job carrying something to act on. Never instead of the post: the owner is told either way |

The post comes first and a failed post mints nothing — the ferry retries the row, bounded, exactly
as everywhere else. On a **goal-channel** thread the row is posted verbatim regardless (that branch
already does), and `wake` degrades to `post` with a warn: a `kind: 'master'` sitting is never minted
on a goal surface.

Producers today: `capabilities/master-profile` emits `[deliver: post]` on its settled-outcome row.
(`capabilities/goal-launch-delay` was the second producer until task 7.778 deleted that capability
with the goal-launch door it tuned.) Nothing emits `wake` yet — the disposition is the
mechanism, and a producer opts in with one token.

### The loop, end to end

Agent X posts a bus row `to: owner` → both gates pass → the row anchors
X's thread in the goal channel (**no sitting**). The owner replies in that thread → `kind:
'agent'` → a `session-create` at **X's own seat** revives X with the reply as its bare prompt (a
chain is minted), **and the reply is recorded back onto X's bus as a `type: answer` row** (see
below). X's next `to: owner` row → ferried into the **same** thread (the map is keyed on `from`).
The owner's next reply → a warm turn, else a `send-message` **follow-up** on X's chain — **and that
one is recorded onto the bus too**, at whichever of the two answered. No relay LLM anywhere; the
only sittings are the agents themselves.

### The answer goes back onto the bus (task 7.771, owner ruling 2026-08-11 § D8)

Delivering the reply was never the whole act: until this row **nothing recorded anywhere that the
ask had been answered**. The bus kept every question and no reply, so nothing that reads it could
ever see an ask close, and a seat could check out past a question the owner had already answered.
⚠ **This leg matters MORE since W2, not less**: the hold is now recomputed from the bus on every
`ready-seats` call (`coord.py`'s `HELD` verdict and its `cmd_checkout` gate), so **the answer row IS
the release** — there is no engine-side verdict left that could be persuaded any other way.

So the bridge makes ONE extra gateway call — `record-bus-answer { goal, seat, corpus }` — and the
**daemon** shells to `coord.py send <seat> --type answer --file <body> --as owner --force
[--re <ask#>]`.

**ONE implementation, THREE doors** (owner review, 2026-08-11). "The owner answered" is ONE FACT,
and an owner turn can arrive through any of three paths: `onChatMessage` forks on
`threadMap.has()`, and `chat-bridge.js` tries the warm path ahead of both. The first cut recorded on
the session-create leg only — the same single-source-of-truth defect this design exists to delete.
Every door now calls `forward-path.js#recordBusAnswer`; the `route.kind === 'agent'` guard lives
inside it, so a `goal` or `master` surface writes nothing at any door.

| door | fires when | its own success condition |
|---|---|---|
| session-create (reply #1) | the thread has no chain yet | the enqueue was accepted **and** not suppressed at the idempotent door |
| follow-up (reply #2+, cold) | the chain exists, warm declined | same, **and** not a corrective redispatch |
| warm (reply #2+, live session) | `chat-bridge.js` — the session answered | `warm.answered` — the seat CONSUMED the words. Whether the agent's reply then posted to Slack is the other direction and does not un-answer it |

**Exactly one fires per owner turn**, by construction: a warm answer returns before the forward
path is reached, and the cold fork is exclusive. The call stays on each door's own success path and
is **never hoisted into `onChatMessage` ahead of the fork** — the seat-busy branch deliberately does
not deliver, so an answer recorded there would assert the owner answered while nothing reached the
seat.

| bound | why |
|---|---|
| the **bridge never spawns** | `chat-bridge-spec.md` lines 14/26 and `probe-chat-boundary`. The bridge asks; `engine/bus-answer.js` acts. Same split `live-sessions.js:10-15` describes for the warm-session manager |
| **coord is the only writer** of `coordination/messages.md` | a second writer from JavaScript is the defect class D8 deletes. This side holds no format, no lock and no append |
| `--force` | three `cmd_send` gates written for SEAT-TO-SEAT traffic can refuse the write and lose the owner's answer: **length** (`MESSAGE_MAX = 2000` vs. arbitrary Slack text), closing seat, bounded inbox. ⚠ **unknown recipient is NO LONGER among them** — W3 made that refusal `--force`-proof (`cmd_send`, the `args.to not in known` arm), because staff chairs are now in the admitted set and the override had nothing left to be right about. `bus-answer.js` checks the seat folder first and reports `no-such-seat` itself |
| `--re` is **resolved, not carried** | the bridge cannot know the ask id (`agentThreads` stores only `threadTs`); the daemon derives it from the goal's own bus through `execution-record.js#openOwnerAsks` — the SAME pairing the hold makes, so coord's `pending` and the hold cannot disagree |
| the goal and seat names are **validated at three doors** | they arrive from an internet-facing component and become path segments under `.rbtv/goals/`: shape at the gateway, shape again at the core (DEC-3), then shape + **existence on disk** in `bus-answer.js` |
| authorization is **`kind: bridge` only** | the row clears a seat's mechanical hold, so an `agent` token must not be able to forge one and release its own hold (`authz.canRecordBusAnswer`) |
| **delivery never fails because the bookkeeping failed** | the reply reaching the seat is the load-bearing act and has already happened. Every failure is logged at `warn` and changes neither the outcome nor the exit path |

⚠ **A CORRECTIVE REDISPATCH IS NOT AN OWNER ANSWER** (ruled 2026-08-11). `chat-bridge.js` calls the
follow-up leg with `corrective: true` as the reply contract's revive turn — the BRIDGE re-asking a
worker that returned a malformed reply. The owner sent nothing, so recording an `answer` on his
behalf would clear a seat's hold on the strength of a schema complaint. Same reasoning that already
makes a corrective post no decline notice and never type `answer`.

⚠ **THE GATE IS NOT `replyType === 'answer'`, THOUGH IT LOOKS LIKE THE TIGHTER CHECK — IT IS DEAD
CODE.** `replyType` is `answer` only when `entry.pendingAsk`, and **nothing sets that true in this
deployment**: `setPendingAsk(true)` fires only from `deliverToOwner({ markAsk: true })`, and every
live call site passes `markAsk: false` (`reply-leg.js:489` — "ask-detection out of scope v1"). A
ferried agent ask does not set it either — `routeToAgentThread` posts through
`transport.sendToOwner`, which never touches the flag. Gating on it would read as correct and never
once fire, on the precise surface this whole mechanism exists for. Grep before restoring it.
*(Consequence beyond this row: D105's reply-type pinning is inert — every follow-up is typed `note`,
so the store's `messages` never carries an `answer` either. Separate defect, not fixed here.)*

⚠ **A DOOR-SUPPRESSED ENQUEUE RECORDS NOTHING.** `heart-store.js#enqueue` returns
`{ deduped: true }` *before* the INSERT and discards the payload — the owner's corpus with it. The
store's own comment makes the rule general: *"a caller that must not lose its payload MUST read
`deduped` rather than treating a returned id as delivery."* Whether a `send-message` job can key
that door depends on whether its catalogue row is homed, which is deployment state — so the write
requires unambiguous delivery instead of guessing. ⚠ The follow-up leg's own `forwarded: true`
still ignores `deduped`, unlike the session-create leg's; a latent gap, named not fixed.

## The warm path — live sessions (`live-session-design.md` §1/§4, built 2026-08-10)

A conversation whose seat declares `human-interactive: yes` and whose profile is a **claude** one
is answered by a **warm process held open across turns** instead of a fresh one-shot spawn. It
removes the three costs a cold turn pays that have nothing to do with thinking: the queue+tick
decision (~1s), process creation (systemd-run + bwrap + CLI boot, ~2.75s) and the reply-leg poll
(~1.5s).

⚑ **The manager is DAEMON-SIDE** (`server/spawn/live-sessions.js`), and this subtree could not
hold it: `probe-chat-boundary` scans every runtime `.js` here for `child_process` and a
process-launch call, so Behavior #5's "no spawn path" is structural, not a habit. `live-sessions.js`
here is only the CALLER — it makes one `live-feed` gateway call on the same forwarder, holds no
process, no timer and no registry. §4's ruled DIRECT feed is intact: one loopback call, no queue
row, no tick.

| | |
|---|---|
| **When it is tried** | On every admitted owner turn, BEFORE the forward path, for a conversation that already holds a chain (`threadMap.has` + a known `sessionExecId`). The FIRST message of a conversation is always cold — it is what mints the chain a live session RESUMES |
| **Every refusal falls through** | `attempt()` returns `answered: false` for not-warm, ineligible seat, non-claude harness, gateway down, turn timeout, session died. The caller then runs the forward path it would have run anyway, so **the cold path is byte-for-byte unchanged** and `live_sessions: false` restores the pre-live behaviour exactly |
| **The reply** | Posted straight into the thread via `deliverToOwner`. No reply-leg arming and no ⏳ marker — both exist to cover a gap of minutes, and there is none here. An answered turn whose reply cannot be POSTED stops there and says so, rather than re-asking the agent a question it already answered |
| **Eligibility** | Gate 1: `human-interactive: yes\|true` in the seat's `seat.md` **frontmatter** (a body line cannot open it). Gate 2: the profile's harness is **claude** and it declares a `resume:` template. `--input-format stream-json` is claude's flag; no other harness's equivalent has been measured, so a non-claude profile is INELIGIBLE rather than guessed at |
| **Continuity** | A live session is always a `--resume` of the chain's `session_ref`, resolved daemon-side from the `exec_id` — never from the wire. The ref is one value for the chain's life, so a reaped session and the cold `--resume` that replaces it are the same conversation |
| **Reaped on** | 10 idle minutes after the last OWNER message · natural exit · a profile switch (the next message names a different profile) · the LRU cap · bridge/daemon shutdown |

| Config key | Where | Meaning |
|------------|-------|---------|
| `live_sessions` | this bridge's JSON config | boolean, **default `true`**. Whether to try the warm path before the cold one |
| `RBTV_IGNITE_LIVE_IDLE_MS` | the **daemon** unit | idle window, default `600000` |
| `RBTV_IGNITE_LIVE_MAX` | the **daemon** unit | warm-session LRU cap, default `4` |

The last two are the daemon's, not this config's: they govern processes the daemon holds and the
memory they occupy, and a bridge that could set them over the wire would be dictating another
process's resource policy.

⚠ **On this deployment the warm path is armed and INERT pending two owner decisions** — the master
profile is `kimi` (not claude) and the channel-master seat declares no `human-interactive:`. Both
are stated with their options in `live-session-design.md` § *On this deployment, nothing is
eligible yet*.

## The forward contract (D104/D105) — `forward-path.js`

One chat thread = one conversation. A message from an admitted principal becomes
exactly one gateway call, always `enqueue-job` (the bridge adds no new intent):

| Case | Forward |
|------|---------|
| **First** message in a new chat thread | `enqueue-job` naming a session-creating **launch-agent** function + a named launch profile (DEC-1 R3). The bridge never spawns; the ticker's Dispatch phase does. |
| **Follow-up** in a mapped thread | `enqueue-job` carrying a **`send-message`** action-type job addressed to the mapped turn-chain's thread (`exec-<first exec_id>`). Reply type `answer` on a pending `ask`, else `note` (closed CMP-8 vocabulary). |

**NEVER `send-to-session`** (D104): that leg was `session_mode: headed` + live only
(the pty keystroke rung). Chat rides the headless turn-boundary ceiling. There is
no send-to-session code path in this module, by construction — and since task 7.29
retired the intent, there is none anywhere: the constraint is now structural rather
than a discipline this module keeps.

### The prompt is the bare user text, plus at most one correlation line (owner ruling 2026-08-06, amended 2026-08-07)

A session-create carries `args: { prompt }` — no `profile` (`#d-abolish-profile-names`,
2026-08-12) and no `workdir` (the seat's home resolves it) — where **`prompt` is the
user's message, verbatim** — on the master, mention and goal legs alike. The bridge
ships **zero behavioural text**: who a session is and how it answers travel with the
seat it is homed at, through that seat's `seat.md` and the auto-injected `CLAUDE.md`
chain above it. That keeps identity in one place its owner edits, and keeps
instance-specific paths out of repo source (the retired `MASTER_CHARTER` constant
carried an absolute `/home/…` path).

**THE ONE ADMITTED PREFIX (owner amendment 2026-08-07, goal ledger
`r-bare-prompt-admits-one-correlation-id`).** The prompt may begin with exactly ONE line,
`chat-thread: <channel>:<ts>`, followed by a blank line — the sitting's own thread id, so a
sitting that relays a question onto the coordination bus can say where the answer belongs.
Before the amendment nothing could tell a sitting which thread it was, which left the
master→channel-master return leg with no producer for its routing token.

**The ban on behaviour is unchanged and total** — no charter, no identity, no instructions,
no instance paths — and this admits ONE addressed FACT, on the chat legs only. The probes
were NARROWED, not relaxed: `probe-chat-mention-route` and `probe-chat-bus-ferry` strip at
most one line of that exact shape and assert the remainder is the user text verbatim, so a
charter is still caught. Any other prefix is still a failure.

⚠ **Plain here, BRACKETED on the way back.** Only `[chat-thread: …]` routes a bus row to a
thread (`bus-ferry.js`). The plain form is deliberately inert: if a relay carried the
bracketed form, the ferry would read an outbound question as an inbound answer and mint a
sitting from it — the question returning to its own thread.

### Where a session runs

| Leg | `args.workdir` |
|-----|----------------|
| master (DM) and mention | `config.workdir`, unchanged |
| **goal channel** | the goal's **`goal-master` seat**: `<workspace_root>/.rbtv/goals/<goalId>/runs/<open run-id>/seats/goal-master`, resolved per message from that goal's `runs.csv` row with `state=open` |
| **agent thread** in a goal channel | **that agent's own seat** — the same resolution with the seat name parameterized (`resolveGoalSeat(..., route.agent)`). The owner is answering the seat that asked, so homing the answer anywhere else would need a relay to carry the question back. The name is validated as a seat NAME (it arrives from a bus row's `from:` field, and a traversing token would resolve a dir outside the run — which becomes a session's cwd). Missing seat → nothing enqueued + `⚠ that agent's seat is no longer open — its thread can't be answered` |

If `workspace_root` is unset, `runs.csv` is missing, no run is open, or the
`goal-master` seat directory does not exist, the bridge enqueues **nothing** and posts
a decline on the goal's channel: it lists each live agent thread in that channel
(agent name + Slack permalink) so the owner can reply there, or says `no agent thread
is open yet in this channel — an agent will open one when it needs you`. There is
deliberately **no fallback workdir**: a session launched outside its seat would run
with no descriptor and no goal identity at all, which is worse than not running.

⚠ **Both rows above are SHARED seats, so a returned queue id is NOT delivery.** The
daemon's idempotent door (ruling `d-q9-door`) dedups `launch-agent` enqueues on a
(run, seat) key and returns **before** the INSERT — a suppressed call's `args`, the
user's text included, are discarded and the caller is handed the **held** operation's
id. Every master sitting shares one `config.workdir`, and every sitting of one goal
shares that goal's `goal-master`, so a new conversation opening while that seat holds a
live turn is exactly the suppressed case.

⚠ **SINCE P2 THE BRIDGE ASKS THE DAEMON TO QUEUE INSTEAD.** Every session-create carries
`on_seat_busy: 'queue'`, and the daemon inserts the row into its persistent queue and launches
it when the seat frees, oldest first (rows older than an hour are dropped daemon-side with an
owner note). Nothing is discarded and nothing is held bridge-side: **the whole pending-re-submit
machinery — the held-text map, the poll-pass sweep, the give-up notice, the state-file key — is
DELETED**, because it was a queue reimplemented inside a transport that restarts. The `deduped`
branch REMAINS as the honest refusal for a daemon that rejects or ignores the flag: it maps
**nothing**, returns `forwarded: false` with `reason: seat-busy-deduped:<what held it>` plus
`undeliveredText`, and posts the seat-busy notice below.

⚠ **AND SINCE THE SEAT SHARD, TWO DM CONVERSATIONS RUN SIDE BY SIDE** (2026-08-17). Queueing made a
busy master seat lossless; it did not make it concurrent. `workdirFor` falls through to the ONE
configured `workdir` for every master/DM route, so the daemon's seat key was identical for every
conversation the owner had and the ticker's seat-busy gate serialized the whole surface — a question
typed in thread B waited out an unrelated twenty-minute turn in thread A. A master session-create now
also carries **`seat_shard: <chat thread id>`**, which the store stamps into the row's args and
`heart-store.js#seatKeyOf` appends to the seat key. Two threads therefore key differently and neither
defers behind the other; **two messages of ONE thread carry the same shard and still serialize, in
order**, which is the property the seat key exists to hold.

- **MASTER ONLY.** A `goal` or `agent` thread homes at a real seat coordinating a live taskforce;
  running two of those in one seat folder is a different question and is not answered here. The
  field is set on the `workdirFor` fallback arm alone (`home.master`).
- **The bridge's two pre-enqueue guards below are deliberately NOT sharded.** The duplicate guard's
  case IS the cross-thread one — the observed incident was one DM redelivered across a reconnect as
  two thread ids — so sharding it would delete the protection it was built for; and the pending cap
  stays a bound on the whole master surface.
- **Fail-open at the transport.** A thread id that could not satisfy the daemon's shard shape
  (`1-200 chars, no whitespace, no #`) is simply omitted rather than sent, because a shape refusal at
  the gateway would take the owner's whole message down with it. None does today.

⚠ **WHAT THE BRIDGE STILL OWES, BEFORE THE ENQUEUE.** A queue that never refuses collapses
nothing, so two guards run in `chat-bridge.js#onChatMessage` ahead of the forward path, on
SESSION-CREATES only (a follow-up rides `send-message`, which the seat door never keys):

- **the byte-identical duplicate** — the last text sent to each *seat home* is remembered for
  10 minutes, and a byte-identical repeat is dropped with the duplicate notice and never
  enqueued. Slack redelivery doubles are real (owner-observed 2026-08-12: the same DM 22 s
  apart with different `ts`, invisible to the transport's redelivery guard) and the daemon
  queue would run each as its own conversation.
- **the per-seat pending cap** — one `inspect queue` read per cold create counts the PENDING
  rows homed at this seat (`args.workdir`); at five or more the send is refused locally with a
  one-line notice. It **fails open**: a queue read that does not answer never refuses the owner.

The follow-up leg is unaffected either way: it rides `send-message`, which the door does not key.

## The reply leg (D110) — `reply-leg.js`

The outbound production driver that closes Behavior #3. On every FORWARDED turn the
bridge arms a per-conversation PENDING-REPLY state; a single driver loop (default
~3 s) then, over the `inspect` read surface only:

1. **captures** the turn's `execId` from `inspect ticker` → `recent_ticks[].actions[]`
   spawn rows matching the conversation's queue id (a conversation sees one exec per
   turn — every not-yet-delivered spawn is a turn to deliver);
2. **waits for turn-end** by polling `inspect status {execId}` until `live === false`
   — NEVER on `status === 'done'` (the daemon's crash sweep mislabels clean detached
   successes `failed`, so the live flag is the only trustworthy signal);
3. **extracts** the reply from `inspect logs {execId}`, paging the bounded surface
   to the log's END (`nextOffset`/`eof`), then applies the reply contract below; a
   log read to eof with NO text at all → a fixed fallback (`⚠ agent run ended
   without a parseable reply`), the raw log is NEVER posted;
4. **delivers** via `deliverToOwner` (markAsk false — plain agent output, D105 note;
   ask-detection is out of scope for v1), marking the exec delivered ONLY on a
   confirmed delivery, so it is never posted twice — and so a TRANSIENT logs/
   transport/Slack failure never burns the reply: the exec is retried next pass,
   bounded per exec; at the attempt cap it is retired undelivered with a warn AND a
   fixed give-up notice to the owner (D111 part 2 — honest non-delivery, never a
   silent success or a fallback posted over a blip).

### The reply contract — bridge-owned, one shape for every harness

Owner ruling 2026-08-10 (`chat-bridge-feedback-and-reply-contract.md`, decisions 5–7).
Extraction used to know exactly ONE log shape, claude's `--output-format stream-json`,
so every non-claude master profile — opencode `run`, kimi `--quiet`, codex `--json` —
produced a log with no `result` line and every reply reached Slack as the bare
fallback (observed live 2026-08-10 on `opencode-glm-5-2`). Adapting the bridge to each
harness's output is the losing end of that: the set grows, each addition guesses where
a harness hides its answer, and none of it makes the reply better formed.

**The contract inverts it.** The agent states where its reply is, and what lies between
the two sentinel lines is Slack mrkdwn delivered VERBATIM:

```
<<<SLACK-REPLY>>>
*the reply, in Slack mrkdwn*
<<<END-SLACK-REPLY>>>
```

LAST complete pair wins, so an echoed prompt or a corrected first attempt is harmless.
The instruction side reaches every master sitting through its seat descriptor — the
`slack-message-format` reference in the `master` mirror component — never through
prompt injection (`r-bare-prompt-admits-one-correlation-id`: the bridge may prefix the
owner's words with the chat-thread line and nothing else).

| Step | What happens |
|---|---|
| **normalize** | log → the text the agent wrote, the ONE per-harness step the contract cannot remove. claude → the last `{type:'result', result}` line; codex `--json` → the last `{type:'item.completed', item:{type:'agent_message', text}}` event (measured on codex-cli 0.144.5); everything else → the raw log text with ANSI escapes stripped (opencode colours its output even into a file). The harness comes from `inspect status`.profile — a field on the response the driver **already** fetches, so no inspect surface is widened. The two structured arms never fall through to the text arm: a claude/codex log with no message event holds JSON, and posting JSON is what D110 step 4 forbids. |
| **check** | fence present, and its content free of the markdown-isms `mrkdwn.js` exists to catch — pipe tables, `**bold**`, `#` headings, `[text](url)` — linted by `lintMrkdwn`, which lives in that module so the converter and the check can never drift, and which honours the same carve-outs (a `**` inside a code fence or an inline code span is data). A lint hit IS non-conformance. |
| **revive** | non-conformance → ONE corrective turn on the SAME chain, carrying feedback that names each failure and quotes its offending line, plus the correct shape. It rides the forward path's own follow-up leg flagged `corrective: true` — a `send-message` note on the chain, never a second enqueue path — which never consumes a pending `ask` and never posts a decline notice (the owner sent nothing to decline). Bounded at **2 per owner turn**, and the budget sits on the CONVERSATION, not the exec: a revive turn's own bad output spends the same allowance, so the loop terminates whatever the agent does. |
| **deliver** | conformant → the fenced content, byte-identical, with **no** `toMrkdwn` pass (running one would reintroduce the parsing the contract removes). Past the bound, or when the chain cannot be re-dispatched → best-effort: the extracted text through `toMrkdwn`, clamped, behind `⚠ unformatted reply — `. The bare fallback is reached ONLY by a log holding no text at all. |

The reply leg's `pending` watch state is **deliberately not persisted**, even when
`state_file` is set: every field in it is time-bound (a 10-minute spawn window, execs
awaiting an imminent turn-end), so restoring it after arbitrary downtime would restore
*stale* windows. Nothing is lost — a follow-up on a restored conversation re-arms the
leg through the normal `arm()` path, with fresh windows.
A pending conversation whose spawn never appears within a bounded window, or whose
status polling errors persistently, is disarmed with a warn (no crash, no unbounded
retry, no unbounded state growth).

Thread ↔ turn-chain mapping (`thread-map.js`) keys the chain by its chain-stable
thread id `exec-<first exec_id>` (D24 Q3a). The bridge navigates
`job-id → exec-id → chain-thread id` via the gateway `inspect` intent (D69) — it
never conflates id spaces and never forwards a follow-up with an unresolved thread.
The `exec-id → chain-thread` step has **two settled resolutions** (D111): the
authoritative `live_sessions[].thread` when the chain's session is currently live,
else the chain-stable **convention** `exec-<first exec_id>` derived from the KNOWN
first exec-id when the session is not live — the turn-boundary reality, since short
v1 turns end between the owner's messages (a running chain has no live session
between turns). Deriving by that fixed convention is a resolution, not a guess;
`sessionExecId` is **first-wins immutable** so the derived id always names the
chain's real thread. Only when NO first exec-id can be established at all
(`exec-id-unknown` — nothing dispatched, or the spawn aged out of the window) is
resolution honestly deferred. The follow-up then FALLS BACK to a fresh
session-create (the stale mapping is dropped) rather than declining: a dead
mapping must not wedge the channel. Other unresolved reasons (`inspect-failed`)
still decline.

### Honest owner notices (D111 part 2)

The bridge never drops an owner-visible reply path in **silence** on a MAPPED
conversation. When a follow-up cannot reach the running work because the chain
is unresolved with `exec-id-unknown`, the forward path falls back to a fresh
session-create rather than declining — the owner's message must produce a sitting.
When the gateway refused the enqueue, or resolution failed for a transient reason
(`inspect-failed`), the forward path posts a
fixed decline notice (`⚠ couldn't route your reply to the running work — please try
again shortly`) via `deliverToOwner`. The same mechanics carry the goal-channel
no-seat notice above. When the reply leg retires an exec undelivered
at its attempt cap, it posts a fixed give-up notice (`⚠ the agent finished but its
reply couldn't be delivered`). When the door suppresses a session-create because the
seat is busy, it posts a fixed seat-busy notice (`⚠ that work is busy with the previous
message — yours is queued behind it and will be delivered as soon as that finishes`) — the
one notice whose fix is nobody's act but the clock's, which is why it names no human act at
all.

**Three more, all from the reply leg's existing poll (P3), one-shot per turn:** a **stall**
notice when `inspect status` reports `stalled` while the exec still lives (`⚠ the agent has
gone silent — nothing is lost; your message is held and it will be restarted if it does not
wake`); a **recovery** notice when that exec then ends `killed` (`⚠ that run was stopped after
going silent — your queued message will be delivered to a fresh run`) — and a killed hang's
partial log is **never** run through the reply extractor, because a half-written hang is not an
answer; and a **slow** notice once a turn passes `RBTV_CHAT_SLOW_NOTICE_S` (default 300) — `⏳
still working on your message — N minutes so far`. The 30 s latency WARN stays log-only.

Notices carry NO internals, are **best-effort** (a
failed post is logged and dropped, never retried into a loop), and are posted ONLY
for mapped conversations — never on an allowlist/pairing refusal (unpaired users get
nothing, by security posture).

## Bus ferry (`bus-ferry.js`) — coordination bus → the owner

Run agents raise things a human must answer on the team-kit **coordination bus**
(`<goal>/runs/<run>/coordination/messages.md`), and a bus row sat unread until somebody opened
the file — the channel-master's Slack sittings are **one-turn headless sessions**, so nothing
pushed one anywhere. The ferry is that push, and only that push.

### The addressing rule (owner ruling `d-agents-address-owner-not-master`, 2026-08-09)

The closed rule every agent is taught, verbatim:

> - **initiate → `owner`**
> - **answer → the asker** (master included)
> - **else → the seat, by name**

**This ferry carries exactly one of those: `to: owner`.** That token is a NEW RESERVED bus
address; the ferry matches it comma/space-tolerantly (`owner`, `owner, leader`, `leader owner`),
and a token that merely CONTAINS the word (`goal-owner`) is a seat name and does not match.

⚠ **`to: master` is NOT a ferry address, and that is the point of the ruling.** A master-addressed
row from an agent is legal only as an ANSWER to something master sent it, so it is bus traffic
between seats end to end: it takes the ordinary cursor-advance path here, exactly like a row
addressed to any other seat, and reaches chat through no leg at all.

**What this DELETED.** The `roleHeldLive` / `seatDeclaresRole` roster machinery is gone —
`workers.md` liveness reads, `relays:` descriptor reads, holder-name matching, the stand-down
branch, and the `master` role token itself. It existed to answer *"is anybody home to read this
`master` row"*, and nobody asks that anymore: an agent-initiated row is addressed to the OWNER,
and whether it reaches him is the two gates' question, not a roster's. It also existed because the
role word and the holder's seat name had drifted apart within two hours of a rename (rows #5585 /
#5606 / #5616, 2026-08-07) — `owner` cannot drift, because it is a **reserved name no seat may
carry**: `resolveGoalSeat` and the gate-1 reader both refuse it (`owner-is-reserved`), so there is
no holder to name and no roster to consult.

**Legacy rows.** Existing `to: master` escalations sitting on a bus park like any master row — no
regression against the ratified autonomous default, which already parked everything owner-bound.

**Scope is one way, deliberately: bus → Slack only.** Slack → bus stays the sittings'
job. The ferry adds no gateway capability, no store handle, no listener and never writes
to the bus; it reads workspace files and posts outbound through the transport.

### Where a row goes — one address, three outcomes

| The row | Where it goes |
|---|---|
| `to:` does **not** contain `owner`, and it names no chat thread | **nowhere** — not this ferry's business. The cursor advances because the ferry never had a claim on it; the bus delivers it to seats. |
| `to: owner`, **gates shut** | **PARKS on the bus.** Nothing posted anywhere — not the goal channel, not the owner's DM — and nothing minted. Logged naming the gate (§ *The two gates on agent-initiated contact*). |
| `to: owner`, gates open, sender declares **`fallback: park`** | **PARKS on the bus**, exactly as a gated row does and logged `gate: fallback-park` — the seat declared that its questions wait there (§ *The seat's fallback arm*). |
| `to: owner`, **gates open** | **the sending agent's own thread in the goal channel**, its header marked with the sender's fallback arm when it declared one (§ *The seat's fallback arm*). (§ *Thread per agent*). A goal with **no channel** no longer falls back anywhere: a map miss re-asks Slack, and if the channel genuinely does not exist the row is **held and retried**, with one content-free notice to the owner naming the goal and the seat at the third failed pass (owner ruling 2026-08-12). |

A row carrying a `[chat-thread:]` token **the bridge knows** is none of the three: it is an ANSWER
into a thread the owner wrote in, so it is read **before** the gates and travels with both of them
shut. A token the bridge does **not** know is ignored, and the row takes whichever of the three rows
above its `to:` field earns (S-13 — see *The return leg*).

**A bare owner-addressed row mints NOTHING (owner ruling 2026-08-12).** The DM leg used to key
the conversation on its own post's `ts` and mint a channel-master sitting with the row as its
prompt, so the owner read an agent's handling instead of triaging the raw row. It also meant the
channel master ANSWERED questions an agent had addressed to the human — measured on
`meeting-digest` at 02:13 UTC, where the plan-interviewer's `to: owner` ask reached the DM and was
answered by the master. `routeBusRowToMaster` now posts and stops on that arm; it still records the
post's reply address, so the thread stays part of the known set the return leg verifies against.
The mint that remains is the one for a row **naming** a thread the owner already engaged.

| Config key | Meaning |
|------------|---------|
| `bus_ferry` | boolean, **default `false`**. Opt-in. |
| `bus_ferry_dm_user` | Slack user id to DM. Defaults to the **first `allowlist` entry**. |
| `workspace_root` | **required** when `bus_ferry` is on — it is what gets enumerated. Enabled without it, the ferry logs at `error` and stays disabled. |

**What triggers a pass — inotify AND the poll, both** (`live-session-design.md` §2). `fs.watch` on
the goals root and on every goal's `coordination/` dir fires the pass ~200 ms after an append
(`watchDebounceMs`); the ~15 s timer stays as the **safety net** and is not decoration — inotify
queues overflow, a dir created between passes is unwatched until the next one arms it, and network
filesystems degrade silently. Every watch failure (ENOSPC on the per-user watch limit, ENOENT on
goal teardown, a later `error` event) closes that watcher, warns **once**, and leaves the dir to the
poll: late, never lost. The watch only **triggers** — the pass still stats, size-checks and reads
the file **at rest**, so `coord.py`'s multi-write append can never be posted half-read.

**How it runs.** On each pass (an `unref`'d, re-entrancy-guarded timer plus the watch above; a
watch event arriving mid-pass re-arms rather than dropping)
it enumerates `<workspace_root>/.rbtv/goals/*/runs.csv` rows with `state=open`,
reads each run's `messages.md`, and routes every new row whose `to:` field contains the
token `owner` (comma/space tolerant; `goal-owner` does **not** match) — to that agent's thread,
or held and retried when the goal has no channel. The DM channel is resolved once at start via `conversations.open`
(`slack-socket-mode.js` `openDm`); **failure fails closed** — loud log, ferry disabled,
rest of the bridge untouched.

**Message shape** (mrkdwn, phone-first):

```
*bus → you* — <goal>/<run> · from <sender> · <type> · #<msg-id>
<body>
```

Bodies over ~3000 chars are cut at a **line boundary** and end
`… (truncated — full text: <workspace-relative path> #<msg-id>)`.

### The cursor-at-tail rule (the part that matters)

| Rule | Behaviour |
|------|-----------|
| **First sight of a run** | The cursor is set **at the current tail** and **nothing is ferried**. A live run's log holds thousands of rows (5.9 MB / 4817 on the run this was built against) — ferrying the backlog would dump a run's whole history into the owner's phone. Only rows appended **after** the ferry first sees the run are ferried. |
| **…unless the ferry watched the run be BORN** (7.546) | A run enumerated `open` while its `messages.md` does **not exist yet** has no history to protect, so its cursor seeds at **0** and its first rows DO travel — on the very pass that first reads them, not a later one. A newly scaffolded goal rosters only the planning DAG, so that first row is the one escalation with nobody in the room to read it; the tail rule cost everything and protected nothing there. The marker is **per-process and deliberately NOT persisted**, which leaves two distinct cases outside the exception. (a) A goal born while the bridge was DOWN, its birth never observed: the log already exists on return, the backlog is history by this rule, and persistence would buy nothing — there was no observation to persist. (b) A birth a pass DID observe, followed by a **restart before the run's first row**: that row IS swallowed, and persisting the marker WOULD have delivered it (measured: state carried across the restart `{"cursors":{}}`, delivered 0, cursor 1, against 1 delivered with no restart). Case (b) is a **known, ruled gap** — the persistence was dropped with the case named, not on a claim that it buys nothing. The durable record for both is the goal's `doubts.md` park — tier 1 of the escalation ladder in the starter-set `conduct.md`. |
| **Persistence** | Per-run last-ferried msg-id, written through the existing `state_file` persister as an **additive `busFerry` block**. `version` stays `1` — the shape is extended, never restructured, so a version-1 loader reads the file unchanged. A restart therefore does not re-arm first sight. |
| **Mark-after-delivery** | A row advances the cursor only on a **confirmed** `delivered: true`. A failed post is retried next pass, bounded (~20 attempts), then **skipped with a loud warn and the cursor advances** — one undeliverable row never wedges the ferry behind it. Rows are processed in id order, so a later row cannot jump a failing one. |
| **Torn writes** | `messages.md` is appended by live agents. A trailing row is only complete when the file ends with a newline; an incomplete one is left for the next pass, never posted half-read. Malformed headers are skipped, warned **once** per run, `debug` thereafter. |

## Files

| File | Role |
|------|------|
| `index.js` | process entry + `buildBridge()` composition |
| `chat-bridge.js` | wires transport + allowlist + thread-map + forward-path + reply-leg; inbound + outbound; owns the reply addresses and the `(goal, agent)` → thread map |
| `forward-path.js` | the D104/D105 forward contract (session-create / follow-up / reply type), plus the ONE `record-bus-answer` gateway call that puts the owner's reply back on the asking seat's bus (§ The answer goes back onto the bus). The ACT is daemon-side (`engine/bus-answer.js`) — this subtree may hold no spawn |
| `reply-leg.js` | the D110 outbound driver: worker turn finishes → fetch its answer via `inspect` → apply the bridge-owned reply contract (per-harness normalize · fence · lint · bounded corrective revive) → `deliverToOwner` into the Slack thread |
| `mrkdwn.js` | markdown→mrkdwn normalization (the best-effort safety net) AND `lintMrkdwn`, the reply contract's conformance check — one module, because both need the same answer to "what is a markdown-ism, and where is it data" |
| `bus-ferry.js` | the bus ferry: coordination-bus rows addressed `to: owner` → through the two gates on agent-initiated contact → the sending agent's own thread in the goal channel (held and retried when that channel is missing — never downgraded to the DM); everything else, `to: master` included, is not its business. One way; cursor-at-tail, persisted |
| `slack-socket-mode.js` | Slack Socket Mode transport (outbound WS + chat.postMessage) |
| `allowlist.js` | chat-user allowlist + DM pairing (admission control) |
| `thread-map.js` | chat-thread ↔ turn-chain map + two-tier chain-thread resolution (live_sessions, else the `exec-<first exec_id>` convention derivation; first-wins immutable exec-id) |
| `live-sessions.js` | the WARM leg's caller: decides whether a turn is a warm candidate, makes ONE `live-feed` gateway call, hands the reply back. The manager itself is daemon-side (`server/spawn/live-sessions.js`) — see § The warm path |
| `gateway-forwarder.js` | outbound HTTP client to the gateway (self-contained; no sibling import). `forward(intent, payload, { timeoutMs })` — the per-call override exists for `live-feed`, the one intent that holds a request open for an agent turn |
| `config.js` | config + secret resolution (secrets from env only) |
| `probes/` | the spec's Test Plan probes (see below) |
| `outbox.js` | durable Slack outbox [C-17]: record first as `pending-delivery`, flip `delivered` only on Slack ack; local query surface (spec-owner-io §7) |

Relocatable subtree (ignite/CLAUDE.md rule 4): the runtime source imports NO sibling
module (`server/`, `gateway/`, `cli/`) — it reaches the daemon only over the gateway
HTTP interface. `probes/` is test harness and MAY reach siblings.

## Configuration (secrets from the environment only — D27)

| Env var | Meaning |
|---------|---------|
| `IGNITE_GATEWAY_ADDR` | daemon gateway address (host[:port]) |
| `IGNITE_BRIDGE_TOKEN` | **secret** — this bridge's `kind: bridge` sender token |
| `SLACK_APP_TOKEN` | **secret** — Socket Mode app-level token (`xapp-…`) |
| `SLACK_BOT_TOKEN` | **secret** — bot token for `chat.postMessage` (`xoxb-…`) |
| `SLACK_API_BASE` | Slack Web API base override (tests point it at a mock) |
| `IGNITE_CHAT_BRIDGE_CONFIG` | path to the non-secret JSON config (allowlist, job/profile names) |

Non-secret JSON config shape: `{ gateway_addr, session_job_id,
send_message_job_id, workdir, workspace_root, channel_prefix,
state_file, bus_ferry, bus_ferry_dm_user, live_sessions,
allowlist: [chat-user-ids] }`. (`session_profile`, `master_profile`, `goal_profile` and
`master_effort` are DELETED — 2026-08-11/12, launch-cast unification — never read; the seat's own
cast decides harness/model now.)

`workspace_root` is the workspace whose `.rbtv/goals/` holds the goal runs — it is what
a goal-channel session's workdir is resolved from (below). Leaving it unset does not
affect DM or mention traffic; goal traffic then refuses loudly instead of launching
somewhere arbitrary.

### Conversation state across restarts — `state_file` (owner ruling 2026-08-06)

The bridge runs as a systemd unit with `Restart=on-failure`, so restarts happen
unattended. Set `state_file` to an **absolute** path and the conversation tables survive one:
the **thread map** (`queueId` / `sessionExecId` / `chainThread` / `pendingAsk`), the
**reply-address map** (conversation → `{ channel, threadTs }`), the ferry's per-run
**cursors**, and the **agent threads** (`<goalId>#<agent>` → `{ threadTs }`). The last two are
**additive keys** — `version` stays `1`, so a version-1 loader that knows neither reads the file
exactly as before.

| Property | Behaviour |
|----------|-----------|
| **Unset (default)** | No reads, no writes, no file. Byte-identical to the pre-ruling in-memory behaviour. Persistence is strictly **opt-in**. |
| **Write** | On **every** mutation of either table, including deletes (`closeGoal` drops a goal's reply address, and the file reflects it). Write-per-mutation, no debounce — chat volume is tiny. |
| **Atomicity** | Temp file in the same directory + `rename` over the target, mode `0600`. A reader never sees a half-written file; a crash mid-write leaves the previous good state. |
| **Load** | At `start()`, **before the transport listens** — no inbound message can race the rebuild. |
| **Corrupt file** | Renamed aside to `<state_file>.corrupt-<ms>` with an `error` log, and the bridge starts **empty**. Never a crash loop: unparseable state must not take the chat surface down, and the aside copy keeps the evidence. |
| **Write failure** | Logged at `error`, swallowed. The bridge degrades to its old amnesia rather than dropping the conversation. |
| **Not persisted** | The reply leg's `pending` watch state (see above) — its windows would be stale. |

Relative paths are **refused at config resolution**, not silently resolved: a relative
path resolves against the daemon's cwd, so the same config would read a different file
depending on how the unit was started — a silent amnesia, which is the bug this key
exists to fix.

The file is non-secret (conversation ids and Slack channel/thread ids, never a token),
so it belongs in the machine's own state root, e.g.
`{state_root}/chat-bridge-state.json`.

## Validation (STAGED — ADX-33(2) / D106)

The spec's fidelity floor (a REAL Slack round-trip) needs an owner-provisioned Slack
app that does not exist at build time. Build-time validation exercises the spec's
probes against a **local stand-in**: a mock Socket-Mode server + a **throwaway**
in-process daemon (heart store + internal API + gateway) on an ephemeral loopback
port — never the live daemon, never port 7431. The real-transport round-trip
(Test Plan rows 1/2/4/6 at the real floor) runs at **p7-checkpoint** with the owner.

Run the probes through the counting runner — `node ../../deploy/probe-suite.js --dir
bridges/chat/probes` (or `--only probe-chat-<name>` for one). Never invoke a probe file
directly: that rewrites its capture with pure noise and the run is neither counted nor
graded for staleness (`ignite/CLAUDE.md` § probes). Evidence → `probe-chat-<name>.out`.

| Probe | Test Plan | Proves |
|-------|-----------|--------|
| `probe-chat-enqueue` | #1 | allowlisted user's message → validated job reaches gateway → queue (full mock-WS round-trip); redelivery legs (D108(C)): same event re-pushed under a new envelope is dropped — SAME-channel follow-up on a live chain (no double `send-message`), the `(channel, event_ts)` fallback key when `client_msg_id` is absent, and a negative control proving two DISTINCT messages both still enqueue |
| `probe-chat-allowlist` | #2 | non-allowlisted user refused, nothing enqueued; admitted user does enqueue |
| `probe-chat-outbound` | #3 | starting the bridge adds NO new inbound listener (`ss -tlnp` delta) |
| `probe-chat-outbound-msg` | #4 | owner output delivered outbound via `chat.postMessage` |
| `probe-chat-reply-leg` | #4 | the D110 driver, armed through the REAL inbound wiring (Slack event → forward path → arm): spawn captured from `recent_ticks` → `live:false` → the reply extracted (multi-page logs paged to the end) → posted to the conversation's channel+thread, text-EQUAL to the fenced content; no exec delivered twice; a follow-up turn (new exec, same queue) delivers a second reply; a transient logs failure or refused post is retried (nothing burned), persistent failure retires the exec undelivered at a bounded attempt cap AND posts the honest give-up notice (D111 part 2). **Reply contract**: the same fenced reply arrives from all three log shapes (claude stream-json, codex `--json` events, plain text with opencode's ANSI escapes) via `inspect status`.profile; a conformant reply is delivered BYTE-IDENTICAL with a body `toMrkdwn` would demonstrably have altered; a lint hit posts nothing and enqueues a corrective `note` on the same chain naming each ism and quoting its line; a missing fence spends the second revive and the third non-conformant turn is delivered best-effort behind the warning marker (never the bare fallback), while a genuinely textless log still delivers the bare fallback and is never revived; **P2/P3 (leg u)** — a stalled-but-live exec posts the stall notice EXACTLY ONCE however many passes see it; that exec then ending `killed` posts ONE recovery notice, delivers **not a byte** of its half-written log, and RESETS the spawn window rather than tombstoning; a turn past the slow threshold posts ONE hourglass notice carrying the minutes; and a conversation whose row is STILL in the daemon's `inspect queue` does **not** disarm — once the row is gone the dead-air notice fires exactly as before |
| `probe-chat-mention-route` | — | the 2026-08-06 rulings: a mention in an unmapped channel routes as master with a thread-scoped conversation and an in-thread reply address; an unmentioned (or someone-else-mentioning) message there stays refused with nothing enqueued; `mpim` stays refused even when mentioned; a failed `auth.test` DISABLES the mention route while the DM path keeps working; a goal session-create is homed at the open run's `goal-master` seat; each of the four unresolvable-seat states (no open run · run open but unseated · goal absent · `workspace_root` unset) enqueues nothing and posts the fixed no-seat notice; every session-create prompt equals the user text verbatim; the runtime source carries no instance path and no `MASTER_CHARTER`; and the **mint-vs-continue** rule — a mention mints, an un-mentioned reply in a KNOWN thread continues as a follow-up `send-message`, while an unknown thread, a top-level message, and the same `thread_ts` in another channel each stay refused with nothing enqueued |
| `probe-chat-state-persistence` | — | the 2026-08-06 `state_file` ruling, modelled as a real restart (a SECOND `buildBridge` on the same file, fresh maps, the same still-running daemon): a mutation writes the file (0600, directory created) carrying BOTH tables; the restarted bridge starts empty, restores at `start()`, and an **un-mentioned reply in the restored thread CONTINUES** — the owner's amnesia repro, now green — with the restored reply address still addressing the original channel+thread; the CONTROL run with no `state_file` refuses that same reply; with no `state_file` **nothing is written anywhere** (asserted against an empty cwd); a corrupt file is renamed aside `.corrupt-<ts>`, logged at `error`, starts EMPTY without crashing, and still mints and re-persists afterwards; `closeGoal`'s reply-address DELETE is persisted; a relative `state_file` is refused at config resolution while unset stays `null` |
| `probe-chat-bus-ferry` | — | the bus ferry: a 50-row `to: owner` backlog is NOT ferried at first sight and the cursor lands at the tail; a row appended after IS ferried once with the exact header; the token grammar — `to: leader` ignored, `to: owner, leader` ferried, `goal-owner` NOT; **the ruling's red/green pair** — a `to: master` row is NEVER ferried while a `to: owner` row from the SAME seat on the SAME pass is; an over-long body truncates at a line boundary naming the workspace-relative source; a torn trailing row is left unposted until it completes; malformed headers warn once then drop to debug without stopping the rows around them; a failed post is retried without advancing the cursor and without letting the next row jump it, then is skipped loudly at the attempt cap leaving the ferry UNWEDGED; the cursor survives a real restart (second `buildBridge`, same `state_file` → no double-post, no re-flood) with the state file EXTENDED not restructured; a `state=closed` run is never enumerated; the fail-closed set — off by default, on-without-`workspace_root`, and a failed `conversations.open` — each disables the ferry loudly while the bridge starts fine; **the DM leg seats nobody** (owner ruling 2026-08-12, replacing the arm that asserted the opposite) — with the agent-thread leg unwired the row is posted to the DM verbatim and NO session-create rides it; what a channel-less goal does now is `probe-chat-agent-thread` arm 5's claim, and every arm here runs with `routeToAgentThread: null` because these arms measure parsing, truncation, retry and cursors rather than the routing surface; **the 7.546 birth route** — a run enumerated open with NO `messages.md` yet takes no cursor on that pass and its FIRST row is then ferried on the very pass that reads it, while a run first seen WITH a 40-row backlog — same workspace, same passes — keeps the tail rule and ferries none of it. ⚠ **Two arms were DELETED with the machinery they tested** (`d-agents-address-owner-not-master`): the roster stand-down / holder-by-name legs, and the live-descriptor arm that required a standing correspondent to declare `relays: master` — the ferry now reads neither a roster nor `relays:`. The live tree is still MEASURED in their place and filed as a SKIP (goals declaring `execution-mode: interactive`), for the reviewer to turn into an assertion once the F-115 mints land — asserting it today would red the suite for work deliberately not done. **The watch and the `[deliver:]` disposition** (arm 12) run with the poll an hour away, so every delivery in it is inotify-driven or it does not happen: the watcher count after `start()` and after `stop()`, a row ferried in well under a second with no `tick()` call, `post` posting into its own thread with nothing minted, `wake` posting AND minting with that row as the prompt, and the CONTROL that a row with NO token still mints and posts nothing — the ruling the disposition is an opt-in *to* |
| `probe-chat-dedup-refusal` | — | **REWRITTEN AT P2** for the daemon-queue world (the arms asserting that a new inbound message DROPS a held one encoded the loss the queue deletes, and the throwaway-daemon arms proved `deduped`/`because` field names the bridge no longer keys on). Now, all against a stub door: every session-create carries `on_seat_busy: 'queue'` and still names no execution; a **byte-identical** re-send at the same seat home is dropped with the duplicate notice and **never enqueued** (a COUNT — 2 is the duplicate agent chain), while two DIFFERENT messages are BOTH enqueued; the per-seat cap refuses a sixth message at a backed-up seat with a notice carrying no internals, with three controls — four waiting still passes, a backlog at ANOTHER seat does not refuse this one, and an unreadable `inspect queue` **fails open**; a follow-up on a live chain bypasses both guards; a pre-queue **state file** carrying the retired `pendingRetries` key loads, has its held text NAMED in a warn rather than swallowed, and never writes the key back. RED ARM: a scratch copy of `chat-bridge.js` with the guard block cut out enqueues the duplicate twice and enqueues past the cap, the mutation asserted to have altered the source first. *(Historic: **two threads at ONE seat** — the coverage no other probe here had (each drives one conversation, and the whole defect lives in the second). Against the REAL door (throwaway daemon, thread A's row FIRED so a live turn genuinely holds the seat): a suppressed session-create writes **no** thread mapping, is never reported as a queued success, posts the seat-busy notice to *that* thread, and carries the undelivered text on `undeliveredText` — proven on BOTH shared-seat derivations, `config.workdir` (master) and `resolveGoalSeat` (goal). The review's control is re-measured (thread A's text in the store, thread B's nowhere); the first thread's follow-up leg still enqueues, which is also the **tolerance sweep** — `send-message` is the only other bridge-side reader of an enqueue response and the door never keys it. RED ARM: a scratch copy of `forward-path.js` with the guard cut out — the pre-fix code exactly — maps the new thread to the held queue id and posts nothing, and the mutation is asserted to have altered the source first. NO-REGRESSION ARM (§2 review): the guard fires on `deduped` being TRUE, never on the field being present — a bare `{jobId}` (the shape the pre-door daemon running today returns) and an explicit `deduped:false` each map normally and post no notice, so the fix cannot break the deployment it ships onto.)* |
| `probe-chat-agent-thread` | — | **thread per agent** (ratified 2026-08-09), gates first: the gate readers in isolation — an **absent** `execution-mode` file, an unreadable one and a junk word are ONE answer (`autonomous`) while only `interactive` (trimmed, case-insensitive) is the other; `yes`/`true` declare a seat, `no` / a missing line / a missing descriptor do not; a traversing `from:` token resolves nothing. Then the ferry: a row PARKS on either gate with **nothing posted to the goal channel AND nothing to the owner DM**, nothing minted, cursor advanced, the log naming the gate — each park **paired with the same row travelling once its own gate opens**, so "not posted" can never pass for "this ferry ferries nothing". The thread: the first row **anchors** top-level with the agent-led header and is recorded on the `(goal, agent)` key (no run id), mints **no** sitting and posts **nothing** to the DM; the same agent's next row replies on the **same** `threadTs` while a different agent anchors its own; a goal with **no channel** posts NOTHING anywhere and mints nothing — the row is held, the cursor does not advance, the miss is proven to have ASKED SLACK (the `conversations.list` call is counted, not inferred), the owner gets ONE content-free notice naming the goal and the seat at the third failed pass and no second one at the fourth, and a channel created out of band afterwards — exactly as the daemon's throwaway CLI creates it — is re-resolved on the next pass so the held row lands in the agent's thread there (owner ruling 2026-08-12). Inbound: a reply in an anchored thread routes `kind: 'agent'` while an unknown thread and an unthreaded message stay `kind: 'goal'` on the channel, and the same `thread_ts` in an unmapped channel is nothing; the owner's reply mints a session-create **homed at the asking seat** on the goal profile with the prompt equal to his bare text behind the one correlation line, and a second reply is a **follow-up** on that chain (never a second session); an agent whose seat has LEFT gets nothing enqueued and the fixed no-agent-seat notice **in its own thread**. The return leg posts a goal-channel-token row into that thread **verbatim with nothing minted**, and does so **with both gates shut** (owner-initiated legs are never gated), with a CONTROL proving a DM-thread token still mints. State: the map is persisted **additively** (version 1, `threads` + `replyAddr` + `busFerry` all still present), a fresh bridge holds none before `start()`, restores at `start()`, and routes a pre-restart thread's reply to the AGENT. the ruling's own pair — a `to: master` row reaches NOTHING with the gates OPEN *and* with them shut, where the discriminator is the DISPOSITION (an owner row PARKS and is logged; a master row was never this ferry's business and is not), plus `owner` refused as a seat name by BOTH readers and gate 1 scoped to the frontmatter so a body line cannot open it. **S-13 token verification** — the fabricated threads are asserted UNKNOWN first, then a forged goal-channel token posts nothing into the invented thread, mints nothing and the row PARKS on the gates (one `does not know` log, cursor advanced), a forged DM-shaped token mints no sitting, and the SAME token shape naming a KNOWN thread routes verbatim into it; the RESTART leg is accepted only because `start()` restored the conversation from the state file, with a no-`state_file` CONTROL that declines instead. **EVERY CLAIM HAS A MUTATION ARM RUN BY THE PROBE ITSELF** (arm 11, the `probe-chat-dedup-refusal` scratch-copy pattern scaled to the tree): each copies `bridges/chat` beside itself, strips the copied `probe-*` scripts so suite discovery can never see it, applies ONE asserted single-string mutation, and requires the copy to go red on exactly the named claims — gates removed · owner token is `master` · every address ferried · gate 1 unscoped · `owner` un-reserved in each of the two readers · absent mode read as interactive · agent-thread leg not tried · header not agent-led · `routeOf` agent branch removed · return-leg guard removed · `agentThreads` not persisted · agent homed at `goal-master` · S-13 token not verified · `knowsThread` vouching for everything · `knowsThread` vouching for nothing (which reds the restart leg while an anchored agent thread stays known — the known set's own asymmetry) · the map miss trusting the in-memory map instead of re-asking Slack · the no-channel DM fallback put back. A CONTROL copy runs UNMUTATED and must be green **at the same check count as the parent run**, so a red can never be the copy being broken and a silently shrunken arm count is caught; a mutant child is marked by env so it runs the checks and not the harness (else mutants spawn mutants forever) |
| `probe-chat-live-session` | — | **the warm path against a REAL harness** (`live-session-design.md` §1/§4): a real `claude-haiku` profile, a real seat folder under a real `.rbtv/goals/` tree, the real seat cage, real `systemd-run --pipe` carriage — nothing about the launch is stubbed. Eligibility: the admission PAIRED against each refusal, including a SYNTHETIC non-claude profile that DOES carry a `resume:` template so the harness gate is the only thing left to refuse it (every shipped non-claude profile is refused one gate earlier, which would make the check vacuous), and gate 1 scoped to the frontmatter with a body-line control. The turns: a cold chain is SEEDED first, then the warm session answers a question only that chain can answer (continuity across the cold→warm boundary, not merely "a reply arrived"), and a SECOND message written **mid-turn** — asserted mid-turn by the registry's own `in-turn` state — is answered too, in order, by the SAME process. Accounting: exactly ONE `sessions.csv` row per live PROCESS (never one per turn) and the stream-json transcript teed to `logs/<session-id>.log` carrying BOTH results. The reaper closes the session and the unit is asserted GONE. A session `SIGKILL`ed **mid-turn** resolves its fed turn `unanswered: true` — never a hang, never a silent drop — and clears the registry so the next message takes the cold path. The wire: `live-feed` through the REAL gateway + internal API on a BRIDGE token, where an unwarm conversation is a SOFT `{fed:false}` (never an error, because the caller's response is the routine one) while a forged `session_ref` field and an empty prompt are both refused. **MUTATION ARM**: the feed's stdin write is cut out of an asserted-altered copy and the SAME feed arm 2 answers goes RED — a probe that cannot fail proves nothing |
| `probe-chat-warm-post` | #4 | **the warm turn's POSTING path** — the half `probe-chat-live-session` does not reach (it proves the harness answers; this proves what the owner then reads). Both owner-reported defects of 2026-08-10, each with the mutation that reds it: a fenced warm reply posts **only** the fenced content — asserted on the WHOLE posted string, so a post that also carries the prose half and the sentinels cannot pass — while an UNFENCED reply is posted byte-for-byte (the extraction may only ever remove a duplication that is there); and the ⏳ read-receipt is stamped on the owner's OWN message **before** the feed and taken off when the answer lands, in that order, on the WARM turn as well as the cold one, marked exactly ONCE when a refused feed falls through to the cold path. Plus the negative claim only the bridge can carry: a warm-answered turn is posted ONCE and enqueues NOTHING — the cold leg did not also run |
| `probe-chat-boundary` | #5 | bridge source holds no spawn/queue handle, opens no server, imports no sibling |
| `probe-chat-followup` | #6 | follow-up forwards as `send-message` on the chain thread (NEVER send-to-session), reply type `answer`/`note`; queue_id → exec_id learned from ticker dispatch actions; **exec KNOWN but NOT live → derives `exec-<firstExecId>`** (D111 convention fallback); **first-exec immutability** (a later exec-id bind is ignored); **exec-id-unknown FALLS BACK to session-create** (chat-launch enqueued, stale mapping dropped, no decline notice) while an allowlist-refused user gets nothing |
| `probe-chat-outbox` | C-17 | mocked Slack `ok:false` / network error keeps the record `pending-delivery` with `last_error` + incremented `attempt_count`; retry does not mint a second record; ack flips `delivered` with `slack_ts`/`delivered_at`; §7.2 filters + newest-first + get-by-id; no strike |

## Flagged seams (task-7.5 / p7-checkpoint — surfaced, not resolved here)

- **`send-message` catalogue row** must exist in the live jobs catalogue for the
  follow-up leg (dry-run validates `type` ∈ CMP-8 types + non-empty `thread`).
  Seeding it is a server/deployment concern **outside this task's write surface**;
  the probes seed it into the throwaway store.
- **`queue_id → exec_id` correlation — initial-learning gap CLOSED** (p7-2 review
  finding; closed by D108(B)). `inspect ticker` → `live_sessions[]` now exposes
  `queue_id` per row (the store's `jobs_log.queue_id` link, populated by
  `fireQueueRow`), and `thread-map.js` resolves in this tier order (see its
  RESOLUTION ORDER header):
  1. **queue_id → live session direct match** (reason `inspect-ticker-queue`) —
     TIME-INDEPENDENT: a live session resolves at ANY age, no ticks window. The
     hit also binds the first exec-id (first-wins preserved — it IS the first
     binding).
  2. **`recent_ticks[].actions[]` navigation** — `{ action: 'spawn', execId,
     queueId }` per fired row; still WINDOWED (last 10 ticks, ~100 s at default
     cadence). It remains the tier that covers a spawn whose session already
     ENDED (absent from `live_sessions[]`) but is still inside the window.
  3. **exec_id → thread via `live_sessions[]`** (reason `inspect-ticker`), else
     the `exec-<first exec_id>` convention derivation (reason
     `derived-convention`, D111).
   The formerly-flagged initial-learning window now bites ONLY the narrow case of a
   session that ENDED before the first follow-up AND whose spawn aged out of the
   ticks window — then resolution is honestly deferred (`exec-id-unknown`), never
   guessed, and the follow-up falls back to a fresh session-create. Once the first
   exec-id IS learned, it is remembered first-wins and EVERY later turn resolves
   by derivation regardless of liveness.
- **Registry convergence.** The settled model is channel → (1:1) goal thread →
  per-slot sub-thread → session; the v1 chat-thread ↔ turn-chain map is the v1
  stand-in until goals/threads-store land.
- **Registry `sender`** resolves to no registry record though load-bearing across
  the gateway/bridge design (task-7.5 reconciliation row).

## Reply grammar — `reply-grammar.js`

Pure first-token parser for owner replies (`spec-owner-io` §4). Input is raw
reply text; output is `{ok, outcome, comments, family, findings, goal}` or a
parse failure carrying the verbatim §4.5 NACK (`nackKind` `ask` vs `mechanical`).
Does not post, touch Slack, or read or write any store. Callers wire it later.
Probe: `probes/probe-chat-reply-grammar.js`.

## The approval thread — `approval-thread.js`

The §3 approval FIRST MESSAGE and the §4.2 post-parse dispatch, for asks whose
record carries `kind = approval` (`spec-owner-io`; law `DESIGN-BASELINE.md` v2
§Planning approval rows).

`composeApprovalBody({goalName, digest, commitId, canvasLink})` builds the body
that goes under `ask-thread.js`'s §3 lead line: the **GOAL NAME** and the
**IRREVERSIBLE EFFECT** (`a reply of approve starts execution.`) each as their
own bold lead line before any other body, then the phone-sized digest, the bound
`commit_id` [T5-R5], the canvas link (or `none — artifacts on disk`), and the six
accepted tokens. It REFUSES to compose without a goal name or a commit id — an
unbound approval approves whatever the tree holds later.

`createApprovalDispatch({materialize, closeGoal, pauseGoal, relaunchDraftVerify,
postBack})` decides what an outcome DOES. The fork is on the ask's `kind`, never
on the token [D-5-ruling, CF-7]: `approve` in a `kind=approval` thread is the D12
trigger; the same word anywhere else is an outcome delivered to the seat.
`reject-and-close` / `close` close the planning goal; `reject-and-pause` pauses it
and keeps the thread as the ONLY door out [T3-R22]; `reject-and-retry` and
`retry with:` relaunch draft + verify with the comments as the findings list
[T3-R21]. Inside a `reject-and-pause`d thread only `retry with:` / `approve` /
`close` are exits; anything else the grammar recognizes changes nothing and is
answered in-thread.

Every effect is a PORT, because this process may not spawn `planning/path_b.py`,
close a goal or write a lane (`probes/probe-chat-boundary.js`). A port that
refuses — including a port that is not wired — reports back into the SAME approval
thread [C-16] and leaves the thread usable. Probe:
`probes/probe-chat-approval.js`.

### D12's port is the fourteenth intent — `start-execution.js`

`materialize` is NO LONGER injectable. The owner ruled the fourteenth gateway
intent on 2026-08-24 (option (b), `redesign-implementation/decisions.md`):
`approve` reaches the daemon as `start-execution`, and a daemon-side executor
(`server/heart/start-execution.js`) runs the supervised Path-B birth
(`planning/path_b.py#run_path_b` through `wrapper.py#supervised_materialize`).

`createExecutionStart({forwarder})` is that sender. It forwards
`{goal, thread, commit}` and nothing else — the plan is the approve-package the
planning goal already carries, so a caller cannot approve one plan and start
another, and the owner's comments after `approve` do not travel (they are a
retry's findings list [T3-R21], and the payload schema is closed at the gateway,
so sending them would be a refusal rather than an ignored key). The call carries a
per-call timeout override, `live-feed`'s precedent: a birth is scaffold + mint
under the materialize lock, not a store write.

The daemon trusts the bridge for NOTHING about the approval: a `kind=approval`
thread is a fact of this process's own map. The executor instead checks the record
the daemon itself wrote — the thread is an ask this daemon opened (`ask_id` IS the
thread [T5-R7]), it is bound to the goal named, and an authorized owner reply
RELEASED it (`authorized_reply_at` is stamped only by the §2.4 release door) —
plus that the commit named is the package's `bound_commit` [T5-R5]. Anything else
is a refusal, and a supervised-materialize failure comes back carrying the
wrapper's six-field record so the [C-16] post-back can show it. `chat-bridge.js`
REFUSES an injected `materialize` at construction: a stub `{ok: true}` there would
tell the owner an execution started when nothing did. Probe:
`server/internal-api/probes/probe-start-execution.js`.

## The mechanical door — `pause-resume.js`

`pause {goal}` / `resume {goal}` (`spec-owner-io` §4.2/§4.4/§4.5) plus the
resume-semantics table (`spec-recovery` §4 [C-14]). A first token of `pause` or
`resume` is handled by the daemon/bot and BYPASSES the goal master; every other
owner-initiated message still goes to the master doors [T5-R14]. In a goal
channel a bare verb targets that channel's goal; in the system channel or a DM
the slug is required, and a slug matching zero or several live goals gets the
verbatim §4.5 mechanical NACK with nothing changed.

`pause` is the inverse of the paused-goal row only: `running` → `paused`. It does
not disarm a lane and does not open an ask. `resume` applies EVERY matching row:
the goal flips `paused` → `running`; a counter-exhausted lane is re-armed through
the `named-external-input` named event (the relaunch budget is not spent); a
`blocked-on-human` lane and a gate-cap lane are REFUSED and pointed at their asks.
Neither verb ever flips an ask off `open`.

The ending-store API arrives INJECTED (`state-store/index.js#bind(db)` plus a
`listSeats(goal)` enumerator) — this module holds no store handle and opens no
database. Probe: `probes/probe-chat-pause-resume.js`.

### ⚠ The mechanical door is BUILT AND PROVEN, NOT REACHABLE IN PRODUCTION YET

The approval door's D12 effect IS reachable now: the fourteenth intent
`start-execution` was minted on 2026-08-24 (option (b)) and `chat-bridge.js`
builds its sender from the forwarder it already holds.

The mechanical door is not. `index.js#main()` still wires no `endingStore`,
because the SAME ruling deliberately did not mint the pause-word intent — pause
stays store-side until the execution-lane reconcile gate converges onto the
goal-state row. The approval door's other three ports (`closeGoal`, `pauseGoal`,
`relaunchDraftVerify`) are also still unwired. All of them degrade LOUDLY — an
unwired approval port posts the [C-16] failure into the approval thread, a missing
ending store logs a warn and applies nothing — never silently.

## The glance surfaces — `system-digest.js` and `status-line.js`

`spec-owner-io.md` §5 and §6 [T5-R13, C-12, T4-R5, D-6-ruling]. Two surfaces, one
purpose: the owner can see everything that is waiting on them from a phone,
without a per-ask re-ping and without a per-goal digest.

### `system-digest.js` — the changed-only SYSTEM digest (§5)

ONE digest, posted only in the system channel, checked every two hours at the ten
America/Sao_Paulo slots `00:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00,
20:00, 22:00`. A check at any other time returns `{ ran: false }` and does
nothing — 00:00–06:00 carries no check apart from the 24:00 slot, which IS 00:00.
The local hour is resolved through `Intl` at `America/Sao_Paulo`, never through a
fixed offset.

When a post happens the order is fixed: open ❓ asks (`display_suffix`, seat,
one-liner, age, link), then the open alarm CONDITIONS, then links.

**Changed** is the snapshot of `(open ask ids + each ask's one_liner + open
condition signatures)` — nothing else. Age is rendered but deliberately excluded:
it ticks every minute and would make every slot post. Unchanged → the checker
posts NOTHING.

The comparison is against the last **DELIVERED** payload, not the last attempt. A
digest the outbox minted but Slack never acked leaves the baseline where it was,
so the next slot re-offers the same change instead of the owner losing it. The
baseline is persisted (`statePath`, `{version, snapshot, delivered_at}`, tmp+rename),
so a restart between two slots does not re-post an unchanged digest.

The open conditions arrive from an INJECTED `readOpenConditions` port — the
alarm-signature registry's published READ interface, which impl-alarms owns
(`ignite/observation/`, §9). ⚠ **That interface is not landed yet.** With no
reader wired the digest reads an EMPTY set, renders `• none open` under
`Open conditions`, and does not crash. No emitter and no stand-in registry lives
here: this module only READS.

### `status-line.js` — the bot status line (§6)

Exact format, `N waiting · oldest Xh · M blocked`; zero case
`0 waiting · oldest 0h · 0 blocked`. `N` counts ask-records in state `open` across
all goals; `Xh` is whole (floored) hours since the oldest one's `opened_at`, `0`
when `N` is 0; `M` is lanes stamped `incomplete: blocked-on-human` plus goals in
stored state `paused`.

It **never posts** — no outbox, no channel, no transport reaches this module. It
writes the bot's Slack status text through an injected `setStatusText` port, and
only on the seven §6 triggers: `ask-minted`, `ask-answered`, `ask-closed`,
`blocked-on-human-stamp`, `blocked-on-human-clear`, `pause-succeeded`,
`resume-succeeded`. Every other event is refused and the text is left alone — a
status line that redraws on every event is a poll loop against Slack. With no
status port wired it computes the line, logs a warn, and writes nothing.

Probe for both: `probes/probe-chat-glance.js` (mocked Slack, mocked clock, no
live post). Both surfaces are BUILT AND PROVEN but not reachable in production
yet — `index.js#main()` wires neither the 2-hourly slot driver, the ask/condition
readers, nor the Slack status port.

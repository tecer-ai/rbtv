'use strict';

// The chat bridge — composition of the four parts (chat-bridge-spec.md):
//   • transport      — Slack Socket Mode (outbound WS; slack-socket-mode.js)
//   • allowlist      — chat-user admission + DM pairing (allowlist.js)
//   • threadMap      — chat-thread ↔ turn-chain mapping (thread-map.js)
//   • goalChannels   — goal ↔ Slack channel, 1:1 (goal-channel-map.js, task 7.58)
//   • forwardPath    — the D104/D105 forward contract to the gateway (forward-path.js)
//
// The bridge is an ORDINARY authenticated SENDER on the narrow gateway API — never
// a privileged path. It holds NO spawn/queue capability (chat-bridge-spec.md
// Behavior #5): its only outbound dependencies are the transport and the gateway
// forwarder, both injected here.

const fs = require('node:fs');
const path = require('node:path');

const { createForwardPath } = require('./forward-path');
const { createLiveLeg } = require('./live-sessions');
const { createReplyLeg, checkReplyContract, bestEffortText } = require('./reply-leg');
const { createBusFerry, seatIsHumanInteractive } = require('./bus-ferry');
const { createAskThreads } = require('./ask-thread');
const { createAskRecord } = require('./ask-store');
const { createOutbox, outboxStorePath } = require('./outbox');

const STATE_VERSION = 1;

function createChatBridge({ config, forwarder, transport, allowlist, threadMap, goalChannels = null, logger = null, replyLegOptions = {}, busFerryOptions = {} }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  const outbox = createOutbox({
    storePath: (config && config.workspaceRoot) ? outboxStorePath(config.workspaceRoot) : null,
    send: ({ channel, threadTs, text }) => transport.sendToOwner({ channel, threadTs, text }),
  });

  function postSlack({ kind, channel, threadTs, text, goal_id = null, ask_id = null }) {
    return outbox.post({
      kind,
      channel_id: channel,
      thread_ts: threadTs == null ? null : threadTs,
      payload: text,
      goal_id,
      ask_id,
    });
  }

  // deliver is the bridge's own outbound delivery (deliverToOwner, hoisted below) —
  // injected so the forward path can post an honest decline notice (D111 part 2) on
  // a MAPPED conversation whose follow-up cannot reach the running work, never silence.
  // ONE sender for the ask record, shared with the forward path so both acts on a thread — the
  // open and the reap — travel the same intent through the same forwarder. Two constructions would
  // be two places to get the intent's name and its refusal handling right.
  const askRecord = createAskRecord({ forwarder, logger });

  // ── THE ASK DOOR (`ask-thread.js`, spec-owner-io §2/§3) ────────────────────────────────────
  //
  // ONE map and one module. `askThreads` is the bridge's answer to the only question the release
  // rule asks that Slack cannot: is THIS thread an ask's thread, and whose? The id IS the Slack
  // `thread_ts` [D-8], so the key is the ordinary conversation address `<channel>:<ts>` and the
  // value is the ask's owner — nothing about the ask's STATE lives here. State is `open_asks`,
  // daemon-side, and a second copy of it in this process would be a second source of one fact.
  //
  // ⚑ PERSISTED ADDITIVELY, `STATE_VERSION` unchanged — the ferry cursors' and the agent threads'
  // discipline exactly. Losing it would leave every open ask thread unattributed: the owner's
  // answer would be handled as ordinary goal traffic and the ask would never be released, which
  // is the pre-redesign silence rebuilt by accident.
  const askThreads = new Map(); // `<channel>:<threadTs>` -> { goalId, seat, askId, label }

  const askDoor = createAskThreads({
    outbox,
    askRecord,
    updateMessage: (args) => transport.updateMessage(args),
    // INSTANCE CONFIG, never repo content, and an empty list authorizes NOBODY (ask-thread.js).
    authorizedSenders: (config && config.allowlist) || [],
    // A GETTER: the identity is resolved from Slack at start(), after this construction.
    botUserId: () => botUserId,
    // [T2-R14] the send-time refusal, at the door the ruling names. The predicate is the
    // BRIDGE's because the bridge owns the goal folder; `seatIsHumanInteractive` is the same
    // reader the descriptor's own linter agrees with (bus-ferry.js).
    seatIsInteractive: (goalId, seatName) => {
      const root = (config && config.workspaceRoot) || null;
      if (!root || !goalId || !seatName) return false;
      return seatIsHumanInteractive(path.join(root, '.rbtv', 'goals', String(goalId)), String(seatName));
    },
    workspaceRoot: (config && config.workspaceRoot) || null,
    logger,
  });

  // POST AN ASK AS A REAL ❓ THREAD. The wrapper is what the ask module deliberately does not
  // hold: the goal→channel resolution (`resolveChannel`, never `channelForGoal` — see
  // routeToAgentThread's header for why a map miss is not proof of absence) and the bookkeeping
  // that makes the owner's reply findable again.
  async function postOwnerAsk({ goalId, seatName, label = 'work-content', body, marker = 'ask' }) {
    const resolved = await goalChannelFor(goalId);
    const channel = resolved.channelId;
    if (!channel) return { posted: false, reason: resolved.reason };
    const fn = marker === 'note' ? askDoor.postNote : askDoor.postAsk;
    const out = await fn({ goalId, channelId: channel, seatName, label, body });
    if (!out || out.posted !== true) return out || { posted: false, reason: 'post-failed' };
    const threadTs = out.askId || out.threadTs;
    const key = `${channel}:${threadTs}`;
    // A 💭 note mints NO record [§2.1] and therefore nothing to release — it is not entered in
    // the map. Its thread still gets a reply address so the owner can be answered in it.
    if (out.askId) askThreads.set(key, { goalId: String(goalId), seat: String(seatName), askId: String(threadTs), label });
    replyAddr.set(key, { channel, threadTs });
    saveState();
    return out;
  }

  // THE RELEASE, called from the inbound path below and nowhere else.
  async function releaseAskFor(entry, chatMsg) {
    const channelGoal = goalChannels ? goalChannels.goalForChannel(chatMsg._channel) : null;
    const out = await askDoor.release({
      goalId: entry.goalId,
      channelId: chatMsg._channel,
      seatName: entry.seat,
      askId: entry.askId,
      threadTs: chatMsg._threadTs,
      senderId: chatMsg.chatUserId,
      text: chatMsg.text,
      channelGoal,
    });
    // The map entry is dropped only on an ACTUAL release. Every other outcome — wrong thread,
    // unauthorized, unparsed, a mechanical verb — leaves the ask `open`, and an ask still open
    // whose thread the bridge has forgotten is an ask that can never be answered.
    if (out && out.released === true) { askThreads.delete(`${chatMsg._channel}:${chatMsg._threadTs}`); saveState(); }
    return out;
  }

  const forwardPath = createForwardPath({
    forwarder, threadMap, allowlist, config, logger, askStore: askRecord,
    deliver: (args) => deliverToOwner(args),
    listAgentThreads: (goalId) => {
      const prefix = `${goalId}#`;
      const out = [];
      for (const [k, v] of agentThreads) {
        if (k.startsWith(prefix) && v && v.threadTs) out.push({ agent: k.slice(prefix.length), threadTs: String(v.threadTs) });
      }
      return out;
    },
  });

  // The WARM leg (live-session-design.md §1/§4). Tried BEFORE the forward path on every owner
  // turn; a refusal is the normal case and falls straight through to the cold path below. It
  // reaches the daemon only through the same injected forwarder, on one new intent — no new
  // capability, no process of its own (see live-sessions.js for why the manager is daemon-side).
  const liveLeg = createLiveLeg({ forwarder, threadMap, config, logger });

  // The outbound reply leg (Behavior #3, D110): drives worker answer → Slack thread.
  // It reaches the daemon ONLY via the injected forwarder's inspect surface, and
  // delivers via this bridge's own deliverToOwner — no new capability.
  // `redispatch` is the reply contract's revive turn (owner ruling 2026-08-10): the SAME
  // follow-up leg an owner reply takes — a send-message job on the conversation's chain — flagged
  // corrective so it consumes no pending ask and posts no decline notice into the owner's thread.
  // No parallel enqueue path exists for it, by construction.
  const replyLeg = createReplyLeg({
    threadMap,
    forwarder,
    deliver: (args) => deliverToOwner(args),
    redispatch: (args) => forwardPath.forwardFollowUp({ ...args, corrective: true }),
    logger,
    ...replyLegOptions,
  });

  // The bus ferry (bus-ferry.js): coordination bus → owner DM, opt-in via `bus_ferry`.
  // Constructed always, STARTED only when enabled — so `busFerry.toJSON()` has a stable
  // shape in the state file whether or not the ferry ran. It holds no forwarder and no
  // thread map: it reads workspace files and posts through the transport, nothing else.
  //
  // ⚑ WHERE AN OWNER-ADDRESSED ROW GOES WHEN IT HAS NO GOAL CHANNEL (owner ruling 2026-08-07,
  // retargeted to `to: owner` by `d-agents-address-owner-not-master`). The ferry decides WHETHER a
  // row travels (the two gates); this decides WHERE. Both halves of the owner's two complaints are
  // one seam:
  //   (1) the row reached the OWNER as work instead of reaching an AGENT — so the post is
  //       followed by a session-create at the channel-master seat, and the owner reads the
  //       agent's handling rather than triaging the raw row;
  //   (2) the owner's reply in that thread opened a sitting that could not see the row that
  //       started it — because the ferry's post was never a conversation. `sendToOwner`
  //       already returns the post's `ts` and the ferry discarded it; minting
  //       `<dmChannel>:<ts>` here makes the owner's reply a FOLLOW-UP on this sitting
  //       (routeOf's DM branch keys on exactly that id), so the row is in its history.
  // The prompt is the SAME TEXT that was posted — no second rendering, and no behavioural
  // text authored by the transport (the 2026-08-06 bare-prompt ruling is untouched: this is
  // the relayed row itself, provenance header included, not a charter).
  // ⚑ THE RETURN LEG (owner ruling 2026-08-07, doubts-queue discussion at the goal-master
  // door). A row that NAMES its own chat thread needs no post at all: the post above exists
  // ONLY to manufacture a `ts` to key a sitting on, and a named thread already is one. So
  // this branch mints the sitting DIRECTLY and posts NOTHING — which is the whole point of
  // the ruling: the owner asked that the answer reach the CHANNEL-MASTER, not that a raw bus
  // row be pushed at him. He sees the agent's message in the thread he asked in, and never
  // the plumbing.
  //
  // ⚑ IT FALLS THROUGH, NEVER DROPS. If the mint fails for any reason the row continues to
  // the posting path below and the owner gets it raw — degraded, but never lost. That is the
  // same "the row IS delivered either way" discipline the post-first path already keeps.
  // ⚑ `deliver` — WHAT THE NAMED THREAD SHOULD DO WITH THE ROW (live-session-design.md §3;
  // vocabulary and the why in `bus-ferry.js` § `deliverToken`). `null` is the ruled default and
  // takes the mint path below unchanged; `post` posts the row into the thread and mints nothing;
  // `wake` does both. It is honoured ONLY on the DM/master branch — the goal-channel branch above
  // already posts verbatim and already refuses to mint (a `kind: 'master'` sitting on a goal's
  // surface is the widening `CHAT_THREAD_RE` warns against), so `wake` degrades to `post` there
  // and says so rather than acquiring a mint the ratified branch does not have.
  async function routeBusRowToMaster({ channel, text, chatThread = null, deliver = null }) {
    if (chatThread) {
      const cut = chatThread.lastIndexOf(':');
      const tokenChannel = cut > 0 ? chatThread.slice(0, cut) : null;
      const tokenThreadTs = cut > 0 ? chatThread.slice(cut + 1) : null;
      // ⚑ A GOAL CHANNEL'S THREAD TAKES THE ROW VERBATIM AND MINTS NOTHING (ratified
      // 2026-08-09). The mint below exists to give the CHANNEL MASTER a sitting that can handle
      // a row the owner would otherwise have to triage. A thread inside a GOAL channel is
      // already an agent's conversation with the owner: the row is that agent's own answer, and
      // minting a `kind: 'master'` sitting for it would home a channel-master at the master
      // workdir on a goal's surface — precisely the widening the CHAT_THREAD_RE note in
      // bus-ferry.js warns against. So this posts and returns; nobody new is seated.
      //
      // ⚑ A FAILED POST RETURNS THE FAILURE — it does NOT fall through to the DM leg below.
      // Falling through would mint exactly the wrong seat on a transient rate limit. The ferry
      // owns this failure: it retries the row next pass, bounded, then gives up loudly with the
      // cursor advanced, which is the same discipline every other undeliverable row gets.
      const tokenGoalId = tokenChannel && goalChannels ? goalChannels.goalForChannel(tokenChannel) : null;
      if (tokenGoalId) {
        const intoThread = await postSlack({ kind: 'notification', channel: tokenChannel, threadTs: tokenThreadTs, text, goal_id: tokenGoalId });
        if (intoThread && intoThread.delivered) {
          log('info', 'bus row posted verbatim into its goal-channel thread — no sitting minted', { chatThreadId: chatThread, goalId: tokenGoalId, deliver });
          if (deliver === 'wake') log('warn', 'the row asked to WAKE a sitting on a goal channel — posted only; a master sitting is never minted on a goal surface', { chatThreadId: chatThread, goalId: tokenGoalId });
          return intoThread;
        }
        log('warn', 'bus row could NOT be posted into its goal-channel thread — the ferry retries it (no master sitting minted on a goal channel)', { chatThreadId: chatThread, goalId: tokenGoalId, error: intoThread && intoThread.error });
        return intoThread || { delivered: false, reason: 'post-failed' };
      }
      // ── `post` / `wake`: THE ROW IS DELIVERED AS WRITTEN, NO AGENT IN THE MIDDLE (design §3) ──
      //
      // The settled outcome of an async job is a fact the tool already composed. Posting it is the
      // whole nudge (`i-no-completion-nudge`); minting a sitting to paraphrase it costs the full
      // spawn pipeline for no added information. `wake` adds the sitting ON TOP, for a row that
      // carries something to act on — never instead of the post, so the owner is told either way.
      //
      // ⚑ THE POST COMES FIRST AND ITS FAILURE IS THE FERRY'S. A failed post returns the failure
      // and nothing is minted: the ferry retries the row next pass, bounded, exactly as it does
      // for the goal-channel branch above. Minting on a failed post would run the follow-up work
      // for a message the owner never saw.
      if (deliver === 'post' || deliver === 'wake') {
        const intoThread = await postSlack({ kind: 'notification', channel: tokenChannel, threadTs: tokenThreadTs, text });
        if (!intoThread || !intoThread.delivered) {
          log('warn', 'bus row could NOT be posted into its named thread — the ferry retries it (nothing minted)', { chatThreadId: chatThread, deliver, error: intoThread && intoThread.error });
          return intoThread || { delivered: false, reason: 'post-failed' };
        }
        if (deliver === 'wake') {
          const woke = await forwardPath.forwardSessionCreate({
            chatThreadId: chatThread, text, route: { kind: 'master', goalId: null },
          });
          if (woke && woke.forwarded) {
            replyLeg.arm(chatThread);
            log('info', 'bus row posted into its named thread AND woke a sitting on it', { chatThreadId: chatThread, queueId: woke.queueId });
          } else {
            // The owner HAS the row — that is why the post came first. The wake failing is a
            // degraded outcome, not a lost one, and it is said out loud rather than retried: the
            // ferry's retry would re-post the row.
            log('warn', 'bus row posted into its named thread but no sitting was woken', { chatThreadId: chatThread, reason: (woke && (woke.reason || woke.error)) || 'unknown' });
          }
        } else {
          log('info', 'bus row posted verbatim into its named thread — no sitting minted (deliver: post)', { chatThreadId: chatThread });
        }
        saveState();
        return intoThread;
      }
      // ⚑ THE REPLY ADDRESS IS NO LONGER DERIVED FROM THE TOKEN'S TEXT (S-13 ruling
      // `d-s13-chat-thread-token-verified`). A `derive it from `<channel>:<ts>`' branch used to
      // stand here for a thread this process had never seen. It is DELETED, not disabled: the
      // token is now verified against the bridge's own state before the ferry hands it over
      // (`knowsThread` below), so an unseen thread never reaches this line, and the restart case
      // it was written for is covered by the state file restoring both tables at `start()` —
      // persistence, not trust. What remains reachable is the narrow torn-state case (a thread the
      // thread map knows with no reply address beside it); that gets `deliverToOwner`'s honest
      // `no-reply-address` warn rather than a fabricated address, which is the same posture as
      // every other cannot-tell here.
      const back = await forwardPath.forwardSessionCreate({
        chatThreadId: chatThread, text, route: { kind: 'master', goalId: null },
      });
      if (back && back.forwarded) {
        replyLeg.arm(chatThread);
        saveState();
        log('info', 'bus row minted a channel-master sitting on its own named thread — nothing posted', { chatThreadId: chatThread, queueId: back.queueId });
        return { delivered: true, ts: null };
      }
      log('warn', 'bus row named a chat thread but no sitting was minted — falling back to the owner DM post', { chatThreadId: chatThread, reason: (back && (back.reason || back.error)) || 'unknown' });
    }
    // ⚑ THE BARE ARM POSTS AND STOPS — IT MINTS NOTHING (owner ruling 2026-08-12). A row with no
    // `[chat-thread:]` token was never part of a conversation the owner opened, and minting a
    // channel-master sitting with the row's own text as its prompt handed the master a question
    // that was ADDRESSED TO THE HUMAN — measured on `meeting-digest` 02:13 UTC, where the
    // plan-interviewer's `to: owner` ask reached the DM and the channel master answered it.
    // The mint that stands is the one above: a row NAMING a thread the owner already engaged.
    //
    // ⚑ THE REPLY ADDRESS IS STILL RECORDED, and only the mint is gone. The address is how the
    // bridge KNOWS this thread (`knowsThread`, S-13) and how it would post into it — dropping it
    // with the mint would quietly narrow the return leg's known set, which is a second change
    // nobody ruled.
    const posted = await postSlack({ kind: 'notification', channel, threadTs: null, text });
    if (posted && posted.delivered && posted.ts) {
      replyAddr.set(`${channel}:${posted.ts}`, { channel, threadTs: posted.ts });
      saveState();
    }
    return posted;
  }

  // ── IS THIS A THREAD WE KNOW? (S-13 owner ruling `d-s13-chat-thread-token-verified`) ─────
  //
  // A `[chat-thread:]` token is TEXT IN A BUS ROW — written by an agent, parsed by a regex, and
  // until this ruling obeyed on sight. Obeying it made the token an instruction to post into any
  // Slack thread the sender cared to name, and to mint a channel-master sitting on it. So the
  // bridge now vouches for the token or it does not travel: a token counts only when it names a
  // thread THIS BRIDGE ALREADY KNOWS.
  //
  // ⚑ THE KNOWN SET IS THE BRIDGE'S OWN LIVE STATE, all three tables:
  //   • `replyAddr`   — every conversation the bridge has an address for,
  //   • `threadMap`   — every conversation with a turn chain,
  //   • `agentThreads`— every thread an agent anchored in a goal channel (the return-leg guard's
  //     own subject, so that leg keeps working BY CONSTRUCTION rather than by exemption).
  // ⚑ THE THIRD CLAUSE IS COMPLIANCE, NOT COVERAGE — stated plainly because the difference is
  // invisible from the code: `routeToAgentThread` writes a `replyAddr` entry beside every thread it
  // anchors, so the first clause already answers for every agent thread that exists today, and no
  // mutation of this clause alone can turn a probe red. It stays because the RULING names all three
  // tables, and because it is what keeps the return-leg guard known BY CONSTRUCTION rather than by
  // a write in another function that a future prune could drop.
  //
  // ⚑ THE RESTART CASE IS COVERED BY PERSISTENCE, NOT BY TRUST. `state_file` restores
  // `replyAddr`, the thread map and the agent threads BEFORE the transport listens, so a token
  // naming a pre-restart conversation is known. Where the file is not configured the bridge
  // forgets — and then it says so by declining, which is the honest answer, not a reason to
  // believe the row instead.
  //
  // ⚑ UNKNOWN = AS IF THE ROW CARRIED NO TOKEN (ruled). Not dropped, not posted to the invented
  // thread, nothing minted: the row falls back to the ordinary path in the ferry — `to: owner` →
  // the two gates → the agent's thread or a PARK; anything else → cursor advance. That is why the
  // check lives at the FERRY's hand-over (an injected predicate, the same shape as
  // `routeToMaster`) and not only here: only there is the normal path still available.
  function knowsThread(chatThread) {
    const id = String(chatThread || '');
    if (!id) return false;
    if (replyAddr.has(id) || threadMap.has(id)) return true;
    const cut = id.lastIndexOf(':');
    if (cut <= 0) return false;
    const goalId = goalChannels ? goalChannels.goalForChannel(id.slice(0, cut)) : null;
    return Boolean(goalId && agentForThread(goalId, id.slice(cut + 1)));
  }

  // ── THREAD PER AGENT IN A GOAL CHANNEL (ratified 2026-08-09) ─────────────────
  //
  // An agent that needs the owner gets its OWN Slack thread in its goal's channel, and the
  // owner's reply in that thread reaches THAT agent. This map is the whole store: key
  // `<goalId>#<agent>`, value the thread's anchor `ts`.
  //
  // ⚑ THE CHANNEL IS NEVER STORED HERE, deliberately. `goalChannels` re-derives every
  // goal↔channel binding from Slack at each start (name-derivation is a bijection), so a
  // channel id cached beside the thread would be a SECOND answer to "which channel is this
  // goal" — stale the moment a channel is re-adopted, and unfalsifiable from this side. The
  // map holds the one fact only Slack can tell us: WHICH THREAD in that channel is this
  // agent's.
  //
  // ⚑ NO RUN ID IN THE KEY, and that is a load-bearing choice: the goals layout is mid-rewrite
  // elsewhere, and an agent's conversation with the owner is not a property of the run it
  // happened to start in. (goal, agent) is the identity the owner recognizes.
  //
  // ⚑ PERSISTED ADDITIVELY, `STATE_VERSION` unchanged — same discipline as the ferry's
  // cursors: a version-1 loader that knows nothing of agent threads reads the file exactly as
  // before and ignores the key.
  const agentThreads = new Map(); // `<goalId>#<agent>` -> { threadTs }
  const agentKey = (goalId, agent) => `${goalId}#${agent}`;

  function agentThreadFor(goalId, agent) {
    const e = agentThreads.get(agentKey(goalId, agent));
    return e ? e.threadTs : null;
  }

  // The reverse lookup, by ITERATION on purpose: entries are one per (goal, agent) that has
  // actually spoken to the owner — a handful — so a second index would be state to keep
  // consistent in exchange for nothing measurable.
  function agentForThread(goalId, threadTs) {
    const prefix = `${goalId}#`;
    for (const [k, v] of agentThreads) {
      if (k.startsWith(prefix) && v && String(v.threadTs) === String(threadTs)) return k.slice(prefix.length);
    }
    return null;
  }

  // WHERE A GATED AGENT-INITIATED ROW GOES (the ferry's `routeToAgentThread`). First row for a
  // (goal, agent) posts TOP-LEVEL — that post IS the thread anchor, and its first line names the
  // agent (bus-ferry.js `formatMessage` § agentLead). Every later row replies on that anchor.
  //
  // ⚑ NO SITTING IS MINTED HERE. The row is the agent's own message; the agent already exists
  // and is homed at its seat. A sitting is minted only when the OWNER replies — and it is minted
  // AT THAT AGENT'S SEAT (forward-path.js § kind 'agent'), which is what makes the reply reach
  // the asker instead of some relay.
  //
  // ⚑ NO CHANNEL → `no-channel`, never a post somewhere else. The ferry reads that one reason
  // and holds the row for its next pass, so the decision "what does a missing channel cost"
  // lives in one place (there) instead of being taken twice.
  //
  // ⚑ AND `resolveChannel`, NEVER `channelForGoal` (2026-08-12). The in-memory map only knows
  // the channels this process saw; every goal channel is created by a THROWAWAY CLI subprocess
  // the bridge never observes, so a miss here must ask Slack before it means anything. See
  // `goal-channel-map.js` § "a map miss is not proof of absence".
  //
  // ⚑ AND THE REFUSAL REASON IS CARRIED THROUGH UNCHANGED. `no-channel` (the channel does not
  // exist) and `resolve-failed` (Slack did not answer) are different facts and the ferry acts on
  // the difference — collapsing them here would put the distinction the map just made straight
  // back in the bin.
  // ONE resolver for every outbound leg that needs a goal's channel. Two copies of this line
  // would be two places to get `resolveChannel`-not-`channelForGoal` right — and the second copy
  // is exactly where a future edit would quietly put the in-memory map back in charge.
  async function goalChannelFor(goalId) {
    return goalChannels ? await goalChannels.resolveChannel(goalId) : { channelId: null, reason: 'no-channel' };
  }

  async function routeToAgentThread({ goalId, agent, text }) {
    const resolved = await goalChannelFor(goalId);
    const channel = resolved.channelId;
    if (!channel) return { delivered: false, reason: resolved.reason };
    const known = agentThreadFor(goalId, agent);
    const posted = await postSlack({ kind: 'notification', channel, threadTs: known, text, goal_id: goalId });
    if (!posted || !posted.delivered) return posted || { delivered: false, reason: 'post-failed' };
    const threadTs = known || posted.ts;
    if (!threadTs) {
      // Delivered but unthreadable. The row IS in the channel — keep the delivery — and record
      // NOTHING: binding this agent to a missing ts would key a thread the owner cannot reply
      // into, while recording nothing means the next row anchors a real one.
      log('warn', 'agent-thread anchor posted but Slack returned no ts — no thread recorded', { goalId, agent, channel });
      return posted;
    }
    if (!known) {
      agentThreads.set(agentKey(goalId, agent), { threadTs });
      log('info', 'agent opened its own owner thread in the goal channel', { goalId, agent, channel, threadTs });
    }
    // The reply address for this conversation, so `deliverToOwner` can address the thread later
    // (the reply leg posts by conversation id and knows no channel).
    replyAddr.set(`${channel}:${threadTs}`, { channel, threadTs });
    saveState();
    return posted;
  }

    const busFerry = createBusFerry({
    workspaceRoot: (config && config.workspaceRoot) || null,
    transport,
    outbox,
    dmUserId: (config && config.busFerryDmUser) || null,
    logger,
    onMutate: () => saveState(),
    routeToMaster: (args) => routeBusRowToMaster(args),
    routeToAgentThread: (args) => routeToAgentThread(args),
    knowsThread: (t) => knowsThread(t),
    // A `to: owner` row is posted as a REAL ❓ ask thread [D18, T5-R8, spec-owner-io §3] — the
    // park that used to swallow it is gone (bus-ferry.js). Injected, so `busFerryOptions` can
    // still unwire it in a probe measuring the legs beneath.
    postAsk: (args) => postOwnerAsk(args),
    ownerUser: (config && config.ownerUser) || null,
    ...busFerryOptions,
  });

  // THE SURFACE ROUTE (task 7.58 d-channel-per-goal; mention route added by the
  // 2026-08-06 owner ruling). Every inbound message is exactly one of three things,
  // and the difference is decided HERE, before admission or forwarding:
  //
  //   'master' — EITHER a DM to the bot identity (cold-contact MASTER traffic,
  //              explicitly UNCHANGED by the channel-per-goal ruling) OR a message in
  //              an unmapped channel/group that MENTIONS the bot (`<@BOTID>`) or that
  //              lands in a thread ALREADY known to the thread map (a mention MINTS a
  //              conversation, membership CONTINUES it — no re-mention per reply). Both
  //              carry the same conversation shape — the Slack thread
  //              `channel:thread_ts` — so a mention starts a per-thread sitting and a
  //              new thread is a new sitting. NEVER goal traffic: neither surface can
  //              be attributed to a goal.
  //   'goal'   — a message in a MAPPED goal channel. The goal thread maps 1:1 onto
  //              the channel, so the CONVERSATION IS THE CHANNEL — sharding it by
  //              `thread_ts` would split one goal thread into many and break the 1:1
  //              the ruling exists to establish.
  //   'agent'  — a reply inside a thread of a mapped goal channel that THIS BRIDGE anchored
  //              for a named agent (ratified 2026-08-09). The ONE admitted exception to the
  //              rule above, and it does not weaken it: the thread exists only because that
  //              agent opened it, so the conversation is the thread and it is homed at that
  //              agent's seat. An unknown thread in a goal channel is still 'goal'.
  //   null     — an UNMENTIONED message in a channel that maps to no goal, in no
  //              already-known conversation thread. REFUSED,
  //              nothing enqueued: unattributable traffic must never mint work. The
  //              mention is what makes it attributable — without one, the bot sitting
  //              in an ordinary channel would mint work from every passing sentence.
  //
  // `mpim` (group DM) routes as neither: it is not a goal channel and it is not the
  // 1:1 owner DM the master path assumes. Refused, deliberately.
  //
  // ⚑ WHEN `_channelType` IS ABSENT. Slack's `message` events always carry it, so an
  // event without it did not come from the Slack transport — it was injected
  // directly (a probe, or an embedder driving the bridge in-process). Two sub-cases,
  // split so the strict rule lands exactly where the risk is:
  //   • the channel id looks like a Slack CHANNEL (`C…`/`G…`) → treat it as a
  //     channel and apply the strict rule. A real channel event that somehow lost
  //     the field must never fall through to master traffic.
  //   • anything else (a `D…` IM id, or no channel at all) → master, the exact
  //     pre-7.58 semantics. Refusing here would silently kill the master path.
  //
  // ⚑ THE MENTION ROUTE FAILS CLOSED. It is armed only once `botUserId` is known
  // (resolved from the transport at start — see start()). Until then, and forever if
  // resolution failed, an unmapped channel behaves exactly as it did before this
  // ruling: refused. A bridge that cannot say who it is must not guess who was meant.
  const CHANNEL_ID_RE = /^[CG]/;
  let botUserId = null;

  function mentionsBot(chatMsg) {
    return Boolean(botUserId) && typeof chatMsg.text === 'string' && chatMsg.text.includes(`<@${botUserId}>`);
  }

  function routeOf(chatMsg) {
    if (!chatMsg) return null;
    const kind = chatMsg._channelType;
    const channel = chatMsg._channel;
    const looksLikeChannel = kind === 'channel' || kind === 'group'
      || (!kind && typeof channel === 'string' && CHANNEL_ID_RE.test(channel));
    if (kind === 'mpim') return null;
    if (!looksLikeChannel) {
      return { kind: 'master', goalId: null, conversationId: chatMsg.chatThreadId };
    }
    const goalId = goalChannels ? goalChannels.goalForChannel(channel) : null;
    if (!goalId) {
      // Unmapped channel: a mention MINTS a conversation; MEMBERSHIP in one already
      // minted CONTINUES it. Anything else stays refused.
      //
      // The continuation check is `threadMap.has(<the same conversation id the mention
      // route would assign>)` — `channel:thread_ts`. It is self-limiting by
      // construction: a TOP-LEVEL message's conversation id is its own `ts`, always
      // brand new, so it can never be in the map — only replies inside a thread that
      // already IS a sitting continue without a mention. Without this, the owner had to
      // re-mention the bot on every single reply in a thread it had already answered
      // in (owner-observed 2026-08-06).
      //
      // The continuation therefore depends entirely on the thread map still holding
      // the sitting. It SURVIVES A RESTART when `state_file` is configured (see
      // § conversation state below) — the owner hit the amnesia twice on 2026-08-06,
      // which is why the key exists. WITHOUT the key the map is in-memory only and a
      // restart sends un-mentioned replies back to refused until a re-mention re-mints.
      if (mentionsBot(chatMsg) || (threadMap && threadMap.has(chatMsg.chatThreadId))) {
        return { kind: 'master', goalId: null, conversationId: chatMsg.chatThreadId };
      }
      return null;
    }
    // AN AGENT'S OWN THREAD inside a mapped goal channel (ratified 2026-08-09) — 'agent'
    // traffic: the conversation is the Slack thread, and it is homed at THAT AGENT's seat.
    //
    // ⚑ ONLY A THREAD THIS MAP KNOWS resolves. An UNKNOWN thread in a goal channel and every
    // unthreaded message stay `kind: 'goal'` on the channel-as-conversation — the goal-master
    // surface the 1:1 ruling established. That is not a gap being left: sharding a goal channel
    // by `thread_ts` in general is exactly what d-channel-per-goal forbids, and the only
    // exception is a thread THIS bridge anchored for a named agent.
    if (chatMsg._inThread && chatMsg._threadTs) {
      const agent = agentForThread(goalId, chatMsg._threadTs);
      if (agent) return { kind: 'agent', goalId, agent, conversationId: `${channel}:${chatMsg._threadTs}` };
    }
    return { kind: 'goal', goalId, conversationId: String(channel) };
  }

  // Inbound: a chat message → the surface route, then the forward path (admission,
  // then session-create or follow-up). Wired as the transport's onMessage.
  //
  // ⚑ THE ROUTE IS RESOLVED HERE BUT ENFORCED IN THE FORWARD PATH, so ADMISSION
  // STAYS FIRST (chat-bridge-spec.md Behavior #2). Refusing an unroutable surface
  // before admission would be no weaker as security, but it would stop a
  // non-admitted principal from ever reaching the allowlist's pairing queue — and
  // that queue IS the DM-pairing feature (DEC-6). Order matters for a reason that
  // has nothing to do with which refusal is stricter.
  async function onChatMessage(rawMsg) {
    // ── THE ASK DOOR, BEFORE EVERY OTHER LEG (spec-owner-io §2.4) ──────────────────────────────
    //
    // A message inside a thread this bridge opened for an ask is an ANSWER TO THAT ASK and is
    // handled here and NOWHERE ELSE. It does not fall through, and that is the point: an
    // unauthorized reply falling through would mint a sitting on somebody's remark, and an
    // authorized one would be answered twice — once by the release and once by the goal leg.
    //
    // Keyed on `<channel>:<threadTs>` off the RAW event, never on `route.conversationId`: for
    // goal traffic the conversation IS the channel, so the routed id cannot tell one ask thread
    // from another, or from the channel itself.
    //
    // ⚑ EVERY §2.4 REFUSAL IS STILL A HANDLED MESSAGE. Wrong thread cannot happen through this
    // key; unauthorized is silent by ruling [§2.4.2]; unparsed already posted its NACK
    // in-thread [§2.4.3]; a mechanical verb belongs to the pause/resume door. In all four the ask
    // stays `open` — nothing here ever closes one by guessing.
    if (rawMsg && rawMsg._channel && rawMsg._inThread && rawMsg._threadTs) {
      const entry = askThreads.get(`${rawMsg._channel}:${rawMsg._threadTs}`);
      if (entry) {
        const released = await releaseAskFor(entry, rawMsg);
        return { forwarded: false, leg: 'ask-release', route: 'ask', ask: entry.askId, ...released };
      }
    }

    const route = routeOf(rawMsg);
    // The conversation id the whole bridge keys on: the Slack thread for master
    // traffic, the CHANNEL for goal traffic. An unroutable message keeps its raw id
    // — it is refused downstream and never reaches the thread map.
    const chatMsg = { ...rawMsg, chatThreadId: route ? route.conversationId : (rawMsg && rawMsg.chatThreadId), route };

    // Remember the Slack reply address for outbound delivery on this conversation.
    // Goal traffic replies IN-CHANNEL (top level) unless the human posted inside a
    // Slack thread — the goal's surface is the channel, so burying every reply in a
    // thread would hide the goal's own conversation from the owner. Master traffic —
    // DM *and* mention — always carries `_threadTs` (the transport defaults it to the
    // message's own ts), so a mention in a busy channel is answered IN-THREAD and one
    // sitting never bleeds into another's.
    if (route && chatMsg.chatThreadId && chatMsg._channel) {
      const threadTs = route.kind === 'goal'
        ? (chatMsg._inThread ? chatMsg._threadTs : null)
        : chatMsg._threadTs;
      replyAddr.set(chatMsg.chatThreadId, { channel: chatMsg._channel, threadTs });
      saveState();
    }
    // ── THE WARM PATH, tried first and never trusted ────────────────────────────────────────
    //
    // A conversation that already holds a chain AND whose seat is live-capable is answered by a
    // warm process in ~1.5-4s instead of ~12s. EVERY other outcome — not warm, ineligible seat,
    // non-claude harness, gateway down, the session died mid-turn — returns `answered: false`
    // and execution continues into the unchanged forward path below, so this block can only ever
    // ADD a fast answer, never remove a slow one.
    //
    // The workdir comes from the forward path's OWN resolver, so a warm turn runs at the same seat
    // the cold turn would have — and since 7.787 the seat is the ONLY thing that decides what runs.
    // ⚑ `isAdmitted`, NEVER `check` — `check` has a SIDE EFFECT on its refusing branch (it
    // records a pairing request and increments its count, allowlist.js), and the forward path
    // below calls it for real. Asking `check` here too would double-count every refused
    // principal's pairing attempts. The admission question is still asked, and it is still asked
    // BEFORE any warm work: a revoked principal holding an old mapped thread is refused here
    // exactly as it is refused there.
    if (route && chatMsg.chatThreadId && allowlist.isAdmitted(chatMsg.chatUserId)) {
      // ⏳ STAMPED HERE, BEFORE THE ATTEMPT — the warm path is not the instant path the design
      // assumed. Measured on this box 2026-08-10: three warm turns at 13.4s, 18.5s and 25.8s
      // (`warm turn answered`, ms), not the 1.5-4s that made a marker "noise". An accepted
      // message showing nothing for 26 seconds is the exact dead air the marker exists for, and
      // the owner read its absence as the bridge ignoring every follow-up. `deliverToOwner`
      // takes it off when the answer lands, on the warm path and the cold one alike.
      markPending(chatMsg.chatThreadId, chatMsg._channel, chatMsg._msgTs);
      const home = forwardPath.workdirFor(route);
      const warm = await liveLeg.attempt({
        chatThreadId: chatMsg.chatThreadId,
        text: chatMsg.text,
        route,
        workdir: home && home.ok ? home.workdir : null,
      });
      if (warm.answered) {
        // Posted straight into the thread — no reply-leg arming. The leg exists to find an
        // exec and wait for it; a warm turn writes no queue row and no `jobs_log` row
        // (server/spawn/live-sessions.js § what it does not do), so there is no spawn action
        // for the leg to capture and nothing to arm it for.
        //
        // ⚠ ROW PRESENCE ONLY, AND THAT IS A HISTORY QUESTION [T4-R8]. What is read here is
        // whether the turn-audit log HAS a row, never what `status` word it carries — a warm
        // session is not "running" in `jobs_log`, it is absent from it. Its ending, when it has
        // one, is stamped in the ending store by the live-session closer.
        //
        // ⚑ THE FENCE IS EXTRACTED HERE, through the COLD PATH'S OWN extractor. A live
        // session's `result` event carries the WHOLE final turn text, and the reply contract
        // asks the agent to end that turn with its message between two sentinel lines — so a
        // conformant warm reply arrives as the prose AND the fenced copy AND the markers, and
        // posting it raw delivered the owner the same answer twice with `<<<SLACK-REPLY>>>`
        // between the halves (owner-observed 2026-08-10, minutes after df65147). One extractor
        // for both legs, never a second regex: last complete pair wins, sentinels matched as
        // whole lines.
        //
        // ⚑ AND THE SAME CONTRACT VERDICT THE COLD PATH DELIVERS ON (owner ruling 2026-08-11,
        // option b). A conformant reply travels VERBATIM — never through the converter, that is
        // the contract's point. Anything else goes out best-effort: clamped, converted to mrkdwn,
        // behind the marker that attributes the shape to the agent. What the warm arm does NOT do
        // is the cold path's corrective revive — a warm turn has no exec and no queue row to
        // re-dispatch against, so the safety net is the whole remedy here. `verdict.body` is null
        // only when there was no text at all, and then the raw text is still better than nothing.
        const verdict = checkReplyContract(warm.text);
        const text = verdict.ok
          ? verdict.body
          : (verdict.body !== null ? bestEffortText(verdict.body) : warm.text);
        // Non-conformance was invisible here — the turn logged as cleanly handled while the
        // owner saw the ⚠ prefix (observed 2026-08-13, three replies in one thread with not
        // one journal line). The cold leg warns on every revive; the warm leg says so too.
        if (!verdict.ok) log('warn', 'warm reply non-conformant — delivered best-effort behind the unformatted marker', { chatThreadId: chatMsg.chatThreadId, problems: (verdict.problems || []).map((p) => p.issue) });
        // ⚑ THE OWNER ANSWERED: SAY SO ON THE BUS — the THIRD door (task 7.771; owner review
        // 2026-08-11). `forward-path.js#recordBusAnswer` is called, never re-implemented: "the
        // owner answered" is ONE FACT and recording it at one door is what made the first cut of
        // this a single-source-of-truth defect. The guard (`route.kind === 'agent'` only) travels
        // inside that function, so a goal channel or a DM writes nothing here either.
        //
        // ⚑ IT RIDES `warm.answered`, NOT THE SLACK POST, and the two are genuinely different
        // questions. `warm.answered` means the live session CONSUMED the owner's words and produced
        // a turn from them — that IS delivery, and it is already irreversible. Whether the agent's
        // reply then reached Slack is the OTHER direction; a rate-limited post does not un-answer
        // the question the seat already read. So BOTH exits below carry it.
        //
        // ⚑ AND IT RUNS AFTER THE POST, not before. This is the latency path the warm leg exists
        // to win (`live-session-design.md` §4), and the bus write shells to a python process — so
        // ordering it first would spend the owner's own wait on bookkeeping he cannot see.
        const delivered = await deliverToOwner({ chatThreadId: chatMsg.chatThreadId, text, markAsk: false, answersOwnerAsk: verdict.ok === true });
        const busAnswer = await forwardPath.recordBusAnswer({ route, text: chatMsg.text });
        if (delivered && delivered.delivered !== false) {
          const out = { forwarded: true, leg: 'live-session', warm: true, ms: warm.ms, ...(busAnswer ? { busAnswer } : {}) };
          log('info', 'chat message handled on the warm path', { chatThreadId: chatMsg.chatThreadId, ...out });
          return out;
        }
        // The turn HAPPENED and its answer could not be posted. Falling through would re-ask the
        // agent the same question, so this stops here and says so — the same honesty the reply
        // leg's give-up notice carries.
        log('error', 'warm turn answered but its reply could not be posted — NOT re-asking the agent', { chatThreadId: chatMsg.chatThreadId, reason: delivered && (delivered.reason || delivered.error) });
        return { forwarded: true, leg: 'live-session', warm: true, delivered: false, ...(busAnswer ? { busAnswer } : {}) };
      }
    }

    // ⚠ THE TWO PRE-ENQUEUE GUARDS (P2). Both sit HERE, above the forward path, because the
    // daemon queue no longer collapses anything for us: whatever reaches `enqueue-job` becomes a row
    // that WILL run. They apply only to a conversation the bridge would open with a SESSION-CREATE —
    // a follow-up rides `send-message` on a live chain, which the seat door never keys.
    if (route && chatMsg.chatThreadId && !threadMap.has(chatMsg.chatThreadId) && allowlist.isAdmitted(chatMsg.chatUserId)) {
      const refusal = await preEnqueueRefusal(route, chatMsg.text);
      if (refusal) {
        clearPending(chatMsg.chatThreadId); // the ⏳ the warm attempt stamped must not outlive the drop
        await deliverToOwner({ chatThreadId: chatMsg.chatThreadId, text: refusal.notice, markAsk: false });
        log('warn', refusal.message, { chatThreadId: chatMsg.chatThreadId, ...refusal.detail });
        return { forwarded: false, refused: true, reason: refusal.reason };
      }
    }

    const outcome = await forwardPath.onChatMessage(chatMsg);
    // Arm the reply leg on every FORWARDED turn — a session-create (new conversation)
    // or a follow-up (the chain re-dispatches → a new exec on the same queue). The
    // leg then watches for the spawn, awaits turn-end, and delivers the reply.
    if (outcome && outcome.liveHolder && chatMsg && chatMsg.chatThreadId) {
      // Bus-only: the live sitting reads the reply. Do not arm — that resets the ⏳ clock —
      // and take off the ⏳ this turn stamped before the warm attempt; the sitting already
      // has its own watcher from the sitting that is live.
      clearPending(chatMsg.chatThreadId);
    } else if (outcome && outcome.forwarded && chatMsg && chatMsg.chatThreadId) {
      // What this seat is now working on (§ the held duplicate) — recorded on the COLD path only.
      // A warm turn answers within the same call, so the seat it ran at is free again by the time
      // anything could match it, and remembering that text would only invite a false drop later.
      noteForwarded(route, chatMsg.text);
      replyLeg.arm(chatMsg.chatThreadId);
      // The read-receipt: ONE marker, stamped the moment the message is accepted for
      // processing and taken off when its answer lands (§ pending marker below). It
      // REPLACES the fire-and-forget 🤖 of 2026-08-06 — see that section for why two
      // independent indicators could not be ordered against each other.
      markPending(chatMsg.chatThreadId, chatMsg._channel, chatMsg._msgTs);
    } else if (chatMsg && chatMsg.chatThreadId) {
      // REFUSED after the warm attempt marked it. Nothing is coming for this message, so the
      // ⏳ must not outlive it — a marker with no answer behind it is dead air wearing the
      // costume of work in progress. A no-op when nothing was marked. (The held-re-submit
      // exception this branch used to carry is gone with the machinery: a message the DAEMON
      // queued was `forwarded`, so it takes the arming branch above and keeps its marker.)
      clearPending(chatMsg.chatThreadId);
    }
    log('info', 'chat message handled', { chatThreadId: chatMsg && chatMsg.chatThreadId, ...outcome });
    return outcome;
  }

  // conversation → { channel, threadTs } — where to post owner output back.
  const replyAddr = new Map();

  // ── THE ⏳ PENDING MARKER (owner-directed 2026-08-07) ────────────────────────
  //
  // Between the forward and the reply the owner saw NOTHING for minutes: a real
  // three-minute turn and a stalled bridge are indistinguishable. So the bridge
  // stamps ⏳ on the owner's OWN message the moment a turn is accepted for
  // processing, and takes it off when that conversation's reply lands in the thread.
  //
  // ⚑ ONE MARKER, NOT TWO (owner-observed 2026-08-07: "the hourglass can appear
  // before the answer and the robot after it"). The 🤖 read-receipt this replaces was
  // a SECOND, independent fire-and-forget reaction: two un-ordered HTTP calls whose
  // arrival order Slack decides, so the acknowledgement could surface after the
  // answer it acknowledged. One marker with a defined lifetime — added at accept,
  // removed at delivery — is the only shape that has an order to guarantee.
  //
  // ⚑ THE CALLS ARE SERIALIZED, which is what makes the order REAL rather than
  // hoped-for. Add and remove are separate Slack calls; on a fast turn the remove can
  // be issued while the add is still in flight, and if they land out of order the ⏳
  // is stuck on the message FOREVER — dead air's exact twin. Chaining every reaction
  // call onto one promise means a remove is never even sent before its own add has
  // returned.
  // ponytail: ONE global chain, not one per conversation — chat is a handful of
  // messages a minute, so a slow reaction call briefly delays another conversation's
  // marker and nothing else. Key the chain by conversation if that ever bites.
  //
  // FAIL-OPEN BY CONSTRUCTION: nothing here is awaited by the handling or delivery
  // path and no result is read, so a missing `reactions:write` scope — or any other
  // Slack error — costs a single info line and changes nothing else.
  //
  // ONE ts PER CONVERSATION, the LATEST wins. If several owner messages queue up in
  // one thread, marking the newest and clearing the previous one is enough; a set of
  // live markers would be state to expire and reconcile for a decoration.
  //
  // NOT PERSISTED, deliberately — same reasoning as the reply leg's watch state
  // (reply-leg.js header): it is time-bound. A restart drops the in-flight turn's
  // reply anyway, and a restored entry would only let the bridge remove a ⏳ from a
  // message whose answer never came.
  const HOURGLASS = 'hourglass_flowing_sand';
  const hourglassAt = new Map(); // conversation → { channel, ts } of the marked message
  let reactionChain = Promise.resolve();

  function queueReaction(call) {
    // `.then(call, call)` — a previous failure must never stop the next call, and the
    // trailing catch keeps the chain from ever rejecting (fail-open, always).
    reactionChain = reactionChain.then(call, call).catch(() => {});
  }

  function markPending(chatThreadId, channel, ts) {
    if (!chatThreadId || !channel || !ts || typeof transport.react !== 'function') return;
    // IDEMPOTENT ON THE SAME MESSAGE. One owner turn now passes here twice — once before the
    // warm attempt, once again if that attempt refuses and the cold path forwards it — and
    // without this the second call would remove the ⏳ it just added and re-add it, a visible
    // flicker plus two useless Slack calls on every cold message.
    const already = hourglassAt.get(chatThreadId);
    if (already && already.channel === channel && already.ts === ts) return;
    clearPending(chatThreadId); // the previous turn's ⏳ never outlives its successor
    hourglassAt.set(chatThreadId, { channel, ts });
    queueReaction(() => transport.react({ channel, ts, name: HOURGLASS }));
  }

  function clearPending(chatThreadId) {
    const at = hourglassAt.get(chatThreadId);
    if (!at) return;
    hourglassAt.delete(chatThreadId);
    if (typeof transport.unreact !== 'function') return;
    queueReaction(() => transport.unreact({ channel: at.channel, ts: at.ts, name: HOURGLASS }));
  }

  // ── THE TWO PRE-ENQUEUE GUARDS (P2, replacing the pending re-submit) ────────
  //
  // The whole pending-re-submit machinery is DELETED. It existed because the daemon's idempotent
  // door DISCARDED a session-create that arrived while the seat held a live turn, so the bridge had
  // to hold the text and re-fire it — a queue reimplemented inside a transport that restarts.
  // `on_seat_busy: 'queue'` (forward-path.js) hands the row to the daemon's own persistent queue
  // instead, and the daemon launches it when the seat frees. Nothing to hold, nothing to re-fire,
  // nothing to persist, and no give-up notice: the queue outlives this process.
  //
  // What the daemon queue does NOT do is collapse a DUPLICATE — every row it takes will run. So the
  // two things the bridge still owes happen BEFORE the enqueue, never after it:

  // ⚠ (1) THE BYTE-IDENTICAL DUPLICATE (owner-observed 2026-08-12). The owner's DM arrived TWICE,
  // byte-identical, 22 seconds apart across a Socket Mode drop/reconnect — two GENUINE Slack
  // messages with different ts (he re-sent after seeing silence), so the transport's redelivery
  // guard cannot see them and must not. The door used to absorb the second one; now it would become
  // a second queued row: a duplicate agent chain, duplicate spend, the same answer twice.
  //
  // ⚑ THE SEAT IS THE UNIT, NOT THE CONVERSATION. The two DMs were two conversations; what they
  // shared was ONE master seat. So the bridge remembers the last text it sent to each seat home and
  // drops a byte-identical repeat BEFORE it reaches `enqueue-job`.
  //
  // ⚑ AND IT NOW APPLIES TO EVERY SEND, not only to a refused one — which is the price of the door
  // no longer telling us "busy". ponytail: exact match, one entry per seat (a different text to the
  // same seat evicts it), no persistence, 10-minute ceiling. Clear the entry when that turn's reply
  // lands if a false drop is ever observed.
  const lastForwarded = new Map(); // seat home -> { text, at }
  const DUPLICATE_WINDOW_MS = 10 * 60 * 1000;

  // The seat a route homes at, from the forward path's OWN resolver — so the key is the thing the
  // door actually keys on and not a second guess at it. `master` stands in for an unset workdir:
  // all master traffic shares one seat, which is exactly the observed case.
  function seatHomeOf(route) {
    const home = route ? forwardPath.workdirFor(route) : null;
    return home && home.ok ? (home.workdir || 'master') : null;
  }

  function noteForwarded(route, text) {
    const seat = seatHomeOf(route);
    if (seat) lastForwarded.set(seat, { text, at: Date.now() });
  }

  // Posted INSTEAD of enqueuing. Dropping in silence would leave the owner watching a thread that
  // never answers. Fixed string, no internals — the same D111 discipline the other notices keep.
  const SEAT_BUSY_DUPLICATE_NOTICE = "⚠ that was identical to the message already being worked on — it was NOT sent again; the answer to the first one is on its way";

  // ⚠ (2) THE PER-SEAT PENDING CAP. A daemon queue that never refuses turns a busy seat into an
  // unbounded backlog: the owner types five more questions into the silence and gets five more
  // sessions, hours later, in order, each answering a question he has moved on from.
  //
  // ⚑ THE SIGNAL IS THE DAEMON'S OWN QUEUE, not a counter this process keeps. A local counter is
  // wrong across a restart and wrong about rows the daemon has already launched; `inspect queue`
  // returns the PENDING rows, which is exactly the question being asked. One read per cold
  // session-create — chat is a handful of messages a minute.
  //
  // ⚑ AND IT FAILS OPEN. A queue read that does not answer means the bridge cannot tell, and a
  // bridge that cannot tell must never refuse the owner's message.
  const PENDING_CAP = 5;
  const PENDING_CAP_NOTICE = `⏳ ${PENDING_CAP} messages already waiting — hold on`;

  // A pending row's seat, from the same `args.workdir` the enqueue put there (`master` for an
  // unset workdir, matching seatHomeOf). `args` is stored as JSON text.
  function seatOfQueueRow(row) {
    if (!row || row.job_id !== config.sessionJobId) return null;
    try {
      const args = typeof row.args === 'string' ? JSON.parse(row.args) : (row.args || {});
      return args.workdir || 'master';
    } catch { return null; }
  }

  async function pendingAtSeat(seat) {
    const res = await forwarder.inspect('queue');
    if (!res || !res.ok || !res.result) {
      log('warn', 'pending-cap queue read failed — NOT refusing the message', { seat, error: res && res.error });
      return null; // cannot tell → fail open
    }
    const rows = Array.isArray(res.result.rows) ? res.result.rows : [];
    return rows.filter((r) => seatOfQueueRow(r) === seat).length;
  }

  // Runs both guards for a message that would open a NEW conversation. Returns null to proceed, or
  // the notice/reason to refuse with.
  async function preEnqueueRefusal(route, text) {
    const seat = seatHomeOf(route);
    if (!seat) return null; // unresolvable seat — the forward path's own refusal is the honest one
    const last = lastForwarded.get(seat);
    if (last && last.text === text && (Date.now() - last.at) <= DUPLICATE_WINDOW_MS) {
      return {
        notice: SEAT_BUSY_DUPLICATE_NOTICE, reason: 'duplicate-at-seat',
        message: 'message DROPPED before the enqueue — byte-identical to the last one sent to this seat',
        detail: { seat, agoMs: Date.now() - last.at },
      };
    }
    // ponytail: `>=` so the notice states a FACT (five are waiting, this would be the sixth). The
    // count also includes a row enqueued at a FREE seat in the seconds before its tick fires —
    // harmless at a cap of five, and the alternative is a liveness check nobody needs.
    const waiting = await pendingAtSeat(seat);
    if (waiting !== null && waiting >= PENDING_CAP) {
      return {
        notice: PENDING_CAP_NOTICE, reason: 'pending-cap',
        message: 'message REFUSED before the enqueue — too many already queued at this seat',
        detail: { seat, waiting, cap: PENDING_CAP },
      };
    }
    return null;
  }

  // ── CONVERSATION STATE ACROSS RESTARTS (owner ruling 2026-08-06) ────────────
  //
  // The bridge is a systemd unit with Restart=on-failure, so restarts happen
  // unattended. Both conversation tables — the thread map and the reply addresses —
  // used to die with the process, and the owner hit the consequence twice in one day:
  // an un-mentioned reply in a live thread fell into the unmapped-channel refusal and
  // got SILENCE, and DM follow-ups minted fresh chains. With `state_file` set, both
  // tables are written on every mutation and rebuilt before the transport listens.
  //
  // OPT-IN: no `state_file` → no reads, no writes, no file — byte-identical to the
  // pre-ruling behaviour for every embedder and probe that passes no key.
  //
  // WRITE-PER-MUTATION, no debounce. Chat volume is a handful of messages a minute;
  // a scheduler here would be machinery guarding against a load that does not exist.
  //
  // A write failure is LOGGED AND SWALLOWED. Persistence is a convenience over an
  // already-correct in-memory path: a full disk must degrade the bridge to its old
  // amnesia, never take the conversation down with it.
  const stateFile = (config && config.stateFile) || null;

  function saveState() {
    if (!stateFile) return;
    const doc = {
      version: STATE_VERSION,
      savedAt: new Date().toISOString(),
      threads: threadMap.toJSON(),
      replyAddr: Object.fromEntries(replyAddr),
      // ADDITIVE, never restructuring: a version-1 loader that knows nothing of the
      // ferry reads this file exactly as before and ignores the extra key. That is why
      // STATE_VERSION does not move — the shape is extended, not changed.
      busFerry: busFerry.toJSON(),
      // Same rule again, for the agent threads (ratified 2026-08-09). Losing this map would
      // orphan every open agent thread: the owner's reply would land in a thread the bridge no
      // longer attributes to anybody and be handled as ordinary goal traffic.
      agentThreads: Object.fromEntries(agentThreads),
      // Same additive rule for the ask threads. See `askThreads`' header: losing this map leaves
      // an open ask whose answer the bridge can no longer recognize as an answer.
      askThreads: Object.fromEntries(askThreads),
      // ⚠ NO `pendingRetries` KEY (P2). The daemon queue holds what this used to hold, and it
      // survives a bridge restart by construction. A file written by an OLDER bridge may still
      // carry the key — loadState says so out loud rather than dropping it in silence.
    };
    // Atomic: temp file in the SAME directory (rename is only atomic within a
    // filesystem) + rename over the target. A reader never sees a half-written file,
    // and a crash mid-write leaves the previous good state intact. 0600 — the file
    // holds no secret, but it does hold who talks to this bridge and where.
    const tmp = `${stateFile}.tmp-${process.pid}`;
    try {
      fs.mkdirSync(path.dirname(stateFile), { recursive: true });
      fs.writeFileSync(tmp, JSON.stringify(doc), { mode: 0o600 });
      fs.renameSync(tmp, stateFile);
    } catch (err) {
      try { fs.unlinkSync(tmp); } catch {}
      log('error', 'chat bridge state write failed — conversations will not survive a restart', { stateFile, error: err.message });
    }
  }

  // Rebuild both tables from disk. Called at start() BEFORE the transport listens, so
  // no inbound message can ever race the load. A corrupt file is renamed ASIDE and the
  // bridge starts EMPTY: crash-looping a systemd unit on unparseable state would take
  // the whole chat surface down over a convenience cache, and the aside copy keeps the
  // evidence for whoever looks.
  function loadState() {
    if (!stateFile || !fs.existsSync(stateFile)) return { loaded: false, reason: stateFile ? 'no-state-file-yet' : 'not-configured' };
    let doc;
    try {
      doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new Error('state is not a JSON object');
    } catch (err) {
      const aside = `${stateFile}.corrupt-${Date.now()}`;
      try { fs.renameSync(stateFile, aside); } catch {}
      log('error', 'chat bridge state file unparseable — renamed aside, starting with EMPTY conversation state', { stateFile, aside, error: err.message });
      return { loaded: false, reason: 'corrupt', aside };
    }
    const threads = threadMap.load(doc.threads);
    replyAddr.clear();
    for (const [id, a] of Object.entries(doc.replyAddr || {})) {
      if (a && typeof a === 'object' && a.channel) replyAddr.set(String(id), { channel: a.channel, threadTs: a.threadTs ?? null });
    }
    // The ferry's cursors ride the same file. Restoring them is what stops a restart
    // from re-arming the first-sight flood on every open run.
    const busCursors = busFerry.load(doc.busFerry);
    // The agent threads ride it too. A row missing its `threadTs` is DROPPED rather than
    // half-restored: an entry with no anchor would make the next row reply to nothing.
    agentThreads.clear();
    for (const [k, v] of Object.entries(doc.agentThreads || {})) {
      if (v && typeof v === 'object' && v.threadTs) agentThreads.set(String(k), { threadTs: String(v.threadTs) });
    }
    askThreads.clear();
    for (const [k, v] of Object.entries(doc.askThreads || {})) {
      if (v && typeof v === 'object' && v.askId && v.goalId && v.seat) {
        askThreads.set(String(k), { goalId: String(v.goalId), seat: String(v.seat), askId: String(v.askId), label: v.label || 'work-content' });
      }
    }
    // ⚠ A STATE FILE FROM THE PRE-QUEUE BRIDGE (P2). Held re-submits used to ride this file, and
    // the deploy that deletes the machinery meets exactly one such file on this box. The entries
    // are DISCARDED — there is no holder left to restore them into — but never in silence: each
    // held text is named in the log, because a message vanishing across a deploy is the one thing
    // the whole re-submit feature existed to prevent. The owner can re-send what he sees here.
    const staleHeld = Object.entries(doc.pendingRetries || {})
      .filter(([, v]) => v && typeof v === 'object' && typeof v.text === 'string' && v.text);
    if (staleHeld.length) {
      log('warn', 'DISCARDING held re-submits from an older state file — the daemon queue replaces them; these texts were NOT sent and are not held any more', {
        stateFile, count: staleHeld.length,
        discarded: staleHeld.map(([id, v]) => ({ chatThreadId: id, text: v.text })),
      });
    }
    log('info', 'chat bridge conversation state restored', { stateFile, threads, replyAddresses: replyAddr.size, busCursors, agentThreads: agentThreads.size, discardedHeldTexts: staleHeld.length, savedAt: doc.savedAt || null });
    return { loaded: true, threads, replyAddresses: replyAddr.size, busCursors, agentThreads: agentThreads.size, discardedHeldTexts: staleHeld.length };
  }

  // Every thread-map mutation persists — including the ones resolveChainThread makes
  // in place. The reply-address map has two mutation sites — set on inbound, delete on
  // closeGoal — each calling saveState() directly. (The load path rebuilds both tables
  // and deliberately does NOT persist: reading the file is not a change to it.)
  threadMap.setOnMutate(saveState);

  // Outbound: deliver worker/leader output addressed to the owner (chat-bridge-spec.md
  // Behavior #3), at the TURN BOUNDARY (notes §7b — never mid-turn). `markAsk`
  // records that the daemon posed a pending `ask` on this conversation, so the
  // owner's NEXT reply forwards as an `answer` (D105) rather than a `note`.
  async function deliverToOwner({ chatThreadId, text, markAsk = false, answersOwnerAsk = false }) {
    const addr = replyAddr.get(chatThreadId);
    if (!addr) {
      log('warn', 'no reply address for conversation — cannot deliver owner output', { chatThreadId });
      return { delivered: false, reason: 'no-reply-address' };
    }
    if (markAsk) threadMap.setPendingAsk(chatThreadId, true);
    const posted = await postSlack({
      kind: 'notification',
      channel: addr.channel,
      threadTs: addr.threadTs,
      text,
      goal_id: goalChannels ? goalChannels.goalForChannel(chatThreadId) : null,
    });
    // Something owner-facing landed in the thread — the reply, or the honest
    // give-up notice. Either way the wait is over, so the ⏳ comes off. This is the
    // ONE place every conversation-addressed post passes through, which is why the
    // clear hangs here and not in the reply leg.
    if (posted && posted.delivered !== false) clearPending(chatThreadId);
    // The `open_asks` row this reply settles, reaped at the ONE place every owner-facing post
    // passes through. `answersOwnerAsk` is true only for a GENUINELY conformant fenced reply
    // (reply-leg.js/live-sessions warm path pass `verdict.ok`) — a FALLBACK_TEXT/GIVE_UP_NOTICE/
    // DEAD_AIR_NOTICE post is a system stand-in and never settles an ask (Q1 = A, owner-ruled D89:
    // only a conformant reply counts).
    //
    // ⚠ THE ASK IS NAMED BY ITS THREAD, and that is the whole release rule [D-4-ruling, T1-R12]:
    // an authorized reply releases the ask bound to THAT EXACT thread. The old "with no askId,
    // settle the OLDEST open one" fallback is DELETED — it is how a reply to one question closed a
    // different one — so `chatThreadId` is passed and the reap refuses without it.
    //
    // ⚠ THE REAP AND THE SEAT'S RELAUNCH SIGNAL ARE ONE TRANSACTION, daemon-side (§2.8): no orphan
    // and no twin. This process holds no store handle (owner ruling 2026-08-24, option (a)) — it
    // makes one `record-owner-ask` gateway call and logs whatever comes back, never changing course
    // on the result, because the owner's post has already landed by here.
    if (answersOwnerAsk && posted && posted.delivered !== false && goalChannels) {
      const goalId = goalChannels.goalForChannel(chatThreadId);
      if (goalId) {
        await askRecord.reapAsk({ goalId, seat: 'goal-master', chatThreadId });
      }
    }
    return posted;
  }

  // ── The goal lifecycle (task 7.58, both settled open points) ────────────────
  //
  // These two calls ARE the settled answers, exposed as the bridge's public surface.
  // Their eventual caller is the goal machinery — `rbtv goal scaffold` at goal
  // registration and the goal close at retire (task 7.63). Until that hook exists an
  // explicit call stands in; the ANSWER is unchanged, only its caller. Reasoning and
  // the registry-transcription flags: `goal-channel-design.md`.

  // (a) CREATION — at goal registration. Idempotent and name-derived.
  async function registerGoal(goalId) {
    if (!goalChannels) return { ok: false, error: 'no-goal-channel-map-configured' };
    return goalChannels.ensureChannel(goalId);
  }

  // (b) CLOSE-TIME — ARCHIVE, never delete. Also forgets the conversation's reply
  // address and its thread-map-facing state, so nothing lingers pointing at a
  // channel that takes no more goal traffic.
  async function closeGoal(goalId) {
    if (!goalChannels) return { ok: false, error: 'no-goal-channel-map-configured' };
    const channelId = goalChannels.channelForGoal(goalId);
    const res = await goalChannels.retire(goalId);
    if (res.ok && channelId) { replyAddr.delete(String(channelId)); saveState(); }
    return res;
  }

  async function start() {
    // FIRST, before anything can listen: rebuild the conversation tables from disk.
    // Ordering is the whole point — a message arriving against an empty map is the
    // amnesia bug, and it would be indistinguishable from the pre-restart behaviour.
    const restored = loadState();
    const r = await transport.start();
    // Resolve THIS bot's user id — the mention route needs it and nothing else can
    // supply it (the id is a property of the installed app, not of config). Failure is
    // loud but not fatal: the mention route simply stays disabled, which is exactly
    // the pre-ruling behaviour, and DM + goal traffic are untouched.
    if (typeof transport.authTest === 'function') {
      try {
        const who = await transport.authTest();
        if (who && who.ok && who.userId) {
          botUserId = who.userId;
          log('info', 'bot identity resolved — mention route armed', { botUserId });
        } else {
          log('error', 'auth.test did not return a bot user id — MENTION ROUTE DISABLED (unmapped channels stay refused)', { error: who && who.error });
        }
      } catch (err) {
        log('error', 'auth.test threw — MENTION ROUTE DISABLED (unmapped channels stay refused)', { error: err.message });
      }
    } else {
      log('warn', 'transport exposes no auth.test — mention route disabled');
    }
    // Rebuild goal↔channel from the workspace BEFORE listening: the bridge's map is
    // in-memory, and name-derivation is what lets a restart recover it with no
    // persistence. A recovery failure is not fatal — the bridge still serves master
    // (DM) traffic, and goal channels re-bind on the next registerGoal — but it is
    // said loudly, because until it succeeds every goal channel reads as unroutable.
    let recovered = null;
    if (goalChannels) {
      try {
        recovered = await goalChannels.recover();
        if (!recovered.ok) log('warn', 'goal↔channel recovery failed — goal channels will read as unroutable until re-registered', { error: recovered.error });
      } catch (err) {
        log('warn', 'goal↔channel recovery threw — continuing with an empty map', { error: err.message });
      }
    }
    replyLeg.start();
    // Opt-in and fail-closed: `bus_ferry` off → never started; on but unable to resolve
    // the owner DM or the workspace → the ferry logs loudly and stays disabled, and
    // nothing else about the bridge changes.
    let ferry = { enabled: false, reason: 'not-configured' };
    if (config && config.busFerry) ferry = await busFerry.start();
    log('info', 'chat bridge started', { transport: 'slack-socket-mode', goalChannelsBound: recovered && recovered.bound, stateRestored: restored, busFerry: ferry, liveSessions: liveLeg.enabled, ...r });
    return r;
  }

  function stop() {
    replyLeg.stop();
    busFerry.stop();
    transport.stop();
    log('info', 'chat bridge stopped');
  }

  return {
    onChatMessage, deliverToOwner, start, stop,
    postOwnerAsk, askDoor,
    registerGoal, closeGoal, routeOf, outbox,
    routeToAgentThread, agentThreadFor, agentForThread, knowsThread,
    _replyAddr: replyAddr, _agentThreads: agentThreads, _askThreads: askThreads, _lastForwarded: lastForwarded,
    forwardPath, replyLeg, busFerry, goalChannels, liveLeg,
    _saveState: saveState, _loadState: loadState, stateFile,
  };
}

module.exports = { createChatBridge };

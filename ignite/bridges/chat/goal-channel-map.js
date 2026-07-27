'use strict';

// THE GOAL ↔ CHANNEL MAP (task 7.58; registry `concepts/channel.md` § v1 realization,
// owner ruling `decisions.md#d-channel-per-goal`). A goal's Slack surface is a
// DEDICATED CHANNEL PER GOAL — the former per-goal chat-THREAD surface is superseded.
// The goal `thread` maps 1:1 onto the `channel`, so in this module ONE CHANNEL IS ONE
// GOAL THREAD: the conversation id for goal traffic is the CHANNEL id, not a
// `channel:thread_ts` pair (that pair remains the conversation id for DM / master
// traffic, which this module never touches).
//
// The two formerly-OPEN points are SETTLED here — reasoning, alternatives, and the
// registry-transcription flags are in `goal-channel-design.md` beside this file. In
// short:
//   (a) CREATION — the BRIDGE creates the channel, at GOAL REGISTRATION, through one
//       idempotent NAME-DERIVED call (`ensureChannel`). Only the bridge holds a chat
//       credential, so creation belongs where that credential already is.
//   (b) CLOSE-TIME — ARCHIVE, never delete (`retire`), idempotent. Deletion is
//       irreversible and destroys the owner-side half of the goal's history.
//
// ⚑ NAME-DERIVATION IS THE LOAD-BEARING PROPERTY, not a convenience. The bridge holds
// no store and its state dies with the process (the same owner-known caveat as
// thread-map / replyAddr). Because `{prefix}{goalId}` is a BIJECTION, a restarted
// bridge re-derives every goal↔channel binding from `conversations.list` alone
// (`recover()`) — no persistence, no store handle, no new capability. That is also why
// a non-derivable goal id is REFUSED rather than sanitized: a lossy transform would
// break the inverse, and two goal ids could silently share one channel.
//
// ⚑ NO `conversations.invite` CODE PATH EXISTS HERE, BY CONSTRUCTION. The bridge never
// adds anyone to a channel; membership is a human act in the Slack UI. This is what
// makes the run's `r-slack-etiquette` guard ("the owner is added to NO test channel")
// mechanically true rather than a policy nobody enforces — `probe-chat-goal-channel`
// asserts the absence of the string from the bridge source, the same shape as
// `probe-chat-boundary`.

// Slack channel names: lowercase, ≤ 80 chars, letters/digits/hyphen/underscore only.
const SLACK_NAME_MAX = 80;
const GOAL_ID_RE = /^[a-z0-9][a-z0-9_-]*$/;
const PREFIX_RE = /^[a-z0-9][a-z0-9_-]*$/;

// goalId → channel name. THROWS on a non-derivable id (fail loud, never sanitize —
// see the header: sanitizing would break the inverse this design depends on).
function channelNameForGoal(goalId, prefix) {
  const p = String(prefix || '');
  if (!PREFIX_RE.test(p)) {
    throw new Error(`channel prefix ${JSON.stringify(p)} is not a valid Slack name fragment`);
  }
  const id = String(goalId || '');
  if (!GOAL_ID_RE.test(id)) {
    throw new Error(`goal id ${JSON.stringify(id)} is not channel-derivable (need ^[a-z0-9][a-z0-9_-]*$) — refusing rather than sanitizing, which would break goal↔channel invertibility`);
  }
  const name = `${p}${id}`;
  if (name.length > SLACK_NAME_MAX) {
    throw new Error(`derived channel name ${JSON.stringify(name)} exceeds Slack's ${SLACK_NAME_MAX}-char limit`);
  }
  return name;
}

// The inverse — the half that makes `recover()` possible.
function goalIdFromChannelName(name, prefix) {
  const n = String(name || '');
  const p = String(prefix || '');
  if (!p || !n.startsWith(p)) return null;
  const id = n.slice(p.length);
  return GOAL_ID_RE.test(id) ? id : null;
}

// `slack` is the transport's narrow ADMIN surface (slack-socket-mode.js):
//   createChannel({ name })      → { ok, channel: { id, name } } | { ok:false, error }
//   listChannels({ cursor, excludeArchived }) → { ok, channels:[{id,name}], nextCursor }
//   archiveChannel({ channel })  → { ok } | { ok:false, error }
// Nothing else. There is deliberately no invite/kick/setTopic here.
function createGoalChannelMap({ slack, prefix, logger = null } = {}) {
  if (!slack) throw new Error('createGoalChannelMap requires a slack admin surface');
  if (!PREFIX_RE.test(String(prefix || ''))) {
    throw new Error('createGoalChannelMap requires a valid channel prefix (e.g. "goal-", or "test-" under a test-channels-only ruling)');
  }
  const pfx = String(prefix);

  const byGoal = new Map();    // goalId    -> channelId
  const byChannel = new Map(); // channelId -> goalId

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  function bind(goalId, channelId) {
    byGoal.set(String(goalId), String(channelId));
    byChannel.set(String(channelId), String(goalId));
  }

  function unbind(goalId) {
    const ch = byGoal.get(String(goalId));
    byGoal.delete(String(goalId));
    if (ch) byChannel.delete(String(ch));
    return ch || null;
  }

  function channelForGoal(goalId) { return byGoal.get(String(goalId)) || null; }
  function goalForChannel(channelId) { return byChannel.get(String(channelId)) || null; }
  function size() { return byGoal.size; }

  // Page `conversations.list` to its end looking for one name. Bounded — never an
  // unbounded cursor loop.
  const MAX_LIST_PAGES = 20;
  async function findByName(name) {
    let cursor = null;
    for (let page = 0; page < MAX_LIST_PAGES; page++) {
      const res = await slack.listChannels({ cursor, excludeArchived: true });
      if (!res || !res.ok) return { ok: false, error: (res && res.error) || 'list-failed' };
      const hit = (res.channels || []).find((c) => c && c.name === name);
      if (hit) return { ok: true, channel: hit };
      cursor = res.nextCursor || null;
      if (!cursor) return { ok: true, channel: null };
    }
    log('warn', 'conversations.list page cap hit before the channel was found', { name, pages: MAX_LIST_PAGES });
    return { ok: true, channel: null };
  }

  // (a) THE CREATION CALL — idempotent, name-derived. The goal-registration hook is
  // its caller once it exists (task 7.63 `rbtv goal scaffold`); until then an explicit
  // call stands in (the ANSWER is unchanged, only its caller — see the design doc).
  //
  // `name_taken` is NOT an error: it is the ADOPT path. Two ways to reach it — a
  // restart that forgot its map, and a channel a human made ahead of time — and both
  // want the same outcome: bind the existing channel, create nothing.
  async function ensureChannel(goalId) {
    const gid = String(goalId);
    const existing = channelForGoal(gid);
    if (existing) return { ok: true, goalId: gid, channelId: existing, created: false, reason: 'cached' };

    const name = channelNameForGoal(gid, pfx); // throws on a non-derivable id — fail loud
    const res = await slack.createChannel({ name });
    if (res && res.ok && res.channel && res.channel.id) {
      bind(gid, res.channel.id);
      log('info', 'goal channel created and bound', { goalId: gid, channelId: res.channel.id, name });
      return { ok: true, goalId: gid, channelId: res.channel.id, created: true, reason: 'created', name };
    }
    if (res && res.error === 'name_taken') {
      const found = await findByName(name);
      if (!found.ok) return { ok: false, goalId: gid, error: found.error, reason: 'adopt-list-failed' };
      if (!found.channel) {
        // Taken but not visible to us: an ARCHIVED channel holds no name in Slack, so
        // the realistic case is a private channel the bot is not in. Fail loud — never
        // silently route a goal at a channel we cannot read.
        return { ok: false, goalId: gid, error: 'name_taken_but_unresolvable', reason: 'adopt-not-found', name };
      }
      bind(gid, found.channel.id);
      log('info', 'goal channel adopted (name already taken) and bound', { goalId: gid, channelId: found.channel.id, name });
      return { ok: true, goalId: gid, channelId: found.channel.id, created: false, reason: 'adopted', name };
    }
    log('warn', 'goal channel creation refused by Slack', { goalId: gid, name, error: res && res.error });
    return { ok: false, goalId: gid, error: (res && res.error) || 'create-failed', reason: 'create-failed', name };
  }

  // Bind a channel the caller already resolved (e.g. a channel created out-of-band).
  // Verifies the name still derives from the goal id, so a hand-bound pair can never
  // violate the bijection the recovery path depends on.
  function bindExisting(goalId, channelId, channelName = null) {
    const gid = String(goalId);
    if (channelName != null && channelName !== channelNameForGoal(gid, pfx)) {
      throw new Error(`channel ${JSON.stringify(channelName)} does not derive from goal ${JSON.stringify(gid)} under prefix ${JSON.stringify(pfx)}`);
    }
    bind(gid, channelId);
    log('info', 'goal channel bound explicitly', { goalId: gid, channelId: String(channelId) });
    return { ok: true, goalId: gid, channelId: String(channelId) };
  }

  // RECOVERY — rebuild the whole map from the workspace. This is the payoff of
  // name-derivation: a restarted bridge calls this once and is whole again, with no
  // persisted state anywhere. Channels whose name does not derive a goal id are
  // ignored (the bot may sit in ordinary channels; those are not goal traffic).
  async function recover() {
    let cursor = null;
    let bound = 0;
    let scanned = 0;
    for (let page = 0; page < MAX_LIST_PAGES; page++) {
      const res = await slack.listChannels({ cursor, excludeArchived: true });
      if (!res || !res.ok) return { ok: false, error: (res && res.error) || 'list-failed', bound, scanned };
      for (const c of res.channels || []) {
        scanned += 1;
        if (!c || !c.id || !c.name) continue;
        const gid = goalIdFromChannelName(c.name, pfx);
        if (!gid) continue;
        bind(gid, c.id);
        bound += 1;
      }
      cursor = res.nextCursor || null;
      if (!cursor) break;
    }
    log('info', 'goal↔channel map recovered from workspace', { bound, scanned, prefix: pfx });
    return { ok: true, bound, scanned };
  }

  // (b) THE CLOSE-TIME CALL — ARCHIVE, never delete. Idempotent: `already_archived`
  // and `channel_not_found` are SUCCESS (the post-condition "this channel takes no
  // more goal traffic" holds either way). The binding is dropped whenever the
  // post-condition holds, so a late inbound on that channel is no longer goal traffic.
  const ARCHIVE_BENIGN = new Set(['already_archived', 'channel_not_found']);
  async function retire(goalId) {
    const gid = String(goalId);
    const channelId = channelForGoal(gid);
    if (!channelId) return { ok: true, goalId: gid, channelId: null, archived: false, reason: 'not-mapped' };
    const res = await slack.archiveChannel({ channel: channelId });
    if (res && res.ok) {
      unbind(gid);
      log('info', 'goal channel archived and unbound (close-time lifecycle)', { goalId: gid, channelId });
      return { ok: true, goalId: gid, channelId, archived: true, reason: 'archived' };
    }
    if (res && ARCHIVE_BENIGN.has(res.error)) {
      unbind(gid);
      log('info', 'goal channel already retired — binding dropped (idempotent)', { goalId: gid, channelId, error: res.error });
      return { ok: true, goalId: gid, channelId, archived: false, reason: res.error };
    }
    // A real refusal (e.g. missing scope): keep the binding — the channel is still
    // live and still the goal's surface. Fail loud, never pretend it retired.
    log('warn', 'goal channel archive refused — binding KEPT (channel is still live)', { goalId: gid, channelId, error: res && res.error });
    return { ok: false, goalId: gid, channelId, archived: false, error: (res && res.error) || 'archive-failed' };
  }

  return {
    ensureChannel, bindExisting, recover, retire,
    channelForGoal, goalForChannel, size,
    prefix: pfx,
  };
}

module.exports = { createGoalChannelMap, channelNameForGoal, goalIdFromChannelName, SLACK_NAME_MAX };

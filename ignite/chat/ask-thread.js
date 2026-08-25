'use strict';

// ── THREAD-PER-ASK, AND THE ONE DOOR THAT RELEASES ONE ────────────────────────────────────────
// `spec-owner-io.md` §2 and §3 (law: `DESIGN-BASELINE.md` v2 §Owner interface).
//
// TWO ACTS LIVE HERE AND NOTHING ELSE DOES:
//
//   1. POSTING an ask. Every new ask batch opens a NEW THREAD in the goal's channel [D18, T5-R8].
//      The opening message's Slack `thread_ts` IS the ask id — there is no allocator [D-8, §2.1] —
//      so the `display_suffix` the opening line prints cannot be known until Slack has answered.
//      That is why `postAsk` POSTS AND THEN REWRITES the same message: one message carrying the
//      §3 line, addressed by the id it minted. A placeholder suffix would be a lie in the one
//      field the owner uses to tell two open asks apart.
//
//   2. RELEASING one. §2.4, verbatim and in order: exact thread, authorized sender, parse, NACK or
//      reap. Everything the pre-D89 door did by GUESSING is gone — `re: <n>` and "the oldest still
//      open ask from that seat" are not implemented here and never will be [D-4-ruling, C-3,
//      T1-R12]. A reply that names no thread this module owns releases NOTHING.
//
// ⚑ ONLY ❓ MINTS A RECORD [§2.1]. `postNote` opens a thread and stamps the same §3 line with the
//   💭 marker, and deliberately does not call `openAsk`: a note is not something the owner owes an
//   answer to, so it must never appear in a digest, a status count, or a kill-clock suspension.
//
// ⚑ THE AUTHORIZED-SENDER SET IS INSTANCE CONFIG, NEVER REPO CONTENT (repo law: RBTV content is
//   general). It arrives injected, from `config.js#allowlist`; an empty set authorizes NOBODY,
//   fail-closed, because "no one is configured" must not read as "everyone is allowed".
//
// ⚑ THE BRIDGE IS A SEPARATE PROCESS. Nothing here holds a store handle, spawns a child, or
//   requires a sibling tree (`probes/probe-chat-boundary.js` enforces that). The ask ROW is
//   written daemon-side through the thirteenth gateway intent `record-owner-ask` (owner ruling
//   2026-08-24) — this module calls `ask-store.js`, which is that intent's sender and nothing more.
//   The one thing it does touch on disk is the REPLY COPY (see `replyCopyPath`), a plain file
//   beside the daemon's ask copy, because §2.4.5 has the relaunched seat read the reply FROM DISK
//   and the reap payload deliberately carries no corpus.

const fs = require('node:fs');
const path = require('node:path');
const { parseReply } = require('./reply-grammar');

const MARKER_ASK = '❓';
const MARKER_NOTE = '💭';
const LABELS = Object.freeze(['work-content', 'recovery']);

// §2.1: last 6 characters of `thread_ts` with the `.` stripped. `1724508123.123456` → `123456`.
function displaySuffix(threadTs) {
  return String(threadTs == null ? '' : threadTs).replace(/\./g, '').slice(-6);
}

// §3: EXACTLY ONE lead line, then the ask body. The separator is a middle dot with single spaces —
// the owner reads this on a phone and the three fields must stay one glance apart.
function openingLine({ marker, threadTs, seatName, label }) {
  return `${marker} ${displaySuffix(threadTs)} · ${seatName} · ${label}`;
}

function composeThreadOpener({ marker, threadTs, seatName, label, body }) {
  return `${openingLine({ marker, threadTs, seatName, label })}\n\n${String(body || '').trim()}`;
}

// The owner's reply, kept where the RELAUNCHED SEAT can read it (§2.4.5). The daemon writes the ask
// body to `<goal>/coordination/asks/<ask>.txt`; this is its sibling and never overwrites it. The
// id is sanitized for the FILENAME only — every record and every address still carries the raw ts.
function replyCopyPath(workspaceRoot, goalId, askId) {
  const safe = String(askId).replace(/[^A-Za-z0-9._-]/g, '_');
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goalId), 'coordination', 'asks', `${safe}.reply.txt`);
}

function createAskThreads({
  outbox,
  askRecord,
  // Rewrites an already-posted message in place. REQUIRED, and the constructor refuses without it
  // rather than degrading: the §3 line cannot be composed before Slack answers, so an embedder
  // that cannot rewrite cannot post a conforming ask at all. A wiring gap is caught HERE, at
  // construction, not at the first ask — which is the one moment it would be silent.
  updateMessage,
  // Instance config (`config.js#allowlist`). Empty = nobody is authorized.
  authorizedSenders = [],
  // This bot's own user id, so its own posts can never release an ask (§2.4.2). A FUNCTION is
  // accepted as well as a value, and the bridge passes one: the identity is resolved from Slack
  // at `start()`, long after this module is constructed, so a captured value would be `null`
  // forever and the self-reply guard would be dead code that reads as live.
  botUserId = null,
  // §2.4 / [T2-R14]: is this seat designated to reach the owner? A non-designated seat's ask is
  // REFUSED AT THIS DOOR. Default TRUE because the predicate is the embedder's (it owns the goal
  // folder) — an embedder that wires none is asking for no designation check, not for a silent
  // refusal of every ask.
  seatIsInteractive = () => true,
  workspaceRoot = null,
  logger = null,
} = {}) {
  if (!outbox || typeof outbox.post !== 'function') throw new Error('createAskThreads requires an outbox');
  if (!askRecord || typeof askRecord.openAsk !== 'function' || typeof askRecord.reapAsk !== 'function') {
    throw new Error('createAskThreads requires an ask record sender (openAsk/reapAsk)');
  }
  if (typeof updateMessage !== 'function') {
    throw new Error('createAskThreads requires updateMessage — the §3 opening line carries the ask id, which only Slack can mint');
  }

  const authorized = new Set(authorizedSenders.map(String).filter(Boolean));
  const botId = () => {
    const v = typeof botUserId === 'function' ? botUserId() : botUserId;
    return v == null ? null : String(v);
  };
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  // The shared body of `postAsk` and `postNote`: open a NEW thread, learn the id it minted, stamp
  // the §3 line onto it. Returns the id or the reason there is none.
  async function openThread({ marker, channelId, goalId, seatName, label, body }) {
    const posted = await outbox.post({
      kind: marker === MARKER_ASK ? 'ask' : 'notification',
      channel_id: channelId,
      thread_ts: null,          // A NEW THREAD, always — one per ask batch [D18, T5-R8].
      goal_id: goalId == null ? null : String(goalId),
      ask_id: null,             // Not known yet: this post is what mints it.
      payload: String(body || '').trim(),
    });
    if (!posted || posted.delivered !== true || !posted.ts) {
      log('warn', 'ask thread NOT opened — Slack never acked the opening message', {
        goalId, seat: seatName, error: (posted && posted.error) || 'not-acked',
      });
      return { posted: false, reason: (posted && posted.error) || 'not-acked' };
    }
    const threadTs = String(posted.ts);
    const line = openingLine({ marker, threadTs, seatName, label });
    const full = composeThreadOpener({ marker, threadTs, seatName, label, body });
    try {
      await updateMessage({ channel: channelId, ts: threadTs, text: full });
    } catch (err) {
      // The ask LANDED; only its lead line did not. Never a throw and never a retry that could
      // double-post: a second message would give the owner two threads for one question.
      log('warn', 'ask thread opened but its §3 lead line could not be stamped — the body is posted, the line is not',
        { goalId, seat: seatName, threadTs, error: err.message });
    }
    return { posted: true, threadTs, openingLine: line, text: full };
  }

  // POST AN ASK — the ❓ door. Mints the record; this is the only function that does.
  async function postAsk({ goalId, channelId, seatName, label = 'work-content', body, kind = 'ordinary' }) {
    if (!LABELS.includes(label)) {
      log('warn', 'ask REFUSED — label is not one of the two [D-7-ruling]', { goalId, seat: seatName, label });
      return { posted: false, reason: 'bad-label' };
    }
    // [T2-R14] A non-designated seat's owner-ask is refused AT SEND. Refused, never parked: a
    // parked ask is the silence this redesign exists to end, and the refusal tells the caller.
    if (!seatIsInteractive(goalId, seatName)) {
      log('warn', 'owner-ask REFUSED — this seat is not designated to reach the owner [T2-R14]', { goalId, seat: seatName });
      return { posted: false, reason: 'seat-not-interact' };
    }
    const opened = await openThread({ marker: MARKER_ASK, channelId, goalId, seatName, label, body });
    if (!opened.posted) return opened;
    const recorded = await askRecord.openAsk({
      goalId, seat: seatName, chatThreadId: opened.threadTs, text: body, label,
    });
    log('info', 'owner ask posted in a NEW thread', {
      goalId, seat: seatName, askId: opened.threadTs, label, kind, recorded: recorded.recorded === true,
    });
    return { posted: true, askId: opened.threadTs, openingLine: opened.openingLine, text: opened.text, label, kind, recorded };
  }

  // POST A NOTE — the 💭 door. §2.1: a note mints NO record, so it can never read as `open`.
  async function postNote({ goalId, channelId, seatName, label = 'work-content', body }) {
    if (!LABELS.includes(label)) return { posted: false, reason: 'bad-label' };
    const opened = await openThread({ marker: MARKER_NOTE, channelId, goalId, seatName, label, body });
    if (!opened.posted) return opened;
    log('info', 'owner note posted in a new thread — NO ask record minted [§2.1]', { goalId, seat: seatName, threadTs: opened.threadTs });
    return { posted: true, threadTs: opened.threadTs, openingLine: opened.openingLine, text: opened.text, recorded: null };
  }

  async function nack({ channelId, goalId, askId, text }) {
    return outbox.post({
      kind: 'nack',
      channel_id: channelId,
      thread_ts: askId,
      goal_id: goalId == null ? null : String(goalId),
      ask_id: askId == null ? null : String(askId),
      payload: text,
    });
  }

  function persistReply({ goalId, askId, senderId, text }) {
    if (!workspaceRoot) return { written: false, reason: 'no-workspace-root' };
    const dest = replyCopyPath(workspaceRoot, goalId, askId);
    try {
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, `${String(text)}\n`);
      return { written: true, path: dest, sender: senderId };
    } catch (err) {
      log('warn', 'authorized reply could not be written to disk — the relaunched seat will have the thread only', { goalId, askId, error: err.message });
      return { written: false, reason: err.message };
    }
  }

  // ── §2.4 RELEASE, IN ITS OWN ORDER ──────────────────────────────────────────────────────────
  //
  // `askId` is what the caller believes this thread's ask is. `threadTs` is where the message
  // actually landed. They are compared rather than assumed EQUAL because that comparison IS the
  // release rule: a reply in any other thread releases nothing, silently (§2.4.1).
  //
  // `reap` is the ONE knob, and it exists for exactly one caller: a `reject-and-pause`d APPROVAL
  // thread [T3-R22]. That thread's ask was already released and reaped by the reply that paused
  // it; the later `retry with:` / `approve` / `close` arrive in the SAME thread and must be
  // authorized and parsed by this same door — but must NOT reap a second time, because a second
  // reap is a second relaunch signal on a seat nobody re-asked. With `reap: false` this function
  // is the release rule minus its last act: exact thread, authorized sender, parse, NACK.
  async function release({ goalId, channelId, seatName, askId, threadTs, senderId, text, channelGoal = null, liveGoals = null, reap = true }) {
    // 1a. THE EXACT THREAD. Not "a thread on this seat", not "the newest", not "the oldest".
    if (askId == null || threadTs == null || String(threadTs) !== String(askId)) {
      log('debug', 'reply is not in the ask\'s exact thread — nothing released [§2.4.1]', { goalId, askId, threadTs });
      return { released: false, reason: 'wrong-thread' };
    }
    // 1b + 2. AUTHORIZED SENDER, and never this bot answering itself. Ignored in SILENCE: no
    // parse, no NACK, no state change — a NACK here would let anyone in the channel make the bot
    // talk back, and an unauthorized message is not a malformed answer, it is not an answer.
    const sender = senderId == null ? '' : String(senderId);
    const self = botId();
    if (!sender || (self && sender === self) || !authorized.has(sender)) {
      log('debug', 'reply ignored — sender is not in the instance-config authorized set [§2.4.2]', { goalId, askId, sender });
      return { released: false, reason: 'unauthorized' };
    }
    // 3. PARSE. One grammar for approval and ordinary threads (`reply-grammar.js`, §4).
    const parsed = parseReply(text, { channelGoal, liveGoals });
    if (!parsed.ok) {
      const posted = await nack({ channelId, goalId, askId, text: parsed.nack });
      log('info', 'unrecognized first token — NACK posted in-thread, the ask stays OPEN [§2.4.3]', {
        goalId, askId, nackKind: parsed.nackKind, delivered: posted && posted.delivered === true,
      });
      return { released: false, reason: 'unparsed', nacked: true, nack: parsed.nack };
    }
    // `pause {goal}` / `resume {goal}` are the daemon's mechanical verbs and are NOT ask outcomes
    // (§4.2): they do their own work elsewhere and leave this record exactly as they found it.
    if (parsed.family === 'mechanical') {
      log('info', 'mechanical verb in an ask thread — handled elsewhere, the ask stays OPEN [§4.2]', { goalId, askId, outcome: parsed.outcome });
      return { released: false, reason: 'mechanical', outcome: parsed.outcome, goal: parsed.goal, comments: parsed.comments };
    }
    // 4. RECOGNIZED OUTCOME. `reap: false` stops here (see the header): the outcome is reported
    // to the caller, and the record — already `answered` — is left exactly as it stands.
    if (reap === false) {
      log('info', 'authorized reply parsed in an already-released thread — reported, NOT reaped again [T3-R22]', {
        goalId, seat: seatName, askId, outcome: parsed.outcome,
      });
      return {
        released: false, reason: 'no-reap', parsedOnly: true,
        outcome: parsed.outcome, comments: parsed.comments, family: parsed.family, findings: parsed.findings,
      };
    }
    // The reply goes to disk FIRST — the reap fires the relaunch in the
    // same act (§2.8), so a seat can be reading this file before the reap call has returned.
    const copy = persistReply({ goalId, askId, senderId: sender, text });
    const reaped = await askRecord.reapAsk({ goalId, seat: seatName, chatThreadId: askId });
    log('info', 'authorized reply RELEASED the ask in its own thread — wait reaped and relaunch fired in one act [§2.4.4]', {
      goalId, seat: seatName, askId, outcome: parsed.outcome, reaped: reaped.recorded === true, replyOnDisk: copy.written === true,
    });
    return {
      released: reaped.recorded === true,
      reason: reaped.recorded === true ? null : (reaped.reason || reaped.error || 'reap-refused'),
      outcome: parsed.outcome,
      comments: parsed.comments,
      family: parsed.family,
      findings: parsed.findings,
      reply: copy,
      reaped,
    };
  }

  return { postAsk, postNote, release, openingLine, displaySuffix, isAuthorized: (id) => authorized.has(String(id)) };
}

module.exports = {
  createAskThreads,
  openingLine,
  displaySuffix,
  composeThreadOpener,
  replyCopyPath,
  MARKER_ASK,
  MARKER_NOTE,
  LABELS,
};

'use strict';

// status-line — the ONE standing glance surface (`spec-owner-io.md` §6 [T4-R5, D-6-ruling]).
//
// Exact format, and it is a FORMAT, not a template to elaborate:
//
//     N waiting · oldest Xh · M blocked
//
// ⚠ IT NEVER POSTS. Not a channel message, not a thread reply, not a digest line. It writes the
// BOT'S SLACK STATUS TEXT and nothing else. The whole reason [D-6-ruling] allows a standing surface
// at all is that it costs the owner no notification: a version of this that posted would be the
// per-ask re-ping §5 deleted.
//
// ⚠ IT UPDATES ON SEVEN TRIGGERS AND NO OTHERS. §6 lists them: ask minted, ask answered, ask
// closed, blocked-on-human stamped, blocked-on-human cleared, `pause` succeeded, `resume` succeeded.
// Anything else — a tick, a post, a seat launch, a FAILED pause — is refused here rather than
// silently allowed, because a status text that redraws on every event is a poll loop against Slack.
//
// ⚠ `oldest Xh` IS WHOLE HOURS AND IS `0` WHEN NOTHING IS OPEN. §6's zero case is spelled out:
// `0 waiting · oldest 0h · 0 blocked`. It is a real rendering, not an empty string — the owner
// glancing at the bot must be able to tell "nothing waiting" from "the bot is not running".

// §6, verbatim. A trigger outside this set does not update the status text.
const TRIGGERS = Object.freeze([
  'ask-minted',
  'ask-answered',
  'ask-closed',
  'blocked-on-human-stamp',
  'blocked-on-human-clear',
  'pause-succeeded',
  'resume-succeeded',
]);
const TRIGGER_SET = new Set(TRIGGERS);

function toMs(value) {
  if (value == null) return NaN;
  if (value instanceof Date) return value.getTime();
  if (typeof value === 'number') return value;
  const parsed = Date.parse(String(value));
  return Number.isNaN(parsed) ? NaN : parsed;
}

// Whole hours since the oldest `open` ask's `opened_at`. Floor, never round: an ask 119 minutes old
// is `1h`, and reporting it as `2h` would overstate how long the owner has left someone waiting.
function oldestHours(asks, nowMs) {
  let oldest = null;
  for (const ask of asks) {
    const ms = toMs(ask && ask.opened_at);
    if (!Number.isFinite(ms)) continue;
    if (oldest === null || ms < oldest) oldest = ms;
  }
  if (oldest === null) return 0;
  return Math.max(0, Math.floor((nowMs - oldest) / 3600000));
}

function renderStatusLine({ asks = [], blocked = 0, nowMs = Date.now() } = {}) {
  const n = asks.length;
  const hours = n === 0 ? 0 : oldestHours(asks, nowMs);
  return `${n} waiting · oldest ${hours}h · ${Math.max(0, Number(blocked) || 0)} blocked`;
}

// `readOpenAsks` → [{ opened_at }] for every ask-record in state `open`, ALL goals.
// `readBlockedCount` → lanes stamped `incomplete: blocked-on-human` PLUS goals in stored state
//   `paused`. One number: §6 sums the two and the owner reads one count.
// `setStatusText` → the port that writes the bot's Slack status text. Injected, and unwired it
//   degrades loudly (a log) rather than pretending the owner can see a line nobody set.
function createStatusLine({
  readOpenAsks,
  readBlockedCount = () => 0,
  setStatusText = null,
  now = () => new Date(),
  logger = null,
} = {}) {
  if (typeof readOpenAsks !== 'function') throw new Error('createStatusLine requires readOpenAsks');
  const log = (level, message, fields) => { if (logger) logger({ level, message, ...fields }); };
  let last = null;

  async function render() {
    const asks = (await readOpenAsks()) || [];
    const blocked = (await readBlockedCount()) || 0;
    return renderStatusLine({ asks, blocked, nowMs: now().getTime() });
  }

  // The ONE entry point. `trigger` must be one of TRIGGERS; anything else is refused and the status
  // text is left exactly as it was.
  async function onTrigger(trigger) {
    if (!TRIGGER_SET.has(trigger)) {
      log('debug', 'status line NOT updated — the event is not one of the seven §6 triggers', { trigger });
      return { updated: false, reason: 'not-a-trigger', trigger };
    }
    const text = await render();
    if (typeof setStatusText !== 'function') {
      log('warn', 'status line computed but NO status port is wired — the owner sees no glance surface',
        { trigger, text });
      return { updated: false, reason: 'no-status-port', trigger, text };
    }
    await setStatusText(text);
    last = text;
    return { updated: true, trigger, text };
  }

  return { onTrigger, render, current: () => last, TRIGGERS };
}

module.exports = { createStatusLine, renderStatusLine, oldestHours, TRIGGERS };

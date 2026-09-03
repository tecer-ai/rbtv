'use strict';

// system-digest — the ONE changed-only SYSTEM digest (`spec-owner-io.md` §5 [T5-R13, C-12]).
//
// THERE IS EXACTLY ONE DIGEST AND IT IS SYSTEM-WIDE. No per-goal digest, no per-ask re-ping: the
// owner's phone-glance surface is this post plus the standing status line (`status-line.js` §6).
// A goal channel's top level carries asks, alarms and big lifecycle events [T5-R11, CF-9] — a
// second, per-goal digest would be the re-ping the baseline deleted.
//
// ⚠ CHANGED IS MEASURED AGAINST THE LAST *DELIVERED* PAYLOAD, NEVER AGAINST THE LAST ATTEMPT. The
// outbox (§7 / C-17) mints a record `pending-delivery` and flips it to `delivered` only on Slack's
// own ack, so a post Slack never acked did NOT reach the owner. Advancing the baseline on the
// attempt would silence the next slot and the owner would never see the change at all. The
// baseline therefore moves ONLY on `delivered === true`, and it is PERSISTED — a daemon restart
// between two slots must not re-post an unchanged digest, which is the whole point of §5.
//
// ⚠ AGE IS RENDERED BUT IS NOT PART OF THE SNAPSHOT. §5 pins the snapshot to
// `(open ask ids + one_liners + open condition signatures)`. Age ticks every minute; if it entered
// the snapshot the digest would post at every one of the ten slots and "changed-only" would mean
// nothing.
//
// ⚠ THE ALARM CONDITIONS ARE READ, NEVER EMITTED. The alarm-signature registry and its emitter are
// impl-alarms' (`spec-owner-io.md` §9, component `ignite/observation/`). This module holds a READER
// port and nothing else: with no registry wired it reads an EMPTY set and the digest still renders
// its ask rows. No stand-in registry lives here.

const fs = require('node:fs');
const path = require('node:path');

const { displaySuffix } = require('./ask-thread');
const { FALLBACK_MARK } = require('./bus-ferry');

// §5: every 2 hours at 06:00…22:00 plus the 24:00 slot (which IS 00:00 of the next day).
// 00:00–06:00 carries no other check — the four missing even hours (02, 04) are the deliberate
// quiet window, so the set is written out rather than computed from a step.
const SLOT_HOURS = Object.freeze([0, 6, 8, 10, 12, 14, 16, 18, 20, 22]);
const SLOT_SET = new Set(SLOT_HOURS);
const DIGEST_TZ = 'America/Sao_Paulo';

const HOUR_FMT = new Intl.DateTimeFormat('en-US', {
  timeZone: DIGEST_TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

// The wall-clock hour and minute AT the digest's timezone. The daemon's own clock may be UTC and
// the ten slots are owner-facing local times — resolving this any other way (a fixed offset) breaks
// twice a year on a DST edge.
function localHourMinute(at) {
  const parts = HOUR_FMT.formatToParts(at);
  const get = (type) => Number(parts.find((p) => p.type === type).value);
  return { hour: get('hour'), minute: get('minute') };
}

function isSlot(at) {
  const { hour, minute } = localHourMinute(at);
  return minute === 0 && SLOT_SET.has(hour);
}

function slotLabel(at) {
  const { hour } = localHourMinute(at);
  return `${String(hour).padStart(2, '0')}:00`;
}

// Whole minutes under an hour, whole hours above it — matching the §5 example's `40m` and `3h`.
// Anything absent renders nothing rather than a fabricated `0m`.
function renderAge(sinceMs, nowMs) {
  if (!Number.isFinite(sinceMs) || !Number.isFinite(nowMs)) return null;
  const mins = Math.max(0, Math.floor((nowMs - sinceMs) / 60000));
  return mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h`;
}

// A goal's Slack channel, permalinked from its `channel_id` alone — a condition carries no thread
// timestamp, so this is deliberately a CHANNEL link, never a thread permalink (that would be
// fabricated). `forward-path.js#slackThreadPermalink` is the thread-scoped sibling; not reused here
// because it requires a `thread_ts` this row does not have.
function slackChannelLink(channelId) {
  return `https://slack.com/archives/${channelId}`;
}

// A goal-scoped condition (frozen-goal, today) leads with its goal, linked to that goal's channel —
// the owner can tell WHERE without opening it. A machine-level condition (the watchdog family) has
// no goal at all: it leads with its own `subject` instead, and keeps `evidence_pointer` inline since
// there is no tap target to reach it through (`d-digest-ui` 5(b)).
function renderConditionRow(cond, nowMs) {
  const hasGoal = cond.goal_id != null && String(cond.goal_id) !== '';
  const link = hasGoal && cond.channel_id ? slackChannelLink(cond.channel_id) : null;
  const lead = link ? `<${link}|*${cond.goal_id}*>` : cond.subject;
  return joinRow([
    lead,
    cond.condition,
    renderAge(toMs(cond.first_emitted_at), nowMs),
    link ? null : cond.evidence_pointer,
  ]);
}

function toMs(value) {
  if (value == null) return NaN;
  if (value instanceof Date) return value.getTime();
  if (typeof value === 'number') return value;
  const parsed = Date.parse(String(value));
  return Number.isNaN(parsed) ? NaN : parsed;
}

function joinRow(fields) {
  return `• ${fields.filter((f) => f != null && String(f) !== '').join(' · ')}`;
}

// R-A2 (`digest-sentence`): one plain sentence per open ask, the goal name itself as the tap
// target — no LANE, no seat token, no `ref` id in the visible line. The goal leads so the owner
// can tell whose ask this is without opening it; `ask.goal` is absent on no row today
// (`ask-record.js#listOpenAsks` / `exhaustion.js#listOpenGroupedAsks` both carry it), but a row is
// never left anonymous: with no goal, the thread-id suffix fills the lead position instead — the
// one unavoidable fallback, never rendered when a goal name is available. `subject` is the
// composer-authored plain sentence (`ask-shape`'s new field on the `listOpenAsks` row); its
// absence (empty string on a pre-existing row, per the interface contract) falls back to
// `one_liner`, the machine text this row used to be built from entirely.
function renderAskRow(ask, nowMs) {
  const hasGoal = ask.goal != null && String(ask.goal) !== '';
  const idSuffix = displaySuffix(ask.id);
  const leadText = hasGoal ? String(ask.goal) : idSuffix;
  const lead = ask.link ? `<${ask.link}|${leadText}>` : leadText;
  const sentence = ask.subject || ask.one_liner || '';
  const age = renderAge(toMs(ask.opened_at), nowMs);
  return `• ${lead} — ${sentence}${age ? ` · waiting ${age}` : ''}`;
}

// `d-ask15-blocking-asks-first`: a seat that stopped and is WAITING on the owner must read above a
// seat that already asked, got no answer, picked its declared default and carried on. NO STRUCTURAL
// FIELD carries that distinction — checked against the schema, not assumed: `open_asks`
// (`state-store/tables.sql`) columns are `ask_id, goal, seat, label, state, posted, posted_at,
// authorized_reply_at, evidence_pointer`; `label` is the CHECK-constrained `work-content|recovery`
// pair (D-7-ruling) and is orthogonal to blocking-vs-default. `ask-record.js#listOpenAsks` (the row
// shape both `readOpenAsks` callers — `chat/ask-store.js` over the gateway and a direct bind — hand
// back) maps only `{ id, goal, seat, label, one_liner, opened_at, evidence_pointer }`; there is no
// `arm` column anywhere on the row. The only place the distinction is computed at all is
// `bus-ferry.js`'s per-pass `fallbackArm`, and it is discarded after formatting the posted message —
// never written back to `open_asks`. So the sort key here is the WEAKEST available one, exactly as
// flagged: whether the ask's rendered `one_liner` (the first line of its corpus, which is
// `formatMessage`'s own header) carries the `default-and-disclose` mark bus-ferry already renders.
// Importing `FALLBACK_MARK` rather than re-typing the string keeps the one spelling of the marker in
// the one place bus-ferry defines it.
const DEFAULT_DISCLOSE_MARK = FALLBACK_MARK['default-and-disclose'].trim();

function isInformationalAsk(ask) {
  const text = ask && ask.one_liner;
  return typeof text === 'string' && text.includes(DEFAULT_DISCLOSE_MARK);
}

// Stable partition, NOT `Array#sort`: two plain passes preserve each group's arrival order by
// construction, with no dependence on a sort implementation's stability guarantee. Blocking asks
// (no `proceeding on its default` mark — the seat is still waiting) lead; informational asks (the
// mark is present — the seat already proceeded) follow, in the order `readOpenAsks` returned them.
function sortAsksBlockingFirst(asks) {
  const blocking = [];
  const informational = [];
  for (const ask of asks) {
    (isInformationalAsk(ask) ? informational : blocking).push(ask);
  }
  return [...blocking, ...informational];
}

// §5's snapshot, and ONLY §5's snapshot. Sorted so a reader returning the same set in a different
// order is not mistaken for a change.
//
// ⚠ `digest-sentence`: the text input is `subject || one_liner`, matching what the row now
// renders (`renderAskRow`) — a pre-existing ask carries `subject: ''` (the interface contract's
// own fallback), so its snapshot text is unchanged until a composer gives it a real subject. Link,
// age and goal name stay OUT of the snapshot on purpose (the standing trap this module's header
// comment states): none of those three may retrigger a post on their own.
function snapshotOf(asks, conditions) {
  return JSON.stringify({
    asks: asks
      .map((a) => [String(a.id), String((a.subject || a.one_liner) == null ? '' : (a.subject || a.one_liner))])
      .sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0)),
    conditions: conditions.map((c) => String(c.signature)).sort(),
  });
}

function renderDigest({ at, asks, conditions, nowMs }) {
  const lines = [`*System digest · ${slotLabel(at)}*`];

  lines.push('');
  if (asks.length === 0) {
    lines.push('Nothing is waiting on you.');
  } else {
    lines.push(`Waiting on you (${asks.length}):`);
    for (const ask of sortAsksBlockingFirst(asks)) {
      lines.push(renderAskRow(ask, nowMs));
    }
  }

  lines.push('', 'Open conditions');
  if (conditions.length === 0) {
    lines.push('• none open');
  } else {
    for (const cond of conditions) {
      lines.push(renderConditionRow(cond, nowMs));
    }
  }

  return lines.join('\n');
}

function loadBaseline(statePath) {
  if (!statePath) return null;
  try {
    const doc = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    return doc && typeof doc.snapshot === 'string' ? doc.snapshot : null;
  } catch {
    return null;
  }
}

function saveBaseline(statePath, snapshot, deliveredAt) {
  if (!statePath) return;
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  const tmp = `${statePath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify({ version: 1, snapshot, delivered_at: deliveredAt }, null, 2)}\n`);
  fs.renameSync(tmp, statePath);
}

// `readOpenAsks` → [{ id, seat, one_liner, opened_at, link?, evidence_pointer? }]
// `readOpenConditions` → [{ signature, condition, subject, first_emitted_at, evidence_pointer,
//   goal_id, channel_id }] — the alarm-signature registry's published READ interface
//   (`observation/emitter.js#readOpenConditions`). `goal_id`/`channel_id` are `null` on a
//   machine-level condition (the watchdog never supplies a goal) — never fabricated here.
//   Absent reader → the default empty reader.
// `post` → the outbox's `post` (kind is stamped here, never by the caller).
function createSystemDigest({
  post,
  systemChannelId,
  readOpenAsks,
  readOpenConditions = () => [],
  statePath = null,
  now = () => new Date(),
  logger = null,
} = {}) {
  if (typeof post !== 'function') throw new Error('createSystemDigest requires post');
  if (!systemChannelId) throw new Error('createSystemDigest requires systemChannelId');
  if (typeof readOpenAsks !== 'function') throw new Error('createSystemDigest requires readOpenAsks');
  const log = (level, message, fields) => { if (logger) logger({ level, message, ...fields }); };

  let baseline = loadBaseline(statePath);

  // The 2-hourly check. Returns what it decided so a caller (and a probe) can see WHY nothing was
  // posted — "posted nothing" and "was not a slot" are different facts and must not collapse.
  async function check(when = null) {
    const at = when || now();
    if (!isSlot(at)) return { ran: false, reason: 'not-a-slot', posted: false };

    const asks = (await readOpenAsks()) || [];
    const conditions = (await readOpenConditions()) || [];
    const snapshot = snapshotOf(asks, conditions);
    if (snapshot === baseline) {
      log('info', 'system digest slot: snapshot unchanged since the last DELIVERED digest — posting nothing',
        { slot: slotLabel(at) });
      return { ran: true, reason: 'unchanged', posted: false, snapshot };
    }

    const payload = renderDigest({ at, asks, conditions, nowMs: at.getTime() });
    const result = await post({
      kind: 'digest', channel_id: systemChannelId, thread_ts: null, goal_id: null, ask_id: null, payload,
    });
    if (result && result.delivered) {
      baseline = snapshot;
      saveBaseline(statePath, snapshot, at.toISOString());
      return { ran: true, reason: 'changed', posted: true, delivered: true, snapshot, payload, outbox_id: result.outbox_id };
    }
    // Not acked: the record stays `pending-delivery` in the outbox and the baseline does NOT move,
    // so the next slot re-offers the same change instead of the owner losing it.
    log('warn', 'system digest was NOT acked by Slack — the baseline stays put and the next slot retries',
      { slot: slotLabel(at), error: result && result.error });
    return { ran: true, reason: 'changed', posted: true, delivered: false, snapshot: baseline, payload, outbox_id: result && result.outbox_id };
  }

  return { check, isSlot, render: (opts) => renderDigest(opts), snapshotOf, lastDelivered: () => baseline };
}

module.exports = {
  createSystemDigest,
  isSlot,
  slotLabel,
  renderAge,
  snapshotOf,
  renderDigest,
  sortAsksBlockingFirst,
  isInformationalAsk,
  SLOT_HOURS,
  DIGEST_TZ,
};

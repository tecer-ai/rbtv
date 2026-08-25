'use strict';

// -- THE ONE ALARM EMITTER [T4-R10, spec-owner-io §9] -------------------------------------------
//
// WHAT WAS BROKEN. Alarms were composed at whatever call site noticed the condition. The frozen-goal
// pager (`server/ticker/goal-stall-alarm.js`, deleted 2026-08-24 by del-observers) is the worked
// example: it built its own Slack text, carried its own dedup in a process-lifetime `Map`, and had
// no schema at all - so an alarm could reach the owner reading `frozen: undefined` and stand there
// for 13 hours (memory `engine/20260823-i-frozen-alarm-said-undefined-fo.md`), and a daemon restart
// wiped the dedup and re-paged everything it had already paged.
//
// THE RULE. ONE emitter. Four fields are REQUIRED and absence is the EMITTING CODE'S bug - this
// module throws rather than post a fragment, so the failure lands in a test or a log at the call
// site instead of on the owner's phone. The dedup key (`signature`) and its state live in a
// PERSISTED registry, not in memory: that is the half of the deleted module's design that carries
// over, and the half that does not.
//
// WHAT THIS MODULE IS NOT. It decides no conditions. It observes nothing. Every caller - the frozen
// scheduler invariant next door, the watchdog, anything later - hands in a finished observation and
// is an ordinary caller of `emit`. It is also not a wake: an alarm is one-way and never counts as
// unread work for a seat, a master or a leader [T4-R10], which is why nothing here writes mail,
// enqueues, or touches the owed set.

const fs = require('node:fs');
const path = require('node:path');

// spec-owner-io §9.1. `what_would_clear_it` accepts the explicit string `unknown`; what it does NOT
// accept is absence - "nobody wrote down what would clear this" and "we looked and do not know" are
// different facts and the owner can only act on the second when it is said out loud.
const REQUIRED_FIELDS = Object.freeze([
  'condition',
  'subject',
  'evidence_pointer',
  'what_would_clear_it',
]);

const UNKNOWN = 'unknown';
const OPEN = 'open';
const CLEARED = 'cleared';

// Runtime state, never repo state (root CLAUDE.md § ignite/ rule 3). Same shape as the outbox's own
// store path so an operator finds both halves of "what did the daemon try to tell me" in one folder.
function alarmRegistryPath(workspaceRoot) {
  if (!workspaceRoot) throw new Error('alarmRegistryPath requires workspaceRoot');
  return path.resolve(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'alarm-registry.json');
}

function plainWords(value) {
  return typeof value === 'string' && value.trim() !== '';
}

// -- THE SCHEMA GATE ---------------------------------------------------------------------------
//
// Throws. Deliberately, and at the emitting call site rather than at the Slack boundary: a partial
// alarm that reached Slack would be indistinguishable from a real one to the owner, while a throw is
// a stack trace pointing at the line that failed to say what it observed.
function validateAlarm(input) {
  if (!input || typeof input !== 'object') throw new Error('alarm requires an object');
  const missing = REQUIRED_FIELDS.filter((f) => input[f] === undefined || input[f] === null || input[f] === '');
  if (missing.length > 0) {
    throw new Error(`alarm is missing required field(s): ${missing.join(', ')} — the emitting code is the bug [T4-R10]`);
  }
  if (!plainWords(input.condition)) {
    throw new Error('alarm `condition` must be plain words, never empty and never a bare code token');
  }
  const subject = input.subject;
  if (!subject || typeof subject !== 'object' || !plainWords(subject.type) || !plainWords(subject.id)) {
    throw new Error('alarm `subject` must be a concrete { type, id } — a goal, seat or lane');
  }
  if (!plainWords(input.evidence_pointer)) {
    throw new Error('alarm `evidence_pointer` must be a path or query key a human can open');
  }
  if (!plainWords(input.what_would_clear_it)) {
    throw new Error(`alarm \`what_would_clear_it\` must be plain words, or the explicit value \`${UNKNOWN}\``);
  }
  if (!plainWords(input.signature_class)) {
    throw new Error('alarm `signature_class` must name the condition class the signature keys on');
  }
  // Not one of the spec's four, and required all the same: §1/§9 exempt a system-health alarm from
  // waiting on the 2-hourly digest, and a caller that never states which kind it is has left that
  // exemption to be guessed. An explicit `false` is a fine answer; silence is not.
  if (typeof input.immediate !== 'boolean') {
    throw new Error('alarm `immediate` must be an explicit boolean: true for system-health (digest-exempt), false otherwise [CF-9]');
  }
  return true;
}

// condition-class + subject, and nothing else. NOT the condition text: the text is what CHANGED
// detection compares, so folding it into the key would mint a new row on every reworded observation
// and dedup would silently stop deduping.
function signatureOf({ signature_class: signatureClass, subject }) {
  return `${signatureClass}:${subject.type}:${subject.id}`;
}

function loadRows(storePath) {
  if (!storePath) return [];
  try {
    const parsed = JSON.parse(fs.readFileSync(storePath, 'utf8'));
    if (!parsed || !Array.isArray(parsed.rows)) return [];
    return parsed.rows.filter((r) => r && typeof r === 'object' && r.signature);
  } catch {
    return [];
  }
}

function saveRows(storePath, rows) {
  if (!storePath) return;
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  const tmp = `${storePath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify({ version: 1, rows }, null, 2)}\n`);
  fs.renameSync(tmp, storePath);
}

// The owner-facing body. One block, plain words, and every required field visible - the point of the
// schema is that the owner never receives an alarm missing one of them, so all four are printed.
function renderAlarm(row) {
  return [
    `Alarm · ${row.subject.type} ${row.subject.id}`,
    '',
    row.condition,
    '',
    `Evidence: ${row.evidence_pointer}`,
    `Clears when: ${row.what_would_clear_it}`,
  ].join('\n');
}

// `post` is the outbox's own `post` (`bridges/chat/outbox.js`) - the durable one, so a bridge outage
// leaves a `pending-delivery` record rather than a lost alarm [C-17]. `kind` is stamped here and
// never by the caller.
function createAlarmEmitter({ storePath = null, post, systemChannelId = null, now = null } = {}) {
  if (typeof post !== 'function') throw new Error('createAlarmEmitter requires post');
  const clock = now || (() => new Date().toISOString());
  let rows = loadRows(storePath);

  function openRow(signature) {
    return rows.find((r) => r.signature === signature && r.state === OPEN) || null;
  }

  // Returns WHY it did or did not post. "deduped" and "delivery failed" are different facts and a
  // caller that cannot tell them apart cannot be debugged.
  async function emit(input) {
    validateAlarm(input);
    const at = clock();
    const signature = signatureOf(input);
    const existing = openRow(signature);
    const repeatEveryMs = Number(input.repeat_every_ms) > 0 ? Number(input.repeat_every_ms) : null;

    if (existing) {
      const conditionChanged = existing.condition !== input.condition;
      const dueForRepeat = repeatEveryMs !== null
        && Date.parse(at) - Date.parse(existing.last_emitted_at) >= repeatEveryMs;
      if (!conditionChanged && !dueForRepeat) {
        return { posted: false, reason: 'deduped', signature, row: { ...existing } };
      }
      existing.condition = input.condition;
      existing.evidence_pointer = input.evidence_pointer;
      existing.what_would_clear_it = input.what_would_clear_it;
      existing.last_emitted_at = at;
      existing.emission_count += 1;
      saveRows(storePath, rows);
      const result = await post({
        kind: 'alarm',
        channel_id: existing.channel_id,
        thread_ts: null,
        goal_id: existing.goal_id,
        ask_id: null,
        payload: renderAlarm(existing),
      });
      return {
        posted: true,
        reason: conditionChanged ? 'condition-changed' : 'repeat',
        signature,
        row: { ...existing },
        outbox_id: result && result.outbox_id,
        delivered: Boolean(result && result.delivered),
      };
    }

    const channelId = input.channel_id || systemChannelId;
    if (!channelId) throw new Error('alarm requires channel_id (or an emitter systemChannelId)');
    const row = {
      signature,
      signature_class: input.signature_class,
      state: OPEN,
      condition: input.condition,
      subject: { type: input.subject.type, id: input.subject.id },
      evidence_pointer: input.evidence_pointer,
      what_would_clear_it: input.what_would_clear_it,
      immediate: input.immediate,
      channel_id: String(channelId),
      goal_id: input.goal_id == null ? null : String(input.goal_id),
      first_emitted_at: at,
      last_emitted_at: at,
      cleared_at: null,
      emission_count: 1,
    };
    rows.push(row);
    saveRows(storePath, rows);
    const result = await post({
      kind: 'alarm',
      channel_id: row.channel_id,
      thread_ts: null,
      goal_id: row.goal_id,
      ask_id: null,
      payload: renderAlarm(row),
    });
    return {
      posted: true,
      reason: 'first',
      signature,
      row: { ...row },
      outbox_id: result && result.outbox_id,
      delivered: Boolean(result && result.delivered),
    };
  }

  // Clearing is silent by design: the owner is told a condition EXISTS, never that one of a hundred
  // transient observations went away. The digest simply stops carrying the row.
  function clear(signature) {
    const row = openRow(signature);
    if (!row) return { cleared: false, signature };
    row.state = CLEARED;
    row.cleared_at = clock();
    saveRows(storePath, rows);
    return { cleared: true, signature, row: { ...row } };
  }

  // -- THE PUBLISHED READ INTERFACE ------------------------------------------------------------
  //
  // This exact shape is what `bridges/chat/system-digest.js` documents as `readOpenConditions` and
  // renders under "Open conditions". `subject` flattens to the bare id there because the digest row
  // already reads as a sentence; the full `{ type, id }` stays on the registry row for anyone else.
  function readOpenConditions() {
    return rows
      .filter((r) => r.state === OPEN)
      .sort((a, b) => (a.first_emitted_at < b.first_emitted_at ? -1 : 1))
      .map((r) => ({
        signature: r.signature,
        condition: r.condition,
        subject: r.subject.id,
        first_emitted_at: r.first_emitted_at,
        evidence_pointer: r.evidence_pointer,
      }));
  }

  function reload() {
    rows = loadRows(storePath);
  }

  return { emit, clear, readOpenConditions, reload };
}

module.exports = {
  REQUIRED_FIELDS,
  UNKNOWN,
  OPEN,
  CLEARED,
  alarmRegistryPath,
  validateAlarm,
  signatureOf,
  renderAlarm,
  createAlarmEmitter,
};

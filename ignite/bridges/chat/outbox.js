'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const KINDS = Object.freeze(['ask', 'alarm', 'digest', 'completion', 'nack', 'closing', 'notification']);
const STATES = Object.freeze(['pending-delivery', 'delivered']);
const KIND_SET = new Set(KINDS);
const STATE_SET = new Set(STATES);

function outboxStorePath(workspaceRoot) {
  if (!workspaceRoot) throw new Error('outboxStorePath requires workspaceRoot');
  return path.resolve(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'outbox.json');
}

function nowIso(clock) {
  return (clock || (() => new Date().toISOString()))();
}

function cloneRecord(row) {
  return {
    outbox_id: row.outbox_id,
    kind: row.kind,
    state: row.state,
    channel_id: row.channel_id,
    thread_ts: row.thread_ts,
    goal_id: row.goal_id,
    ask_id: row.ask_id,
    payload: row.payload,
    created_at: row.created_at,
    delivered_at: row.delivered_at,
    slack_ts: row.slack_ts,
    last_error: row.last_error,
    attempt_count: row.attempt_count,
  };
}

function samePendingKey(row, fields) {
  return row.state === 'pending-delivery'
    && row.kind === fields.kind
    && row.channel_id === fields.channel_id
    && row.thread_ts === fields.thread_ts
    && row.goal_id === fields.goal_id
    && row.ask_id === fields.ask_id
    && row.payload === fields.payload;
}

function loadRecords(storePath) {
  if (!storePath) return [];
  try {
    const raw = fs.readFileSync(storePath, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.records)) return [];
    return parsed.records.filter((r) => r && typeof r === 'object' && r.outbox_id);
  } catch {
    return [];
  }
}

function persistRecords(storePath, records) {
  if (!storePath) return;
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  const tmp = `${storePath}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tmp, `${JSON.stringify({ version: 1, records }, null, 2)}\n`);
  fs.renameSync(tmp, storePath);
}

function newestFirst(a, b) {
  if (a.created_at > b.created_at) return -1;
  if (a.created_at < b.created_at) return 1;
  return a.outbox_id < b.outbox_id ? 1 : a.outbox_id > b.outbox_id ? -1 : 0;
}

function createOutbox({ storePath = null, send, now = null } = {}) {
  if (typeof send !== 'function') throw new Error('createOutbox requires send');
  const clock = now || (() => new Date().toISOString());
  let records = loadRecords(storePath);

  function save() {
    persistRecords(storePath, records);
  }

  function get(outbox_id) {
    if (outbox_id == null) return null;
    const row = records.find((r) => r.outbox_id === String(outbox_id));
    return row ? cloneRecord(row) : null;
  }

  function query(filters = {}) {
    const state = filters.state;
    const kind = filters.kind;
    const channel_id = filters.channel_id;
    const goal_id = filters.goal_id;
    const ask_id = filters.ask_id;
    if (state != null && !STATE_SET.has(state)) throw new Error(`invalid outbox state: ${state}`);
    if (kind != null && !KIND_SET.has(kind)) throw new Error(`invalid outbox kind: ${kind}`);
    return records
      .filter((r) => (state == null || r.state === state)
        && (kind == null || r.kind === kind)
        && (channel_id == null || r.channel_id === channel_id)
        && (goal_id == null || r.goal_id === goal_id)
        && (ask_id == null || r.ask_id === ask_id))
      .slice()
      .sort(newestFirst)
      .map(cloneRecord);
  }

  function mint(fields) {
    const row = {
      outbox_id: `ob-${crypto.randomUUID()}`,
      kind: fields.kind,
      state: 'pending-delivery',
      channel_id: fields.channel_id,
      thread_ts: fields.thread_ts,
      goal_id: fields.goal_id,
      ask_id: fields.ask_id,
      payload: fields.payload,
      created_at: nowIso(clock),
      delivered_at: null,
      slack_ts: null,
      last_error: null,
      attempt_count: 0,
    };
    records.push(row);
    save();
    return row;
  }

  async function deliver(row) {
    row.attempt_count += 1;
    save();
    let result;
    try {
      result = await send({
        channel: row.channel_id,
        threadTs: row.thread_ts,
        text: row.payload,
      });
    } catch (err) {
      row.last_error = err && err.message ? String(err.message) : String(err);
      row.state = 'pending-delivery';
      save();
      return { delivered: false, ts: null, error: row.last_error, outbox_id: row.outbox_id };
    }
    if (result && result.delivered) {
      row.state = 'delivered';
      row.slack_ts = result.ts != null ? String(result.ts) : null;
      row.delivered_at = nowIso(clock);
      row.last_error = null;
      save();
      return { delivered: true, ts: row.slack_ts, error: null, outbox_id: row.outbox_id };
    }
    const error = (result && (result.error || result.reason)) || 'not-acked';
    row.last_error = String(error);
    row.state = 'pending-delivery';
    save();
    return { delivered: false, ts: null, error: row.last_error, outbox_id: row.outbox_id };
  }

  async function post(input = {}) {
    if (input.outbox_id != null) {
      const row = records.find((r) => r.outbox_id === String(input.outbox_id));
      if (!row) throw new Error(`outbox record not found: ${input.outbox_id}`);
      return deliver(row);
    }
    const kind = input.kind;
    if (!KIND_SET.has(kind)) throw new Error(`invalid outbox kind: ${kind}`);
    const channel_id = input.channel_id;
    if (channel_id == null || String(channel_id) === '') throw new Error('channel_id is required');
    const payload = input.payload;
    if (payload == null) throw new Error('payload is required');
    const fields = {
      kind,
      channel_id: String(channel_id),
      thread_ts: input.thread_ts == null ? null : String(input.thread_ts),
      goal_id: input.goal_id == null ? null : String(input.goal_id),
      ask_id: input.ask_id == null ? null : String(input.ask_id),
      payload: String(payload),
    };
    const pending = records.filter((r) => samePendingKey(r, fields)).sort(newestFirst);
    return deliver(pending[0] || mint(fields));
  }

  return { post, query, get };
}

module.exports = {
  KINDS,
  STATES,
  outboxStorePath,
  createOutbox,
};

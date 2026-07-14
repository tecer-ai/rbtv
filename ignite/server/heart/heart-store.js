'use strict';

const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const path = require('node:path');
const {
  HeartStoreError,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
} = require('./errors');

const SCHEMA_SQL = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');

const ACTION_TYPES = new Set(['launch-agent', 'fire-tool', 'start-workflow', 'send-message']);
const MESSAGE_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note']);
const SESSION_MODES = new Set(['headless', 'headed']);
const TRIGGER_KINDS = new Set(['scheduled', 'periodic']);
const VALID_PRIMITIVE_TYPES = new Set(['string', 'integer', 'number', 'boolean', 'object', 'array']);

let singleton = null;

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function toIsoUtc(d) {
  if (!(d instanceof Date)) d = new Date(d);
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function parseIsoUtc(s) {
  if (typeof s !== 'string') return null;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s)) return null;
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

function validateArgs(args, schemaJson, actionType) {
  let parsed;
  try {
    parsed = JSON.parse(args);
  } catch {
    throw new HeartStoreError(E_BAD_ARGS, 'args is not valid JSON', { field: 'args' });
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args must be a JSON object', { field: 'args' });
  }

  let schema;
  try {
    schema = JSON.parse(schemaJson);
  } catch {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema is not valid JSON', { field: 'args_schema' });
  }
  if (schema === null || typeof schema !== 'object' || Array.isArray(schema)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema must be a JSON object', { field: 'args_schema' });
  }

  const required = schema.required || {};
  const optional = schema.optional || {};
  if (typeof required !== 'object' || Array.isArray(required) || typeof optional !== 'object' || Array.isArray(optional)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema.required and args_schema.optional must be objects', { field: 'args_schema' });
  }

  for (const key of Object.keys(required)) {
    if (!(key in parsed)) {
      throw new HeartStoreError(E_BAD_ARGS, `missing required argument: ${key}`, { field: key });
    }
  }
  for (const key of Object.keys(parsed)) {
    if (!(key in required) && !(key in optional)) {
      throw new HeartStoreError(E_BAD_ARGS, `unknown argument: ${key}`, { field: key });
    }
    const expectedType = required[key] || optional[key];
    if (!VALID_PRIMITIVE_TYPES.has(expectedType)) {
      throw new HeartStoreError(E_BAD_ARGS, `unknown expected type for ${key}: ${expectedType}`, { field: key });
    }
    const value = parsed[key];
    let actualType = typeof value;
    if (Array.isArray(value)) actualType = 'array';
    if (value === null) actualType = 'null';
    if (actualType === 'number' && Number.isInteger(value)) actualType = 'integer';
    if (actualType !== expectedType && !(actualType === 'integer' && expectedType === 'number')) {
      throw new HeartStoreError(E_BAD_ARGS, `argument ${key} expected ${expectedType}, got ${actualType}`, { field: key, expected: expectedType, actual: actualType });
    }
  }

  if (actionType === 'launch-agent') {
    if (typeof parsed.profile !== 'string' || parsed.profile.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'launch-agent requires a non-empty profile argument', { field: 'profile' });
    }
  } else if (actionType === 'fire-tool') {
    if (typeof parsed.tool !== 'string' || parsed.tool.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'fire-tool requires a non-empty tool argument', { field: 'tool' });
    }
  } else if (actionType === 'start-workflow') {
    if (typeof parsed.workflow !== 'string' || parsed.workflow.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'start-workflow requires a non-empty workflow argument', { field: 'workflow' });
    }
  } else if (actionType === 'send-message') {
    if (typeof parsed.type !== 'string' || !MESSAGE_TYPES.has(parsed.type)) {
      throw new HeartStoreError(E_BAD_ARGS, 'send-message requires a valid CMP-8 type', { field: 'type' });
    }
    if (typeof parsed.thread !== 'string' || parsed.thread.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'send-message requires a non-empty thread', { field: 'thread' });
    }
    if (typeof parsed.corpus !== 'string') {
      throw new HeartStoreError(E_BAD_ARGS, 'send-message requires a corpus string', { field: 'corpus' });
    }
  }
}

function validateTrigger(req) {
  if (!TRIGGER_KINDS.has(req.triggerKind)) {
    throw new HeartStoreError(E_BAD_TRIGGER, `invalid trigger_kind: ${req.triggerKind}`, { field: 'triggerKind' });
  }
  const runAt = parseIsoUtc(req.runAt);
  if (runAt === null) {
    throw new HeartStoreError(E_BAD_TRIGGER, 'run_at must be fixed-width ISO-8601 UTC', { field: 'runAt' });
  }
  if (req.triggerKind === 'scheduled') {
    if (req.repeatRule !== null && req.repeatRule !== undefined) {
      parseCron(req.repeatRule);
    }
  } else if (req.triggerKind === 'periodic') {
    if (!Number.isInteger(req.intervalSeconds) || req.intervalSeconds <= 0) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'periodic trigger requires a positive interval_seconds', { field: 'intervalSeconds' });
    }
    if (req.repeatRule !== null && req.repeatRule !== undefined) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'periodic trigger must not have a repeat_rule', { field: 'repeatRule' });
    }
  }
  if (req.maxFires !== null && req.maxFires !== undefined) {
    if (!Number.isInteger(req.maxFires) || req.maxFires <= 0) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'max_fires must be a positive integer', { field: 'maxFires' });
    }
    if (req.triggerKind !== 'periodic' && (req.repeatRule === null || req.repeatRule === undefined)) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'max_fires requires a repeating trigger', { field: 'maxFires' });
    }
  }
}

function parseCronField(field, min, max) {
  const values = new Set();
  for (const part of field.split(',')) {
    if (part === '*') {
      for (let i = min; i <= max; i++) values.add(i);
    } else if (part.includes('/')) {
      const [range, step] = part.split('/');
      const stepNum = parseInt(step, 10);
      if (!Number.isInteger(stepNum) || stepNum <= 0) throw new Error('invalid step');
      let start = min;
      let end = max;
      if (range !== '*') {
        if (range.includes('-')) {
          [start, end] = range.split('-').map(x => parseInt(x, 10));
        } else {
          start = end = parseInt(range, 10);
        }
      }
      if (!Number.isInteger(start) || !Number.isInteger(end)) throw new Error('invalid range');
      for (let i = start; i <= end; i += stepNum) values.add(i);
    } else if (part.includes('-')) {
      const [start, end] = part.split('-').map(x => parseInt(x, 10));
      if (!Number.isInteger(start) || !Number.isInteger(end)) throw new Error('invalid range');
      for (let i = start; i <= end; i++) values.add(i);
    } else {
      const n = parseInt(part, 10);
      if (!Number.isInteger(n)) throw new Error('invalid number');
      values.add(n);
    }
  }
  for (const v of values) {
    if (v < min || v > max) throw new Error('value out of range');
  }
  return Array.from(values).sort((a, b) => a - b);
}

function parseCron(expr) {
  if (typeof expr !== 'string' || expr.trim().length === 0) throw new Error('empty cron');
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) throw new Error('cron must have 5 fields');
  const minute = parseCronField(parts[0], 0, 59);
  const hour = parseCronField(parts[1], 0, 23);
  const dayOfMonth = parseCronField(parts[2], 1, 31);
  const month = parseCronField(parts[3], 1, 12);
  let dayOfWeek = parseCronField(parts[4], 0, 7).map(v => v === 7 ? 0 : v);
  dayOfWeek = Array.from(new Set(dayOfWeek)).sort((a, b) => a - b);
  return { minute, hour, dayOfMonth, month, dayOfWeek };
}

function nextCronUtc(after, expr) {
  const cron = parseCron(expr);
  let cursor = new Date(after);
  cursor.setUTCSeconds(0, 0);
  cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);

  for (let safety = 0; safety < 366 * 24 * 60 + 10; safety++) {
    const m = cursor.getUTCMinutes();
    const h = cursor.getUTCHours();
    const dom = cursor.getUTCDate();
    const mon = cursor.getUTCMonth() + 1;
    const dow = cursor.getUTCDay();

    if (!cron.minute.includes(m) || !cron.hour.includes(h) || !cron.month.includes(mon)) {
      cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);
      continue;
    }
    const domMatch = cron.dayOfMonth.includes(dom);
    const dowMatch = cron.dayOfWeek.includes(dow);
    if (!(domMatch || dowMatch)) {
      cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);
      continue;
    }
    return toIsoUtc(cursor);
  }
  throw new Error('cron next occurrence not found within one year');
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function resolveDbPath(opts) {
  if (opts.dbPath) return path.resolve(opts.dbPath);
  if (opts.runtimeStateRoot) {
    return path.resolve(opts.runtimeStateRoot, '.rbtv', 'heart', 'heart.db');
  }
  throw new Error('openHeartStore requires dbPath or runtimeStateRoot');
}

class HeartStore {
  constructor(opts = {}) {
    if (singleton) {
      throw new HeartStoreError(E_SECOND_WRITER, 'heart store writer already open in this process');
    }
    this.dbPath = resolveDbPath(opts);
    ensureDir(path.dirname(this.dbPath));

    this.db = new DatabaseSync(this.dbPath);
    singleton = this;

    this.db.exec('PRAGMA journal_mode = WAL;');
    this.db.exec(SCHEMA_SQL);
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.db.exec('PRAGMA busy_timeout = 5000;');
    this.db.exec('PRAGMA synchronous = NORMAL;');

    this.config = {
      profiles: opts.profiles || {},
      tools: opts.tools || {},
      workflows: opts.workflows || {},
    };
  }

  _prepare(sql) {
    return this.db.prepare(sql);
  }

  close() {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
    if (singleton === this) singleton = null;
  }

  registerJob({ jobId, actionType, function: fn, argsSchema = '{}', description = null, enabled = 1, createdAt, updatedAt }) {
    if (!ACTION_TYPES.has(actionType)) {
      throw new HeartStoreError(E_BAD_ARGS, `invalid action_type: ${actionType}`, { field: 'actionType' });
    }
    const now = createdAt || isoNow();
    const upd = updatedAt || now;
    const stmt = this._prepare(`
      INSERT INTO jobs (job_id, action_type, function, args_schema, description, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(job_id) DO UPDATE SET
        action_type = excluded.action_type,
        function = excluded.function,
        args_schema = excluded.args_schema,
        description = excluded.description,
        enabled = excluded.enabled,
        updated_at = excluded.updated_at
    `);
    stmt.run(jobId, actionType, fn, argsSchema, description, enabled ? 1 : 0, now, upd);
    return this.getJob(jobId);
  }

  getJob(jobId) {
    const stmt = this._prepare('SELECT * FROM jobs WHERE job_id = ?');
    return stmt.get(jobId) || null;
  }

  listJobs() {
    const stmt = this._prepare('SELECT * FROM jobs ORDER BY job_id');
    return stmt.all();
  }

  enqueue(req) {
    const job = this.getJob(req.jobId);
    if (!job) {
      throw new HeartStoreError(E_UNKNOWN_JOB, `unknown job: ${req.jobId}`, { jobId: req.jobId });
    }
    if (!job.enabled) {
      throw new HeartStoreError(E_JOB_DISABLED, `job disabled: ${req.jobId}`, { jobId: req.jobId });
    }

    const args = req.args !== undefined ? req.args : '{}';
    validateArgs(args, job.args_schema, job.action_type);

    const parsedArgs = JSON.parse(args);
    if (job.action_type === 'launch-agent') {
      if (!this.config.profiles[parsedArgs.profile]) {
        throw new HeartStoreError(E_UNKNOWN_PROFILE, `unknown launch profile: ${parsedArgs.profile}`, { profile: parsedArgs.profile });
      }
    } else if (job.action_type === 'fire-tool') {
      if (!this.config.tools[parsedArgs.tool]) {
        throw new HeartStoreError(E_UNKNOWN_TOOL, `unknown tool: ${parsedArgs.tool}`, { tool: parsedArgs.tool });
      }
    } else if (job.action_type === 'start-workflow') {
      if (!this.config.workflows[parsedArgs.workflow]) {
        throw new HeartStoreError(E_UNKNOWN_WORKFLOW, `unknown workflow: ${parsedArgs.workflow}`, { workflow: parsedArgs.workflow });
      }
    }

    validateTrigger(req);

    const sessionMode = req.sessionMode || 'headless';
    if (!SESSION_MODES.has(sessionMode)) {
      throw new HeartStoreError(E_BAD_MODE, `invalid session_mode: ${sessionMode}`, { field: 'sessionMode' });
    }
    if (sessionMode === 'headed') {
      if (job.action_type !== 'launch-agent') {
        throw new HeartStoreError(E_BAD_MODE, 'headed mode only allowed for launch-agent', { field: 'sessionMode' });
      }
      const profile = this.config.profiles[parsedArgs.profile];
      if (!profile || !profile.headed) {
        throw new HeartStoreError(E_BAD_MODE, `profile ${parsedArgs.profile} is not headed-capable`, { field: 'sessionMode', profile: parsedArgs.profile });
      }
    }

    const enqueuedAt = req.enqueuedAt || isoNow();
    const stmt = this._prepare(`
      INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at, repeat_rule, interval_seconds, max_fires, enqueued_by, enqueued_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      req.jobId,
      args,
      sessionMode,
      req.triggerKind,
      req.runAt,
      req.repeatRule === undefined ? null : req.repeatRule,
      req.intervalSeconds === undefined ? null : req.intervalSeconds,
      req.maxFires === undefined ? null : req.maxFires,
      req.enqueuedBy,
      enqueuedAt
    );
    return this.getQueueRow(Number(result.lastInsertRowid));
  }

  getQueueRow(queueId) {
    const stmt = this._prepare('SELECT * FROM queue WHERE queue_id = ?');
    return stmt.get(queueId) || null;
  }

  getQueueDue(now) {
    const stmt = this._prepare('SELECT * FROM queue WHERE run_at <= ? ORDER BY run_at, queue_id');
    return stmt.all(toIsoUtc(now));
  }

  listQueue() {
    const stmt = this._prepare('SELECT * FROM queue ORDER BY run_at, queue_id');
    return stmt.all();
  }

  fireQueueRow({ queueId, now, tick, parentExecId = null }) {
    const firedAt = toIsoUtc(now);
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const queue = this.getQueueRow(queueId);
      if (!queue) {
        this.db.exec('ROLLBACK;');
        return null;
      }
      if (queue.run_at > firedAt) {
        this.db.exec('ROLLBACK;');
        return null;
      }

      let thread = 'pending';
      if (parentExecId !== null) {
        const parent = this._prepare('SELECT thread FROM jobs_log WHERE exec_id = ?').get(parentExecId);
        if (!parent) {
          this.db.exec('ROLLBACK;');
          throw new HeartStoreError(E_BAD_ARGS, `parent_exec_id does not exist: ${parentExecId}`, { field: 'parentExecId' });
        }
        thread = parent.thread;
      }

      const insertLog = this._prepare(`
        INSERT INTO jobs_log
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status, thread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?)
      `);
      const logResult = insertLog.run(
        parentExecId,
        queue.queue_id,
        queue.job_id,
        queue.action_type || this.getJob(queue.job_id)?.action_type || 'launch-agent',
        queue.args,
        queue.enqueued_by,
        queue.session_mode,
        tick,
        firedAt,
        thread
      );
      const execId = Number(logResult.lastInsertRowid);

      if (parentExecId === null) {
        thread = `exec-${execId}`;
        this._prepare('UPDATE jobs_log SET thread = ? WHERE exec_id = ?').run(thread, execId);
      }

      if (queue.trigger_kind === 'scheduled' && (queue.repeat_rule === null || queue.repeat_rule === undefined)) {
        this._prepare('DELETE FROM queue WHERE queue_id = ?').run(queueId);
      } else {
        let nextRunAt;
        if (queue.trigger_kind === 'periodic') {
          nextRunAt = toIsoUtc(new Date(now.getTime() + queue.interval_seconds * 1000));
        } else {
          nextRunAt = nextCronUtc(now, queue.repeat_rule);
        }
        let retired = false;
        if (queue.max_fires !== null && queue.max_fires !== undefined) {
          const countRow = this._prepare('SELECT COUNT(*) AS n FROM jobs_log WHERE queue_id = ?').get(queueId);
          if (countRow.n >= queue.max_fires) {
            this._prepare('DELETE FROM queue WHERE queue_id = ?').run(queueId);
            retired = true;
          }
        }
        if (!retired) {
          this._prepare('UPDATE queue SET run_at = ? WHERE queue_id = ?').run(nextRunAt, queueId);
        }
      }

      this.db.exec('COMMIT;');
      return this.getExecution(execId);
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  recordExecutionStart({ queueId = null, jobId, actionType, args, enqueuedBy, sessionMode = 'headless', firedTick, firedAt, parentExecId = null, thread = null, sessionId = null, pid = null }) {
    const firedAtIso = toIsoUtc(firedAt);
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      let useThread = thread;
      if (useThread === null || useThread === undefined) {
        if (parentExecId !== null) {
          const parent = this._prepare('SELECT thread FROM jobs_log WHERE exec_id = ?').get(parentExecId);
          if (!parent) {
            this.db.exec('ROLLBACK;');
            throw new HeartStoreError(E_BAD_ARGS, `parent_exec_id does not exist: ${parentExecId}`, { field: 'parentExecId' });
          }
          useThread = parent.thread;
        }
      }
      const stmt = this._prepare(`
        INSERT INTO jobs_log
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status, thread, session_id, pid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?, ?, ?)
      `);
      const result = stmt.run(
        parentExecId,
        queueId,
        jobId,
        actionType,
        args,
        enqueuedBy,
        sessionMode,
        firedTick,
        firedAtIso,
        useThread || 'pending',
        sessionId,
        pid
      );
      const execId = Number(result.lastInsertRowid);
      if (useThread === null || useThread === undefined) {
        const chainThread = `exec-${execId}`;
        this._prepare('UPDATE jobs_log SET thread = ? WHERE exec_id = ?').run(chainThread, execId);
      }
      this.db.exec('COMMIT;');
      return this.getExecution(execId);
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  getExecution(execId) {
    const stmt = this._prepare('SELECT * FROM jobs_log WHERE exec_id = ?');
    return stmt.get(execId) || null;
  }

  listExecutionsByStatus(status) {
    const stmt = this._prepare('SELECT * FROM jobs_log WHERE status = ? ORDER BY exec_id');
    return stmt.all(status);
  }

  updateExecutionStatus(execId, { status, sessionId = null, pid = null, exitCode = null, completionMsgId = null, logPath = null, endedAt = null }) {
    const stmt = this._prepare(`
      UPDATE jobs_log SET
        status = ?,
        session_id = COALESCE(?, session_id),
        pid = COALESCE(?, pid),
        exit_code = COALESCE(?, exit_code),
        completion_msg_id = COALESCE(?, completion_msg_id),
        log_path = COALESCE(?, log_path),
        ended_at = COALESCE(?, ended_at)
      WHERE exec_id = ?
    `);
    stmt.run(status, sessionId, pid, exitCode, completionMsgId, logPath, endedAt ? toIsoUtc(endedAt) : null, execId);
    return this.getExecution(execId);
  }

  recordMessage({ type, sender, thread, corpus, status = null, createdAt }) {
    if (!MESSAGE_TYPES.has(type)) {
      throw new HeartStoreError(E_BAD_MESSAGE, `invalid message type: ${type}`, { field: 'type' });
    }
    if (typeof sender !== 'string' || sender.length === 0) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'sender must be non-empty', { field: 'sender' });
    }
    if (typeof thread !== 'string' || thread.length === 0) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'thread must be non-empty', { field: 'thread' });
    }
    if (typeof corpus !== 'string') {
      throw new HeartStoreError(E_BAD_MESSAGE, 'corpus must be a string', { field: 'corpus' });
    }
    if (type === 'completion' && !['done', 'blocked', 'failed'].includes(status)) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'completion requires status done|blocked|failed', { field: 'status' });
    }
    const createdAtIso = createdAt ? toIsoUtc(createdAt) : isoNow();
    const stmt = this._prepare(`
      INSERT INTO messages (type, sender, thread, corpus, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(type, sender, thread, corpus, status, createdAtIso);
    return this.getMessage(Number(result.lastInsertRowid));
  }

  getMessage(msgId) {
    const stmt = this._prepare('SELECT * FROM messages WHERE msg_id = ?');
    return stmt.get(msgId) || null;
  }

  getMessages({ unroutedOnly = false, unbroadcastOnly = false, limit = null } = {}) {
    let sql = 'SELECT * FROM messages';
    const conds = [];
    if (unroutedOnly) conds.push('routed_at_tick IS NULL');
    if (unbroadcastOnly) conds.push('broadcast_at_tick IS NULL');
    if (conds.length) sql += ' WHERE ' + conds.join(' AND ');
    sql += ' ORDER BY msg_id';
    if (limit !== null) sql += ` LIMIT ${Number(limit)}`;
    const stmt = this._prepare(sql);
    return stmt.all();
  }

  resolveCompletion({ msgId, execId, status, endedAt, routedAtTick }) {
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      this._prepare('UPDATE messages SET routed_at_tick = ? WHERE msg_id = ?').run(routedAtTick, msgId);
      this._prepare(`
        UPDATE jobs_log SET status = ?, completion_msg_id = ?, ended_at = ? WHERE exec_id = ?
      `).run(status, msgId, toIsoUtc(endedAt), execId);
      this.db.exec('COMMIT;');
      return { message: this.getMessage(msgId), execution: this.getExecution(execId) };
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  recordTick({ tick, ts, actionsJson = '[]' }) {
    const tsIso = ts ? toIsoUtc(ts) : isoNow();
    const stmt = this._prepare('INSERT INTO ticks (tick, ts, actions_json) VALUES (?, ?, ?)');
    stmt.run(tick, tsIso, actionsJson);
    return this.getTick(tick);
  }

  getTick(tick) {
    const stmt = this._prepare('SELECT * FROM ticks WHERE tick = ?');
    return stmt.get(tick) || null;
  }

  getLastTick() {
    const stmt = this._prepare('SELECT * FROM ticks ORDER BY tick DESC LIMIT 1');
    return stmt.get() || null;
  }

  dump() {
    return {
      jobs: this._prepare('SELECT * FROM jobs ORDER BY job_id').all(),
      queue: this._prepare('SELECT * FROM queue ORDER BY queue_id').all(),
      jobs_log: this._prepare('SELECT * FROM jobs_log ORDER BY exec_id').all(),
      messages: this._prepare('SELECT * FROM messages ORDER BY msg_id').all(),
      ticks: this._prepare('SELECT * FROM ticks ORDER BY tick').all(),
    };
  }
}

function openHeartStore(opts) {
  return new HeartStore(opts);
}

function closeHeartStore() {
  if (singleton) singleton.close();
}

function isHeartStoreOpen() {
  return singleton !== null && singleton.db !== null;
}

module.exports = {
  openHeartStore,
  closeHeartStore,
  isHeartStoreOpen,
  HeartStore,
  HeartStoreError,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
};

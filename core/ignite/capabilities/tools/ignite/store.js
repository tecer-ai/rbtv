'use strict';

// API — consumers use this list, not the body. One store per agent home.
// conversationKey(team, channel, rootTs) → "<team>:<channel>:<rootTs>"
// DISPOSITIONS — completed | continue | waiting_owner | waiting_workers | stopped
// RETRY_DELAYS_MS — [5000, 30000] after attempts 1 and 2; MAX_ATTEMPTS — 3
// new Store(dbPath) — create or open state.sqlite; parent directories are created
// close()
// upsertConversation({ key, agent, workspace, channel, rootTs, activated })
// getConversation(key) — agent, activated (boolean), workspace (Slack team id)
// followConversation(key) — the conversation a key held outside this store names now: a conversation rekeyed since
//   (its first root post) is found under its newest key; a key a new conversation took again names that one
// activateConversation(key)
// conversationByThread({ workspace, channel, rootTs })
// acceptOwnerInput({ key, agent, workspace, channel, rootTs, activated, message, queueId, payload })
// recordMessage(key, { id, role, text, files, metadata, team, channel, ts, createdAt }) — false if duplicate Slack identity
// listHistory(key, limit) — Slack identity on each row
// lastOwnerReply(channel, rootTs, now?) — latest stored owner reply time, excluding roots and synthetic text
// setSession(key, harness, sessionId) / getSession(key, harness) — per harness, never folder-last
// getWork(id) / listWork({ conversationKey })
// enqueue({ id, conversationKey, payload, message, workId, availableAt }) — owner input only; reopens completed|stopped as a new work id; never unholds
// wake({ workId, conversationKey, note }) — worker completion; false on completed|stopped|held|waiting_owner
// notify({ id, conversationKey, note, payload }) — one notice told once, in one transaction: a wake carrying note
//   (queue id wake:<id>), or, when the conversation has no work a wake can take, the post payload (outbox id
//   post:<id>). Either row existing, in any state, makes it 'duplicate': nothing is inserted. → { inserted, reason, woke }
// enqueueScheduleWake({ id, conversationKey, scheduleId, workId, details }) — fresh threadless conversation;
//   conversationKey supplies routing only, workId gates eligibility only. An id already in the queue, in any
//   state, is 'duplicate' and inserts nothing; other timers' wakes never block it. details, when given, is the
//   check's JSON and stays in the row's payload through retries and holds. Never reopens or unholds
// claimNext(now) — owner input before continuation; a pending owner row on completed|stopped work is reopened, then claimed
// getActiveRun() — running row even if the process is dead; liveRun() — the row only when the process's start, read with cast's procStart, equals pidStart (string compare)
// attachProcess(runId, { pid, pidStart, setting }) — freezes the launch snapshot for this run
// finishRun(runId, nonce, { invocationNonce, output, disposition, summary, nextStep, workers, outputs, harness, sessionId, outbox })
// failRun(runId, reason, { scope, now }) — retry then hold; enqueues the one blocker; callers must not enqueue another
// agentHold() / clearHold({ workId }) — owner retry/repair only; wakes and ticks never call it
// stopWork(id) — stops continuation; does not delete schedules or clear an agent hold
// enqueueOutbox({ id, conversationKey, payload, asRoot, clientMsgId }) — client_msg_id defaults to id
// pendingOutbox(now) / markDelivered(id, { channel, ts, asRoot? }) / markDeliveryFailed(id, error, { retryAt })
//   Delivery binds a threadless conversation to its root; confirmed post: rows join the target's history once.
// stopOutbox(id, error) — state failed on the existing column; pendingOutbox no longer returns it. No new column.
// rememberPost(id, { channel, ts }) — text already confirmed; row stays pending so file uploads can retry. No new column.
// beginProactive({ id, agent, workspace, channel, payload, clientMsgId }) — activated; Slack key bound in markDelivered
// checkTool(value) — the stored form of a timer's check tool, or null for none; throws on a value it refuses
// upsertSchedule({ id, conversationKey, workId, cadence, timezone, nextAt, enabled, note, report, subject, checkTool })
// advanceSchedule(id, occurrence, nextAt) — moves next_at only while it still equals occurrence; a null nextAt
//   disables the timer (a spent one-shot). Every other column, enabled included, is kept. false when the timer
//   moved or is gone
// fireSchedule({ schedule, nextAt, details }) — one transaction: records the wake of the row's occurrence
//   (its next_at) under the id schedule:<id>:<next_at>, then advances the timer. Returns enqueueScheduleWake's
//   answer plus advanced; a refused wake (agent_hold, refused) advances nothing, a duplicate advances
// getSchedule(id) / listSchedules() / dueSchedules(now) / deleteSchedule(id) — rows carry check_tool, null for none
// pendingScheduleIds() — ids of schedule wakes still pending or running, including spent one-shots
// setLiveStatus({ conversationKey?, channel, ts, system?, agent?, task?, runId? }) — the live status of one
//   owner message (live-status.js names the states). A field left out keeps its value, null clears it.
//   conversationKey is needed only to insert: without it, a message with no row is skipped (null).
//   Every write takes the next rev, so a reader asks for the rows changed since the rev it last read.
// getLiveStatus(channel, ts) / liveStatusOfRun(runId)
// liveStatuses({ sinceRev, conversationKey }) — rows with rev above sinceRev, oldest change first
// liveStatusesOfWork(workId) — the rows whose last turn (run_id) belongs to that work
// setLiveShown(channel, ts, shown) — records what the message's reactions show (the Slack connector's
//   record, stored as JSON in the row's shown); takes no rev, so a reader of changes never sees it. A row
//   is inserted with shown {} (nothing shown yet); a NULL shown, as in a row made before the column, is
//   an unknown display
// getRun(runId) — a run with its queue row's conversation_key, work_id and kind, or null
// ownerTs(workId) — Slack ts of the latest owner message queued for that work, or null
// transaction(fn)

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');
const { procStart } = require('../../../../cast/capabilities/tools/cast/lib/handles');

const DISPOSITIONS = Object.freeze(['completed', 'continue', 'waiting_owner', 'waiting_workers', 'stopped']);
const DISPOSITION_SET = new Set(DISPOSITIONS);
const RETRY_DELAYS_MS = Object.freeze([5_000, 30_000]);
const MAX_ATTEMPTS = 3;
const TERMINAL = new Set(['completed', 'stopped']);
const HELD = 'held';
const OWNER_PRIORITY = 0;
const AUTO_PRIORITY = 10;

const json = (value) => JSON.stringify(value ?? null);
const parse = (value) => value == null ? null : JSON.parse(value);

function conversationKey(team, channel, rootTs) {
  if (!team || !channel || !rootTs) throw new Error('team, channel and root ts required');
  for (const part of [team, channel, rootTs]) {
    if (String(part).includes(':')) throw new Error('conversation key parts cannot contain colon');
  }
  return `${team}:${channel}:${rootTs}`;
}

// One executable, never split into arguments. With a separator it is a path below the agent home;
// without one it is a command found on PATH. Backslashes are stored as slashes.
function checkTool(value) {
  if (value == null) return null;
  if (typeof value !== 'string' || !value.trim() || /[\r\n\0]/.test(value)) {
    throw new Error('check must be a one-line path or command name');
  }
  const tool = value.trim().replaceAll('\\', '/');
  if (/^(\/|[A-Za-z]:)/.test(tool)) {
    throw new Error('check must be a path relative to the agent home or a command name, never an absolute path');
  }
  const parts = tool.split('/');
  if (parts.includes('..') || !parts.at(-1)) throw new Error('check must name a file below the agent home');
  return tool;
}

class Store {
  constructor(dbPath) {
    if (!dbPath) throw new Error('db path required');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    this.db = new DatabaseSync(dbPath);
    this._inTx = false;
    this.db.exec('PRAGMA busy_timeout=5000; PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;');
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        key TEXT PRIMARY KEY,
        agent TEXT NOT NULL,
        workspace TEXT NOT NULL,
        channel TEXT NOT NULL,
        root_ts TEXT,
        activated INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS conversation_sessions (
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        harness TEXT NOT NULL,
        session_id TEXT NOT NULL,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (conversation_key, harness)
      );
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        role TEXT NOT NULL,
        text TEXT NOT NULL,
        files TEXT NOT NULL,
        metadata TEXT NOT NULL,
        team TEXT,
        channel TEXT,
        ts TEXT,
        created_at INTEGER NOT NULL
      );
      CREATE UNIQUE INDEX IF NOT EXISTS messages_slack_id ON messages(team, channel, ts)
        WHERE team IS NOT NULL AND channel IS NOT NULL AND ts IS NOT NULL;
      CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_key, created_at);
      CREATE TABLE IF NOT EXISTS work (
        id TEXT PRIMARY KEY,
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        state TEXT NOT NULL,
        summary TEXT,
        next_step TEXT,
        workers TEXT,
        outputs TEXT,
        error TEXT,
        predecessor_id TEXT,
        updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS queue (
        id TEXT PRIMARY KEY,
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        kind TEXT NOT NULL,
        payload TEXT NOT NULL,
        work_id TEXT REFERENCES work(id),
        priority INTEGER NOT NULL,
        available_at INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS queue_ready ON queue(state, priority, available_at, created_at);
      CREATE UNIQUE INDEX IF NOT EXISTS queue_one_pending_wake ON queue(work_id)
        WHERE kind = 'wake' AND state = 'pending' AND work_id IS NOT NULL;
      CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        queue_id TEXT NOT NULL REFERENCES queue(id),
        nonce TEXT NOT NULL,
        state TEXT NOT NULL,
        pid INTEGER,
        pid_start TEXT,
        launch_snapshot TEXT,
        output TEXT,
        error TEXT,
        started_at INTEGER NOT NULL,
        ended_at INTEGER
      );
      CREATE UNIQUE INDEX IF NOT EXISTS runs_one_active ON runs(state) WHERE state = 'running';
      CREATE TABLE IF NOT EXISTS outbox (
        id TEXT PRIMARY KEY,
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        payload TEXT NOT NULL,
        as_root INTEGER NOT NULL DEFAULT 0,
        client_msg_id TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        next_retry_at INTEGER,
        last_error TEXT,
        channel TEXT,
        ts TEXT,
        created_at INTEGER NOT NULL,
        delivered_at INTEGER
      );
      CREATE TABLE IF NOT EXISTS schedules (
        id TEXT PRIMARY KEY,
        conversation_key TEXT NOT NULL REFERENCES conversations(key),
        work_id TEXT REFERENCES work(id),
        cadence TEXT NOT NULL,
        timezone TEXT NOT NULL,
        next_at INTEGER,
        enabled INTEGER NOT NULL,
        note TEXT,
        report TEXT,
        subject TEXT,
        check_tool TEXT,
        updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS live_status (
        channel TEXT NOT NULL,
        ts TEXT NOT NULL,
        conversation_key TEXT NOT NULL,
        system TEXT,
        agent TEXT,
        task TEXT,
        run_id TEXT,
        shown TEXT,
        rev INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (channel, ts)
      );
      CREATE INDEX IF NOT EXISTS live_status_rev ON live_status(rev);
      CREATE INDEX IF NOT EXISTS live_status_conversation ON live_status(conversation_key);
      CREATE TABLE IF NOT EXISTS conversation_moves (
        old_key TEXT PRIMARY KEY,
        new_key TEXT NOT NULL,
        moved_at INTEGER NOT NULL
      );
    `);
    this.transaction(() => {
      const columns = this.db.prepare('PRAGMA table_info(schedules)').all().map((column) => column.name);
      for (const added of ['subject', 'check_tool']) {
        if (!columns.includes(added)) this.db.exec(`ALTER TABLE schedules ADD COLUMN ${added} TEXT`);
      }
      const live = this.db.prepare('PRAGMA table_info(live_status)').all().map((column) => column.name);
      if (!live.includes('shown')) this.db.exec('ALTER TABLE live_status ADD COLUMN shown TEXT');
      // Older databases allowed one pending timer wake per agent; a wake is now identified by its queue id.
      this.db.exec('DROP INDEX IF EXISTS queue_one_pending_schedule');
    });
  }

  close() { this.db.close(); }

  transaction(fn) {
    if (this._inTx) return fn();
    this.db.exec('BEGIN IMMEDIATE');
    this._inTx = true;
    try {
      const result = fn();
      this.db.exec('COMMIT');
      return result;
    } catch (error) {
      this.db.exec('ROLLBACK');
      throw error;
    } finally {
      this._inTx = false;
    }
  }

  upsertConversation({ key, agent, workspace, channel, rootTs = null, activated = false }) {
    if (!key || !agent || !workspace || !channel) throw new Error('conversation key, agent, workspace and channel required');
    return this.transaction(() => {
      const existing = this.db.prepare('SELECT * FROM conversations WHERE key=?').get(key);
      const now = Date.now();
      if (!existing) {
        this.db.prepare(`INSERT INTO conversations(key, agent, workspace, channel, root_ts, activated, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?)`).run(key, agent, workspace, channel, rootTs, activated ? 1 : 0, now);
        // The key names a new conversation now, not the one that moved away from it.
        this.db.prepare('DELETE FROM conversation_moves WHERE old_key=?').run(key);
      } else {
        if (existing.agent !== agent) throw new Error('conversation belongs to another agent');
        if (existing.workspace !== workspace || existing.channel !== channel) {
          throw new Error('conversation workspace or channel mismatch');
        }
        this.db.prepare(`UPDATE conversations SET root_ts=COALESCE(?, root_ts),
          activated=MAX(activated, ?), updated_at=? WHERE key=?`)
          .run(rootTs, activated ? 1 : 0, now, key);
      }
      return this.getConversation(key);
    });
  }

  getConversation(key) {
    return this._conversation(this.db.prepare('SELECT * FROM conversations WHERE key=?').get(key));
  }

  followConversation(key) {
    const moved = this.db.prepare('SELECT new_key FROM conversation_moves WHERE old_key=?').get(key);
    return this.getConversation(moved ? moved.new_key : key);
  }

  activateConversation(key) {
    const result = this.db.prepare('UPDATE conversations SET activated=1, updated_at=? WHERE key=?')
      .run(Date.now(), key);
    if (result.changes !== 1) throw new Error('unknown conversation');
    return this.getConversation(key);
  }

  conversationByThread({ workspace, channel, rootTs }) {
    const key = conversationKey(workspace, channel, rootTs);
    return this.getConversation(key);
  }

  _conversation(row) {
    if (!row) return null;
    return { ...row, activated: row.activated === 1 };
  }

  setSession(key, harness, sessionId) {
    if (!key || !harness || !sessionId) throw new Error('conversation, harness and session id required');
    if (!this.getConversation(key)) throw new Error('unknown conversation');
    this.db.prepare(`INSERT INTO conversation_sessions(conversation_key, harness, session_id, updated_at)
      VALUES (?, ?, ?, ?)
      ON CONFLICT(conversation_key, harness) DO UPDATE SET session_id=excluded.session_id, updated_at=excluded.updated_at`)
      .run(key, harness, sessionId, Date.now());
    return this.getSession(key, harness);
  }

  getSession(key, harness) {
    const row = this.db.prepare(`SELECT session_id FROM conversation_sessions
      WHERE conversation_key=? AND harness=?`).get(key, harness);
    return row ? row.session_id : null;
  }

  recordMessage(conversationKeyValue, { id, role, text = '', files = [], metadata = {}, team = null, channel = null, ts = null, createdAt = Date.now() }) {
    if (!id || !role) throw new Error('message id and role required');
    if (!this.getConversation(conversationKeyValue)) throw new Error('unknown conversation');
    return this.transaction(() => this._recordMessage(conversationKeyValue, { id, role, text, files, metadata, team, channel, ts, createdAt }));
  }

  _recordMessage(conversationKeyValue, { id, role, text, files, metadata, team, channel, ts, createdAt }) {
    if (team && channel && ts) {
      const existing = this.db.prepare('SELECT id FROM messages WHERE team=? AND channel=? AND ts=?').get(team, channel, ts);
      if (existing) return false;
    }
    return this.db.prepare(`INSERT OR IGNORE INTO messages
      (id, conversation_key, role, text, files, metadata, team, channel, ts, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
      id, conversationKeyValue, role, text, json(files), json(metadata), team, channel, ts, createdAt,
    ).changes === 1;
  }

  listHistory(conversationKeyValue, limit = 50) {
    return this.db.prepare(`SELECT * FROM (SELECT * FROM messages WHERE conversation_key=?
      ORDER BY created_at DESC, id DESC LIMIT ?) ORDER BY created_at, id`)
      .all(conversationKeyValue, limit)
      .map((row) => ({ ...row, files: parse(row.files), metadata: parse(row.metadata) }));
  }

  lastOwnerReply(channel, rootTs, now = Date.now()) {
    return this.db.prepare(`SELECT MAX(m.created_at) AS latest FROM messages m
      JOIN conversations c ON c.key=m.conversation_key
      WHERE c.channel=? AND c.root_ts=? AND m.role='owner'
        AND m.ts IS NOT NULL AND m.ts!=c.root_ts AND m.created_at<=?`)
      .get(channel, rootTs, now).latest;
  }

  acceptOwnerInput({ key, agent, workspace, channel, rootTs = null, activated = false, message, queueId = null, payload = {} }) {
    if (!message?.id || !message.team || !message.channel || !message.ts) {
      throw new Error('owner message id, team, channel and ts required');
    }
    return this.transaction(() => {
      this.upsertConversation({ key, agent, workspace, channel, rootTs, activated });
      const saved = this._recordMessage(key, { text: '', files: [], metadata: {}, createdAt: Date.now(), ...message });
      if (!saved) return { duplicate: true, inserted: false, workId: null, conversation: this.getConversation(key) };
      const enqueued = this._enqueueOwner({
        id: queueId || message.id,
        conversationKey: key,
        payload: { ...payload, messageId: message.id },
        workId: null,
        availableAt: Date.now(),
      });
      return { duplicate: false, ...enqueued, conversation: this.getConversation(key) };
    });
  }

  _work(row) {
    if (!row) return null;
    return { ...row, workers: parse(row.workers), outputs: parse(row.outputs) };
  }

  getWork(id) {
    return this._work(this.db.prepare('SELECT * FROM work WHERE id=?').get(id));
  }

  listWork({ conversationKey: conversationKeyValue = null } = {}) {
    const rows = conversationKeyValue
      ? this.db.prepare('SELECT * FROM work WHERE conversation_key=? ORDER BY updated_at DESC, id').all(conversationKeyValue)
      : this.db.prepare('SELECT * FROM work ORDER BY updated_at DESC, id').all();
    return rows.map((row) => this._work(row));
  }

  _insertWork(id, conversationKeyValue, { state = 'open', predecessorId = null } = {}) {
    this.db.prepare(`INSERT INTO work(id, conversation_key, state, predecessor_id, updated_at)
      VALUES (?, ?, ?, ?, ?)`).run(id, conversationKeyValue, state, predecessorId, Date.now());
    return this.getWork(id);
  }

  _latestWork(conversationKeyValue) {
    return this._work(this.db.prepare(`SELECT * FROM work WHERE conversation_key=?
      ORDER BY updated_at DESC, id DESC LIMIT 1`).get(conversationKeyValue));
  }

  _reopen(work) {
    const id = randomUUID();
    return this._insertWork(id, work.conversation_key, { predecessorId: work.id });
  }

  enqueue({ id, conversationKey: conversationKeyValue, payload = {}, message = null, workId = null, availableAt = Date.now() }) {
    if (!id || !conversationKeyValue) throw new Error('queue id and conversation required');
    return this.transaction(() => {
      if (!this.getConversation(conversationKeyValue)) throw new Error('unknown conversation');
      if (message && !this._recordMessage(conversationKeyValue, { text: '', files: [], metadata: {}, createdAt: Date.now(), ...message })) {
        return { inserted: false, reason: 'duplicate', workId: null, reopenedFrom: null };
      }
      return this._enqueueOwner({ id, conversationKey: conversationKeyValue, payload, workId, availableAt });
    });
  }

  _enqueueOwner({ id, conversationKey: conversationKeyValue, payload, workId, availableAt }) {
    const existing = this.db.prepare('SELECT id FROM queue WHERE id=?').get(id);
    if (existing) return { inserted: false, reason: 'duplicate', workId: workId ?? null, reopenedFrom: null };
    let targetId = workId;
    let reopenedFrom = null;
    if (targetId) {
      const work = this.getWork(targetId);
      if (!work) throw new Error('unknown work');
      if (work.conversation_key !== conversationKeyValue) throw new Error('work belongs to another conversation');
      if (TERMINAL.has(work.state)) {
        const successor = this._reopen(work);
        reopenedFrom = work.id;
        targetId = successor.id;
      }
    } else {
      const current = this._latestWork(conversationKeyValue);
      if (!current) {
        targetId = randomUUID();
        this._insertWork(targetId, conversationKeyValue);
      } else if (TERMINAL.has(current.state)) {
        const successor = this._reopen(current);
        reopenedFrom = current.id;
        targetId = successor.id;
      } else {
        targetId = current.id;
      }
    }
    this.db.prepare(`INSERT INTO queue
      (id, conversation_key, kind, payload, work_id, priority, available_at, created_at)
      VALUES (?, ?, 'owner', ?, ?, ?, ?, ?)`).run(
      id, conversationKeyValue, json(payload), targetId, OWNER_PRIORITY, availableAt, Date.now(),
    );
    return { inserted: true, reason: reopenedFrom ? 'reopened' : 'queued', workId: targetId, reopenedFrom };
  }

  wake({ workId = null, conversationKey: conversationKeyValue = null, note = 'worker' } = {}) {
    return this.transaction(() => this._wake(workId ? this.getWork(workId) : this._wakeTarget(conversationKeyValue), note));
  }

  _wake(work, note, id = null) {
    if (!work) return { inserted: false, reason: 'unknown' };
    if (TERMINAL.has(work.state) || work.state === HELD || work.state === 'waiting_owner') {
      return { inserted: false, reason: 'refused', workId: work.id };
    }
    const pending = this.db.prepare(`SELECT id FROM queue WHERE kind='wake' AND state='pending' AND work_id=?`).get(work.id);
    if (pending) return { inserted: false, reason: 'duplicate', workId: work.id };
    const queueId = id || `wake:${work.id}:${randomUUID()}`;
    this.db.prepare(`INSERT INTO queue
      (id, conversation_key, kind, payload, work_id, priority, available_at, created_at)
      VALUES (?, ?, 'wake', ?, ?, ?, ?, ?)`).run(
      queueId, work.conversation_key, json({ note }), work.id, AUTO_PRIORITY, Date.now(), Date.now(),
    );
    return { inserted: true, reason: 'queued', workId: work.id, id: queueId };
  }

  notify({ id, conversationKey: conversationKeyValue, note, payload }) {
    if (!id || !conversationKeyValue || !note || !payload) throw new Error('notice id, conversation, note and payload required');
    const wakeId = `wake:${id}`;
    const postId = `post:${id}`;
    return this.transaction(() => {
      if (this.db.prepare('SELECT id FROM queue WHERE id=?').get(wakeId) || this.db.prepare('SELECT id FROM outbox WHERE id=?').get(postId)) {
        return { inserted: false, reason: 'duplicate', woke: false };
      }
      if (!this.getConversation(conversationKeyValue)) throw new Error('unknown conversation');
      if (this._wake(this._wakeTarget(conversationKeyValue), note, wakeId).inserted) {
        return { inserted: true, reason: 'woke', woke: true, id: wakeId };
      }
      this._enqueueOutbox({ id: postId, conversationKey: conversationKeyValue, payload, clientMsgId: postId });
      return { inserted: true, reason: 'posted', woke: false, id: postId };
    });
  }

  _wakeTarget(conversationKeyValue) {
    if (!conversationKeyValue) throw new Error('work id or conversation required');
    return this._work(this.db.prepare(`SELECT * FROM work WHERE conversation_key=? AND state='waiting_workers'
      ORDER BY updated_at DESC, id DESC LIMIT 1`).get(conversationKeyValue))
      || this._work(this.db.prepare(`SELECT * FROM work WHERE conversation_key=? AND state IN ('open', 'continue')
        ORDER BY updated_at DESC, id DESC LIMIT 1`).get(conversationKeyValue));
  }

  enqueueScheduleWake({ id, conversationKey: conversationKeyValue, scheduleId = id, workId = null, details }) {
    if (!id || !conversationKeyValue) throw new Error('schedule wake id and conversation required');
    return this.transaction(() => {
      const source = this.getConversation(conversationKeyValue);
      if (!source) throw new Error('unknown conversation');
      if (this.agentHold()) return { inserted: false, reason: 'agent_hold' };
      if (workId) {
        const work = this.getWork(workId);
        if (!work) throw new Error('unknown work');
        if (work.state !== 'open' && work.state !== 'continue') {
          return { inserted: false, reason: 'refused', workId };
        }
      }
      if (this.db.prepare('SELECT id FROM queue WHERE id=?').get(id)) return { inserted: false, reason: 'duplicate', id };
      const key = `schedule:${randomUUID()}`;
      this.upsertConversation({
        key, agent: source.agent, workspace: source.workspace, channel: source.channel, activated: true,
      });
      this.db.prepare(`INSERT INTO queue
        (id, conversation_key, kind, payload, work_id, priority, available_at, created_at)
        VALUES (?, ?, 'schedule', ?, ?, ?, ?, ?)`).run(
        id, key, json({ scheduleId, details }), null, AUTO_PRIORITY, Date.now(), Date.now(),
      );
      return { inserted: true, reason: 'queued', id };
    });
  }

  claimNext(now = Date.now()) {
    return this.transaction(() => {
      if (this.getActiveRun() || this.agentHold()) return null;
      const row = this.db.prepare(`SELECT q.* FROM queue q LEFT JOIN work w ON w.id=q.work_id
        WHERE q.state='pending' AND q.available_at<=?
        AND (
          q.work_id IS NULL
          OR (q.kind='owner' AND w.state IN ('completed', 'stopped'))
          OR (
            w.state NOT IN ('held', 'completed', 'stopped')
            AND NOT (w.state='waiting_owner' AND q.kind!='owner')
            AND NOT (w.state='waiting_workers' AND q.kind NOT IN ('wake', 'owner'))
          )
        )
        ORDER BY q.priority, q.available_at, q.created_at, q.id LIMIT 1`).get(now);
      if (!row) return null;
      if (row.kind === 'owner' && row.work_id) {
        const work = this.getWork(row.work_id);
        if (work && TERMINAL.has(work.state)) {
          const successor = this._reopen(work);
          this.db.prepare('UPDATE queue SET work_id=? WHERE id=?').run(successor.id, row.id);
          row.work_id = successor.id;
        }
      }
      const runId = randomUUID();
      const nonce = randomUUID();
      this.db.prepare("UPDATE queue SET state='running', attempts=attempts+1 WHERE id=?").run(row.id);
      this.db.prepare(`INSERT INTO runs(id, queue_id, nonce, state, started_at) VALUES (?, ?, ?, 'running', ?)`)
        .run(runId, row.id, nonce, now);
      return {
        ...row,
        payload: parse(row.payload),
        attempts: row.attempts + 1,
        runId,
        nonce,
      };
    });
  }

  getActiveRun() {
    const row = this.db.prepare(`SELECT r.*, q.conversation_key, q.work_id, q.kind, q.attempts, q.payload
      FROM runs r JOIN queue q ON q.id=r.queue_id WHERE r.state='running'`).get();
    if (!row) return null;
    return {
      ...row,
      pidStart: row.pid_start ?? null,
      payload: parse(row.payload),
      launch_snapshot: parse(row.launch_snapshot),
    };
  }

  liveRun() {
    const run = this.getActiveRun();
    if (!run || run.pid == null || !run.pidStart) return null;
    const start = procStart(run.pid);
    if (start == null || String(start) !== String(run.pidStart)) return null;
    return run;
  }

  attachProcess(runId, { pid, pidStart, setting }) {
    if (!Number.isInteger(pid) || pid <= 0 || !pidStart) throw new Error('pid and pidStart required');
    const snapshot = setting;
    if (!snapshot?.harness || !snapshot.model || !snapshot.effort) throw new Error('launch setting required to attach a process');
    const frozen = {
      harness: snapshot.harness,
      model: snapshot.model,
      effort: snapshot.effort,
      voice: snapshot.voice ?? null,
      changedAt: snapshot.changedAt ?? null,
    };
    const result = this.db.prepare(`UPDATE runs SET pid=?, pid_start=?, launch_snapshot=?
      WHERE id=? AND state='running' AND pid IS NULL`).run(pid, String(pidStart), json(frozen), runId);
    if (result.changes !== 1) throw new Error('run not active or process already attached');
    return this.getActiveRun();
  }

  finishRun(runId, nonce, { invocationNonce, output, disposition, summary = '', nextStep = null,
    workers = [], outputs = [], harness = null, sessionId = null, outbox = [] }) {
    if (nonce !== invocationNonce) throw new Error('stale invocation output');
    if (!DISPOSITION_SET.has(disposition)) throw new Error('invalid disposition');
    if (typeof output !== 'string' || !output.trim()) throw new Error('fresh output required');
    if (disposition === 'continue' && (!nextStep || !String(nextStep).trim())) throw new Error('continue requires next step');
    if ((harness && !sessionId) || (!harness && sessionId)) throw new Error('harness and session id are set together');
    return this.transaction(() => {
      const run = this.getActiveRun();
      if (!run || run.id !== runId || run.nonce !== nonce) throw new Error('run not active');
      const now = Date.now();
      this.db.prepare("UPDATE runs SET state='finished', output=?, ended_at=? WHERE id=?").run(output, now, runId);
      this.db.prepare("UPDATE queue SET state='done' WHERE id=?").run(run.queue_id);
      let work = null;
      if (run.work_id) {
        const current = this.getWork(run.work_id);
        const stopped = current?.state === 'stopped';
        const state = stopped ? 'stopped' : disposition;
        this.db.prepare(`UPDATE work SET state=?, summary=?, next_step=?, workers=?, outputs=?, error=NULL, updated_at=?
          WHERE id=?`).run(state, summary, nextStep, json(workers), json(outputs), now, run.work_id);
        work = this.getWork(run.work_id);
        if (!stopped && disposition === 'continue') {
          this.db.prepare(`INSERT OR IGNORE INTO queue
            (id, conversation_key, kind, payload, work_id, priority, available_at, created_at)
            VALUES (?, ?, 'continue', ?, ?, ?, ?, ?)`).run(
            `continue:${runId}`, run.conversation_key, json({ summary, nextStep, workers, outputs }),
            run.work_id, AUTO_PRIORITY, now, now,
          );
        }
      }
      if (harness) this.setSession(run.conversation_key, harness, sessionId);
      this._recordMessage(run.conversation_key, {
        id: `run:${runId}`,
        role: 'assistant',
        text: output,
        files: [],
        metadata: { disposition, workId: run.work_id, summary, nextStep, workers, outputs },
        team: null,
        channel: null,
        ts: null,
        createdAt: now,
      });
      outbox.forEach((item, index) => {
        const itemId = item.id || `reply:${runId}:${index}`;
        this._enqueueOutbox({
          id: itemId,
          conversationKey: run.conversation_key,
          payload: item.payload || { text: item.text ?? '', audio: item.audio ?? false, files: item.files || [] },
          asRoot: Boolean(item.asRoot),
          clientMsgId: item.clientMsgId || itemId,
        });
      });
      return work;
    });
  }

  failRun(runId, reason, { scope = 'work', now = Date.now() } = {}) {
    if (!reason) throw new Error('technical failure reason required');
    if (scope !== 'work' && scope !== 'agent') throw new Error('hold scope must be work or agent');
    return this.transaction(() => {
      const run = this.getActiveRun();
      if (!run || run.id !== runId) throw new Error('run not active');
      this.db.prepare("UPDATE runs SET state='failed', error=?, ended_at=? WHERE id=?").run(String(reason), now, runId);
      const holdAgent = scope === 'agent' || !run.work_id;
      if (run.attempts < MAX_ATTEMPTS) {
        const retryAt = now + RETRY_DELAYS_MS[run.attempts - 1];
        this.db.prepare("UPDATE queue SET state='pending', available_at=? WHERE id=?").run(retryAt, run.queue_id);
        return { held: false, attempts: run.attempts, retryAt };
      }
      this.db.prepare("UPDATE queue SET state='held' WHERE id=?").run(run.queue_id);
      if (holdAgent) {
        this.db.prepare(`INSERT INTO settings(key, value, updated_at) VALUES ('agent_hold', ?, ?)
          ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at`)
          .run(json({ reason: String(reason), at: now }), now);
      } else {
        this.db.prepare("UPDATE work SET state='held', error=?, updated_at=? WHERE id=?").run(String(reason), now, run.work_id);
      }
      const repair = holdAgent
        ? 'rbtv agent configure, then ignite work retry'
        : `ignite work retry ${run.work_id}`;
      this._enqueueOutbox({
        id: `hold:${run.queue_id}`,
        conversationKey: run.conversation_key,
        payload: { text: `Work is on hold after three technical attempts. ${reason} Repair: ${repair}` },
        clientMsgId: `hold:${run.queue_id}`,
      });
      return { held: true, attempts: run.attempts, scope: holdAgent ? 'agent' : 'work' };
    });
  }

  agentHold() {
    return parse(this.db.prepare("SELECT value FROM settings WHERE key='agent_hold'").get()?.value);
  }

  clearHold({ workId = null } = {}) {
    return this.transaction(() => {
      const now = Date.now();
      if (workId) {
        const work = this.getWork(workId);
        if (!work || work.state !== HELD) return false;
        this.db.prepare("UPDATE work SET state='open', error=NULL, updated_at=? WHERE id=?").run(now, workId);
        this.db.prepare(`UPDATE queue SET state='pending', attempts=0, available_at=?
          WHERE work_id=? AND state='held'`).run(now, workId);
        return true;
      }
      if (!this.agentHold()) return false;
      this.db.prepare("DELETE FROM settings WHERE key='agent_hold'").run();
      this.db.prepare(`UPDATE queue SET state='pending', attempts=0, available_at=?
        WHERE state='held' AND (work_id IS NULL OR work_id NOT IN (SELECT id FROM work WHERE state='held'))`)
        .run(now);
      return true;
    });
  }

  stopWork(id) {
    return this.transaction(() => {
      const work = this.getWork(id);
      if (!work) throw new Error('unknown work');
      const now = Date.now();
      this.db.prepare("UPDATE work SET state='stopped', updated_at=? WHERE id=?").run(now, id);
      this.db.prepare(`UPDATE queue SET state='cancelled'
        WHERE work_id=? AND state='pending' AND kind IN ('continue', 'wake', 'schedule')`).run(id);
      return this.getWork(id);
    });
  }

  enqueueOutbox({ id, conversationKey: conversationKeyValue, payload, asRoot = false, clientMsgId = null }) {
    if (!id || !conversationKeyValue || !payload) throw new Error('outbox id, conversation and payload required');
    if (!this.getConversation(conversationKeyValue)) throw new Error('unknown conversation');
    return this._enqueueOutbox({ id, conversationKey: conversationKeyValue, payload, asRoot, clientMsgId: clientMsgId || id });
  }

  _enqueueOutbox({ id, conversationKey: conversationKeyValue, payload, asRoot = false, clientMsgId }) {
    return this.db.prepare(`INSERT OR IGNORE INTO outbox
      (id, conversation_key, payload, as_root, client_msg_id, created_at)
      VALUES (?, ?, ?, ?, ?, ?)`).run(
      id, conversationKeyValue, json(payload), asRoot ? 1 : 0, clientMsgId, Date.now(),
    ).changes === 1;
  }

  _outbox(row) {
    if (!row) return null;
    return { ...row, payload: parse(row.payload), as_root: row.as_root === 1 };
  }

  pendingOutbox(now = Date.now()) {
    return this.db.prepare(`SELECT * FROM outbox WHERE state='pending'
      AND (next_retry_at IS NULL OR next_retry_at<=?) ORDER BY created_at, id`).all(now).map((row) => this._outbox(row));
  }

  markDelivered(id, { channel, ts, asRoot = false }) {
    if (!channel || !ts) throw new Error('delivered Slack channel and timestamp required');
    return this.transaction(() => {
      const row = this.db.prepare('SELECT * FROM outbox WHERE id=?').get(id);
      if (!row) throw new Error('unknown outbox message');
      if (row.state === 'delivered') return { channel: row.channel, ts: row.ts, clientMsgId: row.client_msg_id };
      if (asRoot) {
        this.db.prepare('UPDATE outbox SET as_root=1 WHERE id=?').run(id);
        row.as_root = 1;
      }
      let conversationKeyValue = row.conversation_key;
      const conv = this.getConversation(row.conversation_key);
      if (row.as_root || !conv.root_ts) {
        const bound = conversationKey(conv.workspace, channel, ts);
        if (conv.key !== bound) {
          this._rekey(conv.key, bound);
          conversationKeyValue = bound;
        }
        this.db.prepare(`UPDATE conversations SET root_ts=?, channel=?, activated=1, updated_at=? WHERE key=?`)
          .run(ts, channel, Date.now(), conversationKeyValue);
      }
      this.db.prepare(`UPDATE outbox SET state='delivered', channel=?, ts=?, delivered_at=? WHERE id=?`)
        .run(channel, ts, Date.now(), id);
      if (row.id.startsWith('post:')) {
        const payload = parse(row.payload);
        this.recordMessage(conversationKeyValue, {
          id: row.id, role: 'assistant', text: payload.text || '', files: payload.files || [],
          team: conv.workspace, channel, ts,
        });
      }
      return { channel, ts, clientMsgId: row.client_msg_id, conversationKey: conversationKeyValue };
    });
  }

  markDeliveryFailed(id, error, { retryAt = null } = {}) {
    if (!error) throw new Error('delivery error required');
    return this.transaction(() => {
      const row = this.db.prepare('SELECT * FROM outbox WHERE id=?').get(id);
      if (!row) throw new Error('unknown outbox message');
      if (row.state === 'delivered') throw new Error('delivered outbox message cannot be retried');
      this.db.prepare(`UPDATE outbox SET attempts=attempts+1, last_error=?, next_retry_at=? WHERE id=?`)
        .run(String(error), retryAt, id);
      return this._outbox(this.db.prepare('SELECT * FROM outbox WHERE id=?').get(id));
    });
  }

  rememberPost(id, { channel, ts }) {
    if (!channel || !ts) throw new Error('posted Slack channel and timestamp required');
    return this.transaction(() => {
      const row = this.db.prepare('SELECT state FROM outbox WHERE id=?').get(id);
      if (!row) throw new Error('unknown outbox message');
      if (row.state !== 'pending') return false;
      this.db.prepare(`UPDATE outbox SET channel=?, ts=? WHERE id=? AND state='pending' AND ts IS NULL`)
        .run(channel, ts, id);
      return true;
    });
  }

  stopOutbox(id, error) {
    if (!error) throw new Error('delivery error required');
    return this.transaction(() => {
      const row = this.db.prepare('SELECT * FROM outbox WHERE id=?').get(id);
      if (!row) throw new Error('unknown outbox message');
      if (row.state === 'delivered') return this._outbox(row);
      this.db.prepare(`UPDATE outbox SET state='failed', last_error=?, next_retry_at=NULL WHERE id=?`)
        .run(String(error), id);
      return this._outbox(this.db.prepare('SELECT * FROM outbox WHERE id=?').get(id));
    });
  }

  _rekey(oldKey, newKey) {
    if (oldKey === newKey) return;
    if (this.db.prepare('SELECT key FROM conversations WHERE key=?').get(newKey)) {
      throw new Error('conversation key already exists');
    }
    const row = this.db.prepare('SELECT * FROM conversations WHERE key=?').get(oldKey);
    if (!row) throw new Error('unknown conversation');
    this.db.prepare(`INSERT INTO conversations(key, agent, workspace, channel, root_ts, activated, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`).run(newKey, row.agent, row.workspace, row.channel, row.root_ts, row.activated, Date.now());
    for (const table of ['messages', 'work', 'queue', 'outbox', 'conversation_sessions', 'live_status']) {
      this.db.prepare(`UPDATE ${table} SET conversation_key=? WHERE conversation_key=?`).run(newKey, oldKey);
    }
    // A key held outside this store (a payment's) still finds the conversation: every earlier key points at the newest.
    this.db.prepare('DELETE FROM conversation_moves WHERE old_key=?').run(newKey);
    this.db.prepare('UPDATE conversation_moves SET new_key=? WHERE new_key=?').run(newKey, oldKey);
    this.db.prepare('INSERT OR REPLACE INTO conversation_moves(old_key, new_key, moved_at) VALUES (?, ?, ?)').run(oldKey, newKey, Date.now());
    // Schedules keep their creation reference for routing; it must still satisfy the foreign key.
    this.db.prepare(`DELETE FROM conversations WHERE key=?
      AND NOT EXISTS (SELECT 1 FROM schedules WHERE conversation_key=?)`).run(oldKey, oldKey);
  }

  beginProactive({ id, agent, workspace, channel, payload, clientMsgId = null }) {
    if (!id || !agent || !workspace || !channel || !payload) throw new Error('proactive id, agent, workspace, channel and payload required');
    const key = `pending:${id}`;
    return this.transaction(() => {
      this.upsertConversation({ key, agent, workspace, channel, activated: true });
      const outboxId = `post:${id}`;
      this._enqueueOutbox({
        id: outboxId,
        conversationKey: key,
        payload,
        asRoot: true,
        clientMsgId: clientMsgId || outboxId,
      });
      return { conversationKey: key, outboxId, clientMsgId: clientMsgId || outboxId, activated: true };
    });
  }

  _schedule(row) {
    if (!row) return null;
    return { ...row, enabled: row.enabled === 1 };
  }

  upsertSchedule({ id, conversationKey: conversationKeyValue, workId = null, cadence, timezone, nextAt = null, enabled = true, note = null, report = null, subject = null, checkTool: tool = null }) {
    if (!id || !conversationKeyValue || !cadence || !timezone) {
      throw new Error('schedule id, conversation, cadence and timezone required');
    }
    const check = checkTool(tool);
    return this.transaction(() => {
      if (!this.getConversation(conversationKeyValue)) throw new Error('unknown conversation');
      if (workId && !this.getWork(workId)) throw new Error('unknown work');
      this.db.prepare(`INSERT INTO schedules
        (id, conversation_key, work_id, cadence, timezone, next_at, enabled, note, report, subject, check_tool, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET cadence=excluded.cadence, timezone=excluded.timezone,
          next_at=excluded.next_at, enabled=excluded.enabled, note=excluded.note, report=excluded.report,
          work_id=excluded.work_id, subject=excluded.subject, check_tool=excluded.check_tool,
          updated_at=excluded.updated_at`).run(
        id, conversationKeyValue, workId, cadence, timezone, nextAt, enabled ? 1 : 0, note, report, subject, check, Date.now(),
      );
      return this.getSchedule(id);
    });
  }

  fireSchedule({ schedule, nextAt, details }) {
    return this.transaction(() => {
      const wake = this.enqueueScheduleWake({
        id: `schedule:${schedule.id}:${schedule.next_at}`,
        conversationKey: schedule.conversation_key,
        scheduleId: schedule.id,
        workId: schedule.work_id,
        details,
      });
      const advanced = (wake.inserted || wake.reason === 'duplicate')
        && this.advanceSchedule(schedule.id, schedule.next_at, nextAt);
      return { ...wake, advanced };
    });
  }

  advanceSchedule(id, occurrence, nextAt) {
    return this.db.prepare(`UPDATE schedules SET next_at=COALESCE(?, next_at), enabled=COALESCE(?, enabled), updated_at=?
      WHERE id=? AND next_at=?`).run(nextAt, nextAt == null ? 0 : null, Date.now(), id, occurrence).changes === 1;
  }

  getSchedule(id) {
    return this._schedule(this.db.prepare('SELECT * FROM schedules WHERE id=?').get(id));
  }

  listSchedules() {
    return this.db.prepare('SELECT * FROM schedules ORDER BY id').all().map((row) => this._schedule(row));
  }

  pendingScheduleIds() {
    return this.db.prepare("SELECT payload FROM queue WHERE kind='schedule' AND state IN ('pending', 'running')")
      .all().map((row) => parse(row.payload).scheduleId);
  }

  dueSchedules(now = Date.now()) {
    return this.db.prepare(`SELECT * FROM schedules WHERE enabled=1 AND next_at IS NOT NULL AND next_at<=?
      ORDER BY next_at, id`).all(now).map((row) => this._schedule(row));
  }

  deleteSchedule(id) {
    return this.db.prepare('DELETE FROM schedules WHERE id=?').run(id).changes === 1;
  }

  setLiveStatus({ conversationKey: conversationKeyValue = null, channel, ts, system, agent, task, runId }) {
    if (!channel || !ts) throw new Error('live status channel and ts required');
    return this.transaction(() => {
      const row = this.getLiveStatus(channel, ts);
      if (!row && !conversationKeyValue) return null;
      const keep = (value, current) => (value === undefined ? current ?? null : value);
      const rev = this.db.prepare('SELECT COALESCE(MAX(rev), 0) + 1 AS rev FROM live_status').get().rev;
      this.db.prepare(`INSERT INTO live_status(channel, ts, conversation_key, system, agent, task, run_id, shown, rev, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)
        ON CONFLICT(channel, ts) DO UPDATE SET system=excluded.system, agent=excluded.agent, task=excluded.task,
          run_id=excluded.run_id, rev=excluded.rev, updated_at=excluded.updated_at`).run(
        channel, ts, row?.conversation_key ?? conversationKeyValue,
        keep(system, row?.system), keep(agent, row?.agent), keep(task, row?.task), keep(runId, row?.run_id),
        rev, Date.now(),
      );
      return this.getLiveStatus(channel, ts);
    });
  }

  getLiveStatus(channel, ts) {
    return this.db.prepare('SELECT * FROM live_status WHERE channel=? AND ts=?').get(channel, ts) || null;
  }

  liveStatusOfRun(runId) {
    return this.db.prepare('SELECT * FROM live_status WHERE run_id=?').get(runId) || null;
  }

  liveStatusesOfWork(workId) {
    return this.db.prepare(`SELECT l.* FROM live_status l JOIN runs r ON r.id=l.run_id JOIN queue q ON q.id=r.queue_id
      WHERE q.work_id=? ORDER BY l.rev`).all(workId);
  }

  setLiveShown(channel, ts, shown) {
    this.db.prepare('UPDATE live_status SET shown=? WHERE channel=? AND ts=?').run(json(shown), channel, ts);
  }

  getRun(runId) {
    return this.db.prepare(`SELECT r.*, q.conversation_key, q.work_id, q.kind
      FROM runs r JOIN queue q ON q.id=r.queue_id WHERE r.id=?`).get(runId) || null;
  }

  liveStatuses({ sinceRev = 0, conversationKey: conversationKeyValue = null } = {}) {
    return conversationKeyValue
      ? this.db.prepare('SELECT * FROM live_status WHERE rev>? AND conversation_key=? ORDER BY rev').all(sinceRev, conversationKeyValue)
      : this.db.prepare('SELECT * FROM live_status WHERE rev>? ORDER BY rev').all(sinceRev);
  }

  ownerTs(workId) {
    const row = this.db.prepare(`SELECT payload FROM queue WHERE work_id=? AND kind='owner'
      ORDER BY created_at DESC, id DESC LIMIT 1`).get(workId);
    return row ? parse(row.payload)?.ts || null : null;
  }
}

module.exports = { Store, conversationKey, checkTool, DISPOSITIONS, RETRY_DELAYS_MS, MAX_ATTEMPTS };

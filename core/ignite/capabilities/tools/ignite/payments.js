'use strict';

// The payment gate: the one place that decides whether an agent's payment may leave the account.
// Bank-neutral: a provider (a payment tool such as asaas) resolves the recipient, asks the gate,
// and sends only what the gate approved; the gate never calls a bank.
//
// API
// new Gate({ workspace, now?, timeZone?, currency?, busyMs? }) — opens <installation>/.rbtv/runtime/ignite/payments.sqlite
//   (the ledger) and reads the PIN from <installation>/.rbtv/config/ignite/payments-pin.json. timeZone (an IANA zone,
//   America/Sao_Paulo) sets the day, week and month; currency (an ISO 4217 code with two decimals, BRL) how amounts
//   read; busyMs (5000) bounds each wait for a ledger another process is writing, after which the call throws. A ledger
//   an earlier release created gains the columns added since in one transaction, every request and its history kept;
//   a current ledger opens without taking the write lock.
// close()
// MODES off | automatic | case_by_case.
// STATES pending | approved | sent | uncertain | refused | cancelled | failed. uncertain: the send may have paid (its
//   answer was lost, or the service stopped mid-send); it counts toward the limits until the provider's status
//   proves it sent or failed.
// PIN_RE — a PIN is 4 to 12 digits. settingsProblem(mode, limits) → null, or { field: 'mode', message }: a mode not in
//   MODES, or automatic with no limit set. The panel's form checks with these, so each rule has one home.
// settings() → { mode, limits: { day, week, month }, revision }, amounts in cents, null for no limit; off until saved
// saveSettings({ mode, limits, revision? }) — throws on a bad mode, on a limit outside 1 to MAX_LIMIT_CENTS, on automatic
//   with no limit set, and on a revision that is not the current one; each save adds one to the revision
// MAX_LIMIT_CENTS — the largest limit, 99999999999 (999999999.99): the most canonicalAmount writes and parseAmount reads.
// periodStart(period, at, zone?) — the start of the day, week (Monday) or month of `at` in zone (America/Sao_Paulo)
// usage(at?) → { day, week, month }: cents (amount plus fee) approved, sent or uncertain since each period started
// request({ agent, conversationKey, provider, method, recipient: { name, key, keyType, document, bank },
//   amountCents, feeCents?, note, details? }) → the row. Decided at once, in one transaction:
//   off → refused; case_by_case → pending; automatic → approved (decided_by rule) when the amount plus
//   fee fits every limit that is set, else pending. Automatic with no limit set (never saved so) waits.
// get(id) / list({ agent?, state?, limit? }) / pending() / listUncertain() / lastSent(n)
// resolved(id, { name, document, bank, key, keyType, amountCents, feeCents }) — the recipient as the service read it
//   from the provider, for a pending request; a key, amount or fee that differs from the request refuses it
//   (decided_by rule). resolveFailed(id, reason) — the service could not read it; the request stays pending and can
//   only be refused or withdrawn. → { changed, row }
// unchecked(row) → null once the service has resolved the request's recipient, else why the owner cannot approve it:
//   not resolved yet, or the resolution failed. One rule for the gate, the panel's buttons and the runner.
// approve(id, { interaction? }) / refuse(id, { interaction? }) — the owner's decision; only a pending request changes,
//   and approve changes only one that unchecked passes. → { changed, row, replay?, unchecked? }
// approveWithPin(id, pin, { interaction? }) → { replay } | { unknown } | { row } (not pending) | { unchecked, row }
//   (checked before the PIN, so it spends no try) | { pin: check, row } | { changed, row }.
//   saveSettingsWithPin({ mode, limits, revision }, pin, { interaction? }) → { replay } | { stale } |
//   { pin: check } | { saved }. Each runs in one transaction. interaction is the key of the owner's Slack
//   interaction: recorded once, so a replayed one changes nothing, a wrong PIN included. Only the key is kept.
// cancel(id, agent) — the requesting agent withdraws its own pending request. → { changed, row }
// claim(id) — marks an approved request as being sent; true once only, so it is sent at most once
// sent(id, { providerId, providerStatus?, receiptUrl? }) — the provider took it
// failed(id, reason) — the send did not happen; a request with a provider id or a withdrawal approval becomes
//   uncertain instead. uncertain(id, reason) — the send's outcome is unknown.
// checked(id, { providerStatus, receiptUrl, final, ok, reason? }) — a later read of a sent operation;
//   final and not ok fails the request
// reconciled(id, { found, providerId?, providerStatus?, receiptUrl?, final?, ok?, reason? }) — a read of an uncertain
//   request's operation: found, final and not ok fails it; found otherwise makes it sent; not found leaves it.
// interrupted() — each request claimed but never recorded (the service stopped mid-send) becomes uncertain → ids
// answer({ provider, method, reference, operationId, amountCents, recipientKey }) → { status, reason?, id }
//   The withdrawal validation, bank-neutral. The request is the one reference names or, with no reference, the
//   one whose recorded provider id is operationId. APPROVED only for a request of that provider and method that
//   the service claimed and is sending, has sent or is uncertain of; with the operation id the service recorded
//   when it has one, the same amount, and the same recipient (a request found by its recorded operation id may
//   pass with no recipient named). The first APPROVED records the operation, amount and recipient: a call
//   repeating exactly those is APPROVED again whatever the state now; any other call naming it is REFUSED.
// due({ now }) → { resolve, prompts, unshown, toSend, toCheck, toReconcile, toNotify }: the service's work lists
// promptPosted(id, { channel, ts }) — ts '-' when no thread can show it / promptShown(id, shown) / notified(id, state)
// PIN: pinSet() / setPin(pin) / checkPin(pin) → { ok } | { ok: false, locked, until } | { ok: false, left }
//   scrypt with a random salt; the PIN itself is never stored or logged. Five wrong PINs in a row lock
//   every PIN check for 15 minutes; a right PIN resets the count.
// gate.money(cents) / formatMoney(cents, currency) → "R$ 1.234,56": the currency's symbol, Brazilian notation.
// parseAmount(text) → cents or null ("99", "99.5", "99,50"; nine digits of whole units at most); canonicalAmount(cents)
//   → "1234.56", the one form a saved amount is written back in, which parseAmount reads for every limit.
// publicRow(row) — a request as the ignite payment verbs and the provider's tool read it.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');
const { runtimeFolder } = require('./memory-write.js');
const { timeZoneProblem, currencyProblem } = require('./config.js');

const MODES = Object.freeze(['off', 'automatic', 'case_by_case']);
const STATES = Object.freeze(['pending', 'approved', 'sent', 'uncertain', 'refused', 'cancelled', 'failed']);
// The states that hold money: they count toward the limits, and the withdrawal validation may approve them.
const HOLDING = Object.freeze(['approved', 'sent', 'uncertain']);
const PERIODS = Object.freeze(['day', 'week', 'month']);
const PERIOD_WORD = { day: 'daily', week: 'weekly', month: 'monthly' };
const DEFAULT_ZONE = 'America/Sao_Paulo';
const DEFAULT_CURRENCY = 'BRL';
const MAX_FAILURES = 5;
const LOCK_MS = 15 * 60_000;
const CHECK_EVERY_MS = 5_000;
const CHECK_FOR_MS = 10 * 60_000;
const RECONCILE_EVERY_MS = 60_000;
const SCRYPT = { N: 16384, r: 8, p: 1, keylen: 64 };
const PIN_RE = /^\d{4,12}$/;
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const MAX_LIMIT_CENTS = 99_999_999_999;
// The columns added after the ledger's first release; an older ledger gains them when it is opened.
const ADDED_COLUMNS = Object.freeze([
  ['resolved_at', 'INTEGER'], ['resolved_name', 'TEXT'], ['resolved_key', 'TEXT'], ['resolved_key_type', 'TEXT'],
  ['resolved_document', 'TEXT'], ['resolved_bank', 'TEXT'], ['resolved_amount_cents', 'INTEGER'],
  ['resolved_fee_cents', 'INTEGER'], ['resolve_error', 'TEXT'], ['answered_cents', 'INTEGER'], ['answered_recipient', 'TEXT'],
]);

function ledgerPath(workspace) {
  return path.join(runtimeFolder(workspace), 'payments.sqlite');
}

function pinPath(workspace) {
  return path.join(workspace, '.rbtv', 'config', 'ignite', 'payments-pin.json');
}

const MONEY = new Map();
function formatMoney(cents, currency = DEFAULT_CURRENCY) {
  if (cents == null) return '-';
  if (!MONEY.has(currency)) MONEY.set(currency, new Intl.NumberFormat('pt-BR', { style: 'currency', currency }));
  return MONEY.get(currency).format(Math.round(cents) / 100).replace(/\s/g, ' ');
}

// Nine digits of whole units at most: MAX_LIMIT_CENTS.
function parseAmount(text) {
  const match = String(text ?? '').trim().match(/^(\d{1,9})(?:[.,](\d{1,2}))?$/);
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] || '0').padEnd(2, '0'));
}

function canonicalAmount(cents) {
  if (cents == null) return null;
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;
}

function settingsProblem(mode, limits = {}) {
  if (!MODES.includes(mode)) return { field: 'mode', message: `mode must be one of ${MODES.join(', ')}` };
  if (mode === 'automatic' && PERIODS.every((p) => limits[p] == null)) {
    return { field: 'mode', message: 'automatic needs at least one limit: set a daily, weekly or monthly limit' };
  }
  return null;
}

// The wall-clock parts of `at` in a time zone.
const PARTS = new Map();
const WEEKDAYS = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };

function zoned(at, zone) {
  if (!PARTS.has(zone)) {
    PARTS.set(zone, new Intl.DateTimeFormat('en-US', {
      timeZone: zone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', weekday: 'short',
    }));
  }
  const parts = Object.fromEntries(PARTS.get(zone).formatToParts(new Date(at)).map((p) => [p.type, p.value]));
  return {
    year: Number(parts.year), month: Number(parts.month), day: Number(parts.day),
    hour: Number(parts.hour), minute: Number(parts.minute), second: Number(parts.second),
    weekday: WEEKDAYS[parts.weekday],
  };
}

// The instant the zone's wall clock reads year-month-day 00:00:00.
function zoneMidnight(year, month, day, zone) {
  const wall = Date.UTC(year, month - 1, day);
  let guess = wall;
  for (let i = 0; i < 3; i++) {
    const z = zoned(guess, zone);
    const shown = Date.UTC(z.year, z.month - 1, z.day, z.hour, z.minute, z.second);
    guess += wall - shown;
  }
  return guess;
}

function periodStart(period, at, zone = DEFAULT_ZONE) {
  const z = zoned(at, zone);
  if (period === 'day') return zoneMidnight(z.year, z.month, z.day, zone);
  if (period === 'week') {
    const monday = new Date(Date.UTC(z.year, z.month - 1, z.day - z.weekday));
    return zoneMidnight(monday.getUTCFullYear(), monday.getUTCMonth() + 1, monday.getUTCDate(), zone);
  }
  if (period === 'month') return zoneMidnight(z.year, z.month, 1, zone);
  throw new Error(`unknown period: ${period}`);
}

function refuse(message) {
  const error = new Error(message);
  error.exitCode = 1;
  throw error;
}

function text(value, label, { required = false, max = 500 } = {}) {
  if (value == null || value === '') {
    if (required) refuse(`${label} required`);
    return null;
  }
  if (typeof value !== 'string' || !value.trim()) refuse(`${label} must be text`);
  if (/[\r\n\0]/.test(value) && label !== 'note') refuse(`${label} must be one line`);
  if ([...value].length > max) refuse(`${label} is longer than ${max} characters`);
  return value.trim();
}

function cents(value, label, { min = 0, max = null } = {}) {
  if (!Number.isSafeInteger(value) || value < min) refuse(`${label} must be a whole number of cents, at least ${min}`);
  if (max != null && value > max) refuse(`${label} must be at most ${canonicalAmount(max)}`);
  return value;
}

function unchecked(row) {
  if (row.resolve_error != null) return `Ignite could not check its recipient through ${row.provider} (${row.resolve_error})`;
  if (row.resolved_at == null) return `Ignite has not checked its recipient through ${row.provider} yet`;
  return null;
}

// Text a provider's tool returned, kept as given (one line, bounded); not refused like an agent's input.
function plain(value, max = 500) {
  if (value == null || value === '') return null;
  return String(value).replace(/[\r\n\0]+/g, ' ').trim().slice(0, max) || null;
}

// The form a recipient key is compared in: digits only for a key with no letter or @ (CPF, CNPJ,
// phone, bill line), otherwise trimmed and lowercase (email, random key, QR code payload).
function canonicalKey(key) {
  const value = String(key ?? '').trim();
  if (!value) return '';
  if (!/[a-z@]/i.test(value)) return value.replace(/\D/g, '');
  return value.toLowerCase();
}

function publicRow(row) {
  if (!row) return null;
  return {
    id: row.id,
    agent: row.agent,
    conversation: row.conversation_key,
    provider: row.provider,
    method: row.method,
    recipient: {
      name: row.recipient_name,
      key: row.recipient_key,
      key_type: row.recipient_key_type,
      document: row.recipient_document,
      bank: row.recipient_bank,
    },
    amount_cents: row.amount_cents,
    fee_cents: row.fee_cents,
    note: row.note,
    details: JSON.parse(row.details || '{}'),
    state: row.state,
    reason: row.reason,
    decided_by: row.decided_by,
    decided_at: row.decided_at,
    resolved: row.resolved_at == null ? null : {
      name: row.resolved_name,
      key: row.resolved_key,
      key_type: row.resolved_key_type,
      document: row.resolved_document,
      bank: row.resolved_bank,
      amount_cents: row.resolved_amount_cents,
      fee_cents: row.resolved_fee_cents,
    },
    resolve_error: row.resolve_error,
    provider_id: row.provider_id,
    provider_status: row.provider_status,
    receipt_url: row.receipt_url,
    created_at: row.created_at,
  };
}

class Gate {
  constructor({ workspace, now = Date.now, dbPath = null, pinFile = null, timeZone = DEFAULT_ZONE, currency = DEFAULT_CURRENCY, busyMs = 5000 } = {}) {
    if (!workspace) throw new Error('installation path required');
    if (timeZoneProblem(timeZone)) throw new Error(`payments time zone ${timeZoneProblem(timeZone)}`);
    if (currencyProblem(currency)) throw new Error(`payments currency ${currencyProblem(currency)}`);
    this.workspace = workspace;
    this.now = now;
    this.timeZone = timeZone;
    this.currency = currency;
    this.pinFile = pinFile || pinPath(workspace);
    const file = dbPath || ledgerPath(workspace);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    this.db = new DatabaseSync(file);
    this._inTx = false;
    this.db.exec(`PRAGMA busy_timeout=${Math.max(0, Math.floor(busyMs))}; PRAGMA journal_mode=WAL;`);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS payments (
        seq INTEGER PRIMARY KEY,
        id TEXT NOT NULL UNIQUE,
        agent TEXT NOT NULL,
        conversation_key TEXT NOT NULL,
        provider TEXT NOT NULL,
        method TEXT NOT NULL,
        recipient_name TEXT,
        recipient_key TEXT NOT NULL,
        recipient_key_type TEXT,
        recipient_document TEXT,
        recipient_bank TEXT,
        amount_cents INTEGER NOT NULL,
        fee_cents INTEGER NOT NULL DEFAULT 0,
        note TEXT,
        details TEXT NOT NULL DEFAULT '{}',
        state TEXT NOT NULL,
        reason TEXT,
        decided_by TEXT,
        decided_at INTEGER,
        resolved_at INTEGER,
        resolved_name TEXT,
        resolved_key TEXT,
        resolved_key_type TEXT,
        resolved_document TEXT,
        resolved_bank TEXT,
        resolved_amount_cents INTEGER,
        resolved_fee_cents INTEGER,
        resolve_error TEXT,
        claimed_at INTEGER,
        provider_id TEXT,
        provider_status TEXT,
        receipt_url TEXT,
        sent_at INTEGER,
        checked_at INTEGER,
        check_final INTEGER NOT NULL DEFAULT 0,
        answered_at INTEGER,
        answered_operation TEXT,
        answered_cents INTEGER,
        answered_recipient TEXT,
        prompt_channel TEXT,
        prompt_ts TEXT,
        prompt_shown TEXT,
        notified TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS payments_state ON payments(state, decided_at);
      CREATE INDEX IF NOT EXISTS payments_operation ON payments(provider, provider_id);
      CREATE TABLE IF NOT EXISTS gate (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS interactions (
        key TEXT PRIMARY KEY,
        at INTEGER NOT NULL
      );
    `);
    // Read first, so that a current ledger needs no write lock to open.
    const missing = () => {
      const columns = this.db.prepare('PRAGMA table_info(payments)').all().map((column) => column.name);
      return ADDED_COLUMNS.filter(([name]) => !columns.includes(name));
    };
    if (missing().length) {
      this.transaction(() => {
        for (const [name, type] of missing()) this.db.exec(`ALTER TABLE payments ADD COLUMN ${name} ${type}`);
      });
    }
  }

  close() { this.db.close(); }

  money(amount) { return formatMoney(amount, this.currency); }

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

  _value(key) {
    const row = this.db.prepare('SELECT value FROM gate WHERE key=?').get(key);
    return row ? JSON.parse(row.value) : null;
  }

  _setValue(key, value) {
    this.db.prepare(`INSERT INTO gate(key, value, updated_at) VALUES (?, ?, ?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at`)
      .run(key, JSON.stringify(value), this.now());
  }

  // True the first time an interaction key is seen; the key alone is kept, never the payload it came in.
  _newInteraction(key) {
    return this.db.prepare('INSERT OR IGNORE INTO interactions(key, at) VALUES (?, ?)').run(String(key), this.now()).changes === 1;
  }

  settings() {
    const saved = this._value('settings');
    return {
      mode: MODES.includes(saved?.mode) ? saved.mode : 'off',
      limits: Object.fromEntries(PERIODS.map((p) => [p, Number.isSafeInteger(saved?.limits?.[p]) ? saved.limits[p] : null])),
      revision: Number.isSafeInteger(saved?.revision) ? saved.revision : 0,
    };
  }

  saveSettings({ mode, limits = {}, revision = null } = {}) {
    const clean = {};
    for (const period of PERIODS) {
      const value = limits[period];
      clean[period] = value == null ? null : cents(value, `${period} limit`, { min: 1, max: MAX_LIMIT_CENTS });
    }
    const problem = settingsProblem(mode, clean);
    if (problem) refuse(problem.message);
    return this.transaction(() => {
      const current = this.settings().revision;
      if (revision != null && revision !== current) {
        refuse(`the settings changed after this form was opened (revision ${revision}, now ${current}); nothing changed`);
      }
      this._setValue('settings', { mode, limits: clean, revision: current + 1 });
      return this.settings();
    });
  }

  periodStart(period, at = this.now()) {
    return periodStart(period, at, this.timeZone);
  }

  usage(at = this.now()) {
    const out = {};
    for (const period of PERIODS) {
      out[period] = this.db.prepare(`SELECT COALESCE(SUM(amount_cents + fee_cents), 0) AS used FROM payments
        WHERE state IN ('approved', 'sent', 'uncertain') AND decided_at >= ?`).get(periodStart(period, at, this.timeZone)).used;
    }
    return out;
  }

  // The rule's answer for a new amount, from the settings and the ledger.
  _decide(total, at) {
    const { mode, limits } = this.settings();
    if (mode === 'off') return { state: 'refused', reason: 'payments are off', by: 'rule' };
    if (mode === 'case_by_case') return { state: 'pending', reason: 'case by case: every payment waits for the owner' };
    if (PERIODS.every((p) => limits[p] == null)) return { state: 'pending', reason: 'automatic with no limit set' };
    const used = this.usage(at);
    for (const period of PERIODS) {
      const limit = limits[period];
      if (limit == null) continue;
      if (used[period] + total > limit) {
        const left = Math.max(0, limit - used[period]);
        return { state: 'pending', reason: `over the ${PERIOD_WORD[period]} limit (${this.money(left)} left of ${this.money(limit)})` };
      }
    }
    return { state: 'approved', reason: 'within the limits', by: 'rule' };
  }

  request(input = {}) {
    const agent = text(input.agent, 'agent', { required: true, max: 64 });
    if (!SLUG.test(agent)) refuse('agent must be a slug');
    const conversationKey = text(input.conversationKey, 'conversation', { required: true });
    const provider = text(input.provider, 'provider', { required: true, max: 64 });
    if (!SLUG.test(provider)) refuse('provider must be a slug');
    const method = text(input.method, 'method', { required: true, max: 32 });
    if (!SLUG.test(method)) refuse('method must be a slug');
    const recipient = input.recipient && typeof input.recipient === 'object' ? input.recipient : {};
    const key = text(recipient.key, 'recipient key', { required: true, max: 2000 });
    const amount = cents(input.amountCents, 'amount', { min: 1 });
    const fee = cents(input.feeCents ?? 0, 'fee');
    const note = text(input.note, 'note', { max: 500 });
    const details = input.details && typeof input.details === 'object' && !Array.isArray(input.details) ? input.details : {};
    return this.transaction(() => {
      const at = this.now();
      const decision = this._decide(amount + fee, at);
      const seq = this.db.prepare('SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM payments').get().seq;
      const id = `P-${String(seq).padStart(4, '0')}`;
      const decided = decision.state === 'pending' ? null : at;
      this.db.prepare(`INSERT INTO payments
        (seq, id, agent, conversation_key, provider, method, recipient_name, recipient_key, recipient_key_type,
         recipient_document, recipient_bank, amount_cents, fee_cents, note, details, state, reason,
         decided_by, decided_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
        seq, id, agent, conversationKey, provider, method,
        text(recipient.name, 'recipient name'), key, text(recipient.keyType, 'recipient key type', { max: 32 }),
        text(recipient.document, 'recipient document', { max: 64 }), text(recipient.bank, 'recipient bank'),
        amount, fee, note, JSON.stringify(details), decision.state, decision.reason,
        decision.by || null, decided, at, at,
      );
      return this._row(id);
    });
  }

  _row(id) {
    return this.db.prepare('SELECT * FROM payments WHERE id=?').get(id) || null;
  }

  get(id) { return this._row(id); }

  list({ agent = null, state = null, limit = 20 } = {}) {
    const where = [];
    const args = [];
    if (agent) { where.push('agent=?'); args.push(agent); }
    if (state) { where.push('state=?'); args.push(state); }
    return this.db.prepare(`SELECT * FROM payments ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
      ORDER BY seq DESC LIMIT ?`).all(...args, limit);
  }

  pending() {
    return this.db.prepare("SELECT * FROM payments WHERE state='pending' ORDER BY seq").all();
  }

  listUncertain() {
    return this.db.prepare("SELECT * FROM payments WHERE state='uncertain' ORDER BY seq").all();
  }

  lastSent(n = 10) {
    return this.db.prepare("SELECT * FROM payments WHERE state='sent' ORDER BY sent_at DESC, seq DESC LIMIT ?").all(n);
  }

  _move(id, from, to, fields = {}, where = '') {
    return this.transaction(() => {
      const names = Object.keys(fields);
      const sets = ['state=?', 'updated_at=?', ...names.map((name) => `${name}=?`)];
      const result = this.db.prepare(`UPDATE payments SET ${sets.join(', ')} WHERE id=? AND state=? ${where}`)
        .run(to, this.now(), ...names.map((name) => fields[name]), id, from);
      return { changed: result.changes === 1, row: this._row(id) };
    });
  }

  resolved(id, { name = null, document = null, bank = null, key = null, keyType = null, amountCents = null, feeCents = null } = {}) {
    return this.transaction(() => {
      const row = this._row(id);
      if (!row || row.state !== 'pending' || row.resolved_at != null) return { changed: false, row };
      const at = this.now();
      const amount = Number.isSafeInteger(amountCents) ? amountCents : null;
      const fee = Number.isSafeInteger(feeCents) ? feeCents : null;
      this.db.prepare(`UPDATE payments SET resolved_at=?, resolved_name=?, resolved_key=?, resolved_key_type=?,
        resolved_document=?, resolved_bank=?, resolved_amount_cents=?, resolved_fee_cents=?, updated_at=? WHERE id=?`)
        .run(at, plain(name), plain(key, 2000), plain(keyType, 32), plain(document, 64), plain(bank), amount, fee, at, id);
      const differs = [];
      if (!key || canonicalKey(key) !== canonicalKey(row.recipient_key)) differs.push(`the recipient key is ${plain(key, 2000) || 'not named'}, not ${row.recipient_key}`);
      if (amount != null && amount !== row.amount_cents) differs.push(`the amount is ${this.money(amount)}, not ${this.money(row.amount_cents)}`);
      if (fee != null && fee !== row.fee_cents) differs.push(`the fee is ${this.money(fee)}, not ${this.money(row.fee_cents)}`);
      if (!differs.length) return { changed: true, row: this._row(id) };
      return this._move(id, 'pending', 'refused', {
        decided_by: 'rule', decided_at: at,
        reason: `Ignite's own check through ${row.provider} differs from the request: ${differs.join('; ')}`.slice(0, 500),
      });
    });
  }

  resolveFailed(id, reason) {
    const result = this.db.prepare(`UPDATE payments SET resolve_error=?, updated_at=?
      WHERE id=? AND state='pending' AND resolved_at IS NULL AND resolve_error IS NULL`)
      .run(String(reason || 'failed').slice(0, 300), this.now(), id);
    return { changed: result.changes === 1, row: this._row(id) };
  }

  approve(id, { interaction = null } = {}) {
    return this.transaction(() => {
      if (interaction && !this._newInteraction(interaction)) return { changed: false, replay: true, row: this._row(id) };
      const row = this._row(id);
      const why = row?.state === 'pending' ? unchecked(row) : null;
      if (why) return { changed: false, unchecked: why, row };
      return this._move(id, 'pending', 'approved', { decided_by: 'owner', decided_at: this.now(), reason: 'approved by the owner' });
    });
  }

  refuse(id, { interaction = null } = {}) {
    return this.transaction(() => {
      if (interaction && !this._newInteraction(interaction)) return { changed: false, replay: true, row: this._row(id) };
      return this._move(id, 'pending', 'refused', { decided_by: 'owner', decided_at: this.now(), reason: 'refused by the owner' });
    });
  }

  approveWithPin(id, pin, { interaction = null } = {}) {
    return this.transaction(() => {
      if (interaction && !this._newInteraction(interaction)) return { replay: true, row: this._row(id) };
      const row = this._row(id);
      if (!row) return { unknown: true, row: null };
      if (row.state !== 'pending') return { changed: false, row };
      const why = unchecked(row);
      if (why) return { changed: false, unchecked: why, row };
      const check = this.checkPin(pin);
      if (!check.ok) return { pin: check, row };
      return this.approve(id);
    });
  }

  saveSettingsWithPin({ mode, limits, revision }, pin, { interaction = null } = {}) {
    return this.transaction(() => {
      if (interaction && !this._newInteraction(interaction)) return { replay: true };
      if (revision !== this.settings().revision) return { stale: true };
      const check = this.checkPin(pin);
      if (!check.ok) return { pin: check };
      return { saved: this.saveSettings({ mode, limits, revision }) };
    });
  }

  cancel(id, agent) {
    return this.transaction(() => {
      const row = this._row(id);
      if (!row || row.agent !== agent) refuse(`unknown payment request: ${id}`);
      if (row.state !== 'pending') refuse(`${id} is ${row.state}: only a pending request can be withdrawn`);
      return this._move(id, 'pending', 'cancelled', { reason: 'withdrawn by the agent' });
    });
  }

  claim(id) {
    return this.db.prepare(`UPDATE payments SET claimed_at=?, updated_at=?
      WHERE id=? AND state='approved' AND claimed_at IS NULL`).run(this.now(), this.now(), id).changes === 1;
  }

  sent(id, { providerId, providerStatus = null, receiptUrl = null } = {}) {
    if (!providerId) throw new Error('provider id required');
    return this._move(id, 'approved', 'sent', {
      provider_id: String(providerId), provider_status: providerStatus, receipt_url: receiptUrl, sent_at: this.now(),
    }, 'AND claimed_at IS NOT NULL');
  }

  failed(id, reason) {
    return this.transaction(() => {
      const row = this._row(id);
      if (!row || !['approved', 'sent'].includes(row.state)) return { changed: false, row };
      const why = String(reason || 'failed').slice(0, 500);
      // A provider id or a withdrawal approval means the money may have left: only the provider's status proves not.
      if (row.provider_id || row.answered_at != null) return this._move(id, row.state, 'uncertain', { reason: why });
      return this._move(id, row.state, 'failed', { reason: why });
    });
  }

  uncertain(id, reason) {
    return this._move(id, 'approved', 'uncertain', { reason: String(reason || 'the send\'s outcome is unknown').slice(0, 500) },
      'AND claimed_at IS NOT NULL');
  }

  checked(id, { providerStatus = null, receiptUrl = null, final = false, ok = true, reason = null } = {}) {
    return this.transaction(() => {
      const row = this._row(id);
      if (!row || row.state !== 'sent') return { changed: false, row };
      this.db.prepare(`UPDATE payments SET provider_status=COALESCE(?, provider_status),
        receipt_url=COALESCE(?, receipt_url), checked_at=?, check_final=?, updated_at=? WHERE id=?`)
        .run(providerStatus, receiptUrl, this.now(), final ? 1 : 0, this.now(), id);
      if (final && !ok) {
        return this._move(id, 'sent', 'failed', { reason: reason || `the provider ended it as ${providerStatus}` });
      }
      return { changed: true, row: this._row(id) };
    });
  }

  reconciled(id, { found = false, providerId = null, providerStatus = null, receiptUrl = null, final = false, ok = true, reason = null } = {}) {
    return this.transaction(() => {
      const row = this._row(id);
      if (!row || row.state !== 'uncertain') return { changed: false, row };
      const at = this.now();
      if (!found) {
        this.db.prepare('UPDATE payments SET checked_at=?, updated_at=? WHERE id=?').run(at, at, id);
        return { changed: false, row: this._row(id) };
      }
      const operation = String(providerId || row.provider_id || row.answered_operation);
      if (final && !ok) {
        return this._move(id, 'uncertain', 'failed', {
          provider_id: operation, provider_status: providerStatus, checked_at: at, check_final: 1,
          reason: reason || `the provider ended it as ${providerStatus}`,
        });
      }
      return this._move(id, 'uncertain', 'sent', {
        provider_id: operation, provider_status: providerStatus, receipt_url: receiptUrl || row.receipt_url,
        sent_at: at, checked_at: at, check_final: final ? 1 : 0,
        reason: row.decided_by === 'owner' ? 'approved by the owner' : 'within the limits',
      });
    });
  }

  interrupted() {
    const rows = this.db.prepare("SELECT id FROM payments WHERE state='approved' AND claimed_at IS NOT NULL").all();
    for (const { id } of rows) {
      this._move(id, 'approved', 'uncertain', {
        reason: 'interrupted: Ignite stopped while sending it, so it may have been paid; it counts toward the limits until Ignite reads it at the provider',
      });
    }
    return rows.map((row) => row.id);
  }

  answer({ provider, method, reference, operationId, amountCents, recipientKey } = {}) {
    const operation = operationId == null || operationId === '' ? null : String(operationId);
    if (!reference && !operation) {
      return { status: 'REFUSED', reason: 'the operation names no request and has no id: it did not pass the payment gate', id: null };
    }
    return this.transaction(() => {
      const row = reference
        ? this._row(String(reference))
        : this.db.prepare('SELECT * FROM payments WHERE provider=? AND provider_id=?').get(provider, operation) || null;
      const no = (reason) => ({ status: 'REFUSED', reason, id: row?.id || null });
      if (!row || row.provider !== provider) {
        return no(reference ? `unknown request ${reference}`
          : `no request names operation ${operation}: it did not pass the payment gate, or Ignite has not recorded its id yet`);
      }
      if (row.method !== method) return no(`${row.id} is a ${row.method} payment, not ${method}`);
      const recipient = recipientKey ? canonicalKey(recipientKey) : null;
      if (row.answered_at != null) {
        const same = operation != null && operation === row.answered_operation
          && amountCents === row.answered_cents && recipient === row.answered_recipient;
        return same ? { status: 'APPROVED', id: row.id, again: true }
          : no(`${row.id} was already approved for operation ${row.answered_operation}; this call differs from it`);
      }
      if (!HOLDING.includes(row.state)) return no(`${row.id} is ${row.state}`);
      if (row.claimed_at == null) return no(`${row.id} is approved but Ignite has not sent it`);
      if (row.provider_id && operation !== row.provider_id) {
        return no(`${row.id} was sent as operation ${row.provider_id}, not ${operation}`);
      }
      if (amountCents !== row.amount_cents) {
        return no(`${row.id} approved ${this.money(row.amount_cents)}, the operation is ${this.money(amountCents)}`);
      }
      if (recipient == null) {
        if (!row.provider_id) return no(`the operation names no recipient, and ${row.id} has no operation id to match it by`);
      } else if (recipient !== canonicalKey(row.recipient_key)) {
        return no(`${row.id} approved another recipient`);
      }
      this.db.prepare(`UPDATE payments SET answered_at=?, answered_operation=?, answered_cents=?, answered_recipient=?,
        updated_at=? WHERE id=?`).run(this.now(), operation, amountCents, recipient, this.now(), row.id);
      return { status: 'APPROVED', id: row.id };
    });
  }

  due({ now = this.now() } = {}) {
    const all = (sql, ...args) => this.db.prepare(sql).all(...args);
    return {
      resolve: all("SELECT * FROM payments WHERE state='pending' AND resolved_at IS NULL AND resolve_error IS NULL ORDER BY seq"),
      prompts: all(`SELECT * FROM payments WHERE state='pending' AND prompt_ts IS NULL
        AND (resolved_at IS NOT NULL OR resolve_error IS NOT NULL) ORDER BY seq`),
      unshown: all(`SELECT * FROM payments WHERE prompt_ts IS NOT NULL AND prompt_ts != '-'
        AND COALESCE(prompt_shown, '') != state ORDER BY seq`),
      toSend: all("SELECT * FROM payments WHERE state='approved' AND claimed_at IS NULL ORDER BY seq"),
      toCheck: all(`SELECT * FROM payments WHERE state='sent' AND check_final=0 AND sent_at>=?
        AND COALESCE(checked_at, sent_at)<=? ORDER BY seq`, now - CHECK_FOR_MS, now - CHECK_EVERY_MS),
      toReconcile: all(`SELECT * FROM payments WHERE state='uncertain' AND COALESCE(provider_id, answered_operation) IS NOT NULL
        AND COALESCE(checked_at, 0)<=? ORDER BY seq`, now - RECONCILE_EVERY_MS),
      toNotify: all(`SELECT * FROM payments WHERE COALESCE(notified, '') != state AND (
          (state='refused' AND (decided_by='owner' OR resolved_at IS NOT NULL)) OR state IN ('failed', 'uncertain')
          OR (state='sent' AND (check_final=1 OR sent_at<?))
        ) ORDER BY seq`, now - CHECK_FOR_MS),
    };
  }

  promptPosted(id, { channel, ts }) {
    this.db.prepare('UPDATE payments SET prompt_channel=?, prompt_ts=?, prompt_shown=?, updated_at=? WHERE id=? AND prompt_ts IS NULL')
      .run(channel, ts, 'pending', this.now(), id);
  }

  promptShown(id, shown) {
    this.db.prepare('UPDATE payments SET prompt_shown=?, updated_at=? WHERE id=?').run(shown, this.now(), id);
  }

  notified(id, state) {
    this.db.prepare('UPDATE payments SET notified=?, updated_at=? WHERE id=?').run(state, this.now(), id);
  }

  pinSet() {
    return fs.existsSync(this.pinFile);
  }

  setPin(pin) {
    if (this.pinSet()) refuse('the PIN is already set');
    if (typeof pin !== 'string' || !PIN_RE.test(pin)) refuse('the PIN must be 4 to 12 digits');
    const salt = crypto.randomBytes(16);
    const hash = crypto.scryptSync(pin, salt, SCRYPT.keylen, { N: SCRYPT.N, r: SCRYPT.r, p: SCRYPT.p });
    const record = { algorithm: 'scrypt', N: SCRYPT.N, r: SCRYPT.r, p: SCRYPT.p, salt: salt.toString('hex'), hash: hash.toString('hex') };
    fs.mkdirSync(path.dirname(this.pinFile), { recursive: true });
    const temp = `${this.pinFile}.${process.pid}.tmp`;
    fs.writeFileSync(temp, `${JSON.stringify(record)}\n`, { encoding: 'utf8', mode: 0o600 });
    fs.renameSync(temp, this.pinFile);
  }

  _pinMatches(pin) {
    const record = JSON.parse(fs.readFileSync(this.pinFile, 'utf8'));
    if (record.algorithm !== 'scrypt') throw new Error('unknown PIN record');
    const want = Buffer.from(record.hash, 'hex');
    const got = crypto.scryptSync(String(pin), Buffer.from(record.salt, 'hex'), want.length,
      { N: record.N, r: record.r, p: record.p });
    return got.length === want.length && crypto.timingSafeEqual(got, want);
  }

  checkPin(pin) {
    if (!this.pinSet()) return { ok: false, unset: true };
    return this.transaction(() => {
      const at = this.now();
      const state = this._value('pin') || { failures: 0, lockedUntil: 0 };
      if (state.lockedUntil > at) return { ok: false, locked: true, until: state.lockedUntil };
      if (this._pinMatches(pin)) {
        this._setValue('pin', { failures: 0, lockedUntil: 0 });
        return { ok: true };
      }
      const failures = (state.lockedUntil && state.lockedUntil <= at ? 0 : state.failures) + 1;
      if (failures >= MAX_FAILURES) {
        const until = at + LOCK_MS;
        this._setValue('pin', { failures: 0, lockedUntil: until });
        return { ok: false, locked: true, until };
      }
      this._setValue('pin', { failures, lockedUntil: 0 });
      return { ok: false, left: MAX_FAILURES - failures };
    });
  }
}

module.exports = {
  Gate, MODES, STATES, PERIODS, PIN_RE, MAX_LIMIT_CENTS, DEFAULT_ZONE, DEFAULT_CURRENCY, MAX_FAILURES, LOCK_MS,
  CHECK_EVERY_MS, CHECK_FOR_MS, RECONCILE_EVERY_MS, ledgerPath, pinPath, periodStart, formatMoney, parseAmount,
  canonicalAmount, settingsProblem, unchecked, canonicalKey, publicRow,
};

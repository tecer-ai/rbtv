#!/usr/bin/env node
'use strict';

// Suite for the payment gate: payments.js (settings, limits, ledger and its upgrade, PIN), payment-panel.js (the
// owner's Slack panel and buttons), payment-runner.js (resolving, sending, reconciling, reporting),
// payment-webhook.js (the withdrawal validation, with the asaas connector's adapter) and the ignite
// payment verbs. Injected clock, stand-in Slack and stand-in provider tool; the webhook listens on
// 127.0.0.1 with a free port. No network beyond the loopback.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { Gate, periodStart, formatMoney, parseAmount, canonicalAmount, pinPath, ledgerPath } = require('./payments.js');
const { createPaymentPanel, promptBlocks, ACTION, VIEW } = require('./payment-panel.js');
const { createPaymentRunner } = require('./payment-runner.js');
const { createWebhook, validate, loadProvider } = require('./payment-webhook.js');
const { Slack } = require('./slack.js');
const { Store } = require('./store.js');
const { main } = require('./cli.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

const PIN = '482913';
const TOKEN = 'whk-test-token';
const KEY = 'T1:C1:1.1';
const ASAAS = loadProvider('asaas');
const at = (iso) => Date.parse(iso);

function scratch() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-pay-'));
}

function gateAt(iso, workspace = scratch(), options = {}) {
  const clock = { now: at(iso) };
  const gate = new Gate({ workspace, now: () => clock.now, ...options });
  return { gate, clock, workspace };
}

function ask(gate, fields = {}) {
  return gate.request({
    agent: 'sara', conversationKey: KEY, provider: 'asaas', method: 'pix',
    recipient: { name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', keyType: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' },
    amountCents: 1000, note: 'Owed to Kenu', ...fields,
  });
}

// What asaas pay resolve reports for the request ask() makes: the same owner, read from the bank.
const KENU = { name: 'KENU EXAMPLE SILVA', document: '***.123.456-**', bank: 'Nubank', key: 'kenu@example.com', keyType: 'EMAIL' };

// A request the service is sending: approved by rule, claimed, recorded as sent with provider id tr_1.
function sentRequest(gate, fields = {}) {
  gate.saveSettings({ mode: 'automatic', limits: { month: 1_000_000 } });
  const row = ask(gate, fields);
  assert.equal(row.state, 'approved');
  assert.equal(gate.claim(row.id), true);
  gate.sent(row.id, { providerId: 'tr_1', providerStatus: 'PENDING' });
  return gate.get(row.id);
}

const config = { slack: { team: 'T1', ownerUserId: 'UOWNER' }, payments: {} };

// fail: { method: [n, ...] } — the nth call of that method (from 1) throws, as a Slack call that failed.
function fakeSlack({ fail = {} } = {}) {
  const calls = [];
  const counts = {};
  const record = (method) => async (...args) => {
    calls.push({ method, args });
    counts[method] = (counts[method] || 0) + 1;
    if ((fail[method] || []).includes(counts[method])) throw new Error(`Slack ${method} failed: not_found`);
    if (method === 'postBlocks') return { channel: args[0].channel, ts: `9.${calls.length}` };
    if (method === 'openView' || method === 'pushView' || method === 'updateView') return { viewId: 'V-new' };
    return { ok: true };
  };
  const client = {};
  for (const method of ['openView', 'pushView', 'updateView', 'postEphemeral', 'postBlocks', 'updateMessage']) client[method] = record(method);
  return { client, calls };
}

function panelFor(gate, { slack = fakeSlack(), kicks = [] } = {}) {
  const panel = createPaymentPanel({
    gate: () => gate, slack: () => slack.client, config: () => config, kick: () => kicks.push(1),
  });
  return { panel, slack, kicks };
}

// One interaction as the socket runs it: the ACK's payload first, then the processing.
async function interact(panel, type, payload) {
  const acked = panel.ack(type, payload);
  await panel.handle(type, payload);
  return acked;
}

const slash = (user = 'UOWNER', team = 'T1') => ({ command: '/payments', user_id: user, team_id: team, trigger_id: 'trig-1', channel_id: 'C1' });
function action(actionId, value, { user = 'UOWNER', team = 'T1', view = null, ts = '1.1' } = {}) {
  return {
    type: 'block_actions', user: { id: user, team_id: team }, team: { id: team }, trigger_id: 'trig-2',
    ...(view ? { view } : { channel: { id: 'C1' } }), actions: [{ action_id: actionId, value, action_ts: ts }],
  };
}
function submission(callbackId, values, { user = 'UOWNER', team = 'T1', metadata = '', id = 'V1', root = 'V1', hash = 'h1' } = {}) {
  return {
    type: 'view_submission', user: { id: user, team_id: team }, team: { id: team },
    view: { id, hash, root_view_id: root, callback_id: callbackId, private_metadata: metadata, state: { values } },
  };
}
const pinValue = (pin) => ({ payments_pin: { value: { type: 'plain_text_input', value: pin } } });
function settingsValues(mode, limits, pin) {
  const values = { ...pinValue(pin), payments_mode: { value: { type: 'radio_buttons', selected_option: { value: mode } } } };
  for (const period of ['day', 'week', 'month']) values[`payments_${period}`] = { value: { type: 'plain_text_input', value: limits[period] ?? null } };
  return values;
}
const CHECKING = { response_action: 'update', view: { type: 'modal', callback_id: VIEW.done, title: { type: 'plain_text', text: 'Payments' },
  close: { type: 'plain_text', text: 'Close' }, blocks: [{ type: 'section', text: { type: 'mrkdwn', text: 'Checking…' } }] } };
const viewText = (view) => view.blocks.map((b) => b.text?.text || b.elements?.map((e) => e.text).join(' ') || '').join('\n');

// ───────────────────────────── the gate's rules

test('off refuses: the default mode, decided by rule', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  assert.deepEqual(gate.settings(), { mode: 'off', limits: { day: null, week: null, month: null }, revision: 0 });
  const row = ask(gate);
  assert.equal(row.id, 'P-0001');
  assert.equal(row.state, 'refused');
  assert.equal(row.reason, 'payments are off');
  assert.equal(row.decided_by, 'rule');
});

test('case by case always waits, even within every limit', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: { day: 1_000_000 } });
  const row = ask(gate, { amountCents: 1 });
  assert.equal(row.state, 'pending');
  assert.equal(row.reason, 'case by case: every payment waits for the owner');
  assert.equal(row.decided_by, null);
  assert.equal(row.decided_at, null);
});

test('automatic with no limit is refused on save and the settings stay', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  assert.throws(() => gate.saveSettings({ mode: 'automatic', limits: { day: null, week: null, month: null } }),
    /^Error: automatic needs at least one limit: set a daily, weekly or monthly limit$/);
  assert.equal(gate.settings().mode, 'case_by_case');
  assert.throws(() => gate.saveSettings({ mode: 'automatic', limits: { week: 0 } }), /week limit must be a whole number of cents, at least 1/);
  assert.deepEqual(gate.saveSettings({ mode: 'automatic', limits: { week: 15000 } }),
    { mode: 'automatic', limits: { day: null, week: 15000, month: null }, revision: 2 });
});

test('over a limit waits, naming what is left of which limit (the specification example)', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { week: 15000 } });
  assert.equal(ask(gate, { amountCents: 7000 }).state, 'approved');
  const row = ask(gate, { amountCents: 9900 });
  assert.equal(row.state, 'pending');
  assert.equal(row.reason, 'over the weekly limit (R$ 80,00 left of R$ 150,00)');
});

test('a blank limit does not count; the set one does', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: null, week: 15000, month: null } });
  assert.equal(ask(gate, { amountCents: 14000 }).state, 'approved');
  const row = ask(gate, { amountCents: 2000 });
  assert.equal(row.reason, 'over the weekly limit (R$ 10,00 left of R$ 150,00)');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  assert.equal(ask(gate, { amountCents: 50000 }).state, 'approved');
});

test('periods start at Sao Paulo midnight, weeks on Monday, months on the first', () => {
  const iso = (t) => new Date(t).toISOString();
  assert.equal(iso(periodStart('day', at('2026-10-15T02:59:59Z'))), '2026-10-14T03:00:00.000Z');
  assert.equal(iso(periodStart('day', at('2026-10-15T03:00:00Z'))), '2026-10-15T03:00:00.000Z');
  assert.equal(iso(periodStart('week', at('2026-10-19T02:59:59Z'))), '2026-10-12T03:00:00.000Z');
  assert.equal(iso(periodStart('week', at('2026-10-19T03:00:00Z'))), '2026-10-19T03:00:00.000Z');
  assert.equal(iso(periodStart('month', at('2026-11-01T02:59:59Z'))), '2026-10-01T03:00:00.000Z');
  assert.equal(iso(periodStart('month', at('2026-11-01T03:00:00Z'))), '2026-11-01T03:00:00.000Z');
});

test('the daily limit renews at Sao Paulo midnight, not UTC midnight', () => {
  const { gate, clock } = gateAt('2026-10-15T02:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 1000 } });
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  clock.now = at('2026-10-15T02:59:59Z');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the daily limit (R$ 0,00 left of R$ 10,00)');
  clock.now = at('2026-10-15T03:00:00Z');
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  assert.deepEqual(gate.usage(), { day: 1000, week: 2000, month: 2000 });
});

test('the weekly limit renews on Monday at Sao Paulo midnight', () => {
  const { gate, clock } = gateAt('2026-10-19T02:59:59Z');
  gate.saveSettings({ mode: 'automatic', limits: { week: 1000 } });
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  assert.equal(ask(gate, { amountCents: 1 }).state, 'pending');
  clock.now = at('2026-10-19T03:00:00Z');
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the weekly limit (R$ 0,00 left of R$ 10,00)');
});

test('the monthly limit renews on the first at Sao Paulo midnight', () => {
  const { gate, clock } = gateAt('2026-11-01T02:59:59Z');
  gate.saveSettings({ mode: 'automatic', limits: { month: 1000 } });
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  clock.now = at('2026-11-01T03:00:00Z');
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the monthly limit (R$ 0,00 left of R$ 10,00)');
});

test('the time zone and the currency come from the config: periods in that zone, amounts in that currency', () => {
  const { gate, clock } = gateAt('2026-10-15T02:00:00Z', scratch(), { timeZone: 'UTC', currency: 'USD' });
  gate.saveSettings({ mode: 'automatic', limits: { day: 1000 } });
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  clock.now = at('2026-10-15T23:59:59Z');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the daily limit (US$ 0,00 left of US$ 10,00)');
  clock.now = at('2026-10-16T00:00:00Z');
  assert.equal(new Date(gate.periodStart('day')).toISOString(), '2026-10-16T00:00:00.000Z');
  assert.equal(ask(gate, { amountCents: 1000 }).state, 'approved');
  assert.throws(() => new Gate({ workspace: scratch(), timeZone: 'Mars/Base' }),
    /^Error: payments time zone must be an IANA time zone, such as America\/Sao_Paulo$/);
  assert.throws(() => new Gate({ workspace: scratch(), currency: 'JPY' }),
    /^Error: payments currency must be a currency with two decimals: amounts are kept in hundredths$/);
});

test('limits count approved, sent and uncertain amounts with their fee, not pending, refused, cancelled or failed', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const waiting = ask(gate, { amountCents: 100 });
  const refused = ask(gate, { amountCents: 200 });
  const cancelled = ask(gate, { amountCents: 400 });
  gate.refuse(refused.id);
  gate.cancel(cancelled.id, 'sara');
  const approved = ask(gate, { amountCents: 800, feeCents: 99 });
  gate.resolved(approved.id, KENU);
  gate.approve(approved.id);
  const failing = ask(gate, { amountCents: 1600 });
  gate.resolved(failing.id, KENU);
  gate.approve(failing.id);
  gate.failed(failing.id, 'Asaas answered HTTP 400');
  const unsure = ask(gate, { amountCents: 3200 });
  gate.resolved(unsure.id, KENU);
  gate.approve(unsure.id);
  gate.claim(unsure.id);
  gate.uncertain(unsure.id, 'the answer was lost');
  assert.equal(gate.get(waiting.id).state, 'pending');
  assert.equal(gate.get(failing.id).state, 'failed');
  assert.deepEqual(gate.usage(), { day: 4099, week: 4099, month: 4099 });
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  assert.equal(ask(gate, { amountCents: 901 }).state, 'approved');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the daily limit (R$ 0,00 left of R$ 50,00)');
});

test('a bill counts its fee toward the limits', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const line = '23793381286001234107143000012345890460000002000';
  gate.saveSettings({ mode: 'automatic', limits: { day: 2198 } });
  const over = ask(gate, { method: 'bill', recipient: { name: 'ENEL', key: line }, amountCents: 2000, feeCents: 199 });
  assert.equal(over.state, 'pending');
  assert.equal(over.reason, 'over the daily limit (R$ 21,98 left of R$ 21,98)');
  gate.saveSettings({ mode: 'automatic', limits: { day: 2199 } });
  assert.equal(ask(gate, { method: 'bill', recipient: { name: 'ENEL', key: line }, amountCents: 2000, feeCents: 199 }).state, 'approved');
  assert.deepEqual(gate.usage(), { day: 2199, week: 2199, month: 2199 });
});

test('only a pending request is approved or refused, once', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  assert.equal(gate.approve(row.id).changed, true);
  assert.equal(gate.approve(row.id).changed, false);
  assert.equal(gate.refuse(row.id).changed, false);
  assert.equal(gate.get(row.id).state, 'approved');
  assert.equal(gate.get(row.id).decided_by, 'owner');
  assert.equal(gate.claim(row.id), true);
  assert.equal(gate.claim(row.id), false);
});

test('amounts are shown in the currency and read back in one form at any size', () => {
  assert.equal(formatMoney(123456), 'R$ 1.234,56');
  assert.equal(formatMoney(5), 'R$ 0,05');
  assert.equal(formatMoney(-1250), '-R$ 12,50');
  assert.equal(parseAmount('150'), 15000);
  assert.equal(parseAmount('150,5'), 15050);
  assert.equal(parseAmount('0.01'), 1);
  assert.equal(parseAmount('1.234,00'), null);
  assert.equal(parseAmount(''), null);
  for (const [cents, form] of [[100000, '1000.00'], [1234567, '12345.67'], [5, '0.05'], [null, null]]) {
    assert.equal(canonicalAmount(cents), form);
    if (form != null) assert.equal(parseAmount(form), cents);
  }
});

// The ledger as the payment gate's first release created it (rbtv 4c7d95c6): no resolution, retry or interaction
// columns and no interactions table.
const FIRST_LEDGER = `
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
        claimed_at INTEGER,
        provider_id TEXT,
        provider_status TEXT,
        receipt_url TEXT,
        sent_at INTEGER,
        checked_at INTEGER,
        check_final INTEGER NOT NULL DEFAULT 0,
        answered_at INTEGER,
        answered_operation TEXT,
        prompt_channel TEXT,
        prompt_ts TEXT,
        prompt_shown TEXT,
        notified TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS payments_state ON payments(state, decided_at);
      CREATE TABLE IF NOT EXISTS gate (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at INTEGER NOT NULL
      );
`;
const ADDED = ['resolved_at', 'resolved_name', 'resolved_key', 'resolved_key_type', 'resolved_document', 'resolved_bank',
  'resolved_amount_cents', 'resolved_fee_cents', 'resolve_error', 'answered_cents', 'answered_recipient'];

// A first-release ledger with its history: P-0001 sent and answered, P-0002 pending and posted, P-0003 approved by
// the owner and not sent yet (that release approved before any check), and the settings and PIN lockout it saved.
function firstLedger(workspace) {
  const file = ledgerPath(workspace);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const old = new DatabaseSync(file);
  old.exec('PRAGMA journal_mode=WAL;');
  old.exec(FIRST_LEDGER);
  const t = at('2026-10-14T12:00:00Z');
  const insert = old.prepare(`INSERT INTO payments (seq, id, agent, conversation_key, provider, method, recipient_name,
    recipient_key, recipient_key_type, amount_cents, note, state, reason, decided_by, decided_at, claimed_at, provider_id,
    provider_status, receipt_url, sent_at, check_final, answered_at, answered_operation, prompt_channel, prompt_ts,
    prompt_shown, notified, created_at, updated_at) VALUES (?, ?, 'sara', '${KEY}', 'asaas', 'pix', 'KENU', 'kenu@example.com',
    'EMAIL', ?, 'Owed to Kenu', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'C1', ?, ?, ?, ?, ?)`);
  insert.run(1, 'P-0001', 1000, 'sent', 'approved by the owner', 'owner', t, t, 'tr_1', 'DONE', 'https://r.example/1', t, 1, t + 5000, 'tr_1', '9.1', 'sent', 'sent', t, t + 5000);
  insert.run(2, 'P-0002', 2000, 'pending', 'case by case: every payment waits for the owner', null, null, null, null, null, null, null, 0, null, null, '9.2', 'pending', null, t, t);
  insert.run(3, 'P-0003', 3000, 'approved', 'approved by the owner', 'owner', t, null, null, null, null, null, 0, null, null, '9.3', 'pending', null, t, t);
  const value = old.prepare('INSERT INTO gate(key, value, updated_at) VALUES (?, ?, ?)');
  value.run('settings', '{"mode":"case_by_case","limits":{"day":null,"week":15000,"month":null}}', t);
  value.run('pin', '{"failures":2,"lockedUntil":0}', t);
  const rows = old.prepare('SELECT * FROM payments ORDER BY seq').all().map((row) => ({ ...row }));
  old.close();
  return rows;
}

test('a ledger the first release created gains the new columns when opened and keeps every request and its history', () => {
  const workspace = scratch();
  const before = firstLedger(workspace);
  const { gate } = gateAt('2026-10-15T15:00:00Z', workspace);
  const columns = gate.db.prepare('PRAGMA table_info(payments)').all().map((c) => c.name);
  assert.deepEqual(columns.slice(0, 34), Object.keys(before[0]));
  assert.deepEqual(columns.slice(34), ADDED);
  const after = gate.db.prepare('SELECT * FROM payments ORDER BY seq').all();
  // The pending prompt was posted with the agent's recipient and an Approve button: the upgrade redraws it.
  before[1].prompt_shown = null;
  assert.deepEqual(after.map((row) => [row.id, row.state, row.decided_by, row.provider_id, row.answered_operation, row.prompt_ts, row.notified]), [
    ['P-0001', 'sent', 'owner', 'tr_1', 'tr_1', '9.1', 'sent'],
    ['P-0002', 'pending', null, null, null, '9.2', null],
    ['P-0003', 'approved', 'owner', null, null, '9.3', null],
  ]);
  assert.deepEqual(after.map((row) => Object.fromEntries(Object.keys(before[0]).map((name) => [name, row[name]]))), before);
  assert.deepEqual(after.map((row) => ADDED.filter((name) => row[name] !== null)), [[], [], []]);
  assert.deepEqual(gate.settings(), { mode: 'case_by_case', limits: { day: null, week: 15000, month: null }, revision: 0 });
  assert.equal(gate.db.prepare("SELECT value FROM gate WHERE key='pin'").get().value, '{"failures":2,"lockedUntil":0}');
  assert.equal(gate.db.prepare('SELECT COUNT(*) AS n FROM interactions').get().n, 0);
  // The re-review's probe: the service's first pass read a column the old ledger lacked.
  const work = gate.due();
  assert.deepEqual([work.resolve.map((r) => r.id), work.toSend.map((r) => r.id), work.unshown.map((r) => r.id)], [['P-0002'], ['P-0003'], ['P-0002', 'P-0003']]);
  assert.deepEqual(gate.usage(), { day: 0, week: 4000, month: 4000 });
  gate.resolved('P-0002', KENU);
  assert.equal(gate.approve('P-0002').changed, true);
  gate.close();
  const again = new Gate({ workspace });
  assert.equal(again.db.prepare('PRAGMA table_info(payments)').all().length, 45);
  assert.deepEqual(again.list({ limit: 5 }).map((row) => [row.id, row.state]), [['P-0003', 'approved'], ['P-0002', 'approved'], ['P-0001', 'sent']]);
  again.close();
});

test('a limit is accepted, shown and read back up to 999999999.99, and refused above it', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  assert.throws(() => gate.saveSettings({ mode: 'automatic', limits: { day: 100_000_000_000 } }), /^Error: day limit must be at most 999999999\.99$/);
  assert.equal(gate.settings().revision, 0);
  gate.saveSettings({ mode: 'automatic', limits: { day: 99_999_999_999, week: 1 } });
  const { panel, slack } = panelFor(gate);
  await interact(panel, 'interactive', action(ACTION.settings, 'settings'));
  const form = slack.calls[0].args[1];
  assert.deepEqual(form.blocks.filter((b) => /^payments_(day|week|month)$/.test(b.block_id)).map((b) => [b.block_id, b.element.initial_value ?? null, b.element.max_length]),
    [['payments_day', '999999999.99', 12], ['payments_week', '0.01', 12], ['payments_month', null, 12]]);
  const unchanged = settingsValues('automatic', { day: '999999999.99', week: '0.01' }, PIN);
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.settings, unchanged, { metadata: form.private_metadata })), CHECKING);
  assert.equal(slack.calls[1].args[1].blocks[0].text.text, 'Saved: Automatic within the limits; limits today R$ 999.999.999,99, this week R$ 0,01.');
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: 99_999_999_999, week: 1, month: null }, revision: 2 });
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '1000000000.00' }, PIN), { metadata: '{"revision":2}', hash: 'over' })),
    { response_action: 'errors', errors: { payments_day: 'Write an amount like 1500.00.' } });
  assert.deepEqual([parseAmount('999999999.99'), parseAmount('1000000000'), canonicalAmount(99_999_999_999)], [99_999_999_999, null, '999999999.99']);
});

// ───────────────────────────── the PIN

test('the PIN is kept only as a salted scrypt hash', () => {
  const one = gateAt('2026-10-15T15:00:00Z').gate;
  const two = gateAt('2026-10-15T15:00:00Z').gate;
  one.setPin(PIN);
  two.setPin(PIN);
  const a = fs.readFileSync(one.pinFile, 'utf8');
  const b = fs.readFileSync(two.pinFile, 'utf8');
  assert.equal(a.includes(PIN), false);
  const record = JSON.parse(a);
  assert.deepEqual(Object.keys(record), ['algorithm', 'N', 'r', 'p', 'salt', 'hash']);
  assert.equal(record.algorithm, 'scrypt');
  assert.match(record.salt, /^[0-9a-f]{32}$/);
  assert.match(record.hash, /^[0-9a-f]{128}$/);
  assert.notEqual(JSON.parse(b).salt, record.salt);
  assert.notEqual(JSON.parse(b).hash, record.hash);
  assert.equal(one.pinFile, pinPath(one.workspace));
  assert.equal(one.pinFile.endsWith(path.join('.rbtv', 'config', 'ignite', 'payments-pin.json')), true);
  assert.deepEqual(one.checkPin(PIN), { ok: true });
  const ledger = fs.readFileSync(path.join(one.workspace, '.rbtv', 'runtime', 'ignite', 'payments.sqlite'));
  assert.equal(ledger.includes(PIN), false);
  assert.throws(() => one.setPin('111111'), /the PIN is already set/);
  assert.throws(() => gateAt('2026-10-15T15:00:00Z').gate.setPin('12ab'), /the PIN must be 4 to 12 digits/);
});

test('five wrong PINs in a row lock every PIN check for 15 minutes; a right PIN resets the count', () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  for (const left of [4, 3, 2, 1]) assert.deepEqual(gate.checkPin('000000'), { ok: false, left });
  assert.deepEqual(gate.checkPin(PIN), { ok: true });
  assert.deepEqual(gate.checkPin('000000'), { ok: false, left: 4 });
  for (const left of [3, 2, 1]) assert.deepEqual(gate.checkPin('000000'), { ok: false, left });
  const until = at('2026-10-15T15:15:00Z');
  assert.deepEqual(gate.checkPin('000000'), { ok: false, locked: true, until });
  clock.now = at('2026-10-15T15:14:59Z');
  assert.deepEqual(gate.checkPin(PIN), { ok: false, locked: true, until });
  clock.now = until;
  assert.deepEqual(gate.checkPin(PIN), { ok: true });
});

// ───────────────────────────── the owner's panel and buttons

test('anyone but the owner is refused on every action and nothing changes', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const { panel, slack } = panelFor(gate);
  assert.deepEqual(await interact(panel, 'slash_commands', slash('UOTHER')), { text: 'Only the owner can open /payments. Nothing changed.' });
  assert.deepEqual(await interact(panel, 'slash_commands', slash('UOWNER', 'T2')), { text: 'Only the owner can open /payments. Nothing changed.' });
  for (const id of [ACTION.approve, ACTION.refuse, ACTION.settings]) {
    assert.equal(await interact(panel, 'interactive', action(id, row.id, { user: 'UOTHER' })), null);
  }
  assert.deepEqual(slack.calls.map((c) => c.method), ['postEphemeral', 'postEphemeral', 'postEphemeral']);
  assert.deepEqual(slack.calls[0].args[0], { channel: 'C1', user: 'UOTHER', text: 'Only the owner can approve or refuse payments. Nothing changed.' });
  const refusal = { response_action: 'errors', errors: { payments_pin: 'Only the owner can do this. Nothing changed.' } };
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { user: 'UOTHER', metadata: row.id })), refusal);
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '500' }, PIN), { user: 'UOTHER' })), refusal);
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { team: 'T2', metadata: row.id })), refusal);
  assert.equal(gate.get(row.id).state, 'pending');
  assert.equal(gate.settings().mode, 'case_by_case');
  assert.equal(slack.calls.length, 3);
});

test('/payments asks for a PIN on first use, then opens the panel', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const { panel, slack } = panelFor(gate);
  assert.equal(await interact(panel, 'slash_commands', slash()), null);
  assert.equal(slack.calls[0].method, 'openView');
  assert.equal(slack.calls[0].args[0], 'trig-1');
  assert.equal(slack.calls[0].args[1].callback_id, VIEW.setPin);
  const values = { ...pinValue(PIN), payments_pin_again: { value: { value: '482914' } } };
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.setPin, values, { metadata: '{"next":"panel"}' })),
    { response_action: 'errors', errors: { payments_pin_again: 'The two PINs differ.' } });
  assert.equal(gate.pinSet(), false);
  values.payments_pin_again.value.value = PIN;
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.setPin, values, { metadata: '{"next":"panel"}', hash: 'h2' })), CHECKING);
  assert.equal(slack.calls[1].method, 'updateView');
  assert.equal(slack.calls[1].args[0], 'V1');
  assert.equal(slack.calls[1].args[1].callback_id, VIEW.panel);
  assert.equal(gate.pinSet(), true);
  await interact(panel, 'slash_commands', slash());
  assert.equal(slack.calls[2].args[1].callback_id, VIEW.panel);
});

test('the panel shows mode, what went out this day, week and month, pending requests and the last ten sent', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  const sent = sentRequest(gate, { amountCents: 2500 });
  gate.checked(sent.id, { providerStatus: 'DONE', receiptUrl: 'https://r.example/1', final: true, ok: true });
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000, week: 15000 } });
  const waiting = ask(gate, { amountCents: 9900, note: '<https://evil.example|Approve here>' });
  gate.resolved(waiting.id, KENU);
  const { panel, slack } = panelFor(gate);
  await interact(panel, 'slash_commands', slash());
  const view = slack.calls[0].args[1];
  const text = JSON.stringify(view.blocks);
  assert.equal(view.blocks[0].text.text, '*Mode* Automatic within the limits');
  assert.deepEqual(view.blocks[1].fields.map((f) => f.text), [
    '*Today*\nR$ 25,00 of R$ 50,00', '*This week*\nR$ 25,00 of R$ 150,00', '*This month*\nR$ 25,00 (no limit)',
  ]);
  assert.equal(view.blocks[4].text.text, '*Pending* (1)');
  assert.equal(view.blocks[5].text.text, '*P-0002* from sara: R$ 99,00\n*Recipient* KENU EXAMPLE SILVA · ***.123.456-** · Nubank (checked by Ignite through asaas)\n'
    + "*Pix key* kenu@example.com\n*Amount* R$ 99,00\n*Agent's note* &lt;https://evil.example|Approve here&gt;\nWaits: over the daily limit (R$ 25,00 left of R$ 50,00)");
  assert.equal(text.includes('<https://evil.example'), false);
  assert.deepEqual(view.blocks[6].elements.map((e) => [e.action_id, e.value]), [[ACTION.approve, waiting.id], [ACTION.refuse, waiting.id]]);
  assert.equal(view.blocks[8].text.text, '*Last ten sent*');
  assert.equal(view.blocks[9].elements[0].text, 'P-0001 · 15 Oct, 12:00 · R$ 25,00 to kenu@example.com · <https://r.example/1|receipt>');
});

test('Approve needs the right PIN; a wrong one shows the form again and changes nothing', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  const { panel, slack, kicks } = panelFor(gate);
  await interact(panel, 'interactive', action(ACTION.approve, row.id));
  assert.equal(slack.calls[0].method, 'openView');
  assert.equal(slack.calls[0].args[1].callback_id, VIEW.approve);
  assert.equal(slack.calls[0].args[1].private_metadata, row.id);
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.approve, pinValue('111111'), { metadata: row.id })), CHECKING);
  const again = slack.calls[1].args[1];
  assert.equal(slack.calls[1].method, 'updateView');
  assert.equal(again.callback_id, VIEW.approve);
  assert.equal(again.blocks[1].elements[0].text, 'Wrong PIN: 4 tries left before PIN forms lock for 15 minutes. Nothing changed.');
  assert.equal(gate.get(row.id).state, 'pending');
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id, hash: 'h2' })), CHECKING);
  assert.equal(slack.calls[2].args[1].blocks[0].text.text,
    "Approved P-0001: R$ 10,00 to KENU EXAMPLE SILVA. Ignite is sending it now; the result arrives in sara's thread.");
  assert.equal(kicks.length, 1);
  const approved = gate.get(row.id);
  assert.equal(approved.state, 'approved');
  assert.equal(approved.decided_by, 'owner');
  assert.equal(approved.decided_at, at('2026-10-15T15:00:00Z'));
});

test('after five wrong PINs, approvals and settings are locked for 15 minutes', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  const { panel, slack } = panelFor(gate);
  let n = 0;
  const approve = async (pin) => {
    n += 1;
    await interact(panel, 'interactive', submission(VIEW.approve, pinValue(pin), { metadata: row.id, hash: `h${n}` }));
    return viewText(slack.calls.at(-1).args[1]);
  };
  for (let i = 0; i < 4; i++) await approve('111111');
  const locked = 'Locked after five wrong PINs until 12:15. Nothing changed.';
  assert.equal((await approve('111111')).includes(locked), true);
  assert.equal((await approve(PIN)).includes(locked), true);
  await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '50' }, PIN), { metadata: '{"revision":1}', hash: 'hs' }));
  assert.equal(viewText(slack.calls.at(-1).args[1]).includes(locked), true);
  assert.equal(gate.get(row.id).state, 'pending');
  assert.equal(gate.settings().mode, 'case_by_case');
  clock.now = at('2026-10-15T15:15:00Z');
  assert.equal((await approve(PIN)).startsWith('Approved P-0001'), true);
  assert.equal(gate.get(row.id).state, 'approved');
});

test('settings: field problems answer in the form at once; saving needs the PIN', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  const { panel, slack } = panelFor(gate);
  const submit = (mode, limits, pin, hash) => interact(panel, 'interactive',
    submission(VIEW.settings, settingsValues(mode, limits, pin), { id: 'V2', root: 'V1', metadata: '{"revision":0}', hash }));
  assert.deepEqual(await submit('automatic', {}, PIN, 'a'),
    { response_action: 'errors', errors: { payments_mode: 'Automatic needs at least one limit: set a daily, weekly or monthly limit.' } });
  assert.deepEqual(await submit('automatic', { week: 'abc' }, PIN, 'b'),
    { response_action: 'errors', errors: { payments_week: 'Write an amount like 1500.00.' } });
  assert.equal(slack.calls.length, 0);
  assert.deepEqual(await submit('automatic', { week: '150' }, '111111', 'c'), CHECKING);
  const again = slack.calls[0].args[1];
  assert.equal(again.blocks[0].elements[0].text, 'Wrong PIN: 4 tries left before PIN forms lock for 15 minutes. Nothing changed.');
  assert.equal(again.blocks[1].element.initial_option.value, 'automatic');
  assert.equal(again.blocks[3].element.initial_value, '150.00');
  assert.equal(again.private_metadata, '{"revision":0}');
  assert.equal(gate.settings().mode, 'off');
  await submit('automatic', { week: '150,00' }, PIN, 'd');
  assert.equal(slack.calls[1].args[0], 'V2');
  assert.equal(slack.calls[1].args[1].blocks[0].text.text, 'Saved: Automatic within the limits; limits this week R$ 150,00.');
  assert.equal(slack.calls[2].args[0], 'V1');
  assert.equal(slack.calls[2].args[1].callback_id, VIEW.panel);
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: null, week: 15000, month: null }, revision: 1 });
});

test('limits round-trip through the settings form at any size, and blank stays no limit', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000, week: 1234567, month: null } });
  const { panel, slack } = panelFor(gate);
  await interact(panel, 'interactive', action(ACTION.settings, 'settings'));
  const form = slack.calls[0].args[1];
  const shown = Object.fromEntries(form.blocks.filter((b) => /^payments_(day|week|month)$/.test(b.block_id))
    .map((b) => [b.block_id, b.element.initial_value ?? null]));
  assert.deepEqual(shown, { payments_day: '1000.00', payments_week: '12345.67', payments_month: null });
  const unchanged = settingsValues('automatic', { day: shown.payments_day, week: shown.payments_week, month: shown.payments_month }, PIN);
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.settings, unchanged, { metadata: form.private_metadata })), CHECKING);
  assert.equal(slack.calls[1].args[1].blocks[0].text.text, 'Saved: Automatic within the limits; limits today R$ 1.000,00, this week R$ 12.345,67.');
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: 100000, week: 1234567, month: null }, revision: 2 });
});

test('a settings form carries its revision: a submission from before the last save changes nothing', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'automatic', limits: { day: 10000 } });
  const { panel, slack } = panelFor(gate);
  await interact(panel, 'interactive', action(ACTION.settings, 'settings', { ts: '2.1' }));
  await interact(panel, 'interactive', action(ACTION.settings, 'settings', { ts: '2.2' }));
  const older = slack.calls[0].args[1].private_metadata;
  assert.equal(older, '{"revision":1}');
  await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '10.00' }, PIN),
    { metadata: slack.calls[1].args[1].private_metadata, hash: 'lower' }));
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: 1000, week: null, month: null }, revision: 2 });
  assert.deepEqual(await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '100.00' }, PIN),
    { metadata: older, hash: 'old' })), CHECKING);
  assert.equal(slack.calls.at(-1).args[1].blocks[0].text.text,
    'The settings changed after this form was opened. Nothing changed: open Change settings again to see them.');
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: 1000, week: null, month: null }, revision: 2 });
  assert.throws(() => gate.saveSettings({ mode: 'off', limits: {}, revision: 1 }),
    /^Error: the settings changed after this form was opened \(revision 1, now 2\); nothing changed$/);
});

test('each owner interaction is recorded once: a replay changes nothing, a wrong PIN counts once, and only its key is kept', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const one = ask(gate);
  const two = ask(gate);
  gate.resolved(one.id, KENU);
  const { panel, slack } = panelFor(gate);
  const wrong = submission(VIEW.approve, pinValue('111111'), { metadata: one.id, hash: 'wrong' });
  for (let i = 0; i < 5; i++) await interact(panel, 'interactive', wrong);
  assert.equal(slack.calls.at(-1).args[1].blocks[0].text.text, 'P-0001 is pending. This form was already submitted: nothing changed.');
  assert.deepEqual(gate.checkPin('000000'), { ok: false, left: 3 });
  const right = submission(VIEW.approve, pinValue(PIN), { metadata: one.id, hash: 'right' });
  await interact(panel, 'interactive', right);
  assert.equal(gate.get(one.id).state, 'approved');
  const refuse = action(ACTION.refuse, two.id, { ts: '5.5' });
  await interact(panel, 'interactive', refuse);
  assert.equal(gate.get(two.id).state, 'refused');
  await interact(panel, 'interactive', refuse);
  assert.deepEqual(slack.calls.at(-1).args[0], { channel: 'C1', user: 'UOWNER', text: 'P-0002: this click was already handled. Nothing changed.' });
  const kept = gate.db.prepare('SELECT key FROM interactions ORDER BY key').all().map((r) => r.key);
  assert.deepEqual(kept, ['action:5.5:payments_refuse:P-0002', 'view:V1:right', 'view:V1:wrong']);
  assert.equal(fs.readFileSync(ledgerPath(gate.workspace)).includes(PIN), false);
  assert.equal(fs.readFileSync(`${ledgerPath(gate.workspace)}-wal`).includes(PIN), false);
});

test('Refuse on a thread message refuses at once and needs no PIN', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const { panel, slack, kicks } = panelFor(gate);
  await interact(panel, 'interactive', action(ACTION.refuse, row.id));
  assert.equal(gate.get(row.id).state, 'refused');
  assert.equal(gate.get(row.id).decided_by, 'owner');
  assert.equal(kicks.length, 1);
  assert.deepEqual(slack.calls, []);
  await interact(panel, 'interactive', action(ACTION.approve, row.id, { ts: '1.2' }));
  assert.equal(slack.calls[0].args[1].blocks[0].text.text, 'P-0001 is refused: nothing to approve.');
});

test('the thread message has Approve and Refuse while pending, and its outcome after', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate, { amountCents: 9900 });
  gate.resolved(row.id, KENU);
  const blocks = promptBlocks(gate, gate.get(row.id));
  assert.equal(blocks[0].text.text, '*Payment request P-0001* from sara\n*Recipient* KENU EXAMPLE SILVA · ***.123.456-** · Nubank (checked by Ignite through asaas)\n'
    + "*Pix key* kenu@example.com\n*Amount* R$ 99,00\n*Agent's note* Owed to Kenu");
  assert.equal(blocks[1].elements[0].text, 'Waits for you: case by case: every payment waits for the owner');
  assert.deepEqual(blocks[2].elements.map((e) => e.action_id), [ACTION.approve, ACTION.refuse]);
  gate.refuse(row.id);
  const after = promptBlocks(gate, gate.get(row.id));
  assert.equal(after.length, 2);
  assert.equal(after[1].elements[0].text, 'Refused by you.');
});

test('an approval or refusal the ledger holds is shown as done when a Slack view update fails, never as nothing changed', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  for (let i = 0; i < 3; i++) gate.resolved(ask(gate).id, KENU);
  // views.update calls: 1 the first approval's outcome (fails), 2 its fallback, 3 the second approval's outcome,
  // 4 the panel under it (fails), 5 the panel after a refusal (fails), 6 its fallback, 7 a saved setting (fails), 8 its fallback.
  const slack = fakeSlack({ fail: { updateView: [1, 4, 5, 7] } });
  const { panel, kicks } = panelFor(gate, { slack });
  const shown = () => slack.calls.filter((c) => c.method === 'updateView').map((c) => [c.args[0], viewText(c.args[1])]);
  // The re-review's probe: a valid approval whose first update fails and whose second succeeds.
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: 'P-0001', hash: 'a' }));
  assert.equal(gate.get('P-0001').state, 'approved');
  assert.deepEqual(gate.due().toSend.map((r) => r.id), ['P-0001']);
  assert.equal(kicks.length, 1);
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: 'P-0002', id: 'V2', root: 'V1', hash: 'b' }));
  await interact(panel, 'interactive', action(ACTION.refuse, 'P-0003', { view: { id: 'V1' }, ts: '7.1' }));
  assert.equal(gate.get('P-0003').state, 'refused');
  await interact(panel, 'interactive', submission(VIEW.settings, settingsValues('automatic', { day: '50' }, PIN), { metadata: '{"revision":1}', id: 'V3', root: 'V3', hash: 'c' }));
  assert.deepEqual(gate.settings().limits.day, 5000);
  const approved = (id, to) => `Approved ${id}: R$ 10,00 to ${to}. Ignite is sending it now; the result arrives in sara's thread.`;
  assert.deepEqual(shown().filter((_, i) => [1, 2, 5, 7].includes(i)), [
    ['V1', `${approved('P-0001', 'KENU EXAMPLE SILVA')} The panel could not refresh; reopen /payments to see it.`],
    ['V2', approved('P-0002', 'KENU EXAMPLE SILVA')],
    ['V1', 'Refused P-0003. The panel could not refresh; reopen /payments to see it.'],
    ['V3', 'Saved: Automatic within the limits; limits today R$ 50,00. The panel could not refresh; reopen /payments to see it.'],
  ]);
  assert.equal(shown().length, 8);
  assert.equal(JSON.stringify(slack.calls).includes('Nothing changed'), false);
});

// ───────────────────────────── exactly once

test('an approval is sent exactly once: double click, replayed interaction, overlapping passes', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  const runs = [];
  // Two runners on the same ledger stand for two passes that overlap: only the claim keeps them apart.
  const runnerOf = () => createPaymentRunner({
    gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace, now: () => gate.now(),
    run: async (command, args, input) => {
      runs.push({ command, args, input: JSON.parse(input) });
      await new Promise((resolve) => setTimeout(resolve, 20));
      return { code: 0, stdout: '{"provider_id":"tr_1","status":"PENDING","receipt_url":null}\n', stderr: '' };
    },
  });
  const runner = runnerOf();
  const other = runnerOf();
  const { panel, slack: fake } = panelFor(gate);
  // The owner clicks Approve twice: two PIN forms. Both are submitted.
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id, id: 'V1', hash: 'a' }));
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id, id: 'V2', hash: 'b' }));
  assert.equal(fake.calls[0].args[1].blocks[0].text.text.startsWith('Approved P-0001'), true);
  assert.equal(fake.calls[1].args[1].blocks[0].text.text, 'P-0001 is approved: nothing to approve.');
  // Slack redelivers the same envelope over the socket: acked each time, processed as a replay.
  const ws = [];
  class FakeWS {
    constructor() { this.sent = []; this.listeners = {}; ws.push(this); }
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.closed = true; }
    emit(data) { for (const fn of this.listeners.message || []) fn({ data: JSON.stringify(data) }); }
  }
  const slack = new Slack({
    botToken: 'xoxb-test', appToken: 'xapp-test', WebSocket: FakeWS, log() {},
    fetch: async (url) => ({ ok: true, status: 200, json: async () => (String(url).endsWith('auth.test')
      ? { ok: true, team_id: 'T1', user_id: 'UBOT', bot_id: 'BBOT' } : { ok: true, url: 'wss://example.test/1' }) }),
  });
  await slack.connect(async () => {}, panel);
  const envelope = { type: 'interactive', envelope_id: 'env-9', accepts_response_payload: true,
    payload: submission(VIEW.approve, pinValue(PIN), { metadata: row.id, id: 'V3', hash: 'c' }) };
  ws[0].emit(envelope);
  await slack.pending;
  ws[0].emit(envelope);
  await slack.pending;
  assert.deepEqual(ws[0].sent, [{ envelope_id: 'env-9', payload: CHECKING }, { envelope_id: 'env-9', payload: CHECKING }]);
  assert.deepEqual(fake.calls.filter((c) => c.args[0] === 'V3').map((c) => c.args[1].blocks[0].text.text),
    ['P-0001 is approved: nothing to approve.', 'P-0001 is approved. This form was already submitted: nothing changed.']);
  await Promise.all([runner.step(), other.step(), runner.step()]);
  await runner.step();
  await other.step();
  assert.equal(runs.length, 1);
  assert.deepEqual(runs[0].args, ['--json', 'pay', 'execute', 'P-0001']);
  assert.equal(runs[0].command, 'asaas');
  assert.equal(runs[0].input.state, 'approved');
  assert.equal(gate.get(row.id).state, 'sent');
  slack.stop();
});

// ───────────────────────────── the runner

function agentStore() {
  const dir = scratch();
  const store = new Store(path.join(dir, 'state.sqlite'));
  store.acceptOwnerInput({
    key: KEY, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
    message: { id: 'T1:C1:1.1', role: 'owner', text: 'pay Kenu', team: 'T1', channel: 'C1', ts: '1.1' },
  });
  return store;
}

const wakes = (store) => store.db.prepare("SELECT payload FROM queue WHERE kind='wake' ORDER BY rowid").all().map((r) => JSON.parse(r.payload).note);

// A stand-in for the asaas tool: answers each verb from a table and records each run.
function tool(answers) {
  const runs = [];
  const run = async (command, args, input) => {
    runs.push({ command, args, input: JSON.parse(input) });
    const answer = answers[args[2]];
    const next = Array.isArray(answer) ? answer.shift() : answer;
    if (!next) throw new Error(`no stand-in answer for ${args[2]}`);
    return { stderr: '', ...next, stdout: typeof next.stdout === 'object' ? `${JSON.stringify(next.stdout)}\n` : (next.stdout || '') };
  };
  return { runs, run };
}
const RESOLVED_KENU = { code: 0, stdout: { name: 'KENU EXAMPLE SILVA', document: '***.123.456-**', bank: 'Nubank', key: 'kenu@example.com', key_type: 'EMAIL', amount_cents: null, fee_cents: null } };

test('the runner resolves a pending request, posts it in its thread, then shows its outcome and wakes the conversation', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const store = agentStore();
  const slack = fakeSlack();
  const kicked = [];
  const stand = tool({ resolve: RESOLVED_KENU });
  const runner = createPaymentRunner({
    gate, slack: () => slack.client, store: () => store, providers: ['asaas'], cwd: gate.workspace,
    run: stand.run, kick: (slug) => kicked.push(slug),
  });
  await runner.step();
  assert.deepEqual(stand.runs.map((r) => r.args), [['--json', 'pay', 'resolve', 'P-0001']]);
  assert.equal(slack.calls.length, 1);
  const post = slack.calls[0].args[0];
  assert.equal(post.channel, 'C1');
  assert.equal(post.threadTs, '1.1');
  assert.equal(post.text, 'Payment request P-0001 from sara: R$ 10,00 to KENU EXAMPLE SILVA (pending)');
  assert.deepEqual(post.blocks.at(-1).elements.map((e) => [e.action_id, e.value]), [[ACTION.approve, 'P-0001'], [ACTION.refuse, 'P-0001']]);
  await runner.step();
  assert.equal(slack.calls.length, 1);
  gate.refuse(row.id);
  await runner.step();
  assert.equal(slack.calls[1].method, 'updateMessage');
  assert.equal(slack.calls[1].args[0].ts, '9.1');
  assert.equal(slack.calls[1].args[0].blocks.some((b) => b.type === 'actions'), false);
  assert.deepEqual(wakes(store), ['Payment P-0001 was refused by the owner: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). Nothing was sent.']);
  assert.deepEqual(kicked, ['sara']);
  await runner.step();
  assert.equal(wakes(store).length, 1);
});

test('the service resolves the recipient itself: the thread and the panel show what it resolved, the agent\'s words only as a note', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  ask(gate, { recipient: { name: 'KENU EXAMPLE SILVA', key: 'evil@example.com', keyType: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' } });
  const store = agentStore();
  const slack = fakeSlack();
  const stand = tool({ resolve: { code: 0, stdout: { name: 'EVIL CORP LTDA', document: '**.999.999/0001-**', bank: 'Banco Y', key: 'evil@example.com', key_type: 'EMAIL', amount_cents: null, fee_cents: null } } });
  const runner = createPaymentRunner({ gate, slack: () => slack.client, store: () => store, providers: ['asaas'], cwd: gate.workspace, run: stand.run });
  await runner.step();
  assert.deepEqual(stand.runs[0].input.recipient, { name: 'KENU EXAMPLE SILVA', key: 'evil@example.com', key_type: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' });
  const shown = '*Recipient* EVIL CORP LTDA · **.999.999/0001-** · Banco Y (checked by Ignite through asaas)\n*Pix key* evil@example.com\n*Amount* R$ 10,00\n'
    + "_The agent's own description, not checked:_ KENU EXAMPLE SILVA · ***.123.456-** · Nubank\n*Agent's note* Owed to Kenu";
  const post = slack.calls[0].args[0];
  assert.equal(post.text, 'Payment request P-0001 from sara: R$ 10,00 to EVIL CORP LTDA (pending)');
  assert.equal(post.blocks[0].text.text, `*Payment request P-0001* from sara\n${shown}`);
  const { panel, slack: owner } = panelFor(gate);
  await interact(panel, 'slash_commands', slash());
  assert.equal(owner.calls[0].args[1].blocks[5].text.text, `*P-0001* from sara: R$ 10,00\n${shown}\nWaits: case by case: every payment waits for the owner`);
  await interact(panel, 'interactive', action(ACTION.approve, 'P-0001'));
  assert.equal(owner.calls[1].args[1].blocks[0].text.text, `*P-0001* from sara: R$ 10,00\n${shown}\nWaits: case by case: every payment waits for the owner`);
});

test('a resolution that differs from the request refuses it and wakes the agent; one that keeps failing posts it unchecked', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const line = '23793381286001234107143000012345890460000002000';
  ask(gate, { method: 'bill', recipient: { name: 'ENEL', key: line }, amountCents: 2000, feeCents: 199 });
  ask(gate);
  const store = agentStore();
  const slack = fakeSlack();
  const limited = { code: 1, stdout: '', stderr: 'asaas: Asaas rate limit (429)\n  why: too many lookups\n' };
  const stand = tool({ resolve: [
    { code: 0, stdout: { name: 'ENEL DISTRIBUICAO', document: null, bank: '237', key: line, key_type: null, amount_cents: 50000, fee_cents: 199 } },
    limited, limited, limited,
  ] });
  const runner = createPaymentRunner({ gate, slack: () => slack.client, store: () => store, providers: ['asaas'], cwd: gate.workspace, run: stand.run, now: () => clock.now });
  await runner.step();
  const bill = gate.get('P-0001');
  assert.equal(bill.state, 'refused');
  assert.equal(bill.decided_by, 'rule');
  assert.equal(bill.reason, "Ignite's own check through asaas differs from the request: the amount is R$ 500,00, not R$ 20,00");
  assert.deepEqual(wakes(store), [`Payment P-0001 was refused: R$ 21,99 to ENEL DISTRIBUICAO (bill line ${line}). Ignite's own check through asaas differs from the request: the amount is R$ 500,00, not R$ 20,00. Nothing was sent.`]);
  assert.deepEqual(slack.calls, []);
  clock.now += 30_000;
  await runner.step();
  clock.now += 30_000;
  await runner.step();
  assert.equal(gate.get('P-0002').resolve_error, 'asaas: Asaas rate limit (429) why: too many lookups');
  assert.equal(slack.calls.length, 1);
  assert.equal(slack.calls[0].args[0].blocks[0].text.text, '*Payment request P-0002* from sara\n*Recipient* not checked: Ignite could not read it through asaas '
    + "(asaas: Asaas rate limit (429) why: too many lookups)\n*Pix key* kenu@example.com\n*Amount* R$ 10,00\n_The agent's own description, not checked:_ KENU EXAMPLE SILVA · ***.123.456-** · Nubank\n*Agent's note* Owed to Kenu");
  assert.equal(stand.runs.length, 4);
});

test('the owner approves only a request Ignite has checked: no Approve before, a refused approval, a failed check that stays pending, and nothing sent', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  ask(gate);
  const { panel, slack: owner } = panelFor(gate);
  const last = () => viewText(owner.calls.at(-1).args[1]);
  // The re-review's probe: /payments opened before the service resolved the request, then a valid PIN submitted.
  await interact(panel, 'slash_commands', slash());
  const before = owner.calls[0].args[1].blocks;
  assert.equal(before[5].text.text, '*P-0001* from sara: R$ 10,00\n*Recipient* not checked by Ignite yet\n*Pix key* kenu@example.com\n*Amount* R$ 10,00\n'
    + "_The agent's own description, not checked:_ KENU EXAMPLE SILVA · ***.123.456-** · Nubank\n*Agent's note* Owed to Kenu\nWaits: case by case: every payment waits for the owner");
  assert.equal(before[6].elements[0].text, 'Approve appears once Ignite has checked the recipient.');
  assert.deepEqual(before[7].elements.map((e) => e.action_id), [ACTION.refuse]);
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: 'P-0001', hash: 'a' }));
  assert.equal(last(), 'P-0001 cannot be approved: Ignite has not checked its recipient through asaas yet. Nothing changed.');
  await interact(panel, 'interactive', action(ACTION.approve, 'P-0001', { ts: '3.1' }));
  assert.deepEqual([owner.calls.at(-1).method, last()], ['openView', 'P-0001 cannot be approved: Ignite has not checked its recipient through asaas yet. Nothing changed.']);
  assert.deepEqual(gate.approve('P-0001'), { changed: false, unchecked: 'Ignite has not checked its recipient through asaas yet', row: gate.get('P-0001') });
  assert.equal(gate.get('P-0001').state, 'pending');
  // The service's check fails three times: the request stays pending, shows the failure, and offers Refuse only.
  const store = agentStore();
  const thread = fakeSlack();
  const limited = { code: 1, stdout: '', stderr: 'asaas: Asaas rate limit (429)\n  why: too many lookups\n' };
  const stand = tool({ resolve: [limited, limited, limited] });
  const runner = createPaymentRunner({ gate, slack: () => thread.client, store: () => store, providers: ['asaas'], cwd: gate.workspace, run: stand.run, now: () => clock.now });
  for (let i = 0; i < 5; i++) {
    await runner.step();
    clock.now += 30_000;
  }
  assert.deepEqual(stand.runs.map((r) => r.args[2]), ['resolve', 'resolve', 'resolve']);
  assert.deepEqual([gate.get('P-0001').state, gate.get('P-0001').resolve_error], ['pending', 'asaas: Asaas rate limit (429) why: too many lookups']);
  const posted = thread.calls[0].args[0].blocks;
  assert.equal(posted[0].text.text, '*Payment request P-0001* from sara\n*Recipient* not checked: Ignite could not read it through asaas (asaas: Asaas rate limit (429) why: too many lookups)\n'
    + "*Pix key* kenu@example.com\n*Amount* R$ 10,00\n_The agent's own description, not checked:_ KENU EXAMPLE SILVA · ***.123.456-** · Nubank\n*Agent's note* Owed to Kenu");
  assert.deepEqual(posted.slice(1).map((b) => b.elements.map((e) => e.text?.text ?? e.text)), [
    ['Waits for you: case by case: every payment waits for the owner'],
    ['It cannot be approved: Ignite could not check its recipient. Refuse it; the agent can ask again.'],
    ['Refuse'],
  ]);
  await interact(panel, 'interactive', submission(VIEW.approve, pinValue(PIN), { metadata: 'P-0001', hash: 'b' }));
  assert.equal(last(), 'P-0001 cannot be approved: Ignite could not check its recipient through asaas (asaas: Asaas rate limit (429) why: too many lookups). Nothing changed.');
  await interact(panel, 'slash_commands', slash());
  assert.deepEqual(owner.calls.at(-1).args[1].blocks.filter((b) => b.block_id === 'payment:P-0001').map((b) => b.elements.map((e) => e.action_id)), [[ACTION.refuse]]);
  await runner.step();
  assert.equal(stand.runs.length, 3);
  assert.equal(gate.get('P-0001').state, 'pending');
  assert.deepEqual(wakes(store), []);
  // Neither refused approval spent a PIN try.
  assert.deepEqual(gate.checkPin('000000'), { ok: false, left: 4 });
});

test('the runner never sends a request the owner approved before Ignite checked it', async () => {
  const workspace = scratch();
  firstLedger(workspace);
  const { gate } = gateAt('2026-10-15T15:00:00Z', workspace);
  const stand = tool({ resolve: RESOLVED_KENU });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace, run: stand.run });
  await runner.step();
  assert.deepEqual(stand.runs.map((r) => r.args.slice(2)), [['resolve', 'P-0002']]);
  const unsent = gate.get('P-0003');
  assert.deepEqual([unsent.state, unsent.claimed_at, unsent.reason], ['failed', null,
    'Not sent, because it was approved before Ignite had checked it: Ignite has not checked its recipient through asaas yet']);
  assert.deepEqual(gate.usage(), { day: 0, week: 1000, month: 1000 });
});

test('a request the rule approved is never sent before Ignite checks it; a check that differs or fails refuses it', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const other = ask(gate);
  const failing = ask(gate);
  assert.deepEqual([other.state, failing.state], ['approved', 'approved']);
  assert.deepEqual(gate.due().toSend, []);
  // The re-review's probe: the agent named one key, the provider resolves another.
  const elsewhere = { code: 0, stdout: { ...RESOLVED_KENU.stdout, key: 'other@example.com' } };
  const limited = { code: 1, stdout: '', stderr: 'asaas: Asaas rate limit (429)\n' };
  const stand = tool({ resolve: [elsewhere, limited, limited, limited] });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  for (let i = 0; i < 5; i++) {
    await runner.step();
    clock.now += 30_000;
  }
  assert.deepEqual(stand.runs.map((r) => r.args[2]), ['resolve', 'resolve', 'resolve', 'resolve']);
  assert.deepEqual([gate.get(other.id).state, gate.get(other.id).decided_by], ['refused', 'rule']);
  assert.match(gate.get(other.id).reason, /^Ignite's own check through asaas differs from the request: /);
  assert.deepEqual([gate.get(failing.id).state, gate.get(failing.id).reason], ['refused',
    'Not sent: Ignite could not check its recipient through asaas (asaas: Asaas rate limit (429))']);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
});

test('a rule approval whose check keeps failing is refused even across restarts, and the agent hears it', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const row = ask(gate);
  const store = agentStore();
  const limited = { code: 1, stdout: '', stderr: 'asaas: Asaas rate limit (429)\n' };
  const stand = tool({ resolve: Array(6).fill(limited) });
  // A new runner per pass stands for a restart between lookups: its in-memory try count starts again.
  const restarted = () => createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  // Lookups at 0, 3, 6 and 9 minutes leave it approved; the one at 12 minutes refuses it.
  for (let i = 0; i < 4; i++) {
    await restarted().step();
    clock.now += 3 * 60_000;
  }
  assert.equal(gate.get(row.id).state, 'approved');
  await restarted().step();
  assert.equal(stand.runs.length, 5);
  assert.deepEqual([gate.get(row.id).state, gate.get(row.id).reason], ['refused', 'Not sent: Ignite could not check its recipient through asaas (asaas: Asaas rate limit (429))']);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
  assert.equal(wakes(store).length, 1);
  assert.match(wakes(store)[0], /^Payment P-0001 /);
});

test('a sent payment is still read after ten minutes, so a late failure frees its amount', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  const row = sentRequest(gate);
  const stand = tool({ status: [
    { code: 0, stdout: { provider_id: 'tr_1', status: 'BANK_PROCESSING', final: false, ok: true, receipt_url: null, reason: null } },
    { code: 0, stdout: { provider_id: 'tr_1', status: 'FAILED', final: true, ok: false, receipt_url: null, reason: 'Recusada pelo banco' } },
  ] });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  clock.now += 10 * 60_000 + 1;
  await runner.step();
  assert.equal(stand.runs.length, 1);
  clock.now += 59_000;
  await runner.step();
  assert.equal(stand.runs.length, 1);
  clock.now += 1_000;
  await runner.step();
  assert.equal(stand.runs.length, 2);
  assert.deepEqual([gate.get(row.id).state, gate.get(row.id).reason], ['failed', 'Recusada pelo banco']);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
});

test('a provider program that cannot be started fails the payment and frees its amount', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  // The real launcher, with a PATH that holds no asaas program: spawn fails, nothing can have been paid.
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace,
    env: () => ({ PATH: scratch() }), now: () => clock.now });
  await runner.step();
  const after = gate.get(row.id);
  assert.equal(after.state, 'failed');
  assert.match(after.reason, /^Not sent: Ignite could not start asaas: .*ENOENT/);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
});

test('a launch Node refuses before the program runs (a PATH entry too long, an environment too big) fails the payment and frees its amount', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const long = ask(gate);
  const big = ask(gate);
  for (const row of [long, big]) gate.resolved(row.id, KENU);
  // A real asaas program that leaves a mark when it runs; the oversized environment keeps it from starting.
  const bin = scratch();
  fs.writeFileSync(path.join(bin, 'asaas'), '#!/bin/sh\ntouch "$0.ran"\n', { mode: 0o755 });
  const envs = [{ PATH: path.join(scratch(), 'x'.repeat(300)) }, { PATH: bin, BIG: 'y'.repeat(200_000) }];
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace,
    env: () => envs.shift(), now: () => clock.now });
  await runner.step();
  for (const [row, errno] of [[long, 'ENAMETOOLONG'], [big, 'E2BIG']]) {
    const after = gate.get(row.id);
    assert.equal(after.state, 'failed');
    assert.match(after.reason, /^Not sent: Ignite could not start asaas: /);
    // Linux refuses these launches at once, which Node throws instead of calling back.
    if (process.platform === 'linux') assert.match(after.reason, new RegExp(errno));
  }
  assert.equal(fs.existsSync(path.join(bin, 'asaas.ran')), false);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
});

// Another connection holding a database's write lock, as another process would.
function lockOf(file) {
  const db = new DatabaseSync(file);
  db.exec('BEGIN IMMEDIATE');
  return { release() { db.exec('ROLLBACK'); db.close(); } };
}
const posts = (store) => store.db.prepare("SELECT id, conversation_key FROM outbox WHERE id LIKE 'post:payment:%' ORDER BY rowid").all()
  .map((r) => ({ ...r }));

test('an outcome the agent store could not take is told on a later pass, once', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const row = ask(gate);
  const store = agentStore();
  store.db.exec('PRAGMA busy_timeout=50');
  const lock = lockOf(store.db.location());
  const limited = { code: 1, stdout: '', stderr: 'asaas: Asaas rate limit (429)\n' };
  const stand = tool({ resolve: Array(4).fill(limited) });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  for (let i = 0; i < 3; i++) {
    await runner.step();
    clock.now += 30_000;
  }
  assert.deepEqual([gate.get(row.id).state, gate.get(row.id).notified], ['refused', null]);
  assert.deepEqual(wakes(store), []);
  lock.release();
  await runner.step();
  await runner.step();
  assert.equal(gate.get(row.id).notified, 'refused');
  assert.equal(wakes(store).length, 1);
});

test('an outcome is told once across its wake and its post, when the ledger did not record that it was told', async () => {
  const { gate, clock, workspace } = gateAt('2026-10-15T15:00:00Z', scratch(), { busyMs: 50 });
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const store = agentStore();
  const owner = store.claimNext();
  store.finishRun(owner.runId, owner.nonce, { invocationNonce: owner.nonce, output: 'asked', disposition: 'waiting_workers' });
  const kicked = [];
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: workspace, now: () => clock.now,
    kick: (slug) => kicked.push(slug) });
  // Each outcome is put in the agent store while another connection holds the ledger, so it is not marked told.
  const tellLocked = async (id) => {
    gate.refuse(id);
    const lock = lockOf(ledgerPath(workspace));
    await runner.step();
    lock.release();
    assert.equal(gate.get(id).notified, null);
  };
  // The work waits for workers: a wake. The agent's turn takes that wake and completes the work.
  await tellLocked(ask(gate).id);
  assert.equal(wakes(store).length, 1);
  const woke = store.claimNext();
  assert.equal(woke.kind, 'wake');
  store.finishRun(woke.runId, woke.nonce, { invocationNonce: woke.nonce, output: 'heard it', disposition: 'completed' });
  // Work that no longer waits: a post. The owner's next message then reopens the work.
  await tellLocked(ask(gate).id);
  assert.deepEqual(posts(store).map((p) => p.id), ['post:payment:P-0002:refused']);
  store.acceptOwnerInput({ key: KEY, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1',
    message: { id: 'T1:C1:1.2', role: 'owner', text: 'and now?', team: 'T1', channel: 'C1', ts: '1.2' } });
  for (let i = 0; i < 3; i++) {
    clock.now += 30_000;
    await runner.step();
  }
  assert.deepEqual([gate.get('P-0001').notified, gate.get('P-0002').notified], ['refused', 'refused']);
  assert.deepEqual(wakes(store), ['Payment P-0001 was refused by the owner: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). Nothing was sent.']);
  assert.deepEqual(posts(store).map((p) => p.id), ['post:payment:P-0002:refused']);
  // The pass that marks each one told also asks the service to run the agent's queue and outbox.
  assert.deepEqual(kicked, ['sara', 'sara']);
});

test('an outcome the agent store keeps refusing is tried every 30 s and given up after 20 tries, logged as lost', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  gate.refuse(row.id);
  const store = agentStore();
  store.db.exec('PRAGMA busy_timeout=0');
  const lock = lockOf(store.db.location());
  const logs = [];
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, log: (e) => logs.push(e) });
  const tries = () => logs.filter((e) => e.action === 'notify-retry' || e.action === 'notify-lost').length;
  for (let i = 0; i < 5; i++) await runner.step();
  assert.equal(tries(), 1);
  for (let i = 0; i < 19; i++) {
    clock.now += 30_000;
    await runner.step();
  }
  assert.equal(tries(), 20);
  assert.equal(gate.get(row.id).notified, 'refused');
  assert.deepEqual(logs.filter((e) => e.action === 'notify-lost').map((e) => [e.id, e.state, e.reason]),
    [['P-0001', 'refused', 'not told after 20 tries: database is locked']]);
  clock.now += 60 * 60_000;
  await runner.step();
  assert.equal(tries(), 20);
  lock.release();
  assert.deepEqual([wakes(store), posts(store)], [[], []]);
});

test('a send whose result the ledger could not record is recorded on a later pass and never sent again', async () => {
  const { gate, clock, workspace } = gateAt('2026-10-15T15:00:00Z', scratch(), { busyMs: 50 });
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const row = ask(gate);
  gate.resolved(row.id, KENU);
  let lock = null;
  const runs = [];
  const run = async (command, args) => {
    runs.push(args[2]);
    if (args[2] === 'execute') {
      // The bank took it; meanwhile another connection holds the ledger.
      lock = lockOf(ledgerPath(workspace));
      return { code: 0, stdout: '{"provider_id":"tr_confirmed","status":"PENDING","receipt_url":null}\n', stderr: '' };
    }
    return { code: 0, stdout: '{"provider_id":"tr_confirmed","status":"DONE","final":true,"ok":true,"receipt_url":"https://r.example/c"}\n', stderr: '' };
  };
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: workspace, now: () => clock.now, run });
  await runner.step();
  assert.deepEqual([gate.get(row.id).state, gate.get(row.id).provider_id], ['approved', null]);
  lock.release();
  await runner.step();
  assert.deepEqual([gate.get(row.id).state, runs], ['approved', ['execute']]);
  // 30 s later the result is recorded, and the sent payment is followed like any other.
  clock.now += 30_000;
  await runner.step();
  assert.deepEqual([gate.get(row.id).state, gate.get(row.id).provider_id], ['sent', 'tr_confirmed']);
  clock.now += 5_000;
  await runner.step();
  clock.now += 60 * 60_000;
  for (let i = 0; i < 3; i++) await runner.step();
  const after = gate.get(row.id);
  assert.deepEqual([after.state, after.provider_id, after.receipt_url], ['sent', 'tr_confirmed', 'https://r.example/c']);
  assert.deepEqual(runs, ['execute', 'status']);
  assert.deepEqual(gate.usage(), { day: 1000, week: 1000, month: 1000 });
});

test('a scheduled conversation rekeyed by its first reply still gets its request thread and its outcome', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const store = new Store(path.join(scratch(), 'state.sqlite'));
  store.upsertConversation({ key: KEY, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true });
  store.enqueueScheduleWake({ id: 'schedule:bills:1', conversationKey: KEY, scheduleId: 'bills' });
  // The timer's turn asks for a payment and replies; the reply's delivery makes it a thread with a new key.
  const turn = store.claimNext();
  const row = ask(gate, { conversationKey: turn.conversation_key });
  store.finishRun(turn.runId, turn.nonce, { invocationNonce: turn.nonce, output: 'asked', disposition: 'completed',
    outbox: [{ text: 'I asked to pay Kenu.' }] });
  assert.equal(store.markDelivered(`reply:${turn.runId}:0`, { channel: 'C1', ts: '5.5' }).conversationKey, 'T1:C1:5.5');
  assert.equal(store.getConversation(row.conversation_key), null);
  const slack = fakeSlack();
  const stand = tool({ resolve: RESOLVED_KENU });
  const runner = createPaymentRunner({ gate, slack: () => slack.client, store: () => store, providers: ['asaas'], cwd: gate.workspace, run: stand.run });
  await runner.step();
  assert.deepEqual([slack.calls[0].method, slack.calls[0].args[0].channel, slack.calls[0].args[0].threadTs], ['postBlocks', 'C1', '5.5']);
  gate.refuse(row.id);
  await runner.step();
  await runner.step();
  assert.equal(gate.get(row.id).notified, 'refused');
  assert.deepEqual(posts(store), [{ id: 'post:payment:P-0001:refused', conversation_key: 'T1:C1:5.5' }]);
});

test('a prompt posted before the check is redrawn once Ignite has checked the recipient or could not', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const checked = ask(gate);
  const unreadable = ask(gate);
  for (const [row, ts] of [[checked, '7.1'], [unreadable, '7.2']]) gate.promptPosted(row.id, { channel: 'C1', ts });
  for (const row of [checked, unreadable]) gate.promptShown(row.id, 'pending');
  assert.deepEqual(gate.due().unshown, []);
  gate.resolved(checked.id, KENU);
  gate.resolveFailed(unreadable.id, 'asaas: timed out');
  assert.deepEqual(gate.due().unshown.map((r) => r.id), [checked.id, unreadable.id]);
});

test('the runner sends an approved request with its exact fields, follows it and reports the receipt', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  ask(gate);
  const store = agentStore();
  const stand = tool({
    resolve: RESOLVED_KENU,
    execute: { code: 0, stdout: { provider_id: 'tr_1', status: 'PENDING', receipt_url: null } },
    status: { code: 0, stdout: { provider_id: 'tr_1', status: 'DONE', final: true, ok: true, receipt_url: 'https://r.example/1', reason: null } },
  });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  // The rule approved it at request time; nothing goes out before Ignite has checked the recipient.
  await runner.step();
  assert.deepEqual(stand.runs.map((r) => r.args), [['--json', 'pay', 'resolve', 'P-0001']]);
  stand.runs.shift();
  await runner.step();
  assert.deepEqual(stand.runs[0].args, ['--json', 'pay', 'execute', 'P-0001']);
  assert.deepEqual(stand.runs[0].input, {
    id: 'P-0001', agent: 'sara', conversation: 'T1:C1:1.1', provider: 'asaas', method: 'pix',
    recipient: { name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', key_type: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' },
    amount_cents: 1000, fee_cents: 0, note: 'Owed to Kenu', details: {}, state: 'approved', reason: 'within the limits',
    decided_by: 'rule', decided_at: at('2026-10-15T15:00:00Z'),
    resolved: { name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', key_type: 'EMAIL', document: '***.123.456-**', bank: 'Nubank', amount_cents: null, fee_cents: null },
    resolve_error: null,
    provider_id: null, provider_status: null, receipt_url: null, created_at: at('2026-10-15T15:00:00Z'),
  });
  assert.equal(gate.get('P-0001').state, 'sent');
  assert.equal(gate.get('P-0001').provider_id, 'tr_1');
  clock.now += 4999;
  await runner.step();
  assert.equal(stand.runs.length, 1);
  clock.now += 1;
  await runner.step();
  assert.deepEqual(stand.runs[1].args, ['--json', 'pay', 'status', 'P-0001']);
  assert.equal(stand.runs[1].input.provider_id, 'tr_1');
  assert.equal(gate.get('P-0001').receipt_url, 'https://r.example/1');
  assert.deepEqual(wakes(store), ['Payment P-0001 sent: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). asaas id tr_1, status DONE, receipt https://r.example/1.']);
});

test('a send the bank refused fails and frees its amount; work that no longer waits gets a system message in its thread', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  ask(gate);
  const store = agentStore();
  store.stopWork(store.listWork()[0].id);
  const reason = 'Asaas answered HTTP 400 on POST /transfers: invalid_value: Saldo insuficiente';
  const stand = tool({ resolve: RESOLVED_KENU, execute: { code: 1, stdout: { created: false, reason }, stderr: `asaas: Asaas answered HTTP 400 on POST /transfers\n  why: invalid_value: Saldo insuficiente\n` } });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, run: stand.run });
  await runner.step();
  await runner.step();
  assert.equal(gate.get('P-0001').state, 'failed');
  assert.equal(gate.get('P-0001').reason, reason);
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
  const post = store.db.prepare("SELECT id, payload FROM outbox WHERE id LIKE 'post:payment:%'").get();
  assert.equal(post.id, 'post:payment:P-0001:failed');
  assert.equal(JSON.parse(post.payload).text, `System message: Payment P-0001 failed: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). ${reason}`);
});

test('a send whose answer was lost stays uncertain and keeps its reservation until pay status proves the outcome', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 1000 } });
  ask(gate);
  const store = agentStore();
  const stand = tool({
    execute: { code: 1, stdout: '', stderr: 'asaas: could not reach Asaas (https://api.asaas.com/v3)\n  why: timed out\n' },
    resolve: RESOLVED_KENU,
    status: { code: 0, stdout: { provider_id: 'tr_9', status: 'FAILED', final: true, ok: false, receipt_url: null, reason: 'Saldo insuficiente' } },
  });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  await runner.step();
  await runner.step();
  const lost = gate.get('P-0001');
  assert.equal(lost.state, 'uncertain');
  assert.equal(lost.reason, 'Ignite does not know whether asaas made it: asaas: could not reach Asaas (https://api.asaas.com/v3) why: timed out');
  assert.deepEqual(gate.usage(), { day: 1000, week: 1000, month: 1000 });
  assert.equal(ask(gate).reason, 'over the daily limit (R$ 0,00 left of R$ 10,00)');
  assert.deepEqual(wakes(store), ['Payment P-0001 may have been paid: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). Ignite does not know whether asaas made it: asaas: could not reach Asaas (https://api.asaas.com/v3) why: timed out. '
    + 'It counts toward the limits until Ignite reads it at asaas; this conversation hears the outcome. Do not ask again before checking the statement.']);
  clock.now += 60_000;
  await runner.step();
  assert.deepEqual(stand.runs.map((r) => r.args.slice(2)), [['resolve', 'P-0001'], ['execute', 'P-0001'], ['resolve', 'P-0002']]);
  // Asaas asks about the operation the lost send made; Ignite approves it and learns its id.
  const body = { type: 'TRANSFER', transfer: { id: 'tr_9', value: 10, externalReference: 'P-0001', bankAccount: { pixAddressKey: 'kenu@example.com' } } };
  assert.deepEqual(validate(gate, 'asaas', ASAAS, { 'asaas-access-token': TOKEN }, body, TOKEN), { status: 'APPROVED', id: 'P-0001' });
  clock.now += 60_000;
  await runner.step();
  assert.deepEqual(stand.runs[3].args, ['--json', 'pay', 'status', 'P-0001']);
  assert.equal(stand.runs[3].input.provider_id, 'tr_9');
  assert.equal(gate.get('P-0001').state, 'failed');
  assert.equal(gate.get('P-0001').reason, 'Saldo insuficiente');
  assert.deepEqual(gate.usage(), { day: 0, week: 0, month: 0 });
});

test('a restart after a claim, a provider id or a withdrawal approval keeps a request uncertain; a found operation becomes sent', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 100000 } });
  const cut = ask(gate);
  assert.equal(gate.claim(cut.id), true);
  assert.deepEqual(gate.interrupted(), [cut.id]);
  assert.equal(gate.get(cut.id).state, 'uncertain');
  assert.equal(gate.get(cut.id).reason, 'interrupted: Ignite stopped while sending it, so it may have been paid; it counts toward the limits until Ignite reads it at the provider');
  const withId = ask(gate);
  gate.claim(withId.id);
  gate.sent(withId.id, { providerId: 'tr_2' });
  assert.equal(gate.failed(withId.id, 'lost').row.state, 'uncertain');
  const answered = ask(gate, { amountCents: 2000 });
  gate.claim(answered.id);
  const body = { type: 'TRANSFER', transfer: { id: 'tr_3', value: 20, externalReference: answered.id, bankAccount: { pixAddressKey: 'kenu@example.com' } } };
  assert.equal(validate(gate, 'asaas', ASAAS, { 'asaas-access-token': TOKEN }, body, TOKEN).status, 'APPROVED');
  assert.equal(gate.failed(answered.id, 'the tool crashed').row.state, 'uncertain');
  assert.deepEqual(gate.usage(), { day: 4000, week: 4000, month: 4000 });
  const stand = tool({ status: { code: 0, stdout: { provider_id: 'tr_2', status: 'DONE', final: true, ok: true, receipt_url: 'https://r.example/2', reason: null } } });
  const runner = createPaymentRunner({ gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now, run: stand.run });
  clock.now += 60_000;
  await runner.step();
  assert.deepEqual(stand.runs.map((r) => [r.args[3], r.input.provider_id]), [['P-0002', 'tr_2'], ['P-0003', 'tr_3']]);
  const found = gate.get(withId.id);
  assert.deepEqual([found.state, found.provider_id, found.provider_status, found.receipt_url, found.reason], ['sent', 'tr_2', 'DONE', 'https://r.example/2', 'within the limits']);
  assert.equal(gate.get(cut.id).state, 'uncertain');
});

test('a provider with no withdrawal validation is never run', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  const other = ask(gate, { provider: 'otherbank' });
  const runs = [];
  const runner = createPaymentRunner({
    gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace,
    run: async (...args) => { runs.push(args); return { code: 0, stdout: '{}', stderr: '' }; },
  });
  await runner.step();
  assert.equal(runs.length, 0);
  assert.equal(gate.get(other.id).state, 'refused');
  assert.equal(gate.get(other.id).reason, 'Not sent: Ignite could not check its recipient through otherbank (Ignite does not send through otherbank: it has no withdrawal validation for it)');
});

// ───────────────────────────── the withdrawal validation

function transfer({ reference = 'P-0001', id = 'tr_1', value = 10, key = 'kenu@example.com' } = {}) {
  return {
    type: 'TRANSFER',
    transfer: {
      object: 'transfer', id, value, status: 'PENDING', operationType: 'PIX', externalReference: reference,
      bankAccount: { ownerName: 'KENU EXAMPLE SILVA', cpfCnpj: '***.123.456-**', pixAddressKey: key },
    },
  };
}

async function post(port, body, headers = { 'asaas-access-token': TOKEN }, route = '/asaas/withdrawal-validation', method = 'POST') {
  const started = Date.now();
  const response = await fetch(`http://127.0.0.1:${port}${route}`, {
    method, headers: { 'content-type': 'application/json', ...headers }, ...(method === 'POST' ? { body: JSON.stringify(body) } : {}),
  });
  return { status: response.status, body: await response.json(), ms: Date.now() - started };
}

async function listening(gate, token = () => TOKEN) {
  const logs = [];
  const hook = createWebhook({ gate, providers: { asaas: ASAAS }, token, port: 0, log: (f) => logs.push(f) });
  const port = await hook.listen();
  return { hook, port, logs };
}

test('Asaas lives in its connector: Ignite loads its adapter by name, and its core names no Asaas field', () => {
  assert.deepEqual([ASAAS.path, ASAAS.header, ASAAS.tokenEnv], ['/asaas/withdrawal-validation', 'asaas-access-token', 'ASAAS_WEBHOOK_TOKEN']);
  assert.deepEqual(ASAAS.read(transfer()), { method: 'pix', reference: 'P-0001', operationId: 'tr_1', amountCents: 1000, recipientKey: 'kenu@example.com' });
  assert.throws(() => loadProvider('../asaas'), /^Error: payment provider \.\.\/asaas is not a provider name$/);
  assert.throws(() => loadProvider('nobank'), /^Error: payment provider nobank has no withdrawal validation at /);
  for (const file of ['payments.js', 'payment-webhook.js', 'payment-panel.js', 'payment-runner.js', 'config.js', 'daemon.js']) {
    const source = fs.readFileSync(path.join(__dirname, file), 'utf8');
    for (const word of ['asaas-access-token', 'ASAAS_WEBHOOK_TOKEN', '/asaas/withdrawal-validation', 'pixAddressKey', 'identificationField', 'externalReference']) {
      assert.equal(source.includes(word), false, `${file} names ${word}`);
    }
  }
  const panel = fs.readFileSync(path.join(__dirname, 'payment-panel.js'), 'utf8');
  assert.equal(panel.includes('\\d{4,12}'), false, 'the panel keeps its own PIN pattern');
  assert.equal(panel.includes("'off', 'automatic', 'case_by_case'"), false, 'the panel keeps its own mode list');
  assert.equal(panel.includes('needs at least one limit'), false, 'the panel keeps its own no-ceiling rule');
});

test('the webhook approves the request Ignite sent, from the ledger, within 2 seconds', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  sentRequest(gate);
  const { hook, port, logs } = await listening(gate);
  try {
    const answer = await post(port, transfer());
    assert.equal(answer.status, 200);
    assert.deepEqual(answer.body, { status: 'APPROVED' });
    assert.equal(answer.ms < 2000, true);
    const row = gate.get('P-0001');
    assert.deepEqual([row.answered_operation, row.answered_cents, row.answered_recipient], ['tr_1', 1000, 'kenu@example.com']);
    assert.deepEqual(logs.at(-1), { event: 'payment-webhook', provider: 'asaas', id: 'P-0001', status: 'APPROVED', reason: null });
  } finally {
    await hook.close();
  }
});

test('a retry of the approved operation is approved again only with the same id, amount and recipient', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  sentRequest(gate);
  const { hook, port } = await listening(gate);
  const refused = { status: 'REFUSED', refuseReason: 'P-0001 was already approved for operation tr_1; this call differs from it' };
  try {
    assert.deepEqual((await post(port, transfer())).body, { status: 'APPROVED' });
    assert.deepEqual((await post(port, transfer())).body, { status: 'APPROVED' });
    assert.deepEqual((await post(port, transfer({ value: 10.01 }))).body, refused);
    assert.deepEqual((await post(port, transfer({ key: 'other@example.com' }))).body, refused);
    assert.deepEqual((await post(port, transfer({ id: 'tr_2' }))).body, refused);
    gate.checked('P-0001', { providerStatus: 'FAILED', final: true, ok: false, reason: 'Chave inexistente' });
    assert.equal(gate.get('P-0001').state, 'failed');
    assert.deepEqual((await post(port, transfer())).body, { status: 'APPROVED' });
    assert.deepEqual((await post(port, transfer({ value: 99 }))).body, refused);
    assert.deepEqual((await post(port, transfer({ key: 'other@example.com', id: 'tr_7' }))).body, refused);
  } finally {
    await hook.close();
  }
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const withdrawn = ask(gate);
  gate.cancel(withdrawn.id, 'sara');
  assert.equal(validate(gate, 'asaas', ASAAS, { 'asaas-access-token': TOKEN }, transfer({ reference: withdrawn.id }), TOKEN).refuseReason, 'P-0002 is cancelled');
});

test('the webhook refuses a wrong amount, a wrong recipient, an unknown reference and a bad token', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  sentRequest(gate);
  const { hook, port } = await listening(gate);
  const refused = (refuseReason) => ({ status: 'REFUSED', refuseReason });
  try {
    assert.deepEqual((await post(port, transfer({ value: 10.01 }))).body, refused('P-0001 approved R$ 10,00, the operation is R$ 10,01'));
    assert.deepEqual((await post(port, transfer({ key: 'other@example.com' }))).body, refused('P-0001 approved another recipient'));
    assert.deepEqual((await post(port, transfer({ reference: 'P-9999' }))).body, refused('unknown request P-9999'));
    assert.deepEqual((await post(port, transfer(), { 'asaas-access-token': 'wrong' })).body, refused('bad token'));
    assert.deepEqual((await post(port, transfer(), {})).body, refused('bad token'));
    assert.deepEqual((await post(port, transfer({ id: 'tr_9' }))).body, refused('P-0001 was sent as operation tr_1, not tr_9'));
    assert.equal((await post(port, {}, {}, '/other')).status, 404);
    assert.equal((await post(port, null, {}, '/asaas/withdrawal-validation', 'GET')).status, 405);
  } finally {
    await hook.close();
  }
  const unset = await listening(gate, () => null);
  try {
    assert.deepEqual((await post(unset.port, transfer())).body, refused('the webhook token is not configured in Ignite'));
  } finally {
    await unset.hook.close();
  }
});

test('six calls at once each answer within 1 second while another connection holds the ledger, and are approved once it is free', async () => {
  // The webhook's own connection, as startWebhook opens it: its busy wait is 0, so no call blocks another.
  const { gate, workspace } = gateAt('2026-10-15T15:00:00Z', scratch(), { busyMs: 0 });
  sentRequest(gate);
  const holder = new DatabaseSync(ledgerPath(workspace));
  const { hook, port } = await listening(gate);
  const six = () => Promise.all(Array.from({ length: 6 }, () => post(port, transfer())));
  try {
    // The re-review's probe: another connection holds BEGIN IMMEDIATE and six valid calls arrive at once.
    holder.exec('PRAGMA busy_timeout=0; BEGIN IMMEDIATE');
    const held = await six();
    assert.deepEqual(held.map((a) => a.body), Array(6).fill({ status: 'REFUSED', refuseReason: 'the ledger is busy (database is locked): nothing was approved' }));
    for (const answer of held) assert.equal(answer.ms < 1000, true, `answered in ${answer.ms} ms`);
    // A lock held for a moment: each call waits for it without blocking the others, and is approved.
    const calls = six();
    setTimeout(() => holder.exec('ROLLBACK'), 150);
    const freed = await calls;
    assert.deepEqual(freed.map((a) => a.body), Array(6).fill({ status: 'APPROVED' }));
    for (const answer of freed) assert.equal(answer.ms >= 140 && answer.ms < 1000, true, `answered in ${answer.ms} ms`);
  } finally {
    holder.close();
    await hook.close();
  }
});

test('a direct API call that skipped the gate is refused, even naming a real request', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const headers = { 'asaas-access-token': TOKEN };
  const check = (body) => validate(gate, 'asaas', ASAAS, headers, body, TOKEN);
  assert.deepEqual(check(transfer({ reference: null, id: null })),
    { status: 'REFUSED', refuseReason: 'the operation names no request and has no id: it did not pass the payment gate', id: null });
  assert.deepEqual(check(transfer({ reference: null, id: 'tr_5' })),
    { status: 'REFUSED', refuseReason: 'no request names operation tr_5: it did not pass the payment gate, or Ignite has not recorded its id yet', id: null });
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  ask(gate);
  assert.equal(check(transfer({ reference: 'P-0001' })).refuseReason, 'P-0001 is pending');
  gate.resolved('P-0001', KENU);
  gate.approve('P-0001');
  assert.equal(check(transfer({ reference: 'P-0001' })).refuseReason, 'P-0001 is approved but Ignite has not sent it');
  gate.saveSettings({ mode: 'off', limits: {} });
  ask(gate);
  assert.equal(check(transfer({ reference: 'P-0002' })).refuseReason, 'P-0002 is refused');
  for (const type of ['PIX_REFUND', 'PAYMENT_SPLIT']) {
    assert.equal(check({ type }).refuseReason, `${type} is not paid through the payment gate`);
  }
});

test('a bill is matched by its line and amount', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const line = '23793381286001234107143000012345890460000002000';
  sentRequest(gate, { method: 'bill', recipient: { name: 'ENEL', key: line }, amountCents: 2000, feeCents: 199 });
  const bill = (value, identificationField) => ({ type: 'BILL', bill: { id: 'tr_1', value, identificationField, externalReference: 'P-0001' } });
  const headers = { 'asaas-access-token': TOKEN };
  assert.equal(validate(gate, 'asaas', ASAAS, headers, bill(21.99, line), TOKEN).refuseReason, 'P-0001 approved R$ 20,00, the operation is R$ 21,99');
  assert.equal(validate(gate, 'asaas', ASAAS, headers, bill(20, line.replace(/1/g, '7')), TOKEN).refuseReason, 'P-0001 approved another recipient');
  assert.deepEqual(validate(gate, 'asaas', ASAAS, headers, bill(20, `${line.slice(0, 5)}.${line.slice(5)}`), TOKEN), { status: 'APPROVED', id: 'P-0001' });
});

test('a QR payment and a top-up are matched by the operation id Ignite recorded, and refused until it is recorded', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { month: 1_000_000 } });
  const headers = { 'asaas-access-token': TOKEN };
  const check = (body) => validate(gate, 'asaas', ASAAS, headers, body, TOKEN);
  const payload = '00020126580014br.gov.bcb.pix0136a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d520400005303986540535.005802BR5907PADARIA6009SAO PAULO62070503***6304ABCD';
  const qr = ask(gate, { method: 'qr', recipient: { name: 'PADARIA', key: payload, keyType: 'QR' }, amountCents: 3500 });
  gate.claim(qr.id);
  const qrBody = (id, value) => ({ type: 'PIX_QR_CODE', pixQrCode: { id, value, status: 'AWAITING_REQUEST', externalAccount: { name: 'PADARIA', addressKey: 'padaria@example.com' } } });
  assert.deepEqual(check(qrBody('pq_1', 35)), { status: 'REFUSED',
    refuseReason: 'no request names operation pq_1: it did not pass the payment gate, or Ignite has not recorded its id yet', id: null });
  gate.sent(qr.id, { providerId: 'pq_1', providerStatus: 'AWAITING_REQUEST' });
  assert.equal(check(qrBody('pq_1', 36)).refuseReason, 'P-0001 approved R$ 35,00, the operation is R$ 36,00');
  assert.deepEqual(check(qrBody('pq_1', 35)), { status: 'APPROVED', id: 'P-0001' });
  const top = ask(gate, { method: 'recharge', recipient: { key: '11912345678', keyType: 'PHONE' }, amountCents: 2000, note: null });
  gate.claim(top.id);
  gate.sent(top.id, { providerId: 'rc_1' });
  const recharge = (phoneNumber) => ({ type: 'MOBILE_PHONE_RECHARGE', mobilePhoneRecharge: { id: 'rc_1', value: 20, phoneNumber, status: 'PENDING', operatorName: 'Claro' } });
  assert.equal(check(recharge('11999999999')).refuseReason, 'P-0002 approved another recipient');
  assert.deepEqual(check(recharge('11912345678')), { status: 'APPROVED', id: 'P-0002' });
  assert.equal(check(qrBody('pq_1', 35)).status, 'APPROVED');
  assert.equal(check({ type: 'PIX_QR_CODE', pixQrCode: { id: 'pq_2', value: 35 } }).refuseReason,
    'no request names operation pq_2: it did not pass the payment gate, or Ignite has not recorded its id yet');
});

// ───────────────────────────── the ignite payment verbs

function installation({ payments = true } = {}) {
  const workspace = scratch();
  const dir = path.join(workspace, '.rbtv', 'config', 'ignite');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'config.json'), JSON.stringify({
    slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'w' },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' }, routes: { C1: 'sara' }, ...(payments ? { payments: {} } : {}),
  }));
  for (const slug of ['sara', 'max']) {
    const home = path.join(workspace, '.rbtv', 'agents', slug);
    fs.mkdirSync(home, { recursive: true });
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    store.upsertConversation({ key: KEY, agent: slug, workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true });
    store.close();
  }
  return workspace;
}

function cli(workspace, argv, { agent = 'sara', conversation = KEY, stdin } = {}) {
  const out = [];
  const env = { RBTV_AGENT_HOME: path.join(workspace, '.rbtv', 'agents', agent), ...(conversation ? { IGNITE_CONVERSATION: conversation } : {}) };
  try {
    const code = main(argv, { stdout: (t) => out.push(t), env, stdin });
    return { code, out: out.join('') };
  } catch (error) {
    return { code: error.exitCode || 1, out: out.join(''), err: error.message };
  }
}

const REQUEST = JSON.stringify({ method: 'pix', recipient: { name: 'KENU', key: 'kenu@example.com', key_type: 'EMAIL' }, amount_cents: 9900, note: 'Owed' });

test('ignite payment request records the request and prints the answer as fixed fields', () => {
  const workspace = installation();
  const text = cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', REQUEST]);
  assert.deepEqual(text, { code: 0, out: 'P-0001 refused: payments are off\n' });
  const json = cli(workspace, ['--json', 'payment', 'request', '--provider', 'asaas', '--request', '-'], { stdin: REQUEST });
  const row = JSON.parse(json.out);
  assert.equal(row.id, 'P-0002');
  assert.equal(row.state, 'refused');
  assert.equal(row.agent, 'sara');
  assert.equal(row.conversation, KEY);
  assert.deepEqual(row.recipient, { name: 'KENU', key: 'kenu@example.com', key_type: 'EMAIL', document: null, bank: null });
  assert.equal(row.amount_cents, 9900);
  assert.equal(row.resolved, null);
  assert.equal(row.resolve_error, null);
});

test('outside a turn, in an unknown conversation or with no payments section, nothing is recorded', () => {
  const workspace = installation();
  assert.equal(cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', REQUEST], { conversation: null }).err,
    'ignite payment request runs inside a turn: IGNITE_CONVERSATION is not set\nNothing changed.\nignite payment -h');
  assert.equal(cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', REQUEST], { conversation: 'T1:C9:2.2' }).err,
    'unknown conversation: T1:C9:2.2\nNothing changed.');
  assert.match(cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', '{"method":"pix"'], {}).err, /^--request is not JSON/);
  const gate = new Gate({ workspace });
  assert.equal(gate.list().length, 0);
  gate.close();
  const bare = installation({ payments: false });
  assert.equal(cli(bare, ['payment', 'list']).err,
    "payments are not set up in this installation: Ignite's config has no payments section\nNothing changed.");
});

test('no ignite verb approves, refuses or changes the settings', () => {
  const workspace = installation();
  const gate = new Gate({ workspace });
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  gate.close();
  cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', REQUEST]);
  for (const verb of ['approve', 'refuse', 'settings', 'execute', 'mode']) {
    const result = cli(workspace, ['payment', verb, 'P-0001']);
    assert.equal(result.code, 1);
    assert.equal(result.err, `unknown payment verb: ${verb}\nNothing changed.\nignite payment -h`);
  }
  const after = new Gate({ workspace });
  assert.equal(after.get('P-0001').state, 'pending');
  assert.equal(after.settings().mode, 'case_by_case');
  after.close();
});

test("an agent reads and withdraws only its own pending requests", () => {
  const workspace = installation();
  const gate = new Gate({ workspace });
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  gate.close();
  cli(workspace, ['payment', 'request', '--provider', 'asaas', '--request', REQUEST]);
  assert.equal(cli(workspace, ['payment', 'show', 'P-0001'], { agent: 'max' }).err, 'unknown payment request: P-0001\nNothing changed.\nignite payment list');
  assert.equal(cli(workspace, ['payment', 'cancel', 'P-0001'], { agent: 'max' }).err, 'unknown payment request: P-0001');
  assert.equal(cli(workspace, ['payment', 'list']).out, 'P-0001  pending       R$ 99,00  KENU  (case by case: every payment waits for the owner)\n');
  assert.deepEqual(cli(workspace, ['payment', 'cancel', 'P-0001']), { code: 0, out: 'cancelled P-0001\n' });
  assert.equal(cli(workspace, ['payment', 'cancel', 'P-0001']).err, 'P-0001 is cancelled: only a pending request can be withdrawn');
  assert.equal(cli(workspace, ['payment', 'list', '--state', 'nope']).err, 'unknown state: nope\nchoose from pending, approved, sent, uncertain, refused, cancelled, failed\nNothing changed.\nignite payment -h');
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      process.stdout.write(`PASS ${name}\n`);
    } catch (error) {
      failed += 1;
      process.stdout.write(`FAIL ${name}: ${error.stack || error.message}\n`);
    }
  }
  process.stdout.write(`payments: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();

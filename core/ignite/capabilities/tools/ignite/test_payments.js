#!/usr/bin/env node
'use strict';

// Suite for the payment gate: payments.js (settings, limits, ledger, PIN), payment-panel.js (the
// owner's Slack panel and buttons), payment-runner.js (sending, reporting), payment-webhook.js (the
// withdrawal validation) and the ignite payment verbs. Injected clock, stand-in Slack and stand-in
// provider tool; the webhook listens on 127.0.0.1 with a free port. No network beyond the loopback.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Gate, periodStart, brl, parseAmount, publicRow, pinPath } = require('./payments.js');
const { createPaymentPanel, promptBlocks, ACTION, VIEW } = require('./payment-panel.js');
const { createPaymentRunner } = require('./payment-runner.js');
const { createWebhook, validate } = require('./payment-webhook.js');
const { Slack } = require('./slack.js');
const { Store } = require('./store.js');
const { main } = require('./cli.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

const PIN = '482913';
const TOKEN = 'whk-test-token';
const KEY = 'T1:C1:1.1';
const at = (iso) => Date.parse(iso);

function scratch() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-pay-'));
}

function gateAt(iso, workspace = scratch()) {
  const clock = { now: at(iso) };
  const gate = new Gate({ workspace, now: () => clock.now });
  return { gate, clock, workspace };
}

function ask(gate, fields = {}) {
  return gate.request({
    agent: 'sara', conversationKey: KEY, provider: 'asaas', method: 'pix',
    recipient: { name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', keyType: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' },
    amountCents: 1000, note: 'Owed to Kenu', ...fields,
  });
}

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

function fakeSlack() {
  const calls = [];
  const record = (method) => async (...args) => {
    calls.push({ method, args });
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

const slash = (user = 'UOWNER', team = 'T1') => ({ command: '/payments', user_id: user, team_id: team, trigger_id: 'trig-1', channel_id: 'C1' });
function action(actionId, value, { user = 'UOWNER', team = 'T1', view = null } = {}) {
  return {
    type: 'block_actions', user: { id: user, team_id: team }, team: { id: team }, trigger_id: 'trig-2',
    ...(view ? { view } : { channel: { id: 'C1' } }), actions: [{ action_id: actionId, value }],
  };
}
function submission(callbackId, values, { user = 'UOWNER', team = 'T1', metadata = '', id = 'V1', root = 'V1' } = {}) {
  return {
    type: 'view_submission', user: { id: user, team_id: team }, team: { id: team },
    view: { id, root_view_id: root, callback_id: callbackId, private_metadata: metadata, state: { values } },
  };
}
const pinValue = (pin) => ({ payments_pin: { value: { type: 'plain_text_input', value: pin } } });
function settingsValues(mode, limits, pin) {
  const values = { ...pinValue(pin), payments_mode: { value: { type: 'radio_buttons', selected_option: { value: mode } } } };
  for (const period of ['day', 'week', 'month']) values[`payments_${period}`] = { value: { type: 'plain_text_input', value: limits[period] ?? null } };
  return values;
}

// ───────────────────────────── the gate's rules

test('off refuses: the default mode, decided by rule', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  assert.deepEqual(gate.settings(), { mode: 'off', limits: { day: null, week: null, month: null } });
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
    { mode: 'automatic', limits: { day: null, week: 15000, month: null } });
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

test('limits count approved and sent amounts with their fee, not pending, refused, cancelled or failed', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const waiting = ask(gate, { amountCents: 100 });
  const refused = ask(gate, { amountCents: 200 });
  const cancelled = ask(gate, { amountCents: 400 });
  gate.refuse(refused.id);
  gate.cancel(cancelled.id, 'sara');
  const approved = ask(gate, { amountCents: 800, feeCents: 99 });
  gate.approve(approved.id);
  const failing = ask(gate, { amountCents: 1600 });
  gate.approve(failing.id);
  gate.failed(failing.id, 'Asaas answered HTTP 400');
  assert.equal(gate.get(waiting.id).state, 'pending');
  assert.deepEqual(gate.usage(), { day: 899, week: 899, month: 899 });
  gate.saveSettings({ mode: 'automatic', limits: { day: 1000 } });
  assert.equal(ask(gate, { amountCents: 101 }).state, 'approved');
  assert.equal(ask(gate, { amountCents: 1 }).reason, 'over the daily limit (R$ 0,00 left of R$ 10,00)');
});

test('only a pending request is approved or refused, once', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  assert.equal(gate.approve(row.id).changed, true);
  assert.equal(gate.approve(row.id).changed, false);
  assert.equal(gate.refuse(row.id).changed, false);
  assert.equal(gate.get(row.id).state, 'approved');
  assert.equal(gate.get(row.id).decided_by, 'owner');
  assert.equal(gate.claim(row.id), true);
  assert.equal(gate.claim(row.id), false);
});

test('amounts are shown and read as reais', () => {
  assert.equal(brl(123456), 'R$ 1.234,56');
  assert.equal(brl(5), 'R$ 0,05');
  assert.equal(parseAmount('150'), 15000);
  assert.equal(parseAmount('150,5'), 15050);
  assert.equal(parseAmount('0.01'), 1);
  assert.equal(parseAmount('1.234,00'), null);
  assert.equal(parseAmount(''), null);
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
  assert.deepEqual(await panel.handle('slash_commands', slash('UOTHER')),
    { response: { text: 'Only the owner can open /payments. Nothing changed.' } });
  assert.deepEqual(await panel.handle('slash_commands', slash('UOWNER', 'T2')),
    { response: { text: 'Only the owner can open /payments. Nothing changed.' } });
  for (const id of [ACTION.approve, ACTION.refuse, ACTION.settings]) {
    const result = await panel.handle('interactive', action(id, row.id, { user: 'UOTHER' }));
    await result.after();
  }
  assert.deepEqual(slack.calls.map((c) => c.method), ['postEphemeral', 'postEphemeral', 'postEphemeral']);
  assert.deepEqual(slack.calls[0].args[0], { channel: 'C1', user: 'UOTHER', text: 'Only the owner can approve or refuse payments. Nothing changed.' });
  const approve = await panel.handle('interactive', submission(VIEW.approve, pinValue(PIN), { user: 'UOTHER', metadata: row.id }));
  assert.deepEqual(approve, { response: { response_action: 'errors', errors: { payments_pin: 'Only the owner can do this. Nothing changed.' } } });
  const settings = await panel.handle('interactive', submission(VIEW.settings, settingsValues('automatic', { day: '500' }, PIN), { user: 'UOTHER' }));
  assert.equal(settings.response.errors.payments_pin, 'Only the owner can do this. Nothing changed.');
  const sameUserOtherTeam = await panel.handle('interactive', submission(VIEW.approve, pinValue(PIN), { team: 'T2', metadata: row.id }));
  assert.equal(sameUserOtherTeam.response.response_action, 'errors');
  assert.equal(gate.get(row.id).state, 'pending');
  assert.equal(gate.settings().mode, 'case_by_case');
  assert.equal(slack.calls.some((c) => c.method !== 'postEphemeral'), false);
});

test('/payments asks for a PIN on first use, then opens the panel', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const { panel, slack } = panelFor(gate);
  const first = await panel.handle('slash_commands', slash());
  assert.equal(first.response, undefined);
  await first.after();
  assert.equal(slack.calls[0].method, 'openView');
  assert.equal(slack.calls[0].args[0], 'trig-1');
  assert.equal(slack.calls[0].args[1].callback_id, VIEW.setPin);
  const values = { ...pinValue(PIN), payments_pin_again: { value: { value: '482914' } } };
  assert.deepEqual(await panel.handle('interactive', submission(VIEW.setPin, values, { metadata: '{"next":"panel"}' })),
    { response: { response_action: 'errors', errors: { payments_pin_again: 'The two PINs differ.' } } });
  assert.equal(gate.pinSet(), false);
  values.payments_pin_again.value.value = PIN;
  const set = await panel.handle('interactive', submission(VIEW.setPin, values, { metadata: '{"next":"panel"}' }));
  assert.equal(set.response.response_action, 'update');
  assert.equal(set.response.view.callback_id, VIEW.panel);
  assert.equal(gate.pinSet(), true);
  const again = await panel.handle('slash_commands', slash());
  await again.after();
  assert.equal(slack.calls[1].args[1].callback_id, VIEW.panel);
});

test('the panel shows mode, what went out this day, week and month, pending requests and the last ten sent', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  const sent = sentRequest(gate, { amountCents: 2500 });
  gate.checked(sent.id, { providerStatus: 'DONE', receiptUrl: 'https://r.example/1', final: true, ok: true });
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000, week: 15000 } });
  const waiting = ask(gate, { amountCents: 9900, note: '<https://evil.example|Approve here>' });
  const { panel, slack } = panelFor(gate);
  await (await panel.handle('slash_commands', slash())).after();
  const view = slack.calls[0].args[1];
  const text = JSON.stringify(view.blocks);
  assert.equal(view.blocks[0].text.text, '*Mode* Automatic within the limits');
  assert.deepEqual(view.blocks[1].fields.map((f) => f.text), [
    '*Today*\nR$ 25,00 of R$ 50,00', '*This week*\nR$ 25,00 of R$ 150,00', '*This month*\nR$ 25,00 (no limit)',
  ]);
  assert.equal(view.blocks[4].text.text, '*Pending* (1)');
  assert.equal(view.blocks[5].text.text.includes(`*${waiting.id}* from sara: R$ 99,00`), true);
  assert.equal(view.blocks[5].text.text.includes('&lt;https://evil.example|Approve here&gt;'), true);
  assert.equal(text.includes('<https://evil.example'), false);
  assert.deepEqual(view.blocks[6].elements.map((e) => [e.action_id, e.value]), [[ACTION.approve, waiting.id], [ACTION.refuse, waiting.id]]);
  assert.equal(view.blocks[8].text.text, '*Last ten sent*');
  assert.equal(view.blocks[9].elements[0].text, 'P-0001 · 15 Oct, 12:00 · R$ 25,00 to KENU EXAMPLE SILVA · <https://r.example/1|receipt>');
});

test('Approve needs the right PIN; a wrong one changes nothing', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const { panel, slack, kicks } = panelFor(gate);
  await (await panel.handle('interactive', action(ACTION.approve, row.id))).after();
  assert.equal(slack.calls[0].method, 'openView');
  assert.equal(slack.calls[0].args[1].callback_id, VIEW.approve);
  assert.equal(slack.calls[0].args[1].private_metadata, row.id);
  const wrong = await panel.handle('interactive', submission(VIEW.approve, pinValue('111111'), { metadata: row.id }));
  assert.deepEqual(wrong, { response: { response_action: 'errors', errors: {
    payments_pin: 'Wrong PIN: 4 tries left before PIN forms lock for 15 minutes. Nothing changed.' } } });
  assert.equal(gate.get(row.id).state, 'pending');
  const right = await panel.handle('interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id }));
  assert.equal(right.response.response_action, 'update');
  assert.equal(right.response.view.blocks[0].text.text,
    "Approved P-0001: R$ 10,00 to KENU EXAMPLE SILVA. Ignite is sending it now; the result arrives in sara's thread.");
  await right.after();
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
  const { panel } = panelFor(gate);
  const approve = (pin) => panel.handle('interactive', submission(VIEW.approve, pinValue(pin), { metadata: row.id }));
  for (let i = 0; i < 4; i++) await approve('111111');
  const locked = 'Locked after five wrong PINs until 12:15. Nothing changed.';
  assert.equal((await approve('111111')).response.errors.payments_pin, locked);
  assert.equal((await approve(PIN)).response.errors.payments_pin, locked);
  const settings = await panel.handle('interactive', submission(VIEW.settings, settingsValues('automatic', { day: '50' }, PIN)));
  assert.equal(settings.response.errors.payments_pin, locked);
  assert.equal(gate.get(row.id).state, 'pending');
  assert.equal(gate.settings().mode, 'case_by_case');
  clock.now = at('2026-10-15T15:15:00Z');
  assert.equal((await approve(PIN)).response.response_action, 'update');
  assert.equal(gate.get(row.id).state, 'approved');
});

test('settings: automatic with no limit is refused; saving needs the PIN', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  const { panel } = panelFor(gate);
  const submit = (mode, limits, pin) => panel.handle('interactive', submission(VIEW.settings, settingsValues(mode, limits, pin), { id: 'V2', root: 'V1' }));
  assert.deepEqual((await submit('automatic', {}, PIN)).response.errors,
    { payments_mode: 'Automatic needs at least one limit: set a daily, weekly or monthly limit.' });
  assert.deepEqual((await submit('automatic', { week: 'abc' }, PIN)).response.errors,
    { payments_week: 'Write an amount in reais, like 150 or 150,00.' });
  assert.equal((await submit('automatic', { week: '150' }, '111111')).response.errors.payments_pin,
    'Wrong PIN: 4 tries left before PIN forms lock for 15 minutes. Nothing changed.');
  assert.equal(gate.settings().mode, 'off');
  const saved = await submit('automatic', { week: '150,00' }, PIN);
  assert.equal(saved.response.view.blocks[0].text.text, 'Saved: Automatic within the limits; limits this week R$ 150,00.');
  assert.deepEqual(gate.settings(), { mode: 'automatic', limits: { day: null, week: 15000, month: null } });
});

test('Refuse on a thread message refuses at once and needs no PIN', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const { panel, slack, kicks } = panelFor(gate);
  await (await panel.handle('interactive', action(ACTION.refuse, row.id))).after();
  assert.equal(gate.get(row.id).state, 'refused');
  assert.equal(gate.get(row.id).decided_by, 'owner');
  assert.equal(kicks.length, 1);
  assert.deepEqual(slack.calls, []);
  await (await panel.handle('interactive', action(ACTION.approve, row.id))).after();
  assert.equal(slack.calls[0].args[1].blocks[0].text.text, 'P-0001 is refused: nothing to approve.');
});

test('the thread message has Approve and Refuse while pending, and its outcome after', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate, { amountCents: 9900 });
  const blocks = promptBlocks(row);
  assert.equal(blocks[0].text.text, '*Payment request P-0001* from sara\n*Recipient* KENU EXAMPLE SILVA · ***.123.456-** · Nubank\n*Pix key* kenu@example.com\n*Amount* R$ 99,00\n*Note* Owed to Kenu');
  assert.equal(blocks[1].elements[0].text, 'Waits for you: case by case: every payment waits for the owner');
  assert.deepEqual(blocks[2].elements.map((e) => e.action_id), [ACTION.approve, ACTION.refuse]);
  gate.refuse(row.id);
  const after = promptBlocks(gate.get(row.id));
  assert.equal(after.length, 2);
  assert.equal(after[1].elements[0].text, 'Refused by you.');
});

// ───────────────────────────── exactly once

test('an approval is sent exactly once: double click, replayed interaction, overlapping passes', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.setPin(PIN);
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const runs = [];
  // Two runners on the same ledger stand for two passes that overlap: only the claim keeps them apart.
  const runnerOf = () => createPaymentRunner({
    gate, slack: () => null, store: () => null, providers: ['asaas'], cwd: gate.workspace,
    run: async (command, args, input) => {
      runs.push({ command, args, input: JSON.parse(input) });
      await new Promise((resolve) => setTimeout(resolve, 20));
      return { code: 0, stdout: '{"provider_id":"tr_1","status":"PENDING","receipt_url":null}\n', stderr: '' };
    },
  });
  const runner = runnerOf();
  const other = runnerOf();
  const { panel } = panelFor(gate);
  // The owner clicks Approve twice: two PIN forms. Both are submitted.
  const first = await panel.handle('interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id }));
  const second = await panel.handle('interactive', submission(VIEW.approve, pinValue(PIN), { metadata: row.id }));
  assert.equal(first.response.view.blocks[0].text.text.startsWith('Approved P-0001'), true);
  assert.equal(second.response.view.blocks[0].text.text, 'P-0001 is approved: nothing to approve.');
  // Slack redelivers the same envelope over the socket.
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
  await slack.connect(async () => {}, (type, payload) => panel.handle(type, payload));
  const envelope = { type: 'interactive', envelope_id: 'env-9', accepts_response_payload: true,
    payload: submission(VIEW.approve, pinValue(PIN), { metadata: row.id }) };
  ws[0].emit(envelope);
  await slack.pending;
  ws[0].emit(envelope);
  await slack.pending;
  assert.equal(ws[0].sent.length, 2);
  assert.equal(ws[0].sent[1].payload.view.blocks[0].text.text, 'P-0001 is approved: nothing to approve.');
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

test('the runner posts a pending request in its thread, then shows its outcome and wakes the conversation', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  const row = ask(gate);
  const store = agentStore();
  const slack = fakeSlack();
  const kicked = [];
  const runner = createPaymentRunner({
    gate, slack: () => slack.client, store: () => store, providers: ['asaas'], cwd: gate.workspace,
    run: async () => { throw new Error('not sent'); }, kick: (slug) => kicked.push(slug),
  });
  await runner.step();
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
  const wake = store.db.prepare("SELECT payload FROM queue WHERE kind='wake'").get();
  assert.deepEqual(JSON.parse(wake.payload), {
    note: 'Payment P-0001 was refused by the owner: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). Nothing was sent.',
  });
  assert.deepEqual(kicked, ['sara']);
  await runner.step();
  assert.equal(store.db.prepare("SELECT COUNT(*) AS n FROM queue WHERE kind='wake'").get().n, 1);
});

test('the runner sends an approved request with its exact fields, follows it and reports the receipt', async () => {
  const { gate, clock } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  const row = ask(gate);
  const store = agentStore();
  const runs = [];
  const answers = [
    { code: 0, stdout: '{"provider_id":"tr_1","status":"PENDING","receipt_url":null}\n', stderr: '' },
    { code: 0, stdout: '{"status":"DONE","final":true,"ok":true,"receipt_url":"https://r.example/1","reason":null}\n', stderr: '' },
  ];
  const runner = createPaymentRunner({
    gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace, now: () => clock.now,
    run: async (command, args, input) => { runs.push({ command, args, input: JSON.parse(input) }); return answers.shift(); },
  });
  await runner.step();
  assert.deepEqual(runs[0].args, ['--json', 'pay', 'execute', 'P-0001']);
  assert.deepEqual(runs[0].input, { ...publicRow(gate.get(row.id)), state: 'approved', provider_id: null, provider_status: null });
  assert.equal(gate.get(row.id).state, 'sent');
  assert.equal(gate.get(row.id).provider_id, 'tr_1');
  clock.now += 4999;
  await runner.step();
  assert.equal(runs.length, 1);
  clock.now += 1;
  await runner.step();
  assert.deepEqual(runs[1].args, ['--json', 'pay', 'status', 'P-0001']);
  assert.equal(runs[1].input.provider_id, 'tr_1');
  assert.equal(gate.get(row.id).receipt_url, 'https://r.example/1');
  const wake = store.db.prepare("SELECT payload FROM queue WHERE kind='wake'").get();
  assert.equal(JSON.parse(wake.payload).note,
    'Payment P-0001 sent: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). asaas id tr_1, status DONE, receipt https://r.example/1.');
});

test('a failed send fails the request; work that no longer waits gets a system message in its thread', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  gate.saveSettings({ mode: 'automatic', limits: { day: 5000 } });
  const row = ask(gate);
  const store = agentStore();
  store.stopWork(store.listWork()[0].id);
  const runner = createPaymentRunner({
    gate, slack: () => null, store: () => store, providers: ['asaas'], cwd: gate.workspace,
    run: async () => ({ code: 1, stdout: '', stderr: 'asaas: Asaas answered HTTP 400 on POST /transfers\n  why: invalid_value: Saldo insuficiente\n' }),
  });
  await runner.step();
  assert.equal(gate.get(row.id).state, 'failed');
  assert.equal(gate.get(row.id).reason, 'asaas: Asaas answered HTTP 400 on POST /transfers why: invalid_value: Saldo insuficiente');
  const post = store.db.prepare("SELECT id, payload FROM outbox WHERE id LIKE 'post:payment:%'").get();
  assert.equal(post.id, 'post:payment:P-0001:failed');
  assert.equal(JSON.parse(post.payload).text,
    'System message: Payment P-0001 failed: R$ 10,00 to KENU EXAMPLE SILVA (Pix key kenu@example.com). asaas: Asaas answered HTTP 400 on POST /transfers why: invalid_value: Saldo insuficiente');
});

test('a provider with no withdrawal validation is never run, and a send cut off by a stop fails', async () => {
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
  assert.equal(gate.get(other.id).reason, 'Ignite does not send through otherbank: it has no withdrawal validation for it');
  const cut = ask(gate);
  assert.equal(gate.claim(cut.id), true);
  assert.deepEqual(gate.failInterrupted(), [cut.id]);
  assert.equal(gate.get(cut.id).reason, 'interrupted: Ignite stopped while sending it; check the statement before asking again');
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
  const hook = createWebhook({ gate, token, port: 0, log: (f) => logs.push(f) });
  const port = await hook.listen();
  return { hook, port, logs };
}

test('the webhook approves the request Ignite sent, from the ledger, within 2 seconds', async () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  sentRequest(gate);
  const { hook, port, logs } = await listening(gate);
  try {
    const answer = await post(port, transfer());
    assert.equal(answer.status, 200);
    assert.deepEqual(answer.body, { status: 'APPROVED' });
    assert.equal(answer.ms < 2000, true);
    assert.equal(gate.get('P-0001').answered_operation, 'tr_1');
    assert.deepEqual(logs.at(-1), { event: 'payment-webhook', provider: 'asaas', id: 'P-0001', status: 'APPROVED', reason: null });
    assert.deepEqual((await post(port, transfer())).body, { status: 'APPROVED' });
  } finally {
    await hook.close();
  }
});

test('the webhook refuses a wrong amount, a wrong recipient, an unknown or reused reference and a bad token', async () => {
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
    assert.deepEqual((await post(port, transfer())).body, { status: 'APPROVED' });
    assert.deepEqual((await post(port, transfer({ id: 'tr_2' }))).body, refused('P-0001 was already used by another operation'));
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

test('a direct API call that skipped the gate is refused, even naming a real request', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const headers = { 'asaas-access-token': TOKEN };
  const check = (body) => validate(gate, 'asaas', headers, body, TOKEN);
  assert.deepEqual(check(transfer({ reference: null })),
    { status: 'REFUSED', refuseReason: 'no externalReference: the operation did not pass the payment gate', id: null });
  gate.saveSettings({ mode: 'case_by_case', limits: {} });
  ask(gate);
  assert.equal(check(transfer({ reference: 'P-0001' })).refuseReason, 'P-0001 is pending');
  gate.approve('P-0001');
  assert.equal(check(transfer({ reference: 'P-0001' })).refuseReason, 'P-0001 is approved but Ignite has not sent it');
  gate.saveSettings({ mode: 'off', limits: {} });
  ask(gate);
  assert.equal(check(transfer({ reference: 'P-0002' })).refuseReason, 'P-0002 is refused');
  for (const type of ['PIX_QR_CODE', 'MOBILE_PHONE_RECHARGE', 'PIX_REFUND']) {
    assert.equal(check({ type }).refuseReason, `${type} is not paid through the payment gate`);
  }
});

test('a bill is matched by its line and amount', () => {
  const { gate } = gateAt('2026-10-15T15:00:00Z');
  const line = '23793381286001234107143000012345890460000002000';
  sentRequest(gate, { method: 'bill', recipient: { name: 'ENEL', key: line }, amountCents: 2000, feeCents: 199 });
  const bill = (value, identificationField) => ({ type: 'BILL', bill: { id: 'tr_1', value, identificationField, externalReference: 'P-0001' } });
  const headers = { 'asaas-access-token': TOKEN };
  assert.equal(validate(gate, 'asaas', headers, bill(21.99, line), TOKEN).refuseReason, 'P-0001 approved R$ 20,00, the operation is R$ 21,99');
  assert.equal(validate(gate, 'asaas', headers, bill(20, line.replace(/1/g, '7')), TOKEN).refuseReason, 'P-0001 approved another recipient');
  assert.deepEqual(validate(gate, 'asaas', headers, bill(20, `${line.slice(0, 5)}.${line.slice(5)}`), TOKEN), { status: 'APPROVED', id: 'P-0001' });
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
  assert.equal(cli(workspace, ['payment', 'list', '--state', 'nope']).err, 'unknown state: nope\nchoose from pending, approved, sent, refused, cancelled, failed\nNothing changed.\nignite payment -h');
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

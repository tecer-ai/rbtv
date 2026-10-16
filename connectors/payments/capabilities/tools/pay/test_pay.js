#!/usr/bin/env node
'use strict';

// Suite for the `pay` port command: every cell of the result matrix of its specification, run against
// a synthetic installation (the specification's fixture), a stub `ignite` that keeps the gate's ledger
// in memory and a stub `asaas` connector command, both injected through main(argv, deps).run; help, the
// bare root and an unknown verb run the program as a child process. No network, no money.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const PROGRAM = path.join(__dirname, 'pay.js');
const failures = [];
const tests = [];
function test(name, fn) { tests.push([name, fn]); }
const lines = (text) => text.replace(/\n$/, '').split('\n');

const QR = `000201${'0'.repeat(60)}FAKE6304ABCD`;
const LINE = '23793.38128 60000.000003 00000.000000 1 99990000001800';
const LINE_DIGITS = LINE.replace(/\D/g, '');
const PIA = { name: 'Maria Pia Example', key: 'pia@example.com', key_type: 'EMAIL', document: '123.456.789-00', bank: 'Nu Pagamentos' };
const ENERGY = { name: 'Companhia Example de Energia', key: LINE_DIGITS, key_type: null, document: '12.345.678/0001-00', bank: 'Banco Example' };
const PADARIA = { name: 'Padaria Example', key: QR, key_type: 'QR', document: '12.345.678/0001-00', bank: 'Banco Example' };

// The stub gate: Ignite's ledger in memory, the automatic mode with a day limit, the owner's decisions.
function gateStub() {
  const rows = [];
  const state = { mode: 'automatic', dayLimit: 1500, spent: 0, nextId: 3, sendAs: { id: 'tra_fake0003', status: 'DONE', receipt: 'https://www.asaas.com/i/fake0003' } };
  const money = (cents) => `R$ ${(cents / 100).toFixed(2).replace('.', ',')}`;
  const publicRow = (row) => ({
    id: row.id, agent: 'sara', conversation: 'T0BJAM8PACU:C0SARA0001:1792160000.000100', connector: row.connector, method: row.method,
    recipient: row.recipient, amount_cents: row.amount_cents, fee_cents: row.fee_cents, note: row.note, details: row.details,
    state: row.state, reason: row.reason, decided_by: row.decided_by, decided_at: row.decided_at, resolved: row.resolved || null,
    resolve_error: null, connector_id: row.connector_id, connector_status: row.connector_status, receipt_url: row.receipt_url,
    created_at: '2026-10-16T13:00:00.000Z',
  });
  const answer = (code, body, err = '') => ({ code, stdout: body === null ? '' : `${JSON.stringify(body)}\n`, stderr: err });
  function ignite(args, input) {
    assert.equal(args[0], '--json', 'pay calls ignite with --json first');
    assert.equal(args[1], 'payment');
    const verb = args[2];
    if (verb === 'request') {
      const i = args.indexOf('--connector');
      assert.ok(i > 0, 'pay records the request with --connector');
      assert.ok(!args.includes('--provider'), 'pay never says --provider');
      assert.equal(args[args.indexOf('--request') + 1], '-', 'the request arrives on stdin');
      const request = JSON.parse(input);
      const total = request.amount_cents + (request.fee_cents || 0);
      const row = {
        id: `P-${String(state.nextId++).padStart(4, '0')}`, connector: args[i + 1], method: request.method, recipient: request.recipient,
        amount_cents: request.amount_cents, fee_cents: request.fee_cents || 0, note: request.note, details: request.details || {},
        decided_by: null, decided_at: null, connector_id: null, connector_status: null, receipt_url: null,
      };
      if (state.mode === 'off') Object.assign(row, { state: 'refused', reason: 'payments are off', decided_by: 'rule', decided_at: '2026-10-16T13:00:01.000Z' });
      else if (state.spent + total > state.dayLimit) Object.assign(row, { state: 'pending', reason: `over the daily limit (${money(state.dayLimit - state.spent)} left of ${money(state.dayLimit)})` });
      else {
        state.spent += total;
        Object.assign(row, { state: 'sent', reason: 'within the limits', decided_by: 'rule', decided_at: '2026-10-16T13:00:01.000Z', resolved: request.recipient,
          connector_id: state.sendAs.id, connector_status: state.sendAs.status, receipt_url: state.sendAs.receipt });
      }
      rows.push(row);
      return answer(0, publicRow(row));
    }
    if (verb === 'list') {
      const wanted = args.includes('--state') ? args[args.indexOf('--state') + 1] : null;
      return answer(0, { payments: rows.filter((r) => !wanted || r.state === wanted).slice().reverse().map(publicRow) });
    }
    const row = rows.find((r) => r.id === args[3]);
    if (!row) return answer(1, null, `unknown payment request: ${args[3]}\nNothing changed.\nignite payment list\n`);
    if (verb === 'show') return answer(0, publicRow(row));
    if (verb === 'cancel') {
      if (row.state !== 'pending') return answer(1, null, `${row.id} is ${row.state}: only a pending request can be withdrawn\n`);
      Object.assign(row, { state: 'cancelled', reason: 'withdrawn by the agent' });
      return answer(0, publicRow(row));
    }
    throw new Error(`stub ignite: ${args.join(' ')}`);
  }
  return { rows, state, ignite, publicRow };
}

// The stub connector command, asaas: resolves a draft, cancels at the bank, saves a receipt.
function connectorStub() {
  const calls = [];
  function asaas(args, input) {
    calls.push({ args, input });
    const json = args[0] === '--json';
    const words = json ? args.slice(1) : args;
    const refuse = (what, why, fix) => ({ code: 1, stdout: '', stderr: `asaas: ${what}\n  why: ${why}\n  fix: ${fix}\n` });
    if (words[0] === 'pay' && words[1] === 'resolve' && words[2] === 'draft') {
      assert.ok(json, 'resolve draft is asked with --json');
      const draft = JSON.parse(input);
      assert.equal(draft.connector, 'asaas');
      const key = draft.recipient.key;
      if (draft.method === 'pix') {
        if (key === 'nobody@example.com') return refuse('Asaas has no owner for this key', 'the key is not registered', 'check the key with its owner');
        return { code: 0, stdout: `${JSON.stringify({ recipient: PIA, amount_cents: null, fee_cents: null, changeable: null, details: {} })}\n`, stderr: '' };
      }
      if (draft.method === 'qr') {
        const open = key.includes('OPEN');
        return { code: 0, stdout: `${JSON.stringify({ recipient: { ...PADARIA, key }, amount_cents: open ? null : 3590, fee_cents: null, changeable: open, details: {} })}\n`, stderr: '' };
      }
      if (draft.method === 'bill') {
        return { code: 0, stdout: `${JSON.stringify({ recipient: ENERGY, amount_cents: 1800, fee_cents: 0, changeable: false, details: { due_date: '2026-10-20', company: 'Companhia Example de Energia' } })}\n`, stderr: '' };
      }
      if (draft.method === 'recharge') {
        return { code: 0, stdout: `${JSON.stringify({ recipient: { name: null, key: '11912345678', key_type: 'PHONE', document: null, bank: null }, amount_cents: null, fee_cents: null, changeable: null, details: {} })}\n`, stderr: '' };
      }
    }
    if (words[0] === 'cancel') {
      return { code: 0, stdout: json ? `${JSON.stringify({ id: words[1], connector_id: 'tra_fake0003', status: 'CANCELLED' })}\n` : `Cancelled   ${words[1]} at Asaas (tra_fake0003): CANCELLED\nThe gate counts it until Ignite reads the operation as cancelled.\n`, stderr: '' };
    }
    if (words[0] === 'receipt') {
      const out = words.includes('--out') ? words[words.indexOf('--out') + 1] : `${words[1]}.pdf`;
      if (fs.existsSync(out)) return refuse(`${out} already exists`, 'the receipt is never written over a file', 'pass --out with another path');
      fs.writeFileSync(out, Buffer.alloc(41 * 1024, 1));
      const link = words[1].startsWith('https://') ? words[1] : 'https://www.asaas.com/i/fake0003';
      return { code: 0, stdout: json ? `${JSON.stringify({ path: path.resolve(out), bytes: 41 * 1024, receipt_url: link })}\n` : `Saved     ${path.resolve(out)} (41 KB)\nReceipt   ${link}\n`, stderr: '' };
    }
    throw new Error(`stub asaas: ${args.join(' ')}`);
  }
  return { calls, asaas };
}

function fixture({ payments = {} } = {}) {
  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'pay-inst-'));
  fs.mkdirSync(path.join(installation, '.rbtv', 'config', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'install.json'), JSON.stringify({ schema: 6, components: { 'connectors/asaas': {} } }));
  const config = {
    slack: { team: 'T0BJAM8PACU', botUserId: 'U0BOT', ownerUserId: 'U0OWNER001', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'w' },
    tools: { cast: 'cast', stools: 'slack', audio: 'elevenlabs' }, routes: { C0SARA0001: 'sara' },
  };
  if (payments !== null) config.payments = payments;
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify(config));
  const home = path.join(installation, '.rbtv', 'agents', 'sara');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ name: 'sara', harness: 'claude', model: 'opus-5-5', effort: 'medium' }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt\n');
  const gate = gateStub();
  const connector = connectorStub();
  const commands = { ignite: gate.ignite, asaas: connector.asaas };
  const onPath = new Set(['ignite', 'asaas']);
  const fx = {
    installation, home, gate, connector, onPath, cwd: home,
    async run(argv, { env = {}, turn = true } = {}) {
      const { main } = require(PROGRAM);
      let out = '';
      let err = '';
      const code = await main(argv, {
        cwd: fx.cwd,
        env: { RBTV_AGENT_HOME: home, ...(turn ? { IGNITE_CONVERSATION: 'T0BJAM8PACU:C0SARA0001:1792160000.000100' } : {}), PAY_GATE_WAIT: '0', ...env },
        stdout: (t) => { out += t; }, stderr: (t) => { err += t; },
        which: (name) => (onPath.has(name) ? `/stub/bin/${name}` : null),
        run: async (command, args, input) => {
          const name = path.basename(command);
          if (!commands[name]) throw new Error(`stub: ${name} is not a command`);
          return commands[name](args, input);
        },
      });
      return { code, out, err };
    },
  };
  return fx;
}

function child(argv, cwd = os.tmpdir()) {
  const env = { ...process.env };
  delete env.RBTV_AGENT_HOME;
  const p = spawnSync(process.execPath, [PROGRAM, ...argv], { cwd, encoding: 'utf8', env });
  return { code: p.status, out: p.stdout, err: p.stderr };
}

const three = (r, what, why, fix) => {
  const got = lines(r.err);
  assert.equal(got.length, 3, `three lines: ${r.err}`);
  assert.equal(got[0], what);
  if (why != null) assert.equal(got[1], `  why: ${why}`); else assert.match(got[1], /^ {2}why: /);
  if (fix != null) assert.equal(got[2], `  fix: ${fix}`); else assert.match(got[2], /^ {2}fix: /);
};

test('help at every depth and position exits 0 with no setup; bare root exits 2; no service verbs', () => {
  for (const argv of [['-h'], ['--help'], ['--json', '-h'], ['pix', '-h'], ['pix', '--from', 'asaas', '-h'], ['-h', 'pix'], ['qr', '--help'], ['bill', '-h'], ['recharge', '-h'], ['list', '-h'], ['show', '-h'], ['cancel', '-h'], ['receipt', '-h'], ['accounts', '-h'], ['pix', '--nope', '-h']]) {
    const r = child(argv);
    assert.equal(r.code, 0, `${argv.join(' ')}: ${r.err}`);
    assert.match(r.out, /^usage: pay/);
    assert.equal(r.err, '');
  }
  const root = child(['-h']);
  assert.match(root.out, /^usage: pay \[-h\] \[--json\] COMMAND \.\.\.\n/);
  assert.match(root.out, /pix {7}Pix to a key: looks up its owner, then asks the gate\n/);
  assert.match(root.out, /accounts {2}the accounts --from may name, and their connectors\n/);
  assert.doesNotMatch(root.out, /resolve, execute, status|waking service only|pay execute|pay status/, 'no service verbs');
  assert.match(root.out, /Start: pay accounts, then pay pix -h/);
  for (const line of lines(root.out)) assert.ok(line.length <= 80, `80 columns: ${line}`);
  assert.match(child(['pix', '-h']).out, /^usage: pay pix \[-h\] \[--json\] --from ACCOUNT --to KEY --amount VALUE --note TEXT\n {15}\[--type \{CPF,CNPJ,EMAIL,PHONE,EVP\}\]\n/);
  assert.match(child(['pix', '-h']).out, /Example: pay pix --from asaas --to pia@example.com --amount 18,00 --note "Aula"\nNext: pay show P-0007\n/);
  assert.match(child(['qr', '-h']).out, /^usage: pay qr \[-h\] \[--json\] --from ACCOUNT --code PAYLOAD --note TEXT \[--amount VALUE\]\n/);
  assert.match(child(['bill', '-h']).out, /^usage: pay bill \[-h\] \[--json\] --from ACCOUNT --line DIGITS --note TEXT\n/);
  assert.match(child(['bill', '-h']).out, /amount\s+plus fee counts toward the limits/);
  assert.match(child(['recharge', '-h']).out, /^usage: pay recharge \[-h\] \[--json\] --from ACCOUNT --number PHONE --amount VALUE --note TEXT\n/);
  assert.match(child(['list', '-h']).out, /^usage: pay list \[-h\] \[--json\] \[--state \{pending,approved,sent,uncertain,refused,cancelled,failed\}\]\n/);
  assert.match(child(['show', '-h']).out, /^usage: pay show \[-h\] \[--json\] ID\n/);
  assert.match(child(['cancel', '-h']).out, /^usage: pay cancel \[-h\] \[--json\] ID\n/);
  assert.match(child(['receipt', '-h']).out, /^usage: pay receipt \[-h\] \[--json\] \[--out PATH\] REF\n/);
  assert.match(child(['accounts', '-h']).out, /^usage: pay accounts \[-h\] \[--json\]\n/);
  const bare = child([]);
  assert.equal(bare.code, 2);
  assert.match(bare.out, /^usage: pay/);
  for (const verb of ['resolve', 'execute', 'status']) {
    const r = child([verb, 'P-0001']);
    assert.equal(r.code, 2, `${verb} is not a verb`);
    assert.equal(lines(r.err)[0], `pay: unknown command "${verb}"; the commands are pix, qr, bill, recharge, list, show, cancel, receipt, accounts`);
  }
  const unknown = child(['send']);
  assert.equal(unknown.code, 2);
  three(unknown, 'pay: unknown command "send"; the commands are pix, qr, bill, recharge, list, show, cancel, receipt, accounts');
});

test('S18 missing --from, exit 2, before any call', async () => {
  const fx = fixture();
  const r = await fx.run(['pix', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  assert.equal(r.code, 2);
  assert.equal(r.out, '');
  three(r, 'pay: pix refused: --from ACCOUNT is required',
    'pay never picks the account money leaves; name it, even when one is configured',
    'pay pix --from asaas --to pia@example.com --amount 18,00 --note "Aula"   (pay accounts lists the accounts)');
  assert.deepEqual(fx.connector.calls, []);
  assert.deepEqual(fx.gate.rows, []);
  for (const verb of ['qr', 'bill', 'recharge']) {
    const other = await fx.run([verb, '--note', 'x']);
    assert.equal(other.code, 2);
    assert.equal(lines(other.err)[0], `pay: ${verb} refused: --from ACCOUNT is required`);
  }
});

test('S11 invalid words, exit 2, three lines', async () => {
  const fx = fixture();
  const cases = [
    [['pix', '--from', 'asaas', '--amount', '18,00', '--note', 'Aula'], 'pay: pix refused: --to KEY is required', null, 'pay pix --from asaas --to KEY --amount 18,00 --note "Aula"'],
    [['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', 'abc', '--note', 'x'], 'pay: pix refused: --amount "abc" is not an amount in reais (like 99 or 99,90)', null, null],
    [['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '0', '--note', 'x'], 'pay: pix refused: --amount 0 is below R$ 0,01', null, null],
    [['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1', '--note', 'x'.repeat(141)], 'pay: pix refused: --note is longer than 140 characters', null, null],
    [['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1'], 'pay: pix refused: --note TEXT is required', null, null],
    [['pix', '--from', 'asaas', '--to', QR, '--amount', '1', '--note', 'x'], `pay: pix refused: --to ${QR.slice(0, 12)}… is a Pix QR code (copy and paste), not a Pix key`, null, 'pay qr --from asaas --code PAYLOAD --note TEXT'],
    [['qr', '--from', 'asaas', '--code', 'abc', '--note', 'x'], 'pay: qr refused: --code must start with 000201', null, null],
    [['bill', '--from', 'asaas', '--line', '123456789012345678901234567890', '--note', 'x'], 'pay: bill refused: --line has 30 digits; a digitable line has 47 or 48', null, null],
    [['recharge', '--from', 'asaas', '--number', '1234', '--amount', '20', '--note', 'x'], 'pay: recharge refused: a mobile number has 11 digits with its area code', null, null],
    [['recharge', '--from', 'asaas', '--number', '11912345678', '--amount', '20'], 'pay: recharge refused: --note TEXT is required', null, null],
    [['list', '--state', 'nope'], 'pay: list refused: --state nope is not one of pending, approved, sent, uncertain, refused, cancelled, failed', null, null],
    [['show'], 'pay: show refused: ID is required', null, null],
    [['cancel'], 'pay: cancel refused: ID is required', null, null],
    [['receipt'], 'pay: receipt refused: REF is required', null, null],
    [['accounts', 'extra'], 'pay: accounts takes no argument', null, null],
    [['pix', '--from', 'asaas', '--to', 'a@b.c', '--amount', '1', '--note', 'x', '--bogus'], 'pay: pix has no option --bogus', null, null],
  ];
  for (const [argv, what, why, fix] of cases) {
    const r = await fx.run(argv);
    assert.equal(r.code, 2, `${argv.join(' ')}: exit ${r.code} ${r.err}`);
    assert.equal(r.out, '');
    three(r, what, why, fix);
  }
  assert.deepEqual(fx.connector.calls, []);
  assert.deepEqual(fx.gate.rows, []);
});

test('S12 ambiguous 11-digit key, exit 2, --type decides', async () => {
  const fx = fixture();
  const r = await fx.run(['pix', '--from', 'asaas', '--to', '11912345678', '--amount', '20', '--note', 'x']);
  assert.equal(r.code, 2);
  three(r, 'pay: pix refused: 11912345678 may be a CPF or a phone', 'both are 11 digits; the key type decides whom the bank looks up', 'add --type CPF or --type PHONE');
  assert.deepEqual(fx.connector.calls, []);
  const typed = await fx.run(['--json', 'pix', '--from', 'asaas', '--to', '11912345678', '--amount', '20', '--note', 'x', '--type', 'PHONE']);
  assert.equal(typed.code, 0, typed.err);
  assert.equal(JSON.parse(fx.connector.calls[0].input).recipient.key_type, 'PHONE');
});

test('S16 outside a turn, every paying verb, before any lookup', async () => {
  const fx = fixture();
  for (const [verb, argv] of [['pix', ['--to', 'pia@example.com', '--amount', '1', '--note', 'x']], ['qr', ['--code', QR, '--note', 'x']], ['bill', ['--line', LINE, '--note', 'x']], ['recharge', ['--number', '11912345678', '--amount', '20', '--note', 'x']]]) {
    const r = await fx.run([verb, '--from', 'asaas', ...argv], { turn: false });
    assert.equal(r.code, 1, verb);
    three(r, `pay: pay ${verb} runs inside an Ignite turn`, 'IGNITE_CONVERSATION is not set, so no conversation can be woken with the outcome', "pay from an agent's turn; a person pays in the bank's app");
  }
  assert.deepEqual(fx.connector.calls, []);
  const list = await fx.run(['list'], { turn: false });
  assert.equal(list.code, 0, 'a read verb needs no turn');
});

test('S17 first use: ignite off PATH, no payments section, the connector command missing', async () => {
  const fx = fixture();
  fx.onPath.delete('ignite');
  const noIgnite = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1', '--note', 'x']);
  assert.equal(noIgnite.code, 1);
  three(noIgnite, 'pay: the ignite command is not on PATH', "pay pays only through Ignite's payment gate", "run pay inside an Ignite agent's turn");
  fx.onPath.add('ignite');
  const bare = fixture({ payments: null });
  const noSection = await bare.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1', '--note', 'x']);
  assert.equal(noSection.code, 1);
  three(noSection, "pay: Ignite's payment gate: config has no payments section", 'nothing was recorded or changed', 'the owner sets up payments (runbook); pay accounts shows the state');
  assert.deepEqual(bare.connector.calls, []);
  fx.onPath.delete('asaas');
  const noCommand = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1', '--note', 'x']);
  assert.equal(noCommand.code, 1);
  three(noCommand, 'pay: pix refused: the account asaas has no command on PATH', 'the asaas connector is not installed here (rbtv list --installed)', 'rbtv add connectors/asaas');
  assert.deepEqual(fx.gate.rows, []);
});

test('S10 unknown account, exit 1, naming the configured accounts', async () => {
  const fx = fixture();
  const r = await fx.run(['pix', '--from', 'nubank', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  assert.equal(r.code, 1);
  three(r, 'pay: pix refused: no account named "nubank"', "the accounts are the entries of Ignite's payments configuration: asaas", 'pay pix --from asaas …   (pay accounts)');
  assert.deepEqual(fx.connector.calls, []);
});

test('S1 pix sent by rule: the rows, the draft resolution, the gate request with the resolved recipient; S1j is the row', async () => {
  const fx = fixture();
  const r = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  assert.equal(r.err, '');
  assert.equal(r.code, 0);
  assert.deepEqual(lines(r.out), [
    'Recipient   Maria Pia Example · 123.456.789-00 · Nu Pagamentos',
    'Amount      R$ 1,00',
    'State       sent: approved by rule (within the limits)',
    'Request     P-0003, asaas id tra_fake0003, receipt https://www.asaas.com/i/fake0003',
  ]);
  assert.equal(fx.connector.calls.length, 1);
  assert.deepEqual(fx.connector.calls[0].args, ['--json', 'pay', 'resolve', 'draft']);
  assert.deepEqual(JSON.parse(fx.connector.calls[0].input), { connector: 'asaas', method: 'pix', recipient: { key: 'pia@example.com', key_type: null }, amount_cents: 100, note: 'Teste R$1' });
  assert.equal(fx.gate.rows.length, 1);
  assert.deepEqual(fx.gate.rows[0].recipient, PIA);
  assert.deepEqual([fx.gate.rows[0].method, fx.gate.rows[0].amount_cents, fx.gate.rows[0].fee_cents, fx.gate.rows[0].note, fx.gate.rows[0].details], ['pix', 100, 0, 'Teste R$1', {}]);
  const json = await fx.run(['--json', 'pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  assert.equal(json.code, 0);
  const row = JSON.parse(json.out);
  assert.equal(row.id, 'P-0004');
  assert.equal(row.connector, 'asaas');
  assert.equal(row.connector_id, 'tra_fake0003');
  assert.equal(row.connector_status, 'DONE');
  assert.ok(!('provider' in row) && !('provider_id' in row), 'the row says connector');
  assert.equal(lines(json.out).length, 1);
});

test('S2 pix pending: the rows and the Next line; S2j', async () => {
  const fx = fixture();
  fx.gate.state.spent = 100;
  const r = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    'Recipient   Maria Pia Example · 123.456.789-00 · Nu Pagamentos',
    'Amount      R$ 18,00',
    'State       pending: over the daily limit (R$ 14,00 left of R$ 15,00)',
    'Request     P-0003, sent to the owner for approval',
    'Next        end this turn waiting_workers: Ignite wakes this conversation with the owner\'s decision; pay show P-0003 shows it meanwhile',
  ]);
  const json = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula', '--json']);
  const row = JSON.parse(json.out);
  assert.equal(row.state, 'pending');
  assert.equal(row.reason, 'over the daily limit (R$ 14,00 left of R$ 15,00)');
  assert.equal(row.decided_by, null);
  assert.equal(row.connector_id, null);
});

test('S3 list and S3e, S3j', async () => {
  const fx = fixture();
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  const r = await fx.run(['list']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    'P-0004  pending       R$ 18,00  Maria Pia Example  (over the daily limit (R$ 14,00 left of R$ 15,00))',
    'P-0003  sent           R$ 1,00  Maria Pia Example  (within the limits)',
  ]);
  const empty = await fx.run(['list', '--state', 'refused']);
  assert.equal(empty.code, 0);
  assert.equal(empty.out, 'No refused payment requests.\n');
  const json = await fx.run(['--json', 'list']);
  const body = JSON.parse(json.out);
  assert.equal(body.payments.length, 2);
  assert.equal(body.payments[0].id, 'P-0004');
});

test('S4 show, S4j, and an unknown id', async () => {
  const fx = fixture();
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  const r = await fx.run(['show', 'P-0003']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    'Request     P-0003  pix',
    'Recipient   Maria Pia Example · 123.456.789-00 · Nu Pagamentos',
    'Key         pia@example.com',
    'Amount      R$ 1,00',
    'Note        Teste R$1',
    'State       sent: approved by rule (within the limits)',
    'Connector   asaas, id tra_fake0003 (DONE)',
    'Receipt     https://www.asaas.com/i/fake0003',
  ]);
  const json = await fx.run(['show', 'P-0003', '--json']);
  assert.equal(JSON.parse(json.out).id, 'P-0003');
  const unknown = await fx.run(['show', 'P-0099']);
  assert.equal(unknown.code, 1);
  three(unknown, 'pay: unknown payment request: P-0099', "pay list lists this agent's request ids; an id it does not list is another agent's or does not exist", 'pay list');
});

test('S5 cancel: pending withdrawn, a sent Pix cancelled at the bank; S5r refusals', async () => {
  const fx = fixture();
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  fx.gate.state.spent = 100;
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  const pending = await fx.run(['cancel', 'P-0004']);
  assert.equal(pending.code, 0, pending.err);
  assert.equal(pending.out, 'Cancelled   P-0004: withdrawn before the owner decided\n');
  assert.equal(fx.gate.rows[1].state, 'cancelled');
  const again = await fx.run(['cancel', 'P-0004']);
  assert.equal(again.code, 1);
  three(again, 'pay: P-0004 is cancelled: nothing to cancel', 'a pending request is withdrawn, a sent one is cancelled at the bank while it can be', 'pay show P-0004');
  const sent = await fx.run(['cancel', 'P-0003']);
  assert.equal(sent.code, 0, sent.err);
  assert.deepEqual(lines(sent.out), ['Cancelled   P-0003 at asaas (tra_fake0003): CANCELLED', 'The gate counts it until Ignite reads the operation as cancelled.']);
  assert.deepEqual(fx.connector.calls.at(-1).args, ['--json', 'cancel', 'P-0003']);
  const json = await fx.run(['--json', 'cancel', 'P-0003']);
  assert.deepEqual(JSON.parse(json.out), { id: 'P-0003', connector_id: 'tra_fake0003', status: 'CANCELLED' });
  fx.gate.state.sendAs = { id: 'pq_8', status: 'DONE', receipt: null };
  fx.gate.state.spent = 0;
  fx.gate.state.dayLimit = 10000;
  fx.gate.state.nextId = 8;
  await fx.run(['qr', '--from', 'asaas', '--code', QR, '--note', 'Pão']);
  assert.deepEqual([fx.gate.rows.at(-1).id, fx.gate.rows.at(-1).state], ['P-0008', 'sent']);
  const qr = await fx.run(['cancel', 'P-0008']);
  assert.equal(qr.code, 1);
  three(qr, 'pay: P-0008 is a qr payment asaas already has', 'asaas cancels Pix key transfers and bills only', "ask the owner to cancel it in the bank's app while it allows it");
});

test('S6 show after the owner refused, S7 refused at request (mode off), S7j', async () => {
  const fx = fixture();
  fx.gate.state.spent = 100;
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  Object.assign(fx.gate.rows[0], { state: 'refused', reason: 'refused by the owner', decided_by: 'owner', decided_at: '2026-10-16T13:05:00.000Z' });
  const show = await fx.run(['show', 'P-0003']);
  assert.equal(show.code, 0);
  assert.deepEqual(lines(show.out), [
    'Request     P-0003  pix', 'Recipient   Maria Pia Example · 123.456.789-00 · Nu Pagamentos', 'Key         pia@example.com',
    'Amount      R$ 18,00', 'Note        Aula', 'State       refused: refused by the owner', 'Connector   asaas, id -', 'Receipt     -',
  ]);
  fx.gate.state.mode = 'off';
  const r = await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  assert.equal(r.code, 1);
  assert.equal(r.err, '');
  assert.deepEqual(lines(r.out), [
    'Recipient   Maria Pia Example · 123.456.789-00 · Nu Pagamentos', 'Amount      R$ 18,00', 'State       refused: payments are off', 'Request     P-0004',
  ]);
  const json = await fx.run(['--json', 'pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  assert.equal(json.code, 1);
  assert.equal(JSON.parse(json.out).state, 'refused');
});

test('S8 receipt saved, S8j, S8r without a receipt and over an existing file', async () => {
  const fx = fixture();
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '1,00', '--note', 'Teste R$1']);
  fx.cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'pay-cwd-'));
  const expected = path.join(fx.cwd, 'P-0003.pdf');
  const r = await fx.run(['receipt', 'P-0003']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [`Saved     ${expected} (41 KB)`, 'Receipt   https://www.asaas.com/i/fake0003']);
  assert.ok(fx.connector.calls.at(-1).args.includes('receipt'));
  const again = await fx.run(['receipt', 'P-0003']);
  assert.equal(again.code, 1);
  three(again, `pay: ${expected} already exists`, 'the receipt is never written over a file', 'pass --out with another path');
  const out = path.join(fx.cwd, 'other.pdf');
  const json = await fx.run(['--json', 'receipt', 'P-0003', '--out', out]);
  assert.equal(json.code, 0, json.err);
  assert.deepEqual(JSON.parse(json.out), { path: out, bytes: 41 * 1024, receipt_url: 'https://www.asaas.com/i/fake0003' });
  fx.gate.state.spent = 100;
  await fx.run(['pix', '--from', 'asaas', '--to', 'pia@example.com', '--amount', '18,00', '--note', 'Aula']);
  await fx.run(['cancel', 'P-0004']);
  const none = await fx.run(['receipt', 'P-0004']);
  assert.equal(none.code, 1);
  three(none, 'pay: P-0004 has no receipt yet', 'it is cancelled; the bank gives a receipt once the payment is done', 'pay show P-0004 shows when it has one');
  const link = await fx.run(['receipt', 'https://www.asaas.com/i/fake0003', '--out', path.join(fx.cwd, 'link.pdf')]);
  assert.equal(link.code, 0, link.err);
  const other = await fx.run(['receipt', 'nonsense']);
  assert.equal(other.code, 1);
  assert.match(other.err, /^pay: nonsense is neither a request id nor a receipt link\n/);
});

test('S9a accounts, S9j, S9e with no payments section; nothing contacts the bank', async () => {
  const fx = fixture();
  const r = await fx.run(['accounts']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), ['Account   Connector   Command   Adapter', 'asaas     asaas       found     found (lib/withdrawal-validation.js)']);
  const json = await fx.run(['accounts', '--json']);
  assert.deepEqual(JSON.parse(json.out), { accounts: [{ name: 'asaas', connector: 'asaas', command: true, adapter: true }] });
  assert.deepEqual(fx.connector.calls, []);
  fx.onPath.delete('asaas');
  const missing = await fx.run(['accounts']);
  assert.match(missing.out, /^Account {3}Connector {3}Command {3}Adapter\nasaas {5}asaas {7}missing {3}found/);
  const bare = fixture({ payments: null });
  const none = await bare.run(['accounts']);
  assert.equal(none.code, 1);
  three(none, 'pay: no accounts', "Ignite's config.json has no payments section, so the gate is not set up", 'the owner adds "payments": {} and restarts the service (runbook); until then pay refuses every payment');
  const other = fixture({ payments: { connectors: ['asaas', 'nubank'] } });
  const two = await other.run(['--json', 'accounts']);
  assert.deepEqual(JSON.parse(two.out).accounts.map((a) => [a.name, a.command, a.adapter]), [['asaas', true, true], ['nubank', false, false]]);
  const legacy = fixture({ payments: { providers: ['asaas'] } });
  assert.deepEqual(JSON.parse((await legacy.run(['--json', 'accounts'])).out).accounts.map((a) => a.name), ['asaas'], 'the older key still names the accounts');
});

test('S10 connector failures pass the connector\'s three lines through with pay: in front', async () => {
  const fx = fixture();
  const r = await fx.run(['pix', '--from', 'asaas', '--to', 'nobody@example.com', '--amount', '1', '--note', 'x']);
  assert.equal(r.code, 1);
  assert.equal(r.out, '');
  three(r, 'pay: asaas: Asaas has no owner for this key', 'the key is not registered', 'check the key with its owner');
  assert.deepEqual(fx.gate.rows, [], 'nothing recorded');
});

test('S13 bill: the simulation line, fee and details reach the gate', async () => {
  const fx = fixture();
  fx.gate.state.spent = 100;
  const r = await fx.run(['bill', '--from', 'asaas', '--line', LINE, '--note', 'Luz']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    'Simulated   bill R$ 18,00, fee R$ 0,00, due 2026-10-20: R$ 18,00 counts toward the limits',
    'Recipient   Companhia Example de Energia · 12.345.678/0001-00 · Banco Example',
    'Amount      R$ 18,00',
    'State       pending: over the daily limit (R$ 14,00 left of R$ 15,00)',
    'Request     P-0003, sent to the owner for approval',
    'Next        end this turn waiting_workers: Ignite wakes this conversation with the owner\'s decision; pay show P-0003 shows it meanwhile',
  ]);
  const draft = JSON.parse(fx.connector.calls[0].input);
  assert.deepEqual(draft, { connector: 'asaas', method: 'bill', recipient: { key: LINE_DIGITS, key_type: null }, amount_cents: null, note: 'Luz' });
  assert.deepEqual([fx.gate.rows[0].method, fx.gate.rows[0].amount_cents, fx.gate.rows[0].fee_cents, fx.gate.rows[0].details], ['bill', 1800, 0, { due_date: '2026-10-20', company: 'Companhia Example de Energia' }]);
  const json = await fx.run(['--json', 'bill', '--from', 'asaas', '--line', LINE, '--note', 'Luz']);
  assert.equal(lines(json.out).length, 1, 'no Simulated line with --json');
});

test('S14 qr: a fixed amount; the amount refusals', async () => {
  const fx = fixture();
  fx.gate.state.spent = 100;
  const r = await fx.run(['qr', '--from', 'asaas', '--code', QR, '--note', 'Pão']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out).slice(0, 4), [
    'Recipient   Padaria Example · 12.345.678/0001-00 · Banco Example', 'Amount      R$ 35,90',
    'State       pending: over the daily limit (R$ 14,00 left of R$ 15,00)', 'Request     P-0003, sent to the owner for approval',
  ]);
  assert.equal(fx.gate.rows[0].amount_cents, 3590);
  const open = `000201${'0'.repeat(50)}OPEN6304ABCD`;
  const noAmount = await fx.run(['qr', '--from', 'asaas', '--code', open, '--note', 'Pão']);
  assert.equal(noAmount.code, 1);
  three(noAmount, 'pay: this QR code carries no amount', 'the payer chooses it', 'pay qr --from asaas --code PAYLOAD --amount 35,00 --note TEXT');
  const differs = await fx.run(['qr', '--from', 'asaas', '--code', QR, '--note', 'Pão', '--amount', '30']);
  assert.equal(differs.code, 1);
  three(differs, 'pay: this QR code charges R$ 35,90, not R$ 30,00', 'its amount cannot be changed', 'pay qr --from asaas --code PAYLOAD --note TEXT   (without --amount)');
  const chosen = await fx.run(['--json', 'qr', '--from', 'asaas', '--code', open, '--note', 'Pão', '--amount', '12,50']);
  assert.equal(chosen.code, 0, chosen.err);
  assert.equal(JSON.parse(chosen.out).amount_cents, 1250);
});

test('S15 recharge: the phone as 11 digits, the note recorded', async () => {
  const fx = fixture();
  fx.gate.state.spent = 100;
  const r = await fx.run(['recharge', '--from', 'asaas', '--number', '+55 11 91234-5678', '--amount', '20,00', '--note', 'Celular']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out).slice(0, 4), ['Recipient   11912345678', 'Amount      R$ 20,00', 'State       pending: over the daily limit (R$ 14,00 left of R$ 15,00)', 'Request     P-0003, sent to the owner for approval']);
  assert.deepEqual(JSON.parse(fx.connector.calls[0].input).recipient, { key: '11912345678', key_type: 'PHONE' });
  assert.deepEqual([fx.gate.rows[0].method, fx.gate.rows[0].note, fx.gate.rows[0].recipient.key], ['recharge', 'Celular', '11912345678']);
});

test('--json before or after the verb; a refusal with --json prints nothing on stdout', async () => {
  const fx = fixture();
  const before = await fx.run(['--json', 'accounts']);
  const after = await fx.run(['accounts', '--json']);
  assert.equal(before.out, after.out);
  const refused = await fx.run(['--json', 'pix', '--from', 'nubank', '--to', 'a@b.c', '--amount', '1', '--note', 'x']);
  assert.equal(refused.code, 1);
  assert.equal(refused.out, '');
  assert.equal(lines(refused.err).length, 3);
});

(async () => {
  for (const [name, fn] of tests) {
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push(name);
      console.log(`FAIL ${name}: ${error.message}`);
    }
  }
  process.exit(failures.length ? 1 : 0);
})();

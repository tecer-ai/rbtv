#!/usr/bin/env node
'use strict';

// Suite for the `message` port command: every cell of the result matrix of its specification, run
// against a synthetic installation (the specification's fixture) with stub adapters, in process
// through main(argv, deps) and, for help and the bare root, as a child process. No network: the stub
// Slack and WhatsApp adapters record each call in calls.json beside them and answer from
// scenario.json, which a test rewrites to stage a transition.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const PROGRAM = path.join(__dirname, 'message.js');
const SEND = path.join(__dirname, 'lib', 'send.js');

const failures = [];
const tests = [];
function test(name, fn) { tests.push([name, fn]); }

const STUB_ADAPTER = `'use strict';
const fs = require('node:fs');
const path = require('node:path');
const HERE = __dirname;
const NAME = path.basename(path.resolve(HERE, '..'));
const scenario = () => JSON.parse(fs.readFileSync(path.join(HERE, 'scenario.json'), 'utf8'));
function record(op, input) {
  const file = path.join(HERE, 'calls.json');
  const calls = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : [];
  calls.push({ op, input });
  fs.writeFileSync(file, JSON.stringify(calls));
}
function fail(code, message) { const e = new Error(message); e.code = code; throw e; }
function nextId(s) {
  const ids = s.ids || [];
  const id = ids.shift();
  fs.writeFileSync(path.join(HERE, 'scenario.json'), JSON.stringify({ ...s, ids }));
  return id || '0.0';
}
module.exports = {
  address(value) {
    const s = scenario();
    if (s.contact.test ? false : new RegExp(s.contact).test(value)) return { contact: value };
    if (new RegExp(s.group).test(value)) return { group: value };
    fail('address', s.addressWhy.replace('ADDRESS', value));
  },
  async account() { return scenario().account; },
  operations: {
    async 'message.send'(input) {
      record('message.send', input);
      const s = scenario();
      if (s.sendError) fail(s.sendCode || null, s.sendError);
      if (!input.text) fail(null, NAME + ' answered no_text');
      const conversation = input.contact ? s.direct : input.group;
      return { conversation, id: nextId(s) };
    },
    async 'message.file'(input) {
      record('message.file', input);
      const s = scenario();
      if (s.fileError) fail(null, s.fileError);
      const conversation = input.send.conversation || s.direct;
      return { id: nextId(s), conversation };
    },
    async 'message.history'(input) {
      record('message.history', input);
      const s = scenario();
      const thread = (s.threads || {})[input.thread];
      if (!thread) fail('thread', NAME + ' answered thread_not_found for ' + input.thread + ' in ' + input.conversation);
      return { events: thread };
    },
  },
};
`;

// The specification's fixture: slack with an adapter; whatsapp and google installed with no adapter.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'message-root-'));
  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'message-inst-'));
  const record = (name, extra) => {
    fs.mkdirSync(path.join(root, 'connectors', name), { recursive: true });
    fs.writeFileSync(path.join(root, 'connectors', name, `${name}.json`), JSON.stringify({
      description: `${name} stub`, dependencies: [], type: 'messaging', provides: ['message.send', 'message.history', 'message.file'], ...extra,
    }));
  };
  record('slack');
  record('whatsapp');
  record('google', { serves: ['calendar'] });
  const lib = path.join(root, 'connectors', 'slack', 'capabilities', 'tools', 'slack', 'lib');
  fs.mkdirSync(lib, { recursive: true });
  fs.writeFileSync(path.join(lib, 'messaging.js'), STUB_ADAPTER);
  const slackScenario = {
    account: 'T0BJAM8PACU', direct: 'D0OWNERDM1', contact: '^[UW][A-Z0-9]+$', group: '^[CGD][A-Z0-9]+$',
    addressWhy: 'slack addresses are a user id (U...) or a channel id (C...); a mail address is google\'s',
    ids: ['1792160000.000100'],
    threads: {
      '1792160000.000100': [
        { connector: 'slack', account: 'T0BJAM8PACU', id: '1792160000.000100', at: 1792160000000, from: 'U0BOTSARA1', group: null, conversation: 'D0OWNERDM1', thread: null, text: 'Receipt saved: P-0003.pdf', isSelf: true, raw: { ts: '1792160000.000100' } },
        { connector: 'slack', account: 'T0BJAM8PACU', id: '1792160030.000200', at: 1792160030000, from: 'U0OWNER001', group: null, conversation: 'D0OWNERDM1', thread: '1792160000.000100', text: 'Thanks. Was it the full amount? I remember the invoice being R$ 18,00.', isSelf: false, raw: { ts: '1792160030.000200' } },
        { connector: 'slack', account: 'T0BJAM8PACU', id: '1792160060.000300', at: 1792160060000, from: 'U0BOTSARA1', group: null, conversation: 'D0OWNERDM1', thread: '1792160000.000100', text: 'Done.', isSelf: true, raw: { ts: '1792160060.000300' } },
      ],
    },
  };
  fs.writeFileSync(path.join(lib, 'scenario.json'), JSON.stringify(slackScenario));
  fs.mkdirSync(path.join(installation, '.rbtv', 'config', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'install.json'), JSON.stringify({
    schema: 6, components: { 'connectors/slack': {}, 'connectors/whatsapp': {}, 'connectors/google': {} },
  }));
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify({
    slack: { team: 'T0BJAM8PACU', botUserId: 'U0BOTSARA1', ownerUserId: 'U0OWNER001', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'w' },
    tools: { cast: 'cast', stools: 'slack', audio: 'elevenlabs' }, dmAgent: 'master', routes: { C0SARA0001: 'sara' },
  }));
  const home = path.join(installation, '.rbtv', 'agents', 'sara');
  fs.mkdirSync(path.join(home, 'out'), { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ name: 'sara', harness: 'claude', model: 'opus-5-5', effort: 'medium', avatar: ':owl:' }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt\n');
  fs.writeFileSync(path.join(home, 'out', 'P-0003.pdf'), '%PDF-1.4 fake');
  return { root, installation, home, lib, scenario: (change) => {
    const current = JSON.parse(fs.readFileSync(path.join(lib, 'scenario.json'), 'utf8'));
    fs.writeFileSync(path.join(lib, 'scenario.json'), JSON.stringify({ ...current, ...change }));
  }, calls: () => {
    const file = path.join(lib, 'calls.json');
    return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : [];
  } };
}

// Transition B: the owner installs connectors/whatsapp with its messaging adapter.
function installWhatsapp(fx) {
  const lib = path.join(fx.root, 'connectors', 'whatsapp', 'capabilities', 'tools', 'whatsapp', 'lib');
  fs.mkdirSync(lib, { recursive: true });
  fs.writeFileSync(path.join(lib, 'messaging.js'), STUB_ADAPTER);
  fs.writeFileSync(path.join(lib, 'scenario.json'), JSON.stringify({
    account: '5511999990000', direct: '5511912345678@s.whatsapp.net', contact: '^\\d{12,13}$', group: '@g\\.us$',
    addressWhy: 'whatsapp addresses are a number with country code (5511912345678) or a group (...@g.us); ADDRESS is neither',
    ids: ['3EB0FAKE0001'], threads: { '3EB0FAKE0001': [] },
  }));
}

async function run(fx, argv, { home = fx.home, env = {} } = {}) {
  const { main } = require(PROGRAM);
  let out = '';
  let err = '';
  const code = await main(argv, {
    root: fx.root, cwd: fx.installation,
    env: { ...(home ? { RBTV_AGENT_HOME: home } : {}), IGNITE_CONVERSATION: 'T0BJAM8PACU:C0SARA0001:1792160000.000100', ...env },
    stdout: (t) => { out += t; }, stderr: (t) => { err += t; },
  });
  return { code, out, err };
}

function child(argv, cwd) {
  // Outside any installation: the shell's own agent home must not leak in.
  const env = { ...process.env };
  delete env.RBTV_AGENT_HOME;
  const p = spawnSync(process.execPath, [PROGRAM, ...argv], { cwd, encoding: 'utf8', env });
  return { code: p.status, out: p.stdout, err: p.stderr };
}

const lines = (text) => text.replace(/\n$/, '').split('\n');

test('the program exists and shares one send function with Ignite\'s outbox', () => {
  assert.ok(fs.existsSync(PROGRAM), `${PROGRAM} exists`);
  assert.ok(fs.existsSync(SEND), `${SEND} exists`);
  const { sendModule } = require(PROGRAM);
  assert.equal(sendModule, require(SEND));
  assert.equal(typeof sendModule.send, 'function');
});

test('help at every depth and position exits 0 with no setup; the bare root prints help and exits 2', () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'message-empty-'));
  for (const argv of [['-h'], ['--help'], ['--json', '-h'], ['send', '-h'], ['send', '--to', 'U1', '-h'], ['-h', 'send'], ['reply', '--help'], ['history', '-h'], ['send', '--nope', '-h'], ['sned', '-h']]) {
    const r = child(argv, empty);
    assert.equal(r.code, 0, `${argv.join(' ')}: ${r.err}`);
    assert.match(r.out, /^usage: message/);
    assert.equal(r.err, '');
  }
  const root = child(['-h'], empty);
  assert.match(root.out, /^usage: message \[-h\] \[--json\] COMMAND \.\.\.\n/);
  assert.match(root.out, /send {6}a message to an address, as this agent\n/);
  assert.match(root.out, /Connectors: none installed \(rbtv add connectors\/slack\)/);
  assert.match(root.out, /Exit codes: 0 sent or read; 1 refused or failed/);
  for (const line of lines(root.out)) assert.ok(line.length <= 80, `80 columns: ${line}`);
  const send = child(['send', '-h'], empty);
  assert.match(send.out, /^usage: message send \[-h\] \[--json\] --to ADDRESS --via CONNECTOR\n/);
  assert.match(send.out, /--via CONNECTOR {3}the connector that delivers/);
  assert.match(send.out, /Example: message send --to U0OWNER001 --via slack "Receipt saved: P-0003.pdf"/);
  assert.match(child(['reply', '-h'], empty).out, /^usage: message reply \[-h\] \[--json\] --thread REF/);
  assert.match(child(['history', '-h'], empty).out, /^usage: message history \[-h\] \[--json\] --thread REF \[--full\]/);
  const bare = child([], empty);
  assert.equal(bare.code, 2);
  assert.match(bare.out, /^usage: message/);
  const value = child(['send', '--to=-h', '--via', 'slack', 'x'], empty);
  assert.notEqual(value.code, 0, '--to=-h is a value, never help');
  assert.doesNotMatch(value.out, /^usage/);
});

test('the Connectors line of the root help names the installed connectors with an adapter', async () => {
  const fx = fixture();
  const r = await run(fx, ['-h']);
  assert.equal(r.code, 0);
  assert.match(r.out, /Connectors: slack \(installed\)\./);
});

test('S11 invalid words exit 2 with the three lines', async () => {
  const fx = fixture();
  const cases = [
    [['send', '--to', 'U0OWNER001', '--via', 'slack'], 'message: send needs TEXT, --text-file PATH or --file PATH', 'why: nothing to send', 'fix: message send --to U0OWNER001 --via slack "text"   (message send -h)'],
    [['send', '--via', 'slack', 'hi'], 'message: send needs --to ADDRESS', null, null],
    [['send', '--to', '', '--via', 'slack', 'hi'], 'message: --to is empty', null, null],
    [['send', '--to', 'U0OWNER001', '--via', 'slack', '--text-file', path.join(fx.home, 'prompt.md'), 'hi'], 'message: TEXT and --text-file are two texts: give one', null, null],
    [['send', '--to', 'U0OWNER001', '--via', 'slack', '--thread', 'x', 'hi'], 'message: send has no option --thread; a reply is message reply --thread REF', null, null],
    [['sned', 'hi'], 'message: unknown command "sned"; the commands are send, reply, history', null, null],
    [['reply', 'hi'], 'message: reply needs --thread REF', null, null],
    [['history'], 'message: history needs --thread REF', null, null],
    [['send', '--nope', '--to', 'U0OWNER001', '--via', 'slack', 'hi'], 'message: send has no option --nope', null, null],
  ];
  for (const [argv, what, why, fix] of cases) {
    const r = await run(fx, argv);
    assert.equal(r.code, 2, `${argv.join(' ')}: exit ${r.code} ${r.err}`);
    assert.equal(r.out, '', `${argv.join(' ')}: nothing on stdout`);
    const got = lines(r.err);
    assert.equal(got.length, 3, `${argv.join(' ')}: three lines: ${r.err}`);
    assert.equal(got[0], what);
    if (why) assert.equal(got[1], `  ${why}`);
    else assert.match(got[1], /^ {2}why: /);
    if (fix) assert.equal(got[2], `  ${fix}`);
    else assert.match(got[2], /^ {2}fix: /);
  }
  assert.deepEqual(fx.calls(), [], 'no adapter ran');
});

test('S7: --via is always required, refused with the installed connectors listed', async () => {
  const fx = fixture();
  const one = await run(fx, ['send', '--to', 'U0OWNER001', 'Oi']);
  assert.equal(one.code, 1);
  assert.deepEqual(lines(one.err), [
    'message: send refused: --via is required',
    '  why: every send names the connector that delivers; the messaging connectors installed here are: slack',
    '  fix: message send --to U0OWNER001 --via slack TEXT',
  ]);
  installWhatsapp(fx);
  const two = await run(fx, ['send', '--to', 'U0OWNER001', 'Oi']);
  assert.equal(two.code, 1);
  assert.deepEqual(lines(two.err), [
    'message: send refused: --via is required',
    '  why: every send names the connector that delivers; the messaging connectors installed here are: slack, whatsapp',
    '  fix: message send --to U0OWNER001 --via slack TEXT   (or --via whatsapp)',
  ]);
  assert.deepEqual(fx.calls(), []);
});

test('S1 send to the owner: the three lines, the reference, and the adapter called once with a contact', async () => {
  const fx = fixture();
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt saved: P-0003.pdf']);
  assert.equal(r.err, '');
  assert.equal(r.code, 0);
  assert.deepEqual(lines(r.out), [
    'Sent     to U0OWNER001 (direct) via slack, as Sara',
    'Ref      slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100',
    'Reply    message reply --thread slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100 TEXT',
  ]);
  const calls = fx.calls();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].op, 'message.send');
  assert.deepEqual(calls[0].input, { contact: 'U0OWNER001', thread: null, text: 'Receipt saved: P-0003.pdf', as: { name: 'Sara', avatar: ':owl:' }, clientId: calls[0].input.clientId });
  assert.equal(calls[0].input.group, undefined, 'a contact, not a group');
  assert.ok(calls[0].input.clientId, 'a stable client id is passed');
});

test('S1j: one JSON object on stdout', async () => {
  const fx = fixture();
  const r = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt saved: P-0003.pdf']);
  assert.equal(r.code, 0);
  assert.deepEqual(JSON.parse(r.out), {
    connector: 'slack', account: 'T0BJAM8PACU', to: 'U0OWNER001', conversation: 'D0OWNERDM1', thread: null, id: '1792160000.000100',
    ref: 'slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100', as: 'Sara', files: [],
  });
  assert.equal(lines(r.out).length, 1);
});

test('a send to the agent\'s own channel is a group; --json after the verb; no agent home means as null and the owner only', async () => {
  const fx = fixture();
  const r = await run(fx, ['send', '--to', 'C0SARA0001', '--via', 'slack', 'hello', '--json']);
  assert.equal(r.code, 0, r.err);
  const body = JSON.parse(r.out);
  assert.equal(body.conversation, 'C0SARA0001');
  assert.equal(body.to, 'C0SARA0001');
  assert.deepEqual(fx.calls()[0].input.group, 'C0SARA0001');
  const text = await run(fx, ['send', '--to', 'C0SARA0001', '--via', 'slack', 'hello']);
  assert.match(text.out, /^Sent {5}to C0SARA0001 \(group C0SARA0001\) via slack, as Sara\n/);
  const nobody = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', 'hello'], { home: null });
  assert.equal(nobody.code, 0, nobody.err);
  assert.equal(JSON.parse(nobody.out).as, null);
  const refused = await run(fx, ['send', '--to', 'C0SARA0001', '--via', 'slack', 'hello'], { home: null });
  assert.equal(refused.code, 1);
  assert.match(refused.err, /^message: send refused: no permission to message C0SARA0001\n/);
});

test('S9 permission: anyone but the owner and the own channel is refused before any connector runs', async () => {
  const fx = fixture();
  for (const to of ['U0SOMEONE1', 'D0OWNERDM1', 'C0OTHER0001']) {
    const r = await run(fx, ['send', '--to', to, '--via', 'slack', 'Oi']);
    assert.equal(r.code, 1);
    assert.deepEqual(lines(r.err), [
      `message: send refused: no permission to message ${to}`,
      '  why: until the permission ladder exists, this agent may message the owner (U0OWNER001) and its own channel (C0SARA0001) only',
      '  fix: ask the owner; a contact\'s permission is set in /messages once it exists',
    ]);
    assert.equal(r.out, '');
  }
  assert.deepEqual(fx.calls(), []);
});

test('S6: --via names a connector without an adapter, or an unknown name', async () => {
  const fx = fixture();
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'whatsapp', 'Oi']);
  assert.equal(r.code, 1);
  assert.deepEqual(lines(r.err), [
    'message: send refused: whatsapp cannot deliver yet',
    '  why: connectors/whatsapp is installed but has no messaging adapter (capabilities/tools/whatsapp/lib/messaging.js); only slack can send',
    '  fix: message send --to ADDRESS --via slack TEXT, or whatsapp send text (service command) when your prompt allows it',
  ]);
  const unknown = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'signal', 'Oi']);
  assert.equal(unknown.code, 1);
  assert.deepEqual(lines(unknown.err), [
    'message: send refused: no connector named "signal"',
    '  why: the messaging connectors installed here are: slack',
    '  fix: message send --to U0OWNER001 --via slack TEXT',
  ]);
  assert.deepEqual(fx.calls(), []);
});

test('S8: the adapter refuses an address that is not its form; the why line is the adapter\'s sentence', async () => {
  const fx = fixture();
  installWhatsapp(fx);
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'whatsapp', 'Oi']);
  assert.equal(r.code, 1);
  assert.deepEqual(lines(r.err), [
    'message: send refused: whatsapp does not take the address U0OWNER001',
    '  why: whatsapp addresses are a number with country code (5511912345678) or a group (...@g.us); U0OWNER001 is neither',
    '  fix: message send --to U0OWNER001 --via slack TEXT, or an address in whatsapp\'s form',
  ]);
});

test('S5 first use: no messaging connector with an adapter, any verb', async () => {
  const fx = fixture();
  fs.rmSync(path.join(fx.lib, 'messaging.js'));
  for (const argv of [['send', '--to', 'U0OWNER001', '--via', 'slack', 'x'], ['reply', '--thread', 'slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100', 'x'], ['history', '--thread', 'slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100']]) {
    const r = await run(fx, argv);
    assert.equal(r.code, 1, argv.join(' '));
    assert.deepEqual(lines(r.err), [
      'message: no messaging connector is installed',
      '  why: message delivers through a connector that provides message.send and has a messaging adapter; none is installed here',
      '  fix: rbtv add connectors/slack, then message send again',
    ]);
  }
});

test('S2 reply into a thread, text and --json; the adapter is given the thread and no address', async () => {
  const fx = fixture();
  fx.scenario({ ids: ['1792160060.000300'] });
  const ref = 'slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100';
  const r = await run(fx, ['reply', '--thread', ref, 'Done.']);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    `Sent     in thread ${ref} via slack, as Sara`,
    'Ref      slack:T0BJAM8PACU:D0OWNERDM1:1792160060.000300',
  ]);
  const call = fx.calls()[0];
  assert.equal(call.op, 'message.send');
  assert.equal(call.input.group, 'D0OWNERDM1');
  assert.equal(call.input.thread, '1792160000.000100');
  assert.equal(call.input.contact, undefined);
  fx.scenario({ ids: ['1792160060.000300'] });
  const json = await run(fx, ['--json', 'reply', '--thread', ref, 'Done.']);
  assert.deepEqual(JSON.parse(json.out), {
    connector: 'slack', account: 'T0BJAM8PACU', to: null, conversation: 'D0OWNERDM1', thread: '1792160000.000100', id: '1792160060.000300',
    ref: 'slack:T0BJAM8PACU:D0OWNERDM1:1792160060.000300', as: 'Sara', files: [],
  });
});

test('S3 history: the table, the shortened text line, --full blocks, and S3j with the contract\'s events', async () => {
  const fx = fixture();
  const ref = 'slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100';
  const r = await run(fx, ['history', '--thread', ref]);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [
    `Thread ${ref} (3 messages, via slack)`,
    '',
    'when                   from         text',
    // The times are the events' `at` values in UTC (the specification's screen shows other clock times for
    // the same `at`s); the text is cut so the line keeps 80 columns.
    '2026-10-16 14:13:20Z   U0BOTSARA1   Receipt saved: P-0003.pdf',
    '2026-10-16 14:13:50Z   U0OWNER001   Thanks. Was it the full amount? I remembe...',
    '2026-10-16 14:14:20Z   U0BOTSARA1   Done.',
    'Some texts are shortened: message history --thread REF --full shows them whole.',
  ]);
  for (const line of lines(r.out)) assert.ok(line.length <= 80, `80 columns: ${line}`);
  assert.deepEqual(fx.calls()[0].input, { conversation: 'D0OWNERDM1', thread: '1792160000.000100' });
  const full = await run(fx, ['history', '--thread', ref, '--full']);
  assert.equal(full.code, 0);
  assert.match(full.out, /\nid {5}1792160030.000200\nwhen {3}2026-10-16 14:13:50Z\nfrom {3}U0OWNER001\ntext {3}Thanks\. Was it the full amount\? I remember the invoice being R\$ 18,00\.\n/);
  assert.doesNotMatch(full.out, /shortened/);
  const json = await run(fx, ['history', '--thread', ref, '--json']);
  const body = JSON.parse(json.out);
  assert.equal(body.ref, ref);
  assert.equal(body.events.length, 3);
  assert.deepEqual(Object.keys(body.events[1]).sort(), ['account', 'at', 'connector', 'conversation', 'from', 'group', 'id', 'isSelf', 'raw', 'text', 'thread']);
  assert.equal(body.events[1].text, 'Thanks. Was it the full amount? I remember the invoice being R$ 18,00.');
});

test('S3e: a thread the connector returns no events for', async () => {
  const fx = fixture();
  installWhatsapp(fx);
  const ref = 'whatsapp:5511999990000:5511912345678@s.whatsapp.net:3EB0FAKE0001';
  const r = await run(fx, ['history', '--thread', ref]);
  assert.equal(r.code, 0, r.err);
  assert.deepEqual(lines(r.out), [`Thread ${ref} (0 messages, via whatsapp)`, 'No messages: this service keeps no thread for it.']);
  const json = await run(fx, ['--json', 'history', '--thread', ref]);
  assert.deepEqual(JSON.parse(json.out), { ref, events: [] });
});

test('S10: thread not found, a malformed reference, a connector not installed; nothing is sent', async () => {
  const fx = fixture();
  installWhatsapp(fx);
  fx.scenario({ sendError: 'slack answered thread_not_found for 1792000000.000001 in D0OWNERDM1', sendCode: 'thread' });
  const r = await run(fx, ['reply', '--thread', 'slack:T0BJAM8PACU:D0OWNERDM1:1792000000.000001', 'x']);
  assert.equal(r.code, 1);
  assert.equal(r.out, '');
  assert.deepEqual(lines(r.err), [
    'message: reply failed: thread not found',
    '  why: slack answered thread_not_found for 1792000000.000001 in D0OWNERDM1',
    '  fix: message history --thread REF of a reference message send printed; nothing was sent',
  ]);
  const history = await run(fx, ['history', '--thread', 'slack:T0BJAM8PACU:D0OWNERDM1:1792000000.000001']);
  assert.equal(history.code, 1);
  assert.deepEqual(lines(history.err), [
    'message: history failed: thread not found',
    '  why: slack answered thread_not_found for 1792000000.000001 in D0OWNERDM1',
    '  fix: message history --thread REF of a reference message send printed',
  ]);
  const malformed = await run(fx, ['reply', '--thread', 'D0OWNERDM1', 'x']);
  assert.equal(malformed.code, 1);
  assert.deepEqual(lines(malformed.err), [
    'message: reply refused: not a message reference: D0OWNERDM1',
    '  why: a reference reads connector:account:conversation:id, as message send prints it',
    '  fix: copy the Ref line of message send or message history',
  ]);
  const telegram = await run(fx, ['reply', '--thread', 'telegram:acc:conv:1', 'x']);
  assert.equal(telegram.code, 1);
  assert.equal(lines(telegram.err)[0], 'message: reply refused: connector "telegram" is not installed');
  const google = await run(fx, ['history', '--thread', 'google:me@example.com:thr:msg']);
  assert.equal(google.code, 1);
  assert.equal(lines(google.err)[0], 'message: history refused: google cannot deliver yet');
  assert.equal(fx.calls().filter((c) => c.op !== 'message.history').length, 1, 'one send attempt, which the adapter refused');
});

test('S10: a connector error on send is reported once, exit 1, with --json nothing on stdout', async () => {
  const fx = fixture();
  fx.scenario({ sendError: 'slack answered HTTP 503' });
  const r = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', 'x']);
  assert.equal(r.code, 1);
  assert.equal(r.out, '');
  assert.deepEqual(lines(r.err), [
    'message: send failed: slack did not deliver',
    '  why: slack answered HTTP 503',
    '  fix: run the same command again; nothing was sent',
  ]);
  assert.equal(fx.calls().length, 1, 'no retry');
});

test('S4 partial: the text posted and a file refused; stdout keeps what happened, stderr what did not, exit 1', async () => {
  const fx = fixture();
  const file = path.join(fx.home, 'out', 'P-0003.pdf');
  fx.scenario({ ids: ['1792160100.000400'], fileError: 'slack answered file_too_large' });
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt', '--file', file]);
  assert.equal(r.code, 1);
  assert.deepEqual(lines(r.out), [
    'Sent     to U0OWNER001 (direct) via slack, as Sara, 0 of 1 files',
    'Ref      slack:T0BJAM8PACU:D0OWNERDM1:1792160100.000400',
  ]);
  assert.deepEqual(lines(r.err), [
    `message: 1 file was not sent: ${file}`,
    '  why: slack answered file_too_large',
    `  fix: the text is delivered; send the file again with message reply --thread slack:T0BJAM8PACU:D0OWNERDM1:1792160100.000400 --file PATH`,
  ]);
  fx.scenario({ ids: ['1792160100.000400'], fileError: 'slack answered file_too_large' });
  const json = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt', '--file', file]);
  assert.equal(json.code, 1);
  const body = JSON.parse(json.out);
  assert.deepEqual(body.files, [{ path: file, id: null, error: 'slack answered file_too_large' }]);
  assert.equal(body.ref, 'slack:T0BJAM8PACU:D0OWNERDM1:1792160100.000400');
  assert.deepEqual(lines(json.err).length, 3);
});

test('files: uploaded after the text with no caption, in order; a missing path is refused before anything is sent', async () => {
  const fx = fixture();
  const file = path.join(fx.home, 'out', 'P-0003.pdf');
  fx.scenario({ ids: ['1792160000.000100', '1792160000.000101', '1792160000.000102'] });
  const r = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt', '--file', file, '--file', file]);
  assert.equal(r.code, 0, r.err);
  const body = JSON.parse(r.out);
  assert.deepEqual(body.files, [{ path: file, id: '1792160000.000101' }, { path: file, id: '1792160000.000102' }]);
  assert.equal(body.id, '1792160000.000100');
  const calls = fx.calls();
  assert.deepEqual(calls.map((c) => c.op), ['message.send', 'message.file', 'message.file']);
  assert.deepEqual(calls[1].input, { send: { conversation: 'D0OWNERDM1', thread: null, file, as: { name: 'Sara', avatar: ':owl:' } } });
  const missing = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', 'Receipt', '--file', path.join(fx.home, 'missing.pdf')]);
  assert.equal(missing.code, 1);
  assert.match(missing.err, /^message: send refused: no file at .*missing\.pdf\n/);
  assert.equal(fx.calls().length, 3, 'nothing more was sent');
  fx.scenario({ ids: ['1792160000.000200'] });
  const only = await run(fx, ['--json', 'send', '--to', 'U0OWNER001', '--via', 'slack', '--file', file]);
  assert.equal(only.code, 0, only.err);
  assert.equal(JSON.parse(only.out).id, '1792160000.000200');
  assert.deepEqual(fx.calls().slice(3).map((c) => c.op), ['message.file'], 'a files-only send posts no empty text');
});

test('S12: a text over 12,000 characters is sent as a file, exit 0', async () => {
  const fx = fixture();
  const long = 'x'.repeat(14210);
  const textFile = path.join(fx.home, 'out', 'long.md');
  fs.writeFileSync(textFile, long);
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', '--text-file', textFile]);
  assert.equal(r.code, 0, r.err);
  // The specification's S12 screen shows the first two lines; the Reply line of S1 is kept, since a text sent
  // as a file starts a thread like any other message.
  assert.deepEqual(lines(r.out), [
    'Sent     to U0OWNER001 (direct) via slack, as Sara, as a file (text of 14,210 characters, limit 12,000)',
    'Ref      slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100',
    'Reply    message reply --thread slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100 TEXT',
  ]);
  const calls = fx.calls();
  assert.deepEqual(calls.map((c) => c.op), ['message.file']);
  assert.equal(path.basename(calls[0].input.send.file), 'message.md');
  assert.equal(calls[0].input.send.contact, 'U0OWNER001');
});

test('-- ends the options so a text starting with - is sent; --text-file reads the text', async () => {
  const fx = fixture();
  const r = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', '--', '-text']);
  assert.equal(r.code, 0, r.err);
  assert.equal(fx.calls()[0].input.text, '-text');
  const textFile = path.join(fx.home, 'out', 'note.md');
  fs.writeFileSync(textFile, 'from a file with $HOME\n');
  fx.scenario({ ids: ['1792160000.000101'] });
  const file = await run(fx, ['send', '--to', 'U0OWNER001', '--via', 'slack', '--text-file', textFile]);
  assert.equal(file.code, 0, file.err);
  assert.equal(fx.calls()[1].input.text, 'from a file with $HOME\n');
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

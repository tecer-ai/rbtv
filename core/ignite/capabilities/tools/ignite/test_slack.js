'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { Slack, normalize } = require('./slack.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function identity() {
  return { team: 'T1', botUserId: 'UBOT', botId: 'BBOT' };
}

test('normalize-requires-identity', () => {
  assert.throws(
    () => normalize({ user: 'UBOT', bot_id: 'BBOT', text: 'echo', ts: '1' }),
    /botUserId/
  );
  assert.throws(
    () => normalize({ user: 'UBOT', text: 'echo', ts: '1' }, { botUserId: 'UBOT' }),
    /botId/
  );
});

test('normalize-shape', () => {
  const event = normalize({
    type: 'message', channel: 'C1', channel_type: 'channel', ts: '2.2', thread_ts: '1.1',
    user: 'UOWNER', text: 'hi <@UBOT>', files: [{ id: 'F1', name: 'a.mp3', mimetype: 'audio/mpeg' }],
  }, identity());
  assert.deepEqual(event, {
    team: 'T1', channel: 'C1', channelType: 'channel', ts: '2.2', threadTs: '1.1',
    user: 'UOWNER', text: 'hi <@UBOT>',
    files: [{ id: 'F1', name: 'a.mp3', mimetype: 'audio/mpeg', filetype: null }],
    isBotOrSelf: false, mentionsBot: true,
  });
});

test('mentionsBot-code-span', () => {
  const fenced = normalize({ text: '```\n<@UBOT>\n```', user: 'UOWNER', ts: '1' }, identity());
  const inline = normalize({ text: 'see `<@UBOT>` now', user: 'UOWNER', ts: '1' }, identity());
  const real = normalize({ text: '<@UBOT|bot> go', user: 'UOWNER', ts: '1' }, identity());
  assert.equal(fenced.mentionsBot, false);
  assert.equal(inline.mentionsBot, false);
  assert.equal(real.mentionsBot, true);
});

test('isBotOrSelf-bot-user-and-bot-id', () => {
  const byUser = normalize({ user: 'UBOT', text: 'echo', ts: '1' }, identity());
  const byBot = normalize({ user: 'UOTHER', bot_id: 'BBOT', text: 'echo', ts: '1' }, identity());
  const otherApp = normalize({ user: 'UOWNER', bot_id: 'BOTHER', text: 'owner via app', ts: '1' }, identity());
  assert.equal(byUser.isBotOrSelf, true);
  assert.equal(byBot.isBotOrSelf, true);
  assert.equal(otherApp.isBotOrSelf, false);
});

test('isBotOrSelf-edit-delete-join', () => {
  for (const subtype of ['message_changed', 'message_deleted', 'channel_join', 'group_join']) {
    const event = normalize({ subtype, user: 'UOWNER', text: 'x', ts: '1' }, identity());
    assert.equal(event.isBotOrSelf, true, subtype);
  }
  const share = normalize({ subtype: 'file_share', user: 'UOWNER', text: 'x', ts: '1', files: [] }, identity());
  assert.equal(share.isBotOrSelf, false);
});

function harness(routes, { run } = {}) {
  const calls = [];
  const timers = [];
  class FakeWS {
    constructor(url) {
      this.url = url;
      this.closed = false;
      this.sent = [];
      this.listeners = {};
      FakeWS.latest = this;
    }
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() {
      if (this.closed) return;
      this.closed = true;
      for (const fn of this.listeners.close || []) fn();
    }
    emit(data) {
      for (const fn of this.listeners.message || []) fn({ data: JSON.stringify(data) });
    }
  }
  const fetch = async (url, opts) => {
    const method = String(url).split('/').pop();
    const body = !opts.body || typeof opts.body !== 'string'
      ? (opts.body || null)
      : (String(opts.headers['content-type']).includes('json')
        ? JSON.parse(opts.body)
        : Object.fromEntries(new URLSearchParams(opts.body)));
    calls.push({ url: String(url), method, body, headers: opts.headers });
    if (String(url).startsWith('https://upload.test/')) {
      return { ok: true, status: 200, json: async () => ({ ok: true }) };
    }
    const route = routes[method];
    if (!route) return { ok: false, status: 500, json: async () => ({ ok: false, error: 'unrouted' }) };
    const data = typeof route === 'function' ? route(body, calls) : route;
    if (data instanceof Error) throw data;
    if (data.http) return { ok: false, status: data.http, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => data };
  };
  const slack = new Slack({
    botToken: 'xoxb-test',
    appToken: 'xapp-test',
    stoolsWorkspace: 'ignite',
    stools: 'stools',
    fetch,
    WebSocket: FakeWS,
    run: run || (async () => ({ stdout: '' })),
    schedule(fn, ms) {
      const id = timers.length + 1;
      timers.push({ id, fn, ms, cancelled: false });
      return id;
    },
    cancel(id) {
      const timer = timers.find((item) => item.id === id);
      if (timer) timer.cancelled = true;
    },
    log() {},
  });
  return { slack, calls, timers, FakeWS };
}

const authOk = { ok: true, team_id: 'T1', user_id: 'UBOT', bot_id: 'BBOT' };

test('postMessage', async () => {
  const { slack, calls } = harness({ 'chat.postMessage': { ok: true, ts: '9.9', channel: 'C1' } });
  const sent = await slack.postMessage({ channel: 'C1', threadTs: '1.1', text: '*hi*', clientMsgId: 'cid-1' });
  assert.deepEqual(sent, { channel: 'C1', ts: '9.9' });
  assert.equal(calls[0].method, 'chat.postMessage');
  assert.equal(calls[0].body.mrkdwn, 'true');
  assert.equal(calls[0].body.thread_ts, '1.1');
  assert.equal(calls[0].body.client_msg_id, 'cid-1');
  assert.equal(calls[0].body.text, '*hi*');
});

test('addReaction-eyes', async () => {
  const { slack, calls } = harness({ 'reactions.add': { ok: true } });
  await slack.addReaction('C1', '3.3');
  assert.deepEqual(calls[0].body, { channel: 'C1', timestamp: '3.3', name: 'eyes' });
});

test('threadHistory', async () => {
  const { slack, calls } = harness({
    'conversations.replies': (body) => body.cursor
      ? { ok: true, messages: [{ ts: '1.0', user: 'UOWNER', text: 'root' }], response_metadata: {} }
      : { ok: true, messages: [{ ts: '2.0', user: 'UBOT', text: 'later' }], response_metadata: { next_cursor: 'c2' } },
  });
  slack.identity = { team: 'T1', botUserId: 'UBOT', botId: 'BBOT' };
  const rows = await slack.threadHistory('C1', '1.0');
  assert.deepEqual(rows.map((row) => row.ts), ['1.0', '2.0']);
  assert.equal(rows[1].isBotOrSelf, true);
  assert.equal(calls.filter((call) => call.method === 'conversations.replies').length, 2);
});

test('threadHistory-auths-when-identity-missing', async () => {
  const { slack, calls } = harness({
    'auth.test': authOk,
    'conversations.replies': {
      ok: true,
      messages: [
        { ts: '1.0', user: 'UBOT', bot_id: 'BBOT', text: 'echo' },
        { ts: '2.0', user: 'UOWNER', text: '<@UBOT> hi' },
      ],
    },
  });
  const rows = await slack.threadHistory('C1', '1.0');
  assert.equal(calls.some((call) => call.method === 'auth.test'), true);
  assert.equal(rows[0].isBotOrSelf, true);
  assert.equal(rows[1].mentionsBot, true);
});

test('createChannel', async () => {
  const { slack, calls } = harness({ 'conversations.create': { ok: true, channel: { id: 'C9', name: 'probe' } } });
  assert.deepEqual(await slack.createChannel('probe'), { id: 'C9', name: 'probe' });
  assert.equal(calls[0].body.name, 'probe');
});

test('joinChannel', async () => {
  const { slack } = harness({ 'conversations.join': { ok: true, channel: { id: 'C1' } } });
  assert.deepEqual(await slack.joinChannel('C1'), { id: 'C1' });
});

test('joinChannel-already-in', async () => {
  const { slack } = harness({ 'conversations.join': { ok: false, error: 'already_in_channel' } });
  assert.deepEqual(await slack.joinChannel('C1'), { id: 'C1' });
});

test('inviteUser', async () => {
  const { slack, calls } = harness({ 'conversations.invite': { ok: true, channel: { id: 'C1' } } });
  assert.deepEqual(await slack.inviteUser('C1', 'UOWNER'), { id: 'C1' });
  assert.deepEqual(calls[0].body, { channel: 'C1', users: 'UOWNER' });
});

test('inviteUser-already-in', async () => {
  const { slack } = harness({ 'conversations.invite': { ok: false, error: 'already_in_channel' } });
  assert.deepEqual(await slack.inviteUser('C1', 'UOWNER'), { id: 'C1' });
});

test('archiveChannel', async () => {
  const { slack, calls } = harness({ 'conversations.archive': { ok: true } });
  await slack.archiveChannel('C1');
  assert.deepEqual(calls[0].body, { channel: 'C1' });
});

test('archiveChannel-already-archived', async () => {
  const { slack } = harness({ 'conversations.archive': { ok: false, error: 'already_archived' } });
  const result = await slack.archiveChannel('C1');
  assert.equal(result.already_archived, true);
});

test('uploadFile', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'ignite-up-'));
  const file = path.join(dir, 'note.txt');
  await fs.writeFile(file, 'hello');
  const { slack, calls } = harness({
    'files.getUploadURLExternal': { ok: true, upload_url: 'https://upload.test/put', file_id: 'F9' },
    'files.completeUploadExternal': {
      ok: true,
      files: [{ id: 'F9', name: 'note.txt', shares: { public: { C1: [{ ts: '8.8' }] } } }],
    },
  });
  const result = await slack.uploadFile({ channel: 'C1', threadTs: '1.1', file, text: 'note' });
  assert.equal(result.ts, '8.8');
  assert.deepEqual(result.files, [{ id: 'F9', name: 'note.txt' }]);
  const grant = calls.find((call) => call.method === 'files.getUploadURLExternal');
  assert.equal(grant.body.filename, 'note.txt');
  assert.equal(grant.body.length, '5');
  const put = calls.find((call) => call.url === 'https://upload.test/put');
  assert.equal(put.headers['content-type'], 'application/octet-stream');
  const done = calls.find((call) => call.method === 'files.completeUploadExternal');
  assert.equal(done.body.channel_id, 'C1');
  assert.equal(done.body.thread_ts, '1.1');
  assert.equal(done.body.initial_comment, 'note');
  assert.equal(JSON.parse(done.body.files)[0].id, 'F9');
});

test('downloadFile', async () => {
  const argv = [];
  const { slack } = harness({}, {
    run: async (cmd, args) => {
      argv.push([cmd, ...args]);
      return { stdout: '[1/1] voice note.mp3  (1.0 KB)\n' };
    },
  });
  const files = await slack.downloadFile({ channel: 'C1', ts: '4.4', threadTs: '1.1', dir: path.join(os.tmpdir(), 'ignite-dl') });
  assert.equal(argv[0][0], 'stools', 'the stools command runs directly, never through python3');
  assert.equal(argv[0][1], 'download');
  assert.deepEqual(argv[0].slice(2, 8), ['--channel', 'C1', '--ts', '4.4', '--thread-ts', '1.1']);
  assert.equal(argv[0][8], '--output');
  assert.equal(argv[0].at(-2), '--installation');
  assert.equal(argv[0].at(-1), 'ignite');
  assert.equal(argv[0].at(-1).includes('/'), false);
  assert.equal(files[0].name, 'voice note.mp3');
  assert.equal(path.basename(files[0].path), 'voice note.mp3');
});

test('download-refuses-vault-path', async () => {
  const slack = new Slack({
    botToken: 'xoxb-test',
    stoolsWorkspace: '/tmp/vault',
    stools: 'stools',
    run: async () => { throw new Error('stools must not be called'); },
  });
  await assert.rejects(
    () => slack.downloadFile({ channel: 'C1', ts: '1.1', dir: os.tmpdir() }),
    /not a path/,
  );
});

test('canvasCreate', async () => {
  const { slack, calls } = harness({ 'conversations.canvases.create': { ok: true, canvas_id: 'Fcanvas' } });
  const created = await slack.canvasCreate({ channel: 'C1', markdown: '# t', title: 'T' });
  assert.deepEqual(created, { canvasId: 'Fcanvas' });
  assert.equal(calls[0].body.channel_id, 'C1');
  assert.equal(JSON.parse(calls[0].body.document_content).markdown, '# t');
  assert.equal(calls[0].headers.authorization, 'Bearer xoxb-test');
});

test('canvasEdit', async () => {
  const { slack, calls } = harness({ 'canvases.edit': { ok: true } });
  const edited = await slack.canvasEdit({ canvasId: 'Fcanvas', markdown: 'body', operation: 'insert_at_end' });
  assert.deepEqual(edited, { canvasId: 'Fcanvas' });
  assert.equal(JSON.parse(calls[0].body.changes)[0].operation, 'insert_at_end');
  assert.equal(calls[0].headers.authorization, 'Bearer xoxb-test');
});

test('socket-ack-after-onEvent', async () => {
  const { slack, FakeWS } = harness({
    'auth.test': authOk,
    'apps.connections.open': { ok: true, url: 'wss://example.test/socket' },
  });
  let during = null;
  await slack.connect(async (event) => {
    during = FakeWS.latest.sent.length;
    assert.equal(event.mentionsBot, true);
    assert.equal(event.team, 'T1');
  });
  FakeWS.latest.emit({
    type: 'events_api', envelope_id: 'env-1',
    payload: { event: { type: 'message', channel: 'C1', ts: '5.5', user: 'UOWNER', text: '<@UBOT>' } },
  });
  await slack.pending;
  assert.equal(during, 0);
  assert.deepEqual(FakeWS.latest.sent, [{ envelope_id: 'env-1' }]);
});

test('socket-no-ack-on-onEvent-failure', async () => {
  const { slack, FakeWS } = harness({
    'auth.test': authOk,
    'apps.connections.open': { ok: true, url: 'wss://example.test/socket' },
  });
  await slack.connect(async () => { throw new Error('store down'); });
  FakeWS.latest.emit({
    type: 'events_api', envelope_id: 'env-2',
    payload: { event: { type: 'message', channel: 'C1', ts: '5.5', user: 'UOWNER', text: 'hi' } },
  });
  await slack.pending;
  assert.deepEqual(FakeWS.latest.sent, []);
});

test('socket-disconnect-envelope', async () => {
  let opens = 0;
  const { slack, FakeWS, timers } = harness({
    'auth.test': authOk,
    'apps.connections.open': () => {
      opens += 1;
      return { ok: true, url: `wss://example.test/${opens}` };
    },
  });
  await slack.connect(async () => {});
  const first = FakeWS.latest;
  first.emit({ type: 'disconnect', reason: 'refresh_requested' });
  await slack.pending;
  assert.equal(first.closed, true);
  assert.equal(timers.length, 1);
  assert.equal(timers[0].ms, 1000);
  timers[0].fn();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(opens, 2);
  assert.notEqual(FakeWS.latest, first);
});

test('socket-reconnect-backoff', async () => {
  let opens = 0;
  const { slack, FakeWS, timers } = harness({
    'auth.test': authOk,
    'apps.connections.open': () => {
      opens += 1;
      if (opens > 1) return { ok: false, error: 'socket_down' };
      return { ok: true, url: 'wss://example.test/1' };
    },
  });
  await slack.connect(async () => {});
  FakeWS.latest.close();
  assert.equal(timers[0].ms, 1000);
  timers[0].fn();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(timers[1].ms, 2000);
  assert.equal(timers[1].cancelled, false);
});

test('socket-flap-backs-off-until-hello', async () => {
  let opens = 0;
  const { slack, FakeWS, timers } = harness({
    'auth.test': authOk,
    'apps.connections.open': () => {
      opens += 1;
      return { ok: true, url: `wss://example.test/${opens}` };
    },
  });
  await slack.connect(async () => {});
  FakeWS.latest.close();
  assert.equal(timers[0].ms, 1000);
  timers[0].fn();
  await new Promise((resolve) => setImmediate(resolve));
  FakeWS.latest.close();
  assert.equal(timers[1].ms, 2000);
});

test('socket-stop-cancels-reconnect', async () => {
  const { slack, FakeWS, timers } = harness({
    'auth.test': authOk,
    'apps.connections.open': { ok: true, url: 'wss://example.test/1' },
  });
  await slack.connect(async () => {});
  slack.stop();
  assert.equal(FakeWS.latest.closed, true);
  assert.equal(timers.length, 0);
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
  process.stdout.write(`slack: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();

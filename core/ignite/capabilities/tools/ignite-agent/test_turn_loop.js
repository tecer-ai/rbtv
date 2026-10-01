#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { Store } = require('./store.js');
const { main } = require('./cli.js');
const { runOnce } = require('./turn-loop.js');
const { deliverPending } = require('./outbox.js');
const { historyPath, writeHistory } = require('./history.js');
const { EMPTY_BOARD, boardPath, parseBoard } = require('./board.js');
const TEST_BOARD = EMPTY_BOARD.replace('## What matters now\n', '## What matters now\n\n### BOARD_TOKEN\nReady.\n- Threads: none\n- Detail: none\n- Flags: none\n');

const failures = [];
const pending = [];
const stubPath = path.join(os.tmpdir(), `ignite-fake-cast-${process.pid}.js`);

function test(name, fn) {
  pending.push([name, fn]);
}

const STUB = `#!/usr/bin/env node
'use strict';
const fs = require('fs');
const args = process.argv;
const request = JSON.parse(fs.readFileSync(args[args.indexOf('--request') + 1], 'utf8'));
const resultFile = args[args.indexOf('--result') + 1];
const control = JSON.parse(fs.readFileSync(process.env.FAKE_CAST_CONTROL, 'utf8'));
fs.appendFileSync(process.env.FAKE_CAST_SEEN, JSON.stringify({
  harness: request.harness, model: request.model, effort: request.effort,
  cwd: request.cwd, session: request.session, prompt: request.prompt, env: request.env,
  systemPromptFile: request.systemPromptFile,
}) + '\\n');
const prompt = request.prompt || '';
const resultLine = prompt.split('\\n').find((line) => line.startsWith('RESULT_FILE: '));
const agentFile = resultLine ? resultLine.slice('RESULT_FILE: '.length) : null;
if (agentFile && typeof control.rawAgent === 'string') fs.writeFileSync(agentFile, control.rawAgent);
else if (agentFile && control.agent) {
  const nonce = prompt.split('\\n').find((line) => line.startsWith('NONCE: ')).slice('NONCE: '.length);
  fs.writeFileSync(agentFile, JSON.stringify({ ...control.agent, nonce }));
}
if (control.writeLauncher !== false) {
  const stderrPath = resultFile + '.stderr';
  const stdoutPath = resultFile + '.stdout';
  fs.writeFileSync(stdoutPath, control.stdout || 'HARNESS_STDOUT_SECRET');
  if (control.stderr) fs.writeFileSync(stderrPath, control.stderr);
  const started = control.childStarted !== false;
  const launcher = {
    ok: control.ok !== false,
    harness: request.harness,
    model: request.model,
    effort: request.effort,
    sessionId: control.sessionId === undefined ? 'ses-test' : control.sessionId,
    exitCode: control.childExit ?? 0,
    pid: started ? process.pid : null,
    pidStart: started ? '1' : null,
    stdoutPath: started ? stdoutPath : null,
    stderrPath: control.stderr ? stderrPath : null,
  };
  if (launcher.ok === false && !launcher.error) launcher.error = control.error || 'harness_exit_1';
  if (control.error) launcher.error = control.error;
  fs.writeFileSync(resultFile, JSON.stringify(launcher));
}
process.exit(control.exitCode ?? 0);
`;

function agentOf(disposition, extra = {}) {
  return {
    disposition,
    summary: 'sum',
    nextStep: disposition === 'continue' ? 'do next' : null,
    workers: [],
    outputs: [],
    replies: [{ text: `reply-${disposition}`, audio: false, files: [] }],
    ...extra,
  };
}

function fakeSlack() {
  const slack = {
    posts: [],
    uploads: [],
    reactions: [],
    failPosts: 0,
    reactionError: null,
    downloads: [],
    async postMessage(args) {
      slack.posts.push(args);
      if (slack.failPosts > 0) {
        slack.failPosts -= 1;
        throw new Error('slack down');
      }
      return { channel: args.channel, ts: `9.${slack.posts.length}` };
    },
    async uploadFile(args) {
      slack.uploads.push(args);
      return { ts: '8.1', files: [args.file] };
    },
    async addReaction(channel, ts) {
      if (slack.reactionError) throw new Error(slack.reactionError);
      slack.reactions.push({ channel, ts });
    },
    async downloadFile() {
      return slack.downloads;
    },
  };
  return slack;
}

function fakeAudio() {
  const audio = {
    calls: [],
    fail: false,
    async transcribe() {
      if (audio.fail) throw new Error(audio.error || 'no transcript');
      return { text: 'heard words' };
    },
    async speak(text, opts) {
      audio.calls.push({ text, opts });
      return '/tmp/spoken.mp3';
    },
  };
  return audio;
}

function harness(ctx, setting = {}) {
  const home = path.join(ctx.dir, '.rbtv', 'agents', 'master');
  fs.mkdirSync(home, { recursive: true });
  const launch = { harness: 'claude', model: 'sonnet-5', effort: 'low', voice: 'voice-a', ...setting };
  fs.writeFileSync(path.join(home, 'launch.json'), `${JSON.stringify(launch)}\n`);
  fs.writeFileSync(path.join(home, 'board.md'), TEST_BOARD, 'utf8');
  fs.mkdirSync(path.join(home, 'memory'));
  fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — master\n', 'utf8');
  const memory = path.join(ctx.dir, '.rbtv', 'memory');
  fs.mkdirSync(path.join(memory, '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(memory, 'profile.md'), '# Profile — Sam\n\n## Who\n- PROFILE_TOKEN. (2026-10-01 · source.md)\n\n## Working with Sam\n\n## Now\n', 'utf8');
  fs.writeFileSync(path.join(memory, 'inbox.md'), '# Inbox — waiting to be filed\n- INBOX_TOKEN. (2026-10-01 · master)\n', 'utf8');
  fs.writeFileSync(path.join(memory, '_artifacts', 'index.md'), '# Memory index\n| Open | When |\n|---|---|\n| [../knowledge/](../knowledge/) | WHEN needed. |\n', 'utf8');
  const store = ctx.track(new Store(path.join(home, 'state.sqlite')));
  store.setLaunchSetting(launch);
  const controlPath = path.join(ctx.dir, 'control.json');
  const seenPath = path.join(ctx.dir, 'seen.jsonl');
  fs.writeFileSync(seenPath, '');
  const writeControl = (control) => fs.writeFileSync(controlPath, JSON.stringify(control));
  writeControl({ agent: agentOf('completed'), sessionId: 'ses-keep' });
  const slack = fakeSlack();
  const audio = fakeAudio();
  let now = Date.now();
  const box = {
    home,
    store,
    slack,
    audio,
    logs: [],
    seenPath,
    writeControl,
    launch,
    now: () => now,
    setNow(n) { now = n; },
    sync() { now = Date.now() + 1000; },
    deps: {
      home,
      store,
      slack,
      audio,
      castCmd: stubPath,
      castEnv: { FAKE_CAST_CONTROL: controlPath, FAKE_CAST_SEEN: seenPath },
      now: () => now,
      log(fields) { box.logs.push(fields); },
    },
  };
  return box;
}

function seen(box) {
  const text = fs.readFileSync(box.seenPath, 'utf8').trim();
  if (!text) return [];
  return text.split('\n').map((line) => JSON.parse(line));
}

function seed(store, { key = 'T1:C1:1.1', id = '1.1', text = 'hello', files = [], createdAt = 10 } = {}) {
  const [team, channel, rootTs] = key.split(':');
  return store.acceptOwnerInput({
    key, agent: 'master', workspace: team, channel, rootTs, activated: true,
    message: { id, role: 'owner', text, team, channel, ts: id, files, createdAt },
    payload: { text, files, ts: id, threadTs: rootTs },
  });
}

function pendingKinds(store) {
  return store.db.prepare("SELECT kind FROM queue WHERE state='pending' ORDER BY priority, id").all().map((row) => row.kind);
}

async function exhaust(box) {
  box.writeControl({
    ok: false,
    exitCode: 1,
    childExit: 1,
    error: 'session_identity_missing',
    stderr: 'boom-model: refused',
  });
  box.sync();
  const first = await runOnce('master', box.deps);
  assert.equal(first.failure.held, false);
  box.setNow(box.now() + 5000);
  const second = await runOnce('master', box.deps);
  assert.equal(second.failure.held, false);
  box.setNow(box.now() + 30000);
  const third = await runOnce('master', box.deps);
  assert.equal(third.failure.held, true);
  return third;
}

for (const disposition of ['completed', 'continue', 'waiting_owner', 'waiting_workers', 'stopped']) {
  test(`disposition ${disposition}`, async (ctx) => {
    const box = harness(ctx);
    if (disposition === 'completed') box.slack.reactionError = 'reaction down';
    seed(box.store, { text: `ask-${disposition}` });
    box.writeControl({ agent: agentOf(disposition), sessionId: 'ses-keep', stdout: 'HARNESS_STDOUT_SECRET' });
    box.sync();
    const result = await runOnce('master', box.deps);
    assert.equal(result.disposition, disposition);
    assert.equal(result.work.state, disposition);
    assert.equal(seen(box).length, 1);
    assert.equal(seen(box)[0].session.mode, 'new');
    assert.equal(seen(box)[0].effort, 'low');
    assert.match(result.prompt, /BOARD_TOKEN/);
    assert.match(result.prompt, new RegExp(`ask-${disposition}`));
    const outbox = box.store.pendingOutbox();
    assert.equal(outbox.length, 1);
    assert.equal(outbox[0].payload.text, `reply-${disposition}`);
    assert.equal(JSON.stringify(outbox).includes('HARNESS_STDOUT_SECRET'), false);
    const history = fs.readFileSync(historyPath(box.home, 'T1:C1:1.1'), 'utf8');
    assert.equal(history.includes('HARNESS_STDOUT_SECRET'), false);
    const kinds = pendingKinds(box.store);
    if (disposition === 'continue') assert.deepEqual(kinds, ['continue']);
    else assert.deepEqual(kinds, []);
    if (disposition === 'completed') assert.equal(box.slack.reactions.length, 0);
    else assert.equal(box.slack.reactions.length, 1);
  });
}

test('3 failures → hold + one blocker', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  const third = await exhaust(box);
  assert.equal(third.failure.scope, 'work');
  assert.equal(box.store.agentHold(), null);
  assert.equal(box.store.getWork(third.failure.workId || box.store.listWork()[0].id).state, 'held');
  const outbox = box.store.pendingOutbox(box.now() + 1);
  assert.equal(outbox.length, 1);
  assert.match(outbox[0].payload.text, /boom-model: refused/);
  assert.match(outbox[0].payload.text, /ignite-agent work retry/);
  assert.equal(seen(box).length, 3);
  box.setNow(box.now() + 60_000);
  const again = await runOnce('master', box.deps);
  assert.equal(again.claimed, false);
  assert.equal(seen(box).length, 3);
});

test('a wake after a hold does not relaunch', async (ctx) => {
  const box = harness(ctx);
  const seeded = seed(box.store);
  await exhaust(box);
  const wake = box.store.wake({ workId: seeded.workId });
  assert.equal(wake.inserted, false);
  box.setNow(box.now() + 60_000);
  const result = await runOnce('master', box.deps);
  assert.equal(result.claimed, false);
  assert.equal(seen(box).length, 3);
});

test('owner retry clears it', async (ctx) => {
  const box = harness(ctx);
  const seeded = seed(box.store);
  await exhaust(box);
  assert.equal(box.store.clearHold({ workId: seeded.workId }), true);
  box.writeControl({ agent: agentOf('completed'), sessionId: 'ses-keep' });
  box.setNow(box.now() + 1000);
  const result = await runOnce('master', box.deps);
  assert.equal(result.disposition, 'completed');
  assert.equal(result.work.state, 'completed');
  assert.equal(seen(box).length, 4);
});

test('request carries systemPromptFile', async (ctx) => {
  const box = harness(ctx);
  const home = fs.realpathSync(box.home);
  const agentMd = path.join(home, 'agent.md');
  fs.writeFileSync(agentMd, 'STANDING_SECRET\n');
  assert.equal(fs.existsSync(path.join(box.home, 'CLAUDE.md')), false);
  seed(box.store, { text: 'hello' });
  box.sync();
  const result = await runOnce('master', box.deps);
  const request = JSON.parse(fs.readFileSync(path.join(home, 'turns', result.runId, 'request.json'), 'utf8'));
  assert.equal(request.systemPromptFile, agentMd);
  assert.equal(path.isAbsolute(request.systemPromptFile), true);
  assert.equal(request.prompt.includes('STANDING_SECRET'), false);
  assert.equal(fs.existsSync(path.join(box.home, 'CLAUDE.md')), false);
});

test('live-PID refusal', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.sync();
  const claim = box.store.claimNext(box.now());
  const child = ctx.trackPid(spawn('sleep', ['60']));
  const stat = fs.readFileSync(`/proc/${child.pid}/stat`, 'utf8');
  const pidStart = stat.slice(stat.lastIndexOf(')') + 1).trim().split(/\s+/)[19];
  box.store.attachProcess(claim.runId, { pid: child.pid, pidStart, setting: box.store.getLaunchSetting() });
  const result = await runOnce('master', box.deps);
  assert.equal(result.refused, 'live');
  assert.equal(seen(box).length, 0);
  assert.equal(box.store.getActiveRun().id, claim.runId);
});

test('restart recovery from a DB with a pending queue and an unfinished work item', async (ctx) => {
  const box = harness(ctx);
  const db = path.join(box.home, 'state.sqlite');
  const seeded = seed(box.store, { text: 'still open' });
  assert.equal(box.store.getWork(seeded.workId).state, 'open');
  box.store.close();
  box.store = ctx.track(new Store(db));
  box.deps.store = box.store;
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.equal(result.disposition, 'completed');
  assert.equal(result.work.state, 'completed');
  assert.equal(box.store.getWork(seeded.workId).state, 'completed');
  assert.equal(seen(box).length, 1);

  const again = seed(box.store, { id: '4.4', text: 'crashed', createdAt: 40 });
  const claim = box.store.claimNext(Date.now() + 1000);
  assert.equal(claim.work_id, again.workId);
  assert.equal(box.store.getActiveRun().pid, null);
  box.store.close();
  box.store = ctx.track(new Store(db));
  box.deps.store = box.store;
  box.sync();
  const recovered = await runOnce('master', box.deps);
  assert.equal(recovered.claimed, false);
  assert.equal(recovered.recovered.failure.held, false);
  assert.equal(box.store.getWork(again.workId).state, 'open');
  assert.equal(seen(box).length, 1);
  box.setNow(box.now() + 5000);
  const retried = await runOnce('master', box.deps);
  assert.equal(retried.disposition, 'completed');
  assert.equal(seen(box).length, 2);
});

test('settings changed between turns → next run snapshots the new setting', async (ctx) => {
  const box = harness(ctx);
  seed(box.store, { text: 'first' });
  box.sync();
  const first = await runOnce('master', box.deps);
  assert.equal(first.snapshot.effort, 'low');
  assert.equal(first.snapshot.harness, 'claude');
  assert.equal(first.session.mode, 'new');
  const saved = JSON.parse(box.store.db.prepare('SELECT launch_snapshot FROM runs WHERE id=?').get(first.runId).launch_snapshot);
  assert.equal(saved.effort, 'low');
  const next = { harness: 'claude', model: 'sonnet-5', effort: 'high', voice: 'voice-a' };
  fs.writeFileSync(path.join(box.home, 'launch.json'), `${JSON.stringify(next)}\n`);
  seed(box.store, { id: '3.3', text: 'second', createdAt: 30 });
  box.sync();
  const second = await runOnce('master', box.deps);
  assert.equal(second.snapshot.effort, 'high');
  assert.equal(second.session.mode, 'resume');
  assert.equal(second.session.id, 'ses-keep');
  assert.equal(seen(box)[1].effort, 'high');
  assert.equal(seen(box)[1].session.id, 'ses-keep');
  const still = JSON.parse(box.store.db.prepare('SELECT launch_snapshot FROM runs WHERE id=?').get(first.runId).launch_snapshot);
  assert.equal(still.effort, 'low');
});

test('harness change → new session with re-hydrated prompt', async (ctx) => {
  const box = harness(ctx);
  seed(box.store, { text: 'TRIGGER', createdAt: 100 });
  box.store.recordMessage('T1:C1:1.1', { id: 'old', role: 'owner', text: 'OLD_MSG', createdAt: 1 });
  box.store.recordMessage('T1:C1:1.1', { id: 'mid', role: 'owner', text: 'MID_MSG', createdAt: 2 });
  box.store.setSession('T1:C1:1.1', 'claude', 'claude-session-1');
  box.store.db.prepare('UPDATE work SET summary=? WHERE conversation_key=?').run('WORKSUM', 'T1:C1:1.1');
  fs.writeFileSync(path.join(box.home, 'launch.json'), `${JSON.stringify({
    harness: 'opencode', model: 'glm-5.3', effort: 'high', voice: 'voice-a',
  })}\n`);
  box.deps.historyWindow = 1;
  box.writeControl({ agent: agentOf('completed'), sessionId: 'ses-migrated' });
  box.sync();
  const result = await runOnce('master', box.deps);
  const request = seen(box)[0];
  assert.equal(request.session.mode, 'new');
  assert.equal(request.session.id, undefined);
  assert.equal(request.harness, 'opencode');
  assert.equal(request.prompt.includes('claude-session-1'), false);
  assert.match(request.prompt, /OLD_MSG/);
  assert.match(request.prompt, /WORKSUM/);
  assert.match(request.prompt, /Stored thread context/);
  assert.equal(result.snapshot.harness, 'opencode');
  seed(box.store, { id: '5.5', text: 'AFTER', createdAt: 500 });
  box.sync();
  await runOnce('master', box.deps);
  const resumed = seen(box)[1];
  assert.equal(resumed.session.mode, 'resume');
  assert.equal(resumed.session.id, 'ses-migrated');
  assert.equal(resumed.prompt.includes('OLD_MSG'), false);
  assert.equal(resumed.prompt.includes('Stored thread context'), false);
});

test('successive schedule turns start new sessions with only the schedule id as input', async (ctx) => {
  const box = harness(ctx);
  const key = 'T1:C1:1.1';
  box.store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  box.store.recordMessage(key, { id: 'old', role: 'owner', text: 'OLD_THREAD_CONTEXT' });
  box.store.setSession(key, 'claude', 'old-session');
  const keys = new Set([key]);
  for (const id of ['wake-1', 'wake-2']) {
    box.store.enqueueScheduleWake({ id, conversationKey: key, scheduleId: 'check-inbox' });
    // Even a legacy payload carrying details must expose only the schedule id as input.
    box.store.db.prepare('UPDATE queue SET payload=? WHERE id=?').run(JSON.stringify({
      scheduleId: 'check-inbox', note: 'OLD_SCHEDULE_NOTE', report: 'always', cadence: 'every:1h',
    }), id);
    box.sync();
    const result = await runOnce('master', box.deps);
    assert.equal(result.failed, undefined);
    const request = seen(box).at(-1);
    assert.deepEqual(request.session, { mode: 'new' });
    const freshKey = request.env.IGNITE_CONVERSATION;
    assert.equal(keys.has(freshKey), false);
    keys.add(freshKey);
    assert.equal(box.store.getConversation(freshKey).root_ts, null);
    assert.equal(request.prompt.split('Triggering input:\n')[1].split('\nRecent messages')[0], '[schedule] check-inbox');
    assert.doesNotMatch(request.prompt, /OLD_THREAD_CONTEXT|OLD_SCHEDULE_NOTE|old-session|every:1h/);
    const [delivered] = await deliverPending(box.store, { slack: box.slack });
    assert.equal(delivered.delivered, true);
    assert.equal(box.slack.posts.at(-1).threadTs, undefined);
    assert.equal(box.store.getConversation(delivered.conversationKey).root_ts, delivered.ts);
  }
  assert.equal(box.store.getSession(key, 'claude'), 'old-session');
});

test('two replies from one schedule wake deliver in the same thread in one drain', async (ctx) => {
  const box = harness(ctx);
  const key = 'T1:C1:board';
  box.store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: 'board' });
  const schedule = box.store.upsertSchedule({
    id: 'check-inbox', conversationKey: key, cadence: 'every:1h', timezone: 'UTC',
  });
  box.store.enqueueScheduleWake({ id: 'wake-1', conversationKey: key, scheduleId: schedule.id });
  box.writeControl({ agent: agentOf('completed', {
    replies: [{ text: 'first reply' }, { text: 'second reply' }],
  }) });
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.equal(result.disposition, 'completed');
  const freshKey = seen(box)[0].env.IGNITE_CONVERSATION;
  assert.equal(box.store.getConversation(freshKey).root_ts, null);
  const rows = box.store.pendingOutbox();
  assert.equal(rows.length, 2);
  assert.ok(rows.every((row) => row.conversation_key === freshKey));

  const delivered = await deliverPending(box.store, { slack: box.slack });
  assert.deepEqual(delivered.map((row) => row.delivered), [true, true]);
  assert.deepEqual(box.slack.posts.map((post) => post.text), ['first reply', 'second reply']);
  assert.equal(box.slack.posts[0].threadTs, undefined);
  assert.equal(box.slack.posts[1].threadTs, delivered[0].ts);
  assert.equal(delivered[1].conversationKey, delivered[0].conversationKey);
  assert.equal(box.store.getConversation(freshKey), null);
  for (const row of rows) {
    const saved = box.store.db.prepare('SELECT * FROM outbox WHERE id=?').get(row.id);
    assert.equal(saved.state, 'delivered');
    assert.equal(saved.last_error, null);
    assert.equal(saved.conversation_key, delivered[0].conversationKey);
  }
  assert.deepEqual(box.store.pendingOutbox(), []);
  assert.deepEqual(box.store.getSchedule(schedule.id), schedule);
});

test('post --thread delivers into the target and joins its next turn history', async (ctx) => {
  const box = harness(ctx);
  const workspace = path.join(ctx.dir, 'workspace');
  const configDir = path.join(workspace, '.rbtv', 'config', 'ignite');
  fs.mkdirSync(configDir, { recursive: true });
  fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify({
    slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER',
      appTokenEnv: 'SLACK_APP_TOKEN', botTokenEnv: 'SLACK_BOT_TOKEN', ownerTokenEnv: 'SLACK_OWNER_TOKEN',
      stoolsWorkspace: 'ignite' },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' }, dmAgent: 'master', routes: { C1: 'master' },
  }), 'utf8');
  const key = 'T1:C1:1.1';
  box.store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  box.store.recordMessage(key, { id: 'before', role: 'owner', text: 'EARLIER_THREAD_CONTEXT' });
  box.store.setSession(key, 'claude', 'thread-session');
  box.store.upsertConversation({ key: 'schedule:current', agent: 'master', workspace: 'T1', channel: 'C1' });
  const code = main(['--agent', 'master', '--workspace', workspace, 'post', '--thread', key, '--text', 'CHECK_RESULT'], {
    env: { IGNITE_AGENT_HOME: box.home, IGNITE_CONVERSATION: 'schedule:current' }, stdout() {},
  });
  assert.equal(code, 0);
  const [delivered] = await deliverPending(box.store, { slack: box.slack });
  assert.equal(delivered.delivered, true);
  assert.equal(delivered.conversationKey, key);
  assert.equal(box.slack.posts[0].threadTs, '1.1');
  assert.equal(box.slack.posts[0].text, 'CHECK_RESULT');
  assert.deepEqual(box.store.listHistory('schedule:current'), []);
  seed(box.store, { id: '10.1', text: 'FOLLOW_UP', createdAt: Date.now() });
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.deepEqual(result.session, { mode: 'resume', id: 'thread-session' });
  assert.match(result.prompt, /EARLIER_THREAD_CONTEXT/);
  assert.match(result.prompt, /CHECK_RESULT/);
  assert.match(result.prompt, /FOLLOW_UP/);
  assert.match(fs.readFileSync(historyPath(box.home, key), 'utf8'), /CHECK_RESULT/);
});

test('queued owner input runs before a continue', async (ctx) => {
  const box = harness(ctx);
  seed(box.store, { text: 'start' });
  box.writeControl({ agent: agentOf('continue'), sessionId: 'ses-keep' });
  box.sync();
  const first = await runOnce('master', box.deps);
  assert.equal(first.disposition, 'continue');
  seed(box.store, { id: '7.7', text: 'OWNER_FIRST', createdAt: 70 });
  box.writeControl({ agent: agentOf('completed'), sessionId: 'ses-keep' });
  box.sync();
  const second = await runOnce('master', box.deps);
  assert.equal(second.kind, 'owner');
  assert.match(second.prompt, /OWNER_FIRST/);
  assert.equal(pendingKinds(box.store).includes('continue'), true);
});

test('two conversations never share history in a prompt', async (ctx) => {
  const box = harness(ctx);
  seed(box.store, { key: 'T1:C1:1.1', id: '1.1', text: 'MINE_TOKEN' });
  seed(box.store, { key: 'T1:C2:2.2', id: '2.2', text: 'FOREIGN_TOKEN', createdAt: 20 });
  box.store.db.prepare('UPDATE work SET summary=? WHERE conversation_key=?').run('FOREIGN_WORK', 'T1:C2:2.2');
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.match(result.prompt, /MINE_TOKEN/);
  assert.equal(result.prompt.includes('FOREIGN_TOKEN'), false);
  assert.equal(result.prompt.includes('FOREIGN_WORK'), false);
  const file = fs.readFileSync(historyPath(box.home, 'T1:C1:1.1'), 'utf8');
  assert.equal(file.includes('FOREIGN_TOKEN'), false);
  assert.equal(fs.existsSync(historyPath(box.home, 'T1:C2:2.2')), false);
});

test('outbox never double-posts when delivery is retried', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'r1', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-1',
    payload: { text: 'hello-reply', audio: false, files: [] },
  });
  let t = Date.now();
  const deps = { slack: box.slack, audio: box.audio, home: box.home, now: () => t };
  await deliverPending(box.store, deps);
  await deliverPending(box.store, deps);
  assert.equal(box.slack.posts.length, 1);
  assert.equal(box.slack.posts[0].clientMsgId, 'cid-1');
  assert.equal(box.slack.posts[0].threadTs, '1.1');
  assert.equal(box.slack.posts[0].text.includes('HARNESS_STDOUT_SECRET'), false);
  const saved = box.store.db.prepare('SELECT state, ts FROM outbox WHERE id=?').get('r1');
  assert.equal(saved.state, 'delivered');
  assert.ok(saved.ts);

  box.store.enqueueOutbox({
    id: 'r2', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-2',
    payload: { text: 'again', audio: false, files: ['/tmp/note.txt'] },
  });
  box.slack.failPosts = 1;
  const failed = await deliverPending(box.store, deps);
  assert.equal(failed[0].delivered, false);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('r2').state, 'pending');
  t += 6000;
  const before = box.slack.posts.filter((post) => post.clientMsgId === 'cid-2').length;
  await deliverPending(box.store, deps);
  const after = box.slack.posts.filter((post) => post.clientMsgId === 'cid-2').length;
  assert.equal(after, before + 1);
  await deliverPending(box.store, deps);
  assert.equal(box.slack.posts.filter((post) => post.clientMsgId === 'cid-2').length, after);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('r2').state, 'delivered');

  const proactive = box.store.beginProactive({
    id: 'p1', agent: 'master', workspace: 'T1', channel: 'UOWNER',
    payload: { text: 'dm hello', audio: false, files: [], imUser: 'UOWNER' },
  });
  t += 1000;
  await deliverPending(box.store, deps);
  const dm = box.slack.posts.find((post) => post.channel === 'UOWNER');
  assert.ok(dm);
  assert.equal(dm.threadTs, undefined);
  assert.equal(box.store.getConversation(proactive.conversationKey), null);

  box.store.enqueueOutbox({
    id: 'r3', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-3',
    payload: { text: 'speak this', audio: true, files: [] },
  });
  t += 1000;
  await deliverPending(box.store, deps);
  assert.equal(box.audio.calls.at(-1).opts.voice, 'voice-a');
  assert.equal(box.slack.uploads.some((upload) => upload.file === '/tmp/spoken.mp3'), true);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('r3').state, 'delivered');
});

test('board reply is a new root and associated', async (ctx) => {
  const box = harness(ctx);
  const key = 'T1:C1:board';
  box.store.upsertConversation({
    key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: 'board', activated: true,
  });
  box.store.enqueueOutbox({
    id: 'reply:board:0', conversationKey: key, clientMsgId: 'cid-board',
    payload: { text: 'board result' },
  });
  const [result] = await deliverPending(box.store, { slack: box.slack, audio: box.audio, home: box.home });
  assert.equal(result.delivered, true);
  assert.equal(box.slack.posts.length, 1);
  assert.equal(box.slack.posts[0].channel, 'C1');
  assert.equal(box.slack.posts[0].threadTs, undefined);
  assert.equal(box.slack.posts[0].text, 'board result');
  assert.equal(box.store.getConversation(key), null);
  const bound = box.store.getConversation(result.conversationKey);
  assert.equal(bound.root_ts, result.ts);
  assert.equal(bound.activated, true);
  assert.equal(bound.channel, 'C1');
});

test('permanent Slack error does not retry', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'reply:perm:0', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-perm',
    payload: { text: 'nope' },
  });
  box.slack.postMessage = async (args) => {
    box.slack.posts.push(args);
    throw new Error('Slack chat.postMessage: invalid_thread_ts');
  };
  let t = Date.now();
  const deps = { slack: box.slack, audio: box.audio, home: box.home, now: () => t };
  const [first] = await deliverPending(box.store, deps);
  assert.equal(first.stopped, true);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('reply:perm:0').state, 'failed');
  const holds = () => box.store.db.prepare("SELECT id FROM outbox WHERE id LIKE 'hold:%'").all();
  assert.equal(holds().length, 1);
  t += 60_000;
  await deliverPending(box.store, deps);
  await deliverPending(box.store, deps);
  assert.equal(box.slack.posts.filter((post) => post.clientMsgId === 'cid-perm').length, 1);
  assert.equal(holds().length, 1);
});

test('transient delivery retries are capped', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'reply:cap:0', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-cap',
    payload: { text: 'later' },
  });
  box.slack.postMessage = async (args) => {
    box.slack.posts.push(args);
    throw new Error('slack down');
  };
  let t = Date.now();
  const deps = { slack: box.slack, audio: box.audio, home: box.home, now: () => t };
  for (let i = 0; i < 3; i += 1) {
    await deliverPending(box.store, deps);
    t += 5_000;
  }
  assert.equal(box.slack.posts.filter((post) => post.clientMsgId === 'cid-cap').length, 3);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('reply:cap:0').state, 'failed');
  assert.equal(box.store.db.prepare("SELECT COUNT(*) AS n FROM outbox WHERE id LIKE 'hold:%'").get().n, 1);
  await deliverPending(box.store, deps);
  assert.equal(box.slack.posts.filter((post) => post.clientMsgId === 'cid-cap').length, 3);
});

function textHits(slack, text) {
  return [...slack.posts, ...slack.uploads].filter((call) => call.text === text).length;
}

test('voice reply text appears once', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'reply:voice:0', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-voice',
    payload: { text: 'voice check ok', audio: true, files: ['/tmp/agent.mp3'] },
  });
  await deliverPending(box.store, { slack: box.slack, audio: box.audio, home: box.home });
  assert.equal(textHits(box.slack, 'voice check ok'), 1);
  assert.equal(box.slack.uploads.length, 2);
  assert.equal(box.slack.uploads.every((upload) => upload.text == null), true);
  assert.equal(box.store.db.prepare('SELECT state FROM outbox WHERE id=?').get('reply:voice:0').state, 'delivered');
});

test('files-only reply delivers without a text post', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'reply:file:0', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-file',
    payload: { text: '', audio: false, files: ['/tmp/note.txt'] },
  });
  const [result] = await deliverPending(box.store, { slack: box.slack, audio: box.audio, home: box.home });
  assert.equal(result.delivered, true);
  assert.equal(box.slack.posts.length, 0);
  assert.equal(box.slack.uploads.length, 1);
  assert.equal(box.slack.uploads[0].text, undefined);
});

test('retry after a posted text does not post it again', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.store.enqueueOutbox({
    id: 'reply:partial:0', conversationKey: 'T1:C1:1.1', clientMsgId: 'cid-partial',
    payload: { text: 'once only', audio: false, files: ['/tmp/a.txt', '/tmp/b.txt'] },
  });
  let uploads = 0;
  box.slack.uploadFile = async (args) => {
    box.slack.uploads.push(args);
    uploads += 1;
    if (uploads === 2) throw new Error('upload failed');
    return { ts: '8.1', files: [args.file] };
  };
  let t = Date.now();
  const deps = { slack: box.slack, audio: box.audio, home: box.home, now: () => t };
  const [first] = await deliverPending(box.store, deps);
  assert.equal(first.delivered, false);
  assert.equal(box.slack.posts.length, 1);
  assert.equal(box.slack.posts[0].text, 'once only');
  const pending = box.store.db.prepare('SELECT state, ts FROM outbox WHERE id=?').get('reply:partial:0');
  assert.equal(pending.state, 'pending');
  assert.ok(pending.ts);
  box.slack.uploadFile = async (args) => {
    box.slack.uploads.push(args);
    return { ts: '8.2', files: [args.file] };
  };
  t += 6_000;
  const [second] = await deliverPending(box.store, deps);
  assert.equal(second.delivered, true);
  assert.equal(box.slack.posts.length, 1);
  assert.equal(textHits(box.slack, 'once only'), 1);
});

test('transcription failure replies plainly and logs its detail', async (ctx) => {
  const box = harness(ctx);
  seed(box.store, {
    text: '',
    files: [{ name: 'note.m4a', mimetype: 'audio/mp4', filetype: 'm4a' }],
  });
  box.slack.downloads = [{ name: 'note.m4a', path: '/tmp/note.m4a' }];
  box.audio.fail = true;
  box.audio.error = 'audio keys file: /configured/audio-keys.json';
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.equal(result.launched, false);
  assert.equal(seen(box).length, 0);
  const outbox = box.store.pendingOutbox();
  assert.equal(outbox.length, 1);
  assert.equal(outbox[0].payload.text, 'I could not transcribe that voice note; please send it as text.');
  assert.deepEqual(box.logs, [{
    event: 'transcription-failed', message: 'Transcription failed: note.m4a: audio keys file: /configured/audio-keys.json',
  }]);
  const [delivered] = await deliverPending(box.store, { slack: box.slack, audio: box.audio, home: box.home });
  assert.equal(delivered.delivered, true);
  assert.equal(box.slack.posts.at(-1).text, 'I could not transcribe that voice note; please send it as text.');
  const history = fs.readFileSync(historyPath(box.home, 'T1:C1:1.1'), 'utf8');
  assert.equal(history.includes('/configured/audio-keys.json'), false);
});

test('launch failure holds the agent', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  box.writeControl({ writeLauncher: false, exitCode: 2 });
  box.sync();
  const first = await runOnce('master', box.deps);
  assert.equal(first.failure.held, false);
  assert.equal(first.failure.scope, 'agent');
  box.setNow(box.now() + 5000);
  await runOnce('master', box.deps);
  box.setNow(box.now() + 30000);
  const third = await runOnce('master', box.deps);
  assert.equal(third.failure.held, true);
  assert.equal(third.failure.scope, 'agent');
  assert.ok(box.store.agentHold());
  const outbox = box.store.pendingOutbox(box.now() + 1);
  assert.equal(outbox.length, 1);
  assert.match(outbox[0].payload.text, /settings set/);
  assert.match(outbox[0].payload.text, /cast exit 2/);
});

test('history folder name is Windows-valid', async (ctx) => {
  const home = path.join(ctx.dir, 'agent');
  const store = ctx.track(new Store(path.join(home, 'state.sqlite')));
  const key = 'T1:C1:1790563641.107349';
  store.upsertConversation({
    key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1790563641.107349', activated: true,
  });
  const file = writeHistory(home, store, key);
  const folder = path.basename(path.dirname(file));
  assert.equal(folder, 'T1-C1-1790563641.107349');
  assert.equal(/[:*?"<>|\\]/.test(folder), false);
  assert.equal(fs.existsSync(path.join(home, 'conversations', key)), false);
  assert.equal(fs.existsSync(file), true);
  assert.equal(historyPath(home, key), file);
});

test('old colon history folder is found', async (ctx) => {
  const home = path.join(ctx.dir, 'agent');
  const key = 'T1:C1:1.1';
  const legacy = path.join(home, 'conversations', key);
  fs.mkdirSync(legacy, { recursive: true });
  fs.writeFileSync(path.join(legacy, 'history.md'), 'LEGACY_MARKER\n');
  const file = historyPath(home, key);
  assert.equal(fs.readFileSync(file, 'utf8'), 'LEGACY_MARKER\n');
  assert.equal(path.basename(path.dirname(file)), 'T1-C1-1.1');
  assert.equal(fs.existsSync(legacy), false);
});

test('cwd is symlink-resolved', async (ctx) => {
  const box = harness(ctx);
  const link = path.join(ctx.dir, 'link');
  fs.symlinkSync(box.home, link);
  box.deps.home = link;
  seed(box.store);
  box.sync();
  await runOnce('master', box.deps);
  assert.equal(seen(box)[0].cwd, fs.realpathSync(box.home));
  assert.equal(seen(box)[0].env.IGNITE_AGENT_HOME, fs.realpathSync(box.home));
});

for (const trigger of ['owner', 'schedule']) {
  test(`${trigger} turn injects the canonical board with regenerated timers and owner flags`, async (ctx) => {
    const box = harness(ctx);
    const now = Date.now() + 1000;
    box.setNow(now);
    const rootTs = `${Math.floor((now - 8 * 86_400_000) / 1000)}.000000`;
    const replyTs = `${Math.floor((now - 3_600_000) / 1000)}.000000`;
    const key = `T1:C1:${rootTs}`;
    box.store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs });
    if (trigger === 'owner') seed(box.store, { key, id: replyTs, text: 'Reviewed', createdAt: now - 3_600_000 });
    else {
      box.store.recordMessage(key, { id: 'reply', role: 'owner', ts: replyTs, text: 'Reviewed', createdAt: now - 3_600_000 });
      box.store.enqueueScheduleWake({ id: 'wake', conversationKey: key, scheduleId: 'review-timer' });
    }
    box.store.upsertSchedule({ id: 'review-timer', conversationKey: key, cadence: 'every:1h', timezone: 'fixed',
      nextAt: now + 3_600_000, note: 'Read the review', subject: 'Café review' });
    const text = EMPTY_BOARD.replace('## What matters now\n', `## What matters now\n\n### Café review\nWaiting.\n- Threads: [review](https://example.slack.com/archives/C1/p${rootTs.replace('.', '')})\n- Detail: none\n- Flags: none\n`);
    fs.mkdirSync(path.dirname(boardPath(box.home)));
    fs.writeFileSync(boardPath(box.home), text, 'utf8');
    const result = await runOnce('master', box.deps);
    assert.equal(result.disposition, 'completed');
    assert.match(result.prompt, /Café review/);
    for (const marker of ['PROFILE_TOKEN', '# Learned rules — master', '# Memory index', 'INBOX_TOKEN']) assert.ok(result.prompt.includes(marker), marker);
    assert.match(result.prompt, /\| review-timer \| Read the review \| Café review \|/);
    assert.match(result.prompt, /- Flags: answered \d{4}-\d{2}-\d{2}/);
    assert.doesNotMatch(result.prompt, /BOARD_TOKEN|board refresh failed/);
    assert.equal(parseBoard(fs.readFileSync(boardPath(box.home), 'utf8')).subjects.length, 1);
    assert.equal(fs.readFileSync(path.join(box.home, 'board.md'), 'utf8'), TEST_BOARD);
  });
}

test('a due one-shot injects its note from the board after the schedule disables itself', async (ctx) => {
  const box = harness(ctx);
  const now = Date.now() + 1000;
  box.setNow(now);
  const key = 'T1:C1:board';
  box.store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: 'board' });
  box.store.upsertSchedule({ id: 'send-draft', conversationKey: key, cadence: `at:${new Date(now).toISOString()}`,
    timezone: 'Z', nextAt: now, note: 'Send the draft for review' });
  fs.mkdirSync(path.dirname(boardPath(box.home)));
  fs.writeFileSync(boardPath(box.home), EMPTY_BOARD, 'utf8');
  assert.equal(main(['schedules-due', '--now', new Date(now).toISOString()], {
    env: { IGNITE_AGENT_HOME: box.home }, stdout() {},
  }), 0);
  assert.equal(box.store.getSchedule('send-draft').enabled, false);
  const result = await runOnce('master', box.deps);
  assert.equal(result.disposition, 'completed');
  assert.match(result.prompt, /\| send-draft \| Send the draft for review \| none \|/);
  assert.match(result.prompt, /\[schedule\] send-draft\n/);
  assert.deepEqual(result.session, { mode: 'new' });
});

for (const trigger of ['owner', 'schedule']) {
  test(`${trigger} missing memory still launches and queues a deliverable owner alert`, async (ctx) => {
    const box = harness(ctx);
    seed(box.store);
    if (trigger === 'schedule') {
      box.store.db.prepare("DELETE FROM queue WHERE state='pending'").run();
      box.store.enqueueScheduleWake({ id: 'missing-memory-wake', conversationKey: 'T1:C1:1.1', scheduleId: 'check-memory' });
    }
    fs.unlinkSync(path.join(ctx.dir, '.rbtv', 'memory', 'profile.md'));
    fs.unlinkSync(path.join(box.home, 'board.md'));
    fs.writeFileSync(path.join(box.home, 'memory', 'learned.md'), 'BROKEN_LESSON', 'utf8');
    box.sync();
    const result = await runOnce('master', box.deps);
    assert.equal(result.disposition, 'completed');
    assert.match(result.prompt, /MISSING MEMORY/);
    assert.doesNotMatch(result.prompt, /BROKEN_LESSON/);
    assert.equal(box.store.agentHold(), null);
    const alert = box.store.pendingOutbox().find((row) => row.id.startsWith('memory:'));
    assert.match(alert.payload.text, /profile\.md.*ENOENT/);
    assert.match(alert.payload.text, /board\.md.*ENOENT/);
    assert.match(alert.payload.text, /learned\.md.*memory check failed/);
    assert.ok(fs.readdirSync(path.join(box.home, 'memory')).some((name) => name.startsWith('learned.md.broken-')));
    const delivered = await deliverPending(box.store, { slack: box.slack });
    assert.ok(delivered.every((row) => row.delivered));
    assert.ok(box.slack.posts.some((row) => row.text.includes('Memory alert:')));
  });
}

test('resumed turns reread shared inbox and inject only workspace notes matching their cwd', async (ctx) => {
  const box = harness(ctx);
  const memory = path.join(ctx.dir, '.rbtv', 'memory');
  fs.mkdirSync(path.join(memory, 'workspaces'));
  const note = (folder, marker) => `---\ndescription: when working here\ntype: workspace\npaths: [${folder}]\n---\n# ${marker}\n`;
  fs.writeFileSync(path.join(memory, 'workspaces', 'inside.md'), note('.rbtv/agents/master', 'MATCHING_NOTE'), 'utf8');
  fs.writeFileSync(path.join(memory, 'workspaces', 'outside.md'), note('projects/elsewhere', 'OTHER_PRIVATE_NOTE'), 'utf8');
  seed(box.store);
  box.sync();
  const first = await runOnce('master', box.deps);
  assert.match(first.prompt, /MATCHING_NOTE/);
  assert.doesNotMatch(first.prompt, /OTHER_PRIVATE_NOTE/);
  fs.appendFileSync(path.join(memory, 'inbox.md'), '- NEW_INBOX_FACT. (2026-10-01 · other)\n', 'utf8');
  seed(box.store, { id: '2.2', text: 'again', createdAt: 20 });
  box.sync();
  const second = await runOnce('master', box.deps);
  assert.equal(second.session.mode, 'resume');
  assert.match(second.prompt, /NEW_INBOX_FACT/);
  assert.match(second.prompt, /PROFILE_TOKEN/);
});

test('an owner-alert queue failure leaves a visible instruction and never blocks the turn', async (ctx) => {
  const box = harness(ctx);
  seed(box.store);
  fs.unlinkSync(path.join(ctx.dir, '.rbtv', 'memory', 'profile.md'));
  const original = box.store.enqueueOutbox.bind(box.store);
  box.store.enqueueOutbox = (args) => {
    if (args.id?.startsWith('memory:')) throw new Error('simulated queue failure');
    return original(args);
  };
  box.sync();
  const result = await runOnce('master', box.deps);
  assert.equal(result.disposition, 'completed');
  assert.match(result.prompt, /Owner alert could not be queued; tell the owner/);
  assert.equal(box.logs[0].event, 'memory-alert-failed');
});

async function runAll() {
  fs.writeFileSync(stubPath, STUB);
  fs.chmodSync(stubPath, 0o755);
  try {
    for (const [name, fn] of pending) {
      const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-turn-'));
      const open = [];
      const pids = [];
      try {
        await fn({
          dir,
          track(store) { open.push(store); return store; },
          trackPid(child) { pids.push(child); return child; },
        });
        console.log(`PASS ${name}`);
      } catch (error) {
        failures.push(name);
        console.log(`FAIL ${name}: ${error.stack || error.message}`);
      } finally {
        for (const child of pids) {
          try { child.kill(); } catch { /* gone */ }
        }
        for (const store of open) {
          try { store.close(); } catch { /* closed */ }
        }
        fs.rmSync(dir, { recursive: true, force: true });
      }
    }
  } finally {
    fs.rmSync(stubPath, { force: true });
  }
  if (failures.length) {
    console.log(`FAIL ${failures.length}`);
    process.exit(1);
  }
  console.log('PASS turn-loop');
}

runAll();

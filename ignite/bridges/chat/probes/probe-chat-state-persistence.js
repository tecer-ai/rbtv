'use strict';

// OWNER RULING 2026-08-06 (ruling "a") — CONVERSATION STATE SURVIVES A RESTART.
//
// The repro this probe exists for: the owner mentioned the bot, the bot answered, the
// bridge restarted (it is a systemd unit with Restart=on-failure), and the owner's next
// reply in that same live thread was refused SILENTLY — the in-memory thread map had
// forgotten the sitting. Hit twice in one day.
//
// The restart is modelled the way a restart actually works: a SECOND `buildBridge` on
// the SAME `state_file`, with brand-new maps. Nothing is carried over in process memory
// — if the continuation works, it worked off the file.
//
// Same posture as probe-chat-mention-route: no daemon. Every claim is about the
// bridge's own state handling, so the gateway is a stub recording every enqueue and
// Slack is a fake recording every post. That makes the negative claims — "nothing
// written", "nothing enqueued" — checkable as filesystem and call-log assertions
// rather than as the absence of an error.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { resolveConfig } = require('../config');

const OUT = path.join(__dirname, 'probe-chat-state-persistence.out');

const USER = 'U_OWNER';
const BOT = 'U_BOT';
const PREFIX = 'test-';

// ── fakes (same shapes as probe-chat-mention-route) ──────────────────────────

function makeFakeSlack() {
  const channels = [];
  const posted = [];
  let nextId = 1;
  return {
    channels, posted,
    async authTest() { return { ok: true, userId: BOT }; },
    async createChannel({ name }) {
      if (channels.some((c) => c.name === name && !c.is_archived)) return { ok: false, error: 'name_taken' };
      const ch = { id: `C${String(nextId++).padStart(4, '0')}`, name, is_archived: false };
      channels.push(ch);
      return { ok: true, channel: { id: ch.id, name: ch.name } };
    },
    async listChannels({ excludeArchived = true } = {}) {
      const visible = channels.filter((c) => (excludeArchived ? !c.is_archived : true));
      return { ok: true, channels: visible.map((c) => ({ id: c.id, name: c.name, is_archived: c.is_archived })), nextCursor: null };
    },
    async archiveChannel(id) {
      const ch = channels.find((c) => c.id === id);
      if (ch) ch.is_archived = true;
      return { ok: true };
    },
    async sendToOwner({ channel, threadTs, text }) { posted.push({ channel, threadTs, text }); return { delivered: true, ts: '1.0' }; },
    async start() { return { connected: true }; },
    stop() {},
  };
}

function makeFakeForwarder() {
  const enqueued = [];
  let nextQueueId = 100;
  return {
    enqueued,
    async forward(intent, payload) {
      const jobId = nextQueueId++;
      enqueued.push({ intent, payload, jobId });
      return { ok: true, result: { jobId } };
    },
    async inspect() {
      const live = enqueued
        .filter((e) => e.payload.job_id === 'chat-launch')
        .map((e) => ({ queue_id: e.jobId, exec_id: e.jobId, thread: `exec-${e.jobId}` }));
      return { ok: true, result: { live_sessions: live, recent_ticks: [] } };
    },
  };
}

function seedWorkspace(goalIds = []) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-state-'));
  for (const goalId of goalIds) {
    const goalDir = path.join(root, '.rbtv', 'goals', goalId);
    // 7.607 E3: GOAL-DIRECT — the seat folder IS the home; there is no register to read.
    fs.mkdirSync(path.join(goalDir, 'seats', 'goal-master'), { recursive: true });
  }
  return root;
}

// One bridge "process". Called twice on the same stateFile to model a restart.
//
// `forwarder` is injectable because ONLY THE BRIDGE RESTARTS — the daemon on the other
// side of the gateway keeps running, and its live_sessions keep carrying the
// conversation's queue row. A fresh forwarder per bridge would model both processes
// dying, which is a different (and not the owner's) scenario.
function makeBridge({ stateFile = null, workspaceRoot = null, logs = null, forwarder = makeFakeForwarder() } = {}) {
  const slack = makeFakeSlack();
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot,
    channelPrefix: PREFIX,
    stateFile,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: logs ? (e) => logs.push(e) : () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 },
  });
  return { ...built, slack, forwarder, config };
}

function msg({ channel, ts, threadTs = null, channelType, text = 'hello', user = USER }) {
  return {
    chatUserId: user,
    chatThreadId: `${channel}:${threadTs || ts}`,
    text,
    _channel: channel,
    _threadTs: threadTs || ts,
    _channelType: channelType,
    _inThread: Boolean(threadTs),
  };
}

// ── the probe ────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-statedir-'));

  // 1 — THE RESTART-AMNESIA REPRO, NOW GREEN. Mention mints a sitting in bridge A;
  //     bridge B is a fresh process on the same state file; an UN-MENTIONED reply in
  //     that thread CONTINUES as a follow-up instead of being refused.
  {
    const stateFile = path.join(stateDir, 'run1', 'chat-state.json');
    const daemon = makeFakeForwarder(); // outlives the bridge restart, as the real one does

    const a = makeBridge({ stateFile, forwarder: daemon });
    await a.bridge.start();
    const mint = await a.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '1.1', channelType: 'channel', text: `<@${BOT}> start` }));
    a.bridge.stop();

    check('a mutation writes the state file (created under a directory that did not exist)',
      mint.forwarded === true && fs.existsSync(stateFile), { stateFile, exists: fs.existsSync(stateFile) });

    const mode = fs.statSync(stateFile).mode & 0o777;
    check('state file is 0600', mode === 0o600, { mode: mode.toString(8) });

    const doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    check('the file carries BOTH tables — the thread map and the reply address',
      Boolean(doc.threads && doc.threads['C_RANDOM:1.1'])
      && Boolean(doc.replyAddr && doc.replyAddr['C_RANDOM:1.1'])
      && doc.replyAddr['C_RANDOM:1.1'].channel === 'C_RANDOM'
      && doc.replyAddr['C_RANDOM:1.1'].threadTs === '1.1',
      { threads: Object.keys(doc.threads || {}), replyAddr: doc.replyAddr });

    // THE RESTART. A brand-new bridge, brand-new maps, same file, same daemon.
    const enqueuedBeforeRestart = daemon.enqueued.length;
    const b = makeBridge({ stateFile, forwarder: daemon });
    check('the restarted bridge starts with EMPTY maps before start() — nothing carried in memory',
      b.threadMap.size() === 0 && b.bridge._replyAddr.size === 0,
      { threads: b.threadMap.size(), replyAddr: b.bridge._replyAddr.size });

    await b.bridge.start();
    check('start() restored the conversation from disk',
      b.threadMap.size() === 1 && b.threadMap.has('C_RANDOM:1.1') && b.bridge._replyAddr.size === 1,
      { threads: b.threadMap.size(), replyAddr: b.bridge._replyAddr.size });

    const cont = await b.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '1.2', threadTs: '1.1', channelType: 'channel', text: 'and one more thing' }));
    const sinceRestart = daemon.enqueued.slice(enqueuedBeforeRestart);
    check('AFTER A RESTART an un-mentioned reply in the restored thread CONTINUES (the repro, green)',
      cont.forwarded === true && cont.route === 'master' && cont.leg === 'follow-up'
      && sinceRestart.length === 1
      && sinceRestart[0].payload.job_id === 'send-message',
      { cont, sinceRestart: sinceRestart.map((e) => e.payload.job_id) });

    // The restored reply ADDRESS is what makes the answer land back in the right thread.
    await b.bridge.deliverToOwner({ chatThreadId: 'C_RANDOM:1.1', text: 'restored answer' });
    const post = b.slack.posted[b.slack.posted.length - 1];
    check('the restored reply address still addresses the original channel+thread',
      Boolean(post) && post.channel === 'C_RANDOM' && post.threadTs === '1.1', { post });
    b.bridge.stop();
  }

  // 2 — THE CONTROL. The SAME restart with NO state file refuses the same reply. Without
  //     this, check 1 could pass for a reason that has nothing to do with the file.
  {
    const daemon = makeFakeForwarder(); // identical to case 1 in every way EXCEPT the state file
    const a = makeBridge({ stateFile: null, forwarder: daemon });
    await a.bridge.start();
    await a.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '2.1', channelType: 'channel', text: `<@${BOT}> start` }));
    a.bridge.stop();

    const enqueuedBeforeRestart = daemon.enqueued.length;
    const b = makeBridge({ stateFile: null, forwarder: daemon });
    await b.bridge.start();
    const cont = await b.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '2.2', threadTs: '2.1', channelType: 'channel', text: 'and one more thing' }));
    check('CONTROL — with no state_file the same post-restart reply is still REFUSED (the old amnesia)',
      cont.forwarded === false && cont.reason === 'unroutable-surface' && daemon.enqueued.length === enqueuedBeforeRestart,
      { cont, enqueuedSinceRestart: daemon.enqueued.length - enqueuedBeforeRestart });
    b.bridge.stop();
  }

  // 3 — NO state_file → NOTHING WRITTEN ANYWHERE. Persistence is strictly opt-in, and an
  //     unconfigured deployment must not sprout a file next to whatever its cwd is.
  {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-nostate-'));
    const cwd = process.cwd();
    process.chdir(dir);
    try {
      const a = makeBridge({ stateFile: null });
      await a.bridge.start();
      await a.bridge.onChatMessage(msg({ channel: 'D_IM', ts: '3.1', channelType: 'im', text: 'hello' }));
      await a.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '3.2', channelType: 'channel', text: `<@${BOT}> hi` }));
      a.bridge.stop();
      const left = fs.readdirSync(dir);
      check('no state_file → the bridge writes NOTHING (empty cwd, null stateFile handle)',
        left.length === 0 && a.bridge.stateFile === null, { cwd: dir, left, stateFile: a.bridge.stateFile });
    } finally {
      process.chdir(cwd);
    }
  }

  // 4 — CORRUPT FILE → renamed aside, EMPTY start, no crash, and the bridge still works.
  //     A systemd unit that crash-loops on unparseable state is worse than one that
  //     forgets: the whole chat surface goes down over a convenience cache.
  {
    const stateFile = path.join(stateDir, 'corrupt', 'chat-state.json');
    fs.mkdirSync(path.dirname(stateFile), { recursive: true });
    fs.writeFileSync(stateFile, '{"threads": {"C_X:9.9": {"queue', { mode: 0o600 });

    const logs = [];
    const b = makeBridge({ stateFile, logs });
    let threw = null;
    try { await b.bridge.start(); } catch (err) { threw = err.message; }

    const aside = fs.readdirSync(path.dirname(stateFile)).filter((f) => f.includes('.corrupt-'));
    check('corrupt state file does not crash start()', threw === null, { threw });
    check('corrupt state file is renamed aside (.corrupt-<ts>) and the original is gone',
      aside.length === 1 && !fs.existsSync(stateFile), { aside, originalStillThere: fs.existsSync(stateFile) });
    check('the corruption is LOUD — logged at error level', logs.some((l) => l.level === 'error' && /unparseable/.test(l.message)),
      { errors: logs.filter((l) => l.level === 'error').map((l) => l.message) });
    check('the bridge starts EMPTY after a corrupt file', b.threadMap.size() === 0 && b.bridge._replyAddr.size === 0,
      { threads: b.threadMap.size() });

    // And it is fully functional: a new mention mints and re-persists.
    const mint = await b.bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '4.1', channelType: 'channel', text: `<@${BOT}> after corruption` }));
    check('after a corrupt-file start the bridge still mints and re-persists',
      mint.forwarded === true && fs.existsSync(stateFile)
      && Boolean(JSON.parse(fs.readFileSync(stateFile, 'utf8')).threads['C_RANDOM:4.1']),
      { mint });
    b.bridge.stop();
  }

  // 5 — DELETES PERSIST TOO. closeGoal drops the goal's reply address; the file must
  //     reflect it, or a restart would resurrect an address pointing at an ARCHIVED
  //     channel that takes no more traffic.
  {
    const stateFile = path.join(stateDir, 'close', 'chat-state.json');
    const workspaceRoot = seedWorkspace(['goal-closing']);
    const a = makeBridge({ stateFile, workspaceRoot });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-closing');
    await a.bridge.onChatMessage(msg({ channel: reg.channelId, ts: '5.1', channelType: 'channel', text: 'status?' }));

    const before = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    await a.bridge.closeGoal('goal-closing');
    const after = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    check('closeGoal\'s reply-address DELETE is persisted (any mutation persists, deletes included)',
      Boolean(before.replyAddr[reg.channelId]) && after.replyAddr[reg.channelId] === undefined,
      { channelId: reg.channelId, before: Object.keys(before.replyAddr), after: Object.keys(after.replyAddr) });
    a.bridge.stop();
  }

  // 6 — RELATIVE PATHS ARE REFUSED AT CONFIG RESOLUTION. A relative state_file resolves
  //     against the daemon's cwd, so the same config would read a different file
  //     depending on how the unit was started — a SILENT amnesia, the exact bug the key
  //     exists to fix. Refused loudly instead.
  {
    let threw = null;
    try { resolveConfig({ stateFile: 'chat-state.json' }); } catch (err) { threw = err.message; }
    const abs = resolveConfig({ stateFile: '/abs/chat-state.json' });
    const unset = resolveConfig({});
    check('a relative state_file is refused at config resolution', threw !== null && /absolute/.test(threw), { threw });
    check('an absolute state_file resolves, and unset stays null (opt-in default)',
      abs.stateFile === '/abs/chat-state.json' && unset.stateFile === null,
      { abs: abs.stateFile, unset: unset.stateFile });
  }

  try { fs.rmSync(stateDir, { recursive: true, force: true }); } catch {}

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-state-persistence', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-state-persistence EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();

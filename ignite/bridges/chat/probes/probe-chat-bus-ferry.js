'use strict';

// THE BUS FERRY (bus-ferry.js) — coordination bus → the owner's Slack DM, one way.
//
// The owner-hit problem: a run agent answers the master over the coordination bus and
// the answer sits unread, because the channel-master's Slack sittings are one-turn
// headless sessions and nothing pushes a bus row anywhere.
//
// The claim that MATTERS most here is a NEGATIVE one: a run's existing backlog —
// thousands of rows on a live run — is NEVER ferried. So the fixture builds a run with a
// real backlog of `to: master` rows, and the flood check asserts against the mock
// transport's post log, not against the absence of an error.
//
// No daemon: every claim is about the ferry's own file reading and posting. The gateway
// is a stub and Slack is a fake that records every post.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { resolveConfig } = require('../config');
const { DEFAULT_MAX_BODY_CHARS } = require('../bus-ferry');

const OUT = path.join(__dirname, 'probe-chat-bus-ferry.out');

const USER = 'U_OWNER';
const DM = 'D_OWNER';
const BOT = 'U_BOT';

// ── fakes ────────────────────────────────────────────────────────────────────

function makeFakeSlack() {
  const posted = [];
  const opened = [];
  let failPosts = 0;
  let failOpenDm = false;
  return {
    posted, opened,
    failNextPosts(n) { failPosts = n; },
    failOpenDm() { failOpenDm = true; },
    async authTest() { return { ok: true, userId: BOT }; },
    async openDm(userId) {
      opened.push(userId);
      if (failOpenDm) return { ok: false, error: 'user_not_found' };
      return { ok: true, channel: DM };
    },
    async sendToOwner({ channel, threadTs, text }) {
      if (failPosts > 0) { failPosts -= 1; return { delivered: false, error: 'ratelimited' }; }
      posted.push({ channel, threadTs, text });
      return { delivered: true, ts: '1.0' };
    },
    async start() { return { connected: true }; },
    stop() {},
  };
}

function makeFakeForwarder() {
  return {
    async forward() { return { ok: true, result: { jobId: 1 } }; },
    async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
  };
}

// ── the bus fixture ──────────────────────────────────────────────────────────

function msgRow(id, from, to, type, body) {
  return `## ${id} | from: ${from} | to: ${to} | type: ${type} | 2026-08-06 14:23\n\n${body}\n\n`;
}

function seedRun(root, goalId, runId, { state = 'open', backlogRows = 0 } = {}) {
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  const coord = path.join(goalDir, 'runs', runId, 'coordination');
  fs.mkdirSync(coord, { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'runs.csv'),
    'run-id,type,state,taskforce-ids,opened,closed\n' +
    `${runId},fresh,${state},tf-1,2026-08-03 00:00,\n`);
  const file = path.join(coord, 'messages.md');
  let text = '# messages — append-only coordination log (script-managed, do not edit by hand)\n\n';
  // A REAL backlog, every row addressed to master — exactly what must NOT be ferried.
  for (let i = 1; i <= backlogRows; i++) text += msgRow(i, 'leader', 'master', 'note', `historical row ${i}`);
  fs.writeFileSync(file, text);
  return { file, lastId: backlogRows };
}

function append(file, chunk) { fs.appendFileSync(file, chunk); }

function makeBridge({ workspaceRoot, stateFile = null, busFerry = true, busFerryDmUser = null, logs = null, slack = makeFakeSlack(), busFerryOptions = {} } = {}) {
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sessionProfile: 'p',
    sendMessageJobId: 'send-message',
    workdir: null,
    workspaceRoot,
    channelPrefix: 'test-',
    stateFile,
    busFerry,
    busFerryDmUser: busFerryDmUser || USER,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: logs ? (e) => logs.push(e) : () => {},
    makeTransport: () => slack,
    forwarderImpl: makeFakeForwarder(),
    replyLegOptions: { pollMs: 3600000 },
    busFerryOptions: { pollMs: 3600000, ...busFerryOptions }, // driven by hand via tick()
  });
  return { ...built, slack, config };
}

// ── the probe ────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  const roots = [];
  const mkroot = () => { const r = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-busferry-')); roots.push(r); return r; };

  // 1 — FIRST SIGHT: a run with a 50-row `to: master` backlog ferries NOTHING, and the
  //     cursor lands AT THE TAIL. This is the check the whole module is shaped around.
  {
    const root = mkroot();
    const { file, lastId } = seedRun(root, 'goal-a', 'run-1', { backlogRows: 50 });
    const a = makeBridge({ workspaceRoot: root });
    const started = await a.bridge.start();
    await a.bridge.busFerry.tick();

    check('the ferry starts and resolves the owner DM once',
      a.bridge.busFerry.enabled === true && a.bridge.busFerry.dmChannel === DM && a.slack.opened.length === 1,
      { opened: a.slack.opened, dmChannel: a.bridge.busFerry.dmChannel });

    check('FIRST SIGHT: a 50-row to:master backlog is NOT ferried (nothing posted)',
      a.slack.posted.length === 0, { backlogRows: lastId, posted: a.slack.posted.length });

    check('FIRST SIGHT: the cursor is initialized AT THE TAIL',
      a.bridge.busFerry._cursors.get('goal-a/run-1') === lastId,
      { cursor: a.bridge.busFerry._cursors.get('goal-a/run-1'), tail: lastId });

    // 2 — A row appended AFTER first sight IS ferried, exactly once, with the header.
    append(file, msgRow(51, 'leader', 'master', 'note', 'ack — the m6 pass is running'));
    await a.bridge.busFerry.tick();
    const p = a.slack.posted[0];
    check('a row appended after first sight IS ferried, once, to the DM channel',
      a.slack.posted.length === 1 && p.channel === DM && p.threadTs === null,
      { posted: a.slack.posted.length, channel: p && p.channel });
    check('the ferried message carries the phone-first header and the body verbatim',
      Boolean(p) && p.text === '*bus → you* — goal-a/run-1 · from leader · note · #51\nack — the m6 pass is running',
      { text: p && p.text });

    // Idempotence: another pass with nothing appended posts nothing more.
    await a.bridge.busFerry.tick();
    check('a second pass over an unchanged file ferries nothing again',
      a.slack.posted.length === 1, { posted: a.slack.posted.length });

    // 3 — `to: leader` is not the owner's mail. Ignored, and the cursor still advances.
    append(file, msgRow(52, 'master', 'leader', 'note', 'do the thing'));
    append(file, msgRow(53, 'chief-of-staff', 'master, leader', 'note', 'multi-recipient reaches master'));
    append(file, msgRow(54, 'x', 'goal-master', 'note', 'a token that merely CONTAINS master'));
    await a.bridge.busFerry.tick();
    check('a `to: leader` row is ignored; a comma-separated `to: master, leader` row IS ferried; `goal-master` is NOT',
      a.slack.posted.length === 2 && /#53/.test(a.slack.posted[1].text)
      && a.bridge.busFerry._cursors.get('goal-a/run-1') === 54,
      { posted: a.slack.posted.map((x) => x.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-a/run-1') });

    a.bridge.stop();
  }

  // 4 — TRUNCATION at a line boundary, naming the workspace-relative source.
  {
    const root = mkroot();
    const { file } = seedRun(root, 'goal-b', 'run-1', { backlogRows: 1 });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick(); // first sight

    const long = Array.from({ length: 400 }, (_, i) => `line ${i} ${'x'.repeat(20)}`).join('\n');
    append(file, msgRow(2, 'leader', 'master', 'note', long));
    await a.bridge.busFerry.tick();
    const text = a.slack.posted[0].text;
    const lines = text.split('\n');
    const tail = lines[lines.length - 1];
    const lastBodyLine = lines[lines.length - 2];
    const bodyLen = text.length - text.indexOf('\n') - 1;
    check('an over-long body is truncated at a LINE boundary (last line WHOLE) with the full-text pointer',
      a.slack.posted.length === 1
      && tail === '… (truncated — full text: .rbtv/goals/goal-b/runs/run-1/coordination/messages.md #2)'
      && bodyLen <= DEFAULT_MAX_BODY_CHARS + tail.length + 1
      && /^line \d+ x{20}$/.test(lastBodyLine),
      { bodyLen, tail, lastBodyLine, rawBodyChars: long.length });
    a.bridge.stop();
  }

  // 5 — TORN WRITE: a trailing row with no terminating newline is LEFT for the next
  //     pass, never posted half-read.
  {
    const root = mkroot();
    const { file } = seedRun(root, 'goal-c', 'run-1', { backlogRows: 1 });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();

    fs.appendFileSync(file, '## 2 | from: leader | to: master | type: note | 2026-08-06 14:23\n\nhalf-writ');
    await a.bridge.busFerry.tick();
    check('a torn trailing row (no terminating newline) is NOT posted',
      a.slack.posted.length === 0 && a.bridge.busFerry._cursors.get('goal-c/run-1') === 1,
      { posted: a.slack.posted.length });

    fs.appendFileSync(file, 'ten, now complete\n\n');
    await a.bridge.busFerry.tick();
    check('once the torn row completes it IS ferried, whole',
      a.slack.posted.length === 1 && /half-written, now complete$/.test(a.slack.posted[0].text),
      { text: a.slack.posted[0] && a.slack.posted[0].text });

    // A malformed header is skipped LOUDLY-ONCE, and does not stop the rows around it.
    const logs = [];
    const b = makeBridge({ workspaceRoot: root, logs, slack: a.slack });
    await b.bridge.start();
    b.bridge.busFerry._cursors.set('goal-c/run-1', 2); // pretend we already saw the run
    fs.appendFileSync(file, '## not-a-header at all\n\njunk\n\n');
    fs.appendFileSync(file, msgRow(3, 'leader', 'master', 'note', 'after the junk'));
    fs.appendFileSync(file, '## also not a header\n\nmore junk\n\n');
    fs.appendFileSync(file, msgRow(4, 'leader', 'master', 'note', 'after more junk'));
    await b.bridge.busFerry.tick();
    const warns = logs.filter((l) => l.level === 'warn' && /malformed/.test(l.message));
    const debugs = logs.filter((l) => l.level === 'debug' && /malformed/.test(l.message));
    check('malformed headers are skipped, the surrounding rows still ferry, and the warn fires ONCE (the rest at debug)',
      a.slack.posted.length === 3 && warns.length === 1 && debugs.length === 1,
      { posted: a.slack.posted.length, warns: warns.length, debugs: debugs.length });
    a.bridge.stop(); b.bridge.stop();
  }

  // 6 — DELIVERY FAILURE: retried, order preserved, then skipped at the cap with a loud
  //     log — the ferry never wedges behind one undeliverable row.
  {
    const root = mkroot();
    const { file } = seedRun(root, 'goal-d', 'run-1', { backlogRows: 1 });
    const logs = [];
    const slack = makeFakeSlack();
    const a = makeBridge({ workspaceRoot: root, logs, slack, busFerryOptions: { maxAttempts: 3 } });
    await a.bridge.start();
    await a.bridge.busFerry.tick();

    append(file, msgRow(2, 'leader', 'master', 'note', 'the poisoned row'));
    append(file, msgRow(3, 'leader', 'master', 'note', 'the row behind it'));
    slack.failNextPosts(100);
    await a.bridge.busFerry.tick();
    await a.bridge.busFerry.tick();
    check('a failed post is retried and does NOT advance the cursor, and row 3 does not jump the queue',
      slack.posted.length === 0 && a.bridge.busFerry._cursors.get('goal-d/run-1') === 1,
      { posted: slack.posted.length, cursor: a.bridge.busFerry._cursors.get('goal-d/run-1') });

    await a.bridge.busFerry.tick(); // 3rd attempt == cap
    const gaveUp = logs.filter((l) => l.level === 'warn' && /giving up/.test(l.message));
    check('at the attempt cap the row is SKIPPED loudly and the cursor advances past it',
      gaveUp.length === 1 && a.bridge.busFerry._cursors.get('goal-d/run-1') === 2,
      { gaveUp: gaveUp.length, cursor: a.bridge.busFerry._cursors.get('goal-d/run-1') });

    slack.failNextPosts(0);
    await a.bridge.busFerry.tick();
    check('the ferry is UNWEDGED — the row behind the skipped one ferries on the next pass',
      slack.posted.length === 1 && /#3/.test(slack.posted[0].text),
      { posted: slack.posted.map((p) => p.text.split('\n')[0]) });
    a.bridge.stop();
  }

  // 7 — THE CURSOR SURVIVES A RESTART. A second bridge on the same state_file must not
  //     re-post what the first already delivered — and must not re-arm first sight.
  {
    const root = mkroot();
    const stateFile = path.join(mkroot(), 'chat-state.json');
    const { file } = seedRun(root, 'goal-e', 'run-1', { backlogRows: 20 });
    const a = makeBridge({ workspaceRoot: root, stateFile });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(21, 'leader', 'master', 'note', 'delivered before the restart'));
    await a.bridge.busFerry.tick();
    a.bridge.stop();
    check('pre-restart: one row ferried, cursor persisted to the state file',
      a.slack.posted.length === 1
      && JSON.parse(fs.readFileSync(stateFile, 'utf8')).busFerry.cursors['goal-e/run-1'] === 21,
      { posted: a.slack.posted.length, doc: JSON.parse(fs.readFileSync(stateFile, 'utf8')).busFerry });

    const b = makeBridge({ workspaceRoot: root, stateFile });
    check('the restarted bridge holds NO cursors before start()', b.bridge.busFerry._cursors.size === 0, {});
    await b.bridge.start();
    check('start() restored the ferry cursor from disk',
      b.bridge.busFerry._cursors.get('goal-e/run-1') === 21, { cursor: b.bridge.busFerry._cursors.get('goal-e/run-1') });
    await b.bridge.busFerry.tick();
    check('AFTER A RESTART nothing is re-posted — no double-post, no re-flood of the 20-row backlog',
      b.slack.posted.length === 0, { posted: b.slack.posted.length });

    append(file, msgRow(22, 'leader', 'master', 'note', 'after the restart'));
    await b.bridge.busFerry.tick();
    check('the restarted ferry keeps ferrying from where it left off',
      b.slack.posted.length === 1 && /#22/.test(b.slack.posted[0].text), { text: b.slack.posted[0] && b.slack.posted[0].text });
    b.bridge.stop();

    // The extension is ADDITIVE: the version-1 keys are untouched beside it.
    const doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    check('the state file is EXTENDED, not restructured (version 1, threads + replyAddr still present)',
      doc.version === 1 && Object.prototype.hasOwnProperty.call(doc, 'threads')
      && Object.prototype.hasOwnProperty.call(doc, 'replyAddr') && Boolean(doc.busFerry),
      { keys: Object.keys(doc), version: doc.version });
  }

  // 8 — CLOSED runs are not ferried (only `state=open` rows in runs.csv).
  {
    const root = mkroot();
    const { file } = seedRun(root, 'goal-f', 'run-1', { state: 'closed', backlogRows: 1 });
    append(file, msgRow(2, 'leader', 'master', 'note', 'from a closed run'));
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    check('a CLOSED run is never enumerated — nothing ferried, no cursor minted',
      a.slack.posted.length === 0 && a.bridge.busFerry._cursors.size === 0,
      { posted: a.slack.posted.length, cursors: a.bridge.busFerry._cursors.size });
    a.bridge.stop();
  }

  // 9 — DISABLED / FAIL-CLOSED. Off by default; on without `workspace_root` or without a
  //     resolvable DM it says so LOUDLY and stays off — the bridge is otherwise fine.
  {
    const root = mkroot();
    const { file } = seedRun(root, 'goal-g', 'run-1', { backlogRows: 1 });
    append(file, msgRow(2, 'leader', 'master', 'note', 'should never be ferried'));

    const off = makeBridge({ workspaceRoot: root, busFerry: false });
    await off.bridge.start();
    await off.bridge.busFerry.tick();
    check('bus_ferry off → the ferry never starts, opens no DM, posts nothing',
      off.bridge.busFerry.enabled === false && off.slack.opened.length === 0 && off.slack.posted.length === 0,
      { opened: off.slack.opened.length, posted: off.slack.posted.length });
    off.bridge.stop();

    const noRoot = [];
    const nr = makeBridge({ workspaceRoot: null, busFerry: true, logs: noRoot });
    await nr.bridge.start();
    check('bus_ferry on WITHOUT workspace_root → disabled, logged at error',
      nr.bridge.busFerry.enabled === false
      && noRoot.some((l) => l.level === 'error' && /workspace_root/.test(l.message)),
      { errors: noRoot.filter((l) => l.level === 'error').map((l) => l.message) });
    nr.bridge.stop();

    const dmLogs = [];
    const badDm = makeFakeSlack();
    badDm.failOpenDm();
    const bd = makeBridge({ workspaceRoot: root, busFerry: true, logs: dmLogs, slack: badDm });
    let threw = null;
    try { await bd.bridge.start(); } catch (err) { threw = err.message; }
    await bd.bridge.busFerry.tick();
    check('a failed conversations.open DISABLES the ferry loudly and does not take the bridge down',
      threw === null && bd.bridge.busFerry.enabled === false && badDm.posted.length === 0
      && dmLogs.some((l) => l.level === 'error' && /could not open the owner DM/.test(l.message)),
      { threw, errors: dmLogs.filter((l) => l.level === 'error').map((l) => l.message) });
    bd.bridge.stop();
  }

  // 10 — CONFIG resolution: off by default, and the DM target defaults to the first
  //      allowlist entry.
  {
    const def = resolveConfig({});
    const on = resolveConfig({ busFerry: true, allowlist: ['U_FIRST', 'U_SECOND'] });
    const explicit = resolveConfig({ busFerry: true, allowlist: ['U_FIRST'], busFerryDmUser: 'U_EXPLICIT' });
    check('bus_ferry defaults to false with a null DM user; enabled it defaults to the FIRST allowlist entry; an explicit key wins',
      def.busFerry === false && def.busFerryDmUser === null
      && on.busFerry === true && on.busFerryDmUser === 'U_FIRST'
      && explicit.busFerryDmUser === 'U_EXPLICIT',
      { def: { busFerry: def.busFerry, dm: def.busFerryDmUser }, on: on.busFerryDmUser, explicit: explicit.busFerryDmUser });
  }

  for (const r of roots) { try { fs.rmSync(r, { recursive: true, force: true }); } catch {} }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-bus-ferry', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-bus-ferry EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();

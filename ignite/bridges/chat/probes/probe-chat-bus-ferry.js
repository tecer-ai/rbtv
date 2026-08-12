'use strict';

// THE BUS FERRY (bus-ferry.js) — coordination bus → the owner's Slack DM, one way.
//
// The owner-hit problem: a run agent raises something a human must answer over the coordination
// bus and it sits unread, because the channel-master's Slack sittings are one-turn headless
// sessions and nothing pushes a bus row anywhere.
//
// ⚑ THE ADDRESS IS `to: owner` (ruling `d-agents-address-owner-not-master`, 2026-08-09). Agents
// never INITIATE to `master`; a master-addressed row is an ANSWER between seats and this ferry
// must never carry one — arm 3b is that claim's red/green pair.
//
// The claim that MATTERS most here is a NEGATIVE one: a run's existing backlog —
// thousands of rows on a live run — is NEVER ferried. So the fixture builds a run with a
// real backlog of `to: owner` rows, and the flood check asserts against the mock
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

// EVERY SENDER NAME ANY ARM BELOW WRITES IN A `from:` FIELD. Since 2026-08-09 the ferry's
// nobody-home branch is GATED on agent-initiated contact (bus-ferry.js § THE TWO GATES), so a
// fixture that seeds neither gate parks every row and every delivery claim here would go green
// for the wrong reason — asserting "not posted" while measuring "not allowed to post". The arms
// below are about PARSING, TRUNCATION, RETRY, CURSORS and the ROSTER, so they hold both gates
// OPEN and the gate decision itself is proven in `probe-chat-agent-thread` (both defaults, both
// flag values, and the park).
const SENDERS = ['leader', 'master', 'chief-of-staff', 'planning-strategist', 'fixture-seat-a', 'x', 'some-worker'];

function writeSeatDescriptor(runDir, seat, { humanInteractive = true } = {}) {
  const dir = path.join(runDir, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'),
    `---\nseat: ${seat}\n${humanInteractive ? 'human-interactive: yes\n' : ''}---\nbody\n`);
}

// 7.607 E3: GOAL-DIRECT. No `runs.csv`, no run folder — the bus is `<goal>/coordination/` and the
// third argument is the goal's EXECUTION STAMP (design-lock item 5), written to the marker
// `coordination/execution` exactly as `coord.py mint_execution` writes it. The stamp is what the
// cursor is keyed by, so a fixture that omitted it would test a key shape nothing produces.
function seedGoal(root, goalId, stamp, { backlogRows = 0, executionMode = 'interactive', senders = SENDERS } = {}) {
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  const coord = path.join(goalDir, 'coordination');
  fs.mkdirSync(coord, { recursive: true });
  fs.writeFileSync(path.join(coord, 'execution'), `${stamp}\n`);
  // Gate 2, then gate 1 — see SENDERS above.
  if (executionMode) fs.writeFileSync(path.join(goalDir, 'execution-mode'), `${executionMode}\n`);
  for (const s of senders) writeSeatDescriptor(goalDir, s);
  const file = path.join(coord, 'messages.md');
  let text = '# messages — append-only coordination log (script-managed, do not edit by hand)\n\n';
  // A REAL backlog, every row addressed to the owner — exactly what must NOT be ferried.
  for (let i = 1; i <= backlogRows; i++) text += msgRow(i, 'leader', 'owner', 'note', `historical row ${i}`);
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
    // ⚑ THE AGENT-THREAD LEG IS UNWIRED HERE, DELIBERATELY (2026-08-12). These arms are about
    // PARSING, TRUNCATION, RETRY and CURSORS — the ferry's DM leg is simply the surface they
    // measure them on, and `routeToAgentThread: null` is the documented unwired configuration
    // (bus-ferry.js § routeToAgentThread), not a bypass. Wired, every one of them would now
    // measure the goal-channel routing instead: since the no-channel DM fallback was removed a
    // channel-less goal holds its rows, and `probe-chat-agent-thread` is where that claim lives.
    busFerryOptions: { pollMs: 3600000, routeToAgentThread: null, ...busFerryOptions }, // driven by hand via tick()
  });
  return { ...built, slack, config };
}

// ── the probe ────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  const skipped = [];

  const roots = [];
  const mkroot = () => { const r = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-busferry-')); roots.push(r); return r; };

  // 1 — FIRST SIGHT: a run with a 50-row `to: owner` backlog ferries NOTHING, and the
  //     cursor lands AT THE TAIL. This is the check the whole module is shaped around.
  {
    const root = mkroot();
    const { file, lastId } = seedGoal(root, 'goal-a', '2026-08-03a', { backlogRows: 50 });
    const a = makeBridge({ workspaceRoot: root });
    const started = await a.bridge.start();
    await a.bridge.busFerry.tick();

    check('the ferry starts and resolves the owner DM once',
      a.bridge.busFerry.enabled === true && a.bridge.busFerry.dmChannel === DM && a.slack.opened.length === 1,
      { opened: a.slack.opened, dmChannel: a.bridge.busFerry.dmChannel });

    check('FIRST SIGHT: a 50-row to:owner backlog is NOT ferried (nothing posted)',
      a.slack.posted.length === 0, { backlogRows: lastId, posted: a.slack.posted.length });

    check('FIRST SIGHT: the cursor is initialized AT THE TAIL',
      a.bridge.busFerry._cursors.get('goal-a/2026-08-03a') === lastId,
      { cursor: a.bridge.busFerry._cursors.get('goal-a/2026-08-03a'), tail: lastId });

    // 2 — A row appended AFTER first sight IS ferried, exactly once, with the header.
    append(file, msgRow(51, 'leader', 'owner', 'note', 'ack — the m6 pass is running'));
    await a.bridge.busFerry.tick();
    const p = a.slack.posted[0];
    check('a row appended after first sight IS ferried, once, to the DM channel',
      a.slack.posted.length === 1 && p.channel === DM && p.threadTs === null,
      { posted: a.slack.posted.length, channel: p && p.channel });
    check('the ferried message carries the phone-first header and the body verbatim',
      Boolean(p) && p.text === '*bus → you* — goal-a/2026-08-03a · from leader · note · #51\nack — the m6 pass is running',
      { text: p && p.text });

    // Idempotence: another pass with nothing appended posts nothing more.
    await a.bridge.busFerry.tick();
    check('a second pass over an unchanged file ferries nothing again',
      a.slack.posted.length === 1, { posted: a.slack.posted.length });

    // 3 — THE TOKEN GRAMMAR. `to: leader` is not the owner's mail; a comma-separated list that
    //     CONTAINS `owner` is; a token that merely contains the WORD (`goal-owner`) is a seat
    //     name and is not. The cursor advances past every one of them either way.
    append(file, msgRow(52, 'master', 'leader', 'note', 'do the thing'));
    append(file, msgRow(53, 'chief-of-staff', 'owner, leader', 'note', 'multi-recipient reaches the owner'));
    append(file, msgRow(54, 'x', 'goal-owner', 'note', 'a token that merely CONTAINS owner'));
    await a.bridge.busFerry.tick();
    check('a `to: leader` row is ignored; a comma-separated `to: owner, leader` row IS ferried; `goal-owner` is NOT',
      a.slack.posted.length === 2 && /#53/.test(a.slack.posted[1].text)
      && a.bridge.busFerry._cursors.get('goal-a/2026-08-03a') === 54,
      { posted: a.slack.posted.map((x) => x.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-a/2026-08-03a') });

    // 3b — THE RULING'S RED HALF (`d-agents-address-owner-not-master`, 2026-08-09): a `to: master`
    //      row is NEVER ferried anywhere, from the same seat, in the same run, on the same pass
    //      that a `to: owner` row from that seat travels. Master-addressed traffic is an ANSWER
    //      between seats and stays the bus's business end to end; the GREEN half beside it is what
    //      keeps this from passing against a ferry that had simply stopped working.
    append(file, msgRow(55, 'leader', 'master', 'ask', 'MASTER-ADDRESSED — must never reach chat'));
    append(file, msgRow(56, 'leader', 'owner', 'ask', 'OWNER-ADDRESSED — must reach chat'));
    await a.bridge.busFerry.tick();
    check('RULING: a `to: master` row is NEVER ferried, while a `to: owner` row from the SAME seat on the SAME pass IS',
      a.slack.posted.length === 3
      && !a.slack.posted.some((x) => /MASTER-ADDRESSED/.test(x.text))
      && /OWNER-ADDRESSED/.test(a.slack.posted[2].text)
      && a.bridge.busFerry._cursors.get('goal-a/2026-08-03a') === 56,
      { posted: a.slack.posted.map((x) => x.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-a/2026-08-03a') });

    a.bridge.stop();
  }

  // 4 — TRUNCATION at a line boundary, naming the workspace-relative source.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-b', '2026-08-03a', { backlogRows: 1 });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick(); // first sight

    const long = Array.from({ length: 400 }, (_, i) => `line ${i} ${'x'.repeat(20)}`).join('\n');
    append(file, msgRow(2, 'leader', 'owner', 'note', long));
    await a.bridge.busFerry.tick();
    const text = a.slack.posted[0].text;
    const lines = text.split('\n');
    const tail = lines[lines.length - 1];
    const lastBodyLine = lines[lines.length - 2];
    const bodyLen = text.length - text.indexOf('\n') - 1;
    check('an over-long body is truncated at a LINE boundary (last line WHOLE) with the full-text pointer',
      a.slack.posted.length === 1
      && tail === '… (truncated — full text: .rbtv/goals/goal-b/coordination/messages.md #2)'
      && bodyLen <= DEFAULT_MAX_BODY_CHARS + tail.length + 1
      && /^line \d+ x{20}$/.test(lastBodyLine),
      { bodyLen, tail, lastBodyLine, rawBodyChars: long.length });
    a.bridge.stop();
  }

  // 5 — TORN WRITE: a trailing row with no terminating newline is LEFT for the next
  //     pass, never posted half-read.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-c', '2026-08-03a', { backlogRows: 1 });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();

    fs.appendFileSync(file, '## 2 | from: leader | to: owner | type: note | 2026-08-06 14:23\n\nhalf-writ');
    await a.bridge.busFerry.tick();
    check('a torn trailing row (no terminating newline) is NOT posted',
      a.slack.posted.length === 0 && a.bridge.busFerry._cursors.get('goal-c/2026-08-03a') === 1,
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
    b.bridge.busFerry._cursors.set('goal-c/2026-08-03a', 2); // pretend we already saw the run
    fs.appendFileSync(file, '## not-a-header at all\n\njunk\n\n');
    fs.appendFileSync(file, msgRow(3, 'leader', 'owner', 'note', 'after the junk'));
    fs.appendFileSync(file, '## also not a header\n\nmore junk\n\n');
    fs.appendFileSync(file, msgRow(4, 'leader', 'owner', 'note', 'after more junk'));
    await b.bridge.busFerry.tick();
    const warns = logs.filter((l) => l.level === 'warn' && /malformed/.test(l.message));
    const debugs = logs.filter((l) => l.level === 'debug' && /malformed/.test(l.message));
    check('malformed headers are skipped, the surrounding rows still ferry, and the warn fires ONCE (the rest at debug)',
      a.slack.posted.length === 3 && warns.length === 1 && debugs.length === 1,
      { posted: a.slack.posted.length, warns: warns.length, debugs: debugs.length });

    // The header grammar is ADDITIVE — coord.py inserts `from-pkg:` BETWEEN `from:` and
    // `to:`. A positional parser reads such a row as malformed and drops it, which is a
    // SILENT loss of exactly the cross-package send the ferry exists for. Observed live
    // on build-core-daemon-mvp/run-3 #2366. `re:`/`why:` ride along to hold the tail too.
    fs.appendFileSync(file,
      '## 5 | from: fixture-seat-a | from-pkg: throwaway-fixture | to: owner | type: completion'
      + ' | re: 3 | why: the cross-package answer | 2026-08-06 14:23\n\nfrom outside the package\n\n');
    await b.bridge.busFerry.tick();
    // Assert on THIS line, not on a count: the two junk headers above stay in the file and
    // are re-reported on every re-read pass, so a delta count is not the discriminator.
    const pkgMalformed = logs.filter((l) => /malformed/.test(l.message) && /from-pkg/.test(String(l.line)));
    check('a header carrying the OPTIONAL from-pkg/re/why fields parses and ferries — not dropped as malformed',
      a.slack.posted.length === 4 && pkgMalformed.length === 0
      && a.slack.posted[3].text === '*bus → you* — goal-c/2026-08-03a · from fixture-seat-a · completion · #5\nfrom outside the package',
      { posted: a.slack.posted.length, pkgMalformed: pkgMalformed.length, text: a.slack.posted[3] && a.slack.posted[3].text });
    a.bridge.stop(); b.bridge.stop();
  }

  // 6 — DELIVERY FAILURE: retried, order preserved, then skipped at the cap with a loud
  //     log — the ferry never wedges behind one undeliverable row.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-d', '2026-08-03a', { backlogRows: 1 });
    const logs = [];
    const slack = makeFakeSlack();
    const a = makeBridge({ workspaceRoot: root, logs, slack, busFerryOptions: { maxAttempts: 3 } });
    await a.bridge.start();
    await a.bridge.busFerry.tick();

    append(file, msgRow(2, 'leader', 'owner', 'note', 'the poisoned row'));
    append(file, msgRow(3, 'leader', 'owner', 'note', 'the row behind it'));
    slack.failNextPosts(100);
    await a.bridge.busFerry.tick();
    await a.bridge.busFerry.tick();
    check('a failed post is retried and does NOT advance the cursor, and row 3 does not jump the queue',
      slack.posted.length === 0 && a.bridge.busFerry._cursors.get('goal-d/2026-08-03a') === 1,
      { posted: slack.posted.length, cursor: a.bridge.busFerry._cursors.get('goal-d/2026-08-03a') });

    await a.bridge.busFerry.tick(); // 3rd attempt == cap
    const gaveUp = logs.filter((l) => l.level === 'warn' && /giving up/.test(l.message));
    check('at the attempt cap the row is SKIPPED loudly and the cursor advances past it',
      gaveUp.length === 1 && a.bridge.busFerry._cursors.get('goal-d/2026-08-03a') === 2,
      { gaveUp: gaveUp.length, cursor: a.bridge.busFerry._cursors.get('goal-d/2026-08-03a') });

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
    const { file } = seedGoal(root, 'goal-e', '2026-08-03a', { backlogRows: 20 });
    const a = makeBridge({ workspaceRoot: root, stateFile });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(21, 'leader', 'owner', 'note', 'delivered before the restart'));
    await a.bridge.busFerry.tick();
    a.bridge.stop();
    check('pre-restart: one row ferried, cursor persisted to the state file',
      a.slack.posted.length === 1
      && JSON.parse(fs.readFileSync(stateFile, 'utf8')).busFerry.cursors['goal-e/2026-08-03a'] === 21,
      { posted: a.slack.posted.length, doc: JSON.parse(fs.readFileSync(stateFile, 'utf8')).busFerry });

    const b = makeBridge({ workspaceRoot: root, stateFile });
    check('the restarted bridge holds NO cursors before start()', b.bridge.busFerry._cursors.size === 0, {});
    await b.bridge.start();
    check('start() restored the ferry cursor from disk',
      b.bridge.busFerry._cursors.get('goal-e/2026-08-03a') === 21, { cursor: b.bridge.busFerry._cursors.get('goal-e/2026-08-03a') });
    await b.bridge.busFerry.tick();
    check('AFTER A RESTART nothing is re-posted — no double-post, no re-flood of the 20-row backlog',
      b.slack.posted.length === 0, { posted: b.slack.posted.length });

    append(file, msgRow(22, 'leader', 'owner', 'note', 'after the restart'));
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

  // 8 — 7.607 E3: THE CURSOR IS KEYED BY EXECUTION STAMP, so a goal's NEXT execution is a FIRST
  //     SIGHT and its predecessor's rows are never replayed.
  //
  //     ⚠ THIS ARM REPLACES "a CLOSED run is never enumerated", whose subject the extinguishment
  //     deleted: there is no `state=closed` row to read and the ferry visits every goal that has a
  //     coordination bus. What the old arm actually protected was the owner's inbox against a
  //     goal's history arriving twice — and THAT property now lives in the key. Measured here
  //     rather than asserted: same file, same rows, a new stamp, and the count of posts is the
  //     discriminator.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-f', '2026-08-03a', { backlogRows: 1 });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();                 // FIRST SIGHT under stamp `a` — cursor at tail
    append(file, msgRow(2, 'leader', 'owner', 'note', 'the first execution says something'));
    await a.bridge.busFerry.tick();
    const firstPosts = a.slack.posted.length;
    check('execution 1: the row appended after first sight IS ferried, under the stamped key',
      firstPosts === 1 && a.bridge.busFerry._cursors.get('goal-f/2026-08-03a') === 2,
      { posted: firstPosts, cursors: [...a.bridge.busFerry._cursors.entries()] });

    // THE NEXT EXECUTION of the same goal: the marker advances, the append-only log does NOT
    // reset (design-lock item 5 — "files stay single and append-only").
    fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goal-f', 'coordination', 'execution'),
      '2026-08-03b\n');
    await a.bridge.busFerry.tick();
    check('7.607 E3: a NEW execution stamp is a FIRST SIGHT — the previous execution\'s rows are '
      + 'NOT replayed to the owner, and the new key seeds at the tail',
      a.slack.posted.length === firstPosts
      && a.bridge.busFerry._cursors.get('goal-f/2026-08-03b') === 2
      && a.bridge.busFerry._cursors.get('goal-f/2026-08-03a') === 2,
      { posted: a.slack.posted.length, cursors: [...a.bridge.busFerry._cursors.entries()] });

    // AND IT IS NOT A MUTE: a row appended UNDER the new stamp travels. Without this the arm
    // above passes on a ferry that stopped working entirely.
    append(file, msgRow(3, 'leader', 'owner', 'note', 'the second execution speaks'));
    await a.bridge.busFerry.tick();
    check('7.607 E3 CONTROL: a row appended under the NEW stamp IS ferried — the re-key protects '
      + 'against replay, it does not mute the goal',
      a.slack.posted.length === firstPosts + 1
      && /the second execution speaks/.test(a.slack.posted[a.slack.posted.length - 1].text)
      && a.bridge.busFerry._cursors.get('goal-f/2026-08-03b') === 3,
      { posted: a.slack.posted.map((x) => x.text.split('\n')[0]) });
    a.bridge.stop();
  }

  // 9 — DISABLED / FAIL-CLOSED. Off by default; on without `workspace_root` or without a
  //     resolvable DM it says so LOUDLY and stays off — the bridge is otherwise fine.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-g', '2026-08-03a', { backlogRows: 1 });
    append(file, msgRow(2, 'leader', 'owner', 'note', 'should never be ferried'));

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

  // 11 — THE DM LEG MINTS NOTHING (owner ruling 2026-08-12). The arm that stood here asserted
  //      the opposite: a channel-less goal's row reached the DM and that post's own thread was
  //      MINTED as a channel-master sitting with the row as its prompt. Both halves are gone —
  //      the fallback (bus-ferry.js) and the mint (chat-bridge.js `routeBusRowToMaster`) — because
  //      together they had the channel master ANSWER a question an agent addressed to the human
  //      (`meeting-digest`, 02:13 UTC). What a channel-less goal does now is measured in
  //      `probe-chat-agent-thread` arm 5, which owns every routing-surface claim; what is measured
  //      HERE is only that the DM leg, when it is the one that runs, seats nobody.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-s', '2026-08-03a', { backlogRows: 1 });
    const forwards = [];
    const spyForwarder = {
      async forward(intent, payload) { forwards.push({ intent, payload }); return { ok: true, result: { jobId: 7 } }; },
      async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
    };
    const slack2 = makeFakeSlack();
    const b2 = buildBridge({
      gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch',
      sessionProfile: 'p', sendMessageJobId: 'send-message', workdir: null,
      workspaceRoot: root, channelPrefix: 'test-', stateFile: null, busFerry: true,
      busFerryDmUser: USER, allowlist: [USER],
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, {
      logger: () => {}, makeTransport: () => slack2, forwarderImpl: spyForwarder,
      replyLegOptions: { pollMs: 3600000 },
      busFerryOptions: { pollMs: 3600000, routeToAgentThread: null },
    });
    await b2.bridge.start();
    await b2.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'the owner-review doc is ready'));
    await b2.bridge.busFerry.tick();
    check('the DM leg posts the row VERBATIM and mints NOTHING — no session-create rides a bare owner-addressed row any more',
      slack2.posted.length === 1
      && slack2.posted[0].text === '*bus \u2192 you* \u2014 goal-s/2026-08-03a \u00b7 from leader \u00b7 note \u00b7 #2\nthe owner-review doc is ready'
      && forwards.length === 0,
      { posted: slack2.posted.map((p) => p.text.split('\n')[0]), forwards: forwards.map((f) => f.payload && f.payload.job_id) });
    b2.bridge.stop();
  }

  // 9 (7.546) — BORN-WATCHED. The first-sight rule protects a run's HISTORY, and a run this
  //     process watched be born has none: it was enumerated open while its messages.md did not
  //     exist yet. Seeding at the tail there swallowed exactly one row — a newly scaffolded
  //     goal's FIRST escalation, raised by a planning seat in a run that rosters no authority
  //     seat to read it. Measured 0-delivered before this change.
  {
    const root = mkroot();
    // Birth order byte for byte, as `materialize-seats.py` births a package: `coordination/` is
    // created EMPTY with its execution marker — no messages.md until somebody writes.
    const goalDir = path.join(root, '.rbtv', 'goals', 'goal-newborn');
    fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'coordination', 'execution'), '2026-08-08a\n');
    // Both gates open — this arm is about the BIRTH observation, not the gate (see SENDERS).
    fs.writeFileSync(path.join(goalDir, 'execution-mode'), 'interactive\n');
    writeSeatDescriptor(goalDir, 'planning-strategist');
    // THE CONTROL, in the same workspace and the same passes: a second run that already HAS a
    // 40-row backlog. The flood rule must be untouched for it — the exception is "we watched it
    // be born", never "the ferry started recently".
    const { file: oldFile } = seedGoal(root, 'goal-elderly', '2026-08-03a', { backlogRows: 40 });

    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();               // the birth observation
    check('7.546: a run enumerated open with NO messages.md yet takes no cursor on that pass, while a run that HAS one is seeded at its tail on the same pass',
      a.bridge.busFerry._cursors.has('goal-newborn/2026-08-08a') === false
      && a.bridge.busFerry._cursors.get('goal-elderly/2026-08-03a') === 40,
      { cursors: [...a.bridge.busFerry._cursors.entries()] });

    fs.writeFileSync(path.join(goalDir, 'coordination', 'messages.md'),
      '# messages — append-only coordination log (script-managed, do not edit by hand)\n\n'
      + msgRow(1, 'planning-strategist', 'owner', 'note', 'ESCALATION: this run rosters no authority seat'));
    await a.bridge.busFerry.tick();
    check("7.546 BORN-WATCHED: the newborn run's FIRST row IS ferried, on the very pass that first reads it — not held for a second message that may never come",
      a.slack.posted.length === 1 && /ESCALATION/.test(a.slack.posted[0].text)
      && a.bridge.busFerry._cursors.get('goal-newborn/2026-08-08a') === 1,
      { posted: a.slack.posted.map((p) => p.text.slice(0, 70)),
        cursor: a.bridge.busFerry._cursors.get('goal-newborn/2026-08-08a') });

    append(oldFile, msgRow(41, 'leader', 'owner', 'note', 'the elderly run keeps the tail rule'));
    await a.bridge.busFerry.tick();
    check('7.546 CONTROL: the run that was NOT watched being born still ferries nothing of its 40-row backlog — only the row appended after first sight travels',
      a.slack.posted.length === 2 && /#41/.test(a.slack.posted[1].text)
      && !a.slack.posted.some((p) => /historical row/.test(p.text)),
      { posted: a.slack.posted.map((p) => p.text.split('\n')[0]) });
    a.bridge.stop();
  }

  // 12 — THE WATCH, AND THE `[deliver:]` DISPOSITION AT A NAMED THREAD (live-session-design.md
  //      §2 and §3).
  //
  //      ⚑ THE POLL IS AN HOUR AWAY IN THIS FIXTURE, SO EVERY DELIVERY BELOW IS WATCH-DRIVEN.
  //      That is the whole red/green: remove the `fs.watch` block from bus-ferry.js and nothing
  //      here is ever triggered — the waits time out and all four checks red. No arm above can
  //      say that, because every one of them drives `tick()` by hand.
  //
  //      ⚑ AND THE CONTROL AT THE END IS THE ONE THAT PROTECTS A RULING. A row with NO
  //      `[deliver:]` token must still MINT and post nothing (2026-08-07, a seat answering the
  //      owner). If the disposition were made the default instead of an opt-in, that check reds.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w', '2026-08-03a', { backlogRows: 1 });
    const forwards = [];
    const spy = {
      async forward(intent, payload) { forwards.push({ intent, payload }); return { ok: true, result: { jobId: 9 } }; },
      async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
    };
    const creates = () => forwards.filter((f) => f.payload && f.payload.job_id === 'chat-launch').length;
    const waitFor = async (fn, ms = 5000) => {
      const until = nowMs() + ms;
      while (nowMs() < until) { if (fn()) return true; await new Promise((r) => setTimeout(r, 10)); }
      return fn();
    };
    const slack = makeFakeSlack();
    const b = buildBridge({
      gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch',
      sessionProfile: 'p', sendMessageJobId: 'send-message', workdir: null,
      workspaceRoot: root, channelPrefix: 'test-', stateFile: null, busFerry: true,
      busFerryDmUser: USER, allowlist: [USER],
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, {
      logger: () => {}, makeTransport: () => slack, forwarderImpl: spy,
      replyLegOptions: { pollMs: 3600000 },
      // The agent-thread leg unwired, `makeBridge`'s reason verbatim: this arm measures the WATCH
      // and the `[deliver:]` disposition at a named thread, and its first row is a plain DM post
      // whose `ts` the three token rows below address.
      busFerryOptions: { pollMs: 3600000, watchDebounceMs: 50, routeToAgentThread: null },
    });
    await b.bridge.start();
    check('start() arms a watcher on the goals root AND on the goal\'s coordination dir',
      b.bridge.busFerry.watching >= 2, { watching: b.bridge.busFerry.watching });

    // First sight by hand — its rule (cursor at tail, ferry nothing) is arm 1's subject, not this
    // arm's, and driving it explicitly keeps the measurement below about the TRIGGER alone.
    await b.bridge.busFerry.tick();

    const t = nowMs();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'watch-triggered, no poll in sight'));
    const delivered = await waitFor(() => slack.posted.length === 1);
    const watchMs = nowMs() - t;
    check('THE WATCH ALONE TRIGGERS THE PASS — a row appended with the poll an hour away is ferried in well under a second',
      delivered && watchMs < 1000, { watchMs, posted: slack.posted.length, pollMs: 3600000 });

    // That DM post minted the conversation `<DM>:1.0`, so the bridge KNOWS the thread and the
    // three rows below are routed rather than ignored (`knowsThread`, S-13).
    const known = `${DM}:1.0`;
    const before = creates();

    append(file, msgRow(3, 'master-profile', 'owner', 'note',
      `*master profile changed* - kimi -> claude-haiku\n\n[chat-thread: ${known}] [deliver: post]`));
    const postedOutcome = await waitFor(() => slack.posted.length === 2);
    const p2 = slack.posted[1];
    check('`deliver: post` — the settled outcome is POSTED into its own thread and NO sitting is minted',
      postedOutcome && p2.channel === DM && p2.threadTs === '1.0' && creates() === before
      && /master profile changed/.test(p2.text),
      { channel: p2 && p2.channel, threadTs: p2 && p2.threadTs, creates: creates(), before });

    append(file, msgRow(4, 'some-job', 'owner', 'note',
      `the reindex finished with 3 repairs\n\n[chat-thread: ${known}] [deliver: wake]`));
    const wokeUp = await waitFor(() => slack.posted.length === 3 && creates() === before + 1);
    const p3 = slack.posted[2];
    // Defensively read, because this line runs on the FAILING path too: with the watch mutated
    // away nothing is minted, and a probe that THROWS instead of failing its check reports the
    // mutation as a crash rather than as the red it is.
    const lastCreate = forwards.filter((f) => f.payload && f.payload.job_id === 'chat-launch').pop();
    const wakePrompt = String((lastCreate && lastCreate.payload.args.prompt) || '');
    check('`deliver: wake` — POSTED into the thread AND a sitting minted with that same row as its prompt',
      wokeUp && p3.threadTs === '1.0' && /reindex finished/.test(p3.text) && /reindex finished/.test(wakePrompt),
      { threadTs: p3 && p3.threadTs, creates: creates(), prompt: wakePrompt.slice(0, 120) });

    append(file, msgRow(5, 'a-seat', 'owner', 'note',
      `here is the answer you asked for\n\n[chat-thread: ${known}]`));
    const minted = await waitFor(() => creates() === before + 2);
    check('CONTROL — no `[deliver:]` token keeps the 2026-08-07 ruling: the sitting is minted and NOTHING is posted',
      minted && slack.posted.length === 3,
      { creates: creates(), expected: before + 2, posted: slack.posted.length });

    b.bridge.stop();
    check('stop() closes every watcher it armed', b.bridge.busFerry.watching === 0,
      { watching: b.bridge.busFerry.watching });
  }

  // 10 — THE LIVE ROUTE'S READINESS, REPORTED AND NOT ASSERTED (was: 7.546 LIVE DESCRIPTOR).
  //
  //     ⚠ THE ARM THAT STOOD HERE ASSERTED A PROPERTY OF DELETED CODE. It required this
  //     workspace's standing correspondent to declare `relays: master`, because the ferry
  //     delivered on the ROLE WORD and coord.py admitted only the correspondent's NAME. Since
  //     `d-agents-address-owner-not-master` the ferry reads no `relays:`, consults no roster, and
  //     never carries `master` at all — so that assertion now guards nothing, and keeping it
  //     green would be the fixture-only green it was written to prevent, one level up.
  //
  //     ⚠ ITS SUCCESSOR QUESTION IS REAL BUT NOT YET ASSERTABLE. The live equivalent is "can an
  //     agent-initiated `to: owner` row reach the owner on THIS workspace", whose two on-disk
  //     halves are a goal in `interactive` mode and a seat declaring `human-interactive`. Both are
  //     registry mints the ratified design lists as OPEN FOLLOW-UPS (F-115), so on a correct
  //     deployment today both counts are legitimately ZERO — asserting on them would red the suite
  //     for work that is deliberately not done, and defaulting them to pass would be a check that
  //     cannot fail. So this arm MEASURES the live tree and files the counts as a SKIP (visible in
  //     the capture's SKIPPED_COUNT), for the reviewer to turn into an assertion the day the mints
  //     land. It reads the workspace by walking up from this file — never a path written here.
  {
    let ws = path.resolve(__dirname);
    while (ws !== path.dirname(ws) && !fs.existsSync(path.join(ws, '.rbtv', 'goals'))) ws = path.dirname(ws);
    const goalsDir = path.join(ws, '.rbtv', 'goals');
    let entries = null;
    try { entries = fs.readdirSync(goalsDir, { withFileTypes: true }); } catch {}
    const interactiveGoals = [];
    for (const d of entries || []) {
      if (!d.isDirectory()) continue;
      let mode = null;
      try { mode = fs.readFileSync(path.join(goalsDir, d.name, 'execution-mode'), 'utf8').trim().toLowerCase(); } catch { continue; }
      if (mode === 'interactive') interactiveGoals.push(d.name);
    }
    skipped.push(entries
      ? `live route readiness (NOT asserted — F-115 mints pending): goals declaring execution-mode:interactive = ${interactiveGoals.length}${interactiveGoals.length ? ' (' + interactiveGoals.join(', ') + ')' : ''}. Until a goal is flipped interactive AND its seats declare human-interactive, every agent-initiated to:owner row on this workspace PARKS by ratified default — which is correct, not a defect.`
      : `live route readiness: no readable goals tree at ${goalsDir} — this checkout has no workspace around it.`);
    cap.log({ skip: skipped[skipped.length - 1], goalsDir, interactiveGoals });
  }

  for (const r of roots) { try { fs.rmSync(r, { recursive: true, force: true }); } catch {} }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-bus-ferry', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: skipped.length, skipped });
  process.stdout.write(`PROBE probe-chat-bus-ferry EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();

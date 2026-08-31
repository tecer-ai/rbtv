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
const { DEFAULT_MAX_BODY_CHARS, FINISH_MARKER: busFerryFinishMarker } = require('../bus-ferry');
const { IRREVERSIBLE_PHRASE, APPROVAL_TOKEN_LINE } = require('../approval-thread');

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

// The narrow channel-admin surface `index.js` gates `goalChannels` on (`typeof
// transport.createChannel === 'function'`), bolted onto the DM fake above. SEPARATE, never a
// widening of `makeFakeSlack`: the 54 checks above measure the ferry's DM leg and are wired
// against a bridge with NO goal-channel map — giving the shared fake this surface would switch
// that map on underneath every one of them.
function makeChannelSlack() {
  const base = makeFakeSlack();
  const channels = [];
  let nextId = 1;
  return Object.assign(base, {
    channels,
    async createChannel({ name }) {
      const ch = { id: `C${String(nextId++).padStart(4, '0')}`, name };
      channels.push(ch);
      return { ok: true, channel: { id: ch.id, name: ch.name } };
    },
    async listChannels() { return { ok: true, channels: channels.map((c) => ({ id: c.id, name: c.name })), nextCursor: null }; },
    async archiveChannel() { return { ok: true }; },
  });
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

function writeSeatDescriptor(runDir, seat, { humanInteractive = true, goalWrites = [] } = {}) {
  const dir = path.join(runDir, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'),
    `---\nseat: ${seat}\n${humanInteractive ? 'human-interactive: yes\n' : ''}`
    + `${goalWrites.length ? `goal-writes:\n${goalWrites.map((w) => `- ${w}\n`).join('')}` : ''}`
    + `---\nbody\n`);
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

  // 6b — W8 (adv, C76): THE ESCALATION TRANSPORT CONTRACT. Three arms, each of which fails on a
  //      naive `if (row.type === 'escalation') deliver()` branch bolted onto the gate ladder.
  {
    // W8-A — NO GATE LEFT TO BYPASS [D24, T2-R17, D-7-ruling]. This arm used to pin that an
    // `escalation` cleared two gates a plain `note` could not: an AUTONOMOUS goal whose seat is
    // NOT `human-interactive`, with the note PARKING as the control. Both gates are DELETED —
    // goal-level interactive mode is dead and a non-interact seat's work-content question is a
    // daemon-posted ask, never a swallowed row — so the discriminating fixture now measures the
    // opposite claim, which is the one the redesign asserts: on the WORST fixture the old ladder
    // had, BOTH rows travel, the cursor sweeps both, and nothing is parked.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8a', '2026-08-14a',
      { backlogRows: 1, executionMode: 'autonomous', senders: [] });
    writeSeatDescriptor(path.join(root, '.rbtv', 'goals', 'goal-w8a'), 'leader', { humanInteractive: false });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'an ordinary word to the human'));
    append(file, msgRow(3, 'leader', 'owner', 'escalation', 'nobody in this run can clear this'));
    await a.bridge.busFerry.tick();
    check('W8-A: on an AUTONOMOUS goal with a NON-human-interactive seat — the fixture both deleted '
      + 'gates used to shut — the `escalation` AND the same seat\'s `note` both TRAVEL, and the '
      + 'cursor sweeps both: no row is parked [D24, T2-R17]',
      a.slack.posted.length === 2 && /#2/.test(a.slack.posted[0].text) && /#3/.test(a.slack.posted[1].text)
      && a.bridge.busFerry._cursors.get('goal-w8a/2026-08-14a') === 3,
      { posted: a.slack.posted.map((p) => p.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-w8a/2026-08-14a') });
    a.bridge.stop();
  }
  {
    // W8-B — THE HEAD-OF-LINE JUMP. Section 6 pins that an ordinary row does NOT jump a stuck one;
    // this pins that an escalation DOES, that the cursor does not lie about it (it may not advance
    // over the undelivered row), and that when the stuck row finally posts the escalation is NOT
    // delivered a second time — which is the whole reason `jumped` exists.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8b', '2026-08-14a', { backlogRows: 1 });
    const slack = makeFakeSlack();
    const a = makeBridge({ workspaceRoot: root, slack, busFerryOptions: { maxAttempts: 5 } });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'the poisoned row'));
    append(file, msgRow(3, 'leader', 'owner', 'escalation', 'the halt behind it'));
    slack.failNextPosts(1);                       // row 2 fails; row 3 meets a working transport
    await a.bridge.busFerry.tick();
    check('W8-B: an `escalation` JUMPS a row that is still failing to post, and the cursor stays '
      + 'on the undelivered row rather than claiming it travelled',
      slack.posted.length === 1 && /#3/.test(slack.posted[0].text)
      && a.bridge.busFerry._cursors.get('goal-w8b/2026-08-14a') === 1
      && a.bridge.busFerry._jumped.has('goal-w8b/2026-08-14a#3'),
      { posted: slack.posted.map((p) => p.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-w8b/2026-08-14a'), jumped: [...a.bridge.busFerry._jumped] });
    await a.bridge.busFerry.tick();
    check('W8-B: once the stuck row posts, the cursor sweeps past the jumped escalation WITHOUT '
      + 'delivering it twice, and the jump record is dropped',
      slack.posted.length === 2 && /#2/.test(slack.posted[1].text)
      && a.bridge.busFerry._cursors.get('goal-w8b/2026-08-14a') === 3
      && a.bridge.busFerry._jumped.size === 0,
      { posted: slack.posted.map((p) => p.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-w8b/2026-08-14a'), jumped: [...a.bridge.busFerry._jumped] });
    a.bridge.stop();
  }
  {
    // W8-C — NEVER ABANDONED SILENTLY. At the attempt cap every other row leaves a `giving up`
    // warn line and nothing else; an escalation leaves the owner a CONTENT-BEARING notice on the
    // transport directly, because there is no retry behind it to carry the words later.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8c', '2026-08-14a', { backlogRows: 1 });
    const slack = makeFakeSlack();
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, slack, logs, busFerryOptions: { maxAttempts: 1 } });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'escalation', 'the cage refuses the path and I cannot widen it'));
    slack.failNextPosts(1);                       // the row's own post fails; the notice's does not
    await a.bridge.busFerry.tick();
    check('W8-C: an `escalation` abandoned at the attempt cap still reaches the owner — a direct '
      + 'transport notice CARRYING ITS TEXT, not the bare "giving up" line every other row gets',
      slack.posted.length === 1 && /ESCALATION from \*leader\*/.test(slack.posted[0].text)
      && /cage refuses the path/.test(slack.posted[0].text)
      && logs.some((l) => l.level === 'warn' && /could not post an ESCALATION/.test(l.message)),
      { posted: slack.posted.map((p) => p.text.split('\n')[0]) });
    // ONE outcome per msgId. The delivery line used to be followed IMMEDIATELY by
    // `NOT delivered, cursor advanced` for the SAME row — and `NOT delivered` is what an
    // operator greps, so the log contradicted itself about whether the owner was reached.
    check('W8-C: the cap leaves ONE outcome for the msgId — no `NOT delivered` line for a row the '
      + 'content-bearing DM path DID deliver',
      logs.filter((l) => /NOT delivered/.test(l.message)).length === 0,
      { contradicting: logs.filter((l) => /NOT delivered/.test(l.message)).map((l) => l.message) });
    a.bridge.stop();
  }

  {
    // W8-D — THE REFUSAL AT THE ASK DOOR IS TERMINAL, AND THE ESCALATION'S DM IS TAKEN ON THE
    // FIRST PASS. Observed live 2026-08-27 19:36-19:37Z: `leader`'s escalation #12 produced
    // TWENTY `owner-ask REFUSED — this seat is not designated to reach the owner [T2-R14]` lines
    // and only then the content-bearing DM. Nothing about that refusal can change between passes
    // — it reads the seat's own descriptor — so every one of the twenty was the same answer.
    //
    // The ask door itself is STUBBED here, and deliberately: this arm measures the FERRY's
    // handling of the refusal, which is where the defect lived. That the real door refuses a
    // non-`human-interactive` seat with exactly this reason is pinned one probe over
    // (`probe-chat-ask-release.js:119`), so the stub restates a measured fact rather than
    // inventing a convenient one.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8d', '2026-08-14a', { backlogRows: 1 });
    writeSeatDescriptor(path.join(root, '.rbtv', 'goals', 'goal-w8d'), 'leader', { humanInteractive: false });
    const slack = makeFakeSlack();
    const logs = [];
    const askCalls = [];
    const a = makeBridge({
      workspaceRoot: root, slack, logs,
      busFerryOptions: { postAsk: async (args) => { askCalls.push(args); return { posted: false, reason: 'seat-not-interact' }; } },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'escalation', 'nobody in this run can clear this halt'));
    await a.bridge.busFerry.tick();
    check('W8-D: an `escalation` the ask door REFUSES [T2-R14] reaches the owner on the FIRST pass '
      + '— one ask attempt, one content-bearing DM, no retry storm',
      askCalls.length === 1 && slack.posted.length === 1
      && /ESCALATION from \*leader\*/.test(slack.posted[0].text)
      && /not designated to reach the owner \[T2-R14\]/.test(slack.posted[0].text)
      && /nobody in this run can clear this halt/.test(slack.posted[0].text),
      { askCalls: askCalls.length, posted: slack.posted.map((p) => p.text.split('\n')[0]) });
    check('W8-D: the refusal is TERMINAL — the row leaves no retry attempt behind it and the '
      + 'cursor advances on that same first pass',
      a.bridge.busFerry._cursors.get('goal-w8d/2026-08-14a') === 2
      && a.bridge.busFerry._attempts.size === 0,
      { cursor: a.bridge.busFerry._cursors.get('goal-w8d/2026-08-14a'), attempts: [...a.bridge.busFerry._attempts.keys()] });
    check('W8-D: ONE refusal line in the log, not twenty, and no `will retry next pass` for a '
      + 'refusal that cannot change between passes',
      logs.filter((l) => /REFUSED at the ask door/.test(l.message)).length === 1
      && logs.filter((l) => /will retry next pass/.test(l.message)).length === 0
      && logs.filter((l) => /NOT delivered/.test(l.message)).length === 0,
      {
        refusals: logs.filter((l) => /REFUSED at the ask door/.test(l.message)).length,
        retries: logs.filter((l) => /will retry next pass/.test(l.message)).length,
      });
    // A further pass must not re-deliver it: the cursor, not the attempt counter, is what holds.
    await a.bridge.busFerry.tick();
    check('W8-D: a later pass does NOT deliver the refused escalation a second time',
      slack.posted.length === 1, { posted: slack.posted.length });
    a.bridge.stop();
  }
  {
    // W8-E — REPLACES THE OLD "silent terminal refusal" CLAIM (`d-escalation-surface` part 7,
    // seat `esc-door-split`). BEFORE: `posted: false` for a `note` from a non-designated seat
    // meant the row posted NOTHING anywhere — the exact silent-discard class the ruling exists to
    // end (measured: the daemon's own seed-refusal notice could never post). AFTER: [T2-R14]
    // still refuses the ASK — the row never becomes a blocking record — but the SAME door rescues
    // it as a 💭 NOTICE (`marker: 'note'` → `ask-thread.js#postNote`, which never checks [T2-R14]
    // at all). The stub answers the first call (default `marker`) with the door's real refusal and
    // the second (`marker: 'note'`) with a success, exactly as the real two-function door behaves.
    //
    // Was (quoted verbatim, pre-fix): "an ordinary row refused at the ask door posts NOTHING, is
    // reported once, and is not retried" — asserted `slack.posted.length === 0` with no notice leg
    // at all, because none existed.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8e', '2026-08-14a', { backlogRows: 1 });
    const slack = makeFakeSlack();
    const logs = [];
    const askCalls = [];
    const a = makeBridge({
      workspaceRoot: root, slack, logs,
      busFerryOptions: {
        postAsk: async (args) => {
          askCalls.push(args);
          if (args.marker === 'note') return { posted: true, threadTs: 'T-NOTE-1', text: 'stub-note-text' };
          return { posted: false, reason: 'seat-not-interact' };
        },
      },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'an ordinary word to the human'));
    await a.bridge.busFerry.tick();
    check('W8-E: an ordinary row refused at the ask door [T2-R14] is RESCUED as a 💭 notice — the '
      + 'door is called TWICE (ask, then note), the row leaves no DM post and no retry attempt, and '
      + 'the cursor advances on the first pass',
      askCalls.length === 2 && askCalls[0].marker === undefined && askCalls[1].marker === 'note'
      && slack.posted.length === 0
      && a.bridge.busFerry._cursors.get('goal-w8e/2026-08-14a') === 2
      && a.bridge.busFerry._attempts.size === 0
      && logs.filter((l) => /rescued as a 💭 notice/.test(l.message)).length === 1
      && logs.filter((l) => /REFUSED at the ask door/.test(l.message)).length === 0
      && logs.filter((l) => /will retry next pass/.test(l.message)).length === 0,
      {
        askCalls: askCalls.map((c) => c.marker || 'ask'),
        posted: slack.posted.length,
        cursor: a.bridge.busFerry._cursors.get('goal-w8e/2026-08-14a'),
        attempts: [...a.bridge.busFerry._attempts.keys()],
      });
    a.bridge.stop();
  }
  {
    // W8-F — d-escalation-surface part 7, cont.: WHEN THE NOTICE ATTEMPT ALSO FAILS, THE ROW IS
    // NEVER SILENTLY DROPPED EITHER — it is an ORDINARY post failure at that point (the [T2-R14]
    // refusal is already resolved) and falls through to the SAME retry ladder any other undelivered
    // row uses. Measured here via the DM fallback leg (unwired `routeToAgentThread`, no goal
    // channel in this fixture's fake Slack) actually firing on the first pass.
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-w8f', '2026-08-14a', { backlogRows: 1 });
    const slack = makeFakeSlack();
    const logs = [];
    const a = makeBridge({
      workspaceRoot: root, slack, logs,
      busFerryOptions: { postAsk: async () => ({ posted: false, reason: 'seat-not-interact' }) },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'note', 'an ordinary word to the human'));
    await a.bridge.busFerry.tick();
    check('W8-F: a row whose NOTICE attempt also fails is not a terminal refusal — it falls through '
      + 'to the ordinary DM leg on the same pass rather than being dropped',
      slack.posted.length === 1 && /an ordinary word to the human/.test(slack.posted[0].text)
      && a.bridge.busFerry._cursors.get('goal-w8f/2026-08-14a') === 2,
      { posted: slack.posted.map((p) => p.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-w8f/2026-08-14a') });
    a.bridge.stop();
  }

  // W10 — ONE OPEN ESCALATION PER GOAL (`d-escalation-surface` part 8, seat `esc-one-at-a-time`).
  //       On 2026-08-31 one goal raised three blocking escalations in seventeen minutes and the
  //       second withdrew a claim the first had made; three open threads at once would have let
  //       the owner rule on retracted evidence. A tiny stand-in for the daemon's `open_asks` table
  //       — a plain array, read fresh by `listOpenAsks` on every call, exactly the shape
  //       `ask-store.js#listOpenAsks` -> `state-store/heart/ask-record.js#listOpenAsks` returns
  //       (`{ goal, one_liner }`, among other fields this gate does not read) — proves the gate
  //       reads PERSISTED state on every pass rather than caching a bridge-local flag.
  // A tiny stand-in for the daemon's `open_asks` table — a plain array, read fresh by
  // `listOpenAsks` on every call, exactly the shape `ask-store.js#listOpenAsks` ->
  // `state-store/heart/ask-record.js#listOpenAsks` returns (`{ goal, one_liner }`, among other
  // fields this gate does not read) — proves the gate reads PERSISTED state on every pass rather
  // than caching a bridge-local flag. `postAsk` mints THROUGH THIS TABLE, never through the fake
  // Slack transport — exactly like the real `ask-thread.js#postAsk` leg, which never calls
  // `transport.sendToOwner` on success (`res = { delivered: true, ts: asked.askId }` is set
  // directly). `calls` is every invocation in arrival order, successful or not, which is what lets
  // an assertion prove ORDER without `slack.posted` standing in for a leg it never rides.
  function makeOpenAsksTable() {
    const rows = []; // { goal, one_liner, state: 'open'|'closed', askId }
    const calls = []; // { goalId, body, posted }
    let failNext = 0; // opt-in: fail the next N postAsk calls (a transient mint failure)
    return {
      rows, calls,
      failNextPosts(n = 1) { failNext = n; },
      postAsk: async (args) => {
        if (failNext > 0) {
          failNext -= 1;
          calls.push({ goalId: args.goalId, body: args.body, posted: false });
          return { posted: false, reason: 'transient' };
        }
        const oneLiner = String(args.body || '').split('\n').find((l) => l.trim() !== '') || '';
        const askId = `ask-${rows.length + 1}`;
        rows.push({ goal: args.goalId, one_liner: oneLiner, state: 'open', askId });
        calls.push({ goalId: args.goalId, body: args.body, posted: true, askId });
        return { posted: true, askId, text: args.body };
      },
      listOpenAsks: async () => rows.filter((r) => r.state === 'open').map((r) => ({ goal: r.goal, one_liner: r.one_liner })),
      close(askId) { const r = rows.find((x) => x.askId === askId); if (r) r.state = 'closed'; },
      countOpen(goal) { return rows.filter((r) => r.goal === goal && r.state === 'open').length; },
      minted() { return calls.filter((c) => c.posted); }, // successful mints, arrival order
    };
  }
  {
    // W10-RED — on the CURRENT (unwired) gate, three escalations from one goal all post as open
    // threads simultaneously — `listOpenAsks` is simply not passed, the documented no-op default.
    const root = mkroot();
    const GOAL = 'goal-w10-red';
    const { file } = seedGoal(root, GOAL, '2026-08-31a', { backlogRows: 1 });
    const table = makeOpenAsksTable();
    const a = makeBridge({ workspaceRoot: root, busFerryOptions: { postAsk: table.postAsk } }); // listOpenAsks NOT wired
    await a.bridge.start();
    await a.bridge.busFerry.tick(); // first sight
    append(file, msgRow(2, 'leader', 'owner', 'escalation', 'I said (a) unblocks m1-m6, m8, m9'));
    append(file, msgRow(3, 'leader', 'owner', 'escalation', 'Wrong about m2 — retracting the above'));
    append(file, msgRow(4, 'leader', 'owner', 'escalation', 'a third, independent halt'));
    await a.bridge.busFerry.tick();
    check('W10-RED [DoD 1]: with the gate UNWIRED, three escalations from one goal ALL post as open '
      + 'ask threads on the SAME pass — the pre-fix defect this seat exists to close',
      table.minted().length === 3 && table.countOpen(GOAL) === 3,
      { minted: table.minted().map((c) => c.body.split('\n')[0]), openAsksCount: table.countOpen(GOAL) });
    a.bridge.stop();
  }
  {
    // W10-GREEN — the SAME fixture, `listOpenAsks` WIRED: exactly one posts, the other two are
    // HELD — not lost, not dropped, still on the bus, the cursor stopped before them.
    const root = mkroot();
    const GOAL = 'goal-w10-green';
    const KEY = `${GOAL}/2026-08-31a`;
    const { file } = seedGoal(root, GOAL, '2026-08-31a', { backlogRows: 1 });
    const table = makeOpenAsksTable();
    const logs = [];
    const a = makeBridge({
      workspaceRoot: root, logs,
      busFerryOptions: { postAsk: table.postAsk, listOpenAsks: table.listOpenAsks },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick(); // first sight, cursor -> 1
    const cursorBefore = a.bridge.busFerry._cursors.get(KEY);
    append(file, msgRow(2, 'leader', 'owner', 'escalation', 'I said (a) unblocks m1-m6, m8, m9'));
    append(file, msgRow(3, 'leader', 'owner', 'escalation', 'Wrong about m2 — retracting the above'));
    append(file, msgRow(4, 'leader', 'owner', 'escalation', 'a third, independent halt'));
    await a.bridge.busFerry.tick();
    check('W10-GREEN [DoD 2]: the SAME fixture with the gate WIRED mints EXACTLY ONE ask, and '
      + 'the `open_asks` stand-in carries exactly ONE open row for this goal — held is proven by the '
      + 'COUNT staying at one, never by an absence of an error',
      table.minted().length === 1 && /#2/.test(table.minted()[0].body) && table.countOpen(GOAL) === 1,
      { minted: table.minted().map((c) => c.body.split('\n')[0]), openAsksCount: table.countOpen(GOAL) });
    check('W10-GREEN: the HELD rows are DISTINGUISHED from a drop by a log line naming each one, '
      + 'once per held row per pass',
      logs.filter((l) => /HELD a new escalation/.test(l.message)).length === 2,
      { held: logs.filter((l) => /HELD a new escalation/.test(l.message)).map((l) => l.msgId) });
    check('W10-GREEN [DoD 3]: the cursor did NOT advance past the held escalation — row #2 (the '
      + 'one that DID post) advanced it to 2, but it stops there rather than sweeping over the '
      + 'held #3 and #4',
      cursorBefore === 1 && a.bridge.busFerry._cursors.get(KEY) === 2,
      { cursorBefore, cursorAfter: a.bridge.busFerry._cursors.get(KEY) });

    // W10-RESUME [DoD 4]: answer/close the open escalation; the SECOND posts on the next pass, and
    // the THIRD is still held behind it.
    table.close(table.rows[0].askId);
    logs.length = 0;
    await a.bridge.busFerry.tick();
    check('W10-RESUME: once the open escalation is answered (closed in `open_asks`), the SECOND '
      + 'escalation posts on the very next pass',
      table.minted().length === 2 && /#3/.test(table.minted()[1].body) && table.countOpen(GOAL) === 1,
      { minted: table.minted().map((c) => c.body.split('\n')[0]), openAsksCount: table.countOpen(GOAL) });
    check('W10-RESUME: the THIRD escalation is STILL held — one open at a time, never two — and '
      + 'the cursor advanced only over #3 (the one that just posted), stopping again before #4',
      logs.filter((l) => /HELD a new escalation/.test(l.message)).length === 1
      && a.bridge.busFerry._cursors.get(KEY) === 3,
      { held: logs.filter((l) => /HELD a new escalation/.test(l.message)).length, cursor: a.bridge.busFerry._cursors.get(KEY) });

    // Resolve the goal fully, for cleanliness of the fixture's own bookkeeping (not asserted).
    table.close(table.rows[1].askId);
    a.bridge.stop();
  }
  {
    // W10-DISCRIMINATE [DoD 5] — a goal already holding an OPEN `work-content` ask (an ORDINARY
    // owner-bound question, unrelated to any escalation) must NOT block a NEW escalation. The
    // work-content row's `one_liner` carries no ` · escalation · #` marker — the same fact
    // `isEscalationOneLiner` reads in production, off a real ask's real header — never a
    // hand-typed flag standing in for it.
    const root = mkroot();
    const GOAL = 'goal-w10-disc';
    const { file } = seedGoal(root, GOAL, '2026-08-31a', { backlogRows: 1 });
    const table = makeOpenAsksTable();
    // Seed one OPEN work-content ask directly into the stand-in table, as if a prior pass minted
    // it — its one_liner is an ordinary `formatMessage` header for a `type: ask` row.
    table.rows.push({ goal: GOAL, one_liner: `*🧵 leader* — ${GOAL} · ask · #1`, state: 'open', askId: 'ask-preexisting' });
    const a = makeBridge({
      workspaceRoot: root,
      busFerryOptions: { postAsk: table.postAsk, listOpenAsks: table.listOpenAsks },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'escalation', 'a real halt, unrelated to the open work-content ask'));
    await a.bridge.busFerry.tick();
    check('W10-DISCRIMINATE [DoD 5]: a goal holding an OPEN `work-content`-shaped ask does NOT '
      + 'block a NEW escalation — it mints on the FIRST pass',
      table.minted().length === 1 && /#2/.test(table.minted()[0].body) && table.countOpen(GOAL) === 2,
      { minted: table.minted().map((c) => c.body.split('\n')[0]), openAsksCount: table.countOpen(GOAL) });
    a.bridge.stop();
  }
  {
    // W10-JUMP-HOLD [DoD 6] — the three-way case: one OPEN escalation already on the goal, one
    // STUCK ordinary row (still failing to post), and a NEW escalation arriving behind both. The
    // new escalation clears the head-of-line jump (only an escalation walks past a stuck row) and
    // reaches the hold gate, where it is held — never posted, never deadlocking the stuck row's
    // own independent retry, and the cursor stays behind BOTH.
    const root = mkroot();
    const GOAL = 'goal-w10-jump';
    const KEY = `${GOAL}/2026-08-31a`;
    const { file } = seedGoal(root, GOAL, '2026-08-31a', { backlogRows: 1 });
    const table = makeOpenAsksTable();
    table.rows.push({ goal: GOAL, one_liner: `*🧵 leader* — ${GOAL} · escalation · #0`, state: 'open', askId: 'ask-already-open' });
    const slack = makeFakeSlack();
    const logs = [];
    const a = makeBridge({
      workspaceRoot: root, slack, logs,
      busFerryOptions: { postAsk: table.postAsk, listOpenAsks: table.listOpenAsks, maxAttempts: 5 },
    });
    await a.bridge.start();
    await a.bridge.busFerry.tick(); // first sight, cursor -> 1
    const cursorBefore = a.bridge.busFerry._cursors.get(KEY);
    append(file, msgRow(2, 'leader', 'owner', 'note', 'the poisoned ordinary row'));
    append(file, msgRow(3, 'leader', 'owner', 'escalation', 'a new halt, arriving while one is already open'));
    // row 2's mint fails (transient), and falls through to the DM leg, which also fails — genuinely
    // stuck, undelivered by any leg, exactly the fixture the head-of-line jump was built against.
    table.failNextPosts(1);
    slack.failNextPosts(1);
    await a.bridge.busFerry.tick();
    check('W10-JUMP-HOLD [DoD 6]: NOTHING new delivered anywhere — the stuck ordinary row failed as '
      + 'usual (its mint failed AND its DM fallback failed), and the new escalation was HELD (never '
      + 'even attempted) rather than jumping past the already-open escalation',
      table.minted().length === 0 && slack.posted.length === 0 && table.countOpen(GOAL) === 1,
      { minted: table.minted().length, posted: slack.posted.length, openAsksCount: table.countOpen(GOAL) });
    check('W10-JUMP-HOLD: the cursor stayed behind BOTH rows — no advance over the stuck row and '
      + 'no advance over the held escalation',
      a.bridge.busFerry._cursors.get(KEY) === cursorBefore && cursorBefore === 1,
      { cursorBefore, cursorAfter: a.bridge.busFerry._cursors.get(KEY) });
    check('W10-JUMP-HOLD: no deadlock — the held escalation is logged as HELD, not as a transport '
      + 'failure, so it is never mistaken for the silence this module exists to end',
      logs.some((l) => /HELD a new escalation/.test(l.message) && l.msgId === 3),
      { logs: logs.filter((l) => /HELD|giving up|could not post/.test(l.message)).map((l) => l.message) });
    // Now close the pre-existing open escalation — the FAILURE budget (`table.failNextPosts`) was
    // one-shot and is already spent, so this next pass is the ordinary row's own ordinary retry
    // (unrelated to this gate) succeeding at the SAME time the escalation gate clears. Both must
    // land, in order, with nothing lost.
    table.close('ask-already-open');
    await a.bridge.busFerry.tick();
    check('W10-JUMP-HOLD: once the open escalation closes, the NEXT pass mints BOTH the ordinary '
      + 'row (its own retry, now succeeding) AND the escalation that was held behind it, in order '
      + '— nothing lost',
      table.minted().length === 2
      && /the poisoned ordinary row/.test(table.minted()[0].body)
      && /#3/.test(table.minted()[1].body)
      && a.bridge.busFerry._cursors.get(KEY) === 3,
      { minted: table.minted().map((c) => c.body.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get(KEY) });
    a.bridge.stop();
  }

  // W9 — THE FINISH EDGE'S COMPLETION NOTICE [T5-R16, spec-owner-io §1]. Test 7 of the acceptance
  //      wave failed here for real: `seat-cage-tool-inventory` finished 2026-08-28 01:31Z, the
  //      finish edge fired, and NOTHING reached Slack — the row is `to: all` and this ferry
  //      carried exactly one address. The claims, in the order they can fail:
  //        · a `type: completion` row whose body OPENS with the finish marker, from the `leader`
  //          chair, posts ONE top-level message in the GOAL'S OWN CHANNEL (not a thread, not the
  //          DM) as outbox kind `completion`;
  //        · that message is exactly THREE lines — outcome, headline numbers, deliverables — and
  //          every number in line 2 is counted off the goal's own `executions.csv`;
  //        · a declared output that was never written (D21 creates them EMPTY at spawn) is NOT
  //          named a deliverable;
  //        · a SECOND pass posts nothing more;
  //        · the same marker from a NON-leader seat posts nothing and says why;
  //        · an ORDINARY `completion` — what every seat sends at check-out — posts nothing;
  //        · no ASK record is minted anywhere: a completion is a notification [T2-R16], and the
  //          ask door would suspend the kill clock on a question nobody can answer.
  {
    const root = mkroot();
    const GOAL = 'goal-fin';
    const KEY = `${GOAL}/2026-08-20a`;
    const { file } = seedGoal(root, GOAL, '2026-08-20a', { backlogRows: 1 });
    const goalDir = path.join(root, '.rbtv', 'goals', GOAL);
    // The leader declares TWO outputs; only one of them was ever written.
    writeSeatDescriptor(goalDir, 'leader', { goalWrites: ['report.md', 'never-written.md'] });
    fs.writeFileSync(path.join(goalDir, 'report.md'), 'the deliverable\n');
    fs.writeFileSync(path.join(goalDir, 'never-written.md'), '');
    // The completion authority both the daemon and the operator read — three sittings, two seats.
    fs.writeFileSync(path.join(goalDir, 'executions.csv'),
      'seat,session-id,lane,started,ended,outcome\n'
      + 'worker,s1,daemon,2026-08-20T10:00:00Z,2026-08-20T10:20:00Z,\n'
      + 'leader,s2,daemon,2026-08-20T10:05:00Z,2026-08-20T10:41:00Z,\n'
      + 'leader,s3,daemon,2026-08-20T10:50:00Z,,\n');

    const slack = makeChannelSlack();
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, slack, logs });
    // The goal's channel. `goal-channel-cli.js` is a throwaway subprocess the bridge never
    // observes, so creating it straight on the fake IS that subprocess.
    await slack.createChannel({ name: `test-${GOAL}` });
    await a.bridge.start();
    await a.bridge.busFerry.tick();          // first sight — cursor at the tail
    const beforePosts = slack.posted.length;

    const FINISH_BODY = `${busFerryFinishMarker}\n\nthe room is torn down`;
    append(file, msgRow(2, 'leader', 'all', 'completion', FINISH_BODY));
    await a.bridge.busFerry.tick();

    const channelId = a.bridge.goalChannels.channelForGoal(GOAL);
    const notices = slack.posted.filter((x) => x.channel === channelId);
    const notice = notices[0];
    const lines = notice ? notice.text.split('\n') : [];
    const rowsOut = a.bridge.outbox.query({ kind: 'completion' });

    check('W9: the finish edge posts EXACTLY ONE message, top-level in the GOAL CHANNEL — never a '
      + 'thread, never the owner DM',
      beforePosts === 0 && notices.length === 1 && notice.threadTs === null
      && slack.posted.filter((x) => x.channel === DM).length === 0,
      { posts: slack.posted.length, channel: notice && notice.channel, dmPosts: slack.posted.filter((x) => x.channel === DM).length });

    check('W9: it is ONE outbox row of kind `completion`, carrying the goal, and DELIVERED [C-17]',
      rowsOut.length === 1 && rowsOut[0].goal_id === GOAL && rowsOut[0].state === 'delivered'
      && rowsOut[0].channel_id === channelId && rowsOut[0].thread_ts === null,
      { rows: rowsOut.length, state: rowsOut[0] && rowsOut[0].state, goal: rowsOut[0] && rowsOut[0].goal_id });

    check('W9: THREE lines — line 1 names the goal, WHO fired the edge and WHEN',
      lines.length === 3 && lines[0].includes(`*${GOAL}*`) && lines[0].includes('*leader*')
      && lines[0].includes('2026-08-06 14:23') && /FINISHED/.test(lines[0]),
      { lines: lines.length, line1: lines[0] });

    check('W9: line 2 is COUNTED off the goal\'s own executions.csv — 2 seats, 3 sittings, and the '
      + 'window between the first start and the last end (41m)',
      lines[1] === '*2* seats run · *3* sittings · 41m (2026-08-20T10:00:00Z → 2026-08-20T10:41:00Z)',
      { line2: lines[1] });

    check('W9: line 3 names the deliverable that was WRITTEN and NOT the declared output that '
      + 'stayed empty — D21 creates every goal-write empty at spawn, so existence is not delivery',
      lines[2] === 'Deliverables: `report.md`', { line3: lines[2] });

    check('W9: NO ask record is minted for it — a completion is a notification, never a question '
      + 'the kill clock waits on [T2-R16]',
      a.bridge.outbox.query({ kind: 'ask' }).length === 0,
      { asks: a.bridge.outbox.query({ kind: 'ask' }).length });

    // IDEMPOTENCE — ONE MESSAGE PER FINISH. The cursor is the guard, so the claim is measured
    // both ways: an idle pass (the file unchanged, nothing re-read) and a pass that RE-READS the
    // whole file because a later row appended. The second is the one that matters — `_runOnce`
    // walks every row of `messages.md` on every size change, so a finish row that were not behind
    // the cursor would announce the same goal finished on every later append for the goal's life.
    await a.bridge.busFerry.tick();
    check('W9: an idle second pass posts nothing more, and the cursor sits ON the finish row',
      slack.posted.filter((x) => x.channel === channelId).length === 1
      && a.bridge.outbox.query({ kind: 'completion' }).length === 1
      && a.bridge.busFerry._cursors.get(KEY) === 2,
      { posts: slack.posted.filter((x) => x.channel === channelId).length, cursor: a.bridge.busFerry._cursors.get(KEY) });

    // THE NON-LEADER ARM. Nothing at `coord.py cmd_send` guards the marker, so any seat can put
    // that string in a `--type completion` body. It is WITHHELD, and the withholding is said.
    append(file, msgRow(3, 'some-worker', 'all', 'completion', FINISH_BODY));
    await a.bridge.busFerry.tick();
    check('W9: the SAME marker from a seat that is not the `leader` chair posts NOTHING, advances '
      + 'the cursor, and logs why it was withheld — and the RE-READ of the whole file this append '
      + 'forces does not re-announce the finish row behind the cursor',
      slack.posted.filter((x) => x.channel === channelId).length === 1
      && a.bridge.outbox.query({ kind: 'completion' }).length === 1
      && a.bridge.busFerry._cursors.get(KEY) === 3
      && logs.filter((l) => /NOT posted as a completion notice/.test(l.message)).length === 1,
      { posts: slack.posted.filter((x) => x.channel === channelId).length, cursor: a.bridge.busFerry._cursors.get(KEY) });

    // THE CONTROL. Every seat sends `--type completion` at check-out; the TYPE is not the event.
    append(file, msgRow(4, 'leader', 'all', 'completion', 'my briefing is complete — 12/12 pages render'));
    await a.bridge.busFerry.tick();
    check('W9 CONTROL: an ORDINARY `completion` from the leader — no marker — posts nothing; the '
      + 'finish EVENT is the marker, not the type',
      slack.posted.filter((x) => x.channel === channelId).length === 1
      && a.bridge.busFerry._cursors.get(KEY) === 4,
      { posts: slack.posted.filter((x) => x.channel === channelId).length, cursor: a.bridge.busFerry._cursors.get(KEY) });

    // THE CROSS-LANGUAGE PIN. The marker is a string in TWO languages with no shared constant:
    // `records.py` writes it, `bus-ferry.js` reads it. If they ever drift, the ferry goes blind
    // and every later goal finishes in silence again — exactly the defect this arm exists for.
    // This check is what makes that drift LOUD instead of invisible.
    const recordsPy = fs.readFileSync(path.join(__dirname, '..', '..', 'coord', 'records.py'), 'utf8');
    check('W9 PIN: the ferry\'s FINISH_MARKER is byte-identical to `records.py`\'s — the two '
      + 'languages hold one convention and nothing imports it across them',
      new RegExp(`^FINISH_MARKER = "${busFerryFinishMarker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"$`, 'm').test(recordsPy),
      { marker: busFerryFinishMarker });

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

    // W4 (adv, C42) — the two sigils PROMOTED TO HEADER MECHANICS. The row below carries them in
    // the header only, with a body that contains no bracketed token at all, and must route exactly
    // as row 3 did. The body-sigil arms above are the FALLBACK's control: they still pass, which is
    // what "documented fallback with a sunset" has to mean mechanically.
    append(file, `## 6 | from: leader | to: owner | type: note | chat-thread: ${known} | deliver: post | 2026-08-06 14:23\n\nheader-routed, no bracketed token anywhere in this body\n\n`);
    const hdrPosted = await waitFor(() => slack.posted.length === 4);
    const p6 = slack.posted[3];
    check('W4: `chat-thread:` / `deliver:` READ OFF THE HEADER — a row with no body sigil posts into the named thread and mints no sitting, identically to the bracketed form',
      hdrPosted && p6.channel === DM && p6.threadTs === '1.0' && creates() === before + 2
      && /header-routed/.test(p6.text),
      { channel: p6 && p6.channel, threadTs: p6 && p6.threadTs, creates: creates(), expected: before + 2 });

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

  // 11 — THE APPROVAL ROW: `approve-commit:` ON THE HEADER OPENS AN APPROVAL THREAD.
  //
  //     The plan-verifier composes the digest and sends it with `coordinate send owner --type note
  //     --approve-commit <sha>` (authority checked there: a `human-interactive:` seat, an
  //     approve-package on the goal, that exact `bound_commit`). This arm is the ferry's half —
  //     what it hands `postOwnerAsk`, which is the ONLY thing that decides whether the owner's
  //     `approve` in that thread starts execution (`chat-bridge.js` `kind` fork) or is delivered
  //     to the seat as an ordinary outcome word.
  //
  //     ⚑ THE CONTROL ROW IS THE POINT. Without it, "kind is approval" would also read green if
  //     the ferry marked EVERY owner row an approval — which is the failure that matters, because
  //     it would put an irreversible verb in every question the owner is asked.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-approve', '2026-08-27a');
    const COMMIT = '348ebf7e1111111111111111111111111111abcd';
    const calls = [];
    const b = makeBridge({
      workspaceRoot: root,
      busFerryOptions: {
        postAsk: async (args) => { calls.push(args); return { posted: true, askId: '9.9', text: args.body }; },
      },
    });
    await b.bridge.start();
    await b.bridge.busFerry.tick();                       // first sight: cursor to the tail

    append(file, `## 1 | from: plan-verifier | to: owner | type: note | approve-commit: ${COMMIT} | 2026-08-27 18:37\n\nAPPROVAL-DIGEST\nm1 scaffold · m2 wire · 4 seats\n\n`);
    append(file, msgRow(2, 'plan-verifier', 'owner', 'note', 'which binder should the vault path use?'));
    append(file, `## 3 | from: plan-verifier | to: owner | type: note | approve-commit: not-a-sha | 2026-08-27 18:39\n\nAPPROVAL-DIGEST\nmalformed\n\n`);
    await b.bridge.busFerry.tick();

    const approval = calls[0] || {};
    const ordinary = calls[1] || {};
    const malformed = calls[2] || {};
    check('an `approve-commit:` row reaches postOwnerAsk as kind=approval carrying the bound commit',
      approval.kind === 'approval' && approval.commitId === COMMIT && approval.seatName === 'plan-verifier',
      { kind: approval.kind, commitId: approval.commitId, seatName: approval.seatName });
    check('its body is `approval-thread.js#composeApprovalBody` — the §3 lead lines, the digest as payload, the bound commit, and the token line the thread actually parses',
      typeof approval.body === 'string'
      && approval.body.includes('*GOAL: goal-approve*')
      && approval.body.includes(IRREVERSIBLE_PHRASE)
      && approval.body.includes('APPROVAL-DIGEST')
      && approval.body.includes(`Bound commit: \`${COMMIT}\``)
      && approval.body.includes(APPROVAL_TOKEN_LINE),
      { body: approval.body });
    check('CONTROL: an owner row with NO approve-commit stays kind=ordinary with no commit — the irreversible verb is not in every question',
      ordinary.kind === 'ordinary' && ordinary.commitId === null && !/Bound commit/.test(String(ordinary.body)),
      { kind: ordinary.kind, commitId: ordinary.commitId });
    check('FAIL CLOSED: a malformed approve-commit is NOT an approval — the row still goes out as an ordinary ask rather than posting a garbage binding',
      malformed.kind === 'ordinary' && malformed.commitId === null,
      { kind: malformed.kind, commitId: malformed.commitId });

    b.bridge.stop();
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

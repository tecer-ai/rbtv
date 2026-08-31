#!/usr/bin/env node
'use strict';

// probe-esc-replay — THE OWNER'S OWN ACCEPTANCE BAR (`d-escalation-surface` "done means
// replayed"), replayed end to end over the mock transport.
//
// The owner rejected a code review as the way to close this cluster: "this bug survived because
// every part worked and the joins did not, and only an end-to-end run tests the joins." This
// probe reproduces the 2026-08-31 incident shape — a goal with a bound channel, a staff seat that
// is NOT `human-interactive`, a `type: escalation` row addressed to the owner — and, in ONE run,
// observes every join the owner named: the ask door admits it, the channel post, the thread, the
// `open_asks` record, the open count, the digest, the shutdown clock, the owner DM (must stay
// EMPTY), the reply releasing the ask, and the seat waking.
//
// REAL WIRING (matching probe-chat-followup/probe-chat-reply-leg): a throwaway in-process daemon
// (heart store + internal API + gateway) + a mock Socket-Mode Slack server, both from `./lib.js`,
// driving the REAL `ignite/chat/*` modules (`createChatBridge`, `ask-thread.js#postAsk`,
// `bus-ferry.js`, `system-digest.js#renderDigest`) through `chat.postMessage`/inbound WS events —
// never a stand-in for the modules under test. The one substitution, disclosed: `goalChannels`
// (task 7.58's Slack channel-admin surface) is a fixture stub that resolves ONE fixed test
// channel without touching a `conversations.create` endpoint the mock does not implement — the
// goal↔channel BINDING is real production code (`chat-bridge.js#goalChannelFor`), only the
// channel's own creation is stood in for, exactly as the mission's "a goal with a bound channel"
// asks for (the channel already exists; this probe does not test channel creation).
//
// THE FAILURE ARM (DoD 5): the SAME replay run a second time against `ignite/chat/*` checked out
// at `d2093ebf` — the commit immediately before `d-ask14`'s recovery-thread-shape work first gave
// `ask-thread.js#postAsk` ANY kind/label-based bypass of [T2-R14]. At that commit a non-interactive
// seat's escalation is refused at the door exactly as it was on 2026-08-31, and the OLD
// `bus-ferry.js#deliverEscalationInFull` dumps it into the owner's DM in full — the exact incident,
// reproduced by running code, not by argument. A `git worktree` (never a `git stash`, never an
// edit to the shared tree) checks it out read-only for the duration of the run and is removed after.
//
// Custody: this file ADDS a probe. No `ignite/chat/*.js` runtime file is edited by this probe or by
// its own presence — `lib.js`'s two additive extensions (workspaceRoot threading, a
// `conversations.open` mock endpoint) are committed alongside it as the shared-fixture change this
// replay needed to exist at all (disclosed in the seat report, not hidden here).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const {
  startThrowawayDaemon, startMockSlack, makeCapture, nowMs, sleep,
} = require('./lib');

const OUT = path.join(__dirname, 'probe-esc-replay.out');
const CHAT_DIR = path.resolve(__dirname, '..');
const IGNITE_DIR = path.resolve(CHAT_DIR, '..');
const REPO_ROOT = path.resolve(IGNITE_DIR, '..');
const PRE_FIX_COMMIT = 'd2093ebf'; // the commit before ANY kind/label bypass of [T2-R14] existed

const OWNER_USER = 'U-owner';
const SEAT_NAME = 'leader';

const start = nowMs();
const cap = makeCapture(OUT);
const failures = [];
function record(name, ok, detail) {
  cap.log({ check: name, ok, detail: detail === undefined ? undefined : detail });
  if (!ok) failures.push(name);
  return ok;
}
function observe(join, text) {
  cap.log({ join, text });
}

// ── shared fixture builders ──────────────────────────────────────────────────────────────────

// The bus row exactly as `coord.py send` appends it (matches `probe-owner-ask-hold.js#bus`,
// the shape-reference probe named in this seat's mission).
function appendBusRow(messagesPath, { id, from, to, type, body }) {
  fs.appendFileSync(messagesPath,
    `## ${id} | from: ${from} | to: ${to} | type: ${type} | 2026-08-31 21:00\n${body}\n\n`);
}

// The escalation body: top-level ❓ + one-line decision + TLDR + alternatives, then a
// `Reasoning:` heading — `bus-ferry.js#splitAskBody` finds that heading and moves everything from
// it onward into the FIRST THREADED REPLY (`d-escalation-surface` part 9). Nothing here fabricates
// the split; it is the same shape a real escalating seat's message already carries.
const ESCALATION_BODY =
  '❓ Need an owner decision: widen the credential scope for the audio-link goal?\n'
  + "TLDR: the goal cannot launch its next seat without this and has been stuck 40 minutes.\n"
  + 'Alternatives: (a) widen the scope now (b) hold for a design review — recommend (a).\n'
  + 'Reasoning:\n'
  + 'Full evidence gathered this session: the credential store only carries single-string\n'
  + 'secrets and the goal needs a directory-shaped OAuth account; see `cred-account-shape-design.md`.\n'
  + 'Evidence: /tmp/probe-esc-replay/evidence.txt';

function makeGoalFolder(workspaceRoot, goalId) {
  const dir = path.join(workspaceRoot, '.rbtv', 'goals', goalId);
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true }); // messages.md NOT written yet —
  // the ferry must WATCH this goal be born empty before the escalation lands, or its own
  // first-sight rule reads the row as backlog and never ferries it (bus-ferry.js "FIRST SIGHT").
  fs.mkdirSync(path.join(dir, 'seats', SEAT_NAME), { recursive: true });
  fs.writeFileSync(path.join(dir, 'seats', SEAT_NAME, 'seat.md'),
    '---\nseat: leader\nharness: bash\nmodel: probe-esc-replay\n---\n\nleader\n'); // NOT human-interactive
  return dir;
}

function makeGoalChannelsStub(goalId, channelId) {
  return {
    resolveChannel: async (g) => (g === goalId ? { channelId, reason: null } : { channelId: null, reason: 'no-channel' }),
    goalForChannel: (ch) => (ch === channelId ? goalId : null),
    recover: async () => ({ ok: true, bound: 0 }),
  };
}

async function waitFor(cond, { timeoutMs = 6000, stepMs = 30 } = {}) {
  const t0 = nowMs();
  while (nowMs() - t0 < timeoutMs) {
    if (cond()) return true;
    await sleep(stepMs);
  }
  return cond();
}

// Build one fully-wired REAL bridge (matching probe-chat-followup's real-daemon style, but
// `createChatBridge` directly rather than `index.js#buildBridge` — this probe's `goalChannels` is
// injected fixture, and `buildBridge` would instead try to derive one from `transport.createChannel`
// against endpoints the mock does not implement).
function buildRealBridge({ chatDir, daemon, mock, goalId, channelId, dmUser = OWNER_USER, logs }) {
  const { resolveConfig } = require(path.join(chatDir, 'config.js'));
  const { createGatewayForwarder } = require(path.join(chatDir, 'gateway-forwarder.js'));
  const { createAllowlist } = require(path.join(chatDir, 'allowlist.js'));
  const { createThreadMap } = require(path.join(chatDir, 'thread-map.js'));
  const { createSlackSocketMode } = require(path.join(chatDir, 'slack-socket-mode.js'));
  const { createChatBridge } = require(path.join(chatDir, 'chat-bridge.js'));

  const config = resolveConfig({
    gatewayAddr: daemon.gatewayAddr, bridgeToken: daemon.bridgeToken,
    workspaceRoot: daemon.workspaceRoot, channelPrefix: 'test-',
    allowlist: [dmUser], ownerUser: dmUser, busFerry: true, busFerryDmUser: dmUser,
    systemChannelId: 'C-system-fake',
    slackApiBase: mock.apiBase, slackAppToken: 'xapp-fake', slackBotToken: 'xoxb-fake',
  });
  const forwarder = createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
  const allowlist = createAllowlist({ allowed: config.allowlist });
  const threadMap = createThreadMap({});
  let bridge;
  const onMessage = (m) => bridge.onChatMessage(m);
  const transport = createSlackSocketMode({
    appToken: config.slack.appToken, botToken: config.slack.botToken, apiBase: config.slack.apiBase,
    onMessage, logger: (o) => { if (logs) logs.push(o); },
  });
  const goalChannels = makeGoalChannelsStub(goalId, channelId);
  bridge = createChatBridge({
    config, forwarder, transport, allowlist, threadMap, goalChannels,
    logger: (o) => { if (logs) logs.push(o); },
    replyLegOptions: { pollMs: 3600 * 1000 }, // out of scope — probe-chat-reply-leg's own subject
    busFerryOptions: { pollMs: 150 },
  });
  return { bridge, transport, config };
}

// ── PART A: the positive replay ──────────────────────────────────────────────────────────────

async function runPositiveReplay() {
  const goalId = 'test-esc-replay';
  const channelId = 'C-test-esc-replay';
  const logs = [];
  let daemon, mock;
  observe('setup', `goal=${goalId} channel(fixture)=${channelId} seat=${SEAT_NAME} (not human-interactive)`);

  daemon = await startThrowawayDaemon();
  const goalDir = makeGoalFolder(daemon.workspaceRoot, goalId);
  mock = await startMockSlack();
  const { bridge } = buildRealBridge({ chatDir: CHAT_DIR, daemon, mock, goalId, channelId, logs });

  await bridge.start();
  await mock.connected;
  // Let the ferry's own start()-time openDm resolve and at least two empty-goal ticks pass, so
  // its "watched this execution be born" rule arms BEFORE the row exists on disk (see
  // makeGoalFolder's comment) — writing it any earlier risks the first pass reading a NON-empty
  // messages.md as backlog and never ferrying it.
  await sleep(500);

  const messagesPath = path.join(goalDir, 'coordination', 'messages.md');
  appendBusRow(messagesPath, { id: 1, from: SEAT_NAME, to: 'owner', type: 'escalation', body: ESCALATION_BODY });

  const gotPost = await waitFor(() => mock.sentMessages.length >= 1, { timeoutMs: 8000 });
  record('setup: bus ferry actually started (DM resolved)', logs.some((l) => l.message === 'bus ferry started'),
    logs.filter((l) => /bus ferry/.test(l.message || '')).map((l) => l.message));
  record('A0 the escalation row reached the mock transport at all', gotPost, { sentCount: mock.sentMessages.length });

  // ── join 1: the ask door admits it ──────────────────────────────────────────────────────────
  // `ask-thread.js#createAskThreads` is constructed with NO `logger` by `chat-bridge.js` (its own
  // `log()` calls are silent), so admission is read off the effect, not a log line: `bus-ferry.js`
  // (which IS logged) never fires its [T2-R14] refusal-rescue path for this row, and the row
  // reached the goal channel as a real post — the two are conjunctive because a refused row is
  // NEVER silently dropped in this design (rescued as a 💭 notice instead), so "no refusal logged"
  // plus "a post landed in the goal's own channel" together mean the ask door admitted it.
  const refusalLog = logs.find((l) => /refused at the ask door \[T2-R14\]/.test(l.message || ''));
  record('J1 the ask door admitted the escalation (posted to the goal channel, not refused)',
    !refusalLog && mock.sentMessages.some((m) => m.channel === channelId),
    { refusalLog: refusalLog || null, postedToGoalChannel: mock.sentMessages.filter((m) => m.channel === channelId).length });
  observe('J1 ask door', JSON.stringify({ refusalLog: refusalLog || null }));

  // ── join 2 + 3: the channel post + the thread ───────────────────────────────────────────────
  const goalChannelPosts = mock.sentMessages.filter((m) => m.channel === channelId);
  const topPost = goalChannelPosts.find((m) => m.thread_ts == null);
  const replyPost = goalChannelPosts.find((m) => m.thread_ts != null);
  record('J2 the top-level post carries ❓ + the one-line decision + TLDR + alternatives, at top level (no thread_ts)',
    Boolean(topPost) && /❓/.test(topPost.text) && /Need an owner decision/.test(topPost.text)
      && /TLDR/.test(topPost.text) && /Alternatives/.test(topPost.text) && !/Full evidence gathered/.test(topPost.text),
    { text: topPost && topPost.text });
  const askId = topPost && topPost.ts; // Slack's own ts IS the ask id [T5-R7] — the mock mints one per post
  record('J3 the full reasoning + evidence pointer landed as the FIRST reply, on the SAME thread_ts',
    Boolean(replyPost) && replyPost.thread_ts === askId && /Full evidence gathered/.test(replyPost.text) && /Evidence:/.test(replyPost.text),
    { replyThreadTs: replyPost && replyPost.thread_ts, askId, text: replyPost && replyPost.text });
  observe('J2 top-level post', JSON.stringify(topPost));
  observe('J3 first reply', JSON.stringify(replyPost));

  // ── join 4: the record — exactly one open_asks row, posted=1, ask_id === the top-level ts ──
  const stateStore = require(path.join(IGNITE_DIR, 'state-store'));
  const api = stateStore.bind(stateStore.openEndingStoreFor(daemon.workspaceRoot));
  const askRow = askId ? api.getAsk(askId) : null;
  record('J4 exactly one open_asks row, posted=1, ask_id === the top-level ts',
    Boolean(askRow) && String(askRow.ask_id) === String(askId) && Number(askRow.posted) === 1 && askRow.state === 'open',
    askRow);
  observe('J4 open_asks row', JSON.stringify(askRow));

  // ── join 5: the open count ──────────────────────────────────────────────────────────────────
  const openCount = api.countOpenAsks(goalId);
  record('J5 the goal\'s open-ask count is 1', openCount === 1, { openCount });
  observe('J5 open count', String(openCount));

  // ── join 6: the digest ──────────────────────────────────────────────────────────────────────
  const { renderDigest } = require(path.join(CHAT_DIR, 'system-digest.js'));
  const asksForDigest = await require(path.join(CHAT_DIR, 'ask-store.js'))
    .createAskRecord({ forwarder: require(path.join(CHAT_DIR, 'gateway-forwarder.js'))
      .createGatewayForwarder({ gatewayAddr: daemon.gatewayAddr, token: daemon.bridgeToken }) })
    .listOpenAsks();
  const digestText = renderDigest({ at: new Date(), asks: asksForDigest, conditions: [], nowMs: Date.now() });
  // The digest's `one_liner` is the ask copy's own first line (`system-digest.js#oneLinerOf`) —
  // the ROW HEADER `formatMessage` composed (`*🧵 leader* — <goal> · escalation · #<id>`), not the
  // escalation's own decision text below it. `· escalation · #` is the one marker
  // `bus-ferry.js#isEscalationOneLiner` itself reads back for the SAME row on the fleet-wide
  // gate — the real, documented signal, not a fixture convenience.
  record('J6 the escalation appears as a row in the rendered digest, identifiable as an escalation',
    digestText.includes(goalId) && digestText.includes(SEAT_NAME) && digestText.includes(' · escalation · #'),
    { digestExcerpt: digestText.split('\n').filter((l) => l.startsWith('•')).join(' | ') });
  observe('J6 rendered digest', digestText);

  // ── join 7: the shutdown clock ───────────────────────────────────────────────────────────────
  const waiting = api.goalWaitingOnOwner({ goal: goalId, canAdvance: false });
  record('J7 the goal reads as waiting on the owner (shutdown clock suspended), not reapable',
    waiting === true, { goalWaitingOnOwner: waiting });
  observe('J7 shutdown clock', String(waiting));

  // ── join 8: the owner DM — ZERO posts ────────────────────────────────────────────────────────
  const dmChannelId = 'D-mock-owner-dm'; // the mock's fixed `conversations.open` response (lib.js)
  const dmPosts = mock.sentMessages.filter((m) => m.channel === dmChannelId);
  record('J8 ZERO posts to the owner DM across the whole run',
    dmPosts.length === 0, { dmChannelId, dmPostCount: dmPosts.length, allChannelsPosted: mock.sentMessages.map((m) => m.channel) });
  observe('J8 owner DM — full record of posts to it', JSON.stringify(dmPosts) + ` (count=${dmPosts.length})`);

  // ── join 9 + 10: the reply releases the ask and wakes the seat; the goal moves ──────────────
  const beforeReleaseCount = logs.length;
  await mock.pushMessage({
    type: 'message', user: OWNER_USER, text: 'approve — widen the scope now',
    channel: channelId, thread_ts: askId, ts: `${(Number(askId) || Date.now() / 1000) + 5}`,
    event_ts: `${(Number(askId) || Date.now() / 1000) + 5}`, client_msg_id: 'esc-replay-owner-reply',
    channel_type: 'channel',
  });
  await waitFor(() => logs.slice(beforeReleaseCount).some((l) => l.message === 'authorized reply RELEASED the ask in its own thread — wait reaped and relaunch fired in one act [§2.4.4]'),
    { timeoutMs: 5000 });
  const releaseLog = logs.find((l) => l.message === 'authorized reply RELEASED the ask in its own thread — wait reaped and relaunch fired in one act [§2.4.4]');
  record('J9 the owner reply RELEASED the ask (reaped) and named the outcome',
    Boolean(releaseLog) && releaseLog.reaped === true, releaseLog);
  observe('J9 release log', JSON.stringify(releaseLog));

  const askRowAfter = askId ? api.getAsk(askId) : null;
  const openCountAfter = api.countOpenAsks(goalId);
  record('J10 the goal MOVES: the ask row closes and the open count drops to 0 (the daemon\'s relaunch signal)',
    askRowAfter && askRowAfter.state === 'closed' && openCountAfter === 0,
    { askRowAfter, openCountAfter });
  const replyCopyPath = path.join(goalDir, 'coordination', 'asks', `${String(askId).replace(/[^A-Za-z0-9._-]/g, '_')}.reply.txt`);
  let replyCopyText = null;
  try { replyCopyText = fs.readFileSync(replyCopyPath, 'utf8'); } catch { /* not observed */ }
  record('J10b the relaunched seat\'s answer is available ON DISK (the reply copy the spec has it read from)',
    typeof replyCopyText === 'string' && /approve/.test(replyCopyText),
    { replyCopyPath, replyCopyText });
  observe('J10 goal moves', JSON.stringify({ askRowAfter, openCountAfter, replyCopyText }));

  mock.close();
  await daemon.close(); // heart store is a per-process singleton — the failure arm cannot open
  // its OWN throwaway daemon until this one releases it (`state-store/heart/heart-store.js`).

  return { failures: failures.length, checks: cap.lines.length, goalId, askId, dmPostCount: dmPosts.length };
}

// ── PART B: the failure arm — the SAME replay against the pre-fix commit ─────────────────────

async function runFailureArm() {
  const goalId = 'test-esc-replay-oldcode';
  const channelId = 'C-test-esc-replay-old';
  const logs = [];
  const oldWorktree = fs.mkdtempSync(path.join(os.tmpdir(), 'esc-replay-oldcode-'));
  fs.rmdirSync(oldWorktree); // `git worktree add` refuses an existing (even empty) target dir
  observe('failure-arm setup', `git worktree add --detach ${oldWorktree} ${PRE_FIX_COMMIT}`);
  execFileSync('git', ['worktree', 'add', '--detach', oldWorktree, PRE_FIX_COMMIT], { cwd: REPO_ROOT, stdio: 'pipe' });
  let result;
  try {
    const oldChatDir = path.join(oldWorktree, 'ignite', 'chat');
    if (!fs.existsSync(path.join(oldChatDir, 'ask-thread.js'))) {
      throw new Error(`pre-fix worktree has no ${oldChatDir}/ask-thread.js — cannot run the failure arm`);
    }
    const daemon = await startThrowawayDaemon();
    const goalDir = makeGoalFolder(daemon.workspaceRoot, goalId);
    const mock = await startMockSlack();
    const { bridge } = buildRealBridge({ chatDir: oldChatDir, daemon, mock, goalId, channelId, logs });

    await bridge.start();
    await mock.connected;
    await sleep(500);

    const messagesPath = path.join(goalDir, 'coordination', 'messages.md');
    appendBusRow(messagesPath, { id: 1, from: SEAT_NAME, to: 'owner', type: 'escalation', body: ESCALATION_BODY });
    await waitFor(() => mock.sentMessages.length >= 1, { timeoutMs: 8000 });

    const dmChannelId = 'D-mock-owner-dm';
    const dmPosts = mock.sentMessages.filter((m) => m.channel === dmChannelId);
    const doorRefused = logs.some((l) => /REFUSED/.test(l.message || ''));
    const askedOk = logs.some((l) => l.message === 'owner ask posted in a NEW thread');
    observe('failure-arm sentMessages', JSON.stringify(mock.sentMessages));
    observe('failure-arm logs (REFUSED / posted)', JSON.stringify(logs.filter((l) => /REFUSED|posted in a NEW thread|ESCALATION/.test(l.message || l.level || ''))));

    result = {
      commit: PRE_FIX_COMMIT,
      doorRefused, askedOk, dmPostCount: dmPosts.length,
      dmSample: dmPosts[0] ? dmPosts[0].text : null,
      verdict: (dmPosts.length > 0 && !askedOk) ? 'FAILS as expected — the pre-fix door refused the escalation and it leaked to the owner DM' : 'DID NOT REPRODUCE the incident shape — see raw logs',
    };
    record('B1 the pre-fix door REFUSES the escalation (seat is not human-interactive, no kind bypass existed yet)',
      doorRefused && !askedOk, { doorRefused, askedOk });
    record('B2 the pre-fix code DUMPS the refused escalation into the owner DM (the exact incident)',
      dmPosts.length > 0, { dmPostCount: dmPosts.length, sample: dmPosts[0] });
    mock.close();
    await daemon.close();
  } finally {
    try { execFileSync('git', ['worktree', 'remove', '--force', oldWorktree], { cwd: REPO_ROOT, stdio: 'pipe' }); } catch (err) {
      cap.log({ warn: 'could not remove failure-arm worktree — manual cleanup owed', oldWorktree, error: err.message });
    }
  }
  return result;
}

async function main() {
  observe('probe', 'probe-esc-replay — the owner\'s end-to-end escalation replay (d-escalation-surface "done means replayed")');
  const positive = await runPositiveReplay();
  observe('positive-replay summary', JSON.stringify(positive));

  let failureArm = null;
  try {
    failureArm = await runFailureArm();
  } catch (err) {
    record('B0 failure arm ran without throwing', false, { error: err.message, stack: err.stack });
  }
  observe('failure-arm summary', JSON.stringify(failureArm));
}

main()
  .catch((err) => { record('probe completed without throwing', false, { error: err.message, stack: err.stack }); })
  .then(() => {
    const verdict = failures.length ? `FAIL — ${failures.join(' | ')}` : 'PASS';
    cap.log({ verdict, failures: failures.length, wall_ms: nowMs() - start });
    cap.flush(verdict);
    process.stdout.write(`${cap.lines.map((l) => JSON.stringify(l)).join('\n')}\n`);
    process.stdout.write(`verdict: ${verdict}\n`);
    process.exit(failures.length ? 1 : 0);
  });

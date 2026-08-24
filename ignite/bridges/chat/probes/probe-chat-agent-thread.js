'use strict';

// THREAD PER AGENT IN A GOAL CHANNEL (ratified design 2026-08-09) — the two gates on
// agent-initiated contact, the (goal, agent) thread map, the inbound 'agent' route, the
// return leg into a goal channel, and the seat refusals.
//
// The claims that matter most here are NEGATIVE, and they split into two kinds that a
// careless fixture makes indistinguishable:
//   • a PARKED row — the gates said no, so NOTHING is posted anywhere (not the channel, not
//     the owner's DM) while the cursor still advances. Every park check below therefore
//     asserts against BOTH post logs, and each is paired with the same row travelling once
//     its own gate opens — so "not posted" can never pass for "nothing was ferried at all".
//   • NO SITTING MINTED — the agent-thread post and the return leg both mint nothing, which
//     is checkable only as an absence in the forwarder's enqueue log.
//
// No daemon: every claim is about the bridge's own gating, mapping and routing, so the
// gateway is a stub that records every enqueue and Slack is a fake that records every post.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { NO_AGENT_SEAT_NOTICE, resolveGoalSeat } = require('../forward-path');
const { goalExecutionMode, seatIsHumanInteractive, isSafeName, addressesOwner, seatFallback, formatMessage } = require('../bus-ferry');

const OUT = path.join(__dirname, 'probe-chat-agent-thread.out');

const USER = 'U_OWNER';
const BOT = 'U_BOT';
const DM = 'D_OWNER';
const PREFIX = 'test-';

// ── fakes ────────────────────────────────────────────────────────────────────

// One Slack workspace: the narrow channel-admin surface (create/list/archive — this fake
// exposes no `inviteToChannel`, so the C-3 owner invite is simply not reachable here; it
// is `probe-chat-goal-channel` that owns that claim), `openDm` for the ferry, and a post log that hands back a DISTINCT `ts`
// per post, because "the second row replied on the FIRST row's thread" is only checkable
// when two posts cannot accidentally share one.
function makeFakeSlack() {
  const channels = [];
  const posted = [];
  let nextId = 1;
  let nextTs = 1;
  let failLists = 0;
  // `lists` counts the conversations.list walks: "the bridge re-asked Slack on a map miss" is a
  // CALL, and a check that only reads the outcome cannot tell a re-resolution from a lucky cache.
  const counter = {
    lists: 0,
    channels, posted,
    postsIn(channel) { return posted.filter((p) => p.channel === channel); },
    async authTest() { return { ok: true, userId: BOT }; },
    async openDm(userId) { return { ok: true, channel: DM, userId }; },
    async createChannel({ name }) {
      if (channels.some((c) => c.name === name && !c.is_archived)) return { ok: false, error: 'name_taken' };
      const ch = { id: `C${String(nextId++).padStart(4, '0')}`, name, is_archived: false };
      channels.push(ch);
      return { ok: true, channel: { id: ch.id, name: ch.name } };
    },
    // A Slack API failure on the LOOKUP, which is a different fact from "the channel is not
    // there" — and the only way to drive `resolve-failed` through the real code path.
    failNextLists(n) { failLists = n; },
    async listChannels({ excludeArchived = true } = {}) {
      counter.lists += 1;
      if (failLists > 0) { failLists -= 1; return { ok: false, error: 'ratelimited' }; }
      const visible = channels.filter((c) => (excludeArchived ? !c.is_archived : true));
      return { ok: true, channels: visible.map((c) => ({ id: c.id, name: c.name })), nextCursor: null };
    },
    async archiveChannel() { return { ok: true }; },
    async sendToOwner({ channel, threadTs, text }) {
      const ts = `${nextTs++}.0`;
      posted.push({ channel, threadTs: threadTs ?? null, text, ts });
      return { delivered: true, ts };
    },
    async start() { return { connected: true }; },
    stop() {},
  };
  return counter;
}

// Every session-creating enqueue reads back as a LIVE session on its own queue row (the
// D108(B) tier-1 shape), so a follow-up can resolve its chain thread and the follow-up leg
// is exercised for real rather than declining.
function makeFakeForwarder() {
  const enqueued = [];
  let nextQueueId = 700;
  return {
    enqueued,
    creates() { return enqueued.filter((e) => e.payload.job_id === 'chat-launch'); },
    sends() { return enqueued.filter((e) => e.payload.job_id === 'send-message'); },
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

// ── the bus fixture ──────────────────────────────────────────────────────────

function msgRow(id, from, to, type, body) {
  return `## ${id} | from: ${from} | to: ${to} | type: ${type} | 2026-08-09 14:23\n\n${body}\n\n`;
}

// A goal + open run. `executionMode` is gate 2 (null = the file is ABSENT, which is the
// ratified default of `autonomous`); `seats` is gate 1, one entry per seat name → whether it
// declares `human-interactive` (a string value is written verbatim, so `no` is testable).
// No roster is written anywhere here: an absent `workers.md` is the nobody-home branch, which
// is the ONLY branch the gates sit on.
// 7.607 E3: GOAL-DIRECT. No `runs.csv`, no run folder — the coordination bus and the seats hang
// off the goal folder itself, and the third element of identity is the EXECUTION STAMP
// (design-lock item 5) written to `coordination/execution`.
// `fallbacks` is the 7.626 axis: the seat's declared autonomous arm, written into the SAME
// frontmatter. Absent from the map = no `fallback:` line at all, which is a real state on disk (a
// `component-lint` violation) and the one the ferry must leave behaviour-unchanged.
function seedGoal(root, goalId, { stamp = '2026-08-03a', executionMode = 'interactive', seats = {}, fallbacks = {} } = {}) {
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'coordination', 'execution'), `${stamp}\n`);
  if (executionMode !== null) fs.writeFileSync(path.join(goalDir, 'execution-mode'), `${executionMode}\n`);
  for (const [seat, flag] of Object.entries(seats)) {
    fs.mkdirSync(path.join(goalDir, 'seats', seat), { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'seats', seat, 'seat.md'),
      `---\nseat: ${seat}\n${flag === null ? '' : `human-interactive: ${flag}\n`}`
      + `${fallbacks[seat] ? `fallback: ${fallbacks[seat]}\n` : ''}---\nbody\n`);
  }
  const file = path.join(goalDir, 'coordination', 'messages.md');
  fs.writeFileSync(file, '# messages — append-only coordination log (script-managed, do not edit by hand)\n\n'
    + msgRow(1, 'leader', 'leader', 'note', 'history — first sight seeds the cursor here'));
  return { file, goalDir };
}

function append(file, chunk) { fs.appendFileSync(file, chunk); }

function makeBridge({ workspaceRoot, stateFile = null, logs = null, slack = makeFakeSlack(), forwarder = makeFakeForwarder() } = {}) {
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot,
    channelPrefix: PREFIX,
    stateFile,
    busFerry: true,
    busFerryDmUser: USER,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: logs ? (e) => logs.push(e) : () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 },
    busFerryOptions: { pollMs: 3600000 }, // driven by hand via tick()
  });
  return { ...built, slack, forwarder, config };
}

// A Slack message event as the transport shapes it.
function msg({ channel, ts, threadTs = null, channelType = 'channel', text = 'hello', user = USER }) {
  return {
    chatUserId: user,
    chatThreadId: `${channel}:${threadTs || ts}`,
    text,
    _channel: channel,
    _threadTs: threadTs || ts,
    _msgTs: ts,
    _channelType: channelType,
    _inThread: Boolean(threadTs),
  };
}

// ── THE MUTATION HARNESS (arm 11) ────────────────────────────────────────────
//
// ⚑ EVERY GREEN ABOVE IS WORTH WHAT ITS RED ARM PROVES. A check that cannot fail passes against
// a bridge that was never changed, and nothing in a capture distinguishes the two. So each claim
// this probe makes is replayed against a SCRATCH COPY of the module with ONE STRING CHANGED — the
// defect that claim exists to catch — and the copy MUST go red on exactly that claim. This was
// run by hand at build time and existed in no committed artifact; the reviewer required it be
// repeatable by anybody, so it lives here.
//
// Same shape as `probe-chat-dedup-refusal`'s red arm, scaled to a whole tree because these claims
// span three modules and the composed bridge:
//   • THE COPY LIVES BESIDE THE ORIGINAL (`bridges/__chatmut-<pid>/`), never in a tmpdir: the
//     probe harness `lib.js` requires `../../../server` and `../../../gateway`, which resolve only
//     from a directory one level under `bridges/`. Measured: a tmpdir copy dies MODULE_NOT_FOUND.
//   • THE COPIED `probes/probe-*` FILES ARE DELETED and this file is copied in as `mutant-arm.js`,
//     so the suite's discovery — directories literally named `probes`, files starting with
//     `probe-` — can never see the copy even if a full-tree run overlaps its lifetime.
//   • THE CHILD IS MARKED so it runs the checks and NOT this harness. Without that marker each
//     mutant would spawn its own mutants, forever.
//   • THE MUTATION IS ASSERTED TO HAVE APPLIED (exactly one occurrence, file changed) before its
//     red is believed. A mutation that silently did not apply produces a green mutant, which reads
//     exactly like a probe whose checks are vacuous.
//   • THE CONTROL COPY runs UNMUTATED and must be green at the SAME check count as this run's
//     pre-harness total — so a mutant's red can never be the copy itself being broken, and an arm
//     count that quietly degraded is caught rather than reported as a pass.
const MUTANT_ENV = 'RBTV_CHAT_AGENT_THREAD_MUTANT';
const CHAT_SRC = path.join(__dirname, '..');
const MUTANT_DIR = path.join(__dirname, '..', '..', `__chatmut-${process.pid}`);

// `expect` = substrings of the check names this mutation MUST turn red. Extra reds are allowed
// (one defect often breaks several claims); a missing one is the failure.
const MUTATIONS = [
  // ⚑ `gates-removed` IS GONE, and so is the gate it mutated. The rung it flipped —
  // `if (gate) { … park }` — no longer exists in `bus-ferry.js` [D24, T2-R17, D-7-ruling], so the
  // anchor would be absent and the arm would report "anchor missing" while measuring nothing.
  // What replaced it is the pair of TRAVEL claims in arms 2 and 3, each with its own mutation.
  { name: 'owner-token-is-master', file: 'bus-ferry.js', from: "const OWNER_TOKEN = 'owner';", to: "const OWNER_TOKEN = 'master';",
    expect: ['RULING (gates OPEN)', 'T2-R17 PAIR'] },
  { name: 'every-address-ferried', file: 'bus-ferry.js', from: '.some((t) => t === OWNER_TOKEN)', to: '.some(() => true)',
    expect: ['RULING (gates OPEN)', 'RULING (autonomous goal)'] },
  // ⚑ THE ANCHOR CARRIES ITS KEY. `frontmatterOf(fm).match` alone stopped being unique the moment
  // 7.626's `seatFallback` read the same file the same way — and an ambiguous anchor is not applied
  // at all, so this arm would have gone red claiming "anchor absent" while measuring nothing.
  { name: 'gate1-not-scoped-to-frontmatter', file: 'bus-ferry.js',
    from: 'frontmatterOf(fm).match(/^human-interactive:', to: 'String(fm).match(/^human-interactive:',
    expect: ['scoped to the FRONTMATTER block'] },
  // 7.626 — the three arms, each proven to be the thing doing the work.
  // ⚑ `fallback-park-rung-removed` IS GONE for the same reason: there is no `fallback-park` rung
  // left to remove. `fallback:` survives as a RENDER MARK only, which `arm-marker-dropped` below
  // is the mutation for.
  { name: 'fallback-not-scoped-to-frontmatter', file: 'bus-ferry.js',
    from: 'frontmatterOf(fm).match(/^fallback:', to: 'String(fm).match(/^fallback:',
    expect: ['FRONTMATTER BLOCK ONLY'] },
  { name: 'arm-marker-dropped', file: 'bus-ferry.js',
    from: "const mark = Object.hasOwn(FALLBACK_MARK, arm) ? FALLBACK_MARK[arm] : '';", to: "const mark = '';",
    expect: ['ARM `default-and-disclose`', 'ARM `block-and-queue`', 'MUTATION (the arm)'] },
  // Review F3/F5. The strip anchor carries its RETURN line: the identical strip now runs in
  // `seatFallback` too, so the expression alone is ambiguous and would not be applied at all.
  { name: 'flag-strip-removed', file: 'bus-ferry.js',
    from: "  const v = m ? m[1].replace(/\\s+#.*$/, '').trim().replace(/^[\"']|[\"']$/g, '').toLowerCase() : '';\n  return v === 'yes'",
    to: "  const v = m ? m[1].toLowerCase() : '';\n  return v === 'yes'",
    expect: ['gate 1 agrees with the LINTER'] },
  { name: 'marker-lookup-unguarded', file: 'bus-ferry.js',
    from: "const mark = Object.hasOwn(FALLBACK_MARK, arm) ? FALLBACK_MARK[arm] : '';",
    to: "const mark = FALLBACK_MARK[arm] || '';",
    expect: ['a bogus arm renders NO marker'] },
  { name: 'undeclared-arm-invents-one', file: 'bus-ferry.js',
    from: '  return FALLBACK_ARMS.includes(v) ? v : null;', to: "  return FALLBACK_ARMS.includes(v) ? v : 'block-and-queue';",
    expect: ['NOT A FOURTH ARM'] },
  { name: 'owner-not-reserved-in-gate1', file: 'bus-ferry.js', from: '&& n !== OWNER_TOKEN', to: '',
    expect: ['`owner` is RESERVED'] },
  { name: 'owner-not-reserved-in-seat-resolver', file: 'forward-path.js',
    from: "if (String(seatName) === RESERVED_SEAT_NAME) return { ok: false, reason: 'owner-is-reserved' };", to: '',
    expect: ['`owner` is RESERVED'] },
  { name: 'absent-mode-reads-interactive', file: 'bus-ferry.js', from: '} catch { return goalKindMode(goalDir); }', to: '} catch { return INTERACTIVE_MODE; }',
    // ⚑ ONE expectation now, not two. `goalExecutionMode` is still EXPORTED and still read by other
    // consumers, so its ladder is still measured — but the BUS FERRY no longer asks it anything
    // [D24], so no delivery check can be red for it any more.
    expect: ['an ABSENT execution-mode file reads as autonomous'] },
  // C-4's fix and its red arm: cut rung 2 back to the old behaviour and the goal-kind fallback
  // arm must die, while the two arms around it (file wins, neither resolves) stay green — which
  // is what makes the fallback the discriminator rather than a check that passes either way.
  { name: 'goal-kind-fallback-removed', file: 'bus-ferry.js', from: '} catch { return goalKindMode(goalDir); }', to: '} catch { return AUTONOMOUS_MODE; }',
    expect: ['THE THREE-RUNG LADDER'] },
  { name: 'agent-thread-leg-not-tried', file: 'bus-ferry.js', from: 'if (!res && !chatThread && routeToAgentThread) {', to: 'if (false) {',
    expect: ['ANCHORS a thread', 'D24 PAIR'] },
  { name: 'header-not-agent-led', file: 'bus-ferry.js', from: 'const header = (agentLead', to: 'const header = (false',
    expect: ['ANCHORS a thread'] },
  { name: 'routeof-agent-branch-removed', file: 'chat-bridge.js', from: "if (agent) return { kind: 'agent'", to: "if (false) return { kind: 'agent'",
    expect: ['routes as kind `agent`', 'HOMED AT THE ASKING SEAT'] },
  { name: 'return-leg-guard-removed', file: 'chat-bridge.js', from: 'if (tokenGoalId) {', to: 'if (false) {',
    expect: ['posted into that thread verbatim', 'S-13 (c)'] },
  // S-13 — the two sides of the verification, and the two sides of the known set.
  { name: 's13-token-not-verified', file: 'bus-ferry.js',
    from: 'const chatThread = namedThread && knowsThread(namedThread) ? namedThread : null;', to: 'const chatThread = namedThread;',
    expect: ['S-13 (a)', 'S-13 (b)'] },
  { name: 's13-knowsthread-vouches-for-everything', file: 'chat-bridge.js',
    from: 'if (replyAddr.has(id) || threadMap.has(id)) return true;', to: 'if (true) return true;',
    expect: ['S-13 (a)', 'S-13 (b)'] },
  // The GREEN half's red arm: with the two live-state clauses cut, a restored conversation stops
  // being known and the restart leg dies — while an ANCHORED AGENT THREAD stays known through the
  // third clause, which is exactly the asymmetry the ruling's known set describes.
  { name: 's13-knowsthread-vouches-for-nothing', file: 'chat-bridge.js',
    from: 'if (replyAddr.has(id) || threadMap.has(id)) return true;', to: 'if (false) return true;',
    expect: ['S-13 RESTART', 'CONTROL: a token naming a KNOWN DM thread'] },
  { name: 'agentthreads-not-persisted', file: 'chat-bridge.js', from: 'agentThreads: Object.fromEntries(agentThreads),', to: '',
    expect: ['the anchored thread is persisted', 'start() restores'] },
  // 2026-08-12 — the two halves of the missing-channel incident, each proven to be the thing
  // doing the work. The first puts the map back in charge of a question only Slack can answer;
  // the second puts the DM fallback back.
  { name: 'miss-trusts-the-in-memory-map', file: 'chat-bridge.js',
    from: 'await goalChannels.resolveChannel(goalId)',
    to: "{ channelId: goalChannels.channelForGoal(goalId), reason: 'no-channel' }",
    expect: ['(c) and the miss ASKED SLACK', '(c) THE FIX'] },
  { name: 'resolve-failure-reads-as-absence', file: 'goal-channel-map.js',
    from: "      return { channelId: null, reason: 'resolve-failed' };",
    to: "      return { channelId: null, reason: 'no-channel' };",
    expect: ['a FAILED lookup is `resolve-failed`'] },
  { name: 'no-channel-falls-back-to-the-dm', file: 'bus-ferry.js',
    from: 'res = await routeToAgentThread({ goalId, agent: row.from, text: threadText });',
    to: 'res = await routeToAgentThread({ goalId, agent: row.from, text: threadText });\n              if (res && !res.delivered && res.reason === \'no-channel\') res = null;',
    expect: ['(a) gates pass'] },
  { name: 'agent-homed-at-goal-master', file: 'forward-path.js', from: "route.kind === 'agent' ? route.agent : 'goal-master'", to: "'goal-master'",
    expect: ['HOMED AT THE ASKING SEAT'] },
];

// Copy the module, strip the copied probe scripts, drop this file in under a name discovery
// ignores, and apply one mutation. Returns null when the anchor is not uniquely present.
function buildMutant({ file, from, to } = {}) {
  fs.rmSync(MUTANT_DIR, { recursive: true, force: true });
  fs.cpSync(CHAT_SRC, MUTANT_DIR, { recursive: true });
  const probesDir = path.join(MUTANT_DIR, 'probes');
  for (const f of fs.readdirSync(probesDir)) {
    if (f.startsWith('probe-')) fs.rmSync(path.join(probesDir, f), { force: true });
  }
  fs.copyFileSync(__filename, path.join(probesDir, 'mutant-arm.js'));
  if (!file) return { applied: true, cutBytes: 0 };
  const target = path.join(MUTANT_DIR, file);
  // Normalize CRLF->LF before matching: a multi-line anchor carries a bare \n that only
  // matches LF content, so a CRLF checkout (core.autocrlf=true, e.g. Windows) reads it as
  // absent even though the anchor is genuinely there. The copy is throwaway (deleted after
  // the run), so normalizing before writing back changes no tracked file.
  const before = fs.readFileSync(target, 'utf8').replace(/\r\n/g, '\n');
  if (before.split(from).length - 1 !== 1) return null;   // not present, or ambiguous
  const after = before.replace(from, to);
  if (after === before) return null;
  fs.writeFileSync(target, after);
  return { applied: true, cutBytes: before.length - after.length };
}

// Run the copy and read ITS capture (written inside the copy, never beside this file).
function runMutant() {
  let exit = 0;
  try {
    execFileSync(process.execPath, [path.join(MUTANT_DIR, 'probes', 'mutant-arm.js')],
      { env: { ...process.env, [MUTANT_ENV]: '1' }, stdio: 'pipe', timeout: 60000 });
  } catch (err) { exit = err.status == null ? -1 : err.status; }
  let summary = null;
  try {
    summary = JSON.parse(fs.readFileSync(path.join(MUTANT_DIR, 'probes', 'probe-chat-agent-thread.out'), 'utf8')).summary;
  } catch {}
  return { exit, summary };
}

async function runMutationArms(check, baselineChecks) {
  try {
    // THE CONTROL FIRST. If an unmutated copy is not green at the same count, every red below is
    // uninterpretable — it could be the copy rather than the mutation.
    buildMutant({});
    const control = runMutant();
    check('MUTATION CONTROL: an UNMUTATED copy of the module is green at the same check count as this run — so every red below is the mutation, not the copy',
      control.exit === 0 && Boolean(control.summary) && control.summary.pass === true
      && control.summary.checks === baselineChecks,
      { exit: control.exit, checks: control.summary && control.summary.checks, baselineChecks });

    for (const m of MUTATIONS) {
      const built = buildMutant(m);
      if (!built) {
        check(`MUTANT ${m.name}: the anchor is uniquely present in ${m.file}`, false,
          { detail: 'ANCHOR ABSENT OR AMBIGUOUS — the mutation could not be applied, so this arm proves nothing', from: m.from });
        continue;
      }
      const r = runMutant();
      const failed = (r.summary && r.summary.failed) || [];
      const missing = m.expect.filter((frag) => !failed.some((f) => f.includes(frag)));
      check(`MUTANT ${m.name}: turns the ${m.expect.length} check(s) it should RED (${m.file})`,
        r.exit !== 0 && Boolean(r.summary) && r.summary.pass === false && missing.length === 0,
        { exit: r.exit, expected: m.expect, missing, redCount: failed.length, failed: failed.slice(0, 8) });
    }
  } finally {
    fs.rmSync(MUTANT_DIR, { recursive: true, force: true });
  }
}

// ── the probe ────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  const roots = [];
  const mkroot = () => { const r = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-agentthread-')); roots.push(r); return r; };

  // 1 — THE GATE READERS, in isolation. `absent → autonomous` is the ratified default and the
  //     single most consequential line of the feature, so it is read directly as well as
  //     through the ferry: an unreadable file, a missing file and an unknown word are ONE
  //     answer, and only the exact word `interactive` is the other.
  {
    const root = mkroot();
    const { goalDir } = seedGoal(root, 'goal-modes', {
      executionMode: null,
      // `seat-quoted` and `seat-commented` are the review's F3 fixture: two spellings a human
      // writes and `yaml.safe_load` (therefore `component-lint`) reads as TRUE.
      seats: {
        'seat-yes': 'yes', 'seat-true': 'TRUE', 'seat-no': 'no', 'seat-blank': null, owner: 'yes',
        'seat-quoted': '"yes"', 'seat-commented': 'yes # ratified 2026-08-09',
      },
      fallbacks: { 'seat-quoted': 'block-and-queue', 'seat-commented': 'park' },
    });
    const absent = goalExecutionMode(root, 'goal-modes');
    fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goal-modes', 'execution-mode'), '  Interactive \n');
    const interactive = goalExecutionMode(root, 'goal-modes');
    fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goal-modes', 'execution-mode'), 'paused\n');
    const junk = goalExecutionMode(root, 'goal-modes');
    check('gate 2: an ABSENT execution-mode file reads as autonomous (the ratified default), a junk word too, and only `interactive` (trimmed, case-insensitive) opens it',
      absent === 'autonomous' && junk === 'autonomous' && interactive === 'interactive'
      && goalExecutionMode(root, 'goal-never-scaffolded') === 'autonomous',
      { absent, interactive, junk });

    // C-4 (owner-ruled 2026-08-10): the file is the per-run posture, `goal-kind` the birth
    // attribute. All three rungs on ONE hermetic goal folder, and the middle rung is the fix.
    {
      const kroot = mkroot();
      const kdir = path.join(kroot, '.rbtv', 'goals', 'goal-kind');
      fs.mkdirSync(kdir, { recursive: true });
      fs.writeFileSync(path.join(kdir, 'goal.md'), '---\nname: goal-kind\ngoal-kind: interactive\n---\nbody\n');
      const fallback = goalExecutionMode(kroot, 'goal-kind');            // rung 2 — no file
      fs.writeFileSync(path.join(kdir, 'execution-mode'), 'autonomous\n');
      const fileWins = goalExecutionMode(kroot, 'goal-kind');            // rung 1 — file overrides
      fs.unlinkSync(path.join(kdir, 'execution-mode'));
      fs.writeFileSync(path.join(kdir, 'goal.md'), '---\nname: goal-kind\ngoal-kind: non-interactive\n---\nbody\n');
      const nonInteractive = goalExecutionMode(kroot, 'goal-kind');      // rung 3 — other value
      fs.writeFileSync(path.join(kdir, 'goal.md'), '---\nname: goal-kind\n---\nbody\n');
      const noKey = goalExecutionMode(kroot, 'goal-kind');               // rung 3 — no key
      fs.writeFileSync(path.join(kdir, 'goal.md'), 'no frontmatter here\n');
      const noFm = goalExecutionMode(kroot, 'goal-kind');                // rung 3 — no frontmatter
      fs.writeFileSync(path.join(kdir, 'goal.md'), '---\ngoal-kind: interactive # the owner is in the room\n---\n');
      const commented = goalExecutionMode(kroot, 'goal-kind');           // rung 2 — lint agreement
      check('gate 2 THE THREE-RUNG LADDER: an `execution-mode` file WINS (per-run posture beats birth attribute); ABSENT falls back to `goal-kind: interactive` in goal.md (a trailing YAML comment does not defeat it); and neither resolving — other value, no key, no frontmatter, no goal.md — is `autonomous`',
        fallback === 'interactive' && fileWins === 'autonomous' && commented === 'interactive'
        && nonInteractive === 'autonomous' && noKey === 'autonomous' && noFm === 'autonomous'
        && goalExecutionMode(kroot, 'goal-nothing-at-all') === 'autonomous',
        { fallback, fileWins, commented, nonInteractive, noKey, noFm });
    }

    check('gate 1: `yes`/`true` declare a seat human-interactive; `no`, a missing line, and a missing descriptor do not',
      seatIsHumanInteractive(goalDir, 'seat-yes') === true
      && seatIsHumanInteractive(goalDir, 'seat-true') === true
      && seatIsHumanInteractive(goalDir, 'seat-no') === false
      && seatIsHumanInteractive(goalDir, 'seat-blank') === false
      && seatIsHumanInteractive(goalDir, 'seat-absent') === false,
      {});

    // ⚑ THE TWO READERS OF ONE FILE MUST NOT DISAGREE (review F3). `component-lint` validates a seat
    // descriptor with `yaml.safe_load`, for which `"yes"` and `yes # comment` are both TRUE. Before
    // this arm gate 1 read BOTH as false, and the failure hid itself twice over: the seat was
    // lint-green, its rows PARKED looking correctly gated, and the lane watch's undeclared-arm warn
    // could not fire either — so the declared arm never executed and nothing said so. The
    // `fallback:` reader beside it already stripped both, which is what made the divergence a bug
    // rather than a convention.
    check('gate 1 agrees with the LINTER on the two spellings a human writes: `human-interactive: "yes"` and `yes # trailing comment` both declare the seat — quotes and comments stripped, exactly as the arm reader and `goal-kind` already strip them',
      seatIsHumanInteractive(goalDir, 'seat-quoted') === true
      && seatIsHumanInteractive(goalDir, 'seat-commented') === true
      && seatFallback(goalDir, 'seat-quoted') === 'block-and-queue'
      && seatFallback(goalDir, 'seat-commented') === 'park',
      { quoted: seatIsHumanInteractive(goalDir, 'seat-quoted'), commented: seatIsHumanInteractive(goalDir, 'seat-commented') });

    check('gate 1 reads a seat NAME, never a path — a traversing `from:` token resolves nothing',
      seatIsHumanInteractive(goalDir, '../../seat-yes') === false && seatIsHumanInteractive(goalDir, 'seats/seat-yes') === false, {});

    // `owner` is an ADDRESS, never a seat (`d-agents-address-owner-not-master`). A run that
    // materialized a seat folder called `owner` — declaring the flag, so only the reservation can
    // refuse it — must not make the bus's owner address resolvable as a seat, on either reader.
    check('`owner` is RESERVED: it is refused as a seat name by the gate-1 reader and by resolveGoalSeat, even with the flag declared',
      seatIsHumanInteractive(goalDir, 'owner') === false
      && isSafeName('owner') === false && isSafeName('goal-owner') === true
      && resolveGoalSeat(root, 'goal-modes', 'owner').reason === 'owner-is-reserved',
      { resolve: resolveGoalSeat(root, 'goal-modes', 'owner') });

    // The flag lives in FRONTMATTER. An unscoped read would let a seat's PROSE — a briefing line
    // that quotes the flag, or a copy of this very rule — open gate 1 for a seat nobody declared.
    fs.writeFileSync(path.join(goalDir, 'seats', 'seat-blank', 'seat.md'),
      '---\nseat: seat-blank\n---\n\nThe protocol says to write `human-interactive: yes` in frontmatter.\nhuman-interactive: yes\n');
    check('gate 1 is scoped to the FRONTMATTER block — the same line in the descriptor BODY does not open it',
      seatIsHumanInteractive(goalDir, 'seat-blank') === false, {});
  }

  // 2 — THE GOAL'S MODE NO LONGER DECIDES ANYTHING [D24]. This arm used to pin the opposite:
  //     an AUTONOMOUS goal PARKED its owner-bound rows, which is how work-content questions died
  //     in silence. Interactivity is a per-seat property now, so the goal can no longer mute a
  //     seat — and the pair below is what makes that a measurement rather than an assumption:
  //     the same row, same seat, with `interactive` on disk, travels IDENTICALLY.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-auto', { executionMode: null, seats: { leader: 'yes' } });
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, logs });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-auto');
    await a.bridge.busFerry.tick();                       // first sight → cursor at tail
    const postsBefore = a.slack.posted.length;

    append(file, msgRow(2, 'leader', 'owner', 'ask', 'ruling needed — may I ping the owner?'));
    // Beside it, the row the ruling says this ferry must NEVER carry — same seat, same pass. The
    // ADDRESS is the only discriminator left: the `to: owner` row travels, the `to: master` row
    // was never this ferry's business at all. Arm 4 is the other half of that pair.
    append(file, msgRow(3, 'leader', 'master', 'ask', 'MASTER-ADDRESSED with the gates shut'));
    await a.bridge.busFerry.tick();
    // ⚑ THE PARK IS MEASURED BY ITS ABSENCE FROM THE LOG, not by a count of a message that no
    // longer exists: `/PARK/i` over every line the pass emitted. A future re-introduction of any
    // park — under any wording — reddens this the moment it logs.
    const parked = logs.filter((l) => /PARK/i.test(l.message));
    check('D24 (the goal mode is DEAD): on an AUTONOMOUS goal the owner-bound row TRAVELS — posted into the goal channel, NOTHING parked, cursor advanced past both rows',
      a.slack.postsIn(reg.channelId).length === 1 && /#2/.test(a.slack.postsIn(reg.channelId)[0].text)
      && a.slack.postsIn(DM).length === 0
      && a.bridge.busFerry._cursors.get('goal-auto/2026-08-03a') === 3
      && parked.length === 0,
      { posted: a.slack.posted.length, channelPosts: a.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]), cursor: a.bridge.busFerry._cursors.get('goal-auto/2026-08-03a'), parked });
    check('RULING (autonomous goal): the `to: master` row beside it is not posted anywhere — the ADDRESS, not a gate, is what keeps it off this ferry',
      a.slack.posted.length === postsBefore + 1
      && !a.slack.posted.some((p) => /MASTER-ADDRESSED/.test(p.text))
      && addressesOwner('owner') === true && addressesOwner('master') === false
      && addressesOwner('owner, leader') === true && addressesOwner('goal-owner') === false,
      { posted: a.slack.posted.map((p) => p.text.split('\n')[0]) });
    check('the travelling row mints NOTHING — a delivered agent-thread row is not a session-create',
      a.forwarder.enqueued.length === 0, { enqueued: a.forwarder.enqueued.length });
    a.bridge.stop();

    // THE PAIR: flip the goal to `interactive` and the NEXT row travels THE SAME WAY. Under the
    // deleted gate this pair was the discriminator between park and travel; it is now the proof
    // that the word on disk changes nothing at all — and it still fails against a ferry that
    // ferries nothing, or one that has lost the agent-thread leg.
    fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goal-auto', 'execution-mode'), 'interactive\n');
    const b = makeBridge({ workspaceRoot: root, slack: a.slack, forwarder: a.forwarder });
    await b.bridge.start();
    b.bridge.busFerry._cursors.set('goal-auto/2026-08-03a', 3);
    append(file, msgRow(4, 'leader', 'owner', 'ask', 'now that the goal is interactive'));
    await b.bridge.busFerry.tick();
    check('D24 PAIR: with `interactive` on disk the same row from the same seat travels into the goal channel exactly as it did under `autonomous` — the goal-level mode word decides nothing',
      b.slack.postsIn(reg.channelId).length === 2 && /#4/.test(b.slack.postsIn(reg.channelId)[1].text),
      { channelPosts: b.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]) });
    b.bridge.stop();
  }

  // 3 — THE SEAT FLAG NO LONGER SWALLOWS A ROW [T2-R17, D-7-ruling]. `human-interactive:` used to
  //     PARK the rows of any seat that did not declare it — which is every autonomous seat, i.e.
  //     exactly the ones whose questions nobody was watching for. A non-interact seat's
  //     work-content question is now an ask that REACHES the owner; what the flag still governs is
  //     the seat's own SEND door ([T2-R14], `ask-thread.js#postAsk`), not this ferry's disposition.
  {
    const root = mkroot();
    const { file, goalDir } = seedGoal(root, 'goal-seatflag', { seats: { leader: null, 'chief-of-staff': 'no' } });
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, logs });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-seatflag');
    await a.bridge.busFerry.tick();

    append(file, msgRow(2, 'leader', 'owner', 'ask', 'undeclared seat'));
    append(file, msgRow(3, 'chief-of-staff', 'owner', 'ask', 'seat declaring human-interactive: no'));
    await a.bridge.busFerry.tick();
    const parked = logs.filter((l) => /PARK/i.test(l.message));
    check('T2-R17: a seat with no `human-interactive:` line and a seat declaring `no` BOTH TRAVEL — each into its own thread in the goal channel, with NOTHING parked',
      a.slack.postsIn(reg.channelId).length === 2
      && /#2/.test(a.slack.postsIn(reg.channelId)[0].text) && /#3/.test(a.slack.postsIn(reg.channelId)[1].text)
      && parked.length === 0
      && a.bridge.busFerry._cursors.get('goal-seatflag/2026-08-03a') === 3,
      { channelPosts: a.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]), parked: parked.map((l) => l.message) });

    // THE PAIR: declare the seat and its next row travels the SAME WAY. The seat is the same seat.
    fs.writeFileSync(path.join(goalDir, 'seats', 'leader', 'seat.md'),
      '---\nseat: leader\nhuman-interactive: yes\n---\nbody\n');
    append(file, msgRow(4, 'leader', 'owner', 'ask', 'now declared'));
    await a.bridge.busFerry.tick();
    check('T2-R17 PAIR: declaring `human-interactive: yes` on that seat changes NOTHING here — its next row travels exactly as the undeclared ones did, and it lands on the SAME thread the undeclared row anchored',
      a.slack.postsIn(reg.channelId).length === 3 && /#4/.test(a.slack.postsIn(reg.channelId)[2].text)
      && a.slack.postsIn(reg.channelId)[2].threadTs === a.slack.postsIn(reg.channelId)[0].ts,
      { channelPosts: a.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]) });
    a.bridge.stop();
  }

  // 4 — THE THREAD ITSELF: one per (goal, agent). The first row ANCHORS it top-level with the
  //     agent's name leading the header; the agent's next row REPLIES on that anchor; a
  //     DIFFERENT agent anchors its OWN thread. And no sitting is minted by any of it.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-threads', { seats: { leader: 'yes', engineer: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-threads');
    await a.bridge.busFerry.tick();

    append(file, msgRow(2, 'leader', 'owner', 'ask', 'which branch shape do you want?'));
    await a.bridge.busFerry.tick();
    const anchor = a.slack.postsIn(reg.channelId)[0];
    check('the first row from an agent ANCHORS a thread: posted TOP-LEVEL in the goal channel, header led by the agent name',
      Boolean(anchor) && anchor.threadTs === null
      && anchor.text === `*🧵 leader* — goal-threads · ask · #2\nwhich branch shape do you want?`
      && a.bridge.agentThreadFor('goal-threads', 'leader') === anchor.ts,
      { anchor, mapped: a.bridge.agentThreadFor('goal-threads', 'leader') });
    check('the anchor post mints NO sitting — the agent already exists; only the owner\'s reply seats anything',
      a.forwarder.enqueued.length === 0, { enqueued: a.forwarder.enqueued.map((e) => e.payload.job_id) });
    check('nothing was posted to the owner DM — a gated row goes to the agent\'s thread, not the DM queue',
      a.slack.postsIn(DM).length === 0, { dmPosts: a.slack.postsIn(DM).length });

    append(file, msgRow(3, 'leader', 'owner', 'note', 'second row, same agent'));
    append(file, msgRow(4, 'engineer', 'owner', 'ask', 'a different agent asking'));
    // The GATES-OPEN half of the ruling's pair: this goal is interactive and `leader` declares the
    // flag, so the only thing standing between this row and the owner's thread is its ADDRESS.
    append(file, msgRow(5, 'leader', 'master', 'ask', 'MASTER-ADDRESSED with both gates OPEN'));
    await a.bridge.busFerry.tick();
    const chanPosts = a.slack.postsIn(reg.channelId);
    check('the SAME agent\'s next row replies on the SAME thread (from-keyed), while a DIFFERENT agent anchors its own',
      chanPosts.length === 3
      && chanPosts[1].threadTs === anchor.ts
      && chanPosts[2].threadTs === null
      && a.bridge.agentThreadFor('goal-threads', 'engineer') === chanPosts[2].ts
      && a.bridge.agentThreadFor('goal-threads', 'engineer') !== anchor.ts,
      { threadTsSeen: chanPosts.map((p) => p.threadTs), map: [...a.bridge._agentThreads.entries()] });
    check('the map keys on (goal, agent) only — no run id anywhere in it',
      [...a.bridge._agentThreads.keys()].sort().join(',') === 'goal-threads#engineer,goal-threads#leader',
      { keys: [...a.bridge._agentThreads.keys()] });
    check('RULING (gates OPEN): the `to: master` row still reaches NOTHING — no channel post, no DM, no thread of its own',
      chanPosts.length === 3 && a.slack.postsIn(DM).length === 0
      && !a.slack.posted.some((p) => /MASTER-ADDRESSED/.test(p.text))
      && a.bridge.busFerry._cursors.get('goal-threads/2026-08-03a') === 5,
      { channelPosts: chanPosts.length, cursor: a.bridge.busFerry._cursors.get('goal-threads/2026-08-03a') });
    a.bridge.stop();
  }

  // 4b — THE SEAT'S FALLBACK ARM EXECUTES (task 7.626, owner ruling
  //      `d-s19-fallback-rides-goal-channels`). FOUR seats, ONE interactive goal, ONE pass, both
  //      gates OPEN on every one of them — so the only thing that differs between the four rows is
  //      the word in each seat's own `fallback:` frontmatter. That is what makes this a measurement
  //      of the ARM rather than a re-measurement of the gates.
  {
    const root = mkroot();
    const { file, goalDir } = seedGoal(root, 'goal-arms', {
      seats: { parker: 'yes', discloser: 'yes', blocker: 'yes', undeclared: 'yes' },
      fallbacks: { parker: 'park', discloser: 'default-and-disclose', blocker: 'block-and-queue' },
    });
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, logs });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-arms');
    await a.bridge.busFerry.tick();                       // first sight → cursor at tail

    append(file, msgRow(2, 'parker', 'owner', 'ask', 'park: my question waits on the bus'));
    append(file, msgRow(3, 'discloser', 'owner', 'ask', 'default: I have proceeded on my stated default'));
    append(file, msgRow(4, 'blocker', 'owner', 'ask', 'block: which shape do you want?'));
    append(file, msgRow(5, 'undeclared', 'owner', 'ask', 'no arm declared anywhere'));
    await a.bridge.busFerry.tick();

    // ⚑ KEYED ON THE ROW ID, not just the seat. `parker` no longer posts at most once (its arm
    // stopped being a disposition), so a find-by-seat would hand every later check the FIRST
    // header that seat ever posted and each pair below would measure the wrong message.
    const headerOf = (from, id = null) => {
      const p = a.slack.postsIn(reg.channelId).find((q) => q.text.includes(`🧵 ${from}`)
        && (id === null || q.text.includes(`#${id}`)));
      return p ? p.text.split('\n')[0] : null;
    };
    const parked = () => logs.filter((l) => /PARK/i.test(l.message));
    check('ARM `park` NO LONGER PARKS [D-7-ruling]: the seat\'s row is DELIVERED into its own thread and rendered UNMARKED — `park` described an owner who could not be reached, and under thread-per-ask he can be, so the word survives as a render mark the table deliberately does not carry',
      headerOf('parker', 2) === '*🧵 parker* — goal-arms · ask · #2'
      && a.slack.postsIn(DM).length === 0 && parked().length === 0
      && a.bridge.busFerry._cursors.get('goal-arms/2026-08-03a') === 5,
      { header: headerOf('parker', 2), parked: parked().map((l) => l.message), channelPosts: a.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]) });
    check('ARM `default-and-disclose`: DELIVERED into the seat\'s own thread and MARKED as a disclosure',
      headerOf('discloser', 3) === '*🧵 discloser* — goal-arms · ask · #3 · ℹ proceeding on its default',
      { header: headerOf('discloser', 3) });
    check('ARM `block-and-queue`: DELIVERED into the seat\'s own thread and MARKED as BLOCKING — the owner\'s phone can tell a question from an FYI, which is the whole difference between the two delivered arms',
      headerOf('blocker', 4) === '*🧵 blocker* — goal-arms · ask · #4 · ⏸ WAITING ON YOU',
      { header: headerOf('blocker', 4) });
    check('NO `fallback:` IS NOT A FOURTH ARM: the row is delivered UNMARKED — the header is byte-identical to the pre-7.626 one — because a `component-lint` violation must not ACQUIRE a behaviour nobody declared',
      headerOf('undeclared', 5) === '*🧵 undeclared* — goal-arms · ask · #5',
      { header: headerOf('undeclared', 5) });
    check('none of the four minted anything — the arms change WHERE a row goes, never whether a session is born',
      a.forwarder.enqueued.length === 0, { enqueued: a.forwarder.enqueued.length });

    // ⚑ THE MARKER TABLE IS AN OWN-PROPERTY LOOKUP (review F5). `arm` reaches an EXPORTED function's
    // parameter, and `constructor` / `toString` are legal kebab-case words that walk the prototype
    // chain — a bare `TABLE[arm]` renders JS function source into the owner's Slack header. Read
    // directly rather than through a fixture: the reader is the surface that leaves the process.
    const spoofed = ['constructor', 'toString', '__proto__', 'valueOf', 'hasOwnProperty'].map((w) =>
      formatMessage({ from: 'x', type: 'ask', id: 9, body: 'b' },
        { goalId: 'g', stamp: 's', relPath: 'p', agentLead: true, arm: w }));
    check('a bogus arm renders NO marker and no prototype text — `constructor`, `toString`, `__proto__` and friends all produce the plain unmarked header',
      spoofed.every((t) => t.split('\n')[0] === '*🧵 x* — g · ask · #9'),
      { headers: spoofed.map((t) => t.split('\n')[0]) });
    const asked = formatMessage({ from: 'x', type: 'ask', id: 1, body: 'q' },
      { goalId: 'g', stamp: 's', relPath: 'p', agentLead: true, ownerUser: USER });
    const noted = formatMessage({ from: 'x', type: 'note', id: 2, body: 'n' },
      { goalId: 'g', stamp: 's', relPath: 'p', agentLead: true, ownerUser: USER });
    check('an ask in the agent thread pings the owner; a non-ask does not',
      asked.includes(`<@${USER}>`) && !noted.includes(`<@${USER}>`),
      { asked: asked.split('\n')[0], noted: noted.split('\n')[0] });

    // FRONTMATTER ONLY, `seatIsHumanInteractive`'s rule for the same reason: a briefing line that
    // QUOTES the arm must not be able to silence a seat nobody declared silent.
    fs.writeFileSync(path.join(goalDir, 'seats', 'undeclared', 'seat.md'),
      // AT COLUMN 0, deliberately: the reader's regex is line-anchored, so a quoted-mid-sentence
      // mention would be missed by an UNSCOPED reader too and the arm would pass either way.
      '---\nseat: undeclared\nhuman-interactive: yes\n---\nthe procedure below states this seat\'s arm:\nfallback: park\n');
    append(file, msgRow(6, 'undeclared', 'owner', 'note', 'the arm is only in my prose'));
    await a.bridge.busFerry.tick();
    // ⚑ MEASURED ON THE READER NOW, not on a park. With the rung deleted the row travels either
    // way, so "did the BODY line take effect?" is answered where the arm is actually resolved:
    // `seatFallback` must still return null for this seat, and the delivered header must carry no
    // mark. An unscoped reader would resolve `park` here — and `park` renders no mark either, so
    // the reader assertion is the discriminating half and the header is the corroboration.
    check('the arm is read from the FRONTMATTER BLOCK ONLY — `fallback: park` in the descriptor BODY resolves to NO arm, and the row is delivered unmarked',
      seatFallback(goalDir, 'undeclared') === null,
      { resolved: seatFallback(goalDir, 'undeclared'), channelPosts: a.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]) });
    check('and that BODY-declared row still TRAVELS, unmarked, into the seat\'s own thread',
      headerOf('undeclared', 6) === '*🧵 undeclared* — goal-arms · note · #6' && parked().length === 0,
      { header: headerOf('undeclared', 6), parked: parked().length });

    // THE PAIR for `park`: change that ONE word on that ONE seat and its next row travels. Without
    // it the park check above would pass just as well against a ferry that ferries nothing at all.
    fs.writeFileSync(path.join(goalDir, 'seats', 'parker', 'seat.md'),
      '---\nseat: parker\nhuman-interactive: yes\nfallback: default-and-disclose\n---\nbody\n');
    append(file, msgRow(7, 'parker', 'owner', 'ask', 'arm flipped, same seat, same goal'));
    await a.bridge.busFerry.tick();
    check('MUTATION (the arm): flipping that seat\'s ONE word from `park` to `default-and-disclose` MARKS its next row as a disclosure — the arm is now a render mark and this is the pair that proves the mark is read from the seat',
      headerOf('parker', 7) === '*🧵 parker* — goal-arms · ask · #7 · ℹ proceeding on its default'
      && headerOf('parker', 2) === '*🧵 parker* — goal-arms · ask · #2',
      { flipped: headerOf('parker', 7), before: headerOf('parker', 2) });

    // BLOCK-AND-QUEUE, END TO END — ask → the owner's thread → his answer → the seat proceeds.
    // The last leg is the one that ALREADY EXISTED (§ 7 measures it in isolation): the owner's
    // reply in the agent's thread mints a session at THAT SEAT's own home with his answer as the
    // prompt. That revival IS "the seat proceeds", and it is why this row shipped a marker and a
    // gate rung rather than a hold mechanism nobody ruled.
    const blockerThread = a.bridge.agentThreadFor('goal-arms', 'blocker');
    const reply = await a.bridge.onChatMessage(msg({ channel: reg.channelId, ts: '11.1', threadTs: blockerThread, text: 'the second shape' }));
    const create = a.forwarder.creates()[0];
    check('BLOCK-AND-QUEUE END TO END: the ask reached the blocker\'s OWN thread, the owner answered IN it, and that answer minted a session AT THE BLOCKER\'S SEAT carrying his words — the seat proceeds',
      Boolean(blockerThread) && reply.forwarded === true && reply.leg === 'session-create' && reply.route === 'agent'
      && Boolean(create) && create.payload.args.workdir === path.join(goalDir, 'seats', 'blocker')
      && String(create.payload.args.prompt).endsWith('the second shape'),
      { blockerThread, reply, workdir: create && create.payload.args.workdir });
    a.bridge.stop();
  }

  // 5 — NO CHANNEL: THE ROW IS HELD, THE OWNER IS TOLD, AND A CHANNEL CREATED AFTER BOOT IS
  //     RE-RESOLVED (owner ruling 2026-08-12). Three claims, one incident:
  //       (a) the row does NOT fall back to the owner's DM and mints NOTHING. The old fallback
  //           posted the row to the DM and minted a channel-master sitting with it as the prompt,
  //           so a question addressed to the HUMAN was answered by an agent.
  //       (b) after `NOTICE_AT_ATTEMPT` failed passes the owner gets ONE notice that names the
  //           goal and the seat and carries NO part of the row — and seats nobody.
  //       (c) the miss re-asks SLACK. The in-memory map is filled by `recover()` at boot only,
  //           and every goal channel is created by a throwaway CLI subprocess this process never
  //           sees — which is the whole incident: a channel created 9h after boot read as absent.
  //           `createChannel` straight on the fake IS that subprocess.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-unmapped', { seats: { leader: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();                                  // NOTE: no registerGoal
    await a.bridge.busFerry.tick();
    const listsAtStart = a.slack.lists;
    append(file, msgRow(2, 'leader', 'owner', 'ask', 'no channel for this goal'));
    await a.bridge.busFerry.tick();
    check('(a) gates pass but the goal has NO channel → NOTHING is posted anywhere, NOTHING is minted, and the cursor does NOT advance — the row is held, never downgraded into the owner\'s DM',
      a.slack.posted.length === 0 && a.forwarder.creates().length === 0
      && a.bridge.busFerry._cursors.get('goal-unmapped/2026-08-03a') === 1,
      { posted: a.slack.posted.map((p) => p.text.split('\n')[0]), creates: a.forwarder.creates().length,
        cursor: a.bridge.busFerry._cursors.get('goal-unmapped/2026-08-03a') });
    check('(c) and the miss ASKED SLACK rather than trusting the map — one conversations.list walk per attempt',
      a.slack.lists > listsAtStart, { lists: a.slack.lists, before: listsAtStart });

    await a.bridge.busFerry.tick();
    await a.bridge.busFerry.tick();                          // attempt 3 → the notice
    const notices = a.slack.postsIn(DM);
    check('(b) at the third failed pass the owner is told the CHANNEL is missing — ONE notice, naming the goal and the seat, carrying no part of the row, minting nothing',
      notices.length === 1 && /goal-unmapped/.test(notices[0].text) && /leader/.test(notices[0].text)
      && !/no channel for this goal/.test(notices[0].text) && a.forwarder.creates().length === 0,
      { notices: notices.map((p) => p.text), creates: a.forwarder.creates().length });
    await a.bridge.busFerry.tick();
    check('(b) and ONCE is once — a fourth failed pass adds no second notice',
      a.slack.postsIn(DM).length === 1, { notices: a.slack.postsIn(DM).length });

    // (c) THE REPAIR: the channel appears out of band, exactly as the daemon's throwaway
    // `goal-channel-cli.js ensure` subprocess creates it — nothing tells this process.
    await a.slack.createChannel({ name: `${PREFIX}goal-unmapped` });
    await a.bridge.busFerry.tick();
    const channelId = a.bridge.goalChannels.channelForGoal('goal-unmapped');
    check('(c) THE FIX: the next pass re-resolves the new channel from Slack, binds it, and the HELD row lands in the agent\'s own thread there — no DM, no sitting',
      Boolean(channelId) && a.slack.postsIn(channelId).length === 1
      && /no channel for this goal/.test(a.slack.postsIn(channelId)[0].text)
      && a.slack.postsIn(DM).length === 1 && a.forwarder.creates().length === 0
      && a.bridge.busFerry._cursors.get('goal-unmapped/2026-08-03a') === 2,
      { channelId, channelPosts: a.slack.postsIn(channelId || 'none').map((p) => p.text.split('\n')[0]),
        cursor: a.bridge.busFerry._cursors.get('goal-unmapped/2026-08-03a') });
    a.bridge.stop();
  }

  // 5b — SLACK DID NOT ANSWER IS NOT "THE CHANNEL IS MISSING" (review D1/D3). A rate-limited
  //      `conversations.list` resolves nothing, and the old shape reported that as `no-channel` —
  //      which would fire the notice above and tell the owner to create a channel that exists.
  //      Held and retried, loudly, with NO notice: the four passes take the row past
  //      `NOTICE_AT_ATTEMPT`, so a notice keyed on the wrong reason would already have posted.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-ratelimited', { seats: { leader: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    await a.bridge.busFerry.tick();
    // The channel EXISTS — the only thing wrong is that Slack will not say so.
    await a.slack.createChannel({ name: `${PREFIX}goal-ratelimited` });
    a.slack.failNextLists(4);
    append(file, msgRow(2, 'leader', 'owner', 'ask', 'the lookup will fail'));
    for (let i = 0; i < 4; i++) await a.bridge.busFerry.tick();
    check('a FAILED lookup is `resolve-failed`, not `no-channel`: the row is held and retried past the notice threshold with NOTHING posted anywhere — no false "create the channel" DM',
      a.slack.posted.length === 0 && a.forwarder.creates().length === 0
      && a.bridge.busFerry._cursors.get('goal-ratelimited/2026-08-03a') === 1,
      { posted: a.slack.posted.map((p) => p.text.split('\n')[0]), lists: a.slack.lists,
        cursor: a.bridge.busFerry._cursors.get('goal-ratelimited/2026-08-03a') });
    // THE PAIR: the same row, the same channel, once Slack answers.
    await a.bridge.busFerry.tick();
    const channelId = a.bridge.goalChannels.channelForGoal('goal-ratelimited');
    check('and the retry delivers the moment Slack answers — so "held" above is the rate limit, not a ferry that ferries nothing',
      Boolean(channelId) && a.slack.postsIn(channelId).length === 1
      && a.slack.postsIn(DM).length === 0
      && a.bridge.busFerry._cursors.get('goal-ratelimited/2026-08-03a') === 2,
      { channelId, posts: a.slack.postsIn(channelId || 'none').map((p) => p.text.split('\n')[0]) });
    a.bridge.stop();
  }

  // 6 — THE INBOUND ROUTE. Only a thread THIS bridge anchored resolves as 'agent'; everything
  //     else in a goal channel stays 'goal' on the channel-as-conversation (d-channel-per-goal).
  {
    const root = mkroot();
    seedGoal(root, 'goal-route', { seats: { leader: 'yes', 'goal-master': 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-route');
    // The map is seeded through the bridge's own entry point — no gates involved, because
    // this arm is about ROUTING and gating is arm 2/3's claim.
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-route', agent: 'leader', text: 'ask' });
    const anchorTs = opened.ts;

    const inThread = a.bridge.routeOf(msg({ channel: reg.channelId, ts: '9.1', threadTs: anchorTs }));
    const otherThread = a.bridge.routeOf(msg({ channel: reg.channelId, ts: '9.2', threadTs: '999.9' }));
    const topLevel = a.bridge.routeOf(msg({ channel: reg.channelId, ts: '9.3' }));
    const otherGoal = a.bridge.routeOf(msg({ channel: 'C_UNMAPPED', ts: '9.4', threadTs: anchorTs }));
    check('a reply inside an anchored agent thread routes as kind `agent`, carrying the agent name, on the thread as conversation',
      inThread && inThread.kind === 'agent' && inThread.agent === 'leader' && inThread.goalId === 'goal-route'
      && inThread.conversationId === `${reg.channelId}:${anchorTs}`,
      { inThread });
    check('an UNKNOWN thread in the same goal channel, and an unthreaded message, both stay kind `goal` with the CHANNEL as conversation',
      otherThread && otherThread.kind === 'goal' && otherThread.conversationId === reg.channelId
      && topLevel && topLevel.kind === 'goal' && topLevel.conversationId === reg.channelId,
      { otherThread, topLevel });
    check('the resolution is goal-scoped — the same thread_ts in an unmapped channel is not an agent thread',
      otherGoal === null, { otherGoal });
    a.bridge.stop();
  }

  // 7 — THE OWNER'S REPLY REACHES THE ASKING SEAT, with no relay in the middle: a
  //     session-create homed at THAT AGENT's seat dir (revive), then a follow-up on its chain.
  {
    const root = mkroot();
    const { goalDir } = seedGoal(root, 'goal-reply', { seats: { leader: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-reply');
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-reply', agent: 'leader', text: 'ask' });

    const first = await a.bridge.onChatMessage(msg({ channel: reg.channelId, ts: '10.1', threadTs: opened.ts, text: 'use the second shape' }));
    const create = a.forwarder.creates()[0];
    const seatDir = path.join(goalDir, 'seats', 'leader');
    const CORRELATION_PREFIX = /^chat-thread: [A-Z][A-Z0-9_]{2,}(?::\d+\.\d+)?\n\n/;
    // ⚑ "on the goal profile" RETIRED 2026-08-11 (owner ruling D2): `goal_profile` is deleted and
    // every surface carries the one non-deciding `session_profile`. HOMED AT THE ASKING SEAT is
    // the claim that mattered here and it is untouched — the workdir is what makes the owner's
    // reply reach the asker, and it is what the daemon then resolves the seat's cast FROM.
    check('the owner\'s reply mints a session-create HOMED AT THE ASKING SEAT, naming NO execution',
      first.forwarded === true && first.leg === 'session-create' && first.route === 'agent'
      && Boolean(create) && create.payload.args.workdir === seatDir && !('profile' in create.payload.args)
      && create.payload.session_mode === 'headless',
      { first, workdir: create && create.payload.args.workdir, expected: seatDir });
    check('the prompt is the owner\'s BARE text behind the ONE correlation line — no behavioural text on this leg either',
      Boolean(create)
      && String(create.payload.args.prompt) === `chat-thread: ${reg.channelId}:${opened.ts}\n\nuse the second shape`
      && String(create.payload.args.prompt).replace(CORRELATION_PREFIX, '') === 'use the second shape',
      { prompt: create && create.payload.args.prompt });

    const second = await a.bridge.onChatMessage(msg({ channel: reg.channelId, ts: '10.2', threadTs: opened.ts, text: 'and one more thing' }));
    check('a SECOND reply in that thread continues the seat\'s chain (send-message), never a second session',
      second.forwarded === true && second.leg === 'follow-up'
      && a.forwarder.creates().length === 1 && a.forwarder.sends().length === 1
      && a.forwarder.sends()[0].payload.args.thread === `exec-${create.jobId}`
      && a.forwarder.sends()[0].payload.args.corpus === 'and one more thing',
      { second, creates: a.forwarder.creates().length, sends: a.forwarder.sends().map((e) => e.payload.args) });
    a.bridge.stop();
  }

  // 8 — THE SEAT IS GONE (its run closed, or the seat was never materialized under the goal's
  //     currently-open run). Nothing is enqueued and the owner is told IN THAT THREAD — silence
  //     there reads as the agent ignoring him.
  {
    const root = mkroot();
    const { goalDir } = seedGoal(root, 'goal-ghost', { seats: { ghost: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-ghost');
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-ghost', agent: 'ghost', text: 'ask' });
    fs.rmSync(path.join(goalDir, 'seats', 'ghost'), { recursive: true, force: true }); // the seat leaves

    const res = await a.bridge.onChatMessage(msg({ channel: reg.channelId, ts: '11.1', threadTs: opened.ts, text: 'still there?' }));
    const last = a.slack.posted[a.slack.posted.length - 1];
    check('a reply to an agent whose seat is GONE enqueues nothing and posts the fixed no-agent-seat notice in that same thread',
      res.forwarded === false && res.reason === 'no-agent-seat:seat-missing'
      && a.forwarder.enqueued.length === 0
      && Boolean(last) && last.text === NO_AGENT_SEAT_NOTICE && last.channel === reg.channelId && last.threadTs === opened.ts,
      { res, last });
    a.bridge.stop();
  }

  // 9 — THE RETURN LEG INTO A GOAL CHANNEL. A row NAMING a goal-channel thread is posted there
  //     VERBATIM and mints NOTHING — a `kind: 'master'` sitting on a goal channel would be the
  //     wrong seat. And it flows with BOTH GATES SHUT, because it is not agent-initiated: it
  //     answers into a thread the owner wrote in.
  {
    const root = mkroot();
    const { file, goalDir } = seedGoal(root, 'goal-return', { executionMode: null, seats: { leader: null } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-return');
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-return', agent: 'leader', text: 'ask' });
    await a.bridge.busFerry.tick();
    const before = a.slack.posted.length;

    append(file, msgRow(2, 'leader', 'channel-master', 'answer',
      `here is the answer\n\n[chat-thread: ${reg.channelId}:${opened.ts}]`));
    await a.bridge.busFerry.tick();
    const posted = a.slack.posted[a.slack.posted.length - 1];
    check('a row naming a GOAL-CHANNEL thread is posted into that thread verbatim, with NO sitting minted',
      a.slack.posted.length === before + 1
      && posted.channel === reg.channelId && posted.threadTs === opened.ts
      && posted.text === `*bus → you* — goal-return/2026-08-03a · from leader · answer · #2\nhere is the answer\n\n[chat-thread: ${reg.channelId}:${opened.ts}]`
      && a.forwarder.creates().length === 0,
      { posted, creates: a.forwarder.creates().length });
    check('and it flowed with BOTH GATES SHUT (mode absent, seat undeclared) — an owner-initiated leg is never gated',
      goalExecutionMode(root, 'goal-return') === 'autonomous' && seatIsHumanInteractive(goalDir, 'leader') === false
      && a.bridge.busFerry._cursors.get('goal-return/2026-08-03a') === 2,
      { cursor: a.bridge.busFerry._cursors.get('goal-return/2026-08-03a') });

    // THE CONTROL: a token naming a KNOWN DM thread still mints the channel-master sitting.
    // Without it, the guard above could be passing because the return leg mints nothing ANYWHERE.
    //
    // ⚑ THE THREAD IS MADE KNOWN THE ONLY WAY THAT COUNTS SINCE S-13 — by the owner actually
    // writing in it. A DM inbound sets the reply address and mints the conversation, and it is
    // THAT id the row names. A fabricated DM id would now be ignored (arm 10), which is exactly
    // why this control had to change with the ruling rather than being asserted around it (arm 10).
    await a.bridge.onChatMessage({
      chatUserId: USER, chatThreadId: `${DM}:77.7`, text: 'owner opens a DM thread',
      _channel: DM, _channelType: 'im', _threadTs: '77.7', _msgTs: '77.7', _inThread: false,
    });
    const createsBeforeControl = a.forwarder.creates().length;
    append(file, msgRow(3, 'leader', 'channel-master', 'answer', `to the DM thread\n\n[chat-thread: ${DM}:77.7]`));
    await a.bridge.busFerry.tick();
    check('CONTROL: a token naming a KNOWN DM thread STILL routes on the master leg (a sitting, no goal-channel post) — only goal-channel tokens post-and-return',
      a.forwarder.creates().length === createsBeforeControl + 1 && a.slack.postsIn(DM).length === 0
      && a.bridge.knowsThread(`${DM}:77.7`) === true,
      { creates: a.forwarder.creates().length, before: createsBeforeControl, dmPosts: a.slack.postsIn(DM).length });
    a.bridge.stop();
  }

  // 10 — S-13: THE TOKEN IS A CLAIM, NOT AN INSTRUCTION (`d-s13-chat-thread-token-verified`).
  //      A bus row is text an agent wrote. Before this ruling a named thread was obeyed on sight,
  //      so any agent could post into any Slack thread it cared to name and mint a channel-master
  //      sitting on it. Now the bridge vouches for the token against its OWN state, and an unknown
  //      one is treated as if the row carried none: NOT dropped, NOT posted to the invented thread,
  //      nothing minted — it takes the ordinary path.
  {
    const root = mkroot();
    // The ordinary path's outcome is now a DELIVERY into the seat's own anchored thread, and that
    // is what makes this arm sharper than the park it replaced: "the token was obeyed" and "the
    // row took the ordinary path" are both posts, told apart by WHICH thread they landed in.
    const { file } = seedGoal(root, 'goal-forged', { executionMode: null, seats: { leader: null } });
    const logs = [];
    const a = makeBridge({ workspaceRoot: root, logs });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-forged');
    await a.bridge.busFerry.tick();

    const forgedGoalTs = '9999.9';   // a ts in a REAL goal channel that no agent ever anchored
    check('the fabricated threads are genuinely UNKNOWN to the bridge (the premise of every check below)',
      a.bridge.knowsThread(`${reg.channelId}:${forgedGoalTs}`) === false
      && a.bridge.knowsThread(`${DM}:1.0`) === false
      && a.bridge.knowsThread('') === false && a.bridge.knowsThread('nonsense') === false,
      {});

    // (a) FABRICATED TOKEN ON A REAL GOAL CHANNEL, addressed `to: owner` → the row must take the
    //     ordinary path — a TOP-LEVEL post anchoring this seat's own thread — and NOTHING may land
    //     in the invented thread. A ferry that obeyed the token would post the same body into the
    //     same channel, so the discriminator is `threadTs`, never the post count.
    append(file, msgRow(2, 'leader', 'owner', 'ask', `forged goal-channel thread\n\n[chat-thread: ${reg.channelId}:${forgedGoalTs}]`));
    await a.bridge.busFerry.tick();
    const ignored = logs.filter((l) => /does not know/.test(l.message));
    const parked = logs.filter((l) => /PARK/i.test(l.message));
    const forged = a.slack.posted.filter((q) => q.threadTs === forgedGoalTs);
    check('S-13 (a): a FABRICATED goal-channel token posts NOTHING into the invented thread and mints NOTHING — the row falls to the ordinary path, anchoring the seat\'s OWN top-level thread instead, and nothing is parked',
      forged.length === 0 && a.forwarder.enqueued.length === 0
      && a.slack.postsIn(reg.channelId).length === 1
      && a.slack.postsIn(reg.channelId)[0].threadTs === null
      && /forged goal-channel thread/.test(a.slack.postsIn(reg.channelId)[0].text)
      && ignored.length === 1 && ignored[0].namedThread === `${reg.channelId}:${forgedGoalTs}`
      && parked.length === 0
      && a.bridge.busFerry._cursors.get('goal-forged/2026-08-03a') === 2,
      { forged: forged.length, enqueued: a.forwarder.enqueued.length, ignored: ignored.length, parked: parked.length, channelPosts: a.slack.postsIn(reg.channelId).map((q) => ({ threadTs: q.threadTs, head: q.text.split('\n')[0] })) });

    // (b) FABRICATED DM-SHAPED TOKEN → must mint NO sitting. Same row shape, different invented
    //     surface: this is the leg that used to hand an agent a channel-master sitting on demand.
    const postedBeforeB = a.slack.posted.length;
    append(file, msgRow(3, 'leader', 'channel-master', 'answer', `forged DM thread\n\n[chat-thread: ${DM}:1.0]`));
    await a.bridge.busFerry.tick();
    check('S-13 (b): a FABRICATED DM-shaped token mints NO sitting and posts NOTHING NEW — and being `to: channel-master` the row is not even owner-bound, so the ordinary path just advances the cursor',
      a.forwarder.creates().length === 0 && a.slack.posted.length === postedBeforeB
      && a.slack.postsIn(DM).length === 0
      && a.bridge.busFerry._cursors.get('goal-forged/2026-08-03a') === 3,
      { creates: a.forwarder.creates().length, postedDelta: a.slack.posted.length - postedBeforeB, dm: a.slack.postsIn(DM).length });

    // (c) THE GREEN HALF, same run, same seat: make the thread KNOWN by anchoring
    //     it through the bridge, and the very same token shape now routes verbatim into it. Without
    //     this pair, (a) and (b) would pass just as well against a ferry that had stopped reading
    //     tokens at all.
    // ⚑ A SEAT THAT HAS NO THREAD YET. `leader` anchored one in (a) — its ordinary path is a
    // delivery now, not a park — so a second `routeToAgentThread` for it would REPLY on that
    // anchor and hand this check the reply's ts, which is not a thread id at all.
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-forged', agent: 'scribe', text: 'anchor' });
    const postsBefore = a.slack.posted.length;
    append(file, msgRow(4, 'leader', 'channel-master', 'answer', `known thread\n\n[chat-thread: ${reg.channelId}:${opened.ts}]`));
    await a.bridge.busFerry.tick();
    const landed = a.slack.posted[a.slack.posted.length - 1];
    check('S-13 (c) MUTATION-PAIR: the SAME token shape naming a thread the bridge KNOWS routes verbatim into it — so (a) and (b) are the verification, not a dead return leg',
      a.slack.posted.length === postsBefore + 1
      && landed.channel === reg.channelId && landed.threadTs === opened.ts
      && /known thread/.test(landed.text) && a.forwarder.creates().length === 0,
      { landed: landed && { channel: landed.channel, threadTs: landed.threadTs } });
    a.bridge.stop();
  }

  // 11 — S-13 RESTART: the token of a pre-restart conversation is known because the STATE FILE
  //      restored it, never because the row asserted it. This is the case the deleted
  //      derive-the-address branch used to cover by trusting the token's text.
  {
    const root = mkroot();
    const stateFile = path.join(mkroot(), 'chat-state.json');
    const { file } = seedGoal(root, 'goal-restart', { executionMode: null, seats: { leader: null } });
    const daemon = makeFakeForwarder();
    const a = makeBridge({ workspaceRoot: root, stateFile, forwarder: daemon });
    await a.bridge.start();
    await a.bridge.onChatMessage({
      chatUserId: USER, chatThreadId: `${DM}:55.5`, text: 'owner opens a DM thread before the restart',
      _channel: DM, _channelType: 'im', _threadTs: '55.5', _msgTs: '55.5', _inThread: false,
    });
    await a.bridge.busFerry.tick();
    a.bridge.stop();

    // The restart: a brand-new bridge, empty maps, same file, same still-running daemon.
    const b = makeBridge({ workspaceRoot: root, stateFile, forwarder: daemon });
    check('before start() the restarted bridge knows NOTHING — so the acceptance below cannot come from memory',
      b.bridge.knowsThread(`${DM}:55.5`) === false, {});
    await b.bridge.start();
    b.bridge.busFerry._cursors.set('goal-restart/2026-08-03a', 1);
    const createsBefore = daemon.creates().length;
    append(file, msgRow(2, 'leader', 'channel-master', 'answer', `answering after the restart\n\n[chat-thread: ${DM}:55.5]`));
    await b.bridge.busFerry.tick();
    check('S-13 RESTART: the token is accepted because start() RESTORED the conversation from the state file — persistence, not trust',
      b.bridge.knowsThread(`${DM}:55.5`) === true
      && daemon.creates().length === createsBefore + 1,
      { creates: daemon.creates().length, before: createsBefore });

    // THE CONTROL: the same restart with NO state file forgets, so the same token is UNKNOWN and
    // the row takes the ordinary path — which is the honest decline, not a reason to believe it.
    const root2 = mkroot();
    const { file: file2 } = seedGoal(root2, 'goal-nostate', { executionMode: null, seats: { leader: null } });
    const c = makeBridge({ workspaceRoot: root2, stateFile: null, forwarder: makeFakeForwarder() });
    await c.bridge.start();
    await c.bridge.busFerry.tick();
    append(file2, msgRow(2, 'leader', 'channel-master', 'answer', `answering with no state file\n\n[chat-thread: ${DM}:55.5]`));
    await c.bridge.busFerry.tick();
    check('CONTROL: with no state_file the same token is UNKNOWN after a restart — nothing minted, nothing posted, cursor advanced (the amnesia is disclosed, never papered over by trusting the row)',
      c.bridge.knowsThread(`${DM}:55.5`) === false
      && c.forwarder.creates().length === 0 && c.slack.posted.length === 0
      && c.bridge.busFerry._cursors.get('goal-nostate/2026-08-03a') === 2,
      { creates: c.forwarder.creates().length, posted: c.slack.posted.length });
    b.bridge.stop(); c.bridge.stop();
  }

  // 12 — STATE. The agent threads ride the existing state file ADDITIVELY, and a restarted
  //      bridge routes the owner's reply in a pre-restart thread as 'agent' — without the map
  //      that reply would be handled as ordinary goal traffic by the goal-master.
  {
    const root = mkroot();
    const stateFile = path.join(mkroot(), 'chat-state.json');
    const { file } = seedGoal(root, 'goal-persist', { seats: { leader: 'yes' } });
    const daemon = makeFakeForwarder(); // the daemon outlives the bridge restart, as it does live
    const a = makeBridge({ workspaceRoot: root, stateFile, forwarder: daemon });
    await a.bridge.start();
    const reg = await a.bridge.registerGoal('goal-persist');
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'ask', 'before the restart'));
    await a.bridge.busFerry.tick();
    const anchorTs = a.bridge.agentThreadFor('goal-persist', 'leader');
    a.bridge.stop();

    const doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    check('the anchored thread is persisted, and the file is EXTENDED not restructured (version 1; threads + replyAddr + busFerry all still there)',
      doc.version === 1 && Boolean(anchorTs)
      && Boolean(doc.agentThreads && doc.agentThreads['goal-persist#leader'])
      && doc.agentThreads['goal-persist#leader'].threadTs === anchorTs
      && Object.prototype.hasOwnProperty.call(doc, 'threads')
      && Object.prototype.hasOwnProperty.call(doc, 'replyAddr') && Boolean(doc.busFerry),
      { keys: Object.keys(doc), agentThreads: doc.agentThreads });

    const b = makeBridge({ workspaceRoot: root, stateFile, slack: a.slack, forwarder: daemon });
    check('the restarted bridge holds NO agent threads before start()', b.bridge._agentThreads.size === 0, {});
    await b.bridge.start();
    check('start() restores the (goal, agent) → thread map from disk',
      b.bridge.agentThreadFor('goal-persist', 'leader') === anchorTs && b.bridge.agentForThread('goal-persist', anchorTs) === 'leader',
      { restored: [...b.bridge._agentThreads.entries()] });
    const after = b.bridge.routeOf(msg({ channel: reg.channelId, ts: '12.1', threadTs: anchorTs }));
    check('AFTER A RESTART the owner\'s reply in that thread still routes to the AGENT, not to the goal-master surface',
      after && after.kind === 'agent' && after.agent === 'leader', { after });
    b.bridge.stop();
  }

  for (const r of roots) { try { fs.rmSync(r, { recursive: true, force: true }); } catch {} }

  // 13 — THE RED ARMS. Skipped in a mutant child (it IS one of them) — see the harness header.
  if (!process.env[MUTANT_ENV]) await runMutationArms(check, checks.length);

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-agent-thread', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-agent-thread EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

// A throw anywhere above would exit non-zero with a stack trace and NO flushed capture — the
// one failure shape that leaves no evidence behind. Every check is written to survive its own
// subject being absent (so a broken mechanism reads as a named red, not a crash); this is the
// backstop for the rest.
main().catch((err) => {
  process.stdout.write(`PROBE probe-chat-agent-thread EXIT=1 THREW=${err && err.message}\n`);
  process.exit(1);
});

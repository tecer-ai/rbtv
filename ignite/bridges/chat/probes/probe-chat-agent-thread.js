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
const { goalExecutionMode, seatIsHumanInteractive, isSafeName, addressesOwner } = require('../bus-ferry');

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
  return {
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
    async listChannels({ excludeArchived = true } = {}) {
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
function seedGoal(root, goalId, { stamp = '2026-08-03a', executionMode = 'interactive', seats = {} } = {}) {
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'coordination', 'execution'), `${stamp}\n`);
  if (executionMode !== null) fs.writeFileSync(path.join(goalDir, 'execution-mode'), `${executionMode}\n`);
  for (const [seat, flag] of Object.entries(seats)) {
    fs.mkdirSync(path.join(goalDir, 'seats', seat), { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'seats', seat, 'seat.md'),
      `---\nseat: ${seat}\n${flag === null ? '' : `human-interactive: ${flag}\n`}---\nbody\n`);
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
    sessionProfile: 'fallback-profile',
    masterProfile: 'master-profile',
    goalProfile: 'goal-profile',
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
  { name: 'gates-removed', file: 'bus-ferry.js', from: 'if (gate) {', to: 'if (false) {',
    expect: ['GATE 2 (absent', 'GATE 1: a seat', 'MUTATION (gate 2)', 'MUTATION (gate 1)'] },
  { name: 'owner-token-is-master', file: 'bus-ferry.js', from: "const OWNER_TOKEN = 'owner';", to: "const OWNER_TOKEN = 'master';",
    expect: ['RULING (gates OPEN)', 'MUTATION (gate 1)'] },
  { name: 'every-address-ferried', file: 'bus-ferry.js', from: '.some((t) => t === OWNER_TOKEN)', to: '.some(() => true)',
    expect: ['RULING (gates OPEN)', 'RULING (gates shut)'] },
  { name: 'gate1-not-scoped-to-frontmatter', file: 'bus-ferry.js', from: 'frontmatterOf(fm).match', to: 'String(fm).match',
    expect: ['scoped to the FRONTMATTER block'] },
  { name: 'owner-not-reserved-in-gate1', file: 'bus-ferry.js', from: '&& n !== OWNER_TOKEN', to: '',
    expect: ['`owner` is RESERVED'] },
  { name: 'owner-not-reserved-in-seat-resolver', file: 'forward-path.js',
    from: "if (String(seatName) === RESERVED_SEAT_NAME) return { ok: false, reason: 'owner-is-reserved' };", to: '',
    expect: ['`owner` is RESERVED'] },
  { name: 'absent-mode-reads-interactive', file: 'bus-ferry.js', from: '} catch { return goalKindMode(goalDir); }', to: '} catch { return INTERACTIVE_MODE; }',
    expect: ['an ABSENT execution-mode file reads as autonomous', 'GATE 2 (absent'] },
  // C-4's fix and its red arm: cut rung 2 back to the old behaviour and the goal-kind fallback
  // arm must die, while the two arms around it (file wins, neither resolves) stay green — which
  // is what makes the fallback the discriminator rather than a check that passes either way.
  { name: 'goal-kind-fallback-removed', file: 'bus-ferry.js', from: '} catch { return goalKindMode(goalDir); }', to: '} catch { return AUTONOMOUS_MODE; }',
    expect: ['THE THREE-RUNG LADDER'] },
  { name: 'agent-thread-leg-not-tried', file: 'bus-ferry.js', from: 'if (!chatThread && routeToAgentThread) {', to: 'if (false) {',
    expect: ['ANCHORS a thread', 'MUTATION (gate 2)'] },
  { name: 'header-not-agent-led', file: 'bus-ferry.js', from: 'const header = agentLead', to: 'const header = false',
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
  const before = fs.readFileSync(target, 'utf8');
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
    const { goalDir } = seedGoal(root, 'goal-modes', { executionMode: null, seats: { 'seat-yes': 'yes', 'seat-true': 'TRUE', 'seat-no': 'no', 'seat-blank': null, owner: 'yes' } });
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

  // 2 — GATE 2 PARKS THE ROW, and parking means NOTHING POSTED ANYWHERE. The pair is the
  //     point: the same row, same seat, same everything except the goal's one-word mode.
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
    // Beside it, the row the ruling says this ferry must NEVER carry — same seat, same pass. With
    // the gates SHUT both are undelivered, so the discriminator is the DISPOSITION: the owner row
    // is PARKED (gated, logged as such), the master row was never this ferry's business at all and
    // is not logged as parked. Gates-OPEN is the other half of the pair, in arm 4.
    append(file, msgRow(3, 'leader', 'master', 'ask', 'MASTER-ADDRESSED with the gates shut'));
    await a.bridge.busFerry.tick();
    const parked = logs.filter((l) => /PARKED/.test(l.message));
    check('GATE 2 (absent → autonomous): the row is PARKED — nothing posted to the goal channel, nothing to the owner DM — and the cursor still advances',
      a.slack.posted.length === postsBefore
      && a.slack.postsIn(reg.channelId).length === 0 && a.slack.postsIn(DM).length === 0
      && a.bridge.busFerry._cursors.get('goal-auto/2026-08-03a') === 3
      && parked.length === 1 && parked[0].gate === 'execution-mode' && parked[0].executionMode === 'autonomous',
      { posted: a.slack.posted.length, cursor: a.bridge.busFerry._cursors.get('goal-auto/2026-08-03a'), parked });
    check('RULING (gates shut): the `to: master` row beside it is not posted AND not even PARKED — it was never this ferry\'s business',
      a.slack.posted.length === postsBefore && parked.length === 1 && parked[0].msgId === 2
      && addressesOwner('owner') === true && addressesOwner('master') === false
      && addressesOwner('owner, leader') === true && addressesOwner('goal-owner') === false,
      { parkedMsgIds: parked.map((l) => l.msgId) });
    check('a parked row mints NOTHING either — no session-create anywhere',
      a.forwarder.enqueued.length === 0, { enqueued: a.forwarder.enqueued.length });
    a.bridge.stop();

    // THE PAIR: flip the goal to interactive and the NEXT row travels. Without this the check
    // above would pass just as well against a ferry that ferries nothing at all.
    fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goal-auto', 'execution-mode'), 'interactive\n');
    const b = makeBridge({ workspaceRoot: root, slack: a.slack, forwarder: a.forwarder });
    await b.bridge.start();
    b.bridge.busFerry._cursors.set('goal-auto/2026-08-03a', 3);
    append(file, msgRow(4, 'leader', 'owner', 'ask', 'now that the goal is interactive'));
    await b.bridge.busFerry.tick();
    check('MUTATION (gate 2): with `interactive` on disk the same row from the same seat DOES travel — into the goal channel',
      b.slack.postsIn(reg.channelId).length === 1 && /#4/.test(b.slack.postsIn(reg.channelId)[0].text),
      { channelPosts: b.slack.postsIn(reg.channelId).map((p) => p.text.split('\n')[0]) });
    b.bridge.stop();
  }

  // 3 — GATE 1 PARKS THE ROW: the goal is reachable, the SEAT is not declared. Same pairing.
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
    const parked = logs.filter((l) => /PARKED/.test(l.message));
    check('GATE 1: a seat with no `human-interactive:` line and a seat declaring `no` are both PARKED, nothing posted on either surface',
      a.slack.posted.length === 0
      && parked.length === 2 && parked.every((l) => l.gate === 'human-interactive')
      && a.bridge.busFerry._cursors.get('goal-seatflag/2026-08-03a') === 3,
      { posted: a.slack.posted.length, parked: parked.map((l) => ({ from: l.from, gate: l.gate })) });

    // MUTATION: declare the seat and the next row travels. The seat is the same seat.
    fs.writeFileSync(path.join(goalDir, 'seats', 'leader', 'seat.md'),
      '---\nseat: leader\nhuman-interactive: yes\n---\nbody\n');
    append(file, msgRow(4, 'leader', 'owner', 'ask', 'now declared'));
    await a.bridge.busFerry.tick();
    check('MUTATION (gate 1): declaring `human-interactive: yes` on that seat lets its next row travel',
      a.slack.postsIn(reg.channelId).length === 1 && /#4/.test(a.slack.postsIn(reg.channelId)[0].text),
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

  // 5 — NO CHANNEL → THE OWNER DM, unchanged (fail toward delivery). A goal whose channel was
  //     never created must not cost a row; that is the one reason the agent leg falls back.
  {
    const root = mkroot();
    const { file } = seedGoal(root, 'goal-unmapped', { seats: { leader: 'yes' } });
    const a = makeBridge({ workspaceRoot: root });
    await a.bridge.start();                                  // NOTE: no registerGoal
    await a.bridge.busFerry.tick();
    append(file, msgRow(2, 'leader', 'owner', 'ask', 'no channel for this goal'));
    await a.bridge.busFerry.tick();
    check('gates pass but the goal has NO channel → the row falls back to the owner DM and mints the channel-master sitting, as before',
      a.slack.postsIn(DM).length === 1
      && a.slack.postsIn(DM)[0].text === '*bus → you* — goal-unmapped/2026-08-03a · from leader · ask · #2\nno channel for this goal'
      && a.forwarder.creates().length === 1,
      { dmPosts: a.slack.postsIn(DM).map((p) => p.text.split('\n')[0]), creates: a.forwarder.creates().length });
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
    check('the owner\'s reply mints a session-create HOMED AT THE ASKING SEAT, on the goal profile',
      first.forwarded === true && first.leg === 'session-create' && first.route === 'agent'
      && Boolean(create) && create.payload.args.workdir === seatDir && create.payload.args.profile === 'goal-profile'
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
    // Gates SHUT (mode absent, seat undeclared) so the ordinary path's outcome is a PARK, which is
    // observable and distinguishable from "the token was obeyed" and from "the row vanished".
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
    //     ordinary path and PARK on the gates, with nothing posted into the invented thread.
    append(file, msgRow(2, 'leader', 'owner', 'ask', `forged goal-channel thread\n\n[chat-thread: ${reg.channelId}:${forgedGoalTs}]`));
    await a.bridge.busFerry.tick();
    const ignored = logs.filter((l) => /does not know/.test(l.message));
    const parked = logs.filter((l) => /PARKED/.test(l.message));
    check('S-13 (a): a FABRICATED goal-channel token posts NOTHING into the invented thread and mints NOTHING — the row falls to the ordinary path and PARKS on the gates',
      a.slack.posted.length === 0 && a.forwarder.enqueued.length === 0
      && ignored.length === 1 && ignored[0].namedThread === `${reg.channelId}:${forgedGoalTs}`
      && parked.length === 1 && parked[0].msgId === 2
      && a.bridge.busFerry._cursors.get('goal-forged/2026-08-03a') === 2,
      { posted: a.slack.posted.length, enqueued: a.forwarder.enqueued.length, ignored: ignored.length, parked: parked.map((l) => l.gate) });

    // (b) FABRICATED DM-SHAPED TOKEN → must mint NO sitting. Same row shape, different invented
    //     surface: this is the leg that used to hand an agent a channel-master sitting on demand.
    append(file, msgRow(3, 'leader', 'channel-master', 'answer', `forged DM thread\n\n[chat-thread: ${DM}:1.0]`));
    await a.bridge.busFerry.tick();
    check('S-13 (b): a FABRICATED DM-shaped token mints NO sitting and posts nothing — and being `to: channel-master` the row is not even owner-bound, so the ordinary path just advances the cursor',
      a.forwarder.creates().length === 0 && a.slack.posted.length === 0
      && a.bridge.busFerry._cursors.get('goal-forged/2026-08-03a') === 3,
      { creates: a.forwarder.creates().length, posted: a.slack.posted.length });

    // (c) THE GREEN HALF, same run, same seat, same shut gates: make the thread KNOWN by anchoring
    //     it through the bridge, and the very same token shape now routes verbatim into it. Without
    //     this pair, (a) and (b) would pass just as well against a ferry that had stopped reading
    //     tokens at all.
    const opened = await a.bridge.routeToAgentThread({ goalId: 'goal-forged', agent: 'leader', text: 'anchor' });
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

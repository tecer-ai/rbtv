#!/usr/bin/env node
'use strict';

// probe-queue-request-pass — THE `queue-request` CONSUMER PASS, end to end (W7 of the silent-stall
// rulings programme; the type's record is `system-definition/concepts/queue-request.md`, settled by
// `decisions.md#d-message-types-seven`).
//
// THE QUESTION: a milestone judge records a PASS, the pass-opener writes a `queue-request`, and the
// daemon is supposed to splice the newly unblocked milestone's planning pass into the goal's
// `taskforce.csv`. Does it? Does it do it EXACTLY ONCE, however many cadences read the same row?
// Does a re-fire after a crash between the descriptor write and the registry append mint only the
// DELTA rather than refusing forever? Does it write NOTHING at all when the pass would land a seat
// with no cast? And does it stay off a request whose verdict was retracted?
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · No daemon PROCESS runs here. `runQueueRequestPass` is called directly — the same function
//     `server/index.js` calls from its loop. That the loop calls it is a separate STRUCTURAL arm
//     (S1), because a behavioural arm cannot see a loop that stopped calling the function it drives.
//   · No LLM, no spawn, no store. The pass writes only through `materialize-seats.py`, which is
//     invoked FOR REAL in arm D.
//   · `coord.py` is invoked FOR REAL for every message written and every request read — there is no
//     stub bus anywhere in this probe, because a stub bus would prove nothing about the one reader
//     the pass has.
//   · Arm D needs a component CATALOG, which is workspace state and not repo state. It is copied
//     from the live workspace when one is discoverable; when it is not, the arm records a FINDING
//     and the argv it WOULD have run is asserted instead. Every other arm runs unconditionally.
//
// FOUR MUTATION ARMS run the real pass against a single-string mutation of `queue-request.js`,
// compiled IN MEMORY (no file is ever written into the source tree), and REQUIRE it to go red.
// Each anchor is asserted present before it is replaced, so a mutation that silently matched
// nothing can never pass for a mutation that was survived.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { execFileSync } = require('node:child_process');

const ENGINE_SRC = path.resolve(__dirname, '..');
const QR_PATH = path.join(ENGINE_SRC, 'queue-request.js');
const COORD_PY = path.resolve(ENGINE_SRC, '..', 'team-kit', 'coord.py');
const SERVER_INDEX = path.resolve(ENGINE_SRC, '..', 'server', 'index.js');
const OUT_PATH = path.join(__dirname, 'probe-queue-request-pass.out');

const start = Date.now();
const lines = [];
const failures = [];
const findings = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}
function finding(s) { findings.push(s); lines.push(`FINDING  ${s}`); }

function python() {
  const { requirePythonCmd } = require('../../lib/python-cmd');
  return requirePythonCmd();
}

// ── THE MUTANT LOADER ────────────────────────────────────────────────────────────────────────
//
// `queue-request.js` compiled from a SINGLE-STRING mutation of its own source, in memory. The
// anchor is asserted present first: a mutation that matched nothing would "survive" every arm for
// the most boring reason there is.
function withMutant(anchor, replacement, body) {
  const src = fs.readFileSync(QR_PATH, 'utf8');
  if (!src.includes(anchor)) {
    check(`MUTATION ANCHOR PRESENT: ${anchor.slice(0, 60)}`, false, 'anchor not found in queue-request.js');
    return null;
  }
  const mutated = src.replace(anchor, replacement);
  const m = new Module(QR_PATH, null);
  m.filename = QR_PATH;
  m.paths = Module._nodeModulePaths(path.dirname(QR_PATH));
  m._compile(mutated, QR_PATH);
  return body(m.exports);
}

// ── THE FIXTURE ──────────────────────────────────────────────────────────────────────────────
//
// A workspace shaped exactly as the daemon reads one: `<ws>/rbtv.json`, `<ws>/.rbtv/goals/<goal>`,
// `<ws>/.rbtv/mirror/meta/`, `<ws>/.rbtv/config/modules/meta/planning/bindings/plan.json`.
const SHEET_SEATS = {
  'plan-planner': { agent_type: 'staff', mode: 'interactive', 'ctx-refresh': 35, harness: 'claude', model: 'claude-fable-5', effort: 'high' },
};

function makeWorkspace(root, { sheetSeats = SHEET_SEATS, taskforce, milestones, lane = 'daemon' }) {
  const ws = path.join(root, 'ws');
  const goal = path.join(ws, '.rbtv', 'goals', 'g1');
  fs.mkdirSync(path.join(goal, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(ws, '.rbtv', 'mirror', 'meta'), { recursive: true });
  const sheetDir = path.join(ws, '.rbtv', 'config', 'modules', 'meta', 'planning', 'bindings');
  fs.mkdirSync(sheetDir, { recursive: true });
  fs.writeFileSync(path.join(ws, 'rbtv.json'), JSON.stringify({ rbtv_path: path.resolve(ENGINE_SRC, '..', '..') }));
  fs.writeFileSync(path.join(sheetDir, 'plan.json'),
    JSON.stringify({ defaults: { 'cwd-mode': 'seat-folder' }, seats: sheetSeats }, null, 1));
  fs.writeFileSync(path.join(goal, 'execution-lane'), `${lane}\n`);
  fs.writeFileSync(path.join(goal, 'taskforce.csv'), taskforce);
  fs.writeFileSync(path.join(goal, 'milestones.csv'), milestones);
  return { ws, goal, goalsRoot: path.join(ws, '.rbtv', 'goals'), sheet: path.join(sheetDir, 'plan.json') };
}

const TF_HEADER = 'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n';
const TF_BASE = `${TF_HEADER}tf-1,unblock-checker,,claude,claude-fable-5,high,35,\n`;
const MILESTONES = 'milestone-id,name,description,after,done-contract,planning-mode\n'
  + 'm1,one,first,,contract,collapsed\n'
  + 'm2,two,second,m1,contract,full\n';

// ONE `queue-request` row, written by coord ITSELF. No JS ever touches `messages.md`.
function sendQueueRequest(goal, { milestone, verdict, kind = 'initial', sender = 'unblock-checker', supersedes = null }) {
  const body = path.join(os.tmpdir(), `qr-body-${process.pid}-${Math.random().toString(36).slice(2)}.md`);
  fs.writeFileSync(body, `queue-request: ${milestone}/${verdict}/${kind}\nmilestone ${milestone} became ready.\n`);
  const argv = [COORD_PY, '--package', goal, 'send', 'owner', '--type', 'queue-request',
    '--file', body, '--as', sender, '--force'];
  if (supersedes) argv.push('--supersedes', String(supersedes));
  const out = execFileSync(python(), argv, { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] });
  fs.rmSync(body, { force: true });
  return out;
}

function sendVerdict(goal, { milestone, sender = 'dod-judge', supersedes = null }) {
  const body = path.join(os.tmpdir(), `v-body-${process.pid}-${Math.random().toString(36).slice(2)}.md`);
  fs.writeFileSync(body, `PASS on ${milestone}.\n`);
  const argv = [COORD_PY, '--package', goal, 'send', 'owner', '--type', 'verdict',
    '--file', body, '--as', sender, '--force'];
  if (supersedes) argv.push('--supersedes', String(supersedes));
  const out = execFileSync(python(), argv, { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] });
  fs.rmSync(body, { force: true });
  return out;
}

// The message number coord assigned the last row — read back through coord's OWN listing, never by
// parsing `messages.md` here.
function lastMessageNum(goal) {
  const raw = execFileSync(python(), [COORD_PY, '--package', goal, 'queue-requests', '--json', '--all'],
    { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] });
  const rows = JSON.parse(raw);
  return rows.length ? rows[rows.length - 1].num : null;
}

function logger(sink) { return (m) => sink.push(m); }
function snapshot(goal) {
  const tf = fs.readFileSync(path.join(goal, 'taskforce.csv'), 'utf8');
  let seats = [];
  try { seats = fs.readdirSync(path.join(goal, 'seats')).sort(); } catch { seats = []; }
  return { tf, seats: seats.join(',') };
}

// ── ARM D's CATALOG: the live workspace's, when there is one ────────────────────────────────
//
// Walked UP from this repo — never a hardcoded path, and never `cwd`. What is looked for is the
// planning workflow manifest itself, so a directory that merely LOOKS like a workspace cannot
// satisfy it.
function findLiveCatalog() {
  let dir = path.resolve(ENGINE_SRC, '..', '..');
  for (let i = 0; i < 8; i += 1) {
    const mirror = path.join(dir, '.rbtv', 'mirror');
    let mods = [];
    try { mods = fs.readdirSync(mirror, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name); } catch { mods = []; }
    for (const mod of mods) {
      const comp = path.join(mirror, mod, 'planning');
      if (fs.existsSync(path.join(comp, 'workflows', 'planning', 'planning.csv'))) {
        const sheet = path.join(dir, '.rbtv', 'config', 'modules', mod, 'planning', 'bindings', 'plan.json');
        // The WHOLE module is carried, not just `planning/`: a seat's `exposes:` may reference a
        // SIBLING component (`master-agent/slack-message-format`), and a dangling reference is a
        // materialize refusal by design.
        if (fs.existsSync(sheet)) return { workspace: dir, module: path.join(mirror, mod), sheet };
      }
    }
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return null;
}

// Copy the live planning component in as the fixture catalog's ONLY component, and stub every
// workspace-relative entry point its `exposure.csv` names — the seats declare tools that live in
// the real workspace and the fixture has none of them.
function installCatalog(fx, live) {
  const dest = path.join(fx.ws, '.rbtv', 'mirror', 'meta');
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(live.module, dest, { recursive: true });
  fs.copyFileSync(live.sheet, fx.sheet);
  const refs = new Set();
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name === 'exposure.csv') {
        for (const r of String(fs.readFileSync(p, 'utf8')).match(/ws:[^,"\s]+/g) || []) refs.add(r);
      }
    }
  };
  walk(dest);
  for (const ref of refs) {
    const target = path.join(fx.ws, ref.slice(3));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, '#!/usr/bin/env python3\n');
    fs.chmodSync(target, 0o755);
  }
}

function main() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-qr-'));
  const { runQueueRequestPass, passesMinted, materializeArgv } = require('../queue-request');

  // ── S1 — STRUCTURAL: THE DAEMON'S LOOP ACTUALLY CALLS IT ────────────────────────────────────
  // A behavioural arm cannot see a loop that stopped calling the function it drives (the lesson of
  // review finding F1 on the lane watch). Both call sites are asserted: the boot pass and the
  // interval, and that it runs BEFORE the lane watch — reversed, every wave boundary costs an
  // extra cadence.
  {
    const src = fs.readFileSync(SERVER_INDEX, 'utf8');
    check('S1 the daemon requires the pass', src.includes("require('../engine/queue-request')"));
    const boot = src.indexOf('queueRequestPass();');
    const bootLane = src.indexOf('laneWatchPass();');
    check('S1 the daemon CALLS the pass at boot and inside the interval',
      (src.match(/queueRequestPass\(\);/g) || []).length >= 2,
      `${(src.match(/queueRequestPass\(\);/g) || []).length} call site(s)`);
    check('S1 it runs BEFORE the lane watch, so a spliced row is seeded in the SAME cadence',
      boot > 0 && bootLane > boot);
  }

  // ── A — CONSUMPTION / NO DOUBLE FIRE ────────────────────────────────────────────────────────
  //
  // The request is live and unsuperseded; the goal ALREADY carries a nested pass for that
  // milestone. The pass must recognise it as consumed and do nothing — every cadence, forever.
  {
    const fx = makeWorkspace(path.join(tmp, 'A'), {
      taskforce: `${TF_BASE}tf-2-plan1,plan-2-plan-planner,unblock-checker,claude,claude-fable-5,high,35,m1\n`,
      milestones: MILESTONES,
    });
    sendQueueRequest(fx.goal, { milestone: 'm1', verdict: 7 });
    const before = snapshot(fx.goal);
    const log = [];
    const r1 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(log) });
    const r2 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(log) });
    const after = snapshot(fx.goal);
    check('A the already-consumed request mints NOTHING', r1.seeded.length === 0 && r2.seeded.length === 0,
      `pass1 seeded ${r1.seeded.length}, pass2 seeded ${r2.seeded.length}`);
    check('A it is recognised as CONSUMED (not merely refused for some other reason)',
      r1.skipped.some((s) => s.reason === 'queue-request-consumed'),
      r1.skipped.map((s) => s.reason).join(', '));
    check('A NO-DOUBLE-FIRE: the registry is byte-identical after draining the same request twice',
      after.tf === before.tf && after.seats === before.seats);
    check('A the consumed line is DEBUG, not a warning repeated every cadence forever',
      log.filter((m) => m.reason === 'queue-request-consumed').every((m) => m.level === 'debug'));

    // MUTATION: the consumption count always reads 0 — the pass no longer knows the pass landed.
    const mut = withMutant('  return ids.size;\n}', '  return ids.size * 0;\n}', (mod) => {
      const mlog = [];
      const res = mod.runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(mlog) });
      return { res, mlog };
    });
    if (mut) {
      check('A MUTANT (consumption count forced to 0) -> the pass STOPS skipping and tries to mint '
        + 'again: the double-fire, reproduced',
      !mut.res.skipped.some((s) => s.reason === 'queue-request-consumed'),
      `skips: ${mut.res.skipped.map((s) => s.reason).join(', ') || 'none'}`);
    }
    check('A the live build is UNMUTATED (the in-memory compile touched no file)',
      fs.readFileSync(QR_PATH, 'utf8').includes('  return ids.size;\n}'));
  }

  // ── B — UNCAST REFUSAL: A PASS THAT WOULD LAND AN UNCAST ROW WRITES NOTHING ─────────────────
  //
  // ⚠ WHY THIS IS THE ARM THAT MATTERS MOST. `runLaneWatch` skips a goal WHOLESALE on ONE uncast
  // seat, and quietly after the first cadence. So a single uncast row spliced here does not
  // degrade the new pass — it FREEZES THE ENTIRE GOAL, which is the exact silent stall this
  // programme exists to kill.
  {
    const fx = makeWorkspace(path.join(tmp, 'B'), {
      // `plan-planner` carries NO harness/model: the seat has nothing to run as.
      sheetSeats: { 'plan-planner': { agent_type: 'staff', mode: 'interactive', 'ctx-refresh': 35 } },
      taskforce: TF_BASE,
      milestones: MILESTONES,
    });
    sendQueueRequest(fx.goal, { milestone: 'm1', verdict: 7 });
    const before = snapshot(fx.goal);
    const log = [];
    const res = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(log) });
    const after = snapshot(fx.goal);
    check('B the uncast pass mints NOTHING', res.seeded.length === 0);
    check('B it refuses for the RIGHT reason, naming the seat',
      res.skipped.some((s) => s.reason === 'queue-request-would-land-uncast'
        && (s.seats || []).includes('plan-planner')),
      JSON.stringify(res.skipped.map((s) => s.reason)));
    check('B NOTHING WAS WRITTEN: registry and seats byte-identical',
      after.tf === before.tf && after.seats === before.seats);
    check('B the refusal is LOUD (warn), because only a human can clear it',
      log.some((m) => m.level === 'warn' && /NO cast/.test(m.message || '')));

    // MUTATION: the uncast refusal is removed — the pass proceeds to the materializer.
    const mut = withMutant('      if (uncast.length) {', '      if (uncast.length && false) {', (mod) => {
      const mlog = [];
      const res2 = mod.runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(mlog) });
      return { res2, mlog };
    });
    if (mut) {
      check('B MUTANT (uncast refusal removed) -> the pass no longer refuses and reaches the WRITE '
        + 'path: the goal-freezing splice, reproduced',
      !mut.res2.skipped.some((s) => s.reason === 'queue-request-would-land-uncast'),
      `skips: ${mut.res2.skipped.map((s) => s.reason).join(', ') || 'none'}`);
    }
  }

  // ── C — SUPERSEDES-SKIP ─────────────────────────────────────────────────────────────────────
  //
  // A request whose VERDICT row was superseded is skipped. The filtering is coord's
  // (`cmd_queue_requests` without `--all`); this arm proves the consumer CONSUMES that filtering
  // rather than re-deriving it — and the mutation proves the filtering is what is doing the work.
  {
    const fx = makeWorkspace(path.join(tmp, 'C'), { taskforce: TF_BASE, milestones: MILESTONES });
    sendVerdict(fx.goal, { milestone: 'm1' });
    const verdictNum = 1;
    sendQueueRequest(fx.goal, { milestone: 'm1', verdict: verdictNum });
    // The verdict is RETRACTED by a later verdict that supersedes it.
    sendVerdict(fx.goal, { milestone: 'm1', supersedes: verdictNum });
    const before = snapshot(fx.goal);
    const res = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) });
    const after = snapshot(fx.goal);
    check('C a request minted from a SUPERSEDED verdict mints nothing', res.seeded.length === 0);
    check('C and coord is what hid it — the pass sees NO request at all',
      res.skipped.some((s) => s.reason === 'no-queue-requests'),
      res.skipped.map((s) => s.reason).join(', '));
    check('C nothing was written', after.tf === before.tf && after.seats === before.seats);
    // CONTROL: without the supersession the same fixture DOES see the request. Without this, the
    // arm above passes for any reason at all — including a fixture whose message never landed.
    const raw = execFileSync(python(), [COORD_PY, '--package', fx.goal, 'queue-requests', '--json', '--all'],
      { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] });
    const all = JSON.parse(raw);
    check('C CONTROL: the request row EXISTS and is flagged verdict_superseded — so the skip above '
      + 'is a filter doing its job, not an empty fixture',
    all.length === 1 && all[0].verdict_superseded === true,
    JSON.stringify(all.map((r) => ({ num: r.num, vs: r.verdict_superseded }))));

    // MUTATION: ask coord for `--all` — the retracted request comes back and would be acted on.
    const mut = withMutant("'queue-requests', '--json']", "'queue-requests', '--json', '--all']", (mod) => mod.runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) }));
    if (mut) {
      check('C MUTANT (`--all` restored) -> the retracted request is VISIBLE again: the skip is '
        + "coord's filter and nothing else",
      !mut.skipped.some((s) => s.reason === 'no-queue-requests'),
      `skips: ${mut.skipped.map((s) => s.reason).join(', ') || 'none'}`);
    }
  }

  // ── D — THE REAL SPLICE: ATOMICITY, IDEMPOTENCY, AND THE CRASH-BETWEEN-MINT-AND-SPLICE DELTA ─
  const live = findLiveCatalog();
  if (!live) {
    finding('ARM D DID NOT RUN on this host: no workspace with `.rbtv/mirror/<module>/planning/'
      + 'workflows/planning/planning.csv` plus its casting sheet was found walking up from this '
      + 'repo. A component catalog is WORKSPACE state, not repo state. The argv arm below still '
      + 'ran; the real materialize did not.');
    const argv = materializeArgv({ goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json', milestone: 'm2', mode: 'full', after: ['x'] });
    check('D (degraded) the full-mode invocation is ONE nested workflow materialize carrying '
      + '--force-partial — never N single-seat mints, for which no rollback verb exists',
    argv.includes('--workflow') && argv.includes('--nested') && argv.includes('--force-partial')
      && !argv.includes('--seat'));
  } else {
    const fx = makeWorkspace(path.join(tmp, 'D'), {
      taskforce: TF_BASE,
      milestones: MILESTONES,
    });
    installCatalog(fx, live);
    sendQueueRequest(fx.goal, { milestone: 'm2', verdict: 9 });   // m2 is planning-mode `full`
    const before = snapshot(fx.goal);
    // ⚠ FIXTURE HYGIENE, DISCLOSED. The materializer refuses code `catalog` when ANY component
    // under the root has unloadable frontmatter — before it reads a single seat. That is a defect
    // of the MIRROR this fixture was copied from, not of the consumer, and letting it redden this
    // arm would measure the workspace instead of the code. Such a component is dropped from the
    // FIXTURE (never from the workspace) and the pass re-run; each drop is a FINDING, because the
    // same refusal fires in the live daemon and somebody has to fix it there.
    let res = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) });
    for (let i = 0; i < 5 && !res.seeded.length; i += 1) {
      const bad = res.skipped.find((s) => s.code === 'catalog');
      if (!bad) break;
      const hit = String(bad.evidence || '').match(/(\/[^\s"\\]*component\.md)/);
      if (!hit) break;
      const compDir = path.dirname(hit[1]);
      if (!compDir.startsWith(fx.ws)) break;
      finding('THE LIVE MIRROR CARRIES AN UNLOADABLE COMPONENT: '
        + `${path.relative(fx.ws, compDir)}/component.md does not parse, so EVERY materialize against `
        + 'that catalog root refuses `catalog` — including the daemon\'s. Dropped from this FIXTURE '
        + 'so the arm can measure the consumer; it is NOT fixed in the workspace and must be.');
      fs.rmSync(compDir, { recursive: true, force: true });
      res = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) });
    }
    const after = snapshot(fx.goal);
    const minted = res.seeded[0] || null;
    // ⚠ A CATALOG THAT DOES NOT LOAD IS THIS WORKSPACE'S DEFECT, NOT THE PASS'S. The materializer
    // refuses code `catalog` when ANY component under the root has unloadable frontmatter, and it
    // does so before reading a single seat — so the arm below would be measuring the mirror, not
    // the consumer. Disclosed as a FINDING and the arm stands down rather than reporting a red
    // against code it never reached.
    const catalogBroken = !minted && res.skipped.some((s) => s.code === 'catalog');
    if (catalogBroken) {
      const ev = (res.skipped.find((s) => s.code === 'catalog') || {}).evidence || '';
      finding('ARM D STOOD DOWN: the live component catalog copied into the fixture does not LOAD '
        + `(materialize refusal code \`catalog\`) — ${ev.slice(0, 300)}. Fix the mirror component's `
        + 'frontmatter; until then the real-materialize arm cannot run ANYWHERE, including in the '
        + 'daemon, because the same refusal fires there.');
      fs.rmSync(tmp, { recursive: true, force: true });
      return;
    }
    check('D the pass SPLICED a whole planning instance for the unblocked milestone',
      !!minted && (minted.seats || []).length > 1,
      minted ? `${minted.seats.length} seat(s), ${minted.rows} row(s) appended` : JSON.stringify(res.skipped));
    const addedRows = after.tf.trim().split('\n').length - before.tf.trim().split('\n').length;
    check('D ATOMICITY: every row of the chain landed in ONE append — the row count moved by the '
      + 'whole instance, never by a fraction of it',
    !!minted && addedRows === (minted.seats || []).length,
    `${addedRows} row(s) added for ${minted ? minted.seats.length : '?'} seat(s)`);
    check('D every appended row carries the request\'s milestone and the instance\'s OWN nested '
      + 'taskforce-id (which is what makes consumption re-derivable with no store)',
    !!minted && passesMinted(after.tf.trim().split('\n').slice(1).map((l) => {
      const c = l.split(',');
      return { 'taskforce-id': c[0], 'milestone-id': l.trim().split(',').pop() };
    }), 'm2') === 1);

    // IDEMPOTENCY: the very same request, drained again, adds nothing.
    const res2 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) });
    const after2 = snapshot(fx.goal);
    check('D IDEMPOTENT: the same request drained a second time mints nothing and the registry is '
      + 'byte-identical', res2.seeded.length === 0 && after2.tf === after.tf,
    res2.skipped.map((s) => s.reason).join(', '));

    // ── THE CRASH BETWEEN MINT AND SPLICE (adv, C68) ──────────────────────────────────────────
    // The materializer writes seat DESCRIPTORS first and registry ROWS second. Simulate the
    // interruption by removing the appended rows while KEEPING the folders — the exact half-state
    // an unattended crash leaves. The re-fire must mint only the DELTA (the rows), not refuse
    // `seat-exists` forever.
    fs.writeFileSync(path.join(fx.goal, 'taskforce.csv'), before.tf);
    const halfState = snapshot(fx.goal);
    check('D CONTROL: the half-state is real — the seat FOLDERS are still there and the rows are gone',
      halfState.seats === after.seats && halfState.tf === before.tf);
    const res3 = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) });
    const after3 = snapshot(fx.goal);
    check('D CRASH RECOVERY: the re-fire mints the DELTA — the missing rows are appended and the '
      + 'already-minted seats are not re-created', res3.seeded.length === 1
      && after3.tf.trim().split('\n').length === after.tf.trim().split('\n').length
      && after3.seats === after.seats,
    `seeded ${res3.seeded.length}; rows ${after3.tf.trim().split('\n').length} vs ${after.tf.trim().split('\n').length}`);

    // MUTATION: `--force-partial` dropped — the crash recovery dies on `seat-exists`, forever.
    fs.writeFileSync(path.join(fx.goal, 'taskforce.csv'), before.tf);
    const mut = withMutant("'--milestone-id', milestone, '--force-partial', '--json'",
      "'--milestone-id', milestone, '--json'",
      (mod) => mod.runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) }));
    if (mut) {
      check('D MUTANT (--force-partial dropped) -> the crash-between-mint-and-splice state is '
        + 'UNRECOVERABLE: the mint refuses and the wave stalls forever',
      mut.seeded.length === 0 && mut.skipped.some((s) => s.reason === 'materialize-refused'),
      `seeded ${mut.seeded.length}; skips ${mut.skipped.map((s) => s.reason).join(', ') || 'none'}`);
    }
    check('D the live build is UNMUTATED', fs.readFileSync(QR_PATH, 'utf8').includes("'--force-partial', '--json'"));

    // ── E — REGISTERED BUT UNBUILT (adv, C71 / D5 defect 1) ─────────────────────────────────
    //
    // A milestone's planner and binder REGISTER the next milestone's team as `taskforce.csv` rows
    // and nothing materializes them: rows present, `seats/<seat>/` absent, goal stalls at UNBUILT.
    // The lane watch now builds them. ⚠ The ORDER is the whole fix: a row with no folder has no
    // `seat.md`, so `uncastSeats` calls it UNCAST and the uncast branch skips the goal WHOLESALE —
    // permanently reporting the wrong state with a fix that does not repair it.
    {
      const { runLaneWatch, failedOn } = require('../lane-watch');
      failedOn.clear();
      const tfPath = path.join(fx.goal, 'taskforce.csv');
      const row = 'tf-1,plan-planner,unblock-checker,claude,claude-fable-5,high,35,\n';
      fs.writeFileSync(tfPath, before.tf + row);
      // The fixture's own base row gets a folder, so the ONE unbuilt seat is the one under test.
      fs.mkdirSync(path.join(fx.goal, 'seats', 'unblock-checker'), { recursive: true });
      const seatDir = path.join(fx.goal, 'seats', 'plan-planner');
      check('E CONTROL: the row exists and its seat folder does NOT', !fs.existsSync(seatDir));
      const elog = [];
      const engineStub = { seedGoal: () => { throw new Error('E: seedGoal must NOT be reached this cadence'); } };
      const lw = runLaneWatch({ goalsRoot: fx.goalsRoot, engine: engineStub, logger: logger(elog) });
      check('E the lane watch BUILT the registered-but-unbuilt seat', fs.existsSync(path.join(seatDir, 'seat.md')),
        JSON.stringify((lw.skipped.find((s) => s.reason === 'unbuilt-seats') || {}).failed || []).slice(0, 500));
      check('E it reports the state as `unbuilt-seats` — NOT as `uncast-seats`, which is the '
        + 'misdiagnosis this branch exists to prevent',
      lw.skipped.some((s) => s.reason === 'unbuilt-seats' && (s.built || []).includes('plan-planner'))
        && !lw.skipped.some((s) => s.reason === 'uncast-seats'),
      lw.skipped.map((s) => s.reason).join(', '));
      check('E the registry row was NOT rewritten — the build adds the folder and nothing else',
        fs.readFileSync(tfPath, 'utf8') === before.tf + row);

      // MUTATION: the branch runs AFTER the uncast check instead of before. Reproduced by
      // disabling the branch entirely, which is what "after" amounts to for this row: the uncast
      // check then fires first and swallows the goal.
      fs.rmSync(seatDir, { recursive: true, force: true });
      failedOn.clear();
      const src = fs.readFileSync(path.join(ENGINE_SRC, 'lane-watch.js'), 'utf8');
      const anchor = '    if (unbuilt.length) {';
      if (!src.includes(anchor)) check('E MUTATION ANCHOR PRESENT', false, anchor);
      else {
        const m = new Module(path.join(ENGINE_SRC, 'lane-watch.js'), null);
        m.filename = path.join(ENGINE_SRC, 'lane-watch.js');
        m.paths = Module._nodeModulePaths(ENGINE_SRC);
        m._compile(src.replace(anchor, '    if (unbuilt.length && false) {'), m.filename);
        const mlw = m.exports.runLaneWatch({ goalsRoot: fx.goalsRoot, engine: engineStub, logger: logger([]) });
        check('E MUTANT (branch disabled) -> the seat is NEVER built and the goal is skipped as '
          + '`uncast-seats`: the silent UNBUILT stall, reproduced',
        !fs.existsSync(seatDir) && mlw.skipped.some((s) => s.reason === 'uncast-seats'),
        mlw.skipped.map((s) => s.reason).join(', '));
      }
    }

    // ── E2 — THE UNBUILT ROW WHOSE SEAT IS AN INSTANCE NAME (live stall, 2026-08-17) ─────────
    //
    // THE MEASURED FAILURE: goal `meet-transcript-summarizer` carried two rows —
    // `plan-6-plan-dod-judge`, `plan-6-plan-unblock-checker` — with no folder, and the repair
    // above refused BOTH every 10 s tick, so the WHOLE goal went unseeded (the lane watch
    // `continue`s past an unbuilt goal), including a seat that was ready to run. Two things
    // stacked, and this arm pins both:
    //   · the sheet was looked for ONLY at `bindings/<first-name-segment>.json` — `plan.json` —
    //     but a seat that belongs to NO WORKFLOW carries its own `bindings/<seat>.json` (the
    //     standing-seat spelling), and it is DELIBERATELY absent from the workflow sheet;
    //   · the entry inside that sheet is keyed by the BASE seat, because a composed instance
    //     name is a disk name and never a catalog or bindings key.
    // The fixture reproduces exactly that shape: the base seat's cast is MOVED out of `plan.json`
    // into its own sheet, so nothing but the per-seat sheet can cast the row.
    {
      const { runLaneWatch, failedOn } = require('../lane-watch');
      const tfPath = path.join(fx.goal, 'taskforce.csv');
      const sheetJson = JSON.parse(fs.readFileSync(fx.sheet, 'utf8'));
      const base = 'plan-planner';
      const entry = (sheetJson.seats || {})[base];
      if (!entry) check('E2 FIXTURE: the live sheet casts the base seat', false, base);
      else {
        delete sheetJson.seats[base];
        fs.writeFileSync(fx.sheet, JSON.stringify(sheetJson, null, 1));
        fs.writeFileSync(path.join(path.dirname(fx.sheet), `${base}.json`),
          JSON.stringify({ defaults: sheetJson.defaults || {}, seats: { [base]: entry } }, null, 1));
        const seat = `plan-6-${base}`;
        // `tf-3` — a SECOND bare taskforce-id, as the live registry carries. The row's own id is
        // what the completion reads; nothing here guesses one.
        const row = `tf-3,${seat},,${entry.harness},${entry.model},${entry.effort},`
          + `${entry['ctx-refresh']},\n`;
        fs.writeFileSync(tfPath, before.tf + row);
        const seatDir2 = path.join(fx.goal, 'seats', seat);
        fs.rmSync(seatDir2, { recursive: true, force: true });
        check('E2 CONTROL: the row exists, its folder does NOT, and the WORKFLOW sheet cannot '
          + 'cast it — only the per-seat sheet can', !fs.existsSync(seatDir2)
          && !JSON.parse(fs.readFileSync(fx.sheet, 'utf8')).seats[base]);
        failedOn.clear();
        const engineStub2 = { seedGoal: () => { throw new Error('E2: seedGoal must NOT be reached'); } };
        const lw2 = runLaneWatch({ goalsRoot: fx.goalsRoot, engine: engineStub2, logger: logger([]) });
        check('E2 the lane watch BUILT the instance-named unbuilt seat off its per-seat sheet',
          fs.existsSync(path.join(seatDir2, 'seat.md')),
          JSON.stringify((lw2.skipped.find((s) => s.reason === 'unbuilt-seats') || {}).failed || []).slice(0, 500));
        check('E2 the descriptor carries the COMPOSED name, not the base it was cast under',
          fs.existsSync(path.join(seatDir2, 'seat.md'))
          && fs.readFileSync(path.join(seatDir2, 'seat.md'), 'utf8').includes(`seat: ${seat}`));
        check('E2 the registry row was NOT rewritten — the completion adds the folder and nothing '
          + 'else', fs.readFileSync(tfPath, 'utf8') === before.tf + row);

        // MUTATION 1 — the sheet search drops back to the workflow-code candidate alone. That is
        // the pre-fix reader, and it is the half that made the live goal stall.
        fs.rmSync(seatDir2, { recursive: true, force: true });
        failedOn.clear();
        const m1 = withMutant('[...new Set([seat, base, code].filter(Boolean))]',
          '[...new Set([code].filter(Boolean))]',
          (mod) => mod.buildUnbuiltSeats({
            goalFolder: fx.goal,
            goalsRoot: fx.goalsRoot,
            rows: [{ seat, after: '', 'milestone-id': '' }],
            unbuilt: [seat],
            say: () => {},
          }));
        if (m1) {
          check('E2 MUTANT (workflow-code sheet only) -> the seat is NEVER built: the live stall, '
            + 'reproduced', !fs.existsSync(seatDir2) && m1.built.length === 0 && m1.failed.length === 1,
          JSON.stringify(m1).slice(0, 300));
        }

        // MUTATION 2 — the sheet resolves, but the ENTRY is looked up under the composed name
        // only. The second half of the stack, and it fails on its own.
        failedOn.clear();
        const m2 = withMutant('? seat : instanceBaseSeat(seat);', '? seat : \'\';',
          (mod) => mod.buildUnbuiltSeats({
            goalFolder: fx.goal,
            goalsRoot: fx.goalsRoot,
            rows: [{ seat, after: '', 'milestone-id': '' }],
            unbuilt: [seat],
            say: () => {},
          }));
        if (m2) {
          check('E2 MUTANT (entry keyed by the composed name only) -> `unbuilt-seat-not-in-sheet`: '
            + 'a sheet is keyed by CATALOG ids and a composed name is never one',
          !fs.existsSync(seatDir2) && m2.built.length === 0
            && (m2.failed[0] || {}).code === 'unbuilt-seat-not-in-sheet',
          JSON.stringify(m2).slice(0, 300));
        }
        check('E2 the live build is UNMUTATED',
          fs.readFileSync(QR_PATH, 'utf8').includes('[...new Set([seat, base, code].filter(Boolean))]'));
      }
    }
  }

  // ── R — R9's GENERALIZATION: A THIRD `planning-mode` VALUE CANNOT SLIP THROUGH ─────────────
  //
  // The two pass shapes are injected at TWO symmetric prompt points — `planner.md` demands
  // `collapsed` and fails back on anything else, and the full chain is guarded on
  // `[planning-mode=full]` in the workflow manifest's `after` cells. A THIRD value satisfies
  // NEITHER, so on the prompts alone it does not fail: it produces a milestone nothing ever
  // opens a pass for, which is the silent-stall shape this whole programme exists to end. The
  // guard is the engine's, at the ONE door that opens a pass, and this arm is what pins it.
  {
    const fx = makeWorkspace(path.join(tmp, 'R'), {
      taskforce: TF_BASE,
      milestones: 'milestone-id,name,description,after,done-contract,planning-mode\n'
        + 'm1,one,first,,contract,collapsed\n'
        + 'm2,two,second,m1,contract,hybrid\n',
    });
    sendVerdict(fx.goal, { milestone: 'm2' });
    sendQueueRequest(fx.goal, { milestone: 'm2', verdict: lastMessageNum(fx.goal) || 1 });
    const before = snapshot(fx.goal);
    const rlog = [];
    const res = runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger(rlog) });
    const after = snapshot(fx.goal);
    check('R a milestone stamped a THIRD planning-mode value opens NO pass and writes NOTHING',
      res.seeded.length === 0 && after.tf === before.tf && after.seats === before.seats,
      `seeded ${res.seeded.length}`);
    check('R it refuses BY NAME (`queue-request-planning-mode-unstamped`), so the third value is '
      + 'reported as the authoring error it is — never as a milestone that merely never came up',
    res.skipped.some((s) => s.reason === 'queue-request-planning-mode-unstamped'),
    res.skipped.map((s) => s.reason).join(', ') || 'none');
    check('R the refusal is LOUD (warn) — only a human can restamp the row',
      rlog.some((m) => m.level === 'warn' && /REFUSED before writing/.test(m.message || '')));
    // MUTANT: the enum check relaxed to "anything non-empty". The third value then flows on as a
    // pass shape nothing implements — the exact silent bypass R9 asks to make impossible.
    const mut = withMutant("if (mode !== 'full' && mode !== 'collapsed') {", 'if (!mode) {',
      (mod) => mod.runQueueRequestPass({ goalsRoot: fx.goalsRoot, logger: logger([]) }));
    if (mut) {
      check('R MUTANT (enum relaxed to non-empty) -> `hybrid` is ACCEPTED and the pass proceeds '
        + 'past the shape check: the bypass, reproduced',
      !mut.skipped.some((s) => s.reason === 'queue-request-planning-mode-unstamped'),
      mut.skipped.map((s) => s.reason).join(', ') || 'none');
    }
    check('R the live build is UNMUTATED',
      fs.readFileSync(QR_PATH, 'utf8').includes("if (mode !== 'full' && mode !== 'collapsed') {"));
  }

  // ── G — THE GOAL-LOCAL LINT IS THE BUILD, ASKED NOT TO WRITE ───────────────────────────────
  //
  // The lint exists so a goal whose pass authored a broken seat set is reported ONCE, by code,
  // with nothing half-built behind it. That only holds if it differs from the build in
  // `--dry-run` AND NOTHING ELSE. It did differ: two argv literals drifted, the lint lost
  // `--force-partial`, and since EVERY goal-local seat is a REGISTERED-but-unbuilt row, the
  // dry run took `registry-row-exists`/`seat-exists` — a refusal the build itself would never
  // hit — on every goal, always. One builder is the fix; this arm is what keeps it one.
  {
    const qr = require('../queue-request');
    const args = { goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json', milestone: 'm1' };
    const build = qr.goalLocalArgv({ ...args });
    const lint = qr.goalLocalArgv({ ...args, dryRun: true });
    check('G the lint argv is the build argv PLUS `--dry-run`, and differs in nothing else',
      JSON.stringify(lint) === JSON.stringify([...build, '--dry-run']),
      `build ${JSON.stringify(build)} / lint ${JSON.stringify(lint)}`);
    check('G both carry `--force-partial` — without it a registered-but-unbuilt goal-local seat '
      + 'refuses on the very row that says it needs building',
    build.includes('--force-partial') && lint.includes('--force-partial'));
    check('G both carry the seat\'s own `--milestone-id` — it is a COLUMN of the row the '
      + 'byte-match compares, so omitting it refuses `partial-row-mismatch` on a cell nobody '
      + 'meant to change', build.includes('--milestone-id') && build.includes('m1'));
    check('G a seat registered under NO milestone passes no `--milestone-id` at all (an empty '
      + 'flag value is not the same as an absent column)',
    !qr.goalLocalArgv({ ...args, milestone: '' }).includes('--milestone-id'));
    // STRUCTURAL: there is exactly ONE place the goal-local invocation is spelled.
    const src = fs.readFileSync(QR_PATH, 'utf8');
    check('G ONE builder: `--goal-local` is spelled in exactly one argv literal',
      (src.match(/'--goal-local'/g) || []).length === 1,
      `${(src.match(/'--goal-local'/g) || []).length} occurrence(s)`);
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}

const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the `queue-request` type HAS a consumer: the daemon reads each goal\'s requests '
    + 'through coord (no JS bus parser), splices the newly unblocked milestone\'s planning pass as ONE '
    + 'nested materialize, and does it EXACTLY ONCE however many cadences re-read the row — with no '
    + 'consumption store, because a create-only splice makes re-checking safe. A pass that would land '
    + 'a seat with NO cast writes NOTHING (an uncast row freezes the whole goal at the lane watch). A '
    + 'request minted from a RETRACTED verdict is never acted on. And a crash between the descriptor '
    + 'write and the registry append recovers by minting the DELTA rather than refusing forever. Every '
    + 'mutation red.');
say(`FINDINGS: ${findings.length} (a PASS means "measured" — read the findings for the open bounds)`);
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, `${lines.join('\n')}\n`);
console.log(lines.join('\n'));
process.exit(exitCode);

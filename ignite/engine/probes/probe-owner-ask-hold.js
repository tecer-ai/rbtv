#!/usr/bin/env node
'use strict';

// probe-owner-ask-hold — THE UNIVERSAL OWNER-ASK HOLD, AT THE ENGINE'S SIDE OF IT (W2).
//
// ⚑ THIS FILE REPLACES `probe-block-and-queue-hold.js` AND `hold-scenario.js`, BOTH DELETED, and
// the replacement is not a rename. That probe's SUBJECT was the ruling
// `decisions.md#d-block-and-queue-mechanical-hold`: a hold decided inside the engine, firing only
// when a seat declared `fallback: block-and-queue` AND the chat ferry had DELIVERED its ask. W2
// deleted the decision and all three of its gates — `blockAndQueueVerdict`, `askParkedAtGate`,
// `outcomeForSeat` and the `FALLBACK_BLOCK_AND_QUEUE` constant are gone from
// `execution-record.js`, and the `blocked` word is gone from the outcome column with them. Eight of
// that probe's sections and three of its seven mutants pinned source text that no longer exists;
// there was nothing left for it to be RIGHT about.
//
// WHERE THE HOLD LIVES NOW, and therefore what this file may and may not claim:
//
//   · THE VERDICT is `coord.py ready-seats`' `HELD` — one seat has an unanswered ask to the owner.
//     UNIVERSAL: no arm gate, no delivery gate, no interactivity gate, because those three gates
//     WERE the incident. It is coord's to compute and coord's selftest is where it is proven
//     (its W2 rows: universality, precedence over the seat's own check-out, `held-asks` on every
//     row). NOTHING here re-derives it — a second reader of one question is the drift this whole
//     design removes.
//   · THE ENGINE'S HALF is CONSUMPTION: `seeding.js#recordView` takes coord's rows and turns
//     `verdict: HELD` into `view.blocked`, a `done` disposition into `view.done`, and the record's
//     own last row into `foreign`/`notFinished`. That seam — coord's answer reaching the seeding
//     decision — is reachable from neither side's own suite, and it is what this probe measures.
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10): no seat PROCESS runs. Executions are
// synthesized through the store's own writers and published through the engine façade's own
// `publishRecord()` — the call the tick and the attached lane's adoption pass both make. The ask is
// appended to `coordination/messages.md` exactly as `coord.py send` appends it; the seats' check-ins
// and check-outs go through the REAL `coord.py`, so the verdict under test is the shipped one.
//
// ⚠ NO MUTANT TREES. The deleted probe copied `engine/` seven times per run (~8 MiB, 168 s against
// a 180 s timeout, and 869 MiB of orphaned fixtures measured on the VPS). Every guard that survived
// W2 is measured here as a CONTROL/TREATMENT PAIR against the same goal instead — one fact differs
// between the two runs, which discriminates for the same reason a mutant does and costs one fixture.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-owner-ask-hold.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
// A measured fact that is not a pass/fail bar — a residual this probe found and may not rule on.
const findings = [];
function finding(s) { findings.push(s); lines.push(`FINDING  ${s}`); }
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

const record = require('../execution-record');
const seeding = require('../seeding');
const { createEngine } = require('../index');
const { recordBusAnswer } = require('../bus-answer');
const { requirePythonCmd } = require('../../lib/python-cmd');
const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-owner-ask-hold-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
fs.mkdirSync(dataRoot, { recursive: true });
const PYTHON = requirePythonCmd();
const COORD_PY = path.join(IGNITE_SRC, 'team-kit', 'coord.py');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
cfg['launch-specs'] = { bash: {} };
cfg['launch-specs'].bash['probe-hold'] = {
  exec: { argv: ['bash', '-c', 'exec true', '--model', 'probe-hold'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

// A goal folder: alpha (the asking seat) then bravo, which follows it. `arm` and `flagged` exist
// ONLY so the universality arm can turn them OFF — they are the two gates W2 deleted, and a seat
// carrying neither must be held exactly as hard as one carrying both.
function makeGoal(goal, { arm = 'block-and-queue', flagged = true, mode = 'interactive' } = {}) {
  const dir = path.join(workspace, '.rbtv', 'goals', goal);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-hold,alpha,\ntf-hold,bravo,alpha\n');
  fs.writeFileSync(path.join(dir, 'seats', 'alpha', 'seat.md'),
    `---\nseat: alpha\nharness: bash\nmodel: probe-hold\n${flagged ? 'human-interactive: yes\n' : ''}${arm ? `fallback: ${arm}\n` : ''}---\n\nalpha\n`);
  fs.writeFileSync(path.join(dir, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\nharness: bash\nmodel: probe-hold\n---\n\nbravo\n');
  fs.writeFileSync(path.join(dir, 'execution-mode'), `${mode}\n`);
  return dir;
}

// The bus, appended the way `coord.py send` appends it. `re` is not decoration on an `answer` row:
// `coord.py#open_asks` settles ask #n on an `answer`/`verdict` carrying `re: n` and on nothing else.
let msgId = 0;
function bus(goalDir, { from, to, type, body, re = null }) {
  msgId += 1;
  fs.appendFileSync(path.join(goalDir, 'coordination', 'messages.md'),
    `## ${msgId} | from: ${from} | to: ${to} | type: ${type}`
    + `${re === null ? '' : ` | re: ${re}`} | 2026-08-10 12:00\n${body}\n\n`);
  return msgId;
}

// One `coord.py` call against a package, FROM INSIDE IT — the cwd is load-bearing: coord stamps a
// message's origin off it, and a seat's cwd is its own folder within the goal.
function coord(dir, args) {
  try {
    return { ok: true, out: execFileSync(PYTHON, [COORD_PY, '--package', dir, ...args],
      { cwd: dir, encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] }) };
  } catch (err) {
    return { ok: false, out: `${err.stdout || ''}${err.stderr || ''}`.trim() };
  }
}

// A seat ENDING ITS SESSION for real. The check-in is not optional (`checkout` refuses a seat with
// no ACTIVE roster row); `--force` is the re-check-in lift and `--no-export` skips a transcript
// export there is no pane to take.
function checkOut(dir, seat) {
  coord(dir, ['checkin', seat, 'a synthesized session of the owner-ask hold probe', '--pane', '%81', '--force']);
  return coord(dir, ['checkout', '--as', seat, '--force', '--no-export']);
}

function readyRowsOf(dir) {
  const r = coord(dir, ['ready-seats', '--json']);
  try { return JSON.parse(r.out); } catch { return null; }
}
const verdicts = (rows) => Object.fromEntries((rows || []).map((x) => [x.seat, x.verdict]));

function withEngine(fn) {
  const engine = createEngine({
    dbPath: path.join(dataRoot, 'heart.db'), spawnConfigPath: configPath, userManager: false,
  });
  try { return fn(engine); } finally { engine.close(); }
}

// One session of a seat, synthesized: it starts, it runs whatever `during` does (that is where the
// ask is written — an agent asks DURING its turn), and it ends with the given turn status.
function runSession(engine, goal, goalDir, seat, { status = 'done', during = null } = {}) {
  const sessionId = `${goal}-${seat}-${Math.random().toString(16).slice(2, 10)}`;
  const exec = engine.heartStore.recordExecutionStart({
    jobId: `seat-${goal}-${seat}`,
    actionType: 'launch-agent',
    args: JSON.stringify({}),
    enqueuedBy: 'daemon',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    sessionId,
    workdir: path.join(goalDir, 'seats', seat),
  });
  if (during) during(sessionId);
  if (status) {
    engine.heartStore.endTurnAndCloseSession(exec.exec_id, {
      turnStatus: status, sessionStatus: 'closed', endedAt: new Date(),
    });
  }
  return { sessionId, execId: exec.exec_id };
}

const rowsOf = (dir) => record.readExecutionRecord(dir).rows.map((r) => `${r.seat}=${r.outcome || 'open'}`);
const viewOf = (dir) => withEngine((e) => seeding.recordView(e.heartStore, dir, { readyRows: readyRowsOf(dir) }));
const seed = (dir, goal) => withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));

async function main() {
  say('probe-owner-ask-hold — coord\'s HELD verdict reaching the engine\'s seeding decision (W2)');
  say(`fixture: ${tmp}`);
  say('');

  // ── H · THE HOLD, END TO END ────────────────────────────────────────────────────────────────
  say('H — a seat asks the owner, its turn ends, and its dependent does NOT start');
  const goal = 'hold-goal';
  const dir = makeGoal(goal);
  const pass1 = seed(dir, goal);
  check('H0 the wave really started — alpha was due and bravo was not',
    pass1.enqueued.join() === 'alpha', JSON.stringify(pass1.enqueued));

  let askId = null;
  withEngine((e) => runSession(e, goal, dir, 'alpha', {
    during: () => { askId = bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' }); },
  }));
  const refused = checkOut(dir, 'alpha');
  withEngine((e) => e.publishRecord());

  // ⚠ THE RECORD IS **NOT** WHERE THE HOLD IS EXPRESSED ANY MORE, and this arm says so rather than
  // leaving its absence to be read as an oversight. The old probe asserted `alpha=blocked` here.
  // The column is a PROCESS vocabulary now: alpha's turn ended tidily, so `clean` is the true and
  // complete thing this lane witnessed. A `clean` process is exactly what a fail-blocked seat
  // leaves — which is why nothing may read done-ness out of it.
  check('H1 the record row is a PROCESS fact and says `clean` — the hold is NOT in this column, and '
    + 'a tidy exit is all the lane that watched it can honestly attest',
    rowsOf(dir).join() === 'alpha=clean', JSON.stringify(rowsOf(dir)));

  const heldRows = readyRowsOf(dir);
  const heldV = verdicts(heldRows);
  check('H2 coord HOLDS the seat — `HELD`, and it outranks whatever the seat\'s own check-out said. '
    + 'Computed by coord, read here, re-derived nowhere',
    heldV.alpha === 'HELD' && (heldRows.find((r) => r.seat === 'alpha') || {})['held-asks'].includes(askId),
    `verdicts ${JSON.stringify(heldV)} · held-asks ${JSON.stringify((heldRows.find((r) => r.seat === 'alpha') || {})['held-asks'])} · checkout-refused=${!refused.ok}`);

  // THE SEAM THIS PROBE EXISTS FOR: coord's rows reaching the engine's own view.
  const heldView = viewOf(dir);
  check('H3 THE CONSUMPTION SEAM: `recordView` turns that verdict into `view.blocked` — the map\'s '
    + 'VALUE is coord\'s own reason string, so the engine states nothing about WHY',
    heldView.blocked.has('alpha') && /OWNER-ASK HOLD/.test(heldView.blocked.get('alpha') || '')
      && heldView.notFinished.has('alpha') && !heldView.finished.has('alpha'),
    `blocked=${[...heldView.blocked.keys()].join()} · finished=${[...heldView.finished].join() || 'none'} · reason ${String(heldView.blocked.get('alpha') || '').slice(0, 80)}`);

  const pass2 = seed(dir, goal);
  check('H4 …so its dependent does NOT start. NOT VACUOUS: the SAME pass over the SAME goal enqueues '
    + 'bravo at P2, once the owner answers',
    pass2.enqueued.length === 0 && pass2.states.bravo === 'waiting',
    `enqueued ${JSON.stringify(pass2.enqueued)} · bravo=${pass2.states.bravo}`);
  check('H5 the hold is REPORTED, not silent — an operator can see what the wave waits on, and the '
    + 'evidence is the ask, not a lane fact',
    Object.keys(pass2.blockedOnOwner || {}).join() === 'alpha'
      && /OWNER-ASK HOLD/.test(pass2.blockedOnOwner.alpha || ''),
    JSON.stringify(Object.keys(pass2.blockedOnOwner || {})));

  // ── U · UNIVERSALITY: the three gates W2 deleted ────────────────────────────────────────────
  //
  // Each of the three was a way for a real unanswered question to release the DAG anyway, and each
  // is measured by its ABSENCE: a seat declaring NO fallback arm, NOT marked human-interactive, in
  // an AUTONOMOUS goal (so the ferry would have parked its ask at the first rung) is held exactly
  // as hard. Under the deleted ruling every one of these three would have proceeded.
  say('');
  say('U — the seat carrying NONE of the three gates the old hold required is held just the same');
  const gU = 'hold-goal-ungated';
  const dU = makeGoal(gU, { arm: null, flagged: false, mode: 'autonomous' });
  seed(dU, gU);
  withEngine((e) => runSession(e, gU, dU, 'alpha', {
    during: () => bus(dU, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' }),
  }));
  checkOut(dU, 'alpha');
  withEngine((e) => e.publishRecord());
  const passU = seed(dU, gU);
  check('U1 no `fallback:` arm, no `human-interactive:`, an AUTONOMOUS goal — the seat is `HELD` '
    + 'anyway, and the engine reports it. All three of the deleted gates would have released it',
    verdicts(readyRowsOf(dU)).alpha === 'HELD'
      && Object.keys(passU.blockedOnOwner || {}).join() === 'alpha',
    `verdicts ${JSON.stringify(verdicts(readyRowsOf(dU)))} · blockedOnOwner ${JSON.stringify(Object.keys(passU.blockedOnOwner || {}))}`);
  // ⚠ AND HERE IS WHERE THE UNIVERSALITY STOPS — MEASURED, NOT ASSUMED, and stated as a FINDING
  // rather than pinned as a bar, because which way it should go is an owner's call and not this
  // probe's. `HELD` holds THE SEAT: it keeps `ready-seats` from offering alpha and puts it in
  // `view.blocked`. What holds a seat's DEPENDENTS is a DIFFERENT door — coord's `cmd_checkout`
  // refusing a `done` while the ask is open, which is what leaves the successor's `after` member
  // unsatisfied. That door still consults `ask_parked_at_gate`, so on a goal where the ferry PARKED
  // the ask (autonomous, or an unflagged seat) the check-out is admitted and the wave runs on.
  const bravoRan = passU.enqueued.includes('bravo');
  check('U2 …and the SEAT\'s hold is what was made universal, not the DAG\'s: with the ask parked, '
    + 'alpha checks out and bravo starts anyway. The finding below records that, at its real size',
    verdicts(readyRowsOf(dU)).bravo === 'READY' && bravoRan,
    `verdicts ${JSON.stringify(verdicts(readyRowsOf(dU)))} · enqueued ${JSON.stringify(passU.enqueued)}`);
  finding('W2\'s `HELD` is universal at the READY SURFACE — the seat is never offered and the engine '
    + 'reports it blocked-on-owner with none of the three deleted gates present. The hold on a '
    + 'seat\'s DEPENDENTS is still coord\'s `cmd_checkout` refusal, and that door still reads '
    + '`ask_parked_at_gate`: in an AUTONOMOUS goal, or for a seat not marked `human-interactive`, '
    + 'the ask parks, the `done` check-out is admitted, and the successors advance on an unanswered '
    + 'question. Measured at U2. Whether that is the intended residual of the parked-ask workaround '
    + '(`d-parked-ask-autonomous-workaround`) or a surviving limb of the incident W2 closes is an '
    + 'OWNER call, not this probe\'s — it is recorded, not ruled.');

  // ── P · THE RELEASE ─────────────────────────────────────────────────────────────────────────
  //
  // Through the REAL transport: `engine/bus-answer.js#recordBusAnswer` is what the gateway's
  // `record-bus-answer` handler calls when the bridge delivers the owner's Slack reply. It resolves
  // the ask id off this goal's own bus (`openOwnerAsks` — the one surviving half of the deleted
  // hold) and has `coord.py send` write the row, so the bus keeps exactly one writer. A fixture
  // that hand-wrote the row would prove the row's shape and nothing about the code producing it.
  say('');
  say('P — the owner answers, through the real transport, and the wave moves');
  const answer = await recordBusAnswer({
    workspaceRoot: workspace, goal, seat: 'alpha',
    corpus: 'that way — mind the `backticks` and the $(echo literal)',
  });
  check('P0 the reply is RECORDED against the ask it answers — `re` resolved, never guessed',
    answer && answer.recorded === true && answer.re !== null, JSON.stringify(answer));
  // …and the seat, which is still checked IN because H's check-out was REFUSED, now ends its
  // session for real. THAT act is what advances bravo's `after` member; the answer is what lets it
  // through. Exactly ONE thing differs between this call and the refused one at H — the answer row.
  const released = checkOut(dir, 'alpha');
  check('P0b the SAME check-out that was refused while the ask was open now PASSES — the hold lifted '
    + 'for the right reason, not merely lifted',
    !refused.ok && released.ok && /refused \[coord state\]/.test(refused.out)
      && refused.out.includes(`#${askId} to owner`),
    `refused=${!refused.ok} released=${released.ok} · ${String(refused.out).replace(/\s+/g, ' ').slice(0, 140)}`);
  withEngine((e) => e.publishRecord());
  const pass3 = seed(dir, goal);
  check('P1 THE HOLD LIFTS, and for the right reason: ONE act differs from H4 — the owner\'s answer '
    + 'row. coord flips alpha off `HELD`, `view.blocked` empties, and bravo starts',
    verdicts(readyRowsOf(dir)).alpha !== 'HELD'
      && !viewOf(dir).blocked.has('alpha')
      && pass3.enqueued.join() === 'bravo',
    `verdicts ${JSON.stringify(verdicts(readyRowsOf(dir)))} · enqueued ${JSON.stringify(pass3.enqueued)}`);

  // ── D · THE DEGRADE, WHICH IS A DECISION AND NOT A DEFAULT ──────────────────────────────────
  //
  // `readyRows` absent must degrade to "NOTHING is done, NOTHING is held" — never to the old column
  // read. Two callers pass none today. Both directions of a wrong guess are unsafe and they are not
  // equally unsafe: an empty `done` set makes a finished seat merely look unfinished, and the
  // store's own no-double-fire guard plus `foreign` still stop it being re-run; reading the stale
  // column instead would advance a wave off values the migration deliberately left inert.
  say('');
  say('D — `recordView` with no coord answer degrades to "nothing done, nothing held"');
  const degraded = withEngine((e) => seeding.recordView(e.heartStore, dir));
  check('D1 no `readyRows` -> `done` and `blocked` are EMPTY, and the record\'s own `clean` rows are '
    + 'NOT read as done. NOT VACUOUS: the same goal with coord\'s rows answers `done` at D2',
    degraded.done.size === 0 && degraded.blocked.size === 0 && degraded.finished.size === 0,
    `done=${[...degraded.done].join() || 'none'} · blocked=${[...degraded.blocked.keys()].join() || 'none'}`);
  check('D2 CONTROL: the SAME goal WITH coord\'s rows answers `done` for alpha — so D1 measured the '
    + 'degrade and not a goal in which nothing was ever finished',
    viewOf(dir).done.has('alpha'), `done=${[...viewOf(dir).done].join() || 'none'}`);

  // ── F · `done` AND `notFinished` ARE INDEPENDENT, AND COME FROM DIFFERENT SURFACES ──────────
  //
  // Review findings F1 and F2, re-founded. The shape: a seat that checked out `done` AND whose LAST
  // record row is ANOTHER lane's OPEN one — what a crashed foreign revival leaves. Since W2 the two
  // facts come from two different files, so the independence is structural rather than incidental.
  // It must NOT read finished, and it must be REPORTED. These three arms are what the deleted
  // probe's `predicate`, `foreign` and `skipped` mutants pinned; each guard is one line of
  // `recordView`/`seatState` and each is measured here by its observable instead of by a copied
  // source tree (see the header).
  say('');
  say('F — a seat attested `done` with a LATER open row in another lane is not finished, and says so');
  const gF = 'hold-goal-foreign-open';
  const dF = makeGoal(gF, { arm: null });
  seed(dF, gF);
  withEngine((e) => runSession(e, gF, dF, 'alpha'));       // works, in the DAEMON store
  checkOut(dF, 'alpha');                                    // …and checks out `done`
  withEngine((e) => e.publishRecord());
  // THE CONTROL FIRST, so the treatment below has something to differ from: with nothing after it,
  // the attested seat IS finished and its foreign hold is cleared.
  const beforeF = viewOf(dF);
  const passFa = seed(dF, gF);
  check('F0 CONTROL: with nothing running after it the attested seat reads FINISHED and its '
    + 'dependent starts — so the hold at F1 is the open row and not the fixture',
    beforeF.finished.has('alpha') && !beforeF.foreign.has('alpha') && passFa.enqueued.join() === 'bravo',
    `finished=${[...beforeF.finished].join() || 'none'} · foreign=${[...beforeF.foreign.keys()].join() || 'none'} · enqueued ${JSON.stringify(passFa.enqueued)}`);

  // …and now the OTHER lane opens a row for the same seat and never closes it. Written through the
  // real writer, from a real second store placed IN the goal folder — which is what makes it
  // `attached` (`execution-record.laneOf`).
  {
    const attachedEngine = createEngine({
      dbPath: path.join(dF, 'heart.db'), spawnConfigPath: configPath, userManager: false,
    });
    try {
      attachedEngine.heartStore.registerJob({
        jobId: 'seat-alpha',
        actionType: 'launch-agent',
        function: 'the other lane',
        argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string' } }),
        description: 'the other lane', createdAt: isoNow(), updatedAt: isoNow(),
      });
      attachedEngine.heartStore.recordExecutionStart({
        jobId: 'seat-alpha',
        actionType: 'launch-agent',
        args: JSON.stringify({}),
        enqueuedBy: 'attached-execution',
        sessionMode: 'headless',
        firedTick: 1,
        firedAt: new Date(),
        sessionId: `${gF}-revival`,
        workdir: path.join(dF, 'seats', 'alpha'),
      });
      attachedEngine.publishRecord();
    } finally { attachedEngine.close(); }
  }
  const afterF = viewOf(dF);
  const passFb = seed(dF, gF);
  check('F1 the attestation still says `done` and the LAST row is OPEN — `done` and `notFinished` '
    + 'are BOTH true, from two different surfaces, and `finished` is the set that reconciles them',
    afterF.done.has('alpha') && afterF.notFinished.has('alpha') && !afterF.finished.has('alpha'),
    `${JSON.stringify(rowsOf(dF))} · done=${[...afterF.done].join()} · notFinished=${[...afterF.notFinished.keys()].join()} · finished=${[...afterF.finished].join() || 'none'}`);
  // ⚠ BRAVO'S STATE IS `queued`, NOT `waiting`, AND ASSERTING `waiting` HERE WOULD BE WRONG: the F0
  // control already enqueued it off alpha's `done` check-out, and a queue row does not un-queue when
  // a later execution opens for its predecessor. The claim is that THIS pass adds nothing.
  check('F2 …so the seat reads `live`, NOT `done` — the state predicate honours the last word over '
    + 'the attestation, and this pass enqueues nothing further',
    passFb.states.alpha === 'live' && passFb.enqueued.length === 0,
    `${JSON.stringify(passFb.states)} · enqueued ${JSON.stringify(passFb.enqueued)}`);
  check('F3 …and it is REPORTED as held by the other lane and NOT as skipped-because-finished — the '
    + 'foreign deletion and the report both key on `finished`, never on the bare attestation',
    Object.keys(passFb.heldByOtherLane || {}).join() === 'alpha'
      && !passFb.skippedAsFinished.includes('alpha'),
    `heldByOtherLane ${JSON.stringify(Object.keys(passFb.heldByOtherLane || {}))} · skippedAsFinished ${JSON.stringify(passFb.skippedAsFinished)}`);

  // ── N · THE INTERIM SURFACING (W2, adv C25) ─────────────────────────────────────────────────
  //
  // W2 removes the engine's ability to say "this seat did not finish" by publishing `blocked`.
  // Until W3 builds the staff-mail carrier NOTHING else says it either — a crash recorded truthfully
  // and surfaced to nobody is the original stall with a green acceptance. So each non-clean close
  // mints ONE owner `note` on the goal's own bus, through the one writer of that file.
  say('');
  say('N — a non-clean close mints exactly one owner `note`, and a clean one mints none');
  const gN = 'hold-goal-crashed';
  const dN = makeGoal(gN, { arm: null });
  seed(dN, gN);
  withEngine((e) => runSession(e, gN, dN, 'alpha', { status: 'failed' }));
  const pubN = withEngine((e) => e.publishRecord());
  const busN = () => fs.readFileSync(path.join(dN, 'coordination', 'messages.md'), 'utf8');
  const notesN = () => (busN().match(/from: ignite-daemon \| to: owner \| type: note/g) || []).length;
  check('N1 the crash is recorded `crashed` AND surfaced — one owner `note` naming the seat',
    rowsOf(dN).join() === 'alpha=crashed' && pubN.nonClean.length === 1
      && pubN.nonClean[0].seat === 'alpha' && notesN() === 1 && /seat `alpha` ended `crashed`/.test(busN()),
    `${JSON.stringify(rowsOf(dN))} · nonClean ${JSON.stringify(pubN.nonClean.map((n) => `${n.seat}=${n.outcome}`))} · notes ${notesN()}`);
  // ONCE PER EXECUTION, NOT ONCE PER TICK — and the idempotence is `closeExecution`'s stamp, not the
  // publish loop's. A second publish over the same terminal row must mint nothing.
  const pubN2 = withEngine((e) => e.publishRecord());
  check('N2 a SECOND publish over the same terminal row mints NOTHING — once per execution, not '
    + 'once per tick forever',
    pubN2.nonClean.length === 0 && notesN() === 1,
    `nonClean ${JSON.stringify(pubN2.nonClean)} · notes ${notesN()}`);
  check('N3 CONTROL: the CLEAN closes of every goal above minted no note at all — the note tracks '
    + 'the outcome word and not the act of publishing',
    !fs.existsSync(path.join(dir, 'coordination', 'messages.md'))
      || !/from: ignite-daemon \| to: owner \| type: note/.test(fs.readFileSync(path.join(dir, 'coordination', 'messages.md'), 'utf8')),
    'the H/P goal closed `clean` throughout');

  say('');
  say('NOT MEASURED HERE, deliberately: the HELD verdict\'s own computation (coord.py\'s selftest');
  say('owns it — universality, precedence over the check-out, `held-asks` on every row), and the');
  say('ticker\'s dispatch, which no part of this hold touches.');
}

Promise.resolve()
  .then(main)
  .catch((err) => { check('probe completed without throwing', false, err && err.stack ? err.stack.split('\n')[0] : String(err)); })
  .then(() => {
    say('');
    say(`checks: ${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} · failures: ${failures.length}`);
    say(`verdict: ${failures.length ? `FAIL — ${failures.join(' | ')}` : 'PASS'}`);
    say(`wall_ms: ${Date.now() - start}`);
    fs.writeFileSync(OUT_PATH, `${lines.join('\n')}\n`);
    process.stdout.write(`${lines.join('\n')}\n`);
    // Deleted on EVERY path, before `exit` — `process.exit` runs no `finally`. The predecessor probe
    // left 151 orphaned trees holding 869 MiB on the VPS's quota-mounted tmpfs and reddened three
    // neighbouring probes for want of room.
    fs.rmSync(tmp, { recursive: true, force: true });
    process.exit(failures.length ? 1 : 0);
  });

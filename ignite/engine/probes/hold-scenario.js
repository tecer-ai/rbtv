#!/usr/bin/env node
'use strict';

// hold-scenario.js — THE BLOCK-AND-QUEUE HOLD, driven end to end, printed as JSON.
//
// It is a SEPARATE FILE from `probe-block-and-queue-hold.js` for one reason: the probe runs it
// THREE times — once against this repo, and twice against MUTANT copies of `engine/` — and a
// mutation proof needs the scenario to be a thing that can be pointed at a different tree. `node
// hold-scenario.js <ignite-root> <tmpdir>` requires the engine from the root it is given.
//
// NOTHING SPAWNS. `engine.tick()` is deliberately never called: it would DISPATCH the seats this
// scenario enqueues, and what is under test is the seeding DECISION, not the ticker. The publish is
// the façade's own `publishRecord()` — the same `publishToRecord` the tick calls, and the same call
// the attached lane's adoption pass makes at boot. What is SUBSTITUTED, disclosed: the seats'
// PROCESSES. Their executions are synthesized into the store through the store's own writers, and
// the ask is appended to `coordination/messages.md` the way `coord.py send` appends it.
//
// ⚑ THE SEAT NOW ENDS ITS SESSION FOR REAL, AND THAT IS THE HALF THIS FILE WAS MISSING (task
// 7.771). Design D1 deleted seeding's own `after`-cell walk: readiness is
// `coordinate ready-seats --json`'s answer now, and coord reads it off the seats' CHECK-OUTS. A
// scenario that never checks a seat out therefore has no seat that can EVER be ready but the root
// — every `enqueued` below reads `[]` whatever the engine does, and every arm asserting "the
// dependent does not start" passes for the one reason that proves nothing. So the synthesized
// session ends the way a real one does: `coordinate checkin` then `coordinate checkout`, against
// the real `team-kit/coord.py` under the root this scenario was pointed at.
//
// ⚑ …AND ONLY WHEN ASKED (`--coord`, argv[4]). `coord.py` is NOT part of a mutant tree — the probe
// copies and edits `engine/` alone and symlinks everything else — so a mutant's check-outs behave
// EXACTLY as the real run's, and any DAG claim measured against a mutant is structurally unable to
// fire. The DAG half is therefore driven ONCE, on the real run; the mutant runs measure the
// engine's own observables (record rows, seat states, the reports) and skip ~20 subprocesses they
// could not learn anything from. `out.coord` says which kind of run produced these numbers, so a
// reader can never mistake a mutant's empty `enqueued` for a measurement.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const IGNITE = path.resolve(process.argv[2]);
const TMP = path.resolve(process.argv[3]);
const COORD_MODE = process.argv[4] === '--coord';
const COORD_PY = path.join(IGNITE, 'team-kit', 'coord.py');
// The ONE interpreter resolver this repo has, exactly as `engine/seeding.js` and
// `engine/bus-answer.js` name it (`python3` is a Microsoft-Store LIE on Windows).
const PYTHON = COORD_MODE ? require(path.join(IGNITE, 'lib', 'python-cmd')).requirePythonCmd() : null;
const { recordBusAnswer } = require(path.join(IGNITE, 'engine', 'bus-answer.js'));

const { createEngine } = require(path.join(IGNITE, 'engine', 'index.js'));
const record = require(path.join(IGNITE, 'engine', 'execution-record.js'));
const yaml = require(path.join(IGNITE, 'node_modules', 'js-yaml'));

const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

// ── one spawn config, shared by every goal below ──────────────────────────────────────────────
const dataRoot = path.join(TMP, 'data');
fs.mkdirSync(dataRoot, { recursive: true });
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(TMP, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
// 7.787: `profiles:` is `launch-specs:`, keyed by (harness, model). The `bash -c` shim keeps
// the argv agreeing with the key (`profiles.js#validateSpecKey` refuses a disagreement at
// LOAD) while running exactly what it ran before; the goal's seats declare the matching cast.
cfg['launch-specs'] = { bash: {} };
cfg['launch-specs'].bash['probe-hold'] = {
  exec: { argv: ['bash', '-c', 'exec true', '--model', 'probe-hold'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(TMP, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const workspace = path.join(TMP, 'workspace');

// A goal folder: alpha (the asking seat) then bravo, which follows it.
// `mode` is the goal's execution mode, and it is what decides whether an ask is DELIVERED or
// PARKED — i.e. whether the hold can fire at all (owner ruling d-parked-ask-autonomous-workaround).
// `interactive` is the default here because every arm written before that ruling assumes a
// deliverable ask.
function makeGoal(goal, { arm, mode = 'interactive', flagged = true }) {
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

// The bus, appended the way `coord.py send` appends it — `## <id> | from: … | to: … | type: … | ts`
// with a blank line after the body, and always newline-terminated (the ferry's torn-write rule).
//
// ⚠ `re` IS NOT DECORATION ON AN `answer` ROW, and leaving it off is how a fixture ends up
// measuring two readers instead of one. `coord.py#open_asks` settles ask #n on an `answer`/`verdict`
// carrying `re: n` AND ON NOTHING ELSE, so a bare `type: answer` leaves the ask open to the D8
// check-out gate; `execution-record.js#openOwnerAsks` closes the OLDEST open ask on any `answer`
// addressed to the seat, `re:` or no `re:`. The live transport always writes one
// (`bus-answer.js` resolves the id and passes `--re`), so the two agree in production — the
// divergence is reachable only from a hand-written or peer-written answer, and is filed as its own
// task rather than pinned here.
let msgId = 0;
function bus(goalDir, { from, to, type, body, re = null }) {
  msgId += 1;
  fs.appendFileSync(path.join(goalDir, 'coordination', 'messages.md'),
    `## ${msgId} | from: ${from} | to: ${to} | type: ${type}`
    + `${re === null ? '' : ` | re: ${re}`} | 2026-08-10 12:00\n${body}\n\n`);
  return msgId;
}

// ── THE SEAT'S OWN ENDING, through coord (see the header) ─────────────────────────────────────

// One `coord.py` call against a package, FROM INSIDE IT. The cwd is load-bearing and not cosmetic:
// coord stamps a message's origin off it (`origin_of` / `is_own_send`), and a seat's cwd is its own
// folder within the goal — run from elsewhere every row reads `external` and the D8 gate, which
// narrows `open_asks` by sender, sees none of this seat's asks.
function coord(dir, args) {
  try {
    // `stdio: 'pipe'` on all three, deliberately: the default INHERITS stderr, so coord's refusals
    // — which are the expected outcome of half these calls — would print into this scenario's own
    // stderr and reach the probe as if something had gone wrong.
    return { ok: true, out: execFileSync(PYTHON, [COORD_PY, '--package', dir, ...args],
      { cwd: dir, encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'] }) };
  } catch (err) {
    return { ok: false, out: `${err.stdout || ''}${err.stderr || ''}`.trim() };
  }
}

// A seat ENDING ITS SESSION. `null` when coord is not being driven; otherwise `{ok, out}`, where
// `ok: false` is coord REFUSING the disposition — which is exactly what D8's hold looks like from
// the seat's side, and the reason the refusal text is carried back rather than discarded.
//
// The check-in is not optional: `checkout` refuses a seat with no ACTIVE roster row. `--force` on
// it is the zombie-double-launch lift (this seat re-checks-in for its revival on the same pane),
// and `--no-export` skips a transcript export there is no pane to take.
//
// Only the `done` disposition is driven here. `--incomplete` — the escape the refusal names — is
// coord's own to prove and it does: its selftest's D8 row A runs the SAME seat with the SAME open
// ask out that door and asserts the successor stays BLOCKED. A second copy here would be a second
// place to keep in step, not a second measurement.
function checkOut(dir, seat) {
  if (!COORD_MODE) return null;
  coord(dir, ['checkin', seat, 'a synthesized session of the hold scenario', '--pane', '%81', '--force']);
  return coord(dir, ['checkout', '--as', seat, '--force', '--no-export']);
}

// coord's OWN readiness verdicts, so an arm can report WHY the wave did or did not move rather
// than only that it did not.
function coordVerdicts(dir) {
  if (!COORD_MODE) return null;
  const r = coord(dir, ['ready-seats', '--json']);
  try {
    return Object.fromEntries(JSON.parse(r.out).map((x) => [x.seat, x.verdict]));
  } catch { return { unparsed: String(r.out).slice(0, 200) }; }
}

function withEngine(fn) {
  const engine = createEngine({
    dbPath: path.join(dataRoot, 'heart.db'),
    
    spawnConfigPath: configPath,
    userManager: false,
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

// ── THE MAIN SCENARIO: ask → hold → answer → release ──────────────────────────────────────────
async function scenario() {
  const goal = 'hold-goal';
  const dir = makeGoal(goal, { arm: 'block-and-queue' });
  const out = { coord: COORD_MODE };

  // 1. the wave starts: alpha is due, bravo waits on it
  const pass1 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.seeded = pass1.enqueued;

  // 2. alpha's session: it ASKS THE OWNER on the bus, then exits 0 — the exact 7.626 shape — and
  //    then tries to END, which is where the hold is expressed to the DAG now (D8). coord REFUSES
  //    the `done`: recording it is what would start every successor on an unsettled question.
  let askId = null;
  withEngine((e) => runSession(e, goal, dir, 'alpha', {
    during: () => { askId = bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' }); },
  }));
  const refused = checkOut(dir, 'alpha');
  out.checkoutHeld = refused && {
    ok: refused.ok,
    refusal: refused.out.includes('refused [coord state]'),
    namesTheAsk: refused.out.includes(`#${askId} to owner`) && refused.out.includes('which way?'),
    namesTheWayOut: refused.out.includes('checkout --incomplete'),
  };
  withEngine((e) => e.publishRecord());
  out.recordAfterAsk = rowsOf(dir);

  // 3. THE HOLD: the next seeding pass must not start bravo. NOT vacuous — step 5 runs the SAME
  //    pass over the SAME goal after the check-out lands, and it DOES start it.
  const pass2 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedWhileHeld = pass2.enqueued;
  out.statesWhileHeld = pass2.states;
  out.blockedOnOwner = Object.keys(pass2.blockedOnOwner || {});
  out.readyWhileHeld = coordVerdicts(dir);

  // 4. THE ANSWER LANDS, THROUGH THE REAL TRANSPORT. `engine/bus-answer.js#recordBusAnswer` is the
  //    module the gateway's `record-bus-answer` handler calls when the bridge delivers the owner's
  //    Slack reply — it resolves the ask id off this goal's own bus and has `coord.py send` write
  //    the `type: answer | re: <n>` row, so the bus is written by its one writer. Called here
  //    rather than imitated: a fixture that hand-writes the row proves the row's shape and nothing
  //    about the code that produces it. The corpus carries backticks and `$(…)` on purpose — the
  //    body rides `--file` and never touches a shell.
  //
  //    The owner's reply ALSO mints a session at the ASKING SEAT'S OWN HOME (`forward-path.js`,
  //    route kind `agent`). While that revived session RUNS, bravo must STILL wait — the F6
  //    concurrency the hold closes, and now also coord's answer, since nothing has checked out yet.
  out.answer = await recordBusAnswer({
    workspaceRoot: workspace, goal, seat: 'alpha',
    corpus: 'that way — mind the `backticks` and the $(echo literal)',
  });
  const revival = withEngine((e) => runSession(e, goal, dir, 'alpha', { status: null }));
  withEngine((e) => e.publishRecord());
  out.recordDuringRevival = rowsOf(dir);
  const pass3 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedDuringRevival = pass3.enqueued;
  out.statesDuringRevival = pass3.states;

  // 5. the revived session finishes the work and checks out — and THIS TIME coord admits the
  //    `done`, because the ask it was held on now carries an answer. That check-out is what
  //    releases the wave; the record's `done` is what stops the seat being re-dispatched.
  withEngine((e) => e.heartStore.endTurnAndCloseSession(revival.execId, {
    turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date(),
  }));
  const released = checkOut(dir, 'alpha');
  out.checkoutReleased = released && { ok: released.ok, out: released.out.trim().slice(0, 160) };
  withEngine((e) => e.publishRecord());
  out.recordFinal = rowsOf(dir);
  const pass4 = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  out.enqueuedAfterAnswer = pass4.enqueued;
  out.statesAfterAnswer = pass4.states;
  out.readyAfterAnswer = coordVerdicts(dir);

  // 6. THE RELAUNCH ESCAPE, on a goal held with no answer coming: the grant clears the hold the
  //    same way it clears a foreign one.
  const g2 = 'hold-goal-relaunch';
  const d2 = makeGoal(g2, { arm: 'block-and-queue' });
  withEngine((e) => e.seedGoal({ goalFolder: d2, goal: g2, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g2, d2, 'alpha', {
    during: () => bus(d2, { from: 'alpha', to: 'owner', type: 'ask', body: 'anyone?' }),
  }));
  withEngine((e) => e.publishRecord());
  //    Measured as a PAIR against the same goal: without the grant it is held, with it it is not.
  out.relaunchWithout = withEngine((e) => e.seedGoal({ goalFolder: d2, goal: g2, profile: 'probe-hold' })).states;
  out.relaunchWith = grantOn(d2, g2).states;

  // 7. THE SECOND HOLD (review F1). The seat is answered, works, and asks AGAIN — so the record
  //    reads `blocked, done, blocked` and the seat carries a `done` row while being held. That is
  //    the shape whose `--relaunch` was a NO-OP: the grant bailed on "has a done row" before it
  //    reached the deletes, and the wave was stuck with no escape but hand-editing the record.
  const g3 = 'hold-goal-second-ask';
  const d3 = makeGoal(g3, { arm: 'block-and-queue' });
  withEngine((e) => e.seedGoal({ goalFolder: d3, goal: g3, profile: 'probe-hold' }));
  const ask = (dir) => () => bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' });
  withEngine((e) => runSession(e, g3, d3, 'alpha', { during: ask(d3) }));   // asks → held
  withEngine((e) => e.publishRecord());
  withEngine((e) => runSession(e, g3, d3, 'alpha'));                        // the revival → done
  withEngine((e) => e.publishRecord());
  withEngine((e) => runSession(e, g3, d3, 'alpha', { during: ask(d3) }));   // asks AGAIN → held
  withEngine((e) => e.publishRecord());
  out.secondHoldRecord = rowsOf(d3);
  const pass5 = withEngine((e) => e.seedGoal({ goalFolder: d3, goal: g3, profile: 'probe-hold' }));
  out.secondHoldStates = pass5.states;
  out.secondHoldEnqueued = pass5.enqueued;
  out.secondHoldBlockedOnOwner = Object.keys(pass5.blockedOnOwner || {});
  out.secondHoldSkippedAsFinished = pass5.skippedAsFinished;
  out.secondHoldRelaunch = grantOn(d3, g3).states;

  // 8. A GENUINELY BLOCKED TURN IS NOT A SPENT HOLD (review F3). A turn can END `blocked` for its
  //    own reasons — the store validates the status and the ticker redispatches — and that writes a
  //    `blocked` record row too. Counting it as a hold already paid made the NEXT turn's real ask
  //    read as already-held, publishing `done` and releasing the dependent unanswered.
  const g4 = 'hold-goal-turn-blocked';
  const d4 = makeGoal(g4, { arm: 'block-and-queue' });
  withEngine((e) => e.seedGoal({ goalFolder: d4, goal: g4, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g4, d4, 'alpha', { status: 'blocked' }));  // blocked for its OWN reasons
  withEngine((e) => e.publishRecord());
  out.turnBlockedFirstRow = rowsOf(d4);
  withEngine((e) => runSession(e, g4, d4, 'alpha', { during: ask(d4) }));    // then asks and exits 0
  withEngine((e) => e.publishRecord());
  out.turnBlockedRecord = rowsOf(d4);
  const pass6 = withEngine((e) => e.seedGoal({ goalFolder: d4, goal: g4, profile: 'probe-hold' }));
  out.turnBlockedEnqueued = pass6.enqueued;
  out.turnBlockedStates = pass6.states;

  // 9. A SEAT WHOSE LAST ROW IS SOMEBODY ELSE'S OPEN ONE (review F2) — `done, open`, the shape a
  //    crashed foreign revival leaves. It must not read FINISHED, and it must be REPORTED: the
  //    reason recordView computes for it was read by nothing.
  const g5 = 'hold-goal-foreign-open';
  const d5 = makeGoal(g5, { arm: null });
  withEngine((e) => e.seedGoal({ goalFolder: d5, goal: g5, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g5, d5, 'alpha'));                         // done, in the DAEMON store
  withEngine((e) => e.publishRecord());
  // …and the OTHER lane opens a row for the same seat and never closes it. Written through the real
  // writer, from a real second store placed in the goal folder (which is what makes it `attached`).
  const attachedEngine = createEngine({
    dbPath: path.join(d5, 'heart.db'), spawnConfigPath: configPath, userManager: false,
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
      sessionId: `${g5}-revival`,
      workdir: path.join(d5, 'seats', 'alpha'),
    });
    attachedEngine.publishRecord();
  } finally { attachedEngine.close(); }
  out.foreignOpenRecord = rowsOf(d5);
  const pass7 = withEngine((e) => e.seedGoal({ goalFolder: d5, goal: g5, profile: 'probe-hold' }));
  out.foreignOpenStates = pass7.states;
  out.foreignOpenSkippedAsFinished = pass7.skippedAsFinished;
  out.foreignOpenHeldByOtherLane = Object.keys(pass7.heldByOtherLane || {});
  out.foreignOpenEnqueued = pass7.enqueued;

  // 10. THE MODE SPLIT (owner ruling d-parked-ask-autonomous-workaround). The SAME seat, the SAME
  //     arm, the SAME ask — in an AUTONOMOUS goal. The ferry parks the ask (nobody is told, so
  //     nobody can answer), so the seat is NOT held: it took its authored autonomous workaround,
  //     its turn's real outcome is published, and the wave COMPLETES. Autonomous means the workflow
  //     finishes.
  const g6 = 'hold-goal-autonomous';
  const d6 = makeGoal(g6, { arm: 'block-and-queue', mode: 'autonomous' });
  withEngine((e) => e.seedGoal({ goalFolder: d6, goal: g6, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g6, d6, 'alpha', { during: ask(d6) }));
  // …and its check-out is ADMITTED, which is the same fork read at coord's end: `ask_parked_at_gate`
  // mirrors the ferry's gates there exactly as `askParkedAtGate` does here, and a `done` refused
  // here would be a wave the owner cannot restart by answering.
  out.autonomousCheckout = checkOut(d6, 'alpha');
  const publish = withEngine((e) => e.publishRecord());
  out.autonomousRecord = rowsOf(d6);
  out.autonomousProceeded = (publish.proceeded || []).map((p) => `${p.seat}:${p.evidence.includes('gate: execution-mode')}`);
  const pass8 = withEngine((e) => e.seedGoal({ goalFolder: d6, goal: g6, profile: 'probe-hold' }));
  out.autonomousEnqueued = pass8.enqueued;
  out.autonomousStates = pass8.states;
  out.autonomousBlockedOnOwner = Object.keys(pass8.blockedOnOwner || {});
  // …and the ask itself is still ON THE BUS, which is what makes it reviewable on return.
  out.autonomousBusHasAsk = fs.readFileSync(path.join(d6, 'coordination', 'messages.md'), 'utf8')
    .includes('from: alpha | to: owner');

  // 11. THE OTHER GATE, same fork: an UNFLAGGED seat's row parks at gate 1 (`human-interactive`)
  //     even in an interactive goal. Same verdict — not held — through the other rung.
  const g7 = 'hold-goal-unflagged';
  const d7 = makeGoal(g7, { arm: 'block-and-queue', flagged: false });
  withEngine((e) => e.seedGoal({ goalFolder: d7, goal: g7, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g7, d7, 'alpha', { during: ask(d7) }));
  out.unflaggedCheckout = checkOut(d7, 'alpha');
  const publish7 = withEngine((e) => e.publishRecord());
  out.unflaggedRecord = rowsOf(d7);
  out.unflaggedGate = (publish7.proceeded || []).map((p) => (p.evidence.match(/gate: ([a-z-]+)/) || [])[1]);
  out.unflaggedEnqueued = withEngine((e) => e.seedGoal({ goalFolder: d7, goal: g7, profile: 'probe-hold' })).enqueued;

  // 12. THE LOOP RE-FIRE (owner ruling 2026-08-12, `concepts/loop.md`): a grant releases a
  //     FINISHED seat — a judge's FAIL verdict re-dispatches a builder whose row says `done` on
  //     its own slot. Measured as a pair against the same goal: without the grant the seat reads
  //     `done`; with it, it is dispatchable again. The "must not re-run completed work" guard now
  //     lives at the grant's MINT (a deliberate act), not in the eligibility reader.
  const g8 = 'hold-goal-done-relaunch';
  const d8 = makeGoal(g8, { arm: 'block-and-queue' });
  withEngine((e) => e.seedGoal({ goalFolder: d8, goal: g8, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, g8, d8, 'alpha'));                         // works, checks out done
  withEngine((e) => e.publishRecord());
  out.doneRelaunchWithout = withEngine((e) => e.seedGoal({ goalFolder: d8, goal: g8, profile: 'probe-hold' })).states;
  out.doneRelaunchWith = grantOn(d8, g8).states;

  return out;
}

// A `--relaunch alpha` seeding pass, through the real seedGoal with the grant set.
function grantOn(dir, goal) {
  return withEngine((e) => {
    const { seedGoal } = require(path.join(IGNITE, 'engine', 'seeding.js'));
    return seedGoal({
      heartStore: e.heartStore, goalFolder: dir, goal, profile: 'probe-hold',
      relaunch: new Set(['alpha']),
    });
  });
}

// ── THE CONTROLS: every neighbouring case must be UNTOUCHED ───────────────────────────────────
//
// Each one ENDS ITS SESSION like the held seat does, and must get all the way through: an arm that
// only checked the record row would leave "does this gate hold a seat the ruling never spoke
// about" unmeasured, and on a DAG that is a stall nobody but the seat's own `--incomplete` clears.
function control(name, { arm, ask = true, answeredBeforeExit = false }) {
  const goal = `ctl-${name}`;
  const dir = makeGoal(goal, { arm });
  withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  withEngine((e) => runSession(e, goal, dir, 'alpha', {
    during: () => {
      if (!ask) return;
      const id = bus(dir, { from: 'alpha', to: 'owner', type: 'ask', body: 'which way?' });
      if (answeredBeforeExit) bus(dir, { from: 'charlie', to: 'alpha', type: 'answer', body: 'that way', re: id });
    },
  }));
  const co = checkOut(dir, 'alpha');
  withEngine((e) => e.publishRecord());
  const pass = withEngine((e) => e.seedGoal({ goalFolder: dir, goal, profile: 'probe-hold' }));
  return {
    record: rowsOf(dir), enqueued: pass.enqueued, states: pass.states,
    checkedOut: co === null ? null : co.ok,
  };
}

scenario().then((result) => {
  // ⚠ THE CONTROLS ARE THE REAL RUN'S ONLY, and skipping them elsewhere is a measured cost, not
  // tidiness: they are asserted at C1–C5 off `r.controls` — the real run — and NO mutant arm reads
  // them, because none of the seven mutations can change a seat that was never held. Computing
  // them in all eight runs cost ~4.5 s × 7 for numbers nothing looked at, on a probe already
  // running at 168 s against the suite's 180 s per-probe timeout. `null` rather than `{}` so a
  // future arm reading them from a mutant run fails loudly instead of on an empty object.
  result.controls = COORD_MODE ? {
    'never-asked': control('never-asked', { arm: 'block-and-queue', ask: false }),
    'default-and-disclose': control('default-and-disclose', { arm: 'default-and-disclose' }),
    park: control('park', { arm: 'park' }),
    'no-arm-declared': control('no-arm-declared', { arm: null }),
    'answered-before-exit': control('answered-before-exit', { arm: 'block-and-queue', answeredBeforeExit: true }),
  } : null;
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}).catch((err) => {
  // The probe parses this file's stdout as JSON, so a throw must not look like an empty result:
  // exit non-zero and put the reason on stderr, where `execFileSync` carries it into the arm.
  process.stderr.write(`${err && err.stack ? err.stack : String(err)}\n`);
  process.exit(1);
});

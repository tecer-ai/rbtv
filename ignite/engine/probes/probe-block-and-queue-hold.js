#!/usr/bin/env node
'use strict';

// probe-block-and-queue-hold — THE MECHANICAL HOLD (owner ruling
// `1-projects/rbtv-sb-merge-refactor-core-build/decisions.md#d-block-and-queue-mechanical-hold`,
// settling the 7.626 `#decision` row).
//
// THE RULING, and therefore the two arms this probe exists to be: a `block-and-queue` seat that
// asks the owner and exits 0 is NOT `done` to the DAG — its dependents do NOT start (HOLD arm) —
// until the answer arrives, and then they DO (PAIRED arm). Before this build the two fallback arms
// were distinguishable at the owner's Slack surface and identical at the DAG.
//
// ⚑ RE-FOUNDED FOR D1/D8 (task 7.771). The ruling is unchanged; WHERE IT IS ENFORCED MOVED, and
// this probe was measuring the old place. Design D1 deleted `seeding.js`'s own `after`-cell walk —
// readiness is `coordinate ready-seats --json`'s answer now, read off the seats' CHECK-OUTS — so
// the hold on a seat's DEPENDENTS is expressed by coord refusing the `done` check-out (design D8),
// not by the engine's record row. The engine's half is what remains genuinely its own: the seat is
// not re-dispatched, the wave says WHY it is waiting, and the attached lane hands the terminal
// back. The two halves are named per arm below, because a reader who mixes them up will "fix" a
// green one.
//
// ⚠ WHAT THAT COST BEFORE IT WAS FOUND: this probe stood RED with twelve failing arms, and the
// twelve were not twelve findings — the scenario never checked a seat out, so NO seat could ever
// be READY but the root, and every arm reading `enqueued` read `[]` no matter what the engine did.
// `M-outcome`, `M-predicate` and `M-spent` were asserting that a defanged guard makes the dependent
// START: unreachable by construction, so those three were pinned to an outcome no mutation could
// produce. A mutant that cannot go red is worse than no mutant, and the fix is not a threshold — it
// is measuring each half where it now lives.
//
// WHAT IS MEASURED WHERE:
//   · the HOLD, the RELEASE and every neighbouring case that must stay untouched — `hold-scenario.js`
//     beside this file, run as a child against THIS repo (arms H*/P*/C*). The real run is given
//     `--coord`, so its seats end their sessions through the real `coord.py`: the refusal, the
//     owner's answer written by the real `engine/bus-answer.js`, and the check-out that then
//     passes. That round trip is the seam neither half's own suite can reach — `coord.py`'s
//     selftest has no engine and the engine's fixtures had no check-out.
//   · that the arms are not vacuous — the SAME scenario run against MUTANT copies of `engine/`,
//     each with one line of the guard defanged (arms M*). Mutant runs get NO `--coord`: `coord.py`
//     is symlinked into a mutant tree, never copied, so its verdicts are identical in every run and
//     a DAG claim measured there could not move. Each mutant asserts the ENGINE observable its own
//     guard owns.
//   · the ATTACHED lane's own two seams — `evaluateExit` and the foreground carriage — in process
//     (arms A*), because that lane has a terminal carriage the daemon lane does not.
//
// SUBSTITUTED, disclosed up front (`bars.md` 10): no seat PROCESS runs. Executions are synthesized
// through the store's own writers and published through the engine façade's own `publishRecord()`
// (the call the tick and the attached lane's adoption pass both make); the ask is appended to
// `coordination/messages.md` exactly as `coord.py send` appends it. What that leaves unmeasured is
// the ticker's dispatch, which no part of this ruling touches.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-block-and-queue-hold.out');
const SCENARIO = path.join(__dirname, 'hold-scenario.js');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-bq-hold-'));

// Run the scenario against an ignite root, in a child, with its own fixture dir. `coord` drives the
// seats' real check-outs (see the header) — the real run only.
function runScenario(igniteRoot, tag, { coord = false } = {}) {
  const dir = path.join(tmp, tag);
  fs.mkdirSync(dir, { recursive: true });
  const raw = execFileSync(process.execPath, [SCENARIO, igniteRoot, dir, ...(coord ? ['--coord'] : [])],
    { encoding: 'utf8', timeout: 120000 });
  return JSON.parse(raw);
}

// A MUTANT TREE: every entry of `ignite/` symlinked (so `../server`, `../bridges`, `../team-kit`
// and `node_modules` resolve to the real, unmutated code) except `engine/`, which is copied and
// then edited. One line changes per mutant, and the edit is ASSERTED to have landed — a mutation
// that silently did not apply is a probe that proves nothing (`ponytail:` a sed on source text; if
// the guard is ever reworded, the assertion below goes red rather than the arm going quietly
// vacuous).
//
// ⚠ THE MATCH STRINGS CARRY NO LEADING WHITESPACE, and that is a fix, not a style. They used to,
// and a `seeding.js` edit that merely RE-INDENTED the `grant` mutant's line un-anchored it: the
// site count fell to 0 and the arm reported nothing while the guard it guards went unmeasured.
// Only the `applied` assertion below made that visible instead of silent — keep it, and keep the
// strings indentation-free so an ordinary re-indent cannot reach them.
function mutantRoot(tag, from, to) {
  const root = path.join(tmp, `mutant-${tag}`);
  fs.mkdirSync(root, { recursive: true });
  for (const e of fs.readdirSync(IGNITE_SRC)) {
    if (e === 'engine') continue;
    fs.symlinkSync(path.join(IGNITE_SRC, e), path.join(root, e));
  }
  fs.cpSync(path.join(IGNITE_SRC, 'engine'), path.join(root, 'engine'), { recursive: true });
  const targets = ['execution-record.js', 'seeding.js']
    .map((f) => path.join(root, 'engine', f))
    .filter((p) => fs.readFileSync(p, 'utf8').includes(from));
  if (targets.length !== 1) return { root, applied: false, where: `${targets.length} file(s) carry the mutation site` };
  const src = fs.readFileSync(targets[0], 'utf8');
  fs.writeFileSync(targets[0], src.replace(from, to));
  return { root, applied: true, where: path.basename(targets[0]) };
}

function main() {
  say('probe-block-and-queue-hold — the ruling d-block-and-queue-mechanical-hold, measured');
  say(`fixture: ${tmp}`);
  say('');

  // ── V · THE VOCABULARY IS THE FERRY'S, NOT A SECOND SPELLING ────────────────────────────────
  const ferry = require('../../bridges/chat/bus-ferry');
  const rec = require('../execution-record');
  check('V1 the arm this hold keys on IS one of the ferry\'s declared arms — one vocabulary, not two',
    ferry.FALLBACK_ARMS.includes(rec.FALLBACK_BLOCK_AND_QUEUE),
    `${rec.FALLBACK_BLOCK_AND_QUEUE} ∈ ${JSON.stringify(ferry.FALLBACK_ARMS)}`);
  check('V2 the held outcome is the STORE\'s own turn word — no term is minted for this',
    rec.BLOCKED === 'blocked'
      && require('../../server/heart/heart-store').TERMINAL_TURN_STATUSES.has(rec.BLOCKED),
    `outcome word: '${rec.BLOCKED}'`);

  // ── H · THE HOLD ARM ────────────────────────────────────────────────────────────────────────
  say('');
  say('H — a block-and-queue seat asks the owner, exits 0, and its dependent does NOT start');
  const r = runScenario(IGNITE_SRC, 'real', { coord: true });
  check('H0 the wave really started — alpha was due and bravo was not',
    r.seeded.join() === 'alpha', JSON.stringify(r.seeded));
  check('H0b the scenario really drove coord — every DAG arm below is void if it did not, and so '
    + 'are the five controls, which only the coord run computes',
    r.coord === true && Boolean(r.checkoutHeld) && Boolean(r.readyWhileHeld) && Boolean(r.controls),
    `coord=${r.coord} · controls=${r.controls ? Object.keys(r.controls).length : 'ABSENT'}`);
  // ── the DAG half, which is coord's since D1 ──
  check('H1 THE RULING, where it is now enforced: the seat may not RECORD `done` while its ask to '
    + 'the owner is unanswered. `done` is the one disposition that advances the DAG and readiness '
    + 'is read off the check-out, so this refusal IS the hold on the dependents — and it names the '
    + 'ask, its words, and the honest way out rather than leaving the seat to guess',
    r.checkoutHeld.ok === false && r.checkoutHeld.refusal
      && r.checkoutHeld.namesTheAsk && r.checkoutHeld.namesTheWayOut,
    JSON.stringify(r.checkoutHeld));
  check('H2 …so its dependent does NOT start — nothing is enqueued while the ask is open, and '
    + 'coord says why. NOT VACUOUS: the SAME pass over the SAME goal enqueues bravo at P3, once '
    + 'the check-out lands',
    r.enqueuedWhileHeld.length === 0 && r.statesWhileHeld.bravo === 'waiting'
      && r.readyWhileHeld.bravo === 'BLOCKED',
    `enqueued ${JSON.stringify(r.enqueuedWhileHeld)} · bravo=${r.statesWhileHeld.bravo} · coord ${JSON.stringify(r.readyWhileHeld)}`);
  // ── the engine half, which is still its own ──
  check('H3 the seat\'s record row says `blocked`, NOT `done` — the outcome no scheduler reads as finished',
    r.recordAfterAsk.join() === 'alpha=blocked', JSON.stringify(r.recordAfterAsk));
  check('H4 …and the held seat itself is NOT `done` and NOT re-dispatchable',
    r.statesWhileHeld.alpha === 'live', `alpha=${r.statesWhileHeld.alpha}`);
  check('H5 the hold is REPORTED, not silent — an operator can see what the wave is waiting on',
    r.blockedOnOwner.join() === 'alpha', JSON.stringify(r.blockedOnOwner));

  // ── P · THE PAIRED ARM ──────────────────────────────────────────────────────────────────────
  say('');
  say('P — the answer lands (a session at the asking seat\'s own home) and the dependent starts');
  // The answer's own leg, structurally: the bridge homes an `agent`-thread reply at THAT seat.
  const { resolveGoalSeat } = require('../../bridges/chat/forward-path');
  const wsRoot = path.join(tmp, 'real', 'workspace');
  check('P0 the answer leg homes at the ASKING seat — the revival this release depends on exists',
    resolveGoalSeat(wsRoot, 'hold-goal', 'alpha').ok === true,
    JSON.stringify(resolveGoalSeat(wsRoot, 'hold-goal', 'alpha')));
  // THE TRANSPORT, exercised rather than imitated. `engine/bus-answer.js#recordBusAnswer` is what
  // the gateway's `record-bus-answer` handler calls when the bridge delivers the owner's reply; it
  // resolves the ask id off this goal's own bus (`openOwnerAsks`, the hold's own pairing) and has
  // `coord.py send` write the row, so the bus keeps exactly one writer. A fixture that hand-wrote
  // the row would prove the row's shape and nothing about the code that produces it.
  check('P0b the owner\'s reply is RECORDED on the bus by the real transport, against the ask it '
    + 'answers — `re` resolved, never guessed, which is what keeps the row from settling nothing',
    r.answer && r.answer.recorded === true && r.answer.re !== null,
    JSON.stringify(r.answer));
  check('P1 while the REVIVED session runs, the dependent STILL waits — the F6 concurrency is closed',
    r.enqueuedDuringRevival.length === 0 && r.statesDuringRevival.bravo === 'waiting'
      && r.statesDuringRevival.alpha === 'live',
    `enqueued ${JSON.stringify(r.enqueuedDuringRevival)} · ${JSON.stringify(r.statesDuringRevival)}`);
  check('P2 the revived session\'s work lands COHERENTLY in the record — the ask, then the outcome',
    r.recordFinal.join() === 'alpha=blocked,alpha=done', JSON.stringify(r.recordFinal));
  check('P3 THE RULING\'s other half: the SAME check-out that was refused at H1 now PASSES, coord '
    + 'flips the seat to DONE and its dependent starts. The hold lifted for the right reason — one '
    + 'act differs between H1 and here, the owner\'s answer row — not merely lifted',
    r.checkoutReleased.ok === true && r.readyAfterAnswer.alpha === 'DONE'
      && r.enqueuedAfterAnswer.join() === 'bravo' && r.statesAfterAnswer.alpha === 'done',
    `checkout ok=${r.checkoutReleased.ok} · coord ${JSON.stringify(r.readyAfterAnswer)} · enqueued ${JSON.stringify(r.enqueuedAfterAnswer)}`);
  check('P4 the operator escape works too — the SAME held goal is `live` without a `--relaunch` grant and not with it',
    r.relaunchWithout.alpha === 'live' && r.relaunchWith.alpha !== 'live',
    `without=${r.relaunchWithout.alpha} · with=${r.relaunchWith.alpha}`);
  check('P5 the loop re-fire (owner ruling 2026-08-12) — a grant releases a FINISHED seat: `done` '
    + 'without it, dispatchable again with it',
    r.doneRelaunchWithout.alpha === 'done' && r.doneRelaunchWith.alpha !== 'done',
    `without=${r.doneRelaunchWithout.alpha} · with=${r.doneRelaunchWith.alpha}`);

  // ── R · THE REVIEW'S THREE FINDINGS, each an arm ────────────────────────────────────────────
  say('');
  say('R — review 51cd2eb: the second hold and its escape (F1), the unreported last word (F2), a');
  say('    genuinely blocked turn that is not a spent hold (F3)');
  say('    ⚠ these goals never check out, so their `enqueued` is EMPTY for a reason that has');
  say('      nothing to do with the guard under test — the DAG half is measured at H2/P3, and');
  say('      asserting it here would be an arm that passes whatever the engine does');
  check('R-F1 a seat held on its SECOND ask carries a `done` row AND is still held',
    r.secondHoldRecord.join() === 'alpha=blocked,alpha=done,alpha=blocked',
    `${JSON.stringify(r.secondHoldRecord)} · states ${JSON.stringify(r.secondHoldStates)}`);
  check('R-F1 …and it is REPORTED as blocked-on-the-owner, never as finished',
    r.secondHoldBlockedOnOwner.join() === 'alpha' && !r.secondHoldSkippedAsFinished.includes('alpha'),
    `blockedOnOwner ${JSON.stringify(r.secondHoldBlockedOnOwner)} · skippedAsFinished ${JSON.stringify(r.secondHoldSkippedAsFinished)}`);
  check('R-F1 …and `--relaunch` RELEASES it — the documented escape, which was a NO-OP for this shape',
    r.secondHoldRelaunch.alpha !== 'live',
    `after the grant alpha=${r.secondHoldRelaunch.alpha}`);
  check('R-F2 a seat whose LAST row is another lane\'s OPEN one is not finished, and IS reported',
    r.foreignOpenRecord.join() === 'alpha=done,alpha=open'
      && r.foreignOpenStates.alpha === 'live'
      && !r.foreignOpenSkippedAsFinished.includes('alpha')
      && r.foreignOpenHeldByOtherLane.join() === 'alpha',
    `${JSON.stringify(r.foreignOpenRecord)} · alpha=${r.foreignOpenStates.alpha} · heldByOtherLane ${JSON.stringify(r.foreignOpenHeldByOtherLane)} · skippedAsFinished ${JSON.stringify(r.foreignOpenSkippedAsFinished)}`);
  check('R-F3 a turn that genuinely ended `blocked` writes a `blocked` row — the control for the pairing',
    r.turnBlockedFirstRow.join() === 'alpha=blocked', JSON.stringify(r.turnBlockedFirstRow));
  check('R-F3 …and it is NOT a spent hold: the NEXT turn\'s real ask is still held',
    r.turnBlockedRecord.join() === 'alpha=blocked,alpha=blocked',
    `${JSON.stringify(r.turnBlockedRecord)} · states ${JSON.stringify(r.turnBlockedStates)}`);

  // ── D · THE MODE SPLIT: the hold keys on a DELIVERED ask ────────────────────────────────────
  say('');
  say('D — owner ruling d-parked-ask-autonomous-workaround: autonomous means the workflow COMPLETES,');
  say('    so a PARKED ask does not hold — the seat takes its authored workaround and the wave runs on');
  check('D1 in an AUTONOMOUS goal the seat is NOT held — its record row is its real outcome, `done`',
    r.autonomousRecord.join() === 'alpha=done', JSON.stringify(r.autonomousRecord));
  check('D2 …so the wave CONTINUES: its check-out is ADMITTED — coord mirrors the same ferry gates '
    + 'at its end, and a `done` refused there would be a wave the owner cannot restart by answering '
    + '— the dependent starts, and nothing is reported as blocked-on-the-owner',
    r.autonomousCheckout.ok === true
      && r.autonomousEnqueued.join() === 'bravo' && r.autonomousStates.alpha === 'done'
      && r.autonomousBlockedOnOwner.length === 0,
    `checkout ok=${r.autonomousCheckout.ok} · enqueued ${JSON.stringify(r.autonomousEnqueued)} · alpha=${r.autonomousStates.alpha} · blockedOnOwner ${JSON.stringify(r.autonomousBlockedOnOwner)}`);
  check('D3 …and it is REPORTED as proceeded-on-its-workaround, naming the gate that parked the ask',
    r.autonomousProceeded.join() === 'alpha:true', JSON.stringify(r.autonomousProceeded));
  check('D4 …with the ask still ON THE BUS — the durable record the owner reviews on return',
    r.autonomousBusHasAsk === true, `ask row present: ${r.autonomousBusHasAsk}`);
  check('D5 the OTHER gate reaches the same verdict — an unflagged seat\'s ask parks at `human-interactive`',
    r.unflaggedRecord.join() === 'alpha=done' && r.unflaggedGate.join() === 'human-interactive'
      && r.unflaggedCheckout.ok === true && r.unflaggedEnqueued.join() === 'bravo',
    `${JSON.stringify(r.unflaggedRecord)} · gate ${JSON.stringify(r.unflaggedGate)} · checkout ok=${r.unflaggedCheckout.ok} · enqueued ${JSON.stringify(r.unflaggedEnqueued)}`);

  // THE STRUCTURAL PIN. The engine re-derives the ferry's park decision from the ferry's own
  // readers, so the one thing that can drift is the ferry's RUNG SET. This arm reads the ladder out
  // of `bus-ferry.js` and fails if it is not exactly the three rungs the engine knows about — a
  // fourth gate would mean asks park for a reason the hold cannot see, and the seat would be held
  // on a question nobody received.
  const ferrySrc = fs.readFileSync(path.join(IGNITE_SRC, 'bridges', 'chat', 'bus-ferry.js'), 'utf8');
  const ladder = (ferrySrc.match(/const gate = [\s\S]*?: null;/) || [''])[0];
  const rungs = (ladder.match(/'[a-z-]+'/g) || []).map((x) => x.replace(/'/g, ''));
  check('D6 the ferry\'s gate ladder is still exactly the three rungs the engine re-derives',
    rungs.join() === 'execution-mode,human-interactive,fallback-park',
    `rungs: ${JSON.stringify(rungs)}${rungs.length ? '' : ' — the ladder was not found at all'}`);

  // ── C · WHAT MUST NOT CHANGE ────────────────────────────────────────────────────────────────
  say('');
  say('C — the neighbouring cases, each of which must behave exactly as it did before');
  const c = r.controls;
  // BOTH HALVES, per control: the engine publishes the seat's real outcome AND coord lets it out
  // the door. Either one dropped is a class of seat the ruling never spoke about, stalled on a DAG
  // with nothing but its own `--incomplete` to clear it.
  const untouched = (name) => {
    const x = c[name];
    return x.record.join() === 'alpha=done' && x.checkedOut === true && x.enqueued.join() === 'bravo';
  };
  check('C1 a block-and-queue seat that NEVER ASKED completed normally — nothing is held',
    untouched('never-asked'), JSON.stringify(c['never-asked']));
  check('C2 `default-and-disclose` is untouched — it proceeds on its default and does not wait',
    untouched('default-and-disclose'), JSON.stringify(c['default-and-disclose']));
  check('C3 `park` is untouched — the ask is parked, the seat proceeds',
    untouched('park'), JSON.stringify(c.park));
  check('C4 a flagged seat with NO declared arm keeps its pre-ruling behaviour — a lint violation gains nothing',
    untouched('no-arm-declared'), JSON.stringify(c['no-arm-declared']));
  // ⚠ THE ANSWER HERE CARRIES `re: <ask#>`, which is the form the live transport writes and the
  // only form BOTH readers settle on. `coord.py#open_asks` settles ask #n on an `answer`/`verdict`
  // carrying `re: n` and on nothing else; `execution-record.js#openOwnerAsks` closes the OLDEST
  // open ask on any `answer` addressed to the seat, `re:` or no `re:`. So a bare `type: answer`
  // releases the engine's hold and NOT coord's check-out gate — two readers of one question that
  // disagree, which is the defect class this whole design deletes. Unreachable from the live path
  // (`bus-answer.js` always resolves and passes `--re`), so it is FILED as its own task rather than
  // pinned red here; this control asserts the agreeing form, and does not pin the divergence.
  check('C5 a seat ANSWERED ON THE BUS before it exited is NOT held — the hold is the UNANSWERED ask',
    untouched('answered-before-exit'), JSON.stringify(c['answered-before-exit']));

  // ── M · THE MUTATIONS ───────────────────────────────────────────────────────────────────────
  say('');
  say('M — the same scenario against a defanged guard: each must flip the observable ITS OWN guard');
  say('    owns. Mutant runs get no --coord: coord.py is symlinked into a mutant tree, never');
  say('    copied, so "the dependent starts" reads identically under every mutation and is the one');
  say('    outcome no engine mutation can reach (task 7.771 — the three arms that asserted it');
  say('    stood red for weeks, pinned to something unreachable by construction)');
  //
  // ⚠ EACH MUTANT REVERTS EXACTLY ONE GUARD TO WHAT STOOD BEFORE IT, so these ARE the red-first
  // proofs for the fixes — the arm below each is the one the review measured red.
  const mutants = [
    // The record row is this guard's WHOLE output, and every downstream engine reader — the seat's
    // state, `blockedOnOwner`, the attached lane's exit — takes it from there. H3/H5 assert it
    // `blocked`; the mutant must produce `done` and a silent wave.
    ['outcome', 'the close publishes `done` instead of `blocked`',
      'if (verdict && verdict.held) return { outcome: BLOCKED, held: verdict.held, parked: null };',
      'if (verdict && verdict.held) return { outcome: status, held: verdict.held, parked: null };',
      (o) => o.recordAfterAsk.join() === 'alpha=done' && o.blockedOnOwner.length === 0
        && o.statesWhileHeld.alpha === 'done',
      (o) => `record ${JSON.stringify(o.recordAfterAsk)} · alpha=${o.statesWhileHeld.alpha} · blockedOnOwner ${JSON.stringify(o.blockedOnOwner)}`],
    // `seatState`'s reader of that row. The record still says `blocked`; the mutant makes the
    // engine read the seat as FINISHED anyway — the disagreement H4 exists to prevent.
    ['predicate', 'seatState stops honouring the record\'s last word',
      'const isDone = (seat) => !(notFinished && notFinished.has(seat))\n    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));',
      'const isDone = (seat) => ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));',
      (o) => o.recordAfterAsk.join() === 'alpha=blocked' && o.statesWhileHeld.alpha === 'done',
      (o) => `record ${JSON.stringify(o.recordAfterAsk)} · alpha=${o.statesWhileHeld.alpha} — read as finished off a row that says blocked`],
    // the loop re-fire (owner ruling 2026-08-12) — a mutant that restores the retired
    // finished-guard must be CAUGHT: a granted `done` seat would stay done and the FAIL loop
    // could never re-dispatch the builder on its slot (`concepts/loop.md`).
    ['grant', 'the relaunch grant refuses a FINISHED seat (pre-loop-re-fire behavior)',
      'finished.delete(seat);',
      'if (finished.has(seat)) continue;',
      (o) => o.doneRelaunchWith.alpha === 'done',
      (o) => `after the grant alpha=${o.doneRelaunchWith.alpha} (the loop re-fire is a NO-OP)`],
    // review F2 — the foreign deletion doing the same, hiding a crashed foreign revival
    ['foreign', 'the foreign deletion outranks a LATER open row (review F2)',
      'for (const seat of finished) foreign.delete(seat);',
      'for (const seat of done) foreign.delete(seat);',
      (o) => o.foreignOpenHeldByOtherLane.length === 0,
      (o) => `heldByOtherLane ${JSON.stringify(o.foreignOpenHeldByOtherLane)} · skippedAsFinished ${JSON.stringify(o.foreignOpenSkippedAsFinished)}`],
    // review F2's other half — the report itself claiming the seat is finished
    ['skipped', 'skippedAsFinished reads ANY `done` row (review F2)',
      'seats.filter((s) => view.finished.has(s))',
      'seats.filter((s) => view.done.has(s))',
      (o) => o.foreignOpenSkippedAsFinished.includes('alpha'),
      (o) => `skippedAsFinished ${JSON.stringify(o.foreignOpenSkippedAsFinished)} while states says alpha=${o.foreignOpenStates.alpha}`],
    // the DELIVERY check — remove it and an autonomous goal is wrongly held on an ask nobody got
    ['delivery', 'the hold stops keying on a DELIVERED ask (d-parked-ask-autonomous-workaround)',
      'const gate = askParkedAtGate(goalFolder, seat);',
      'const gate = null;',
      (o) => o.autonomousRecord.join() === 'alpha=blocked' && o.autonomousBlockedOnOwner.join() === 'alpha',
      (o) => `autonomous goal: record ${JSON.stringify(o.autonomousRecord)} · blockedOnOwner ${JSON.stringify(o.autonomousBlockedOnOwner)} — held on a question nobody received`],
    // review F3 — counting a genuinely blocked turn as a spent hold
    ['spent', 'every `blocked` row counts as a spent hold (review F3)',
      " && doneTurns.has(r['session-id'])",
      '',
      (o) => o.turnBlockedRecord.join() === 'alpha=blocked,alpha=done',
      (o) => `record ${JSON.stringify(o.turnBlockedRecord)} — the real ask published `
        + 'done because an unrelated blocked turn was counted as the hold already paid'],
  ];
  for (const [tag, what, from, to, isRed, detail] of mutants) {
    const m = mutantRoot(tag, from, to);
    if (!check(`M-${tag} the mutation APPLIED (a mutation that did not land proves nothing)`, m.applied, m.where)) continue;
    let out = null;
    let err = null;
    try { out = runScenario(m.root, `run-${tag}`); } catch (e) { err = e.message; }
    check(`M-${tag} RED under the mutant — ${what}`,
      Boolean(out) && isRed(out), err || (out ? detail(out) : 'scenario threw'));
  }

  // ── A · BOTH LANES: the attached lane's own seams ───────────────────────────────────────────
  say('');
  say('A — the ATTACHED lane honours the same hold: one implementation, two attachments');
  const attached = require('../attached-execution');
  const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
  const aTmp = path.join(tmp, 'attached');
  const dataRoot = path.join(aTmp, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });
  const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
  cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
  cfg.default_workdir_root = path.join(aTmp, 'work');
  fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
  cfg.profiles['probe-hold'] = {
    exec: { argv: ['true'], prompt: 'stdin' },
    headed: { tui: { argv: ['true'] } },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: '.rbtv/goals',
    caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
  };
  const aConfig = path.join(aTmp, 'spawn-profiles.yaml');
  fs.writeFileSync(aConfig, yaml.dump(cfg));

  const goalFolder = path.join(aTmp, 'workspace', '.rbtv', 'goals', 'attached-hold');
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(goalFolder, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-a,alpha,\ntf-a,bravo,alpha\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
    '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nalpha\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\n---\n\nbravo\n');
  fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');

  // alpha is human-interactive in an interactive goal, so the attached lane CARRIES it in the
  // terminal. The injected carriage IS the session: it writes the ask onto the bus and exits 0.
  return attached.executeAttached({
    goalFolder,
    profile: 'probe-hold',
    spawnConfigPath: aConfig,
    tickIntervalMs: 200,
    maxTicks: 2,
    spawnForeground: () => {
      fs.appendFileSync(path.join(goalFolder, 'coordination', 'messages.md'),
        '## 1 | from: alpha | to: owner | type: ask | 2026-08-10 12:00\nwhich way?\n\n');
      return { status: 0 };
    },
  }).then((res) => {
    const rows = require('../execution-record').readExecutionRecord(goalFolder).rows;
    check('A1 the FOREGROUND carriage publishes `blocked` too — the arm is the seat\'s, not the lane\'s',
      rows.map((x) => `${x.seat}=${x.outcome || 'open'}`).join() === 'alpha=blocked',
      JSON.stringify(rows.map((x) => `${x.seat}=${x.outcome || 'open'}/${x.lane}`)));
    const st = attached.statusAttached({ goalFolder });
    check('A2 `--status` reports the hold — alpha not done, bravo waiting, and WHY it is waiting',
      !st.done.includes('alpha') && st.waiting.includes('bravo') && st.blockedOnOwner.join() === 'alpha',
      JSON.stringify({ done: st.done, waiting: st.waiting, blockedOnOwner: st.blockedOnOwner }));
    check('A3 the attached loop RETURNS `blocked` rather than calling the run complete or the seat failed',
      res && res.outcome === 'blocked' && (res.unfinished || []).includes('bravo'),
      JSON.stringify({ outcome: res && res.outcome, unfinished: res && res.unfinished }));
  });
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
    // ⚠ THE FIXTURE IS DELETED ON EVERY PATH, and this probe is the most expensive leaker in the
    // repo when it is not: `mutantRoot()` makes FIVE full copies of `engine/` plus the scenario's
    // stores, ~8 MiB a run, and nothing ever removed them. MEASURED 2026-08-12 on the VPS: 151
    // orphaned `/tmp/probe-bq-hold-*` trees holding 869 MiB — the largest reclaimable block on a
    // quota-mounted tmpfs `/tmp`, and therefore the reason `probe-migration`, `probe-chain-resume`
    // and `probe-argv-template` were all red for want of room that day. A probe that reddens its
    // neighbours by running is worse than one that is merely slow. Same defect and same fix as
    // `0030c855` on probe-migration; it is placed AFTER the capture write and BEFORE `exit`,
    // because `process.exit` runs no `finally`.
    fs.rmSync(tmp, { recursive: true, force: true });
    process.exit(failures.length ? 1 : 0);
  });

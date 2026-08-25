'use strict';

// -- SELFTESTS FOR THE PROGRESS-SIGNAL COLLECTORS -----------------------------------------------
//
// The load-bearing assertion is the pair, per kind: every signal in the spec's "advances" column
// MOVES `last_progress_at`, and every signal in its "does not" column LEAVES IT WHERE IT WAS. The
// second half is the one that catches the defect this seat exists for - a busy-looking frozen seat
// survives precisely because something in the "does not" column was counted as progress.
//
// The stamps are injected (`at`), never slept for: a test that proves an advance by sleeping proves
// only that time passes.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const registry = require('./registry');
const progress = require('./progress');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-progress-'));
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.message ? err.message : err}\n`);
}
function check(name, fn) {
  try { fn(); pass(name); } catch (err) { fail(name, err); }
}
function assert(cond, message) {
  if (!cond) throw new Error(message || 'assertion failed');
}

const SPAWN_STAMP = '2026-08-24T10:00:00.000Z';
const SIGNAL_STAMP = '2026-08-24T10:20:00.000Z';

// One registry file per case, so a case can never read another's row.
function freshRegistry(label, { seat = 'worker', goal = 'g' } = {}) {
  const file = path.join(tmpRoot, `${label}.jsonl`);
  fs.rmSync(file, { force: true });
  registry.recordSpawn({ goal, seat, pid: process.pid, last_progress_at: SPAWN_STAMP }, file);
  return file;
}

// The spec table, restated INDEPENDENTLY here rather than imported from the module under test: a
// test whose expectations are read out of the code it is testing passes any table.
const EXPECTED = [
  {
    kind: 'file-writing',
    advances: ['file-write', 'progress-note', 'journal-append', 'tool-call-product'],
    doesNot: ['token-growth', 'transcript-growth'],
  },
  {
    kind: 'chat-only',
    advances: ['message-sent'],
    doesNot: ['draft-unsent', 'mail-inbound'],
  },
  {
    kind: 'planning',
    advances: ['stage-artifact', 'progress-note', 'subagent-product-file'],
    doesNot: ['subagent-transcript'],
  },
  {
    kind: 'judge',
    advances: ['verdict-write', 'progress-note'],
    doesNot: ['input-reread'],
  },
];

for (const row of EXPECTED) {
  check(`${row.kind}: every listed signal advances last_progress_at`, () => {
    for (const signal of row.advances) {
      const file = freshRegistry(`${row.kind}-${signal}`);
      const before = registry.lastProgressAt({ goal: 'g', seat: 'worker' }, file);
      assert(before === SPAWN_STAMP, `spawn stamp expected, got ${before}`);
      const result = progress.recordSignal(
        { goal: 'g', seat: 'worker', kind: row.kind, signal, at: SIGNAL_STAMP }, { registryFile: file },
      );
      assert(result.advanced === true, `${signal} did not advance: ${result.reason}`);
      const after = registry.lastProgressAt({ goal: 'g', seat: 'worker' }, file);
      assert(after === SIGNAL_STAMP, `${signal}: fact reads ${after}`);
    }
  });

  check(`${row.kind}: every "does not" signal leaves the fact untouched`, () => {
    for (const signal of row.doesNot) {
      const file = freshRegistry(`${row.kind}-no-${signal}`);
      const result = progress.recordSignal(
        { goal: 'g', seat: 'worker', kind: row.kind, signal, at: SIGNAL_STAMP }, { registryFile: file },
      );
      assert(result.advanced === false, `${signal} advanced the fact and must not`);
      assert(result.reason === 'not-a-progress-signal', `unexpected reason ${result.reason}`);
      const after = registry.lastProgressAt({ goal: 'g', seat: 'worker' }, file);
      assert(after === SPAWN_STAMP, `${signal}: fact moved to ${after}`);
    }
  });

  check(`${row.kind}: a signal from ANOTHER kind's column does not leak in`, () => {
    const foreign = EXPECTED
      .filter((other) => other.kind !== row.kind)
      .flatMap((other) => other.advances)
      .filter((signal) => !row.advances.includes(signal));
    for (const signal of foreign) {
      const file = freshRegistry(`${row.kind}-foreign-${signal}`);
      const result = progress.recordSignal(
        { goal: 'g', seat: 'worker', kind: row.kind, signal, at: SIGNAL_STAMP }, { registryFile: file },
      );
      assert(result.advanced === false, `${row.kind} advanced on ${signal}, which is not in its column`);
    }
  });
}

check('an unnamed kind is file-writing, and an unknown kind falls back to it too', () => {
  for (const kind of [undefined, '', 'some-kind-this-build-never-heard-of']) {
    assert(progress.resolveKind(kind) === 'file-writing', `resolveKind(${kind})`);
    const file = freshRegistry(`fallback-${String(kind)}`);
    const result = progress.recordSignal(
      { goal: 'g', seat: 'worker', kind, signal: 'file-write', at: SIGNAL_STAMP }, { registryFile: file },
    );
    assert(result.advanced === true, 'a file write must count for an unnamed kind');
    assert(result.kind === 'file-writing', `resolved to ${result.kind}`);
  }
});

check('orchestrator is the planning kind under another name, not a fifth kind', () => {
  assert(progress.resolveKind('orchestrator') === 'planning', 'orchestrator alias');
  assert(progress.resolveKind('planning/orchestrator') === 'planning', 'planning/orchestrator alias');
});

check('an unknown signal never advances, for any kind', () => {
  for (const row of EXPECTED) {
    const file = freshRegistry(`unknown-${row.kind}`);
    const result = progress.recordSignal(
      { goal: 'g', seat: 'worker', kind: row.kind, signal: 'something-nobody-enumerated', at: SIGNAL_STAMP },
      { registryFile: file },
    );
    assert(result.advanced === false, `${row.kind} advanced on an unknown signal`);
  }
});

check('a sitting with no registry row is unsupervised, not idle and not an error', () => {
  const file = path.join(tmpRoot, 'no-row.jsonl');
  fs.rmSync(file, { force: true });
  const result = progress.recordSignal(
    { goal: 'g', seat: 'ghost', kind: 'file-writing', signal: 'file-write', at: SIGNAL_STAMP },
    { registryFile: file },
  );
  assert(result.advanced === false, 'nothing to advance');
  assert(result.reason === 'no-registry-row', `reason was ${result.reason}`);
  assert(progress.progressOf({ goal: 'g', seat: 'ghost' }, { registryFile: file }) === null, 'no fact');
});

check('the module table matches the spec table exactly - no kind, no signal, more or fewer', () => {
  const kinds = Object.keys(progress.SIGNAL_TABLE).sort();
  assert(JSON.stringify(kinds) === JSON.stringify(EXPECTED.map((r) => r.kind).sort()),
    `kinds are ${kinds.join(',')}`);
  for (const row of EXPECTED) {
    const actual = progress.signalsFor(row.kind);
    assert(JSON.stringify([...actual.advances].sort()) === JSON.stringify([...row.advances].sort()),
      `${row.kind} advances column is ${actual.advances.join(',')}`);
    assert(JSON.stringify([...actual.refuses].sort()) === JSON.stringify([...row.doesNot].sort()),
      `${row.kind} does-not column is ${actual.refuses.join(',')}`);
  }
});

fs.rmSync(tmpRoot, { recursive: true, force: true });
process.stdout.write(failed ? `\n${failed} FAILED\n` : '\nALL PASS\n');
process.exit(failed ? 1 : 0);

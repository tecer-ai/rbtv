'use strict';

// -- SELFTESTS FOR THE OPERATIONAL CHECKPOINT CONTRACT ------------------------------------------
//
// Four subjects, one per artefact of spec-recovery section 6:
//   the progress note   - three fields required, and a write ADVANCES the progress fact
//   the journal line    - the exact tab-separated shape, appended BEFORE the act
//   the relaunch prompt - brief + note + the instruction VERBATIM
//   the skip            - a journalled idempotency key means the act is not repeated
//
// The verbatim assertion compares against the spec sentence typed out here, not against the
// module's own constant: a test that reads its expectation out of the code under test would pass
// any paraphrase, and a paraphrase is exactly how "and in the journal" gets dropped.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const checkpoint = require('./checkpoint');
const registry = require('./registry');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-checkpoint-'));
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

const SPEC_INSTRUCTION = 'check what already exists at your outputs and in the journal; continue from there; do not repeat listed side effects.';
const SPAWN_STAMP = '2026-08-24T10:00:00.000Z';
const STEP_STAMP = '2026-08-24T10:30:00.000Z';
const NOTE = { 'done-so-far': 'read the spec', 'next-step': 'write the loader', 'open-questions': 'none' };

function seatFixture(label, { kind } = {}) {
  const seatDir = path.join(tmpRoot, label);
  const registryFile = path.join(tmpRoot, `${label}.jsonl`);
  fs.rmSync(registryFile, { force: true });
  registry.recordSpawn({ goal: 'g', seat: label, pid: process.pid, last_progress_at: SPAWN_STAMP }, registryFile);
  return { seatDir, registryFile, ident: { goal: 'g', seat: label, kind } };
}

check('a note with all three fields is written, and it advances last_progress_at', () => {
  const f = seatFixture('note-full');
  const result = checkpoint.writeProgressNote(f.seatDir, NOTE, { ...f.ident, at: STEP_STAMP, registryFile: f.registryFile });
  const text = fs.readFileSync(result.path, 'utf8');
  for (const field of ['done-so-far', 'next-step', 'open-questions']) {
    assert(text.includes(`## ${field}`), `the note is missing ${field}`);
  }
  assert(result.progress.advanced === true, `the write did not advance: ${result.progress.reason}`);
  assert(registry.lastProgressAt({ goal: 'g', seat: 'note-full' }, f.registryFile) === STEP_STAMP, 'the fact did not move');
});

check('a note missing ANY of the three fields is refused, and nothing is written', () => {
  for (const field of ['done-so-far', 'next-step', 'open-questions']) {
    const f = seatFixture(`note-missing-${field}`);
    const partial = { ...NOTE };
    delete partial[field];
    let threw = null;
    try {
      checkpoint.writeProgressNote(f.seatDir, partial, { ...f.ident, registryFile: f.registryFile });
    } catch (err) { threw = err; }
    assert(threw && threw.message.includes(field), `omitting ${field} was accepted`);
    assert(checkpoint.readProgressNote(f.seatDir) === null, `a partial note was written for ${field}`);
    assert(registry.lastProgressAt({ goal: 'g', seat: `note-missing-${field}` }, f.registryFile) === SPAWN_STAMP,
      'a refused write still advanced the fact');
  }
});

// Section 6 says a note write advances the fact "for every kind that LISTS progress-note in
// section 1" - and chat-only does not list it. Its one advancing signal is a message actually
// sent. Asserting the exclusion here is deliberate: the tempting reading ("a note is progress, so
// it counts everywhere") would hand a chat-only seat a way to look busy without sending anything.
check('a note write advances the fact for the three kinds that list progress-note, and not chat-only', () => {
  for (const kind of ['file-writing', 'planning', 'judge']) {
    const f = seatFixture(`note-kind-${kind}`, { kind });
    const result = checkpoint.writeProgressNote(f.seatDir, NOTE, { ...f.ident, at: STEP_STAMP, registryFile: f.registryFile });
    assert(result.progress.advanced === true, `${kind}: ${result.progress.reason}`);
  }
  const chat = seatFixture('note-kind-chat-only', { kind: 'chat-only' });
  const result = checkpoint.writeProgressNote(chat.seatDir, NOTE, { ...chat.ident, at: STEP_STAMP, registryFile: chat.registryFile });
  assert(result.progress.advanced === false, 'a chat-only note write must not advance the fact');
  assert(checkpoint.readProgressNote(chat.seatDir) !== null, 'the note itself is still written');
  assert(registry.lastProgressAt({ goal: 'g', seat: 'note-kind-chat-only' }, chat.registryFile) === SPAWN_STAMP,
    'the chat-only fact moved on a note write');
});

check('the journal line is ISO-8601 TAB kind TAB target TAB idempotency-key', () => {
  const f = seatFixture('journal-shape');
  const entry = { kind: 'slack-post', target: 'C123/thread-9', idempotencyKey: 'ask-9-open', at: STEP_STAMP };
  const result = checkpoint.appendJournal(f.seatDir, entry, { ...f.ident, registryFile: f.registryFile });
  const raw = fs.readFileSync(result.path, 'utf8');
  assert(raw.endsWith('\n'), 'the line is not newline-terminated');
  const line = raw.trim();
  const cols = line.split('\t');
  assert(cols.length === 4, `the line has ${cols.length} tab-separated columns`);
  assert(cols[0] === STEP_STAMP, `column 1 is ${cols[0]}`);
  assert(new Date(cols[0]).toISOString() === cols[0], 'column 1 is not ISO-8601');
  assert(cols[1] === entry.kind && cols[2] === entry.target && cols[3] === entry.idempotencyKey,
    `columns read ${cols.slice(1).join(' | ')}`);
  assert(result.progress.advanced === true, `the append did not advance: ${result.progress.reason}`);
  assert(registry.lastProgressAt({ goal: 'g', seat: 'journal-shape' }, f.registryFile) === STEP_STAMP, 'the fact did not move');
});

check('a field carrying a tab or a newline is refused, not escaped', () => {
  const f = seatFixture('journal-tabs');
  for (const bad of ['a\tb', 'a\nb']) {
    let threw = null;
    try {
      checkpoint.appendJournal(f.seatDir, { kind: 'slack-post', target: bad, idempotencyKey: 'k' }, {});
    } catch (err) { threw = err; }
    assert(threw, `${JSON.stringify(bad)} was accepted into a tab-separated line`);
  }
});

check('a journalled idempotency-key makes the relaunch SKIP that act', () => {
  const f = seatFixture('journal-skip');
  checkpoint.appendJournal(f.seatDir, { kind: 'slack-post', target: 'C123', idempotencyKey: 'post-once', at: STEP_STAMP },
    { ...f.ident, registryFile: f.registryFile });
  assert(checkpoint.isJournaled(f.seatDir, 'post-once') === true, 'a journalled key must be skipped');
  assert(checkpoint.isJournaled(f.seatDir, 'never-posted') === false, 'an unjournalled key must not be skipped');
  // The crash-between-line-and-act case: the line is on disk, the act never happened, and the
  // relaunch still skips - that IS the ruling.
  const acts = [{ key: 'post-once' }, { key: 'never-posted' }];
  const performed = acts.filter((a) => !checkpoint.isJournaled(f.seatDir, a.key)).map((a) => a.key);
  assert(JSON.stringify(performed) === JSON.stringify(['never-posted']), `performed ${performed.join(',')}`);
});

check('a torn final journal line does not hide the keys that landed', () => {
  const f = seatFixture('journal-torn');
  checkpoint.appendJournal(f.seatDir, { kind: 'k', target: 't', idempotencyKey: 'landed', at: STEP_STAMP }, {});
  fs.appendFileSync(checkpoint.journalPath(f.seatDir), '2026-08-24T10:31:00.000Z\tk\tt', 'utf8');
  assert(checkpoint.isJournaled(f.seatDir, 'landed') === true, 'the landed key was lost');
  assert(checkpoint.journalEntries(f.seatDir).length === 1, 'the torn line was read as an entry');
});

check('the relaunch prompt is brief + current note + the instruction, verbatim', () => {
  const f = seatFixture('relaunch');
  checkpoint.writeProgressNote(f.seatDir, NOTE, { ...f.ident, at: STEP_STAMP, registryFile: f.registryFile });
  const brief = 'ORIGINAL BRIEF: build the recovery loader.';
  const prompt = checkpoint.relaunchPrompt({ brief, seatDir: f.seatDir });
  assert(prompt.includes(brief), 'the original brief is missing');
  for (const field of Object.keys(NOTE)) {
    assert(prompt.includes(NOTE[field]), `the note field ${field} is missing from the prompt`);
  }
  assert(prompt.includes(SPEC_INSTRUCTION), 'the continue-instruction is not verbatim');
  assert(prompt.indexOf(brief) < prompt.indexOf(NOTE['done-so-far']), 'the brief must come first');
  assert(prompt.indexOf(SPEC_INSTRUCTION) > prompt.indexOf(NOTE['done-so-far']), 'the instruction must come last');
  assert(checkpoint.CONTINUE_INSTRUCTION === SPEC_INSTRUCTION, 'the module constant drifted from the spec sentence');
});

check('a relaunch with no note on disk still composes, and says so', () => {
  const f = seatFixture('relaunch-nonote');
  const prompt = checkpoint.relaunchPrompt({ brief: 'BRIEF', seatDir: f.seatDir });
  assert(prompt.includes('BRIEF') && prompt.includes(SPEC_INSTRUCTION), 'brief + instruction');
  assert(prompt.includes('none on disk'), 'the absence of a note must be stated, not implied');
});

fs.rmSync(tmpRoot, { recursive: true, force: true });
process.stdout.write(failed ? `\n${failed} FAILED\n` : '\nALL PASS\n');
process.exit(failed ? 1 : 0);

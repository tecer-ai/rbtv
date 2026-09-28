'use strict';

// -- THE CHECKPOINT CONTRACT, OPERATIONAL - disk is the checkpoint [D4, T1-R2, T1-R11, T4-R2] ---
//
// NO checkpoint API, NO transcript replay, NO harness-native resume. Crash-only stands: a killed
// seat is relaunched and reads what is already on disk. Three artefacts and nothing else:
//
//   1. the PROGRESS NOTE  - one file per seat folder, three fields, all three on every write. A
//                           write advances `last_progress_at` for every kind whose signal list
//                           carries `progress-note` (spec section 1: file-writing, planning and
//                           judge - NOT chat-only, whose only signal is a message actually sent).
//   2. the SIDE-EFFECT JOURNAL - one line appended BEFORE any external side effect. A crash
//                           between the line and the act is the case this exists for: the relaunch
//                           sees the line and SKIPS the act, matching on the idempotency key.
//                           An append advances `last_progress_at` for file-writing seats.
//   3. the RELAUNCH PROMPT - original brief + current note + one verbatim continue-instruction.
//
// WHY ALL THREE FIELDS ON EVERY WRITE. A note that carries `done-so-far` but drops `next-step`
// leaves the relaunched seat re-deciding what it had already decided, which is precisely the work
// a kill is supposed to cost at most one step of. The writer refuses a partial note rather than
// writing a note that will read as complete.
//
// ACCEPTED LOSS [T1-R2]: a kill loses the in-flight step, and progress inside one large mid-write
// artefact. Ruled and accepted; this contract does not try to make a mid-write atomic.

const fs = require('node:fs');
const path = require('node:path');
const progress = require('./progress');

const PROGRESS_NOTE_FILENAME = 'progress-note.md';
const JOURNAL_FILENAME = 'side-effect-journal.tsv';

// The three fields, spelled the way spec-recovery section 6 spells them. The headings ARE the
// contract: a relaunched seat greps for these words.
const NOTE_FIELDS = Object.freeze(['done-so-far', 'next-step', 'open-questions']);

// VERBATIM from spec-recovery section 6. Do not reword: the relaunch composer's test asserts on
// this exact string, because a paraphrase ("check your outputs first") drops the journal half and
// re-runs side effects that were already performed.
const CONTINUE_INSTRUCTION = 'check what already exists at your outputs and in the journal; continue from there; do not repeat listed side effects.';

function notePath(seatDir) {
  return path.join(seatDir, PROGRESS_NOTE_FILENAME);
}

function journalPath(seatDir) {
  return path.join(seatDir, JOURNAL_FILENAME);
}

// -- THE PROGRESS NOTE ---------------------------------------------------------------------------
//
// Whole-file rewrite through a temp file + rename: the note is the CURRENT state, not a log, so an
// append-only note would hand the relaunched seat several contradictory "next-step"s and no way to
// tell which one is live.
function writeProgressNote(seatDir, fields = {}, { goal, seat, kind, at, registryFile } = {}) {
  const missing = NOTE_FIELDS.filter((f) => {
    const value = fields[f];
    return value === undefined || value === null || String(value).trim() === '';
  });
  if (missing.length) {
    throw new Error(`progress note requires all three fields, missing: ${missing.join(', ')}`);
  }
  fs.mkdirSync(seatDir, { recursive: true });
  const body = NOTE_FIELDS.map((f) => `## ${f}\n\n${String(fields[f]).trim()}\n`).join('\n');
  const file = notePath(seatDir);
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, body, 'utf8');
  fs.renameSync(tmp, file);
  // The write IS a progress signal (section 1). Advancing here rather than at each call site is
  // what makes the fact impossible to forget: there is one writer of the note, so there is one
  // place the stamp can be missed.
  const advance = seat
    ? progress.recordSignal({ goal, seat, kind, signal: 'progress-note', at }, { registryFile })
    : null;
  return { path: file, fields: { ...fields }, progress: advance };
}

function readProgressNote(seatDir) {
  try {
    return fs.readFileSync(notePath(seatDir), 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return null;   // no note yet is a legal first sitting
    throw err;
  }
}

// -- THE SIDE-EFFECT JOURNAL ----------------------------------------------------------------------
//
// `ISO-8601<TAB>kind<TAB>target<TAB>idempotency-key`, one line, appended BEFORE the act. Tabs are
// the separator, so no field may contain one: a target with a tab in it would split into two
// columns and the relaunch would match the wrong key. Refused at the writer rather than escaped -
// an escaping scheme is a second format nobody would remember to decode.
function journalLine({ kind, target, idempotencyKey, at }) {
  if (!kind || !target || !idempotencyKey) {
    throw new Error('journal line requires kind, target and idempotency-key');
  }
  const fields = [kind, target, idempotencyKey].map(String);
  if (fields.some((f) => f.includes('\t') || f.includes('\n'))) {
    throw new Error('journal fields may not contain a tab or a newline');
  }
  const stamp = at ? new Date(at).toISOString() : new Date().toISOString();
  return [stamp, ...fields].join('\t');
}

function appendJournal(seatDir, entry, { goal, seat, kind: seatKind, registryFile } = {}) {
  fs.mkdirSync(seatDir, { recursive: true });
  const line = journalLine(entry);
  fs.appendFileSync(journalPath(seatDir), `${line}\n`, 'utf8');
  const advance = seat
    ? progress.recordSignal(
      { goal, seat, kind: seatKind, signal: 'journal-append', at: entry.at },
      { registryFile },
    )
    : null;
  return { path: journalPath(seatDir), line, progress: advance };
}

function journalEntries(seatDir) {
  let text;
  try {
    text = fs.readFileSync(journalPath(seatDir), 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  const rows = [];
  for (const raw of text.split('\n')) {
    if (!raw.trim()) continue;
    const [at, kind, target, idempotencyKey] = raw.split('\t');
    // A torn final line (the crash this file is about can happen mid-append) is skipped rather
    // than thrown on: the whole journal must stay readable for the keys that DID land.
    if (!at || !kind || !target || !idempotencyKey) continue;
    rows.push({ at, kind, target, idempotency_key: idempotencyKey });
  }
  return rows;
}

// The relaunch's one question: has this act already been journalled? A hit means SKIP - the act
// either happened or was interrupted so close to happening that repeating it is the greater risk
// (that is the ruling: journal BEFORE the effect, skip on relaunch).
function isJournaled(seatDir, idempotencyKey) {
  if (!idempotencyKey) return false;
  return journalEntries(seatDir).some((row) => row.idempotency_key === String(idempotencyKey));
}

// -- THE RELAUNCH PROMPT ---------------------------------------------------------------------------
//
// brief + note + the verbatim instruction, in that order and with nothing else. It is NOT a summary
// of the transcript and NOT a harness resume token: the whole point of crash-only is that the
// relaunched seat reads DISK.
function relaunchPrompt({ brief, seatDir, note } = {}) {
  if (!brief || !String(brief).trim()) throw new Error('relaunch prompt requires the original brief');
  const current = note === undefined ? readProgressNote(seatDir) : note;
  const parts = [String(brief).trim()];
  parts.push(current && String(current).trim()
    ? `## progress note\n\n${String(current).trim()}`
    // Said explicitly rather than omitted: a relaunch with no note is a seat killed before its
    // first meaningful step, and the seat must know that instead of inferring it from silence.
    : '## progress note\n\nnone on disk - this sitting produced no progress note.');
  parts.push(CONTINUE_INSTRUCTION);
  return parts.join('\n\n');
}

module.exports = {
  PROGRESS_NOTE_FILENAME,
  JOURNAL_FILENAME,
  NOTE_FIELDS,
  CONTINUE_INSTRUCTION,
  notePath,
  journalPath,
  writeProgressNote,
  readProgressNote,
  journalLine,
  appendJournal,
  journalEntries,
  isJournaled,
  relaunchPrompt,
};

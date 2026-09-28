'use strict';

// -- THE PROGRESS-SIGNAL COLLECTORS - the only writers of `last_progress_at` [T4-R1, CF-2] -------
//
// WHAT WAS BROKEN. Liveness of WORK was inferred from two things that are not work: the admission
// fingerprint (which changed whenever a timestamp or a session id inside it changed) and transcript
// growth (which a frozen seat produces by re-reading its own inputs). A seat could look busy while
// producing nothing, and a seat producing files could be judged idle. Both directions were wrong,
// and they were wrong because nobody was measuring WORK PRODUCT.
//
// THE CURE. ONE fact per seat - `last_progress_at` on the supervisor registry row - and a closed
// table of what may advance it. This file IS that table (spec-recovery section 1). The 30-minute
// no-progress kill and the frozen alarm read the fact and nothing else.
//
// THE "DOES NOT" COLUMN IS BINDING, not decoration. Raw token growth, an unsent draft, inbound
// mail, a sub-agent's transcript activity and a judge re-reading its inputs are each named in the
// spec as NOT progress, and each of them is something a stuck seat emits abundantly. The table
// below carries them explicitly rather than letting them fall through an "unknown" arm, so a
// reader can see the refusal and a selftest can assert it.
//
// ACCEPTED RISK, on the record [CF-1, T4 Reversals]: a seat that keeps emitting listed signals -
// endless rewrites, sub-agent spawning, token burn behind real files - is UNKILLABLE by the
// 30-minute clock. Planning waves that emit product files stay "busy" forever [T3-R13]. This was
// ruled and is not a defect to be fixed here.

const registry = require('./registry');

// The spec's kind column. An unnamed kind is FILE-WRITING (spec section 1, last line) - the
// default is the widest signal set, because misclassifying a file-writing seat as chat-only would
// make its file writes invisible and kill a working seat.
const DEFAULT_KIND = 'file-writing';

// Both columns of the spec table, verbatim in structure: `advances` is the closed allow-list,
// `refuses` the named "does not" entries. A signal in neither list is unknown, and unknown does
// not advance - a progress fact must never be advanced by something nobody enumerated.
const SIGNAL_TABLE = Object.freeze({
  'file-writing': Object.freeze({
    advances: Object.freeze([
      'file-write',        // new or changed files in the seat write area
      'progress-note',     // a progress-note update (section 6)
      'journal-append',    // a side-effect journal append (section 6)
      'tool-call-product', // a tool call that produces one of the three above
    ]),
    refuses: Object.freeze(['token-growth', 'transcript-growth']),
  }),
  'chat-only': Object.freeze({
    advances: Object.freeze([
      'message-sent',      // a message the seat ACTUALLY sent
    ]),
    refuses: Object.freeze(['draft-unsent', 'mail-inbound']),
  }),
  'planning': Object.freeze({
    advances: Object.freeze([
      'stage-artifact',        // a stage artifact write
      'progress-note',
      'subagent-product-file', // a sub-agent PRODUCT FILE landing, never its chatter
    ]),
    refuses: Object.freeze(['subagent-transcript']),
  }),
  judge: Object.freeze({
    advances: Object.freeze([
      'verdict-write',     // verdict / findings file write
      'progress-note',
    ]),
    refuses: Object.freeze(['input-reread']),
  }),
});

// `planning/orchestrator` in the spec is ONE kind with two names in the plan vocabulary. Aliasing
// here keeps the table single-rowed: two rows would be two answers waiting to drift apart.
const KIND_ALIASES = Object.freeze({
  orchestrator: 'planning',
  'planning/orchestrator': 'planning',
});

function resolveKind(kind) {
  if (!kind) return DEFAULT_KIND;
  const named = String(kind).trim().toLowerCase();
  const aliased = KIND_ALIASES[named] || named;
  // An unrecognised kind resolves to file-writing for the same reason an absent one does: the plan
  // author naming a kind this build does not know must not silence that seat's file writes.
  return SIGNAL_TABLE[aliased] ? aliased : DEFAULT_KIND;
}

// Does this signal advance the fact, for this kind? The whole policy, in one predicate.
function advances(kind, signal) {
  const row = SIGNAL_TABLE[resolveKind(kind)];
  return row.advances.includes(String(signal || '').trim().toLowerCase());
}

function isRefused(kind, signal) {
  const row = SIGNAL_TABLE[resolveKind(kind)];
  return row.refuses.includes(String(signal || '').trim().toLowerCase());
}

function signalsFor(kind) {
  return SIGNAL_TABLE[resolveKind(kind)];
}

// -- THE COLLECTOR - one signal in, at most one registry write out ------------------------------
//
// The return value tells the caller which of the three things happened, because a caller that
// cannot tell "advanced" from "refused" from "no row" has no way to report why a seat looks idle:
//
//   advanced: true  - the fact moved, `at` is the new stamp
//   advanced: false, reason 'not-a-progress-signal' - the signal is in the does-not column (or
//                    is unknown); NOTHING was written, which is the point of the refusal
//   advanced: false, reason 'no-registry-row' - the sitting is unsupervised, so there is no
//                    supervisor-owned fact to advance. Not an error and never a death.
function recordSignal({ goal, seat, kind, signal, at }, { registryFile } = {}) {
  if (!seat) throw new Error('recordSignal requires seat');
  const resolvedKind = resolveKind(kind);
  if (!advances(resolvedKind, signal)) {
    return { advanced: false, reason: 'not-a-progress-signal', kind: resolvedKind, signal };
  }
  const stamp = at ? new Date(at).toISOString() : new Date().toISOString();
  const row = registry.recordProgress({ goal, seat }, stamp, registryFile);
  if (!row) return { advanced: false, reason: 'no-registry-row', kind: resolvedKind, signal };
  return { advanced: true, reason: 'progress-signal', kind: resolvedKind, signal, at: row.last_progress_at };
}

// The read side the kill clock and the frozen alarm use. Spelled here so both readers reach the
// fact through the progress module rather than each opening the registry with its own key spelling.
function progressOf({ goal, seat }, { registryFile } = {}) {
  return registry.lastProgressAt({ goal, seat }, registryFile);
}

module.exports = {
  DEFAULT_KIND,
  SIGNAL_TABLE,
  KIND_ALIASES,
  resolveKind,
  advances,
  isRefused,
  signalsFor,
  recordSignal,
  progressOf,
};

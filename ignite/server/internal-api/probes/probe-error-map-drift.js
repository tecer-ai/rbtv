'use strict';

// probe-error-map-drift — the STORE_TO_WIRE decay guard (owner ruling 2026-07-20,
// registry-reconciliation batch 08 item 7; task 7.18).
//
// THE FAILURE MODE THIS GUARDS: STORE_TO_WIRE (server/internal-api/dispatch.js) is a
// CLOSED literal map, and toWireError() degrades any typed store code absent from it to
// the anonymous { code: INTERNAL, message: 'server-core fault' } — so a sender cannot
// tell its own correctable mistake from a broken daemon. The map was correct when
// written and had NO mechanism to stay correct: a new typed code raised from a wire
// path would decay silently. This is the THIRD closed set in batch 08 with that shape
// (gateway intent allowlist · gate<->handler pair · this map).
//
// THE INVARIANT (the durable half of the ruling — the rows are incidental):
//
//   Every typed E_* code exported by server/{pty,spawn,heart}/errors.js is either a
//   STORE_TO_WIRE key (it crosses the wire AS ITSELF, deliberately) or a
//   NOT_WIRE_REACHABLE key (its absence is a RULED classification with a stated
//   rationale) — EXACTLY ONE. Never neither (silent decay), never both (contradiction).
//
// Adding a typed code without deciding its wire fate FAILS this probe NAMING the code.
// Reachability itself cannot be computed statically here; the NOT_WIRE_REACHABLE
// rationale strings are the reachability ruling of record, and this probe forces every
// future code through that decision point — which is exactly the drift detection the
// closed set lacked.
//
// Sibling guard: task 7.16's intent-set drift probe (probe-intent-drift.js) shares this
// shape (a closed set diffed against its universe, failures NAMED). The partition check
// was lifted into the shared lib/closed-set.js at task 7.16 — one helper, two probes,
// so the checker itself cannot become a fourth drifting closed set.
//
// Static — requires the modules as data; no daemon, no db, no ports. Exit code is the
// truth; the .out footer is a hint (D51 evidence-husk hazard: capture truncated at load).

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-error-map-drift.out');
fs.writeFileSync(outPath, '');
const lines = [];
function emit(s) { lines.push(s); }

const { STORE_TO_WIRE, NOT_WIRE_REACHABLE } = require('../dispatch');
const { WIRE_ERROR_CODES } = require('../errors');
const { checkClosedSetPartition } = require('./lib/closed-set');

// The typed-code UNIVERSE: every E_* string constant the three error modules export.
// Derived by REQUIRING the modules (never by regex over source) so a code cannot hide
// behind formatting — if it is exported, it is in scope.
const ERROR_MODULES = ['../../pty/errors', '../../spawn/errors', '../../heart/errors'];
const defined = new Set();
for (const mod of ERROR_MODULES) {
  const exp = require(mod);
  for (const [name, value] of Object.entries(exp)) {
    if (typeof value === 'string' && /^E_[A-Z0-9_]+$/.test(value)) defined.add(value);
    if (typeof value === 'string' && /^E_/.test(name) && name !== value) {
      emit(`FAIL: ${mod} exports ${name} whose value '${value}' does not match its name`);
    }
  }
}

// The partition check — every universe member in exactly one side, no stale keys —
// lives in the shared lib (see header note); this probe supplies its own failure
// wording so the findings keep naming THIS map's decay mode. On top of it: every
// mapped value a ratified wire code, every classification a real rationale (below).
const failures = checkClosedSetPartition({
  universe: defined,
  sides: [
    { name: 'STORE_TO_WIRE', keys: [...STORE_TO_WIRE.keys()] },
    { name: 'NOT_WIRE_REACHABLE', keys: [...NOT_WIRE_REACHABLE.keys()] },
  ],
  describe: {
    staleRow: (name, key) => `STALE ROW: ${name} carries '${key}', which no errors module defines`,
    unclassified: (code) =>
      `UNCLASSIFIED TYPED CODE: '${code}' is in neither STORE_TO_WIRE nor NOT_WIRE_REACHABLE — ` +
      `if it can cross toWireError() it will degrade to the anonymous INTERNAL 'server-core fault'. ` +
      `Rule its wire fate: map it, or classify it with a rationale.`,
    contradiction: (code, homes) =>
      `CONTRADICTION: '${code}' is in BOTH ${homes.join(' and ')} — a code cannot be mapped and not-wire-reachable at once`,
  },
});

for (const [code, wire] of STORE_TO_WIRE) {
  if (!WIRE_ERROR_CODES.has(wire)) {
    failures.push(`BAD WIRE CODE: STORE_TO_WIRE maps '${code}' to '${wire}', which is not in the ratified closed wire set`);
  }
}
for (const [code, rationale] of NOT_WIRE_REACHABLE) {
  if (typeof rationale !== 'string' || rationale.trim().length === 0) {
    failures.push(`EMPTY RATIONALE: NOT_WIRE_REACHABLE carries '${code}' with no stated reason — the classification IS the ruling; an empty one is a default`);
  }
}

emit(`typed-code universe (server/{pty,spawn,heart}/errors.js exports): ${defined.size}`);
emit(`STORE_TO_WIRE rows: ${STORE_TO_WIRE.size}`);
emit(`NOT_WIRE_REACHABLE classifications: ${NOT_WIRE_REACHABLE.size}`);
emit(`partition: ${STORE_TO_WIRE.size} + ${NOT_WIRE_REACHABLE.size} = ${STORE_TO_WIRE.size + NOT_WIRE_REACHABLE.size} (universe ${defined.size})`);

let exitCode = 0;
if (failures.length > 0) {
  exitCode = 1;
  emit('');
  for (const f of failures) emit(`FAIL: ${f}`);
  emit('');
  emit(`RESULT: FAIL — ${failures.length} drift finding(s) above, each naming its code.`);
} else {
  emit('');
  emit('RESULT: PASS — every typed code is either deliberately mapped or deliberately classified; the closed map cannot decay silently.');
}
emit(`WALL_MS ${Date.now() - start}`);
emit(`EXIT ${exitCode}`);
fs.writeFileSync(outPath, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);

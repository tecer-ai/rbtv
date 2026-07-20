'use strict';

// probe-intent-drift — the closed intent-set LOCKSTEP guard (owner ruling 2026-07-20,
// registry-reconciliation batch 08 item 5; task 7.16; owed since D91).
//
// THE FAILURE MODE THIS GUARDS: the closed intent set exists in THREE copies —
//   1. gateway/parse.js `INTENTS` (the front-door allowlist),
//   2. server/internal-api/dispatch.js `INTENTS` (the server-core gate),
//   3. the `switch (env.intent)` handler cases inside dispatch() itself.
// The duplication of 1 vs 2 is BY DESIGN: the gateway holds no core import (DEC-4),
// so no shared constant is possible, and every new intent must extend ALL THREE
// together — the lockstep invariant. The copies diverged once and an authenticated
// owner got `400 UNKNOWN_INTENT` before authz was ever consulted (the p6-3a incident).
//
// THE PAIR D91 NEVER CONTEMPLATED — gate<->handler drift is the dangerous one:
// gateway<->gate drift is LOUD (a legitimate command refused at the front door), but
// an intent present in the gate's INTENTS with NO `case` in the switch falls through
// with `result` left undefined. What the sender then receives is NOT a refusal that
// names the drift: at current HEAD, roundTrip(undefined) throws inside dispatch()'s
// try and the sender gets the anonymous `INTERNAL 'server-core fault'` — a registered,
// gate-approved intent indistinguishable from a broken daemon. (Were roundTrip ever
// relaxed, the same fall-through would become ok:true with an empty result — a silent
// success. The probe's fall-through detector covers BOTH shapes.)
//
// ★ CONSTRUCTION (ruled at the review sitting): the probe compares the modules'
// EXPORTED constants — NEVER regex over source text (an ad-hoc regex check at that
// sitting false-alarmed by missing `result = await handle…` spellings, and a
// false-alarming probe gets ignored). Sets 1 and 2 are required as data. Set 3 has no
// data form (the cases live inside dispatch()), so per the ruling's fallback it is
// DERIVED BEHAVIORALLY: a real internal API is built (stub store/spawn — never
// reached) and dispatch() is exercised once per gate intent with a payload whose
// unknown field every handler's strict-schema check refuses FIRST. A typed non-fall-
// through response proves a case ran; the fall-through signature proves it did not.
//
// Static in-process — no daemon, no db, no ports. Exit code is the truth; the .out
// footer is a hint (D51 evidence-husk hazard: capture truncated at load).

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-intent-drift.out');
fs.writeFileSync(outPath, '');
const lines = [];
function emit(s) { lines.push(s); }

const { INTENTS: GATEWAY_INTENTS } = require('../../../gateway/parse');
const { INTENTS: GATE_INTENTS, createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { checkClosedSetsLockstep } = require('./lib/closed-set');

async function main() {
  const failures = [];

  // ── Set 3, derived by exercising dispatch (the ruling's no-data fallback) ────
  const SECRET = 'probe-intent-drift-per-boot-secret';
  const api = createInternalApi({
    // Stubs, deliberately empty: the probe payload carries ONE unknown field, and every
    // handler's first act is the strict-schema rejection (spawn-via-named-profile throws
    // its D70 exclusion on entry) — no handler reaches the store, spawn, or pty host.
    heartStore: {},
    spawnManager: {},
    secret: SECRET,
  });

  // A gate-approved envelope that every EXISTING handler refuses typed at its first
  // check. A missing case cannot refuse it — the switch falls through instead.
  function envelopeFor(intent) {
    return {
      v: ENVELOPE_VERSION,
      id: `probe-intent-drift-${intent}`,
      ts: new Date().toISOString(),
      auth: SECRET,
      sender: { id: 'probe-intent-drift', kind: 'owner' },
      intent,
      payload: { __intent_drift_probe__: true },
    };
  }

  // Fall-through signature — BOTH shapes a caseless intent can produce (see header):
  // the current roundTrip(undefined) throw (anonymous INTERNAL 'server-core fault')
  // and the empty successful response it would become if roundTrip were relaxed.
  function isFallThrough(res) {
    if (res.ok === true && (res.result === null || res.result === undefined)) return true;
    return res.ok === false && res.error && res.error.code === 'INTERNAL' && res.error.message === 'server-core fault';
  }

  const handled = [];
  for (const intent of [...GATE_INTENTS].sort()) {
    const res = await api.dispatch(envelopeFor(intent));
    if (isFallThrough(res)) {
      emit(`derived: '${intent}' -> FALL-THROUGH (no switch case ran) — observed ${res.ok ? 'ok:true with empty result' : `error ${res.error.code} '${res.error.message}'`}`);
    } else {
      handled.push(intent);
      const seen = res.ok ? 'ok:true result' : `typed ${res.error.code}`;
      emit(`derived: '${intent}' -> handler ran (${seen})`);
    }
  }

  // ── The lockstep check — all three copies identical, every miss NAMED ────────
  failures.push(...checkClosedSetsLockstep({
    sets: [
      { name: 'gateway/parse.js INTENTS (front-door allowlist)', keys: [...GATEWAY_INTENTS] },
      { name: 'dispatch.js INTENTS (server-core gate)', keys: [...GATE_INTENTS] },
      { name: 'dispatch() switch handlers (derived by exercising dispatch)', keys: handled },
    ],
    describe: {
      missing: (setName, intent) => {
        if (setName.startsWith('dispatch() switch handlers')) {
          if (GATE_INTENTS.has(intent)) {
            return `SILENT DRIFT: '${intent}' is in the dispatch.js INTENTS gate but the switch has NO case for it — ` +
              `a gate-approved request falls through with result undefined and the sender cannot tell it from a broken daemon. ` +
              `Add the handler case (and keep all three sets in lockstep).`;
          }
          return `NO REACHABLE HANDLER: '${intent}' is not in the dispatch.js INTENTS gate, so no switch case can ever run for it — ` +
            `fix the gate-set finding above and re-run.`;
        }
        return `SET DRIFT: ${setName} is MISSING '${intent}' — the closed intent set is duplicated BY DESIGN (DEC-4: no ` +
          `gateway<->core import), so every new intent must extend ALL THREE copies together.`;
      },
    },
  }));

  emit('');
  emit(`gateway/parse.js INTENTS: ${GATEWAY_INTENTS.size}`);
  emit(`dispatch.js INTENTS (gate): ${GATE_INTENTS.size}`);
  emit(`dispatch() switch handlers (derived): ${handled.length}`);

  let exitCode = 0;
  if (failures.length > 0) {
    exitCode = 1;
    emit('');
    for (const f of failures) emit(`FAIL: ${f}`);
    emit('');
    emit(`RESULT: FAIL — ${failures.length} drift finding(s) above, each naming the set and the intent.`);
  } else {
    emit('');
    emit('RESULT: PASS — all three copies of the closed intent set are in lockstep; gate->handler fall-through is impossible at this HEAD.');
  }
  emit(`WALL_MS ${Date.now() - start}`);
  emit(`EXIT ${exitCode}`);
  fs.writeFileSync(outPath, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(exitCode);
}

main().catch((err) => {
  emit(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  emit('EXIT 1');
  fs.writeFileSync(outPath, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(1);
});

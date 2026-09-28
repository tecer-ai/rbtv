'use strict';

// probe-message-type-vocabulary — the closed message-type enum is COPIED at eight sites, and this
// probe is the only thing that makes them one object. (SEVEN until the D2 change swept the tree
// and found the goal-scaffold `threads.sql` template carrying a ninth-hand copy of its own.)
//
// ⚠ THE COUNT MOVES WITH THE VOCABULARY, NOT WITH THE SITES. W4 closed the enum at seven types;
// D2's routed types (owner ruling, 2026-08-19) widened it to EIGHT by adding `stuck`. EXPECTED
// below is still spelled out by hand and still compared EXACTLY — widening it is the deliberate,
// reviewable act that a vocabulary change is supposed to cost.
//
// ⚠ WHY THE COPIES EXIST AND WHY THEY MUST NOT BE UNIFIED. Each copy is deliberate and documented
// at its own site: the gateway holds no store import by design (DEC-4), the core re-validates
// independently of gateway origin (DEC-3), the chat bridge is a separate process, and `coord.py` is
// a different LANGUAGE on a different substrate. The store's CHECK is SQL. So the vocabulary cannot
// live in one place — which leaves exactly one honest guard: read all of them and compare.
//
// ⚠ THE FAILURE THIS CATCHES IS SILENT AT EVERY SITE. A type added at seven of eight is not a
// syntax error anywhere: the sender writes the row into its append-only log, the seventh door refuses it,
// the sender exits non-zero, and the row is permanent. That is the D3 silent class the W4 package
// exists to close, rebuilt by the change that closed it.
//
// ⚠ NON-VACUITY IS ASSERTED, NOT ASSUMED. Every site must yield a NON-EMPTY set, and each must
// match the expected vocabulary EXACTLY. A regex that stops matching (a reformat, a rename, a moved
// file) yields an empty set and turns this probe RED rather than green-by-absence — the failure
// mode a "does every site contain 'escalation'?" scan has.

const fs = require('node:fs');
const path = require('node:path');

const IGNITE = path.resolve(__dirname, '..', '..', '..');

// The vocabulary, spelled out. Deliberately NOT read from any of the eight sites: an expectation
// that reads one of the things under test moves with it and passes every change to it.
const EXPECTED = ['completion', 'ask', 'answer', 'verdict', 'note', 'queue-request', 'escalation', 'stuck'];

// Each site: where it lives, and the pattern that isolates its enum literal. The pattern captures
// the LIST TEXT; the values are then pulled out of it, so a site is free to reformat its own
// quoting or spacing without this probe caring.
const SITES = [
  ['state-store/heart/heart-store.js', /const MESSAGE_TYPES = new Set\(\[([^\]]*)\]\)/],
  ['runtime/internal-api/dispatch.js', /const MESSAGE_TYPES = new Set\(\[([^\]]*)\]\)/],
  ['runtime/gateway/parse.js', /const MESSAGE_TYPES = new Set\(\[([^\]]*)\]\)/],
  ['chat/forward-path.js', /const CMP8_TYPES = new Set\(\[([^\]]*)\]\)/],
  ['state-store/heart/schema.sql', /CHECK \(type IN \(([^)]*)\)\)/],
  ['team-kit/coord.py', /^MESSAGE_TYPES = \[([^\]]*)\]/m],
  // TYPE_COLOR is the seventh site and the one a partial move breaks LOUDLY but late: a view
  // rendering a colourless type raises KeyError on the row a reader most needs to see.
  ['team-kit/coord.py', /^TYPE_COLOR = \{([^}]*)\}/m, 'TYPE_COLOR'],
  // The EIGHTH copy, found by a tree sweep during the D2 change and named by no site list before
  // it: the goal-scoped `threads.sql` schema TEMPLATE that `goal scaffold` writes. Nothing opens
  // that file as a database today, so it is inert — which is exactly why it drifted unnoticed and
  // exactly why it belongs here rather than in a comment. Its own pattern, because the literal is
  // wrapped across lines and `CHECK (type IN (` is not contiguous there.
  ['operator/goals-tree/tool/goal_cli.py', /CHECK \(type IN\s*\(([^)]*)\)\)/, 'threads.sql template'],
];

const outPath = path.join(__dirname, 'probe-message-type-vocabulary.out');
const lines = [];
const out = (...l) => lines.push(...l);

let failures = 0;
function check(name, pass, detail) {
  if (!pass) failures += 1;
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

out(`IGNITE_ROOT: ${IGNITE}`);
out(`EXPECTED (${EXPECTED.length}): ${EXPECTED.join(', ')}`);

const seen = [];
for (const [rel, re, label] of SITES) {
  const file = path.join(IGNITE, rel);
  let text = '';
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) {
    check(`${label || rel} · readable`, false, `${e.code || e.message}`);
    continue;
  }
  const m = text.match(re);
  if (!m) {
    check(`${rel}${label ? ' · ' + label : ''} · enum literal located`, false,
      'the pattern matched NOTHING — the site moved or was reformatted, and a scan that cannot '
      + 'find a site reports the same "no problem" as a site that is correct');
    continue;
  }
  const values = (m[1].match(/['"]([a-z][a-z-]*)['"]/g) || []).map((q) => q.slice(1, -1));
  seen.push({ rel, label, values });
  const same = values.length === EXPECTED.length && EXPECTED.every((t) => values.includes(t));
  check(`${rel}${label ? ' · ' + label : ''} carries the ${EXPECTED.length}-type vocabulary`,
    same, `${values.length} value(s): ${values.join(', ')}`);
}

check(`all ${SITES.length} sites were located and read`, seen.length === SITES.length,
  `${seen.length}/${SITES.length}`);

out('', `${SITES.length - failures} site check(s) clean, ${failures} failure(s)`);
out(`EXIT: ${failures ? 1 : 0}`);
fs.writeFileSync(outPath, lines.join('\n') + '\n');
process.exit(failures ? 1 : 0);

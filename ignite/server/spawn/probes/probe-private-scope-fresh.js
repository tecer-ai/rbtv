#!/usr/bin/env node
'use strict';

// ── THE MASK LIST IS COMPOSED FRESH, EVERY TIME (closeout task 07, 2026-08-15) ─────────────────
//
// `composePrivateScope`'s floor walk cost 6.5 s per spawn on the live workspace and the fix was to
// make the walk CHEAP (set membership instead of an O(tree x entries) containment scan), NOT to
// cache its result. That choice is the thing this probe holds: a cache that serves yesterday's
// entry set is not a performance win, it is a seat reading a secret that was denied an hour ago.
//
// Three legs, each a MUTATION of an input the walk must notice between two calls in ONE process —
// which is exactly where a naive memo would be wrong and a cold re-run would not catch it:
//   1  a NEW file matching the pattern floor appears -> masked on the very next composition
//   2  a `deny` entry ADDED to private.json takes effect on the very next composition
//   3  a `deny` entry REMOVED from private.json stops masking on the very next composition
// Leg 4 is the non-entry: `sender-token.env` is never masked (adv C55), asserted here too because
// it is the one path whose masking would break every seat's `send` silently.
//
// ⚠ This probe goes RED for the RIGHT reason only if `composePrivateScope` is reachable and the
// legs really flip; leg 0 pins the floor itself so a fixture that masks nothing cannot read green.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { composePrivateScope } = require('../private-scope');

function fixture() {
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'private-scope-fresh-'));
  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  fs.mkdirSync(path.join(ws, 'area'), { recursive: true });
  fs.mkdirSync(path.join(ws, 'plain'), { recursive: true });
  fs.writeFileSync(path.join(ws, 'plain', 'notes.md'), 'ordinary\n');
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'sender-token.env'), 'IGNITE_SENDER_TOKEN=x\n');
  writeScope(ws, []);
  return ws;
}

function writeScope(ws, deny) {
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'private.json'),
    JSON.stringify({ deny, patterns: ['**/*.env', '**/*.key'] }), 'utf8');
}

// The read-root shape: the whole workspace ro-bound, which is what turns the floor walk on.
const compose = (ws) => composePrivateScope([{ verb: 'ro-bind', path: ws, source: ws }],
  { workspaceRoot: ws }).entries;

capture('probe-private-scope-fresh', async (lines) => {
  const ws = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  const masks = (set, p) => set.some((e) => e === p || p.startsWith(e + path.sep));

  try {
    const secret = path.join(ws, 'plain', 'later.key');
    const token = path.join(ws, '.rbtv', 'config', 'sender-token.env');

    // ── 0 — THE FLOOR IS ACTUALLY WALKING (else every leg below passes vacuously) ─────────────
    const base = compose(ws);
    leg('0', 'the pattern floor masks something in this fixture — the legs below are not vacuous',
      base.length > 0 && !masks(base, secret),
      `entries=${base.length}; the not-yet-created ${path.basename(secret)} is absent from it`);

    // ── 1 — A NEW SECRET IS DENIED THE MOMENT IT APPEARS, NOT ON THE NEXT COLD START ──────────
    fs.writeFileSync(secret, 'sk-canary\n');
    const withNew = compose(ws);
    leg('1', 'a file matching the pattern floor is masked on the NEXT composition in the same process',
      masks(withNew, secret),
      `entries ${base.length} -> ${withNew.length}; ${path.basename(secret)} masked=${masks(withNew, secret)}`);

    // ── 2 — A TIGHTENED private.json TAKES EFFECT ON THE NEXT COMPOSITION ─────────────────────
    const area = path.join(ws, 'area');
    writeScope(ws, ['area/']);
    const tight = compose(ws);
    leg('2', 'a `deny` entry ADDED to private.json masks on the NEXT composition',
      masks(tight, area) && !masks(withNew, area),
      `area masked before=${masks(withNew, area)} after=${masks(tight, area)}`);

    // ── 3 — AND A LOOSENED ONE STOPS MASKING (a cache is wrong in BOTH directions) ────────────
    writeScope(ws, []);
    const loose = compose(ws);
    leg('3', 'a `deny` entry REMOVED from private.json stops masking on the NEXT composition',
      !masks(loose, area),
      `area masked after removal=${masks(loose, area)}`);

    // ── 4 — THE LOAD-BEARING NON-ENTRY (adv C55) ──────────────────────────────────────────────
    leg('4', '`.rbtv/config/sender-token.env` is never masked, on any of the four compositions',
      [base, withNew, tight, loose].every((s) => !masks(s, token)),
      'the DEFAULT_ALLOW exclusion holds across every mutation above');

    // ── 5/6 — THE FAIL-CLOSED FLOOR SURVIVES THE WALK CHANGE ─────────────────────────────────
    // An operator who deletes or breaks private.json must not get a WIDER cage than yesterday's:
    // the built-in DEFAULT_PATTERNS floor and the two hardcodes stand on their own. Asserted here
    // because the walk is where the floor is applied, and the walk is what changed.
    const scopeFile = path.join(ws, '.rbtv', 'config', 'private.json');
    fs.rmSync(scopeFile);
    const absent = compose(ws);
    // (No hardcode assertion on THIS leg: an entry that does not exist on disk is filtered out
    // before the walk, and masking a path that is not there would bind a mountpoint over nothing.
    // Leg 6 carries the hardcode, where the file does exist.)
    leg('5', 'private.json ABSENT — the built-in pattern floor still masks, and the cage is not wider',
      masks(absent, secret) && !masks(absent, token),
      `entries=${absent.length}; ${path.basename(secret)} masked=${masks(absent, secret)}; ` +
      `token masked=${masks(absent, token)}`);

    fs.writeFileSync(scopeFile, '{ this is not json', 'utf8');
    const broken = compose(ws);
    leg('6', 'private.json UNPARSEABLE — same floor, not a wider cage',
      masks(broken, secret) && masks(broken, scopeFile) && !masks(broken, token),
      `entries=${broken.length}; ${path.basename(secret)} masked=${masks(broken, secret)}`);

    lines.push('');
    lines.push(fails.length === 0 ? 'ALL LEGS PASS' : `FAILED LEGS: ${fails.join(', ')}`);
    if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(ws, { recursive: true, force: true }); } catch { /* best effort */ }
  }
});

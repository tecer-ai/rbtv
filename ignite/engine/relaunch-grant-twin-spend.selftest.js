'use strict';

// Self-check for the G-0818 fix: `relaunch-grants.js#spendCoordTwin` spends the grant coord's own
// predicate would pick — all three cells (seat + session-id + anchor, unspent and unrevoked) — and
// spends NOTHING, loudly, when none matches.
//
// THE FIXTURE IS THE 02:42Z SHAPE: two unspent grants for ONE seat, the SESSION-STALE one FIRST in
// file order and the LIVE one second. The old code stamped "the first unspent row for the seat
// name", so it burnt the stale row and left the live one standing — and a standing unspent grant
// makes `coord.py#mint_staff_wake` refuse every later wake mint for that chair, forever.
//
// NON-VACUOUS BY MUTATION: replace the three-cell `find` in `spendCoordTwin` with a
// first-unspent-row scan (the old predicate) and ARM 1 goes RED — the stale row is stamped and the
// live one is not. Drop the `refuse()` call from the `!sessionId || !anchor` branch and ARM 2c goes
// RED. Drop the `log && standing.length` guard and ARM 5 goes RED.
//
// Deliberately NOT a probe (no `probes/` dir, not `probe-*`), matching its siblings
// `seeding-retry-strike-limit.selftest.js` and `seeding-outcome-translation.selftest.js`. By hand:
//   node engine/relaunch-grant-twin-spend.selftest.js

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { spendCoordTwin } = require('./relaunch-grants');

const SEAT = 'leader';
const STALE_SID = '4b1e0d22';          // the seat's superseded sitting
const LIVE_SID = '98b6bcf1';           // the sitting the live grant is bound to
const NEW_SID = 'c0ffee01';            // the session a dispatch is STARTING — never a grant binding
const ANCHOR = 'mail:staff-wake';

// coord.py#RELAUNCH_GRANT_COLS, in coord's own column order.
const HEADER = 'seat,session-id,anchor,minted-by,minted-at,spent-at,revoked-at,revoke-reason';
const CSV = `${HEADER}
${SEAT},${STALE_SID},${ANCHOR},leader,2026-08-18T01:05:00Z,,,
${SEAT},${LIVE_SID},${ANCHOR},leader,2026-08-18T01:25:00Z,,,
other-seat,${LIVE_SID},${ANCHOR},leader,2026-08-18T01:26:00Z,,,
`;

function fixture() {
  const goalFolder = fs.mkdtempSync(path.join(os.tmpdir(), 'twin-spend-'));
  fs.mkdirSync(path.join(goalFolder, 'coordination'));
  const file = path.join(goalFolder, 'coordination', 'relaunch-grants.csv');
  fs.writeFileSync(file, CSV, 'utf8');
  return { goalFolder, file, read: () => fs.readFileSync(file, 'utf8') };
}

const rowsOf = (text) => text.split('\n').filter((l) => l.trim()).slice(1).map((l) => l.split(','));
const spentCellOf = (text, sid) => (rowsOf(text).find((c) => c[0] === SEAT && c[1] === sid) || [])[5];

// A `log` seam of spawn.js's shape: log(level, message, context).
function recorder() {
  const seen = [];
  const log = (level, message, ctx) => seen.push({ level, message, ctx });
  return { log, seen };
}

// ── ARM 1 · the RIGHT grant is spent ──────────────────────────────────────────────────────────
{
  const fx = fixture();
  const before = fx.read();
  const out = spendCoordTwin(fx.goalFolder, SEAT, LIVE_SID, ANCHOR, recorder().log);
  const after = fx.read();
  assert.strictEqual(out.why, '', `arm 1 must match, got why=${out.why}`);
  assert.ok(out.spent, 'arm 1 must return the stamp it wrote');
  assert.strictEqual(spentCellOf(after, LIVE_SID), out.spent, 'the LIVE row must carry the stamp');
  assert.strictEqual(spentCellOf(after, STALE_SID), '', 'the SESSION-STALE row must be UNTOUCHED');
  assert.strictEqual(rowsOf(after).length, rowsOf(before).length, 'no row may appear or vanish');
  assert.strictEqual(rowsOf(after)[2].join(','), rowsOf(before)[2].join(','),
    "another seat's row must be byte-identical");

  // ARM 4 · already spent → coord's `spent` leg, and nothing written twice.
  const again = spendCoordTwin(fx.goalFolder, SEAT, LIVE_SID, ANCHOR, recorder().log);
  assert.strictEqual(again.why, 'spent', `a burnt grant must refuse as \`spent\`, got ${again.why}`);
  assert.strictEqual(again.spent, '', 'a burnt grant must write nothing');
  assert.strictEqual(fx.read(), after, 'the file must be byte-identical after the second ask');
  fs.rmSync(fx.goalFolder, { recursive: true, force: true });
}

// ── ARM 2 · the WRONG spend is impossible, and it says so ─────────────────────────────────────
for (const [name, sid, anchor, why] of [
  // ⚠ THE TRAP: the id of the session being STARTED is not the grant's binding. It must match
  // NOTHING — never "the first unspent row", which is what made the freeze permanent.
  ['2a new-session (the dispatch trap)', NEW_SID, ANCHOR, 'stale-session'],
  ['2b right session, wrong anchor', LIVE_SID, 'rule-relaunch:hand', 'anchor-mismatch'],
  ['2c no binding at all (spawn.js dispatch)', null, null, 'no-binding'],
]) {
  const fx = fixture();
  const before = fx.read();
  const rec = recorder();
  const out = spendCoordTwin(fx.goalFolder, SEAT, sid, anchor, rec.log);
  assert.strictEqual(out.why, why, `arm ${name}: expected \`${why}\`, got \`${out.why}\``);
  assert.strictEqual(out.spent, '', `arm ${name}: must spend NOTHING`);
  assert.strictEqual(fx.read(), before, `arm ${name}: the file must be byte-identical`);
  assert.strictEqual(rec.seen.length, 1, `arm ${name}: the refusal must be logged exactly once`);
  assert.strictEqual(rec.seen[0].level, 'warn', `arm ${name}: at warn`);
  assert.strictEqual(rec.seen[0].ctx.why, why, `arm ${name}: the log must name the leg`);
  assert.ok(rec.seen[0].ctx.standing.length === 2,
    `arm ${name}: the log must name the grants left standing`);
  fs.rmSync(fx.goalFolder, { recursive: true, force: true });
}

// ── ARM 5 · a seat with NOTHING standing is the ordinary case and stays QUIET ──────────────────
{
  const fx = fixture();
  const rec = recorder();
  const out = spendCoordTwin(fx.goalFolder, 'ungranted-seat', NEW_SID, ANCHOR, rec.log);
  assert.strictEqual(out.why, 'no-row', `a seat with no grant row must answer \`no-row\`, got ${out.why}`);
  assert.strictEqual(rec.seen.length, 0,
    'a seat with no grant standing must NOT warn — warning every dispatch buries the one line that matters');

  // ...and neither does a seat whose only rows are already burnt.
  spendCoordTwin(fx.goalFolder, SEAT, STALE_SID, ANCHOR, rec.log);
  spendCoordTwin(fx.goalFolder, SEAT, LIVE_SID, ANCHOR, rec.log);
  const quiet = recorder();
  const done = spendCoordTwin(fx.goalFolder, SEAT, NEW_SID, ANCHOR, quiet.log);
  assert.strictEqual(done.why, 'stale-session', `expected \`stale-session\`, got ${done.why}`);
  assert.strictEqual(quiet.seen.length, 0, 'nothing standing → nothing to warn about');
  fs.rmSync(fx.goalFolder, { recursive: true, force: true });
}

// ── ARM 6 · a missing csv is no grant, never a throw ───────────────────────────────────────────
{
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'twin-spend-none-'));
  assert.strictEqual(spendCoordTwin(empty, SEAT, LIVE_SID, ANCHOR, null).why, 'no-row');
  fs.rmSync(empty, { recursive: true, force: true });
}

console.log('relaunch-grant twin-spend selftest OK '
  + '(live row spent, stale row untouched; new-session/wrong-anchor/no-binding all refused and logged; '
  + 'nothing standing stays quiet)');

'use strict';

// engine/relaunch-grants.js — THE ONE HOME OF "the operator authorized this seat to run again".
//
// The grant already existed and the eligibility engine already honoured it: `recordView` drops a
// granted seat from `foreign`/`notFinished`/`blocked` (never from `finished`), and
// `executionsByJob` hides this store's memory of the seat's failed attempt, so the seat reads
// `ready` once more. What did not exist was a way for the DAEMON lane to receive one: the grant's
// only source was an in-memory `Set` built from `rbtv-execution --relaunch` argv, and
// `lane-watch.js` calls `seedGoal({goalFolder, goal, profile})` with no relaunch key, ever. A seat
// that failed on the daemon lane could therefore never be retried — measured on
// `.rbtv/goals/forge-reference-seat-id-naming`, seat `forg-intake`.
//
// So the grant becomes a FILE in the goal folder, which is the one surface both lanes already
// share (`executions.csv`, `execution-lane`, `execution-mode` all live there). It is read INSIDE
// the shared seeding functions rather than threaded down from each caller — a parameter would be a
// SECOND place that decides whether a grant applies, and a future third caller of `seedGoal` would
// silently get none, which is exactly how this gap was born.
//
//   <goal-folder>/relaunch-grants   ONE BARE SEAT NAME PER LINE. No header, no CSV, no columns.
//
// ⚠ NOT `coordination/relaunch-grants.csv`. That is the team-kit's tmux-lifecycle grant (a leader
// minting a pane relaunch, `coord.py#relaunch_grants_csv`) — a different act on a different
// surface. Same word, different file, and neither reads the other's.
//
// FAIL-CLOSED, in both directions:
//   · an ABSENT or UNREADABLE file yields an EMPTY set and never throws. A grant is an act of
//     authorization; an I/O error must never be able to synthesize one.
//   · the spend is tmp+rename, for the reason `goal_cli.py#write_lane_raw` is: a truncate window
//     must not read as "no grant" mid-write (dropping a grant the operator gave), nor as a grant
//     after the spend (running the seat twice).

const fs = require('node:fs');
const path = require('node:path');

const GRANT_FILE = 'relaunch-grants';

function grantPath(goalFolder) {
  return path.join(goalFolder, GRANT_FILE);
}

function readLines(goalFolder) {
  return fs.readFileSync(grantPath(goalFolder), 'utf8')
    .split('\n').map((l) => l.trim()).filter((l) => l.length);
}

function readGrants(goalFolder) {
  try {
    return new Set(readLines(goalFolder));
  } catch {
    return new Set();          // missing, unreadable, a directory — all ONE answer: no grant
  }
}

// Append one seat. `appendFileSync` opens O_APPEND, so a concurrent minter's line cannot land
// inside ours and no window ever shows the file short of what it held.
function grantRelaunch(goalFolder, seat) {
  fs.appendFileSync(grantPath(goalFolder), `${String(seat).trim()}\n`, 'utf8');
  return grantPath(goalFolder);
}

// Remove every line naming `seat`. Returns true when the file changed.
//
// ponytail: read-modify-write, so a mint racing a spend can lose the mint. The window is two file
// ops in a pass that already re-reads the record every cadence, and the losing outcome is a grant
// the operator re-issues — not a double run, which is the direction that matters. Upgrade path: the
// `O_EXCL` lockfile `execution-record.js` already carries, the day a minter is not a human typing.
function spendGrant(goalFolder, seat) {
  const file = grantPath(goalFolder);
  let lines;
  try { lines = readLines(goalFolder); } catch { return false; }
  const keep = lines.filter((l) => l !== seat);
  if (keep.length === lines.length) return false;
  const tmp = `${file}.tmp.${process.pid}`;      // same directory — that is what makes rename atomic
  fs.writeFileSync(tmp, keep.length ? `${keep.join('\n')}\n` : '', 'utf8');
  fs.renameSync(tmp, file);
  spendCoordTwin(goalFolder, seat);
  return true;
}

// ── THE COORD TWIN'S SPEND (loop re-fire, owner ruling 2026-08-12) ─────────────────────────────
//
// The verdict verb's `on-fail-relaunch` route mints into BOTH grant stores (see coord.py
// #mint_loop_refire), because coord's csv is what flips a `done` seat READY on the ready surface
// and this file is what hides its history from the engine's own eligibility reader. The csv grant
// is spent by `coordinate launch` on the tmux lane — but the ENGINE lane never calls that, so an
// engine spend that left the twin standing would flip the seat READY again after its re-run,
// forever, and hold its dependents on `relaunch-granted` with it. Stamping the FIRST unspent row
// for the seat here keeps the two stores moving as one on this lane. Best-effort by design: no
// csv, no matching row, or an unparseable file spends nothing and fails silently — this is a
// hygiene write over another surface's file, and refusing the engine's own spend over it would
// invert the ownership. Plain comma split: every column the writer emits (seat, session-id,
// anchor, minted-by, stamps) is comma-free by construction.
function spendCoordTwin(goalFolder, seat) {
  const file = path.join(goalFolder, 'coordination', 'relaunch-grants.csv');
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return; }
  const lines = text.split('\n');
  const header = (lines[0] || '').split(',').map((c) => c.trim());
  const seatIdx = header.indexOf('seat');
  const spentIdx = header.indexOf('spent-at');
  if (seatIdx === -1 || spentIdx === -1) return;
  for (let i = 1; i < lines.length; i += 1) {
    if (!lines[i].trim()) continue;
    const cells = lines[i].split(',');
    if ((cells[seatIdx] || '').trim() !== seat || (cells[spentIdx] || '').trim()) continue;
    while (cells.length <= spentIdx) cells.push('');
    cells[spentIdx] = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    lines[i] = cells.join(',');
    const tmp = `${file}.tmp.${process.pid}`;
    try {
      fs.writeFileSync(tmp, lines.join('\n'), 'utf8');
      fs.renameSync(tmp, file);
    } catch { /* hygiene write only — the engine's own spend already happened */ }
    return;
  }
}

module.exports = { GRANT_FILE, grantPath, readGrants, grantRelaunch, spendGrant };

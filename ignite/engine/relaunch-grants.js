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
  return true;
}

// ── THE COORD TWIN'S SPEND (loop re-fire, owner ruling 2026-08-12) ─────────────────────────────
//
// The verdict verb's `on-fail-relaunch` route mints into BOTH grant stores (see coord.py
// #mint_loop_refire), because coord's csv is what flips a `done` seat READY on the ready surface
// and this file is what hides its history from the engine's own eligibility reader. The csv grant
// is spent by `coordinate launch` on the tmux lane — but the ENGINE lane never calls that, so an
// engine spend that left the twin standing would flip the seat READY again after its re-run,
// forever, and hold its dependents on `relaunch-granted` with it. Still a hygiene write over
// another surface's file; still best-effort — no csv, no matching row, or an unparseable file
// spends nothing. Plain comma split: every column the writer emits (seat, session-id, anchor,
// minted-by, stamps) is comma-free by construction.
//
// ── ONE FILE, ONE PREDICATE (G-0818 fix) ──────────────────────────────────────────────────────
//
// THIS USED TO STAMP THE FIRST UNSPENT ROW FOR THE SEAT NAME, and that is the defect. coord owns
// this file and its predicate needs ALL THREE CELLS — seat AND `session-id` AND `anchor`, unspent
// and unrevoked (`coord.py#match_relaunch_grant`, `#spend_relaunch_grant`). Two readers with two
// ideas of what a matching grant is made a freeze permanent on 2026-08-18 at 02:42Z: a chat-bridge
// dispatch reached here, stamped the SESSION-STALE 01:05 grant, and left the LIVE 01:25 one
// standing — and a standing unspent grant makes `coord.py#mint_staff_wake` refuse every later wake
// mint for that chair, forever. So the predicate below IS coord's, leg for leg, including the
// order the legs are reported in. Nothing is invented over coord's file; the three cells cross as
// ARGUMENTS, which is the rule `seeding.js#mintRetryGrants` states.
//
// ⚠ `sessionId` IS THE GRANT'S BINDING — THE SEAT'S PREVIOUS, ENDED SITTING — NOT the id of the
// session a caller is starting. A dispatch that passes its NEW session id matches nothing, ever,
// which turns this function into a silent no-op. Callers that hold no binding pass none and get
// `no-binding` back.
//
// THE NO-MATCH BEHAVIOUR, stated because a silent one is how 02:42Z stayed invisible: SPEND
// NOTHING, and say so through `log` — with the leg that failed, in coord's own five-word
// vocabulary (`no-row`, `stale-session`, `anchor-mismatch`, `spent`, `revoked`; `no-binding` and
// `write-failed` name a CALLER-side and an IO-side absence, which are this side's, not coord's).
// It logs only when a LIVE grant is left STANDING for that seat, because that is the state with a
// cost — an unspent grant suppresses the chair's next wake mint. A seat with nothing standing is
// the ordinary case and warning on it every dispatch would bury the one line that matters.
//
// Returns `{spent, why}`: the stamp written (or ""), and the leg that refused (or "").
function spendCoordTwin(goalFolder, seat, sessionId, anchor, log = null) {
  const file = path.join(goalFolder, 'coordination', 'relaunch-grants.csv');
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return { spent: '', why: 'no-row' }; }
  const lines = text.split('\n');
  const header = (lines[0] || '').split(',').map((c) => c.trim());
  const seatIdx = header.indexOf('seat');
  const spentIdx = header.indexOf('spent-at');
  if (seatIdx === -1 || spentIdx === -1) return { spent: '', why: 'no-row' };
  const sessionIdx = header.indexOf('session-id');
  const anchorIdx = header.indexOf('anchor');
  const revokedIdx = header.indexOf('revoked-at');
  // An ABSENT column reads "" on every row — `coord.py#read_relaunch_grants` pads the same way, so
  // a narrow legacy header refuses rather than matching on the columns it happens to carry.
  const cell = (cells, i) => (i === -1 ? '' : (cells[i] || '').trim());

  const forSeat = [];
  for (let i = 1; i < lines.length; i += 1) {
    if (!lines[i].trim()) continue;
    const cells = lines[i].split(',');
    if (cell(cells, seatIdx) !== seat) continue;
    const stampCell = cell(cells, spentIdx);
    // coord's own two predicates: a legacy `revoked-…` written into `spent-at` is REVOKED, not
    // spent (`grant_is_spent`/`grant_is_revoked`), and a retired grant is not a consumed one.
    const revoked = !!cell(cells, revokedIdx) || /^revoked-/.test(stampCell);
    const spent = !!stampCell && !/^revoked-/.test(stampCell);
    forSeat.push({
      i,
      cells,
      session: cell(cells, sessionIdx),
      anchor: cell(cells, anchorIdx),
      revoked,
      live: !spent && !revoked,
    });
  }
  if (!forSeat.length) return { spent: '', why: 'no-row' };

  const standing = forSeat.filter((g) => g.live);
  const refuse = (why) => {
    if (log && standing.length) {
      log('warn', 'coord relaunch grant NOT spent — no row matched all three cells (seat + session-id '
        + '+ anchor, unspent and unrevoked), and a LIVE grant is left STANDING for this seat. An '
        + 'unspent grant suppresses this chair\'s next wake mint (coord.py#mint_staff_wake), so the '
        + 'seat can go quiet with nothing else saying why.', {
        seat,
        why,
        goalFolder,
        askedSession: sessionId || null,
        askedAnchor: anchor || null,
        standing: standing.map((g) => `${g.session}/${g.anchor}`),
      });
    }
    return { spent: '', why };
  };

  if (!sessionId || !anchor) return refuse('no-binding');

  const hit = forSeat.find((g) => g.session === sessionId && g.anchor === anchor && g.live);
  if (!hit) {
    // The legs, in `match_relaunch_grant`'s order — cheapest for the caller to check first.
    const sameSession = forSeat.filter((g) => g.session === sessionId);
    if (!sameSession.length) return refuse('stale-session');
    const matched = sameSession.filter((g) => g.anchor === anchor);
    if (!matched.length) return refuse('anchor-mismatch');
    return refuse(matched.some((g) => g.revoked) ? 'revoked' : 'spent');
  }

  const stamp = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  while (hit.cells.length <= spentIdx) hit.cells.push('');
  hit.cells[spentIdx] = stamp;
  lines[hit.i] = hit.cells.join(',');
  const tmp = `${file}.tmp.${process.pid}`;
  try {
    fs.writeFileSync(tmp, lines.join('\n'), 'utf8');
    fs.renameSync(tmp, file);
  } catch {
    return refuse('write-failed');    // hygiene write only — the engine's own spend already happened
  }
  return { spent: stamp, why: '' };
}

module.exports = { GRANT_FILE, grantPath, readGrants, grantRelaunch, spendGrant, spendCoordTwin };

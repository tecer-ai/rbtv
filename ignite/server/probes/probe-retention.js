'use strict';

// probe-retention — task 7.13's retention policy for the per-machine state root, exercised
// against a THROWAWAY fabricated root under os.tmpdir() (this probe deletes files — it must
// NEVER be pointed at a live state root).
//
// What it proves, per the owner ruling (batch 08 item 2 + item 10 part 5, D8):
//   1. The env knob's floor: default 90, `0` = never delete, and values below 7 are REJECTED
//      loudly (a typo must not be able to erase the audit trail).
//   2. The sweep's DATE BOUNDARY: an artifact just OUTSIDE the window is deleted; one just
//      INSIDE survives.
//   3. ⚑ THE EXCLUSION THAT PROTECTS THE LIVE DATABASE: `heart.db` (which task 7.20 moved
//      into this exact root) and `.runtime-config/` are NEVER touched, at ANY age — and the
//      scope is a POSITIVE enumeration, so an unknown file in the root also survives. If the
//      exclusion regresses, this probe FAILS.
//   4. A LIVE session's artifacts are never swept regardless of age.
//   5. Singleton rotation: ticker.log/feed.jsonl/ttyd.log rotate to dated segments at most
//      once per UTC day, and only the SEGMENTS age out.
//   6. Piece 4's heal pass: a 664 transcript in logs/ is tightened to 0600 — even when
//      retentionDays is 0 (mode-tightening is not deletion).
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The process
// exit code is the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-retention.out');
fs.writeFileSync(outPath, '');

const {
  parseRetentionDays, sweepRetention, RetentionConfigError,
  DEFAULT_RETENTION_DAYS, MIN_RETENTION_DAYS,
} = require('../retention');

const checks = [];
let skipped = 0;
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'} | ${name}${detail ? ' | ' + detail : ''}`);
}

const DAY_MS = 24 * 60 * 60 * 1000;
const NOW = Date.now();
const WINDOW = 90;
const CUTOFF = NOW - WINDOW * DAY_MS;

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-probe-retention-'));

function mkfile(rel, { ageMs = 0, mode = 0o600, content = 'x' } = {}) {
  const p = path.join(root, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content, { mode });
  const t = new Date(NOW - ageMs);
  fs.utimesSync(p, t, t);
  return p;
}

function main() {
  // --- 1. The knob's parse floor.
  check('unset -> default 90', parseRetentionDays(undefined) === DEFAULT_RETENTION_DAYS);
  check("'0' -> 0 (never delete)", parseRetentionDays('0') === 0);
  check(`'${MIN_RETENTION_DAYS}' -> ${MIN_RETENTION_DAYS} (floor is inclusive)`, parseRetentionDays(String(MIN_RETENTION_DAYS)) === MIN_RETENTION_DAYS);
  check("'90' -> 90", parseRetentionDays('90') === 90);
  for (const bad of ['6', '1', '3']) {
    let threw = null;
    try { parseRetentionDays(bad); } catch (e) { threw = e; }
    check(`'${bad}' (below the ${MIN_RETENTION_DAYS}-day floor) is REJECTED loudly`,
      threw instanceof RetentionConfigError && threw.code === 'E_CONFIG_LOAD',
      threw ? threw.message.slice(0, 80) : 'no throw');
  }
  for (const bad of ['-1', 'abc', '7.5']) {
    let threw = null;
    try { parseRetentionDays(bad); } catch (e) { threw = e; }
    check(`'${bad}' (not a non-negative integer) is REJECTED loudly`, threw instanceof RetentionConfigError,
      threw ? threw.message.slice(0, 80) : 'no throw');
  }

  // --- Fabricate the root.
  // Date boundary pair (the window edge, exercised one hour to each side).
  const oldLog = mkfile('logs/dead-session-old.log', { ageMs: (WINDOW * DAY_MS) + 3600e3 });
  const oldAudit = mkfile('logs/dead-session-old.keys.jsonl', { ageMs: (WINDOW * DAY_MS) + 3600e3 });
  const youngLog = mkfile('logs/dead-session-young.log', { ageMs: (WINDOW * DAY_MS) - 3600e3 });
  // Per-session artifacts across the other enumerated dirs, all beyond the window.
  const oldPrompt = mkfile('prompts/dead-session-old.txt', { ageMs: 100 * DAY_MS });
  const oldExit = mkfile('exits/dead-session-old.exit', { ageMs: 100 * DAY_MS });
  const oldSock = mkfile('ptys/dead-session-old.sock', { ageMs: 100 * DAY_MS });
  // A LIVE session's ancient artifacts (must survive).
  const liveLog = mkfile('logs/live-session.log', { ageMs: 200 * DAY_MS });
  // ⚑ The protected neighbours, at absurd ages: the database, its WAL, the runtime config,
  // and a file the enumeration has never heard of.
  const heartDb = mkfile('heart.db', { ageMs: 400 * DAY_MS, content: 'THE LIVE DATABASE' });
  const heartWal = mkfile('heart.db-wal', { ageMs: 400 * DAY_MS });
  const runtimeCfg = mkfile('.runtime-config/spawn-profiles.yaml', { ageMs: 400 * DAY_MS });
  const unknown = mkfile('some-future-artifact.bin', { ageMs: 400 * DAY_MS });
  // Singletons: fresh live files + one ancient rotated segment.
  const tickerLog = mkfile('ticker.log', { ageMs: 0, content: 'tick\n' });
  const feedJsonl = mkfile('feed.jsonl', { ageMs: 0, content: '{}\n' });
  const ttydLog = mkfile('ttyd.log', { ageMs: 0, content: 'ttyd\n' });
  const oldSegment = mkfile('ticker.log.2020-01-01', { ageMs: 400 * DAY_MS });
  // Piece 4: a loosened transcript (664), young — must be tightened, not deleted.
  const looseLog = mkfile('logs/loose-session.log', { ageMs: 1 * DAY_MS, mode: 0o664 });

  // --- 2..6. One sweep.
  const res = sweepRetention({
    dataRoot: root, retentionDays: WINDOW, now: NOW,
    isSessionLive: (sid) => sid === 'live-session',
  });

  check('date boundary: artifact just OUTSIDE the window is deleted (transcript)', !fs.existsSync(oldLog));
  check('date boundary: its audit neighbour is deleted with it', !fs.existsSync(oldAudit));
  check('date boundary: artifact just INSIDE the window survives', fs.existsSync(youngLog));
  check('prompts/ artifact beyond the window is deleted', !fs.existsSync(oldPrompt));
  check('exits/ artifact beyond the window is deleted', !fs.existsSync(oldExit));
  check('ptys/ artifact beyond the window is deleted', !fs.existsSync(oldSock));
  check('a LIVE session\'s artifacts are never swept, at any age', fs.existsSync(liveLog),
    `skipped_live=${JSON.stringify(res.skipped_live.map((p) => path.basename(p)))}`);

  // ⚑ THE PROBE THAT PROTECTS THE LIVE DATABASE — if the exclusion regresses, these FAIL.
  check('heart.db SURVIVES the sweep at 400 days old (positive enumeration — never visited)',
    fs.existsSync(heartDb) && fs.readFileSync(heartDb, 'utf8') === 'THE LIVE DATABASE');
  check('heart.db-wal SURVIVES', fs.existsSync(heartWal));
  check('.runtime-config/ SURVIVES', fs.existsSync(runtimeCfg));
  check('an UNKNOWN root file survives (enumeration fails closed, not a denylist)', fs.existsSync(unknown));

  const today = new Date(NOW).toISOString().slice(0, 10);
  check('ticker.log rotated to a dated segment', fs.existsSync(`${tickerLog}.${today}`) && !fs.existsSync(tickerLog));
  check('feed.jsonl rotated to a dated segment', fs.existsSync(`${feedJsonl}.${today}`));
  check('ttyd.log rotated to a dated segment (D8: INCLUDED in retention)', fs.existsSync(`${ttydLog}.${today}`));
  check('an ancient rotated segment is deleted', !fs.existsSync(oldSegment));

  check('a 664 transcript in logs/ is tightened to 0600 (piece 4 heal pass)',
    (fs.statSync(looseLog).mode & 0o777) === 0o600,
    `mode=${(fs.statSync(looseLog).mode & 0o777).toString(8)}`);

  // Same-day idempotence: a second sweep must not double-rotate or delete today's segments.
  fs.writeFileSync(tickerLog, 'tick2\n'); // the writer's next append recreates the live file
  const res2 = sweepRetention({ dataRoot: root, retentionDays: WINDOW, now: NOW });
  check('second sweep the same day does NOT rotate again (dated target exists)',
    res2.rotated.length === 0 && fs.existsSync(tickerLog) && fs.existsSync(`${tickerLog}.${today}`));

  // retentionDays === 0: nothing is deleted, but modes are still tightened.
  const zeroRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-probe-retention0-'));
  const zOld = path.join(zeroRoot, 'logs', 'z.log');
  fs.mkdirSync(path.dirname(zOld), { recursive: true });
  fs.writeFileSync(zOld, 'x', { mode: 0o664 });
  const zt = new Date(NOW - 400 * DAY_MS);
  fs.utimesSync(zOld, zt, zt);
  const zres = sweepRetention({ dataRoot: zeroRoot, retentionDays: 0, now: NOW });
  check('retentionDays=0: a 400-day-old artifact is NOT deleted (never delete)', fs.existsSync(zOld),
    `removed=${zres.removed.length}`);
  check('retentionDays=0: the mode heal pass still runs (tightening is not deletion)',
    (fs.statSync(zOld).mode & 0o777) === 0o600);
  fs.rmSync(zeroRoot, { recursive: true, force: true });
}

try {
  main();
} catch (err) {
  out('ERROR:', err.message, err.stack);
  checks.push({ name: 'unhandled error', pass: false });
} finally {
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }
}

const failed = checks.filter((c) => !c.pass);
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`SKIPPED_COUNT: ${skipped}`);
out(`RETENTION_OK: ${failed.length === 0}`);
out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = failed.length === 0 ? 0 : 1;

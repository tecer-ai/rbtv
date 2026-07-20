'use strict';

// probe-cli-ticker — proves `ignite inspect ticker` end-to-end through the
// REAL CLI binary against a REAL (throwaway) daemon.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, waitForLog, stopDaemon, runCli,
} = require('./lib/fixtures');
const { openHeartStore, closeHeartStore } = require('../../server/heart/heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-ticker.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-3-cli-ticker');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // Wait for at least one tick to complete so ticker has data.
    try {
      await waitForLog(d, /"message":"tick \d+ end"/);
    } catch {
      out('NOTE: timed out waiting for a tick — continuing anyway (ticker view should still answer)');
    }

    // 1. inspect ticker --json
    let r = await runCli(['--json', 'inspect', 'ticker'], cliEnv);
    out('--- inspect ticker --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('inspect ticker --json exits 0 and returns ok envelope',
      r.code === 0 && envelope && envelope.ok === true,
      `exit=${r.code} ok=${envelope && envelope.ok}`);

    check('inspect ticker result carries recent_ticks array',
      envelope && envelope.ok && Array.isArray(envelope.result.recent_ticks),
      `recent_ticks_len=${envelope && envelope.result && envelope.result.recent_ticks && envelope.result.recent_ticks.length}`);

    check('inspect ticker result has at least one tick after daemon boot',
      envelope && envelope.ok && Array.isArray(envelope.result.recent_ticks)
        && envelope.result.recent_ticks.length > 0,
      `recent_ticks_len=${envelope && envelope.result && envelope.result.recent_ticks ? envelope.result.recent_ticks.length : 'N/A'}`);

    check('inspect ticker carries live_sessions array (every row carrying queue_id, D108(B))',
      envelope && envelope.ok && Array.isArray(envelope.result.live_sessions)
        && envelope.result.live_sessions.every((s) => s && Object.prototype.hasOwnProperty.call(s, 'queue_id')),
      `live_sessions_len=${envelope && envelope.result && envelope.result.live_sessions && envelope.result.live_sessions.length}`);

    check('inspect ticker carries queue_rows array',
      envelope && envelope.ok && Array.isArray(envelope.result.queue_rows),
      `queue_rows_len=${envelope && envelope.result && envelope.result.queue_rows && envelope.result.queue_rows.length}`);

    check('inspect ticker carries owner_feed_notes array',
      envelope && envelope.ok && Array.isArray(envelope.result.owner_feed_notes),
      `owner_feed_notes_len=${envelope && envelope.result && envelope.result.owner_feed_notes && envelope.result.owner_feed_notes.length}`);

    check('inspect ticker carries config knobs',
      envelope && envelope.ok && envelope.result.config
        && typeof envelope.result.config.tick_interval_ms === 'number',
      `config=${JSON.stringify(envelope && envelope.result && envelope.result.config)}`);

    // 2. inspect ticker human-readable
    r = await runCli(['inspect', 'ticker'], cliEnv);
    out('--- inspect ticker (human) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('inspect ticker exits 0 and renders something non-empty',
      r.code === 0 && r.stdout.trim().length > 0,
      `exit=${r.code} stdout_len=${r.stdout.trim().length}`);

    // 10. >50-message owner-feed recency regression guard (task 4.5,
    // registry-reconciliation batch-08 item 8). Seeds 50 non-owner-feed
    // messages, then 5 recent owner-feed notes, directly into the LIVE
    // daemon's own store (a 2nd connection to its WAL db — same pattern as
    // lib/fixtures.js's seedWarning against an already-booted daemon). If
    // handleInspectTicker's owner-feed read ever regresses to a HEAD-bound
    // `getMessages({ limit: 50 })` (the bug this task exists to catch), the
    // oldest-50 window is entirely non-owner-feed and owner_feed_notes comes
    // back EMPTY — this assertion fails loudly instead of the recurrence
    // passing silently.
    const seedStore = openHeartStore({ dbPath: path.join(ws.dataRoot, 'heart.db') });
    let newestNoteCorpus = '';
    let seededTotal = 0;
    try {
      for (let i = 1; i <= 50; i++) {
        seedStore.recordMessage({ type: 'note', sender: 'ticker', thread: `exec-recency-${i}`, corpus: `non-feed-${i}` });
      }
      for (let i = 1; i <= 5; i++) {
        newestNoteCorpus = `RECENT-OWNER-NOTE-${i}`;
        seedStore.recordMessage({ type: 'note', sender: 'ticker', thread: 'owner-feed', corpus: newestNoteCorpus });
      }
      seededTotal = seedStore.getMessages().length;
    } finally {
      closeHeartStore();
    }

    r = await runCli(['--json', 'inspect', 'ticker'], cliEnv);
    out('--- inspect ticker --json (post-seed, recency guard) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let recencyEnvelope = null;
    try { recencyEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    const recencyNotes = (recencyEnvelope && recencyEnvelope.ok && recencyEnvelope.result.owner_feed_notes) || [];
    const recencyCorpora = recencyNotes.map((n) => n.corpus || JSON.stringify(n));
    check('owner_feed_notes returns the NEWEST note past a >50-message head (fails if {limit:50} is reintroduced)',
      r.code === 0 && recencyEnvelope && recencyEnvelope.ok === true
        && seededTotal > 50 && recencyCorpora.some((c) => String(c).includes(newestNoteCorpus)),
      `seeded_total=${seededTotal} newest="${newestNoteCorpus}" got=[${recencyCorpora.join(' | ').slice(0, 200)}]`);
  } finally {
    await stopDaemon(d);
    try { fs.rmSync(ws.tmp, { recursive: true, force: true }); } catch {}
  }
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
});

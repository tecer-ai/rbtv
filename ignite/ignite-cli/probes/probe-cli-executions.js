'use strict';

// probe-cli-executions — proves `ignite inspect executions --status <s> [--offset n] [--limit n]
// [--tail n]`
// (task 7.62) end-to-end through the REAL CLI BINARY, as a REAL CHILD PROCESS, over the REAL HTTP
// transport, against a REAL (throwaway) daemon.
//
// WHY THIS EXISTS ALONGSIDE server/internal-api/probes/probe-inspect-executions.js, which already
// covers this feature: that probe enters at the gateway function and, for the CLI, calls
// commands/inspect.js's `run()` in-process against a stub ctx. Both are real coverage — and both
// enter BELOW `ignite.js`. So argv parsing/routing through the CLI entry point and the HTTP round
// trip were exercised by NOTHING, in a feature whose entire audience is an operator typing it at a
// terminal. That gap was filed as G-159's sibling before this probe was written, and this probe is
// what closes it: a completion claiming "the CLI is covered" would otherwise have been true of
// what was checked and false of what it implies.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file, ephemeral port; only
// the child this probe spawns is ever signaled.
//
// ⚑ Nothing runs cli/probes/ automatically (the suite has no runner — that is a live, separately
// filed defect, and fixtures.js's own comment records a probe here rotting unnoticed for a week
// because of it). This probe is therefore written to be readable and runnable BY HAND, and its
// exit code is the truth.

const fs = require('node:fs');
const path = require('node:path');
const {
  IGNITE_SRC, freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

// LOCAL fixture helper (cli-expansion ruling D4: fixtures.js is READ-ONLY — a missing helper is
// built inside the probe file, never added there). seedCatalogue always leaves an execution
// 'launching'; this moves seeded rows onto the statuses under test, pre-boot, through the store's
// OWN API — never raw SQL, and never the CLI bypassing the gateway.
const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'state-store', 'heart', 'heart-store'));
const { DatabaseSync } = require('node:sqlite');
function setStatus(ws, execId, status) {
  const store = openHeartStore({ dbPath: path.join(ws.dataRoot, 'heart.db') });
  try {
    store.updateExecutionStatus(execId, { status });
  } finally {
    closeHeartStore();
  }
}
// Disk truth on a read-only connection — a reader can never be a second writer.
function readStatuses(ws) {
  const raw = new DatabaseSync(path.join(ws.dataRoot, 'heart.db'), { readOnly: true });
  try {
    return raw.prepare('SELECT exec_id, status FROM jobs_log ORDER BY exec_id').all();
  } finally {
    raw.close();
  }
}

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-executions.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass: Boolean(pass) });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function parseJson(stdout) {
  try { return JSON.parse(stdout); } catch { return null; }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('t762-cli-executions');
  const port = await freePort();
  const env = baseEnv(ws, port);

  // Three executions across TWO statuses, plus a third status left EMPTY on purpose. Uneven and
  // interleaved, so a surface that ignored its filter or returned the first N rows is
  // distinguishable from one that filtered.
  //
  // ⚑ THE STATUSES ARE `failed` AND `done`, AND THAT CHOICE IS LOAD-BEARING — NOT `stalled`.
  // This probe's first run seeded `stalled` and found all three rows reading `failed` within the
  // daemon's FIRST TICK: a live ticker actively rewrites non-terminal statuses, sweeping seeded
  // never-spawned rows through the stall ladder (server/ticker/ticker.js — listExecutionsByStatus
  // ('stalled')), and `blocked` is re-dispatched by the same loop while `launching`/`running` meet
  // the crash sweep. Measured, not reasoned: seeded-before-boot rows were intact AT boot and
  // rewritten ~1.5s later; `failed`/`done` were still intact after 4s.
  //
  // The finding is the FIXTURE's, never the feature's — but it is exactly the class an
  // in-process probe CANNOT see, because it has no ticker. A probe that seeded a transient status
  // against a live daemon would fail intermittently and read as a broken filter.
  const a = seedCatalogue(ws, { withExecution: true }).execId;
  const b = seedCatalogue(ws, { withExecution: true }).execId;
  const c = seedCatalogue(ws, { withExecution: true }).execId;
  setStatus(ws, a, 'failed');
  setStatus(ws, b, 'done');
  setStatus(ws, c, 'failed');
  out(`seeded: failed=[${a},${c}] done=[${b}] killed=[] (empty on purpose)`);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  // The summary block that sets the exit code is INSIDE main(), so this abort must carry
  // its own verdict: a bare `return` here exited 0 with the check above FAILED (7.701).
  if (!d.listening) { out('ABORT: daemon never listened.'); process.exit(1); }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // ── 0. FIXTURE PRECONDITION, asserted rather than assumed. If the running engine has
    // rewritten a seeded status, every filter check below would be measuring the wrong fleet and
    // would read as a broken filter. This check makes that failure NAME ITSELF.
    {
      const disk = readStatuses(ws);
      const want = JSON.stringify([{ exec_id: a, status: 'failed' }, { exec_id: b, status: 'done' }, { exec_id: c, status: 'failed' }]
        .sort((x, y) => x.exec_id - y.exec_id));
      check('FIXTURE: the seeded statuses are still on disk with the daemon RUNNING (no tick rewrote them)',
        JSON.stringify(disk) === want,
        `disk=${JSON.stringify(disk)} seeded=${want}`);
    }

    // ── 1. TWO status filters over the real transport, each returning EXACTLY its own rows. ────
    for (const [status, want] of [['failed', [a, c].sort((x, y) => x - y)], ['done', [b]]]) {
      const r = await runCli(['--json', 'inspect', 'executions', '--status', status], cliEnv);
      const env2 = parseJson(r.stdout);
      const rows = (env2 && env2.result && env2.result.rows) || [];
      const got = rows.map((x) => x.exec_id).sort((x, y) => x - y);
      out(`--- inspect executions --status ${status} ---`, 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim().slice(0, 400));
      check(`\`ignite inspect executions --status ${status}\` exits 0 over the real transport`,
        r.code === 0, `exit=${r.code} stderr=${r.stderr.trim().slice(0, 200)}`);
      check(`it returns EXACTLY the ${want.length} ${status} row(s), by exec_id`,
        JSON.stringify(got) === JSON.stringify(want), `got=${JSON.stringify(got)} want=${JSON.stringify(want)}`);
      check(`every row it returned actually carries status '${status}'`,
        rows.length > 0 && rows.every((x) => x.status === status),
        `statuses=${JSON.stringify([...new Set(rows.map((x) => x.status))])}`);
    }

    // The discriminator a per-status check cannot make on its own: the two filters must DISAGREE.
    // A surface ignoring --status passes each filter's "exit 0" and fails only here.
    {
      const rf = parseJson((await runCli(['--json', 'inspect', 'executions', '--status', 'failed'], cliEnv)).stdout);
      const rs = parseJson((await runCli(['--json', 'inspect', 'executions', '--status', 'done'], cliEnv)).stdout);
      const fIds = ((rf.result || {}).rows || []).map((x) => x.exec_id);
      const sIds = ((rs.result || {}).rows || []).map((x) => x.exec_id);
      check('two different --status values return DISJOINT, NON-EMPTY sets through the CLI',
        fIds.length > 0 && sIds.length > 0 && fIds.every((id) => !sIds.includes(id)),
        `failed=${JSON.stringify(fIds)} done=${JSON.stringify(sIds)}`);
    }

    // ── 2. EMPTY RESULT — a VALID status with no rows. ─────────────────────────────────────────
    {
      const r = await runCli(['--json', 'inspect', 'executions', '--status', 'killed'], cliEnv);
      const e = parseJson(r.stdout);
      out('--- inspect executions --status killed (empty) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim().slice(0, 300));
      check('a valid status with NO rows exits 0 with an empty list — no rows is not a failure',
        r.code === 0 && e && e.ok === true && Array.isArray(e.result.rows) && e.result.rows.length === 0,
        `exit=${r.code} rows=${JSON.stringify(e && e.result && e.result.rows)}`);

      // The human-readable path, not just --json: an operator reading a blank screen cannot tell
      // success from a swallowed error.
      const h = await runCli(['inspect', 'executions', '--status', 'killed'], cliEnv);
      check('the rendered (non-json) empty result SAYS it is empty rather than printing nothing',
        h.code === 0 && /executions \(status killed\): 0 row\(s\)/.test(h.stdout),
        `exit=${h.code} stdout=${JSON.stringify(h.stdout.trim().slice(0, 160))}`);
    }

    // ── 3. EMPTY is NOT the same answer as INVALID — over the real transport. ──────────────────
    {
      const r = await runCli(['--json', 'inspect', 'executions', '--status', 'no-such-status'], cliEnv);
      out('--- inspect executions --status no-such-status ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim().slice(0, 300), 'STDERR=' + r.stderr.trim().slice(0, 300));
      const combined = r.stdout + r.stderr;
      check('an UNKNOWN status FAILS through the CLI (non-zero exit), never a silent empty list',
        r.code !== 0, `exit=${r.code}`);
      check('the failure NAMES the valid status set so the operator can self-correct',
        /launching/.test(combined) && /killed/.test(combined),
        `output=${JSON.stringify(combined.trim().slice(0, 220))}`);
    }

    // ── 4. --status is REQUIRED, and refused LOCALLY (no pointless round trip). ────────────────
    {
      const r = await runCli(['inspect', 'executions'], cliEnv);
      check('`inspect executions` with no --status fails, naming status',
        r.code !== 0 && /status/.test(r.stdout + r.stderr),
        `exit=${r.code} output=${JSON.stringify((r.stdout + r.stderr).trim().slice(0, 200))}`);
    }

    // ── 5. PAGING over the real transport — walkable to completion. ────────────────────────────
    {
      const expectFailed = [a, c].sort((x, y) => x - y);
      const p1 = parseJson((await runCli(['--json', 'inspect', 'executions', '--status', 'failed', '--offset', '0', '--limit', '1'], cliEnv)).stdout);
      check('--limit 1 returns ONE row and reports eof:false with a nextOffset (numeric args survive argv)',
        p1 && p1.ok === true && p1.result.rows.length === 1 && p1.result.eof === false && p1.result.nextOffset === 1,
        `result=${JSON.stringify(p1 && p1.result && { n: p1.result.rows.length, eof: p1.result.eof, next: p1.result.nextOffset })}`);

      // `total` is what makes the LAST page addressable — `eof` only says whether the page you
      // asked for was the last one, never where that page starts. --tail below jumps on it.
      check('a PAGE reports the total of the whole filtered set, not just of the page',
        p1 && p1.result.total === 2, `total=${p1 && p1.result.total} rows=${p1 && p1.result.rows.length}`);

      const p2 = parseJson((await runCli(['--json', 'inspect', 'executions', '--status', 'failed', '--offset', String(p1.result.nextOffset), '--limit', '1'], cliEnv)).stdout);
      const walked = p1.result.rows.concat(p2.result.rows).map((x) => x.exec_id).sort((x, y) => x - y);
      check('walking nextOffset through the CLI reaches every row exactly once and ends at eof:true',
        JSON.stringify(walked) === JSON.stringify(expectFailed) && p2.result.eof === true,
        `walked=${JSON.stringify(walked)} want=${JSON.stringify(expectFailed)} eof=${p2.result.eof}`);
    }

    // ── 5b. --tail N — the NEWEST rows in ONE command. The listing is oldest-first with no total,
    // so before this the newest row cost blind offset probes. The check that matters is that the
    // tail is the LAST row of the walk, not the first: a --tail that forgot to reverse-slice
    // passes "returns 1 row" and fails only here.
    {
      const newestFailed = Math.max(a, c);
      const r = await runCli(['--json', 'inspect', 'executions', '--status', 'failed', '--tail', '1'], cliEnv);
      const e = parseJson(r.stdout);
      out('--- inspect executions --status failed --tail 1 ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim().slice(0, 400));
      check('--tail 1 returns exactly the NEWEST row of the status, in one command',
        r.code === 0 && e && e.ok === true && e.result.rows.length === 1 && e.result.rows[0].exec_id === newestFailed,
        `got=${JSON.stringify(e && e.result && e.result.rows.map((x) => x.exec_id))} want=[${newestFailed}]`);
      check('--tail reports the TOTAL the paged envelope never carried (tailOf)',
        e && e.result && e.result.tailOf === 2 && e.result.eof === true,
        `tailOf=${e && e.result && e.result.tailOf} eof=${e && e.result && e.result.eof}`);

      const h = await runCli(['inspect', 'executions', '--status', 'failed', '--tail', '1'], cliEnv);
      check('the rendered --tail says which slice of what total it is showing',
        h.code === 0 && /executions \(status failed\): newest 1 of 2 row\(s\)/.test(h.stdout),
        `exit=${h.code} stdout=${JSON.stringify(h.stdout.trim().slice(0, 200))}`);

      // --tail names a window from the END, --offset/--limit one from the START: refused, never
      // silently honouring one of the two.
      const x = await runCli(['inspect', 'executions', '--status', 'failed', '--tail', '1', '--limit', '1'], cliEnv);
      check('--tail with --limit is REFUSED rather than silently honouring one of them',
        x.code !== 0 && /mutually exclusive/.test(x.stdout + x.stderr),
        `exit=${x.code} output=${JSON.stringify((x.stdout + x.stderr).trim().slice(0, 200))}`);

      // The oldest-first default is UNCHANGED — the flag adds a view, it does not flip the order
      // every existing caller (and check 5 above) reads.
      const d0 = parseJson((await runCli(['--json', 'inspect', 'executions', '--status', 'failed'], cliEnv)).stdout);
      const ids = ((d0.result || {}).rows || []).map((x2) => x2.exec_id);
      check('the DEFAULT listing is still oldest-first (no default was flipped)',
        JSON.stringify(ids) === JSON.stringify([a, c].sort((x2, y2) => x2 - y2)),
        `default=${JSON.stringify(ids)}`);
    }

    // ── 6. The target is DISCOVERABLE from the CLI's own help — a surface nobody can find is
    // not shipped, and this is the only layer where an operator would look.
    {
      const r = await runCli(['inspect'], cliEnv);
      check('`ignite inspect` with no target surfaces `executions` to the operator',
        /executions/.test(r.stdout + r.stderr),
        `output=${JSON.stringify((r.stdout + r.stderr).trim().slice(0, 240))}`);
    }
  } finally {
    await stopDaemon(d);
  }

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`checks: ${checks.length}  passed: ${checks.length - failed.length}  failed: ${failed.length}`);
  if (failed.length) for (const f of failed) out(`FAILED: ${f.name}`);
  out(failed.length
    ? `RESULT: FAIL — ${failed.length} check(s) above.`
    : 'RESULT: PASS — inspect executions filters, pages, refuses and stays discoverable through the real CLI binary over the real transport.');
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(1);
});

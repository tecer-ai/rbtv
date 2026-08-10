#!/usr/bin/env node
'use strict';

// probe-suite — discover, execute and COUNT every probe under ignite/.
//
// WHY THIS EXISTS (G-141): probes are self-contained scripts that write their own verdict into an
// adjacent `.out`. Nothing in this repo enumerated, executed or counted them, so a probe's death
// was visible only to whoever happened to run that one file by hand — and the `.out` (the evidence
// it once passed) is overwritten by the crash that kills it. Two probes were dead for seven days
// across two different commits and nothing said so.
//
// THE BAR THIS RUNNER IS BUILT AGAINST: "all probes passed" and "the runner never executed them"
// MUST NOT look alike. Three independent mechanisms, so no single failure hides an incomplete run:
//
//   1. A DENOMINATOR ESTABLISHED BEFORE ANY WORK. Discovery runs first and its count is written
//      into the summary header before the first probe is spawned. attempted < discovered is a
//      suite failure however many probes passed.
//   2. A DISTINCT EXIT CODE. 0 = green · 1 = a probe FAILED · 2 = the run was INCOMPLETE (nothing
//      discovered, nothing attempted, or attempted < discovered). Zero discovered is a REFUSAL,
//      never a vacuous green.
//   3. A COMPLETION TRAILER. `SUITE-COMPLETE` is written only after the last probe returns, so a
//      truncated run is detectable by a human reading the file with no exit code in hand
//      (`G-121`: a truncated run reads greener than a complete one).
//
// And the 7.50 bar — a probe can print PASS without having run: a probe that exits 0 but whose
// adjacent `.out` was NOT written inside its own [start, end] window is graded STALE, not PASS.
// Verdicts come from a live child-process exit, NEVER from the content of a committed `.out`.
//
// CAPTURES ARE UNTRACKED AND ALWAYS FRESH (G-171). A `.out` beside a probe is THIS run's output,
// with a real mtime. Preserve mode — which used to restore each capture's bytes AND its mtime
// after every run — is RETIRED: it fixed the churn (G-163) by freezing every tracked capture into
// a snapshot nothing would refresh, and rolled the mtime back too, so nothing on disk revealed it.
// `probe-error-map-drift.out` read "1 drift finding" while the live probe reported 15, and a seat
// read the file, took it for its own run's output, and reported the debt 15x too small.
// THE DETECTOR WAS NEVER FOOLED — grade() reads the pre-restore mtime — THE PERSON WAS, AND
// NOTHING ON DISK COULD TELL THEM. Each run is also archived under the summary's captures/ folder:
// untracked files carry no git history, so that archive is the only per-run record that survives.
//
// Usage:
//   node ignite/deploy/probe-suite.js [options]
//     --dir <rel>        limit to a probes directory (repeatable); default: every one discovered
//     --only <name>      run ONE probe (repeatable) — `probe-cli-status`, `cli-status`, or the
//                        filename. Prefer it over `node probe-x.js`: the run is counted, graded
//                        for staleness, and archived, which a bare invocation is not
//     --timeout-ms <n>   per-probe timeout (default 180000)
//     --summary <path>   summary file (default: <tmpdir>/rbtv-probe-suite/<stamp>.txt)
//     --list             discover and print, execute nothing (exit 0 if any found, 2 if none)
//     --json             machine-readable result on stdout
//     --selftest         run the runner's own fixtures and mutations; execute no real probe
//
// Placement note: `deploy/` already holds this repo's cross-cutting validation harnesses
// (p3-2-smoke.js, p3-2b-containment.js, p3-5-*) and already held `probe-suite.out`/`.log` — the
// orphaned output of the lost 2026-07-15 sweep. This restores a mechanism into its own footprint;
// it is NOT a new interim CLI home (owner CLI-placement ruling, 2026-07-26).
//
// `ignite/` rule 3 (no runtime state in the repo): the summary NEVER defaults into `ignite/deploy/`
// — that also stops a fresh run from destroying the 2026-07-15 record.
//
// ⚠ THE DEFAULT IS THE OS TEMP DIR, NOT `.rbtv/` (7.607 E3, review F5). It used to be
// `<workspace>/.rbtv/runtime/probe-suite/`, which put a WRITE into the goals workspace as the price
// of running a read-only check: every dispatch fenced against `.rbtv/**` — the normal posture while
// a live goal is executing — had to remember to pass `--summary` or silently breach its own fence.
// `os.tmpdir()` is the least surprising home for a per-invocation report nobody has ever cited by
// path: it needs no workspace, survives a read-only checkout, and is swept by the OS. A summary
// worth keeping is worth naming — pass `--summary <path>` and it is written verbatim.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const IGNITE_ROOT = path.resolve(__dirname, '..');
const DEFAULT_TIMEOUT_MS = 180000;

const EXIT_GREEN = 0;
const EXIT_FAILED = 1;
const EXIT_INCOMPLETE = 2;

// ---------------------------------------------------------------- discovery

// Walk for directories literally named `probes` and take their probe-* scripts. Discovery is by
// STRUCTURE, never a hardcoded list: the 2026-07-15 sweep listed 21 probes from 3 directories and
// read complete, because nothing in it carried a denominator to compare against.
function discoverProbes(root, only, probeOnly) {
  const found = [];
  const skip = new Set(['node_modules', '.git', 'lib', 'fixtures']);

  function walk(dir) {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (skip.has(e.name)) continue;
      const abs = path.join(dir, e.name);
      if (e.name === 'probes') collect(abs); else walk(abs);
    }
  }

  function collect(dir) {
    const rel = path.relative(root, dir).split(path.sep).join('/');
    if (only && only.length && !only.some((d) => rel === d || rel.startsWith(d + '/'))) return;
    for (const f of fs.readdirSync(dir).sort()) {
      if (!f.startsWith('probe-')) continue;
      const ext = path.extname(f);
      if (ext !== '.js' && ext !== '.py') continue;
      // `--only` exists so that running ONE probe still goes through this runner — it is then
      // counted, graded against the 7.50 staleness bar, and archived. (It was introduced under
      // G-163 to inherit preserve mode; preserve mode is gone, the reason to route through here
      // is not.)
      if (probeOnly && probeOnly.length
          && !probeOnly.some((n) => f === n || f.replace(/\.(js|py)$/, '') === n
                                 || f.replace(/^probe-/, '').replace(/\.(js|py)$/, '') === n)) continue;
      const abs = path.join(dir, f);
      found.push({
        id: rel + '/' + f,
        abs,
        lang: ext === '.py' ? 'py' : 'js',
        outPath: abs.slice(0, -ext.length) + '.out',
      });
    }
  }

  walk(root);
  found.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return found;
}

// ---------------------------------------------------------------- execution

// A result is evidence of execution ONLY if it carries a numeric exit or an explicit spawn error.
// `attempted` is counted from the RESULT, never from the fact that execute() was called — an
// executor that silently runs nothing must not be able to report a full attempt count.
// ⚠⚠ EVERY probe child runs TMUX-ISOLATED, unconditionally. The suite is routinely invoked from
// INSIDE a tmux pane (an agent session IS one), and a probe's throwaway-server teardown — a bare
// `tmux kill-server` in a finally block — binds through the inherited $TMUX to the DEFAULT server
// and kills every live session on the box, including the operator's own. That is not hypothetical:
// it crashed the driving session repeatedly on 2026-08-10, and d481e65 had already patched five
// probes ONE AT A TIME for the same class. Per-probe hygiene cannot hold a floor a NEW probe can
// break by default, so the runner holds it here instead: $TMUX/$TMUX_PANE are stripped and
// TMUX_TMPDIR is pointed at a per-run scratch dir, so any tmux command a probe runs — create,
// send-keys, kill-server — resolves to an isolated socket directory that no real session uses.
// Probes that manage their own isolation (a -L socket, their own TMUX_TMPDIR) still win: their
// child env overrides this one. A probe that GENUINELY needs the operator's real server does not
// exist today and must not be created — that need is a design smell, not a missing escape hatch.
// ⚠ THE SCRATCH IS ROOTED AT `os.tmpdir()`, NEVER AT `captureDir` — a UNIX socket path is capped
// at ~108 bytes (`sun_path`), and tmux appends `/tmux-<uid>/<socket-name>` to `$TMUX_TMPDIR`.
// Under the scheduled runner the capture dir is
// `<workspace>/.rbtv/runtime/probe-suite/<stamp>-captures/` — 89 bytes on the ignite VPS before
// tmux adds its own 37 for `/tmux-1000/probe-launcher-attribution`, i.e. 140 > 108. tmux answered
// "File name too long", and probe-planning-entry / probe-sensor-start / probe-launcher-attribution
// FAILED in SUITE context for a reason unrelated to what they measure — vacuous hourly coverage,
// while the same probes ran green by hand from the repo root (task 7.652). `/tmp/rbtv-tmux-XXXXXX`
// is 21 bytes, so the same worst case lands at 58 with ~50 to spare. Captures are NOT affected —
// they stay in `captureDir`; only the socket-bearing scratch moves.
let cachedIsolatedEnv = null;
function tmuxIsolatedEnv(opts) {
  if (!cachedIsolatedEnv) {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtv-tmux-'));
    // Nothing used to reap this dir (it rode inside captureDir); rooted in /tmp it must reap itself.
    process.on('exit', () => { try { fs.rmSync(scratch, { recursive: true, force: true }); } catch {} });
    const env = { ...process.env, TMUX_TMPDIR: scratch };
    delete env.TMUX;
    delete env.TMUX_PANE;
    cachedIsolatedEnv = env;
  }
  return cachedIsolatedEnv;
}

// ⚠ `python3` IS NOT AN INTERPRETER ON WINDOWS — IT IS USUALLY A LIE (task 7.700). Windows ships a
// Microsoft-Store app-execution alias at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` that is
// ON PATH, IS EXECUTABLE, AND RUNS NO PYTHON: it prints "Python was not found; run without
// arguments to install from the Microsoft Store" and exits non-zero (9009 from cmd, 49 from a
// POSIX shell). So every `.py` probe read RED-by-environment through this runner on the Windows
// desktop while the real interpreter sat on the same PATH as `python`.
// THE DETECTION MUST THEREFORE BE AN EXECUTION, NOT A LOOKUP. `where python3` finds the alias;
// `spawnSync` succeeds in spawning the alias; only its EXIT CODE plus its OUTPUT distinguish it
// from a real interpreter. Probed ONCE per process, in PATH order, first candidate that actually
// reports `Python <n>` on exit 0 wins.
// POSIX IS BYTE-UNCHANGED: `python3 --version` exits 0 saying `Python 3.x` there, so `python3` is
// still what every probe is spawned with. The `python` fallback is reachable only where `python3`
// does not exist or is the alias, and when NEITHER candidate runs we hand back `python3` so the
// failure a box without Python produces is the same one it produced before.
let cachedPython;
function pythonCmd() {
  if (cachedPython !== undefined) return cachedPython;
  cachedPython = null;
  for (const cmd of ['python3', 'python']) {
    const r = spawnSync(cmd, ['--version'], { encoding: 'utf8', timeout: 15000 });
    if (r.error || r.status !== 0) continue;
    if ([r.stdout, r.stderr].some((s) => /^Python \d/.test(String(s || '').trim()))) {
      cachedPython = cmd;
      break;
    }
  }
  return cachedPython;
}

function executeProbe(probe, opts) {
  const timeoutMs = opts.timeoutMs;
  const outBefore = statMtimeMs(probe.outPath);
  // ⚠ PRESERVE MODE IS RETIRED (G-171). It used to take each capture and its TIMESTAMPS hostage
  // before the run and put them back byte-identical after. That stopped the churn (G-163) and, in
  // the same stroke, froze every tracked capture into a snapshot no ordinary run would ever
  // refresh — while `fs.utimesSync` rolled the mtime back too, so nothing on disk revealed it.
  // `probe-error-map-drift.out` sat at "1 drift finding" while the live probe reported 15, and a
  // seat read the file, believed it was its own run's output, and reported a debt 15x too small.
  // The captures are no longer tracked (see .gitignore), so there is no churn left to prevent:
  // a run now simply refreshes the file beside its probe, with a real mtime.
  const startedAt = Date.now();

  const cmd = probe.lang === 'py' ? (pythonCmd() || 'python3') : process.execPath;
  const res = spawnSync(cmd, [probe.abs], {
    cwd: path.dirname(probe.abs),
    timeout: timeoutMs,
    encoding: 'utf8',
    maxBuffer: 8 * 1024 * 1024,
    env: tmuxIsolatedEnv(opts),
  });

  const endedAt = Date.now();
  const outAfter = statMtimeMs(probe.outPath);
  // The capture stays where the probe wrote it AND is archived per-run out of the repo. The
  // archive is deliberately KEPT after preserve mode's retirement: untracked captures carry no
  // git history, so without it a run leaves no comparable record at all — and a per-run archive
  // is the only reason G-171's three contradictory readings could be reconciled at all.
  const archived = archiveCapture(probe, opts.captureDir);

  // ⚠ STDOUT IS KEPT — it used to be dropped here while stderr was kept.
  //
  // ⚠⚠ AND THE REASON THIS MATTERS IS NOT THAT PROBES ARE SILENT. Writing nothing to either stream
  // is the CONTRACT this file's own header states (G-141): a probe writes its verdict into an
  // adjacent capture. 59 of the 94 do exactly that and nothing else, and that is correct. The
  // defect was that on the FAILURE path the runner named nowhere: `grade()` returned FAIL with NO
  // capture reference, so a red probe was undiagnosable EVEN THOUGH ITS DIAGNOSIS WAS ALREADY
  // WRITTEN TO DISK, one directory away, by the run that just failed. The runner did not fail to
  // make probes speak; it failed to say where they had spoken. (The 35 that DO print were losing
  // that too, which is what this line fixes.)
  const common = { attempted: true, wallMs: endedAt - startedAt, startedAt, endedAt,
    outBefore, outAfter, archived, stderr: tail(res.stderr), stdout: tail(res.stdout) };

  if (res.error && res.error.code === 'ETIMEDOUT') return Object.assign(common, { timedOut: true });
  if (res.error) return Object.assign(common, { spawnError: String(res.error.message) });
  return Object.assign(common, {
    exit: res.status === null ? null : res.status,
    signal: res.signal || null,
  });
}

function statMtimeMs(p) {
  try { return fs.statSync(p).mtimeMs; } catch { return null; }
}

// Copy this run's capture into the summary's own captures/ folder, outside the repo (ignite rule
// 3). PURELY ADDITIVE: the probe's capture is left exactly where the probe wrote it, untouched in
// content and in mtime. Nothing here reads, rewrites or reverts the working tree — that reversion
// WAS G-171, and its absence is the fix.
function archiveCapture(probe, captureDir) {
  if (!captureDir) return null;
  let fresh = null;
  try { fresh = fs.readFileSync(probe.outPath); } catch { return 'none'; }
  const dest = path.join(captureDir, probe.id.replace(/[\\/]/g, '__'));
  try {
    fs.mkdirSync(captureDir, { recursive: true });
    fs.writeFileSync(dest, fresh);
    return 'archived';
  } catch (e) { return 'ARCHIVE-FAILED: ' + String(e && e.message || e); }
}

function tail(s, n = 400) {
  if (!s) return '';
  const t = String(s).trim();
  return t.length <= n ? t : '…' + t.slice(-n);
}

// ---------------------------------------------------------------- grading

// Grade from the LIVE run only. A committed `.out` is never read for its content — a probe that
// prints PASS without having run (task 7.50) is exactly what that would launder.
function grade(probe, r) {
  if (!r || r.attempted !== true) return { verdict: 'NOT-ATTEMPTED', ok: false, counted: false };
  if (r.timedOut) return { verdict: 'TIMEOUT', ok: false, counted: true };
  if (r.spawnError) return { verdict: 'CRASH', ok: false, counted: true };
  if (typeof r.exit !== 'number') return { verdict: 'NOT-ATTEMPTED', ok: false, counted: false };
  if (r.exit !== 0) return { verdict: 'FAIL', ok: false, counted: true };

  // exit 0. Execution evidence: if this probe writes a capture, it must have been written inside
  // this probe's own [start, end] window. A stale capture beside a green exit is NOT a pass.
  const writesCapture = r.outBefore !== null || r.outAfter !== null;
  if (!writesCapture) return { verdict: 'PASS', ok: true, counted: true, capture: 'none' };

  const fresh = r.outAfter !== null && r.outAfter >= r.startedAt - 1000 && r.outAfter <= r.endedAt + 1000;
  if (!fresh) return { verdict: 'STALE', ok: false, counted: true, capture: 'stale' };
  return { verdict: 'PASS', ok: true, counted: true, capture: 'fresh' };
}

// ⚠⚠ DIAGNOSTIC ONLY — NEVER GRADING, AND THE SEPARATION IS THE WHOLE DESIGN.
// The verdict is already decided above from the LIVE exit code, and S10 proves a capture claiming
// PASS cannot make a failing probe pass. This function runs AFTER that decision and changes
// nothing about it; it exists because a reader facing `exit=1` had nothing else to go on.
//
// ⚠ FRESHNESS IS STATED EVERY TIME (G-171). A capture beside a probe may predate this run. A seat
// once read `probe-error-map-drift.out`, took it for its own run's output and reported a debt 15x
// too small — with nothing on disk able to reveal it. So lines this run did not write are LABELLED
// as not-this-run rather than quoted as evidence of this failure. Quoting them silently would
// rebuild G-171 inside the mechanism meant to make failures readable.
function diagnose(probe, r) {
  if (!r) return [];
  const lines = [];
  const push = (what, body) => {
    const t = String(body || '').trim();
    if (t) lines.push(`      ${what}:`, ...t.split('\n').slice(-12).map((l) => '        ' + l));
  };
  push('stdout', r.stdout);
  push('stderr', r.stderr);
  const wroteThisRun = r.outAfter !== null && r.outAfter !== r.outBefore;
  let body = null;
  try { body = fs.readFileSync(probe.outPath, 'utf8'); } catch { body = null; }
  if (body === null) {
    if (!lines.length) lines.push('      (no stdout, no stderr, and no capture beside the probe)');
    return lines;
  }
  // ⚠ ANCHORED AT LINE START, and that is not tidiness. Unanchored, this matched PASS lines
  // whose TEXT contains a failure word — `PASS  a SESSION status is REFUSED on a turn row`
  // in probe-session-turn-split — and the diagnostic filled with passing rows at the moment
  // a reader most needs the failing ones. Same shape as a grader keying on a token that its
  // own green control prints: assert the PROPERTY (this line reports a failure), never the
  // VOCABULARY (this line contains a word). Every probe here writes its verdict FIRST.
  const marked = body.split('\n').filter((l) => /^\s*(FAIL|FAILED|ERROR|REFUSED)\b/.test(l));
  const shown = (marked.length ? marked : body.trim().split('\n').slice(-8));
  lines.push(`      capture ${probe.outPath}${wroteThisRun
    ? ' (written by THIS run)'
    : ' ⚠ NOT written by this run — the lines below are from an EARLIER run, not this failure'}:`);
  for (const l of shown.slice(0, 12)) lines.push('        ' + l);
  return lines;
}

// ---------------------------------------------------------------- the suite

function runSuite(opts) {
  const root = opts.root || IGNITE_ROOT;
  const discover = opts.discover || ((r) => discoverProbes(r, opts.only, opts.probeOnly));
  const execute = opts.execute || executeProbe;
  const timeoutMs = opts.timeoutMs || DEFAULT_TIMEOUT_MS;
  const emit = opts.emit || (() => {});

  const probes = discover(root) || [];
  const discovered = probes.length;

  // THE DENOMINATOR IS COMMITTED BEFORE ANY WORK. Everything after this line is measured against
  // a number written down before the first spawn.
  const header = [
    'probe-suite',
    'generated: ' + new Date().toISOString(),
    'root: ' + root,
    'discovered: ' + discovered,
    'timeout-ms: ' + timeoutMs,
    'selection: ' + [(opts.only && opts.only.length ? 'dirs=' + opts.only.join(',') : ''),
                     (opts.probeOnly && opts.probeOnly.length ? 'probes=' + opts.probeOnly.join(',') : '')]
                    .filter(Boolean).join(' ') || 'all',
    '--- results (appended as each probe returns) ---',
  ].join('\n') + '\n';
  emit(header);

  if (discovered === 0) {
    // Zero discovered is a REFUSAL. A suite that ran nothing must never read like a suite that
    // found nothing wrong — this is the exact case the leader's bar names.
    const reason = 'no probes discovered under ' + root + (opts.only && opts.only.length
      ? ' matching selection ' + opts.only.join(',') : '');
    emit('REFUSED: ' + reason + '\n');
    return finish({ discovered, rows: [], reason, opts, emit });
  }

  const rows = [];
  const refreshed = [];
  const archiveFailures = [];
  for (const p of probes) {
    let r;
    try { r = execute(p, { timeoutMs, captureDir: opts.captureDir }); }
    catch (e) { r = { attempted: true, spawnError: String(e && e.message || e) }; }
    const g = grade(p, r);
    const row = {
      id: p.id, verdict: g.verdict, ok: g.ok, counted: g.counted,
      exit: r && typeof r.exit === 'number' ? r.exit : null,
      wallMs: r && r.wallMs != null ? r.wallMs : null,
      capture: g.capture || null,
      stderr: r && r.stderr ? r.stderr : '',
      stdout: r && r.stdout ? r.stdout : '',
    };
    // A failing row now carries WHAT THE PROBE SAID, in the machine-readable output as well as
    // the summary — a consumer reading --json had exactly the same nothing a human did.
    row.diagnostic = g.ok ? [] : diagnose(p, r);
    rows.push(row);
    if (r && r.outAfter !== null && r.outAfter !== r.outBefore) refreshed.push(p.outPath);
    if (r && typeof r.archived === 'string' && r.archived.startsWith('ARCHIVE-FAILED')) {
      archiveFailures.push(p.outPath + ' — ' + r.archived);
    }
    emit(`${row.id} ${row.verdict} exit=${row.exit === null ? '-' : row.exit}`
      + ` wall_ms=${row.wallMs === null ? '-' : row.wallMs}`
      + (row.capture ? ` capture=${row.capture}` : '') + '\n');
    for (const l of row.diagnostic) emit(l + '\n');
    if (opts.onRow) opts.onRow(row);
  }

  return finish({ discovered, rows, refreshed, archiveFailures, opts, emit });
}

function finish({ discovered, rows, refreshed = [], archiveFailures = [], reason, opts, emit }) {
  const attempted = rows.filter((r) => r.counted).length;
  const passed = rows.filter((r) => r.ok).length;
  const failed = attempted - passed;
  const incomplete = discovered === 0 || attempted === 0 || attempted < discovered;

  let verdict;
  let exitCode;
  if (incomplete) { verdict = 'INCOMPLETE'; exitCode = EXIT_INCOMPLETE; }
  else if (failed > 0) { verdict = 'RED'; exitCode = EXIT_FAILED; }
  else { verdict = 'GREEN'; exitCode = EXIT_GREEN; }

  const trailer = [
    '--- accounting ---',
    'discovered: ' + discovered,
    'attempted: ' + attempted,
    'passed: ' + passed,
    'failed: ' + failed,
    'not-attempted: ' + (discovered - attempted),
    // Named `captures-refreshed`, and it is now the HEALTHY reading. Under preserve mode this
    // line reported "written then restored ... working tree unchanged", which was true and read
    // as reassurance while the file beside each probe silently went stale (G-171).
    'captures-refreshed: ' + refreshed.length,
    'archive-failures: ' + archiveFailures.length,
    // Written LAST and only here. Header without this line == a truncated run, readable with no
    // exit code in hand.
    `SUITE-COMPLETE verdict=${verdict} exit=${exitCode}`,
    '',
  ].join('\n');
  emit(trailer);

  return { verdict, exitCode, discovered, attempted, passed, failed,
    notAttempted: discovered - attempted, rows, refreshed, archiveFailures,
    reason: reason || null };
}

// ---------------------------------------------------------------- selftest

// Every bar below is proven by RUNNING a fixture or an injected mutation. Two of this seat's own
// checks were once theatre because their fixtures could not distinguish the bar from its own
// failure mode — so S8 exists specifically to prove the STALE fixture discriminates.
function selftest() {
  const results = [];
  const t = (name, fn) => {
    try { fn(); results.push([true, name, '']); }
    catch (e) { results.push([false, name, String(e && e.message || e)]); }
  };
  const eq = (got, want, what) => {
    if (got !== want) throw new Error(`${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
  };

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-suite-selftest-'));
  const dir = path.join(tmp, 'mod', 'probes');
  fs.mkdirSync(dir, { recursive: true });

  const write = (name, body) => fs.writeFileSync(path.join(dir, name), body);
  const capture = (n) => `const fs=require('fs'),p=require('path');`
    + `fs.writeFileSync(p.join(__dirname,'${n}.out'),'PASS ${n}\\n');`;

  write('probe-ok.js', capture('probe-ok') + 'process.exit(0);');
  write('probe-bad.js', capture('probe-bad') + 'process.exit(1);');
  write('probe-crash.js', 'throw new Error("boom");');
  write('probe-hang.js', 'setTimeout(()=>{}, 60000);');
  // STALE: a committed capture already saying PASS, and a probe that exits 0 without touching it.
  write('probe-stale.js', 'process.exit(0);');
  fs.writeFileSync(path.join(dir, 'probe-stale.out'), 'PASS probe-stale (written days ago)\n');
  fs.utimesSync(path.join(dir, 'probe-stale.out'), new Date(Date.now() - 7 * 86400000), new Date(Date.now() - 7 * 86400000));
  write('probe-nocapture.js', 'process.exit(0);');

  const run = (o = {}) => runSuite(Object.assign({ root: tmp, timeoutMs: 4000 }, o));

  let full;
  t('S1 discovery finds every probe by structure (6), not by a list', () => {
    const found = discoverProbes(tmp);
    eq(found.length, 6, 'discovered');
  });

  t('S2 each fixture earns its own verdict', () => {
    full = run();
    const by = Object.fromEntries(full.rows.map((r) => [r.id.split('/').pop(), r.verdict]));
    eq(by['probe-ok.js'], 'PASS', 'ok');
    eq(by['probe-bad.js'], 'FAIL', 'bad');
    eq(by['probe-crash.js'], 'FAIL', 'crash');       // node exits 1 on an uncaught throw
    eq(by['probe-hang.js'], 'TIMEOUT', 'hang');
    eq(by['probe-stale.js'], 'STALE', 'stale');
    eq(by['probe-nocapture.js'], 'PASS', 'nocapture');
  });

  t('S3 a run with failures exits 1 — RED, not incomplete', () => {
    eq(full.exitCode, EXIT_FAILED, 'exitCode');
    eq(full.verdict, 'RED', 'verdict');
    eq(full.attempted, 6, 'attempted');
    eq(full.discovered, 6, 'discovered');
  });

  t('S4 an all-passing selection exits 0 and writes SUITE-COMPLETE', () => {
    let buf = '';
    const r = run({
      discover: (root) => discoverProbes(root).filter((p) => /probe-(ok|nocapture)\.js$/.test(p.id)),
      emit: (s) => { buf += s; },
    });
    eq(r.exitCode, EXIT_GREEN, 'exitCode');
    eq(r.verdict, 'GREEN', 'verdict');
    if (!/SUITE-COMPLETE verdict=GREEN/.test(buf)) throw new Error('trailer missing from summary');
    if (!/^discovered: 2$/m.test(buf)) throw new Error('header denominator missing');
  });

  // ---- MUTATIONS: the bar must FAIL on the broken mechanism, not merely pass on the good one ----

  t('M1 discovery returns nothing -> exit 2 REFUSED, never a vacuous green', () => {
    let buf = '';
    const r = run({ discover: () => [], emit: (s) => { buf += s; } });
    eq(r.exitCode, EXIT_INCOMPLETE, 'exitCode');
    eq(r.verdict, 'INCOMPLETE', 'verdict');
    if (!/^REFUSED:/m.test(buf)) throw new Error('zero discovered did not refuse out loud');
    if (/SUITE-COMPLETE verdict=GREEN/.test(buf)) throw new Error('reported green having run nothing');
  });

  t('M2 executor never spawns -> attempted 0 against discovered 6 -> exit 2', () => {
    const r = run({ execute: () => ({}) });   // a result carrying no execution evidence
    eq(r.discovered, 6, 'discovered');
    eq(r.attempted, 0, 'attempted');
    eq(r.exitCode, EXIT_INCOMPLETE, 'exitCode');
    if (r.exitCode === EXIT_FAILED) throw new Error('an unexecuted suite reported as a failing suite');
  });

  t('M2b executor runs only part of the set -> attempted < discovered -> exit 2', () => {
    let n = 0;
    const r = run({ execute: (p, o) => (n++ < 2 ? executeProbe(p, o) : ({})) });
    eq(r.attempted, 2, 'attempted');
    eq(r.discovered, 6, 'discovered');
    eq(r.exitCode, EXIT_INCOMPLETE, 'exitCode');
  });

  t('M3 a probe that exits 0 without refreshing its capture is not a PASS', () => {
    const r = run({ discover: (root) => discoverProbes(root).filter((p) => /probe-stale\.js$/.test(p.id)) });
    eq(r.rows[0].verdict, 'STALE', 'verdict');
    eq(r.passed, 0, 'passed');
    if (r.exitCode === EXIT_GREEN) throw new Error('a stale capture passed the suite');
  });

  t('M4 a truncated run leaves the header and NO SUITE-COMPLETE', () => {
    let buf = '';
    let n = 0;
    try {
      run({
        emit: (s) => { buf += s; },
        onRow: () => { if (++n === 2) throw new Error('killed mid-suite'); },
      });
    } catch { /* the kill */ }
    if (!/^discovered: 6$/m.test(buf)) throw new Error('header denominator missing');
    if (/SUITE-COMPLETE/.test(buf)) throw new Error('a truncated run wrote the completion trailer');
  });

  t('S8 FIXTURE DISCRIMINATES: the same probe rewriting its capture flips STALE -> PASS', () => {
    // Without this, S2/M3 would pass even if the stale check were checking nothing: they would be
    // distinguishing a probe that fails from a probe that passes, not a fresh capture from an old
    // one. Same script, same exit code, one line of difference.
    write('probe-stale.js', capture('probe-stale') + 'process.exit(0);');
    const r = run({ discover: (root) => discoverProbes(root).filter((p) => /probe-stale\.js$/.test(p.id)) });
    eq(r.rows[0].verdict, 'PASS', 'verdict after the probe starts writing its capture');
    eq(r.rows[0].capture, 'fresh', 'capture');
    write('probe-stale.js', 'process.exit(0);');   // restore
  });

  // ---- CAPTURES: a run must REFRESH the file beside its probe, and say so ----------------

  t('P1 a run REFRESHES the capture in place — mtime ADVANCES and content CHANGES (G-171)', () => {
    // THE DISCRIMINATOR preserve mode could never have passed: it restored both halves. This is
    // the exact A/B whose absence let `probe-error-map-drift.out` sit 15 findings behind reality
    // while a reader took it for their own run's output.
    const capDir = path.join(tmp, 'caps');
    const target = path.join(dir, 'probe-ok.out');
    fs.writeFileSync(target, 'STALE CAPTURE FROM A RUN LONG AGO\n');
    const old = new Date(Date.now() - 9 * 86400000);
    fs.utimesSync(target, old, old);
    const before = fs.readFileSync(target);
    const beforeMtime = fs.statSync(target).mtimeMs;

    const r = run({ captureDir: capDir,
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });

    eq(r.rows[0].verdict, 'PASS', 'verdict');
    if (fs.readFileSync(target).equals(before)) throw new Error('the stale capture SURVIVED the run — preserve mode is back');
    if (!(fs.statSync(target).mtimeMs > beforeMtime)) throw new Error('mtime did not advance — a reader cannot tell this file is current');
    if (!/PASS probe-ok/.test(fs.readFileSync(target, 'utf8'))) throw new Error('the capture does not hold this run output');
    eq(r.refreshed.length, 1, 'refreshed count');
  });

  t('P2 the fresh capture is ALSO archived out of the repo, byte-identical to what is on disk', () => {
    // Untracked captures carry no git history, so this archive is the only per-run record left.
    const capDir = path.join(tmp, 'caps-archive');
    const target = path.join(dir, 'probe-ok.out');
    fs.rmSync(target, { force: true });
    run({ captureDir: capDir,
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });
    const side = fs.readFileSync(path.join(capDir, 'mod__probes__probe-ok.js'));
    if (!side.equals(fs.readFileSync(target))) throw new Error('the archive does not match the capture the probe wrote');
  });

  t('P3 a capture the probe newly created is LEFT IN PLACE — nothing is reverted or removed', () => {
    // Preserve mode DELETED such a file ('removed-new') to keep the tree pristine. Now the tree is
    // where the evidence lives, so removing it would be destroying this run's only local record.
    const target = path.join(dir, 'probe-ok.out');
    fs.rmSync(target, { force: true });
    run({ captureDir: path.join(tmp, 'caps2'),
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });
    if (!fs.existsSync(target)) throw new Error('the capture the probe wrote was removed');
  });

  t('P4 --only selects ONE probe by any of its three spellings, and 0 matches REFUSES', () => {
    for (const spelling of ['probe-ok.js', 'probe-ok', 'ok']) {
      const found = discoverProbes(tmp, null, [spelling]);
      eq(found.length, 1, 'matches for ' + spelling);
      eq(found[0].id.endsWith('probe-ok.js'), true, 'picked for ' + spelling);
    }
    // A name that matches nothing must not quietly run the whole suite, and must not read green.
    const r = run({ probeOnly: ['no-such-probe'] });
    eq(r.discovered, 0, 'discovered');
    eq(r.exitCode, EXIT_INCOMPLETE, 'exitCode');
  });

  t('S9 the three outcomes carry three DIFFERENT exit codes', () => {
    const codes = new Set([EXIT_GREEN, EXIT_FAILED, EXIT_INCOMPLETE]);
    eq(codes.size, 3, 'distinct exit codes');
    const green = run({ discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });
    const red = run({ discover: (root) => discoverProbes(root).filter((p) => /probe-bad\.js$/.test(p.id)) });
    const inc = run({ discover: () => [] });
    eq(green.exitCode, EXIT_GREEN, 'green');
    eq(red.exitCode, EXIT_FAILED, 'red');
    eq(inc.exitCode, EXIT_INCOMPLETE, 'incomplete');
  });

  t('S10 verdicts never come from the content of a committed .out', () => {
    // probe-bad writes "PASS probe-bad" into its capture and exits 1. If grading ever read the
    // file, this would be a PASS. The capture it wrote now simply survives the run (preserve mode
    // used to restore it away, which is why this bar had to opt out of the default).
    const r = run({
      discover: (root) => discoverProbes(root).filter((p) => /probe-bad\.js$/.test(p.id)) });
    eq(r.rows[0].verdict, 'FAIL', 'verdict');
    const body = fs.readFileSync(path.join(dir, 'probe-bad.out'), 'utf8');
    if (!/PASS/.test(body)) throw new Error('fixture broken: capture should claim PASS');
  });

  // ---- the diagnostic's fixtures, in their OWN root ----
  // ⚠ A SEPARATE ROOT ON PURPOSE. Written into `dir` above, these three files moved the fixture
  // count from 6 to 9 and turned S1, S3, M2, M2b and M4 red — rows whose subject is precisely that
  // a denominator is established independently of the work. Adding a fixture to a directory
  // something COUNTS is a change to that count, and the tests that caught it were right to.
  const tmp2 = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-suite-diag-'));
  const dir2 = path.join(tmp2, 'mod', 'probes');
  fs.mkdirSync(dir2, { recursive: true });
  const write2 = (name, body) => fs.writeFileSync(path.join(dir2, name), body);
  const run2 = (re) => runSuite({ root: tmp2, timeoutMs: 4000,
    discover: (root) => discoverProbes(root).filter((p) => re.test(p.id)) });

  // The SILENT-STREAM shape, which is 59 of this repo's 94 probes: the verdict goes into the
  // capture and nothing at all is printed.
  write2('probe-diag.js',
    `const fs=require('fs'),p=require('path');`
    + `fs.writeFileSync(p.join(__dirname,'probe-diag.out'),`
    + `'PASS  something fine\\nFAIL  the fixture is not what this probe needs\\n');`
    + 'process.exit(1);');
  // Fails WITHOUT touching its capture, so a diagnostic that quoted it would be quoting an
  // earlier run's lines as though they were this failure's.
  write2('probe-diagstale.js', 'process.exit(1);');
  fs.writeFileSync(path.join(dir2, 'probe-diagstale.out'),
    'FAIL  a line from an EARLIER run, days ago\n');
  fs.utimesSync(path.join(dir2, 'probe-diagstale.out'),
    new Date(Date.now() - 7 * 86400000), new Date(Date.now() - 7 * 86400000));
  write2('probe-diagout.js', 'console.log("spoken on stdout, not in any capture");process.exit(1);');
  // A capture whose PASSING line contains a failure WORD — the shape that flooded the
  // diagnostic with green rows before the marker was anchored to line start.
  write2('probe-diagword.js',
    `const fs=require('fs'),p=require('path');`
    + `fs.writeFileSync(p.join(__dirname,'probe-diagword.out'),`
    + `'PASS  a bad status is REFUSED on this path\\nFAIL  the real failure\\n');`
    + 'process.exit(1);');
  // Claims PASS in its capture and exits 1 — S14's subject.
  write2('probe-diagliar.js',
    `const fs=require('fs'),p=require('path');`
    + `fs.writeFileSync(p.join(__dirname,'probe-diagliar.out'),'PASS  all good here\\n');`
    + 'process.exit(1);');

  t('S11 a FAILING probe reports what the probe itself SAID — its capture path and its failing '
    + 'lines. 59 of this repo\'s 94 probes print nothing on either stream, so a red row was '
    + '`exit=1` and nothing else: undiagnosable unless you already knew to go and read a file',
    () => {
      const r = run2(/probe-diag\.js$/);
      eq(r.rows[0].verdict, 'FAIL', 'verdict');
      const d = r.rows[0].diagnostic.join('\n');
      if (!/the fixture is not what this probe needs/.test(d)) {
        throw new Error('the probe\'s own FAIL line is missing from the diagnostic');
      }
      if (!/written by THIS run/.test(d)) throw new Error('freshness not stated');
    });

  t('S12 ⚠ a failing probe whose capture this run did NOT write is LABELLED as such — quoting an '
    + 'earlier run\'s lines as this failure\'s evidence would rebuild G-171 inside the mechanism '
    + 'that exists to make failures readable', () => {
      const r = run2(/probe-diagstale\.js$/);
      eq(r.rows[0].verdict, 'FAIL', 'verdict');
      const d = r.rows[0].diagnostic.join('\n');
      if (!/NOT written by this run/.test(d)) {
        throw new Error('a stale capture was quoted as this run\'s output');
      }
      if (!/an EARLIER run/.test(d)) {
        throw new Error('fixture broken: the stale line should still be SHOWN, labelled');
      }
    });

  t('S13 stdout is REPORTED rather than discarded — the runner kept stderr and threw stdout away, '
    + 'so even a probe that did speak was silenced by its own runner', () => {
      if (!/spoken on stdout/.test(run2(/probe-diagout\.js$/).rows[0].diagnostic.join('\n'))) {
        throw new Error('stdout missing from the diagnostic');
      }
    });

  t('S14 ⚠ the diagnostic NEVER grades. Its capture claims PASS and the probe exits 1: the verdict '
    + 'stays FAIL and the claim is still QUOTED, because S10\'s guarantee now has to hold across '
    + 'new code that deliberately READS that file', () => {
      const r = run2(/probe-diagliar\.js$/);
      eq(r.rows[0].verdict, 'FAIL', 'verdict');
      eq(r.exitCode, EXIT_FAILED, 'suite exit');
      if (!/all good here/.test(r.rows[0].diagnostic.join('\n'))) {
        throw new Error('fixture broken: the capture\'s PASS claim should be shown');
      }
    });

  t('S15 ⚠ the failure marker is ANCHORED — a PASSING line that merely CONTAINS a failure word '
    + 'is not selected. Unanchored it matched `PASS  a SESSION status is REFUSED ...` and filled '
    + 'the diagnostic with green rows exactly when a reader needed the red ones: a check keying on '
    + 'a token its own passing output prints', () => {
      const d = run2(/probe-diagword\.js$/).rows[0].diagnostic.join('\n');
      if (!/the real failure/.test(d)) throw new Error('the genuine FAIL line is missing');
      if (/a bad status is REFUSED/.test(d)) {
        throw new Error('a PASS line containing a failure word was selected as a failure');
      }
    });

  t('S16 ⚠ the resolved python interpreter EXECUTES python — the Windows MS-Store alias for '
    + '`python3` is on PATH and spawns fine while running nothing, so a lookup-based check passes '
    + 'on the exact box where every .py probe reds by environment (7.700)', () => {
      const cmd = pythonCmd();
      if (cmd === null) return;   // no python on this box at all — nothing to resolve, nothing to assert
      const r = spawnSync(cmd, ['-c', 'print("live")'], { encoding: 'utf8', timeout: 15000 });
      if (r.error || r.status !== 0 || !/live/.test(String(r.stdout || ''))) {
        throw new Error(`resolved '${cmd}' does not run python: status=${r.status} `
          + `stdout=${JSON.stringify(tail(r.stdout, 120))} stderr=${JSON.stringify(tail(r.stderr, 120))}`);
      }
    });

  fs.rmSync(tmp2, { recursive: true, force: true });
  fs.rmSync(tmp, { recursive: true, force: true });

  const failures = results.filter((r) => !r[0]);
  for (const [ok, name, err] of results) console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${err ? ' — ' + err : ''}`);
  console.log(`\nprobe-suite selftest: ${results.length - failures.length}/${results.length} passed`);
  return failures.length === 0 ? 0 : 1;
}

// ---------------------------------------------------------------- cli

function defaultSummaryPath() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(os.tmpdir(), 'rbtv-probe-suite', `${stamp}.txt`);
}

function main(argv) {
  const opts = { only: [], probeOnly: [], timeoutMs: DEFAULT_TIMEOUT_MS };
  let json = false; let list = false; let summaryPath = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--selftest') return selftest();
    else if (a === '--dir') opts.only.push(argv[++i]);
    else if (a === '--only') opts.probeOnly.push(argv[++i]);
    else if (a === '--timeout-ms') opts.timeoutMs = Number(argv[++i]);
    else if (a === '--summary') summaryPath = argv[++i];
    else if (a === '--json') json = true;
    else if (a === '--list') list = true;
    else if (a === '-h' || a === '--help') {
      console.log(fs.readFileSync(__filename, 'utf8').split('\n')
        .filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
      return 0;
    } else { console.error('unknown option: ' + a); return EXIT_INCOMPLETE; }
  }

  if (list) {
    const found = discoverProbes(IGNITE_ROOT, opts.only, opts.probeOnly);
    for (const p of found) console.log(p.id);
    console.log(`\ndiscovered: ${found.length}`);
    return found.length ? EXIT_GREEN : EXIT_INCOMPLETE;
  }

  const out = summaryPath || defaultSummaryPath();
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, '');
  const captureDir = out.replace(/\.[^.]*$/, '') + '-captures';
  const emit = (s) => { fs.appendFileSync(out, s); if (!json) process.stdout.write(s); };

  const r = runSuite(Object.assign({}, opts, { emit, captureDir }));

  if (json) console.log(JSON.stringify(r, null, 2));
  else {
    console.log(`\nsummary: ${out}`);
    console.log(`${r.refreshed.length} capture(s) refreshed in place beside their probes`
      + ` (untracked since G-171 — the file next to a probe is now THIS run's output, not a`
      + ` frozen snapshot); archived per-run in ${captureDir}`);
    if (r.archiveFailures.length) {
      console.log('⚠ ARCHIVE FAILED — this run leaves no durable record for these probes:');
      for (const f of r.archiveFailures) console.log('  ' + f);
    }
  }
  return r.exitCode;
}

if (require.main === module) process.exit(main(process.argv.slice(2)));

module.exports = { discoverProbes, executeProbe, grade, runSuite, selftest,
  EXIT_GREEN, EXIT_FAILED, EXIT_INCOMPLETE };

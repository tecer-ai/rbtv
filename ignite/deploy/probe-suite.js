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
// Usage:
//   node ignite/deploy/probe-suite.js [options]
//     --dir <rel>        limit to a probes directory (repeatable); default: every one discovered
//     --only <name>      run ONE probe (repeatable) — `probe-cli-status`, `cli-status`, or the
//                        filename. Use this instead of `node probe-x.js`: it keeps preserve mode,
//                        so running a single probe stops dirtying its tracked capture (G-163)
//     --timeout-ms <n>   per-probe timeout (default 180000)
//     --summary <path>   summary file (default: <workspace>/.rbtv/runtime/probe-suite/<stamp>.txt)
//     --list             discover and print, execute nothing (exit 0 if any found, 2 if none)
//     --json             machine-readable result on stdout
//     --selftest         run the runner's own fixtures and mutations; execute no real probe
//
// Placement note: `deploy/` already holds this repo's cross-cutting validation harnesses
// (p3-2-smoke.js, p3-2b-containment.js, p3-5-*) and already held `probe-suite.out`/`.log` — the
// orphaned output of the lost 2026-07-15 sweep. This restores a mechanism into its own footprint;
// it is NOT a new interim CLI home (owner CLI-placement ruling, 2026-07-26).
//
// `ignite/` rule 3 (no runtime state in the repo): the summary defaults to the workspace `.rbtv/`
// runtime root, never into `ignite/deploy/`. That also stops a fresh run from destroying the
// 2026-07-15 record.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const IGNITE_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(IGNITE_ROOT, '..');
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
      // G-163: `--only` exists so that running ONE probe still goes through this runner, and so
      // inherits preserve mode. Running a probe by hand is what dirties tracked captures — making
      // the runner the way to run a single probe fixes that without touching 84 probe files.
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
function executeProbe(probe, opts) {
  const timeoutMs = opts.timeoutMs;
  const outBefore = statMtimeMs(probe.outPath);
  // PRESERVE MODE (default): take the probe's capture and its timestamps hostage before the run,
  // and put them back byte-identical after — the fresh output is kept in the summary's own
  // captures/ folder instead. A census that must mutate ~80 committed files to tell you a number
  // is a census nobody runs, which is exactly how this suite rotted (G-141). Regeneration is still
  // available, but it is now a deliberate act (--write-captures), not the default.
  const preserve = opts.preserve !== false;
  const original = preserve ? readCapture(probe.outPath) : null;
  const startedAt = Date.now();

  const cmd = probe.lang === 'py' ? 'python3' : process.execPath;
  const res = spawnSync(cmd, [probe.abs], {
    cwd: path.dirname(probe.abs),
    timeout: timeoutMs,
    encoding: 'utf8',
    maxBuffer: 8 * 1024 * 1024,
    env: process.env,
  });

  const endedAt = Date.now();
  // Read the freshness evidence BEFORE any restore — the grader must see what the probe actually
  // did, not what the working tree looks like once we have put it back.
  const outAfter = statMtimeMs(probe.outPath);
  const preserved = preserve ? restoreCapture(probe, original, opts.captureDir) : null;

  const common = { attempted: true, wallMs: endedAt - startedAt, startedAt, endedAt,
    outBefore, outAfter, preserved, stderr: tail(res.stderr) };

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

function readCapture(p) {
  try {
    const st = fs.statSync(p);
    return { existed: true, body: fs.readFileSync(p), atime: st.atime, mtime: st.mtime, mode: st.mode };
  } catch { return { existed: false }; }
}

// Put the committed capture back exactly as it was — bytes AND timestamps, so `git status` and any
// other seat see nothing at all. The probe's FRESH output is not discarded: it is written into the
// summary's captures/ folder, outside the repo, where it is still evidence.
function restoreCapture(probe, original, captureDir) {
  if (!original) return null;
  let fresh = null;
  try { fresh = fs.readFileSync(probe.outPath); } catch { /* the probe wrote none */ }

  const unchanged = fresh && original.existed && fresh.equals(original.body);
  if (fresh && !unchanged && captureDir) {
    const dest = path.join(captureDir, probe.id.replace(/[\\/]/g, '__'));
    try { fs.mkdirSync(captureDir, { recursive: true }); fs.writeFileSync(dest, fresh); } catch { /* best effort */ }
  }

  if (!original.existed) {
    if (fresh) { try { fs.unlinkSync(probe.outPath); } catch {} return 'removed-new'; }
    return 'none';
  }
  if (unchanged) return 'unchanged';
  try {
    fs.writeFileSync(probe.outPath, original.body);
    fs.chmodSync(probe.outPath, original.mode);
    fs.utimesSync(probe.outPath, original.atime, original.mtime);
    return 'restored';
  } catch (e) { return 'RESTORE-FAILED: ' + String(e && e.message || e); }
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
  const dirtied = [];
  const restoreFailures = [];
  const preserve = opts.preserve !== false;
  for (const p of probes) {
    let r;
    try { r = execute(p, { timeoutMs, preserve, captureDir: opts.captureDir }); }
    catch (e) { r = { attempted: true, spawnError: String(e && e.message || e) }; }
    const g = grade(p, r);
    const row = {
      id: p.id, verdict: g.verdict, ok: g.ok, counted: g.counted,
      exit: r && typeof r.exit === 'number' ? r.exit : null,
      wallMs: r && r.wallMs != null ? r.wallMs : null,
      capture: g.capture || null,
      stderr: r && r.stderr ? r.stderr : '',
    };
    rows.push(row);
    if (r && r.outAfter !== null && r.outAfter !== r.outBefore) dirtied.push(p.outPath);
    if (r && typeof r.preserved === 'string' && r.preserved.startsWith('RESTORE-FAILED')) {
      restoreFailures.push(p.outPath + ' — ' + r.preserved);
    }
    emit(`${row.id} ${row.verdict} exit=${row.exit === null ? '-' : row.exit}`
      + ` wall_ms=${row.wallMs === null ? '-' : row.wallMs}`
      + (row.capture ? ` capture=${row.capture}` : '') + '\n');
    if (opts.onRow) opts.onRow(row);
  }

  return finish({ discovered, rows, dirtied, restoreFailures, preserve, opts, emit });
}

function finish({ discovered, rows, dirtied = [], restoreFailures = [], preserve, reason, opts, emit }) {
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
    (preserve === false
      ? 'captures-rewritten-in-tree: ' + dirtied.length
      : 'captures-written-then-restored: ' + dirtied.length + ' (working tree unchanged)'),
    'restore-failures: ' + restoreFailures.length,
    // Written LAST and only here. Header without this line == a truncated run, readable with no
    // exit code in hand.
    `SUITE-COMPLETE verdict=${verdict} exit=${exitCode}`,
    '',
  ].join('\n');
  emit(trailer);

  return { verdict, exitCode, discovered, attempted, passed, failed,
    notAttempted: discovered - attempted, rows, dirtied, restoreFailures,
    preserved: preserve !== false, reason: reason || null };
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

  // ---- PRESERVE MODE: the census must be able to report a NUMBER without mutating the repo ----

  t('P1 preserve (default) leaves the capture byte-identical AND its mtime untouched', () => {
    const capDir = path.join(tmp, 'caps');
    const target = path.join(dir, 'probe-ok.out');
    fs.writeFileSync(target, 'ORIGINAL COMMITTED CAPTURE\n');
    const old = new Date(Date.now() - 9 * 86400000);
    fs.utimesSync(target, old, old);
    const before = fs.readFileSync(target);
    const beforeMtime = fs.statSync(target).mtimeMs;

    const r = run({ captureDir: capDir,
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });

    eq(r.rows[0].verdict, 'PASS', 'verdict');           // grading still saw the fresh write
    eq(r.preserved, true, 'preserved');
    if (!fs.readFileSync(target).equals(before)) throw new Error('capture was not restored byte-identical');
    eq(fs.statSync(target).mtimeMs, beforeMtime, 'mtime');
    // FIXTURE DISCRIMINATES: the sidecar must hold something DIFFERENT, else "restored" would be
    // indistinguishable from "the probe never wrote anything" and this bar would prove nothing.
    const side = fs.readFileSync(path.join(capDir, 'mod__probes__probe-ok.js'));
    if (side.equals(before)) throw new Error('sidecar equals the original — the probe wrote nothing to restore');
    if (!/PASS probe-ok/.test(side.toString())) throw new Error('sidecar did not capture the fresh output');
  });

  t('P2 --write-captures actually leaves the fresh capture in the tree', () => {
    const target = path.join(dir, 'probe-ok.out');
    fs.writeFileSync(target, 'ORIGINAL COMMITTED CAPTURE\n');
    const r = run({ preserve: false,
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });
    eq(r.preserved, false, 'preserved');
    if (!/PASS probe-ok/.test(fs.readFileSync(target, 'utf8'))) throw new Error('write mode did not keep the fresh capture');
  });

  t('P3 preserve removes a capture the probe newly created — tree unchanged either way', () => {
    const target = path.join(dir, 'probe-ok.out');
    fs.rmSync(target, { force: true });
    run({ captureDir: path.join(tmp, 'caps2'),
      discover: (root) => discoverProbes(root).filter((p) => /probe-ok\.js$/.test(p.id)) });
    if (fs.existsSync(target)) throw new Error('a capture that did not exist before the run was left behind');
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
    // file, this would be a PASS. Runs with preserve OFF so the capture it wrote survives the run
    // to be asserted on — under the default it would be restored away, which is P1/P3's job.
    const r = run({ preserve: false,
      discover: (root) => discoverProbes(root).filter((p) => /probe-bad\.js$/.test(p.id)) });
    eq(r.rows[0].verdict, 'FAIL', 'verdict');
    const body = fs.readFileSync(path.join(dir, 'probe-bad.out'), 'utf8');
    if (!/PASS/.test(body)) throw new Error('fixture broken: capture should claim PASS');
  });

  fs.rmSync(tmp, { recursive: true, force: true });

  const failures = results.filter((r) => !r[0]);
  for (const [ok, name, err] of results) console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${err ? ' — ' + err : ''}`);
  console.log(`\nprobe-suite selftest: ${results.length - failures.length}/${results.length} passed`);
  return failures.length === 0 ? 0 : 1;
}

// ---------------------------------------------------------------- cli

function defaultSummaryPath() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, '..', '..', '..', '.rbtv', 'runtime', 'probe-suite', `${stamp}.txt`);
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
    else if (a === '--write-captures') opts.preserve = false;
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
    if (r.preserved) {
      console.log(`working tree UNCHANGED — ${r.dirtied.length} capture(s) were written by probes`
        + ` and restored byte-identical; the fresh output is in ${captureDir}`);
    } else if (r.dirtied.length) {
      // --write-captures: probes write their capture in place, hardcoded to __dirname, so this
      // mode dirties the repo BY DESIGN. Report it rather than let a seat find it at `git status`.
      console.log(`captures rewritten in the working tree: ${r.dirtied.length}`
        + ' (commit them deliberately, by explicit pathspec, or restore them)');
    }
    if (r.restoreFailures.length) {
      console.log('⚠ RESTORE FAILED — these captures are DIRTY and must be handled by hand:');
      for (const f of r.restoreFailures) console.log('  ' + f);
    }
  }
  return r.exitCode;
}

if (require.main === module) process.exit(main(process.argv.slice(2)));

module.exports = { discoverProbes, executeProbe, grade, runSuite, selftest,
  EXIT_GREEN, EXIT_FAILED, EXIT_INCOMPLETE };

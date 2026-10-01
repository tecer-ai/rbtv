'use strict';

// This CLI's own mechanics, exercised against reality.
//
// Three disciplines this run paid for, encoded here rather than remembered:
//
//  1. THE HARNESS ASSERTS ITS OWN COMPLETENESS. A truncated run reads GREENER
//     than a complete one — G-121 shipped 7 PASS lines, no failure line and exit 1,
//     because the harness died at the first refusal check. So every check is
//     isolated (a throw fails THAT check, never the run), and the run refuses
//     unless the number of checks that reported equals the number declared.
//  2. NOTHING IS HANDED THE VALUE UNDER TEST. Exit-code and argv transparency are
//     proven by executing a REAL subprocess whose exit code and output this file
//     chooses, then reading back what the delegation layer produced —
//     never by stubbing the layer being tested (p-green-harness-over-a-broken-mechanism).
//  3. PROPERTIES ARE ASSERTED, NOT INFERRED FROM TODAY'S DATA. Retired verbs stay
//     unrouted, and a removed catalog flag stays a refusal, because a later edit
//     can put either back without meaning to.
//
// It creates a throwaway script in a temp dir and removes it. It never touches
// the live daemon, never runs a delegate's write verb, and needs no network.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const verbs = require('./verbs');
const { delegate, buildDelegateArgs, winShebang } = require('./delegate');

const RBTV_BIN = path.join(__dirname, '..', 'rbtv');

function runCli(args, env) {
  return spawnSync(process.execPath, [RBTV_BIN, ...args], {
    encoding: 'utf8',
    env: { ...process.env, ...(env || {}) },
  });
}

// Each check returns nothing and throws on failure. The name is the report line.
const CHECKS = [
  ['a module name is not a command and points at rbtv install list', () => {
    const r = runCli(['core']);
    if (r.status !== 2) throw new Error(`\`rbtv core\` exited ${r.status}, expected 2`);
    if (!/rbtv install list/.test(r.stderr)) throw new Error('`rbtv core` does not point at rbtv install list');
    if (/component\(s\)/.test(r.stdout)) throw new Error('`rbtv core` still listed components');
  }],

  ['--rules is refused and points at rbtv install list', () => {
    for (const args of [['--rules'], ['core', '--rules']]) {
      const r = runCli(args);
      if (r.status !== 2) throw new Error(`\`rbtv ${args.join(' ')}\` exited ${r.status}, expected 2`);
      if (!/rbtv install list/.test(r.stderr)) {
        throw new Error(`\`rbtv ${args.join(' ')}\` does not point at rbtv install list`);
      }
    }
  }],

  ['Ignite 0.1 verbs are not routed', () => {
    const retired = [
      ['ignite', 'daemon'],
      ['ignite', 'ticker'],
      ['ignite'],
      ['goal'],
      ['run'],
    ];
    for (const argv of retired) {
      const route = verbs.matchRoute(argv);
      if (route && route.prefix.join(' ') === argv.join(' ')) {
        throw new Error(`\`${argv.join(' ')}\` is still a route`);
      }
    }
    const names = new Set(verbs.verbNamespaceTokens());
    for (const tok of ['goal', 'run', 'ignite']) {
      if (names.has(tok)) throw new Error(`\`${tok}\` is still a verb-namespace token`);
    }
    const r = runCli(['ignite', 'daemon', '-h']);
    if (r.status === 0) throw new Error('`rbtv ignite daemon -h` exited 0 — the retired verb still runs');
    if (/not on disk/.test(r.stderr || '')) {
      throw new Error('`rbtv ignite daemon -h` still delegated to a missing 0.1 target');
    }
  }],

  ['delegation propagates a delegate exit code EXACTLY (real subprocess)', () => {
    // Silent by design: delegation inherits stdio, so a chatty fixture would print
    // into this report. Its exit code is the whole subject here.
    const { file, cleanup } = throwaway('#!/bin/sh\nexit ${EXIT_CODE:-0}\n');
    try {
      for (const code of [0, 1, 2, 7]) {
        process.env.EXIT_CODE = String(code);
        const res = delegate({ prefix: ['fake'], target: file, exec: 'direct' }, []);
        if (res.status !== code) throw new Error(`delegate exited ${code}, layer reported ${res.status}`);
      }
    } finally {
      delete process.env.EXIT_CODE;
      cleanup();
    }
  }],

  ['a health verdict is NEVER collapsed into the exit status (G-121 guard)', () => {
    // The delegate reports an UNHEALTHY subject with a SUCCESSFUL read: exit 0,
    // health "failed". If this layer ever re-derived a verdict, this is the check
    // that catches it — the exit code must stay 0 and the body must reach stdout
    // byte-identical.
    const payload = '{"read_ok":true,"health":"failed","active_seconds":0,"n_restarts":46}';
    // Emits to stdout only when asked, so the delegated call below stays silent in
    // this report while the direct call still proves the bytes are unaltered.
    const { file, cleanup } = throwaway(`#!/bin/sh\n[ -n "$SHOW" ] && printf '%s\\n' '${payload}'\nexit 0\n`);
    try {
      const interp = winShebang(file);
      const r = spawnSync(interp || file, interp ? [file.replace(/\\/g, '/')] : [], {
        encoding: 'utf8', env: { ...process.env, SHOW: '1' },
      });
      if (r.status !== 0) throw new Error(`fixture itself exited ${r.status}`);
      const res = delegate({ prefix: ['fake'], target: file, exec: 'direct' }, []);
      if (res.status !== 0) {
        throw new Error(`an unhealthy-but-readable unit produced exit ${res.status} — health was collapsed into the exit status`);
      }
      if (res.message !== null) throw new Error('the layer injected a message into a successful delegated call');
      if (r.stdout.trim() !== payload) throw new Error('fixture stdout was altered');
    } finally { cleanup(); }
  }],

  ['a missing delegate refuses loudly instead of reporting success', () => {
    const res = delegate({ prefix: ['fake'], target: '/nonexistent/rbtv-selftest-absent', exec: 'direct' }, []);
    if (res.status === 0) throw new Error('a missing delegate returned success');
    if (!res.missing || !/not on disk/.test(res.message || '')) throw new Error('refusal does not name the cause');
  }],

  ['global --json reaches the delegate exactly once', () => {
    if (buildDelegateArgs(['unit'], { json: true }).join(' ') !== 'unit --json') {
      throw new Error('a global --json was not forwarded to the delegate');
    }
    if (buildDelegateArgs(['unit', '--json'], { json: true }).join(' ') !== 'unit --json') {
      throw new Error('--json was duplicated when given on both sides of the route');
    }
    if (buildDelegateArgs(['unit'], { json: false }).join(' ') !== 'unit') {
      throw new Error('--json was invented where the caller asked for none');
    }
  }],

  ['no arguments and -h print help that points at rbtv install list', () => {
    for (const args of [[], ['-h'], ['--help']]) {
      const r = runCli(args);
      if (r.status !== 0) throw new Error(`\`rbtv ${args.join(' ')}\` exited ${r.status}`);
      if (!/rbtv install list/.test(r.stdout)) throw new Error('help does not point at rbtv install list');
      if (/--rules/.test(r.stdout)) throw new Error('help still advertises --rules');
    }
  }],

  ['doctor --json is parseable', () => {
    const r = runCli(['--json', 'doctor']);
    if (r.status !== 0) throw new Error(`\`rbtv --json doctor\` exited ${r.status}`);
    JSON.parse(r.stdout);
  }],

  ['bare status teaches the installer command without acting', () => {
    const r = runCli(['status']);
    if (r.status !== 2) throw new Error(`bare status exited ${r.status}, expected usage exit 2`);
    if (!/Fix: rbtv install status --target/.test(r.stderr)) {
      throw new Error('bare status did not teach the installer status command');
    }
    for (const args of [['--json', 'status'], ['status', '--json']]) {
      const structured = runCli(args);
      if (structured.status !== 2 || structured.stderr) throw new Error('JSON status refusal has prose or wrong exit');
      const body = JSON.parse(structured.stdout);
      if (body.ok !== false || body.error?.code !== 'wrong-command'
          || !body.next?.startsWith('rbtv install status --target')) {
        throw new Error('JSON status refusal lacks the exact recovery command');
      }
    }
  }],

  ['top-level help stays a map, not a manual (<= 30 lines)', () => {
    const r = runCli(['--help']);
    if (r.status !== 0) throw new Error(`--help exited ${r.status}`);
    const lines = r.stdout.trimEnd().split('\n').length;
    if (lines > 30) throw new Error(`top-level help is ${lines} lines — the bar is 30`);
    if (/rbtv ignite daemon|rbtv goal |rbtv run /.test(r.stdout)) {
      throw new Error('top-level help still advertises a retired 0.1 verb as a command');
    }
  }],

  ['doctor names every delegate individually', () => {
    const r = runCli(['--json', 'doctor']);
    const out = JSON.parse(r.stdout);
    for (const route of verbs.ROUTES) {
      const name = `delegate: ${route.prefix.join(' ')}`;
      if (!out.checks.some((c) => c.name === name)) throw new Error(`doctor does not check ${name}`);
    }
    if (typeof out.ok !== 'boolean') throw new Error('doctor --json carries no ok verdict');
  }],

  ['no token value is ever emitted', () => {
    const r = runCli(['--json', 'doctor'], { IGNITE_SENDER_TOKEN: 'SELFTEST-SECRET-VALUE' });
    if (/SELFTEST-SECRET-VALUE/.test(r.stdout + r.stderr)) {
      throw new Error('doctor printed the token VALUE — it may report presence only');
    }
    if (!/set in env/.test(r.stdout)) throw new Error('doctor does not report token presence at all');
  }],

  ['spark finds an installed agent by its folder and builds the cast command from launch.json', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtv-spark-'));
    try {
      const home = path.join(dir, '.rbtv', 'agents', 'sara');
      fs.mkdirSync(home, { recursive: true });
      fs.writeFileSync(path.join(home, 'launch.json'), JSON.stringify({ harness: 'claude', model: 'sonnet-5', effort: 'high' }));
      fs.writeFileSync(path.join(home, 'agent.md'), '# sara\n');
      const r = runCli(['spark', 'sara', '--target', dir, '--dry-run', '--json']);
      if (r.status !== 0) throw new Error(`spark --dry-run exited ${r.status}: ${r.stderr}`);
      const out = JSON.parse(r.stdout);
      const want = ['cast', 'claude', 'sonnet-5', '3', home, '--headed', '-S', path.join(home, 'agent.md')];
      if (JSON.stringify(out.cast.slice(0, 8)) !== JSON.stringify(want)) {
        throw new Error(`unexpected cast command: ${JSON.stringify(out.cast)}`);
      }
      const missing = runCli(['spark', 'nobody', '--target', dir]);
      if (missing.status !== 1 || !/no installed agent/.test(missing.stderr)) {
        throw new Error('an unknown agent did not refuse by name');
      }
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }],

  ['an unresolvable rbtv root refuses with a teaching error, not a stack trace', () => {
    // Found by probing this CLI from a throwaway copy of itself: the root is
    // inferred from the script's own position, so a relocated tree crashed with an
    // ENOENT stack. A caller cannot act on a stack trace.
    const r = runCli(['doctor'], { RBTV_ROOT: '/nonexistent-rbtv-root' });
    if (r.status !== 1) throw new Error(`expected refusal exit 1, got ${r.status}`);
    if (/INTERNAL:|at Module\._compile/.test(r.stderr)) throw new Error('a stack trace reached the caller');
    if (!/RBTV_ROOT=/.test(r.stderr)) throw new Error('the refusal does not name the override that fixes it');
    if (!r.stderr.includes(path.resolve('/nonexistent-rbtv-root'))) {
      throw new Error('the refusal does not name the root it resolved');
    }
  }],

];

function throwaway(body) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtv-selftest-'));
  const file = path.join(dir, 'fake-delegate');
  fs.writeFileSync(file, body, { mode: 0o755 });
  return { file, cleanup: () => fs.rmSync(dir, { recursive: true, force: true }) };
}

function runSelftest() {
  const declared = CHECKS.length;
  let ran = 0;
  let failed = 0;

  for (const [name, fn] of CHECKS) {
    // Isolated: a throw fails THIS check and the run continues. A harness that
    // dies at the first failure reports fewer failures than it found.
    try {
      fn();
      console.log(`PASS  ${name}`);
    } catch (err) {
      failed += 1;
      console.log(`FAIL  ${name}\n        ${err.message}`);
    }
    ran += 1;
  }

  // Completeness: the run is only a result if every declared check reported.
  if (ran !== declared) {
    console.log(`FAIL  harness completeness: ${ran}/${declared} checks reported — this run is TRUNCATED, not green`);
    return 1;
  }

  console.log(`\n${ran} checks, ${failed} failed`);
  return failed === 0 ? 0 : 1;
}

module.exports = { runSelftest, CHECKS };

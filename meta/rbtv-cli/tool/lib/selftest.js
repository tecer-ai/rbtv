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
//  3. PROPERTIES ARE ASSERTED, NOT INFERRED FROM TODAY'S DATA. The namespace
//     disjointness check is the one that matters: it holds today by accident of
//     naming, and only an assertion catches the future module that breaks it (G-107).
//
// It creates a throwaway script in a temp dir and removes it. It never touches
// the live daemon, never runs a delegate's write verb, and needs no network.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const catalog = require('./catalog');
const verbs = require('./verbs');
const { delegate, buildDelegateArgs, winShebang } = require('./delegate');
const { suggest, blurb } = require('./render');

const RBTV_BIN = path.join(__dirname, '..', 'rbtv');

function runCli(args, env) {
  return spawnSync(process.execPath, [RBTV_BIN, ...args], {
    encoding: 'utf8',
    env: { ...process.env, ...(env || {}) },
  });
}

// Each check returns nothing and throws on failure. The name is the report line.
const CHECKS = [
  ['component and verb names stay disjoint under every module (ASSERTED)', () => {
    // The property, not today's data. `ignite` is deliberately both a module and a
    // verb namespace — that is resolved by position. What is NOT resolvable is a
    // component whose name equals a verb of its own module: `rbtv ignite inspect`
    // would then mean two things. It holds today by accident of naming; a future
    // capability called `status` or `inspect` breaks it, and only this assertion
    // catches that the moment it lands rather than in an outage.
    for (const mod of catalog.modules()) {
      const route = verbs.ROUTES.find((r) => r.prefix.length === 1 && r.prefix[0] === mod.name);
      if (!route) continue;
      const componentNames = new Set((catalog.components(mod.name) || []).map((c) => c.name));
      const nested = verbs.ROUTES
        .filter((r) => r.prefix.length === 2 && r.prefix[0] === mod.name)
        .map((r) => r.prefix[1]);
      const clash = [...route.verbs, ...nested].filter((v) => componentNames.has(v));
      if (clash.length) {
        throw new Error(
          `under module \`${mod.name}\`, ${clash.join(', ')} name(s) BOTH a component and an action verb — `
          + `\`rbtv ${mod.name} ${clash[0]}\` is ambiguous. Rename one of the two.`,
        );
      }
    }
  }],

  ['a bare module token is the drill, never a delegated call', () => {
    // The collision this suite caught during the build: routing action verbs ahead
    // of the drill at position 1 made the ignite module's own level 1 and level 2
    // UNREACHABLE — `rbtv ignite` reached the gateway client instead of listing
    // components. Kept as a permanent check because the fix is a precedence rule,
    // and precedence rules are exactly what a later route addition quietly changes.
    const r = runCli(['ignite']);
    if (r.status !== 0) throw new Error(`\`rbtv ignite\` exited ${r.status} — it is being delegated, not drilled`);
    if (/Commands:/.test(r.stdout)) throw new Error('`rbtv ignite` printed the gateway client help — the drill is shadowed');
    if (!/component\(s\)/.test(r.stdout)) throw new Error('`rbtv ignite` did not list components');
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

  ['drill levels 0, 1 and 2 resolve against a real module', () => {
    const l0 = runCli([]);
    if (l0.status !== 0) throw new Error(`level 0 exited ${l0.status}`);
    if (!/\bignite\b/.test(l0.stdout)) throw new Error('level 0 does not list the ignite module');

    const l1 = runCli(['ignite']);
    if (l1.status !== 0) throw new Error(`level 1 exited ${l1.status}`);
    if (!/^agents\b/m.test(l1.stdout)) throw new Error('level 1 does not list agents');
    if (/rbtv ignite daemon/.test(l1.stdout)) throw new Error('level 1 still surfaces the retired ignite daemon verb');

    const l2 = runCli(['ignite', 'agents']);
    if (l2.status !== 0) throw new Error(`level 2 exited ${l2.status}`);
    if (!/entry point:/.test(l2.stdout) && !/units \(/.test(l2.stdout)) {
      throw new Error('level 2 delivers neither an entry point nor units');
    }
    if (!/ignite-agent/.test(l2.stdout)) throw new Error('level 2 does not list the ignite-agent invocable');
  }],

  ['drill --json is parseable at every level', () => {
    for (const args of [['--json'], ['--json', 'ignite'], ['--json', 'ignite', 'agents'], ['--json', 'doctor']]) {
      const r = runCli(args);
      if (r.status !== 0 && !(args.includes('doctor'))) throw new Error(`\`${args.join(' ')}\` exited ${r.status}`);
      try {
        JSON.parse(r.stdout);
      } catch (err) {
        throw new Error(`\`rbtv ${args.join(' ')}\` emitted unparseable JSON: ${err.message}`);
      }
    }
  }],

  ['unknown references refuse with a closest-match suggestion', () => {
    const r = runCli(['ignit']);
    if (r.status !== 1) throw new Error(`expected exit 1, got ${r.status}`);
    if (!/ignite/.test(r.stderr)) throw new Error('no suggestion offered for a near-miss module');
    const r2 = runCli(['ignite', 'agnts']);
    if (r2.status !== 1) throw new Error(`unknown component exited ${r2.status}`);
    if (!/agents/.test(r2.stderr)) throw new Error('no suggestion offered for a near-miss component');
    if (suggest('zzzzzzzz', ['ignite', 'core']) !== null) throw new Error('a far-miss produced a suggestion');
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

  ['the pretty mode is opt-in, never TTY-derived', () => {
    const plain = runCli([]);
    if (/\x1b\[/.test(plain.stdout)) throw new Error('default output carries colour');
    const pretty = runCli(['--pretty']);
    if (!/\x1b\[/.test(pretty.stdout)) throw new Error('--pretty produced no colour');
    const viaEnv = runCli([], { RBTV_PRETTY: '1' });
    if (!/\x1b\[/.test(viaEnv.stdout)) throw new Error('RBTV_PRETTY did not enable pretty mode');
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

  ['drill flags work AFTER the module token, the form the help teaches', () => {
    // The defect this replaced: `rbtv core --rules` refused — only `rbtv --rules
    // core` worked — while the top-level help taught "--rules with a drill level".
    // A CLI whose own help teaches a failing command. Found by RUNNING --rules for
    // the first time at close, not by re-reading the parser.
    const after = runCli(['core', '--rules']);
    if (after.status !== 0) throw new Error(`\`rbtv core --rules\` exited ${after.status}`);
    // Counted by the body HEADER, not by a path shape: the rules used to live at
    // `core/rules/<name>.md` and now live inside the component that exposes them
    // (`core/behaviour/references/…`). Pinning the old folder made this check red
    // on a move that broke nothing.
    const bodies = (after.stdout.match(/^--- core\//gm) || []).length;
    if (bodies < 2) throw new Error(`--rules after the module delivered ${bodies} rule bodies`);

    const before = runCli(['--rules', 'core']);
    const beforeBodies = (before.stdout.match(/^--- core\//gm) || []).length;
    if (beforeBodies !== bodies) throw new Error('flag position changes the result');

    if (runCli(['ignite', '--json']).status !== 0) throw new Error('`rbtv ignite --json` refused');
    if (runCli(['ignite', '--nonsense']).status !== 2) throw new Error('an unknown drill flag is not a usage error');
  }],

  ['every component on the tree resolves by name to exactly itself', () => {
    let checked = 0;
    for (const mod of catalog.modules()) {
      for (const comp of catalog.components(mod.name) || []) {
        const got = catalog.findComponent(mod.name, comp.name);
        if (!got || got.name !== comp.name) {
          throw new Error(`${mod.name} ${comp.name}: findComponent did not return it`);
        }
        checked += 1;
      }
    }
    if (checked < 10) throw new Error(`only ${checked} names checked — the tree read is not delivering components`);
    const r = runCli(['core', 'coding']);
    if (r.status !== 0) throw new Error(`\`rbtv core coding\` exited ${r.status}`);
    const j = JSON.parse(runCli(['--json', 'core', 'coding']).stdout);
    if (j.units.length !== catalog.findComponent('core', 'coding').units.length) {
      throw new Error('--json dropped a unit');
    }
  }],

  ['an unresolvable rbtv root refuses with a teaching error, not a stack trace', () => {
    // Found by probing this CLI from a throwaway copy of itself: the root is
    // inferred from the script's own position, so a relocated tree crashed with an
    // ENOENT stack. A caller cannot act on a stack trace.
    const r = runCli(['ignite'], { RBTV_ROOT: '/nonexistent-rbtv-root' });
    if (r.status !== 1) throw new Error(`expected refusal exit 1, got ${r.status}`);
    if (/INTERNAL:|at Module\._compile/.test(r.stderr)) throw new Error('a stack trace reached the caller');
    if (!/RBTV_ROOT=/.test(r.stderr)) throw new Error('the refusal does not name the override that fixes it');
    if (!r.stderr.includes(path.resolve('/nonexistent-rbtv-root'))) {
      throw new Error('the refusal does not name the root it resolved');
    }
  }],

  ['blurb truncation never emits a partial escape or unbounded text', () => {
    const long = `${'x'.repeat(400)}. tail`;
    const out = blurb(long);
    if (out.length > 110) throw new Error(`blurb returned ${out.length} chars, cap is 110`);
    if (blurb('') !== '') throw new Error('blurb of empty text is not empty');
    if (blurb(null) !== '') throw new Error('blurb of null is not empty');
  }],

  ['a component is listed at level 1 with its units read from its folders', () => {
    const agents = catalog.findComponent('ignite', 'agents');
    if (!agents) throw new Error('`ignite` components() does not carry the agents component');
    if (!agents.units.some((u) => u.id === 'ignite-agent' && u.method === 'tool')) {
      throw new Error('agents carries no ignite-agent tool unit');
    }

    const r = runCli(['ignite']);
    if (r.status !== 0) throw new Error(`\`rbtv ignite\` exited ${r.status}`);
    if (!/^agents\b/m.test(r.stdout)) throw new Error('level 1 does not list agents as a component');
  }],

  ['level 2 delivers the orientation body (frontmatter stripped) then the units', () => {
    const r = runCli(['ignite', 'agents']);
    if (r.status !== 0) throw new Error(`\`rbtv ignite agents\` exited ${r.status}`);
    if (!/^\n?ignite agents \(component\)/m.test(r.stdout)) throw new Error('no component header printed');
    const bodyIdx = r.stdout.indexOf('--- ignite/agents/capabilities/component.md ---');
    if (bodyIdx === -1) throw new Error('the orientation body was not delivered');
    if (/^description:/m.test(r.stdout.slice(bodyIdx))) throw new Error('frontmatter leaked into the printed body');
    const unitsIdx = r.stdout.indexOf('units (');
    if (unitsIdx === -1 || unitsIdx < bodyIdx) throw new Error('units did not follow the orientation body');
    if (!/ignite-agent \(tool\)/.test(r.stdout)) throw new Error('the ignite-agent unit was not delivered');
  }],

  ['an unknown name under a module WITH component folders still refuses, and the known-list carries the new components', () => {
    const r = runCli(['ignite', 'nosuchthing']);
    if (r.status !== 1) throw new Error(`expected exit 1, got ${r.status}`);
    if (!/agents/.test(r.stderr)) throw new Error('refusal known-list does not carry agents');
  }],

  ['a module built ENTIRELY of component folders lists all of them', () => {
    // This check used to assert the opposite — that `core` carried NO component
    // folders, so the folder reader could be seen not to disturb it. core was
    // migrated to component folders and the check had been red on that stale
    // assumption before the module manifest was retired. Every module is
    // folder-built now, so the property worth holding is that none is dropped.
    const folders = catalog.componentFolders('core');
    if (folders.length < 3) throw new Error(`core carries ${folders.length} component folders — expected the whole module`);
    const r = runCli(['core']);
    if (r.status !== 0) throw new Error(`\`rbtv core\` exited ${r.status}`);
    for (const f of folders) {
      if (!r.stdout.includes(f.name)) throw new Error(`\`rbtv core\` did not list ${f.name}`);
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

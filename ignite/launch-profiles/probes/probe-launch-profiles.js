'use strict';

// probe-launch-profiles — the shared launch-profile resolver's own probe (task 7.42).
//
// Self-contained by construction: it requires ONLY `../` (the shared module) and node builtins.
// If this file ever needs something under `server/`, the module has stopped being daemon-free and
// the probe should fail rather than be patched.
//
// TWO DISCIPLINES THIS RUN PAID FOR, applied here deliberately:
//
//  · NO PROBE MAY SUPPLY THE VALUE UNDER TEST. The value under test is the RESOLUTION — which
//    half is picked, which dialect an effort level renders as, whether a caller value becomes an
//    argv element. The probe supplies INPUT (a profile) and the module computes the answer. For
//    half selection it does NOT pass a capability in — `detectHostCapability()` takes no argument
//    at all. It changes the HOST instead: leg 6/7 run in a CHILD PROCESS whose real PATH contains
//    no `bwrap`, so the detector genuinely computes `portable`.
//
//  · A CONTROL THAT CANNOT FAIL IS NOT A CONTROL. Leg 2 asserts BOTH directions: the new
//    resolver REFUSES an undeclared slot key, AND the pre-7.42 path (resolveTemplateSlots alone,
//    which the daemon used directly) SILENTLY IGNORES the same input. That second assertion is
//    what makes the leg fail on pre-fix code by construction — without it, "it refused" would be
//    compatible with a resolver that refuses everything.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const lp = require('..');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..');
const SHIPPED = path.join(IGNITE_ROOT, 'config', 'spawn-profiles.yaml');
const OUT = path.join(__dirname, 'probe-launch-profiles.out');

const lines = [];
const started = new Date();
let failed = null;

function check(label, fn) {
  try {
    const detail = fn();
    lines.push(`PASS ${label}${detail ? ` -> ${detail}` : ''}`);
  } catch (err) {
    lines.push(`FAIL ${label} -> ${err.message}`);
    if (!failed) failed = err;
  }
}

function expectCode(code, fn) {
  try {
    fn();
  } catch (err) {
    if (err.code === code) return err;
    throw new Error(`expected ${code}, got ${err.code || err.message}`);
  }
  throw new Error(`expected ${code}, but the call SUCCEEDED`);
}

// A two-half fixture, written to a TEMP dir at runtime. It is deliberately NOT a committed file:
// criterion 6 is "no second profile file exists anywhere in the repo", and a checked-in fixture
// would be exactly that. The daemon cannot spawn a half-shaped profile today (spawn.js reads
// `profile.exec` unguarded — filed as an issue), which is why these do not ship in the production
// config either.
function writeFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lp-probe-'));
  const file = path.join(dir, 'halves.yaml');
  yaml && fs.writeFileSync(file, yaml.dump({
    default_workdir_root: dir,
    profiles: {
      'both-halves': {
        command: {
          caged: { argv: ['sleep', '--caged-marker', '{workdir}'], prompt: 'stdin' },
          portable: { argv: ['sleep', '--portable-marker', '{workdir}'], prompt: 'stdin' },
        },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      },
      'caged-only': {
        command: { caged: { argv: ['sleep', '1'], prompt: 'stdin' } },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      },
    },
  }));
  return file;
}

const fixture = writeFixture();
const fx = lp.loadConfig(fixture);
const shipped = lp.loadConfig(SHIPPED, { seatBindValidator: () => {} });

// ── 1 · resolve by NAME ──────────────────────────────────────────────────────────────────────
check('(1) unknown profile name is refused typed', () => {
  const err = expectCode('E_UNKNOWN_PROFILE', () => lp.resolveProfile(shipped, 'no-such-profile'));
  return err.code;
});
check('(1b) a known name resolves', () => {
  const r = lp.resolveProfile(shipped, 'test-sleep');
  if (r.argv[0] !== 'sleep') throw new Error(`argv0 ${r.argv[0]}`);
  return r.argv.join(' ');
});

// ── 2 · rejects raw flags — THE DISCRIMINATING CONTROL ───────────────────────────────────────
check('(2) undeclared slot key REFUSED by the resolver', () => {
  const err = expectCode('E_RAW_FLAG', () => lp.resolveProfile(shipped, 'test-sleep', {
    slots: { evil: '--dangerously-skip-permissions' },
  }));
  return err.code;
});
check('(2b) CONTROL — the pre-7.42 path SILENTLY IGNORES the same input (so leg 2 discriminates)', () => {
  // resolveTemplateSlots is what the daemon called directly before this task. It has no notion of
  // "declared slots": an unknown key is not an error, it is simply never substituted. If a future
  // edit made it throw, leg 2 would stop proving anything and THIS leg would go red.
  const out = lp.resolveTemplateSlots(['sleep', '60'], { evil: '--dangerously-skip-permissions' });
  if (out.length !== 2 || out.join(' ') !== 'sleep 60') {
    throw new Error(`pre-fix path changed behaviour: ${JSON.stringify(out)}`);
  }
  return 'silent, unchanged — the refusal in (2) is new behaviour, not shared behaviour';
});
check('(3) a caller value can never BECOME an argv element (arity asserted)', () => {
  const r = lp.resolveProfile(fx, 'both-halves', { slots: { workdir: '/tmp/x --rm -rf /' } });
  const tmpl = fx.profiles['both-halves'].command.caged.argv.length;
  if (r.argv.length !== tmpl) throw new Error(`arity ${r.argv.length} != template ${tmpl}`);
  if (r.argv[2] !== '/tmp/x --rm -rf /') throw new Error('value not substituted in place');
  return `${tmpl} elements in, ${r.argv.length} out — flags inside a value stay INSIDE it`;
});

// ── 4/5 · half selection on THIS host, detected ──────────────────────────────────────────────
check('(4) host capability is DETECTED on this box (no argument accepted)', () => {
  if (lp.detectHostCapability.length !== 0) throw new Error('detector accepts an argument — a caller could choose');
  return lp.detectHostCapability();
});
check('(5) dual-half profile resolves the CAGED half on this VPS', () => {
  const r = lp.resolveProfile(fx, 'both-halves', { slots: { workdir: '/tmp' } });
  if (r.half !== 'caged') throw new Error(`half=${r.half}`);
  if (!r.argv.includes('--caged-marker')) throw new Error(`argv=${r.argv.join(' ')}`);
  return `half=${r.half} argv=${r.argv.join(' ')}`;
});

// ── 6/7 · a GENUINELY cage-less host, in a child process with no bwrap on PATH ───────────────
function inCagelessChild(script) {
  const emptyDir = fs.mkdtempSync(path.join(os.tmpdir(), 'nopath-'));
  return execFileSync(process.execPath, ['-e', script], {
    encoding: 'utf8',
    env: { ...process.env, PATH: emptyDir },   // a REAL environment with no bwrap
    cwd: IGNITE_ROOT,
  }).trim();
}
check('(6) on a cage-less host the SAME profile resolves the PORTABLE half', () => {
  const out = inCagelessChild(`
    const lp=require(${JSON.stringify(path.join(IGNITE_ROOT, 'launch-profiles'))});
    if (lp.detectHostCapability()!=='portable') { console.log('DETECT='+lp.detectHostCapability()); process.exit(0); }
    const c=lp.loadConfig(${JSON.stringify(fixture)});
    const r=lp.resolveProfile(c,'both-halves',{slots:{workdir:'/tmp'}});
    console.log('half='+r.half+' argv='+r.argv.join(' '));
  `);
  if (!out.startsWith('half=portable')) throw new Error(out);
  if (!out.includes('--portable-marker')) throw new Error(out);
  return out;
});
check('(7) a portable-LESS profile FAILS CLOSED on a cage-less host', () => {
  const out = inCagelessChild(`
    const lp=require(${JSON.stringify(path.join(IGNITE_ROOT, 'launch-profiles'))});
    const c=lp.loadConfig(${JSON.stringify(fixture)});
    try { const r=lp.resolveProfile(c,'caged-only'); console.log('UNEXPECTED PASS half='+r.half+' argv='+r.argv.join(' ')); }
    catch(e){ console.log('refused='+e.code); }
  `);
  if (out !== 'refused=E_NO_PORTABLE_HALF') throw new Error(out);
  return out;
});

// ── 8/9/10/11 · the effort slot, against the SHIPPED file ────────────────────────────────────
check('(8) effort round-trips through the claude dialect', () => {
  const r = lp.resolveProfile(shipped, 'claude-sonnet', { effort: 'high' });
  if (!r.argv.includes('--effort') || !r.argv.includes('high')) throw new Error(r.argv.join(' '));
  return `dialect=${r.effort.dialect} argv-tail=${r.argv.slice(-2).join(' ')}`;
});
check('(9) …and through a SECOND, differently-spelled dialect (codex)', () => {
  const r = lp.resolveProfile(shipped, 'codex-gpt-5-5', { effort: 'high', slots: { workdir: '/tmp' } });
  const tail = r.argv.slice(-2).join(' ');
  if (!tail.includes('model_reasoning_effort=high')) throw new Error(tail);
  if (r.effort.dialect !== 'thinking') throw new Error(`dialect=${r.effort.dialect}`);
  return `dialect=${r.effort.dialect} argv-tail=${tail}`;
});
check('(9b) the table TRANSLATES rather than passes through (max -> high on codex [3-depth dial, lossy stated collapse], max on claude)', () => {
  const cx = lp.resolveProfile(shipped, 'codex-gpt-5-5', { effort: 'max', slots: { workdir: '/tmp' } });
  const cl = lp.resolveProfile(shipped, 'claude-sonnet', { effort: 'max' });
  if (cx.effort.value !== 'high') throw new Error(`codex max -> ${cx.effort.value}`);
  if (cl.effort.value !== 'max') throw new Error(`claude max -> ${cl.effort.value}`);
  return 'ONE abstract level, two different rendered values — translation, not passthrough';
});
check('(10) an INERT dial is STATED, never silently dropped', () => {
  const dir = path.dirname(fixture);
  const f = path.join(dir, 'inert.yaml');
  fs.writeFileSync(f, yaml.dump({
    default_workdir_root: dir,
    profiles: {
      'no-dial': {
        exec: { argv: ['sleep', '1'], prompt: 'stdin' },
        effort: { inert: true },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      },
    },
  }));
  const r = lp.resolveProfile(lp.loadConfig(f), 'no-dial', { effort: 'high' });
  if (r.effortInert !== true) throw new Error('inert not reported');
  if (r.argv.length !== 2) throw new Error(`argv grew: ${r.argv.join(' ')}`);
  return 'effortInert=true reported to the caller; argv unchanged';
});
check('(11) an effort level outside the abstract vocabulary is refused', () => {
  const err = expectCode('E_UNKNOWN_EFFORT', () => lp.resolveProfile(shipped, 'claude-sonnet', { effort: 'turbo' }));
  return err.code;
});

// ── 12 · the pinned-flag pre-flight, against a REAL installed binary ─────────────────────────
check('(12) pre-flight PASSES a flag the installed CLI really has', () => {
  const r = lp.preflightPinnedFlags({ name: 'probe', argv: ['node', '--version'] });
  return `checked ${r.checked.join(',')} against ${r.binary}`;
});
check('(13) pre-flight REFUSES a flag the installed CLI does not have', () => {
  const err = expectCode('E_PINNED_FLAG_ABSENT', () => lp.preflightPinnedFlags({ name: 'probe', argv: ['node', '--not-a-real-node-flag'] }));
  return `${err.code} missing=${err.details.missing.join(',')}`;
});
check('(14) pre-flight distinguishes "could not look" from "flag is gone"', () => {
  const err = expectCode('E_PREFLIGHT_UNAVAILABLE', () => lp.preflightPinnedFlags({ name: 'probe', argv: ['definitely-not-installed-binary-xyz', '--help'] }));
  return err.code;
});

// Legs 14b/14c guard the two defects the CLOSE-OUT "run one thing you did not prove" found in
// this very module, by running it against the REALLY-INSTALLED harness CLIs. Both would have
// shipped: the pre-flight refused 2 of the 3 real profiles, authoritatively and wrongly.
check('(14b) help is read from the SUBCOMMAND page, not the top-level binary', () => {
  // Ground truth first, so this leg fails if the premise ever stops holding: `--json` is on
  // `codex exec --help` and ABSENT from `codex --help`.
  let top;
  try { top = lp.readHelp('codex', { helpArgs: ['--help'] }); } catch { return 'skipped — codex not installed on this host'; }
  if (top.includes('--json')) throw new Error('premise gone: codex --help now lists --json');
  const r = lp.preflightPinnedFlags({ name: 'ctl', argv: ['codex', 'exec', '--cd', '{workdir}', '--json'] });
  return `checked ${r.checked.join(' ')} against \`codex exec --help\``;
});
check('(14c) an EMPTY help is "could not look", never "the flag is gone"', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'silent-'));
  const bin = path.join(dir, 'silentcli');
  fs.writeFileSync(bin, '#!/bin/sh\nexit 0\n');           // succeeds, prints NOTHING
  fs.chmodSync(bin, 0o755);
  const err = expectCode('E_PREFLIGHT_UNAVAILABLE', () => lp.preflightPinnedFlags({ name: 'ctl', argv: [bin, '--some-flag'] }));
  if (err.details.reason !== 'empty-help') throw new Error(`reason=${err.details.reason}`);
  return 'E_PREFLIGHT_UNAVAILABLE(empty-help) — NOT E_PINNED_FLAG_ABSENT';
});

// ── 15 · criterion 6 — no second profile file in the repo ───────────────────────────────────
check('(15) exactly ONE file in the repo defines profiles', () => {
  const out = execFileSync('git', ['grep', '-l', '^profiles:', '--', '*.yaml', '*.yml'], {
    cwd: path.resolve(IGNITE_ROOT, '..'), encoding: 'utf8',
  }).trim().split('\n').filter(Boolean);
  if (out.length !== 1) throw new Error(`profile-defining files: ${out.join(', ')}`);
  return out[0];
});

const ended = new Date();
const body = [
  'probe: probe-launch-profiles',
  `started: ${started.toISOString()}`,
  'command: node launch-profiles/probes/probe-launch-profiles.js',
  ...lines,
  `status: ${failed ? 'FAIL' : 'PASS'}`,
  `checks: ${lines.length} (${lines.filter((l) => l.startsWith('PASS')).length} pass, ${lines.filter((l) => l.startsWith('FAIL')).length} fail)`,
  `exit: ${failed ? 1 : 0}`,
  `wall_ms: ${ended - started}`,
  `ended: ${ended.toISOString()}`,
  '',
].join('\n');
fs.writeFileSync(OUT, body);
process.stdout.write(body);
// A truncated run must never read greener than a complete one (G-121): the check count above is
// asserted by the reader, and the exit code is the authority.
process.exit(failed ? 1 : 0);

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
const skipped = [];

// A SKIP IS A DISTINCT VERDICT, NEVER A PASS. `check` grades any return as PASS, so a leg that
// returned the STRING 'skipped — codex not installed' was counted into `checks: N (N pass)` as
// evidence — the leg that never ran read exactly like the leg that ran and held. A leg that cannot
// measure throws this instead, and the run exits 2 (see the accounting block).
class Skip extends Error {}

function check(label, fn) {
  try {
    const detail = fn();
    lines.push(`PASS ${label}${detail ? ` -> ${detail}` : ''}`);
  } catch (err) {
    if (err instanceof Skip) { skipped.push(label); lines.push(`SKIP ${label} -> ${err.message}`); return; }
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
// r-chat-chain-resumes-session: the shipped claude profiles DECLARE the `{session_ref}` slot
// (`--session-id {session_ref}`), and a declared slot with no value is E_MISSING_KEY by design —
// the resolver refuses to emit a literal `{session_ref}` onto a command line. The effort legs
// below therefore supply one, exactly as the codex legs already supply `{workdir}`.
const SESSION_REF = '00000000-0000-4000-8000-000000000000';

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

// ── 8/9/10/11 · the effort RUNG, against the SHIPPED file ────────────────────────────────────
// Migrated 2026-08-11 from the four-level abstract vocabulary to per-profile numeric rungs (owner
// ruling `d-0811lp-effort-numeric-per-profile`). The legs test the SAME property they always did —
// one caller vocabulary, each harness's own spelling — with the ladder now the profile's, not a
// shared closed set. Leg 9b changed SUBJECT with the scheme: there is no longer a lossy collapse
// to observe (that was the four-level table's artefact), so it now asserts what replaced it —
// the SAME rung number renders differently per harness, and the TOP rung differs per harness.
check('(8) a rung round-trips through the claude ladder (rung 4 = xhigh, the 5-rung dial\'s fourth)', () => {
  const r = lp.resolveProfile(shipped, 'claude-sonnet', { effort: 4, slots: { session_ref: SESSION_REF } });
  if (!r.argv.includes('--effort') || !r.argv.includes('xhigh')) throw new Error(r.argv.join(' '));
  if (r.effort.of !== 5) throw new Error(`ladder size ${r.effort.of}`);
  return `dialect=${r.effort.dialect} rung=${r.effort.rung}/${r.effort.of} argv-tail=${r.argv.slice(-2).join(' ')}`;
});
check('(9) …and through a SECOND, differently-spelled dialect (codex: a -c override, 3 rungs)', () => {
  const r = lp.resolveProfile(shipped, 'codex-gpt-5-5', { effort: 3, slots: { workdir: '/tmp' } });
  const tail = r.argv.slice(-2).join(' ');
  if (!tail.includes('model_reasoning_effort=high')) throw new Error(tail);
  if (r.effort.dialect !== 'thinking' || r.effort.of !== 3) throw new Error(`${r.effort.dialect}/${r.effort.of}`);
  return `dialect=${r.effort.dialect} rung=${r.effort.rung}/${r.effort.of} argv-tail=${tail}`;
});
check('(9b) ONE rung number, three harness spellings — and each ladder has its OWN top', () => {
  const three = [
    ['claude-sonnet', lp.resolveProfile(shipped, 'claude-sonnet', { effort: 2, slots: { session_ref: SESSION_REF } })],
    ['codex-gpt-5-5', lp.resolveProfile(shipped, 'codex-gpt-5-5', { effort: 2, slots: { workdir: '/tmp' } })],
    ['kimi', lp.resolveProfile(shipped, 'kimi', { effort: 2, slots: { workdir: '/tmp' } })],
  ];
  const rendered = three.map(([n, r]) => `${n}:${r.effort.value}`);
  if (rendered.join(' ') !== 'claude-sonnet:medium codex-gpt-5-5:medium kimi:--thinking') throw new Error(rendered.join(' '));
  // The tops DIFFER — which is the whole reason the closed four-level vocabulary was retired: it
  // could only be as wide as its narrowest member, so claude's `xhigh` was unspellable through it.
  const tops = three.map(([n, r]) => `${n}:${r.effort.of}`).join(' ');
  if (tops !== 'claude-sonnet:5 codex-gpt-5-5:3 kimi:2') throw new Error(tops);
  return `${rendered.join(' ')} | ladder sizes ${tops}`;
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
  // An inert profile declares NO range, so ANY rung is accepted on it — including one no dialed
  // profile in the shipped file would admit. That is the G-270 posture, not a missing bound.
  const r = lp.resolveProfile(lp.loadConfig(f), 'no-dial', { effort: 99 });
  if (r.effortInert !== true) throw new Error('inert not reported');
  if (r.argv.length !== 2) throw new Error(`argv grew: ${r.argv.join(' ')}`);
  return 'effortInert=true reported to the caller; argv unchanged';
});
check('(11) a rung outside THIS profile\'s range is refused, and the refusal NAMES the range', () => {
  const err = expectCode('E_UNKNOWN_EFFORT', () => lp.resolveProfile(shipped, 'codex-gpt-5-5', { effort: 4, slots: { workdir: '/tmp' } }));
  if (!/range 1\.\.3/.test(err.message)) throw new Error(err.message);
  // The CONTROL that makes it a range check rather than a ceiling: the same rung composes on a
  // profile whose ladder is longer, so nothing about "4" is refused — only "4 on codex".
  const ok = lp.resolveProfile(shipped, 'claude-sonnet', { effort: 4, slots: { session_ref: SESSION_REF } });
  if (ok.effort.value !== 'xhigh') throw new Error(ok.effort.value);
  // …and a level from the RETIRED abstract vocabulary is now refused as a non-integer, so a caller
  // left on the old scheme fails loudly instead of resolving to something plausible.
  expectCode('E_UNKNOWN_EFFORT', () => lp.resolveProfile(shipped, 'claude-sonnet', { effort: 'high', slots: { session_ref: SESSION_REF } }));
  return `${err.code}; rung 4 still composes on claude (xhigh); legacy 'high' refused`;
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
  try { top = lp.readHelp('codex', { helpArgs: ['--help'] }); } catch { throw new Skip('codex not installed on this host — the subcommand-page property is UNMEASURED here'); }
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

// ── 16/17/17b · task 7.87 — the widened slot vocabulary, and the control that it is still CLOSED ─
//
// Leg 17 is the one the widening's ruling demands: proving the new slot is ACCEPTED cannot
// distinguish "the vocabulary grew by one" from "the vocabulary stopped being closed", and the
// second silently retires the guard. So an unknown slot is PLANTED and the refusal is the assertion.
function writeSplitFixture(slotName) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lp-g1-'));
  const file = path.join(dir, 'split.yaml');
  fs.writeFileSync(file, yaml.dump({
    default_workdir_root: dir,
    profiles: {
      'g1-split': {
        // The G1 confinement split, written by the PROFILE: guidance-root = {workdir},
        // work-target = the add-dir operand. TWO path values in one command template.
        exec: { argv: ['claude', '-p', '--cd', '{workdir}', '--add-dir', `{${slotName}}`], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      },
    },
  }));
  return file;
}
check('(16) a profile can express the G1 split as TWO values — {workdir} AND {extra_dir}', () => {
  const c = lp.loadConfig(writeSplitFixture('extra_dir'));
  const r = lp.resolveProfile(c, 'g1-split', {
    slots: { workdir: '/srv/orchestrator-root', extra_dir: '/srv/repos/target' },
  });
  const tmpl = c.profiles['g1-split'].exec.argv.length;
  if (r.argv.length !== tmpl) throw new Error(`arity ${r.argv.length} != template ${tmpl}`);
  if (r.argv[3] !== '/srv/orchestrator-root') throw new Error(`workdir slot: ${r.argv[3]}`);
  if (r.argv[5] !== '/srv/repos/target') throw new Error(`extra_dir slot: ${r.argv[5]}`);
  return `${r.argv.join(' ')} — the add-dir flag is written by the PROFILE, not hand-composed`;
});
check('(17) PLANTED UNKNOWN SLOT — the vocabulary is still CLOSED after the widening', () => {
  // Same fixture shape, one slot name changed to something nobody declared. If the widening had
  // opened the set instead of extending it, this would load clean and the leg would go red.
  const err = expectCode('E_UNKNOWN_SLOT', () => lp.loadConfig(writeSplitFixture('not_a_real_slot')));
  if (err.details.slot !== '{not_a_real_slot}') throw new Error(`slot=${err.details.slot}`);
  return `${err.code} at config LOAD, slot=${err.details.slot}`;
});
check('(17b) …and a caller still cannot SUPPLY {extra_dir} to a profile that declares none', () => {
  // The second half of "closed": the load gate bounds what a PROFILE may write, this bounds what a
  // CALLER may fill. Widening the first must not widen the second.
  const err = expectCode('E_RAW_FLAG', () => lp.resolveProfile(shipped, 'test-sleep', {
    slots: { extra_dir: '/srv/repos/target' },
  }));
  return `${err.code} — declared-slots-only, unchanged`;
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
// EXIT CHANNEL for a skip: 2 = INOPERATIVE, the suite runner's existing third class ("the probe
// self-declared it could not meaningfully run" — counted as attempted, kept OUT of `failed`, so a
// by-design refusal never turns the scheduled verdict permanently RED, d-probe-suite-verdict-delivery).
// A FAIL still wins the exit code. On the VPS every leg measures, so exit stays 0 there; on a host
// missing a harness CLI the run now reads INOPERATIVE instead of falsely GREEN.
const exitCode = failed ? 1 : skipped.length ? 2 : 0;
const body = [
  'probe: probe-launch-profiles',
  `started: ${started.toISOString()}`,
  'command: node launch-profiles/probes/probe-launch-profiles.js',
  ...lines,
  `status: ${failed ? 'FAIL' : skipped.length ? 'INOPERATIVE' : 'PASS'}`,
  `checks: ${lines.length} (${lines.filter((l) => l.startsWith('PASS')).length} pass, ${lines.filter((l) => l.startsWith('FAIL')).length} fail, ${skipped.length} skipped)`,
  `exit: ${exitCode}`,
  `wall_ms: ${ended - started}`,
  `ended: ${ended.toISOString()}`,
  '',
].join('\n');
fs.writeFileSync(OUT, body);
process.stdout.write(body);
// A truncated run must never read greener than a complete one (G-121): the check count above is
// asserted by the reader, and the exit code is the authority.
process.exit(exitCode);

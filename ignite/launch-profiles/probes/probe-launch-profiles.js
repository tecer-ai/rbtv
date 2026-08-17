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
  // ⚠ FILED UNDER `jobs:`, NOT `launch-specs:` (7.787). A halves-shaped fixture pins no model, so
  // it has no (harness, model) to be keyed by — which is exactly the split
  // `#d-abolish-profile-names` sub-ruling 1 introduced. The two blocks share one validator, so this
  // still exercises the same schema path it always did.
  yaml && fs.writeFileSync(file, yaml.dump({
    default_workdir_root: dir,
    'launch-specs': { probe: { 'probe-model': {
      exec: { argv: ['probe', '--model', 'probe-model', '1'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      workdir_root: dir,
      caps: { memory_max: '64M' },
    } } },
    jobs: {
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
// ── 1 · resolve by the ONE address a launch spec has: its (harness, model) — or a job's NAME ──
// 7.787: `resolveProfile(config, 'a-name')` is `resolveLaunchSpec(config, {harness, model})`. Leg
// 1c is the abolition's own assertion — a caller cannot select a launch spec by any name at all.
check('(1) an uncastable (harness, model) is refused typed', () => {
  const err = expectCode('E_UNKNOWN_LAUNCH_SPEC', () => lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'no-such-model' }));
  return err.code;
});
check('(1b) a castable pair resolves', () => {
  const r = lp.resolveLaunchSpec(shipped, { harness: 'codex', model: 'gpt-5.5' }, { slots: { workdir: '/tmp' } });
  if (r.argv[0] !== 'codex') throw new Error(`argv0 ${r.argv[0]}`);
  return r.argv.join(' ');
});
check('(1c) THE ABOLITION — a NAME selects nothing; only the pair or a job name addresses a spec', () => {
  // The retired names are planted deliberately: they were the only unit a caller could select
  // before `#d-abolish-profile-names`, and if `launch-specs:` ever regained a name layer this leg
  // would go green for the wrong reason.
  for (const dead of ['claude-opus', 'claude-fable', 'codex-gpt-5-5', 'kimi']) {
    expectCode('E_UNKNOWN_LAUNCH_SPEC', () => lp.resolveLaunchSpec(shipped, { job: dead }));
    expectCode('E_UNKNOWN_LAUNCH_SPEC', () => lp.resolveLaunchSpec(shipped, { harness: dead, model: dead }));
  }
  // CONTROL, so the leg is not passing because everything is refused: the `jobs:` block DOES still
  // address by name (sub-ruling 1 — "a job's name IS its identity"), and `test-sleep` lives there.
  const job = lp.resolveLaunchSpec(shipped, { job: 'test-sleep' });
  if (job.argv[0] !== 'sleep') throw new Error(`the jobs: block stopped resolving: ${job.argv.join(' ')}`);
  return 'every retired profile NAME refuses on both address forms; jobs: still resolves test-sleep';
});

// ── 2 · rejects raw flags — THE DISCRIMINATING CONTROL ───────────────────────────────────────
check('(2) undeclared slot key REFUSED by the resolver', () => {
  const err = expectCode('E_RAW_FLAG', () => lp.resolveLaunchSpec(shipped, { job: 'test-sleep' }, {
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
  const r = lp.resolveLaunchSpec(fx, { job: 'both-halves' }, { slots: { workdir: '/tmp/x --rm -rf /' } });
  const tmpl = fx.jobs['both-halves'].command.caged.argv.length;
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
  const r = lp.resolveLaunchSpec(fx, { job: 'both-halves' }, { slots: { workdir: '/tmp' } });
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
    const r=lp.resolveLaunchSpec(c,{job:'both-halves'},{slots:{workdir:'/tmp'}});
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
    try { const r=lp.resolveLaunchSpec(c,{job:'caged-only'}); console.log('UNEXPECTED PASS half='+r.half+' argv='+r.argv.join(' ')); }
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
  const r = lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'claude-sonnet-5' }, { effort: 4, slots: { session_ref: SESSION_REF } });
  if (!r.argv.includes('--effort') || !r.argv.includes('xhigh')) throw new Error(r.argv.join(' '));
  if (r.effort.of !== 5) throw new Error(`ladder size ${r.effort.of}`);
  return `dialect=${r.effort.dialect} rung=${r.effort.rung}/${r.effort.of} argv-tail=${r.argv.slice(-2).join(' ')}`;
});
check('(9) …and through a SECOND, differently-spelled dialect (codex: a -c override, 3 rungs)', () => {
  const r = lp.resolveLaunchSpec(shipped, { harness: 'codex', model: 'gpt-5.5' }, { effort: 3, slots: { workdir: '/tmp' } });
  const tail = r.argv.slice(-2).join(' ');
  if (!tail.includes('model_reasoning_effort=high')) throw new Error(tail);
  if (r.effort.dialect !== 'thinking' || r.effort.of !== 3) throw new Error(`${r.effort.dialect}/${r.effort.of}`);
  return `dialect=${r.effort.dialect} rung=${r.effort.rung}/${r.effort.of} argv-tail=${tail}`;
});
check('(9b) ONE rung number, three harness spellings — and each ladder has its OWN top', () => {
  const three = [
    ['claude/claude-sonnet-5', lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'claude-sonnet-5' }, { effort: 2, slots: { session_ref: SESSION_REF } })],
    ['codex/gpt-5.5', lp.resolveLaunchSpec(shipped, { harness: 'codex', model: 'gpt-5.5' }, { effort: 2, slots: { workdir: '/tmp' } })],
    ['kimi/kimi-code/kimi-for-coding', lp.resolveLaunchSpec(shipped, { harness: 'kimi', model: 'kimi-code/kimi-for-coding' }, { effort: 2, slots: { workdir: '/tmp' } })],
  ];
  const rendered = three.map(([n, r]) => `${n}:${r.effort.value}`);
  if (rendered.join(' ') !== 'claude/claude-sonnet-5:medium codex/gpt-5.5:medium kimi/kimi-code/kimi-for-coding:--thinking') throw new Error(rendered.join(' '));
  // The tops DIFFER — which is the whole reason the closed four-level vocabulary was retired: it
  // could only be as wide as its narrowest member, so claude's `xhigh` was unspellable through it.
  const tops = three.map(([n, r]) => `${n}:${r.effort.of}`).join(' ');
  if (tops !== 'claude/claude-sonnet-5:5 codex/gpt-5.5:3 kimi/kimi-code/kimi-for-coding:2') throw new Error(tops);
  return `${rendered.join(' ')} | ladder sizes ${tops}`;
});
check('(10) an INERT dial is STATED, never silently dropped', () => {
  const dir = path.dirname(fixture);
  const f = path.join(dir, 'inert.yaml');
  fs.writeFileSync(f, yaml.dump({
    default_workdir_root: dir,
    jobs: {
      'no-dial': {
        exec: { argv: ['sleep', '1'], prompt: 'stdin' },
        effort: { inert: true },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      },
    },
    'launch-specs': { probe: { 'probe-model': {
      exec: { argv: ['probe', '--model', 'probe-model', '1'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' }, workdir_root: dir, caps: { memory_max: '64M' },
    } } },
  }));
  // An inert profile declares NO range, so ANY rung is accepted on it — including one no dialed
  // profile in the shipped file would admit. That is the G-270 posture, not a missing bound.
  const r = lp.resolveLaunchSpec(lp.loadConfig(f), { job: 'no-dial' }, { effort: 99 });
  if (r.effortInert !== true) throw new Error('inert not reported');
  if (r.argv.length !== 2) throw new Error(`argv grew: ${r.argv.join(' ')}`);
  return 'effortInert=true reported to the caller; argv unchanged';
});
check('(11b) an unknown effort-block key is a LOAD failure (KNOWN_EFFORT_KEYS mutant)', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lp-unk-effort-'));
  const f = path.join(dir, 'unknown-effort-key.yaml');
  fs.writeFileSync(f, yaml.dump({
    default_workdir_root: dir,
    'launch-specs': { probe: { 'probe-model': {
      exec: { argv: ['probe', '--model', 'probe-model'], prompt: 'stdin' },
      effort: {
        dialect: 'x', rungs: ['low'], argv: ['--effort', '{effort}'],
        not_a_real_effort_key: true,
      },
      session_ref: { source: 'cwd-implicit' }, workdir_root: dir, caps: { memory_max: '64M' },
    } } },
  }));
  const err = expectCode('E_CONFIG_LOAD', () => lp.loadConfig(f));
  if (!/not_a_real_effort_key/.test(err.message)) throw new Error(err.message);
  return `${err.code} names the unknown key`;
});

check('(11) a rung outside THIS profile\'s range is refused, and the refusal NAMES the range', () => {
  const err = expectCode('E_UNKNOWN_EFFORT', () => lp.resolveLaunchSpec(shipped, { harness: 'codex', model: 'gpt-5.5' }, { effort: 4, slots: { workdir: '/tmp' } }));
  if (!/range 1\.\.3/.test(err.message)) throw new Error(err.message);
  // The CONTROL that makes it a range check rather than a ceiling: the same rung composes on a
  // profile whose ladder is longer, so nothing about "4" is refused — only "4 on codex".
  const ok = lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'claude-sonnet-5' }, { effort: 4, slots: { session_ref: SESSION_REF } });
  if (ok.effort.value !== 'xhigh') throw new Error(ok.effort.value);
  // …and a level from the RETIRED abstract vocabulary is now refused as a non-integer, so a caller
  // left on the old scheme fails loudly instead of resolving to something plausible.
  expectCode('E_UNKNOWN_EFFORT', () => lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'claude-sonnet-5' }, { effort: 'high', slots: { session_ref: SESSION_REF } }));
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
    'launch-specs': { claude: { 'probe-split-model': {
        // The G1 confinement split, written by the PROFILE: guidance-root = {workdir},
        // work-target = the add-dir operand. TWO path values in one command template.
        exec: { argv: ['claude', '-p', '--model', 'probe-split-model', '--cd', '{workdir}', '--add-dir', `{${slotName}}`], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: dir,
        caps: { memory_max: '64M' },
      } } },
  }));
  return file;
}
check('(16) a profile can express the G1 split as TWO values — {workdir} AND {extra_dir}', () => {
  const c = lp.loadConfig(writeSplitFixture('extra_dir'));
  const r = lp.resolveLaunchSpec(c, { harness: 'claude', model: 'probe-split-model' }, {
    slots: { workdir: '/srv/orchestrator-root', extra_dir: '/srv/repos/target' },
  });
  const tmpl = c.launchSpecs['claude/probe-split-model'].exec.argv.length;
  if (r.argv.length !== tmpl) throw new Error(`arity ${r.argv.length} != template ${tmpl}`);
  if (r.argv[5] !== '/srv/orchestrator-root') throw new Error(`workdir slot: ${r.argv[5]}`);
  if (r.argv[7] !== '/srv/repos/target') throw new Error(`extra_dir slot: ${r.argv[7]}`);
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
  const err = expectCode('E_RAW_FLAG', () => lp.resolveLaunchSpec(shipped, { job: 'test-sleep' }, {
    slots: { extra_dir: '/srv/repos/target' },
  }));
  return `${err.code} — declared-slots-only, unchanged`;
});

// ── 15 · criterion 6 — no second profile file in the repo ───────────────────────────────────
check('(15) exactly ONE file in the repo defines launch specs', () => {
  const out = execFileSync('git', ['grep', '-l', '^launch-specs:', '--', '*.yaml', '*.yml'], {
    cwd: path.resolve(IGNITE_ROOT, '..'), encoding: 'utf8',
  }).trim().split('\n').filter(Boolean);
  if (out.length !== 1) throw new Error(`spec-defining files: ${out.join(', ')}`);
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

'use strict';

// probe-effort-lane — the DAEMON's effort lane, end to end (owner ruling
// `d-0811lp-effort-lane-build-now`, run exec-0811-live-proofs, 2026-08-11).
//
// WHAT THIS COVERS THAT probe-launch-profiles DOES NOT. That probe exercises `resolveProfile`,
// which the daemon does NOT call (G-144 stands: half selection is still 7.43/7.54). This one walks
// the path a channel-master DM sitting actually takes: bridge config -> forward-path enqueue args
// -> the catalogue job's args_schema -> ticker -> `spawn.js#composeArgv`. Every leg below is a REAL
// call into the shipped module, never a re-implementation of what it should do.
//
// THE CONTROL THAT MAKES LEG 6 A CONTROL. "The new job id admits `effort`" is compatible with a
// store that admits everything, so the leg asserts BOTH: the new schema ACCEPTS the arg AND the
// pre-ruling `chat-agent` shape still REFUSES it with `unknown argument: effort`. That second half
// fails by construction on a store whose door was weakened rather than a schema widened.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const lp = require('../../launch-profiles');
const { composeArgv } = require('../spawn');
const { openHeartStore, closeHeartStore } = require('../../../state-store/heart/heart-store');
const { resolveConfig } = require('../../../chat/config');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..', '..');
const SHIPPED = path.join(IGNITE_ROOT, 'envelope', 'spawn-profiles.yaml');
const OUT = path.join(__dirname, 'probe-effort-lane.out');

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

function expectThrow(re, fn) {
  try {
    fn();
  } catch (err) {
    if (re.test(err.message)) return err;
    throw new Error(`message did not match ${re}: ${err.message}`);
  }
  throw new Error('expected a refusal, but the call SUCCEEDED');
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'effort-lane-'));
const shipped = lp.loadConfig(SHIPPED, { seatBindValidator: () => {} });
const SID = '00000000-0000-4000-8000-000000000000';
const dataRoot = path.join(tmp, 'data');
fs.mkdirSync(dataRoot, { recursive: true });

// ── 1 · the DAEMON's own composer applies a rung, on a claude profile ────────────────────────
check('(1) composeArgv appends the claude rung the profile declares (rung 4 -> xhigh)', () => {
  const { argv } = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, tmp, 'hi', dataRoot, null, 4, 'claude/claude-opus-5');
  const at = argv.indexOf('--effort');
  if (at < 0 || argv[at + 1] !== 'xhigh') throw new Error(argv.join(' '));
  return `…${argv.slice(at, at + 2).join(' ')}`;
});

// ── 2 · …and on a NON-claude harness, whose dial is spelled entirely differently ─────────────
check('(2) …and on codex, whose dial is a `-c` config override, not a flag (rung 2 -> medium)', () => {
  const { argv } = composeArgv(shipped.launchSpecs['codex/gpt-5.5'], 'headless', SID, tmp, 'hi', dataRoot, null, 2, 'codex/gpt-5.5');
  const tail = argv.slice(-2).join(' ');
  if (tail !== '-c model_reasoning_effort=medium') throw new Error(argv.join(' '));
  return tail;
});

check('(2b) …and on opencode, whose dial is `--variant` (kimi-for-coding/k3 rung 1 -> low, rung 2 -> high)', () => {
  // The kimi HARNESS is retired; the models live on opencode. Retargeting here keeps the
  // three-harness / three-spelling property (claude `--effort`, codex `-c`, opencode `--variant`)
  // and proves the models still compose. The old `--no-thinking`/`--thinking` mapping died with
  // the harness key — asserting it now would be asserting the retired world.
  const key = 'opencode/kimi-for-coding/k3';
  const spec = shipped.launchSpecs[key];
  if (!spec) throw new Error(`${key} missing — retiring the harness must not drop the models`);
  const lo = composeArgv(spec, 'headless', SID, tmp, 'hi', dataRoot, null, 1, key).argv;
  const hi = composeArgv(spec, 'headless', SID, tmp, 'hi', dataRoot, null, 2, key).argv;
  const tail = (a) => a.slice(-2).join(' ');
  if (tail(lo) !== '--variant low' || tail(hi) !== '--variant high') {
    throw new Error(`${lo.join(' ')} | ${hi.join(' ')}`);
  }
  return 'rung 1 and rung 2 render as this harness\'s --variant words; kimi models compose on opencode';
});

// ── 3 · a rung outside the profile's ladder is REFUSED, naming the range ─────────────────────
check('(3) out-of-range refuses NAMING the profile\'s own range (codex gpt-5.5 has 4 rungs, not 5)', () => {
  const err = expectThrow(/range 1\.\.4/, () =>
    composeArgv(shipped.launchSpecs['codex/gpt-5.5'], 'headless', SID, tmp, 'hi', dataRoot, null, 5, 'codex/gpt-5.5'));
  if (err.code !== 'E_UNKNOWN_EFFORT') throw new Error(`code=${err.code}`);
  // A CONTROL: the SAME rung is in range on claude (5-rung ladder), so the refusal is the profile's, not a ceiling.
  const ok = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, tmp, 'hi', dataRoot, null, 5, 'claude/claude-opus-5').argv;
  if (!ok.includes('max')) throw new Error('rung 5 should compose on claude');
  return `${err.code}: ${err.message.split('(')[0].trim()}`;
});

check('(3b) a non-integer / zero / negative rung refuses before any ladder is consulted', () => {
  for (const bad of ['high', 0, -1, 2.5]) {
    const err = expectThrow(/INTEGER RUNG/, () =>
      composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, tmp, 'hi', dataRoot, null, bad, 'claude/claude-opus-5'));
    if (err.code !== 'E_UNKNOWN_EFFORT') throw new Error(`${bad}: code=${err.code}`);
  }
  return 'high, 0, -1, 2.5 all refused E_UNKNOWN_EFFORT';
});

// ── 4 · an INERT profile ACCEPTS the rung and emits nothing (G-270) ──────────────────────────
check('(4) an inert dial ACCEPTS any rung and composes no argv for it (claude-haiku)', () => {
  const base = composeArgv(shipped.launchSpecs['claude/claude-haiku-4-5'], 'headless', SID, tmp, 'hi', dataRoot, null, null, 'claude/claude-haiku-4-5').argv;
  const with9 = composeArgv(shipped.launchSpecs['claude/claude-haiku-4-5'], 'headless', SID, tmp, 'hi', dataRoot, null, 9, 'claude/claude-haiku-4-5').argv;
  if (base.join(' ') !== with9.join(' ')) throw new Error(with9.join(' '));
  // …and the resolver REPORTS it inert rather than the caller inferring it from an unchanged argv.
  const r = lp.resolveLaunchSpec(shipped, { harness: 'claude', model: 'claude-haiku-4-5' }, { effort: 9, slots: { session_ref: SID } });
  if (r.effortInert !== true) throw new Error('effortInert not reported');
  return 'argv byte-identical with and without a rung; effortInert=true reported';
});

// ── 5 · ABSENT effort is byte-for-byte the pre-ruling behaviour ──────────────────────────────
check('(5) absent effort changes nothing — every pre-ruling caller is unaffected', () => {
  const a = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, tmp, 'hi', dataRoot, null).argv;
  const b = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, tmp, 'hi', dataRoot, null, null, 'claude/claude-opus-5').argv;
  // ⚠ THE SEPARATOR IS A LITERAL NUL BYTE AND MUST STAY ONE — do not "fix" it to a space.
  // NUL cannot occur in an argv element, so this join is INJECTIVE: ['a b'] compares UNEQUAL to
  // ['a','b']. A space separator equates them and silently weakens this regression control. The
  // cost is that git reports the whole file as binary. A reviewer has now read the raw byte as a
  // typo and proposed exactly that weakening, which is why this note exists. The error message
  // below joins with a space DELIBERATELY — that one is for humans, not for the comparison.
  if (a.join(' ') !== b.join(' ')) throw new Error(`${a.join(' ')} != ${b.join(' ')}`);
  if (a.includes('--effort')) throw new Error('an unrequested effort appeared');
  return 'no --effort, and the 7-arg call is identical to the 9-arg one with null';
});

// ── 6 · the enqueue door: the NEW schema admits `effort`, the OLD one still refuses it ───────
check('(6) a job whose args_schema declares `effort` admits it — and the pre-ruling shape refuses', () => {
  const dbPath = path.join(tmp, 'heart.db');
  const store = openHeartStore({ dbPath });
  try {
    // ⚠ NEITHER SHAPE DECLARES `profile` ANY MORE (7.787): `launch-agent`'s REQUIRED_ARGS is empty
    // and the argument is gone from the wire. The leg's SUBJECT is unchanged and still
    // discriminating — `effort` is admitted by the shape that declares it and refused by the one
    // that does not, which is the pre/post-ruling pair this control was written for.
    const OLD = { required: {}, optional: { prompt: 'string', workdir: 'string' } };
    const NEW = { required: {}, optional: { prompt: 'string', workdir: 'string', effort: 'integer' } };
    for (const [id, schema] of [['probe-chat-old', OLD], ['probe-chat-v2', NEW]]) {
      store.registerJob({
        jobId: id, actionType: 'launch-agent', function: 'launch-worker',
        argsSchema: JSON.stringify(schema),
        description: 'probe fixture',
      });
    }
    const RUN_AT = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    const args = JSON.stringify({ prompt: 'x', effort: 4 });
    // ACCEPTS — through the store's real enqueue door, not a re-read of the schema.
    store.enqueue({ jobId: 'probe-chat-v2', args, sessionMode: 'headless', triggerKind: 'scheduled', runAt: RUN_AT, enqueuedBy: 'probe' });
    // …and the CONTROL: the same args on the pre-ruling schema is the exact refusal that made a
    // new catalogue id necessary (registration is create-only — the old id cannot be widened).
    const err = expectThrow(/unknown argument: effort/, () =>
      store.enqueue({ jobId: 'probe-chat-old', args, sessionMode: 'headless', triggerKind: 'scheduled', runAt: RUN_AT, enqueuedBy: 'probe' }));
    return `v2 accepted; old refused "${err.message}"`;
  } finally {
    closeHeartStore(store);
  }
});

// ── 7 · the bridge config reads the knob, and refuses a shape the enqueue door would ─────────
check('(7) the chat transport names NO effort — `master_effort` is not read at all', () => {
  // ⚑ INVERTED 2026-08-11 (launch-cast unification, owner ruling D2). This arm used to assert that
  // `chat/config.js` READS `master_effort` and range-checks it. That key is DELETED: the
  // transport no longer names execution — not the model, not the harness, not the rung — so a
  // config still carrying it must be INERT rather than honoured. Reading it again is the
  // regression this now guards.
  const withKey = path.join(tmp, 'chat-with-effort.json');
  fs.writeFileSync(withKey, JSON.stringify({ master_profile: 'claude-opus', master_effort: 4 }));
  const c = resolveConfig({ configFile: withKey });
  if ('masterEffort' in c || 'masterProfile' in c || 'goalProfile' in c) {
    throw new Error(`the transport still surfaces execution keys: ${Object.keys(c).filter((k) => /master(Effort|Profile)|goalProfile/.test(k)).join(',')}`);
  }
  // …and the CONTROL that this is not vacuous: the loader DID parse the file, so "absent" means
  // "not read", never "nothing was loaded". Without it, a resolveConfig that threw and returned {}
  // would read green.
  if (!c.sessionProfile && !c.stateFile && !c.channelPrefix) {
    throw new Error('the config did not load at all — the absence above proves nothing');
  }
  return 'master_effort/master_profile/goal_profile carried in the file, surfaced by none';
});

// ── 8 · the DAEMON'S OWN DECORATION forwards the operand it was handed ───────────────────────
// Every leg above calls `composeArgv` directly, so all of them stayed green while the daemon's
// headed/headless fork in `runtime/index.js` silently ATE the rung: that wrapper is a positional
// pass-through, and a pass-through pinned to an old arity drops whatever operand was added last.
// It has done so twice — `resumeRef` (measured 2026-08-08, execs 24666/24669/24672) and `effort`
// (2026-08-11, this leg). The rule this asserts is therefore the CLASS, not the operand: the
// headless forward must be REST-ARGS, so no future operand can be dropped there again.
// Source-shaped, and stated as such: `runtime/index.js` is a boot script that calls `main()` on
// require, so there is no seam to call the decoration through. Same posture as
// probe-caged-settings, which greps `supervisor/spawn/` for profile literals.
check('(8) runtime/index.js forwards the spawn operands WHOLE — no arity pin on the pass-through', () => {
  const src = fs.readFileSync(path.join(IGNITE_ROOT, 'runtime', 'index.js'), 'utf8');
  const fwd = /return spawnManager\.spawn\(([^)]*)\);/.exec(src);
  if (!fwd) throw new Error('no headless pass-through found in runtime/index.js — has the decoration moved?');
  if (!fwd[1].includes('...')) {
    throw new Error(
      `the decoration forwards a PINNED positional list — spawnManager.spawn(${fwd[1]}) — so every `
      + 'operand added to spawn() after it is silently dropped; forward with rest args instead',
    );
  }
  return `spawnManager.spawn(${fwd[1]})`;
});

// ── 9 · THE SEAT'S OWN `effort:` WORD REACHES THE DAEMON DOOR (owner ruling, 2026-08-11) ─────
//
// Legs 1-8 all hand the rung in as a NUMBER, so every one of them stayed green while the seat's
// own declaration was read by nobody. These walk the chain that was missing, module by real
// module: `spawn.js#seatDeclaresValue` reads a seat.md off disk, `catalog.js#effortRungFor` turns
// the harness's WORD into that profile's rung number, `composeArgv` composes it. Nothing is
// stubbed — a fixture that faked the descriptor read would prove the resolver and not the fix
// (the standing reason `probe-binding-catalog` writes real descriptors too).
//
// ⚠ THE SEPARATOR IN THE ARGV COMPARISONS BELOW IS THE SAME NUL LEG 5 STATES IN FULL — written
// here as the `\0` ESCAPE rather than a raw byte, so this edit adds no new binary bytes to the
// file. Same character, same injectivity, do not "fix" either spelling to a space.
const { seatDeclaresValue, launchSpecForSeat } = require('../spawn');
const cat = require('../../launch-profiles/catalog');
const quiet = () => {};

// A REAL descriptor in a real folder: `materialize-seats.py#_descriptor_frontmatter` emits the
// cast as plain frontmatter scalars, all three or none, and that is exactly what this writes.
function seatFixture(name, fm) {
  const dir = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'effort-seat-')), name);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'), `---\n${fm.join('\n')}\n---\n\n# ${name}\n`);
  return dir;
}
const OPUS_CAST = ['harness: claude', 'model: claude-opus-5'];

check('(9) a seat declaring `effort: xhigh` composes the rung ITS OWN profile numbers it at', () => {
  const dir = seatFixture('plan-writer', [...OPUS_CAST, 'effort: xhigh']);
  const word = seatDeclaresValue(dir, 'effort');            // the shipped descriptor reader
  const { rung, inert } = cat.effortRungFor(shipped.launchSpecs['claude/claude-opus-5'], word, 'claude-opus', 'plan-writer');
  if (word !== 'xhigh' || rung !== 4 || inert !== false) throw new Error(`word=${word} rung=${rung} inert=${inert}`);
  const { argv } = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, dir, 'hi', dataRoot, null, rung, 'claude/claude-opus-5');
  const at = argv.indexOf('--effort');
  if (at < 0 || argv[at + 1] !== 'xhigh') throw new Error(argv.join(' '));
  return `seat.md 'xhigh' -> rung 4 -> ${argv.slice(at, at + 2).join(' ')}`;
});

check('(9a) CONTROL: the SAME fixture with the `effort:` LINE DELETED composes no effort at all', () => {
  // THE leg that discriminates reading-the-descriptor from a hardcoded push. It differs from (9)
  // in exactly one line of one file; a composer that pushed a rung of its own would pass (9) and
  // fail here, and a composer that read nothing would fail (9) and pass here.
  const dir = seatFixture('plan-writer', OPUS_CAST);
  const word = seatDeclaresValue(dir, 'effort');
  if (word !== '') throw new Error(`the reader invented a word: ${JSON.stringify(word)}`);
  const { rung, inert } = cat.effortRungFor(shipped.launchSpecs['claude/claude-opus-5'], word, 'claude-opus', 'plan-writer');
  if (rung !== null || inert !== false) throw new Error(`rung=${rung} inert=${inert}`);
  const r = lp.resolveEffort(shipped.launchSpecs['claude/claude-opus-5'], rung, 'claude/claude-opus-5');
  if (r.argv.length !== 0 || r.applied !== null) throw new Error(`argv=${r.argv.join(' ')} applied=${JSON.stringify(r.applied)}`);
  const full = composeArgv(shipped.launchSpecs['claude/claude-opus-5'], 'headless', SID, dir, 'hi', dataRoot, null, rung, 'claude/claude-opus-5').argv;
  if (full.includes('--effort')) throw new Error(`an effort appeared where none was declared: ${full.join(' ')}`);
  return 'no `effort:` line -> rung null, applied null, zero effort tokens';
});

check('(9b) a word the ladder does not carry REFUSES, naming the word, the seat and the ladder', () => {
  const dir = seatFixture('plan-writer', [...OPUS_CAST, 'effort: nonesuch']);
  const err = expectThrow(/nonesuch/, () =>
    cat.effortRungFor(shipped.launchSpecs['claude/claude-opus-5'], seatDeclaresValue(dir, 'effort'), 'claude-opus', 'plan-writer'));
  if (err.code !== 'E_UNKNOWN_EFFORT') throw new Error(`code=${err.code}`);
  if (!/1=low, 2=medium, 3=high, 4=xhigh, 5=max/.test(err.message)) throw new Error(`the ladder is not NUMBERED in the refusal: ${err.message}`);
  if (!/plan-writer/.test(err.message)) throw new Error(`the seat is not named: ${err.message}`);
  // ⚠ AND THE REFUSAL IS THE RIGHT ONE. Letting `indexOf`'s -1 flow onward would reach
  // `resolveEffort` and read "effort must be an INTEGER RUNG >= 1, got 0" — a true sentence about
  // a number nobody wrote, sending the reader hunting a rung instead of a stale word.
  if (/INTEGER RUNG/.test(err.message)) throw new Error('the -1 leaked downstream to resolveEffort');
  return `${err.code}: names 'nonesuch', the seat, and 1..5`;
});

check('(9c) an INERT dial ACCEPTS a declared word and REPORTS inert — the FLAG, not an empty argv', () => {
  const dir = seatFixture('haiku-seat', ['harness: claude', 'model: claude-haiku-4-5', 'effort: xhigh']);
  const r = cat.effortRungFor(shipped.launchSpecs['claude/claude-haiku-4-5'], seatDeclaresValue(dir, 'effort'), 'claude-haiku', 'haiku-seat');
  // ⚠ ASSERT THE FLAG. An empty argv is ALSO what a swallowed throw and an undeclared word
  // produce, so argv-emptiness alone cannot tell accept-and-report (G-270) from silent drop.
  if (r.inert !== true) throw new Error(`inert=${r.inert} — an empty argv alone is indistinguishable from a drop`);
  if (r.rung !== null) throw new Error(`an inert dial has no ladder to number against: rung=${r.rung}`);
  const with9c = composeArgv(shipped.launchSpecs['claude/claude-haiku-4-5'], 'headless', SID, dir, 'hi', dataRoot, null, r.rung, 'claude/claude-haiku-4-5').argv;
  const bare = composeArgv(shipped.launchSpecs['claude/claude-haiku-4-5'], 'headless', SID, dir, 'hi', dataRoot, null, null, 'claude/claude-haiku-4-5').argv;
  if (with9c.join('\0') !== bare.join('\0')) throw new Error(with9c.join(' '));
  return 'inert=true REPORTED; argv byte-identical to the undialed composition';
});

check('(9d) an OPENCODE cast composes `--variant`, on THIS MODEL\'s ladder', () => {
  const dir = seatFixture('glm-seat', ['harness: opencode', 'model: zai-coding-plan/glm-5.2', 'effort: max']);
  const { key: name } = launchSpecForSeat(shipped.launchSpecs, dir, quiet);   // the cast, and nothing else
  if (name !== 'opencode/zai-coding-plan/glm-5.2') throw new Error(`cast resolved to ${name}`);
  const { rung, inert } = cat.effortRungFor(shipped.launchSpecs[name], seatDeclaresValue(dir, 'effort'), name, 'glm-seat');
  if (inert !== false) throw new Error('opencode still reports an inert dial — the ladder is not declared');
  const argv = composeArgv(shipped.launchSpecs[name], 'headless', SID, dir, 'hi', dataRoot, null, rung, name).argv;
  const at = argv.indexOf('--variant');
  // Position: the flag lands AFTER `run` (opencode's subcommand must come first) and the prompt
  // never rides argv on this profile at all — its carriage is `stdin`, so there is no positional
  // to land in front of.
  if (argv[1] !== 'run' || at < 2 || argv[at + 1] !== 'max') throw new Error(argv.join(' '));
  // …and the ladder is this MODEL's, not this harness's: glm-5.2 publishes only [high, max], so
  // `low` — a rung every other opencode model carries — is a refusal HERE. A copy-pasted ladder
  // would pass every assertion above this line and fail this one.
  const err = expectThrow(/low/, () => cat.effortRungFor(shipped.launchSpecs[name], 'low', name, 'glm-seat'));
  if (err.code !== 'E_UNKNOWN_EFFORT') throw new Error(`code=${err.code}`);
  return `${argv.slice(0, 2).join(' ')} … ${argv.slice(at, at + 2).join(' ')}; 'low' refused on this model's 2-rung ladder`;
});

// ── 10 · BOTH daemon doors actually read it, and a caller's rung still outranks the seat ──────
// Source-shaped for leg 8's reason, stated the same way: `spawn()` and `spawnSeat()` are closures
// minted inside `createSpawnManager`, so reaching either one needs a heart store, a config and a
// workspace — a fixture whose failure modes would outnumber the two lines under test. What is
// checkable without all that is that the two doors are WIRED, which is precisely the leg the
// pre-ruling code failed: the reader existed, the resolver existed, and neither door called them.
check('(10) both spawn doors read the seat\'s effort, and an explicit rung still wins', () => {
  const src = fs.readFileSync(path.join(IGNITE_ROOT, 'supervisor', 'spawn', 'spawn.js'), 'utf8');
  const bodyOf = (name) => {
    const i = src.indexOf(`async function ${name}(`);
    if (i < 0) throw new Error(`no ${name} door in spawn.js — has it moved?`);
    const j = src.indexOf('async function ', i + 16);
    return src.slice(i, j > 0 ? j : src.length);
  };
  for (const door of ['spawn', 'spawnSeat']) {
    if (!/seatEffortRung\(/.test(bodyOf(door))) throw new Error(`the ${door} door does not read the seat's declared effort`);
  }
  // PRECEDENCE, and `??` specifically: rung 0 is already a refusal downstream, but a `||` here
  // would silently re-open it by treating an explicit 0 as "unset" and substituting the seat's.
  if (!/effort \?\? /.test(src)) throw new Error('the caller-wins precedence (`effort ?? seat`) is not in spawn.js');
  // …and the CONTROL that this is not a grep of a comment: the helper must be DEFINED here too,
  // so a file that merely mentions the name in prose cannot pass.
  if (!/function seatEffortRung\(/.test(src)) throw new Error('seatEffortRung is named but never defined');
  return 'spawn() and spawnSeat() both call seatEffortRung; precedence is `??`';
});

const ended = new Date();
const body = [
  'probe: probe-effort-lane',
  `started: ${started.toISOString()}`,
  'command: node supervisor/spawn/probes/probe-effort-lane.js',
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
process.exit(failed ? 1 : 0);

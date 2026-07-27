'use strict';

// probe-profile-halves-refusal — G-144: the spawn path must REFUSE a half-shaped launch profile
// with a NAMED typed error, never crash the daemon with a bare TypeError.
//
// THE DEFECT (measured 2026-07-27, engineer s5): task 7.42 ruled the caged/portable half shape
// (`command: { caged:, portable: }`, #d-profile-source-unification (4)) and shipped the shared
// resolver with ONE live consumer — which is NOT spawn.js. So a profile declaring `command:`
// instead of `exec:`:
//   * PASSES config load (profiles.js validateProfile accepts either shape), and then
//   * crashes `composeArgv` (`profile.exec` -> `.prompt`) and `spawnSeat` (`profile.exec.argv`)
//     with `TypeError: Cannot read properties of undefined`.
// The config layer is not a backstop. An untyped TypeError out of the spawn path is the daemon
// falling over on a well-formed config — the failure mode a typed refusal exists to replace.
//
// SCOPE (leader #523): a TYPED REFUSAL at both sites, NOT half support. Routing spawn.js through
// resolveProfile() is the root-cause shape and is deliberately a later task (7.43/7.54 unbuilt).
//
// ⚠ THE ASSERTION IS THE NAMED CODE, NEVER "it did not crash." Exit 1 is the PRE-fix evidence;
// after the fix the expectation INVERTS to naming E_PROFILE_HALVES_UNSUPPORTED. "Did not crash"
// is also satisfied by a probe that never reached the line — G-121's shape.
//
// ⚠ THE SHIPPED CONFIG IS NEVER WRITTEN. The fixture IS the failure mode: a half-shaped profile
// left in config/spawn-profiles.yaml kills the next daemon start (G-108 crash-looped it 46
// times). Every profile here is a runtime temp config; leg (6) proves the shipped file's sha256
// is byte-identical across the run. The hash is the PROOF, not the mechanism.
//
// Static — no daemon, no ports, no tmux, no live store beyond a temp sqlite file.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { loadConfig } = require('../config');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

const SHIPPED_CONFIG = path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml');
const EXPECTED_CODE = 'E_PROFILE_HALVES_UNSUPPORTED';

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

// The RULED half shape, taken from launch-profiles/profiles.js validateCommandHalves — not
// guessed. ⚠ My first fixture guessed `command: { argv, prompt }` and loadConfig refused it with
// a clean E_CONFIG_LOAD, which reads exactly like "the config layer already handles this, G-144
// is stale". A fixture that does not model the RULED shape does not test a weaker version of the
// claim; it tests a DIFFERENT claim, and answers confidently.
function halfShapedProfile(workRoot) {
  return {
    command: {
      caged: { argv: ['sleep', '3600'], prompt: 'stdin' },
      portable: { argv: ['sleep', '3600'], prompt: 'stdin' },
    },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: workRoot,
    caps: { memory_max: '64M', runtime_max: '1h' },
  };
}

function execShapedProfile(workRoot) {
  return {
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: workRoot,
    caps: { memory_max: '64M', runtime_max: '1h' },
  };
}

async function throwsFrom(fn) {
  try {
    await fn();
  } catch (err) {
    return err;
  }
  return null;
}

capture('probe-profile-halves-refusal', async (lines) => {
  const shippedBefore = sha256(SHIPPED_CONFIG);
  lines.push(`shipped config baseline sha256: ${shippedBefore}`);

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'halves-refusal-probe-'));
  let store = null;
  try {
    const dataRoot = path.join(tmp, 'data');
    const workRoot = path.join(tmp, 'work');
    const seatish = path.join(workRoot, 'seatish');
    // OUTSIDE workdir_root on purpose — leg (2)'s control lands here so it refuses LATER than
    // the guard instead of spawning a real worker.
    const escapeDir = path.join(tmp, 'outside');
    fs.mkdirSync(dataRoot, { recursive: true });
    fs.mkdirSync(seatish, { recursive: true });
    fs.mkdirSync(escapeDir, { recursive: true });

    const cfg = {
      bind: { host: '127.0.0.1', port: 7431 },
      spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
      default_workdir_root: workRoot,
      profiles: {
        'halves-only': halfShapedProfile(workRoot),
        'exec-only': execShapedProfile(workRoot),
      },
    };
    const cfgPath = path.join(tmp, 'spawn.yaml');
    fs.writeFileSync(cfgPath, yaml.dump(cfg));

    // ── (1) CONTROL — the half shape LOADS. This is the premise the whole defect rests on: if
    // config load refused it, there would be nothing downstream to crash. Asserted, not assumed.
    const loaded = loadConfig(cfgPath);
    const p = loaded.profiles['halves-only'];
    if ('exec' in p) throw new Error('(1) fixture is not half-shaped — it declares exec');
    if (!('command' in p)) throw new Error('(1) fixture lost its command halves through load');
    lines.push(`(1) CONTROL: the ruled half shape PASSES config load — 'exec' in profile = false, halves = [${Object.keys(p.command).join(', ')}]`);

    store = openHeartStore({ dbPath: path.join(tmp, 'heart.db') });
    const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

    // ── (2) CONTROL — REACHABILITY of the guard's negative case. An exec-shaped profile must
    // get PAST the guard. Without this leg a guard that refused EVERY profile would pass legs
    // (3) and (4) and look correct. (G-135's lesson turned on its own fix: assert the thing
    // under test is reachable from the fixture's state before asserting anything about it.)
    //
    // ⚠ IT PROVES THAT BY LANDING ON A *LATER* REFUSAL (E_WORKDIR_ESCAPE) RATHER THAN BY
    // SPAWNING. My first version passed a valid workdir, the exec-shaped profile spawned for
    // real, and the probe leaked a live `sleep 3600` under bwrap on every run — a probe with a
    // side effect on the box it is measuring. Getting past the guard is the whole claim; running
    // the worker is not part of it.
    const execErr = await throwsFrom(() => mgr.spawn('probe-halves-control', 'exec-only', 'headless', null, escapeDir, 'probe'));
    if (!execErr) throw new Error('(2) CONTROL did not refuse at all — it may have SPAWNED; the fixture must land on a later refusal, never launch a worker');
    if (execErr.code === EXPECTED_CODE) {
      throw new Error('(2) the guard REFUSED an exec-shaped profile — it refuses everything, so legs (3)/(4) prove nothing');
    }
    if (execErr.code !== 'E_WORKDIR_ESCAPE') {
      throw new Error(`(2) CONTROL landed on an unexpected refusal ${execErr.code || execErr.name} (expected the later E_WORKDIR_ESCAPE): ${execErr.message}`);
    }
    lines.push(`(2) CONTROL: exec-shaped profile passes the guard and lands on the LATER ${execErr.code} — the guard discriminates, and nothing was spawned`);

    // ── (3) spawn() — the headless/ticker door (composeArgv, spawn.js:160).
    const spawnErr = await throwsFrom(() => mgr.spawn('probe-halves-spawn', 'halves-only', 'headless', null, seatish, 'probe'));
    if (!spawnErr) throw new Error('(3) spawn() with a half-shaped profile did not throw at all');
    if (spawnErr instanceof TypeError || spawnErr.name === 'TypeError') {
      throw new Error(`(3) spawn() crashed with an UNTYPED TypeError (the G-144 defect, unfixed): ${spawnErr.message}`);
    }
    if (spawnErr.code !== EXPECTED_CODE) {
      throw new Error(`(3) spawn() refused with the WRONG code ${spawnErr.code || spawnErr.name} (expected ${EXPECTED_CODE}): ${spawnErr.message}`);
    }
    if (!/halves-only/.test(spawnErr.message)) {
      throw new Error(`(3) the refusal does not NAME the offending profile: ${spawnErr.message}`);
    }
    lines.push(`(3) spawn()      -> ${spawnErr.code}: ${spawnErr.message}`);

    // ── (4) spawnSeat() — the seat door (spawn.js:487). The guard must sit AHEAD of the
    // seatDir/workdir/identity gates: a caller who supplies no seat folder must still see the
    // profile-shape refusal, not a seatDir complaint that hides it. Passing seatDir here would
    // let a guard placed downstream of those gates pass this leg for the wrong reason.
    //
    // ⚠ WHAT THIS LEG DOES NOT PROVE, stated rather than implied: it does not reach spawn.js:487
    // and watch it crash. Reaching that line needs a fully materialized seat folder in a LIVE
    // run (parseSeatPath + checkRunLive + checkMaterializedSeat all pass), which a static probe
    // cannot stand up. So leg (4)'s PRE-fix evidence is a WRONG-CODE failure (the seat gates
    // refuse first), not a TypeError. The crash AT :487 is evidenced separately: the premise
    // audit measured `profile.exec.argv` on the ruled half shape throwing
    // `TypeError: Cannot read properties of undefined (reading 'argv')`. Leg (3) is the leg that
    // reaches a real crash site; this leg proves the guard's PLACEMENT, which is what makes :487
    // unreachable with a half-shaped profile.
    const seatErr = await throwsFrom(() => mgr.spawnSeat('probe-halves-seat', 'halves-only', { room: 'probe-room', seatName: 'probe-seat', seatDir: seatish, enqueuedBy: 'probe' }));
    if (!seatErr) throw new Error('(4) spawnSeat() with a half-shaped profile did not throw at all');
    if (seatErr instanceof TypeError || seatErr.name === 'TypeError') {
      throw new Error(`(4) spawnSeat() crashed with an UNTYPED TypeError (the G-144 defect, unfixed): ${seatErr.message}`);
    }
    if (seatErr.code !== EXPECTED_CODE) {
      throw new Error(`(4) spawnSeat() refused with the WRONG code ${seatErr.code || seatErr.name} (expected ${EXPECTED_CODE}): ${seatErr.message}`);
    }
    lines.push(`(4) spawnSeat()  -> ${seatErr.code}: ${seatErr.message}`);

    // ── (5) The refusal must be a SpawnError carrying structured details, not a bare Error with
    // a code bolted on — that is what makes it classifiable at the dispatch boundary at all.
    if (!seatErr.details || seatErr.details.profile !== 'halves-only') {
      throw new Error(`(5) the refusal carries no details.profile naming the offender: ${JSON.stringify(seatErr.details)}`);
    }
    if (!Array.isArray(seatErr.details.halves) || seatErr.details.halves.length === 0) {
      throw new Error(`(5) the refusal does not report which halves the profile declares: ${JSON.stringify(seatErr.details)}`);
    }
    lines.push(`(5) details: ${JSON.stringify(seatErr.details)}`);
  } finally {
    try { if (store) closeHeartStore(); } catch { /* fine */ }
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch { /* fine */ }
  }

  // ── (6) The shipped config was only ever READ. Byte-identical, proven by hash.
  const shippedAfter = sha256(SHIPPED_CONFIG);
  if (shippedAfter !== shippedBefore) {
    throw new Error(`(6) THE SHIPPED CONFIG CHANGED under this probe: ${shippedBefore} -> ${shippedAfter}`);
  }
  lines.push(`(6) shipped config byte-identical after the run: ${shippedAfter}`);
  lines.push('RESULT: a half-shaped profile is refused by NAME at both spawn doors; the guard discriminates; the shipped config is untouched.');
});

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { DispatchError, E_FANOUT_EXCEEDED } = require('./errors');

// ═════════════════════════════════════════════════════════════════════════════════════════════
// Boundary 10 — THE PER-DISPATCHER FAN-OUT CAP.
//
// Owner-ruled 2026-07-26, `decisions.md#d-sub-agent-population-bounds`, CMP-10 boundary 10:
// "a cap on how many sub-agents one dispatcher may run SIMULTANEOUSLY, carried as a config value
// (default 5) in the same shared config the lane's launch profiles live in (DEC-1 § Shared profile
// source)".
//
// ⚠⚠ THE ROW ORDERED THIS SEAT TO VERIFY WHERE `default 5` ACTUALLY LIVES RATHER THAN ASSUME IT
// HAS A HOME. IT HAS NONE. Measured 2026-07-28 on branch `ignite/core-daemon`:
//
//   grep -rniE "fan.?out|max_?concurr" ignite/ (excluding node_modules)  → 0 hits for any cap
//   ignite/config/spawn-profiles.yaml                                    → no such key
//   ignite/launch-profiles/profiles.js KNOWN_TOP_KEYS                    → {bind, auth, spawn,
//                                                                          profiles,
//                                                                          default_workdir_root}
//
// And the absence is STRUCTURAL, not merely unwritten: that root-key set is a CLOSED allowlist, so
// adding `sub_agent:` (or any other root key) to `spawn-profiles.yaml` today is a loud
// `E_CONFIG_LOAD` at config load. The ruled home for this value is not just empty — it is closed,
// and opening it means editing `ignite/launch-profiles/`, which task 7.43 is READ-ONLY to.
//
// ⇒ SO THE VALUE LIVES HERE, IN THIS CAPABILITY'S OWN CODE, AND THE ABSENCE IS REPORTED RATHER
// THAN QUIETLY SUPPLIED. There is deliberately NO caller override and NO environment override: an
// escape hatch on a fail-closed population bound is the bound's repeal.
const FANOUT_MAX = 5;

// ── WHO THE DISPATCHER IS ────────────────────────────────────────────────────────────────────
// CMP-10: the sub-agent is "attached to the caller's terminal" and "dies with the dispatching
// step/terminal". The cap is PER DISPATCHER, so the key must be stable across the several
// invocations one dispatcher makes — the process id of a single `dispatch` invocation is NOT that
// (it is the dispatching STEP, and each step is a new pid), so keying on it would make the cap
// unreachable by construction: a cap that can never bind is `bars.md` 11's *blind* shape.
//
// The POSIX SESSION ID is the stable identity of the caller's terminal: every process an agent
// runs from one pane shares it, and a different pane has a different one. Read from
// `/proc/self/stat` field 6 (Linux; ignite is a Linux daemon and this capability ships beside it).
// If it cannot be read, the cap FAILS CLOSED by refusing to guess an identity — see below.
function dispatcherId() {
  const stat = fs.readFileSync('/proc/self/stat', 'utf8');
  // Field 2 (comm) may contain spaces and parentheses; parse from the LAST ')' as procfs requires.
  const rest = stat.slice(stat.lastIndexOf(')') + 2).split(' ');
  // After comm+state, fields are: ppid(4) pgrp(5) session(6) → indexes 1, 2, 3 of `rest`.
  const sid = Number(rest[3]);
  if (!Number.isInteger(sid) || sid <= 0) {
    throw new Error(`could not read the POSIX session id from /proc/self/stat (got ${rest[3]})`);
  }
  return sid;
}

function registryDir(runtimeRoot, sid) {
  return path.join(runtimeRoot, 'sub-agent-dispatch', String(sid));
}

function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === 'EPERM';
  }
}

// Prunes dead claims and returns the live ones. A claim is a file named `<pid>.json` whose pid is
// the SUPERVISOR's, not the dispatcher's: the supervisor is what lives for the sub-agent's whole
// life, so its liveness IS the sub-agent's. A dispatcher that is SIGKILLed leaves its claim file
// behind; the supervisor dies with it (death pipe, supervisor.js) and the next pass prunes it.
function liveClaims(dir) {
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch {
    return [];
  }
  const live = [];
  for (const name of names) {
    if (!name.endsWith('.json')) continue;
    const file = path.join(dir, name);
    let claim;
    try {
      claim = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      fs.rmSync(file, { force: true });
      continue;
    }
    if (typeof claim.supervisorPid === 'number' && pidAlive(claim.supervisorPid)) live.push(claim);
    else fs.rmSync(file, { force: true });
  }
  return live;
}

// Exclusive lock around count-then-claim. Without it two concurrent dispatches both read 4 and
// both claim, and the cap is off by one under exactly the condition it exists for.
function withLock(dir, fn) {
  const lock = path.join(dir, '.lock');
  const deadline = Date.now() + 5000;
  let fd = null;
  for (;;) {
    try {
      fd = fs.openSync(lock, 'wx');
      break;
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      // A lock left by a crashed dispatcher must not wedge the lane forever.
      try {
        if (Date.now() - fs.statSync(lock).mtimeMs > 30000) fs.rmSync(lock, { force: true });
      } catch { /* raced with another remover; retry */ }
      if (Date.now() > deadline) throw new Error(`fan-out registry lock at ${lock} is held; giving up`);
    }
  }
  try {
    return fn();
  } finally {
    fs.closeSync(fd);
    fs.rmSync(lock, { force: true });
  }
}

// ⚠ A DEAD SESSION'S DIRECTORY IS NEVER READ AGAIN, so its stale claims are never pruned by
// `liveClaims` — which only runs against the CURRENT dispatcher's dir. Observed immediately: the
// two dispatchers this capability's probe SIGKILLs left a claim file each under session ids that
// can never recur. Harmless to the cap (a dead session cannot dispatch) but unbounded litter under
// the runtime root, so the sweep happens here, where a live dispatcher is already holding a lock
// and paying for a directory read. A sibling is removed only when BOTH tests hold: its session
// leader is gone AND it holds no live claim — either alone would be enough to be plausible and
// neither alone is enough to be safe.
function sweepDeadSessions(runtimeRoot, keepSid) {
  const root = path.join(runtimeRoot, 'sub-agent-dispatch');
  let names;
  try { names = fs.readdirSync(root); } catch { return; }
  for (const name of names) {
    const sid = Number(name);
    if (!Number.isInteger(sid) || sid === keepSid || pidAlive(sid)) continue;
    const dir = path.join(root, name);
    if (liveClaims(dir).length > 0) continue;
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* raced with another sweeper */ }
  }
}

// RESERVE a slot BEFORE the spawn, then bind it to the supervisor once spawned. The two steps are
// separate on purpose: counting after spawning would admit the (max+1)th sub-agent for as long as
// it takes to write the claim.
function reserve({ runtimeRoot, max = FANOUT_MAX, meta = {} }) {
  const sid = dispatcherId();
  const dir = registryDir(runtimeRoot, sid);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  sweepDeadSessions(runtimeRoot, sid);

  return withLock(dir, () => {
    const live = liveClaims(dir);
    if (live.length >= max) {
      throw new DispatchError(
        E_FANOUT_EXCEEDED,
        `dispatcher (POSIX session ${sid}) already runs ${live.length} sub-agent(s); the ` +
        `per-dispatcher fan-out cap is ${max} — REFUSING, nothing spawned (CMP-10 boundary 10, ` +
        `decisions.md#d-sub-agent-population-bounds). There is no override flag: an escape hatch ` +
        `on a population bound is the bound's repeal.`,
        { dispatcherSession: sid, live: live.length, max, registry: dir },
      );
    }
    const claimFile = path.join(dir, `reserve-${process.pid}.json`);
    fs.writeFileSync(claimFile, JSON.stringify({ reservedBy: process.pid, ...meta }), { mode: 0o600 });
    return {
      dir,
      sid,
      claimFile,
      // Rename the reservation onto the supervisor's pid once it exists, so liveness tracks the
      // process that actually holds the sub-agent.
      bind(supervisorPid) {
        const final = path.join(dir, `${supervisorPid}.json`);
        fs.writeFileSync(final, JSON.stringify({ supervisorPid, dispatcherPid: process.pid, ...meta }), { mode: 0o600 });
        fs.rmSync(claimFile, { force: true });
        this.claimFile = final;
      },
      release() {
        fs.rmSync(this.claimFile, { force: true });
      },
    };
  });
}

module.exports = { FANOUT_MAX, dispatcherId, registryDir, liveClaims, pidAlive, reserve };

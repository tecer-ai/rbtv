'use strict';

// await-exit.js — wait for a spawned victim's exit WITHOUT the verdictless-green race (task 7.621).
//
// `await new Promise((r) => child.on('exit', r))` is a trap: if the child already died before the
// listener attached, the event has been emitted and a late listener NEVER fires. main() then hangs
// on a promise nobody will settle, node drains the event loop, and the probe exits 0 having printed
// nothing and written no `.out` — a verdictless green. Observed live (wave-B finding F6) when
// `admin/install/module-manifest.json` was absent and every rbtv CLI leg refused instantly.
//
// The guard is the one `supervisor/spawn/carrier.js:307` already uses: read `exitCode` BEFORE awaiting.
// `error` is covered too — a child that fails to SPAWN emits no `exit` at all, which hangs the same
// way. It lives in this folder (not duplicated per probe) because it landed here
// first and probes already reach across folders by relative require; `runtime/gateway/probes/probe-gateway-live.js`
// is a consumer too (task 7.686). One body, wherever it sits. The suite enumerates
// `probe-*.js` only, so a helper here is never mistaken for a probe.

/**
 * @param {import('node:child_process').ChildProcess} child
 * @returns {Promise<{ code: number|null, signal: string|null, error?: Error }>}
 */
function awaitExit(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.signalCode !== null) {
      resolve({ code: child.exitCode, signal: child.signalCode });
      return;
    }
    child.once('error', (error) => resolve({ code: child.exitCode, signal: child.signalCode, error }));
    child.once('exit', (code, signal) => resolve({ code, signal }));
  });
}

module.exports = { awaitExit };

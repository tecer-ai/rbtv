'use strict';

/**
 * code-fingerprint.js — what code THIS daemon process actually loaded (run issue G-188 stage 2).
 *
 * WHY THIS EXISTS. The run could not answer "is the daemon running current code". It answered it by
 * INFERENCE — start time later than commit time — which is exactly the reasoning `G-158` was filed
 * to replace on the watch loop. Three deploy-backlog rows sat at INFERRED, NOT PROVEN for that
 * reason (`G-143`'s identity-gate fix, 7.42's resolver, 7.36's cockpit). The watch loop now reports
 * THAT the daemon restarted; nothing reported WHICH BYTES it came back on.
 *
 * ⚠⚠ FAIL-SOFT IS A HARD BAR, NOT A COURTESY (leader ruling, binding). This runs AT BOOT, so it IS
 * boot behaviour however read-only it looks — an unreadable file, a permission, a path that will
 * not resolve, and hashing throws. `index.js` exits hard on an unhandled boot error. The failure
 * being barred is THE DAEMON REFUSING TO START AT THE EXACT RESTART THE OWNER PERFORMS, caused by
 * the machinery added to observe that restart. So EVERY failure path here returns `null`, and a
 * null renders UNKNOWN at the reader — out loud.
 *
 * ⇒ THE TRICHOTOMY, which this file must never collapse:
 *      ABSENT (null)          → the reader says UNKNOWN. Loud, honest, actionable.
 *      PRESENT AND POPULATED  → a real claim about real bytes.
 *      EMPTY-BUT-PRESENT      → THE ONLY STATE THAT LIES. An empty map reads as "nothing drifted"
 *                               forever, so it is never returned; an empty scan yields null.
 *
 * ⚠ CAPTURED ONCE, AT BOOT, FROM FILE BYTES — NEVER RECOMPUTED WHEN ASKED. Recomputation hashes a
 * file against itself and can only ever report agreement: a detector that cannot fire, over the
 * defect it exists to detect. This is proven for the Python twin by
 * `team-kit/probes/probe-g158-stale-code.py` (arm A vs arm B), and it is the single design point
 * most likely to be "simplified" by someone who finds the caching odd.
 *
 * ⚠ THE SET IS DERIVED FROM `require.cache`, NOT ENUMERATED. An entry-file-only marker certifies
 * exactly the state it exists to detect — measured on the twin: the live loop's own `watch.py` was
 * current while `coord.py` had drifted four commits underneath it. The process's code is its whole
 * import closure, so the closure is the unit.
 *
 * BOUNDARIES, stated rather than discovered later:
 *   * `node_modules` is EXCLUDED. It is a different question — a dependency's identity is answered
 *     by its package version, which is how the js-yaml 5.2.1 -> 5.2.2 deploy was actually proven —
 *     and hashing the dependency tree at boot buys noise at a cost paid on every start.
 *   * Modules `require`d LAZILY, after this capture, are NOT covered. The claim is "the closure as
 *     it stood at capture", never "every byte this process will ever execute". Measured coverage is
 *     reported as `files`, so a caller can see the claim's size instead of assuming it is total.
 */

const crypto = require('crypto');
const path = require('path');

/**
 * Fingerprint the loaded closure, or return null. NEVER throws — see the fail-soft bar above.
 *
 * @param {string} rootDir  only files under here are fingerprinted (the daemon's own tree).
 * @returns {{captured_at: string, files: number, digest: string, entries: Object}|null}
 */
function captureLoadedCode(rootDir) {
  try {
    const fs = require('fs');
    const root = path.resolve(rootDir);
    const entries = {};
    for (const filename of Object.keys(require.cache)) {
      try {
        const resolved = path.resolve(filename);
        if (!resolved.startsWith(root + path.sep)) continue;
        if (resolved.split(path.sep).includes('node_modules')) continue;
        if (!resolved.endsWith('.js')) continue;
        // Re-read from disk rather than trusting any in-memory copy: the honest limit, same as the
        // twin's, is that these are the bytes AS THEY STOOD at capture, not the bytes the runtime
        // compiled. The failure this addresses lasts minutes to hours, not microseconds.
        entries[path.relative(root, resolved)] =
          crypto.createHash('sha256').update(fs.readFileSync(resolved)).digest('hex');
      } catch {
        // One unreadable file must not cost the whole fingerprint. It is simply absent from the
        // map, and `files` therefore under-reports rather than the capture failing outright.
        continue;
      }
    }
    const names = Object.keys(entries).sort();
    // An EMPTY scan is a FAILED scan, not a clean one. Returning `{files: 0}` would read as
    // "nothing drifted" on every future comparison — the empty-but-present state that lies.
    if (names.length === 0) return null;
    const digest = crypto.createHash('sha256')
      .update(names.map((n) => `${n}:${entries[n]}`).join('\n')).digest('hex');
    return {
      captured_at: new Date().toISOString(),
      files: names.length,
      digest,
      entries,
    };
  } catch {
    return null;
  }
}

module.exports = { captureLoadedCode };

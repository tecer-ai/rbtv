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
 * `coord/probes/probe-g158-stale-code.py` (arm A vs arm B), and it is the single design point
 * most likely to be "simplified" by someone who finds the caching odd.
 *
 * ⚠ THE SET IS DERIVED FROM `require.cache`, NOT ENUMERATED. An entry-file-only marker certifies
 * exactly the state it exists to detect — measured on the twin (the retired `coord/watch.py`
 * loop, 2026-07): its own module was current while `coord.py` had drifted four commits
 * underneath it. The process's code is its whole
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

// The marker's home, spelled ONCE. The writer below and the reader beside it must never be able to
// disagree about where the file is - a reader looking in the wrong place reports "no previous
// boot" forever, which is the empty-but-present lie in a second costume.
const MARKER_REL = path.join('.rbtv', 'runtime', 'daemon-code.json');

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

/**
 * Publish the boot fingerprint where a reader with NO CREDENTIAL can find it — G-188 stage 3.
 *
 * WHY A FILE AND NOT THE GATEWAY (leader ruling `#840`, and (b) is refused on principle, not cost):
 * `inspect daemon` requires auth, so a continuously-watching loop would have to HOLD the owner's
 * sender token for its whole life. Standing bar 11 reads the credential at CALL TIME and never
 * holds it; a daemon-lifetime process holding it is a durable exposure in a room that publishes
 * three surfaces by design. The marker needs no credential and is gitignored (`.rbtv/runtime/*`).
 *
 * ⚠⚠ THE FAILURE THIS FILE INTRODUCES, AND THE BAR THAT ANSWERS IT (leader, binding): THE MARKER
 * OUTLIVES THE PROCESS THAT WROTE IT. It is written at boot; if the daemon dies the file SURVIVES,
 * carrying the last boot's fingerprint, and a reader trusting it standalone reports "code is
 * current" about a daemon that is not running — absence-reading-as-health, arriving through the
 * very artifact built to prevent it.
 *
 * ⇒ SO THE MARKER STAMPS ITS OWN BOOT IDENTITY — `pid` and systemd's `INVOCATION_ID` — and a reader
 * MUST correlate that against the LIVE unit before believing a word of it. `INVOCATION_ID` is in
 * the service's own environment (verified on this box: it equals the `InvocationID` the unit
 * reports), so the daemon and the watcher key on the SAME identity with no inference in between.
 * A marker that does not match the live unit is UNKNOWN — never stale, never current.
 *
 * Fail-soft on the same terms as the capture: this runs at boot, so it returns false rather than
 * throwing. A marker that cannot be written leaves the reader saying UNKNOWN, out loud, which is
 * strictly better than a daemon that will not start.
 *
 * `deployFingerprint` is a SECOND capture over a WIDER root (the whole `ignite/` closure), stored
 * as a SUMMARY — digest and count, no per-file map. It answers a different question from the one
 * above: `code` is "which bytes is this daemon RUNNING", scoped to the process's own component and
 * re-hashed file-by-file by the watchdog; `deploy` is "was anything in this daemon's code
 * DEPLOYED since the last boot", which is spec-recovery §5's `code-deploy` re-arm trigger
 * (`code-deploy-rearm.js`). The narrow digest cannot answer it: a deploy touching only
 * `supervisor/` leaves it byte-identical, and the re-arm would never fire for the commits most
 * likely to need it. Its entries are deliberately NOT stored — the map would be ten times the
 * marker's size for a question only its digest answers.
 *
 * @returns {boolean} whether the marker was written (never throws)
 */
function writeCodeMarker(workspaceRoot, fingerprint, deployFingerprint = null) {
  try {
    if (!fingerprint) return false;   // absent stays ABSENT: never publish an empty marker
    const fs = require('fs');
    const dir = path.dirname(path.join(path.resolve(workspaceRoot), MARKER_REL));
    fs.mkdirSync(dir, { recursive: true });
    const body = JSON.stringify({
      pid: process.pid,
      // The absolute root the fingerprint's paths are relative to. CARRIED, never re-derived by the
      // reader: the reader is `daemon_code_state` in the daemon-watchdog capability's
      // `rbtv-ignite-watchdog` (it replaced the retired `coord/watch.py` reader, task 7.35),
      // a component every install runs, and a literal like `3-resources/tools/rbtv/ignite/server`
      // there would freeze this vault's layout into it. G-107's lesson: carry the subject, never
      // infer it.
      root: path.resolve(__dirname),
      // Absent when the daemon is run outside systemd (a dev run). Written as null rather than
      // omitted, so a reader can tell "no systemd identity" from "field I forgot to read".
      invocation: process.env.INVOCATION_ID || null,
      written_at: new Date().toISOString(),
      code: fingerprint,
      // The wide summary. `null` when the capture failed, which reads as UNKNOWN at the re-arm
      // (never as "unchanged") — see the trichotomy at the top of this file.
      deploy: deployFingerprint ? {
        digest: deployFingerprint.digest,
        files: deployFingerprint.files,
        captured_at: deployFingerprint.captured_at,
      } : null,
    }, null, 1);
    // Same-directory temp + rename: a reader must never observe a half-written marker, and a
    // truncated JSON would read as a CORRUPT marker — which the reader must treat as UNKNOWN, but
    // it is cheaper not to create the case at all.
    const tmp = path.join(dir, `.daemon-code.json.${process.pid}.tmp`);
    fs.writeFileSync(tmp, body);
    fs.renameSync(tmp, path.join(path.resolve(workspaceRoot), MARKER_REL));
    return true;
  } catch {
    return false;
  }
}

/**
 * Read the marker the PREVIOUS boot left, or null - the other side of `writeCodeMarker`.
 *
 * WHY IT EXISTS. `code-deploy` is one of spec-recovery section 5's four named re-arm events and it
 * had no producer: nothing in the tree ever compared this boot's code to the last one's, so every
 * attempt counter that reached N stayed there through every deploy and restart. The comparison
 * needs the previous digest, and the previous digest is already on disk in this marker - written
 * at every boot since G-188 stage 3. NO SECOND LEDGER IS ADDED for it.
 *
 * ⚠ THE MARKER IS THE LAST BOOT'S, NOT THE LAST DEPLOY'S, and the difference is the whole point:
 * a plain restart re-reads the same bytes and yields the same digest, so it is NOT a deploy and
 * must re-arm nothing. That is what makes this comparison a deploy detector rather than a restart
 * detector.
 *
 * Fail-soft on the same terms as everything else in this file - it is read at boot.
 *
 * @returns {{pid:number, root:string, invocation:string|null, written_at:string, code:object}|null}
 */
function readCodeMarker(workspaceRoot) {
  try {
    const fs = require('fs');
    const parsed = JSON.parse(fs.readFileSync(path.join(path.resolve(workspaceRoot), MARKER_REL), 'utf8'));
    return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : null;
  } catch {
    return null;
  }
}

module.exports = {
  MARKER_REL, captureLoadedCode, writeCodeMarker, readCodeMarker,
};

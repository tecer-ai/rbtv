#!/usr/bin/env node
'use strict';

/**
 * probe-daemon-code-fingerprint.js — the daemon's boot code fingerprint (G-188 stage 2).
 *
 * WHAT IS UNDER TEST. The run could not say WHICH BYTES the daemon was running; it inferred it from
 * start time against commit time, which is the reasoning `G-158` exists to replace. Three
 * deploy-backlog rows still sit at INFERRED, NOT PROVEN for want of this.
 *
 * ⚠⚠ THE BAR THAT MATTERS MOST IS NOT THE FEATURE — IT IS THAT THE FEATURE CANNOT BREAK BOOT
 * (leader ruling, binding). This capture runs at boot, so it IS boot behaviour however read-only it
 * looks, and `index.js` exits hard on an unhandled boot error. The failure being barred is the
 * daemon refusing to start at the exact restart the owner performs, caused by the machinery added
 * to observe that restart. Arms C and D are that bar; they matter more than arm A.
 *
 * ⚠ AND THE TRICHOTOMY: absent (null) reads UNKNOWN and is loud; populated is a real claim;
 * EMPTY-BUT-PRESENT IS THE ONLY STATE THAT LIES, because an empty map reads as "nothing drifted"
 * forever. An empty scan therefore returns null, and arm C asserts exactly that.
 *
 * RUN IT:  node server/probes/probe-daemon-code-fingerprint.js
 * Exit 0 all pass · 1 a property is broken · 2 the probe could not run (never reported as a pass).
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

let captureLoadedCode;
try {
  ({ captureLoadedCode } = require('../code-fingerprint'));
} catch (err) {
  console.log(`INOPERATIVE: could not load the module under test (${err.message})`);
  process.exit(2);
}

const PASSED = [];
const FAILED = [];
function check(name, ok, detail) {
  (ok ? PASSED : FAILED).push(name);
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

console.log('\nARM A — the real closure of THIS process is fingerprinted (the control).');
const here = path.resolve(__dirname, '..');
const real = captureLoadedCode(here);
check('a capture came back at all', real && typeof real === 'object', real ? 'object' : String(real));
check('it counts the files it actually hashed', real && real.files > 0, real && `files=${real.files}`);
check('every entry is a sha256 hex digest',
  real && Object.values(real.entries).every((v) => /^[0-9a-f]{64}$/.test(v)));
check('the digest is over the whole set, not one file',
  real && /^[0-9a-f]{64}$/.test(real.digest));
// ⚠ THE OBVIOUS VERSION OF THIS CHECK IS VACUOUS AND A MUTANT PROVED IT. Asserting "no entry under
// `server/` contains node_modules" passes no matter what the code does, because the dependency tree
// lives at `ignite/node_modules`, OUTSIDE this root — there is nothing to exclude, so deleting the
// exclusion entirely left the probe green. A check that cannot fail is not a check. The real
// assertion needs a root that ACTUALLY CONTAINS a loaded node_modules file, built below in arm B.
check('no node_modules entry appears in the real capture (necessary, not sufficient — see arm B)',
  real && !Object.keys(real.entries).some((k) => k.split(path.sep).includes('node_modules')));
check('paths are relative to the root, so the map is portable',
  real && Object.keys(real.entries).every((k) => !path.isAbsolute(k)));
check('the closure is DERIVED, not one entry file — it covers more than this probe',
  real && real.files > 1, real && `${real.files} files`);

// ⚠ THE CONTROL ABOVE IS WEAK ON ITS OWN AND SAYING SO IS THE POINT: this probe process had loaded
// only a couple of server files, so `files=2` proves the mechanism and NOT that it scales to the
// daemon's real graph. Loading a slice of that graph and re-capturing is what turns "it returns a
// map" into "it tracks what this process actually loaded". These requires are side-effect-free
// module loads — the daemon is NOT started, and nothing here touches the live unit.
const beforeGraph = real.files;
require('../internal-api/dispatch');
require('../heart/heart-store');
const grown = captureLoadedCode(here);
check('loading more of the daemon graph GROWS the fingerprint',
  grown && grown.files > beforeGraph, `${beforeGraph} -> ${grown && grown.files} files`);
check('and it covers a real slice of the daemon, not a token few',
  grown && grown.files >= 10, grown && `${grown.files} files`);
check('the digest moves with the closure, so the set is part of the identity',
  grown && grown.digest !== real.digest);

console.log('\nARM B — the digest MOVES when bytes move, and only then.');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'g188-fp-'));
const modPath = path.join(tmp, 'victim.js');
fs.writeFileSync(modPath, 'module.exports = 1;\n');
require(modPath);
const before = captureLoadedCode(tmp);
check('a temp-root capture sees only the temp module', before && before.files === 1,
  before && `files=${before.files}`);
const again = captureLoadedCode(tmp);
check('two captures of unchanged bytes agree', before && again && before.digest === again.digest);
fs.writeFileSync(modPath, 'module.exports = 2;\n');
const after = captureLoadedCode(tmp);
check('the digest CHANGES when the file on disk changes',
  after && after.digest !== before.digest,
  'this is the whole feature: the loaded bytes and the disk bytes have parted');
check('and the per-file entry changes too, so the drifted file is nameable',
  after && after.entries['victim.js'] !== before.entries['victim.js']);

// The NON-VACUOUS node_modules exclusion: a root that genuinely contains a LOADED dependency file.
// Without this the exclusion can be deleted outright and every other check stays green.
fs.mkdirSync(path.join(tmp, 'node_modules', 'faux'), { recursive: true });
const depPath = path.join(tmp, 'node_modules', 'faux', 'index.js');
fs.writeFileSync(depPath, 'module.exports = 42;\n');
require(depPath);
const withDep = captureLoadedCode(tmp);
check('a LOADED node_modules file is excluded — the exclusion actually runs',
  withDep && !Object.keys(withDep.entries).some((k) => k.split(path.sep).includes('node_modules')),
  withDep && Object.keys(withDep.entries).join(', '));
check('while the sibling non-dependency file in the same root is still captured',
  withDep && 'victim.js' in withDep.entries);

console.log('\nARM C — ⚠ FAIL-SOFT: every failure is null, never a throw, never empty.');
let threw = null;
let out;
try {
  out = captureLoadedCode('/nonexistent/path/that/cannot/be/read');
} catch (err) {
  threw = err;
}
check('an unresolvable root does NOT throw', threw === null, threw && threw.message);
check('and it returns null rather than an empty map',
  out === null, JSON.stringify(out));
check('EMPTY-BUT-PRESENT is never returned — the only state that lies',
  out === null || (out && out.files > 0));

threw = null;
try {
  out = captureLoadedCode(undefined);
} catch (err) {
  threw = err;
}
check('an undefined root does NOT throw', threw === null, threw && threw.message);
check('and yields null', out === null);

threw = null;
try {
  out = captureLoadedCode(null);
} catch (err) {
  threw = err;
}
check('a null root does NOT throw', threw === null, threw && threw.message);

console.log('\nARM D — ⚠ THE BOOT BAR: a hostile filesystem cannot stop the daemon starting.');
// The realistic boot failure is not a missing root — it is a file that resolves, is in the cache,
// and CANNOT BE READ. Simulated by making readFileSync throw for one entry, which is the shape a
// permission error takes. The capture must lose that file, not the whole fingerprint, and above
// all must not propagate to index.js's hard exit.
const realRead = fs.readFileSync;
let sawCall = false;
threw = null;
try {
  fs.readFileSync = function poisoned(p, ...rest) {
    sawCall = true;
    if (String(p).endsWith('victim.js')) throw new Error('EACCES simulated');
    return realRead.call(fs, p, ...rest);
  };
  out = captureLoadedCode(tmp);
} catch (err) {
  threw = err;
} finally {
  fs.readFileSync = realRead;
}
check('an unreadable file did NOT throw out of the capture', threw === null, threw && threw.message);
check('the poisoned read was actually exercised (the arm is not vacuous)', sawCall);
check('and the sole unreadable file yields null rather than a bogus empty map', out === null);
check('fs.readFileSync was restored', fs.readFileSync === realRead);

// A root with one readable and one unreadable file must keep the readable one.
fs.writeFileSync(path.join(tmp, 'survivor.js'), 'module.exports = 3;\n');
require(path.join(tmp, 'survivor.js'));
threw = null;
try {
  fs.readFileSync = function poisoned(p, ...rest) {
    if (String(p).endsWith('victim.js')) throw new Error('EACCES simulated');
    return realRead.call(fs, p, ...rest);
  };
  out = captureLoadedCode(tmp);
} catch (err) {
  threw = err;
} finally {
  fs.readFileSync = realRead;
}
check('one unreadable file costs that file, not the whole fingerprint',
  threw === null && out && out.files === 1 && 'survivor.js' in out.entries,
  out && `files=${out.files} keys=${Object.keys(out.entries)}`);
check('and the lost file is absent rather than recorded with a fake hash',
  out && !('victim.js' in out.entries));

console.log('\nARM E — captured ONCE at boot, never recomputed when asked.');
// The design point most likely to be "simplified". A recomputing reader hashes a file against
// itself and can only ever report agreement — a detector that cannot fire, over the very defect it
// exists to detect. Asserted by showing a held capture goes STALE against a changed disk, which is
// precisely the signal a recomputing implementation would destroy.
const held = captureLoadedCode(tmp);
fs.writeFileSync(path.join(tmp, 'survivor.js'), 'module.exports = 99;\n');
const fresh = captureLoadedCode(tmp);
check('a held capture does NOT silently follow the disk',
  held && fresh && held.digest !== fresh.digest,
  'a boot capture must be able to disagree with disk — that disagreement IS the drift signal');
check('so a reader comparing held-vs-disk can detect drift',
  held.entries['survivor.js'] !== fresh.entries['survivor.js']);

fs.rmSync(tmp, { recursive: true, force: true });

console.log(`\nCHECKS ${PASSED.length}/${PASSED.length + FAILED.length}`);
if (FAILED.length) {
  console.log(`FAILED: ${FAILED.join('; ')}`);
  process.exit(1);
}
if (PASSED.length < 30) {
  console.log(`INOPERATIVE: only ${PASSED.length} checks ran; this probe asserts at least 30`);
  process.exit(2);
}
process.exit(0);

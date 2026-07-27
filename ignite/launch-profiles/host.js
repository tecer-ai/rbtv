'use strict';

const fs = require('node:fs');
const path = require('node:path');

// Host containment-capability detection — the resolver's half picker (task 7.42,
// registry decisions.md#d-profile-source-unification (4)).
//
// ⚠ THE HALF IS PICKED FROM THE HOST, NEVER BY CALLER CHOICE. There is deliberately NO parameter
// and no environment override on `detectHostCapability()`: the ruling's whole point is that a
// caller cannot ask for the caged half on a box that cannot cage. A test that wants the portable
// answer changes the HOST condition (a PATH with no `bwrap`), which makes the detector genuinely
// compute `portable` — it does not hand the answer in. Handing it in would test everything except
// the detection.
//
// ⚠ PRIN-11 residual, disclosed rather than hidden: `server/spawn/bwrap.js` carries its own
// `scanPath` with the same shape. The shared module may not require anything under `server/`, so
// the two coexist today. The named fix is for bwrap.js to consume THIS one when the seat cage is
// adopted (it is BUILT, NOT APPLIED — leader adoption bar, issue G-124); doing it now would edit
// 7.11's freshly landed cage path for no behaviour gain. Filed, not silently accepted.

// In-process PATH scan — deterministic and testable; never forks `which` (the resolver may run
// inside a spawn path where forking a helper per resolution is a cost and a failure mode).
function scanPath(binary, pathEnv) {
  const raw = pathEnv === undefined ? process.env.PATH : pathEnv;
  if (!raw) return null;
  for (const dir of raw.split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.join(dir, binary);
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      // not here; keep scanning
    }
  }
  return null;
}

const CAGED = 'caged';
const PORTABLE = 'portable';

// A host is CAGED when it can actually build the mount namespace the caged half presumes.
// `bwrap` is the discriminator: the caged half's whole premise is a bwrap mount namespace, and a
// box without the binary cannot produce one. Absence of bwrap => PORTABLE, which then forces the
// profile to carry a portable half or be refused.
//
// systemd-run is NOT part of this test, on purpose. It governs the CARRIER (cgroup caps + unit
// lifecycle, carrier.js's own `auto|systemd|setsid` choice) — a different axis, already decided
// elsewhere. Folding it in here would make one profile half depend on two unrelated capabilities
// and would silently change which half a systemd-less-but-bwrap-capable box gets.
// ⚠ TAKES NO ARGUMENTS, deliberately. An earlier draft accepted a `pathEnv` override "for
// testability" — that is the same defect in a thinner disguise: a caller passing a bwrap-less PATH
// is still a caller choosing `portable`. The probe instead launches a CHILD PROCESS whose real
// environment lacks bwrap, so this function reads the true host state and computes the answer.
function detectHostCapability() {
  return scanPath('bwrap') ? CAGED : PORTABLE;
}

module.exports = { detectHostCapability, scanPath, CAGED, PORTABLE };

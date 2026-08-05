'use strict';

// D58(4) — the ADVISORY second belt. At spawn, materialize into the worker's launch (session)
// dir a SIMPLE harness-local write-restraint config for whichever of the three harnesses
// (claude, codex, opencode) the profile launches. Layer honesty (D58, POC finding 3): the KERNEL
// sandbox is the LOAD-BEARING layer and the acceptance test grades IT; this config only expresses
// intent to a harness that honors a local config and NEVER substitutes for the kernel confinement.
// It restrains writes to the launch dir + the editable paths the launch's kernel sandbox already
// grants (the designated test folder, when a launch declares it). Minimal: one file per harness,
// no wrappers, no new subsystems.
//
// ⚠ TASK 7.45 — THIS FILE IS NOW A THIN ADAPTER, NOT A HOME. The per-harness KNOWLEDGE it used to
// carry (which harness an argv[0] names, and what each harness's config file is) moved to the ONE
// shared injection ladder, `ignite/injection-ladder/` (CMP-9, decisions.md#d-injection-ladder-shared).
// What stays here is the DAEMON's half and only that: the filesystem writes and the daemon's log
// line. The split follows CMP-9 § Interface literally — the ladder "exposes no command, holds no
// state, spawns nothing, and WRITES nothing" — which is exactly what lets the no-daemon lanes
// (7.43/7.44/7.54) read the same knowledge without keeping a private second copy.
//
// The direction of the require matters and is the same rule 7.42 established: `server/` may import
// the shared module; the shared module may NEVER import anything under `server/`.
//
// `harnessOf` is RE-EXPORTED rather than redefined. Its four other call sites (spawn.js:366/579/622,
// the spawn path) keep importing it from here, so this re-home changes where the knowledge lives
// and nothing any caller observes.

const fs = require('node:fs');
const { harnessOf, hooksConfigFor } = require('../../injection-ladder');

// Execute the ladder's hooks-rung descriptor. The bytes, paths, modes and returned object are the
// ladder's; the I/O is the daemon's. A null harness (sleep/test/bash profiles) descriptor carries
// no dirs and no files, so it performs no I/O — the same "no harness, no config" behaviour as before.
function materializeHarnessConfig({ sessionDir, profile, editablePaths = [] }) {
  const plan = hooksConfigFor(harnessOf(profile), { sessionDir, editablePaths });

  for (const dir of plan.dirs) {
    fs.mkdirSync(dir.path, { recursive: true, mode: dir.mode });
  }
  for (const file of plan.files) {
    if (file.mode === undefined) fs.writeFileSync(file.path, file.content);
    else fs.writeFileSync(file.path, file.content, { mode: file.mode });
  }
  return plan.result;
}

module.exports = { materializeHarnessConfig, harnessOf };

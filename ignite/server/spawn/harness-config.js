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
// `harnessOf` is RE-EXPORTED rather than redefined. Its other call sites (several in spawn.js, the
// spawn path) keep importing it from here, so this re-home changes where the knowledge lives and
// nothing any caller observes.

const fs = require('node:fs');
const path = require('node:path');
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

// ── Task 7.444 (MC2) — MAKE A PROFILE'S `--settings` FILE READABLE INSIDE THE SEAT CAGE ──────
//
// The defect (`G-mrd-fork-driver-0806-1746`): all four claude profiles pass an absolute
// `--settings` path under `ignite/config/`, and NO line of the shared `cage.SeatBinds` template
// covers that tree — so the harness exits 1 within 10 s on `Error: Settings file not found: …`
// naming a file that exists on disk and is simply absent from its namespace. No claude-family
// seat could be spawned by the daemon at all.
//
// THE FIX REUSES THE MECHANISM ABOVE RATHER THAN WIDENING THE WALL: the file is materialized
// into the launch dir — which `bind:{seatDir}` already opens read-write inside the cage — and the
// argument re-pointed at that copy. The two rivals, recorded because they were considered and
// NOT taken: binding the ignite config tree into `cage.SeatBinds` opens a whole config tree to
// EVERY seat to solve one file; re-pathing the profile relocates the defect onto whoever owns the
// settings content. This one widens nothing and adds no new subsystem.
//
// FLAG-DRIVEN, NEVER PROFILE-DRIVEN. It reads the composed argv, so all four claude profiles
// resolve through this one path with no per-profile special case — and a profile that names no
// `--settings` (every non-claude one today) plans nothing and copies nothing.
//
// SPLIT IN TWO, and the split is load-bearing: `spawnSeat({dryRun:true})` must compose the REAL
// argv while leaving NO trace on disk, so planning is pure and copying is a separate call. Same
// descriptor/adapter division the injection ladder above already uses, for the same reason.
const SETTINGS_FLAG = '--settings';

function planCagedSettings(argv, sessionDir) {
  const next = [...argv];
  const copies = [];
  for (let i = 0; i < next.length - 1; i++) {
    if (next[i] !== SETTINGS_FLAG) continue;
    const src = next[i + 1];
    // A relative name already resolves against the launch dir, which is inside the cage — there
    // is nothing to carry in, and rewriting it would move a path the profile author controls.
    if (!path.isAbsolute(src)) continue;
    const dest = path.join(sessionDir, `.ignite-${path.basename(src)}`);
    if (path.normalize(src) === path.normalize(dest)) continue;
    copies.push({ src, dest });
    next[i + 1] = dest;
  }
  return { argv: next, copies };
}

// Performs the plan. NOT wrapped in a try/catch by its callers, deliberately: an unreadable
// settings source means this launch cannot succeed, and failing HERE surfaces it as a typed
// spawn failure against a real jobs_log row, at the daemon, naming the file — instead of ten
// seconds later as one opaque line in a worker transcript, which is the defect being fixed.
function materializeCagedSettings(copies) {
  for (const { src, dest } of copies) fs.copyFileSync(src, dest);
  return copies;
}

module.exports = { materializeHarnessConfig, harnessOf, planCagedSettings, materializeCagedSettings };

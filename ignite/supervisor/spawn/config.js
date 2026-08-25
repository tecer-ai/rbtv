'use strict';

// server/spawn/config.js — the DAEMON-SIDE ADAPTER over the shared launch-profile resolver.
//
// Task 7.42 (registry decisions.md#d-profile-source-unification (2)) moved profile loading,
// validation, slot resolution, the carriage vocabulary and the workdir guard OUT of this file and
// into `ignite/launch-profiles/`, so that the daemon's spawn path, the attached dispatch
// capability (7.43) and the orchestration conductor's worker dispatch (7.54) all resolve through
// ONE module — "a second interpreter of the one file is the same drift as a second file".
//
// This file survives, unmoved and with its EXACT former export set, for one reason: it is what
// `supervisor/spawn/spawn.js` and the spawn probes require. Keeping the
// seam means the daemon's behaviour is byte-unchanged — no call site moved, no signature changed,
// the same `SpawnError` class with the same codes.
//
// What this adapter adds on top of the shared module is exactly one thing: it INJECTS cage.js's
// SeatBinds template validator (task 7.11). The shared module may not import anything under
// `server/`, and the SeatBinds vocabulary is cage.js's to define — so the daemon, which does own
// cage.js, hands the validator in. A consumer that supplies none has SeatBinds REFUSED rather
// than waved through (see profiles.js) — absence of a checker never becomes absence of a check.

const shared = require('../launch-profiles');

// Lazily required inside the closure: cage.js requires ./errors, which requires the shared
// errors module — resolving it at call time rather than module load keeps the require graph
// order-independent, exactly as the former in-function `require('./cage')` did.
function seatBindValidator(template, profileName, filePath) {
  const { validateSeatBindTemplate } = require('./cage');
  return validateSeatBindTemplate(template, profileName, filePath);
}

// Same signature the daemon has always called. The second parameter is new and internal — no
// existing call site passes it, and the default is the daemon's own validator.
function loadConfig(filePath) {
  return shared.loadConfig(filePath, { seatBindValidator });
}

module.exports = {
  loadConfig,
  resolveTemplateSlots: shared.resolveTemplateSlots,
  resolveWorkdir: shared.resolveWorkdir,
  resolveWorkspaceRoot: shared.resolveWorkspaceRoot,
  sessionsRootFor: shared.sessionsRootFor,
  CLOSED_SLOTS: shared.CLOSED_SLOTS,
  // The effort ladder's one interpreter, passed straight through — the daemon composes its own
  // argv (G-144) but must NOT own a second reading of the profile's `effort:` table.
  resolveEffort: shared.resolveEffort,
};

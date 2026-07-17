'use strict';

// Task 6.2 (session-surface-spec.md Design 1–3) — the headed/pty extension's typed errors.
// Reuses the SpawnError class + shared codes from the spawn module (same ignite module, so a
// require of a sibling FILE inside ignite/ is allowed; ignite/CLAUDE.md rule 4 forbids reach-outs
// into OTHER module folders, not intra-module requires — index.js already requires ../gateway).
// A dead/nonexistent session id yields a TYPED error, never a hang (spec Behavior #11).

const {
  SpawnError,
  E_HEADED_NOT_CAPABLE,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_FLAG_INJECTION,
  E_FS_SANDBOX_UNAVAILABLE,
} = require('../spawn/errors');

// pty-host specific codes (spec Design 1 & 3).
const E_HEADED_PROMPT_REJECTED = 'E_HEADED_PROMPT_REJECTED';   // prompt + headed vs a profile declaring NO carriage (Design 3 default, Behavior #9)
const E_HEADED_PROMPT_CARRIAGE = 'E_HEADED_PROMPT_CARRIAGE';   // malformed carriage (unknown value, missing {prompt} slot, stdin structurally absent)
const E_HEADED_STDIN_CARRIAGE = 'E_HEADED_STDIN_CARRIAGE';     // `stdin` carriage is a config-LOAD failure (Design 3 — structurally absent)
const E_SESSION_NOT_LIVE = 'E_SESSION_NOT_LIVE';               // keys/capture on a dead/unknown headed session (Behavior #11)
const E_PTY_BRIDGE = 'E_PTY_BRIDGE';                           // the pty attach bridge could not be established/relayed
const E_PROMPT_INJECTION_TIMEOUT = 'E_PROMPT_INJECTION_TIMEOUT'; // keystroke-carriage readiness marker never appeared (Behavior #10)
const E_HOLDER_FAILED = 'E_HOLDER_FAILED';                     // the in-unit dtach holder failed to launch

module.exports = {
  SpawnError,
  E_HEADED_NOT_CAPABLE,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_FLAG_INJECTION,
  E_FS_SANDBOX_UNAVAILABLE,
  E_HEADED_PROMPT_REJECTED,
  E_HEADED_PROMPT_CARRIAGE,
  E_HEADED_STDIN_CARRIAGE,
  E_SESSION_NOT_LIVE,
  E_PTY_BRIDGE,
  E_PROMPT_INJECTION_TIMEOUT,
  E_HOLDER_FAILED,
};

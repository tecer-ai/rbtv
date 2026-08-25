'use strict';

// The injection ladder's error surface (task 7.45; registry CMP-9,
// decisions.md#d-injection-ladder-shared, decisions.md#d-profile-source-unification).
//
// A SEPARATE class from `SpawnError` (launch-profiles/errors.js), deliberately. The two modules
// answer different questions — the resolver answers WHAT THE COMMAND LINE IS, this ladder answers
// WHICH METHOD (CMP-9 § Interface (2)) — and a consumer that catches one must not silently swallow
// the other. They are consumed together; they are not one failure domain.
class LadderError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'LadderError';
    this.code = code;
    this.details = details;
  }
}

// The harness is outside the closed vocabulary. NOT a fallback to "assume the most common shape":
// a harness the ladder has no measured entry for has no known rungs, and guessing one would put
// unverified launch knowledge back into the system this module exists to hold in one place.
const E_UNKNOWN_HARNESS = 'E_UNKNOWN_HARNESS';

// The walk reached the bottom of the ladder with no rung available for this (harness, phase, host).
// Fail closed: there is no "try it anyway" rung below keystroke.
const E_NO_RUNG_AVAILABLE = 'E_NO_RUNG_AVAILABLE';

// A caller named a rung outside the closed vocabulary (headless|hooks|keystroke). Raised by the
// direct-query helpers, never by the walk — the walk never accepts a rung from a caller, which is
// the whole point of it being a walk (see index.js's header on p-green-harness-over-a-broken-mechanism).
const E_UNKNOWN_RUNG = 'E_UNKNOWN_RUNG';

module.exports = {
  LadderError,
  E_UNKNOWN_HARNESS,
  E_NO_RUNG_AVAILABLE,
  E_UNKNOWN_RUNG,
};

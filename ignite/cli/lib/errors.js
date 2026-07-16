'use strict';

// Local (never-reaches-the-gateway) CLI errors — usage/parse problems and
// transport failures. A gateway-returned envelope error is NOT re-wrapped in
// either of these: it is rendered straight from the envelope (lib/output.js).

class CliUsageError extends Error {
  constructor(message) {
    super(message);
    this.name = 'CliUsageError';
  }
}

class CliTransportError extends Error {
  constructor(message) {
    super(message);
    this.name = 'CliTransportError';
  }
}

// gateway-cli-spec.md § Exit codes:
//   0 success · 2 local usage/parse error · 3 refused by gateway auth
//   4 validation refused (gateway shape-check OR server re-validation)
//   5 gateway unreachable/transport failure · 1 anything else
//
// Only AUTH_REFUSED and {SHAPE_INVALID,VALIDATION_FAILED} get a dedicated exit
// code per that table; every other typed envelope error (AUTH_FAILED,
// UNKNOWN_INTENT, VERSION_MISMATCH, BAD_ENVELOPE, NOT_FOUND, UNAUTHORIZED_SENDER,
// INTERNAL, or anything not yet named) falls into the catch-all "1 anything else".
function exitForEnvelopeCode(code) {
  if (code === 'AUTH_REFUSED') return 3;
  if (code === 'SHAPE_INVALID' || code === 'VALIDATION_FAILED') return 4;
  return 1;
}

module.exports = { CliUsageError, CliTransportError, exitForEnvelopeCode };

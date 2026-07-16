'use strict';

// Typed wire errors for the internal gateway<->server-core API
// (internal-api-contract-spec.md § 2). Errors are DATA, never exceptions thrown
// across the boundary: every handler converts a throw into one of these codes
// before the response envelope is built.
//
// This set is CLOSED by the ratified contract — a new code is a contract change,
// never a build decision (D23: a term is invented only when necessary, and every
// invented term is owner-approved before it binds).

class InternalApiError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = 'InternalApiError';
    this.code = code;
    this.details = details;
  }
}

// Missing/wrong client secret. Refused BEFORE intent dispatch.
const AUTH_FAILED = 'AUTH_FAILED';
// Envelope `v` differs from the supported major version (the split's skew guard).
const VERSION_MISMATCH = 'VERSION_MISMATCH';
// Envelope malformed or not JSON-serializable (missing/unknown field, circular ref).
const BAD_ENVELOPE = 'BAD_ENVELOPE';
// Intent name not registered.
const UNKNOWN_INTENT = 'UNKNOWN_INTENT';
// The dry-run re-validation refused the payload; `details` names the failing check.
const VALIDATION_FAILED = 'VALIDATION_FAILED';
// A referenced id (queue row, execution) does not exist.
const NOT_FOUND = 'NOT_FOUND';
// Envelope authenticated, but the attested sender may not perform this action.
const UNAUTHORIZED_SENDER = 'UNAUTHORIZED_SENDER';
// Server-core fault; the envelope was valid. Leaks no handle and no stack.
const INTERNAL = 'INTERNAL';

const WIRE_ERROR_CODES = new Set([
  AUTH_FAILED,
  VERSION_MISMATCH,
  BAD_ENVELOPE,
  UNKNOWN_INTENT,
  VALIDATION_FAILED,
  NOT_FOUND,
  UNAUTHORIZED_SENDER,
  INTERNAL,
]);

module.exports = {
  InternalApiError,
  AUTH_FAILED,
  VERSION_MISMATCH,
  BAD_ENVELOPE,
  UNKNOWN_INTENT,
  VALIDATION_FAILED,
  NOT_FOUND,
  UNAUTHORIZED_SENDER,
  INTERNAL,
  WIRE_ERROR_CODES,
};

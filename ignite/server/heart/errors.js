'use strict';

class HeartStoreError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'HeartStoreError';
    this.code = code;
    this.details = details;
  }
}

const E_SECOND_WRITER = 'E_SECOND_WRITER';
const E_UNKNOWN_JOB = 'E_UNKNOWN_JOB';
const E_JOB_DISABLED = 'E_JOB_DISABLED';
const E_BAD_ARGS = 'E_BAD_ARGS';
const E_UNKNOWN_PROFILE = 'E_UNKNOWN_PROFILE';
const E_UNKNOWN_TOOL = 'E_UNKNOWN_TOOL';
const E_UNKNOWN_WORKFLOW = 'E_UNKNOWN_WORKFLOW';
const E_BAD_MESSAGE = 'E_BAD_MESSAGE';
const E_BAD_TRIGGER = 'E_BAD_TRIGGER';
const E_BAD_MODE = 'E_BAD_MODE';
// Typed not-found for a sender-initiated queue-row removal (p4-0; owner-approved
// D66(B)). Name follows the module's established `E_<THING>_NOT_FOUND` shape
// (`server/spawn/errors.js` E_SESSION_NOT_FOUND). A NEW code is NECESSARY (D23
// invents only when necessary): E_UNKNOWN_JOB means "no such CATALOGUE job", a
// different thing from "no such QUEUE ROW", and the internal-API contract maps
// the two to DIFFERENT wire codes (VALIDATION_FAILED vs NOT_FOUND) — overloading
// one code would make that ratified mapping unimplementable.
const E_QUEUE_ROW_NOT_FOUND = 'E_QUEUE_ROW_NOT_FOUND';

module.exports = {
  HeartStoreError,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
  E_QUEUE_ROW_NOT_FOUND,
};

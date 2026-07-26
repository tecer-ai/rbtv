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
// Typed duplicate refusal for sender-initiated catalogue registration (task 7.12;
// owner ruling 2026-07-25 Call 2 — registration is CREATE-ONLY, never an upsert).
// A NEW code is NECESSARY (D23 invents only when necessary): E_UNKNOWN_JOB means
// "no such catalogue job" and this is its INVERSE — "that catalogue id is already
// taken" — a different mistake a sender corrects differently (pick another id).
// Both map to VALIDATION_FAILED, but collapsing them into one code would make the
// sender read "unknown job" for a job that exists, which is a lie about the state.
const E_JOB_EXISTS = 'E_JOB_EXISTS';

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
  E_JOB_EXISTS,
};

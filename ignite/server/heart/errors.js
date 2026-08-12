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
// Typed refusal for the PURGE arm of `deregister-job` (the catalogue's reclaim path).
// ONE code, not three, and that is the D23 "invent only when necessary" line held: the
// three refusals it carries — the row is still enabled, pending queue rows reference it,
// a non-terminal execution is still running it — are all "the catalogue will not let go
// of this id YET", and a caller branches on `details.reason` (`enabled` |
// `pending-queue-rows` | `live-executions`), which each message also names in words along
// with the command that clears it. Distinct from E_JOB_EXISTS (that id is taken, pick
// another) and E_UNKNOWN_JOB (no such id): here the id exists, the sender may have it,
// and something concrete is in the way.
const E_JOB_PURGE_REFUSED = 'E_JOB_PURGE_REFUSED';

// G-135. Raised at DAEMON START, which is the only place they can be raised: the store is opened
// before anything else exists. Both are refusals to proceed on a store this build cannot honestly
// operate — never a partial migration, never an open store that lies about its shape.
const E_MIGRATION_FAILED = 'E_MIGRATION_FAILED';
const E_STORE_NEWER_THAN_CODE = 'E_STORE_NEWER_THAN_CODE';

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
  E_JOB_PURGE_REFUSED,
  E_MIGRATION_FAILED,
  E_STORE_NEWER_THAN_CODE,
};

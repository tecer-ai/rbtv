'use strict';

class EndingStoreError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'EndingStoreError';
    this.code = code;
    this.details = details;
  }
}

const E_WRITE_ONCE = 'E_WRITE_ONCE';
const E_KILLED_VOCABULARY = 'E_KILLED_VOCABULARY';
const E_WRITER_REFUSED = 'E_WRITER_REFUSED';
const E_BAD_ENDING = 'E_BAD_ENDING';
const E_MISSING_EVIDENCE = 'E_MISSING_EVIDENCE';
const E_ASK_NOT_FOUND = 'E_ASK_NOT_FOUND';
const E_NO_CURRENT_ENDING = 'E_NO_CURRENT_ENDING';

module.exports = {
  EndingStoreError,
  E_WRITE_ONCE,
  E_KILLED_VOCABULARY,
  E_WRITER_REFUSED,
  E_BAD_ENDING,
  E_MISSING_EVIDENCE,
  E_ASK_NOT_FOUND,
  E_NO_CURRENT_ENDING,
};

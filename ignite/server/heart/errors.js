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
};

'use strict';

function failure({ path = null, operation = null, requirement, expected, reason }) {
  return { path, operation, requirement, expected, reason };
}

function fromMessage(message, extra = {}) {
  return failure({
    path: extra.path || null,
    operation: extra.operation || null,
    requirement: message,
    expected: extra.expected || message,
    reason: message,
  });
}

class Refusal extends Error {
  constructor(message, failures = []) {
    super(message);
    this.name = 'Refusal';
    this.failures = failures;
  }
}

function refusalError(failures) {
  const rows = failures.length ? failures : [fromMessage('proposal refused')];
  return new Refusal(rows.map((row) => row.reason).join('\n'), rows);
}

module.exports = { failure, fromMessage, Refusal, refusalError };

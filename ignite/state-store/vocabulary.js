'use strict';

const ENDINGS = Object.freeze(['done', 'incomplete', 'failed']);
const GOAL_WORDS = Object.freeze(['running', 'paused', 'finished']);
const REASON_CLASSES = Object.freeze([
  'provider-error',
  'configuration-error',
  'crash',
  'killed-no-progress',
  'outputs-missing',
  'inputs-missing',
  'launch-refused',
]);
const NAMED_EVENTS = Object.freeze([
  'ask-answered',
  'materialize-resolved',
  'named-external-input',
]);
const ASK_LABELS = Object.freeze(['work-content', 'recovery']);
const ASK_STATES = Object.freeze(['open', 'answered', 'closed']);
const WHO_ENDING = Object.freeze(['seat', 'system']);
const WHO_GOAL = Object.freeze(['owner', 'system']);

const LISTED_INCOMPLETE = Object.freeze({
  'context full': { armed: 1, named_event: null, who_stamped: 'seat' },
  'blocked-on-human': { armed: 0, named_event: 'ask-answered', who_stamped: 'system' },
  'materialize-failed': { armed: 0, named_event: 'materialize-resolved', who_stamped: 'system' },
  'attempt-counter exhaustion': { armed: 0, named_event: 'named-external-input', who_stamped: 'system' },
  'gate-re-plan cap': { armed: 0, named_event: 'ask-answered', who_stamped: 'system' },
});

const KILLED_WORDS = Object.freeze(new Set([
  'exited',
  'unverified',
  'revive',
  'renew',
  'READY',
  'RUNNING',
  'RENEWING',
  'IDLE',
  'STOPPED',
  'HELD',
  'UNBUILT',
  'UNDECLARED',
  'SKEW',
  'BLOCKED',
  'RENEW-BLOCKED',
  'clean',
  'crashed',
  'killed',
  'waiting-on-owner',
  'parked',
  'frozen',
  'hold-anchor',
  'renew-interrupted',
  'rule-disposition',
  'RULED_FLIP_FROM_STATES',
]));

function isKilledWord(value) {
  if (value == null || value === '') return false;
  return KILLED_WORDS.has(String(value));
}

module.exports = {
  ENDINGS,
  GOAL_WORDS,
  REASON_CLASSES,
  NAMED_EVENTS,
  ASK_LABELS,
  ASK_STATES,
  WHO_ENDING,
  WHO_GOAL,
  LISTED_INCOMPLETE,
  KILLED_WORDS,
  isKilledWord,
};

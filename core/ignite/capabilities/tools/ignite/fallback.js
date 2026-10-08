'use strict';

// Everything Ignite does about a fallback: a model that runs a turn in place of the agent's own
// model when that one fails to start. The rule that picks the models is cast's
// (cast/lib/fallback.js) and is only called here.
//
// API
// planFor(setting, home, log) → cast's fallback plan for the agent's model, or null: the
//   installation's fallback is off, the model catalog gives the model no level, or the defaults
//   or the catalog cannot be read (logged as `fallback-unavailable`).
// requestList(plan, sessionOf, promptFor) → the `fallbacks` of a turn request: each candidate
//   with the conversation's own session on its harness, a new one when `sessionOf(harness)`
//   has none, and the prompt for that session. undefined when there is no plan.
// failureWords(launcher, plan) → the parts of a turn's failure that a fallback explains.
// report(launcher, plan, { store, claim, log }) → logs `fallback` and queues Ignite's own
//   message to the owner in the turn's conversation:
//     fallback:<run id>    a turn that ran on a fallback: each model that did not start, how
//                          its run ended, and the model that ran. Queued before the turn's
//                          replies, and its id sorts before theirs, so it is delivered first.
//     no-model:<queue id>  no model of the level started. The store keeps the first row of an
//                          id, so the retries of one queued input send it once.

const { exhausted, fallbackPlan, howEnded, nameOf } = require('../../../../cast/capabilities/tools/cast/lib/fallback');

function planFor(setting, home, log) {
  const plan = fallbackPlan(setting.harness, setting.model, setting.effort, home);
  if (!plan?.problem) return plan;
  if (typeof log === 'function') log({ event: 'fallback-unavailable', message: plan.problem });
  return null;
}

function requestList(plan, sessionOf, promptFor) {
  if (!plan) return undefined;
  return plan.candidates.map((candidate) => {
    const id = sessionOf(candidate.harness);
    const session = id ? { mode: 'resume', id } : { mode: 'new' };
    return { harness: candidate.harness, model: candidate.model, effort: candidate.effort,
      session, prompt: promptFor(session) };
  });
}

// cast's words for a level with no model left, or null when the turn did not end that way.
function noneStarted(launcher, plan) {
  return launcher?.exhausted && plan ? exhausted(plan, [...launcher.failed, launcher]) : null;
}

function failureWords(launcher, plan) {
  const none = noneStarted(launcher, plan);
  if (none) return none;
  if (!launcher?.failed?.length) return [];
  const failed = launcher.failed.map((f) => `${nameOf(f)} (${f.error})`).join(', ');
  return [`did not start: ${failed}; ${nameOf(launcher)} ran in their place and failed`];
}

function report(launcher, plan, { store, claim, log }) {
  const failed = launcher?.failed || [];
  if (failed.length && typeof log === 'function') {
    log({ event: 'fallback', failed, ran: { harness: launcher.harness, model: launcher.model } });
  }
  const none = noneStarted(launcher, plan);
  if (!none && !failed.length) return;
  const text = none
    ? none.join('; ')
    : `${failed.map((f) => `the model ${nameOf(f)} has failed (${howEnded(f.end)})`).join(', ')}, routing to ${nameOf(launcher)}`;
  store.enqueueOutbox({
    id: none ? `no-model:${claim.id}` : `fallback:${claim.runId}`,
    conversationKey: claim.conversation_key,
    payload: { text: `System message: ${text}`, audio: false, files: [] },
  });
}

module.exports = { planFor, requestList, failureWords, report };

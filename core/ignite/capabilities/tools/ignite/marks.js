'use strict';

// API
// setMark(slack, channel, ts, state, { log? }) → void. Never throws.
//   Marks one owner message with the reaction for its state and removes the reactions of the
//   states it replaces. state is received | working | replied | failed (MARKS below). The
//   reaction is added first, so the message is never bare. Any Slack error (already_reacted,
//   no_reaction, network) is swallowed: a mark never breaks a turn or a delivery. The two
//   expected codes (already_reacted, no_reaction) pass silently; any other is logged as
//   { event: 'mark-failed' }. A slack client without addReaction is a no-op.

const MARKS = {
  received: 'hourglass_flowing_sand',
  working: 'eyes',
  replied: 'heavy_check_mark',
  failed: 'heavy_multiplication_x',
};

// The reactions each state replaces. A retry or a work retry moves a message back from failed
// or working, so received and working clear failed too.
const REPLACES = {
  received: ['working', 'failed'],
  working: ['received', 'failed'],
  replied: ['received', 'working'],
  failed: ['received', 'working'],
};

async function setMark(slack, channel, ts, state, { log } = {}) {
  if (!slack || !channel || !ts || typeof slack.addReaction !== 'function') return;
  const note = (step, error) => {
    if (/already_reacted$|no_reaction$/.test(error.message)) return;
    if (typeof log !== 'function') return;
    try { log({ event: 'mark-failed', state, step, message: error.message }); } catch { /* keep the turn */ }
  };
  try {
    await slack.addReaction(channel, ts, MARKS[state]);
  } catch (error) {
    note('add', error);
  }
  if (typeof slack.removeReaction !== 'function') return;
  for (const old of REPLACES[state]) {
    try {
      await slack.removeReaction(channel, ts, MARKS[old]);
    } catch (error) {
      note(`remove-${old}`, error);
    }
  }
}

module.exports = { setMark, MARKS };

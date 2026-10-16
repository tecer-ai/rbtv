'use strict';

// The /legend slash command: any user of the workspace opens a modal, seen only by them, that explains
// every live status reaction. The states, their order and their meanings are Ignite's (live-status.js
// MEANING); the view and its emoji are the Slack connector's (lib/live-status.js legendView).
//
// API
// createLegend({ slack, log? }) → { handle(type, payload) }
//   slack() → the Slack client. handle is an interactions handle of slack.js connect, run after the ACK:
//   a /legend slash command, from any user, opens the legend with its trigger_id; anything else is
//   ignored. It never rejects: a failed views.open is logged as { event: 'legend', action: 'open-failed' }.

const { MEANING } = require('./live-status.js');
const { legendView } = require('../../../../../connectors/slack/capabilities/tools/slack/lib/live-status.js');

function createLegend({ slack, log = () => {} } = {}) {
  async function handle(type, payload = {}) {
    if (type !== 'slash_commands' || payload?.command !== '/legend') return;
    try {
      await slack().openView(payload.trigger_id, legendView(MEANING));
    } catch (error) {
      try { log({ event: 'legend', action: 'open-failed', message: error.message }); } catch { /* the legend never fails on a log */ }
    }
  }
  return { handle };
}

module.exports = { createLegend };

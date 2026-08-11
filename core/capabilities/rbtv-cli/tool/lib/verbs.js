'use strict';

// The ACTION VERB registry — the routes that DO something rather than deliver
// content. Every one of them DELEGATES: this CLI owns no second implementation of
// any behaviour that already ships (PRIN-11). The registry is data so that the
// disjointness check in selftest.js can read it, rather than a human re-deriving
// it each time a route is added.

const path = require('path');
const { RBTV_ROOT } = require('./catalog');

const DAEMON_OPERATOR = path.join(
  RBTV_ROOT, 'ignite', 'capabilities', 'daemon-operator', 'tool', 'rbtv-ignite-daemon',
);
const GATEWAY_CLIENT = path.join(RBTV_ROOT, 'ignite', 'cli', 'ignite.js');
const GOALS_TREE = path.join(
  RBTV_ROOT, 'ignite', 'capabilities', 'goals-tree', 'tool', 'rbtv-goal',
);
const TICKER_SETTINGS = path.join(
  RBTV_ROOT, 'ignite', 'capabilities', 'ticker-settings', 'tool', 'rbtv-ignite-ticker',
);
// 7.607 E3 renamed the capability and its entry point (`attached-run/tool/rbtv-run` ->
// `attached-execution/tool/rbtv-execution`, design-lock item 7). The `run` VERB below is
// deliberately unchanged — it is this CLI's user surface, not the renamed component.
const ATTACHED_EXECUTION = path.join(
  RBTV_ROOT, 'ignite', 'capabilities', 'attached-execution', 'tool', 'rbtv-execution',
);
const TEAMBUILD = path.join(
  RBTV_ROOT, 'core', 'capabilities', 'teambuild', 'tool', 'rbtv-teambuild',
);

// Task 7.66 built the cadence-edit surface, so the namespace that previously refused now routes.
// `set-interval` is the DESIGN's verb name (operator-surface design § 2.3), not coined here — the
// reason the earlier route deliberately named none was to leave that word to this task, and the
// task took it from the design rather than inventing a second one.
const TICKER_VERBS = ['show', 'set-interval', 'history', 'selftest'];

// The five daemon verbs are the DESIGN's and the registry's, not this CLI's, and
// they fold in verbatim: same verbs, same names, same exit codes. `unit` is NOT
// named `status` — `ignite status` is the daemon's report of ITSELF and needs it
// alive; `unit` is the machine's report ABOUT the daemon and works when it is
// dead. No field appears in both, which is the only reason PRIN-11 is satisfied.
const DAEMON_VERBS = ['start', 'restart', 'stop', 'kill', 'unit', 'selftest'];


// The gateway client's own command set. Kept here ONLY to route and to prove
// disjointness; the client remains the single source of truth for its behaviour
// and its help (`rbtv ignite --help` execs the client's own help).
const GATEWAY_COMMANDS = [
  'register-job', 'add-job', 'remove-job', 'inspect',
  'snooze', 'status', 'send', 'screen', 'kill',
];

const GOAL_VERBS = ['scaffold', 'reindex', 'lint', 'materialize', 'selftest'];

// Core-build task 7.433. The staffing-discovery browse — one database per verb.
// `search` joins them at 7.434: the semantic ranking now exists behind its own
// provider-module boundary (teambuild's lib/provider.js) and rides that same corpus
// enumerator, so the route no longer points at nothing.
const TEAMBUILD_VERBS = ['agents', 'units', 'seats', 'tasks', 'workflows', 'search', 'selftest'];

// Routes are matched by their token PREFIX, longest first, so `ignite daemon kill`
// (the unit) can never be shadowed by `ignite kill` (a gateway session). Both
// exist, they mean different things, and the extra token is what tells them apart.
const ROUTES = [
  {
    prefix: ['ignite', 'daemon'],
    target: DAEMON_OPERATOR,
    exec: 'direct',
    verbs: DAEMON_VERBS,
    summary: 'ignite daemon lifecycle — start/restart/stop/kill/unit (systemd user unit; works when the daemon is DOWN)',
  },
  {
    prefix: ['ignite', 'ticker'],
    target: TICKER_SETTINGS,
    exec: 'direct',
    verbs: TICKER_VERBS,
    summary: 'ignite tick cadence — show/set-interval/history (edits settings.json; takes effect at the next daemon restart)',
  },
  {
    prefix: ['ignite'],
    target: GATEWAY_CLIENT,
    exec: 'node',
    verbs: GATEWAY_COMMANDS,
    summary: 'ignite gateway client — jobs, queue, sessions (every call crosses the gateway; needs the daemon UP)',
  },
  {
    prefix: ['goal'],
    target: GOALS_TREE,
    exec: 'direct',
    verbs: GOAL_VERBS,
    summary: 'goals-tree machinery — scaffold/reindex/lint/materialize a goal folder',
  },
  // Core-build task 7.44. `run` takes no sub-verb: its argument is a GOAL FOLDER, not a word from a
  // fixed set, so `verbs` is empty and the disjointness check has nothing to collide with. It is
  // the one route that BOOTS the ignite engine rather than talking to something that already runs
  // it — attached to this terminal, dying with it (decisions.md#d-attached-run-embedded-engine).
  {
    prefix: ['run'],
    target: ATTACHED_EXECUTION,
    exec: 'direct',
    verbs: [],
    summary: 'run a goal ATTACHED to this terminal — the daemon\'s own engine, in-process, resumable from the goal folder',
  },
  {
    prefix: ['teambuild'],
    target: TEAMBUILD,
    exec: 'direct',
    verbs: TEAMBUILD_VERBS,
    summary: 'browse the component databases blurb-first — agent cards, kind-filtered cognitive units, seats, tasks, workflows — or `search` them by meaning (read-only; binds nothing)',
  },
];

// The tokens that, at position 1, belong to the verb namespace rather than the
// drill. A module name landing in this set would make `rbtv <module>` ambiguous —
// selftest ASSERTS the sets are disjoint rather than inferring it from today's
// data, because the failure would otherwise arrive silently with a future module.
function verbNamespaceTokens() {
  return [...new Set(ROUTES.map((r) => r.prefix[0]))];
}

// Longest prefix wins.
function matchRoute(argv) {
  let best = null;
  for (const route of ROUTES) {
    const p = route.prefix;
    if (p.length > argv.length) continue;
    if (p.every((tok, i) => argv[i] === tok)) {
      if (!best || p.length > best.prefix.length) best = route;
    }
  }
  return best;
}

module.exports = {
  ROUTES,
  DAEMON_OPERATOR,
  GATEWAY_CLIENT,
  GOALS_TREE,
  DAEMON_VERBS,
  GATEWAY_COMMANDS,
  GOAL_VERBS,
  TEAMBUILD,
  TEAMBUILD_VERBS,
  verbNamespaceTokens,
  matchRoute,
};

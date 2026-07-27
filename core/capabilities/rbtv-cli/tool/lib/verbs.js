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
  // The NAMESPACE is registered and refuses; NO verb name is coined. Naming a verb
  // here would be the smallest possible invention of 7.66's schema — and if 7.66
  // settles on a different word, a coined verb is one more thing to migrate. The
  // namespace carries the teaching without pre-empting the task (leader ruling on
  // this seat's premise audit, #235).
  {
    prefix: ['ignite', 'ticker'],
    target: null,
    exec: 'unbuilt',
    verbs: [],
    summary: 'ignite tick cadence — NOT BUILT (core-build task 7.66)',
    unbuilt: {
      task: '7.66',
      why:
        'The cadence edit writes settings.json, and the settings.json schema plus the '
        + 'settings-history.jsonl line format are UNRULED — task 7.66 settles them as part of '
        + 'building this consumer. Naming a verb here would invent that schema.',
    },
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
  verbNamespaceTokens,
  matchRoute,
};

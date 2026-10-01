'use strict';

// The ACTION VERB registry — the routes that DO something rather than deliver
// content. Every one of them DELEGATES: this CLI owns no second implementation of
// any behaviour that already ships (PRIN-11). The registry is data so that the
// disjointness check in selftest.js can read it, rather than a human re-deriving
// it each time a route is added.
//
// Ignite 0.1 verbs (ignite daemon, ignite ticker, the gateway client, goal, run)
// are not routed. Their delegates live in the 0.1 tree and are deleted with it.

const path = require('path');
const { RBTV_ROOT } = require('./root');

// Installing rbtv into a workspace is the installer's job; its own argparse prog is
// already `rbtv install`, and this route makes that string true.
const INSTALLER = path.join(
  RBTV_ROOT, 'core', 'installer', 'capabilities', 'tools', 'rbtv-install', 'install.py',
);

// Advertise the current installer commands. Every token after `install` is
// delegated unchanged, so aliases and retired forms can still receive the
// installer's own help or teaching refusal.
const INSTALL_VERBS = ['status', 'list', 'search', 'show', 'configure',
  'add', 'remove', 'update', 'agent', 'doctor', 'interactive', 'selftest'];

// Routes are matched by their token PREFIX, longest first, so a later
// multi-token route can never be shadowed by a shorter one that shares its head.
const ROUTES = [
  {
    prefix: ['install'],
    target: INSTALLER,
    exec: 'direct',
    verbs: INSTALL_VERBS,
    summary: 'discover and manage rbtv units and agents in a workspace — status, list, show, add, remove, agent, doctor',
  },
];

// The tokens that, at position 1, are this CLI's own commands rather than a
// delegated route. selftest asserts retired names stay out of this set.
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
  INSTALLER,
  INSTALL_VERBS,
  verbNamespaceTokens,
  matchRoute,
};

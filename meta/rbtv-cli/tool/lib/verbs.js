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
const { RBTV_ROOT } = require('./catalog');

const CONTROL_PANEL = path.join(
  RBTV_ROOT, 'meta', 'control-panel', 'tool', 'rbtv-control-panel',
);
// The installer lives in the `meta` module (owner ruling, 2026-08-22): `meta/` hosts
// what operates on the rbtv SYSTEM itself rather than on a user goal's content, and
// installing rbtv into a workspace is exactly that — `core/` was the wrong home and
// `core/capabilities/installer/` (the unbuilt second installer) is gone with it. Its
// own argparse prog is already `rbtv install`; this route makes that string true.
const INSTALLER = path.join(RBTV_ROOT, 'meta', 'installer', 'install.py');

const CONTROL_PANEL_VERBS = ['update', 'status', 'selftest'];

// The installer's own verb set. `harness` and `artifact` own the two WORKSPACE
// SETTINGS (which AI tools to write files for, and which root guidance file the
// human authors): `add` chooses components and refuses those flags after the
// first install, so a human who reaches for them lands on the verb that works
// rather than on a run that succeeds and changes nothing (installer D16).
// `set` joined at D16b (2026-08-22): the workspace settings moved to an
// ACTION-FIRST grammar (`add harness`, `rm harness`, `set artifact`), and the
// basis needs a third action word because choosing a new one REPLACES the old.
//
// `harness` and `artifact` are RETIRED verbs kept on this list deliberately
// (D16c): the installer no longer advertises them — their three values are
// read at the head of `rbtv install li` — but it still answers them with a
// refusal naming where they went. Dropping them here would replace that
// sentence with this CLI's own `not a component or action verb`, which knows
// nothing about the move.
const INSTALL_VERBS = ['list', 'status', 'show', 'add', 'remove', 'doctor',
  'rm', 'set', 'ls', 'li', 'harness', 'artifact',
  'dupe-artifacts', 'selftest', 'interactive'];

// Routes are matched by their token PREFIX, longest first, so a later
// multi-token route can never be shadowed by a shorter one that shares its head.
const ROUTES = [
  {
    prefix: ['install'],
    target: INSTALLER,
    exec: 'direct',
    verbs: INSTALL_VERBS,
    summary: 'discover and manage rbtv parts in a workspace — status, list, show, add, remove, doctor',
  },
  {
    prefix: ['control-panel'],
    target: CONTROL_PANEL,
    exec: 'direct',
    verbs: CONTROL_PANEL_VERBS,
    summary: 'build the control panel — one page over the scaffolding (seats, workflows) from shipped rbtv + the mirror; output lives outside the tree',
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
  CONTROL_PANEL,
  CONTROL_PANEL_VERBS,
  INSTALLER,
  INSTALL_VERBS,
  verbNamespaceTokens,
  matchRoute,
};

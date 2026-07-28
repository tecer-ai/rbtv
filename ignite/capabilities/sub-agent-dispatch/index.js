'use strict';

// ignite/capabilities/sub-agent-dispatch — the CLI-lane instrument of CMP-10's standing sub-agent
// lane (task 7.43; registry decisions.md#d-sub-agent-standing-lane, CMP-10 § Standing sub-agent
// lane, enforcement class ruled by #d-sub-agent-exposure-enforcement).
//
// TWO INSTRUMENTS, ONE CAGE, TYPED BY LANE. The harness-native sub-agent tool is the preferred
// instrument and its counterpart bounds are `constraints`-class — judgment-honored, carried to the
// dispatching agent by the rule task 7.49 already ships. THIS lane's bounds are
// `restrictions`-class: fail-closed in this capability's own code, with nothing left to the
// model's judgment. Neither lane's bounds are restated in the other's home.
//
// Native-tool DETECTION is deliberately absent: native-first is guidance for the AGENT (CMP-10
// boundary 7, HONORED), and this CLI does not need to detect what the caller is running inside.

const dispatch = require('./dispatch');
const catalog = require('./catalog');
const env = require('./env');
const fanout = require('./fanout');
const errors = require('./errors');

module.exports = {
  // the dispatch path
  dispatch: dispatch.dispatch,
  // the individual bounds, exported so a probe can exercise each one on its own terms
  assertNotNested: dispatch.assertNotNested,
  assertNotSeatIdentity: dispatch.assertNotSeatIdentity,
  resolveTarget: catalog.resolveTarget,
  loadCatalog: catalog.loadCatalog,
  buildChildEnv: env.buildChildEnv,
  reserveFanoutSlot: fanout.reserve,
  // vocabulary
  DISPATCHABLE_METHOD: catalog.DISPATCHABLE_METHOD,
  FANOUT_MAX: fanout.FANOUT_MAX,
  DEPTH_VAR: env.DEPTH_VAR,
  MINIMAL_PATH: env.MINIMAL_PATH,
  BASE_PASSTHROUGH: env.BASE_PASSTHROUGH,
  // errors — re-exported so a consumer never reaches into another module's error file, and the
  // two upstream error surfaces with them: a caller of this lane catches refusals from all three
  // modules and must be able to name them without importing three files.
  ...errors,
  SpawnError: require('../../launch-profiles').SpawnError,
  LadderError: require('../../injection-ladder').LadderError,
};

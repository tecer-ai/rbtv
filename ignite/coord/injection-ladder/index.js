'use strict';

// ignite/coord/injection-ladder — THE one per-harness injection ladder (CMP-9).
//
// Task 7.45; registry decisions.md#d-injection-ladder-shared + #d-profile-source-unification.
// Three consumers read this module and no other (CMP-9 § Interface (1)):
//   1. the daemon's spawn path                            — LIVE (server/spawn/harness-config.js
//                                                            is a thin adapter over this)
//   2. the attached dispatch surface (rbtv CLI run verb)   — task 7.44, NOT BUILT. Its former
//      other half, the sub-agent dispatch capability (7.43), is RETIRED — the daemon's sub-agent
//      lane is gone; delegation is seat-side (r-seats-only-architecture, 2026-08-06)
//   3. the orchestration conductor's CLI-worker dispatch   — task 7.54, NOT BUILT
//
// ⚠ The unbuilt consumers list 7.45 in their own `_Depends:_`. So this module ships with ONE
// live consumer not because the work stopped short but because the other two CANNOT be built before
// it. Said plainly here so no reader infers more completeness than exists — the same disclosure
// 7.42 made for `resolveProfile()`, for the same structural reason.
//
// ⚠ THE ONE THING A CALLER MUST NOT DO: never pass the rung in. `resolveRung()` takes the SITUATION
// (harness, phase, whether the session must be reachable again, host capability) and WALKS. A caller
// that hands the ladder the rung it wanted has exercised everything except the selection, which is
// `p-green-harness-over-a-broken-mechanism` — and a check written over that call cannot fail.
//
// WHERE THE PRESET DATA IS RULED TO LIVE, and does not yet: CMP-9 § Interface (5) rules the
// per-harness driving knowledge into the model-and-harness catalog at the runtime root's `config/`
// (`CMP-1` § Model-and-harness catalog; owner-ruled decisions.md#d-elist-model-catalog-relocation,
// pinned by #d-cmp9-preset-data-home). That relocation is UNBUILT and carries no Phase-7 task
// (measured: zero grep hits for its anchors over the whole core-build tasks file, 2026-07-28).
// This module is therefore an INTERIM home beside 7.42's `ignite/launch-profiles/`, and says so
// rather than quietly becoming the destination. See README § Known residuals.

const {
  RUNGS,
  RUNG_PHASES,
  HARNESSES,
  KNOWN_HARNESSES,
  harnessOf,
  harnessFromBinary,
  rungsFor,
  rungFor,
  resolveRung,
  hooksConfigFor,
} = require('./ladder');
const errors = require('./errors');

module.exports = {
  // the walk — the module's whole point
  resolveRung,
  // harness identification (D23: from the profile's own exec argv[0])
  harnessOf,
  harnessFromBinary,
  // reading the table directly (reporting, probes, a consumer that must explain a refusal)
  rungsFor,
  rungFor,
  hooksConfigFor,
  // vocabulary
  RUNGS,
  RUNG_PHASES,
  HARNESSES,
  KNOWN_HARNESSES,
  // errors — re-exported so a consumer never reaches into another module's error file
  ...errors,
};

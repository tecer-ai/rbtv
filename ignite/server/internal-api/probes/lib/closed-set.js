'use strict';

// closed-set — the shared drift-guard helpers for the batch-08 closed-set probes.
//
// Batch 08 found THREE closed sets that were each correct when written with NO
// mechanism to STAY correct: the gateway intent allowlist, the dispatch gate<->switch
// handler pair (item 5, task 7.16), and the STORE_TO_WIRE error map (item 7, task
// 7.18). Two probes guarding the same shape must not duplicate the partition logic —
// a duplicated checker would itself be a fourth undetected-drift closed set. This lib
// is the ONE home; probe-error-map-drift.js and probe-intent-drift.js both require it.
//
// Both helpers return an ARRAY OF FAILURE STRINGS, each NAMING the set and the member
// — never a boolean. A drift guard that cannot say WHICH set is missing WHAT gets
// ignored; naming the finding is the contract.

// checkClosedSetPartition — every universe member in EXACTLY ONE side.
//
// universe: Set of the values that must all be classified.
// sides:    [{ name, keys }] — the closed sets that together must partition the universe.
// describe: optional message overrides, each returning the full failure string:
//   staleRow(sideName, key)        — a side carries a key the universe does not define
//   unclassified(key)              — a universe member in NO side
//   contradiction(key, homeNames)  — a universe member in MORE THAN ONE side
//
// Failure classes: STALE ROW (a side carries a key outside the universe),
// UNCLASSIFIED (a member in no side — the silent-decay case), CONTRADICTION (a member
// in more than one side).
function checkClosedSetPartition({ universe, sides, describe = {} }) {
  const failures = [];
  const membership = new Map(); // key -> [side names]
  for (const { name, keys } of sides) {
    for (const key of keys) {
      if (!universe.has(key)) {
        failures.push(describe.staleRow
          ? describe.staleRow(name, key)
          : `STALE ROW: ${name} carries '${key}', which is not in the universe`);
      }
      membership.set(key, [...(membership.get(key) || []), name]);
    }
  }
  for (const key of [...universe].sort()) {
    const homes = membership.get(key) || [];
    if (homes.length === 0) {
      failures.push(describe.unclassified
        ? describe.unclassified(key)
        : `UNCLASSIFIED: '${key}' is in none of ${sides.map((s) => s.name).join(' / ')}`);
    } else if (homes.length > 1) {
      failures.push(describe.contradiction
        ? describe.contradiction(key, homes)
        : `CONTRADICTION: '${key}' is in BOTH ${homes.join(' and ')}`);
    }
  }
  return failures;
}

// checkClosedSetsLockstep — N named copies of ONE closed set that must be IDENTICAL.
//
// The intent-set shape (task 7.16): the set is duplicated BY DESIGN (no shared
// constant is possible across the DEC-4 boundary), so the invariant is not a
// partition but LOCKSTEP — the universe is the UNION of all copies, and every copy
// must carry every universe member. Each miss is one failure naming the set that is
// missing the member.
//
// sets:     [{ name, keys }] — the copies.
// describe: optional missing(setName, key) returning the full failure string.
function checkClosedSetsLockstep({ sets, describe = {} }) {
  const universe = new Set();
  for (const { keys } of sets) for (const key of keys) universe.add(key);
  const failures = [];
  for (const { name, keys } of sets) {
    const have = new Set(keys);
    for (const key of [...universe].sort()) {
      if (!have.has(key)) {
        failures.push(describe.missing
          ? describe.missing(name, key)
          : `SET DRIFT: ${name} is MISSING '${key}'`);
      }
    }
  }
  return failures;
}

module.exports = { checkClosedSetPartition, checkClosedSetsLockstep };

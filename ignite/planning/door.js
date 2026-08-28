'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PLANNING_DIR = __dirname;
// ── WHAT THIS FILE IS NOW ────────────────────────────────────────────────────────────────
// It was the per-tick planning-mint pass (spec-planning-door §1 Path A): a goal carrying
// `role: planning` in its `goal.md` frontmatter, with the five pipeline seats absent from
// its `taskforce.csv`, was minted once per cadence. THE PASS IS DELETED (2026-08-28), and
// the deletion is a deviation from that spec's MECHANISM, not from its trigger.
//
// WHY. `role: planning` had NO PRODUCER. `goals-tree/tool/goal_cli.py#cmd_scaffold` writes
// exactly six frontmatter keys (name, creation-date, due-date, type, goal-kind, status) and
// no other route writes a `role:` key at all, so the admission test could never be true —
// measured as `planning-mint` appearing 0 times in 592,458 daemon journal lines. The spec's
// trigger ("a planning goal exists AND its five pipeline seats are not yet minted") is
// satisfied AT BIRTH instead: the ruled creation route
// (`goal-creation-request/tool/goal_creation_request.py#create`) runs `scaffold-seats
// --workflow plan-console` unconditionally in the same act, and `rbtv goal scaffold --lane
// daemon` REFUSES `daemon-lane-unmaterialized` rather than producing an unminted daemon
// goal. A daemon-lane goal that still reaches the watcher with no `taskforce.csv` is named
// out loud there (`supervisor/lane-watch.js`, reason `no-taskforce-yet`), not minted here.
//
// WHAT SURVIVES, and why it is not the door. `pipeline-seats.json` is still read by
// `argv.py` (`PLANNING_SEATS`, its `--seats-json` flag, and `path_a.py`'s uncast set), and
// it is NOT the source of truth for those names — it is a cached mirror of the workflow
// manifest `meta/planning/workflows/plan-console/plan-console.csv` (`Seat/workflow`
// column), which is what `materialize-seats.py --workflow plan-console` actually writes
// onto `taskforce.csv`. The two vocabularies MUST be one string set. The json is a bare
// array and carries no comment field, so the divergence alarm lives in code:
// `planning/queue-request.js` `planningManifestSeats()` reads the manifest, its module
// selftest deep-equals the two, and `planning/probes/probe-queue-request-pass.js` leg M
// fails on divergence.
const SEATS_FILE = path.join(PLANNING_DIR, 'pipeline-seats.json');
const PLANNING_SEATS = Object.freeze(JSON.parse(fs.readFileSync(SEATS_FILE, 'utf8')));

// MINTED, stated once and executably: every name in the mirror is a `seat` row on the goal's
// taskforce. `path_a.py` mints exactly this set, so a taskforce it wrote must read true here.
function pipelineMinted(rows) {
  const seats = new Set((rows || []).map((r) => String((r && r.seat) || '').trim()));
  return PLANNING_SEATS.every((s) => seats.has(s));
}

module.exports = { PLANNING_SEATS, SEATS_FILE, pipelineMinted };

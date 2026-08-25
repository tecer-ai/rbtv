#!/usr/bin/env node
'use strict';

// Resolves the channel master's cast the SAME WAY the live warm-path door does, and asserts the
// result is warm-path eligible. No daemon, no restart, no DM — a static read of the same files.
//
// The door being mirrored is `supervisor/spawn/live-sessions.js#eligible()`: it resolves the SEAT'S
// cast via `launchSpecForSeat`, then gates on `spec.resume` + `harnessOf(spec) ∈ LIVE_HARNESSES` +
// the seat's `human-interactive:` declaration. Every one of those is called here, from the real
// modules — nothing is reimplemented, so a change to the resolution law fails this check.
//
// ⚠ THERE IS NO REQUESTED PROFILE ANY MORE (`#d-abolish-profile-names`, 2026-08-12). This used to
// read `bridge.session_profile` and hand it in as the caller's name; that key is deleted and the
// door takes none. The bridge config is still read for ONE thing — `workdir`, which is WHERE master
// traffic homes, and therefore the seat whose cast decides everything else.
//
// `LIVE_HARNESSES` is not exported, so it is read out of the source text rather than copied: a
// copied literal would keep passing after the gate widened or narrowed.

const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const IGNITE = path.resolve(__dirname, '..', '..');
const WORKSPACE = path.resolve(IGNITE, '..', '..', '..', '..');   // same derivation as tool/master_profile.py's _IGNITE.parents[3]
const BRIDGE_CONFIG = path.join(WORKSPACE, '.rbtv', 'config', 'chat-bridge-config.json');
const LIVE_SESSIONS = path.join(IGNITE, 'supervisor', 'spawn', 'live-sessions.js');

const { loadConfig } = require(path.join(IGNITE, 'supervisor', 'spawn', 'config.js'));
const { launchSpecForSeat } = require(path.join(IGNITE, 'supervisor', 'spawn', 'spawn.js'));
const { harnessOf } = require(path.join(IGNITE, 'supervisor', 'spawn', 'harness-config.js'));
const { seatDirIsHumanInteractive } = require(path.join(IGNITE, 'chat', 'bus-ferry.js'));

const bridge = JSON.parse(fs.readFileSync(BRIDGE_CONFIG, 'utf8'));
const workdir = bridge.workdir;                    // master/DM traffic homes here (forward-path.js#workdirFor)

const config = loadConfig(path.join(IGNITE, 'envelope', 'spawn-profiles.yaml'));
const { key: profileName, spec: profile } = launchSpecForSeat(config.launchSpecs, workdir, () => {});
const harness = harnessOf(profile);
const model = (profile.exec.argv[profile.exec.argv.indexOf('--model') + 1]) || '';

const src = fs.readFileSync(LIVE_SESSIONS, 'utf8');
const liveHarnesses = new Set(
  /const LIVE_HARNESSES = new Set\(\[([^\]]*)\]\)/.exec(src)[1].match(/'([^']+)'/g).map(s => s.slice(1, -1)));

console.log(JSON.stringify({
  workdir, resolved_launch_spec: profileName,
  harness, model, has_resume_template: Boolean(profile.resume),
  live_harnesses: [...liveHarnesses],
  seat_human_interactive: seatDirIsHumanInteractive(workdir),
  // Both retired bridge keys, asserted absent below: `master_profile` (deleted 2026-08-11) and
  // `session_profile` (deleted 2026-08-12 by `#d-abolish-profile-names`). A config still carrying
  // either is a config whose author believes the transport names execution.
  master_profile_key_present: Object.prototype.hasOwnProperty.call(bridge, 'master_profile'),
  session_profile_key_present: Object.prototype.hasOwnProperty.call(bridge, 'session_profile'),
}, null, 2));

assert.strictEqual(harness, 'claude', `cast harness is ${harness}, not claude`);
assert.ok(/haiku/.test(model), `cast model is ${model}, not haiku-class`);
assert.ok(liveHarnesses.has(harness), `${harness} is not warm-path capable (LIVE_HARNESSES)`);
assert.ok(profile.resume, `${profileName} declares no resume: template — warm path refuses`);
assert.ok(seatDirIsHumanInteractive(workdir), 'seat does not declare human-interactive');
assert.ok(!Object.prototype.hasOwnProperty.call(bridge, 'master_profile'),
  'chat-bridge-config.json still carries master_profile — a dead key that contradicts the cast');
assert.ok(!Object.prototype.hasOwnProperty.call(bridge, 'session_profile'),
  'chat-bridge-config.json still carries session_profile — deleted by #d-abolish-profile-names; '
  + 'the bridge names no execution at all now');

console.log('OK — the channel master resolves to a warm-path-eligible claude/haiku cast');

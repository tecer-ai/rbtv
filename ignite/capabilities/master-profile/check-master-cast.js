#!/usr/bin/env node
'use strict';

// Resolves the channel master's cast the SAME WAY the live warm-path door does, and asserts the
// result is warm-path eligible. No daemon, no restart, no DM — a static read of the same files.
//
// The door being mirrored is `server/spawn/live-sessions.js#eligible()`: it takes the caller's
// profile name (the bridge's `session_profile`), replaces it with the SEAT'S cast via
// `profileForSeatCast`, then gates on `profile.resume` + `harnessOf(profile) ∈ LIVE_HARNESSES` +
// the seat's `human-interactive:` declaration. Every one of those is called here, from the real
// modules — nothing is reimplemented, so a change to the resolution law fails this check.
//
// `LIVE_HARNESSES` is not exported, so it is read out of the source text rather than copied: a
// copied literal would keep passing after the gate widened or narrowed.

const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const IGNITE = path.resolve(__dirname, '..', '..');
const WORKSPACE = '/home/henri/ht-wkdir/second-brain';
const BRIDGE_CONFIG = path.join(WORKSPACE, '.rbtv', 'config', 'chat-bridge-config.json');
const LIVE_SESSIONS = path.join(IGNITE, 'server', 'spawn', 'live-sessions.js');

const { loadConfig } = require(path.join(IGNITE, 'server', 'spawn', 'config.js'));
const { profileForSeatCast } = require(path.join(IGNITE, 'server', 'spawn', 'spawn.js'));
const { harnessOf } = require(path.join(IGNITE, 'server', 'spawn', 'harness-config.js'));
const { seatDirIsHumanInteractive } = require(path.join(IGNITE, 'bridges', 'chat', 'bus-ferry.js'));

const bridge = JSON.parse(fs.readFileSync(BRIDGE_CONFIG, 'utf8'));
const workdir = bridge.workdir;                    // master/DM traffic homes here (forward-path.js#workdirFor)
const requested = bridge.session_profile;          // the REQUEST; the seat's cast is the DECISION

const config = loadConfig(path.join(IGNITE, 'config', 'spawn-profiles.yaml'));
const profileName = profileForSeatCast(config.profiles, workdir, requested, () => {});
const profile = config.profiles[profileName];
const harness = harnessOf(profile);
const model = (profile.exec.argv[profile.exec.argv.indexOf('--model') + 1]) || '';

const src = fs.readFileSync(LIVE_SESSIONS, 'utf8');
const liveHarnesses = new Set(
  /const LIVE_HARNESSES = new Set\(\[([^\]]*)\]\)/.exec(src)[1].match(/'([^']+)'/g).map(s => s.slice(1, -1)));

console.log(JSON.stringify({
  workdir, requested_profile: requested, resolved_profile: profileName,
  harness, model, has_resume_template: Boolean(profile.resume),
  live_harnesses: [...liveHarnesses],
  seat_human_interactive: seatDirIsHumanInteractive(workdir),
  master_profile_key_present: Object.prototype.hasOwnProperty.call(bridge, 'master_profile'),
}, null, 2));

assert.strictEqual(harness, 'claude', `cast harness is ${harness}, not claude`);
assert.ok(/haiku/.test(model), `cast model is ${model}, not haiku-class`);
assert.ok(liveHarnesses.has(harness), `${harness} is not warm-path capable (LIVE_HARNESSES)`);
assert.ok(profile.resume, `${profileName} declares no resume: template — warm path refuses`);
assert.ok(seatDirIsHumanInteractive(workdir), 'seat does not declare human-interactive');
assert.ok(!Object.prototype.hasOwnProperty.call(bridge, 'master_profile'),
  'chat-bridge-config.json still carries master_profile — a dead key that contradicts the cast');

console.log('OK — the channel master resolves to a warm-path-eligible claude/haiku cast');

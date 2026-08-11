'use strict';
// Solo-run twin of the probe runner's tmux isolation (deploy/probe-suite.js § tmuxIsolatedEnv).
// The runner strips $TMUX and pins TMUX_TMPDIR for every child it spawns, so a probe run THROUGH
// the suite is safe. A probe or selftest run BY HAND from inside a pane (G-163 forbids it — this is
// defense-in-depth, not a licence) inherits neither, so a bare `tmux kill-server` reaches the
// operator DEFAULT server and kills every session on the box. Call selfIsolateTmux() FIRST, before
// any tmux touch: with $TMUX set it clears $TMUX/$TMUX_PANE and pins TMUX_TMPDIR to a throwaway
// /tmp dir, so every later tmux command lands on a socket no real session uses. No-op when $TMUX is
// unset — the suite child (runner already stripped it) and any non-tmux caller pass through
// untouched, so the runner stays PRIMARY and a second call cannot double-isolate (the first deletes
// $TMUX). Scratch rooted at os.tmpdir(), never a long path — a UNIX sun_path caps at ~108 bytes.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function selfIsolateTmux() {
  if (!process.env.TMUX) return process.env.TMUX_TMPDIR;
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtv-tmux-'));
  process.on('exit', () => { try { fs.rmSync(scratch, { recursive: true, force: true }); } catch {} });
  process.env.TMUX_TMPDIR = scratch;
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  return scratch;
}

module.exports = { selfIsolateTmux };

// ponytail self-check: `node probe-self-isolate.js` — asserts the gate both ways.
if (require.main === module) {
  const assert = require('node:assert');
  delete process.env.TMUX;
  const passthrough = selfIsolateTmux();
  assert.strictEqual(passthrough, process.env.TMUX_TMPDIR, 'no-op when $TMUX unset');
  process.env.TMUX = '/tmp/fake,1,0';
  const scratch = selfIsolateTmux();
  assert.ok(scratch && scratch.includes('rbtv-tmux-'), 'pins a private scratch when $TMUX set');
  assert.ok(!('TMUX' in process.env), '$TMUX cleared');
  assert.ok(!('TMUX_PANE' in process.env), '$TMUX_PANE cleared');
  assert.strictEqual(process.env.TMUX_TMPDIR, scratch, 'TMUX_TMPDIR pinned to scratch');
  assert.strictEqual(selfIsolateTmux(), scratch, 'idempotent second call (TMUX already gone)');
  console.log('probe-self-isolate self-check ok:', scratch);
}

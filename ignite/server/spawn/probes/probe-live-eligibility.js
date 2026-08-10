'use strict';

// ── Gate 1 of the warm path: `seatIsHumanInteractive`, over BOTH seat layouts ────────────────────
//
// The predicate is the ferry's, imported by `live-sessions.js` as the SEAT-DIR core
// (`seatDirIsHumanInteractive`). This probe exists because the goal-seat arms alone CANNOT
// discriminate the bug task 7.642 fixed: `live-sessions` reached the ferry through the
// `(goalDir, seat)` wrapper by splitting the seat dir with `dirname`², which is the exact inverse
// of the wrapper's `seats/<seat>/` join and therefore CORRECT for a goal seat and WRONG for a
// STANDING-SEAT HOME (`materialize-seats.py#standing_seat`, `r-master-seat-homes`), where the
// package IS the seat folder and `seat.md` sits at its root with no `seats/` layer. Every goal-seat
// arm passed while `_channel-master` — the one seat the warm path was built for — read FALSE and
// fell through to the cold path SILENTLY, because every ineligibility does, by design.
//
// ARMS
//   1  STANDING seat  — `seat.md` at the package root, NO `seats/` layer  → TRUE   (the discriminator)
//   2  GOAL seat      — `<goal>/seats/<seat>/seat.md` declaring the flag   → TRUE
//   3  GOAL seat      — the same tree with no declaration                  → FALSE
//   4  the F3 strip   — quoted value and trailing comment                  → TRUE  (both layouts)
//   5  eligible()     — a claude profile at a STANDING seat is ADMITTED, paired against the same
//                       profile at an undeclared seat, so gate 1 is proven to be READ
//
// ⚠ Arm 1 is what makes this file evidence, and it is proven RED by mutation: re-introduce the
// `dirname`² split in `live-sessions.js#seatIsHumanInteractive` and arm 1 fails (measured
// 2026-08-10, suite verdict RED, exit 1) while every GOAL-seat assertion here still holds under the
// same mutation — that asymmetry IS the bug, and it is why the goal-seat arms in
// `bridges/chat/probes/probe-chat-agent-thread.js` never saw it.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');

const IGNITE = path.resolve(__dirname, '../../..');
const REAL_PROFILES = path.join(IGNITE, 'config', 'spawn-profiles.yaml');
const LIVE_MODULE = path.join(IGNITE, 'server', 'spawn', 'live-sessions.js');
const FERRY_MODULE = path.join(IGNITE, 'bridges', 'chat', 'bus-ferry.js');

const SEAT_YES = '---\nseat: s\nhuman-interactive: yes\nfallback: park\n---\n\nbody\n';
const SEAT_NONE = '---\nseat: s\nfallback: park\n---\n\nbody\n';
// Both forms are TRUE to the `yaml.safe_load` that `component-lint` validates the seat with, so a
// reader that answers FALSE to either is the F3 defect (bus-ferry `seatDirIsHumanInteractive`).
const SEAT_QUOTED = '---\nseat: s\nhuman-interactive: "yes"\n---\n\nbody\n';
const SEAT_COMMENTED = '---\nseat: s\nhuman-interactive: true # ratified 2026-08-09\n---\n\nbody\n';

function writeSeat(dir, text) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'), text);
  return dir;
}

// The REAL profiles file with `spawn.data_root` overridden — the same choice
// `probe-chat-live-session.js` makes, and for the same reason: eligibility must be proven against
// the profiles the deployment actually ships, not a minimal one authored to pass.
function scratchConfig(root) {
  const dataRoot = path.join(root, 'state');
  fs.mkdirSync(dataRoot, { recursive: true });
  const yamlText = fs.readFileSync(REAL_PROFILES, 'utf8')
    .replace(/^(\s*)data_root:.*$/m, `$1data_root: ${dataRoot.replace(/\\/g, '/')}`);
  const configPath = path.join(root, 'spawn-profiles.yaml');
  fs.writeFileSync(configPath, yamlText);
  return configPath;
}

function must(lines, name, pass, detail = {}) {
  lines.push(`${pass ? 'ok  ' : 'FAIL'} ${name}${Object.keys(detail).length ? ` ${JSON.stringify(detail)}` : ''}`);
  if (!pass) throw new Error(`check failed: ${name}`);
}

capture('probe-live-eligibility', async (lines) => {
  const { seatIsHumanInteractive, createLiveSessions } = require(LIVE_MODULE);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-live-elig-'));
  let mgr = null;
  try {
    // ── ARM 1 — the STANDING-seat home: the package IS the seat folder ────────────────────────
    const standing = writeSeat(path.join(root, '.rbtv', 'goals', '_standing-master'), SEAT_YES);
    lines.push(`standing-seat home: ${standing} (seat.md at its ROOT, no seats/ layer)`);
    must(lines, 'arm1: a STANDING-seat home declaring the flag is human-interactive', seatIsHumanInteractive(standing) === true);
    // The split the fix removed, spelled out: this is the path the `dirname`² reach READ.
    const splitPath = path.join(path.dirname(path.dirname(standing)), 'seats', path.basename(standing), 'seat.md');
    must(lines, 'arm1: the retired dirname^2 split pointed at a path that does not exist',
      fs.existsSync(splitPath) === false, { splitPath });

    // ── ARMS 2/3 — the GOAL-seat layout, the pair that proves the reader is read at all ───────
    const goalYes = writeSeat(path.join(root, '.rbtv', 'goals', 'g1', 'seats', 'seat-yes'), SEAT_YES);
    const goalNo = writeSeat(path.join(root, '.rbtv', 'goals', 'g1', 'seats', 'seat-no'), SEAT_NONE);
    must(lines, 'arm2: a GOAL seat declaring the flag is human-interactive', seatIsHumanInteractive(goalYes) === true);
    must(lines, 'arm3: a GOAL seat with no declaration is NOT', seatIsHumanInteractive(goalNo) === false);
    must(lines, 'arm3: a seat dir with no seat.md at all is NOT',
      seatIsHumanInteractive(path.join(root, '.rbtv', 'goals', 'g1', 'seats', 'absent')) === false);

    // ── ARM 4 — the F3 strip survives the dedupe, in BOTH layouts ─────────────────────────────
    must(lines, 'arm4: `human-interactive: "yes"` (quoted) at a STANDING home is TRUE',
      seatIsHumanInteractive(writeSeat(path.join(root, '.rbtv', 'goals', '_quoted'), SEAT_QUOTED)) === true);
    must(lines, 'arm4: `human-interactive: true # …` (trailing comment) at a GOAL seat is TRUE',
      seatIsHumanInteractive(writeSeat(path.join(root, '.rbtv', 'goals', 'g1', 'seats', 'seat-cmt'), SEAT_COMMENTED)) === true);
    // FRONTMATTER ONLY — the same line in the body must not open the gate.
    must(lines, 'arm4: the flag in the BODY does not open gate 1',
      seatIsHumanInteractive(writeSeat(path.join(root, '.rbtv', 'goals', 'g1', 'seats', 'seat-body'),
        '---\nseat: s\n---\n\nhuman-interactive: yes\n')) === false);

    // ── ARM 5 — through `eligible()`, which is what the bridge actually asks ──────────────────
    mgr = createLiveSessions({ configPath: scratchConfig(root), workspaceRoot: path.join(root), reapPollMs: 3600000 });
    const admitted = mgr.eligible({ profileName: 'claude-haiku', workdir: standing });
    must(lines, 'arm5: a claude profile at a STANDING-seat home is ELIGIBLE',
      admitted.ok === true && admitted.harness === 'claude', { got: admitted });
    const refused = mgr.eligible({ profileName: 'claude-haiku', workdir: goalNo });
    must(lines, 'arm5: the SAME profile at an undeclared seat is refused ON GATE 1',
      refused.ok === false && refused.reason === 'seat-not-human-interactive', { got: refused });

    // ── ARM 6 — the SIBLING field, read from the SAME frontmatter block ───────────────────────
    // `fallback:` and `human-interactive:` are declared together (`_channel-master` sets both in
    // one act, vault commit `1c82a61f1`), so a reader of one that cannot see a STANDING-SEAT HOME
    // while its sibling can is the 7.642 blind spot rebuilt beside the fix. `seatDirFallback` is
    // that reader's core (task 7.656); the arm lives HERE rather than beside the goal-seat
    // `seatFallback` arms in `probe-chat-agent-thread.js` for the reason stated at the top of this
    // file — a `seats/<seat>/` fixture cannot discriminate the bug, and those arms never saw it.
    // ⚠ RED BY MUTATION: give the core back the `seats/` join it had before the split
    // (`path.join(seatDir, 'seats', path.basename(seatDir), 'seat.md')`) and arm 6's STANDING check
    // is the first thing to fail — `{"got":null}`, exactly the arm the ferry would have read for
    // `_channel-master` — while arms 1–5 stay green under that same mutation (measured 2026-08-10,
    // suite RED, exit 1; GREEN, exit 0 on revert). That asymmetry is the whole point of the arm.
    const { seatDirFallback, seatFallback } = require(FERRY_MODULE);
    must(lines, 'arm6: the SIBLING `fallback:` reader answers at a STANDING-seat home',
      seatDirFallback(standing) === 'park', { got: seatDirFallback(standing) });
    must(lines, 'arm6: it answers at a GOAL seat through the same core', seatDirFallback(goalYes) === 'park');
    must(lines, 'arm6: the `(goalDir, seat)` wrapper still joins `seats/<seat>/` and still guards the name',
      seatFallback(path.join(root, '.rbtv', 'goals', 'g1'), 'seat-yes') === 'park'
      && seatFallback(path.join(root, '.rbtv', 'goals', 'g1'), '../..') === null);
    must(lines, 'arm6: no `fallback:` line is null — absent is not a fourth arm',
      seatDirFallback(writeSeat(path.join(root, '.rbtv', 'goals', '_no-arm'), SEAT_QUOTED)) === null);

    lines.push('result: gate 1 answers for BOTH seat layouts; the standing-seat home is admitted end-to-end');
  } finally {
    if (mgr) { try { mgr.stop(); } catch {} }
    try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  }
});

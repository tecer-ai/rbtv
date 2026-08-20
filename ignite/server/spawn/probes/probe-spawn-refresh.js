'use strict';

// probe-spawn-refresh — D37 (2026-08-20): DOES A LAUNCH RE-RENDER THE SEAT-DESCRIPTOR FIRST,
// AND DOES A FAILED RE-RENDER STILL LET THE LAUNCH THROUGH?
//
// A seat-descriptor used to have exactly ONE lifecycle event: create. Catalog edits reached
// nothing already on disk — meet's chairs carried pre-D30 prose, m4's 18 `plan-4-*` sheets
// predated `delta-anchors`, 118 sheets carried EROFS-era prose — and D36's outputs projection
// would have reached nothing either. D37 gives the descriptor its second event at the one moment
// per-seat quiescence is already proven: the seat is being SPAWNED, so it is not sitting.
//
// The two facts this probe holds, and they pull in opposite directions ON PURPOSE:
//   (a) FRESHNESS — a catalog edit made after materialize IS on the sheet before any reader of it
//       runs (`launchSpecForSeat` reads the cast, `seatEffortRung` the rung, `composeArgv` hands
//       the file to the harness). Asserted through the REAL `spawnSeat` door, on the md5.
//   (b) NON-BLOCKING — a render that REFUSES leaves the old sheet byte-identical, writes ONE
//       journal line, and the launch continues. A stale descriptor is a working seat; a launch
//       that does not happen is a frozen goal, which is the defect this plan exists to end.
// Plus the dry-run control: composing an argv for inspection must leave the tree untouched.
//
// Everything here runs the REAL `materialize-seats.py --refresh` over a REAL catalog fixture
// (`materialize-seats.py#build_fixture`, the same one its own selftest uses) — no stub. A stub
// materializer is more permissive than the binary, and this probe exists to catch exactly the
// case where the binary says no.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { setup, teardown, capture } = require('./lib');
const { requirePythonCmd } = require('../../../lib/python-cmd');
const { refreshSeatDescriptor, catalogRootForSeat } = require('../spawn');

const TEAM_KIT = path.join(__dirname, '..', '..', '..', 'team-kit');
const MATERIALIZE_PY = path.join(TEAM_KIT, 'materialize-seats.py');

const md5 = (p) => crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex');

function py(args) {
  const r = spawnSync(requirePythonCmd(), args, { encoding: 'utf8', timeout: 180000 });
  return r;
}

// The catalog fixture, built by the materializer's OWN builder so the probe cannot drift from the
// shape the tool actually accepts.
function buildCatalog(root) {
  const r = py(['-c', [
    'import importlib.util, json, sys',
    'from pathlib import Path',
    `sys.path.insert(0, ${JSON.stringify(TEAM_KIT)})`,
    `spec = importlib.util.spec_from_file_location("ms", ${JSON.stringify(MATERIALIZE_PY)})`,
    'ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)',
    `fx = ms.build_fixture(Path(${JSON.stringify(root)}))`,
    'print(json.dumps({k: v for k, v in fx.items() if isinstance(v, str)}))',
  ].join('\n')]);
  if (r.status !== 0) throw new Error(`build_fixture failed: ${(r.stderr || '').slice(0, 500)}`);
  return JSON.parse(r.stdout.trim().split('\n').pop());
}

capture('probe-spawn-refresh', async (lines) => {
  const ctx = setup();
  try {
    // ── the fixture: a REAL catalog, a REAL goal folder inside the spawn root, a REAL seat ──
    const fxRoot = path.join(ctx.tmp, 'mfx');
    fs.mkdirSync(fxRoot, { recursive: true });
    const fx = buildCatalog(fxRoot);
    const goalDir = path.join(ctx.workRoot, '.rbtv', 'goals', 'refresh-goal');
    fs.cpSync(fx.pkg, goalDir, { recursive: true });
    fs.rmSync(path.join(goalDir, 'seats'), { recursive: true, force: true });

    // `component:` is a bindings key that rides into the descriptor; it is what the spawn door
    // reads to find the catalog root to re-render from (never a hardcoded module).
    const bindings = JSON.parse(fs.readFileSync(fx.b_alpha, 'utf8'));
    bindings.seats.alpha.component = path.join(fx.catalog, 'demo-comp') + path.sep;
    fs.writeFileSync(fx.b_alpha, JSON.stringify(bindings));

    const mat = py([MATERIALIZE_PY, '--package', goalDir, '--seat', 'alpha',
      '--catalog-root', fx.catalog, '--bindings', fx.b_alpha, '--root', '--json']);
    if (mat.status !== 0) throw new Error(`materialize failed: ${(mat.stdout + mat.stderr).slice(0, 500)}`);
    const seatDir = path.join(goalDir, 'seats', 'alpha');
    const sheet = path.join(seatDir, 'seat.md');
    lines.push(`fixture: seat.md materialized at ${sheet}`);

    const cr = catalogRootForSeat(seatDir);
    if (cr !== fx.catalog) throw new Error(`catalogRootForSeat: got ${cr}, want ${fx.catalog}`);
    lines.push(`ok    catalog root read off the descriptor's own \`component:\` line -> ${cr}`);

    // ── ARM A: a catalog edit AFTER materialize reaches the sheet, through the REAL spawn door ──
    const rolePath = path.join(fx.catalog, 'demo-comp', 'prompts', 'cognitive-units', 'roles', 'alpha-role.md');
    const MARK = 'REFRESHED-BY-PROBE-D37';
    fs.writeFileSync(rolePath, fs.readFileSync(rolePath, 'utf8').replace('You are alpha.', `You are alpha. ${MARK}`));
    const before = md5(sheet);
    if (fs.readFileSync(sheet, 'utf8').includes(MARK)) throw new Error('fixture is vacuous: the mark was already on the sheet');

    // The launch WILL fail — this fixture seat is cast `claude/claude-opus-5` and the probe's
    // launch-spec table carries only the `bash` fixture specs. That is exactly the point: the
    // throw comes from `launchSpecForSeat`, THE FIRST READER OF seat.md, so a sheet that carries
    // the mark afterwards can only have been re-rendered BEFORE that reader ran.
    let threw = null;
    try {
      await ctx.mgr.spawnSeat('probe-refresh-1', { room: null, seatName: 'alpha', seatDir });
    } catch (err) { threw = err.code || err.message; }
    const after = md5(sheet);
    const marked = fs.readFileSync(sheet, 'utf8').includes(MARK);
    if (before === after || !marked) {
      throw new Error(`ARM A FAILED — md5 ${before} -> ${after}, mark present=${marked} (launch threw ${threw})`);
    }
    lines.push(`ok    ARM A: catalog edited after materialize -> seat.md md5 ${before.slice(0, 12)} -> ${after.slice(0, 12)}, `
      + `carries ${MARK}, and it landed BEFORE the first reader (the launch threw ${threw} out of launchSpecForSeat)`);

    // ── ARM A-control: a DRY RUN refreshes nothing ──
    fs.writeFileSync(rolePath, fs.readFileSync(rolePath, 'utf8').replace(MARK, 'DRYRUN-MARK-MUST-NOT-LAND'));
    const dryBefore = md5(sheet);
    try {
      await ctx.mgr.spawnSeat('probe-refresh-2', { room: null, seatName: 'alpha', seatDir, dryRun: true });
    } catch { /* same later refusal; the md5 is the assertion */ }
    if (md5(sheet) !== dryBefore) throw new Error('ARM A-control FAILED — a dryRun spawn rewrote the descriptor');
    lines.push('ok    ARM A-control: the SAME call with dryRun:true leaves seat.md byte-identical — one flag apart, opposite outcome');

    // ── ARM B: a render that REFUSES leaves the sheet alone, journals once, and does not block ──
    fs.rmSync(path.join(fx.catalog, 'demo-comp', 'prompts.csv'));
    const bBefore = fs.readFileSync(sheet);
    const journal = [];
    refreshSeatDescriptor(seatDir, (level, message, extra) => journal.push({ level, message, extra }));
    const bAfter = fs.readFileSync(sheet);
    const skipped = journal.filter((j) => j.level === 'warn' && j.message === 'spawn: descriptor refresh skipped');
    if (!bBefore.equals(bAfter)) throw new Error('ARM B FAILED — a refused render changed the descriptor');
    if (skipped.length !== 1) throw new Error(`ARM B FAILED — want exactly 1 skip line, got ${JSON.stringify(journal)}`);
    lines.push(`ok    ARM B: catalog broken -> sheet byte-identical (${bBefore.length} bytes), ONE journal line: `
      + `warn "spawn: descriptor refresh skipped" reason="${String(skipped[0].extra.reason).slice(0, 120)}"`);

    // …and the launch still proceeds past the hook to its own, unrelated refusal.
    let threw2 = null;
    try {
      await ctx.mgr.spawnSeat('probe-refresh-3', { room: null, seatName: 'alpha', seatDir });
    } catch (err) { threw2 = err.code || err.message; }
    if (!threw2 || threw2 === 'E_REFRESH_FAILED') throw new Error(`ARM B FAILED — the hook blocked the launch (${threw2})`);
    if (!fs.readFileSync(sheet).equals(bBefore)) throw new Error('ARM B FAILED — the launch path rewrote the sheet anyway');
    lines.push(`ok    ARM B: with the catalog still broken the launch RAN ON and reached its own refusal (${threw2}) — `
      + 'the refresh never became a gate');

    // ── ARM C: a seat with no `component:` is skipped, loudly, not crashed on ──
    const orphan = path.join(goalDir, 'seats', 'orphan');
    fs.mkdirSync(orphan, { recursive: true });
    fs.writeFileSync(path.join(orphan, 'seat.md'), '---\nseat: orphan\nharness: bash\nmodel: test-sleep\n---\n');
    const j2 = [];
    refreshSeatDescriptor(orphan, (level, message, extra) => j2.push({ level, message, extra }));
    if (j2.length !== 1 || !/no catalog root/.test(j2[0].extra.reason)) {
      throw new Error(`ARM C FAILED — want one no-catalog-root skip, got ${JSON.stringify(j2)}`);
    }
    lines.push('ok    ARM C: a goal-local seat (no `component:`) is skipped by name, never guessed at a module and never crashed on');

    lines.push('result: refresh-before-launch is FIRST and it is NOT a gate (D37)');
  } finally {
    teardown(ctx);
  }
});

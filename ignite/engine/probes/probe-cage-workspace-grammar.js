#!/usr/bin/env node
'use strict';

// probe-cage-workspace-grammar — DOES THE ADMISSION GATE SPEAK THE WORKSPACE GRAMMAR?
//
// D2 (2026-08-19). The measured defect this holds closed (G-owner-console-0818-2030): a seat
// whose `## Outputs` declared workspace-relative mirror paths (`.rbtv/mirror/…`) was refused
// `producer-cannot-write` quoting the GOAL ro-bind — the token was resolved goal-relative, and
// the gate composed from `goal-writes` only, so no `rw-paths:` declaration could ever flip the
// verdict: a permanent, misdiagnosed refusal loop, journal-only. Three arms (a former second arm,
// admitting on a `coordination/permission-edits.csv` row, was DELETED with the grant store it
// exercised — [T2-R12, T1-R9], 2026-08-24):
//
//   1. ADMIT on the `rw-paths:` grant — the frontmatter class the spawner composes.
//   3. REFUSE with `no-workspace-grant` (naming the grant class, never the goal bind) when
//      it is absent.
//   4. The GOAL grammar follows D3 (2026-08-19): a `goal-writes`-covered token still admits;
//      an ordinary in-goal token now also admits (the whole goal folder is RW). A wall-control
//      surface (`seat.md`) still refuses `producer-cannot-write` — those ro-binds are the fence
//      holding its posts, not the retired anti-forgery rule.
//
// Plus the refusal->bus wire: `seeding.js#surfaceCageRefusal` -> `coord.py surface-refusal`
// lands EXACTLY ONE row per (seat, reason) on the fixture goal's messages.md, however many
// seed passes repeat it.
//
// The cage is composed over the LIVE profile-resolved SeatBinds template (the same read the
// seeding pass performs) — so a template edit that drops the `bind:{grant:rwPath}` line, or a
// gate edit that stops consuming the shared resolvers, reddens here.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const HERE = __dirname;
const OUT_PATH = path.join(HERE, 'probe-cage-workspace-grammar.out');
const { admitDeclaredOutputs } = require('../cage-admission');
const { surfaceCageRefusal } = require('../seeding');
const { loadConfig } = require('../../server/spawn/config');
const { resolveRwPathGrants } = require('../../server/spawn/seat-grants');
const { contains } = require('../../server/spawn/cage');

const start = Date.now();
const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

const SEAT = 'mirror-smith';

// The live template, exactly as the seeding pass resolves it: any launch spec that cages.
function liveSeatBinds() {
  const config = loadConfig(path.join(HERE, '..', '..', 'config', 'spawn-profiles.yaml'));
  for (const spec of Object.values(config.launchSpecs || {})) {
    const binds = spec && spec.sandbox && spec.sandbox.SeatBinds;
    if (Array.isArray(binds) && binds.length) return binds;
  }
  throw new Error('no launch spec with sandbox.SeatBinds — nothing cages, nothing to probe');
}

// A scratch WORKSPACE (never under the real .rbtv/goals — the live daemon scans that tree) with
// a mirror subtree and one fixture goal holding one seat.
function fixture({ rwPaths, outputs }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-cage-ws-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'fixture-goal');
  const seatDir = path.join(goalDir, 'seats', SEAT);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(ws, '.rbtv', 'mirror', 'communication'), { recursive: true });
  const fm = ['---', `seat: ${SEAT}`];
  if (rwPaths) fm.push('rw-paths:', '- .rbtv/mirror');
  fm.push('goal-writes:', `- coordination/${SEAT}-report.md`, '---');
  const body = ['<io-spec>', '## Outputs',
    ...outputs.map((t) => `- \`${t}\``), '</io-spec>', ''].join('\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), fm.join('\n') + '\n' + body);
  return { root, ws, goalDir, seatDir };
}

const MIRROR_TOKEN = '.rbtv/mirror/communication/module.md';

function admit(f, seatBinds) {
  return admitDeclaredOutputs({
    seatBinds, goalFolder: f.goalDir, seat: SEAT, successorReads: 'no', workspaceRoot: f.ws,
  });
}

function main() {
  const seatBinds = liveSeatBinds();
  const roots = [];
  const make = (opts) => { const f = fixture(opts); roots.push(f.root); return f; };
  try {
    // 1 — the frontmatter grant class admits, and the shared resolver composes the same grant.
    const f1 = make({ rwPaths: true, outputs: [MIRROR_TOKEN] });
    check('arm 1: mirror token ADMITTED on the seat\'s own `rw-paths:` grant',
      admit(f1, seatBinds) === null, `refused: ${admit(f1, seatBinds)}`);
    const g1 = resolveRwPathGrants({ workspaceRoot: f1.ws, goalDir: f1.goalDir, seatDir: f1.seatDir, seat: SEAT }, () => {});
    check('arm 1 parity: the SPAWNER\'s resolver composes a writable bind containing the admitted path',
      g1.some((g) => contains(g.rwPath, path.resolve(f1.ws, MIRROR_TOKEN))), JSON.stringify(g1));

    // 3 — no grant, no admission — and the refusal must name the WORKSPACE grant class, never
    // the goal ro-bind (that misdiagnosis is the measured defect).
    const f3 = make({ rwPaths: false, outputs: [MIRROR_TOKEN] });
    const r3 = admit(f3, seatBinds) || '';
    check('arm 3: mirror token REFUSED with `no-workspace-grant` when the grant class is absent',
      r3.includes('no-workspace-grant'), r3.slice(0, 300) || 'admitted');
    check('arm 3: the refusal names the missing grant class (`rw-paths:`)',
      r3.includes('rw-paths'), r3.slice(0, 300));
    check('arm 3: the refusal is NOT the misdiagnosed `producer-cannot-write` quoting the goal bind',
      !r3.includes('producer-cannot-write'), r3.slice(0, 300));

    // 4 — the goal grammar follows D3: the whole goal folder is RW. The former
    // `producer-cannot-write` on an ordinary in-goal path was the cage's anti-forgery /
    // narrow-opening rule; D3 retired it. Wall-control surfaces still refuse.
    const f4 = make({ rwPaths: true, outputs: [`coordination/${SEAT}-report.md`] });
    check('arm 4a: a `goal-writes`-covered goal-relative token still ADMITS',
      admit(f4, seatBinds) === null, `refused: ${admit(f4, seatBinds)}`);
    const f5 = make({ rwPaths: false, outputs: ['outputs/product.md'] });
    const r5 = admit(f5, seatBinds);
    check('arm 4b: an ordinary in-goal token now ADMITS (D3: the goal folder is RW; never misrouted to the workspace lane)',
      r5 === null, r5 ? r5.slice(0, 300) : 'admitted');
    const f5b = make({ rwPaths: false, outputs: [`seats/${SEAT}/seat.md`] });
    const r5b = admit(f5b, seatBinds) || '';
    check('arm 4c: a wall-control surface (`seat.md`) still refuses `producer-cannot-write` (D3: the fence holding its posts)',
      r5b.includes('producer-cannot-write') && !r5b.includes('no-workspace-grant'), r5b.slice(0, 300) || 'admitted');

    // 5 — the refusal->bus wire: once per (seat, reason), however many passes repeat it.
    const f6 = make({ rwPaths: false, outputs: [MIRROR_TOKEN] });
    const reason = admit(f6, seatBinds);
    surfaceCageRefusal(f6.goalDir, SEAT, reason, null);
    surfaceCageRefusal(f6.goalDir, SEAT, reason, null);
    const bus = fs.readFileSync(path.join(f6.goalDir, 'coordination', 'messages.md'), 'utf8');
    const rows = bus.split('\n').filter((l) => l.includes(`seed-refusal: ${SEAT}`)).length;
    check('arm 5: two seed passes land EXACTLY ONE `seed-refusal` row on the fixture goal\'s bus',
      rows === 1, `${rows} marker rows`);
    check('arm 5: the bus row carries the verbatim refusal',
      bus.includes('no-workspace-grant'), bus.slice(0, 300));
  } finally {
    for (const r of roots) fs.rmSync(r, { recursive: true, force: true });
  }
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}
const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the admission gate admits workspace-grammar outputs on the spawner\'s `rw-paths` '
    + 'grant (the shared resolver, so the two sides agree by construction), refuses grantless ones '
    + 'naming the missing grant, admits ordinary in-goal tokens (D3: goal folder is RW), still '
    + 'refuses a wall-control surface (`seat.md`), and lands each refusal on the goal bus exactly once.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);

#!/usr/bin/env node
'use strict';

// probe-seed-gates — THE TWO SEED-PASS DOOR REFUSALS (seed-gates, 2026-08-19).
//
// D5 · LANE REACH. The measured defect (G-plan-3-plan-dod-judge-0818-2130,
// G-canvas-live-prober-0818-1955, G-leader-0818-1936): a goal burned two waves and three seats
// because its DoD judge kept landing in a cage where its probe lane could not run
// (`stools workspaces` → exit 127). The requirement was written in four PROSE surfaces and read
// by nothing that admits a launch. It now lives machine-readable in the seat's io-spec
// (`## Requires-reach`) and `cage-admission.js#admitLaneReach` refuses at the pre-enqueue door:
//   1. `cli stools` with NO `exposed-clis:` declaration → refused `no-cli-grant`, by name.
//   2. the same seat WITH the declaration → admitted.
//   4. a malformed entry → refused (an unreadable requirement is never a met one).
//   5. the refusal lands EXACTLY ONCE on the goal bus through the landed D2 surfacing wire.
//
// (A former arm 3, admitting a `path` entry ONLY on a `coordination/permission-edits.csv` row,
// was DELETED with the grant store it exercised — [T2-R12, T1-R9], 2026-08-24.)
//
// D9 · GOAL-LIVE BEFORE GRANT SPEND. The measured defect (G-leader-0818-1830,
// meet-transcript-summarizer): two relaunch grants burned with no session row — `seedGoal`'s
// ready-row loop spent them while the goal-live refusal (`E_GOAL_NOT_LIVE`) fired later, at the
// spawn door. `seedGoal` now reads the SAME lease at the SAME room threshold FIRST:
//   6. goal NOT live → nothing enqueued, the
//      refusal surfaced on the goal bus.
//   7. goal LIVE → the seat enqueues, and no grant file exists on either pass (D12).
//
// The lease is injected as `readLease` — the real `deriveLease` over a fixture tmux reading
// (real measurables, never a verdict), `checkGoalExecuting`'s own injection pattern.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-seed-gates.out');
const { admitLaneReach } = require('../../envelope/cage-admission');
const { surfaceCageRefusal } = require('../seeding');
const { createEngine } = require('../../runtime/engine');
const { loadConfig } = require('../spawn/config');
const { deriveLease } = require('../../runtime/lease/lease');

const start = Date.now();
const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

const SEAT = 'dod-judge';

// The live template, exactly as the seeding pass resolves it: any launch spec that cages.
function liveSeatBinds() {
  const config = loadConfig(path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml'));
  for (const spec of Object.values(config.launchSpecs || {})) {
    const binds = spec && spec.sandbox && spec.sandbox.SeatBinds;
    if (Array.isArray(binds) && binds.length) return binds;
  }
  throw new Error('no launch spec with sandbox.SeatBinds — nothing cages, nothing to probe');
}

// A scratch WORKSPACE (never under the real .rbtv/goals — the live daemon scans that tree) with
// one fixture goal, one seat, and a workspace tool subtree a `path` reach can point at.
function reachFixture({ exposedClis, reach }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'fixture-goal');
  const seatDir = path.join(goalDir, 'seats', SEAT);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(ws, 'tools', 'stools', '.git'), { recursive: true });
  const fm = ['---', `seat: ${SEAT}`];
  if (exposedClis) fm.push('exposed-clis:', `- stools ${path.join(ws, 'tools', 'stools', 'stools.py')}`);
  fm.push('goal-writes:', `- coordination/${SEAT}-verdict.md`, '---');
  const body = ['<io-spec>', '## Outputs', `- \`coordination/${SEAT}-verdict.md\``,
    '## Requires-reach', ...reach, '</io-spec>', ''].join('\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), fm.join('\n') + '\n' + body);
  return { root, ws, goalDir, seatDir };
}

function laneReachArms(seatBinds, roots) {
  const make = (opts) => { const f = reachFixture(opts); roots.push(f.root); return f; };
  const admit = (f) => admitLaneReach({ seatBinds, goalFolder: f.goalDir, seat: SEAT, workspaceRoot: f.ws });

  // 1 — the D5 red: the lane requirement with no grant is REFUSED at the door, by name.
  const f1 = make({ exposedClis: false, reach: ['- cli `stools`'] });
  const r1 = admit(f1) || '';
  check('arm 1: `cli stools` with NO `exposed-clis:` declaration is REFUSED `no-cli-grant`',
    r1.includes('no-cli-grant') && r1.includes('stools'), r1.slice(0, 300) || 'admitted');

  // 2 — the same requirement WITH the declaration admits.
  const f2 = make({ exposedClis: true, reach: ['- cli `stools`'] });
  check('arm 2: the SAME seat WITH the `exposed-clis:` declaration is ADMITTED',
    admit(f2) === null, `refused: ${admit(f2)}`);

  // 3 — the leader's audited widen lane (`coordination/permission-edits.csv`) is DELETED
  // ([T2-R12, T1-R9], 2026-08-24); a `path` reach with no grant at all is refused, naming the
  // one remaining grant lane.
  const f3 = make({ exposedClis: false, reach: ['- path `tools/stools/.git`'] });
  const r3 = admit(f3) || '';
  check('arm 3: `path tools/stools/.git` with NO grant is REFUSED `lane-cannot-reach`',
    r3.includes('lane-cannot-reach'), r3.slice(0, 300) || 'admitted');
  check('arm 3: the refusal names the grant lane (`rw-paths:`)',
    r3.includes('rw-paths'), r3.slice(0, 300));

  // 4 — fail closed: an unparseable entry refuses rather than passing as "no requirement".
  const f4 = make({ exposedClis: true, reach: ['- clii `stools`'] });
  const r4 = admit(f4) || '';
  check('arm 4: a MALFORMED requires-reach entry REFUSES (an unreadable requirement is never met)',
    r4.includes('undecided'), r4.slice(0, 300) || 'admitted');

  // 5 — the refusal→bus wire (DoD clause 2): once per (seat, reason), however many passes.
  surfaceCageRefusal(f1.goalDir, SEAT, r1, null);
  surfaceCageRefusal(f1.goalDir, SEAT, r1, null);
  const bus = fs.readFileSync(path.join(f1.goalDir, 'coordination', 'messages.md'), 'utf8');
  const rows = bus.split('\n').filter((l) => l.includes(`seed-refusal: ${SEAT}`)).length;
  check('arm 5: two seed passes land EXACTLY ONE `seed-refusal` row on the fixture goal bus',
    rows === 1, `${rows} marker rows`);
  check('arm 5: the bus row carries the verbatim `no-cli-grant` refusal',
    bus.includes('no-cli-grant'), bus.slice(0, 400));
  say(`arm 5 bus row (verbatim head): ${bus.split('\n').slice(0, 12).join(' | ').slice(0, 500)}`);
}

// ── D9 · the goal-live fixture: a real engine over a fixture workspace, an armed grant file ────
function goalLiveArms() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seed-gates-live-'));
  const ws = path.join(tmp, 'ws');
  const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
  const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml'), 'utf8'));
  cfg.spawn = { ...(cfg.spawn || {}), data_root: path.join(tmp, 'data'), carrier: 'setsid' };
  cfg.default_workdir_root = path.join(tmp, 'work');
  fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
  cfg['launch-specs'] = { bash: { 'probe-live': {
    exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-live'], prompt: 'stdin' },
    headed: { tui: { argv: ['true'] } },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: '.rbtv/goals',
    caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
  } } };
  const configPath = path.join(tmp, 'spawn-profiles.yaml');
  fs.writeFileSync(configPath, yaml.dump(cfg));

  const goal = 'live-goal';
  const goalFolder = path.join(ws, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(goalFolder, 'seats', 'alpha'), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-g,alpha,\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
    '---\nseat: alpha\nharness: bash\nmodel: probe-live\n---\n\nbody\n');
  // ⚠ THE STORE SITS UNDER THE FIXTURE WORKSPACE'S OWN `.rbtv/` — that is what threads the
  // FIXTURE workspace root into the D9 check (resolveWorkspaceRoot walks the db path), so the
  // arm never leans on RBTV_IGNITE_WORKSPACE_ROOT pointing anywhere.
  const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  // The real deriveLease over injected tmux readings — measurables, never a verdict.
  const deadLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: '', panes: '' }) });
  const liveLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: a.goal, panes: '' }) });

  const pass = (readLease) => {
    const logs = [];
    const engine = createEngine({ dbPath, spawnConfigPath: configPath, userManager: false, logger: (m) => logs.push(m) });
    try { return { pickup: engine.seedGoal({ goalFolder, goal, readLease }), logs }; }
    finally { engine.close(); }
  };

  try {
    const dead = pass(deadLease);
    check('arm 6: goal NOT live → NOTHING enqueued and the pass says why (`goalNotLive`)',
      dead.pickup.enqueued.length === 0 && Boolean(dead.pickup.goalNotLive),
      JSON.stringify({ enqueued: dead.pickup.enqueued, goalNotLive: dead.pickup.goalNotLive || null }).slice(0, 300));
    const bus = fs.readFileSync(path.join(goalFolder, 'coordination', 'messages.md'), 'utf8');
    check('arm 6: the refusal is SURFACED on the goal bus (one `seed-refusal` row keyed by the goal)',
      bus.split('\n').filter((l) => l.includes(`seed-refusal: ${goal}`)).length === 1
      && bus.includes('NO live room'), bus.slice(0, 300));
    say(`arm 6 log line: ${JSON.stringify((dead.logs.find((l) => /not LIVE/.test(l.message)) || {}).message || null)}`);

    const live = pass(liveLease);
    // D12: no grant file exists to spend. The discriminator is the LEASE alone — the same pass
    // that refused above enqueues here, and the only thing that changed is the tmux reading.
    check('arm 7: goal LIVE → the seat ENQUEUES',
      live.pickup.enqueued.includes('alpha') && !live.pickup.goalNotLive,
      JSON.stringify({ enqueued: live.pickup.enqueued, goalNotLive: live.pickup.goalNotLive || null }));
    check('arm 7: and NO grant file was created by either pass — the stores are deleted (D12)',
      fs.readdirSync(path.join(goalFolder, 'coordination')).filter((f) => /grant/.test(f)).length === 0,
      JSON.stringify(fs.readdirSync(path.join(goalFolder, 'coordination'))));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function main() {
  const roots = [];
  try {
    laneReachArms(liveSeatBinds(), roots);
  } finally {
    for (const r of roots) fs.rmSync(r, { recursive: true, force: true });
  }
  goalLiveArms();
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
  : 'RESULT: PASS — the pre-enqueue door refuses a lane whose reach the composed cage cannot '
    + 'satisfy (cli via exposed-clis, path via the `rw-paths` grant lane, fail-closed on '
    + 'malformed entries, surfaced once on the bus), and seedGoal refuses a not-live goal BEFORE '
    + 'any relaunch grant is spent while a live one seeds and spends normally.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);

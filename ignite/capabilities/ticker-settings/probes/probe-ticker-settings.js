'use strict';

// probe-ticker-settings — task 7.66's READ + WRITE half, against THROWAWAY workspaces under
// os.tmpdir(). It never reads and never writes the live `.rbtv/`.
//
// ⚠ THE BAR IT IS BUILT AGAINST (`p-green-harness-over-a-broken-mechanism`): a probe that writes a
// settings file and reads it back exercises the FILE, not the mechanism. So every check below
// asserts a property that can be WRONG — a bound that refuses, a `from` that is computed rather
// than assumed, a key the daemon must reject, a seed shape that exists in the wild. The
// discriminating power is recorded in `../mutations.md`: each mutation named there turns specific
// checks RED, measured, not asserted.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The exit code is
// the truth; the footer is a hint, and the tally asserts its OWN completeness (`G-121`).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-ticker-settings.out');
fs.writeFileSync(outPath, '');

const S = require('../../../server/settings.js');
const TOOL = path.resolve(__dirname, '..', 'tool', 'rbtv-ignite-ticker');

// The number of checks this probe intends to run. A run that ends with a different tally is
// INCOMPLETE, not green — a truncated run reads greener than a complete one (`G-121`).
// (Set to the MEASURED tally of a complete run, not an estimate — my first guess was 31 and the
// assertion turned the run red at 39, which is the assertion doing its job on its own author.)
const EXPECTED_CHECKS = 43;

const checks = [];
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass: !!pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? `  [${detail}]` : ''}`);
}

const MACHINE = S.thisMachine();

function mkWorkspace(seed) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-ticker-settings-'));
  const mod = path.join(root, '.rbtv', 'modules', 'ignite');
  fs.mkdirSync(mod, { recursive: true });
  if (seed !== undefined) fs.writeFileSync(path.join(mod, 'settings.json'), seed);
  return root;
}

function runTool(root, args, env = {}) {
  try {
    const stdout = execFileSync(TOOL, args, {
      env: { ...process.env, RBTV_IGNITE_WORKSPACE_ROOT: root, ...env },
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    });
    return { status: 0, stdout, stderr: '' };
  } catch (err) {
    return { status: err.status === undefined ? -1 : err.status, stdout: err.stdout || '', stderr: err.stderr || '' };
  }
}

async function main() {
  // ── 1. Both live seeds read, and so does no file at all ─────────────────────────────────────
  // MEASURED on the live VPS: the daemon seeds `{}` (server/index.js) and the installer seeds
  // `{"machines": {}}` (rbtv-install), and whichever ran first is what is on the box. A reader
  // that handled only one of them would work everywhere it was tested and fail on the machine
  // this task was built on.
  for (const [label, seed] of [
    ['daemon seed {}', '{}'],
    ['installer seed {"machines":{}}', '{"machines": {}}\n'],
    ['empty file', ''],
    ['no file at all', undefined],
  ]) {
    const root = mkWorkspace(seed);
    let ok = false; let detail = '';
    try {
      const eff = S.effectiveBlock(root, 'ticker');
      ok = eff.tick_interval_ms === 10000 && eff.tick_interval_floor_ms === 5000 && eff.tick_interval_ceiling_ms === 60000;
      detail = `tick=${eff.tick_interval_ms}`;
    } catch (err) { detail = err.message; }
    check(`reads the ${label} and falls back to the defaults`, ok, detail);
    fs.rmSync(root, { recursive: true, force: true });
  }

  // Corrupt JSON must FAIL LOUD, never be treated as empty: silently running at the default while
  // the file on disk says otherwise is the silent-no-op class this runtime keeps paying for.
  {
    const root = mkWorkspace('{ not json');
    let threw = false;
    try { S.readSettings(root); } catch { threw = true; }
    check('a corrupt settings.json THROWS rather than reading as empty', threw);
    fs.rmSync(root, { recursive: true, force: true });
  }

  // ── 2. The write, machine-keyed, and the history line ───────────────────────────────────────
  {
    const root = mkWorkspace('{}');
    const res = S.setValue(root, { block: 'ticker', key: 'tick_interval_ms', value: 15000, by: 'probe' });
    const written = JSON.parse(fs.readFileSync(S.settingsPaths(root).settingsPath, 'utf8'));

    check('the value lands at machines.<hostname>.ticker.tick_interval_ms',
      written.machines[MACHINE].ticker.tick_interval_ms === 15000,
      JSON.stringify(written.machines[MACHINE] || null));
    check('it is NOT written flat at the top level',
      written.tick_interval_ms === undefined && written.ticker === undefined);
    check('the read-back effective value is the written one',
      S.effectiveBlock(root, 'ticker').tick_interval_ms === 15000);
    check('an UNSET key keeps its default beside a set one',
      S.effectiveBlock(root, 'ticker').tick_interval_floor_ms === 5000);

    // Another machine's block must survive untouched — the file travels by git, so a write here
    // that dropped or rewrote another box's entry would corrupt a machine nobody was looking at.
    const s2 = JSON.parse(fs.readFileSync(S.settingsPaths(root).settingsPath, 'utf8'));
    s2.machines['some-other-box'] = { ticker: { tick_interval_ms: 42000 } };
    fs.writeFileSync(S.settingsPaths(root).settingsPath, JSON.stringify(s2, null, 2));
    S.setValue(root, { block: 'ticker', key: 'tick_interval_ms', value: 20000, by: 'probe' });
    const s3 = JSON.parse(fs.readFileSync(S.settingsPaths(root).settingsPath, 'utf8'));
    check('a write leaves ANOTHER machine\'s block byte-intact',
      s3.machines['some-other-box'].ticker.tick_interval_ms === 42000);
    check('another machine\'s value NEVER leaks into this machine\'s effective read',
      S.effectiveBlock(root, 'ticker').tick_interval_ms === 20000);

    // ── The history lines ──
    const lines = fs.readFileSync(S.settingsPaths(root).historyPath, 'utf8')
      .split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
    check('one appended line per change, and only one', lines.length === 2, `lines=${lines.length}`);
    check('the line carries exactly the six adopted keys {ts,machine,key,from,to,by}',
      JSON.stringify(Object.keys(lines[0]).sort()) === JSON.stringify(['by', 'from', 'key', 'machine', 'to', 'ts']),
      Object.keys(lines[0]).join(','));
    check('key is the path WITHIN the machine block, not repeating the hostname',
      lines[0].key === 'ticker.tick_interval_ms', lines[0].key);
    check('machine names this machine', lines[0].machine === MACHINE);
    check('ts parses as a date', !Number.isNaN(Date.parse(lines[0].ts)), lines[0].ts);

    // ⚠ THE CHECK THE LEADER'S RULING (#522) EXISTS FOR. The installer hardcodes `"from": None`
    // and never reads prior state, so all three of its live lines read null -> 1 for one key: a
    // history whose `from` is always null cannot reconstruct ONE transition, which is the whole
    // purpose of carrying it. This module computes `from` by READING. Adopting the field set
    // while refusing the write semantics is what these two checks pin down.
    check('first change: from is null (nothing was stored)', lines[0].from === null, JSON.stringify(lines[0].from));
    check('⚠ second change: from is the PRIOR STORED VALUE, not null',
      lines[1].from === 15000, JSON.stringify(lines[1].from));
    check('to is the new value', lines[0].to === 15000 && lines[1].to === 20000);

    // A no-op write must not manufacture a history entry: an audit trail that records changes
    // that did not happen is the defect above, in the other direction.
    const noop = S.setValue(root, { block: 'ticker', key: 'tick_interval_ms', value: 20000, by: 'probe' });
    const after = fs.readFileSync(S.settingsPaths(root).historyPath, 'utf8').split('\n').filter((l) => l.trim());
    check('setting the SAME value writes no history line and reports changed=false',
      noop.changed === false && after.length === 2, `lines=${after.length}`);

    // Append-only, never rewritten (CMP-1): pre-existing lines survive byte-identical.
    check('earlier history lines are byte-intact after later writes',
      fs.readFileSync(S.settingsPaths(root).historyPath, 'utf8').startsWith(JSON.stringify(lines[0]) + '\n'));
    fs.rmSync(root, { recursive: true, force: true });
  }

  // ── 3. Enforcement point ONE: the surface refuses, and writes NOTHING ────────────────────────
  {
    const root = mkWorkspace('{}');
    const before = fs.readFileSync(S.settingsPaths(root).settingsPath, 'utf8');
    for (const [label, dur] of [['below the floor', '1s'], ['above the ceiling', '120s']]) {
      const r = runTool(root, ['set-interval', dur]);
      check(`the surface REFUSES ${dur} (${label}) with a typed exit`, r.status === 3, `exit=${r.status}`);
    }
    check('a refused edit leaves settings.json BYTE-IDENTICAL',
      fs.readFileSync(S.settingsPaths(root).settingsPath, 'utf8') === before);
    check('a refused edit appends NO history line',
      !fs.existsSync(S.settingsPaths(root).historyPath)
      || fs.readFileSync(S.settingsPaths(root).historyPath, 'utf8').trim() === '');

    // Both bounds are CONFIGURABLE DEFAULTS (owner, 2026-07-26), not limits — so lowering the
    // floor must make a previously-refused cadence legal. A bound that cannot be moved would be a
    // constant wearing a config key's name.
    S.setValue(root, { block: 'ticker', key: 'tick_interval_floor_ms', value: 1000, by: 'probe' });
    const r2 = runTool(root, ['set-interval', '1s']);
    check('with the floor lowered to 1000ms the SAME 1s edit is ACCEPTED', r2.status === 0, `exit=${r2.status}`);
    check('...and it actually landed', S.effectiveBlock(root, 'ticker').tick_interval_ms === 1000);
    fs.rmSync(root, { recursive: true, force: true });
  }

  // A floor above its ceiling admits no cadence at all and must be named as such, rather than
  // surfacing as a baffling refusal of every value.
  {
    const root = mkWorkspace(JSON.stringify({
      machines: { [MACHINE]: { ticker: { tick_interval_floor_ms: 60000, tick_interval_ceiling_ms: 5000 } } },
    }));
    const problems = S.validateMachine(root);
    check('an inverted floor/ceiling is reported as its own named problem',
      problems.some((p) => p.includes('no cadence could satisfy both')), problems.join(' | '));
    fs.rmSync(root, { recursive: true, force: true });
  }

  // ── 4. Enforcement point TWO: what the daemon refuses at boot ────────────────────────────────
  // These are the values a hand-edit reaches by going around the surface. `validateMachine` is the
  // exact function `server/index.js` throws on, so this exercises the boot refusal itself.
  {
    for (const [label, block, expectHit] of [
      ['a cadence below the floor', { tick_interval_ms: 100 }, 'below the floor'],
      ['a cadence above the ceiling', { tick_interval_ms: 999999 }, 'above the ceiling'],
      ['a non-integer cadence', { tick_interval_ms: '15s' }, 'must be an integer'],
      ['a MISSPELLED key', { tick_interval: 15000 }, 'is not a known setting'],
    ]) {
      const root = mkWorkspace(JSON.stringify({ machines: { [MACHINE]: { ticker: block } } }));
      const problems = S.validateMachine(root);
      check(`boot REFUSES ${label}`, problems.some((p) => p.includes(expectHit)), problems.join(' | ') || 'no problems');
      fs.rmSync(root, { recursive: true, force: true });
    }

    // A block this daemon does not know is IGNORED, not refused — the file travels by git and a
    // newer machine's block must not stop an older daemon booting. The asymmetry with the
    // misspelled-key refusal above is deliberate and is the schema's rule.
    const root = mkWorkspace(JSON.stringify({ machines: { [MACHINE]: { some_future_block: { x: 1 } } } }));
    check('boot IGNORES an unknown BLOCK (git-travelling file, forward compatibility)',
      S.validateMachine(root).length === 0);
    fs.rmSync(root, { recursive: true, force: true });

    // Another machine's broken block must never stop THIS machine booting.
    const root2 = mkWorkspace(JSON.stringify({ machines: { 'some-other-box': { ticker: { tick_interval_ms: 1 } } } }));
    check('boot IGNORES another machine\'s out-of-bound value', S.validateMachine(root2).length === 0);
    fs.rmSync(root2, { recursive: true, force: true });
  }

  // ── 5. The duration grammar ─────────────────────────────────────────────────────────────────
  {
    check('15s parses to 15000ms', S.parseDurationMs('15s') === 15000);
    check('15000ms parses to 15000ms', S.parseDurationMs('15000ms') === 15000);
    let refused = false;
    try { S.parseDurationMs('15'); } catch { refused = true; }
    // A bare number is a 1000x ambiguity — 15ms or 15s — resolved silently in whichever direction
    // the implementation happened to pick. Refusing is the only reading that cannot be wrong.
    check('a BARE number is REFUSED rather than guessed', refused);
  }

  // ── 5b. `inspect daemon`'s two cadence fields, through the REAL handler ──────────────────────
  //
  // ⚠ THIS SECTION EXISTS BECAUSE THE CODE HAD NEVER RUN. The closure was wired into
  // `createInternalApi` and the field pair computed in `handleInspectDaemon`, and every check
  // elsewhere in this task exercised the settings MODULE instead — the two halves proven, the
  // composition never taken (`G-124`'s shape). So this drives the real dispatch envelope.
  //
  // The case that matters most is the third: an unreadable settings file must report `null`, NEVER
  // `false`. `false` means "nothing pending" and would be a confident wrong answer.
  {
    const crypto = require('node:crypto');
    const { createInternalApi } = require('../../../server/internal-api/dispatch.js');
    const SECRET = 'x'.repeat(64);
    const store = {
      getLastTick: () => ({ tick: 7 }), listExecutionsByStatus: () => [],
      listQueue: () => [], listWarnings: () => [],
    };
    const ask = async (readFn, running) => {
      const api = createInternalApi({
        heartStore: store, spawnManager: {}, secret: SECRET,
        daemonConfig: { tick_interval_ms: running }, readConfiguredTickIntervalMs: readFn,
      });
      const r = await api.dispatch({
        v: 1, id: crypto.randomUUID(), ts: new Date().toISOString(), auth: SECRET,
        sender: { id: 'probe-agent', kind: 'owner', via: 'cli' },
        intent: 'inspect', payload: { target: 'daemon' },
      });
      return r.ok ? r.result.config : null;
    };
    const cases = [
      ['nothing pending: configured == running', () => 10000, 10000, 10000, false],
      ['an edit written but not restarted is reported PENDING', () => 15000, 10000, 15000, true],
      ['⚠ an unreadable settings file reports null, NEVER false', () => { throw new Error('boom'); }, 10000, null, null],
      ['no reader wired reports null, not a fabricated verdict', null, 10000, null, null],
    ];
    // Sequential and awaited: a forEach with an async body would let the tally finish before the
    // checks landed, which is the truncated-run hazard this probe asserts against.
    for (const [label, fn, running, expConf, expPend] of cases) {
      // eslint-disable-next-line no-await-in-loop
      const c = await ask(fn, running);
      check(label, c && c.tick_interval_ms_configured === expConf && c.tick_interval_pending_restart === expPend,
        c ? `configured=${c.tick_interval_ms_configured}, pending=${c.tick_interval_pending_restart}` : 'dispatch failed');
    }
  }

  // ── 6. The surface reports the pending state ────────────────────────────────────────────────
  {
    const root = mkWorkspace('{}');
    const r = runTool(root, ['set-interval', '15s']);
    check('an accepted edit says it is NOT in effect until a restart',
      r.stdout.includes('NOT IN EFFECT YET'), r.stdout.split('\n').slice(-6).join(' / '));
    check('...and prints the tick-denominated ladder the new cadence implies',
      r.stdout.includes('stall halt') && r.stdout.includes('360s'), 'stall halt @24 ticks x 15s = 360s');
    fs.rmSync(root, { recursive: true, force: true });
  }
}

// The report is emitted INSIDE the async completion, never beside it: a top-level `main()` whose
// promise nobody awaits would print the tally before the checks ran — a green report over an
// unfinished run, which is this file's own completeness bar violated by its own harness.
async function run() {
  try {
    await main();
  } catch (err) {
    out('ERROR:', err.message, err.stack);
    checks.push({ name: 'unhandled error', pass: false });
  }
  report();
}

function report() {
const failed = checks.filter((c) => !c.pass);
// The completeness assertion, separate from the pass/fail tally: a run that dies half way through
// would otherwise print only PASS lines and exit 0.
const complete = checks.length === EXPECTED_CHECKS;
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`COMPLETE: ${complete} (ran ${checks.length}, expected ${EXPECTED_CHECKS})`);
if (!complete) out('INCOMPLETE RUN — a short tally is a FAILURE however many checks passed (G-121)');
out(`TICKER_SETTINGS_OK: ${failed.length === 0 && complete}`);
out(`EXIT: ${failed.length === 0 && complete ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = (failed.length === 0 && complete) ? 0 : 1;
}

run();

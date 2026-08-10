'use strict';

// probe-goal-containment — D10 (task 7.529). `goalDirOf` joins a DAEMON-SUPPLIED goal id into a
// path, so a `..`, an absolute path or a symlinked component would hand every caller below a
// "goal folder" outside `<ws>/.rbtv/goals/` — one it may read, materialize into, or bind into a
// cage. This probe pins the typed refusal, the hostile-input suite, the live-set control, and
// BOTH call sites (a unit test over the function alone does not cover the ticker's use of it).
//
// Nothing live is written: the hostile arms run against a scratch workspace under the OS temp
// dir, and the control arm only READS the live goals root to re-resolve names.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { goalDirOf, GoalPathError, resolveSeatHome } = require('../seat-folder');
const { channelEnsureDecision, SKIP, REASONS } = require('../../ticker/goal-channel-start');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-goal-containment.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// The live workspace, for the CONTROL arm only (read-only).
const LIVE_WS = process.env.RBTV_PROBE_WORKSPACE || path.resolve(__dirname, '..', '..', '..', '..', '..', '..', '..');
const BEFORE = process.env.RBTV_PROBE_BEFORE || '';

function refusalOf(goal, workspaceRoot) {
  try {
    return { threw: false, value: goalDirOf({ workspaceRoot, goal }) };
  } catch (err) {
    return { threw: true, err };
  }
}

function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── scratch workspace: a real goals root, plus a goal folder that is a SYMLINK out of it ──
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'p7529-'));
  const goalsRoot = path.join(ws, '.rbtv', 'goals');
  fs.mkdirSync(goalsRoot, { recursive: true });
  fs.mkdirSync(path.join(goalsRoot, 'legit-goal'));
  const outside = path.join(ws, 'OUTSIDE');
  fs.mkdirSync(outside);
  fs.symlinkSync(outside, path.join(goalsRoot, 'symlinked-escapee'));
  out(`scratch workspace: ${ws}`);

  // ── ARM 1 — the hostile-input suite. Every member refused, and NAMED. ──────────────────────
  const hostile = [
    ['dotdot-traversal', '..'],
    ['nested-traversal', '../../etc'],
    ['absolute-path', '/etc/passwd'],
    ['symlinked-component', 'symlinked-escapee'],
    ['empty-goal', ''],
    ['whitespace-goal', '   '],
    ['percent-encoded-traversal', '%2e%2e%2f%2e%2e'],
  ];
  for (const [label, goal] of hostile) {
    const r = refusalOf(goal, ws);
    check(`hostile ${label} is refused, typed and named`,
      r.threw && r.err instanceof GoalPathError && r.err.code === 'E_GOAL_PATH_REFUSED',
      r.threw ? r.err.message : `NO REFUSAL — returned ${JSON.stringify(r.value)}`);
  }

  // The symlink arm must be refused by the RESOLVED-REAL-PATH check, not by the name check: its
  // name is a clean segment. Asserted so a future string-only guard cannot pass this suite.
  const sym = refusalOf('symlinked-escapee', ws);
  check('the symlink arm is refused on the RESOLVED path, not on the input string',
    sym.threw && /resolves to .*OUTSIDE, outside the goals root/.test(sym.err.message),
    sym.threw ? sym.err.message : 'not refused');

  // ── ARM 2 — DISCRIMINATION: a legitimate goal in the same root still resolves. ─────────────
  const good = refusalOf('legit-goal', ws);
  check('a legitimate goal still resolves (the guard is not a blanket stop)',
    !good.threw && good.value === path.join(goalsRoot, 'legit-goal'),
    good.threw ? good.err.message : good.value);

  // ── ARM 3 — CONTROL: every goal that exists under the LIVE .rbtv/goals/ today resolves to a
  // BYTE-IDENTICAL path. `before` was captured from the pre-guard function at HEAD.
  if (BEFORE && fs.existsSync(BEFORE)) {
    const before = fs.readFileSync(BEFORE, 'utf8').trimEnd().split('\n');
    const liveRoot = path.join(LIVE_WS, '.rbtv', 'goals');
    const names = fs.readdirSync(liveRoot, { withFileTypes: true })
      .filter((e) => e.isDirectory()).map((e) => e.name).sort();
    const after = names.map((g) => `${g} -> ${goalDirOf({ workspaceRoot: LIVE_WS, goal: g })}`);
    const same = before.length === after.length && before.every((l, i) => l === after[i]);
    check(`CONTROL: all ${names.length} live goals resolve byte-identically after the guard`,
      same, same ? `${names.length} goals, diff empty` : `before=${JSON.stringify(before)} after=${JSON.stringify(after)}`);
    out('--- live-set resolution (after) ---');
    after.forEach((l) => out('    ' + l));
  } else {
    check('CONTROL: live-set before/after diff', false, `no before-capture at ${BEFORE}`);
  }

  // ── ARM 4 — BOTH CALL SITES, not just the function. ───────────────────────────────────────
  // (a) seat-folder.js's own use, inside resolveSeatHome.
  const rsh = resolveSeatHome({ workspaceRoot: ws, goal: '../../etc', seat: 'any-seat' });
  check('call site A (resolveSeatHome) refuses a hostile goal in its own {ok:false} shape',
    rsh && rsh.ok === false && /E_GOAL_PATH_REFUSED/.test(rsh.reason || ''),
    JSON.stringify(rsh));

  // (b) the ticker's use, through the module's public entry. It contains throws by design
  // (goal-channel-start.js: a throw would abandon the whole tick), so the refusal must arrive as
  // a NAMED skip rather than as an exception escaping into dispatch().
  const dec = channelEnsureDecision({
    job: { action_type: 'start-workflow', goal_name: '../../etc' },
    resolveRoot: () => ws,
  });
  check('call site B (ticker goal-channel-start) skips, naming the refusal, and never throws',
    dec && dec.action === SKIP && dec.reason.startsWith(REASONS.DECISION_ERROR)
      && /E_GOAL_PATH_REFUSED/.test(dec.reason),
    JSON.stringify(dec));

  // ...and the same call site still DECIDES normally for a clean goal (non-interactive here,
  // which is the ruled negative arm — the point is that it reaches the kind read at all).
  const decOk = channelEnsureDecision({
    job: { action_type: 'start-workflow', goal_name: 'legit-goal' },
    resolveRoot: () => ws,
  });
  check('call site B still decides normally for a clean goal',
    decOk && !String(decOk.reason || '').startsWith(REASONS.DECISION_ERROR),
    JSON.stringify(decOk));

  fs.rmSync(ws, { recursive: true, force: true });

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`GOAL_CONTAINMENT_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}

try {
  main();
} catch (err) {
  out('ERROR: ' + err.message, err.stack);
  out('EXIT: 1');
  process.exitCode = 1;
}

'use strict';

// probe-workdir-governance — task 7.562. A scheduled `fire-tool` row may not choose an arbitrary
// working directory.
//
// WHAT IT ASSERTS, in one line: `checkFireToolWorkdir` admits exactly the two roots every
// legitimate row has ever used — the configured `default_workdir_root` EXACTLY, and a path inside
// `.rbtv/goals/<goal>` — refuses every hostile shape with a typed reason that NAMES the sanctioned
// root, and is CALLED at both fire-tool doors.
//
// ⚠ WHY THE GREEN ARMS ARE NOT DECORATION. The failure mode of this row is an OUTAGE, not a hole:
// a containment rule that refuses the live self-heal or edge-runner rows disables the daemon's own
// recovery. G1/G2/G3 are the criterion, and each carries a mutation that turns it RED — G2 goes red
// the moment W1 is dropped from the root set, which is the "just reuse the workflow rule" mistake.
//
// ⚠ WHAT IT DOES NOT ASSERT: that a fire-tool exec is contained. It is not. cwd is not a security
// boundary and this rule is not a sandbox — see the header above `checkFireToolWorkdir`.
//
// Every red arm is proven non-vacuous by MUTATION: the guard is deleted from a scratch copy of
// `argv-template.js` and the arm is shown to flip to ACCEPTED. The pre-fix state (no guard on the
// fire-tool path at all) is arm M0.

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-workdir-governance.out');
const SRC = path.join(__dirname, '..', 'argv-template.js');
const TICKER_SRC = path.join(__dirname, '..', '..', 'ticker', 'ticker.js');
const STORE_SRC = path.join(__dirname, '..', 'heart-store.js');

const lines = [];
const say = (s) => lines.push(s);
let failures = 0;
function check(ok, label, detail = '') {
  say(`${ok ? 'PASS' : 'FAIL'} ${label}${detail ? '  — ' + detail : ''}`);
  if (!ok) failures += 1;
}

// The fixture's sanctioned root. A FIXTURE value, never the live one: the rule must be
// per-instance, and a probe that only passes on one box would hide a hardcoded path.
const ROOT = '/srv/fixture-ws';
const GOALDIR = `${ROOT}/.rbtv/goals/some-goal`;

// The hostile shapes. `pre` names which guard line the mutation arm deletes to prove the arm real.
const RED = [
  { id: 'R1', label: 'traversal', wd: `${ROOT}/.rbtv/goals/../../../../etc`, expect: '".." segment' },
  { id: 'R2', label: 'absolute path outside any sanctioned root', wd: '/home/henri/.ssh', expect: 'default_workdir_root' },
  { id: 'R4', label: 'control character (a newline aimed at the unit properties)', wd: `${GOALDIR}\nSuccessExitStatus=77`, expect: 'control character' },
  { id: 'R5', label: 'relative path', wd: 'goals/x', expect: 'absolute path' },
  // The exact-root ruling's own edge: a DESCENDANT of the sanctioned root is not sanctioned. The
  // workspace root holds `.rbtv/config/.env` and the source tree, so "anything under it" is no
  // containment at all (owner ruling `d-owner-board-clear-0809`).
  { id: 'R6', label: 'a descendant of the sanctioned root (holds the credentials file)', wd: `${ROOT}/.rbtv/config`, expect: 'default_workdir_root' },
];

// The legitimate shapes, each with the live row it stands for (live store, 2026-08-10).
const GREEN = [
  { id: 'G1', label: 'self-heal: NO workdir supplied (24,918 fires — selfheal-watch/room)', args: { tool: 'selfheal-watch' } },
  { id: 'G2', label: 'edge-runner: workdir = default_workdir_root exactly (exec 25552, the ONE fire-tool row that ever supplied one)', args: { tool: 'edge-runner', workdir: ROOT } },
  { id: 'G3', label: 'planning: workdir = a run package under .rbtv/goals/<goal>', args: { workflow: 'planning', workdir: `${GOALDIR}/runs/run-1` } },
];

// Build a scratch copy of argv-template.js with one guard removed, and return its exports.
const scratches = [];
function mutant(tag, mutate) {
  const original = fs.readFileSync(SRC, 'utf8');
  const mutated = mutate(original);
  if (mutated === original) return { error: 'mutation matched nothing — the anchor moved' };
  const file = path.join(__dirname, '..', `argv-template.__7562scratch-${tag}-${process.pid}.js`);
  fs.writeFileSync(file, mutated);
  scratches.push(file);
  try {
    return { mod: require(file) };
  } catch (err) {
    return { error: err.message };
  }
}

let exit = 0;
try {
  const { checkFireToolWorkdir } = require(SRC);

  say(`SANCTIONED ROOT (fixture): ${ROOT}`);
  say('');
  say('── RED: hostile shapes are REFUSED, typed, post-fix ──');
  for (const r of RED) {
    const reason = checkFireToolWorkdir({ tool: 't', workdir: r.wd }, ROOT);
    check(typeof reason === 'string' && reason.includes(r.expect),
      `${r.id} ${r.label} is REFUSED and the reason names "${r.expect}"`,
      reason === null ? 'ACCEPTED — no refusal at all' : `reason: ${reason}`);
  }

  say('');
  say('── REFUSAL SHAPE: loud, and it NAMES the sanctioned root (never a silent normalization) ──');
  const named = checkFireToolWorkdir({ workdir: '/home/henri/.ssh' }, ROOT);
  check(typeof named === 'string' && named.includes(ROOT),
    'the refusal message carries the sanctioned root verbatim', String(named));
  // A repaired value would be the defect criterion 5 forbids: the function returns a REASON or
  // null, and never a path — there is nothing for a caller to accept as a fixed-up value.
  check(checkFireToolWorkdir({ workdir: `${ROOT}/` }, ROOT) !== null,
    'a trailing-slash near-miss is REFUSED, not normalized into the sanctioned root',
    String(checkFireToolWorkdir({ workdir: `${ROOT}/` }, ROOT)));

  say('');
  say('── GREEN: every legitimate live row shape still passes (the outage criterion) ──');
  for (const g of GREEN) {
    const reason = checkFireToolWorkdir(g.args, ROOT);
    check(reason === null, `${g.id} ${g.label} is ACCEPTED`, reason || 'no refusal');
  }

  say('');
  say('── SUPPLIED, NEVER RESOLVED (the outage detector) ──');
  check(checkFireToolWorkdir({ tool: 'selfheal-watch' }, ROOT) === null,
    'G1b an ABSENT workdir is not judged at all — the server-composed fallback is never gated');
  // The mutation: govern what the fire path RESOLVES (`args.workdir || default_workdir_root`)
  // rather than what the caller supplied. Under the pre-7.562 rule (W1 absent) that refuses the
  // resolved value of every one of the 25,647 fire-tool rows that supplied nothing.
  check(checkFireToolWorkdir({ workdir: ROOT }, null) !== null,
    'G1c MUTATION — governing the RESOLVED value under the pre-7.562 root set refuses the fallback every live row uses',
    String(checkFireToolWorkdir({ workdir: ROOT }, null)));

  say('');
  say('── MUTATION: each arm is shown to FLIP when its guard is removed ──');

  // M0 — the PRE-FIX state: no workdir guard on the fire-tool path at all. Every hostile shape
  // reaches `--property WorkingDirectory=`.
  const m0 = mutant('nogate', (s) => s.replace(
    "  if (!Object.hasOwn(args, 'workdir')) return null;",
    '  return null; // MUTANT M0 — the pre-7.562 fire-tool path: no workdir guard whatsoever'));
  if (m0.error) {
    check(false, 'M0 the pre-fix (unguarded) mutant was built', m0.error);
  } else {
    const accepted = RED.filter((r) => m0.mod.checkFireToolWorkdir({ workdir: r.wd }, ROOT) === null);
    check(accepted.length === RED.length,
      `M0 PRE-FIX every hostile shape is ACCEPTED with no guard (${accepted.length}/${RED.length})`,
      accepted.map((r) => r.id).join(','));
  }

  // M1 — delete the raw `..` test. R1 must still be refused, but for a DIFFERENT reason; asserting
  // on the reason string rather than on mere refusal is what makes R1 non-vacuous.
  const m1 = mutant('dots', (s) => s.replace("raw.includes('..')", 'false /* MUTANT M1 */'));
  if (m1.error) {
    check(false, 'M1 the ..-guard mutant was built', m1.error);
  } else {
    const r = m1.mod.checkFireToolWorkdir({ workdir: RED[0].wd }, ROOT);
    check(typeof r === 'string' && !r.includes('".." segment'),
      'M1 with the ".." test deleted, R1 is refused by a DIFFERENT rule — the arm discriminates', String(r));
  }

  // M2 — delete the containment predicate. R2/R6 must flip to ACCEPTED.
  const m2 = mutant('containment', (s) => s.replace(
    '  if (i === -1 || parts[i + 1] !== \'goals\' || !parts[i + 2]) {',
    '  if (false) { // MUTANT M2 — containment predicate removed'));
  if (m2.error) {
    check(false, 'M2 the containment mutant was built', m2.error);
  } else {
    check(m2.mod.checkFireToolWorkdir({ workdir: '/home/henri/.ssh' }, ROOT) === null
      && m2.mod.checkFireToolWorkdir({ workdir: `${ROOT}/.rbtv/config` }, ROOT) === null,
      'M2 with the containment predicate removed, R2 and R6 are ACCEPTED');
  }

  // M3 — delete the control-character test in the fire-tool door. R4 must flip to ACCEPTED,
  // because the lexical containment alone reads `x\nSuccessExitStatus=77` as a legal goal segment.
  const m3 = mutant('control', (s) => s.replace(
    "CONTROL_RE.test(value)) return 'workdir must carry no control character'",
    'false) return null /* MUTANT M3 */'));
  if (m3.error) {
    check(false, 'M3 the control-character mutant was built', m3.error);
  } else {
    check(m3.mod.checkFireToolWorkdir({ workdir: RED[2].wd }, ROOT) === null,
      'M3 with the control-character test removed, R4 is ACCEPTED', String(m3.mod.checkFireToolWorkdir({ workdir: RED[2].wd }, ROOT)));
  }

  // M4 — drop W1 from the root set. G2 (the edge-runner) must go RED. This is the arm that catches
  // "just reuse the workflow rule unchanged", which is the outage the code comment predicted.
  check(checkFireToolWorkdir({ workdir: ROOT }, null) !== null,
    'M4 with W1 dropped, G2 the edge-runner row is REFUSED — the naive rule really would break it');

  say('');
  say('── WIRED AT BOTH DOORS, AND EXACTLY ONE VALIDATOR EXISTS ──');
  const ticker = fs.readFileSync(TICKER_SRC, 'utf8');
  const store = fs.readFileSync(STORE_SRC, 'utf8');
  check(/checkFireToolWorkdir\(args, cc\.defaultWorkdir\)/.test(ticker),
    'the FIRE door (ticker.js launchFireTool) calls the validator with the configured root');
  check(/checkFireToolWorkdir\(parsed, workdirRoot\)/.test(store),
    'the ENQUEUE door (heart-store.js validateArgs, fire-tool branch) calls the same validator');
  // A second, parallel workdir validator is the defect this row exists to prevent, so the probe
  // pins that the containment predicate is written down ONCE.
  const definers = [SRC, TICKER_SRC, STORE_SRC]
    .filter((f) => /\.rbtv'\)/.test(fs.readFileSync(f, 'utf8')) || /indexOf\('\.rbtv'\)/.test(fs.readFileSync(f, 'utf8')));
  check(definers.length === 1 && definers[0] === SRC,
    'the `.rbtv/goals` containment is implemented in exactly ONE file — no parallel validator',
    definers.map((f) => path.basename(f)).join(','));

  say('');
  say(`RESULT: ${failures === 0 ? 'workdir governance holds at both doors, no legitimate row refused' : failures + ' check(s) failed'}`);
  exit = failures === 0 ? 0 : 1;
} catch (err) {
  say('ERROR: ' + err.stack);
  exit = 1;
} finally {
  for (const f of scratches) { try { fs.unlinkSync(f); } catch { /* best effort */ } }
}

say('EXIT: ' + exit);
say('WALL_MS: ' + (Date.now() - start));
fs.writeFileSync(outPath, lines.join('\n') + '\n');
process.stdout.write(lines.join('\n') + '\n');
process.exitCode = exit;

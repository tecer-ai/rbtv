'use strict';

// probe-caged-settings — task 7.444 (MC2). Proves the `--settings` carry-into-the-cage step on
// the REAL profile catalogue, and proves the wall it does NOT widen.
//
// Four checks, each with the control that makes it capable of failing:
//
//   1. ALL FOUR claude profiles rewrite, loaded from the real `config/spawn-profiles.yaml`
//      through the real `loadConfig` — not from hand-typed argv, which would test the mechanism
//      and never the mapping.
//   2. THE MUTATION RED: with the flag the planner matches on changed, every one of those four
//      stops rewriting. A planner that rewrote regardless would pass check 1 and fail here.
//   3. NO PER-PROFILE SPECIAL CASE: no profile name appears anywhere in server/spawn/. Fired
//      POSITIVE CONTROL — the same search run against the config file, where the names DO live,
//      so an empty result is a measurement rather than a broken pattern.
//   4. THE WALL IS UNCHANGED: composed against a scratch seat, the cage spec contains NO opening
//      covering the ignite config tree, while it DOES contain the RW opening covering the
//      materialized copy. Both halves asserted together — "the file is reachable" and "the tree
//      is still not" are different claims and the fix must produce both.
//
// Run: node server/spawn/probes/probe-caged-settings.js

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const IGNITE = path.resolve(__dirname, '..', '..', '..');
const { loadConfig } = require('../config');
const { planCagedSettings, materializeCagedSettings } = require('../harness-config');
const { composeSeatCage, contains } = require('../cage');

const outPath = path.join(__dirname, 'probe-caged-settings.out');
fs.writeFileSync(outPath, '');
const checks = [];
function out(...l) { fs.appendFileSync(outPath, l.join('\n') + '\n'); console.log(l.join('\n')); }
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const CONFIG = path.join(IGNITE, 'config', 'spawn-profiles.yaml');
const CLAUDE = ['claude-fable', 'claude-opus', 'claude-sonnet', 'claude-haiku'];
const CONFIG_TREE = path.join(IGNITE, 'config');

out(`COMMAND: node ${path.relative(process.cwd(), __filename)}`, `CONFIG: ${CONFIG}`, '');

const config = loadConfig(CONFIG);
const seatDir = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-caged-settings-'));

// ── 1. all four claude profiles rewrite, off the real catalogue ──────────────────────────────
const rewritten = [];
for (const name of CLAUDE) {
  const profile = config.profiles[name];
  const before = profile.exec.argv;
  const { argv, copies } = planCagedSettings(before, seatDir);
  const i = argv.indexOf('--settings');
  const ok = i >= 0 && argv[i + 1].startsWith(seatDir + path.sep) && copies.length === 1;
  rewritten.push(ok);
  out(`  ${name}: ${before[before.indexOf('--settings') + 1]}`, `        -> ${i >= 0 ? argv[i + 1] : '(no --settings)'}`);
}
check('all four claude profiles rewrite --settings into the launch dir (real catalogue)',
  rewritten.length === 4 && rewritten.every(Boolean), `${rewritten.filter(Boolean).length}/4`);

// The copy is real and byte-identical — the criterion is content identity, not path existence.
const { argv: haikuArgv, copies } = planCagedSettings(config.profiles['claude-haiku'].exec.argv, seatDir);
materializeCagedSettings(copies);
const sha = (p) => execFileSync('sha256sum', [p]).toString().split(' ')[0];
check('the materialized copy is byte-identical to its source',
  sha(copies[0].src) === sha(copies[0].dest), `${sha(copies[0].src)} == ${sha(copies[0].dest)}`);

// ── 2. the mutation red ──────────────────────────────────────────────────────────────────────
// Re-plan with the flag spelled differently. Nothing must rewrite. This is the arm that fails if
// the planner ever matches on something other than the flag it claims to match on.
const mutated = CLAUDE.map((name) => {
  const argv = config.profiles[name].exec.argv.map((a) => (a === '--settings' ? '--settings-MUTATED' : a));
  return planCagedSettings(argv, seatDir).copies.length;
});
check('MUTATION RED: rename the flag and every one of the four stops rewriting',
  mutated.every((n) => n === 0), `copies per profile: [${mutated.join(', ')}]`);

// ── 3. no per-profile special case, with a fired positive control ────────────────────────────
// `-l` (files WITH a match), never `-c`: `-c` prints a count line for EVERY file searched,
// including the zeros, so counting its output lines counts the whole directory. That bug read
// "29 files name a claude profile" on a tree where none does — measured on this probe's own
// first run, and it would have failed the check for the opposite of the real reason.
function grepFiles(pattern, dir) {
  try {
    // `--exclude-dir=probes` is the ONE exclusion and it is stated, not hidden: this probe's own
    // source lists the four names to iterate them, so an unexcluded search reports the CHECKER's
    // statement of the rule as a violation of it. The claim under test is about the SPAWN PATH,
    // never about its instruments; the positive control below still fires, so the exclusion
    // narrows the search without blinding it.
    return execFileSync('grep', ['-rlE', pattern, dir, '--include=*.js', '--exclude-dir=probes'], { encoding: 'utf8' })
      .trim().split('\n').filter(Boolean);
  } catch { return []; }   // grep exits 1 on no match
}
function grepCountFile(pattern, file) {
  try { return execFileSync('grep', ['-Ec', pattern, file], { encoding: 'utf8' }).trim() | 0; } catch { return 0; }
}
const NAMES = 'claude-(fable|opus|sonnet|haiku)';
const inSpawn = grepFiles(NAMES, path.join(IGNITE, 'server', 'spawn'));
const inConfig = grepCountFile(NAMES, CONFIG);
check('POSITIVE CONTROL: the profile-name pattern DOES match where the names live',
  inConfig > 0, `${inConfig} line(s) in ${path.relative(IGNITE, CONFIG)}`);
check('no per-profile special case anywhere in server/spawn/ (probes excluded, see grepFiles)',
  inSpawn.length === 0, inSpawn.map((f) => path.relative(IGNITE, f)).join(', ') || '0 files name a claude profile');

// ── 4. the wall is unchanged: the copy is inside it, the config tree is still outside ────────
// The template lives on the PROFILE's resolved `sandbox`, not at a top-level `cage:` key — the
// config loader folds the shared block in. Reading it from the wrong place yields an EMPTY spec,
// under which both wall checks below pass VACUOUSLY; the assertion after it is what makes that
// impossible rather than merely unlikely (it fired on this probe's own first run).
const template = config.profiles['claude-haiku'].sandbox && config.profiles['claude-haiku'].sandbox.SeatBinds;
const goalDir = path.join(seatDir, 'g');
const spec = composeSeatCage({
  seatBinds: template,
  // 7.607 E2b — the `{runDir}` cage slot is RETIRED (design-lock item 8); what it named is the
  // disclosed alias), so the fixture supplies exactly what parseSeatPath would.
  values: { workdir: seatDir, seatDir, goalDir },
  grants: [],                                  // no read-root, no worktree — an ordinary seat
});
if (!Array.isArray(template) || template.length === 0 || spec.length === 0) {
  check('the composed cage spec is NON-EMPTY (else both wall checks below are vacuous)', false,
    `template=${Array.isArray(template) ? template.length : 'absent'} spec=${spec.length}`);
  out('', 'ABORT: refusing to report a wall verdict from an empty spec.');
  process.exit(1);
}
check('the composed cage spec is NON-EMPTY (else both wall checks below are vacuous)', true,
  `${template.length} template entries -> ${spec.length} openings`);
const opensConfigTree = spec.filter((e) => e.verb !== 'tmpfs' && contains(e.path, CONFIG_TREE));
const opensTheCopy = spec.filter((e) => e.verb === 'bind' && contains(e.path, haikuArgv[haikuArgv.indexOf('--settings') + 1]));
check('the cage opens NO path covering the ignite config tree (SeatBinds NOT widened)',
  opensConfigTree.length === 0, opensConfigTree.map((e) => `${e.verb}:${e.path}`).join(', ') || 'none');
check('the cage DOES open the materialized copy read-write',
  opensTheCopy.length > 0, opensTheCopy.map((e) => `${e.verb}:${e.path}`).join(', ') || 'NONE');

fs.rmSync(seatDir, { recursive: true, force: true });
const failed = checks.filter((c) => !c.pass).length;
out('', `${checks.length - failed}/${checks.length} PASS`);
process.exit(failed === 0 ? 0 : 1);

'use strict';

// cast — shared primitives: argv parsing, model/effort/folder resolution, the model table, doctor + list.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { SPECS, ROWS } = require('../catalog');

// CLI model names are short: the provider prefix and the `claude-` prefix are dropped
// (`zai-coding-plan/glm-5.2` -> `glm-5.2`, `claude-opus-5` -> `opus-5`). SPECS stays keyed by
// the id the harness itself wants; this maps short name -> that id, per harness.
function shortName(harness, id) {
  return SPECS[harness][id].short || id.split('/').pop().replace(/^claude-/, '');
}

const SHORT = {};
for (const harness of Object.keys(SPECS)) {
  SHORT[harness] = {};
  for (const id of Object.keys(SPECS[harness])) SHORT[harness][shortName(harness, id)] = id;
}

// headed = the harness's interactive TUI instead of its one-shot print mode. The TUI owns the
// terminal, so the prompt rides argv (see promptArgv) instead of stdin.
function baseArgv(harness, model, folder, headed) {
  switch (harness) {
    case 'claude': return ['claude', ...(headed ? [] : ['-p']), '--model', model, '--permission-mode', 'bypassPermissions'];
    case 'codex': return ['codex', ...(headed ? [] : ['exec']), '--cd', folder, '-m', model, '--sandbox', 'danger-full-access', '-c', 'approval_policy=never'];
    // --auto: headless `opencode run` auto-REJECTS every permission.asked (observed: external_directory
    // on /tmp and on the launch folder of a resumed session — issue G-owner-console-0819-0010); --auto
    // flips that to auto-approve, per invocation. The opencode twin of the two flags above.
    case 'opencode': return headed ? ['opencode', '-m', model] : ['opencode', 'run', '-m', model, '--auto'];
    default: return null;
  }
}

// How each harness takes the initial prompt on the command line (headed mode).
function promptArgv(harness, text) {
  switch (harness) {
    case 'opencode': return ['--prompt', text];
    default: return [text]; // claude, codex: positional
  }
}

function fail(msg) {
  process.stderr.write(`cast: ${msg}\n`);
  process.exit(2);
}

const HARNESSES = Object.keys(SPECS);
const USAGE = 'cast <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) [-s TEXT | -S FILE] [--headed] [--dry-run]';
const SEAT_USAGE = 'cast seat [launch-folder] [-p TEXT | -f FILE] [--headed] [--dry-run]';
const RESUME_USAGE = 'cast resume <harness> <session-id|last> [launch-folder] (-p TEXT | -f FILE) [--dry-run]';
const SESSIONS_USAGE = 'cast sessions [harness] [launch-folder] [--json] [-n N]';
const KNOWN_FLAGS = '-p, -f, -s, -S, --headed, --dry-run, --detached, -h/--help';

// Detached launches lose the caller's tracking: the orchestrator never hears the exit
// (issue I-1 / ruling D, 2026-08-18). Measured discriminators: under `… &` and nohup-
// then-abandon inside a harness Bash call the parent shell exits instantly, so cast
// starts (or lands within 300ms) with a systemd/init parent; setsid makes cast a
// session leader. A tracked run_in_background launch keeps a live bash parent with
// neither mark — and a nohup'd launch the caller WAITS on also passes, correctly: the
// tracking exists. (No SIGHUP-ignore arm: node resets nohup's SIG_IGN at startup —
// measured 2026-08-18 — so that mark can never fire inside cast.) This check is the
// standing gate on the resource itself — it holds for every caller on every harness.
function detachMarks() {
  const marks = [];
  const ppid = process.ppid;
  let pcomm = '';
  try { pcomm = fs.readFileSync(`/proc/${ppid}/comm`, 'utf8').trim(); } catch { /* parent gone */ }
  if (ppid === 1 || pcomm === 'systemd' || pcomm === 'init' || pcomm === '') {
    marks.push(`orphaned at launch (parent ${ppid} ${pcomm || 'gone'})`);
  }
  try {
    const stat = fs.readFileSync('/proc/self/stat', 'utf8');
    const sid = Number(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[3]);
    if (sid === process.pid) marks.push('session leader (setsid)');
  } catch { /* no procfs */ }
  return marks;
}

function refuseIfDetached(skip) {
  if (skip || process.platform !== 'linux') return;
  let marks = detachMarks();
  if (!marks.length) {
    // the parent shell may not have exited yet — one re-check after a beat
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 300);
    marks = detachMarks();
  }
  if (marks.length) {
    fail(`refused: detached launch — ${marks.join('; ')}\n`
      + 'A detached cast job is invisible to the calling harness: no completion nudge, no '
      + 'tracking (issue I-1, ruling D 2026-08-18). Launch cast as a plain foreground command '
      + "in a tracked background call (run_in_background) instead, and arm 'cast monitor "
      + "--watch' for freeze detection.\n"
      + 'A deliberate detach (cron, a systemd unit) may pass --detached to override.');
  }
}

// "1=low 2=medium 3-5=high" — what each effort number resolves to, clamping folded in.
function effortMap(eff) {
  if (!eff || eff.inert) return '(no dial — any number)';
  const parts = [];
  for (let n = 1; n <= 5; n++) {
    const word = eff.rungs[Math.min(n, eff.rungs.length) - 1];
    const last = parts[parts.length - 1];
    if (last && last.word === word) last.to = n;
    else parts.push({ from: n, to: n, word });
  }
  return parts.map((p) => `${p.from === p.to ? p.from : `${p.from}-${p.to}`}=${p.word}`).join(' ');
}

function modelTable() {
  const lines = [];
  const names = [];
  for (const harness of HARNESSES) {
    for (const id of Object.keys(SPECS[harness])) names.push(`${harness}  ${shortName(harness, id)}`);
  }
  const width = Math.max(...names.map((n) => n.length));
  let i = 0;
  for (const harness of HARNESSES) {
    for (const id of Object.keys(SPECS[harness])) {
      lines.push(`  ${names[i++].padEnd(width)}   ${effortMap(SPECS[harness][id].effort)}`);
    }
  }
  return lines;
}

function buildInventory() {
  const inv = {};
  for (const harness of HARNESSES) {
    inv[harness] = {};
    for (const id of Object.keys(SPECS[harness])) {
      const eff = SPECS[harness][id].effort;
      inv[harness][shortName(harness, id)] = (!eff || eff.inert) ? [] : eff.rungs.slice();
    }
  }
  return inv;
}

// naive scoring: longest common prefix length, +100 if either string contains the other
function suggest(input, candidates) {
  let best = null;
  let bestScore = -1;
  for (const c of candidates) {
    let i = 0;
    while (i < input.length && i < c.length && input[i] === c[i]) i++;
    let score = i;
    if (c.includes(input) || input.includes(c)) score += 100;
    if (score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return best;
}

// Both halves live in acct — `doctor` (harnesses installed + providers enabled) and `usage`
// (what is left on each) — so cast doctor runs them rather than keeping a second copy of either.
// `usage` hits the network; it is the slow half of this command.
function runDoctor(args) {
  const json = args.includes('--json');
  const run = (sub) => {
    const res = spawnSync('acct', [sub, ...(json ? ['--json'] : [])], { encoding: 'utf8' });
    if (res.error) fail('doctor needs `acct` on PATH — it owns the harness/provider inventory');
    if (res.status !== 0) fail(`acct ${sub} failed:\n${(res.stderr || res.stdout).trim()}`);
    return res.stdout;
  };
  const doctor = run('doctor');
  const usage = run('usage');
  if (json) {
    process.stdout.write(`${JSON.stringify({ ...JSON.parse(doctor), usage: JSON.parse(usage) })}\n`);
  } else {
    process.stdout.write(`${doctor.trimEnd()}\n\nusage now\n${usage.replace(/^/gm, '  ').trimEnd()}\n`);
  }
  process.exit(0);
}

function runList(args) {
  if (args.includes('--json')) {
    process.stdout.write(`${JSON.stringify(buildInventory())}\n`);
  } else {
    for (const line of modelTable()) process.stdout.write(`${line}\n`);
  }
  process.exit(0);
}

// Rung mapping: input N (1-5) -> ladder[min(N, ladder.length) - 1]. Inert ladder -> no argv.
function resolveEffort(spec, n) {
  const eff = spec.effort;
  if (!eff || eff.inert) return { word: null, argv: [] };
  const word = eff.rungs[Math.min(n, eff.rungs.length) - 1];
  return { word, argv: eff.flag(word) };
}

// Flags shared by both launch modes: -p/-f prompt, -s/-S system prompt, --headed, --dry-run.
// Seat mode supplies the system prompt itself (seat.md), so its prompt is optional and -s/-S refused.
function parseArgs(rawArgv, usage, requirePrompt) {
  let dryRun = false;
  let headed = false;
  let detached = false;
  let promptText = null;
  let promptSource = null;
  let system = null;
  const positional = [];
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--detached') {
      detached = true;
    } else if (a === '--headed') {
      headed = true;
    } else if (a === '-p' || a === '-f') {
      if (promptSource) fail("refused: -p and -f are mutually exclusive — pass exactly one");
      promptSource = a;
      const val = rawArgv[++i];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      if (a === '-p') {
        promptText = val;
      } else if (val === '-') {
        promptText = fs.readFileSync(0, 'utf8');
      } else {
        promptText = fs.readFileSync(val, 'utf8');
      }
    } else if (a === '-s' || a === '-S') {
      if (system) fail('refused: -s and -S are mutually exclusive — pass exactly one');
      const val = rawArgv[++i];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      if (a === '-s') {
        system = { text: val };
      } else {
        const file = path.resolve(process.cwd(), val);
        if (!fs.existsSync(file)) fail(`system-prompt file does not exist: ${file}`);
        system = { file };
      }
    } else if (a.startsWith('-')) {
      fail(`refused: unknown flag '${a}'\nknown flags: ${KNOWN_FLAGS}`);
    } else {
      positional.push(a);
    }
  }
  if (requirePrompt && !promptSource) fail(`refused: exactly one of -p TEXT or -f FILE is required\nusage: ${usage}`);
  return { dryRun, headed, detached, promptText, system, positional };
}

function resolveFolder(folderArg) {
  const folder = path.resolve(process.cwd(), folderArg);
  if (!fs.existsSync(folder) || !fs.statSync(folder).isDirectory()) {
    fail(`launch-folder does not exist: ${folder}`);
  }
  return folder;
}

// The catalog also carries rows cast can NEVER spawn — the API workers. `cast route` may pick
// them; addressing one as a launch pair is a refusal, not a "no such model", so the caller learns
// WHY (and reaches it via `cast api`).
function refuseIfNotLaunchable(harness, model) {
  const row = ROWS.find((r) => r.harness === harness && r.model === model && r.mode !== 'cli');
  if (row) {
    fail(`refused: '${harness} ${model}' is mode=${row.mode} — not launchable by cast, use \`cast api\``);
  }
}

function resolveModel(harness, model) {
  if (!SPECS[harness]) {
    refuseIfNotLaunchable(harness, model);
    fail(`refused: '${harness}' is not a known harness\nknown: ${HARNESSES.join(', ')}`);
  }
  const modelId = SPECS[harness][model] ? model : SHORT[harness][model];
  const spec = SPECS[harness][modelId];
  if (!spec) {
    refuseIfNotLaunchable(harness, model);
    const candidates = Object.keys(SHORT[harness]);
    const guess = suggest(model, candidates);
    fail(`refused: '${model}' is not a known model for '${harness}'\ndid you mean '${guess}'?\nknown (${harness}): ${candidates.join(', ')}`);
  }
  return { modelId, spec };
}

module.exports = {
  shortName, SHORT, baseArgv, promptArgv,
  fail, HARNESSES, USAGE, SEAT_USAGE,
  RESUME_USAGE, SESSIONS_USAGE, KNOWN_FLAGS, detachMarks,
  refuseIfDetached, effortMap, modelTable, buildInventory,
  suggest, runDoctor, runList, resolveEffort,
  parseArgs, resolveFolder, refuseIfNotLaunchable, resolveModel,
};

'use strict';

// cast — shared primitives: argv parsing, model/effort/folder resolution, the words of `cast list`.

const fs = require('fs');
const path = require('path');
const { SPECS, ROWS } = require('../supported-models');

const { gate } = require('./model-catalog');

// CLI model names are short: the provider prefix and the `claude-` prefix are dropped
// (`zai-coding-plan/glm-5.3` -> `glm-5.3`, `claude-opus-5-5` -> `opus-5-5`). SPECS stays keyed by
// the id the harness itself wants; this maps short name -> that id, per harness.
function shortName(harness, id) {
  return SPECS[harness][id].short || id.split('/').pop().replace(/^claude-/, '');
}

const SHORT = {};
for (const harness of Object.keys(SPECS)) {
  SHORT[harness] = {};
  for (const id of Object.keys(SPECS[harness])) SHORT[harness][shortName(harness, id)] = id;
}

// Codex reads at most this many bytes of AGENTS.md (default 32 KiB); rbtv rules reach it as
// full text there, so every Codex launch raises it. Needs no trusted folder, unlike config.toml.
const CODEX_DOC_LIMIT = ['-c', 'project_doc_max_bytes=131072'];

// headed = the harness's interactive TUI instead of its one-shot print mode. The TUI owns the
// terminal, so the prompt rides argv (see promptArgv) instead of stdin.
function baseArgv(harness, model, folder, headed) {
  switch (harness) {
    case 'claude': return ['claude', ...(headed ? [] : ['-p']), '--model', model, '--permission-mode', 'bypassPermissions'];
    // --skip-git-repo-check: codex refuses to start outside a git repo without it (0.154+, observed 2026-09-24).
    case 'codex': return ['codex', ...(headed ? [] : ['exec']), '--cd', folder, '-m', model, '--sandbox', 'danger-full-access', '-c', 'approval_policy=never', '--skip-git-repo-check', ...CODEX_DOC_LIMIT];
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
const USAGE = 'cast <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) [-s TEXT | -S FILE | --rogue AGENT-FILE] [--headed] [--dry-run]';
const USAGE_IG = 'cast --agent NAME (-p TEXT | -f FILE) [--headed] [--dry-run]';
const RESUME_USAGE = 'cast resume <harness> <session-id|last> [launch-folder] (-p TEXT | -f FILE) [--dry-run]';
const SESSIONS_USAGE = 'cast sessions [harness] [launch-folder] [--json] [-n N]';
const KNOWN_FLAGS = '-p, -f, -s, -S, --agent, --rogue, --headed, --dry-run, --detached, -h/--help';

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

// The one sentence every effort-facing surface says: the dial takes a NUMBER, the words are
// labels. Agents kept passing rung words to the launch path, which only ever accepted 1-5.
const EFFORT_RULE = "effort is an integer 1-5: N picks the Nth rung, clamped to the model's top — pass the number, the words are labels only.";

// The words of `cast list`: --agents (every agent, the default) or --agent NAME, --full for whole
// descriptions, and --json. Every other word is refused. The model lists are `cast models list`.
function listArgs(args) {
  const refuse = (what, why, next) => fail(`refused: ${what}\n${why}\nNothing was listed.\n${next}`);
  const moved = () => refuse('the model lists moved',
    'cast list shows the rbtv agents; every list of models is a view of cast models list', 'cast models list');
  let json = false;
  let agents = false;
  let full = false;
  let agent = null;
  const named = [];
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (a === '--json') json = true;
    else if (a === '--full') full = true;
    else if (a === '--models') moved();
    else if (a === '--agents') agents = true;
    else if (a === '--agent') {
      const name = args[i + 1];
      if (name === undefined || name.startsWith('-')) {
        refuse("--agent takes an agent's name or path", 'every agent: cast list --agents', 'cast list --agent NAME');
      }
      if (agent !== null) refuse('--agent takes one agent', `got '${agent}' and '${name}'`, 'cast list -h');
      agent = name;
      i += 1;
    } else if (a.startsWith('-')) {
      refuse(`'${a}' is not a cast list option`,
        'cast list takes --agents or --agent NAME, and --full and --json', 'cast list -h');
    } else named.push(a);
  }
  if (agents && agent !== null) {
    refuse('--agents and --agent NAME are different lists', 'pass one of them', 'cast list -h');
  }
  if (named[0] === 'models') moved();
  if (named.length) {
    refuse(`cast list takes no name by itself, got '${named[0]}'`,
      'one agent in full is --agent NAME', `cast list --agent ${named[0]}`);
  }
  return { json, full, agent };
}

// Rung mapping: input N (1-5) -> ladder[min(N, ladder.length) - 1]. Inert ladder -> no argv.
function resolveEffort(spec, n) {
  const eff = spec.effort;
  if (!eff || eff.inert) return { word: null, argv: [] };
  const word = eff.rungs[Math.min(n, eff.rungs.length) - 1];
  return { word, argv: eff.flag(word) };
}

// An effort given as a number 1-5 (the rung mapping above) or as the model's own rung word (what
// an agent.json stores). A model with no dial takes neither. Anything else is unsupported.
function resolveEffortValue(spec, effort, harness, model) {
  if (spec.effort?.inert && (effort === null || effort === 'inert' || (Number.isInteger(effort) && effort >= 1 && effort <= 5))) {
    return { word: null, argv: [] };
  }
  if (Number.isInteger(effort) && effort >= 1 && effort <= 5) return resolveEffort(spec, effort);
  if (typeof effort === 'string' && spec.effort && !spec.effort.inert && spec.effort.rungs.includes(effort)) {
    return { word: effort, argv: spec.effort.flag(effort) };
  }
  throw new Error(`unsupported effort for ${harness}/${model}: ${effort}`);
}

// Launch flags: -p/-f prompt, -s/-S system prompt, --headed, --dry-run, --detached.
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

// The supported models also hold rows cast can NEVER spawn — the API workers. `cast route` may
// pick them; addressing one as a launch pair is a refusal, not a "no such model", so the caller
// learns WHY (and reaches it via `cast api`).
function refuseIfNotLaunchable(harness, model) {
  const row = ROWS.find((r) => r.harness === harness && r.model === model && r.mode !== 'cli');
  if (row) {
    fail(`refused: '${harness} ${model}' is mode=${row.mode} — not launchable by cast, use \`cast api\``);
  }
}

// The one lookup every launch goes through: the model's launch spec, once the launch check
// (lib/model-catalog.js `gate`) has passed it for the installation that holds `from` — the agent's folder
// for an agent launch, the current folder for a plain one. Throws; never exits.
function lookupModel(harness, model, from) {
  if (typeof harness !== 'string' || !SPECS[harness]) throw new Error(`unknown harness: ${harness}`);
  if (typeof model !== 'string' || !model) throw new Error('model must be a string');
  if (typeof from !== 'string' || !from) throw new Error('lookupModel needs the folder that locates the installation');
  const modelId = SPECS[harness][model] ? model : SHORT[harness][model];
  gate(harness, modelId ? shortName(harness, modelId) : model, from);
  return { modelId, spec: SPECS[harness][modelId] };
}

function resolveModel(harness, model, from) {
  try {
    return lookupModel(harness, model, from);
  } catch (e) {
    refuseIfNotLaunchable(harness, model);
    if (typeof harness !== 'string' || !SPECS[harness]) {
      fail(`refused: '${harness}' is not a known harness\nknown: ${HARNESSES.join(', ')}`);
    }
    fail(e.message);
  }
}

module.exports = {
  CODEX_DOC_LIMIT, shortName, SHORT, baseArgv, promptArgv,
  fail, HARNESSES, USAGE, USAGE_IG,
  RESUME_USAGE, SESSIONS_USAGE, KNOWN_FLAGS, detachMarks,
  refuseIfDetached, effortMap, EFFORT_RULE,
  listArgs, resolveEffort, resolveEffortValue,
  parseArgs, resolveFolder, refuseIfNotLaunchable, lookupModel, resolveModel,
};

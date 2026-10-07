'use strict';

// API — ignite deploy [COMMIT] [--deploy-folder PATH] [--dry-run]: resolves the commit, the
// installation and the deploy folder, runs deploy.sh once, confirms the service stays active at
// that commit, and appends the result to the installation's deploy log.
// run(argv, flags, deps, resolveInstallation) → Promise of the exit code.
// deps.env / deps.stdout / deps.stderr optional. deps.platform, deps.sourceDir (the folder whose
// repository gives the default commit), deps.pollMs and deps.limitMs replace the real ones in tests.

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { runtimeFolder } = require('./memory-write.js');

const UNIT = 'rbtv-ignite-agents.service';
const UNIT_TEMPLATE = path.join(__dirname, 'units', UNIT);
const SCRIPT = path.join(__dirname, 'deploy.sh');
const POLL_MS = 1000;
const LIMIT_MS = 30000;
const STEADY_CHECKS = 3;
const JOURNAL_LINES = 20;
const LOG_NAME = 'deploys.jsonl';

const HELP = `ignite deploy — run the waking service from a commit

usage: ignite deploy [COMMIT] [--deploy-folder PATH] [--installation PATH]
                     [--dry-run] [--json]

Runs deploy.sh (beside this program) once, then confirms the result. The
script checks the deploy folder out at COMMIT, rewrites the systemd user unit
${UNIT} and restarts it. The restart reaches every
agent of the installation. A turn in progress is left running: the restarted
service takes it over and starts no second one.
Linux only. On another system this command refuses and changes nothing.

COMMIT
  Any name git resolves to a commit in the deploy folder. Default: the HEAD
  commit of the repository that holds this program. The full id is printed.

--deploy-folder PATH
  The git worktree the service runs from. The first of these that is set:
    1. --deploy-folder PATH
    2. the environment variable RBTV_DEPLOY
    3. the folder the installed unit file already runs from (its ExecStart
       line)
  When none gives it (a first deploy), the command refuses and asks for
  --deploy-folder.

--installation PATH
  Default: the installation of RBTV_AGENT_HOME, otherwise the walk up from
  the current folder to .rbtv/config/ignite/config.json. When the installed
  unit serves another installation, the command refuses until --installation
  names the one to serve.

--dry-run
  Prints the commit, the installation, the deploy folder, the exact script
  command and the deploy log. Runs nothing and writes nothing.

After the script, the command waits up to ${LIMIT_MS / 1000} seconds for the service to answer
active on ${STEADY_CHECKS} checks in a row, one second apart, with the deploy folder at COMMIT.

Undo: when the deploy folder's commit changed, the output ends with one line
to copy, "to undo: ignite deploy <commit before> ...". It deploys the commit
that was there before, with the same deploy folder and installation.

Deploy log: every deploy that ran the script appends one line to
<installation>/.rbtv/runtime/ignite/${LOG_NAME}, a JSON object with time
(UTC), commitBefore, commitAsked, commitAfter, deployFolder, outcome ("ok" or
"failed") and, for a failure, reason. A refusal and a dry run write nothing.
When the line cannot be written, the command warns on stderr and its exit
code does not change.

Success: exit 0, with the commit before, the commit now and the service state.
  --json prints {dryRun, commit, installation, deployFolder,
  deployFolderSource, command, log, before, now, service, undo}. now, service
  and undo are null on a dry run; undo is also null when the commit did not
  change, and log when the line was not written. The script's own output goes
  to stderr.
Refusal: exit 1, the reason on stderr, nothing changed.
Failure: exit 1 when the script fails or the service is not active in time.
  stderr carries the commit before, the commit now, the service state, the
  last ${JOURNAL_LINES} journal lines, the deploy log and the undo line.

Examples:
  ignite deploy --dry-run
  ignite deploy
  ignite deploy 0f197eb0 --deploy-folder ~/.local/state/rbtv-agents-deploy
`;

function refuse(reason) {
  throw Object.assign(new Error(`${reason}\nNothing changed.\nignite deploy -h`), { exitCode: 1 });
}

function parse(argv) {
  const opts = { dryRun: false, deployFolder: null, commit: null };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') opts.dryRun = true;
    else if (arg === '--deploy-folder') {
      const value = argv[i + 1];
      if (value == null || value.startsWith('--')) refuse('--deploy-folder requires a value');
      opts.deployFolder = value;
      i += 1;
    } else if (arg.startsWith('-')) refuse(`'${arg}' is not a deploy option`);
    else if (opts.commit != null) refuse(`unexpected argument: ${arg}\ndeploy takes one COMMIT`);
    else opts.commit = arg;
  }
  return opts;
}

function git(dir, args, env) {
  const result = spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8', env });
  return result.status === 0 ? result.stdout.trim() : null;
}

// The unit file deploy.sh writes (its unit_dst), read back with the template's own ExecStart line
// as the pattern: the deploy folder and the installation the installed service runs with.
function installedUnit(env) {
  const base = env.XDG_CONFIG_HOME || env.HOME;
  const file = base ? path.join(base, '.config', 'systemd', 'user', UNIT) : null;
  if (!file || !fs.existsSync(file)) return { file };
  const line = fs.readFileSync(UNIT_TEMPLATE, 'utf8').split('\n').find((text) => text.startsWith('ExecStart='));
  const pattern = line.split(/(@DEPLOY@|@INSTALLATION@)/).map((part) => {
    if (part === '@DEPLOY@') return '(?<deploy>.+)';
    if (part === '@INSTALLATION@') return '(?<installation>.+)';
    return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }).join('');
  const match = fs.readFileSync(file, 'utf8').match(new RegExp(`^${pattern}$`, 'm'));
  return { file, ...match?.groups };
}

function deployFolder(opts, env, unit) {
  if (opts.deployFolder) return { folder: path.resolve(opts.deployFolder), source: '--deploy-folder' };
  if (env.RBTV_DEPLOY) return { folder: path.resolve(env.RBTV_DEPLOY), source: 'RBTV_DEPLOY' };
  if (unit.deploy) return { folder: unit.deploy, source: `the installed unit ${unit.file}` };
  const unitState = unit.file && fs.existsSync(unit.file)
    ? `${unit.file} has no ExecStart line this program can read`
    : `no unit is installed${unit.file ? ` at ${unit.file}` : ''}`;
  return refuse(`no deploy folder: --deploy-folder was not given, RBTV_DEPLOY is not set, and ${unitState}.\nFor a first deploy, pass the git worktree the service will run from: ignite deploy --deploy-folder PATH`);
}

function quote(text) {
  return /^[\w@%+=:,./-]+$/.test(text) ? text : `'${text.replace(/'/g, "'\\''")}'`;
}

function serviceState(env) {
  const result = spawnSync('systemctl', ['--user', 'is-active', UNIT], { encoding: 'utf8', env });
  return (result.stdout || '').trim() || 'unknown';
}

// One reading of "active" proves little: a service that exits at startup is restarted by systemd
// and answers active between two exits. The wait ends when it answered active STEADY_CHECKS times
// in a row with the deploy folder at the commit, or when the limit passes.
async function settle(folder, commit, env, deps) {
  const until = Date.now() + (deps.limitMs ?? LIMIT_MS);
  let steady = 0;
  for (;;) {
    const service = serviceState(env);
    const now = git(folder, ['rev-parse', 'HEAD'], env);
    steady = service === 'active' && now === commit ? steady + 1 : 0;
    if (steady === STEADY_CHECKS || Date.now() >= until) return { ok: steady === STEADY_CHECKS, service, now };
    await new Promise((resolve) => setTimeout(resolve, deps.pollMs ?? POLL_MS));
  }
}

// The command that deploys the commit the folder held before; null when that commit is still there.
function undoCommand(plan, now) {
  if (now === plan.before) return null;
  return `ignite deploy ${plan.before} --deploy-folder ${quote(plan.deployFolder)} --installation ${quote(plan.installation)}`;
}

// One line per deploy that ran the script. A line that cannot be written is a warning, never the
// deploy's outcome. Returns the log file, or null when the line was not written.
function logDeploy(plan, seen, reason, err) {
  const entry = {
    time: new Date().toISOString(),
    commitBefore: plan.before,
    commitAsked: plan.commit,
    commitAfter: seen.now,
    deployFolder: plan.deployFolder,
    outcome: reason ? 'failed' : 'ok',
    ...(reason && { reason }),
  };
  try {
    fs.mkdirSync(path.dirname(plan.log), { recursive: true });
    fs.appendFileSync(plan.log, `${JSON.stringify(entry)}\n`);
    return plan.log;
  } catch (error) {
    err(`warning: this deploy was not written to the deploy log ${plan.log} (${error.code || error.message}).\n`);
    return null;
  }
}

function failure(reason, plan, seen, env, log) {
  const undo = undoCommand(plan, seen.now);
  const journal = spawnSync('journalctl', ['--user', '-u', UNIT, '-n', String(JOURNAL_LINES), '--no-pager'], { encoding: 'utf8', env });
  return [
    `ignite deploy failed: ${reason}`,
    `Commit before  ${plan.before}`,
    `Commit now     ${seen.now ?? 'unreadable'}`,
    `Service        ${UNIT} ${seen.service}`,
    `Last ${JOURNAL_LINES} journal lines:`,
    (journal.stdout || '').trimEnd() || `(none: journalctl answered ${journal.error ? journal.error.message : `exit ${journal.status}`})`,
    'A turn that was in progress was left running.',
    ...(log ? [`Deploy log     ${log}`] : []),
    ...(undo ? [`to undo: ${undo}`] : []),
    '',
  ].join('\n');
}

async function run(argv, flags, deps = {}, resolveInstallation) {
  const out = deps.stdout || ((text) => process.stdout.write(text));
  const err = deps.stderr || ((text) => process.stderr.write(text));
  if (flags.help) { out(HELP); return 0; }
  const opts = parse(argv);
  if (flags.agent) refuse('--agent is not a deploy option: the service serves every agent of the installation');
  const platform = deps.platform || process.platform;
  if (platform !== 'linux') {
    refuse(`ignite deploy runs on Linux only: the waking service is a systemd user service, and this system is ${platform}.`);
  }
  const env = deps.env || process.env;
  let installation;
  try { installation = resolveInstallation(); } catch (error) { refuse(error.message); }
  const unit = installedUnit(env);
  if (unit.installation && unit.installation !== installation && !flags.installation) {
    refuse(`the installed service serves installation ${unit.installation}, and this command resolved ${installation}.\nTo deploy the service as it is: ignite deploy --installation ${quote(unit.installation)}\nTo make the service serve the other one: ignite deploy --installation ${quote(installation)}`);
  }
  const target = deployFolder(opts, env, unit);
  const before = git(target.folder, ['rev-parse', 'HEAD'], env);
  if (!before) refuse(`the deploy folder ${target.folder} (from ${target.source}) is not a git worktree with a commit checked out.`);
  const source = deps.sourceDir || __dirname;
  const asked = opts.commit ?? git(source, ['rev-parse', 'HEAD'], env);
  if (!asked) refuse(`no default commit: ${source} is not inside a git repository.\nName the commit: ignite deploy COMMIT`);
  const commit = git(target.folder, ['rev-parse', '--verify', '--quiet', `${asked}^{commit}`], env);
  if (!commit) refuse(`commit ${asked} is not known in the deploy folder ${target.folder}.\nFetch it there, or name a commit that folder has.`);

  const plan = {
    dryRun: opts.dryRun,
    commit,
    installation,
    deployFolder: target.folder,
    deployFolderSource: target.source,
    command: `RBTV_DEPLOY=${quote(target.folder)} RBTV_INSTALLATION=${quote(installation)} bash ${quote(SCRIPT)} ${commit}`,
    log: path.join(runtimeFolder(installation), LOG_NAME),
    before,
    now: null,
    service: null,
    undo: null,
  };
  const resolved = [
    `Commit         ${commit} (${opts.commit ? `given as ${opts.commit}` : `HEAD of the repository holding ${source}`})`,
    `Installation   ${installation}`,
    `Deploy folder  ${target.folder} (from ${target.source})`,
  ];
  if (opts.dryRun) {
    out(flags.json ? `${JSON.stringify(plan)}\n` : [
      'ignite deploy — dry run, nothing ran',
      '',
      ...resolved,
      `Commit there   ${before}`,
      `Would run      ${plan.command}`,
      `Would log to   ${plan.log}`,
      '',
      `The script checks the deploy folder out at the commit, rewrites the unit ${UNIT}`,
      'and restarts it for every agent of the installation. A turn in progress is left running.',
      '',
    ].join('\n'));
    return 0;
  }

  const script = spawnSync('bash', [SCRIPT, commit], {
    encoding: 'utf8', env: { ...env, RBTV_DEPLOY: target.folder, RBTV_INSTALLATION: installation },
  });
  err(`${script.stdout || ''}${script.stderr || ''}`);
  const failed = (reason, seen) => {
    err(failure(reason, plan, seen, env, logDeploy(plan, seen, reason, err)));
    return 1;
  };
  if (script.error || script.status !== 0) {
    const seen = { now: git(target.folder, ['rev-parse', 'HEAD'], env), service: serviceState(env) };
    return failed(`deploy.sh ${script.error ? `did not run: ${script.error.message}` : `exited ${script.status}`}.`, seen);
  }
  const seen = await settle(target.folder, commit, env, deps);
  if (!seen.ok) return failed(`the service did not stay active at ${commit} within ${(deps.limitMs ?? LIMIT_MS) / 1000} seconds.`, seen);
  const log = logDeploy(plan, seen, null, err);
  const undo = undoCommand(plan, seen.now);
  out(flags.json ? `${JSON.stringify({ ...plan, log, now: seen.now, service: seen.service, undo })}\n` : [
    'ignite deploy — done',
    '',
    ...resolved,
    `Commit before  ${before}`,
    `Commit now     ${seen.now}`,
    `Service        ${UNIT} ${seen.service}`,
    '',
    'A turn that was in progress was left running: the restarted service takes it over',
    'and starts no second one.',
    `Follow the service: journalctl --user -u ${UNIT} -f`,
    ...(log ? [`Deploy log     ${log}`] : []),
    ...(undo ? [`to undo: ${undo}`] : []),
    '',
  ].join('\n'));
  return 0;
}

module.exports = { run, HELP };

'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-secret-add-cage.out');
fs.writeFileSync(outPath, '');

const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath, parseServiceSeatPath } = require('../../seat-identity/seat-folder');
const {
  makeWorkspace, baseEnv, bootDaemon, stopDaemon, freePort, IGNITE_SRC,
} = require('../../../cli/probes/lib/fixtures');

const PROFILES = path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml');
const TEAM_KIT = path.join(IGNITE_SRC, 'team-kit');
const DUMMY = 'dummy-secret-add2-cage-e7f3a9c';
const NAME = 'TEST_SECRET_ADD2_CAGE';

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function shippedSandbox() {
  const cfg = yaml.load(fs.readFileSync(PROFILES, 'utf8'));
  if (!Array.isArray(cfg?.cage?.MasterBinds)) {
    throw new Error('cage.MasterBinds absent from ' + PROFILES);
  }
  return { SeatBinds: cfg.cage.SeatBinds, MasterBinds: cfg.cage.MasterBinds };
}

function inCage(seatDir, flags, script, extraEnv) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  const env = { ...process.env, ...(extraEnv || {}) };
  delete env.TMUX_PANE;
  delete env.TMUX;
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'], timeout: 45000, encoding: 'utf8',
      env,
    });
    return { exit: 0, stdout, stderr: '' };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stdout: (err.stdout || '').toString(),
      stderr: (err.stderr || '').toString(),
    };
  }
}

function pythonScan(roots, needle) {
  const hits = [];
  for (const root of roots) {
    if (!root || !fs.existsSync(root)) continue;
    const st = fs.statSync(root);
    if (st.isFile()) {
      try {
        if (fs.readFileSync(root, 'utf8').includes(needle)) hits.push(root);
      } catch {}
      continue;
    }
    const walk = (dir) => {
      let ents;
      try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
      for (const e of ents) {
        if (e.name === '.git' || e.name === 'node_modules') continue;
        const p = path.join(dir, e.name);
        if (e.isDirectory()) walk(p);
        else {
          try {
            if (fs.readFileSync(p, 'utf8').includes(needle)) hits.push(p);
          } catch {}
        }
      }
    };
    walk(root);
  }
  return hits;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: SCRATCH daemon (working-tree JS, not the systemd unit) + production composeCageFor MasterBinds; scratch workspace under os.tmpdir(); never the live .env');

  const port = await freePort();
  const ws = makeWorkspace('secret-add2-cage');
  const envPath = path.join(ws.workspaceRoot, '.rbtv', 'config', '.env');
  fs.mkdirSync(path.dirname(envPath), { recursive: true });
  fs.writeFileSync(envPath, '# fixture — no real secrets\nKEEP_ME=1\n', 'utf8');
  fs.writeFileSync(path.join(ws.workspaceRoot, 'rbtv.json'),
    JSON.stringify({ env_file: '.rbtv/config/.env' }), 'utf8');

  const goalDir = path.join(ws.workspaceRoot, '.rbtv', 'goals', 'scratch-secret-add2');
  const masterDir = path.join(goalDir, 'seats', 'goal-master');
  fs.mkdirSync(masterDir, { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(masterDir, 'seat.md'),
    '---\nseat: goal-master\nread-root: true\nbus-write: true\ngateway-env: true\n---\nbriefing\n');

  const kitDir = path.join(ws.workspaceRoot, 'kit');
  fs.mkdirSync(kitDir, { recursive: true });
  // ⚠ THE STAND-IN KIT CARRIES coord.py'S LOADED SIBLINGS TOO. The move-only split
  // [D23, T4-R12] put most of the product in the files named by coord.py's own SPLIT_MODULES
  // tuple, and coord.py loads them from its OWN directory — a kit missing one dies at load with
  // FileNotFoundError before any refusal under test is reached. Derived from the tuple, so the
  // next split file arrives here for free.
  const splitModules = ((fs.readFileSync(path.join(TEAM_KIT, 'coord.py'), 'utf8')
    .match(/SPLIT_MODULES = \(([\s\S]*?)\)/) || [, ''])[1].match(/"([a-z_]+)"/g) || [])
    .map((q) => `${q.replace(/"/g, '')}.py`);
  for (const f of ['coord.py', 'gateway_client.py', 'budget.py', ...splitModules]) {
    fs.copyFileSync(path.join(TEAM_KIT, f), path.join(kitDir, f));
  }

  const drop = path.join(ws.workspaceRoot, 'drop-key.txt');
  fs.writeFileSync(drop, DUMMY + '\n', 'utf8');
  const pkg = path.join(ws.workspaceRoot, 'pkg');
  fs.mkdirSync(path.join(pkg, 'coordination'), { recursive: true });

  const env = baseEnv(ws, port);
  const d = await bootDaemon(env);
  if (!d.listening) {
    check('scratch daemon booted', false, `listening=${d.listening} timedOut=${d.timedOut} exit=${d.exitCode}`);
    await stopDaemon(d);
    process.exit(1);
  }
  check('scratch daemon booted (working-tree JS, not systemd)', true, `port=${port}`);

  const sandbox = shippedSandbox();
  const parsed = parseSeatPath(masterDir) || parseServiceSeatPath(masterDir);
  const flags = composeCageFor(sandbox, parsed, masterDir, `127.0.0.1:${port}`);
  const cageEnv = {
    COORD_AGENT: 'goal-master',
    IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`,
    IGNITE_SENDER_TOKEN: ws.AGENT_TOKEN,
  };
  delete cageEnv.TMUX_PANE;
  delete cageEnv.TMUX;

  const script = [
    `unset TMUX_PANE TMUX`,
    `export COORD_AGENT=goal-master`,
    `export IGNITE_GATEWAY_ADDR=127.0.0.1:${port}`,
    `export IGNITE_SENDER_TOKEN='${ws.AGENT_TOKEN}'`,
    `python3 ${kitDir}/coord.py --package ${pkg} secret-add ${NAME} --from-file ${drop}`,
  ].join('; ');

  const ran = inCage(masterDir, flags, script, cageEnv);
  const combined = (ran.stdout || '') + (ran.stderr || '');
  const envText = fs.readFileSync(envPath, 'utf8');
  check('1. caged secret-add lands dummy key, drop gone, exit 0, value absent from output',
    ran.exit === 0
      && envText.includes(NAME + '=' + DUMMY)
      && !fs.existsSync(drop)
      && !combined.includes(DUMMY)
      && combined.includes(`appended ${NAME}`),
    `exit=${ran.exit}\nstdout=${JSON.stringify(ran.stdout)}\nstderr=${JSON.stringify(ran.stderr)}\nenv_has=${envText.includes(NAME + '=')} drop_gone=${!fs.existsSync(drop)}`);

  const direct = inCage(masterDir, flags,
    `echo DIRECT_APPEND=1 >> ${envPath}; echo EXIT:$?`, cageEnv);
  const afterDirect = fs.readFileSync(envPath, 'utf8');
  check('2. in-cage direct append to env path does not land',
    !afterDirect.includes('DIRECT_APPEND=1')
      && /EXIT:1|Read-only file system|EROFS|Permission denied|No such file/i.test((direct.stderr || '') + (direct.stdout || '')),
    `exit=${direct.exit} stdout=${JSON.stringify((direct.stdout || '').trim())} stderr=${JSON.stringify((direct.stderr || '').trim())} host_has_direct=${afterDirect.includes('DIRECT_APPEND')}`);

  const dropW = path.join(ws.workspaceRoot, 'drop-worker.txt');
  fs.writeFileSync(dropW, DUMMY + '\n', 'utf8');
  const workerScript = [
    `unset TMUX_PANE TMUX`,
    `export COORD_AGENT=crashy`,
    `export IGNITE_GATEWAY_ADDR=127.0.0.1:${port}`,
    `export IGNITE_SENDER_TOKEN='${ws.AGENT_TOKEN}'`,
    `python3 ${kitDir}/coord.py --package ${pkg} secret-add TEST_SECRET_ADD2_WORKER --from-file ${dropW}`,
  ].join('; ');
  const w = inCage(masterDir, flags, workerScript, { ...cageEnv, COORD_AGENT: 'crashy' });
  check('3a. worker refused [coord role gate], drop left',
    w.exit === 2 && /Workers cannot add secrets/.test((w.stdout || '') + (w.stderr || ''))
      && fs.existsSync(dropW) && !((w.stdout || '') + (w.stderr || '')).includes(DUMMY),
    `exit=${w.exit}\n${((w.stdout || '') + (w.stderr || '')).trim()}`);

  const dropAs = path.join(ws.workspaceRoot, 'drop-as.txt');
  fs.writeFileSync(dropAs, DUMMY + '\n', 'utf8');
  const asScript = [
    `unset TMUX_PANE TMUX`,
    `export COORD_AGENT=crashy`,
    `python3 ${kitDir}/coord.py --package ${pkg} --as goal-master secret-add TEST_SECRET_ADD2_AS --from-file ${dropAs}`,
  ].join('; ');
  const a = inCage(masterDir, flags, asScript, { ...cageEnv, COORD_AGENT: 'crashy' });
  check('3b. uncorroborated --as master refused [coord identity], drop left',
    a.exit === 2 && /you claimed 'goal-master' \(--as\)/.test((a.stdout || '') + (a.stderr || ''))
      && fs.existsSync(dropAs),
    `exit=${a.exit}\n${((a.stdout || '') + (a.stderr || '')).trim()}`);

  const goalsDrop = path.join(ws.workspaceRoot, '.rbtv', 'goals', 'g', 'mailbox.txt');
  fs.mkdirSync(path.dirname(goalsDrop), { recursive: true });
  fs.writeFileSync(goalsDrop, DUMMY + '\n', 'utf8');
  const gScript = [
    `unset TMUX_PANE TMUX`,
    `export COORD_AGENT=goal-master`,
    `export IGNITE_GATEWAY_ADDR=127.0.0.1:${port}`,
    `export IGNITE_SENDER_TOKEN='${ws.AGENT_TOKEN}'`,
    `python3 ${kitDir}/coord.py --package ${pkg} secret-add TEST_SECRET_ADD2_GOALS --from-file ${goalsDrop}`,
  ].join('; ');
  const g = inCage(masterDir, flags, gScript, cageEnv);
  check('3c. drop under .rbtv/goals/ refused [coord input], drop left',
    g.exit === 2 && /\.rbtv\/goals\//.test((g.stdout || '') + (g.stderr || ''))
      && fs.existsSync(goalsDrop),
    `exit=${g.exit}\n${((g.stdout || '') + (g.stderr || '')).trim()}`);

  const dropDup = path.join(ws.workspaceRoot, 'drop-dup.txt');
  fs.writeFileSync(dropDup, DUMMY + '\n', 'utf8');
  const dupScript = [
    `unset TMUX_PANE TMUX`,
    `export COORD_AGENT=goal-master`,
    `export IGNITE_GATEWAY_ADDR=127.0.0.1:${port}`,
    `export IGNITE_SENDER_TOKEN='${ws.AGENT_TOKEN}'`,
    `python3 ${kitDir}/coord.py --package ${pkg} secret-add ${NAME} --from-file ${dropDup}`,
  ].join('; ');
  const dup = inCage(masterDir, flags, dupScript, cageEnv);
  check('3d. existing NAME refused [coord state], drop left',
    dup.exit === 2 && /already exists/.test((dup.stdout || '') + (dup.stderr || ''))
      && fs.existsSync(dropDup)
      && !((dup.stdout || '') + (dup.stderr || '')).includes(DUMMY),
    `exit=${dup.exit}\n${((dup.stdout || '') + (dup.stderr || '')).trim()}`);

  const cmdOut = path.join(ws.tmp, 'cmd.out');
  const cmdErr = path.join(ws.tmp, 'cmd.err');
  fs.writeFileSync(cmdOut, ran.stdout || '');
  fs.writeFileSync(cmdErr, ran.stderr || '');
  const daemonLog = path.join(ws.tmp, 'daemon.log');
  fs.writeFileSync(daemonLog, (d.log && d.log()) || '');
  const daemonErr = path.join(ws.tmp, 'daemon.err');
  fs.writeFileSync(daemonErr, (d.errLog && d.errLog()) || '');
  const scanRoots = [cmdOut, cmdErr, daemonLog, daemonErr, path.join(pkg, 'coordination')];
  const pyHits = pythonScan(scanRoots, DUMMY).filter((p) => path.resolve(p) !== path.resolve(envPath));
  let grepHits = [];
  try {
    const g = execFileSync('grep', ['-R', '-l', '--binary-files=without-match', DUMMY, ...scanRoots.filter((p) => fs.existsSync(p))],
      { encoding: 'utf8' });
    grepHits = g.split('\n').filter(Boolean).filter((p) => path.resolve(p) !== path.resolve(envPath));
  } catch (err) {
    if (err.status !== 1) throw err;
  }
  check('4. log-clean: dummy VALUE zero hits outside env file (python walk + grep)',
    pyHits.length === 0 && grepHits.length === 0,
    `python=${JSON.stringify(pyHits)} grep=${JSON.stringify(grepHits)}`);

  await stopDaemon(d);
  try { fs.rmSync(ws.tmp, { recursive: true, force: true }); } catch {}

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`RESULT: ${failed.length ? 'FAIL' : 'PASS'} — ${checks.length - failed.length}/${checks.length} checks`);
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(failed.length ? 1 : 0);
}

main().catch(async (err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(1);
});

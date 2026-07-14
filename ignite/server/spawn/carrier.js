'use strict';

const { spawn, execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {
  SpawnError,
  E_SYSTEMD_NOT_AVAILABLE,
  E_CARRIER_FAILED,
} = require('./errors');

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true, mode: 0o700 });
}

function generateSessionId() {
  return crypto.randomUUID();
}

function systemdAvailable(userManager = true) {
  try {
    const flag = userManager ? '--user' : '--system';
    execFileSync('systemctl', [flag, 'is-system-running'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function selectCarrier(configCarrier, userManager = true) {
  if (configCarrier === 'systemd') {
    if (!systemdAvailable(userManager)) {
      throw new SpawnError(E_SYSTEMD_NOT_AVAILABLE, 'systemd carrier requested but user manager is not available', {});
    }
    return 'systemd';
  }
  if (configCarrier === 'setsid') return 'setsid';
  // auto
  return systemdAvailable(userManager) ? 'systemd' : 'setsid';
}

function capToProperty(key, value) {
  switch (key) {
    case 'memory_max': return `MemoryMax=${value}`;
    case 'cpu_quota': return `CPUQuota=${value}`;
    case 'runtime_max': return `RuntimeMaxSec=${value}`;
    case 'tasks_max': return `TasksMax=${String(value)}`;
    default: return null;
  }
}

function sandboxToProperty(key, value) {
  switch (key) {
    case 'ProtectSystem': return `ProtectSystem=${value}`;
    case 'PrivateTmp': return `PrivateTmp=${value ? 'yes' : 'no'}`;
    case 'NoNewPrivileges': return `NoNewPrivileges=${value ? 'yes' : 'no'}`;
    case 'ReadWritePaths': {
      const arr = Array.isArray(value) ? value : [value];
      return arr.map((p) => `ReadWritePaths=${p}`);
    }
    default: return null;
  }
}

function buildSystemdRunArgs({ sessionId, argv, workdir, logPath, caps, sandbox, envFile, userManager = true }) {
  const unitName = `rbtv-worker-${sessionId}`;
  const args = [
    userManager ? '--user' : '--system',
    '--unit', unitName,
    '--collect',
    '--property', `WorkingDirectory=${workdir}`,
    '--property', `StandardOutput=append:${logPath}`,
    '--property', `StandardError=append:${logPath}`,
  ];

  for (const [key, value] of Object.entries(caps || {})) {
    if (value === undefined || value === null) continue;
    const prop = capToProperty(key, value);
    if (prop) args.push('--property', prop);
  }

  for (const [key, value] of Object.entries(sandbox || {})) {
    if (value === undefined || value === null) continue;
    const prop = sandboxToProperty(key, value);
    if (prop) {
      if (Array.isArray(prop)) {
        for (const p of prop) args.push('--property', p);
      } else {
        args.push('--property', prop);
      }
    }
  }

  if (envFile) {
    args.push('--property', `EnvironmentFile=${envFile}`);
  }

  args.push('--');
  for (const a of argv) args.push(a);

  return { args, unitName };
}

function spawnSystemd({ sessionId, argv, workdir, logPath, caps, sandbox, envFile, userManager = true }, logger = null) {
  ensureDir(path.dirname(logPath));
  const { args, unitName } = buildSystemdRunArgs({ sessionId, argv, workdir, logPath, caps, sandbox, envFile, userManager });

  if (logger) logger({ level: 'info', message: 'systemd-run', args });

  const proc = spawn('systemd-run', args, { detached: false, stdio: ['ignore', 'pipe', 'pipe'] });
  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('error', (err) => {
      reject(new SpawnError(E_CARRIER_FAILED, `systemd-run spawn error: ${err.message}`, { carrier: 'systemd', unitName }));
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new SpawnError(E_CARRIER_FAILED, `systemd-run failed (exit ${code}): ${stderr || stdout}`, { carrier: 'systemd', unitName, exitCode: code }));
        return;
      }
      // systemd-run on success prints something like "Running as unit: rbtv-worker-xxx.service"
      resolve({ carrier: 'systemd', unitName, sessionId, stdout, stderr });
    });
  });
}

function spawnSetsid({ sessionId, argv, workdir, logPath }, logger = null) {
  ensureDir(path.dirname(logPath));

  const out = fs.openSync(logPath, 'a', 0o600);
  const err = fs.openSync(logPath, 'a', 0o600);

  if (logger) logger({ level: 'info', message: 'setsid spawn', argv, workdir, logPath });

  const proc = spawn(argv[0], argv.slice(1), {
    cwd: workdir,
    detached: true,
    stdio: ['ignore', out, err],
  });

  proc.unref();

  return new Promise((resolve, reject) => {
    proc.on('error', (err) => {
      try { fs.closeSync(out); } catch {}
      try { fs.closeSync(err); } catch {}
      reject(new SpawnError(E_CARRIER_FAILED, `setsid spawn error: ${err.message}`, { carrier: 'setsid' }));
    });

    // Give the child a moment to fork; if it exits immediately, report failure.
    setImmediate(() => {
      if (proc.exitCode !== null) {
        try { fs.closeSync(out); } catch {}
        try { fs.closeSync(err); } catch {}
        reject(new SpawnError(E_CARRIER_FAILED, `setsid process exited immediately with code ${proc.exitCode}`, { carrier: 'setsid', exitCode: proc.exitCode }));
        return;
      }
      resolve({ carrier: 'setsid', pid: proc.pid, sessionId });
    });
  });
}

function systemctlShow(unitName, userManager = true) {
  try {
    const flag = userManager ? '--user' : '--system';
    const out = execFileSync('systemctl', [flag, 'show', '--property=ExecMainPID,ExecMainStatus,Result,ActiveState,SubState', unitName], { encoding: 'utf8', timeout: 10000 });
    const props = {};
    for (const line of out.split('\n')) {
      const idx = line.indexOf('=');
      if (idx > 0) props[line.slice(0, idx)] = line.slice(idx + 1);
    }
    return props;
  } catch (err) {
    return { error: err.message };
  }
}

function systemctlIsActive(unitName, userManager = true) {
  try {
    const flag = userManager ? '--user' : '--system';
    execFileSync('systemctl', [flag, 'is-active', unitName], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function systemdStatus(unitName, userManager = true) {
  const show = systemctlShow(unitName, userManager);
  const active = systemctlIsActive(unitName, userManager);
  return {
    carrier: 'systemd',
    unitName,
    active,
    pid: show.ExecMainPID ? parseInt(show.ExecMainPID, 10) || null : null,
    exitCode: show.ExecMainStatus ? parseInt(show.ExecMainStatus, 10) : null,
    result: show.Result || null,
    state: show.ActiveState || null,
    subState: show.SubState || null,
  };
}

function setsidStatus(pid, pidStarttime = null) {
  // pidStarttime guard against PID reuse is optional here; caller supplies if known.
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    // starttime is field 22 (1-indexed). comm (field 2) may contain spaces AND parens,
    // so anchor on the LAST ')' and index by field position from there:
    // after ") ", the tokens are field 3 (state), 4, ...; starttime (field 22) is index 19.
    const rparen = stat.lastIndexOf(')');
    const rest = rparen >= 0 ? stat.slice(rparen + 2).trim().split(/\s+/) : [];
    const starttime = rest.length > 19 ? parseInt(rest[19], 10) : null;
    return {
      carrier: 'setsid',
      pid,
      active: true,
      pidStarttime: starttime,
    };
  } catch {
    return { carrier: 'setsid', pid, active: false, pidStarttime: null };
  }
}

function killSystemd(unitName, graceSeconds = 10, userManager = true, logger = null) {
  return new Promise((resolve) => {
    const flag = userManager ? '--user' : '--system';
    if (logger) logger({ level: 'info', message: 'systemd kill SIGTERM', unitName });
    try {
      execFileSync('systemctl', [flag, 'kill', '--signal=SIGTERM', unitName], { stdio: 'ignore', timeout: 10000 });
    } catch {}

    const deadline = Date.now() + graceSeconds * 1000;
    const timer = setInterval(() => {
      if (!systemctlIsActive(unitName, userManager)) {
        clearInterval(timer);
        resolve({ killed: true, signal: 'SIGTERM' });
        return;
      }
      if (Date.now() >= deadline) {
        clearInterval(timer);
        if (logger) logger({ level: 'info', message: 'systemd kill SIGKILL', unitName });
        try {
          execFileSync('systemctl', [flag, 'kill', '--signal=SIGKILL', unitName], { stdio: 'ignore', timeout: 10000 });
        } catch {}
        resolve({ killed: true, signal: 'SIGKILL' });
      }
    }, 200);
  });
}

function killSetsid(pid, graceSeconds = 10, logger = null) {
  return new Promise((resolve) => {
    if (logger) logger({ level: 'info', message: 'setsid kill SIGTERM', pid });
    try {
      process.kill(-pid, 'SIGTERM');
    } catch {}

    const deadline = Date.now() + graceSeconds * 1000;
    const timer = setInterval(() => {
      try {
        process.kill(-pid, 0);
      } catch {
        clearInterval(timer);
        resolve({ killed: true, signal: 'SIGTERM' });
        return;
      }
      if (Date.now() >= deadline) {
        clearInterval(timer);
        if (logger) logger({ level: 'info', message: 'setsid kill SIGKILL', pid });
        try {
          process.kill(-pid, 'SIGKILL');
        } catch {}
        resolve({ killed: true, signal: 'SIGKILL' });
      }
    }, 200);
  });
}

function listSystemdUnits(prefix = 'rbtv-worker-', userManager = true) {
  try {
    const flag = userManager ? '--user' : '--system';
    const out = execFileSync('systemctl', [flag, 'list-units', '--type=service', '--no-legend', '--no-pager', `${prefix}*`], { encoding: 'utf8', timeout: 10000 });
    const units = [];
    for (const line of out.split('\n')) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 5 && parts[0].startsWith(prefix)) {
        units.push({ unitName: parts[0], load: parts[1], active: parts[2], sub: parts[3], description: parts.slice(4).join(' ') });
      }
    }
    return units;
  } catch (err) {
    return [];
  }
}

module.exports = {
  ensureDir,
  generateSessionId,
  systemdAvailable,
  selectCarrier,
  buildSystemdRunArgs,
  spawnSystemd,
  spawnSetsid,
  systemdStatus,
  setsidStatus,
  killSystemd,
  killSetsid,
  listSystemdUnits,
};

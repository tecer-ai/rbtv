'use strict';

const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { requirePythonCmd } = require('../runtime/python-cmd');

const COORD_PY = path.join(__dirname, '..', 'coord', 'coord.py');

function finishOnCompletion(goalFolder, { spawn = spawnSync } = {}) {
  if (!goalFolder) return { fired: false, skipped: 'no-folder' };
  const env = { ...process.env };
  delete env.COORD_AGENT;
  const r = spawn(requirePythonCmd(), [
    COORD_PY, '--package', goalFolder, '--as', 'ignite-daemon', 'finish-on-completion',
  ], { encoding: 'utf8', timeout: 30000, env });
  const detail = `${r.stdout || ''}${r.stderr || ''}`;
  if (r.status === 0) return { fired: true, detail };
  return { fired: false, status: r.status, detail };
}

module.exports = { finishOnCompletion, COORD_PY };

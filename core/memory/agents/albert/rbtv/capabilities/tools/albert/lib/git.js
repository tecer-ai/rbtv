'use strict';

function git(workspace, args, input, statuses = [0]) {
  const result = require('node:child_process').spawnSync('git', ['--literal-pathspecs', '-C', workspace, ...args], {
    input,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30_000,
    maxBuffer: 8 * 1024 * 1024,
  });
  if (result.error || !statuses.includes(result.status)) {
    const error = new Error(`git ${args[0]} failed`);
    error.result = result;
    throw error;
  }
  return result;
}

function commitForRun(workspace, runId) {
  const result = git(workspace, ['log', '-1', '--grep', runId, '--format=%H']);
  const hash = result.stdout.trim();
  return hash || null;
}

module.exports = { git, commitForRun };

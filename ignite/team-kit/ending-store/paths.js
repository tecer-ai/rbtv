'use strict';

const path = require('node:path');

const RUNTIME_REL = path.join('.rbtv', 'runtime', 'team-kit');
const STORE_FILENAME = 'heart.db';

function endingStorePath(workspaceRoot) {
  if (!workspaceRoot) throw new Error('endingStorePath requires workspaceRoot');
  return path.resolve(workspaceRoot, RUNTIME_REL, STORE_FILENAME);
}

function endingStoreDir(workspaceRoot) {
  return path.dirname(endingStorePath(workspaceRoot));
}

module.exports = {
  RUNTIME_REL,
  STORE_FILENAME,
  endingStorePath,
  endingStoreDir,
};

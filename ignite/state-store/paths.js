'use strict';

const path = require('node:path');

const RUNTIME_IGNITE = path.join('.rbtv', 'runtime', 'ignite');
const STORE_FILENAME = 'heart.db';

function endingStorePath(workspaceRoot) {
  if (!workspaceRoot) throw new Error('endingStorePath requires workspaceRoot');
  return path.resolve(workspaceRoot, RUNTIME_IGNITE, STORE_FILENAME);
}

function endingStoreDir(workspaceRoot) {
  return path.dirname(endingStorePath(workspaceRoot));
}

module.exports = {
  RUNTIME_IGNITE,
  STORE_FILENAME,
  endingStorePath,
  endingStoreDir,
};

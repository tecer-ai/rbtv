'use strict';

const lib = require('../../../../memory/capabilities/tools/memory/lib/index.js');

module.exports = {
  NOFOLLOW: lib.NOFOLLOW,
  safeWritePath: lib.safeWritePath,
  writeRoot: lib.writeRoot,
  runtimeFolder: lib.runtimeFolder,
  acquireMemoryLock: lib.acquireMemoryLock,
  withMemoryLock: lib.withMemoryLock,
};

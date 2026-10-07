'use strict';

// One short publication lock per installation. Callbacks are synchronous: never
// keep the lock while awaiting a model, Slack, or other outside work.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { randomUUID } = require('node:crypto');

const NOFOLLOW = fs.constants.O_NOFOLLOW || 0;
const sleep = new Int32Array(new SharedArrayBuffer(4));
// Windows answers EPERM, not EEXIST or ENOENT, for a lock file another process has released and
// that is not yet gone from the folder: the lock is still taken for that instant.
const releasing = (error) => process.platform === 'win32' && error.code === 'EPERM';

function safeWritePath(root, file) {
  const relative = path.relative(path.resolve(root), path.resolve(file));
  if (path.isAbsolute(relative) || relative === '..' || relative.startsWith(`..${path.sep}`)) {
    throw new Error('memory write outside installation');
  }
  // lstat also identifies Windows junctions (directory reparse points).
  const absolute = path.resolve(file);
  let current = path.parse(absolute).root;
  for (const part of absolute.slice(current.length).split(path.sep)) {
    current = path.join(current, part);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error('memory writes cannot traverse symlinks or junctions');
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return absolute;
}

function writeRoot(file) {
  let dir = path.dirname(path.resolve(file));
  while (path.dirname(dir) !== dir) {
    if (path.basename(dir) === '.rbtv') return path.dirname(dir);
    dir = path.dirname(dir);
  }
  // Standalone boards used outside an installed agent share their folder lock.
  return path.dirname(path.resolve(file));
}

// Where Ignite keeps its operational data in an installation: `.rbtv/runtime/<component>/`.
function runtimeFolder(workspace) {
  return path.join(workspace, '.rbtv', 'runtime', 'ignite');
}

function acquireMemoryLock(workspace) {
  const file = safeWritePath(workspace, path.join(runtimeFolder(workspace), 'memory.lock'));
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const deadline = Date.now() + 5000;
  const owner = JSON.stringify({ token: randomUUID(), pid: process.pid, hostname: os.hostname() });
  for (;;) {
    let fd;
    try { fd = fs.openSync(file, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | NOFOLLOW, 0o600); }
    catch (error) {
      if (error.code !== 'EEXIST' && !releasing(error)) throw error;
      safeWritePath(workspace, file);
      try {
        if (Date.now() - fs.statSync(file).mtimeMs > 60_000) {
          const contents = fs.readFileSync(file, 'utf8');
          let holder;
          try { holder = JSON.parse(contents); } catch { /* Unknown owners cannot be reclaimed safely. */ }
          if (holder?.hostname === os.hostname() && Number.isInteger(holder.pid) && holder.pid > 0) {
            let abandoned = false;
            try { process.kill(holder.pid, 0); }
            catch (error) { abandoned = error.code === 'ESRCH'; }
            if (abandoned && fs.readFileSync(file, 'utf8') === contents) {
              fs.unlinkSync(file);
              continue;
            }
          }
        }
      } catch (race) {
        if (race.code === 'ENOENT') continue;
        if (!releasing(race)) throw race;
      }
      if (Date.now() >= deadline) throw new Error('memory write lock busy; retry the command');
      Atomics.wait(sleep, 0, 0, 25);
      continue;
    }
    try { fs.writeFileSync(fd, owner, 'utf8'); }
    catch (error) { fs.unlinkSync(file); throw error; }
    finally { fs.closeSync(fd); }
    return () => {
      try {
        if (fs.readFileSync(file, 'utf8') === owner) fs.unlinkSync(file);
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    };
  }
}

function withMemoryLock(workspace, fn) {
  const release = acquireMemoryLock(workspace);
  try { return fn(); } finally { release(); }
}

module.exports = { NOFOLLOW, safeWritePath, writeRoot, runtimeFolder, acquireMemoryLock, withMemoryLock };

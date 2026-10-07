'use strict';

// cast — the installation a launch belongs to, and that installation's environment file.
//
// The installation is the first folder, from the launch folder upward, that holds the installer's
// record `.rbtv/config/install.json`. Its environment file is `.rbtv/config/env/.env`. A launch
// folder inside no installation has neither: nothing is read and nothing is an error.

const fs = require('fs');
const path = require('path');

const INSTALL_RECORD_REL = path.join('.rbtv', 'config', 'install.json');
const ENV_FILE_REL = path.join('.rbtv', 'config', 'env', '.env');

function installationRoot(from) {
  let dir = path.resolve(from);
  for (;;) {
    if (fs.existsSync(path.join(dir, INSTALL_RECORD_REL))) return dir;
    const up = path.dirname(dir);
    if (up === dir) return null;
    dir = up;
  }
}

// Presence only: the value is never returned. `KEY=` with nothing after it is NOT present; a
// value may sit in matching outer quotes, as the installation's other readers accept.
function envFileHasKey(root, name) {
  if (!root) return false;
  let text;
  try { text = fs.readFileSync(path.join(root, ENV_FILE_REL), 'utf8'); } catch { return false; }
  return text.split('\n').some((line) => {
    const t = line.trim();
    if (!t || t.startsWith('#')) return false;
    const eq = t.indexOf('=');
    if (eq === -1 || t.slice(0, eq).trim() !== name) return false;
    const value = t.slice(eq + 1).trim().replace(/^(["'])(.*)\1$/, '$2');
    return value !== '';
  });
}

module.exports = { INSTALL_RECORD_REL, ENV_FILE_REL, installationRoot, envFileHasKey };

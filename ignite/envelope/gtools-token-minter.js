'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFile } = require('node:child_process');

// The REAL minter `credential-broker.js#startBroker` wires in production — a thin relay to
// `gtools_mint_token.py`, which does the actual OAuth refresh via gtools' own `auth.py`. Kept
// as a separate, injectable function (not inlined into the broker) so the broker's socket/
// protocol/allow-list logic can be proven with a fixture minter that never touches a real
// account, Google, or the network — see `probes/probe-credential-broker.js`.
const MINT_SCRIPT = path.join(__dirname, 'gtools_mint_token.py');

// gtools' own OAuth libraries (google-auth, google-auth-oauthlib, …) live in ITS venv, not on
// the bare `python3` a PATH lookup would find — a bare interpreter has no `google` module and
// the mint dies `ModuleNotFoundError` before touching any account (measured, judge-deploy
// window 5). The interpreter is derived HERE, once, from the same `gtoolsRoot` the mint script
// is already given — never at the call site, and never fixed by installing packages globally.
// Falls back to the bare name only if a `gtoolsRoot` genuinely has no venv (e.g. a fixture
// tree in a probe, which never imports `google` at all), so that case is unaffected.
function gtoolsPython(gtoolsRoot) {
  const venvPython = path.join(gtoolsRoot, '.venv', 'bin', 'python3');
  return fs.existsSync(venvPython) ? venvPython : 'python3';
}

function gtoolsTokenMinter(gtoolsRoot) {
  const pythonBin = gtoolsPython(gtoolsRoot);
  return (account) => new Promise((resolve) => {
    execFile(
      pythonBin,
      [MINT_SCRIPT, '--gtools-root', gtoolsRoot, '--account', account],
      { timeout: 20000 },
      (err, stdout, stderr) => {
        if (err) {
          resolve({ ok: false, reason: `mint failed: ${String(stderr || err.message).trim().slice(0, 300)}` });
          return;
        }
        let parsed;
        try { parsed = JSON.parse(stdout); } catch (parseErr) {
          resolve({ ok: false, reason: `mint script output unparsable: ${parseErr.message}` });
          return;
        }
        if (!parsed || !parsed.access_token) {
          resolve({ ok: false, reason: 'mint script returned no access_token' });
          return;
        }
        resolve({ ok: true, accessToken: parsed.access_token, expiresAt: parsed.expiry || null });
      },
    );
  });
}

module.exports = { gtoolsTokenMinter, MINT_SCRIPT, gtoolsPython };

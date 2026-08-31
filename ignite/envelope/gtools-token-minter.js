'use strict';

const path = require('node:path');
const { execFile } = require('node:child_process');

// The REAL minter `credential-broker.js#startBroker` wires in production — a thin relay to
// `gtools_mint_token.py`, which does the actual OAuth refresh via gtools' own `auth.py`. Kept
// as a separate, injectable function (not inlined into the broker) so the broker's socket/
// protocol/allow-list logic can be proven with a fixture minter that never touches a real
// account, Google, or the network — see `probes/probe-credential-broker.js`.
const MINT_SCRIPT = path.join(__dirname, 'gtools_mint_token.py');

function gtoolsTokenMinter(gtoolsRoot) {
  return (account) => new Promise((resolve) => {
    execFile(
      'python3',
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

module.exports = { gtoolsTokenMinter, MINT_SCRIPT };

'use strict';

// One rendering path for every subcommand's gateway response, so the
// success/failure feedback bar (ADX-2/ADX-4, D21(3): "clear, unambiguous
// success/failure feedback on every run") and the --json envelope stability
// (gateway-cli-spec.md § `--json` envelope) are enforced in exactly one place
// rather than re-implemented per command.

const { exitForEnvelopeCode } = require('./errors');

// `envelope` is exactly what the gateway returned: `{ ok: true, result }` or
// `{ ok: false, error: { code, message, details? } }`. `renderSuccess(result)`
// is the command's own human-readable rendering; omit it for a bare "OK".
// Returns the process exit code for this run.
function finish(envelope, { json, renderSuccess } = {}) {
  if (json) {
    process.stdout.write(JSON.stringify(envelope) + '\n');
    return envelope.ok ? 0 : exitForEnvelopeCode(envelope.error && envelope.error.code);
  }

  if (envelope.ok) {
    if (renderSuccess) renderSuccess(envelope.result);
    else console.log('OK');
    return 0;
  }

  const e = envelope.error || {};
  console.error(`ERROR [${e.code || 'UNKNOWN'}] ${e.message || 'refused'}`);
  if (e.details) console.error(JSON.stringify(e.details));
  return exitForEnvelopeCode(e.code);
}

module.exports = { finish };

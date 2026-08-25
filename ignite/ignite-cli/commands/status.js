'use strict';

// `ignite status` — thin alias for `inspect daemon`. On transport failure
// (gateway unreachable = daemon down, because the gateway lives INSIDE the
// daemon), renders `daemon: DOWN` instead of a raw connect error.

const { CliUsageError } = require('../lib/errors');
const { finish } = require('../lib/output');

const HELP = `ignite status [--json]

  Alias for "ignite inspect daemon". Renders daemon health (or the full envelope
  with --json). On transport failure (daemon not reachable) prints "daemon: DOWN".`;

async function run(argv, ctx) {
  if (argv.length > 0) throw new CliUsageError(`status: unrecognized argument(s): ${argv.join(' ')}`);

  let envelope;
  try {
    const result = await ctx.call('inspect', { target: 'daemon' });
    envelope = result.envelope;
  } catch (err) {
    // The caller (ignite.js) throws CliTransportError on connect failure
    // (exit 5 — gateway unreachable = daemon down).
    if (err.name === 'CliTransportError') {
      if (ctx.json) {
        console.log(JSON.stringify({ ok: false, error: { code: 'DAEMON_DOWN', message: 'daemon: DOWN' } }));
      } else {
        console.log('daemon: DOWN');
      }
      return 0;
    }
    throw err;
  }

  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => console.log(JSON.stringify(result, null, 2)),
  });
}

module.exports = { HELP, run };

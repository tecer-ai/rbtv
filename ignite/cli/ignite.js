#!/usr/bin/env node
'use strict';

// The `ignite` client CLI — one subcommand per action, each a THIN WRAPPER
// over the gateway API (gateway-cli-spec.md, DEC-1 R1). It is the client for
// BOTH the owner and agents (gateway-cli-spec.md behavior row 7).
//
// ⚑ THE BOUNDARY IS THE POINT: this tree requires nothing from ../server/heart,
// ../server/spawn, ../server/spawn/config, or ../server/internal-api. Every
// command reaches the daemon ONLY through lib/gateway-client.js's HTTP call —
// never a direct store/spawn/raw-SQL call (gateway-cli-spec.md § Gateway
// Pipeline; task p4-2 Forbidden Paths).
//
// Usage: ignite <command> [...args] [--json]
// Auth/config: IGNITE_GATEWAY_ADDR, IGNITE_SENDER_TOKEN (env only — the token
// never appears in argv; see lib/config.js).

const { resolveGatewayAddr, resolveToken } = require('./lib/config');
const { callGateway } = require('./lib/gateway-client');
const { CliUsageError, CliTransportError } = require('./lib/errors');
const { takeFlag } = require('./lib/args');

const COMMANDS = {
  'add-job': require('./commands/add-job'),
  'remove-job': require('./commands/remove-job'),
  inspect: require('./commands/inspect'),
  snooze: require('./commands/snooze'),
};

function topHelp() {
  const lines = ['ignite <command> [...args] [--json]', '', 'Commands:', ''];
  for (const mod of Object.values(COMMANDS)) {
    lines.push(mod.HELP, '');
  }
  lines.push('Auth/config: IGNITE_GATEWAY_ADDR, IGNITE_SENDER_TOKEN (env only — never a flag;');
  lines.push('tokens must never appear in argv). Server resolution falls back to the');
  lines.push('workspace\'s .rbtv/modules/ignite/server.json (D27 install model).');
  return lines.join('\n');
}

// Resolved fresh on every call rather than once at startup, so a resolution
// failure surfaces at the exact call site with the command's own context —
// and so nothing is resolved at all for `--help`.
function makeCaller() {
  return (intent, payload) => {
    const addr = resolveGatewayAddr();
    const token = resolveToken();
    return callGateway({ addr, token, intent, payload });
  };
}

async function main() {
  const argv = process.argv.slice(2);
  const json = takeFlag(argv, '--json');

  if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') {
    console.log(topHelp());
    return 0;
  }

  const name = argv.shift();
  const cmd = COMMANDS[name];
  if (!cmd) {
    throw new CliUsageError(`unknown command "${name}" — run "ignite --help" for the command list`);
  }
  if (argv[0] === '--help' || argv[0] === '-h') {
    console.log(cmd.HELP);
    return 0;
  }

  return cmd.run(argv, { call: makeCaller(), json });
}

main()
  .then((code) => {
    process.exitCode = code || 0;
  })
  .catch((err) => {
    const json = process.argv.includes('--json');
    if (err instanceof CliUsageError) {
      if (json) console.log(JSON.stringify({ ok: false, error: { code: 'CLI_USAGE_ERROR', message: err.message } }));
      else console.error(`USAGE ERROR: ${err.message}`);
      process.exitCode = 2;
      return;
    }
    if (err instanceof CliTransportError) {
      if (json) console.log(JSON.stringify({ ok: false, error: { code: 'CLI_TRANSPORT_ERROR', message: err.message } }));
      else console.error(`CONNECT ERROR: ${err.message}`);
      process.exitCode = 5;
      return;
    }
    if (json) console.log(JSON.stringify({ ok: false, error: { code: 'CLI_INTERNAL_ERROR', message: err.message } }));
    else console.error(`INTERNAL CLI ERROR: ${err.stack || err.message}`);
    process.exitCode = 1;
  });

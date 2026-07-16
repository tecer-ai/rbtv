'use strict';

// `ignite inspect jobs|queue|status <id>|logs <id> [--tail <n>]` — wraps the
// `inspect` intent (four read-only targets, one gateway intent).

const { CliUsageError } = require('../lib/errors');
const { takeValue, requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite inspect jobs
ignite inspect queue
ignite inspect status <exec-id>
ignite inspect logs <exec-id> [--tail <n>]

  Read-only. Renders server state (or the full envelope with --json).`;

const TARGETS = new Set(['jobs', 'queue', 'status', 'logs']);

// A single page's line count for the (offset, limit) walk logs paging does.
// Generous but arbitrary — the server-side page bound (internal-api-contract-
// spec.md §1 inspect) governs the real ceiling; this just keeps the walk to a
// handful of round trips for an ordinary log.
const LOG_PAGE_LIMIT = 500;

function renderRows(label, rows) {
  console.log(`${label}: ${rows.length} row(s)`);
  for (const row of rows) console.log(JSON.stringify(row));
}

async function runJobsOrQueue(target, argv, ctx) {
  if (argv.length > 0) throw new CliUsageError(`inspect ${target}: unrecognized argument(s): ${argv.join(' ')}`);
  const { envelope } = await ctx.call('inspect', { target });
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => renderRows(target, result.rows || []),
  });
}

async function runStatus(argv, ctx) {
  const rawId = requirePositional(argv, 'exec-id');
  if (!/^\d+$/.test(rawId)) throw new CliUsageError('inspect status requires an integer id');
  if (argv.length > 0) throw new CliUsageError(`inspect status: unrecognized argument(s): ${argv.join(' ')}`);

  const { envelope } = await ctx.call('inspect', { target: 'status', id: rawId });
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => console.log(JSON.stringify(result)),
  });
}

async function runLogs(argv, ctx) {
  const rawId = requirePositional(argv, 'exec-id');
  if (!/^\d+$/.test(rawId)) throw new CliUsageError('inspect logs requires an integer id');

  const rawTail = takeValue(argv, '--tail');
  let tail;
  if (rawTail !== undefined) {
    if (!/^\d+$/.test(rawTail) || Number(rawTail) <= 0) throw new CliUsageError('--tail must be a positive integer');
    tail = Number(rawTail);
  }
  if (argv.length > 0) throw new CliUsageError(`inspect logs: unrecognized argument(s): ${argv.join(' ')}`);

  if (tail === undefined) {
    // No --tail: a single round trip, the server's default bounded chunk from
    // the start of the log.
    const { envelope } = await ctx.call('inspect', { target: 'logs', id: rawId });
    return finish(envelope, {
      json: ctx.json,
      renderSuccess: (result) => {
        for (const line of result.lines || []) console.log(line);
        if (result.eof === false) {
          console.log(`... more available (nextOffset=${result.nextOffset}); re-run with --tail to see the end`);
        }
      },
    });
  }

  // --tail N: the contract exposes offset/limit PAGING only, never a reverse
  // read (internal-api-contract-spec.md §1 `inspect` — "pagination, never a
  // stream handle"), so getting the LAST N lines means walking the WHOLE
  // bounded log through the gateway — one `inspect logs` call per page, never
  // a direct file/store read — and keeping only the final N lines client-side.
  let offset = 0;
  let lines = [];
  let lastEnvelope = null;
  for (;;) {
    const { envelope } = await ctx.call('inspect', { target: 'logs', id: rawId, offset, limit: LOG_PAGE_LIMIT });
    lastEnvelope = envelope;
    if (!envelope.ok) break;
    const chunk = envelope.result.lines || [];
    lines = lines.concat(chunk);
    if (envelope.result.eof || chunk.length === 0) break;
    offset = envelope.result.nextOffset;
  }

  if (!lastEnvelope.ok) return finish(lastEnvelope, { json: ctx.json });

  const tailLines = lines.slice(-tail);
  const synthEnvelope = { ok: true, result: { lines: tailLines, eof: true, tailOf: lines.length } };
  return finish(synthEnvelope, {
    json: ctx.json,
    renderSuccess: (result) => { for (const line of result.lines) console.log(line); },
  });
}

async function run(argv, ctx) {
  const target = requirePositional(argv, 'target (jobs|queue|status|logs)');
  if (!TARGETS.has(target)) {
    throw new CliUsageError(`inspect target must be jobs|queue|status|logs (got "${target}")`);
  }
  if (target === 'jobs' || target === 'queue') return runJobsOrQueue(target, argv, ctx);
  if (target === 'status') return runStatus(argv, ctx);
  return runLogs(argv, ctx);
}

module.exports = { HELP, run };

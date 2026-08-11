'use strict';

// `ignite inspect jobs|queue|status <id>|logs <id> [--tail <n>]|daemon|ticker|
// messages <id>|executions --status <s>` — wraps the `inspect` intent (read-only
// targets, one gateway intent). `messages` (cli-expansion ruling D3, ce-5) is
// execution-scoped like status/logs: the server resolves the execution's
// chain-stable thread and returns that thread's message rows, paged.
//
// `executions` (task 7.62) is the odd one out and deliberately so: it is neither a
// fixed view nor execution-scoped — it takes no id and lists the WHOLE jobs_log in
// ONE status, paged. It is the only way to ask "every failed run" or "every stalled
// worker"; every other target answers about one execution or about the fleet as a
// whole, never about a state across it.

const { CliUsageError } = require('../lib/errors');
const { takeValue, requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite inspect jobs
ignite inspect queue
ignite inspect status <exec-id>
ignite inspect logs <exec-id> [--tail <n>]
ignite inspect daemon
ignite inspect ticker
ignite inspect messages <exec-id>
ignite inspect executions --status <status> [--offset <n>] [--limit <n>]
ignite inspect executions --status <status> --tail <n>

  Read-only. Renders server state (or the full envelope with --json).
  messages:   the message rows of the execution's chain-stable thread.
  executions: every execution in one status, paged OLDEST-FIRST —
              launching|running|done|blocked|failed|stalled|killed.
              --tail <n>: the NEWEST n, plus the total, in one command.`;

const TARGETS = new Set(['jobs', 'queue', 'status', 'logs', 'daemon', 'ticker', 'messages', 'executions']);

// A single page's size for the (offset, limit) walk that `--tail` does — for
// logs, and since the executions tail, for executions too. Generous but
// arbitrary — the server-side page bound (internal-api-contract-spec.md §1
// inspect) governs the real ceiling; this just keeps the walk to a handful of
// round trips.
const PAGE_LIMIT = 500;

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
    const { envelope } = await ctx.call('inspect', { target: 'logs', id: rawId, offset, limit: PAGE_LIMIT });
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

// One line per message: msg_id, type, sender, status, created_at, and a
// truncated corpus preview — compact enough to scan a whole thread. `--json`
// stays the raw envelope (finish() renders it before this ever runs).
const CORPUS_PREVIEW_CHARS = 80;

function corpusPreview(corpus) {
  const flat = String(corpus ?? '').replace(/\s+/g, ' ').trim();
  return flat.length > CORPUS_PREVIEW_CHARS ? flat.slice(0, CORPUS_PREVIEW_CHARS - 1) + '…' : flat;
}

async function runMessages(argv, ctx) {
  const rawId = requirePositional(argv, 'exec-id');
  if (!/^\d+$/.test(rawId)) throw new CliUsageError('inspect messages requires an integer id');
  if (argv.length > 0) throw new CliUsageError(`inspect messages: unrecognized argument(s): ${argv.join(' ')}`);

  const { envelope } = await ctx.call('inspect', { target: 'messages', id: rawId });
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => {
      const rows = result.rows || [];
      console.log(`messages (thread ${result.thread}): ${rows.length} row(s)`);
      for (const m of rows) {
        console.log(`#${m.msg_id} ${m.created_at} ${m.type} from=${m.sender} status=${m.status ?? '-'} ${corpusPreview(m.corpus)}`);
      }
      if (result.eof === false) {
        console.log(`... more available (nextOffset=${result.nextOffset})`);
      }
    },
  });
}

// One line per execution, the fields an operator triaging a fleet actually scans:
// which execution, what fired it, when, and where its session went. `--json` stays
// the raw envelope (finish() renders it before this ever runs).
//
// ⚑ The CLI does NOT carry its own copy of the status enum. It forwards whatever the
// caller typed and lets the SERVER refuse it — one fewer copy of a closed set to
// drift (the enum already lives at gateway/parse.js and dispatch.js, and a third
// copy here would be guarded by nothing at the moment a caller most needs the right
// answer). The cost is one round trip on a typo; the refusal names the valid set.
function renderExecutionRow(r) {
  console.log(`#${r.exec_id} ${r.fired_at} ${r.action_type} job=${r.job_id} session=${r.session_id ?? '-'} pid=${r.pid ?? '-'} exit=${r.exit_code ?? '-'} thread=${r.thread ?? '-'}`);
}

async function runExecutions(argv, ctx) {
  const status = takeValue(argv, '--status');
  if (status === undefined) throw new CliUsageError('inspect executions requires --status <status>');

  const rawTail = takeValue(argv, '--tail');
  let tail;
  if (rawTail !== undefined) {
    if (!/^\d+$/.test(rawTail) || Number(rawTail) <= 0) throw new CliUsageError('--tail must be a positive integer');
    tail = Number(rawTail);
  }

  const payload = { target: 'executions', status };
  for (const flag of ['--offset', '--limit']) {
    const raw = takeValue(argv, flag);
    if (raw === undefined) continue;
    // --tail names a window from the END; --offset/--limit name one from the START.
    // Accepting both would silently honour one — the shape that teaches a caller a
    // flag works when it does not (parse.js's stated reason for refusing both ways).
    if (tail !== undefined) throw new CliUsageError(`inspect executions: ${flag} and --tail are mutually exclusive`);
    const key = flag.slice(2);
    if (!/^\d+$/.test(raw)) throw new CliUsageError(`${flag} must be a non-negative integer`);
    if (key === 'limit' && Number(raw) <= 0) throw new CliUsageError('--limit must be a positive integer');
    payload[key] = Number(raw);
  }
  if (argv.length > 0) throw new CliUsageError(`inspect executions: unrecognized argument(s): ${argv.join(' ')}`);

  // --tail N: the listing is ordered OLDEST-FIRST (jobs_log ORDER BY exec_id) and exposes
  // offset/limit paging only, never a reverse read — so the newest row costs blind offset
  // probes. With the envelope's `total` the last page is addressable: ask for one row to
  // learn the total, then jump to `total - N`. TWO round trips, whatever the size of the
  // set (measured on the live VPS: 25,858 `done` rows).
  //
  // A daemon predating `total` (the field ships with this change) still answers — the walk
  // below is `inspect logs --tail`'s answer to the same contract, and it is what runs against
  // an un-redeployed box. Delete it once no such daemon is left; `tailOf` is the total either
  // way.
  if (tail !== undefined) {
    const head = await ctx.call('inspect', { ...payload, offset: 0, limit: 1 });
    if (!head.envelope.ok) return finish(head.envelope, { json: ctx.json });
    const total = head.envelope.result.total;

    let rows;
    let walked = null;
    if (Number.isInteger(total)) {
      const offset = Math.max(0, total - tail);
      const page = await ctx.call('inspect', { ...payload, offset, limit: tail });
      if (!page.envelope.ok) return finish(page.envelope, { json: ctx.json });
      rows = page.envelope.result.rows || [];
    } else {
      let offset = 0;
      let all = [];
      let lastEnvelope = null;
      for (;;) {
        const { envelope } = await ctx.call('inspect', { ...payload, offset, limit: PAGE_LIMIT });
        lastEnvelope = envelope;
        if (!envelope.ok) break;
        const chunk = envelope.result.rows || [];
        all = all.concat(chunk);
        if (envelope.result.eof || chunk.length === 0) break;
        offset = envelope.result.nextOffset;
      }
      if (!lastEnvelope.ok) return finish(lastEnvelope, { json: ctx.json });
      walked = all.length;
      rows = all.slice(-tail);
    }

    const tailOf = Number.isInteger(total) ? total : walked;
    const synth = { ok: true, result: { target: 'executions', status, rows, eof: true, tailOf } };
    return finish(synth, {
      json: ctx.json,
      renderSuccess: (result) => {
        console.log(`executions (status ${result.status}): newest ${result.rows.length} of ${result.tailOf} row(s)`);
        for (const r of result.rows) renderExecutionRow(r);
      },
    });
  }

  const { envelope } = await ctx.call('inspect', payload);
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => {
      const rows = result.rows || [];
      console.log(`executions (status ${result.status}): ${rows.length} row(s)`);
      for (const r of rows) renderExecutionRow(r);
      if (result.eof === false) {
        console.log(`... more available (nextOffset=${result.nextOffset})`);
      }
    },
  });
}

async function runDaemonOrTicker(target, argv, ctx) {
  if (argv.length > 0) throw new CliUsageError(`inspect ${target}: unrecognized argument(s): ${argv.join(' ')}`);
  const { envelope } = await ctx.call('inspect', { target });
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => console.log(JSON.stringify(result, null, 2)),
  });
}

async function run(argv, ctx) {
  const target = requirePositional(argv, `target (${[...TARGETS].join('|')})`);
  if (!TARGETS.has(target)) {
    throw new CliUsageError(`inspect target must be ${[...TARGETS].join('|')} (got "${target}")`);
  }
  if (target === 'jobs' || target === 'queue') return runJobsOrQueue(target, argv, ctx);
  if (target === 'daemon' || target === 'ticker') return runDaemonOrTicker(target, argv, ctx);
  if (target === 'status') return runStatus(argv, ctx);
  if (target === 'messages') return runMessages(argv, ctx);
  if (target === 'executions') return runExecutions(argv, ctx);
  return runLogs(argv, ctx);
}

// TARGETS is exported as DATA for probe-inspect-executions.js's target-set lockstep
// check (task 7.62) — the set exists in THREE copies (here, gateway/parse.js and
// dispatch.js) and until that probe nothing compared them. Exported constants, never
// regex over source text (task 7.16's ruled construction requirement).
module.exports = { HELP, run, TARGETS };

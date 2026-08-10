'use strict';

// THE OUTBOUND REPLY LEG (chat-bridge-spec.md Behavior #3; Test Plan #4; owner
// ruling D110). The bridge's missing production DRIVER: when the agent worker
// spawned for a chat conversation finishes its turn, this leg fetches the
// worker's answer from the daemon (over the SAME narrow gateway `inspect` surface
// the rest of the bridge uses) and posts it into the mapped Slack thread via the
// bridge's existing `deliverToOwner`. It closes the loop the forward path opened.
//
// ⚑ NO NEW CAPABILITY. The driver reaches the daemon ONLY through the injected
// `forwarder.inspect` (the closed seven-intent surface, D90) — no store handle,
// no spawn path, no new intent, no new inbound listener. It is pure polling over
// `inspect ticker | status | logs` plus a call to the bridge's own delivery.
//
// ⚑ THE WATCH STATE IS DELIBERATELY NOT PERSISTED — unlike the thread map and the
// reply addresses, which DO survive a restart when `state_file` is set (chat-bridge.js
// § conversation state, owner ruling 2026-08-06). Every field in `pending` below is
// TIME-BOUND: `armedAt` bounds a 10-minute spawn wait, and `watching` holds execs
// whose turn-end we expect imminently. Restored after an arbitrary downtime those
// windows are stale — a restored `armedAt` would disarm a conversation the instant the
// bridge came back, and a restored `watching` would poll execs whose logs the retention
// sweep may already have taken. Nothing is lost by dropping them: the owner's next
// follow-up on a RESTORED conversation goes through the forward path, which re-arms
// this leg via the existing arm() call, with fresh windows. Sessions are cattle; the
// conversation is what has to survive, and it does.
//
// ⚑ `live` FLAG, NEVER `status`, is the turn-finished signal. The daemon's crash
// sweep marks EVERY exited detached (`systemd --collect`) execution `failed`, so a
// clean success is recorded `status:'failed'` (no exit-code visibility). Keying
// "turn finished" on `status === 'done'` would miss every real reply. We key on
// the `live` flag transitioning to false (dispatch.js inspect status → `live`).

const { toMrkdwn, lintMrkdwn } = require('./mrkdwn');

// ⚑ THE BRIDGE OWNS ONE REPLY CONTRACT, NOT ONE PARSER PER HARNESS (owner ruling 2026-08-10,
// chat-bridge-feedback-and-reply-contract.md decisions 5–7). Before it, extraction knew exactly
// one log shape — claude's `--output-format stream-json` — so every non-claude master profile
// (opencode `run`, kimi `--quiet`, codex `--json`) produced a log with no `result` line and every
// reply reached Slack as the bare fallback (observed live 2026-08-10 on opencode-glm-5-2).
//
// Adapting the bridge to each harness's output format is the losing end of that: the set grows,
// each addition is a new guess at where a harness hides its answer, and none of it makes the
// REPLY any better formed. The contract inverts it — the AGENT states where its reply is, with
// two fixed sentinel lines, and what lies between them is Slack mrkdwn delivered VERBATIM. No
// parsing stands between the agent and Slack on a conformant reply. What remains per-harness is
// the unavoidable mechanical step BELOW the contract: turning a log file into the text the agent
// wrote (`normalizeLog`). The contract and its enforcement are harness-agnostic.
//
// Non-conformance is not absorbed — it is FED BACK. The agent gets one corrective turn on its own
// chain naming what failed and quoting the offending line, bounded at MAX_REVIVES; past the bound
// the owner still gets the text, through the mrkdwn safety net, behind a marker that says it was
// not formatted. The bare fallback below is reached only by a log with NO text in it at all.
const FENCE_OPEN = '<<<SLACK-REPLY>>>';
const FENCE_CLOSE = '<<<END-SLACK-REPLY>>>';

// The template quoted back to a non-conformant agent. It contains a COMPLETE fence pair, which is
// safe by the same rule that makes the contract work at all: LAST complete pair wins, and a prompt
// echoed into a log is always echoed BEFORE the reply it provokes.
const CONTRACT_TEMPLATE = [
  FENCE_OPEN,
  '*The answer in one bold lead line*',
  '',
  'Detail below it, plain mrkdwn: *bold*, _italic_, `code`, <https://url|link text>, - bullets.',
  FENCE_CLOSE,
].join('\n');

// One human sentence per lint issue — the specific thing that failed, and the mrkdwn that
// replaces it. Keyed by `lintMrkdwn`'s issue vocabulary.
const ISSUE_TEXT = {
  'pipe-table': 'a pipe table — Slack renders the pipes literally; use short aligned lines or bullets',
  'markdown-bold': 'markdown bold (`**text**`) — Slack bold is single asterisks, `*text*`',
  'markdown-heading': 'a markdown heading (`#`) — Slack has no headings; use `*a short bold line*`',
  'markdown-link': 'a markdown link (`[text](url)`) — Slack links are `<url|text>`',
};

// Quote at most this many offending lines back: the feedback has to be specific, not a
// transcript, and a 200-row table would otherwise become the whole corrective prompt.
const MAX_QUOTED_ISSUES = 5;

// Corrective turns per OWNER turn (owner ruling, decision 7). Bounded on the CONVERSATION, not on
// the exec — see the revive block in _runOnce for why that is what makes the loop terminate.
const DEFAULT_MAX_REVIVES = 2;

// The best-effort marker (decision 7): past the revive bound the owner reads the reply anyway,
// prefixed so the shape it arrives in is attributed to the agent rather than to the bridge.
const UNFORMATTED_PREFIX = '⚠ unformatted reply — ';

// A best-effort body is whatever text the log held, which on a plain-text harness is the WHOLE
// log. Slack rejects an oversized post, and a rejected post is a retry loop ending in the give-up
// notice — i.e. the owner would lose the message entirely to a length nobody chose. Clamped.
const BEST_EFFORT_MAX_CHARS = 3500;

// Fixed fallback delivered when a run ends with no parseable reply line — the raw
// log is NEVER dumped into Slack (D110 step 4).
const FALLBACK_TEXT = '⚠ agent run ended without a parseable reply';

// D111 part 2 — the honest give-up notice. When the driver RETIRES an exec
// UNDELIVERED at the attempt cap (persistent fetch/delivery failure), the owner
// sees this ONE fixed line instead of silence: the agent finished but its reply
// could not be delivered. Fixed string, NO internals. Best-effort — a failed post
// is logged and dropped, never retried.
const GIVE_UP_NOTICE = "⚠ the agent finished but its reply couldn't be delivered";

// The dead-air notice: a DISARM means nothing will ever answer this turn — the expected
// run never appeared (spawn refused, or crashed before the carrier saw it) or the driver
// lost its ability to watch. Measured live 2026-08-10: kimi's binary failed execvp inside
// the cage, the corrective revive's spawn never materialized, and the conversation pended
// FOREVER in silence — the owner's exact original complaint, resurfacing one layer down.
// Every disarm now says so. Fixed string, NO internals, best-effort, never retried.
const DEAD_AIR_NOTICE = '⚠ no reply is coming for this turn — the agent run never completed';

const DEFAULT_POLL_MS = 3000;                 // single driver cadence (D110 step 3)
const DEFAULT_WINDOW_MS = 10 * 60 * 1000;     // bound: wait for a spawn ≤ 10 min (step 6)
const DEFAULT_LOG_LIMIT = 1000;               // per-page log fetch bound (server clamps to its MAX_PAGE)
const DEFAULT_MAX_LOG_PAGES = 50;             // cap the log paging loop (never unbounded)
const DEFAULT_MAX_STATUS_ERRORS = 20;         // disarm after persistent status errors (step 6)
const DEFAULT_MAX_DELIVER_ATTEMPTS = 20;      // per-exec fetch/delivery retry bound (step 6 — never unbounded)

// stream-json extraction (D110 step 4): the worker log is one JSON object per
// line (`claude -p --output-format stream-json`); the answer is the LAST line of
// shape `{ type:'result', result:'<text>', … }`. Non-JSON / non-result lines are
// skipped. No parseable result line → null (caller substitutes the fallback).
function extractReplyText(lines) {
  let text = null;
  for (const line of lines) {
    if (!line) continue;
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    if (obj && obj.type === 'result' && typeof obj.result === 'string') {
      text = obj.result; // keep scanning — take the LAST result line
    }
  }
  return text;
}

// codex `--json` extraction. The event shape is MEASURED, not assumed — `codex exec --json` on
// codex-cli 0.144.5 (2026-08-10, this box) emits one JSON event per line and puts the agent's turn
// text in `{ type:'item.completed', item:{ type:'agent_message', text } }`. Non-JSON lines are
// real ("Reading prompt from stdin...") and are skipped. LAST agent_message wins, matching the
// claude arm: a turn may emit several and the final one is the answer.
function extractCodexText(lines) {
  let text = null;
  for (const line of lines) {
    if (!line) continue;
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    const item = obj && obj.type === 'item.completed' ? obj.item : null;
    if (item && item.type === 'agent_message' && typeof item.text === 'string') text = item.text;
  }
  return text;
}

// CSI escape sequences. opencode writes its banner and status lines with colour even when its
// stdout is a file (measured on a live log, 2026-08-10) — an escape sitting on a sentinel line is
// enough to make an exactly-conformant reply read as non-conformant.
const ANSI = /\x1b\[[0-9;?]*[ -/]*[@-~]/g;

// LOG → THE TEXT THE AGENT WROTE, per harness. The harness is the profile name's leading token:
// profiles are one-per-harness+model and named for it (`claude-opus`, `codex-gpt-5-5`,
// `opencode-glm-5-2`, bare `kimi` — config/spawn-profiles.yaml § profiles).
//
// `jobs_log.profile` is nullable, but never null on an exec THIS leg watches: the leg watches
// ticker SPAWN actions only, and a launch-agent job cannot be enqueued without naming a profile
// (DEC-1 R3, enforced in forward-path.js#forwardSessionCreate). So the arm is selected, never
// guessed at.
//
// ⚑ THE DEFAULT ARM IS PLAIN TEXT, AND THAT IS THE HONEST DEFAULT, not a guess: a harness that
// emits no structured events writes its answer as text, so an unrecognized profile degrades to
// reading the log as what it is. The two structured arms deliberately do NOT fall through to it —
// a claude or codex log with no message event holds JSON, and dumping JSON into the owner's thread
// is the thing D110 step 4 forbids. For those two, no message event means no text.
function normalizeLog(lines, profile) {
  const harness = String(profile || '').split('-')[0];
  if (harness === 'claude') return extractReplyText(lines);
  if (harness === 'codex') return extractCodexText(lines);
  const text = lines.join('\n').replace(ANSI, '');
  return text.trim() ? text : null;
}

// The contract's own extraction: the content of the LAST COMPLETE sentinel pair. Last-wins is what
// makes an echoed prompt, a quoted template, or a first attempt the agent then corrected harmless
// — the reply the agent ended on is the one that travels. Sentinels are matched as WHOLE trimmed
// lines, so the two markers can never be confused with each other or with prose mentioning them.
function extractFenced(text) {
  if (typeof text !== 'string' || text === '') return null;
  const lines = text.split('\n');
  let open = -1;
  let body = null;
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (t === FENCE_OPEN) { open = i; continue; }
    if (t === FENCE_CLOSE && open >= 0) {
      body = lines.slice(open + 1, i).join('\n');
      open = -1;
    }
  }
  if (body === null) return null;
  // Outer blank lines are the fence's own whitespace, not the message; the CONTENT is untouched.
  body = body.replace(/^\n+|\n+$/g, '');
  return body === '' ? null : body;
}

// THE CONFORMANCE VERDICT. `body` is always the best text available for delivery — the fenced
// content when there is one, the whole normalized text when there is not, `null` only when the log
// held no text at all. That single field is what lets the caller deliver verbatim, deliver
// best-effort, and fall back, without re-deriving anything.
function checkReplyContract(normalized) {
  if (normalized == null) return { ok: false, body: null, problems: [{ issue: 'no-text' }] };
  const fenced = extractFenced(normalized);
  if (fenced === null) return { ok: false, body: normalized, problems: [{ issue: 'no-fence' }] };
  const hits = lintMrkdwn(fenced);
  return { ok: hits.length === 0, body: fenced, problems: hits };
}

// The corrective prompt. Specific first (what failed, with the offending line quoted), the shape
// second — a feedback that only says "wrong" produces another wrong turn.
function buildFeedback(problems) {
  const head = problems.some((p) => p.issue === 'no-fence')
    ? `Your reply did not reach the owner: your turn ended with no ${FENCE_OPEN} … ${FENCE_CLOSE} pair, so the bridge could not tell which part of your output was the message.`
    : 'Your reply did not reach the owner: the text inside your reply fence is markdown, and Slack renders mrkdwn. What broke:';
  const quoted = problems
    .filter((p) => ISSUE_TEXT[p.issue])
    .slice(0, MAX_QUOTED_ISSUES)
    .map((p) => `- line ${p.line}: ${ISSUE_TEXT[p.issue]}\n    ${p.text}`);
  const more = problems.length > MAX_QUOTED_ISSUES ? [`- …and ${problems.length - MAX_QUOTED_ISSUES} more of the same kind.`] : [];
  return [
    head,
    ...(quoted.length ? ['', ...quoted, ...more] : []),
    '',
    'Send the answer again now. End your turn with it between these two lines exactly, and write NOTHING after the closing line:',
    '',
    CONTRACT_TEMPLATE,
    '',
    'The text between the lines is delivered to Slack verbatim — it must be Slack mrkdwn (your slack-message-format reference has the full mapping).',
  ].join('\n');
}

// The driver. `deliver({ chatThreadId, text, markAsk })` is the bridge's own
// outbound delivery (chat-bridge.js deliverToOwner) — injected so the leg holds
// no transport of its own. `forwarder.inspect(target, extra)` is the gateway read
// surface. `threadMap` supplies each conversation's session queue-row id.
function createReplyLeg({
  threadMap,
  forwarder,
  deliver,
  // The corrective re-dispatch the revive loop rides: `async ({ chatThreadId, text }) =>
  // { forwarded, … }`. It is the bridge's OWN follow-up leg (forward-path.js forwardFollowUp,
  // flagged corrective) — a send-message job on the conversation's existing chain, which is the
  // same machinery an owner follow-up takes. Injected rather than built here for the reason every
  // other edge of this leg is injected: the driver holds no transport and mints no path of its
  // own. Absent (an embedder that wires none) → non-conformance goes straight to best-effort.
  redispatch = null,
  logger = null,
  pollMs = DEFAULT_POLL_MS,
  windowMs = DEFAULT_WINDOW_MS,
  logLimit = DEFAULT_LOG_LIMIT,
  maxLogPages = DEFAULT_MAX_LOG_PAGES,
  maxStatusErrors = DEFAULT_MAX_STATUS_ERRORS,
  maxDeliverAttempts = DEFAULT_MAX_DELIVER_ATTEMPTS,
  maxRevives = DEFAULT_MAX_REVIVES,
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // chatThreadId -> {
  //   queueId,           // the conversation's FIRST session queue-row id — the
  //                      //   first turn's watch key. A wake/recycle re-dispatch
  //                      //   mints a NEW queue row, so later turns are captured
  //                      //   by the chain-thread match below, never by queueId.
  //   armedAt,           // ms — refreshed each turn (arm) and on delivery; bounds
  //                      //   the wait for a spawn to appear (step 6 window).
  //   watching,          // Map execId -> { capturedAt } — spawns seen, awaiting turn-end.
  //   delivered,         // Set<execId> — execs already HANDLED (delivered, revived, or retired);
  //                      //   never processed twice.
  //   statusErrors,      // consecutive status-poll errors (bound, step 6).
  //   revives,           // corrective turns spent on the CURRENT owner turn (bound, decision 7).
  //                      //   Reset by arm() — a new owner turn gets a fresh budget — and by any
  //                      //   delivery, which is what ends a turn.
  // }
  const pending = new Map();
  let timer = null;
  let ticking = false;

  // Arm (or re-arm) a conversation as PENDING-REPLY. Called after the forward path
  // enqueues a session-create job (new conversation) AND after a follow-up
  // send-message lands on a mapped chain (the chain re-dispatches → a new exec on
  // the same queue). Re-arming refreshes the spawn-wait window for the new turn.
  function arm(chatThreadId) {
    const id = String(chatThreadId);
    const entry = threadMap.get(id);
    const queueId = entry ? entry.queueId : null;
    let p = pending.get(id);
    if (!p) {
      p = { queueId, armedAt: Date.now(), watching: new Map(), delivered: new Set(), statusErrors: 0, revives: 0 };
      pending.set(id, p);
    } else {
      p.armedAt = Date.now();
      p.revives = 0; // a NEW owner turn — never charged for the previous turn's corrections
      if (p.queueId == null) p.queueId = queueId;
    }
    log('info', 'reply leg armed for conversation', { chatThreadId: id, queueId: p.queueId });
    return p;
  }

  // Fetch + extract one exec's reply text, paging the bounded log surface to its
  // end so the LAST result line is seen even when the log spans pages (the server
  // clamps `limit` to its MAX_PAGE; we follow `nextOffset` until `eof`).
  //
  // Returns { fetched: false } on a FAILED page read (a transient gateway/transport
  // error — the real answer may still be on disk, so the caller RETRIES, bounded),
  // or { fetched: true, text } where text === null means the log was read to eof
  // and genuinely holds no parseable result line (the fallback case, D110 step 4).
  // Conflating the two would post the fallback — and burn the exec as delivered —
  // on a mere transport blip, silently losing the worker's real answer.
  //
  // `profile` selects the harness normalization (normalizeLog). It comes from the SAME
  // `inspect status` response that told us the turn ended — `jobs_log.profile`, already on the
  // status snapshot (server/spawn/spawn.js#status → dispatch.js). No inspect surface is widened
  // and no second lookup is made: the caller has the value in hand at exactly this point.
  async function fetchReplyText(execId, chatThreadId, profile) {
    const lines = [];
    let offset = 0;
    for (let page = 0; page < maxLogPages; page++) {
      const res = await forwarder.inspect('logs', { id: execId, offset, limit: logLimit });
      if (!res || !res.ok || !res.result) {
        log('warn', 'reply leg logs inspect failed — will retry next pass', { chatThreadId, execId, offset, error: res && res.error && res.error.code });
        return { fetched: false, text: null };
      }
      const pageLines = Array.isArray(res.result.lines) ? res.result.lines : [];
      for (const l of pageLines) lines.push(l);
      const next = res.result.nextOffset;
      offset = Number.isInteger(next) ? next : (offset + pageLines.length);
      if (res.result.eof || pageLines.length === 0) return { fetched: true, text: normalizeLog(lines, profile) };
    }
    // Page cap hit without eof: an absurdly long log (> maxLogPages × server page).
    // The result line is the LAST line, so it was NOT reached — treat as no
    // parseable reply (honest fallback), never deliver a mid-log line as the answer.
    log('warn', 'reply leg log page cap hit before eof — treating as no parseable reply', { chatThreadId, execId, pagesRead: maxLogPages, linesRead: lines.length });
    return { fetched: true, text: null };
  }

  // One driver pass (the setInterval body; also directly drivable for tests). A
  // re-entrancy guard keeps two passes from overlapping their async inspects.
  async function _runOnce() {
    if (ticking) return;
    ticking = true;
    try {
      if (pending.size === 0) return;

      // 1. Capture new execIds from ticker spawn actions, per conversation. A
      //    conversation may see MULTIPLE execs over its life (one per turn) — every
      //    spawn action with an execId not yet delivered is a turn to deliver. TWO
      //    match keys: the FIRST turn matches by the conversation's queueId; every
      //    later turn is a wake/recycle re-dispatch on a NEW queue row, matched by
      //    the spawn action's chain thread against the mapped conversation's
      //    resolved chainThread (p7-multiturn — the server stamps `thread` on every
      //    spawn action). A `compact: true` spawn is a compaction turn: its output
      //    is the chain's short-term memory, never an owner-facing reply — skipped.
      const tickerRes = await forwarder.inspect('ticker');
      if (tickerRes && tickerRes.ok && tickerRes.result) {
        const ticks = Array.isArray(tickerRes.result.recent_ticks) ? tickerRes.result.recent_ticks : [];
        for (const [id, p] of pending) {
          const entry = threadMap.get(id);
          const chainThread = (entry && entry.chainThread) || null;
          if (p.queueId == null && !chainThread) continue;
          for (const t of ticks) {
            const actions = Array.isArray(t.actions) ? t.actions : [];
            for (const a of actions) {
              if (!a || a.action !== 'spawn' || a.execId == null || a.compact) continue;
              const byQueue = p.queueId != null && Number(a.queueId) === Number(p.queueId);
              const byThread = chainThread !== null && a.thread === chainThread;
              if (!byQueue && !byThread) continue;
              const execId = Number(a.execId);
              // TEACH THE THREAD MAP WHAT WE JUST LEARNED. The driver has the
              // conversation's exec-id in hand here; the thread map is the thing that
              // has to resolve a chain thread for the NEXT turn. Binding it now is
              // what makes the follow-up leg window-independent: `bindSessionExecId`
              // is FIRST-WINS immutable, so this records the FIRST exec and every
              // later turn derives `exec-<first exec_id>` by convention regardless of
              // liveness (thread-map RESOLUTION ORDER tier 4).
              //
              // Without this the two modules each hold half the answer and neither
              // completes it: the driver knows the exec but only watches it, while
              // resolveChainThread re-derives from `recent_ticks`, which is WINDOWED
              // to the last ~10 ticks. A conversation whose session ended and whose
              // spawn then aged out of that window resolves `exec-id-unknown` and the
              // follow-up is honestly DECLINED — correct behaviour, avoidable cause.
              // Found live: a follow-up sent ~2.5 min after its first turn (while a
              // seat close/renew was captured in between) declined for exactly this.
              threadMap.bindSessionExecId(id, execId);
              if (!p.delivered.has(execId) && !p.watching.has(execId)) {
                p.watching.set(execId, { capturedAt: Date.now(), attempts: 0 });
                log('info', 'reply leg captured spawn exec for conversation', { chatThreadId: id, queueId: p.queueId, execId, matchedBy: byQueue ? 'queue-id' : 'chain-thread' });
              }
            }
          }
        }
      } else {
        log('warn', 'reply leg ticker inspect failed', { error: tickerRes && tickerRes.error });
      }

      // 2. Poll each watched exec's status; on `live === false`, fetch + extract +
      //    deliver exactly once. Key on the live flag, NEVER on status (crash-sweep
      //    mislabels clean successes `failed`).
      for (const [id, p] of pending) {
        for (const execId of Array.from(p.watching.keys())) {
          const statusRes = await forwarder.inspect('status', { id: execId });
          if (!statusRes || !statusRes.ok || !statusRes.result) {
            p.statusErrors += 1;
            log('warn', 'reply leg status inspect failed', { chatThreadId: id, execId, error: statusRes && statusRes.error, statusErrors: p.statusErrors });
            continue;
          }
          p.statusErrors = 0;
          if (statusRes.result.live !== false) continue; // still live (or unknown) — keep polling

          // Turn ended — fetch, extract, deliver. Failures here are ISOLATED per
          // exec (a throw must not abort the pass for other execs/conversations)
          // and RETRIED next pass, bounded per exec (step 6 — never unbounded):
          // the exec is marked delivered ONLY on a confirmed delivery, so a
          // transient logs/transport/Slack failure never burns the reply.
          const watch = p.watching.get(execId);
          let failure = null;
          try {
            const read = await fetchReplyText(execId, id, statusRes.result.profile);
            if (!read.fetched) {
              failure = 'logs-fetch-failed';
            } else {
              const verdict = checkReplyContract(read.text);

              // NON-CONFORMANCE → ONE corrective turn on the SAME chain, then this exec is DONE
              // here. It is retired watching→delivered exactly as the give-up path retires one:
              // it has been handled, and a lingering recent_ticks spawn row must never re-capture
              // it. The corrective turn's own exec arrives as an ordinary turn on this
              // conversation and is checked identically — which is precisely why the budget lives
              // on the CONVERSATION and not on the exec. A per-exec counter would hand every
              // revive a fresh allowance of two and the loop would never terminate; this one is
              // spent by the revive's own bad output, so the bound holds whatever the agent does.
              if (!verdict.ok && verdict.body !== null && p.revives < maxRevives) {
                const back = typeof redispatch === 'function'
                  ? await redispatch({ chatThreadId: id, text: buildFeedback(verdict.problems) })
                  : { forwarded: false, reason: 'no-redispatch-wired' };
                if (back && back.forwarded) {
                  p.revives += 1;
                  p.watching.delete(execId);
                  p.delivered.add(execId);
                  p.armedAt = Date.now(); // the corrective turn's spawn is what we now wait for
                  log('warn', 'reply leg revived the agent for a non-conformant reply', {
                    chatThreadId: id, execId, revives: p.revives, maxRevives,
                    problems: verdict.problems.map((x) => x.issue),
                  });
                  continue;
                }
                // The chain could not be re-dispatched (unresolved, refused, unwired). Correcting
                // is impossible, so the owner gets the text now rather than after two more passes
                // that would fail the same way.
                log('warn', 'reply leg corrective re-dispatch refused — delivering best-effort instead', {
                  chatThreadId: id, execId, reason: (back && (back.reason || back.error)) || 'unknown',
                });
              }

              // DELIVERY. A CONFORMANT reply travels VERBATIM — that is the contract's whole
              // point, and running it through the converter would reintroduce the parsing step
              // the contract exists to remove. Everything else is best-effort (decision 7): the
              // text we do have, through the mrkdwn safety net, behind a marker attributing the
              // shape to the agent. The bare FALLBACK is reached only by a log with no text at
              // all — never while any text exists.
              const text = verdict.ok
                ? verdict.body
                : (verdict.body !== null
                  ? `${UNFORMATTED_PREFIX}${toMrkdwn(clampBestEffort(verdict.body))}`
                  : FALLBACK_TEXT);
              if (!verdict.ok) {
                log('warn', 'reply leg delivering a NON-CONFORMANT reply', {
                  chatThreadId: id, execId, revives: p.revives,
                  problems: verdict.problems.map((x) => x.issue), hasText: verdict.body !== null,
                });
              }
              const d = await deliver({ chatThreadId: id, text, markAsk: false }); // plain agent output (D105 note; ask-detection out of scope v1)
              if (d && d.delivered === false) {
                failure = `deliver-refused:${d.reason || d.error || 'unknown'}`;
              } else {
                p.watching.delete(execId);
                p.delivered.add(execId);
                p.armedAt = Date.now(); // healthy activity — reset the spawn-wait window
                p.revives = 0;          // the turn ended in a delivery; the next one starts fresh
                log('info', 'reply leg delivered worker reply to owner', { chatThreadId: id, execId, chars: text.length, conformant: verdict.ok });
              }
            }
          } catch (err) {
            failure = `deliver-threw:${err.message}`;
          }
          if (failure) {
            watch.attempts += 1;
            if (watch.attempts >= maxDeliverAttempts) {
              // Give up HONESTLY: stop retrying, keep the exec in `delivered` so a
              // lingering recent_ticks spawn row cannot re-capture it. The reply is
              // NOT delivered and the warn says so — never a silent success.
              p.watching.delete(execId);
              p.delivered.add(execId);
              log('warn', 'reply leg giving up on exec after persistent fetch/delivery failures — reply NOT delivered', { chatThreadId: id, execId, attempts: watch.attempts, failure });
              // Tell the owner (D111 part 2) instead of silence — best-effort: a
              // failed notice post is logged and dropped, never retried into a loop.
              try {
                const n = await deliver({ chatThreadId: id, text: GIVE_UP_NOTICE, markAsk: false });
                if (n && n.delivered === false) {
                  log('warn', 'reply leg give-up notice not delivered (best-effort, dropped)', { chatThreadId: id, execId, reason: n.reason || n.error || 'unknown' });
                } else {
                  log('info', 'reply leg give-up notice posted to owner', { chatThreadId: id, execId });
                }
              } catch (nerr) {
                log('warn', 'reply leg give-up notice threw (best-effort, dropped)', { chatThreadId: id, execId, error: nerr.message });
              }
            } else {
              log('warn', 'reply leg fetch/delivery failed — will retry next pass', { chatThreadId: id, execId, attempts: watch.attempts, failure });
            }
          }
        }
      }

      // 3. Bound (step 6): disarm a conversation that errored persistently, or whose
      //    expected spawn never appeared within the window (never delivered, nothing
      //    in flight). No crash, no unbounded retry. EVERY disarm posts the dead-air
      //    notice: a disarm is the driver declaring "nobody will answer this turn",
      //    and the one thing worse than that is declaring it only to the log.
      const deadAir = async (id, reason) => {
        try {
          const n = await deliver({ chatThreadId: id, text: DEAD_AIR_NOTICE, markAsk: false });
          if (n && n.delivered === false) log('warn', 'reply leg dead-air notice not delivered (best-effort, dropped)', { chatThreadId: id, reason });
        } catch (err) {
          log('warn', 'reply leg dead-air notice threw (best-effort, dropped)', { chatThreadId: id, reason, error: err.message });
        }
      };
      const now = Date.now();
      for (const [id, p] of Array.from(pending.entries())) {
        if (p.statusErrors >= maxStatusErrors) {
          log('warn', 'reply leg disarming conversation — persistent status errors', { chatThreadId: id, statusErrors: p.statusErrors });
          pending.delete(id);
          await deadAir(id, 'status-errors');
          continue;
        }
        // A corrective turn was ordered and its spawn never came. Without this rung the
        // conversation pends FOREVER: the revive retired its exec into `delivered`, so the
        // never-delivered rung below can never match again. Measured live 2026-08-10 (kimi
        // execvp failure): revive issued 12:49:47, no spawn ever followed, silence.
        if (p.revives > 0 && p.watching.size === 0 && (now - p.armedAt) > windowMs) {
          log('warn', 'reply leg disarming conversation — corrective spawn never appeared', { chatThreadId: id, revives: p.revives, windowMs });
          pending.delete(id);
          await deadAir(id, 'revive-no-spawn');
          continue;
        }
        if (p.watching.size === 0 && p.delivered.size === 0 && (now - p.armedAt) > windowMs) {
          log('warn', 'reply leg disarming conversation — no spawn within window', { chatThreadId: id, queueId: p.queueId, windowMs });
          pending.delete(id);
          await deadAir(id, 'no-spawn');
        }
      }
    } finally {
      ticking = false;
    }
  }

  function start() {
    if (timer) return;
    timer = setInterval(() => {
      _runOnce().catch((err) => log('warn', 'reply leg tick error', { error: err.message }));
    }, pollMs);
    if (timer.unref) timer.unref();
    log('info', 'reply leg started', { pollMs, windowMs });
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    log('info', 'reply leg stopped');
  }

  return { arm, start, stop, tick: _runOnce, _pending: pending };
}

function clampBestEffort(s) {
  return s.length <= BEST_EFFORT_MAX_CHARS ? s : `${s.slice(0, BEST_EFFORT_MAX_CHARS)}\n… (truncated)`;
}

module.exports = {
  createReplyLeg, extractReplyText, extractCodexText, normalizeLog, extractFenced,
  checkReplyContract, buildFeedback,
  FALLBACK_TEXT, GIVE_UP_NOTICE, DEAD_AIR_NOTICE, FENCE_OPEN, FENCE_CLOSE, CONTRACT_TEMPLATE, UNFORMATTED_PREFIX,
};

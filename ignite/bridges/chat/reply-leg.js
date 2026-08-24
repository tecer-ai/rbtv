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

// ── THE THREE VISIBILITY NOTICES (P3) ────────────────────────────────────────────────────────
// Same discipline as GIVE_UP_NOTICE and DEAD_AIR_NOTICE in every respect: fixed strings, NO
// internals, best-effort (a failed post is logged and dropped, never retried), ONE-SHOT per turn.
// They exist because every silence the owner sees is indistinguishable from a broken bridge, and
// the leg's own poll already knows the difference — it just never said so.

// The daemon marked the exec `stalled` (silent past the stall rung) while its process still lives.
const STALL_NOTICE = '⚠ the agent has gone silent — nothing is lost; your message is held and it will be restarted if it does not wake';

// …and it was then killed for that silence. The owner is told the run died, NOT shown its partial
// log: a hung run's half-written output is not an answer and must never be delivered as one.
const RECOVERY_NOTICE = '⚠ that run was stopped after going silent — your queued message will be delivered to a fresh run';

// The turn is simply LONG. Not an error, not a promise — just the fact that would otherwise be
// silence. Env-overridable, one number, one place (same shape as the latency threshold above).
const DEFAULT_SLOW_NOTICE_S = Number(process.env.RBTV_CHAT_SLOW_NOTICE_S || 300);
const slowNoticeText = (minutes) => `⏳ still working on your message — ${minutes} minute${minutes === 1 ? '' : 's'} so far`;

const DEFAULT_POLL_MS = 3000;                 // single driver cadence (D110 step 3)
const DEFAULT_WINDOW_MS = 10 * 60 * 1000;     // bound: wait for a spawn ≤ 10 min (step 6)

// The CORRECTIVE spawn wait, deliberately far shorter than the first-turn window above. A revive
// enqueues a send-message on a chain that is ALREADY awake, and the daemon dispatches it on the
// next tick — measured 2026-08-12: enqueue 02:28:42, spawn 02:28:45, three seconds. Ten minutes of
// silence to detect "it never came" is ten minutes the owner spends staring at nothing. 120 s is
// ~40 poll cycles past that horizon, which absorbs a burst of gateway timeouts; and the rung is
// additionally gated on having SUCCESSFULLY read the ticker this pass (see `tickerOk` below), so a
// blind driver never declares a spawn missing it merely could not look for.
const DEFAULT_CORRECTIVE_WINDOW_MS = 120 * 1000;

// End-to-end latency (owner message accepted → reply posted) above which the delivery line is
// raised to a WARNING. Env-overridable; no config machinery — one number, one place.
const DEFAULT_LATENCY_WARN_S = Number(process.env.RBTV_CHAT_REPLY_LATENCY_WARN_S || 30);
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

// LOG → THE TEXT THE AGENT WROTE, per harness. The harness is the LAUNCH-SPEC KEY's first
// segment: `jobs_log.profile` records the key of the spec that actually launched — `harness/model`
// (`claude/claude-opus-5`, `codex/gpt-5.5`, `opencode/zai-coding-plan/glm-5.2`) — written by
// `spawn.js` from the RESOLVED value, never from a request.
//
// ⚠ THE SEPARATOR IS `/` SINCE 7.787 AND THE OLD SPLIT WAS FRAGILE. This read `split('-')[0]` off
// a profile NAME, which worked only because every name happened to lead with its harness; a name
// like `worker` or `fast-opus` would have picked the wrong arm silently. The key's first `/`
// segment IS the harness by construction (`catalog.js#specKey`), so the parse is now structural.
// A model literal may itself contain `/` (`zai-coding-plan/glm-5.2`) — which is exactly why the
// FIRST segment is taken and not the last.
//
// ⚠ THE LEGACY NAME FORM STILL FLOWS TODAY — it is not "historical". `jobs_log` was not migrated
// (nothing in it is re-read as a launch instruction — the whole table is HISTORY / turn audit
// [T4-R8], and `profile` is an audit column like every other on the row), and the bridge's own
// enqueue path was still writing `claude-sonnet` on 2026-08-12, on live execs THIS leg was
// watching. A slashless name has no `/`, so the first segment is the whole string; the resolver
// below therefore matches on a `-` boundary too, and treats "unrecognized" as an event to report
// rather than a shape to assume.
//
// ⚠ AND `jobs_log.profile` IS GENUINELY NULL SOMETIMES. It was claimed here to be "never null on
// an exec THIS leg watches, because every spawn resolves a spec before it records anything" — the
// resolution is what can FAIL. `heart-store.js#fireQueueRow` inserts the `launching` row with a
// NULL profile and only a SUCCESSFUL spawn fills in the resolved spec key, so a spawn that failed
// (an uncast seat, a refused launch) leaves the column NULL on a row this leg is watching. Null is
// therefore an ordinary input on the unrecognized path — loud, structured extractor first, raw
// text only as the last resort — and never the silent whole-log dump it used to be.
//
// ⚑ THE PLAIN-TEXT ARM IS FOR HARNESSES WE KNOW EMIT NO EVENTS, NEVER FOR A VALUE WE FAILED TO
// RECOGNIZE. It used to be both, and that cost the owner a whole evening (2026-08-12): the live
// value was the legacy profile NAME `claude-sonnet`, `'claude-sonnet' !== 'claude'` under the old
// strict equality, and every claude reply became the ENTIRE stream-json session log delivered as
// "the reply" — head-clamped to the SessionStart hook banner — with not one log line saying why.
// Recognition is now (a) the first `/` segment, (b) matched on a `-` boundary inside it, so both
// `claude/claude-haiku-4-5` and `claude-sonnet` reach the claude arm; and an UNRECOGNIZED value is
// LOUD and tries the structured extractor before it will ever hand back a raw log. A raw-log dump
// is no longer reachable without a warn having named the value that caused it.
const HARNESS_TOKENS = ['claude', 'codex', 'opencode', 'kimi'];
function resolveHarness(profile) {
  const seg = String(profile || '').split('/')[0];
  return HARNESS_TOKENS.find((t) => seg === t || seg.startsWith(`${t}-`)) || null;
}

// `notify` (optional) is called ONLY on the unrecognized-harness path, with the value that was not
// recognized and whether the text being returned is a RAW LOG. The caller logs the warn and — the
// point of the flag — declines to blame the AGENT for a fence the bridge never located.
function normalizeLog(lines, profile, notify = null) {
  const harness = resolveHarness(profile);
  if (harness === 'claude') return extractReplyText(lines);
  if (harness === 'codex') return extractCodexText(lines);
  const plain = () => {
    const t = lines.join('\n').replace(ANSI, '');
    return t.trim() ? t : null;
  };
  // A KNOWN plain-text harness (opencode, kimi) writes its answer as text — reading the log as
  // what it is remains the honest default there, and a missing fence there IS the agent's.
  if (harness) return plain();
  // Unrecognized. Best effort in order of least damage: the structured extractor first (a result
  // event is the answer and nothing else in the log is), the raw text only if that finds nothing.
  const structured = extractReplyText(lines);
  const text = structured !== null ? structured : plain();
  if (notify) notify({ profile: String(profile || ''), rawFallback: structured === null && text !== null });
  return text;
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
  correctiveWindowMs = DEFAULT_CORRECTIVE_WINDOW_MS,
  latencyWarnS = DEFAULT_LATENCY_WARN_S,
  logLimit = DEFAULT_LOG_LIMIT,
  maxLogPages = DEFAULT_MAX_LOG_PAGES,
  maxStatusErrors = DEFAULT_MAX_STATUS_ERRORS,
  maxDeliverAttempts = DEFAULT_MAX_DELIVER_ATTEMPTS,
  maxRevives = DEFAULT_MAX_REVIVES,
  slowNoticeS = DEFAULT_SLOW_NOTICE_S,
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // The one owner-notice path for the P3 notices: best-effort, both outcomes logged, a failure
  // dropped and NEVER retried into a loop. (`deadAir` below keeps its own wording, unchanged.)
  async function postNotice(chatThreadId, text, kind) {
    try {
      const n = await deliver({ chatThreadId, text, markAsk: false });
      if (n && n.delivered === false) log('warn', 'reply leg notice not delivered (best-effort, dropped)', { chatThreadId, kind, why: n.reason || n.error || 'unknown' });
      else log('info', 'reply leg notice posted to owner', { chatThreadId, kind });
    } catch (err) {
      log('warn', 'reply leg notice threw (best-effort, dropped)', { chatThreadId, kind, error: err.message });
    }
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
  //   disarmedAt,        // ms or null — the spawn-wait rung fired and the owner was told. The
  //                      //   entry is KEPT for one more corrective window so a late spawn can
  //                      //   still be captured and delivered (§ TOMBSTONE), then reaped into
  //                      //   `recoverable` (not forgotten) so a still-later spawn can re-arm.
  // }
  const pending = new Map();
  // chatThreadId -> stashed pending fields. A revive-no-spawn tombstone whose grace
  // expired is removed from `pending` (r3: not a leak of the hot watch loop) but
  // remembered here so a late spawn on the same chain is re-armed instead of dropped.
  const recoverable = new Map();
  let timer = null;
  let ticking = false;

  // Arm (or re-arm) a conversation as PENDING-REPLY. Called after the forward path
  // enqueues a session-create job (new conversation) AND after a follow-up
  // send-message lands on a mapped chain (the chain re-dispatches → a new exec on
  // the same queue). Re-arming refreshes the spawn-wait window for the new turn.
  function arm(chatThreadId) {
    const id = String(chatThreadId);
    recoverable.delete(id); // a new owner turn supersedes a stashed revive-no-spawn reap
    const entry = threadMap.get(id);
    const queueId = entry ? entry.queueId : null;
    let p = pending.get(id);
    if (!p) {
      p = { queueId, armedAt: Date.now(), turnStartedAt: Date.now(), watching: new Map(), delivered: new Set(), statusErrors: 0, revives: 0, compacted: false, disarmedAt: null, slowNoticed: false };
      pending.set(id, p);
    } else {
      p.armedAt = Date.now();
      p.disarmedAt = null; // a new owner turn revives a tombstoned conversation outright
      // `armedAt` is a spawn-wait deadline and is reset by revives and deliveries; `turnStartedAt`
      // is the OWNER's clock and moves only here, on a real owner turn. The end-to-end latency the
      // owner actually experiences is measured from this one, never from armedAt.
      p.turnStartedAt = Date.now();
      p.revives = 0; // a NEW owner turn — never charged for the previous turn's corrections
      p.compacted = false;
      p.slowNoticed = false; // …and a fresh slow-notice budget: one per owner turn (P3)
      if (p.queueId == null) p.queueId = queueId;
    }
    log('info', 'reply leg armed for conversation', { chatThreadId: id, queueId: p.queueId });
    return p;
  }

  // Fetch + extract one exec's reply text, paging the bounded log surface to its
  // end so the LAST result line is seen even when the log spans pages (the server
  // clamps `limit` to its MAX_PAGE; we follow `nextOffset` until `eof`).
  //
  // `rawFallback: true` on the returned read means the text is a RAW LOG the leg could not
  // attribute to any harness — the one shape whose missing fence is the BRIDGE's failure and not
  // the agent's, and the caller must not revive on it (see the revive gate).
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
    let rawFallback = false;
    const notify = (ev) => {
      rawFallback = ev.rawFallback;
      log('warn', ev.rawFallback
        ? 'reply leg could not resolve the harness AND found no result event — delivering RAW LOG text, and NOT blaming the agent for it'
        : 'reply leg could not resolve the harness — fell back to the structured extractor, which found the reply',
      { chatThreadId, execId, profile: ev.profile, knownHarnesses: HARNESS_TOKENS.join(',') });
    };
    let offset = 0;
    for (let page = 0; page < maxLogPages; page++) {
      const res = await forwarder.inspect('logs', { id: execId, offset, limit: logLimit });
      if (!res || !res.ok || !res.result) {
        log('warn', 'reply leg logs inspect failed — will retry next pass', { chatThreadId, execId, offset, error: res && res.error && res.error.code });
        return { fetched: false, text: null, rawFallback: false };
      }
      const pageLines = Array.isArray(res.result.lines) ? res.result.lines : [];
      for (const l of pageLines) lines.push(l);
      const next = res.result.nextOffset;
      offset = Number.isInteger(next) ? next : (offset + pageLines.length);
      if (res.result.eof || pageLines.length === 0) {
        const text = normalizeLog(lines, profile, notify);
        return { fetched: true, text, rawFallback };
      }
    }
    // Page cap hit without eof: an absurdly long log (> maxLogPages × server page).
    // The result line is the LAST line, so it was NOT reached — treat as no
    // parseable reply (honest fallback), never deliver a mid-log line as the answer.
    log('warn', 'reply leg log page cap hit before eof — treating as no parseable reply', { chatThreadId, execId, pagesRead: maxLogPages, linesRead: lines.length });
    return { fetched: true, text: null, rawFallback: false };
  }

  // One driver pass (the setInterval body; also directly drivable for tests). A
  // re-entrancy guard keeps two passes from overlapping their async inspects.
  async function _runOnce() {
    if (ticking) return;
    ticking = true;
    try {
      // `recoverable` keeps the tick alive past an empty `pending`: a reaped
      // revive-no-spawn conversation is re-armed from the stash below, and that
      // code is unreachable if an empty map short-circuits the pass.
      if (pending.size === 0 && recoverable.size === 0) return;

      // 1. Capture new execIds from ticker spawn actions, per conversation. A
      //    conversation may see MULTIPLE execs over its life (one per turn) — every
      //    spawn action with an execId not yet delivered is a turn to deliver. TWO
      //    match keys: the FIRST turn matches by the conversation's queueId; every
      //    later turn is a wake/recycle re-dispatch on a NEW queue row, matched by
      //    the spawn action's chain thread against the mapped conversation's
      //    resolved chainThread (p7-multiturn — the server stamps `thread` on every
      //    spawn action).
      //
      //    ⚑ A `compact: true` spawn IS CAPTURED, and used to be skipped. Its output is the
      //    chain's short-term memory, never an owner-facing reply — but skipping it made the leg
      //    BLIND to the one spawn that stands between an owner turn and its answer. Measured
      //    2026-08-12 (thread D0BJ50Y1DC6:1786501607): a revive enqueued its corrective
      //    send-message (queue 458, 02:28:42), the daemon woke the chain and dispatched it three
      //    seconds later — AS A COMPACTION TURN (tick 235208, exec 26449, `compact:true`, because
      //    the chain transcript had crossed `history_compact_chars`). The leg ignored that spawn,
      //    watched nothing, and 10 minutes on disarmed with "corrective spawn never appeared" —
      //    while the compaction turn had in fact spawned, crashed (exit 1, 02:28:59) and HALTED
      //    the chain, so no answering turn was ever coming. Captured, it is retired without
      //    delivery when it ends (below) — one status poll buys the leg the difference between
      //    "the chain is working" and "the chain is dead".
      const tickerRes = await forwarder.inspect('ticker');
      const tickerOk = Boolean(tickerRes && tickerRes.ok && tickerRes.result);
      if (tickerOk) {
        const ticks = Array.isArray(tickerRes.result.recent_ticks) ? tickerRes.result.recent_ticks : [];
        // A spawn whose queue/thread matches a REAPED revive-no-spawn conversation
        // has nowhere to land in `pending`. Re-arm from the stash so the capture
        // loop below attaches it. Dead-air was already posted; the real answer
        // following it is the accepted UX (measured 2026-08-18: 7.5 min relaunch).
        if (recoverable.size > 0) {
          for (const t of ticks) {
            const actions = Array.isArray(t.actions) ? t.actions : [];
            for (const a of actions) {
              if (!a || a.action !== 'spawn' || a.execId == null) continue;
              for (const [id, saved] of Array.from(recoverable.entries())) {
                const mapped = threadMap.get(id);
                const queueId = (saved && saved.queueId) ?? (mapped && mapped.queueId);
                const chainThread = (mapped && mapped.chainThread)
                  || (mapped && mapped.sessionExecId != null ? `exec-${mapped.sessionExecId}` : null);
                const byQueue = queueId != null && Number(a.queueId) === Number(queueId);
                const byThread = chainThread !== null && a.thread === chainThread;
                if (!byQueue && !byThread) continue;
                pending.set(id, {
                  queueId,
                  armedAt: Date.now(),
                  turnStartedAt: (saved && saved.turnStartedAt) || Date.now(),
                  watching: new Map(),
                  delivered: (saved && saved.delivered) || new Set(),
                  statusErrors: 0,
                  revives: (saved && saved.revives) || 0,
                  compacted: Boolean(saved && saved.compacted),
                  disarmedAt: null,
                  slowNoticed: Boolean(saved && saved.slowNoticed),
                });
                recoverable.delete(id);
                log('info', 'reply leg re-armed a reaped conversation — late spawn arrived after revive-no-spawn', {
                  chatThreadId: id, execId: Number(a.execId), matchedBy: byQueue ? 'queue-id' : 'chain-thread',
                });
              }
            }
          }
        }
        for (const [id, p] of pending) {
          const entry = threadMap.get(id);
          const chainThread = (entry && entry.chainThread) || null;
          if (p.queueId == null && !chainThread) continue;
          for (const t of ticks) {
            const actions = Array.isArray(t.actions) ? t.actions : [];
            for (const a of actions) {
              if (!a || a.action !== 'spawn' || a.execId == null) continue;
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
              // …and a COMPACTION turn is never the chain's first exec, so it must never become
              // the first-wins binding the follow-up leg derives every later thread from.
              if (!a.compact) threadMap.bindSessionExecId(id, execId);
              if (!p.delivered.has(execId) && !p.watching.has(execId)) {
                p.watching.set(execId, { capturedAt: Date.now(), attempts: 0, compact: Boolean(a.compact) });
                log('info', 'reply leg captured spawn exec for conversation', { chatThreadId: id, queueId: p.queueId, execId, compact: Boolean(a.compact), matchedBy: byQueue ? 'queue-id' : 'chain-thread' });
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
          const watch = p.watching.get(execId);

          // ── STALL (P3) ──────────────────────────────────────────────────────────────────
          // The daemon marks an exec `stalled` when it has been silent past the stall rung while
          // its process still lives, and halts the slot's automatic action. From Slack that is
          // indistinguishable from a bridge that stopped working. ONE post per watched exec
          // (`stallNoticed`), and only while the exec is otherwise LIVE — a stall that has already
          // ended is the recovery arm's business, not this one.
          if (statusRes.result.live !== false) {
            if (statusRes.result.status === 'stalled' && !watch.stallNoticed) {
              watch.stallNoticed = true;
              log('warn', 'reply leg saw a STALLED exec — telling the owner once', { chatThreadId: id, execId });
              await postNotice(id, STALL_NOTICE, 'stall');
            }
            continue; // still live (or unknown) — keep polling
          }

          // ── RECOVERY (P3) ───────────────────────────────────────────────────────────────
          // The turn ended as `killed` AFTER we told the owner it had gone silent: the daemon's
          // hang-killer took it. Its log is a HALF-WRITTEN HANG, so it must never reach the reply
          // extractor — delivering that as "the reply" is worse than saying nothing. The exec is
          // retired, the owner is told once, and the spawn window is RESET so the leg waits for
          // the daemon's next run on this conversation instead of tombstoning it.
          if (statusRes.result.status === 'killed' && watch.stallNoticed) {
            p.watching.delete(execId);
            p.delivered.add(execId);
            p.armedAt = Date.now();
            p.disarmedAt = null;
            log('warn', 'reply leg retired a KILLED hung exec — its partial log was NOT run through the reply extractor', { chatThreadId: id, execId });
            await postNotice(id, RECOVERY_NOTICE, 'recovery');
            continue;
          }

          // Turn ended — fetch, extract, deliver. Failures here are ISOLATED per
          // exec (a throw must not abort the pass for other execs/conversations)
          // and RETRIED next pass, bounded per exec (step 6 — never unbounded):
          // the exec is marked delivered ONLY on a confirmed delivery, so a
          // transient logs/transport/Slack failure never burns the reply.

          // A COMPACTION turn ended. Its output is the chain's memory, not a reply — nothing is
          // fetched and nothing is delivered. Retire it and RESTART the spawn wait: the answering
          // turn is dispatched only after this one ends, so the clock on it starts now. If no
          // answering turn follows (the chain crashed, as it did on 2026-08-12), the wait blows
          // within `correctiveWindowMs` and the owner is told — instead of ten minutes of silence.
          if (watch.compact) {
            p.watching.delete(execId);
            p.delivered.add(execId);
            p.armedAt = Date.now();
            p.compacted = true;
            log('info', 'reply leg retired a compaction turn — now waiting for the answering turn', { chatThreadId: id, execId });
            continue;
          }

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
              //
              // ⚑ AND NEVER ON TEXT THE BRIDGE COULD NOT ATTRIBUTE. `read.rawFallback` means the
              // body is a raw log the leg failed to resolve a harness for — the fence may be
              // sitting in it perfectly formed, wrapped in thousands of lines of JSON the check
              // cannot see past. Telling that agent "your turn ended with no fence" is a false
              // accusation that costs a duplicate session and a duplicate Slack message per
              // revive; it happened twice per conversation on 2026-08-12. An extraction failure is
              // the BRIDGE's problem: it is warned about above and delivered best-effort.
              if (!verdict.ok && verdict.body !== null && !read.rawFallback && p.revives < maxRevives) {
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
                  ? bestEffortText(verdict.body)
                  : FALLBACK_TEXT);
              if (!verdict.ok) {
                log('warn', 'reply leg delivering a NON-CONFORMANT reply', {
                  chatThreadId: id, execId, revives: p.revives,
                  problems: verdict.problems.map((x) => x.issue), hasText: verdict.body !== null,
                  rawFallback: read.rawFallback,
                });
              }
              const d = await deliver({ chatThreadId: id, text, markAsk: false, answersOwnerAsk: verdict.ok === true }); // plain agent output (D105 note; ask-detection out of scope v1)
              if (d && d.delivered === false) {
                failure = `deliver-refused:${d.reason || d.error || 'unknown'}`;
              } else {
                p.watching.delete(execId);
                p.delivered.add(execId);
                p.armedAt = Date.now(); // healthy activity — reset the spawn-wait window
                p.revives = 0;          // the turn ended in a delivery; the next one starts fresh
                p.compacted = false;
                p.disarmedAt = null;    // a LATE reply arrived after all — the tombstone is lifted
                p.slowNoticed = true;   // the turn is ANSWERED — spend the slow-notice budget so the
                                        // P3 rung can never tell the owner "still working" AFTER his
                                        // answer landed (owner-reported 2026-08-20 03:49Z, both goal
                                        // channels). arm() re-opens it on the next real owner turn.
                // THE LATENCY LINE — one per delivered reply, end to end: the owner's message
                // being armed → this post landing. Everything the bridge does between those two
                // stamps (dispatch, run, revives, compaction, retries) is inside it, which is
                // exactly what the owner feels. Over threshold it is raised to a WARNING.
                const latencyS = p.turnStartedAt ? Math.round((Date.now() - p.turnStartedAt) / 100) / 10 : null;
                const slow = latencyS !== null && latencyS > latencyWarnS;
                log(slow ? 'warn' : 'info', slow
                  ? 'reply leg delivered worker reply to owner — SLOW, over the latency threshold'
                  : 'reply leg delivered worker reply to owner',
                { chatThreadId: id, execId, chars: text.length, conformant: verdict.ok, latencyS, thresholdS: latencyWarnS });
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
              p.compacted = false; // the turn is over (undelivered, and said so) — stop waiting on it
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
          // Both outcomes are logged. Only the failure used to be, so an owner reporting silence
          // after a disarm could not be told from the log whether the notice was posted at all.
          if (n && n.delivered === false) log('warn', 'reply leg dead-air notice not delivered (best-effort, dropped)', { chatThreadId: id, reason, why: n.reason || n.error || 'unknown' });
          else log('info', 'reply leg dead-air notice posted to owner', { chatThreadId: id, reason });
        } catch (err) {
          log('warn', 'reply leg dead-air notice threw (best-effort, dropped)', { chatThreadId: id, reason, error: err.message });
        }
      };
      const now = Date.now();

      // ⚑ A TURN STILL SITTING IN THE DAEMON'S QUEUE IS NOT DEAD AIR (P2). With `on_seat_busy:
      // 'queue'` an owner message that arrives at a busy seat is QUEUED rather than refused, so no
      // spawn appears until the seat frees — which behind a 20-minute turn is well past the
      // spawn-wait window. The rung below would call that a dead thread and tell the owner nothing
      // is coming, minutes before his answer arrives.
      //
      // The queue is the authority. ONE `inspect queue` read per pass, taken LAZILY — only when a
      // conversation is actually about to be disarmed — and the conversation is identified by the
      // `chat-thread: <id>` line the forward path puts at the head of every session-create prompt
      // (forward-path.js § the one admitted correlation id).
      //
      // ⚑ A FAILED READ COUNTS AS "STILL QUEUED", the same posture the `tickerOk` gate keeps: a
      // driver that could not look has seen nothing to declare a thread dead on.
      let queuedArgs; // undefined = not read this pass · null = read failed · string = joined args
      const stillQueued = async (id) => {
        if (queuedArgs === undefined) {
          const res = await forwarder.inspect('queue');
          const rows = res && res.ok && res.result && Array.isArray(res.result.rows) ? res.result.rows : null;
          queuedArgs = rows ? rows.map((r) => String((r && r.args) || '')).join('\n') : null;
          if (queuedArgs === null) log('warn', 'reply leg queue inspect failed — holding off on every disarm this pass', { error: res && res.error });
        }
        return queuedArgs === null || queuedArgs.includes(`chat-thread: ${id}`);
      };

      for (const [id, p] of Array.from(pending.entries())) {
        // ── SLOW (P3) ────────────────────────────────────────────────────────────────────────
        // The turn is simply taking a long time. One post per OWNER turn (`slowNoticed`, reset in
        // arm() beside the other per-turn resets), never on a conversation already tombstoned —
        // that one has been told the opposite and must not now be told to keep waiting.
        if (!p.slowNoticed && !p.disarmedAt && p.turnStartedAt && (now - p.turnStartedAt) > slowNoticeS * 1000) {
          p.slowNoticed = true;
          const minutes = Math.max(1, Math.round((now - p.turnStartedAt) / 60000));
          log('info', 'reply leg telling the owner his turn is still running', { chatThreadId: id, minutes, thresholdS: slowNoticeS });
          await postNotice(id, slowNoticeText(minutes), 'slow');
        }
        // A TOMBSTONED conversation has already been declared dead to the owner; it is kept only
        // so a LATE spawn can still be captured and delivered (below, § tombstone). Once the grace
        // is spent with nothing watched, the entry leaves the hot loop — but is STASHED, not
        // forgotten: a spawn that arrives after the grace (measured 2026-08-18: 7.5 min) re-arms
        // from `recoverable` instead of being dropped.
        if (p.disarmedAt && p.watching.size === 0 && (now - p.disarmedAt) > correctiveWindowMs) {
          log('info', 'reply leg reaped a tombstoned conversation — no late reply arrived', { chatThreadId: id, graceMs: correctiveWindowMs });
          recoverable.set(id, {
            queueId: p.queueId,
            delivered: p.delivered,
            revives: p.revives,
            turnStartedAt: p.turnStartedAt,
            compacted: p.compacted,
            slowNoticed: p.slowNoticed,
          });
          pending.delete(id);
          continue;
        }
        if (p.statusErrors >= maxStatusErrors) {
          log('warn', 'reply leg disarming conversation — persistent status errors', { chatThreadId: id, statusErrors: p.statusErrors });
          pending.delete(id);
          await deadAir(id, 'status-errors');
          continue;
        }
        // THE SPAWN-WAIT RUNG — one rung, three ways in, because they differ only in HOW LONG a
        // missing spawn is allowed to stay missing:
        //   • nothing ever delivered  → the FIRST turn is still owed a spawn (the original bound).
        //   • a revive was issued     → its corrective turn was ordered and never came (2026-08-10,
        //                               kimi execvp failure). The revive retired its exec into
        //                               `delivered`, so the first way in can never match again.
        //   • a compaction was retired → the ANSWERING turn was owed and never came (2026-08-12,
        //                               exec 26449 crashed after compacting). Same shape, and the
        //                               first two ways in both miss it.
        // The last two wait `correctiveWindowMs`, not `windowMs`: both are a re-dispatch on a chain
        // that is ALREADY awake, which the daemon fires on the next tick. Ten minutes there is ten
        // minutes of the owner staring at nothing. An ORDINARY follow-up keeps the long window —
        // it may legitimately queue behind the chain's running turn.
        //
        // ⚑ THE RUNG REQUIRES `tickerOk`. "No spawn appeared" is a claim about what the ticker
        // showed, and this pass may not have been able to LOOK — on 2026-08-12 the gateway timed
        // out on `inspect ticker` for minutes at a stretch. A driver that cannot see the ticker
        // must not declare a thread dead; it waits for a pass that can.
        const fast = p.revives > 0 || p.compacted === true;
        const owedSpawn = p.delivered.size === 0 || fast;
        if (tickerOk && !p.disarmedAt && owedSpawn && p.watching.size === 0 && (now - p.armedAt) > (fast ? correctiveWindowMs : windowMs)) {
          if (await stillQueued(id)) {
            log('info', 'reply leg NOT disarming — this turn is still waiting its place in the daemon queue', { chatThreadId: id, queueId: p.queueId });
            continue;
          }
          const reason = p.revives > 0 ? 'revive-no-spawn' : p.compacted ? 'compaction-no-answering-turn' : 'no-spawn';
          log('warn', 'reply leg disarming conversation — expected spawn never appeared', { chatThreadId: id, queueId: p.queueId, reason, revives: p.revives, windowMs: fast ? correctiveWindowMs : windowMs });
          // `no-spawn` used to leave the thread-map entry in place. The next owner
          // post then hit follow-up → exec-id-unknown → terminal decline, and the
          // channel stayed wedged (measured 2026-08-20). The mapping is left as-is
          // (dropping it here would remint mid-probe and break queue-id fixtures);
          // forwardFollowUp now falls back to session-create on exec-id-unknown, so
          // the conversation can start fresh without a terminal decline.
          // § TOMBSTONE — `revive-no-spawn` ONLY. That disarm used to `pending.delete(id)`, which
          // made the notice a LIE whenever it was merely EARLY: on 2026-08-12 the corrective spawn
          // HAD run and had answered fine — the daemon was mid-restart and the ticker did not show
          // it in time — and with the entry gone there was no longer any path for that answer to
          // reach the owner. Keeping the entry for ONE more corrective window costs one Map row and
          // buys the late reply a door; the reaper above closes it. The notice is still posted NOW
          // (the owner is never left waiting on a maybe) and posted ONCE — `disarmedAt` gates this
          // rung as well as the reaper. The other two reasons keep the plain delete: a chain that
          // crashed inside its compaction turn is not late, it is dead.
          if (reason === 'revive-no-spawn') p.disarmedAt = now;
          else pending.delete(id);
          await deadAir(id, reason);
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

// KEEP THE TAIL. An agent's answer is what its turn ENDS on — for every harness the leg reads, the
// reply is at EOF and the head is boot noise. Head-clamping delivered exactly that noise to the
// owner on 2026-08-12: 3518 bytes of SessionStart hook banner, cut mid-word, while the real reply
// sat past the cut. If anything is lost to the bound, it must be the preamble.
function clampBestEffort(s) {
  return s.length <= BEST_EFFORT_MAX_CHARS ? s : `… (truncated)\n${s.slice(-BEST_EFFORT_MAX_CHARS)}`;
}

// THE BEST-EFFORT DELIVERY SHAPE, shared by BOTH legs. The cold leg reaches it after its revive
// budget is spent; the warm arm reaches it immediately (no revive there — owner ruling 2026-08-11).
// One function so the two can never drift into posting a non-conformant reply differently.
function bestEffortText(body) {
  return `${UNFORMATTED_PREFIX}${toMrkdwn(clampBestEffort(body))}`;
}

module.exports = {
  createReplyLeg, extractReplyText, extractCodexText, normalizeLog, extractFenced,
  checkReplyContract, buildFeedback, bestEffortText,
  FALLBACK_TEXT, GIVE_UP_NOTICE, DEAD_AIR_NOTICE, STALL_NOTICE, RECOVERY_NOTICE, slowNoticeText,
  FENCE_OPEN, FENCE_CLOSE, CONTRACT_TEMPLATE, UNFORMATTED_PREFIX,
};

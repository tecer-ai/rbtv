'use strict';

const NACK_ASK = "couldn't parse that reply. First word must be one of: approve, reject-and-close, reject-and-pause, reject-and-retry, retry with:, close, a letter (a–g), pause {goal}, resume {goal}. Comments go after that word. Reply again.";

const NACK_MECHANICAL = "couldn't parse pause/resume. Use `pause {goal}` or `resume {goal}` with one live goal slug. In a goal channel, bare pause/resume targets that goal. Reply again.";

// The recovery ladder's own NACK [`d-ask14-recovery-thread-shape`] — a recovery thread's reply is
// ALWAYS exactly one of the three ruled options [spec-recovery §5, T1-R8, D-2-ruling]; the ask/
// approval NACK above names a vocabulary (approve, letters, …) that does not apply here and would
// mislead the owner about what this thread will accept.
const NACK_RECOVERY = "couldn't parse that reply. First word must be one of: retry-with-change, drop-lane, pause-goal. Comments go after that word. Reply again.";

// Verbatim [T1-R8, D-2-ruling] — the SAME three words `supervisor/exhaustion.js#ASK_OPTIONS` opens
// the ask with. `chat/` may not `require()` that module [`probes/probe-chat-boundary.js`], so this
// is a second, hand-kept copy of the same closed vocabulary — the same shape `approval-thread.js`'s
// `APPROVAL_TOKEN_LINE` already accepts for the same reason.
const RECOVERY_TOKENS = [
  { outcome: 'retry-with-change', pattern: 'retry with change' },
  { outcome: 'drop-lane', pattern: 'drop lane' },
  { outcome: 'pause-goal', pattern: 'pause goal' },
].sort((a, b) => b.pattern.length - a.pattern.length);

const FINDINGS_OUTCOMES = new Set(['reject-and-retry', 'retry with:']);

const APPROVAL_TOKENS = [
  { outcome: 'reject-and-close', pattern: 'reject and close' },
  { outcome: 'reject-and-pause', pattern: 'reject and pause' },
  { outcome: 'reject-and-retry', pattern: 'reject and retry' },
  { outcome: 'retry with:', pattern: 'retry with:' },
  { outcome: 'retry with:', pattern: 'retry with' },
  { outcome: 'approve', pattern: 'approved' },
  { outcome: 'approve', pattern: 'approve' },
  { outcome: 'close', pattern: 'close' },
].sort((a, b) => b.pattern.length - a.pattern.length);

function nackAsk() {
  return { ok: false, nack: NACK_ASK, nackKind: 'ask' };
}

function nackMechanical() {
  return { ok: false, nack: NACK_MECHANICAL, nackKind: 'mechanical' };
}

function nackRecovery() {
  return { ok: false, nack: NACK_RECOVERY, nackKind: 'recovery' };
}

function skipWs(line, i) {
  while (i < line.length && /[ \t]/.test(line[i])) i += 1;
  return i;
}

function matchPattern(line, pattern) {
  let i = skipWs(line, 0);
  let ti = 0;
  while (ti < pattern.length) {
    const pc = pattern[ti];
    if (pc === ' ') {
      if (i >= line.length || !/[- \t]/.test(line[i])) return null;
      while (i < line.length && /[- \t]/.test(line[i])) i += 1;
      ti += 1;
      continue;
    }
    if (i >= line.length || line[i].toLowerCase() !== pc) return null;
    i += 1;
    ti += 1;
  }
  if (i < line.length && !/[ \t]/.test(line[i]) && !pattern.endsWith(':')) return null;
  return i;
}

function matchLetter(line) {
  let i = skipWs(line, 0);
  const head = line.slice(i, i + 6).toLowerCase();
  if (head === 'option') {
    const after = i + 6;
    if (after >= line.length || !/[- \t]/.test(line[after])) return null;
    i = after;
    while (i < line.length && /[- \t]/.test(line[i])) i += 1;
  }
  if (i >= line.length) return null;
  const ch = line[i].toLowerCase();
  if (ch < 'a' || ch > 'g') return null;
  i += 1;
  if (i < line.length && /[.):]/.test(line[i])) i += 1;
  if (i < line.length && /[A-Za-z0-9]/.test(line[i])) return null;
  return { letter: ch, end: i };
}

function commentsOf(firstLine, end, following) {
  const onLine = firstLine.slice(end);
  return [onLine, ...following].join('\n').trim();
}

function findingsOf(outcome, comments) {
  if (!FINDINGS_OUTCOMES.has(outcome)) return null;
  return comments.split('\n').map((l) => l.trim()).filter(Boolean);
}

function resolveGoal(slug, opts) {
  const live = opts.liveGoals;
  if (!Array.isArray(live)) return { ok: true, goal: slug };
  const needle = slug.toLowerCase();
  const hits = live.filter((g) => String(g).toLowerCase() === needle);
  if (hits.length !== 1) return { ok: false };
  return { ok: true, goal: hits[0] };
}

function parseMechanical(verb, firstLine, end, following, opts) {
  let i = skipWs(firstLine, end);
  let slug = null;
  if (i < firstLine.length) {
    const rest = firstLine.slice(i);
    const m = /^(\S+)/.exec(rest);
    if (m) {
      slug = m[1];
      i += m[1].length;
    }
  }
  if (!slug) {
    if (!opts.channelGoal) return nackMechanical();
    slug = opts.channelGoal;
  }
  const resolved = resolveGoal(slug, opts);
  if (!resolved.ok) return nackMechanical();
  const comments = commentsOf(firstLine, i, following);
  return {
    ok: true,
    outcome: verb,
    comments,
    family: 'mechanical',
    findings: null,
    goal: resolved.goal,
  };
}

function parseReply(text, opts = {}) {
  if (typeof text !== 'string') return opts.kind === 'recovery' ? nackRecovery() : nackAsk();
  const lines = text.split(/\r?\n/);
  let idx = 0;
  while (idx < lines.length && lines[idx].trim() === '') idx += 1;
  if (idx >= lines.length) return opts.kind === 'recovery' ? nackRecovery() : nackAsk();
  const first = lines[idx];
  const following = lines.slice(idx + 1);

  // A RECOVERY THREAD PARSES ONLY THE RECOVERY LADDER, NEVER THE OTHERS [`d-ask14-recovery-thread-
  // shape`]. The three options are not configurable [T1-R8, D-2-ruling] — mixing this family into
  // the ask/approval/mechanical pool below would risk a stray collision (a bare `pause-goal` would
  // otherwise fall into the mechanical `pause {goal}` arm further down, hunting for a goal literally
  // named `goal`) and would let an approval word answer a question this thread never asked.
  if (opts.kind === 'recovery') {
    for (const tok of RECOVERY_TOKENS) {
      const end = matchPattern(first, tok.pattern);
      if (end == null) continue;
      const comments = commentsOf(first, end, following);
      return {
        ok: true, outcome: tok.outcome, comments, family: 'recovery', findings: null, goal: null,
      };
    }
    return nackRecovery();
  }

  let best = null;
  for (const tok of APPROVAL_TOKENS) {
    const end = matchPattern(first, tok.pattern);
    if (end == null) continue;
    if (!best || end > best.end || (end === best.end && tok.pattern.length > best.pattern.length)) {
      best = { outcome: tok.outcome, end, pattern: tok.pattern };
    }
  }
  if (best) {
    const comments = commentsOf(first, best.end, following);
    return {
      ok: true,
      outcome: best.outcome,
      comments,
      family: 'approval',
      findings: findingsOf(best.outcome, comments),
      goal: null,
    };
  }

  const letter = matchLetter(first);
  if (letter) {
    const comments = commentsOf(first, letter.end, following);
    return {
      ok: true,
      outcome: letter.letter,
      comments,
      family: 'lettered',
      findings: null,
      goal: null,
    };
  }

  const pauseEnd = matchPattern(first, 'pause');
  if (pauseEnd != null) return parseMechanical('pause', first, pauseEnd, following, opts);
  const resumeEnd = matchPattern(first, 'resume');
  if (resumeEnd != null) return parseMechanical('resume', first, resumeEnd, following, opts);

  return nackAsk();
}

module.exports = {
  parseReply, NACK_ASK, NACK_MECHANICAL, NACK_RECOVERY,
};

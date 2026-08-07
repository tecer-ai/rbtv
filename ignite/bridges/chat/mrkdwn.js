'use strict';

// MARKDOWN → MRKDWN NORMALIZATION, applied to the agent's reply on its way into Slack.
//
// WHY THIS EXISTS AS CODE. The channel-master seat is TOLD the mrkdwn rules — its
// `slack-message-format` reference states them, and its seat descriptor makes reading that
// reference mandatory before the first reply. Twice measured (2026-08-06 and 2026-08-07), the
// owner still received markdown: once from a sitting that HAD read the reference, once from a
// sitting that never read its descriptor at all. A rule the occupant may skip is not a wall.
// This module is the wall: the reply leg is the ONE place every agent reply passes through, so
// the conversion happens there, deterministically, whatever the model did.
//
// ⚑ THIS IS NOT BEHAVIOURAL TEXT AND DOES NOT BREACH THE BRIDGE'S "no charter" RULING (owner,
// 2026-08-06 — forward-path.js header). That ruling governs what the bridge puts INTO a session's
// prompt: identity and behaviour travel with the seat. This is OUTPUT normalization on the way
// back out — it adds no instruction, changes no meaning, and would be a no-op on a reply that
// already followed the rules.
//
// ⚑ WHAT IT DELIBERATELY DOES NOT DO. It never touches content inside a fenced code block or an
// inline code span (a `**` inside a shell snippet is data, not emphasis), and it does not rewrite
// pipe tables. The reference tells the seat not to send tables; converting one here would mean
// GUESSING at column intent, and a wrong guess silently corrupts the owner's information. A table
// that arrives renders as raw pipes — visibly wrong, which is the correct failure mode for
// something this module refuses to interpret.

// One line that is nothing but 3+ of - * _ (optionally spaced): a markdown horizontal rule.
// mrkdwn has none; Slack shows the characters. Dropped, and the blank line does the separating.
const HR_LINE = /^\s{0,3}((-\s*){3,}|(\*\s*){3,}|(_\s*){3,})$/;

// ATX heading: `# text` … `###### text`. Becomes a bold line, which is what a heading IS in Slack.
const HEADING = /^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$/;

// `**bold**` and `__bold__` → `*bold*`. Non-greedy, no newlines inside, and the delimiters must
// wrap at least one non-space character so `** ` in prose is left alone.
const BOLD = /(\*\*|__)(?=\S)([^\n]*?\S)\1/g;

// `[text](url)` → `<url|text>`. The url may not contain whitespace, `(`, or `)`.
const LINK = /\[([^\]\n]+)\]\(([^\s()]+)\)/g;

// Split a line into code spans and non-code runs. Backticks are honoured pairwise; an unpaired
// trailing backtick leaves the remainder as ordinary text (never swallows the rest of the line).
function mapOutsideInlineCode(line, fn) {
  const parts = line.split('`');
  // Even indices are outside code, odd indices are inside — unless the count is even, meaning the
  // last backtick is unpaired; that final fragment is outside too.
  const lastOutside = parts.length % 2 === 0 ? parts.length - 1 : -1;
  return parts
    .map((part, i) => (i % 2 === 0 || i === lastOutside ? fn(part) : part))
    .join('`');
}

function convertLine(line) {
  const heading = HEADING.exec(line);
  if (heading) {
    // An empty heading (`#` alone) has no text to bold — drop it rather than emit a bare `**`.
    return heading[1] ? `*${mapOutsideInlineCode(heading[1], inlineConvert)}*` : '';
  }
  return mapOutsideInlineCode(line, inlineConvert);
}

function inlineConvert(text) {
  return text.replace(BOLD, '*$2*').replace(LINK, '<$2|$1>');
}

// The entry point. Returns the text unchanged when there is nothing to convert.
function toMrkdwn(text) {
  if (typeof text !== 'string' || text === '') return text;
  const out = [];
  let inFence = false;
  for (const line of text.split('\n')) {
    // A fence toggles regardless of language tag; the tag itself is stripped because Slack shows
    // it as the first line of the block (```python renders literally).
    const fence = /^\s{0,3}```/.exec(line);
    if (fence) {
      inFence = !inFence;
      out.push(inFence ? '```' : line.trim().startsWith('```') ? '```' : line);
      continue;
    }
    if (inFence) { out.push(line); continue; }
    if (HR_LINE.test(line)) continue; // the rule disappears; surrounding blank lines separate
    out.push(convertLine(line));
  }
  // A dropped horizontal rule can leave three consecutive blank lines; collapse runs to one blank.
  return out.join('\n').replace(/\n{3,}/g, '\n\n');
}

module.exports = { toMrkdwn };

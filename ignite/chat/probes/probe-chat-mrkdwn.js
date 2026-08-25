'use strict';

// MARKDOWN → MRKDWN normalization on the outbound reply (mrkdwn.js, wired at the reply leg's ONE
// delivery point). Guards the conversion the owner's Slack client actually needs, and — just as
// importantly — the three things it must NOT do: touch code, invent table structure, or alter a
// reply that already obeyed the rules.
//
// THE PRIMARY CASE IS REAL. `LIVE_*` below are the two replies the owner actually received
// (2026-08-06 and 2026-08-07 sittings, extracted from the daemon's session logs) — the defect
// this module exists for, asserted on its own bytes rather than on a case invented to pass.

const path = require('node:path');
const fs = require('node:fs');
const { toMrkdwn } = require('../mrkdwn');

const OUT = path.join(__dirname, 'probe-chat-mrkdwn.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence }); };

// ── the two measured failures ────────────────────────────────────────────────
const LIVE_HR = `Both rulings are now logged and relayed.

---
Nothing else needed on either one.

*#4925* — ruled (a) Accept as-is.`;

const LIVE_BOLD = `I have direct-access tools plus deferred ones (loaded on demand):

**Direct tools:**
- **Bash** — run shell commands (git, tests, scripts, etc.)
- **Read / Edit / Write** — read, edit, or create files`;

// 1. The horizontal rule disappears (Slack renders it as literal dashes).
const hr = toMrkdwn(LIVE_HR);
check('a markdown horizontal rule is dropped from a real reply',
  !/^\s*---\s*$/m.test(hr) && hr.includes('Nothing else needed') && hr.includes('*#4925*'),
  { before: LIVE_HR, after: hr });

// 2. `**bold**` becomes `*bold*`, everywhere on the line, and single-asterisk bold is untouched.
const bold = toMrkdwn(LIVE_BOLD);
check('every **bold** run becomes *bold*, and nothing else on the line moves',
  !bold.includes('**') && bold.includes('*Direct tools:*') && bold.includes('*Bash*') && bold.includes('- *Read / Edit / Write*'),
  { before: LIVE_BOLD, after: bold });

// 3. Headings become bold lines; links become <url|text>.
const head = toMrkdwn('## Status\nsee [the runbook](https://example.com/rb) for detail');
check('an ATX heading becomes a bold line and a markdown link becomes a mrkdwn link',
  head === '*Status*\nsee <https://example.com/rb|the runbook> for detail', { after: head });

// 4. CODE IS NEVER TOUCHED — fenced or inline. A `**` in a shell snippet is data.
const code = toMrkdwn('run `git log --format=**x**` first\n```python\nx = a ** b  # power\n---\n```\ndone');
check('fenced and inline code pass through byte-identical (the ** and --- inside survive)',
  code.includes('`git log --format=**x**`') && code.includes('x = a ** b  # power') && code.includes('\n---\n'),
  { after: code });
check('a language tag on the fence is stripped (```python renders literally in Slack)',
  !code.includes('```python') && code.includes('```'), { after: code });

// 5. IDEMPOTENT, and a no-op on a reply that already followed the rules.
const already = 'Nothing else needed.\n\n*#4925* — ruled (a). See `runs.csv`.\n> quoted\n• bullet';
check('a reply that already obeys the rules is returned unchanged',
  toMrkdwn(already) === already, { text: already });
check('the conversion is idempotent (running it twice changes nothing further)',
  toMrkdwn(bold) === bold && toMrkdwn(hr) === hr, {});

// 6. THE REFUSAL, stated as a check so it is a decision and not an oversight: a pipe table is
//    left exactly as it arrived. Converting one means guessing at column intent, and a wrong
//    guess silently corrupts the owner's information; raw pipes are visibly wrong instead.
const table = '| a | b |\n|---|---|\n| 1 | 2 |';
check('a pipe table is left untouched — never re-interpreted (the separator row is not an HR)',
  toMrkdwn(table) === table, { after: toMrkdwn(table) });

// 7. Degenerate input never throws or invents output.
check('empty / non-string input passes through untouched',
  toMrkdwn('') === '' && toMrkdwn(null) === null && toMrkdwn(undefined) === undefined, {});
check('an unpaired backtick does not swallow the rest of the line',
  toMrkdwn('a `b **c** d') === 'a `b *c* d', { after: toMrkdwn('a `b **c** d') });

const pass = checks.every((c) => c.pass);
const wallMs = Date.now() - t0;
const exit = pass ? 0 : 1;
fs.writeFileSync(OUT, JSON.stringify({
  summary: { probe: 'probe-chat-mrkdwn', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
  entries: checks,
}, null, 2) + '\n');
process.stdout.write(`PROBE probe-chat-mrkdwn EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
process.exit(exit);

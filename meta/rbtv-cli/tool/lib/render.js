'use strict';

// Output modes. Default is terse and agent-lean; `--pretty` is the human opt-in;
// `--json` is for machine callers. The mode is NEVER chosen by TTY detection —
// agents live in TTYs too, so a TTY test would hand the agent the human mode
// exactly where it costs most.

const C = {
  dim: '\x1b[2m', bold: '\x1b[1m', reset: '\x1b[0m',
  cyan: '\x1b[36m', yellow: '\x1b[33m', red: '\x1b[31m',
};

function paint(pretty, color, s) {
  return pretty ? `${C[color]}${s}${C.reset}` : s;
}

// Two columns, aligned only in pretty mode — alignment padding is bytes an agent
// pays for and cannot use.
function table(rows, pretty) {
  if (!rows.length) return [];
  if (!pretty) return rows.map(([a, b]) => (b ? `${a}  ${b}` : a));
  const w = Math.max(...rows.map(([a]) => a.length));
  return rows.map(([a, b]) => `  ${C.cyan}${a.padEnd(w)}${C.reset}  ${b || ''}`);
}

// One sentence, for scan views. The full text is always one drill level away.
//
// Sentence end ONLY — never a dash. These descriptions use the em-dash as a clause
// separator ("Building RBTV itself — components, install…"), so treating it as a
// stop truncated every module in the catalog to its first three words. Measured on
// the real manifest, which is the only reason it was visible at all.
function blurb(text, max = 110) {
  if (!text) return '';
  const flat = String(text).replace(/\s+/g, ' ').trim();
  const stop = flat.search(/\.(\s|$)/);
  const cut = stop > 20 ? flat.slice(0, stop + 1) : flat;
  return cut.length > max ? `${cut.slice(0, max - 1)}…` : cut;
}

function json(obj) {
  process.stdout.write(`${JSON.stringify(obj)}\n`);
}

// Every refusal states what was refused, why it matters, the exact fix, and the
// escape if one exists — an agent must recover from the error text alone.
function refusal({ what, why, fix, escape }) {
  const out = [`refused: ${what}`];
  if (why) out.push(`  why: ${why}`);
  if (fix) out.push(`  fix: ${fix}`);
  if (escape) out.push(`  escape: ${escape}`);
  return out.join('\n');
}

// Closest-match suggestion for a mistyped reference (Levenshtein, small sets).
function suggest(input, candidates) {
  let best = null;
  let bestD = Infinity;
  for (const c of candidates) {
    const d = distance(input, c);
    if (d < bestD) { bestD = d; best = c; }
  }
  // Past a third of the token's length the "suggestion" is noise, not help.
  return bestD <= Math.max(2, Math.floor(input.length / 3)) ? best : null;
}

function distance(a, b) {
  const m = a.length;
  const n = b.length;
  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i += 1) {
    const cur = [i];
    for (let j = 1; j <= n; j += 1) {
      cur[j] = Math.min(
        prev[j] + 1,
        cur[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
    prev = cur;
  }
  return prev[n];
}

module.exports = { paint, table, blurb, json, refusal, suggest, C };

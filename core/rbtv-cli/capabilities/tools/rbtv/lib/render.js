'use strict';

// Output helpers the action verbs share. Default text is plain; `--json` is for
// machine callers. Colour is not a mode of this CLI: nothing here paints.

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

module.exports = { json, refusal };

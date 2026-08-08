'use strict';

// Task C5 — PER-ROW ARGV TEMPLATING (owner ruling `d-owner-q10-launcher-0808` (2), r03 §5 B1(a)).
//
// A queue row's `args` expand into the registered workflow's static argv, so `--workflow` /
// `--entry-seat` ride the ROW and one generic launcher serves every workflow. Before this, the
// only value that crossed from a queue row into a fired command line was `workdir`, so a static
// registration could fire exactly one fixed request forever.
//
// ⚠ THIS IS AN INJECTION SURFACE AND THE DEFENCE IS STRUCTURAL, NOT TEXTUAL. Row text becomes an
// exec'd command line. Four properties carry that, and each is a property of the SHAPE rather than
// of a filter someone has to keep current:
//
//   1. ARRAY IN, ARRAY OUT. The expansion maps an argv array to an argv array. Nothing here joins
//      tokens into a string, and the carriers exec the array directly — `spawn(argv[0],
//      argv.slice(1))` in `spawn/carrier.js` for setsid, and `systemd-run … argv` for systemd.
//      There is no shell anywhere on this path, so a `;` or a `$(…)` inside a value is a literal
//      argument byte and cannot become a command. The value validators below are defence in depth
//      over that, never the thing standing between a row and a shell.
//   2. WHOLE-TOKEN ONLY. A token is a placeholder or it is a literal — never a mix. So a value can
//      never be concatenated onto a flag it did not come with (`--flag={{v}}` is refused as a
//      malformed token, not expanded), and the token count of the composed argv equals the token
//      count of the registered argv, always.
//   3. ONE PASS, AND AN EXPANDED VALUE IS NEVER RE-SCANNED. Placeholder smuggling — a row value
//      that itself reads `{{workdir}}` — is not filtered, it is unreachable: the output array is
//      returned, not re-entered. This is why the expansion is a `map` and never a loop-to-fixpoint.
//   4. CLOSED KEY SET. Only the keys in TEMPLATE_KEYS may appear as placeholders, and each carries
//      its own value rule. An unknown placeholder is a typed refusal, never an empty string —
//      silently dropping it would compose an argv missing a flag's operand, which is the failure
//      that looks like a success.
//
// Used at BOTH ends on purpose (defence in depth): `heart-store.js` validateArgs refuses a bad
// value at ENQUEUE, so no such row is ever stored; `ticker.js` launchStartWorkflow re-validates at
// FIRE, because the store can hold rows enqueued before this code existed.

const path = require('node:path');

// Kebab-case, the same shape `goal_creation_request.py`'s GOAL_NAME_RE already enforces on goal
// names. Carrying NO dot is what makes `..` unrepresentable rather than filtered, and carrying no
// `/` is what makes a path separator unrepresentable in a value that names a seat or a workflow —
// the D10 containment pattern, applied where the value is born instead of where it is joined.
const NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MAX_NAME = 64;
const MAX_PATH = 512;

// A token is a placeholder only if the WHOLE token is one. The key grammar is deliberately
// narrower than the value grammar: a placeholder key is authored in config, never in a row.
const PLACEHOLDER_RE = /^\{\{([a-z][a-z0-9-]*)\}\}$/;

function nameRule(label) {
  return (value) => {
    if (typeof value !== 'string') return `${label} must be a string, got ${typeof value}`;
    if (value.length === 0 || value.length > MAX_NAME) {
      return `${label} must be 1..${MAX_NAME} characters, got ${value.length}`;
    }
    if (!NAME_RE.test(value)) {
      return `${label} must be lowercase kebab-case ([a-z0-9] groups joined by "-"): ` +
        `no path separator, no "..", no leading "-", no shell metacharacter`;
    }
    return null;
  };
}

// CONTAINMENT WITHOUT A HARDCODED ROOT. The module rule forbids baking a workspace path into the
// code, and the workspace root is not knowable here — so containment is proven from the path's own
// SEGMENTS after normalisation: an absolute path whose segments carry `.rbtv/goals/<something>`.
// `..` is refused on the RAW value first rather than normalised away, because a value that needed
// normalising to become legal is a value someone wrote to escape.
//
// ⚠ THE CONTAINMENT IS LEXICAL, NOT RESOLVED — measured, C5 review 2026-08-08. A workdir whose
// segments read `.rbtv/goals/<x>` but whose `<x>` is a SYMLINK pointing elsewhere passes this rule,
// and the fired child's cwd is then outside the goals root (capture:
// `evidence/c5-review/c5r-02-integration-attacks.txt` § P2). This is deliberate, not an oversight:
// resolving with `realpath` would refuse two legal cases — a workdir scaffolded but not yet on disk,
// and a deployment whose `.rbtv/goals` root is itself a symlink onto another volume (the resolved
// path no longer carries the `.rbtv/goals` segments at all). The exposure it leaves is bounded by
// who can PLANT a symlink under the goals root, which is local filesystem write as the daemon user
// — strictly more access than this rule defends against. A row author cannot reach it: the inbox
// boundary carries a goal NAME through `GOAL_NAME_RE`, which creates a directory and never a link.
// Tightening this needs an owner ruling on the two legal cases above, not a silent realpath.
function workdirRule(value) {
  if (typeof value !== 'string') return `workdir must be a string, got ${typeof value}`;
  if (value.length === 0 || value.length > MAX_PATH) {
    return `workdir must be 1..${MAX_PATH} characters, got ${value.length}`;
  }
  if (!path.posix.isAbsolute(value)) return 'workdir must be an absolute path';
  const raw = value.split('/');
  if (raw.includes('..')) return 'workdir must carry no ".." segment';
  const parts = path.posix.normalize(value).split('/');
  const i = parts.indexOf('.rbtv');
  if (i === -1 || parts[i + 1] !== 'goals' || !parts[i + 2]) {
    return 'workdir must resolve inside a `.rbtv/goals/<goal>` containment';
  }
  return null;
}

// The CLOSED set of keys a registered argv may template from a row, each with its value rule.
// Growing it is a deliberate act: a new key is a new byte class reaching an exec'd command line.
const TEMPLATE_KEYS = Object.freeze({
  workflow: nameRule('workflow'),
  'entry-seat': nameRule('entry-seat'),
  goal: nameRule('goal'),
  workdir: workdirRule,
});

// Every control character is refused in every value, ahead of the per-key rule. A newline or a NUL
// in an argv token corrupts the systemd unit properties the carrier writes, and no legal value of
// any key above carries one.
// eslint-disable-next-line no-control-regex
const CONTROL_RE = /[\x00-\x1f\x7f]/;

// Validate the templatable keys PRESENT in a row's args. Keys outside the set are not this
// module's business — `validateArgs`'s args_schema check already refuses an undeclared argument.
// Returns null when clean, else the refusal reason (a string), so both callers can raise it in
// their own idiom: a typed store error at enqueue, a recorded failure action at fire.
function checkTemplateArgs(args) {
  // `Array.isArray` is not pedantry: an array IS `typeof 'object'`, so without it a row whose args
  // are `["…"]` passes a check that says "must be a JSON object", carries no templatable key, and
  // is then treated as an empty args object. `validateArgs` already spells the same three-part test
  // at the enqueue door; this is the fire-side half, which reads rows that door never saw.
  if (args === null || typeof args !== 'object' || Array.isArray(args)) return 'args must be a JSON object';
  for (const [key, rule] of Object.entries(TEMPLATE_KEYS)) {
    if (!(key in args)) continue;
    const value = args[key];
    if (typeof value === 'string' && CONTROL_RE.test(value)) {
      return `${key} must carry no control character`;
    }
    const reason = rule(value);
    if (reason) return reason;
  }
  return null;
}

// Expand a registered argv against a row's args. Returns `{ argv }` or `{ refused }` — never
// throws, because the fire path records a refusal rather than abandoning the tick.
function expandArgv(argv, args) {
  if (!Array.isArray(argv)) return { refused: 'registered argv is not an array' };
  const bad = checkTemplateArgs(args);
  if (bad) return { refused: bad };

  const out = [];
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (typeof token !== 'string') return { refused: `registered argv carries a non-string token: ${typeof token}` };
    // ⚠ A ROW MAY FILL AN OPERAND, NEVER CHOOSE THE PROGRAM (added C5 review 2026-08-08). argv[0]
    // is the executable — `spawn(argv[0], argv.slice(1))` in `spawn/carrier.js`, which resolves a
    // bare name through PATH. A placeholder there would hand the row that choice, and `entry-seat`
    // and `goal` are bounded only by kebab-case, so `python3`, `curl` and `node` are all legal
    // values. The other four shape properties do NOT cover this one: the argv stays an array, the
    // token stays whole, and the key stays in the closed set — every guarantee holds while the row
    // still picks the binary. It is refused here, in the ONE definition, rather than trusted to the
    // config author, because the `workflows:` entry this mechanism exists to serve is not authored
    // yet and its whole selling point is that one generic entry serves every workflow.
    if (i === 0 && PLACEHOLDER_RE.test(token)) {
      return { refused: `registered argv[0] is the placeholder "${token}" — a row may fill an operand, never choose the program` };
    }
    const m = PLACEHOLDER_RE.exec(token);
    if (!m) {
      // A token that merely CONTAINS `{{` is a malformed placeholder, not a literal. Passing it
      // through would hand the exec a token reading `--flag={{workdir}}` and call it composed.
      if (token.includes('{{')) {
        return { refused: `malformed placeholder token "${token}" — a placeholder must be the WHOLE token` };
      }
      out.push(token);
      continue;
    }
    const key = m[1];
    if (!(key in TEMPLATE_KEYS)) {
      return { refused: `unknown placeholder {{${key}}} — the templatable keys are ${Object.keys(TEMPLATE_KEYS).join(', ')}` };
    }
    if (!(key in args)) {
      return { refused: `placeholder {{${key}}} has no value in the row args` };
    }
    out.push(args[key]);
  }
  return { argv: out };
}

module.exports = {
  TEMPLATE_KEYS,
  MAX_NAME,
  MAX_PATH,
  checkTemplateArgs,
  expandArgv,
};

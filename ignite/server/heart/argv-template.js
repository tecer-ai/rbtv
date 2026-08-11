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
//   5. IDENTITY ADMISSION ON THE FIRE-TOOL PATH (task 7.559, owner ruling
//      `d-owner-7559-design-rulings-0808`). The optional `allow` argument switches admission from
//      GRAMMAR to MEMBERSHIP: a value is admitted because the config author WROTE IT DOWN, never
//      because it matches a shape. Passed → the rules above (1-4) all still hold and the per-key
//      grammar is switched OFF ENTIRELY for that entry; omitted → this module behaves exactly as
//      C5 shipped it.
//
// ⚠ THE TWO CATALOGUE SECTIONS ADMIT VALUES BY DIFFERENT RULES, AND THAT IS DELIBERATE.
// `workflows:` (C5) admits by GRAMMAR — `NAME_RE`, a genuinely name-shaped space of workflow and
// seat names. `tools:` (7.559) admits by IDENTITY, because a fired tool runs with NO sandbox at all
// (`ticker.js` runToolLikeExec passes literal `caps: {}` / `sandbox: {}`) and its operands are
// absolute paths, which no name grammar can bound. MEASURED, not asserted — and the measurement is
// RE-TAKEN EVERY RUN rather than quoted here: arm F10 of `ticker/probes/probe-argv-template.js`
// deletes the membership test from a scratch copy and prints how many of its hostile arms flip from
// refused to composed. Shell metacharacters, traversal, `/etc/passwd`, `--dry-run`, a 10 000-byte
// value, and case and homoglyph near-misses ALL compose under grammar alone. ⚠ NO FIGURE IS WRITTEN
// HERE, ON PURPOSE (task 7.577): this sentence used to say "12" — a design-time unit-level count —
// while the shipped probe measured a different number, and a reader reproducing it had no way to
// tell which was wrong. The arm's own output IS the number. A grammar is "a pattern that looks
// safe"; on this path that is not an admission mechanism.
//
// ⚠ WHERE THE ALLOWLIST MAY LIVE — THE WHOLE SECURITY CONDITION (owner ruling B1). `allow` is read
// from the BOOT-READ MERGED CONFIG (`config/spawn-profiles.yaml` → `loadMergedConfig`, no
// `fs.watch`) and from NOWHERE ELSE. It must NEVER be resolved from a job registration's
// `args_schema`, a runtime settings file, an env var, or a queue row: `authz.canRegisterJob`
// admits any enrolled AGENT token, so an allowlist living there would be extensible BY THE VERY
// AGENTS IT BOUNDS, with no restart and no reviewed diff. Extending the list must keep costing
// exactly what the argv freeze cost — a reviewed diff plus a deliberate daemon restart.
//
// Used at BOTH ends on purpose (defence in depth): `heart-store.js` validateArgs refuses a bad
// value at ENQUEUE, so no such row is ever stored; `ticker.js` launchStartWorkflow re-validates at
// FIRE, because the store can hold rows enqueued before this code existed.

const fs = require('node:fs');
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
// ⚠ THE LEXICAL CONTAINMENT IS BACKED BY A BOOT-TIME RESOLVE (owner ruling
// `d-0811-workdir-symlink-boot-resolve`, option (a); it discharges the reservation this block used
// to carry). The segment test above is necessary and was never sufficient: measured in the C5
// review 2026-08-08, a workdir whose segments read `.rbtv/goals/<x>` but whose `<x>` is a SYMLINK
// pointing elsewhere passed it, and the fired child's cwd was then outside the goals root. So the
// goals root is resolved ONCE at daemon boot — a TRUSTED value, composed from the boot-read
// `default_workdir_root` and never from a row — and cached (`setResolvedGoalsRoot`, called from the
// engine's composition root). Each candidate workdir is then required to resolve INSIDE that cached
// real path.
//
// ⚠ WHAT IS RESOLVED IS THE LONGEST EXISTING PREFIX, AND THAT IS THE WHOLE DESIGN. The two legal
// cases the ruling names are SERVED, not refused:
//   A. A workdir scaffolded but NOT YET ON DISK — `goal_creation_request.py:476` composes
//      `goals_root / <goal-name>` before the scaffold creates it. A goal-name segment that does not
//      exist is never resolved, so it cannot be refused for failing to resolve. Full-path `realpath`
//      — option (c) — is exactly what would refuse this, and the owner DECLINED it.
//   B. A `.rbtv/goals` root that is ITSELF a symlink onto another volume. The boot resolve stores
//      the root's REAL path, so a workdir under the symlinked root resolves to that same real path
//      and is admitted — where a lexical `.rbtv/goals` segment test on the RESOLVED path would have
//      refused it, the resolved path no longer carrying those segments at all.
// The one thing this refuses that the lexical rule admitted is the hostile shape: an EXISTING
// segment under the goals root that resolves out of it.
//
// ⚠ ACCEPTED RESIDUAL, BY RULING, NOT BY OVERSIGHT: a boot-to-spawn TOCTOU window. The root is
// cached at boot, not re-resolved per check, so a root replaced under a running daemon is not seen
// until the next boot. The owner accepted this rather than pay a per-check resolve of the root.
// The exposure both the residual and the closed hole live in is bounded by who can PLANT a symlink
// under the goals root — local filesystem write as the daemon user, strictly more access than this
// rule defends against. A row author cannot reach it: the inbox boundary carries a goal NAME
// through `GOAL_NAME_RE`, which creates a directory and never a link.
//
// ⚠ NO CACHED ROOT ⇒ NO RESOLVE-COMPARE, and the rule is byte-for-byte what it was before. That is
// the case for every consumer that never boots an engine (the probes' fixture roots, a unit-level
// caller), and it is why this change refuses nothing that was admitted before on those paths.
//
// ⚠ `sanctionedRoot` (task 7.562, owner ruling `d-owner-board-clear-0809`) is the configured
// `default_workdir_root`, admitted by EXACT EQUALITY and never as a prefix. "Anything under the
// workspace root" would be no containment at all — that root holds `.rbtv/config/.env` and the
// source tree. Passed by the fire-tool doors, which know it; omitted elsewhere, where the rule is
// exactly what it has always been. Widening only, so no value accepted before is refused now.
// The boot-resolved goals root, or null when nothing has booted an engine in this process.
// ponytail: module-global, because the two doors (`ticker.js` launchFireTool, `heart-store.js`
// validateArgs) call the validator with a fixed arity this change is not allowed to widen — and
// one process runs one engine. Thread it as an argument if that ever stops being true.
let resolvedGoalsRoot = null;

// Called ONCE, at the engine's composition root, with the boot-read `default_workdir_root` (the
// workspace root). Resolves `<root>/.rbtv/goals` and caches its REAL path. A falsy root, or a root
// whose goals tree is not on disk yet, leaves the cache null — the resolve-compare then never runs
// and the rule is exactly the lexical one, which is the pre-ruling behaviour and refuses nothing.
function setResolvedGoalsRoot(workspaceRoot) {
  resolvedGoalsRoot = null;
  if (typeof workspaceRoot !== 'string' || workspaceRoot.length === 0) return null;
  try {
    resolvedGoalsRoot = fs.realpathSync(path.join(workspaceRoot, '.rbtv', 'goals'));
  } catch {
    resolvedGoalsRoot = null;
  }
  return resolvedGoalsRoot;
}

// Does `value` resolve inside the cached goals root? Climb to the LONGEST EXISTING prefix and
// resolve THAT: a segment that does not exist cannot be a symlink, so leaving it unresolved costs
// nothing and is what admits legal case A. Only ENOENT climbs — any other error is a refusal,
// because a path we cannot resolve is not a path we can vouch for.
// `root` is PARAMETERIZED (task fA-4, D-1) so the seat-cage grant resolvers in
// `server/spawn/spawn.js` can ask this same question of a different containment — a specific
// `{goalDir}`, or the workspace root — instead of minting a third containment rule. It defaults to
// the cached goals root, so the fire-tool caller below is byte-unchanged. The root MUST already be
// a REAL path (`setResolvedGoalsRoot` realpaths it; a caller passing its own root realpaths it
// first), otherwise a symlinked root would never equal the resolved candidate and every value
// would be refused.
//
// ⚠ A falsy root returns FALSE, never true: "no root to check against" is not a pass. The one
// pre-existing caller is already guarded by `resolvedGoalsRoot &&`, so this only bounds new ones.
//
// ⚠ `path.dirname`, not `path.posix.dirname`: on POSIX — the only place the daemon runs — the two
// are identical for the absolute paths this walks, so the fire-tool behaviour is byte-for-byte what
// it was. On Windows `path.posix.dirname('C:\\a\\b')` returns `.` immediately, which collapsed the
// climb and made the check refuse everything; native `dirname` climbs correctly on both, which is
// what lets this be exercised off the VPS at all.
function resolvesInsideGoalsRoot(value, root = resolvedGoalsRoot) {
  if (!root) return false;
  let candidate = value;
  for (;;) {
    try {
      const real = fs.realpathSync(candidate);
      return real === root || real.startsWith(root + path.sep);
    } catch (err) {
      if (err.code !== 'ENOENT') return false;
      const parent = path.dirname(candidate);
      if (parent === candidate) return false;
      candidate = parent;
    }
  }
}

function workdirRule(value, sanctionedRoot = null) {
  if (typeof value !== 'string') return `workdir must be a string, got ${typeof value}`;
  if (value.length === 0 || value.length > MAX_PATH) {
    return `workdir must be 1..${MAX_PATH} characters, got ${value.length}`;
  }
  if (!path.posix.isAbsolute(value)) return 'workdir must be an absolute path';
  const raw = value.split('/');
  if (raw.includes('..')) return 'workdir must carry no ".." segment';
  if (sanctionedRoot && value === sanctionedRoot) return null;
  const parts = path.posix.normalize(value).split('/');
  const i = parts.indexOf('.rbtv');
  if (i === -1 || parts[i + 1] !== 'goals' || !parts[i + 2]) {
    // The refusal NAMES the sanctioned root, because the one thing no read can enumerate is a row
    // an operator hand-registered and never documented (7.562 §3.5) — that operator must read what
    // IS allowed rather than guess.
    return sanctionedRoot
      ? `workdir must be exactly the configured default_workdir_root (${sanctionedRoot}) `
        + 'or resolve inside a `.rbtv/goals/<goal>` containment'
      : 'workdir must resolve inside a `.rbtv/goals/<goal>` containment';
  }
  // The resolve-compare (ruling `d-0811-workdir-symlink-boot-resolve`). LAST, so the segment test
  // still answers first and every refusal reason above is unchanged — and skipped entirely when no
  // engine boot cached a root.
  if (resolvedGoalsRoot && !resolvesInsideGoalsRoot(value)) {
    return 'workdir must resolve inside the boot-resolved goals root '
      + `(${resolvedGoalsRoot}) — a segment on this path is a symlink out of it`;
  }
  return null;
}

// ⚠ THIS IS THE ENTIRE SECURITY CHECK of task 7.559 — three tests, and the third is the boundary.
// A row does not SUPPLY a string, it SELECTS a member of a list a human wrote in a reviewed diff,
// so the exact bytes reaching the command line are bytes the config author typed. `includes` is
// `===` identity: no case folding, no trimming, no normalisation, no prefix match. A near miss is a
// miss — that is the property a grammar cannot have.
function allowValue(key, permitted, value) {
  // An entry that declares a key with nothing in it admits NOTHING. Failing open here would turn a
  // typo (`goal:` with an empty list) into an unbounded operand, which is the whole defect class.
  // ⚠ TWO REFUSALS, ONE OUTCOME (task 7.585). `Array.isArray` STAYS FIRST — that ordering is the
  // security condition, and neither branch changes what is admitted. The split is for the OPERATOR:
  // a per-key value that is a scalar (`goal: "/some/path"` where `goal: ["/some/path"]` was meant)
  // was reported as an empty list, so the reader was sent to fix an emptiness that was never there.
  if (!Array.isArray(permitted)) {
    return `${key} does not carry a list of permitted values on this entry — got `
      + `${permitted === null ? 'null' : typeof permitted}, and a value that is not a list admits nothing`;
  }
  if (permitted.length === 0) {
    return `${key} has an empty positive list on this entry — an empty positive list admits nothing`;
  }
  if (typeof value !== 'string') {
    const seen = Array.isArray(value) ? 'array' : (value === null ? 'null' : typeof value);
    return `${key} must be a string, got ${seen}`;
  }
  if (!permitted.includes(value)) {
    return `${key} is not on this entry's allowlist (${permitted.length} permitted value(s))`;
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
// `allow` (7.559) is the entry's `args_allowlist`, and its SHAPE IS A MAPPING OF KEY → LIST:
// `{ <key>: [ …permitted literal values… ] }`. Anything else truthy — a scalar, a bare list — is a
// config typo and is refused as a shape error by the first test below (7.577), never raised.
// When present, the keys it names are checked by MEMBERSHIP and the grammar rules above never run;
// a key it does not name carries no value rule here, because such a key can never reach the argv —
// the placeholder branch in `expandArgv` refuses `{{key}}` BY NAME when the key has no allowlist on
// that entry. So the admissible operand set is exactly the allowlist, and nothing else is reachable.
function checkTemplateArgs(args, allow = null) {
  // ⚠ A NON-MAPPING `allow` IS REFUSED AS A SHAPE ERROR — NEVER THROWN (task 7.577). A SCALAR
  // `args_allowlist:` (`goal`, `5`, `true` — the YAML typo where a mapping of key → list is meant)
  // made `key in allow` raise a TypeError out of `expandArgv`, against the never-throws contract
  // that function's own header states. `tick()` is `try/finally` with NO `catch`, so the throw
  // abandoned enforce, broadcast and `recordTick` for the WHOLE tick and repeated every cadence
  // until the config was fixed. ⚠ THE FIX IS A REFUSAL, NOT A RESCUE: catching it downstream would
  // leave this module throwing and merely hide it — the property being restored is the one written
  // above `expandArgv`, that a refusal is RECORDED rather than raised. Refused HERE because this is
  // the gate `expandArgv` calls before its first `in` on `allow` AND the one `heart-store.js`
  // shares, so one test covers every caller.
  //
  // The predicate is the one `heart/catalogue-paths.js` already applies to this same field at boot
  // — an array is `typeof 'object'` and is still not a mapping of key → list, the same reason the
  // `args` test below carries `Array.isArray`. A FALSY `allow` keeps meaning "this entry declares
  // no allowlist" (ticker.js normalises with `|| null`), so the frozen default narrows by nothing.
  if (allow && (typeof allow !== 'object' || Array.isArray(allow))) {
    return 'args_allowlist must be a mapping of key to a list of permitted values, got '
      + `${Array.isArray(allow) ? 'array' : typeof allow}`;
  }
  // `Array.isArray` is not pedantry: an array IS `typeof 'object'`, so without it a row whose args
  // are `["…"]` passes a check that says "must be a JSON object", carries no templatable key, and
  // is then treated as an empty args object. `validateArgs` already spells the same three-part test
  // at the enqueue door; this is the fire-side half, which reads rows that door never saw.
  if (args === null || typeof args !== 'object' || Array.isArray(args)) return 'args must be a JSON object';
  const keys = allow ? Object.keys(allow) : Object.keys(TEMPLATE_KEYS);
  for (const key of keys) {
    if (!(key in args)) continue;
    const value = args[key];
    // Unconditional in BOTH modes and ahead of the per-key rule, so a newline can never reach the
    // systemd unit properties the carrier writes — including on an allowlisted key, where it would
    // otherwise be reported as a mere non-membership and teach the reader the wrong reason.
    if (typeof value === 'string' && CONTROL_RE.test(value)) {
      return `${key} must carry no control character`;
    }
    // No sanctioned root is threaded here on purpose: this is the `start-workflow` grammar path,
    // whose every live row already supplies a `.rbtv/goals/…` workdir (measured — 4 of 7 rows, all
    // W2). Widening it too would be a change nothing asks for.
    const reason = allow ? allowValue(key, allow[key], value) : TEMPLATE_KEYS[key](value);
    if (reason) return reason;
  }
  return null;
}

// ── Task 7.562 · THE FIRE-TOOL WORKDIR DOOR (owner rulings `d-owner-7559-design-rulings-0808` C1,
// `d-owner-board-clear-0809`; design `dossiers/7562-workdir-governance-design.md`) ───────────────
//
// `fire-tool` never reaches `checkTemplateArgs`'s grammar: an entry with no `args_allowlist` skips
// the call entirely, and an entry WITH one switches the per-key grammar OFF. So `args.workdir` —
// a value whoever enqueues the row chooses — reached `--property WorkingDirectory=` ungoverned,
// on a path that runs with NO sandbox (`ticker.js` runToolLikeExec passes literal `caps: {}` /
// `sandbox: {}`; `buildBwrapArgv` count in that file is 0). This is that one gap, wired to the
// validator above rather than to a second parallel one.
//
// ⚠⚠ IT GOVERNS THE SUPPLIED VALUE, NEVER THE RESOLVED ONE, and that is the whole outage
// avoidance. The fire path resolves `args.workdir || default_workdir_root`; the fallback is
// server-composed from the unit's environment and boot-validated (`index.js` refuses the seed
// placeholder), so it is not caller-influenceable and needs no gate. MEASURED on the live store
// 2026-08-10 (25,999 rows, exec_id 1..25999, no gaps): of 25,648 fire-tool executions ever fired,
// exactly ONE supplied a workdir — `edge-runner` exec 25552, and its value was the configured
// `default_workdir_root` exactly. A rule on the SUPPLIED value refuses nothing that has ever run;
// a rule on the RESOLVED value would refuse every one of them.
function checkFireToolWorkdir(args, sanctionedRoot = null) {
  if (args === null || typeof args !== 'object' || Array.isArray(args)) return null;
  if (!Object.hasOwn(args, 'workdir')) return null;
  const value = args.workdir;
  if (typeof value === 'string' && CONTROL_RE.test(value)) return 'workdir must carry no control character';
  return workdirRule(value, sanctionedRoot);
}

// Expand a registered argv against a row's args. Returns `{ argv }` or `{ refused }` — never
// throws, because the fire path records a refusal rather than abandoning the tick.
function expandArgv(argv, args, allow = null) {
  if (!Array.isArray(argv)) return { refused: 'registered argv is not an array' };
  const bad = checkTemplateArgs(args, allow);
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
    // ⚠ REFUSED BY NAME, not by a grammar complaint. An entry that templates a key it declares no
    // allowlist for has no admissible value at all, and saying so is the point: the first draft let
    // the grammar answer first and produced "goal must be 1..64 characters" — a refusal that teaches
    // the reader the value was merely too long, when the truth is that this entry admits nothing.
    if (allow && !(key in allow)) {
      return { refused: `placeholder {{${key}}} has no allowlist on this entry` };
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
  checkFireToolWorkdir,
  expandArgv,
  setResolvedGoalsRoot,
  // Exported for the seat-cage grant resolvers (`server/spawn/spawn.js`), which must answer the
  // SAME symlink-aware containment question against their own roots (fA-4 D-1). One rule, three
  // callers — a second spelling of "does this path really live under that one" is a second wall.
  resolvesInsideGoalsRoot,
};

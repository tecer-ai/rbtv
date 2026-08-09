'use strict';

// probe-defect-fix.js — the fix-wave probes for the daemon half (campaign issues S-2, S-3, S-6(b)).
//
// WHAT THIS SCORES OVER, stated per defect, because "probes pass" reads as a clean class and is not:
//
//   S-2(a) registration — every action type whose enqueue requires a named argument is refused at
//       REGISTRATION when its args_schema does not declare it. The red half is the shape that
//       actually happened: the same registration SUCCEEDS today's-behaviour-style and then every
//       enqueue of it dies, which this probe demonstrates rather than asserts. It also scores the
//       ORDERING — a duplicate id must still refuse E_JOB_EXISTS, because the certified create-only
//       behaviour must not change shape underneath this new check.
//   S-2 fireable — `jobFireability` over the EXACT shape of the two dead ids live on this box
//       (`fire-tool` + `args_schema: {}`), a healthy row, and a disabled row. It does not score the
//       wire surface end-to-end; the annotation site in dispatch.js is one `.map()` over this
//       function, and the function is what can be wrong.
//   S-3 wording — a refused sender is told the predicate ACTUALLY enforced and the kind it was SEEN
//       as, and the word `master` appears in no caller-visible refusal. Scored over all three sender
//       kinds plus a null sender.
//   S-6(b) catalogue paths — the validator flags a deliberately broken entry (the red half), passes
//       a good one, ignores template slots, and reports the LIVE config's real count. That live
//       number is printed, not asserted: today it is zero because the ephemeral folders still exist,
//       and a probe that asserted zero would go red the day the defect it guards against occurs.
//
// Everything runs in a temp directory. The live heart store and the live config are never written.
//
// Run: node probe-defect-fix.js   ->  exit 0 all green, exit 1 on any failure.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');

const { HeartStore, jobFireability } = require('../heart-store');
const { validateCataloguePaths } = require('../catalogue-paths');
const { createAuthzPolicy } = require('../../internal-api/authz');

const results = [];

function check(label, cond, detail = '') {
  results.push([Boolean(cond), label]);
  console.log((cond ? 'ok    ' : 'FAIL  ') + label + (!cond && detail ? `\n        ${detail}` : ''));
}

function attempt(fn) {
  try {
    return { ok: true, value: fn() };
  } catch (err) {
    return { ok: false, code: err.code, message: err.message };
  }
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-defect-fix-'));
const store = new HeartStore({
  dbPath: path.join(dir, 'heart.db'),
  tools: { 'real-tool': { argv: ['/bin/true'] } },
  profiles: { 'real-profile': { workdir_root: dir } },
});

// ── S-2(a) ───────────────────────────────────────────────────────────────────────────────
const CASES = [
  ['fire-tool', 'tool'],
  ['launch-agent', 'profile'],
  ['start-workflow', 'workflow'],
];
for (const [actionType, needed] of CASES) {
  const r = attempt(() => store.registerJob({
    jobId: `empty-${actionType}`, actionType, function: actionType,
  }));
  check(`S-2(a): registering a ${actionType} job with the DEFAULT empty args_schema is REFUSED — ` +
        `it would report enabled=1 forever and never fire, with no in-place repair`,
    !r.ok && r.code === 'E_BAD_ARGS' && r.message.includes(`"${needed}"`),
    `${r.code || 'registered'} ${r.message || ''}`);
  check(`S-2(a): ...and no row landed for ${actionType} — a refusal that wrote would be worse than ` +
        `the defect`, store.getJob(`empty-${actionType}`) === null);
}

const good = attempt(() => store.registerJob({
  jobId: 'good-tool', actionType: 'fire-tool', function: 'fire-tool',
  argsSchema: JSON.stringify({ required: { tool: 'string' }, optional: { workdir: 'string' } }),
}));
check('S-2(a) control: a fire-tool job that DECLARES `tool` still registers — the check is on the ' +
      'declaration, not on fire-tool', good.ok && store.getJob('good-tool') !== null,
  `${good.code || ''} ${good.message || ''}`);

const enq = attempt(() => store.enqueue({
  jobId: 'good-tool', args: JSON.stringify({ tool: 'real-tool' }),
  triggerKind: 'scheduled', runAt: '2030-01-01T00:00:00Z', enqueuedBy: 'probe',
}));
check('S-2(a) control: ...and it can actually be ENQUEUED, which is the thing the refused shape ' +
      'could never do. A green suite over a path that never succeeded is still green',
  enq.ok, `${enq.code || ''} ${enq.message || ''}`);

// The ORDERING guard: create-only must still refuse a duplicate first, with its certified code.
const dup = attempt(() => store.registerJob({
  jobId: 'good-tool', actionType: 'send-message', function: 'OVERWRITTEN', argsSchema: '{}',
}));
check('S-2(a): a DUPLICATE id still refuses E_JOB_EXISTS, not the new schema error — the new check ' +
      'sits after the duplicate check so certified create-only behaviour keeps its shape',
  !dup.ok && dup.code === 'E_JOB_EXISTS', `${dup.code} ${dup.message}`);

// The RED HALF: the exact live shape, and why it is unrepairable. Written straight to the table,
// bypassing registerJob, because that is how the two live dead ids got there — before the gate.
store.db.exec(`INSERT INTO jobs (job_id, action_type, function, args_schema, description, enabled, created_at, updated_at)
  VALUES ('legacy-dead', 'fire-tool', 'fire-tool', '{}', NULL, 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')`);
const legacy = store.getJob('legacy-dead');
const legacyEnq = attempt(() => store.enqueue({
  jobId: 'legacy-dead', args: JSON.stringify({ tool: 'real-tool' }),
  triggerKind: 'scheduled', runAt: '2030-01-01T00:00:00Z', enqueuedBy: 'probe',
}));
check('S-2 red half: a row already in that shape reads enabled=1 AND every enqueue of it dies ' +
      '"unknown argument: tool" — this is what the two live dead ids do, permanently',
  legacy.enabled === 1 && !legacyEnq.ok && legacyEnq.code === 'E_BAD_ARGS'
  && /unknown argument: tool/.test(legacyEnq.message), `${legacyEnq.code} ${legacyEnq.message}`);
check('S-2 masking, recorded because it misled a ledger: the schema failure fires BEFORE the ' +
      'catalogue lookup, so the tool check is unreachable on exactly the rows people test — the ' +
      'tool name IS validated at enqueue (E_UNKNOWN_TOOL), it was simply hidden',
  (() => {
    const r = attempt(() => store.enqueue({
      jobId: 'good-tool', args: JSON.stringify({ tool: 'no-such-tool' }),
      triggerKind: 'scheduled', runAt: '2030-01-01T00:00:00Z', enqueuedBy: 'probe',
    }));
    return !r.ok && r.code === 'E_UNKNOWN_TOOL';
  })());

// ── S-2 fireable ─────────────────────────────────────────────────────────────────────────
const deadVerdict = jobFireability(legacy);
check('S-2: `fireable` is FALSE for the dead shape, where `enabled` says 1 — enabled is evidence a ' +
      'row EXISTS, never that it can RUN',
  deadVerdict.fireable === false && /declares no `tool`/.test(deadVerdict.reason),
  JSON.stringify(deadVerdict));
check('S-2: ...and the reason says the id CANNOT be repaired in place, which is the operator\'s ' +
      'actual next question', /CANNOT be repaired/.test(deadVerdict.reason));
check('S-2: `fireable` is TRUE for a healthy row',
  jobFireability(store.getJob('good-tool')).fireable === true);
check('S-2: a disabled row is not fireable, and says so plainly',
  jobFireability({ ...legacy, enabled: 0 }).reason === 'disabled');

// ── S-3 ──────────────────────────────────────────────────────────────────────────────────
const policy = createAuthzPolicy();
const bridge = policy.canRegisterJob({ sender: { id: 'chat', kind: 'bridge' } });
check('S-3: a BRIDGE sender is told the predicate ACTUALLY enforced and the kind it was SEEN as',
  bridge.allowed === false && /owner or an enrolled AGENT token/.test(bridge.reason)
  && /you are a bridge token/.test(bridge.reason), bridge.reason);
check('S-3: the word `master` appears in NO caller-visible refusal — naming a principal the ' +
      'runtime cannot prove is the defect itself (PRINCIPALS.master: enforcedInV1 false, provenBy null)',
  !/master/i.test(bridge.reason)
  && !/master/i.test(policy.canRegisterJob({ sender: null }).reason),
  bridge.reason);
check('S-3: a null sender is described honestly rather than as a policy',
  /no attested sender/.test(policy.canRegisterJob({ sender: null }).reason));
check('S-3 control: an AGENT token is still ALLOWED — the wording change did not move the gate, ' +
      'which is the whole point of it being a wording change',
  policy.canRegisterJob({ sender: { id: 'seat', kind: 'agent' } }).allowed === true
  && policy.canRegisterJob({ sender: { id: 'h', kind: 'owner' } }).allowed === true);

// ── S-6(b) ───────────────────────────────────────────────────────────────────────────────
const missing = path.join(dir, 'seats', 'closed-seat', 'throwaway', 'pkg');
const broken = validateCataloguePaths({
  tools: {
    'points-at-a-closed-seat': { argv: ['/usr/bin/python3', '/bin/true', '--package', missing] },
  },
});
check('S-6(b) RED HALF: an entry pointing into a folder that no longer exists is FLAGGED, naming ' +
      'the entry, the argv index and the path — it used to produce silence',
  broken.length === 1 && broken[0].name === 'points-at-a-closed-seat'
  && broken[0].path === missing && broken[0].index === 3, JSON.stringify(broken));
check('S-6(b): a fully-resolvable entry produces NO finding',
  validateCataloguePaths({ tools: { ok: { argv: ['/usr/bin/python3', '/bin/true'] } } }).length === 0);
check('S-6(b): a template slot is NOT reported as missing — a false ERROR would train readers to ' +
      'ignore the check',
  validateCataloguePaths({ tools: { t: { argv: ['/usr/bin/python3', '{workdir}/x'] } } }).length === 0);
check('S-6(b): an entry with no argv at all is reported rather than skipped',
  validateCataloguePaths({ tools: { t: {} } }).length === 1);

// ── S-6(b) · task 7.559 — THE COVERAGE MUST SURVIVE THE MOVE INTO `args_allowlist` ───────────
// 7.559 takes the edge-runner's goal path OUT of `argv` and puts it on an allowlist. The argv walk
// skips any token containing `{`, so WITHOUT the allowlist walk that path would leave the boot
// check silently — the same invisibility this whole module exists to end, reintroduced by the very
// change that needed it. These arms are that regression, written as a before/after on ONE path.
const ALLOW_ARGV = ['/usr/bin/python3', '/bin/true', '--goal', missing];
const beforeMove = validateCataloguePaths({ tools: { 'edge-shaped': { argv: ALLOW_ARGV } } });
const afterMove = validateCataloguePaths({
  tools: {
    'edge-shaped': {
      argv: ['/usr/bin/python3', '/bin/true', '--goal', '{{goal}}'],
      args_allowlist: { goal: [missing] },
    },
  },
});
check('S-6(b)/7.559 CONTROL: the same missing path IS flagged while it still lives in argv — the ' +
      'before half of the move, without which the after half proves nothing',
  beforeMove.length === 1 && beforeMove[0].path === missing, JSON.stringify(beforeMove));
check('S-6(b)/7.559 RED HALF: after the path moves from `argv` into `args_allowlist` it is STILL ' +
      'flagged — the boot existence check follows the value, and the `{{goal}}` token that replaced ' +
      'it in argv is correctly skipped rather than double-reported',
  afterMove.length === 1 && afterMove[0].path === missing && afterMove[0].key === 'goal'
  && afterMove[0].index === null && /allowlisted path does not exist/.test(afterMove[0].why),
  JSON.stringify(afterMove));
check('S-6(b)/7.559: an allowlisted path that EXISTS produces NO finding — the check is existence, ' +
      'not "any entry with an allowlist is suspect"',
  validateCataloguePaths({
    tools: { ok: { argv: ['/usr/bin/python3', '/bin/true'], args_allowlist: { goal: ['/bin/true'] } } },
  }).length === 0);
check('S-6(b)/7.559: a NON-absolute allowlist member is not reported — a goal NAME is not a path, ' +
      'and a false ERROR trains readers to ignore the check',
  validateCataloguePaths({
    tools: { t: { argv: ['/usr/bin/python3', '/bin/true'], args_allowlist: { goal: ['some-goal-name'] } } },
  }).length === 0);
check('S-6(b)/7.559: a malformed `args_allowlist` (not an object / not a list) is skipped rather ' +
      'than thrown on — a boot check that crashes the boot is worse than the silence it replaced',
  validateCataloguePaths({
    tools: {
      a: { argv: ['/bin/true'], args_allowlist: ['not', 'an', 'object'] },
      b: { argv: ['/bin/true'], args_allowlist: { goal: 'not-a-list' } },
      c: { argv: ['/bin/true'], args_allowlist: { goal: [null, 7, { x: 1 }] } },
    },
  }).length === 0);

// The LIVE config: reported, never asserted. Asserting zero would go red on the day the defect
// this guards against actually happens, which is precisely when the check must stay green.
const liveCfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
const liveFindings = validateCataloguePaths(liveCfg);
// The denominator counts BOTH surfaces since 7.559 — counting only argv would understate exactly
// the paths that moved onto an allowlist, so the report would look complete while shrinking.
const absolutes = (e) => [
  ...(e.argv || []),
  ...Object.values((e.args_allowlist && typeof e.args_allowlist === 'object' && !Array.isArray(e.args_allowlist))
    ? e.args_allowlist : {}).flatMap((v) => (Array.isArray(v) ? v : [])),
].filter((x) => typeof x === 'string' && x.startsWith('/'));
const liveRefs = Object.values(liveCfg.tools || {}).flatMap(absolutes).length;
const liveAllowed = Object.values(liveCfg.tools || {})
  .flatMap((e) => Object.values((e && e.args_allowlist) || {}).flatMap((v) => (Array.isArray(v) ? v : []))).length;
console.log(`\nLIVE CONFIG (reported, not asserted): ${liveFindings.length} broken reference(s) ` +
            `over ${liveRefs} absolute path(s) in ${Object.keys(liveCfg.tools || {}).length} tool entries ` +
            `(${liveAllowed} of them selectable per-run via args_allowlist).`);
for (const f of liveFindings) {
  console.log(`  broken: ${f.section}.${f.name} ${f.key ? `args_allowlist.${f.key}` : `argv[${f.index}]`} ${f.path}`);
}

store.close();
fs.rmSync(dir, { recursive: true, force: true });

const failed = results.filter(([ok]) => !ok);
console.log(`\nprobe-defect-fix (daemon): ${failed.length ? 'FAIL' : 'PASS'} ` +
            `(${results.length - failed.length}/${results.length} checks)`);
for (const [, l] of failed) console.log('  failed: ' + l);
process.exit(failed.length ? 1 : 0);

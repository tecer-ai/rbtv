#!/usr/bin/env node
'use strict';

// `cast route` self-check — REWRITTEN 2026-08-20 for the redesigned selector. The old suite
// tested the retired algorithm (bands, pins, halt seams, footprint) and was deleted with it.
//
// WHAT IS TESTED WHERE (owner ruling 2026-08-22):
//   * LOGIC arms route against a FIXTURE table this suite writes and owns (FIXTURE below). The
//     shipped models.csv is the OWNER'S DATA — they re-rank the roster whenever they like — so an
//     arm that pinned a verdict off it only restated a cell they had just edited. That design
//     reddened 16 arms on the 2026-08-22 re-curation and taught nobody anything: the checks broke
//     because the data changed, never because the selector did.
//   * The SHIPPED table gets ONE arm, at the bottom: VALIDATION, not verdicts — every row joins
//     catalog.js, every cell is in its vocabulary, no duplicates, every class still has a routable
//     row, and loading it emits NO warning. That is the half that can be wrong without anyone
//     noticing (a decimal comma silently shifted four rows out of routing that same day).
//
// Hermetic environment (availability is a PRESENCE test, never a spend): api keys are pinned to
// synthetic placeholders and XDG_DATA_HOME points at an empty dir, so this box's real opencode
// credential store cannot decide a verdict. Available in these runs: every claude + codex row
// (cli-login), the opencode deepseek + google rows and both api rows (env keys). Unavailable:
// zai (glm), sakana (fugu), xai (grok), kimi (k3).

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const TOOL = path.join(__dirname, 'cast.js');
const EMPTY_XDG = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-xdg-'));
const ENV = {
  ...process.env,
  DEEPSEEK_API_KEY: 'test-fake-not-real',
  GEMINI_API_KEY: 'test-fake-not-real',
  XDG_DATA_HOME: EMPTY_XDG,
};

// --- the fixture table -------------------------------------------------------------------------
// cwd is what selects a table: route resolves the vault root from cwd first, and a per-vault
// override file there REPLACES the shipped CSV. So the suite makes itself a scratch vault, writes
// its own table into it, and every logic arm runs there — the shipped models.csv is reached only
// by the validation arm, which passes __dirname explicitly.
//
// The table is built so each arm has ONE right answer and no tie, and so every axis has a
// discriminating pair: web Y vs N, cli vs api, a blank cost, an image row, and one row (k3, on a
// kimi credential ENV does not fake) that must drop at availability.
const FIXTURE = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-fixture-'));
fs.writeFileSync(path.join(FIXTURE, 'rbtv.json'), '{"rbtv_version":"test"}\n');
const FIXTURE_CSV = path.join(FIXTURE, '.rbtv', 'config', 'modules', 'core', 'sub-agents', 'models.csv');
fs.mkdirSync(path.dirname(FIXTURE_CSV), { recursive: true });
fs.writeFileSync(FIXTURE_CSV, [
  'mode,harness,model,efforts,image,web,level,reasoning,coding,cost,use,quality-override,price-override',
  'cli,claude,fable-5,5,N,Y,SOTA,7,7,50,route,N,N',
  'cli,claude,opus-5,5,N,Y,L1,6,6,25,route,N,N',
  'cli,codex,gpt-5.6-sol,5,N,Y,L1,5,5,20,route,N,N',
  'cli,claude,sonnet-5,5,N,Y,L2,5,5,10,route,N,N',
  'cli,codex,gpt-5.6-terra,5,N,N,L2,4,4,5,route,N,N',
  'cli,opencode,k3,3,N,N,L2,5,5,15,route,N,N',
  'cli,codex,gpt-5.6-luna,5,N,Y,L3,3,2,1.2,route,N,N',
  'cli,opencode,deepseek-v4-pro,4,N,N,L3,3,3,3.96,route,N,N',
  'cli,claude,haiku-4-5,0,N,Y,L3,3,3,,route,N,N',
  'api,api,gemini-3.5-flash,0,N,Y,L3,3,3,9,route,N,N',
  'cli,opencode,gemini-3.1-pro-preview,3,Y,N,L4,0,0,,route,N,N',
  '',
].join('\n'));

function route(flags, cwd = FIXTURE) {
  const res = spawnSync('node', [TOOL, 'route', ...flags], { encoding: 'utf8', env: ENV, cwd });
  assert.ok(res.stdout, `route printed nothing; stderr: ${res.stderr}`);
  return { ...JSON.parse(res.stdout), _status: res.status, _stderr: res.stderr };
}

const pair = (v) => `${v.harness}/${v.model}/${v.mode}`;
const dropped = (v, stage) => (v.explain || [])
  .filter((e) => e.stage === stage && e.action === 'drop')
  .map((e) => `${e.harness}/${e.model}`);

// --- the three job flags are REQUIRED; --optimize has a ruled default --------------------------
{
  const v = route(['--access', 'open']);
  assert.strictEqual(v._status, 1, 'an unanswered interview must exit 1');
  assert.strictEqual(v.error, 'malformed_request');
  assert.strictEqual(v.details.length, 2, `expected 2 missing flags (--type, --class), got ${JSON.stringify(v.details)}`);
  assert.ok(!v.details.some((d) => /--optimize/.test(d)), '--optimize is optional since 2026-08-21');
  const typo = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'best']);
  assert.strictEqual(typo.error, 'malformed_request', 'an omitted --optimize defaults; a WRONG one still refuses');
  assert.ok(/--optimize must be one of/.test(typo.details[0]), typo.details[0]);

  const bad = route(['--access', 'sideways', '--type', 'code', '--class', 'bounded', '--optimize', 'price']);
  assert.strictEqual(bad.error, 'malformed_request');
  assert.ok(/--access must be one of/.test(bad.details[0]), bad.details[0]);
}

// --- price-optimized mechanical code -----------------------------------------------------------
// Levels L2+L3; the cheapest priced row across them is luna at 1.2. Effort 1, and effort_is_floor
// false — only planner floors.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'mechanical', '--optimize', 'price']);
  assert.strictEqual(v._status, 0, `expected a verdict: ${JSON.stringify(v)}`);
  assert.strictEqual(v.verdict, 'route');
  assert.strictEqual(pair(v), 'codex/gpt-5.6-luna/cli');
  assert.strictEqual(v.effort, 1);
  assert.strictEqual(v.effort_is_floor, false);
}

// --- a row whose credential does not resolve drops at availability -------------------------------
// k3 rides a kimi credential ENV does not fake, and it is the best-scoring L2 row in the fixture —
// so if availability ever stopped running, this arm's verdict would change.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.ok(dropped(v, 'availability').includes('opencode/k3'), JSON.stringify(dropped(v, 'availability')));
  assert.ok(!/k3/.test(JSON.stringify(v.alternates)), 'an unavailable row must not survive as a backup');
}

// --- the DEFAULT is price, for every class (owner ruling 2026-08-22) ---------------------------
// Replaces the tiered SOTA/L1-on-price + L2/L3-on-quality default of 2026-08-21. Omitting
// --optimize now means exactly `--optimize price`, so the invariant to hold is IDENTITY: for the
// same interview, the two must answer the same thing, class by class. The class's levels are all
// that stands between a job and the cheapest model on the roster.
{
  for (const cls of ['planner', 'broad', 'bounded', 'mechanical']) {
    for (const type of ['code', 'text']) {
      const base = ['--access', 'bounded', '--type', type, '--class', cls];
      const dflt = route(base);
      const priced = route([...base, '--optimize', 'price']);
      assert.strictEqual(dflt._status, 0, JSON.stringify(dflt));
      assert.deepStrictEqual({ ...dflt, _stderr: '' }, { ...priced, _stderr: '' },
        `${cls}/${type}: the default must answer exactly what --optimize price answers`);
    }
  }

  // The trace still says which one the caller asked for — an --explain reader can tell an omitted
  // flag from an explicit one, even though the ranking is the same.
  const mech = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--explain']);
  assert.strictEqual(pair(mech), 'codex/gpt-5.6-luna/cli', 'mechanical default = the cheapest L2/L3 row');
  const rank = mech.explain.find((e) => e.stage === 'optimize' && e.action === 'rank');
  assert.strictEqual(rank.optimize, 'default');
  assert.ok(/price, for every class/.test(rank.rule || ''), JSON.stringify(rank));
  // A blank cost is excluded from the default exactly as it is from an explicit price pick.
  assert.ok(dropped(mech, 'optimize').includes('claude/haiku-4-5'), JSON.stringify(dropped(mech, 'optimize')));

  // THE BEHAVIOUR THAT CHANGED, pinned so it cannot drift back silently: in a class spanning two
  // levels, the default now takes the cheaper LOWER-level row. Under the retired tiered rule the
  // whole SOTA/L1 band ranked first, so bounded could never answer with an L2.
  const bounded = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--explain']);
  assert.strictEqual(pair(bounded), 'codex/gpt-5.6-terra/cli', 'bounded default = cheapest of L1+L2, level no longer breaks the tie');
  const order = bounded.explain.find((e) => e.stage === 'optimize' && e.action === 'rank').order;
  assert.ok(order.indexOf('codex/gpt-5.6-terra') < order.indexOf('codex/gpt-5.6-sol'),
    `a cheap L2 now outranks every L1 under the default: ${JSON.stringify(order)}`);

  // Batch: an omitted optimize on a seat takes the same default as the flag form.
  const b = routeBatch([{ name: 'm', access: 'bounded', type: 'code', class: 'mechanical' }]);
  assert.strictEqual(b._status, 0, JSON.stringify(b));
  assert.strictEqual(`${b.seats[0].harness}/${b.seats[0].model}`, 'codex/gpt-5.6-luna');
}

// --- max quality NEVER leaves the class's own levels --------------------------------------------
// class=bounded is L1+L2. fable-5 is SOTA and available, and it must NOT be picked: a bounded
// executor at max quality gets the best L1 (opus-5), never SOTA. Only planner reaches SOTA.
{
  const v = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(v), 'claude/opus-5/cli');
  assert.strictEqual(v.effort, 2);
  assert.ok(dropped(v, 'class').includes('claude/fable-5'),
    `fable-5 (SOTA) must be dropped at the class filter: ${JSON.stringify(dropped(v, 'class'))}`);
}

// --- planner floors the effort -----------------------------------------------------------------
{
  const v = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--optimize', 'quality']);
  assert.strictEqual(pair(v), 'claude/fable-5/cli');
  assert.strictEqual(v.effort, 3);
  assert.strictEqual(v.effort_is_floor, true, 'planner effort is a FLOOR the caller raises');

  const code = route(['--access', 'open', '--type', 'code', '--class', 'planner', '--optimize', 'quality']);
  assert.strictEqual(code.effort, 3, 'planner is 3 on code and text alike');
  assert.strictEqual(code.effort_is_floor, true);
}

// --- --access open drops the api rows ----------------------------------------------------------
// One scenario, two accesses: the api row stays IN the ranking when the job is bounded, and drops
// AT THE ACCESS STAGE when the job must roam a disk.
{
  const bounded = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', 'quality', '--explain']);
  assert.strictEqual(bounded.effort, 1);
  assert.strictEqual(dropped(bounded, 'access').length, 0, 'access=bounded drops nothing at the access stage');
  const boundedOrder = bounded.explain.find((e) => e.stage === 'optimize' && e.action === 'rank').order;
  assert.ok(boundedOrder.includes('api/gemini-3.5-flash'), `the api row must be IN the bounded ranking: ${JSON.stringify(boundedOrder)}`);

  const open = route(['--access', 'open', '--type', 'text', '--class', 'mechanical', '--optimize', 'quality', '--explain']);
  assert.ok(dropped(open, 'access').includes('api/gemini-3.5-flash'),
    `the api row must be dropped at the access stage: ${JSON.stringify(dropped(open, 'access'))}`);
  assert.strictEqual(pair(open), 'claude/sonnet-5/cli', 'access=open must exclude every api row');
}

// --- --caps web drops every web=N row ----------------------------------------------------------
{
  const v = route(['--access', 'open', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--caps', 'web', '--explain']);
  assert.strictEqual(pair(v), 'claude/opus-5/cli');
  const webDrops = dropped(v, 'caps');
  assert.ok(webDrops.includes('codex/gpt-5.6-terra'), `web=N rows must drop at caps: ${JSON.stringify(webDrops)}`);
  assert.ok(webDrops.includes('opencode/deepseek-v4-pro'), JSON.stringify(webDrops));
  assert.ok(!webDrops.includes('claude/sonnet-5'), 'a web=Y row must NOT drop at caps');
}

// --- the verdict carries two backups ----------------------------------------------------------
// class=bounded optimizing price ranks every L1+L2 row by cost; the head is the verdict, the next
// two ride along as alternates in that same order, with no duplicate of the head.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'price', '--explain']);
  const order = (v.explain.find((e) => e.stage === 'optimize' && e.action === 'rank') || {}).order;
  assert.ok(Array.isArray(order) && order.length > 2, `expected a ranking deeper than 1: ${JSON.stringify(order)}`);
  assert.strictEqual(v.alternates.length, 2, JSON.stringify(v.alternates));
  assert.deepStrictEqual(v.alternates.map((a) => `${a.harness}/${a.model}`), order.slice(1, 3));
  assert.ok(!v.alternates.some((a) => a.harness === v.harness && a.model === v.model),
    'an alternate must never repeat the top pick');
  assert.ok(v.alternates.every((a) => a.mode), 'each alternate carries its own mode');
}

// --- --caps image short-circuits everything -----------------------------------------------------
// No other flag is needed, and no other question is asked: the image row is L4 (a level no class
// admits) and web=N, yet it is what comes back. Effort is the nominal 1.
{
  const v = route(['--caps', 'image']);
  assert.strictEqual(v._status, 0, `the image short-circuit must answer: ${JSON.stringify(v)}`);
  assert.strictEqual(pair(v), 'opencode/gemini-3.1-pro-preview/cli');
  assert.strictEqual(v.effort, 1);
  // ...and against a table with no image=Y row at all, the honest answer is zero_candidates naming
  // the missing axis — NEVER a malformed_request over the flags the short-circuit deliberately
  // skips. Its own one-row table: whether the SHIPPED table happens to carry an image row is the
  // owner's data, and this arm is about the code path.
  const noImage = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-noimage-'));
  fs.writeFileSync(path.join(noImage, 'rbtv.json'), '{"rbtv_version":"test"}\n');
  const noImageCsv = path.join(noImage, '.rbtv', 'config', 'modules', 'core', 'sub-agents', 'models.csv');
  fs.mkdirSync(path.dirname(noImageCsv), { recursive: true });
  fs.writeFileSync(noImageCsv, [
    'mode,harness,model,efforts,image,web,level,reasoning,coding,cost,use,quality-override,price-override',
    'cli,claude,opus-5,5,N,Y,L1,6,6,25,route,N,N', ''].join('\n'));
  const none = route(['--caps', 'image'], noImage);
  assert.strictEqual(none.error, 'zero_candidates', JSON.stringify(none));
  assert.ok(/image=Y/.test(none.details), none.details);
}

// --- price vs quality pull the bounded class apart ---------------------------------------------
// class=bounded is L1+L2: the cheapest row is terra (L2, 5), the best is opus-5 (L1, reasoning 6).
// One class, two optimizers, two different answers.
{
  const cheap = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'price']);
  assert.strictEqual(pair(cheap), 'codex/gpt-5.6-terra/cli');
  assert.strictEqual(cheap.effort, 2, 'bounded is effort 2 on code');

  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality']);
  assert.strictEqual(pair(best), 'claude/opus-5/cli');
  assert.strictEqual(best.effort, 2, 'bounded is effort 2 on text');
  const broadCode = route(['--access', 'bounded', '--type', 'code', '--class', 'broad', '--optimize', 'price']);
  assert.strictEqual(broadCode.effort, 2, 'broad is effort 2 on code');
  const broadText = route(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality']);
  assert.strictEqual(broadText.effort, 3, 'broad is effort 3 on text');
}

// --- the per-vault override REPLACES the shipped CSV --------------------------------------------
// A scratch vault root (rbtv.json + the override path) — never the real .rbtv/config. Route
// resolves the root from cwd first, so running there is what selects the override.
{
  const vault = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-vault-'));
  fs.writeFileSync(path.join(vault, 'rbtv.json'), '{"rbtv_version":"test"}\n');
  const overrideDir = path.join(vault, '.rbtv', 'config', 'modules', 'core', 'sub-agents');
  fs.mkdirSync(overrideDir, { recursive: true });
  const overrideFile = path.join(overrideDir, 'models.csv');
  // Two rows only, priced, and web is what separates them — so a wrong answer here cannot be the
  // shipped CSV leaking through.
  fs.writeFileSync(overrideFile, [
    'mode,harness,model,efforts,image,web,level,reasoning,coding,cost,use,quality-override,price-override',
    'cli,claude,sonnet-5,5,N,N,L2,6,5,3,route,N,N',
    'cli,claude,haiku-4-5,0,N,Y,L2,3,2,9,route,N,N',
    // A SHORT row on purpose: the three columns added 2026-08-22 are absent, which is what a CSV
    // written before them looks like. Missing cells must read as use=route with neither override.
    'cli,claude,opus-5,5,N,N,L2,7,6,',
    'cli,opencode,not-a-real-model,3,N,Y,L2,6,6,1,route,N,N',
    '',
  ].join('\n'));

  const cheap = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', 'price', '--explain'], vault);
  assert.strictEqual(pair(cheap), 'claude/sonnet-5/cli', 'the override IS the catalog — cost 3 beats cost 9');
  assert.ok(/no catalog\.js row for opencode\/not-a-real-model/.test(cheap._stderr),
    `an unjoinable CSV row must warn LOUDLY on stderr: ${cheap._stderr}`);
  // A blank cost sits OUT of every price pick — unknown is not cheap. It stays eligible for
  // quality, where opus-5's reasoning 7 beats every priced row.
  assert.ok(dropped(cheap, 'optimize').includes('claude/opus-5'),
    `blank-cost rows must drop AT THE OPTIMIZE STAGE with a reason: ${JSON.stringify(dropped(cheap, 'optimize'))}`);
  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', 'quality'], vault);
  assert.strictEqual(pair(best), 'claude/opus-5/cli', 'a blank-cost row is still eligible for quality');

  const web = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', 'price', '--caps', 'web'], vault);
  assert.strictEqual(pair(web), 'claude/haiku-4-5/cli', 'caps=web drops the cheaper web=N row');

  // and the shipped CSV is genuinely IGNORED while the override exists
  const roster = spawnSync('node', [TOOL, 'route', '--catalog'], { encoding: 'utf8', env: ENV, cwd: vault });
  assert.ok(roster.stdout.startsWith(`catalog: ${overrideFile}`),
    `--catalog must name the file it actually read: ${roster.stdout.split('\n')[0]}`);
  assert.ok(!roster.stdout.includes('fable-5'), 'the shipped CSV must not leak into an overridden run');
  assert.ok(/not-a-real-model .* no /.test(roster.stdout.replace(/ +/g, ' ')),
    'the roster must SHOW an unjoinable row as launchable=no, not hide it');
}

// --- use / quality-override / price-override (owner ruling 2026-08-22) --------------------------
// Its own scratch vault, rewritten per arm: these three columns ARE the routing decision, so each
// arm changes exactly one cell and pins what moved. Every row is a claude/codex model, which the
// hermetic env makes available, so nothing here can be decided by a credential.
{
  const vault = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-use-'));
  fs.writeFileSync(path.join(vault, 'rbtv.json'), '{"rbtv_version":"test"}\n');
  const dir = path.join(vault, '.rbtv', 'config', 'modules', 'core', 'sub-agents');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, 'models.csv');
  const HEAD = 'mode,harness,model,efforts,image,web,level,reasoning,coding,cost,use,quality-override,price-override';
  // level/score/cost chosen so every ranking below has ONE right answer and no tie:
  //   L1: sol  cost 20 (score 5) · opus cost 25 (score 6)   -> price picks sol, quality picks opus
  //   L2: terra cost 5 (score 4) · sonnet cost 10 (score 5) -> price picks terra, quality picks sonnet
  const BASE = {
    'opus-5': 'cli,claude,opus-5,5,N,Y,L1,6,6,25',
    'gpt-5.6-sol': 'cli,codex,gpt-5.6-sol,5,N,Y,L1,5,5,20',
    'sonnet-5': 'cli,claude,sonnet-5,5,N,Y,L2,5,5,10',
    'gpt-5.6-terra': 'cli,codex,gpt-5.6-terra,5,N,Y,L2,4,4,5',
  };
  // tweak: {model: [use, quality-override, price-override]}; anything unnamed stays route,N,N.
  const write = (tweak = {}) => {
    const lines = [HEAD];
    for (const [model, cells] of Object.entries(BASE)) {
      const [use, q, pr] = tweak[model] || ['route', 'N', 'N'];
      lines.push(`${cells},${use},${q},${pr}`);
    }
    fs.writeFileSync(file, `${lines.join('\n')}\n`);
  };
  const at = (flags) => route(flags, vault);
  const ranking = (v) => v.explain.filter((e) => e.stage === 'optimize' && e.action !== 'drop').pop().order;

  // 1. the columns are INERT until set: the plain ranking is the pre-2026-08-22 one.
  write();
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price'])), 'codex/gpt-5.6-terra/cli');
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'])), 'claude/opus-5/cli');

  // 2. price-override wins its OWN level: sonnet (10) jumps ahead of terra (5) inside L2, so the
  //    cheapest-first ranking now heads with sonnet.
  write({ 'sonnet-5': ['route', 'N', 'Y'] });
  const priced = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price', '--explain']);
  assert.strictEqual(pair(priced), 'claude/sonnet-5/cli', 'price-override must beat a cheaper row of its own level');
  assert.ok(ranking(priced).indexOf('claude/sonnet-5') < ranking(priced).indexOf('codex/gpt-5.6-terra'), JSON.stringify(ranking(priced)));

  // 3. and it NEVER crosses a level: the same override on an L2 row cannot outrank L1 under
  //    quality, where levels are ranked first. It only takes the head of its own level's block.
  write({ 'sonnet-5': ['route', 'Y', 'N'] });
  const q = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(q), 'claude/opus-5/cli', 'an L2 quality-override must still lose to every eligible L1');
  const qOrder = ranking(q);
  assert.deepStrictEqual(qOrder.slice(0, 2), ['claude/opus-5', 'codex/gpt-5.6-sol'], JSON.stringify(qOrder));
  assert.ok(qOrder.indexOf('claude/sonnet-5') < qOrder.indexOf('codex/gpt-5.6-terra'), JSON.stringify(qOrder));

  // 4. each override fires only in the ranking it names — the quality one is silent under --optimize price.
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price'])), 'codex/gpt-5.6-terra/cli');

  // 5. the default is a price ranking (owner ruling 2026-08-22), so price-override is the one
  //    that fires there — for every class, at every level.
  write();
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), 'codex/gpt-5.6-sol/cli', 'default = cheapest L1');
  write({ 'opus-5': ['route', 'N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), 'claude/opus-5/cli', 'price-override fires in the default');
  write({ 'gpt-5.6-terra': ['route', 'N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'mechanical'])), 'codex/gpt-5.6-terra/cli', 'price-override fires in the default at the low levels too');

  // 6. quality-override, by the same rule, fires in NEITHER — the default no longer ranks anything
  //    on quality, so it takes an explicit --optimize quality to make one bite.
  write({ 'sonnet-5': ['route', 'Y', 'N'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'mechanical'])), 'codex/gpt-5.6-terra/cli', 'quality-override must NOT fire in the default');
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', 'quality'])), 'claude/sonnet-5/cli', 'the same flag DOES bite under --optimize quality');

  // 7. use=panel — no verdict may name it, and it drops at its own stage with its own reason...
  write({ 'opus-5': ['panel', 'N', 'N'] });
  const panel = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(panel), 'codex/gpt-5.6-sol/cli', 'a use=panel row must never be a verdict');
  assert.ok(dropped(panel, 'use').includes('claude/opus-5'), JSON.stringify(dropped(panel, 'use')));
  //    ...but it stays in the roster, which is the surface a panel spreads its seats across.
  const roster = spawnSync('node', [TOOL, 'route', '--catalog', '--json'], { encoding: 'utf8', env: ENV, cwd: vault });
  const rows = JSON.parse(roster.stdout).rows;
  assert.strictEqual(rows.find((r) => r.model === 'opus-5').use, 'panel', 'the roster must SHOW a panel row with its use value');

  // 8. use=off — same invisibility to routing; with both L1 rows gone, class broad has nothing left.
  write({ 'opus-5': ['panel', 'N', 'N'], 'gpt-5.6-sol': ['off', 'N', 'N'] });
  const none = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality']);
  assert.strictEqual(none.error, 'zero_candidates', JSON.stringify(none));
  assert.strictEqual(none._status, 1);

  // 9. an unrecognised use value is never guessed: loud warning, row out of routing.
  write({ 'opus-5': ['maybe', 'N', 'N'] });
  const bad = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(bad), 'codex/gpt-5.6-sol/cli');
  assert.ok(/use='maybe'/.test(bad._stderr), `an unrecognised use must warn on stderr: ${bad._stderr}`);
  assert.ok(dropped(bad, 'use').includes('claude/opus-5'), JSON.stringify(dropped(bad, 'use')));

  // 10. a header missing the three columns is REFUSED, not silently read as blanks: the columns
  //     carry routing decisions, so a stale override CSV must be fixed, never half-obeyed.
  fs.writeFileSync(file, ['mode,harness,model,efforts,image,web,level,reasoning,coding,cost',
    'cli,claude,opus-5,5,N,Y,L1,6,6,25', ''].join('\n'));
  const stale = at(['--access', 'bounded', '--type', 'text', '--class', 'broad']);
  assert.strictEqual(stale.error, 'no_models');
  assert.ok(/header is /.test(stale.details), stale.details);
}

// --- determinism ---------------------------------------------------------------------------------
{
  const flags = ['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'quality'];
  const first = JSON.stringify(route(flags));
  for (let i = 0; i < 3; i++) assert.strictEqual(JSON.stringify(route(flags)), first, 'route must be deterministic');
}

// --- batch: a whole team in one call -------------------------------------------------------------
// Batch turns a plan's seats into ONE assignment table. These arms pin the envelope (input order,
// name-keyed entries, exit 0 only when every seat routed) and the selector's purity (a batch of
// one must answer EXACTLY what the flag form answers for the same interview).
function routeBatch(body, extraFlags = []) {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-batch-')), 'seats.json');
  fs.writeFileSync(file, typeof body === 'string' ? body : JSON.stringify(body));
  const res = spawnSync('node', [TOOL, 'route', '--batch', file, ...extraFlags], { encoding: 'utf8', env: ENV, cwd: FIXTURE });
  assert.ok(res.stdout, `batch printed nothing; stderr: ${res.stderr}`);
  return { ...JSON.parse(res.stdout), _status: res.status, _stderr: res.stderr };
}
function routeBatchStdin(text, extraFlags = []) {
  const res = spawnSync('node', [TOOL, 'route', '--batch', '-', ...extraFlags],
    { encoding: 'utf8', env: ENV, cwd: FIXTURE, input: text });
  assert.ok(res.stdout, `batch on stdin printed nothing; stderr: ${res.stderr}`);
  return { ...JSON.parse(res.stdout), _status: res.status, _stderr: res.stderr };
}

const PLANNER_SEAT = { name: 'planner', access: 'open', type: 'text', class: 'planner', optimize: 'quality', caps: ['web'] };
const FIXER_SEAT = { name: 'fixer', access: 'bounded', type: 'code', class: 'mechanical', optimize: 'price' };

// --- batch happy path: multi-seat, input order, exit 0 ------------------------------------------
{
  const v = routeBatch({ seats: [PLANNER_SEAT, FIXER_SEAT] });
  assert.strictEqual(v._status, 0, `every seat routed, so exit 0: ${JSON.stringify(v)}`);
  assert.strictEqual(v.verdict, 'route-batch');
  assert.deepStrictEqual(v.seats.map((s) => s.name), ['planner', 'fixer'], 'seats must come back in INPUT order');
  assert.strictEqual(pair(v.seats[0]), 'claude/fable-5/cli');
  assert.strictEqual(pair(v.seats[1]), 'codex/gpt-5.6-luna/cli');
}

// --- batch of one == the flag form, field for field ----------------------------------------------
// The batch must not fork the selector: same answers in, same verdict fields out.
{
  const flag = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--optimize', 'quality', '--caps', 'web']);
  const batch = routeBatch([PLANNER_SEAT]);
  assert.strictEqual(batch._status, 0);
  for (const f of ['verdict', 'harness', 'model', 'mode', 'effort', 'effort_is_floor', 'alternates']) {
    assert.deepStrictEqual(batch.seats[0][f], flag[f], `batch seat must reproduce the flag form's ${f}`);
  }
}

// --- a per-seat error never aborts the batch ------------------------------------------------------
{
  const v = routeBatch([PLANNER_SEAT, { name: 'typo', access: 'open', type: 'text', class: 'planer', optimize: 'quality' }]);
  assert.strictEqual(v._status, 1, 'any seat error means exit 1');
  assert.strictEqual(v.seats[0].verdict, 'route', 'the good seat still routed');
  assert.strictEqual(v.seats[1].error, 'malformed_request');
  assert.ok(/class must be one of/.test(v.seats[1].details[0]), JSON.stringify(v.seats[1].details));
}

// --- an unknown key is a refusal, not a silent ignore ---------------------------------------------
{
  const v = routeBatch([{ ...FIXER_SEAT, model: 'opus-5' }]);
  assert.strictEqual(v._status, 1);
  assert.strictEqual(v.seats[0].error, 'malformed_request');
  assert.ok(/unknown key 'model'/.test(v.seats[0].details[0]), JSON.stringify(v.seats[0].details));
}

// --- envelope refusals: one malformed_request object, nothing routed ------------------------------
{
  const dupe = routeBatch([PLANNER_SEAT, { ...FIXER_SEAT, name: 'planner' }]);
  assert.strictEqual(dupe._status, 1);
  assert.strictEqual(dupe.error, 'malformed_request');
  assert.ok(!dupe.seats, 'an envelope refusal carries no seats array');
  assert.ok(/duplicate seat name 'planner'/.test(dupe.details[0]), JSON.stringify(dupe.details));

  const empty = routeBatch('[]');
  assert.strictEqual(empty.error, 'malformed_request');
  assert.ok(/empty/.test(empty.details[0]), JSON.stringify(empty.details));

  const junk = routeBatch('this is not json');
  assert.strictEqual(junk.error, 'malformed_request');
  assert.ok(/not valid JSON/.test(junk.details[0]), JSON.stringify(junk.details));

  const nonObject = routeBatch([PLANNER_SEAT, 'just a string']);
  assert.strictEqual(nonObject.error, 'malformed_request');
  assert.ok(/seat at index 1 is not an object/.test(nonObject.details[0]), JSON.stringify(nonObject.details));

  const noSeats = routeBatchStdin('');
  assert.strictEqual(noSeats._status, 1);
  assert.strictEqual(noSeats.error, 'malformed_request');
  assert.ok(/empty stdin/.test(noSeats.details[0]), JSON.stringify(noSeats.details));
}

// --- the stdin form answers exactly what the file form answers -------------------------------------
{
  const fromFile = routeBatch([PLANNER_SEAT, FIXER_SEAT]);
  const fromStdin = routeBatchStdin(JSON.stringify([PLANNER_SEAT, FIXER_SEAT]));
  assert.strictEqual(fromStdin._status, 0);
  assert.deepStrictEqual(fromStdin.seats, fromFile.seats, '--batch - must reproduce --batch FILE');
}

// --- --batch combines with none of the interview flags ---------------------------------------------
{
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-batch-')), 'seats.json');
  fs.writeFileSync(file, JSON.stringify([FIXER_SEAT]));
  for (const flags of [['--access', 'open'], ['--caps', 'web'], ['--catalog']]) {
    const res = spawnSync('node', [TOOL, 'route', '--batch', file, ...flags], { encoding: 'utf8', env: ENV, cwd: __dirname });
    assert.strictEqual(res.status, 2, `batch + ${flags[0]} must be refused: ${res.stdout}`);
    assert.ok(/--batch takes the whole interview as JSON/.test(res.stderr),
      `the refusal must teach the correct form: ${res.stderr}`);
  }
}

// --- --explain attaches each seat's OWN trace -------------------------------------------------------
{
  const v = routeBatch([PLANNER_SEAT, FIXER_SEAT], ['--explain']);
  assert.strictEqual(v._status, 0);
  for (const s of v.seats) {
    assert.ok(Array.isArray(s.explain), `seat ${s.name} must carry its own trace`);
    assert.strictEqual(s.explain[0].stage, 'catalog');
  }
  const plannerDrops = (v.seats[0].explain || []).filter((e) => e.action === 'drop').length;
  const fixerDrops = (v.seats[1].explain || []).filter((e) => e.action === 'drop').length;
  assert.notStrictEqual(plannerDrops, fixerDrops, 'each trace is the seat\'s own pipeline, not a shared one');
}

// --- the SHIPPED table: validation, never verdicts ----------------------------------------------
// The one arm that reads the real models.csv. It asserts nothing about WHO wins — that is the
// owner's data and theirs to change — only that the table is well-formed enough to be obeyed:
// every row joinable and launchable, every cell in its vocabulary, no duplicates, and every class
// still holding a routable row. Credentials are deliberately NOT consulted: availability depends
// on which keys this box happens to have, and a table is not malformed because a key is missing.
{
  const shipped = spawnSync('node', [TOOL, 'route', '--catalog', '--json'],
    { encoding: 'utf8', env: ENV, cwd: __dirname });
  assert.strictEqual(shipped.status, 0, shipped.stderr);
  const { source, rows } = JSON.parse(shipped.stdout);
  assert.ok(source.endsWith(path.join('tool', 'models.csv')), `expected the shipped table, got ${source}`);
  assert.ok(rows.length > 3, `the shipped table is suspiciously short: ${rows.length} rows`);

  const LEVELS = ['SOTA', 'L1', 'L2', 'L3', 'L4'];
  // Every axis a multi-level twin must agree on — the CSV columns minus `level` itself.
  const AXES = ['mode', 'harness', 'model', 'efforts', 'image', 'web', 'reasoning', 'coding',
    'cost', 'use', 'quality-override', 'price-override'];
  const YN = ['Y', 'N'];
  const seen = new Map();
  for (const r of rows) {
    const at = `models.csv row ${r.harness}/${r.model || '(blank model)'}`;
    // Launchability is the join: a row cast cannot launch is a row route must never name, and the
    // tool only WARNS about it — so this is where a typo like `gemini-3.7-flash` with no catalog
    // entry gets caught instead of silently shrinking the roster.
    assert.strictEqual(r.launchable, 'yes', `${at} has no catalog.js twin — route excludes it`);
    assert.ok(['cli', 'api'].includes(r.mode), `${at}: mode '${r.mode}'`);
    assert.ok(LEVELS.includes(r.level), `${at}: level '${r.level}' is not one of ${LEVELS.join('|')}`);
    assert.ok(YN.includes(r.image), `${at}: image '${r.image}'`);
    assert.ok(YN.includes(r.web), `${at}: web '${r.web}'`);
    assert.ok(['', 'route', 'panel', 'off'].includes(r.use), `${at}: use '${r.use}' (blank | route | panel | off)`);
    for (const col of ['quality-override', 'price-override']) {
      assert.ok(['', ...YN].includes(r[col]), `${at}: ${col} is '${r[col]}' (blank | Y | N)`);
    }
    for (const col of ['efforts', 'reasoning', 'coding']) {
      assert.ok(/^\d+$/.test(r[col]), `${at}: ${col} is '${r[col]}' — expected a whole number`);
    }
    // Cost may be blank (unknown), but anything else must be a number. This is the arm that
    // catches a decimal COMMA: '4,4' shifts every later cell one column left, which silently
    // dropped four models out of routing on 2026-08-22 before anyone noticed.
    assert.ok(r.cost === '' || Number.isFinite(Number(r.cost)),
      `${at}: cost is '${r.cost}' — a number, or blank for unknown (a decimal comma shifts the whole row)`);
    // A model MAY appear on more than one line, once per level it is admitted at (owner ruling
    // 2026-08-23: claude/sonnet-5 sits at L2 and L3 so `bounded` and `mechanical` can both reach
    // it, its subscription making the L3 list price misleading). The join onto catalog.js is on
    // harness+model and both copies resolve to the same launch spec, so this is unambiguous where
    // it matters. What stays forbidden is the ACCIDENTAL duplicate: two lines for one model that
    // disagree on any other axis — that is a typo, and route would rank the same model twice with
    // different numbers. So: unique on harness+model+level, and identical on everything else.
    const key = `${r.harness}/${r.model}/${r.level}`;
    assert.ok(!seen.has(key), `${at} appears twice at level ${r.level} — one line per model per level`);
    const twin = [...seen.entries()].find(([, v]) => v.harness === r.harness && v.model === r.model);
    if (twin) {
      const differ = AXES.filter((c) => twin[1][c] !== r[c]);
      assert.strictEqual(differ.length, 0,
        `${at} repeats ${r.harness}/${r.model} at a second level but also differs on ${differ.join(', ')} — a multi-level row may differ ONLY in level`);
    }
    seen.set(key, r);
  }

  // Every class must still have somewhere to go. Structural, not a verdict: a table where every
  // L2 row went `panel` would answer every bounded job with an L1 model and nothing would say so.
  const CLASS_LEVELS = { planner: ['SOTA', 'L1'], broad: ['L1'], bounded: ['L1', 'L2'], mechanical: ['L2', 'L3'] };
  const routable = rows.filter((r) => r.use === '' || r.use === 'route');
  for (const [cls, levels] of Object.entries(CLASS_LEVELS)) {
    assert.ok(routable.some((r) => levels.includes(r.level)),
      `class ${cls} (${levels.join('+')}) has no routable row left in models.csv`);
  }
  // Per LEVEL too, not only per class: a class check alone stays green when a whole level empties
  // out, because its other level covers for it — bounded (L1+L2) keeps answering from L1 while
  // every L2 row has quietly gone `panel`, and every bounded job silently gets a bigger, pricier
  // model than the class intends. The level is the unit that can vanish unnoticed.
  for (const level of [...new Set(Object.values(CLASS_LEVELS).flat())]) {
    assert.ok(routable.some((r) => r.level === level),
      `no routable models.csv row is left at level ${level} — every class that reaches it now answers from its other level`);
  }

  // And loading it must be SILENT. Every exclusion route makes on its own is a stderr warning, so
  // an empty stderr is the proof that nothing was quietly left out of the roster.
  const quiet = spawnSync('node', [TOOL, 'route', '--access', 'bounded', '--type', 'text', '--class', 'mechanical'],
    { encoding: 'utf8', env: ENV, cwd: __dirname });
  assert.strictEqual(quiet.stderr, '', `loading the shipped table must warn about nothing:\n${quiet.stderr}`);
}

process.stdout.write('all route tests passed\n');

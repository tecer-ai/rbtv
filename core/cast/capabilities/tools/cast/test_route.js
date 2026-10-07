#!/usr/bin/env node
'use strict';

// `cast route` self-check — REWRITTEN 2026-08-20 for the redesigned selector. The old suite
// tested the retired algorithm (bands, pins, halt seams, footprint) and was deleted with it.
//
// WHAT IS TESTED WHERE (owner ruling 2026-08-22):
//   * LOGIC arms route against a FIXTURE table this suite writes and owns (FIXTURE below). The
//     shipped models.csv is the OWNER'S DATA — they re-rank the model catalog whenever they like — so an
//     arm that pinned a verdict off it only restated a cell they had just edited. That design
//     reddened 16 arms on the 2026-08-22 re-curation and taught nobody anything: the checks broke
//     because the data changed, never because the selector did.
//   * The SHIPPED table gets ONE arm, at the bottom: VALIDATION, not verdicts — every row joins
//     supported-models.js, every cell is in its vocabulary, no duplicates, every class still has a routable
//     row, and loading it emits NO warning. That is the half that can be wrong without anyone
//     noticing (a decimal comma silently shifted four rows out of routing that same day).
//
// Hermetic environment (availability is a PRESENCE test, never a spend): api keys are pinned to
// synthetic placeholders and XDG_DATA_HOME points at an empty dir, so this box's real opencode
// credential store cannot decide a verdict. Available in these runs: every claude + codex row
// (the harness holds its own account login), the opencode deepseek + google rows and both api rows
// (env keys). Unavailable: zai (glm), sakana (fugu), xai (grok), kimi (k3).

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
// cwd is what selects a table: route finds the installation from cwd (the first folder upward
// holding .rbtv/config/install.json), and that installation's model catalog
// (.rbtv/config/cast/models.csv) is read INSTEAD of the shipped one. So the suite makes itself a
// scratch installation, writes its own table into it, and every logic arm runs there — the
// shipped models.csv is reached only by the arms that run from OUTSIDE, a fresh folder inside no
// installation.
//
// The table is built so each arm has ONE right answer and no tie, and so every axis has a
// discriminating pair: cli vs api, a blank cost, an image row, and one row (k3, on a
// kimi credential ENV does not fake) that must drop at availability.
function scratchInstallation(prefix) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  fs.mkdirSync(path.join(root, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(root, '.rbtv', 'config', 'install.json'), '{}\n');
  return root;
}
// Where an installation keeps its model catalog; the folder is made, the file is the caller's.
function catalogOf(root) {
  const file = path.join(root, '.rbtv', 'config', 'cast', 'models.csv');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  return file;
}
const OUTSIDE = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-outside-'));
const FIXTURE = scratchInstallation('cast-route-fixture-');
fs.writeFileSync(catalogOf(FIXTURE), [
  'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
  'cli,claude,fable-5-1,5,N,SOTA,7,7,50,route,N,N',
  'cli,codex,gpt-6-astra,5,N,SOTA,7,7,50,route,Y,Y',
  'cli,claude,opus-5-5,5,N,L1,6,6,25,route,N,N',
  'cli,codex,gpt-6.1-sol,5,N,L1,5,5,20,route,N,N',
  'cli,claude,sonnet-5-5,5,N,L2,5,5,10,route,N,N',
  'cli,codex,gpt-5.6-terra,5,N,L2,4,4,5,route,N,N',
  'cli,opencode,k3,3,N,L2,5,5,15,route,N,N',
  'cli,codex,gpt-6-luna,5,N,L3,3,2,1.2,route,N,N',
  'cli,opencode,deepseek-v4-pro,4,N,L3,3,3,3.96,route,N,N',
  'cli,claude,haiku-4-5,0,N,L3,3,3,,route,N,N',
  'api,api,gemini-3.5-flash,0,N,L3,3,3,9,route,N,N',
  'cli,opencode,gemini-3.1-pro-preview,3,Y,L4,0,0,,route,N,N',
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
// Level L3; the cheapest priced row there is luna at 1.2. Effort 1, and effort_is_floor
// false — only planner floors.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'mechanical', '--optimize', 'price']);
  assert.strictEqual(v._status, 0, `expected a verdict: ${JSON.stringify(v)}`);
  assert.strictEqual(v.verdict, 'route');
  assert.strictEqual(pair(v), 'codex/gpt-6-luna/cli');
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
// that stands between a job and the cheapest model in the model catalog.
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
  assert.strictEqual(pair(mech), 'codex/gpt-6-luna/cli', 'mechanical default = the cheapest L3 row');
  const rank = mech.explain.find((e) => e.stage === 'optimize' && e.action === 'rank');
  assert.strictEqual(rank.optimize, 'default');
  assert.ok(/price, for every class/.test(rank.rule || ''), JSON.stringify(rank));
  // A blank cost is excluded from the default exactly as it is from an explicit price pick.
  assert.ok(dropped(mech, 'optimize').includes('claude/haiku-4-5'), JSON.stringify(dropped(mech, 'optimize')));

  // ONE LEVEL PER CLASS (owner ruling 2026-09-24), pinned so it cannot drift back silently: when a
  // class spanned two levels, the price default handed it to the cheaper level's row (planning went
  // to an L1 model). Now the other levels drop at the class stage and never enter the ranking.
  const planner = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--explain']);
  assert.strictEqual(pair(planner), 'codex/gpt-6-astra/cli', 'planner default stays at SOTA');
  const bounded = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--explain']);
  assert.strictEqual(pair(bounded), 'codex/gpt-5.6-terra/cli', 'bounded default = cheapest L2');
  for (const v of [planner, bounded]) {
    assert.ok(dropped(v, 'class').includes('codex/gpt-6.1-sol'), `the cheaper L1 row must drop at the class stage: ${JSON.stringify(dropped(v, 'class'))}`);
  }

  // Batch: an omitted optimize on an agent takes the same default as the flag form.
  const b = routeBatch([{ name: 'm', access: 'bounded', type: 'code', class: 'mechanical' }]);
  assert.strictEqual(b._status, 0, JSON.stringify(b));
  assert.strictEqual(`${b.agents[0].harness}/${b.agents[0].model}`, 'codex/gpt-6-luna');
}

// --- max quality NEVER leaves the class's own levels --------------------------------------------
// class=bounded is L2 only. fable-5-1 (SOTA) and opus-5-5 (L1) are available and score higher, and
// neither may be picked: a bounded executor at max quality gets the best L2 (sonnet-5-5).
{
  const v = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(v), 'claude/sonnet-5-5/cli');
  assert.ok(dropped(v, 'class').includes('claude/opus-5-5'), JSON.stringify(dropped(v, 'class')));
  assert.strictEqual(v.effort, 2);
  assert.ok(dropped(v, 'class').includes('claude/fable-5-1'),
    `fable-5-1 (SOTA) must be dropped at the class filter: ${JSON.stringify(dropped(v, 'class'))}`);
}

// --- planner floors the effort -----------------------------------------------------------------
{
  const v = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--optimize', 'quality']);
  assert.strictEqual(pair(v), 'codex/gpt-6-astra/cli');
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
  assert.strictEqual(pair(open), 'codex/gpt-6-luna/cli', 'access=open must exclude every api row');
}

// --- the verdict carries two backups ----------------------------------------------------------
// class=mechanical optimizing price ranks every priced L3 row by cost; the head is the verdict, the
// next two ride along as alternates in that same order, with no duplicate of the head.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'mechanical', '--optimize', 'price', '--explain']);
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
// admits), yet it is what comes back. Effort is the nominal 1.
{
  const v = route(['--caps', 'image']);
  assert.strictEqual(v._status, 0, `the image short-circuit must answer: ${JSON.stringify(v)}`);
  assert.strictEqual(pair(v), 'opencode/gemini-3.1-pro-preview/cli');
  assert.strictEqual(v.effort, 1);
  // ...and against a table with no image=Y row at all, the honest answer is zero_candidates naming
  // the missing axis — NEVER a malformed_request over the flags the short-circuit deliberately
  // skips. Its own one-row table: whether the SHIPPED table happens to carry an image row is the
  // owner's data, and this arm is about the code path.
  const noImage = scratchInstallation('cast-route-noimage-');
  fs.writeFileSync(catalogOf(noImage), [
    'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
    'cli,claude,opus-5-5,5,N,L1,6,6,25,route,N,N', ''].join('\n'));
  const none = route(['--caps', 'image'], noImage);
  assert.strictEqual(none.error, 'zero_candidates', JSON.stringify(none));
  assert.ok(/image=Y/.test(none.details), none.details);
}

// --- price vs quality pull the bounded class apart ---------------------------------------------
// class=bounded is L2: the cheapest row is terra (cost 5), the best is sonnet-5-5 (reasoning 5).
// One class, two optimizers, two different answers.
{
  const cheap = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'price']);
  assert.strictEqual(pair(cheap), 'codex/gpt-5.6-terra/cli');
  assert.strictEqual(cheap.effort, 2, 'bounded is effort 2 on code');

  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality']);
  assert.strictEqual(pair(best), 'claude/sonnet-5-5/cli');
  assert.strictEqual(best.effort, 2, 'bounded is effort 2 on text');
  const broadCode = route(['--access', 'bounded', '--type', 'code', '--class', 'broad', '--optimize', 'price']);
  assert.strictEqual(broadCode.effort, 2, 'broad is effort 2 on code');
  const broadText = route(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality']);
  assert.strictEqual(broadText.effort, 3, 'broad is effort 3 on text');
}

// --- the installation's model catalog REPLACES the shipped one -----------------------------------
// A scratch installation (the install record + its model catalog) — never the real .rbtv/config.
// Route finds the installation from cwd, so running there is what selects its table.
{
  const vault = scratchInstallation('cast-route-vault-');
  const overrideFile = catalogOf(vault);
  // Two rows only, priced, and cost is what separates them — so a wrong answer here cannot be the
  // shipped CSV leaking through.
  fs.writeFileSync(overrideFile, [
    'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
    'cli,claude,sonnet-5-5,5,N,L2,6,5,3,route,N,N',
    'cli,claude,haiku-4-5,0,N,L2,3,2,9,route,N,N',
    // BLANK cells on purpose: a blank use reads as route, a blank override as N, and a blank cost
    // as unknown.
    'cli,claude,opus-5-5,5,N,L2,7,6,,,,',
    'cli,opencode,not-a-real-model,3,N,L2,6,6,1,route,N,N',
    '',
  ].join('\n'));

  const cheap = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price', '--explain'], vault);
  assert.strictEqual(pair(cheap), 'claude/sonnet-5-5/cli', "the installation's table IS the model catalog — cost 3 beats cost 9");
  assert.ok(/no supported-models\.js row for opencode\/not-a-real-model/.test(cheap._stderr),
    `an unjoinable CSV row must warn LOUDLY on stderr: ${cheap._stderr}`);
  // A blank cost sits OUT of every price pick — unknown is not cheap. It stays eligible for
  // quality, where opus-5-5's reasoning 7 beats every priced row.
  assert.ok(dropped(cheap, 'optimize').includes('claude/opus-5-5'),
    `blank-cost rows must drop AT THE OPTIMIZE STAGE with a reason: ${JSON.stringify(dropped(cheap, 'optimize'))}`);
  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'], vault);
  assert.strictEqual(pair(best), 'claude/opus-5-5/cli', 'a blank-cost row is still eligible for quality');

  // and the shipped model catalog is genuinely IGNORED while the installation has its own: the
  // trace names the file that was read, and counts its four rows, three of them joined.
  const read = cheap.explain[0];
  assert.strictEqual(read.source, fs.realpathSync(overrideFile), 'the trace must name the file it actually read');
  assert.deepStrictEqual([read.csv_rows, read.joined], [4, 3], JSON.stringify(read));
}

// --- use / quality-override / price-override (owner ruling 2026-08-22) --------------------------
// Its own scratch vault, rewritten per arm: these three columns ARE the routing decision, so each
// arm changes exactly one cell and pins what moved. Every row is a claude/codex model, which the
// hermetic env makes available, so nothing here can be decided by a credential.
{
  const vault = scratchInstallation('cast-route-use-');
  const file = catalogOf(vault);
  const HEAD = 'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override';
  // level/score/cost chosen so every ranking below has ONE right answer and no tie:
  //   L1: sol  cost 20 (score 5) · opus cost 25 (score 6)   -> price picks sol, quality picks opus
  //   L2: terra cost 5 (score 4) · sonnet cost 10 (score 5) -> price picks terra, quality picks sonnet
  const BASE = {
    'opus-5-5': 'cli,claude,opus-5-5,5,N,L1,6,6,25',
    'gpt-6.1-sol': 'cli,codex,gpt-6.1-sol,5,N,L1,5,5,20',
    'sonnet-5-5': 'cli,claude,sonnet-5-5,5,N,L2,5,5,10',
    'gpt-5.6-terra': 'cli,codex,gpt-5.6-terra,5,N,L2,4,4,5',
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
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'])), 'claude/sonnet-5-5/cli');

  // 2. price-override wins its OWN level: sonnet (10) jumps ahead of terra (5) inside L2, so the
  //    cheapest-first ranking now heads with sonnet.
  write({ 'sonnet-5-5': ['route', 'N', 'Y'] });
  const priced = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price', '--explain']);
  assert.strictEqual(pair(priced), 'claude/sonnet-5-5/cli', 'price-override must beat a cheaper row of its own level');
  assert.ok(ranking(priced).indexOf('claude/sonnet-5-5') < ranking(priced).indexOf('codex/gpt-5.6-terra'), JSON.stringify(ranking(priced)));

  // 3. quality-override wins its level against a higher score: terra (4) jumps sonnet (5).
  write({ 'gpt-5.6-terra': ['route', 'Y', 'N'] });
  const q = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.deepStrictEqual(ranking(q), ['codex/gpt-5.6-terra', 'claude/sonnet-5-5'], JSON.stringify(ranking(q)));

  // 4. each override fires only in the ranking it names — the quality one is silent under --optimize price.
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price'])), 'codex/gpt-5.6-terra/cli');

  // 5. the default is a price ranking (owner ruling 2026-08-22), so price-override is the one
  //    that fires there — for every class, at every level.
  write();
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), 'codex/gpt-6.1-sol/cli', 'default = cheapest L1');
  write({ 'opus-5-5': ['route', 'N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), 'claude/opus-5-5/cli', 'price-override fires in the default');
  write({ 'sonnet-5-5': ['route', 'N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded'])), 'claude/sonnet-5-5/cli', 'price-override fires in the default at the low levels too');

  // 6. quality-override, by the same rule, fires in NEITHER — the default no longer ranks anything
  //    on quality, so it takes an explicit --optimize quality to make one bite.
  write({ 'sonnet-5-5': ['route', 'Y', 'N'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded'])), 'codex/gpt-5.6-terra/cli', 'quality-override must NOT fire in the default');
  write({ 'gpt-5.6-terra': ['route', 'Y', 'N'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'])), 'codex/gpt-5.6-terra/cli', 'the flag DOES bite under --optimize quality');

  // 7. use=panel — no verdict may name it, and it drops at its own stage with its own reason...
  write({ 'opus-5-5': ['panel', 'N', 'N'] });
  const panel = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(panel), 'codex/gpt-6.1-sol/cli', 'a use=panel row must never be a verdict');
  assert.ok(dropped(panel, 'use').includes('claude/opus-5-5'), JSON.stringify(dropped(panel, 'use')));

  // 8. use=off — same invisibility to routing; with both L1 rows gone, class broad has nothing left.
  write({ 'opus-5-5': ['panel', 'N', 'N'], 'gpt-6.1-sol': ['off', 'N', 'N'] });
  const none = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality']);
  assert.strictEqual(none.error, 'zero_candidates', JSON.stringify(none));
  assert.strictEqual(none._status, 1);

  // 9. an unrecognised use value is never guessed: loud warning, row out of routing.
  write({ 'opus-5-5': ['maybe', 'N', 'N'] });
  const bad = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(bad), 'codex/gpt-6.1-sol/cli');
  assert.ok(/use='maybe'/.test(bad._stderr), `an unrecognised use must warn on stderr: ${bad._stderr}`);
  assert.ok(dropped(bad, 'use').includes('claude/opus-5-5'), JSON.stringify(dropped(bad, 'use')));

  // 10. cells are read by header name: a table without the three columns reads them blank, which
  //     is use=route with neither override.
  fs.writeFileSync(file, ['mode,harness,model,efforts,image,level,reasoning,coding,cost',
    'cli,claude,opus-5-5,5,N,L1,6,6,25', ''].join('\n'));
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), 'claude/opus-5-5/cli');

  // 11. a table that cannot be read as one is REFUSED with its file and line, never half-obeyed:
  //     an unknown column, a row whose cell count is not the header's (what a decimal comma
  //     makes), a missing harness column, a blank model, an empty file.
  for (const [lines, where, why] of [
    [[`${HEAD},notes`, 'cli,claude,opus-5-5,5,N,L1,6,6,25,route,N,N,x'], 'line 1:', "unknown column 'notes'"],
    [[HEAD, '', 'cli,claude,opus-5-5,5,N,L1,6,6,2,5,route,N,N'], 'line 3:', '13 cells where the header has 12'],
    [[HEAD, 'cli,claude,opus-5-5,5,N,L1,6,6,25'], 'line 2:', '9 cells where the header has 12'],
    [['mode,model,level', 'cli,opus-5-5,L1'], 'line 1:', "no 'harness' column"],
    [[HEAD, 'cli,claude,,5,N,L1,6,6,25,route,N,N'], 'line 2:', 'blank model'],
    [[], 'models.csv:', 'the file is empty'],
  ]) {
    fs.writeFileSync(file, `${lines.join('\n')}\n`);
    const broken = at(['--access', 'bounded', '--type', 'text', '--class', 'broad']);
    assert.strictEqual(broken._status, 1, JSON.stringify(broken));
    assert.strictEqual(broken.error, 'no_models');
    assert.ok(broken.details.startsWith(`cannot read the model catalog ${fs.realpathSync(file)}`), broken.details);
    assert.ok(broken.details.includes(`${where} ${why}`), broken.details);
  }
}

// --- the model catalog left `cast route` -----------------------------------------------------------
{
  for (const flags of [['--catalog'], ['--catalog', '--json'], ['--access', 'open', '--catalog']]) {
    const res = spawnSync('node', [TOOL, 'route', ...flags], { encoding: 'utf8', env: ENV, cwd: FIXTURE });
    assert.strictEqual(res.status, 2, `route ${flags.join(' ')} must be refused: ${res.stdout}`);
    assert.strictEqual(res.stdout, '');
    assert.strictEqual(res.stderr, 'cast: refused: --catalog moved\nthe model catalog is a view of cast models list\nNothing changed.\ncast models list --catalog\n');
  }
}

// --- determinism ---------------------------------------------------------------------------------
{
  const flags = ['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'quality'];
  const first = JSON.stringify(route(flags));
  for (let i = 0; i < 3; i++) assert.strictEqual(JSON.stringify(route(flags)), first, 'route must be deterministic');
}

// --- batch: a whole team in one call -------------------------------------------------------------
// Batch turns a plan's agents into ONE assignment table. These arms pin the envelope (input order,
// name-keyed entries, exit 0 only when every agent routed) and the selector's purity (a batch of
// one must answer EXACTLY what the flag form answers for the same interview).
function routeBatch(body, extraFlags = []) {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-batch-')), 'agents.json');
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

const PLANNER_AGENT = { name: 'planner', access: 'open', type: 'text', class: 'planner', optimize: 'quality' };
const FIXER_AGENT = { name: 'fixer', access: 'bounded', type: 'code', class: 'mechanical', optimize: 'price' };

// --- batch happy path: multi-agent, input order, exit 0 ------------------------------------------
{
  const v = routeBatch({ agents: [PLANNER_AGENT, FIXER_AGENT] });
  assert.strictEqual(v._status, 0, `every agent routed, so exit 0: ${JSON.stringify(v)}`);
  assert.strictEqual(v.verdict, 'route-batch');
  assert.deepStrictEqual(v.agents.map((s) => s.name), ['planner', 'fixer'], 'agents must come back in INPUT order');
  assert.strictEqual(pair(v.agents[0]), 'codex/gpt-6-astra/cli');
  assert.strictEqual(pair(v.agents[1]), 'codex/gpt-6-luna/cli');
}

// --- batch of one == the flag form, field for field ----------------------------------------------
// The batch must not fork the selector: same answers in, same verdict fields out.
{
  const flag = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--optimize', 'quality']);
  const batch = routeBatch([PLANNER_AGENT]);
  assert.strictEqual(batch._status, 0);
  for (const f of ['verdict', 'harness', 'model', 'mode', 'effort', 'effort_is_floor', 'alternates']) {
    assert.deepStrictEqual(batch.agents[0][f], flag[f], `batch agent must reproduce the flag form's ${f}`);
  }
}

// --- a per-agent error never aborts the batch ------------------------------------------------------
{
  const v = routeBatch([PLANNER_AGENT, { name: 'typo', access: 'open', type: 'text', class: 'planer', optimize: 'quality' }]);
  assert.strictEqual(v._status, 1, 'any agent error means exit 1');
  assert.strictEqual(v.agents[0].verdict, 'route', 'the good agent still routed');
  assert.strictEqual(v.agents[1].error, 'malformed_request');
  assert.ok(/class must be one of/.test(v.agents[1].details[0]), JSON.stringify(v.agents[1].details));
}

// --- an unknown key is a refusal, not a silent ignore ---------------------------------------------
{
  const v = routeBatch([{ ...FIXER_AGENT, model: 'opus-5-5' }]);
  assert.strictEqual(v._status, 1);
  assert.strictEqual(v.agents[0].error, 'malformed_request');
  assert.ok(/unknown key 'model'/.test(v.agents[0].details[0]), JSON.stringify(v.agents[0].details));
}

// --- envelope refusals: one malformed_request object, nothing routed ------------------------------
{
  const dupe = routeBatch([PLANNER_AGENT, { ...FIXER_AGENT, name: 'planner' }]);
  assert.strictEqual(dupe._status, 1);
  assert.strictEqual(dupe.error, 'malformed_request');
  assert.ok(!dupe.agents, 'an envelope refusal carries no agents array');
  assert.ok(/duplicate agent name 'planner'/.test(dupe.details[0]), JSON.stringify(dupe.details));

  const empty = routeBatch('[]');
  assert.strictEqual(empty.error, 'malformed_request');
  assert.ok(/empty/.test(empty.details[0]), JSON.stringify(empty.details));

  const junk = routeBatch('this is not json');
  assert.strictEqual(junk.error, 'malformed_request');
  assert.ok(/not valid JSON/.test(junk.details[0]), JSON.stringify(junk.details));

  const nonObject = routeBatch([PLANNER_AGENT, 'just a string']);
  assert.strictEqual(nonObject.error, 'malformed_request');
  assert.ok(/agent at index 1 is not an object/.test(nonObject.details[0]), JSON.stringify(nonObject.details));

  const noAgents = routeBatchStdin('');
  assert.strictEqual(noAgents._status, 1);
  assert.strictEqual(noAgents.error, 'malformed_request');
  assert.ok(/empty stdin/.test(noAgents.details[0]), JSON.stringify(noAgents.details));
}

// --- the stdin form answers exactly what the file form answers -------------------------------------
{
  const fromFile = routeBatch([PLANNER_AGENT, FIXER_AGENT]);
  const fromStdin = routeBatchStdin(JSON.stringify([PLANNER_AGENT, FIXER_AGENT]));
  assert.strictEqual(fromStdin._status, 0);
  assert.deepStrictEqual(fromStdin.agents, fromFile.agents, '--batch - must reproduce --batch FILE');
}

// --- --batch combines with none of the interview flags ---------------------------------------------
{
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-batch-')), 'agents.json');
  fs.writeFileSync(file, JSON.stringify([FIXER_AGENT]));
  for (const flags of [['--access', 'open'], ['--caps', 'image']]) {
    const res = spawnSync('node', [TOOL, 'route', '--batch', file, ...flags], { encoding: 'utf8', env: ENV, cwd: OUTSIDE });
    assert.strictEqual(res.status, 2, `batch + ${flags[0]} must be refused: ${res.stdout}`);
    assert.ok(/--batch takes the whole interview as JSON/.test(res.stderr),
      `the refusal must teach the correct form: ${res.stderr}`);
  }
}

// --- --explain attaches each agent's OWN trace -------------------------------------------------------
{
  const v = routeBatch([PLANNER_AGENT, FIXER_AGENT], ['--explain']);
  assert.strictEqual(v._status, 0);
  for (const s of v.agents) {
    assert.ok(Array.isArray(s.explain), `agent ${s.name} must carry its own trace`);
    assert.strictEqual(s.explain[0].stage, 'catalog');
  }
  const plannerDrops = (v.agents[0].explain || []).filter((e) => e.action === 'drop').length;
  const fixerDrops = (v.agents[1].explain || []).filter((e) => e.action === 'drop').length;
  assert.notStrictEqual(plannerDrops, fixerDrops, 'each trace is the agent\'s own pipeline, not a shared one');
}

// --- every supported model names a provider that serves its harness ------------------------------
// supported-models.js rows point into providers.json by name; a row whose provider is missing, or
// whose harness that provider does not list, would crash the availability check at route time.
{
  const { ROWS } = require('./supported-models');
  const { providers } = require('./providers.json');
  for (const r of ROWS) {
    const at = `supported-models.js row ${r.harness}/${r.model}`;
    assert.ok(providers[r.provider], `${at}: provider '${r.provider}' is not in providers.json`);
    assert.ok(Object.prototype.hasOwnProperty.call(providers[r.provider].harnesses, r.harness),
      `${at}: providers.json does not list harness '${r.harness}' under provider '${r.provider}'`);
  }
}

// --- a row whose provider cannot be looked up is refused by name ----------------------------------
// The check above keeps the shipped rows sound; this arm keeps the failure readable if one ever is
// not: one line naming the row, exit 2, never a program error with a stack.
{
  const probe = (row) => spawnSync(process.execPath, ['-e',
    `require(${JSON.stringify(path.join(__dirname, 'lib', 'route.js'))}).isAvailable(${JSON.stringify(row)}, null)`],
  { encoding: 'utf8', env: ENV });
  for (const [row, provider] of [
    [{ harness: 'opencode', model: 'no-such-model', provider: 'no-such-provider' }, 'no-such-provider'],
    [{ harness: 'opencode', model: 'no-such-model', provider: 'claude' }, 'claude'],
  ]) {
    const res = probe(row);
    assert.strictEqual(res.status, 2, `expected a refusal, got ${res.status}: ${res.stderr}`);
    assert.strictEqual(res.stderr.trimEnd().split('\n').length, 1, `one line, got: ${res.stderr}`);
    assert.ok(res.stderr.startsWith('cast: refused: supported-models.js row opencode/no-such-model '), res.stderr);
    assert.ok(res.stderr.includes(`'${provider}'`) && res.stderr.includes('providers.json'), res.stderr);
  }
  assert.strictEqual(probe({ harness: 'claude', model: 'opus-5-5', provider: 'claude' }).status, 0);
}

// --- where a login is looked for -------------------------------------------------------------------
// Its own scratch installation, table and opencode store, so each source is the ONLY thing that
// can make a row available: the installation's env file, or the provider's entry in the store.
{
  const inst = scratchInstallation('cast-route-login-');
  fs.writeFileSync(catalogOf(inst), [
    'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
    'cli,opencode,k3,3,N,L2,5,5,15,route,N,N',
    'cli,opencode,glm-5.3,2,N,L2,5,5,15,route,N,N',
    'cli,opencode,fugu-ultra,3,N,L2,5,5,15,route,N,N',
    'cli,opencode,grok-4.7,3,N,L2,5,5,15,route,N,N',
    ''].join('\n'));
  const xdg = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-store-'));
  fs.mkdirSync(path.join(xdg, 'opencode'));
  const envFile = path.join(inst, '.rbtv', 'config', 'env', '.env');
  fs.mkdirSync(path.dirname(envFile), { recursive: true });
  const available = (store, envText, extraEnv = {}) => {
    fs.writeFileSync(path.join(xdg, 'opencode', 'auth.json'), JSON.stringify(store));
    fs.writeFileSync(envFile, envText);
    // Every row is L2, so a bounded interview weighs all four: a row is available unless the trace
    // shows it dropped at the availability stage.
    const res = spawnSync('node', [TOOL, 'route', '--access', 'bounded', '--type', 'text', '--class', 'bounded', '--explain'],
      { encoding: 'utf8', env: { ...ENV, XDG_DATA_HOME: xdg, ...extraEnv }, cwd: path.join(inst, '.rbtv') });
    const gone = dropped(JSON.parse(res.stdout), 'availability');
    return Object.fromEntries(['k3', 'glm-5.3', 'fugu-ultra', 'grok-4.7'].map((m) => [m, String(!gone.includes(`opencode/${m}`))]));
  };

  // Nothing anywhere: every row is unavailable. `KEY=` with no value is NOT a key, quoted or not.
  assert.deepStrictEqual(available({}, 'KIMI_API_KEY=\nZHIPU_API_KEY=""\n'),
    { k3: 'false', 'glm-5.3': 'false', 'fugu-ultra': 'false', 'grok-4.7': 'false' });
  // The env file of the installation found from cwd (a folder BELOW the root) serves a key row.
  assert.deepStrictEqual(available({}, '# comment\nKIMI_API_KEY=test-fake-not-real\n'),
    { k3: 'true', 'glm-5.3': 'false', 'fugu-ultra': 'false', 'grok-4.7': 'false' });
  // The store serves sakana (an API key kept by opencode) and xai (an account login kept by
  // opencode) alike: what counts is the provider's entry in the harness's store.
  assert.deepStrictEqual(available({ sakana: { type: 'api' }, xai: { type: 'oauth' } }, ''),
    { k3: 'false', 'glm-5.3': 'false', 'fugu-ultra': 'true', 'grok-4.7': 'true' });
  // xai has no key variable: an account login is never "always available", and a stray
  // XAI_API_KEY does not stand in for the missing store entry.
  assert.strictEqual(available({}, '', { XAI_API_KEY: 'test-fake-not-real' })['grok-4.7'], 'false');
}

// --- the SHIPPED table: validation, never verdicts ----------------------------------------------
// The one arm that reads the real models.csv. It asserts nothing about WHO wins — that is the
// owner's data and theirs to change — only that the table is well-formed enough to be obeyed:
// every row joinable and launchable, every supported model holding a row (an installation with
// no model catalog of its own has every supported model selected), every cell in its vocabulary,
// no duplicates, and every class still holding a routable row. Credentials are deliberately NOT consulted: availability depends
// on which keys this box happens to have, and a table is not malformed because a key is missing.
{
  const { ROWS } = require('./supported-models');
  const { loadSelection, supportedRow } = require('./lib/model-catalog');
  const { file: source, shipped, rows } = loadSelection(null);
  assert.ok(shipped && source === path.join(__dirname, 'models.csv'), `expected the shipped table, got ${source}`);
  assert.ok(rows.length > 3, `the shipped table is suspiciously short: ${rows.length} rows`);
  for (const r of ROWS) {
    assert.ok(rows.some((c) => c.harness === r.harness && c.model === r.model),
      `supported model ${r.harness}/${r.model} has no models.csv row — cast models add could not select it`);
  }

  const LEVELS = ['SOTA', 'L1', 'L2', 'L3', 'L4'];
  // Every axis a multi-level twin must agree on — the CSV columns minus `level` and the two
  // override columns, which are per level by definition (sonnet-5-5 wins L3 on both, L2 on neither).
  const AXES = ['mode', 'harness', 'model', 'efforts', 'image', 'reasoning', 'coding', 'cost', 'use'];
  const YN = ['Y', 'N'];
  const seen = new Map();
  for (const r of rows) {
    const at = `models.csv row ${r.harness}/${r.model}`;
    // Launchability is the join: a row cast cannot launch is a row route must never name, and the
    // tool only WARNS about it — so this is where a typo like `gemini-3.7-flash` with no
    // supported-models.js row gets caught instead of silently shrinking the model catalog.
    assert.ok(supportedRow(r.harness, r.model), `${at} has no supported-models.js twin — route excludes it`);
    assert.ok(['cli', 'api'].includes(r.mode), `${at}: mode '${r.mode}'`);
    assert.ok(LEVELS.includes(r.level), `${at}: level '${r.level}' is not one of ${LEVELS.join('|')}`);
    assert.ok(YN.includes(r.image), `${at}: image '${r.image}'`);
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
    // 2026-08-23: claude/sonnet-5-5 sits at L2 and L3 so `bounded` and `mechanical` can both reach
    // it, its subscription making the L3 list price misleading). The join onto supported-models.js is on
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
  const CLASS_LEVELS = { planner: ['SOTA'], broad: ['L1'], bounded: ['L2'], mechanical: ['L3'] };
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
  // an empty stderr is the proof that nothing was quietly left out of the model catalog. Run from
  // OUTSIDE, it is the shipped table the command reads.
  const quiet = spawnSync('node', [TOOL, 'route', '--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--explain'],
    { encoding: 'utf8', env: ENV, cwd: OUTSIDE });
  assert.strictEqual(quiet.stderr, '', `loading the shipped table must warn about nothing:\n${quiet.stderr}`);
  assert.strictEqual(JSON.parse(quiet.stdout).explain[0].source, source);
}

process.stdout.write('all route tests passed\n');

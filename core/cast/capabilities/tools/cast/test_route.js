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
//   * The SHIPPED table gets ONE arm, at the bottom: its structure and its approved levels and scores — every row joins
//     supported-models.js, every cell is in its vocabulary, no duplicates, every class still has a routable
//     row, and loading it emits NO warning. That is the half that can be wrong without anyone
//     noticing (a decimal comma silently shifted four rows out of routing that same day).
//
// Hermetic environment (availability is a PRESENCE test, never a spend): the api keys of the two
// providers named in FAKE_KEYS are pinned to synthetic placeholders and XDG_DATA_HOME points at an
// empty dir, so this box's real opencode credential store cannot decide a verdict. Available in
// these runs: every claude and codex row (the harness holds its own account login), the opencode
// rows of a provider whose key is faked and the api row of such a provider. Unavailable: the
// opencode rows of every other provider.
//
// No supported model is named here: each arm picks its models by the property it depends on
// (example-models.js), so adding, replacing or removing a supported model edits no arm.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { example } = require('./example-models');
const { providers } = require('./providers.json');

const TOOL = path.join(__dirname, 'cast.js');
const EMPTY_XDG = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-route-xdg-'));
const FAKE_KEYS = ['DEEPSEEK_API_KEY', 'GEMINI_API_KEY'];
const ENV = {
  ...process.env,
  ...Object.fromEntries(FAKE_KEYS.map((k) => [k, 'test-fake-not-real'])),
  XDG_DATA_HOME: EMPTY_XDG,
};

// --- the models the arms use ---------------------------------------------------------------------
// Each is picked by the property its arm needs, and no model is picked twice. The level, scores and
// cost an arm gives a model are the arm's own, written into its table: a model needs only its
// harness (for availability), its rungs and, for opencode, the provider that decides its login.
const taken = [];
const take = (what, has) => {
  const m = example(what, has, taken);
  taken.push(m);
  return m;
};
const fiveRungs = (harness) => (m) => m.mode === 'cli' && m.harness === harness && m.rungs.length === 5;
const faked = (m) => FAKE_KEYS.includes(providers[m.provider].env_var);
const freshProvider = (m) => !taken.some((t) => t.provider === m.provider);
// claudeA..D and codexA..D fill the fixture levels top down: SOTA, L1, L2, L3 (the codex SOTA row
// is the one that holds the overrides).
const claudeA = take('a claude model with five effort rungs', fiveRungs('claude'));
const claudeB = take('a second claude model with five effort rungs', fiveRungs('claude'));
const claudeC = take('a third claude model with five effort rungs', fiveRungs('claude'));
const claudeD = take('a fourth claude model with five effort rungs', fiveRungs('claude'));
const codexA = take('a codex model with five effort rungs', fiveRungs('codex'));
const codexB = take('a second codex model with five effort rungs', fiveRungs('codex'));
const codexC = take('a third codex model with five effort rungs', fiveRungs('codex'));
const codexD = take('a fourth codex model with five effort rungs', fiveRungs('codex'));
const fakedOpencodeA = take('an opencode model whose provider key this suite fakes',
  (m) => m.mode === 'cli' && m.harness === 'opencode' && faked(m));
const fakedOpencodeB = take('a second opencode model whose provider key this suite fakes',
  (m) => m.mode === 'cli' && m.harness === 'opencode' && faked(m));
const apiModel = take('an api-mode model', (m) => m.mode === 'api');
// Four opencode models of four different providers, one login each (the "where a login is looked
// for" arm): a key in the installation's env file, no key at all, an api key kept in the store, an
// account login kept in the store. The first also stands for the row that drops at availability.
const apiKeyProvider = (m) => m.mode === 'cli' && m.harness === 'opencode' && providers[m.provider].login === 'api-key' && !faked(m) && freshProvider(m);
const envKeyModel = take('an opencode model whose api-key provider this suite does not fake', apiKeyProvider);
const noKeyModel = take('an opencode model of another api-key provider this suite does not fake', apiKeyProvider);
const storeKeyModel = take('an opencode model of a third api-key provider this suite does not fake', apiKeyProvider);
const accountModel = take('an opencode model whose provider logs in with an account',
  (m) => m.mode === 'cli' && m.harness === 'opencode' && providers[m.provider].login === 'account' && freshProvider(m));

const key = (m) => `${m.harness}/${m.model}`;
const want = (m) => `${key(m)}/${m.mode}`;
const HEAD = 'mode,harness,model,efforts,image,level,reasoning,coding,cost,quality-override,price-override';
// One row of a catalog table: the first nine cells, then the two overrides.
const cells = (m, image, level, reasoning, coding, cost) => [m.mode, m.harness, m.model, m.efforts, image, level, reasoning, coding, cost].join(',');
const csv = (m, image, level, reasoning, coding, cost, qo = 'N', po = 'N') => `${cells(m, image, level, reasoning, coding, cost)},${qo},${po}`;

// --- the fixture table -------------------------------------------------------------------------
// cwd is what selects a table: route finds the installation from cwd (the first folder upward
// holding .rbtv/config/install.json), and that installation's model catalog
// (.rbtv/config/cast/models.csv) is read INSTEAD of the shipped one. So the suite makes itself a
// scratch installation, writes its own table into it, and every logic arm runs there — the
// shipped models.csv is reached only by the arms that run from OUTSIDE, a fresh folder inside no
// installation.
//
// The table is built so each arm has ONE right answer and no tie, and so every axis has a
// discriminating pair: cli vs api, a blank cost, an image row, and one row (a provider whose key
// ENV does not fake) that must drop at availability. The table is the suite's own: it lists an
// api model as a text worker (image=N) so that the api arms have a row, and gives the image flag
// to an opencode model, which carries no level and no score.
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
  HEAD,
  csv(claudeA, 'N', 'SOTA', 7, 7, 50),
  csv(codexA, 'N', 'SOTA', 7, 7, 50, 'Y', 'Y'),
  csv(claudeB, 'N', 'L1', 6, 6, 25),
  csv(codexB, 'N', 'L1', 5, 5, 20),
  csv(claudeC, 'N', 'L2', 5, 5, 10),
  csv(codexC, 'N', 'L2', 4, 4, 5),
  csv(envKeyModel, 'N', 'L2', 5, 5, 15),
  csv(codexD, 'N', 'L3', 3, 2, 1.2),
  csv(fakedOpencodeA, 'N', 'L3', 3, 3, 3.96),
  csv(claudeD, 'N', 'L3', 3, 3, ''),
  csv(apiModel, 'N', 'L3', 3, 3, 9),
  csv(fakedOpencodeB, 'Y', '', '', '', ''),
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
// Level L3; the cheapest priced row there is the fourth codex model at 1.2. Effort 1, and effort_is_floor
// false — only planner floors.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'mechanical', '--optimize', 'price']);
  assert.strictEqual(v._status, 0, `expected a verdict: ${JSON.stringify(v)}`);
  assert.strictEqual(v.verdict, 'route');
  assert.strictEqual(pair(v), want(codexD));
  assert.strictEqual(v.effort, 1);
  assert.strictEqual(v.effort_is_floor, false);
}

// --- a row whose credential does not resolve drops at availability -------------------------------
// The env-key model rides a credential ENV does not fake, and it is the best-scoring L2 row in the fixture —
// so if availability ever stopped running, this arm's verdict would change.
{
  const v = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.ok(dropped(v, 'availability').includes(key(envKeyModel)), JSON.stringify(dropped(v, 'availability')));
  assert.ok(!v.alternates.some((a) => key(a) === key(envKeyModel)), 'an unavailable row must not survive as a backup');
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
      // identical but for where the ranking came from, which every verdict states
      assert.strictEqual(dflt.optimize_from, "cast's default");
      assert.strictEqual(priced.optimize_from, '--optimize');
      assert.deepStrictEqual({ ...dflt, _stderr: '', optimize_from: null }, { ...priced, _stderr: '', optimize_from: null },
        `${cls}/${type}: the default must answer exactly what --optimize price answers`);
    }
  }

  // The trace still says which one the caller asked for — an --explain reader can tell an omitted
  // flag from an explicit one, even though the ranking is the same.
  const mech = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--explain']);
  assert.strictEqual(pair(mech), want(codexD), 'mechanical default = the cheapest L3 row');
  const rank = mech.explain.find((e) => e.stage === 'optimize' && e.action === 'rank');
  assert.strictEqual(rank.optimize, 'default');
  assert.ok(/price, for every class/.test(rank.rule || ''), JSON.stringify(rank));
  // A blank cost is excluded from the default exactly as it is from an explicit price pick.
  assert.ok(dropped(mech, 'optimize').includes(key(claudeD)), JSON.stringify(dropped(mech, 'optimize')));

  // ONE LEVEL PER CLASS (owner ruling 2026-09-24), pinned so it cannot drift back silently: when a
  // class spanned two levels, the price default handed it to the cheaper level's row (planning went
  // to an L1 model). Now the other levels drop at the class stage and never enter the ranking.
  const planner = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--explain']);
  assert.strictEqual(pair(planner), want(codexA), 'planner default stays at SOTA');
  const bounded = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--explain']);
  assert.strictEqual(pair(bounded), want(codexC), 'bounded default = cheapest L2');
  for (const v of [planner, bounded]) {
    assert.ok(dropped(v, 'class').includes(key(codexB)), `the cheaper L1 row must drop at the class stage: ${JSON.stringify(dropped(v, 'class'))}`);
  }

  // Batch: an omitted optimize on an agent takes the same default as the flag form.
  const b = routeBatch([{ name: 'm', access: 'bounded', type: 'code', class: 'mechanical' }]);
  assert.strictEqual(b._status, 0, JSON.stringify(b));
  assert.strictEqual(`${b.agents[0].harness}/${b.agents[0].model}`, key(codexD));
}

// --- max quality NEVER leaves the class's own levels --------------------------------------------
// class=bounded is L2 only. The SOTA and the L1 claude models are available and score higher, and
// neither may be picked: a bounded executor at max quality gets the best L2 (the third claude model).
{
  const v = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.strictEqual(pair(v), want(claudeC));
  assert.ok(dropped(v, 'class').includes(key(claudeB)), JSON.stringify(dropped(v, 'class')));
  assert.strictEqual(v.effort, 2);
  assert.ok(dropped(v, 'class').includes(key(claudeA)),
    `the SOTA row must be dropped at the class filter: ${JSON.stringify(dropped(v, 'class'))}`);
}

// --- planner floors the effort -----------------------------------------------------------------
{
  const v = route(['--access', 'open', '--type', 'text', '--class', 'planner', '--optimize', 'quality']);
  assert.strictEqual(pair(v), want(codexA));
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
  assert.ok(boundedOrder.includes(key(apiModel)), `the api row must be IN the bounded ranking: ${JSON.stringify(boundedOrder)}`);

  const open = route(['--access', 'open', '--type', 'text', '--class', 'mechanical', '--optimize', 'quality', '--explain']);
  assert.ok(dropped(open, 'access').includes(key(apiModel)),
    `the api row must be dropped at the access stage: ${JSON.stringify(dropped(open, 'access'))}`);
  assert.strictEqual(pair(open), want(codexD), 'access=open must exclude every api row');
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
// No other flag is needed, and no other question is asked: the image row has no level and no
// score, so no class reaches it, yet it is what comes back. Effort is the nominal 1.
{
  const v = route(['--caps', 'image']);
  assert.strictEqual(v._status, 0, `the image short-circuit must answer: ${JSON.stringify(v)}`);
  assert.strictEqual(pair(v), want(fakedOpencodeB));
  assert.strictEqual(v.effort, 1);
  // ...and against a table with no image=Y row at all, the honest answer is zero_candidates naming
  // the missing axis — NEVER a malformed_request over the flags the short-circuit deliberately
  // skips. Its own one-row table: whether the SHIPPED table happens to carry an image row is the
  // owner's data, and this arm is about the code path.
  const noImage = scratchInstallation('cast-route-noimage-');
  fs.writeFileSync(catalogOf(noImage), [HEAD, csv(claudeB, 'N', 'L1', 6, 6, 25), ''].join('\n'));
  const none = route(['--caps', 'image'], noImage);
  assert.strictEqual(none.error, 'zero_candidates', JSON.stringify(none));
  assert.ok(/image=Y/.test(none.details), none.details);

  // An image model is chosen by capability and by nothing else: no class names it or ranks it,
  // whatever its other cells hold. Here it carries a level and is the cheapest and best L3 row.
  const leveled = scratchInstallation('cast-route-image-level-');
  fs.writeFileSync(catalogOf(leveled), [HEAD, csv(fakedOpencodeB, 'Y', 'L3', 7, 7, 0.1, 'Y', 'Y'), csv(codexD, 'N', 'L3', 3, 2, 1.2), ''].join('\n'));
  for (const optimize of ['price', 'quality']) {
    const general = route(['--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--optimize', optimize, '--explain'], leveled);
    assert.strictEqual(pair(general), want(codexD), `an image model must never take a ${optimize} verdict`);
    assert.deepStrictEqual(general.alternates, [], 'nor ride along as a backup');
    assert.deepStrictEqual(dropped(general, 'class'), [key(fakedOpencodeB)]);
  }
  assert.strictEqual(pair(route(['--caps', 'image'], leveled)), want(fakedOpencodeB));
  // In the fixture no general ranking holds the image row either, for any class.
  for (const cls of ['planner', 'broad', 'bounded', 'mechanical']) {
    const v = route(['--access', 'bounded', '--type', 'text', '--class', cls, '--optimize', 'quality', '--explain']);
    assert.ok(!JSON.stringify(v.explain.filter((e) => e.stage === 'optimize')).includes(fakedOpencodeB.model), cls);
  }
}

// --- price vs quality pull the bounded class apart ---------------------------------------------
// class=bounded is L2: the cheapest row is the third codex model (cost 5), the best the third claude (reasoning 5).
// One class, two optimizers, two different answers.
{
  const cheap = route(['--access', 'bounded', '--type', 'code', '--class', 'bounded', '--optimize', 'price']);
  assert.strictEqual(pair(cheap), want(codexC));
  assert.strictEqual(cheap.effort, 2, 'bounded is effort 2 on code');

  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality']);
  assert.strictEqual(pair(best), want(claudeC));
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
    HEAD,
    csv(claudeC, 'N', 'L2', 6, 5, 3),
    csv(claudeD, 'N', 'L2', 3, 2, 9),
    // BLANK cells on purpose: a blank override reads as N, and a blank cost as unknown.
    `${cells(claudeB, 'N', 'L2', 7, 6, '')},,`,
    'cli,opencode,not-a-real-model,3,N,L2,6,6,1,N,N',
    '',
  ].join('\n'));

  const cheap = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price', '--explain'], vault);
  assert.strictEqual(pair(cheap), want(claudeC), "the installation's table IS the model catalog — cost 3 beats cost 9");
  assert.ok(/no supported-models\.js row for opencode\/not-a-real-model/.test(cheap._stderr),
    `an unjoinable CSV row must warn LOUDLY on stderr: ${cheap._stderr}`);
  // A blank cost sits OUT of every price pick — unknown is not cheap. It stays eligible for
  // quality, where its reasoning 7 beats every priced row.
  assert.ok(dropped(cheap, 'optimize').includes(key(claudeB)),
    `blank-cost rows must drop AT THE OPTIMIZE STAGE with a reason: ${JSON.stringify(dropped(cheap, 'optimize'))}`);
  const best = route(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'], vault);
  assert.strictEqual(pair(best), want(claudeB), 'a blank-cost row is still eligible for quality');

  // and the shipped model catalog is genuinely IGNORED while the installation has its own: the
  // trace names the file that was read, and counts its four rows, three of them joined.
  const read = cheap.explain[0];
  assert.strictEqual(read.source, fs.realpathSync(overrideFile), 'the trace must name the file it actually read');
  assert.deepStrictEqual([read.csv_rows, read.joined], [4, 3], JSON.stringify(read));
}

// --- quality-override / price-override, and selection as the one gate ---------------------------
// Its own scratch vault, rewritten per arm: these two columns ARE the routing decision, so each
// arm changes exactly one cell and pins what moved. Every row is a claude or codex model, which the
// hermetic env makes available, so nothing here can be decided by a credential.
{
  const vault = scratchInstallation('cast-route-override-');
  const file = catalogOf(vault);
  // level/score/cost chosen so every ranking below has ONE right answer and no tie:
  //   L1: codexB cost 20 (score 5) · claudeB cost 25 (score 6) -> price picks codexB, quality picks claudeB
  //   L2: codexC cost 5 (score 4) · claudeC cost 10 (score 5)   -> price picks codexC, quality picks claudeC
  const BASE = {
    [key(claudeB)]: cells(claudeB, 'N', 'L1', 6, 6, 25),
    [key(codexB)]: cells(codexB, 'N', 'L1', 5, 5, 20),
    [key(claudeC)]: cells(claudeC, 'N', 'L2', 5, 5, 10),
    [key(codexC)]: cells(codexC, 'N', 'L2', 4, 4, 5),
  };
  // tweak: {harness/model: [quality-override, price-override]}; anything unnamed stays N,N. `only` keeps
  // the named models and leaves the others out of the file.
  const write = (tweak = {}, only = Object.keys(BASE)) => {
    const lines = [HEAD];
    for (const model of only) {
      const [q, pr] = tweak[model] || ['N', 'N'];
      lines.push(`${BASE[model]},${q},${pr}`);
    }
    fs.writeFileSync(file, `${lines.join('\n')}\n`);
  };
  const at = (flags) => route(flags, vault);
  const ranking = (v) => v.explain.filter((e) => e.stage === 'optimize' && e.action !== 'drop').pop().order;

  // 1. the columns are INERT until set: the plain ranking is the pre-2026-08-22 one.
  write();
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price'])), want(codexC));
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'])), want(claudeC));

  // 2. price-override wins its OWN level: sonnet (10) jumps ahead of terra (5) inside L2, so the
  //    cheapest-first ranking now heads with sonnet.
  write({ [key(claudeC)]: ['N', 'Y'] });
  const priced = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price', '--explain']);
  assert.strictEqual(pair(priced), want(claudeC), 'price-override must beat a cheaper row of its own level');
  assert.ok(ranking(priced).indexOf(key(claudeC)) < ranking(priced).indexOf(key(codexC)), JSON.stringify(ranking(priced)));

  // 3. quality-override wins its level against a higher score: terra (4) jumps sonnet (5).
  write({ [key(codexC)]: ['Y', 'N'] });
  const q = at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality', '--explain']);
  assert.deepStrictEqual(ranking(q), [key(codexC), key(claudeC)], JSON.stringify(ranking(q)));

  // 4. each override fires only in the ranking it names — the quality one is silent under --optimize price.
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'price'])), want(codexC));

  // 5. the default is a price ranking (owner ruling 2026-08-22), so price-override is the one
  //    that fires there — for every class, at every level.
  write();
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), want(codexB), 'default = cheapest L1');
  write({ [key(claudeB)]: ['N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), want(claudeB), 'price-override fires in the default');
  write({ [key(claudeC)]: ['N', 'Y'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded'])), want(claudeC), 'price-override fires in the default at the low levels too');

  // 6. quality-override, by the same rule, fires in NEITHER — the default no longer ranks anything
  //    on quality, so it takes an explicit --optimize quality to make one bite.
  write({ [key(claudeC)]: ['Y', 'N'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded'])), want(codexC), 'quality-override must NOT fire in the default');
  write({ [key(codexC)]: ['Y', 'N'] });
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'bounded', '--optimize', 'quality'])), want(codexC), 'the flag DOES bite under --optimize quality');

  // 7. one favorite for both rankings: sonnet holds both overrides and heads its level under
  //    price, under quality and in the default, while every other row keeps its place behind it.
  write({ [key(claudeC)]: ['Y', 'Y'] });
  for (const optimize of [[], ['--optimize', 'price'], ['--optimize', 'quality']]) {
    const v = at(['--access', 'bounded', '--type', 'code', '--class', 'bounded', ...optimize, '--explain']);
    assert.deepStrictEqual(ranking(v), [key(claudeC), key(codexC)], optimize.join(' '));
  }
  //    ...and the override stays inside its level: class broad is untouched by it.
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), want(codexB));

  // 8. selection is the one gate: every row of the file competes, and a model with no row is
  //    never ranked, named or kept as a backup. With both L1 rows gone, class broad has nothing.
  write({}, [key(claudeB), key(claudeC), key(codexC)]);
  const unselected = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'price', '--explain']);
  assert.strictEqual(pair(unselected), want(claudeB), 'the cheaper L1 row has no row, so it cannot win');
  assert.ok(!JSON.stringify(unselected).includes(codexB.model), JSON.stringify(unselected));
  write({}, [key(claudeC), key(codexC)]);
  const none = at(['--access', 'bounded', '--type', 'text', '--class', 'broad', '--optimize', 'quality']);
  assert.deepStrictEqual([none.error, none._status], ['zero_candidates', 1], JSON.stringify(none));

  // 9. no column takes a selected row out of routing: a file that still carries `use` is refused
  //    as a file with an unknown column, never read with that column ignored.
  fs.writeFileSync(file, ['mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
    `${cells(claudeB, 'N', 'L1', 6, 6, 25)},off,N,N`, ''].join('\n'));
  const old = at(['--access', 'bounded', '--type', 'text', '--class', 'broad']);
  assert.strictEqual(old.error, 'no_models', JSON.stringify(old));
  assert.ok(old.details.includes("line 1: unknown column 'use' (the columns are mode, harness, model, efforts, image, level, reasoning, coding, cost, quality-override, price-override)"), old.details);

  // 10. cells are read by header name: a table without the two columns reads them blank, which
  //     is neither override.
  fs.writeFileSync(file, ['mode,harness,model,efforts,image,level,reasoning,coding,cost',
    cells(claudeB, 'N', 'L1', 6, 6, 25), ''].join('\n'));
  assert.strictEqual(pair(at(['--access', 'bounded', '--type', 'text', '--class', 'broad'])), want(claudeB));

  // 11. a table that cannot be read as one is REFUSED with its file and line, never half-obeyed:
  //     an unknown column, a row whose cell count is not the header's (what a decimal comma
  //     makes), a missing harness column, a blank model, an empty file.
  for (const [lines, where, why] of [
    [[`${HEAD},notes`, 'cli,claude,example-model,5,N,L1,6,6,25,N,N,x'], 'line 1:', "unknown column 'notes'"],
    [[HEAD, '', 'cli,claude,example-model,5,N,L1,6,6,2,5,N,N'], 'line 3:', '12 cells where the header has 11'],
    [[HEAD, 'cli,claude,example-model,5,N,L1,6,6,25'], 'line 2:', '9 cells where the header has 11'],
    [['mode,model,level', 'cli,example-model,L1'], 'line 1:', "no 'harness' column"],
    [[HEAD, 'cli,claude,,5,N,L1,6,6,25,N,N'], 'line 2:', 'blank model'],
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
  assert.strictEqual(pair(v.agents[0]), want(codexA));
  assert.strictEqual(pair(v.agents[1]), want(codexD));
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
  const v = routeBatch([{ ...FIXER_AGENT, model: 'example-model' }]);
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
  assert.strictEqual(probe({ harness: claudeA.harness, model: 'example-model', provider: claudeA.provider }).status, 0);
}

// --- where a login is looked for -------------------------------------------------------------------
// Its own scratch installation, table and opencode store, so each source is the ONLY thing that
// can make a row available: the installation's env file, or the provider's entry in the store.
{
  // In order: a key from the env file, no key anywhere, an api key in the store, an account login in the store.
  const LOGINS = [envKeyModel, noKeyModel, storeKeyModel, accountModel];
  const envVar = (m) => providers[m.provider].env_var;
  const storeKey = (m) => providers[m.provider].harnesses.opencode.store_key;
  const states = (...v) => Object.fromEntries(LOGINS.map((m, i) => [m.model, v[i]]));
  const inst = scratchInstallation('cast-route-login-');
  fs.writeFileSync(catalogOf(inst), [HEAD, ...LOGINS.map((m) => csv(m, 'N', 'L2', 5, 5, 15)), ''].join('\n'));
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
    return Object.fromEntries(LOGINS.map((m) => [m.model, String(!gone.includes(key(m)))]));
  };

  // Nothing anywhere: every row is unavailable. `KEY=` with no value is NOT a key, quoted or not.
  assert.deepStrictEqual(available({}, `${envVar(envKeyModel)}=\n${envVar(noKeyModel)}=""\n`),
    states('false', 'false', 'false', 'false'));
  // The env file of the installation found from cwd (a folder BELOW the root) serves a key row.
  assert.deepStrictEqual(available({}, `# comment\n${envVar(envKeyModel)}=test-fake-not-real\n`),
    states('true', 'false', 'false', 'false'));
  // The store serves an API key kept by opencode and an account login kept by opencode
  // alike: what counts is the provider's entry in the harness's store.
  assert.deepStrictEqual(available({ [storeKey(storeKeyModel)]: { type: 'api' }, [storeKey(accountModel)]: { type: 'oauth' } }, ''),
    states('false', 'false', 'true', 'true'));
  // An account-login provider has no key variable: it is never "always available", and a stray
  // key variable named after it does not stand in for the missing store entry.
  assert.strictEqual(available({}, '', { [`${accountModel.provider.toUpperCase()}_API_KEY`]: 'test-fake-not-real' })[accountModel.model], 'false');
}

// --- the SHIPPED table: its structure and its approved calibration -------------------------------
// The one arm that reads the real models.csv. It checks that the table can be obeyed: every row
// joinable and launchable, one row for every supported model and no other, every cell in its
// vocabulary, and every class still holding a row. Credentials are deliberately NOT consulted:
// availability depends on which keys this box happens to have, and a table is not malformed
// because a key is missing. It also pins the level and the two scores of every model, which are
// rbtv's proposal to every installation: a change to one is made here and in the file together.
{
  const { ROWS } = require('./supported-models');
  const { loadSelection, supportedRow } = require('./lib/model-catalog');
  const { file: source, shipped, rows } = loadSelection(null);
  assert.ok(shipped && source === path.join(__dirname, 'models.csv'), `expected the shipped table, got ${source}`);
  const name = (r) => `${r.harness}/${r.model}`;
  // One row per supported model: a repeated model, a model with no row (cast models add could not
  // select it) and a row cast cannot launch (route would exclude it with a warning) all fail here.
  assert.deepStrictEqual(rows.map(name).sort(), ROWS.map(name).sort());

  const LEVELS = ['SOTA', 'L1', 'L2', 'L3'];
  for (const r of rows) {
    const at = `models.csv row ${name(r)}`;
    assert.strictEqual(supportedRow(r.harness, r.model).mode, r.mode, `${at}: mode '${r.mode}'`);
    assert.ok(['Y', 'N'].includes(r.image), `${at}: image '${r.image}'`);
    assert.ok(/^\d+$/.test(r.efforts), `${at}: efforts is '${r.efforts}' — expected a whole number`);
    // The overrides are an installation's preference: rbtv ships the columns and proposes none.
    for (const col of ['quality-override', 'price-override']) {
      assert.strictEqual(r[col], '', `${at}: ${col} is '${r[col]}' — the shipped model catalog leaves it blank`);
    }
    // Cost may be blank (unknown), but anything else must be a number. This is the arm that
    // catches a decimal COMMA: '4,4' shifts every later cell one column left, which silently
    // dropped four models out of routing on 2026-08-22 before anyone noticed.
    assert.ok(r.cost === '' || Number.isFinite(Number(r.cost)),
      `${at}: cost is '${r.cost}' — a number, or blank for unknown (a decimal comma shifts the whole row)`);
    if (r.image === 'Y') {
      // An image model has no level and no score: blank, never a zero that would rank it.
      assert.deepStrictEqual([r.level, r.reasoning, r.coding], ['', '', ''], `${at}: an image model carries no level and no score`);
    } else {
      assert.ok(r.cost !== '', `${at}: a blank cost keeps the model out of every price ranking`);
    }
  }

  // level / reasoning / coding of every general model, as approved 2026-10-10.
  const APPROVED = {
    'codex/gpt-6-astra': 'SOTA/7/7', 'claude/fable-5-1': 'SOTA/7/7',
    'claude/opus-5-5': 'L1/6/6', 'opencode/grok-4.7': 'L1/6/6', 'codex/gpt-6.1-sol': 'L1/4/4', 'opencode/fugu-ultra': 'L1/6/6',
    'claude/sonnet-5-5': 'L2/3/3', 'opencode/glm-5.3': 'L2/4/4', 'codex/gpt-5.6-terra': 'L2/3/3', 'opencode/deepseek-v4-pro': 'L2/3/3',
    'opencode/k3': 'L2/4/4', 'opencode/gemini-3.1-pro-preview': 'L2/4/3', 'opencode/sakana-namazu': 'L2/4/4',
    'claude/haiku-5-5': 'L3/3/3', 'codex/gpt-6-luna': 'L3/3/3', 'opencode/deepseek-v4-flash': 'L3/3/2', 'opencode/gemini-3.8-flash': 'L3/3/3',
  };
  const general = rows.filter((r) => r.image !== 'Y');
  assert.deepStrictEqual(Object.fromEntries(general.map((r) => [name(r), `${r.level}/${r.reasoning}/${r.coding}`])), APPROVED,
    'the shipped level and scores differ from the approved ones: a level, a score and a new or removed model are the owner\'s rulings; follow core/cast/capabilities/methods/changing-the-supported-models.md');
  const imageRows = rows.filter((r) => r.image === 'Y');
  assert.strictEqual(imageRows.length, 1, 'one image model, so --caps image has one answer');
  for (const level of LEVELS) assert.ok(general.some((r) => r.level === level), `no models.csv row is left at level ${level}`);
  // No superseded version, moving alias or sentinel cost is left behind.
  const text = fs.readFileSync(source, 'utf8');
  for (const gone of ['haiku-4-5', 'gemini-3.7-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'k3-256k', 'L4', '999']) {
    assert.ok(!text.includes(gone), `models.csv still holds '${gone}'`);
  }

  // The shipped table routes every class with no override in play, and --caps image answers the
  // image model, which no general ranking holds. Hermetic env, so the rows whose login is a store
  // entry are out; the claude, codex, deepseek and google rows decide.
  const shippedRoute = (flags) => route([...flags, '--explain'], OUTSIDE);
  for (const [cls, level] of [['planner', 'SOTA'], ['broad', 'L1'], ['bounded', 'L2'], ['mechanical', 'L3']]) {
    const v = shippedRoute(['--access', 'bounded', '--type', 'code', '--class', cls]);
    assert.strictEqual(v._status, 0, JSON.stringify(v));
    assert.strictEqual(rows.find((r) => name(r) === `${v.harness}/${v.model}`).level, level);
    assert.ok(!v.explain.some((e) => e.action === 'override'), `${cls}: the shipped table promotes no row`);
    assert.ok(!JSON.stringify(v.explain.filter((e) => e.stage === 'optimize')).includes(imageRows[0].model), cls);
  }
  assert.strictEqual(pair(shippedRoute(['--caps', 'image'])), `${name(imageRows[0])}/${imageRows[0].mode}`);

  // And loading it must be SILENT. Every exclusion route makes on its own is a stderr warning, so
  // an empty stderr is the proof that nothing was quietly left out of the model catalog. Run from
  // OUTSIDE, it is the shipped table the command reads.
  const quiet = spawnSync('node', [TOOL, 'route', '--access', 'bounded', '--type', 'text', '--class', 'mechanical', '--explain'],
    { encoding: 'utf8', env: ENV, cwd: OUTSIDE });
  assert.strictEqual(quiet.stderr, '', `loading the shipped table must warn about nothing:\n${quiet.stderr}`);
  assert.strictEqual(JSON.parse(quiet.stdout).explain[0].source, source);

  // And no other file of the repository names a supported model, by its short name or by the
  // harness's id: a test asks example-models.js for one by a property, help text takes its example
  // from the table and a document writes HARNESS MODEL. So a change to the supported models edits
  // the two tables, the APPROVED list above and the record of sources, and nothing else.
  const REPO = path.join(__dirname, '..', '..', '..', '..', '..');
  const rel = (...parts) => parts.join('/');
  const CAST = 'core/cast/capabilities';
  const NAMED_ON_PURPOSE = [
    rel(CAST, 'tools/cast/supported-models.js'), rel(CAST, 'tools/cast/models.csv'), // the two tables
    rel(CAST, 'methods/changing-the-supported-models/score-and-cost-sources.md'), // where each cost and score came from
    'core/ignite/capabilities/tools/ignite/config.js', // DREAMER_MODEL, the Dreamer's default
  ];
  const names = [...new Set(ROWS.flatMap((r) => [r.model, r.id]))];
  const escaped = names.map((n) => n.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')).join('|');
  const naming = new RegExp(`(^|[^A-Za-z0-9])(${escaped})(?![A-Za-z0-9])`);
  const TEXT = /\.(js|cjs|mjs|py|md|json|csv|sh|ps1|toml|ya?ml|txt)$/;
  // `repository` is the checkout of another repository inside a connector component.
  const SKIPPED = ['.git', 'node_modules', '__pycache__', 'repository'];
  const named = [];
  (function walk(dir) {
    for (const entry of fs.readdirSync(path.join(REPO, dir), { withFileTypes: true })) {
      const at = dir ? rel(dir, entry.name) : entry.name;
      if (entry.isDirectory()) { if (!SKIPPED.includes(entry.name)) walk(at); continue; }
      if (!TEXT.test(entry.name) || NAMED_ON_PURPOSE.includes(at)) continue;
      let lines = fs.readFileSync(path.join(REPO, at), 'utf8');
      // this arm is the one place of this file that names shipped models
      if (path.join(REPO, at) === __filename) lines = lines.replace(/\/\/ --- the SHIPPED table[\s\S]*?\n}\n/, (arm) => arm.replace(/[^\n]/g, ''));
      lines.split('\n').forEach((line, i) => { if (naming.test(line)) named.push(`${at}:${i + 1}: ${line.trim().slice(0, 100)}`); });
    }
  })('');
  assert.deepStrictEqual(named, [], `these lines name a supported model; take the model from example-models.js (a test), from the table (help text) or write HARNESS MODEL (a document):\n${named.join('\n')}`);
}

// --- the installation's default ranking (lib/defaults.js, key `route`) --------------------------
// A call with no --optimize ranks as the installation says, and every verdict states the ranking
// and where it came from. class=bounded on text: price answers the third codex model, quality the third claude.
{
  const root = scratchInstallation('cast-route-defaults-');
  fs.copyFileSync(catalogOf(FIXTURE), catalogOf(root));
  const file = path.join(root, '.rbtv', 'config', 'cast', 'defaults.json');
  const ask = ['--access', 'bounded', '--type', 'text', '--class', 'bounded'];

  const none = route(ask, root);
  assert.deepStrictEqual([pair(none), none.optimize, none.optimize_from], [want(codexC), 'price', "cast's default"]);

  fs.writeFileSync(file, '{"route":"quality"}\n');
  const set = route([...ask, '--explain'], root);
  assert.deepStrictEqual([pair(set), set.optimize, set.optimize_from], [want(claudeC), 'quality', file]);
  assert.deepStrictEqual(set.explain.find((e) => e.action === 'default'), { stage: 'optimize', action: 'default', optimize: 'quality', source: file });
  // the call's own flag wins over the installation
  const flag = route([...ask, '--optimize', 'price'], root);
  assert.deepStrictEqual([pair(flag), flag.optimize, flag.optimize_from], [want(codexC), 'price', '--optimize']);
  // a batch agent with no optimize takes the same default
  const batchFile = path.join(root, 'agents.json');
  fs.writeFileSync(batchFile, JSON.stringify([{ name: 'a', access: 'bounded', type: 'text', class: 'bounded' }]));
  const batch = route(['--batch', batchFile], root);
  assert.deepStrictEqual([batch.agents[0].model, batch.agents[0].optimize_from], [claudeC.model, file]);
  // a file that sets only the fallback leaves the route default cast's own
  fs.writeFileSync(file, '{"fallback":"price"}\n');
  assert.strictEqual(route(ask, root).optimize_from, "cast's default");

  // a defaults file cast cannot use answers bad_defaults, naming the file
  for (const [text, why] of [['{"route":"best"}', 'route is "best" (one of price, quality)'], ['{"rout":"price"}', "unknown key 'rout' (the keys are route, fallback)"], ['[]', 'it holds no object']]) {
    fs.writeFileSync(file, text);
    const bad = route(ask, root);
    assert.deepStrictEqual([bad._status, bad.error, bad.details], [1, 'bad_defaults', `cannot read cast's defaults ${file}: ${why}`]);
  }
}

process.stdout.write('all route tests passed\n');

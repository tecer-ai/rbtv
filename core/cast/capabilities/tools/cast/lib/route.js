'use strict';

// cast — `cast route` — the deterministic (harness, model, mode, effort) selector.
//
// Route answers ONE question: given five facts about a job (the interview below), which
// (harness, model, mode, effort) runs it. Purity holds — no network, no clock, no randomness, so
// the same flags against the same model catalog always yield the same verdict.
//
// Two inputs, deliberately split by who edits them:
//   the model catalog     the ROUTING axes (level, scores, cost, image) — owner-editable data. The
//                         installation's own file when it has one, else the shipped one
//                         (lib/model-catalog.js `loadSelection`).
//   supported-models.js   the LAUNCH mechanics (harness-native id, effort ladder, provider) — code.
// Route JOINS them on harness+model. A model catalog row with no supported-models.js twin is
// EXCLUDED with a loud stderr warning: route must never answer with something cast cannot launch.
// Availability reads `providers.json`: which login each row's provider needs and where it is kept.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { stores: STORES, providers: PROVIDERS } = require('../providers.json');

const { fail } = require('./core');
const { installationRoot, envFileHasKey } = require('./installation');
const { DefaultsError, loadDefaults } = require('./defaults');
const { CatalogError, loadSelection, supportedRow } = require('./model-catalog');

const ROUTE_USAGE = 'cast route --access open|bounded --type code|text --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps image] [--explain]';
// The forms that ask nothing as flags. Kept OUT of ROUTE_USAGE so the top-level `cast -h` stays
// one line per verb; the route help page and every refusal print all of them.
const ROUTE_FORMS = ['cast route --caps image          # short-circuit, no other flags',
  'cast route --batch agents.json    # a whole team in one call (- reads stdin)'];

// Level vocabulary: SOTA > L1 > L2 > L3, plus L4 — the image tier, which NO class admits, so an
// L4 row is reachable only through the `--caps image` short-circuit. Each class below lists its
// eligible levels BEST FIRST; that order is what `--optimize quality` ranks on.
// The class table (spec §4). `levels` is the eligibility filter: each class sees exactly one
// level, so `--optimize` only reorders rows of that level. Effort is a fixed cast-normalized 1-5 number, mapped onto the picked row's own
// rungs at launch (inert ladders accept N and emit no argv).
const CLASSES = {
  // One level per class (owner ruling 2026-09-24; promoteOverrides relies on it): with two levels eligible, price ranking let a
  // lower level's cheaper row take the job (Grok on planning, L1 rows on bounded work).
  planner: { levels: ['SOTA'], effort: { code: 3, text: 3 }, floor: true },
  broad: { levels: ['L1'], effort: { code: 2, text: 3 } },
  bounded: { levels: ['L2'], effort: { code: 2, text: 2 } },
  mechanical: { levels: ['L3'], effort: { code: 1, text: 1 } },
};

// The levels a class reaches, best first: the ones a routed job, and a fallback, can land on.
const LEVELS = Object.values(CLASSES).flatMap((c) => c.levels);

const ACCESS = ['open', 'bounded'];
const TYPES = ['code', 'text'];
const OPTIMIZE = ['price', 'quality'];
// A call that omits --optimize ranks as the installation's defaults say (lib/defaults.js, key
// `route`). Where the installation sets none, the default is PRICE, for every class alike (owner ruling
// 2026-08-22, replacing the tiered SOTA/L1-on-price + L2/L3-on-quality rule of 2026-08-21: one
// rule the owner can hold in their head beat two bands). Omitting the flag is now exactly
// `--optimize price` — same ranking, same blank-cost exclusion, same tie-breaks — and the class's
// levels remain the only thing standing between a job and the cheapest model in the model catalog.
// Consequence to keep in view: `price-override` fires in the default, `quality-override` does not.
const DEFAULT_OPTIMIZE = 'default';
const CAPS = ['image'];

// The `use` column (owner ruling 2026-08-22) — WHO may see a row:
//   route  the normal state; the row competes for `cast route` verdicts. A BLANK cell reads as
//          this, so a CSV written before the column existed keeps behaving exactly as it did.
//   panel  invisible to every verdict; the row still appears in `cast models list --catalog`, which is
//          the surface a panel spreads its seats across (the `sub-agents` skill's panel capability). For a model worth
//          a second opinion but never worth being the single answer.
//   off    invisible to routing entirely. Still LAUNCHABLE by hand (`cast <harness> <model> <n>`)
//          and still listed by `cast models list --catalog` with its use value — nothing is hidden.
// An unrecognised value is NEVER guessed: the row drops from routing with a loud warning. One
// column rather than two flags because `route=Y` + `panel-only=Y` would be a state with no
// meaning, and the code would have to invent a winner for it.
const USE_VALUES = ['route', 'panel', 'off'];
const USE_DEFAULT = 'route';

// The two override columns (same ruling). `Y` means: inside ITS OWN LEVEL, this row wins the named
// ranking whatever the numbers say. It never bypasses a filter: availability, --caps, --access and
// the class level all run first, so an override can only reorder survivors. A model listed at two
// levels carries its overrides per line, so it can win one level and not the other.
const OVERRIDE = { quality: 'quality_override', price: 'price_override' };

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

// providers.json writes a path under the user's home folder with a leading `~`.
function expandHome(file) {
  return file.replace(/^~(?=\/|$)/, os.homedir());
}

// A harness that keeps its own credential store has an entry in providers.json `stores`, keyed by
// the harness name. Presence of the provider's key in that file IS the login — cast never spends
// a call to test availability.
function storePath(harness) {
  const store = STORES[harness];
  if (!store) return null;
  const base = process.env[store.base_env] || expandHome(store.base_default);
  return path.join(base, store.path);
}

function storedCredential(harness, key) {
  const file = storePath(harness);
  if (!file || !key) return false;
  const data = readJson(file);
  return !!(data && Object.prototype.hasOwnProperty.call(data, key));
}

// What a row's login check can look at: the provider's key variable (when it has one) and the
// provider's entry in the harness's own store (when the harness keeps one). A row that names a
// provider providers.json does not hold, or a harness that provider does not list, is a broken
// table: refused by name, because no login can be looked up for it.
function loginSources(spec) {
  const provider = PROVIDERS[spec.provider];
  const harness = provider && provider.harnesses[spec.harness];
  if (!harness) {
    fail(`refused: supported-models.js row ${spec.harness}/${spec.model} names provider '${spec.provider}', which providers.json does not list for harness '${spec.harness}'`);
  }
  return { envVar: provider.env_var, storeKey: harness.store_key };
}

// Availability: an explicit `available: false` drops the row. A row with nothing to look at (a
// claude or codex harness row: the harness holds its own account login) is always available.
// Otherwise the key variable must be set, in the OS environment first and then in the
// installation's environment file, or the harness's store must hold the provider's entry. An
// `api` row has no store, so only the key variable can serve it. An absent login drops the row —
// never an error.
function isAvailable(spec, root) {
  return loginFoundIn(spec, root) !== null;
}

// Where that check found the row's login, in words for a report, or null when it found none. A
// row with nothing to look at answers with its harness: the harness holds the login itself.
function loginFoundIn(spec, root) {
  if (spec.available === false) return null;
  const { envVar, storeKey } = loginSources(spec);
  if (!envVar && !storeKey) return `the ${spec.harness} harness's own login`;
  if (envVar && process.env[envVar]) return `${envVar} in the OS environment`;
  if (envVar && envFileHasKey(root, envVar)) return `${envVar} in the installation's environment file`;
  return storedCredential(spec.harness, storeKey) ? `'${storeKey}' in the ${spec.harness} store` : null;
}

function unavailableReason(spec) {
  if (spec.available === false) return 'marked available: false in supported-models.js';
  const { envVar, storeKey } = loginSources(spec);
  const noStore = `no stored '${storeKey}' credential in the ${spec.harness} store`;
  if (!envVar) return noStore;
  return storeKey
    ? `${envVar} absent in OS env and the env file, and ${noStore}`
    : `${envVar} absent in both OS env and the env file`;
}

// --- the model catalog -------------------------------------------------------------------------

// The table in force for this installation, or the `no_models` answer when it cannot be read.
function loadCatalog(root) {
  try { return loadSelection(root); } catch (e) {
    if (!(e instanceof CatalogError)) throw e;
    process.stdout.write(`${JSON.stringify({ error: 'no_models', details: e.message })}\n`);
    return process.exit(1);
  }
}

// The installation's defaults, or the `bad_defaults` answer when its file cannot be used.
function loadRouteDefaults(root) {
  try { return loadDefaults(root); } catch (e) {
    if (!(e instanceof DefaultsError)) throw e;
    process.stdout.write(`${JSON.stringify({ error: 'bad_defaults', details: e.message })}\n`);
    return process.exit(1);
  }
}

const num = (v) => (v === '' ? null : Number(v));

// JOIN — the model catalog row carries the axes, its supported-models.js twin carries the launch
// spec. No twin means route could name something cast cannot run, so the row is dropped and the
// drop is LOUD.
function joinCatalog(csvRows, warnings) {
  const joined = [];
  for (const c of csvRows) {
    const spec = supportedRow(c.harness, c.model);
    const label = `${c.harness}/${c.model}`;
    if (!spec) {
      warnings.push(`models.csv line ${c._line}: no supported-models.js row for ${label} — excluded (cast cannot launch it)`);
      continue;
    }
    if (spec.mode !== c.mode) {
      warnings.push(`models.csv line ${c._line}: ${label} says mode=${c.mode}, supported-models.js says mode=${spec.mode} — using supported-models.js`);
    }
    const use = c.use === '' ? USE_DEFAULT : c.use;
    if (!USE_VALUES.includes(use)) {
      warnings.push(`models.csv line ${c._line}: ${label} has use='${c.use}' — expected ${USE_VALUES.join(' | ')} (blank = ${USE_DEFAULT}) — excluded from routing`);
    }
    joined.push({
      harness: c.harness,
      model: c.model,
      mode: spec.mode,
      level: c.level,
      image: c.image === 'Y',
      efforts: num(c.efforts),
      reasoning: num(c.reasoning),
      coding: num(c.coding),
      cost: num(c.cost),
      use,
      quality_override: c['quality-override'] === 'Y',
      price_override: c['price-override'] === 'Y',
      spec,
      _line: c._line,
    });
  }
  return joined;
}

// --- selection ---------------------------------------------------------------------------------

const label = (r) => `${r.harness}/${r.model}`;

function drop(trace, stage, row, reason) {
  trace.push({ stage, action: 'drop', harness: row.harness, model: row.model, reason });
}

// Blank score = 0 in tie-breaks (spec §5). Type absent (image short-circuit) reads as text.
// `both` is the type of a fallback, which does not know its task: the two scores added.
const scoreOf = (r, type) => (type === 'both' ? (r.coding ?? 0) + (r.reasoning ?? 0)
  : ((type === 'code' ? r.coding : r.reasoning) ?? 0));

function byKey(rows, keyFn) {
  return rows.slice().sort((a, b) => {
    const ka = keyFn(a);
    const kb = keyFn(b);
    for (let i = 0; i < ka.length; i++) {
      if (ka[i] < kb[i]) return -1;
      if (ka[i] > kb[i]) return 1;
    }
    return 0;
  });
}

// price: cheapest -> higher score -> alphabetical harness, then model. A blank cost is not "free":
// the row sits OUT of every price pick (it is still eligible for quality).
// quality: highest level WITHIN the class's eligible levels -> higher score -> lower cost -> alpha.
// A blank cost sorts last in that tie-break (Infinity) — unknown is never preferred as cheaper.
// default (flag omitted): identical to `price` in every respect — it is the same ranking under a
// different trace label, so the reader of an --explain can still see the flag was omitted.
// Returns the FULL ranked list, best first: the caller takes the head as the verdict and the next
// two as backups.
// An override lifts the flagged rows to the head of the ranking, keeping their relative order;
// every other row keeps its place, so a ranking with no flagged row is unchanged. That is "wins
// its own level" because every class sees exactly ONE level (CLASSES) — a class admitting two
// levels again would need this lift scoped per level.
function promoteOverrides(ranked, flag, trace, optimize) {
  const flagged = ranked.filter((r) => r[flag]);
  if (!flagged.length) return ranked;
  const out = [...flagged, ...ranked.filter((r) => !r[flag])];
  trace.push({ stage: 'optimize', action: 'override', optimize, column: flag.replace('_', '-'),
    promoted: flagged.map(label), order: out.map(label) });
  return out;
}

function pick(rows, optimize, type, levels, trace) {
  const priceKey = (r) => [r.cost, -scoreOf(r, type), r.harness, r.model];
  const qualityKey = (r) => [levels.indexOf(r.level), -scoreOf(r, type),
    r.cost == null ? Infinity : r.cost, r.harness, r.model];
  if (optimize === 'price' || optimize === DEFAULT_OPTIMIZE) {
    const priced = rows.filter((r) => {
      if (r.cost != null) return true;
      drop(trace, 'optimize', r, 'blank cost in models.csv — unknown is not cheap, so it is excluded from every price-ranked pick (--optimize price, and the default)');
      return false;
    });
    if (!priced.length) return [];
    const ranked = byKey(priced, priceKey);
    trace.push({ stage: 'optimize', action: 'rank', optimize,
      ...(optimize === DEFAULT_OPTIMIZE ? { rule: 'no --optimize given: price, for every class' } : {}),
      order: ranked.map(label) });
    return promoteOverrides(ranked, OVERRIDE.price, trace, optimize);
  }
  if (optimize === 'quality') {
    const ranked = byKey(rows, qualityKey);
    trace.push({ stage: 'optimize', action: 'rank', optimize, ceiling: levels[0], order: ranked.map(label) });
    return promoteOverrides(ranked, OVERRIDE.quality, trace, optimize);
  }
  throw new Error(`unreachable: unknown optimize '${optimize}'`);
}

// The verdict IS the top pick; `alternates` carries the next two of the SAME ranking as backups
// for when the first cannot be launched. They share the effort — effort comes from the class, not
// from the row.
function verdictFor(ranked, effort, isFloor, optimize) {
  const [row] = ranked;
  return {
    verdict: 'route',
    harness: row.harness,
    model: row.model,
    mode: row.mode,
    effort,
    effort_is_floor: !!isFloor,
    optimize: optimize.value,
    optimize_from: optimize.from,
    alternates: ranked.slice(1, 3).map((r) => ({ harness: r.harness, model: r.model, mode: r.mode })),
  };
}

// The pipeline, in the spec's order: availability -> image short-circuit -> access ->
// class levels -> optimize -> effort. Every filter records why each row left.
// The ranking of one request and where it came from: the call's own --optimize, else the
// installation's defaults file when it sets `route`, else cast's default.
function optimizeOf(req, defaults) {
  if (req.optimize) return { value: req.optimize, from: '--optimize', rank: req.optimize };
  if (defaults.own.route) return { value: defaults.route, from: defaults.file, rank: defaults.route };
  return { value: defaults.route, from: "cast's default", rank: DEFAULT_OPTIMIZE };
}

function selectRoute(req, joined, root, trace, defaults) {
  const optimize = optimizeOf(req, defaults);
  if (!joined.length) {
    return { error: 'no_models', details: 'no models.csv row has a supported-models.js twin' };
  }

  // `use` runs FIRST: a row the owner has taken out of routing is never weighed, never explained
  // as an availability or class casualty, and never named by a verdict.
  const routable = [];
  for (const r of joined) {
    if (r.use === 'route') { routable.push(r); continue; }
    drop(trace, 'use', r, r.use === 'panel'
      ? 'models.csv says use=panel — panel seats only, never a route verdict'
      : (r.use === 'off'
        ? 'models.csv says use=off — routing ignores it (still launchable by hand)'
        : `models.csv has an unrecognised use='${r.use}' — expected ${USE_VALUES.join(' | ')}`));
  }
  if (!routable.length) {
    return { error: 'zero_candidates', details: 'every models.csv row is use=panel or use=off — nothing is routable' };
  }

  let rows = [];
  for (const r of routable) {
    if (isAvailable(r.spec, root)) rows.push(r);
    else drop(trace, 'availability', r, unavailableReason(r.spec));
  }
  if (!rows.length) return { error: 'zero_candidates', details: 'every row dropped at availability' };

  // Image short-circuit: every other question is skipped. `--optimize` still breaks a tie if the
  // owner listed several image rows; absent, price ordering (which is alphabetical while costs are
  // blank) decides. Effort is nominal 1 — image rows carry an inert ladder (efforts 0).
  if (req.caps.has('image')) {
    const images = rows.filter((r) => r.image);
    trace.push({ stage: 'image', action: 'short_circuit', candidates: images.map(label) });
    if (!images.length) {
      return { error: 'zero_candidates', details: 'no available models.csv row carries image=Y' };
    }
    // `|| images[0]` is the all-blank-cost case: --optimize price can pick nothing, so CSV order
    // (deterministic) decides rather than the call failing over a tie-break input the owner
    // has not filled in yet.
    const chosen = pick(images, optimize.value, req.type, ['L4'], trace);
    return { verdict: verdictFor(chosen.length ? chosen : images, 1, false, optimize) };
  }

  if (req.access === 'open') {
    rows = rows.filter((r) => {
      if (r.mode !== 'api') return true;
      drop(trace, 'access', r, 'access=open needs a worker that can roam a disk; an api worker cannot');
      return false;
    });
  }

  const cls = CLASSES[req.class];
  rows = rows.filter((r) => {
    if (!r.level) { drop(trace, 'class', r, 'blank level in models.csv — excluded entirely'); return false; }
    if (!cls.levels.includes(r.level)) {
      drop(trace, 'class', r, `level ${r.level} is outside class ${req.class} (${cls.levels.join(', ')})`);
      return false;
    }
    return true;
  });
  if (!rows.length) {
    return { error: 'zero_candidates', details: `no available row survives access=${req.access}, caps=${[...req.caps].join(',') || 'none'}, class=${req.class}` };
  }

  if (optimize.from === defaults.file) trace.push({ stage: 'optimize', action: 'default', optimize: optimize.value, source: defaults.file });
  const chosen = pick(rows, optimize.rank, req.type, cls.levels, trace);
  if (!chosen.length) {
    return { error: 'zero_candidates', details: 'every surviving row has a blank cost, so a price-ranked pick can pick none — use --optimize quality or fill the cost column' };
  }
  return { verdict: verdictFor(chosen, cls.effort[req.type], cls.floor, optimize) };
}

// --- surfaces ----------------------------------------------------------------------------------

function parseRouteArgs(rawArgv) {
  const req = { access: null, type: null, class: null, optimize: null, caps: new Set(),
    explain: false, batch: null };
  const takeValue = (flag, i) => {
    const v = rawArgv[i + 1];
    if (v === undefined || v.startsWith('--')) fail(`refused: ${flag} requires a value\nusage: ${ROUTE_USAGE}\n       ${ROUTE_FORMS.join('\n       ')}`);
    return v;
  };
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '--explain') req.explain = true;
    else if (a === '--catalog') {
      fail('refused: --catalog moved\nthe model catalog is a view of cast models list\nNothing changed.\ncast models list --catalog');
    }
    else if (a === '--batch') req.batch = takeValue(a, i++);
    else if (a === '--access') req.access = takeValue(a, i++);
    else if (a === '--type') req.type = takeValue(a, i++);
    else if (a === '--class') req.class = takeValue(a, i++);
    else if (a === '--optimize') req.optimize = takeValue(a, i++);
    else if (a === '--caps') {
      for (const c of takeValue(a, i++).split(',')) if (c.trim()) req.caps.add(c.trim());
    } else fail(`refused: unknown flag '${a}'\nusage: ${ROUTE_USAGE}\n       ${ROUTE_FORMS.join('\n       ')}`);
  }
  return req;
}

// The three job flags are REQUIRED — the interview must be ANSWERED, never silently defaulted.
// `--optimize` is the one question with a ruled default (the tiered rule above, owner 2026-08-21):
// omitted means "the default", a value typed WRONG is still an error. `--caps image` is the other
// exemption: it short-circuits every other question.
function validateRequest(req) {
  const errors = [];
  const oneOf = (flag, value, allowed) => {
    if (value === null) errors.push(`missing required flag: ${flag} (one of ${allowed.join(' | ')})`);
    else if (!allowed.includes(value)) errors.push(`${flag} must be one of ${allowed.join(' | ')}, got '${value}'`);
  };
  for (const c of req.caps) {
    if (!CAPS.includes(c)) errors.push(`--caps must be one of ${CAPS.join(' | ')}, got '${c}'`);
  }
  if (req.caps.has('image')) {
    // Short-circuit: the other flags are optional here, but a value typed WRONG is still an error.
    if (req.optimize !== null && !OPTIMIZE.includes(req.optimize)) errors.push(`--optimize must be one of ${OPTIMIZE.join(' | ')}, got '${req.optimize}'`);
    if (req.type !== null && !TYPES.includes(req.type)) errors.push(`--type must be one of ${TYPES.join(' | ')}, got '${req.type}'`);
    return errors;
  }
  oneOf('--access', req.access, ACCESS);
  oneOf('--type', req.type, TYPES);
  oneOf('--class', req.class, Object.keys(CLASSES));
  if (req.optimize !== null && !OPTIMIZE.includes(req.optimize)) errors.push(`--optimize must be one of ${OPTIMIZE.join(' | ')}, got '${req.optimize}'`);
  return errors;
}

// --- batch -------------------------------------------------------------------------------------

// `--batch FILE` routes a whole TEAM in one call: a planning agent designs every agent at once and
// needs one deterministic assignment table, not N shell calls. The interview moves from flags to
// JSON; the selector does not move — each agent goes through the same selectRoute, and the CSV is
// loaded and joined ONCE for the whole batch.
const AGENT_KEYS = ['name', 'access', 'type', 'class', 'optimize', 'caps'];

function readBatchInput(source) {
  let text;
  if (source === '-') {
    try { text = fs.readFileSync(0, 'utf8'); } catch (e) { return { error: `cannot read stdin: ${e.message}` }; }
    if (text.trim() === '') return { error: 'empty stdin — pipe a JSON batch into cast route --batch -' };
  } else {
    try { text = fs.readFileSync(source, 'utf8'); } catch (e) { return { error: `cannot read ${source}: ${e.message}` }; }
  }
  try { return { data: JSON.parse(text) }; } catch (e) {
    return { error: `${source === '-' ? 'stdin' : source} is not valid JSON: ${e.message}` };
  }
}

// The envelope is a bare array of agent objects or {"agents":[...]}. Anything that breaks the
// name-keyed mapping the caller relies on — wrong shape, an entry with no usable name, a
// duplicate name — refuses the WHOLE batch (one malformed_request object, nothing routed):
// a table the caller cannot map back to its agents is worse than no table.
function batchAgents(data) {
  let agents = null;
  if (Array.isArray(data)) agents = data;
  else if (data && typeof data === 'object') {
    if (!Array.isArray(data.agents)) return { error: '"agents" must be an array of agent objects' };
    agents = data.agents;
  }
  if (agents === null) return { error: 'a batch is a JSON array of agent objects, or {"agents":[...]}' };
  if (!agents.length) return { error: 'the agents list is empty' };
  const seen = new Set();
  for (let i = 0; i < agents.length; i++) {
    const s = agents[i];
    if (!s || typeof s !== 'object' || Array.isArray(s)) return { error: `agent at index ${i} is not an object` };
    if (typeof s.name !== 'string' || s.name.trim() === '') {
      return { error: `agent at index ${i} has no usable name — every agent needs a non-empty string name, unique across the batch` };
    }
    if (seen.has(s.name)) return { error: `duplicate agent name '${s.name}' — the caller maps verdicts back by name` };
    seen.add(s.name);
  }
  return { agents };
}

// An agent IS the flag interview as an object: same vocabulary, same required-ness, same image
// short-circuit. Errors here are PER-AGENT — the batch keeps going so the caller fixes the whole
// plan in one pass instead of one agent per run.
function validateAgent(agent) {
  const errors = [];
  for (const k of Object.keys(agent)) {
    if (!AGENT_KEYS.includes(k)) errors.push(`unknown key '${k}' — an agent carries only: ${AGENT_KEYS.join(', ')}`);
  }
  const caps = new Set();
  if (agent.caps !== undefined && agent.caps !== null) {
    if (!Array.isArray(agent.caps) || agent.caps.some((c) => typeof c !== 'string')) {
      errors.push('caps must be an array of strings');
    } else {
      for (const c of agent.caps) {
        if (!CAPS.includes(c)) errors.push(`caps must be one of ${CAPS.join(' | ')}, got '${c}'`);
        else caps.add(c);
      }
    }
  }
  const oneOf = (field, allowed) => {
    const v = agent[field];
    if (v === undefined || v === null) errors.push(`missing required field: ${field} (one of ${allowed.join(' | ')})`);
    else if (!allowed.includes(v)) errors.push(`${field} must be one of ${allowed.join(' | ')}, got '${v}'`);
  };
  if (caps.has('image')) {
    // Short-circuit: the other fields are optional here, but a value typed WRONG is still an error.
    if (agent.optimize != null && !OPTIMIZE.includes(agent.optimize)) errors.push(`optimize must be one of ${OPTIMIZE.join(' | ')}, got '${agent.optimize}'`);
    if (agent.type != null && !TYPES.includes(agent.type)) errors.push(`type must be one of ${TYPES.join(' | ')}, got '${agent.type}'`);
    return { errors, caps };
  }
  oneOf('access', ACCESS);
  oneOf('type', TYPES);
  oneOf('class', Object.keys(CLASSES));
  if (agent.optimize != null && !OPTIMIZE.includes(agent.optimize)) errors.push(`optimize must be one of ${OPTIMIZE.join(' | ')}, got '${agent.optimize}'`);
  return { errors, caps };
}

function runBatch(source, explain, root) {
  const envelopeError = (details) => {
    process.stdout.write(`${JSON.stringify({ error: 'malformed_request', details: [].concat(details) })}\n`);
    process.exit(1);
  };
  const input = readBatchInput(source);
  if (input.error) envelopeError(input.error);
  const parsed = batchAgents(input.data);
  if (parsed.error) envelopeError(parsed.error);

  const csv = loadCatalog(root);
  const defaults = loadRouteDefaults(root);
  // ONE load, ONE join, ONE round of warnings — N agents share the model catalog.
  const warnings = [];
  const joined = joinCatalog(csv.rows, warnings);
  for (const w of warnings) process.stderr.write(`cast route: WARNING: ${w}\n`);

  let allRouted = true;
  const agents = parsed.agents.map((agent) => {
    const trace = [{ stage: 'catalog', source: csv.file, csv_rows: csv.rows.length,
      joined: joined.length, excluded: warnings }];
    const { errors, caps } = validateAgent(agent);
    if (errors.length) {
      allRouted = false;
      return { name: agent.name, error: 'malformed_request', details: errors };
    }
    const req = { access: agent.access ?? null, type: agent.type ?? null, class: agent.class ?? null,
      optimize: agent.optimize ?? null, caps };
    const result = selectRoute(req, joined, root, trace, defaults);
    if (!result.verdict) allRouted = false;
    const entry = { name: agent.name, ...(result.verdict || { error: result.error, details: result.details }) };
    if (explain) entry.explain = trace;
    return entry;
  });
  process.stdout.write(`${JSON.stringify({ verdict: 'route-batch', agents })}\n`);
  process.exit(allRouted ? 0 : 1);
}

function runRoute(rawArgv) {
  const req = parseRouteArgs(rawArgv);
  const root = installationRoot(process.cwd());

  if (req.batch !== null) {
    // The batch carries the interview as JSON — mixing it with the flag interview would leave two
    // sources of truth for the same answers.
    const mixed = [];
    if (req.access !== null) mixed.push('--access');
    if (req.type !== null) mixed.push('--type');
    if (req.class !== null) mixed.push('--class');
    if (req.optimize !== null) mixed.push('--optimize');
    if (req.caps.size) mixed.push('--caps');
    if (mixed.length) {
      fail(`refused: --batch takes the whole interview as JSON — do not combine it with ${mixed.join(', ')}\nusage: cast route --batch agents.json  # or --batch - for stdin\n       ${ROUTE_USAGE}`);
    }
    return runBatch(req.batch, req.explain, root);
  }
  const errors = validateRequest(req);
  if (errors.length) {
    process.stdout.write(`${JSON.stringify({ error: 'malformed_request', details: errors })}\n`);
    process.exit(1);
  }

  const csv = loadCatalog(root);
  const defaults = loadRouteDefaults(root);

  const warnings = [];
  const joined = joinCatalog(csv.rows, warnings);
  for (const w of warnings) process.stderr.write(`cast route: WARNING: ${w}\n`);

  const trace = [{ stage: 'catalog', source: csv.file, csv_rows: csv.rows.length, joined: joined.length,
    excluded: warnings }];
  const result = selectRoute(req, joined, root, trace, defaults);
  const out = result.verdict || { error: result.error, details: result.details };
  if (req.explain) out.explain = trace;
  process.stdout.write(`${JSON.stringify(out)}\n`);
  process.exit(result.verdict ? 0 : 1);
}

module.exports = {
  ROUTE_USAGE, ROUTE_FORMS, CLASSES, LEVELS,
  ACCESS, TYPES, OPTIMIZE, CAPS,
  readJson, expandHome, storePath, storedCredential, isAvailable, loginFoundIn, unavailableReason,
  loadCatalog, joinCatalog,
  scoreOf, pick, selectRoute, parseRouteArgs, validateRequest, runRoute,
  AGENT_KEYS, readBatchInput, batchAgents, validateAgent, runBatch,
};

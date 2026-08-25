'use strict';

// cast — `cast route` — the deterministic (harness, model, mode, effort) selector.
//
// REWRITTEN 2026-08-20 against the settled route-redesign spec. The old profile-based selector is
// GONE: boundedness bands, pinned roles, halt seams, stakes tier-up, the haiku clause, footprint /
// window gating, evidence ranking and the JSON-profile-on-stdin interface all died with it, and no
// back-compat path was kept.
//
// Route answers ONE question: given five facts about a job (the interview below), which
// (harness, model, mode, effort) runs it. Purity holds — no network, no clock, no randomness, so
// the same flags against the same CSV always yield the same verdict.
//
// Two inputs, deliberately split by who edits them:
//   models.csv   the ROUTING axes (level, scores, cost, web, image) — owner-editable data.
//   catalog.js   the LAUNCH mechanics (harness-native id, effort ladder, auth) — code.
// Route JOINS them on harness+model. A CSV row with no catalog twin is EXCLUDED with a loud stderr
// warning: route must never answer with something cast cannot launch.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { ROWS } = require('../catalog');

const { fail } = require('./core');

const ROUTE_USAGE = 'cast route --access open|bounded --type code|text --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps web[,image]] [--explain]';
// The forms that ask nothing as flags. Kept OUT of ROUTE_USAGE so the top-level `cast -h` stays
// one line per verb; the route help page and every refusal print all of them.
const ROUTE_FORMS = ['cast route --caps image          # short-circuit, no other flags',
  'cast route --batch seats.json    # a whole team in one call (- reads stdin)',
  'cast route --catalog [--json]    # the roster, asks nothing'];

const CSV_NAME = 'models.csv';
// -- THE SHARED ROUTING TABLE, AND WHY IT IS NOT BESIDE THIS FILE ANYMORE [spec-recovery §3] ----
//
// It moved to `ignite/supervisor/` 2026-08-25. It is no longer cast's private roster: the daemon's
// provider-lane reroute reads the SAME rows to answer "which alternates may this lane try" when a
// transient provider fault (quota, rate-limit, provider-down) takes a model out. Two copies of
// that answer is a daemon rerouting onto a model `cast` cannot launch — the exact drift the
// catalog join already exists to prevent, one level up.
//
// ⚠ THE OTHER READER IS `ignite/supervisor/routing-table.js`. It asks a different question of the
// same file (eligible alternates, not a class-ranked verdict) and parses it separately; the FILE
// is the shared thing, not the parse. Move this path and that constant in the SAME edit.
const CSV_LOCAL = path.join(__dirname, '..', '..', '..', '..', 'ignite', 'supervisor', CSV_NAME);
// Per-vault override, WHOLE-FILE replace: present -> it IS the catalog, the shipped CSV is ignored.
// The path follows the live `{module}/{component}` convention of `.rbtv/config/modules/` — module
// `core`, component `sub-agents` (spec §6). Changing it means changing the -h text in the same edit:
// an override nobody can find is an override nobody has.
const CSV_OVERRIDE_REL = path.join('.rbtv', 'config', 'modules', 'core', 'sub-agents', CSV_NAME);

const COLUMNS = ['mode', 'harness', 'model', 'efforts', 'image', 'web', 'level',
  'reasoning', 'coding', 'cost', 'use', 'quality-override', 'price-override'];

// Level vocabulary: SOTA > L1 > L2 > L3, plus L4 — the image tier, which NO class admits, so an
// L4 row is reachable only through the `--caps image` short-circuit. Each class below lists its
// eligible levels BEST FIRST; that order is what `--optimize quality` ranks on.
// The class table (spec §4). `levels` is BOTH the eligibility filter and the ceiling `--optimize
// quality` may reach: a bounded executor optimizing quality picks the best L1, never SOTA — only planner
// reaches SOTA. Effort is a fixed cast-normalized 1-5 number, mapped onto the picked row's own
// rungs at launch (inert ladders accept N and emit no argv).
const CLASSES = {
  planner: { levels: ['SOTA', 'L1'], effort: { code: 3, text: 3 }, floor: true },
  broad: { levels: ['L1'], effort: { code: 2, text: 3 } },
  bounded: { levels: ['L1', 'L2'], effort: { code: 2, text: 2 } },
  mechanical: { levels: ['L2', 'L3'], effort: { code: 1, text: 1 } },
};

const ACCESS = ['open', 'bounded'];
const TYPES = ['code', 'text'];
const OPTIMIZE = ['price', 'quality'];
// The default when --optimize is omitted is PRICE, for every class alike (owner ruling
// 2026-08-22, replacing the tiered SOTA/L1-on-price + L2/L3-on-quality rule of 2026-08-21: one
// rule the owner can hold in their head beat two bands). Omitting the flag is now exactly
// `--optimize price` — same ranking, same blank-cost exclusion, same tie-breaks — and the class's
// levels remain the only thing standing between a job and the cheapest model on the roster.
// Consequence to keep in view: `price-override` fires in the default, `quality-override` does not.
const DEFAULT_OPTIMIZE = 'default';
const CAPS = ['web', 'image'];

// The `use` column (owner ruling 2026-08-22) — WHO may see a row:
//   route  the normal state; the row competes for `cast route` verdicts. A BLANK cell reads as
//          this, so a CSV written before the column existed keeps behaving exactly as it did.
//   panel  invisible to every verdict; the row still appears in `cast route --catalog`, which is
//          the surface a panel spreads its seats across (references/panel.md). For a model worth
//          a second opinion but never worth being the single answer.
//   off    invisible to routing entirely. Still LAUNCHABLE by hand (`cast <harness> <model> <n>`)
//          and still listed by --catalog with its use value — nothing is hidden from the owner.
// An unrecognised value is NEVER guessed: the row drops from routing with a loud warning. One
// column rather than two flags because `route=Y` + `panel-only=Y` would be a state with no
// meaning, and the code would have to invent a winner for it.
const USE_VALUES = ['route', 'panel', 'off'];
const USE_DEFAULT = 'route';

// The two override columns (same ruling). `Y` means: inside ITS OWN LEVEL, this row wins the named
// ranking whatever the numbers say. It NEVER crosses a level — an L2 row with quality-override=Y
// still loses to every eligible L1 row — and it never bypasses a filter: availability, --caps,
// --access and the class levels all run first, so an override can only reorder survivors. On the
// tiered default the override that fires is the one matching how that band is ranked:
// price-override in the SOTA/L1 band, quality-override in the L2/L3 band.
const OVERRIDE = { quality: 'quality_override', price: 'price_override' };

// The vault root = the nearest ancestor carrying rbtv.json, from cwd first (a workspace may sit
// elsewhere) and from this module second (cast is installed inside the vault it serves).
function vaultRoot() {
  for (const start of [process.cwd(), __dirname]) {
    let dir = path.resolve(start);
    for (let i = 0; i < 12; i++) {
      if (fs.existsSync(path.join(dir, 'rbtv.json'))) return dir;
      const up = path.dirname(dir);
      if (up === dir) break;
      dir = up;
    }
  }
  return null;
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

function envFileHasKey(root, cfg, name) {
  const pointer = cfg && cfg.env_file;
  if (!root || !pointer) return false;
  let text;
  try { text = fs.readFileSync(path.join(root, pointer), 'utf8'); } catch { return false; }
  return text.split('\n').some((l) => {
    const t = l.trim();
    return t && !t.startsWith('#') && t.split('=')[0].trim() === name;
  });
}

// opencode persists `opencode auth login` credentials in the store its own `auth list` header
// names: $XDG_DATA_HOME/opencode/auth.json, else ~/.local/share/opencode/auth.json. Presence of
// the provider key IS the credential — cast never spends a call to test availability.
const CREDENTIAL_STORES = {
  opencode: () => path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'),
    'opencode', 'auth.json'),
};

function storedCredential(store, key) {
  const resolver = CREDENTIAL_STORES[store];
  if (!resolver || !key) return false;
  const data = readJson(resolver());
  return !!(data && Object.prototype.hasOwnProperty.call(data, key));
}

// Availability: an explicit `available: false` drops the row; otherwise an api-key row needs its
// key to RESOLVE (OS env first, then rbtv.json's env_file dotenv, then a stored CLI login), and
// cli-login rows are always available. An absent key drops the row — never an error.
function isAvailable(spec, root, cfg) {
  if (spec.available === false) return false;
  const auth = spec.auth || {};
  if (auth.method !== 'api-key') return true;
  if (auth.env_var && process.env[auth.env_var]) return true;
  if (auth.env_var && envFileHasKey(root, cfg, auth.env_var)) return true;
  return storedCredential(auth.credential_store, auth.credential_store_key);
}

function unavailableReason(spec) {
  if (spec.available === false) return 'marked available: false in the catalog';
  const auth = spec.auth || {};
  return auth.credential_store
    ? `${auth.env_var} absent in OS env and env_file, and no stored '${auth.credential_store_key}' credential in the ${auth.credential_store} store`
    : `${auth.env_var} absent in both OS env and env_file`;
}

// --- the CSV -----------------------------------------------------------------------------------

// ponytail: split(',') — this CSV has no quoted fields and no embedded commas, and a header check
// guards the shape. Swap in a real parser only if a column ever needs quoting.
function parseCsv(text, source) {
  const lines = text.split('\n').map((l) => l.replace(/\r$/, '')).filter((l) => l.trim() !== '');
  if (!lines.length) return { error: `${source} is empty` };
  const header = lines.shift().split(',').map((s) => s.trim());
  if (header.join(',') !== COLUMNS.join(',')) {
    return { error: `${source} header is ${header.join(',')} — expected ${COLUMNS.join(',')}` };
  }
  const rows = lines.map((line, i) => {
    const cells = line.split(',');
    const row = { _line: i + 2, _source: source };
    COLUMNS.forEach((c, idx) => { row[c] = (cells[idx] === undefined ? '' : cells[idx]).trim(); });
    return row;
  });
  return { rows };
}

function csvPath(root) {
  const override = root ? path.join(root, CSV_OVERRIDE_REL) : null;
  if (override && fs.existsSync(override)) return override;
  return CSV_LOCAL;
}

function loadCsv(root) {
  const file = csvPath(root);
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) { return { error: `cannot read ${file}: ${e.message}` }; }
  const parsed = parseCsv(text, file);
  if (parsed.error) return parsed;
  return { rows: parsed.rows, file };
}

const num = (v) => (v === '' ? null : Number(v));

// JOIN — the CSV row carries the axes, its catalog.js twin carries the launch spec. No twin means
// route could name something cast cannot run, so the row is dropped and the drop is LOUD.
function joinCatalog(csvRows, warnings) {
  const joined = [];
  for (const c of csvRows) {
    const spec = ROWS.find((r) => r.harness === c.harness && r.model === c.model);
    const label = `${c.harness}/${c.model || '(blank model)'}`;
    if (!spec) {
      warnings.push(`models.csv line ${c._line}: no catalog.js row for ${label} — excluded (cast cannot launch it)`);
      continue;
    }
    if (spec.mode !== c.mode) {
      warnings.push(`models.csv line ${c._line}: ${label} says mode=${c.mode}, catalog.js says mode=${spec.mode} — using catalog.js`);
    }
    const rawUse = (c.use === undefined ? '' : c.use).trim();
    const use = rawUse === '' ? USE_DEFAULT : rawUse;
    if (!USE_VALUES.includes(use)) {
      warnings.push(`models.csv line ${c._line}: ${label} has use='${rawUse}' — expected ${USE_VALUES.join(' | ')} (blank = ${USE_DEFAULT}) — excluded from routing`);
    }
    joined.push({
      harness: c.harness,
      model: c.model,
      mode: spec.mode,
      level: c.level,
      image: c.image === 'Y',
      web: c.web === 'Y',
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

const label = (r) => `${r.harness}/${r.model || '(blank model)'}`;

function drop(trace, stage, row, reason) {
  trace.push({ stage, action: 'drop', harness: row.harness, model: row.model, reason });
}

// Blank score = 0 in tie-breaks (spec §5). Type absent (image short-circuit) reads as text.
const scoreOf = (r, type) => ((type === 'code' ? r.coding : r.reasoning) ?? 0);

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
// An override moves rows WITHIN their own level and nowhere else: the flagged rows of a level are
// lifted to that level's first position in the already-ranked list, keeping their relative order.
// Every other row keeps its place, so a ranking with no flagged row is byte-identical to before —
// the column is inert until the owner sets it. Implemented as a post-sort lift rather than a sort
// key because "ahead of my own level only" is not a total order: with price ranking, levels are
// interleaved by cost, and folding the rule into the comparator would regroup rows the owner never
// flagged.
function promoteOverrides(ranked, flag, trace, optimize) {
  const flagged = ranked.filter((r) => r[flag]);
  if (!flagged.length) return ranked;
  let out = ranked.slice();
  for (const level of [...new Set(flagged.map((r) => r.level))]) {
    const promoted = out.filter((r) => r.level === level && r[flag]);
    const rest = out.filter((r) => !(r.level === level && r[flag]));
    // Insert where that level starts among the rows left; a level whose every row was promoted
    // keeps the block's old position.
    let at = rest.findIndex((r) => r.level === level);
    if (at === -1) at = Math.min(out.indexOf(promoted[0]), rest.length);
    out = [...rest.slice(0, at), ...promoted, ...rest.slice(at)];
  }
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
function verdictFor(ranked, effort, isFloor) {
  const [row] = ranked;
  return {
    verdict: 'route',
    harness: row.harness,
    model: row.model,
    mode: row.mode,
    effort,
    effort_is_floor: !!isFloor,
    alternates: ranked.slice(1, 3).map((r) => ({ harness: r.harness, model: r.model, mode: r.mode })),
  };
}

// The pipeline, in the spec's order: availability -> image short-circuit -> access -> caps ->
// class levels -> optimize -> effort. Every filter records why each row left.
function selectRoute(req, joined, root, cfg, trace) {
  if (!joined.length) {
    return { error: 'no_models', details: 'no models.csv row has a catalog.js twin' };
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
    if (isAvailable(r.spec, root, cfg)) rows.push(r);
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
    const chosen = pick(images, req.optimize || 'price', req.type, ['L4'], trace);
    return { verdict: verdictFor(chosen.length ? chosen : images, 1, false) };
  }

  if (req.access === 'open') {
    rows = rows.filter((r) => {
      if (r.mode !== 'api') return true;
      drop(trace, 'access', r, 'access=open needs a worker that can roam a disk; an api worker cannot');
      return false;
    });
  }

  if (req.caps.has('web')) {
    rows = rows.filter((r) => {
      if (r.web) return true;
      drop(trace, 'caps', r, 'caps=web but models.csv says web=N');
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

  const chosen = pick(rows, req.optimize || DEFAULT_OPTIMIZE, req.type, cls.levels, trace);
  if (!chosen.length) {
    return { error: 'zero_candidates', details: 'every surviving row has a blank cost, so a price-ranked pick can pick none — use --optimize quality or fill the cost column' };
  }
  return { verdict: verdictFor(chosen, cls.effort[req.type], cls.floor) };
}

// --- surfaces ----------------------------------------------------------------------------------

// cast route --catalog: the roster. Shows EVERY models.csv row, including one with no catalog.js
// twin (`launchable: no`) — an owner filling the CSV needs to see a row that route is ignoring,
// not have it vanish.
function runCatalog(json, root, cfg) {
  const csv = loadCsv(root);
  if (csv.error) {
    process.stdout.write(`${JSON.stringify({ error: 'no_models', details: csv.error })}\n`);
    process.exit(1);
  }
  const rows = csv.rows.map((c) => {
    const spec = ROWS.find((r) => r.harness === c.harness && r.model === c.model);
    const out = {};
    for (const col of COLUMNS) out[col] = c[col];
    out.launchable = spec ? 'yes' : 'no';
    out.available = spec ? String(isAvailable(spec, root, cfg)) : '-';
    return out;
  });
  if (json) {
    process.stdout.write(`${JSON.stringify({ source: csv.file, rows })}\n`);
    process.exit(0);
  }
  const cols = [...COLUMNS, 'launchable', 'available'];
  const cell = (r, c) => String(r[c] === '' ? '-' : r[c]);
  const width = {};
  for (const c of cols) width[c] = Math.max(c.length, ...rows.map((r) => cell(r, c).length));
  const line = (vals) => cols.map((c, i) => vals[i].padEnd(width[c])).join('  ').trimEnd();
  process.stdout.write(`catalog: ${csv.file}\n`);
  process.stdout.write(`${line(cols)}\n`);
  for (const r of rows) process.stdout.write(`${line(cols.map((c) => cell(r, c)))}\n`);
  process.exit(0);
}

function parseRouteArgs(rawArgv) {
  const req = { access: null, type: null, class: null, optimize: null, caps: new Set(),
    explain: false, catalog: false, json: false, batch: null };
  const takeValue = (flag, i) => {
    const v = rawArgv[i + 1];
    if (v === undefined || v.startsWith('--')) fail(`refused: ${flag} requires a value\nusage: ${ROUTE_USAGE}\n       ${ROUTE_FORMS.join('\n       ')}`);
    return v;
  };
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '--explain') req.explain = true;
    else if (a === '--catalog') req.catalog = true;
    else if (a === '--json') req.json = true;
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
    if (!CAPS.includes(c)) errors.push(`--caps must be one of ${CAPS.join(' | ')} (comma-separated), got '${c}'`);
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

// `--batch FILE` routes a whole TEAM in one call: a planning agent designs every seat at once and
// needs one deterministic assignment table, not N shell calls. The interview moves from flags to
// JSON; the selector does not move — each seat goes through the same selectRoute, and the CSV is
// loaded and joined ONCE for the whole batch.
const SEAT_KEYS = ['name', 'access', 'type', 'class', 'optimize', 'caps'];

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

// The envelope is a bare array of seat objects or {"seats":[...]}. Anything that breaks the
// name-keyed mapping the caller relies on — wrong shape, an entry with no usable name, a
// duplicate name — refuses the WHOLE batch (one malformed_request object, nothing routed):
// a table the caller cannot map back to its seats is worse than no table.
function batchSeats(data) {
  let seats = null;
  if (Array.isArray(data)) seats = data;
  else if (data && typeof data === 'object') {
    if (!Array.isArray(data.seats)) return { error: '"seats" must be an array of seat objects' };
    seats = data.seats;
  }
  if (seats === null) return { error: 'a batch is a JSON array of seat objects, or {"seats":[...]}' };
  if (!seats.length) return { error: 'the seats list is empty' };
  const seen = new Set();
  for (let i = 0; i < seats.length; i++) {
    const s = seats[i];
    if (!s || typeof s !== 'object' || Array.isArray(s)) return { error: `seat at index ${i} is not an object` };
    if (typeof s.name !== 'string' || s.name.trim() === '') {
      return { error: `seat at index ${i} has no usable name — every seat needs a non-empty string name, unique across the batch` };
    }
    if (seen.has(s.name)) return { error: `duplicate seat name '${s.name}' — the caller maps verdicts back by name` };
    seen.add(s.name);
  }
  return { seats };
}

// A seat IS the flag interview as an object: same vocabulary, same required-ness, same image
// short-circuit. Errors here are PER-SEAT — the batch keeps going so the caller fixes the whole
// plan in one pass instead of one seat per run.
function validateSeat(seat) {
  const errors = [];
  for (const k of Object.keys(seat)) {
    if (!SEAT_KEYS.includes(k)) errors.push(`unknown key '${k}' — a seat carries only: ${SEAT_KEYS.join(', ')}`);
  }
  const caps = new Set();
  if (seat.caps !== undefined && seat.caps !== null) {
    if (!Array.isArray(seat.caps) || seat.caps.some((c) => typeof c !== 'string')) {
      errors.push('caps must be an array of strings');
    } else {
      for (const c of seat.caps) {
        if (!CAPS.includes(c)) errors.push(`caps must be one of ${CAPS.join(' | ')}, got '${c}'`);
        else caps.add(c);
      }
    }
  }
  const oneOf = (field, allowed) => {
    const v = seat[field];
    if (v === undefined || v === null) errors.push(`missing required field: ${field} (one of ${allowed.join(' | ')})`);
    else if (!allowed.includes(v)) errors.push(`${field} must be one of ${allowed.join(' | ')}, got '${v}'`);
  };
  if (caps.has('image')) {
    // Short-circuit: the other fields are optional here, but a value typed WRONG is still an error.
    if (seat.optimize != null && !OPTIMIZE.includes(seat.optimize)) errors.push(`optimize must be one of ${OPTIMIZE.join(' | ')}, got '${seat.optimize}'`);
    if (seat.type != null && !TYPES.includes(seat.type)) errors.push(`type must be one of ${TYPES.join(' | ')}, got '${seat.type}'`);
    return { errors, caps };
  }
  oneOf('access', ACCESS);
  oneOf('type', TYPES);
  oneOf('class', Object.keys(CLASSES));
  if (seat.optimize != null && !OPTIMIZE.includes(seat.optimize)) errors.push(`optimize must be one of ${OPTIMIZE.join(' | ')}, got '${seat.optimize}'`);
  return { errors, caps };
}

function runBatch(source, explain, root, cfg) {
  const envelopeError = (details) => {
    process.stdout.write(`${JSON.stringify({ error: 'malformed_request', details: [].concat(details) })}\n`);
    process.exit(1);
  };
  const input = readBatchInput(source);
  if (input.error) envelopeError(input.error);
  const parsed = batchSeats(input.data);
  if (parsed.error) envelopeError(parsed.error);

  const csv = loadCsv(root);
  if (csv.error) {
    process.stdout.write(`${JSON.stringify({ error: 'no_models', details: csv.error })}\n`);
    process.exit(1);
  }
  // ONE load, ONE join, ONE round of warnings — N seats share the catalog.
  const warnings = [];
  const joined = joinCatalog(csv.rows, warnings);
  for (const w of warnings) process.stderr.write(`cast route: WARNING: ${w}\n`);

  let allRouted = true;
  const seats = parsed.seats.map((seat) => {
    const trace = [{ stage: 'catalog', source: csv.file, csv_rows: csv.rows.length,
      joined: joined.length, excluded: warnings }];
    const { errors, caps } = validateSeat(seat);
    if (errors.length) {
      allRouted = false;
      return { name: seat.name, error: 'malformed_request', details: errors };
    }
    const req = { access: seat.access ?? null, type: seat.type ?? null, class: seat.class ?? null,
      optimize: seat.optimize ?? null, caps };
    const result = selectRoute(req, joined, root, cfg, trace);
    if (!result.verdict) allRouted = false;
    const entry = { name: seat.name, ...(result.verdict || { error: result.error, details: result.details }) };
    if (explain) entry.explain = trace;
    return entry;
  });
  process.stdout.write(`${JSON.stringify({ verdict: 'route-batch', seats })}\n`);
  process.exit(allRouted ? 0 : 1);
}

function runRoute(rawArgv) {
  const req = parseRouteArgs(rawArgv);
  const root = vaultRoot();
  const cfg = root ? (readJson(path.join(root, 'rbtv.json')) || {}) : {};

  if (req.batch !== null) {
    // The batch carries the interview as JSON — mixing it with the flag interview (or the roster
    // form) would leave two sources of truth for the same answers.
    const mixed = [];
    if (req.access !== null) mixed.push('--access');
    if (req.type !== null) mixed.push('--type');
    if (req.class !== null) mixed.push('--class');
    if (req.optimize !== null) mixed.push('--optimize');
    if (req.caps.size) mixed.push('--caps');
    if (req.catalog) mixed.push('--catalog');
    if (mixed.length) {
      fail(`refused: --batch takes the whole interview as JSON — do not combine it with ${mixed.join(', ')}\nusage: cast route --batch seats.json  # or --batch - for stdin\n       ${ROUTE_USAGE}`);
    }
    return runBatch(req.batch, req.explain, root, cfg);
  }
  if (req.catalog) return runCatalog(req.json, root, cfg);

  const errors = validateRequest(req);
  if (errors.length) {
    process.stdout.write(`${JSON.stringify({ error: 'malformed_request', details: errors })}\n`);
    process.exit(1);
  }

  const csv = loadCsv(root);
  if (csv.error) {
    process.stdout.write(`${JSON.stringify({ error: 'no_models', details: csv.error })}\n`);
    process.exit(1);
  }

  const warnings = [];
  const joined = joinCatalog(csv.rows, warnings);
  for (const w of warnings) process.stderr.write(`cast route: WARNING: ${w}\n`);

  const trace = [{ stage: 'catalog', source: csv.file, csv_rows: csv.rows.length, joined: joined.length,
    excluded: warnings }];
  const result = selectRoute(req, joined, root, cfg, trace);
  const out = result.verdict || { error: result.error, details: result.details };
  if (req.explain) out.explain = trace;
  process.stdout.write(`${JSON.stringify(out)}\n`);
  process.exit(result.verdict ? 0 : 1);
}

module.exports = {
  ROUTE_USAGE, ROUTE_FORMS, CSV_NAME, CSV_LOCAL, CSV_OVERRIDE_REL, COLUMNS, CLASSES,
  ACCESS, TYPES, OPTIMIZE, CAPS,
  vaultRoot, readJson, envFileHasKey, CREDENTIAL_STORES, storedCredential,
  isAvailable, unavailableReason,
  parseCsv, csvPath, loadCsv, joinCatalog,
  scoreOf, pick, selectRoute, runCatalog, parseRouteArgs, validateRequest, runRoute,
  SEAT_KEYS, readBatchInput, batchSeats, validateSeat, runBatch,
};

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const provider = require(path.join(__dirname, '..', '..', '..', 'teambuild', 'tool', 'lib', 'provider'));

const KEY_VAR = 'VOYAGE_API_KEY';
const VAULT_ENV = path.join('.user', 'config', 'env', '.env');
const SKIP_DIRS = new Set(['.git', 'node_modules', '4-archives']);
const NORMALIZER = 'v1-section';

function sha256(s) { return crypto.createHash('sha256').update(s, 'utf8').digest('hex'); }

function resolveRoot(root) {
  if (!root) {
    const e = new Error('--root is required');
    e.rbtvCode = 'usage';
    throw e;
  }
  const abs = path.resolve(root);
  let st;
  try { st = fs.statSync(abs); } catch {
    const e = new Error(`root is not readable: ${abs}`);
    e.rbtvCode = 'no-root';
    throw e;
  }
  if (!st.isDirectory()) {
    const e = new Error(`root is not a directory: ${abs}`);
    e.rbtvCode = 'no-root';
    throw e;
  }
  return abs;
}

function defaultIndexPath(root) {
  const key = sha256(path.resolve(root)).slice(0, 16);
  const state = process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local', 'state');
  return path.join(state, 'rbtv-embed-search', key, 'index.json');
}

function globToRe(glob) {
  const esc = String(glob).replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*\*\//g, '\0')
    .replace(/\*\*/g, '\0')
    .replace(/\*/g, '[^/]*')
    .replace(/\0/g, '(?:.*/)?');
  return new RegExp(`^${esc}$`);
}

function walk(root, glob) {
  const re = globToRe(glob || '**/*.md');
  const out = [];
  function rec(dir, rel) {
    let ents;
    try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      if (SKIP_DIRS.has(e.name)) continue;
      const r = rel ? `${rel}/${e.name}` : e.name;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) rec(full, r);
      else if (e.isFile() && re.test(r)) out.push(r);
    }
  }
  rec(root, '');
  return out;
}

function splitSections(rel, text) {
  const lines = String(text).split(/\r?\n/);
  const parts = [];
  let heading = '';
  let buf = [];
  function flush() {
    const body = buf.join('\n').trim();
    buf = [];
    if (!body && !heading) return;
    const id = heading ? `${rel}#${heading}` : rel;
    parts.push({
      id,
      path: rel,
      heading,
      text: heading ? `# ${heading}\n${body}` : body,
    });
  }
  for (const line of lines) {
    const m = /^(#{1,6})\s+(.+)$/.exec(line);
    if (m) { flush(); heading = m[2].trim(); }
    else buf.push(line);
  }
  flush();
  if (!parts.length) parts.push({ id: rel, path: rel, heading: '', text: String(text) });
  return parts;
}

function sourceEnvFile(file) {
  const names = [];
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line);
    if (!m) continue;
    names.push(m[1]);
    if (process.env[m[1]] === undefined) {
      process.env[m[1]] = m[2].trim().replace(/^(["'])(.*)\1$/, '$2');
    }
  }
  return names;
}

function findVaultEnv(starts) {
  for (const start of starts) {
    if (!start) continue;
    let dir = path.resolve(start);
    for (;;) {
      const file = path.join(dir, VAULT_ENV);
      if (fs.existsSync(file)) return file;
      const up = path.dirname(dir);
      if (up === dir) break;
      dir = up;
    }
  }
  return null;
}

function resolveKey(starts) {
  const present = Boolean(process.env[KEY_VAR]);
  if (present) return { available: true, origin: 'os-env', file: null };
  const file = findVaultEnv(starts);
  if (!file) return { available: false, origin: 'absent', file: null };
  sourceEnvFile(file);
  if (process.env[KEY_VAR]) return { available: true, origin: 'env-file', file };
  return { available: false, origin: 'env-file-no-key', file };
}

function tokens(s) {
  return String(s).toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 1);
}

function keywordScore(query, text) {
  const qt = tokens(query);
  const tt = tokens(text);
  if (!qt.length || !tt.length) return 0;
  const tf = new Map();
  for (const t of tt) tf.set(t, (tf.get(t) || 0) + 1);
  let s = 0;
  for (const t of qt) {
    if (tf.has(t)) s += 1 + Math.log(1 + tf.get(t));
  }
  return s / qt.length;
}

function grepScore(query, text) {
  const q = String(query).toLowerCase().trim();
  const t = String(text).toLowerCase();
  if (!q || !t) return 0;
  if (t.includes(q)) return 1 + Math.min(10, t.split(q).length - 1) / 10;
  const parts = q.split(/\s+/).filter(Boolean);
  if (!parts.length) return 0;
  let hits = 0;
  for (const p of parts) if (t.includes(p)) hits += 1;
  return hits / parts.length;
}

function cosine(a, b) {
  if (!a || !b || a.length !== b.length) return 0;
  let dot = 0; let na = 0; let nb = 0;
  for (let i = 0; i < a.length; i += 1) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}

function round(v) { return v.map((x) => Math.round(x * 1e6) / 1e6); }

function loadIndex(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

function saveIndex(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(obj));
  fs.renameSync(tmp, file);
}

function collect(root, glob) {
  const files = walk(root, glob);
  const sections = [];
  const mtimes = {};
  for (const rel of files) {
    const full = path.join(root, rel);
    let st;
    let text;
    try {
      st = fs.statSync(full);
      text = fs.readFileSync(full, 'utf8');
    } catch { continue; }
    mtimes[rel] = st.mtimeMs;
    for (const s of splitSections(rel, text)) {
      sections.push({ ...s, hash: sha256(s.text), mtime: st.mtimeMs });
    }
  }
  return { files, sections, mtimes };
}

function tryProvider(starts) {
  const key = resolveKey(starts);
  if (!key.available) return { key, prov: null, error: null };
  try {
    return { key, prov: provider.voyage(starts[0] || process.cwd()), error: null };
  } catch (err) {
    return { key: { ...key, available: false }, prov: null, error: err.message };
  }
}

async function sync(opts) {
  const root = resolveRoot(opts.root);
  const glob = opts.glob || '**/*.md';
  const file = opts.indexFile || defaultIndexPath(root);
  const { sections } = collect(root, glob);
  const prev = loadIndex(file);
  const header = { root, glob, normalizer: NORMALIZER };
  const reuse = prev && prev.root === root && prev.glob === glob && prev.normalizer === NORMALIZER
    ? (prev.entries || {})
    : {};

  const entries = {};
  const changed = [];
  for (const s of sections) {
    const old = reuse[s.id];
    if (old && old.hash === s.hash && old.mtime === s.mtime) {
      entries[s.id] = { ...old, path: s.path, heading: s.heading, text: s.text };
    } else {
      entries[s.id] = {
        path: s.path, heading: s.heading, hash: s.hash, mtime: s.mtime, text: s.text,
        vec: old && old.hash === s.hash ? old.vec : undefined,
      };
      if (!(old && old.hash === s.hash && Array.isArray(old.vec))) changed.push(s.id);
    }
  }

  let semantic = { available: false, origin: null, error: null };
  const wantEmbed = opts.embed !== false;
  if (wantEmbed) {
    const got = tryProvider([opts.cwd || process.cwd(), root]);
    semantic = {
      available: Boolean(got.prov),
      origin: got.key.origin,
      error: got.error,
    };
    if (got.prov) {
      const need = changed.filter((id) => !Array.isArray(entries[id].vec));
      for (let i = 0; i < need.length; i += got.prov.batchLimit) {
        const ids = need.slice(i, i + got.prov.batchLimit);
        try {
          const vecs = await got.prov.embedDocuments(ids.map((id) => entries[id].text));
          ids.forEach((id, j) => { entries[id].vec = round(vecs[j]); });
        } catch (err) {
          semantic.error = err.message;
          semantic.available = i === 0 ? false : semantic.available;
          break;
        }
      }
    }
  } else {
    const key = resolveKey([opts.cwd || process.cwd(), root]);
    semantic = { available: key.available, origin: key.origin, error: null };
  }

  const built = new Date().toISOString();
  saveIndex(file, { ...header, built, entries });
  return {
    root, glob, index_file: file, built,
    docs: sections.length,
    files: new Set(sections.map((s) => s.path)).size,
    changed: changed.length,
    semantic,
    entries,
    sections,
  };
}

function rrf(lists, k) {
  const scores = new Map();
  for (const list of lists) {
    list.forEach((id, i) => {
      scores.set(id, (scores.get(id) || 0) + 1 / ((k || 60) + i + 1));
    });
  }
  return scores;
}

async function query(opts) {
  const notes = [];
  let synced;
  try {
    synced = await sync({ ...opts, embed: opts.arm !== 'keyword' && opts.arm !== 'grep' });
  } catch (err) {
    if (err.rbtvCode === 'usage' || err.rbtvCode === 'no-root') throw err;
    const e = new Error(err.message);
    e.rbtvCode = 'sync-failed';
    throw e;
  }

  const q = String(opts.query || '').trim();
  const top = opts.top || 10;
  const sections = synced.sections;
  const entries = synced.entries;

  const kwRank = [...sections]
    .map((s) => ({ id: s.id, score: keywordScore(q, s.text) }))
    .sort((a, b) => b.score - a.score);
  const grRank = [...sections]
    .map((s) => ({ id: s.id, score: grepScore(q, s.text) }))
    .sort((a, b) => b.score - a.score);

  let arm = 'keyword';
  let degraded = false;
  let semRank = [];

  const wantSem = !opts.arm || opts.arm === 'semantic';
  if (opts.arm === 'grep') {
    arm = 'grep';
  } else if (opts.arm === 'keyword') {
    arm = 'keyword';
  } else if (wantSem) {
    const got = tryProvider([opts.cwd || process.cwd(), synced.root]);
    if (!got.prov) {
      notes.push(`semantic unavailable — ${got.error || got.key.origin}`);
      degraded = true;
      arm = 'keyword';
    } else {
      try {
        const qvec = await got.prov.embedQuery(q);
        semRank = sections
          .filter((s) => Array.isArray(entries[s.id] && entries[s.id].vec))
          .map((s) => ({ id: s.id, score: cosine(qvec, entries[s.id].vec) }))
          .sort((a, b) => b.score - a.score);
        if (!opts.arm) {
          arm = 'semantic+keyword';
          const fused = rrf([
            semRank.filter((r) => r.score > 0).map((r) => r.id),
            kwRank.filter((r) => r.score > 0).map((r) => r.id),
          ]);
          const ranked = [...fused.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, top)
            .map(([id, score]) => {
              const s = entries[id];
              return { id, path: s.path, heading: s.heading, score, text: s.text };
            });
          return pack(synced, arm, degraded, notes, ranked, got.key);
        }
        arm = 'semantic';
      } catch (err) {
        notes.push(`semantic failed — ${err.message}`);
        degraded = true;
        arm = 'keyword';
      }
    }
  }

  const src = arm === 'grep' ? grRank : arm === 'semantic' ? semRank : kwRank;
  const ranked = src.slice(0, top).map((r) => {
    const s = entries[r.id];
    return { id: r.id, path: s.path, heading: s.heading, score: r.score, text: s.text };
  });
  const key = resolveKey([opts.cwd || process.cwd(), synced.root]);
  return pack(synced, arm, degraded, notes, ranked, key);
}

function pack(synced, arm, degraded, notes, results, key) {
  return {
    arm,
    degraded,
    notes,
    semantic_available: Boolean(synced.semantic && synced.semantic.available) || Boolean(key && key.available),
    semantic_origin: (synced.semantic && synced.semantic.origin) || (key && key.origin) || 'absent',
    root: synced.root,
    index_file: synced.index_file,
    docs: synced.docs,
    files: synced.files,
    built: synced.built,
    results,
  };
}

function status(opts) {
  const root = resolveRoot(opts.root);
  const glob = opts.glob || '**/*.md';
  const file = opts.indexFile || defaultIndexPath(root);
  const idx = loadIndex(file);
  const key = resolveKey([opts.cwd || process.cwd(), root]);
  const live = collect(root, glob);
  return {
    root,
    index_file: file,
    index_exists: Boolean(idx),
    built: idx && idx.built,
    docs: idx ? Object.keys(idx.entries || {}).length : 0,
    live_docs: live.sections.length,
    files: live.files.length,
    semantic_available: key.available,
    semantic_origin: key.origin,
    keyword: true,
    grep: true,
  };
}

module.exports = {
  KEY_VAR,
  resolveRoot,
  defaultIndexPath,
  walk,
  splitSections,
  resolveKey,
  keywordScore,
  grepScore,
  sync,
  query,
  status,
};

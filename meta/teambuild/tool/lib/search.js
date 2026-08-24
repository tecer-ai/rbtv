'use strict';

// `rbtv teambuild search` — natural-language need → RANKED entries over the same
// blurb corpus the browse lists. Rides `corpus.js` (the ONE enumerator, parity
// constraint) and `provider.js` (the ONE vendor boundary). It knows no vendor.
//
// THE INDEX LIFECYCLE IS W9's, IMPLEMENTED, NOT REINVENTED
// (mrd-w9-refresh-story.md §3.4 — the record this task's criterion 3 is measured
// against). Every invocation, in this order:
//   1 enumerate + hash the corpus from DISK   2 header check (provider/model/dim/
//   normalizer changed ⇒ discard every vector)   3 diff: changed = new ∪ hash-differs,
//   gone = indexed ∖ on-disk (deleted)   4 embed the changed set, batched; a batch
//   that fails keeps the prior index and yields `unindexed` ids rather than aborting
//   5 persist atomically BEFORE ranking   6 embed the query — on failure REFUSE
//   7 rank.
// The refresh is not a separate act anyone can forget: it is steps 1–5 of the search.
//
// NO KEYWORD FALLBACK, EVER. A lexical ranker wearing the word "semantic" is
// `p-green-harness`, refused on row 7.55 and refused here. A search that cannot
// reach the provider says so and exits non-zero.
//
// Built for core-build task 7.434 (design W11-semantic-search-provider-module).

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const corpus = require('./corpus');
const provider = require('./provider');

// The blurb → embed-input transform. Its VERSION is an index header field:
// changing this function without bumping the tag would leave stale vectors that
// no hash can catch, because the hash is taken over this function's OUTPUT.
const NORMALIZER = 'v1-label-blurb';

// Identity text rides along with the blurb: a staffer searching "who reviews plans"
// should reach a seat whose name says reviewer even where its description does not.
function embedText(e) {
  const label = `${e.module}/${e.component}/${e.id}${e.unit_kind ? ` (${e.unit_kind})` : ''}`;
  return `${e.kind}: ${label} — ${e.blurb}`;
}

// Entry ids per W9 §3.2 — the FILE for file-backed entries, `<csv>#<id-column>` for
// catalog rows. A row ORDINAL would invalidate every row's vector on a reordering
// that changed no content.
const CATALOG_KINDS = new Set(['agents', 'tasks', 'seats']);

function entryId(e, wsRoot) {
  const rel = wsRoot ? path.relative(wsRoot, e.path) : e.path;
  const base = rel.startsWith('..') ? e.path : rel;
  return CATALOG_KINDS.has(e.kind) ? `${base}#${e.id}` : base;
}

function sha256(s) { return crypto.createHash('sha256').update(s, 'utf8').digest('hex'); }

// ------------------------------------------------------------------ manifest

// Enumerated by corpus.js's recursive directory walk — never a wildcard pattern.
// W9's M16: `*` does not cross a leading dot, and the office-scaffold half of the
// corpus lives under a dotted path segment, so a glob-built enumerator silently
// loses 17 of its 18 files and reports success.
function manifest(root, wsRoot) {
  const out = new Map();
  for (const kind of corpus.KINDS) {
    for (const e of corpus.entries(root, kind)) {
      // An entry authored with no description carries no signal and would rank
      // 20+ identical `(no description)` strings against every query. Excluded
      // from the index and COUNTED, never silently dropped.
      if (e.blurb === corpus.NO_BLURB) continue;
      const text = embedText(e);
      out.set(entryId(e, wsRoot), { text, hash: sha256(text), entry: e });
    }
  }
  return out;
}

// --------------------------------------------------------------- index store

function indexPath(wsRoot) {
  return path.join(wsRoot, '.rbtv', 'runtime', 'teambuild', 'index.json');
}

function loadIndex(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

// Atomic: temp file in the SAME directory, then rename. A crash mid-write leaves
// the previous index intact rather than a truncated one.
function saveIndex(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(obj));
  fs.renameSync(tmp, file);
}

// W9 §3.4 step 2. `root` is carried beyond W9's four header fields because one
// index file serves whichever corpus root is searched, and vectors from another
// root are as stale as vectors from another model.
function headerOf(p, root) {
  return { provider: p.id, model: p.model, dim: p.dim, normalizer: NORMALIZER, root };
}

function headerMatches(index, header) {
  return Boolean(index) && Object.keys(header).every((k) => index[k] === header[k]);
}

// -------------------------------------------------------------------- ranking

// Cosine. The provider returns unit-length vectors, so this is a dot product in
// practice — computed properly anyway, because "the vendor normalizes" is an
// assumption about someone else's implementation.
function cosine(a, b) {
  let dot = 0; let na = 0; let nb = 0;
  for (let i = 0; i < a.length; i += 1) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}

// 6 decimals: 512 floats × 3k entries at full precision is a 40 MB JSON to parse
// on every search. The truncation is far below any ranking's resolution.
function round(v) { return v.map((x) => Math.round(x * 1e6) / 1e6); }

// ------------------------------------------------------------------ the search

// `prov` is INJECTED — the whole vendor boundary is this one parameter. Anything
// satisfying provider.js's documented contract drives this function; the shipped
// caller passes provider.voyage() and nothing else.
async function run(prov, opts) {
  const wsRoot = provider.workspaceRoot(opts.cwd) || opts.cwd;
  const root = corpus.resolveRoot(opts.root, opts.cwd);

  const t0 = Date.now();
  const man = manifest(root, wsRoot);                                    // 1
  const walkMs = Date.now() - t0;

  const file = opts.indexFile || indexPath(wsRoot);
  const header = headerOf(prov, root);
  let index = loadIndex(file);
  const headerOk = headerMatches(index, header);                          // 2
  const vectors = headerOk ? index.entries : {};
  if (index && !headerOk) index = null;

  const changed = [];                                                     // 3
  for (const [id, m] of man) {
    if (!vectors[id] || vectors[id].hash !== m.hash) changed.push(id);
  }
  const gone = Object.keys(vectors).filter((id) => !man.has(id));
  for (const id of gone) delete vectors[id];

  const unindexed = [];                                                   // 4
  const failures = [];
  for (let i = 0; i < changed.length; i += prov.batchLimit) {
    const ids = changed.slice(i, i + prov.batchLimit);
    try {
      const vecs = await prov.embedDocuments(ids.map((id) => man.get(id).text));
      ids.forEach((id, j) => { vectors[id] = { hash: man.get(id).hash, vec: round(vecs[j]) }; });
    } catch (err) {
      // A hiccup on one batch of 3,000 entries must not black out a working
      // search — but a ranking over a partial corpus that does not SAY so is a
      // lie about its own coverage. These ids are returned to the caller.
      unindexed.push(...ids);
      failures.push({ class: err.rbtvCode || 'provider-error', message: err.message, count: ids.length });
    }
  }

  // 5 — persist only when the VECTORS actually moved. A run whose every embed
  // failed must leave the file exactly as it was: rewriting identical entries
  // under a fresh timestamp would make "the index was left alone" unobservable,
  // and writing an emptied index after a header mismatch whose re-embed failed
  // would destroy usable-later data to record a failure.
  const embedded = changed.length - unindexed.length;
  if (embedded > 0 || gone.length > 0) {
    saveIndex(file, { ...header, built: new Date().toISOString(), entries: vectors });
  }

  const qvec = await prov.embedQuery(opts.query);                         // 6 — throws ⇒ refuse

  const ranked = [...man.entries()]                                       // 7
    .filter(([id]) => vectors[id])
    .map(([id, m]) => ({ id, score: cosine(qvec, vectors[id].vec), entry: m.entry }))
    .sort((a, b) => b.score - a.score)
    .slice(0, opts.top);

  return {
    query: opts.query,
    root,
    index_file: file,
    provider: header,
    corpus_entries: man.size,
    embedded,
    deleted: gone.length,
    reused: man.size - changed.length,
    walk_ms: walkMs,
    unindexed,
    failures,
    results: ranked,
  };
}

module.exports = { run, manifest, indexPath, embedText, NORMALIZER, headerOf, cosine, entryId };

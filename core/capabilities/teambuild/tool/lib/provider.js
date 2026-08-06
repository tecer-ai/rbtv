'use strict';

// THE PROVIDER BOUNDARY — the one place `teambuild search` touches an embedding
// vendor, and the one place the API key is ever read.
//
// THE CONTRACT (this is the boundary; `search.js` knows nothing else about any
// vendor). A provider is an object:
//
//   { id, model, dim, batchLimit,
//     embedDocuments(texts) -> Promise<number[][]>,   // corpus side
//     embedQuery(text)      -> Promise<number[]> }    // query side
//
//   id/model/dim go into the index header. Changing ANY of them invalidates every
//   stored vector (search.js §header check) — that is what makes the swap safe
//   rather than merely possible: a new provider cannot inherit the old one's
//   vectors.
//   embedDocuments returns one vector per input text, in input order.
//   Failures throw an Error carrying `.rbtvCode` from ERRORS below — never a raw
//   vendor payload, and never anything key-derived.
//
// SHIPPED REALIZATIONS: exactly one — Voyage. There is no provider table, no
// `--provider` flag and no stub in this file: a second realization is proven by
// CONSTRUCTING one against the contract above and passing it to search.js, which
// is a scratch act (`p-green-harness` stays refused — a stub proves the boundary,
// it never produces a shipped ranking).
//
// THE KEY BAR (7.55 §3 convention vi, standing): VOYAGE_API_KEY's VALUE never
// appears in a file, a message, a log line, an error, or a process argument.
// Everything below reports it by NAME and LENGTH only.
//
// Built for core-build task 7.434 (design W11-semantic-search-provider-module).

const fs = require('fs');
const path = require('path');

const KEY_VAR = 'VOYAGE_API_KEY';
const MODEL = 'voyage-3.5-lite';
const DIM = 512; // an output_dimension the model offers; the index header carries it
const ENDPOINT = 'https://api.voyageai.com/v1/embeddings';

// The provider's OWN contract, re-derived from it rather than remembered:
//   POST 1001 inputs -> 400 "The batch size limit is 1000. Your batch size is 1001."
// W9's M3 assumed 1000 as a round figure; this is the measured value agreeing.
const BATCH_LIMIT = 1000;

const ERRORS = {
  NO_WORKSPACE: 'no-workspace',            // no rbtv.json above cwd — cannot resolve the key's address
  KEY_FILE_ABSENT: 'key-file-absent',      // F-W11a — a SUPPLY question, routed to the owner
  KEY_MISSING: 'key-missing-after-sourcing', // F-W11b — a WIRING defect, repaired here
  UNREACHABLE: 'provider-unreachable',
  REJECTED: 'provider-rejected',
  RATE_LIMITED: 'provider-rate-limited',
  PROVIDER_ERROR: 'provider-error',
  SHAPE: 'provider-shape',                 // 200 that does not carry the promised shape
};

function fail(code, message) {
  const e = new Error(message);
  e.rbtvCode = code;
  throw e;
}

// --------------------------------------------------------------- key address
//
// The address is RESOLVED, never remembered. It was `~/ht-wkdir/.env/voyage.env`
// until 2026-08-06 15:32, when commit eaeb17b4e consolidated every machine-local
// env into one file and renamed that directory away. A remembered path returns
// nothing, and "nothing" reads as KEY MISSING — the run made exactly that error
// once already. `rbtv.json`'s `env_file` field is the durable answer.

function workspaceRoot(start) {
  let dir = path.resolve(start || process.cwd());
  for (;;) {
    if (fs.existsSync(path.join(dir, 'rbtv.json'))) return dir;
    const up = path.dirname(dir);
    if (up === dir) return null;
    dir = up;
  }
}

function keyFilePath(start) {
  const root = workspaceRoot(start);
  if (!root) {
    fail(ERRORS.NO_WORKSPACE, `no rbtv.json found walking up from ${path.resolve(start || process.cwd())} — `
      + 'the key file\'s address is that file\'s `env_file` field and cannot be guessed');
  }
  let cfg = {};
  try { cfg = JSON.parse(fs.readFileSync(path.join(root, 'rbtv.json'), 'utf8')); } catch { cfg = {}; }
  return path.join(root, cfg.env_file || '.rbtv/config/.env');
}

// The module's OWN sourcing act: nothing in this workspace loads that file into a
// process environment (measured — the run confirmed no seat env carries the var),
// so the module does it itself, at use, and every assert below then reads exactly
// what the provider call will read. An OS-environment value always wins: sourcing
// never overwrites a var that is already set.
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

// ------------------------------------------------------------- the preamble
//
// A-3, asserted IN ORDER, because the order is what discriminates (C-4):
//   1 file present BY NAME  2 sourcing performed  3 the VARIABLE present
// file absent            -> SUPPLY question (F-W11a) — the owner supplies a key;
//                           nothing here can repair it.
// file present, var empty -> WIRING defect (F-W11b) — the sourcing is wrong, or
//                           the var is named differently in the file; repaired here.
// Collapsing the two into "key missing" is the error this ordering exists to
// prevent. Values are never read into the report — name and length only.
function preamble(start) {
  const steps = [];
  const fromOsEnv = Boolean(process.env[KEY_VAR]);
  let file = null;
  try {
    file = keyFilePath(start);
  } catch (err) {
    if (!fromOsEnv) throw err;
  }

  const filePresent = Boolean(file) && fs.existsSync(file);
  steps.push({
    n: 1,
    assert: 'key file present BY NAME',
    ok: filePresent || fromOsEnv,
    detail: file
      ? `${file} — ${filePresent ? 'present' : 'ABSENT'}${fromOsEnv ? ' (moot: the variable is already in the OS environment)' : ''}`
      : 'no address resolvable (moot: the variable is already in the OS environment)',
  });
  if (!filePresent && !fromOsEnv) {
    return { ok: false, class: ERRORS.KEY_FILE_ABSENT, origin: null, file, steps };
  }

  let sourced = [];
  if (!fromOsEnv) sourced = sourceEnvFile(file);
  steps.push({
    n: 2,
    assert: 'module sourcing performed',
    ok: true,
    detail: fromOsEnv
      ? `skipped — ${KEY_VAR} was already in the OS environment (OS-env-first)`
      : `sourced ${sourced.length} variable name(s) from that file; ${KEY_VAR} among them: ${sourced.includes(KEY_VAR) ? 'yes' : 'NO'}`,
  });

  const value = process.env[KEY_VAR];
  steps.push({
    n: 3,
    assert: `environment variable ${KEY_VAR} present`,
    ok: Boolean(value),
    detail: value
      ? `${KEY_VAR} present, length ${value.length} (value never read into this report)`
      : `${KEY_VAR} absent or empty AFTER sourcing`,
  });
  if (!value) return { ok: false, class: ERRORS.KEY_MISSING, origin: null, file, steps };

  return { ok: true, class: null, origin: fromOsEnv ? 'os-env' : 'env-file', file, steps };
}

function renderPreamble(p) {
  const lines = p.steps.map((s) => `  ${s.ok ? 'ok  ' : 'FAIL'} ${s.n}. ${s.assert}: ${s.detail}`);
  lines.unshift('key preamble (A-3, asserted in order — file → sourcing → variable):');
  if (p.ok) lines.push(`  key resolved from: ${p.origin}`);
  return lines.join('\n');
}

// ------------------------------------------------------------ the realization

async function post(key, body) {
  let res;
  try {
    res = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
      body: JSON.stringify(body),
    });
  } catch (err) {
    // No response at all: DNS, TLS, connection refused, offline.
    fail(ERRORS.UNREACHABLE, `${ENDPOINT} did not answer — ${err.code || err.message}`);
  }
  const text = await res.text();
  if (res.status === 401 || res.status === 403) {
    fail(ERRORS.REJECTED, `the provider rejected the credential (HTTP ${res.status}) — the key is present but not accepted`);
  }
  if (res.status === 429) fail(ERRORS.RATE_LIMITED, `the provider rate-limited this request (HTTP ${res.status})`);
  if (res.status !== 200) {
    // The vendor's own message is carried through: it names batch/token limits
    // that no local constant should be guessing at. It carries no key material.
    fail(ERRORS.PROVIDER_ERROR, `HTTP ${res.status} — ${text.slice(0, 300)}`);
  }
  let json;
  try { json = JSON.parse(text); } catch { fail(ERRORS.SHAPE, 'HTTP 200 whose body is not JSON'); }
  const data = json.data;
  if (!Array.isArray(data) || !data.length || !Array.isArray(data[0].embedding)) {
    fail(ERRORS.SHAPE, 'HTTP 200 carrying no `data[].embedding` array');
  }
  // Ordered by the vendor's own `index`, never by array position: a provider is
  // free to answer out of order and the mapping back to entry ids must not guess.
  const out = new Array(data.length);
  data.forEach((d, i) => { out[d.index === undefined ? i : d.index] = d.embedding; });
  if (out.length !== body.input.length || out.some((v) => !Array.isArray(v))) {
    fail(ERRORS.SHAPE, `asked for ${body.input.length} vectors, got ${out.filter(Array.isArray).length}`);
  }
  return { vectors: out, tokens: (json.usage && json.usage.total_tokens) || 0 };
}

// `start` only fixes where the key address is resolved FROM; it changes nothing else.
function voyage(start) {
  const p = preamble(start);
  if (!p.ok) {
    const e = new Error(renderPreamble(p));
    e.rbtvCode = p.class;
    e.preamble = p;
    throw e;
  }
  const key = process.env[KEY_VAR];
  let tokens = 0;
  let requests = 0;

  async function embed(texts, inputType) {
    const out = [];
    for (let i = 0; i < texts.length; i += BATCH_LIMIT) {
      const slice = texts.slice(i, i + BATCH_LIMIT);
      const r = await post(key, {
        input: slice, model: MODEL, input_type: inputType, output_dimension: DIM,
      });
      requests += 1;
      tokens += r.tokens;
      out.push(...r.vectors);
    }
    return out;
  }

  return {
    id: 'voyage',
    model: MODEL,
    dim: DIM,
    batchLimit: BATCH_LIMIT,
    preamble: p,
    usage: () => ({ requests, tokens }),
    embedDocuments: (texts) => embed(texts, 'document'),
    embedQuery: async (text) => (await embed([text], 'query'))[0],
  };
}

module.exports = { KEY_VAR, ERRORS, voyage, preamble, renderPreamble, keyFilePath, workspaceRoot };

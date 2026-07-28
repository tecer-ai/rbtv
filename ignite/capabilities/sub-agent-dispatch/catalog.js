'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
  DispatchError,
  E_TARGET_NOT_CATALOGED,
  E_NO_CATALOG,
  E_CATALOG_ROW_INVALID,
} = require('./errors');

// ═════════════════════════════════════════════════════════════════════════════════════════════
// Boundary 1 — CATALOG-BOUND. The catalog is the component's EXPOSURE MANIFEST.
//
// Owner-ruled 2026-07-26 (`decisions.md#d-catalog-bound-exposure-manifest`, closing F-52), and
// restated on CMP-10 boundary 1: "a target is dispatchable IFF its component's exposure manifest
// exposes it for sub-agent dispatch". Dispatchability is an EXPOSURE fact read from the artifact
// that already owns exposure facts, so no second list of what exists is minted (PRIN-11) and
// per-part opt-in comes free.
//
// WHICH COLUMN CARRIES IT is explicitly NOT ruled — "the `method` column's `sub-agent` value, the
// `rbtv-cli` column, or a dedicated marker are Phase-3/4 design output; the ruling binds the
// ARTIFACT, not the column mechanics". THIS MODULE CHOOSES THE `method` COLUMN'S `sub-agent`
// VALUE, and the choice plus its reasoning is recorded on the manifest itself and in
// `sub-agent-dispatch.md` § The interim exposure manifest, so task 7.48 inherits a rationale
// rather than a fait accompli and is free to re-shape it without treating it as precedent.
//
// The reason, in one line: `sub-agent` is ALREADY a member of the canonical exposure-method
// vocabulary (`decisions.md#d-exposure-method-canon` — skill, command, rule, hook, sub-agent,
// agents.md, config). Reading it from `method` mints nothing. A dedicated marker column would be
// a second way to say a thing the vocabulary already says.
//
// ⚠ THE MANIFEST THIS READS TODAY IS ONE THE 7.43 SEAT AUTHORED — one row, one target, marked
// INTERIM on its own face. A green obtained against a catalog its own author wrote is a weaker
// claim than a green against a populated one, and that is stated in the seat's report rather than
// left for a reader to notice (`bars.md` 10). What it DOES prove is that the mechanism reads a
// real file at a real path on the real tree — not a fixture handed in by the check.
// ═════════════════════════════════════════════════════════════════════════════════════════════

// The exposure method that makes a part CLI-lane dispatchable. From the canonical vocabulary; not
// coined here.
const DISPATCHABLE_METHOD = 'sub-agent';

// The rbtv repo root, DERIVED from this file's own location — never supplied by a caller on the
// dispatch path. `rbtvRoot` is an option only so a probe can prove the E_NO_CATALOG branch (a root
// with no manifest anywhere); the CLI never passes it and never reads it from argv, because a
// caller that can point the catalog somewhere else has repealed boundary 1.
const RBTV_ROOT = path.resolve(__dirname, '..', '..', '..');

// WHERE MANIFESTS LIVE. `concepts/exposure-manifest.md` § file schema fixes the ruled path as
// `rbtv/<module>/<component>/exposure.csv`. MEASURED 2026-07-28: no component folders exist on
// disk anywhere in this repo — CMP-5's component-first layout is Phase-6 migration work and is
// unbuilt (`find . -mindepth 2 -maxdepth 2 -name component.md` → 0). So the interim manifest sits
// at the MODULE root and this scan accepts BOTH depths: when the component tree materializes and
// 7.48 moves the file one level down, this resolver keeps working with no edit.
const MANIFEST_NAME = 'exposure.csv';
const MANIFEST_DEPTHS = [1, 2];

// ── A minimal RFC-4180 CSV reader ────────────────────────────────────────────────────────────
// Quoted fields are honoured because entry-point paths and descriptions may carry commas; `#`
// comment lines and blank lines are skipped so the manifest can state on its own face that it is
// interim (one of the four bounds the leader put on authoring it).
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  let i = 0;
  const pushField = () => { row.push(field); field = ''; };
  const pushRow = () => { row.push(field); field = ''; rows.push(row); row = []; };
  while (i < text.length) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        quoted = false; i += 1; continue;
      }
      field += c; i += 1; continue;
    }
    if (c === '"') { quoted = true; i += 1; continue; }
    if (c === ',') { pushField(); i += 1; continue; }
    if (c === '\r') { i += 1; continue; }
    if (c === '\n') { pushRow(); i += 1; continue; }
    field += c; i += 1;
  }
  if (field.length > 0 || row.length > 0) pushRow();
  return rows.filter((r) => {
    const first = (r[0] || '').trim();
    if (first.startsWith('#')) return false;
    return r.some((cell) => cell.trim().length > 0);
  });
}

function findManifests(rbtvRoot) {
  const found = [];
  const walk = (dir, depth) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
      const child = path.join(dir, entry.name);
      const candidate = path.join(child, MANIFEST_NAME);
      if (MANIFEST_DEPTHS.includes(depth) && fs.existsSync(candidate)) found.push(candidate);
      if (depth < Math.max(...MANIFEST_DEPTHS)) walk(child, depth + 1);
    }
  };
  walk(rbtvRoot, 1);
  return found.sort();
}

// Reads every manifest on the tree and returns the rows whose `method` is `sub-agent`.
function loadCatalog({ rbtvRoot = RBTV_ROOT } = {}) {
  const manifests = findManifests(rbtvRoot);
  if (manifests.length === 0) {
    throw new DispatchError(
      E_NO_CATALOG,
      `no exposure manifest (${MANIFEST_NAME}) exists anywhere under ${rbtvRoot} — boundary 1 ` +
      `(catalog-bound) has no catalog to read, so NOTHING is dispatchable. This is a deployment ` +
      `fault, not a per-target refusal: the lane fails closed on every target until a component ` +
      `manifest exposes one for '${DISPATCHABLE_METHOD}' dispatch (task 7.48 populates it).`,
      { rbtvRoot, manifestName: MANIFEST_NAME },
    );
  }

  const entries = [];
  for (const file of manifests) {
    const rows = parseCsv(fs.readFileSync(file, 'utf8'));
    if (rows.length === 0) continue;
    const header = rows[0].map((h) => h.trim());
    const idx = (name) => header.indexOf(name);
    const iPart = idx('part-id');
    const iKind = idx('part-kind');
    const iMethod = idx('method');
    const iEntry = idx('entry-point');
    const iDesc = idx('description');
    if (iPart < 0 || iMethod < 0 || iEntry < 0) {
      throw new DispatchError(
        E_CATALOG_ROW_INVALID,
        `${file} is missing a required column (part-id, method, entry-point) — header: ${header.join(',')}`,
        { file, header },
      );
    }
    for (const row of rows.slice(1)) {
      const method = (row[iMethod] || '').trim();
      if (method !== DISPATCHABLE_METHOD) continue;
      entries.push({
        partId: (row[iPart] || '').trim(),
        partKind: iKind >= 0 ? (row[iKind] || '').trim() : '',
        method,
        entryPoint: (row[iEntry] || '').trim(),
        description: iDesc >= 0 ? (row[iDesc] || '').trim() : '',
        manifest: file,
        module: path.relative(rbtvRoot, path.dirname(file)),
      });
    }
  }
  return { manifests, entries, rbtvRoot };
}

// THE BOUNDARY-1 GATE. Returns the row, or throws. There is no third outcome and no override.
function resolveTarget(targetId, { rbtvRoot = RBTV_ROOT } = {}) {
  const catalog = loadCatalog({ rbtvRoot });
  const row = catalog.entries.find((e) => e.partId === targetId);
  if (!row) {
    throw new DispatchError(
      E_TARGET_NOT_CATALOGED,
      `target '${targetId}' is not exposed for '${DISPATCHABLE_METHOD}' dispatch by any component ` +
      `exposure manifest — REFUSING, nothing spawned (CMP-10 boundary 1: only owner-defined ` +
      `cataloged parts, never free-form agents). Dispatchable today: ` +
      `${catalog.entries.map((e) => e.partId).join(', ') || 'none'}`,
      {
        target: targetId,
        known: catalog.entries.map((e) => e.partId),
        manifests: catalog.manifests,
      },
    );
  }
  if (!row.entryPoint) {
    throw new DispatchError(
      E_CATALOG_ROW_INVALID,
      `target '${targetId}' is cataloged but declares no entry-point in ${row.manifest} — a row ` +
      `that names no entry point is not a licence to improvise one`,
      { target: targetId, manifest: row.manifest },
    );
  }
  const entryAbs = path.resolve(rbtvRoot, row.entryPoint);
  if (!fs.existsSync(entryAbs)) {
    throw new DispatchError(
      E_CATALOG_ROW_INVALID,
      `target '${targetId}' declares entry-point '${row.entryPoint}' which does not exist at ${entryAbs}`,
      { target: targetId, entryPoint: row.entryPoint, resolved: entryAbs },
    );
  }
  return { ...row, entryPointAbs: entryAbs };
}

module.exports = {
  DISPATCHABLE_METHOD,
  RBTV_ROOT,
  MANIFEST_NAME,
  parseCsv,
  findManifests,
  loadCatalog,
  resolveTarget,
};

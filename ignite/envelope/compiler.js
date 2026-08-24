'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { CONFIG_DIR, loadConfig } = require('./load-config');
const { covers, realpathOrNull, expandTokens, toPosix, matchDeny } = require('./paths');

function unresolved(p, source, extra) {
  return { ok: false, refuse: { kind: 'unresolved', path: p, source, ...extra } };
}

function conflict(pair) {
  return {
    ok: false,
    refuse: {
      kind: 'conflict',
      path: pair[0].path,
      pair: pair.map((s) => ({ path: s.path, access: s.access, source: s.source, family: s.family })),
    },
  };
}

function familyById(template, id) {
  return template.families.find((f) => f.id === id);
}

function resolveAbs(spec, ctx) {
  const expanded = expandTokens(spec, ctx);
  return path.isAbsolute(expanded) ? path.normalize(expanded) : path.resolve(ctx.workspaceRoot, expanded);
}

function pushResolved(sources, lexical, access, source, family, origin) {
  const resolved = realpathOrNull(lexical);
  if (!resolved) return unresolved(lexical, source, { family, origin });
  sources.push({ path: resolved, access, source, family, origin });
  return null;
}

function expandGlob(spec, ctx) {
  const expanded = expandTokens(spec, ctx);
  if (!expanded.endsWith('/*')) return [resolveAbs(expanded, ctx)];
  const parent = resolveAbs(expanded.slice(0, -2), ctx);
  if (!realpathOrNull(parent)) return { missing: parent };
  const names = fs.readdirSync(parent);
  return names.map((n) => path.join(parent, n));
}

function isExcluded(abs, excludes, ctx) {
  return excludes.some((ex) => covers(resolveAbs(ex, ctx), abs) || covers(abs, resolveAbs(ex, ctx)));
}

function walkOwnedFiles(root, basenames, out) {
  let entries;
  try { entries = fs.readdirSync(root, { withFileTypes: true }); } catch { return; }
  for (const ent of entries) {
    const p = path.join(root, ent.name);
    if (ent.isDirectory()) walkOwnedFiles(p, basenames, out);
    else if (basenames.has(ent.name)) out.push(p);
  }
}

function denyRelBase(rule, ctx) {
  if (rule['relative-to'] === 'rbtv-repo') return ctx.rbtvRepo;
  return ctx.workspaceRoot;
}

function relTo(base, abs) {
  const rel = toPosix(path.relative(base, abs));
  if (rel.startsWith('..')) return null;
  return rel;
}

function extensionOf(relPosix) {
  const base = relPosix.split('/').pop() || '';
  const i = base.lastIndexOf('.');
  return i < 0 ? '' : base.slice(i);
}

function excepted(relPosix, rule) {
  const exts = rule['except-extensions'] || [];
  if (exts.includes(extensionOf(relPosix))) return true;
  for (const ex of rule.except || []) {
    const n = ex.replace(/\/+$/, '');
    if (relPosix === n || relPosix.startsWith(`${n}/`)) return true;
  }
  return false;
}

function denyHits(abs, rule, ctx, goalId) {
  const base = denyRelBase(rule, ctx);
  const rel = relTo(base, abs);
  if (rel == null) return false;
  if (rule['except-launching-goal']) {
    const prefix = '.rbtv/goals/';
    if (rel === prefix + goalId || rel.startsWith(prefix + goalId + '/')) return false;
  }
  if (!matchDeny(rel, rule)) return false;
  return !excepted(rel, rule);
}

function isCredentialDeny(abs, denyList, ctx, goalId) {
  return denyList.deny.some((rule) => rule.credential && denyHits(abs, rule, ctx, goalId));
}

const TEMP_FAMILIES = new Set(['scratch-temp', 'benign-cache-config-temp']);

function authorizedCarve(a, b) {
  if (a.path === b.path) return false;
  const [narrow, wide] = covers(a.path, b.path) ? [b, a] : [a, b];
  if (narrow.origin === 'deny' && wide.family === 'vault-wide-read') return true;
  if (narrow.origin === 'daemon-owned' && (wide.family === 'goal-folder' || TEMP_FAMILIES.has(wide.family))) return true;
  if (wide.family === 'vault-wide-read' && wide.access === 'ro' && narrow.access === 'rw') return true;
  if (TEMP_FAMILIES.has(wide.family) && wide.access === 'rw') return true;
  if (narrow.origin === 'deny' && narrow.credential && wide.family === 'named-repos') return true;
  return false;
}

function findConflict(sources) {
  for (let i = 0; i < sources.length; i++) {
    for (let j = i + 1; j < sources.length; j++) {
      const a = sources[i];
      const b = sources[j];
      if (a.access === b.access) continue;
      if (!covers(a.path, b.path) && !covers(b.path, a.path)) continue;
      if (a.path !== b.path && authorizedCarve(a, b)) continue;
      return [a, b];
    }
  }
  return null;
}

function addFamilyPaths(family, specs, ctx, sources) {
  for (const spec of specs) {
    const expanded = expandGlob(spec, ctx);
    if (expanded.missing) {
      return unresolved(expanded.missing, 'template-family', { family: family.id });
    }
    const excludes = family.exclude || [];
    for (const lexical of expanded) {
      if (isExcluded(lexical, excludes, ctx)) continue;
      const fail = pushResolved(sources, lexical, family.access, 'template-family', family.id, 'family');
      if (fail) return fail;
    }
  }
  return null;
}

function compile(raw) {
  const workspaceRoot = raw && raw.workspaceRoot;
  const goalId = raw && raw.goalId;
  const rbtvRepo = raw && raw.rbtvRepo;
  if (!workspaceRoot) return unresolved('', 'template-family', { family: 'vault-wide-read', reason: 'workspaceRoot required' });
  if (!goalId) return unresolved('', 'template-family', { family: 'goal-folder', reason: 'goalId required' });
  if (!rbtvRepo) return unresolved('', 'template-family', { family: 'rbtv-and-mirror', reason: 'rbtvRepo required' });

  const ctx = {
    workspaceRoot: path.resolve(workspaceRoot),
    goalId,
    home: raw.home || os.homedir(),
    tmpdir: raw.tmpdir || os.tmpdir(),
    rbtvRepo: path.resolve(rbtvRepo),
    mirror: path.resolve(raw.mirror || path.join(workspaceRoot, '.rbtv', 'mirror')),
  };
  const namedRepos = raw.namedRepos || [];
  const projectFolder = raw.projectFolder || null;
  const credentialNames = [...(raw.credentialNames || [])];
  const extraPaths = raw.extraPaths || [];
  const config = raw.config || loadConfig(raw.configDir || CONFIG_DIR);
  const sources = [];

  const f1 = familyById(config.template, 'goal-folder');
  const failGoal = addFamilyPaths(f1, [f1.path], ctx, sources);
  if (failGoal) return failGoal;

  const ownedRoot = resolveAbs(f1.path, ctx);
  const ownedFiles = [];
  walkOwnedFiles(ownedRoot, new Set(config.daemonOwned.files), ownedFiles);
  for (const p of ownedFiles) {
    const fail = pushResolved(sources, p, 'ro', 'daemon-owned', 'goal-folder', 'daemon-owned');
    if (fail) return fail;
  }
  for (const dir of config.daemonOwned.directories) {
    const p = path.join(ownedRoot, dir);
    if (!fs.existsSync(p)) continue;
    const fail = pushResolved(sources, p, 'ro', 'daemon-owned', 'goal-folder', 'daemon-owned');
    if (fail) return fail;
  }

  const f2 = familyById(config.template, 'named-repos');
  for (const repo of namedRepos) {
    const lexical = path.isAbsolute(repo) ? path.normalize(repo) : path.resolve(ctx.workspaceRoot, repo);
    const fail = pushResolved(sources, lexical, f2.access, 'named-repo', f2.id, 'family');
    if (fail) return fail;
  }

  const f3 = familyById(config.template, 'project-folder');
  if (projectFolder) {
    const lexical = path.isAbsolute(projectFolder)
      ? path.normalize(projectFolder)
      : path.resolve(ctx.workspaceRoot, projectFolder);
    const fail = pushResolved(sources, lexical, f3.access, 'project-folder', f3.id, 'family');
    if (fail) return fail;
  }

  const f4 = familyById(config.template, 'scratch-temp');
  const failScratch = addFamilyPaths(f4, f4.paths, ctx, sources);
  if (failScratch) return failScratch;

  const f5 = familyById(config.template, 'vault-wide-read');
  const failVault = addFamilyPaths(f5, [f5.path], ctx, sources);
  if (failVault) return failVault;

  const f6 = familyById(config.template, 'rbtv-and-mirror');
  const failRbtv = addFamilyPaths(f6, f6.paths, ctx, sources);
  if (failRbtv) return failRbtv;

  const f7 = familyById(config.template, 'benign-cache-config-temp');
  const failBenign = addFamilyPaths(f7, f7.paths, ctx, sources);
  if (failBenign) return failBenign;

  for (const extra of extraPaths) {
    if (!extra || !extra.path) return unresolved('', 'extra-path', { reason: 'empty extra path' });
    const access = extra.access;
    if (access !== 'rw' && access !== 'ro') {
      return unresolved(extra.path, 'extra-path', { reason: `invalid access ${access}` });
    }
    const lexical = path.isAbsolute(extra.path)
      ? path.normalize(extra.path)
      : path.resolve(ctx.workspaceRoot, extra.path);
    const fail = pushResolved(sources, lexical, access, 'extra-path', null, 'extra');
    if (fail) return fail;
    if (isCredentialDeny(sources[sources.length - 1].path, config.denyList, ctx, goalId)) {
      return conflict([
        sources[sources.length - 1],
        { path: sources[sources.length - 1].path, access: 'ro', source: 'deny-list', family: 'vault-wide-read', kind: 'deny', credential: true },
      ]);
    }
  }

  const pair = findConflict(sources);
  if (pair) return conflict(pair);

  const byPath = new Map();
  for (const s of sources) {
    if (s.origin === 'deny') continue;
    const prev = byPath.get(s.path);
    if (!prev) byPath.set(s.path, { path: s.path, access: s.access, family: s.family, origin: s.origin, source: s.source });
  }
  const binds = [...byPath.values()].sort((a, b) => a.path.localeCompare(b.path));

  return {
    ok: true,
    binds,
    denies: config.denyList.deny,
    credentialNames,
    posture: 'caged-worker',
  };
}

function compilePlanning(raw) {
  return compile({
    ...raw,
    namedRepos: [],
    projectFolder: null,
    credentialNames: [],
    extraPaths: [],
  });
}

module.exports = {
  compile,
  compilePlanning,
  loadConfig,
  CONFIG_DIR,
  // Exported for `server/spawn/cage.js#lastCovering`, which must answer "is this covering pair at
  // different access a conflict?" with THIS function and not a second copy of it (spec-envelope §2
  // makes the compiler the source of truth). The carve rules are why a fixture workspace under a
  // baked temp family compiles: re-deriving them elsewhere refused launches the compiler admitted.
  authorizedCarve,
};

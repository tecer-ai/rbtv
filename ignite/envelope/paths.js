'use strict';

const fs = require('node:fs');
const path = require('node:path');

function covers(parent, child) {
  const a = path.normalize(parent);
  const b = path.normalize(child);
  return b === a || b.startsWith(a.endsWith(path.sep) ? a : a + path.sep);
}

function realpathOrNull(p) {
  if (!p || !fs.existsSync(p)) return null;
  try { return fs.realpathSync(p); } catch { return null; }
}

function expandTokens(spec, ctx) {
  return spec
    .split('{workspace}').join(ctx.workspaceRoot)
    .split('{goal}').join(ctx.goalId)
    .split('{home}').join(ctx.home)
    .split('{tmpdir}').join(ctx.tmpdir)
    .split('{rbtv-repo}').join(ctx.rbtvRepo)
    .split('{mirror}').join(ctx.mirror);
}

function toPosix(rel) {
  return rel.split(path.sep).join('/');
}

function globToRegExp(pattern) {
  let i = 0;
  let out = '^';
  while (i < pattern.length) {
    if (pattern.startsWith('**/', i)) {
      out += '(?:.*/)?';
      i += 3;
      continue;
    }
    if (pattern[i] === '*' && pattern[i + 1] === '*') {
      out += '.*';
      i += 2;
      continue;
    }
    if (pattern[i] === '*') {
      out += '[^/]*';
      i += 1;
      continue;
    }
    if (pattern[i] === '?') {
      out += '[^/]';
      i += 1;
      continue;
    }
    if ('\\^$+()[]{}|.'.includes(pattern[i])) out += `\\${pattern[i]}`;
    else out += pattern[i];
    i += 1;
  }
  if (pattern.endsWith('/')) out += '.*';
  out += '$';
  return new RegExp(out);
}

function matchDeny(relPosix, rule) {
  const pat = rule.pattern.replace(/\/+$/, rule.pattern.endsWith('/') ? '/' : '');
  if (pat.includes('*')) return globToRegExp(pat).test(relPosix);
  if (pat.endsWith('/')) return relPosix === pat.slice(0, -1) || relPosix.startsWith(pat);
  return relPosix === pat;
}

module.exports = {
  covers,
  realpathOrNull,
  expandTokens,
  toPosix,
  globToRegExp,
  matchDeny,
};

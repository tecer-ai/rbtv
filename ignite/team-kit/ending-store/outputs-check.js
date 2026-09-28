'use strict';

const fs = require('node:fs');

function checkDoneOutputs(declaredOutputs) {
  const list = Array.isArray(declaredOutputs) ? declaredOutputs : [];
  if (list.length === 0) return { ok: true, missing: null };
  for (const item of list) {
    const declaredPath = typeof item === 'string' ? item : item && item.path;
    if (!declaredPath) return { ok: false, missing: String(item) };
    if (!fs.existsSync(declaredPath)) return { ok: false, missing: declaredPath };
    const stat = fs.statSync(declaredPath);
    if (!stat.isFile()) return { ok: false, missing: declaredPath };
    if (stat.size <= 0) return { ok: false, missing: declaredPath };
  }
  return { ok: true, missing: null };
}

module.exports = { checkDoneOutputs };

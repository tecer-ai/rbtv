'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { withMemoryLock, safeWritePath } = require('./lock.js');
const { checkMemory, LEARNED_FILE, agentBaselinePath } = require('./records.js');
const { failure, refusalError } = require('./failures.js');

function globalRulesPath(workspace) {
  return path.join(workspace, '.rbtv', 'memory', LEARNED_FILE);
}

function publishGlobalRule(workspace, text, { approval = null, migrated = false } = {}) {
  const failures = [];
  if (migrated) {
    failures.push(failure({
      path: `.rbtv/memory/${LEARNED_FILE}`, operation: 'global-rule',
      requirement: 'migrated feedback is not global approval',
      expected: 'an explicit global correction or an owner approval reference',
      reason: 'migrated feedback is not global approval',
    }));
  }
  if (typeof approval !== 'string' || !approval.trim()) {
    failures.push(failure({
      path: `.rbtv/memory/${LEARNED_FILE}`, operation: 'global-rule',
      requirement: 'approval reference missing',
      expected: 'an explicit global correction or an owner approval reference',
      reason: 'global rule requires an approval reference',
    }));
  }
  if (failures.length) throw refusalError(failures);
  let form;
  try { form = checkMemory('learned', text); }
  catch (error) {
    throw refusalError([failure({
      path: `.rbtv/memory/${LEARNED_FILE}`, operation: 'global-rule',
      requirement: error.message, expected: 'learned-rules heading, marker, Why, and dated provenance',
      reason: error.message,
    })]);
  }
  return withMemoryLock(workspace, () => {
    const file = globalRulesPath(workspace);
    safeWritePath(workspace, file);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, text.endsWith('\n') ? text : `${text}\n`, 'utf8');
    return { path: file, published: true, approval: approval.trim(), form };
  });
}

function loadLearned(workspace, agentHome) {
  const files = [];
  const globalFile = globalRulesPath(workspace);
  const localFile = agentHome ? agentBaselinePath(agentHome) : null;
  for (const file of [globalFile, localFile].filter(Boolean)) {
    if (fs.existsSync(file)) files.push({ path: file, text: fs.readFileSync(file, 'utf8') });
  }
  return files;
}

module.exports = { globalRulesPath, publishGlobalRule, loadLearned };

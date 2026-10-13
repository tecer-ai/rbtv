'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { runtimeFolder, safeWritePath, withMemoryLock } = require('./lock.js');
const { failure, refusalError } = require('./failures.js');

const KINDS = ['remember', 'transcript', 'message', 'file', 'artifact'];

function pendingDir(workspace) {
  return path.join(runtimeFolder(workspace), 'evidence-pending');
}

function intakeEvidence(workspace, text, { agent, thread = null, now = Date.now(), evidence }) {
  const failures = [];
  const need = (ok, requirement, expected) => {
    if (!ok) failures.push(failure({ path: null, operation: 'evidence', requirement, expected, reason: requirement }));
  };
  need(evidence && typeof evidence === 'object', 'evidence intake requires a source object', 'sourceKind, sourceRef, author, quote, and connector.accessible or artifact');
  if (!evidence || typeof evidence !== 'object') throw refusalError(failures);
  need(KINDS.includes(evidence.sourceKind), 'evidence sourceKind is missing or unknown', `one of ${KINDS.join(', ')}`);
  need(typeof evidence.sourceRef === 'string' && evidence.sourceRef.trim(), 'evidence sourceRef is missing', 'native source identifier or reference');
  need(typeof evidence.author === 'string' && evidence.author.trim(), 'evidence author is missing', 'attributable speaker or author identity');
  need(typeof evidence.quote === 'string' && evidence.quote.trim(), 'evidence quote is missing', 'quoted evidence submitted by the caller');
  const accessible = evidence.connector?.accessible === true || (typeof evidence.artifact === 'string' && evidence.artifact.trim());
  const observed = evidence.observed === true || evidence.sourceKind !== 'remember';
  if (failures.length) throw refusalError(failures);
  if (!accessible || observed) {
    return withMemoryLock(workspace, () => {
      const dir = pendingDir(workspace);
      fs.mkdirSync(dir, { recursive: true });
      const file = safeWritePath(workspace, path.join(dir, `${randomUUID()}.json`));
      const body = {
        status: 'pending',
        agent,
        thread,
        recorded_at: new Date(now).toISOString(),
        sourceKind: evidence.sourceKind,
        sourceRef: evidence.sourceRef,
        author: evidence.author,
        quote: evidence.quote,
        reason: !accessible ? 'source not verified' : 'observed evidence is not a remember request',
      };
      fs.writeFileSync(file, `${JSON.stringify(body)}\n`, { mode: 0o600 });
      return { path: file, pending: true, appended: false, claim: false };
    });
  }
  const { rememberFact } = require('./records.js');
  const saved = rememberFact(workspace, text, { agent, thread, now });
  return { ...saved, pending: false, claim: true };
}

module.exports = { intakeEvidence, pendingDir };

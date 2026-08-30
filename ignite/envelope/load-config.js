'use strict';

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');

const CONFIG_DIR = __dirname;
const REQUIRED_FAMILY_IDS = [
  'goal-folder',
  'named-repos',
  'project-folder',
  'scratch-temp',
  'vault-wide-read',
  'rbtv-repo',
  'benign-cache-config-temp',
  'ending-store',
  'mirror',
];

function loadYaml(filePath) {
  const doc = yaml.load(fs.readFileSync(filePath, 'utf8'));
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    throw new Error(`${filePath}: must be a YAML mapping`);
  }
  return doc;
}

function requireKeys(doc, keys, filePath) {
  for (const key of keys) {
    if (doc[key] == null) throw new Error(`${filePath}: missing required key ${key}`);
  }
}

function validateTemplate(doc, filePath) {
  requireKeys(doc, ['version', 'families'], filePath);
  if (!Array.isArray(doc.families) || doc.families.length !== REQUIRED_FAMILY_IDS.length) {
    throw new Error(`${filePath}: families must be a ${REQUIRED_FAMILY_IDS.length}-row list`);
  }
  const ids = doc.families.map((f) => f && f.id);
  for (const id of REQUIRED_FAMILY_IDS) {
    if (!ids.includes(id)) throw new Error(`${filePath}: missing family ${id}`);
  }
  return doc;
}

function validateDenyList(doc, filePath) {
  requireKeys(doc, ['version', 'deny'], filePath);
  if (!Array.isArray(doc.deny) || doc.deny.length === 0) {
    throw new Error(`${filePath}: deny must be a non-empty list`);
  }
  for (const row of doc.deny) {
    if (!row || typeof row.pattern !== 'string' || !row.pattern) {
      throw new Error(`${filePath}: each deny row needs pattern`);
    }
  }
  return doc;
}

function validateDaemonOwned(doc, filePath) {
  requireKeys(doc, ['version', 'files', 'directories', 'proper-subfolders-rw'], filePath);
  if (!Array.isArray(doc.files) || doc.files.length === 0) {
    throw new Error(`${filePath}: files must be a non-empty list`);
  }
  if (!Array.isArray(doc.directories) || doc.directories.length === 0) {
    throw new Error(`${filePath}: directories must be a non-empty list`);
  }
  return doc;
}

function loadConfig(configDir) {
  const dir = configDir || CONFIG_DIR;
  const templatePath = path.join(dir, 'envelope-template.yaml');
  const denyPath = path.join(dir, 'envelope-deny-list.yaml');
  const ownedPath = path.join(dir, 'daemon-owned-records.yaml');
  return {
    template: validateTemplate(loadYaml(templatePath), templatePath),
    denyList: validateDenyList(loadYaml(denyPath), denyPath),
    daemonOwned: validateDaemonOwned(loadYaml(ownedPath), ownedPath),
    paths: { templatePath, denyPath, ownedPath },
  };
}

module.exports = {
  CONFIG_DIR,
  REQUIRED_FAMILY_IDS,
  loadConfig,
  validateTemplate,
  validateDenyList,
  validateDaemonOwned,
};

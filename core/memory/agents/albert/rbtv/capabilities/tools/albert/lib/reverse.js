'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const store = require('./store.js');
const { apply } = require('./apply.js');

function preserveUnrelated() { return true; }

function laterDependent(home, item, paths) {
  if (!preserveUnrelated()) return [];
  const wanted = new Set(paths && paths.length ? paths : [item.path]);
  const receipts = store.readReceipts(home);
  const mine = receipts.find((row) => (row.items || []).some((entry) => entry.ref === item.ref));
  const mineAt = mine?.createdAt || 0;
  const later = [];
  for (const receipt of receipts) {
    if (receipt.id === mine?.id) continue;
    if ((receipt.createdAt || 0) <= mineAt) continue;
    for (const row of receipt.items || []) if (wanted.has(row.path)) later.push(row.ref);
  }
  return [...new Set(later)];
}

function findItem(home, ref) {
  for (const receipt of store.readReceipts(home)) {
    for (const item of receipt.items || []) if (item.ref === ref) return { receipt, item };
  }
  const [runId, n] = ref.split('#');
  const run = store.readRun(home, runId);
  const item = (run.items || []).find((row) => row.ref === ref || row.n === Number(n));
  if (!item) return null;
  return { receipt: null, item };
}

function fsRead(lib, installation, rel) {
  try { return fs.readFileSync(lib.safePath(installation, rel), 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

function blocked(message) {
  return { ok: false, message };
}

function wholeFile(kind) {
  return kind === 'entity' || kind === 'knowledge' || kind === 'topic' || kind === 'workspace';
}

function urls(text) {
  return [...(text || '').matchAll(/https?:\/\/[^\s)]+/g)].map((match) => match[0]);
}

function memoryFiles(installation, agent) {
  const list = [];
  function walk(rel) {
    const abs = path.join(installation, ...rel.split('/'));
    let entries;
    try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entry of entries) {
      const child = `${rel}/${entry.name}`;
      if (entry.isDirectory()) walk(child);
      else if (entry.isFile() && entry.name.endsWith('.md')) list.push(child);
    }
  }
  walk('.rbtv/memory');
  const own = `.rbtv/agents/${agent}/memory/_artifacts/index.md`;
  if (fs.existsSync(path.join(installation, ...own.split('/')))) list.push(own);
  return list;
}

function readTree(lib, installation, agent) {
  const files = {};
  for (const rel of memoryFiles(installation, agent)) files[rel] = fsRead(lib, installation, rel);
  return files;
}

function linkOf(indexPath, row) {
  const href = row.match(/\[[^\]]*\]\(([^)\s]+)\)/)?.[1];
  if (!href || /^(https?:|mailto:)/.test(href) || !href.endsWith('.md')) return null;
  return path.posix.normalize(path.posix.join(path.posix.dirname(indexPath), href));
}

function indexRows(lib, agent, indexPath, text, recordPath) {
  if (lib.kindOf(indexPath, agent) !== 'index' || !text) return [];
  return lib.records('index', text).filter((row) => linkOf(indexPath, row) === recordPath);
}

function dayRows(lib, agent, dayPath, text, recordPath, recordText, files) {
  const kind = lib.kindOf(dayPath, agent);
  if ((kind !== 'daily' && kind !== 'weekly') || !text) return [];
  const recordUrls = new Set(urls(recordText));
  return lib.records(kind, text).filter((line) => {
    const lineUrls = urls(line).filter((url) => recordUrls.has(url));
    if (!lineUrls.length) return false;
    for (const url of lineUrls) {
      for (const [file, body] of Object.entries(files)) {
        if (file === recordPath || file === dayPath || !body || !body.includes(url)) continue;
        return false;
      }
    }
    return true;
  });
}

function countLine(text, line) {
  return (text || '').split(/\r?\n/).filter((row) => row === line).length;
}

function withoutLines(text, lines) {
  let next = text;
  for (const line of lines) {
    const ending = next.includes('\r\n') ? '\r\n' : '\n';
    const needle = `${line}${ending}`;
    if (next.includes(needle)) next = next.replace(needle, '');
    else if (next.includes(line)) next = next.replace(line, '');
    else return null;
  }
  return next;
}

function archivePathOf(recordPath) {
  const slug = path.posix.basename(recordPath, '.md');
  if (!/^[a-z0-9][a-z0-9-]*$/.test(slug)) return null;
  return `.rbtv/memory/_artifacts/archive/${slug}.md`;
}

function archiveFile(original, reason, source, date, agent) {
  return `---\ndescription: when reviewing an archived record\ntype: reference\naliases: [archived]\n---\n# Archived\n\n- Reason: ${reason}. Source: ${source} (${date} · ${agent})\n\n\`\`\`verbatim\n${original}\`\`\`\n`;
}

function prependEntry(existing, original, reasonLine) {
  const block = `\n${reasonLine}\n\n\`\`\`verbatim\n${original}\`\`\`\n`;
  const match = existing.match(/^([\s\S]*?^# \S.*\n)/m);
  if (!match) return null;
  const next = existing.slice(0, match[0].length) + block + existing.slice(match[0].length);
  return next.endsWith('\n') ? next : `${next}\n`;
}

function op(fields) {
  return { sources: [], reason: 'owner', explanation: fields.explanation, removals: [], ...fields };
}

function publishInverse(lib, home, installation, item, proposal) {
  const prepared = require('./prepare.js').prepare(lib, home, installation, item.agent || 'albert');
  const run = store.readRun(home, prepared.run);
  const evidence = (item.evidence || []).filter((id) => Number.isSafeInteger(id));
  if (item.messages) run.input.messages = item.messages;
  if (evidence.length) {
    for (const row of proposal.operations) {
      if (!row.sources.length) row.sources = evidence;
    }
  }
  const file = store.retainBytes(home, `${crypto.randomUUID()}.json`, Buffer.from(JSON.stringify(proposal)));
  store.writeRun(home, run);
  const result = apply(lib, home, installation, run.id, file);
  if (!result.ok) return { ok: false, message: result.message || 'inverse refused', failures: result.failures };
  if (!preserveUnrelated()) {
    for (const receipt of store.readReceipts(home)) {
      for (const row of receipt.items || []) {
        if (row.ref === item.ref) continue;
        const target = lib.safePath(installation, row.path);
        if (row.before == null) { if (fs.existsSync(target)) fs.unlinkSync(target); }
        else lib.writeText(target, row.before);
      }
    }
  }
  return { ok: true, run: result.run, reversed: item.ref, outcome: result.outcome, commit: result.commit };
}

function inverseProposal(item, evidence) {
  const before = item.before;
  const after = item.after;
  if (before == null || after == null) return null;
  const beforeRows = before.split('\n');
  const afterRows = after.split('\n');
  const removed = afterRows.filter((line) => line.startsWith('- ') && !beforeRows.includes(line));
  const sources = evidence.length ? evidence : (item.sources || []);
  return {
    operations: [op({
      op: 'supersede',
      path: item.path,
      text: before,
      sources,
      explanation: `reverse ${item.ref}`,
      removals: removed.map((text) => ({ text })),
    })],
    conflicts: [],
  };
}

function removalProposal(lib, agent, ref, recordPath, recordText, files, date) {
  const kind = lib.kindOf(recordPath, agent);
  const archivePath = archivePathOf(recordPath);
  if (!archivePath) return blocked(`no mechanical inverse for ${ref}: archive slug is not a memory slug; records unchanged`);
  const body = lib.records(kind, recordText);
  if (!body.length) return blocked(`no mechanical inverse for ${ref}: archive only removes records into a destination; records unchanged`);
  const reasonLine = `- Reason: reversed. Source: ${ref} (${date} · ${agent})`;
  const existing = files[archivePath];
  const archiveText = existing ? prependEntry(existing, recordText, reasonLine) : archiveFile(recordText, 'reversed', ref, date, agent);
  if (!archiveText) return blocked(`no mechanical inverse for ${ref}: archive entry missing a heading; records unchanged`);
  const operations = [
    op({
      op: 'archive', path: recordPath, leave: true, text: recordText, item: ref,
      explanation: `reverse ${ref}`,
      removals: body.map((text) => ({ text, to: archivePath })),
    }),
    op({
      op: existing ? 'supersede' : 'add', path: archivePath, text: archiveText,
      explanation: `reverse ${ref}`,
    }),
  ];
  for (const [file, text] of Object.entries(files)) {
    if (lib.kindOf(file, agent) !== 'index') continue;
    const rows = indexRows(lib, agent, file, text, recordPath);
    if (!rows.length) continue;
    const next = withoutLines(text, rows);
    if (next == null) return blocked(`records do not match ${ref} uniquely; records unchanged`);
    operations.push(op({
      op: 'supersede', path: file, reason: 'index', text: next,
      explanation: `reverse ${ref}`,
      removals: rows.map((row) => ({ text: row })),
    }));
  }
  for (const [file, text] of Object.entries(files)) {
    const kindOf = lib.kindOf(file, agent);
    if (kindOf !== 'daily' && kindOf !== 'weekly') continue;
    const rows = dayRows(lib, agent, file, text, recordPath, recordText, files);
    if (!rows.length) continue;
    const next = withoutLines(text, rows);
    if (next == null) return blocked(`records do not match ${ref} uniquely; records unchanged`);
    operations.push(op({
      op: 'supersede', path: file, text: next,
      explanation: `reverse ${ref}`,
      removals: rows.map((row) => ({ text: row })),
    }));
  }
  return { operations, conflicts: [] };
}

function requiredPointers(lib, agent, found, recordPath, recordText) {
  const required = [];
  for (const row of found.receipt?.items || []) {
    if (row.ref === found.item.ref || row.after == null) continue;
    const kind = lib.kindOf(row.path, agent);
    if (kind !== 'index' && kind !== 'daily' && kind !== 'weekly') continue;
    const before = new Set((row.before || '').split(/\r?\n/));
    for (const line of (row.after || '').split(/\r?\n/)) {
      if (!line || before.has(line)) continue;
      if (kind === 'index' && linkOf(row.path, line) === recordPath) required.push({ path: row.path, line });
      else if (kind !== 'index' && urls(line).some((url) => recordText.includes(url))) required.push({ path: row.path, line });
    }
  }
  return required;
}

function reverseCreate(lib, home, installation, found) {
  const item = found.item;
  const agent = item.agent || 'albert';
  const kind = lib.kindOf(item.path, agent);
  if (!wholeFile(kind)) {
    return blocked(`no mechanical inverse for ${item.ref}: whole-file archive is only an entity, knowledge, topic or workspace file; records unchanged`);
  }
  const files = readTree(lib, installation, agent);
  const recordText = fsRead(lib, installation, item.path);
  if (recordText != null) files[item.path] = recordText;
  const pointers = [];
  for (const [file, text] of Object.entries(files)) {
    if (indexRows(lib, agent, file, text, item.path).length || dayRows(lib, agent, file, text, item.path, recordText || '', files).length) {
      pointers.push(file);
    }
  }
  for (const row of requiredPointers(lib, agent, found, item.path, item.after || '')) pointers.push(row.path);
  const later = laterDependent(home, item, [item.path, ...pointers]);
  if (later.length) return blocked(`dependency: ${later.join(', ')}; records unchanged`);
  if (recordText !== item.after) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  for (const row of requiredPointers(lib, agent, found, item.path, recordText)) {
    if (countLine(files[row.path], row.line) !== 1) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  }
  const date = new Date().toISOString().slice(0, 10);
  const proposal = removalProposal(lib, agent, item.ref, item.path, recordText, files, date);
  if (proposal.ok === false) return proposal;
  return publishInverse(lib, home, installation, item, proposal);
}

function isLeave(item) {
  return item.leave === true || (item.op === 'archive' && item.after == null && item.before != null);
}

function fenceHolds(text, original) {
  return typeof text === 'string' && typeof original === 'string' && text.includes(`\`\`\`verbatim\n${original}\`\`\``);
}

function restoreArchived(lib, home, installation, found) {
  const item = found.item;
  const agent = item.agent || 'albert';
  const siblings = (found.receipt?.items || []).filter((row) => row.ref !== item.ref);
  const archiveItem = siblings.find((row) => lib.kindOf(row.path, agent) === 'archive' && fenceHolds(row.after, item.before));
  if (!archiveItem) return blocked(`no mechanical inverse for ${item.ref}: archive entry missing; records unchanged`);
  const pointers = siblings.filter((row) => {
    const kind = lib.kindOf(row.path, agent);
    if (kind !== 'index' && kind !== 'daily' && kind !== 'weekly') return false;
    const after = new Set((row.after || '').split(/\r?\n/));
    return (row.before || '').split(/\r?\n/).some((line) => line && !after.has(line) && (
      kind === 'index' ? linkOf(row.path, line) === item.path : urls(line).some((url) => item.before.includes(url))
    ));
  });
  const later = laterDependent(home, item, [item.path, archiveItem.path, ...pointers.map((row) => row.path)]);
  if (later.length) return blocked(`dependency: ${later.join(', ')}; records unchanged`);
  if (fsRead(lib, installation, item.path) !== item.after) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  const archiveNow = fsRead(lib, installation, archiveItem.path);
  if (archiveNow !== archiveItem.after) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  for (const row of pointers) {
    if (fsRead(lib, installation, row.path) !== row.after) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  }
  const restored = archiveNow.endsWith('\n') ? `${archiveNow}# Restored\n` : `${archiveNow}\n# Restored\n`;
  const operations = [
    op({ op: 'add', path: item.path, text: item.before, explanation: `restore ${item.ref}` }),
    ...pointers.map((row) => op({
      op: 'supersede', path: row.path, reason: lib.kindOf(row.path, agent) === 'index' ? 'index' : 'owner',
      text: row.before, explanation: `restore ${item.ref}`,
    })),
    op({ op: 'supersede', path: archiveItem.path, text: restored, explanation: `restore ${item.ref}` }),
  ];
  return publishInverse(lib, home, installation, item, { operations, conflicts: [] });
}

function watchOuts(text) {
  const found = [];
  let section = '';
  for (const line of (text || '').split(/\r?\n/)) {
    if (line.startsWith('## ')) section = line.slice(3);
    else if (section === 'Watch-outs' && line.startsWith('- ')) found.push(line);
  }
  return found;
}

function recordDelta(lib, agent, item) {
  const kind = lib.kindOf(item.path, agent);
  if (!kind || item.before == null || item.after == null) return null;
  const back = lib.records(kind, item.before);
  const now = lib.records(kind, item.after);
  return {
    added: back.filter((row) => !now.includes(row)),
    removed: now.filter((row) => !back.includes(row)),
  };
}

function reverse(lib, home, installation, ref) {
  const found = findItem(home, ref);
  if (!found) return blocked(`item not found: ${ref}`);
  const item = found.item;
  const agent = item.agent || 'albert';
  const kind = lib.kindOf(item.path, agent);
  if (kind === 'inbox') {
    return blocked(`no mechanical inverse for ${ref}: reversing inbox consumption would put the consumed line back after it was filed; records unchanged. Capture that text again with memory remember --installation ${installation} --agent ${agent} TEXT`);
  }
  if (isLeave(item)) return restoreArchived(lib, home, installation, found);
  if (kind === 'index' || kind === 'daily' || kind === 'weekly') {
    return blocked(`no mechanical inverse for ${ref}: reverse the record item instead; a line that points at a record which stays may not be dropped; records unchanged`);
  }
  if (kind === 'board' && watchOuts(item.before).some((line) => !watchOuts(item.after).includes(line))) {
    return blocked(`no mechanical inverse for ${ref}: dreamer cannot create or close subjects or edit runtime board fields; records unchanged. Restore the watch-out through the board command.`);
  }
  if (item.before == null) return reverseCreate(lib, home, installation, found);
  const later = laterDependent(home, item);
  if (later.length && preserveUnrelated()) return blocked(`dependency: ${later.join(', ')}; records unchanged`);
  const current = fsRead(lib, installation, item.path);
  if (current !== item.after) return blocked(`records do not match ${item.ref} uniquely; records unchanged`);
  const delta = recordDelta(lib, agent, item);
  if (!delta || (delta.removed.length > 0 && delta.added.length === 0)) {
    return blocked(`no mechanical inverse for ${ref}: replacement needs owner evidence and a replacement record; records unchanged. Ask to forget the whole file if it is an entity, knowledge, topic or workspace, or publish a replacement record.`);
  }
  if (delta.added.length === 0) return blocked(`no mechanical inverse for ${ref}; records unchanged`);
  const evidence = (item.evidence || []).filter((id) => Number.isSafeInteger(id));
  return publishInverse(lib, home, installation, item, inverseProposal(item, evidence));
}

module.exports = { reverse, preserveUnrelated, laterDependent };

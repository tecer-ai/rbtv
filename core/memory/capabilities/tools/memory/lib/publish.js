'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { stripVTControlCharacters } = require('node:util');
const { parseBoard } = require('./board.js');
const { checkMemory } = require('./records.js');
const { runtimeFolder, acquireMemoryLock } = require('./lock.js');
const { PROFILE_POINTS, LEARNED_MAX, DAILY_LINES, WEEKLY_LINES, WARN_LINES, SPLIT_LINES, nonemptyLines, splitOnDemand } = require('./limits.js');
const { failure, fromMessage, Refusal, refusalError } = require('./failures.js');

const GENERAL = '.rbtv/memory/';
const REASONS = ['owner', 'merge', 'file', 'fold', 'detail', 'closed', 'expired', 'index'];
const normalize = (text) => text.replace(/\r\n/g, '\n');
const nonempty = (text) => normalize(text).split('\n').filter((line) => line.trim());
function requireThat(ok, message) { if (!ok) throw new Refusal(message); }

function safePath(workspace, relative) {
  requireThat(typeof relative === 'string' && relative.length > 0, 'path required');
  const parts = relative.split('/');
  requireThat(!parts.some((part) => !part || part === '.' || part === '..' ||
    /[\\\x00-\x1f:*?"<>|]/.test(part) || /[. ]$/.test(part) ||
    /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part) ||
    /^(4-archives|agent\.md)$/i.test(part)), 'unsafe memory path');
  let file = workspace;
  for (const part of parts) {
    file = path.join(file, part);
    try { requireThat(!fs.lstatSync(file).isSymbolicLink(), 'memory paths cannot traverse symlinks'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return file;
}

function kindOf(relative, slug) {
  const own = `.rbtv/agents/${slug}/`;
  if (relative === `${own}_artifacts/board.md`) return 'board';
  if (relative === `${own}memory/learned.md`) return 'learned';
  if (relative === `${own}memory/_artifacts/index.md`) return 'index';
  if (new RegExp(`^${own.replaceAll('.', '\\.')}memory/(?:archive/)?[a-z0-9][a-z0-9-]*\\.md$`).test(relative)) return 'topic';
  if (!relative.startsWith(GENERAL)) return null;
  const name = relative.slice(GENERAL.length);
  if (['profile.md', 'inbox.md', 'workstreams.md'].includes(name)) return name.slice(0, -3);
  if (name === '_artifacts/index.md' || /^(?:entities(?:\/(?:people|orgs|places|devices))?|knowledge|workspaces|timeline(?:\/(?:daily|weekly))?)\/_artifacts\/index\.md$/.test(name)) return 'index';
  if (/^_artifacts\/archive\/[a-z0-9][a-z0-9-]*\.md$/.test(name)) return 'archive';
  if (/^entities\/(people|orgs|places|devices)\/[a-z0-9][a-z0-9-]*\.md$/.test(name)) return 'entity';
  if (/^knowledge\/(facts|preferences|decisions|self|health)(?:\/[a-z0-9][a-z0-9-]*)?\.md$/.test(name)) return 'knowledge';
  if (/^workspaces\/[a-z0-9][a-z0-9-]*\.md$/.test(name)) return 'workspace';
  if (/^timeline\/daily\/\d{4}-\d{2}-\d{2}\.md$/.test(name)) return 'daily';
  if (/^timeline\/weekly\/\d{4}-W\d{2}\.md$/.test(name)) return 'weekly';
  return null;
}

function bodyOf(text) { return normalize(text).replace(/^---\n[\s\S]*?\n---\n/, ''); }
function recordBody(text) { return text.match(/^(.*) \(\d{4}-\d{2}-\d{2} · .+\)$/)?.[1] ?? text; }
function records(kind, text) {
  if (kind === 'board') {
    const board = parseBoard(text);
    return [...board.subjects.map((subject) => board.lines.slice(subject.start, subject.end).filter((line) => line.trim()).join('\n')),
      ...board.watchOuts, ...board.closed];
  }
  return nonempty(bodyOf(text)).filter((line) => !line.startsWith('#') &&
    !/^\|\s*(?:Open\s*\||:?-)/.test(line));
}

function validDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`)) &&
    new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}

// Use the same counts for prompt budgets and cap refusals. Character counts
// include frontmatter and line endings, matching the memory checkers.
function fileSizes(kind, text) {
  const size = (count, cap, unit) => ({ count, cap, unit });
  if (kind === 'board') {
    const sections = [[], [], [], []];
    let section = -1;
    for (const line of nonempty(text)) {
      if (line.startsWith('## ')) section++;
      else if (sections[section]) sections[section].push(line);
    }
    return [size(nonempty(text).length - sections[2].length, null, 'nonempty lines outside Timers'),
      size(sections[0].filter((line) => line.startsWith('### ')).length, null, 'subjects'),
      size(sections[1].length, null, 'watch-outs'), size(sections[3].length, null, 'closed entries')];
  }
  if (kind === 'learned') return [size(nonempty(text).filter((line) => line.startsWith('- ')).length, LEARNED_MAX, 'rules')];
  if (kind === 'daily' || kind === 'weekly') return [size(text ? normalize(text).trimEnd().split('\n').length : 0, kind === 'daily' ? DAILY_LINES : WEEKLY_LINES, 'lines')];
  if (['inbox', 'index', 'workstreams', 'board'].includes(kind) && kind !== 'board') return [size(nonempty(text).length, null, 'nonempty lines')];
  if (kind === 'profile') return [size([...text].length, PROFILE_POINTS, 'characters')];
  return [size(nonemptyLines(text).length, null, `nonempty lines; warn at ${WARN_LINES}; split at ${SPLIT_LINES}`)];
}

function checkFile(relative, kind, text) {
  requireThat(typeof text === 'string' && !/[\x00\r]/.test(text.replace(/\r\n/g, '')) && !text.includes('[['), 'invalid memory text');
  for (const { count, cap, unit } of fileSizes(kind, text)) {
    requireThat(cap == null || count <= cap, `${relative}: ${kind} cap exceeded (${count}/${cap} ${unit})`);
  }
  if (['board', 'learned', 'profile', 'inbox', 'index', 'workspace'].includes(kind)) {
    try { checkMemory(kind, text); } catch (error) { throw new Refusal(error.message, [fromMessage(error.message, { path: relative, operation: kind, expected: error.message })]); }
  } else {
    const front = normalize(text).match(/^---\n([\s\S]*?)\n---\n/);
    requireThat(front && /^description: when .+$/m.test(front[1]) && /^# \S/m.test(bodyOf(text)), `${kind} requires description and heading`);
    if (!['daily', 'weekly', 'workstreams'].includes(kind)) {
      const type = front[1].match(/^type: (\S+)$/m)?.[1];
      const expected = kind === 'entity' ? ({ people: 'person', orgs: 'org', places: 'place', devices: 'device' })[relative.split('/').at(-2)] :
        kind === 'knowledge' ? (relative.split('/').at(-2) === 'knowledge' ? path.posix.basename(relative, '.md') : relative.split('/').at(-2)) : null;
      requireThat(expected ? type === expected : ['subject', 'procedure', 'reference'].includes(type), `${kind} type refused`);
      requireThat(/^aliases: \[.*\]$/m.test(front[1]), `${kind} aliases required`);
      if (kind === 'topic' && type === 'subject') {
        const threads = nonempty(bodyOf(text)).filter((line) => line.startsWith('Threads: '));
        requireThat(threads.length === 1 && /^Threads: (?:none|\[[^\]]+\]\(https?:\/\/\S+\)(?: · \[[^\]]+\]\(https?:\/\/\S+\))*)$/.test(threads[0]), 'subject topics require Threads');
      }
    }
    const rows = records(kind, text);
    if (kind === 'daily' || kind === 'weekly') {
      const stem = path.posix.basename(relative, '.md');
      requireThat(kind === 'daily' ? validDate(stem) : /^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$/.test(stem), 'invalid timeline date');
      for (const row of rows) requireThat(/^(?:Periodic note: |Week: )?\[[^\]]+\]\([^)]+\)$/.test(row) ||
        (kind === 'daily' ? /^- .+ — [a-z0-9-]+\/\[[^\]]+\]\(https?:\/\/[^\s]+\)$/.test(row) :
          /^- .+ — \[\d{4}-\d{2}-\d{2}\]\(\.\.\/daily\/\d{4}-\d{2}-\d{2}\.md\)$/.test(row)), 'timeline must contain episodes and links only');
    } else if (kind === 'workstreams') {
      requireThat(rows.every((row) => /^- .+(?:\[board\]\([^)]+\)|board: none)$/.test(row)), 'workstreams requires pointers');
    } else {
      for (const row of rows) {
        if (/^(?:Threads: |(?:- )?(?:Vault|Glossary|Shared docs): )/.test(row)) continue;
        const record = row.match(/^(?:- |\d+\. ).+ \((\d{4}-\d{2}-\d{2}) · .+\)$/);
        requireThat(record && validDate(record[1]), 'records require dated provenance');
      }
    }
  }
  const dated = kind === 'board' ? (() => {
    const board = parseBoard(text);
    return [...board.subjects.flatMap((subject) => subject.state), ...board.watchOuts, ...board.closed];
  })() : records(kind, text);
  for (const row of dated) {
    const fact = recordBody(row);
    if (/\buntil\s+\d{4}-/.test(fact)) {
      const until = fact.match(/\buntil (\d{4}-\d{2}-\d{2})\.?$/)?.[1];
      requireThat(until && validDate(until), 'expiry requires a final until YYYY-MM-DD');
    }
  }
}

function readText(file) {
  try { return new TextDecoder('utf-8', { fatal: true }).decode(fs.readFileSync(file)); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

function points(text) { return [...text].length; }

function saveBytes(workspace, folder, bytes) {
  const raw = Buffer.isBuffer(bytes) ? bytes : Buffer.from(String(bytes));
  const dir = path.join(runtimeFolder(workspace), folder);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${randomUUID()}.bin`);
  fs.writeFileSync(file, raw, { mode: 0o600 });
  requireThat(fs.readFileSync(file).equals(raw), 'durable bytes were not preserved');
  return file;
}

function saveRejected(workspace, bytes) { return saveBytes(workspace, 'dreamer-rejected', bytes); }

function retainIndivisible(workspace, relative, record) {
  requireThat(typeof record === 'string' && record.length > 0, 'indivisible record required');
  const file = saveBytes(workspace, 'dreamer-oversized', Buffer.from(`oversized indivisible\nsource: ${relative}\nretained whole\n\n${record}`, 'utf8'));
  const saved = fs.readFileSync(file, 'utf8');
  requireThat(saved.endsWith(record) && saved.includes(record), 'oversized record was trimmed');
  return file;
}

function relieveKnowledge(workspace) {
  const paths = [];
  for (const name of ['facts', 'preferences', 'decisions', 'self', 'health']) {
    const relative = `.rbtv/memory/knowledge/${name}.md`;
    let file;
    try { file = safePath(workspace, relative); } catch { continue; }
    const text = readText(file);
    if (text == null || nonemptyLines(text).length < SPLIT_LINES) continue;
    const rows = records('knowledge', text);
    const huge = rows.find((row) => nonemptyLines(row).length >= SPLIT_LINES);
    if (huge) { retainIndivisible(workspace, relative, huge); continue; }
    if (rows.length < 2) continue;
    const ending = text.includes('\r\n') ? '\r\n' : '\n';
    const without = (drop) => {
      let next = text.split(/\r?\n/).filter((line) => !drop.includes(line)).join(ending);
      if (text.endsWith(ending) && !next.endsWith(ending)) next += ending;
      return next;
    };
    const moved = [];
    for (let i = rows.length - 1; i > 0; i--) {
      const trial = [...moved, rows[i]];
      const source = without(trial);
      const dest = `---\ndescription: when reviewing ${name}\ntype: ${name}\naliases: [${name}]\n---\n# ${name}\n\n${trial.slice().reverse().join('\n')}\n`;
      if (nonemptyLines(dest).length >= SPLIT_LINES) break;
      moved.push(rows[i]);
      if (nonemptyLines(source).length < SPLIT_LINES) break;
    }
    if (!moved.length || nonemptyLines(without(moved)).length >= SPLIT_LINES) continue;
    const source = without(moved);
    let slug = 'part-1';
    let n = 1;
    while (readText(safePath(workspace, `.rbtv/memory/knowledge/${name}/${slug}.md`))) slug = `part-${++n}`;
    const destRelative = `.rbtv/memory/knowledge/${name}/${slug}.md`;
    const dest = `---\ndescription: when reviewing ${name}\ntype: ${name}\naliases: [${name}]\n---\n# ${name}\n\n${moved.slice().reverse().join('\n')}\n`;
    const before = records('knowledge', text);
    const after = [...records('knowledge', source), ...records('knowledge', dest)];
    if (before.length !== after.length || before.some((row) => !after.includes(row))) continue;
    const original = saveBytes(workspace, 'dreamer-originals', Buffer.from(text, 'utf8'));
    requireThat(fs.readFileSync(original).equals(Buffer.from(text, 'utf8')), 'original bytes were not preserved');
    checkFile(relative, 'knowledge', source);
    checkFile(destRelative, 'knowledge', dest);
    writeText(file, source);
    writeText(safePath(workspace, destRelative), dest);
    const index = '.rbtv/memory/_artifacts/index.md';
    const row = `| [${name} ${slug}](../knowledge/${name}/${slug}.md) | when reviewing split ${name}. |`;
    let indexText = readText(safePath(workspace, index)) || '# Memory\n\n| Open | When |\n|---|---|\n';
    if (!indexText.includes(row)) indexText = `${indexText.endsWith('\n') ? indexText : `${indexText}\n`}${row}\n`;
    checkFile(index, 'index', indexText);
    writeText(safePath(workspace, index), indexText);
    paths.push(relative, destRelative, index);
  }
  if (!paths.length) return [];
  git(workspace, ['add', '--', ...paths]);
  git(workspace, ['commit', '-F', '-', '--', ...paths], `Split on-demand knowledge\n\n${[...new Set(paths)].join('\n')}\n`);
  return paths;
}

function snapshot(workspace, agents) {
  const files = new Map();
  function walk(relative, slug) {
    const folder = safePath(workspace, relative);
    for (const entry of fs.readdirSync(folder, { withFileTypes: true })) {
      // Runtime recovery copies are not memory records. Never follow symlinks.
      if (entry.name === '4-archives') continue;
      const name = `${relative}/${entry.name}`;
      if (entry.isDirectory()) walk(name, slug);
      else if (entry.name.endsWith('.md')) {
        const kind = kindOf(name, slug);
        // Migration leaves legacy pointers in place; they are neither evidence
        // nor writable memory in the ruled layout.
        if (!kind) continue;
        const text = readText(safePath(workspace, name));
        checkFile(name, kind, text);
        files.set(name, text);
      }
    }
  }
  walk(GENERAL.slice(0, -1), agents[0]?.slug);
  for (const { slug } of agents) {
    walk(`.rbtv/agents/${slug}/memory`, slug);
    const board = `.rbtv/agents/${slug}/_artifacts/board.md`;
    const text = readText(safePath(workspace, board));
    checkFile(board, 'board', text);
    files.set(board, text);
    requireThat(files.has(`.rbtv/agents/${slug}/memory/learned.md`), 'learned rules missing');
  }
  requireThat(files.has(`${GENERAL}inbox.md`) && files.has(`${GENERAL}profile.md`), 'general memory missing');
  return files;
}

function threadKey(url) {
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== 'slack.com' && !parsed.hostname.endsWith('.slack.com')) return null;
    const match = parsed.pathname.match(/^\/archives\/([A-Z0-9]+)\/p(\d+)$/);
    if (!match) return null;
    const root = parsed.searchParams.get('thread_ts')?.replace('.', '') || match[2];
    return `${match[1]}:${root}`;
  } catch { return null; }
}

function links(text) { return [...text.matchAll(/\[[^\]]+\]\((https?:\/\/[^\s]+?)\)/g)].map((match) => match[1]); }
function provenance(text) { return text.match(/^.* \(\d{4}-\d{2}-\d{2} · (.+)\)$/)?.[1] || ''; }

function parseProposal(value) {
  if (typeof value === 'string') {
    try { value = JSON.parse(value.trim().replace(/^```(?:json)?\s*\n([\s\S]*?)\n```$/, '$1')); }
    catch { throw new Refusal('model did not return JSON'); }
  }
  requireThat(value && Array.isArray(value.operations) && Array.isArray(value.conflicts), 'proposal requires operations and conflicts arrays');
  requireThat(value.conflicts.every((line) => typeof line === 'string' && line.trim()), 'invalid conflict');
  return value;
}

function validateProposal(input, raw, workspace) {
  const proposal = parseProposal(raw);
  const before = new Map(Object.entries(input.files));
  const after = new Map(before);
  const operations = new Map();
  const evidence = new Map(input.messages.map((row) => [row.rowid, row]));
  const inbox = new Set(records('inbox', before.get(`${GENERAL}inbox.md`)).filter((line) =>
    provenance(line) === input.agent || provenance(line).startsWith(`${input.agent}/`)));
  const failures = [];
  const guard = (fn) => { try { return fn(); } catch (error) { if (!(error instanceof Refusal)) throw error; failures.push(...(error.failures && error.failures.length ? error.failures : [fromMessage(error.message, { path: error.path || null })])); return null; } };
  for (const op of proposal.operations) guard(() => {
    requireThat(op && ['add', 'supersede', 'archive'].includes(op.op), 'invalid operation');
    safePath(workspace, op.path);
    const kind = kindOf(op.path, input.agent);
    requireThat(kind && !operations.has(op.path), 'path outside agent memory or repeated operation');
    requireThat(REASONS.includes(op.reason) && typeof op.explanation === 'string' && op.explanation.trim(), 'operation requires a reason and explanation');
    requireThat(Array.isArray(op.sources) && op.sources.every((id) =>
      Number.isSafeInteger(id) ? evidence.has(id) : typeof id === 'string' && inbox.has(id)),
    'source is not an unread owner message or this agent\'s inbox line');
    requireThat(typeof op.text === 'string', 'operation requires complete file text');
    requireThat(op.op === 'add' ? !before.has(op.path) : before.has(op.path), 'add requires a new file; other operations require an existing file');
    const text = normalize(op.text).replace(/\n/g, before.get(op.path)?.includes('\r\n') ? '\r\n' : '\n');
    checkFile(op.path, kind, text);
    after.set(op.path, text);
    operations.set(op.path, { ...op, text, kind, agent: input.agent });
  });
  for (const op of operations.values()) guard(() => {
    const previous = before.has(op.path) ? records(op.kind, before.get(op.path)) : [];
    const next = records(op.kind, op.text);
    const removed = [...new Set(previous.filter((row) => !next.includes(row)))];
    const added = next.filter((row) => !previous.includes(row));
    const removals = op.removals || [];
    requireThat(Array.isArray(removals) && removals.length === removed.length && new Set(removals.map((item) => item.text)).size === removed.length &&
      removed.every((row) => removals.some((item) => item.text === row)), 'no record may vanish unexplained');
    requireThat(new Set(next).size === next.length, 'duplicate memory record');
    if (op.kind === 'board') {
      const old = parseBoard(before.get(op.path));
      const board = parseBoard(op.text);
      requireThat(JSON.stringify(board.timers) === JSON.stringify(old.timers) && board.subjects.length === old.subjects.length &&
        board.subjects.every((subject) => old.subjects.some((prior) => prior.title === subject.title && prior.threads === subject.threads && prior.flags === subject.flags)) &&
        board.watchOuts.every((row) => old.watchOuts.includes(row)) && board.closed.every((row) => old.closed.includes(row)), 'dreamer cannot create or close subjects or edit runtime board fields');
    }
    const rows = op.sources.filter((id) => Number.isSafeInteger(id)).map((id) => evidence.get(id));
    if (op.op === 'archive') requireThat(removed.length > 0 && added.length === 0, 'archive only removes records into a destination');
    const conversations = new Set(rows.map((row) => row.conversation_key));
    const sourceThreads = new Set(rows.map((row) => threadKey(row.thread)).filter(Boolean));
    for (const record of added) {
      if (['board', 'index', 'workstreams'].includes(op.kind) || /^(?:Periodic note:|Week:|Threads:|- (?:Vault|Glossary|Shared docs):)/.test(record)) continue;
      const filed = ['profile', 'knowledge', 'entity'].includes(op.kind) &&
        (operations.get(`${GENERAL}inbox.md`)?.removals || []).some((item) =>
          inbox.has(item.text) && op.sources.includes(item.text) && item.to === op.path &&
          item.replacement === record && provenance(item.text) === provenance(record));
      if (filed) continue;
      // Exact relocation is preservation, not new evidence. The source operation
      // below must account for the old record and its destination.
      const relocated = [...operations.values()].some((other) => (other.removals || []).some((item) => item.text === record && item.to === op.path));
      if (relocated && op.kind !== 'learned') continue;
      const preservedState = op.kind === 'topic' && [...operations.values()].some((other) =>
        other.kind === 'board' && other.reason === 'detail' &&
        provenance(record) === path.posix.relative(path.posix.dirname(op.path), other.path) &&
        (other.removals || []).some((item) => item.to === op.path &&
          parseBoard(before.get(other.path)).subjects.some((subject) => item.text.startsWith(`### ${subject.title}\n`) &&
            subject.state.includes(recordBody(record.replace(/^- /, ''))))));
      if (preservedState) continue;
      requireThat(rows.length > 0, 'new facts require owner evidence');
      if (op.kind === 'weekly') {
        const target = record.match(/\]\((\.\.\/daily\/\d{4}-\d{2}-\d{2}\.md)\)$/)?.[1];
        const daily = target && after.get(path.posix.normalize(path.posix.join(path.posix.dirname(op.path), target)));
        requireThat(daily && links(daily).some((url) => sourceThreads.has(threadKey(url))), 'weekly source must link a daily file backed by owner messages');
        continue;
      }
      const tail = op.kind === 'daily' ? record.slice(record.lastIndexOf(' — ') + 3) : provenance(record);
      const cited = links(tail);
      requireThat(cited.length > 0 && cited.every((url) => sourceThreads.has(threadKey(url))) &&
        tail.split(' · ').every((part) => part.startsWith(`${input.agent}/`)), 'record provenance must cite its owner conversations');
      if (op.kind === 'learned' && record.startsWith('- [inferred]')) {
        requireThat(conversations.size >= 2 && new Set(cited.map(threadKey)).size >= 2, 'inferred rules need two separate owner conversations');
      }
    }
    for (const item of removals) {
      if (item.duplicate) requireThat(item.duplicate === true && op.op === 'supersede' &&
        (op.kind === 'inbox' || (op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text))),
      'only inbox lines and watch-outs may be removed as duplicates');
      if (op.reason === 'expired') {
        const until = recordBody(item.text).match(/\buntil (\d{4}-\d{2}-\d{2})\.?$/)?.[1];
        requireThat(until && validDate(until) && until < input.date && op.kind !== 'learned', 'only an explicit past until date expires');
      }
      if (item.to) {
        safePath(workspace, item.to);
        requireThat(item.to !== op.path && kindOf(item.to, input.agent) && after.has(item.to), 'removal destination missing');
      }
      if (op.op === 'archive') {
        requireThat(op.kind !== 'inbox' && !(op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text)), 'inbox and watch-outs must be filed or folded');
        requireThat(['expired', 'closed', 'owner'].includes(op.reason), 'archive requires expiry, closure or owner evidence');
        requireThat(item.to && records(kindOf(item.to, input.agent), after.get(item.to)).includes(item.text), 'archived records must be preserved verbatim');
        if (op.reason === 'closed') requireThat(op.kind === 'board' && parseBoard(before.get(op.path)).closed.includes(item.text), 'only closed board records may be pruned as closed');
        if (op.reason === 'owner') requireThat(rows.length, 'archive requires owner evidence');
      } else if (op.kind === 'inbox' || (op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text))) {
        const destinationKind = item.to && kindOf(item.to, input.agent);
        requireThat(op.reason === (op.kind === 'inbox' ? 'file' : 'fold'), 'inbox and watch-outs must be filed or folded');
        requireThat(op.kind === 'inbox' ? ['profile', 'knowledge', 'entity'].includes(destinationKind) : destinationKind === 'learned', 'incorrect filing destination');
        requireThat(typeof item.replacement === 'string' && records(destinationKind, after.get(item.to)).includes(item.replacement), 'filed record missing at destination');
        if (item.duplicate) {
          requireThat(before.has(item.to) && records(destinationKind, before.get(item.to)).includes(item.replacement), 'duplicate record missing from snapshot');
          requireThat(op.kind !== 'inbox' || (inbox.has(item.text) && op.sources.includes(item.text)), 'duplicate inbox removal requires its own source');
          continue;
        }
        if (op.kind === 'board' && links(provenance(item.text)).length === 0) {
          const date = item.text.match(/ \((\d{4}-\d{2}-\d{2}) · .+\)$/)[1];
          const replacement = item.replacement.match(/^- \[correction\] .+ Why: .+ \((\d{4}-\d{2}-\d{2}) · (.+)\)$/);
          requireThat(replacement && replacement[1] === date && replacement[2].split(' · ').every((part) => {
            const source = part.match(/^([a-z0-9-]+)\/\[[^\]]+\]\((https?:\/\/[^\s]+?)\)$/);
            return source && source[1] === input.agent && sourceThreads.has(threadKey(source[2]));
          }), 'watch-out replacement requires its original date and owner thread evidence');
        } else requireThat(provenance(item.text) === provenance(item.replacement), 'filing must retain provenance');
        if (op.kind === 'board') requireThat(item.replacement.startsWith('- [correction]'), 'watch-outs become correction rules');
        requireThat((op.kind === 'inbox' && inbox.has(item.text) && op.sources.includes(item.text)) ||
          (rows.length && links(provenance(item.text)).every((url) => sourceThreads.has(threadKey(url)))), 'filing requires owner evidence');
      } else if (op.kind === 'board') {
        const old = parseBoard(before.get(op.path));
        const subject = old.subjects.find((row) => item.text.startsWith(`### ${row.title}\n`));
        requireThat(subject && op.reason === 'detail' && item.to?.startsWith(`.rbtv/agents/${input.agent}/memory/`) &&
          kindOf(item.to, input.agent) === 'topic' && /^type: subject\r?$/m.test(after.get(item.to)) &&
          records('topic', after.get(item.to)).includes(`Threads: ${subject.threads}`) &&
          subject.state.every((line) => records('topic', after.get(item.to)).some((record) => record.includes(line))), 'subject detail must be preserved in an agent topic');
        const nextSubject = parseBoard(op.text).subjects.find((row) => row.title === subject.title);
        requireThat(nextSubject.detail === `../memory/${item.to.split('/memory/')[1]}`, 'board must link moved detail');
      } else {
        requireThat(op.op === 'supersede' && ['owner', 'merge', 'index'].includes(op.reason) &&
          (op.kind === 'index' || rows.length > 0) && added.length > 0, 'replacement needs owner evidence and a replacement record');
      }
    }
    if (removed.length && before.get(op.path)?.includes('- [') && op.kind === 'learned') {
      proposal.conflicts.push(`Changed learned rules for ${input.agent}: ${op.explanation}`);
    }
  });
  if (failures.length) throw refusalError(failures);
  const boardPath = `.rbtv/agents/${input.agent}/_artifacts/board.md`;
  const ownerThreads = new Set(input.messages.map((row) => threadKey(row.thread)).filter(Boolean));
  for (const watch of parseBoard(after.get(boardPath)).watchOuts) {
    const cited = links(provenance(watch));
    const foldable = ownerThreads.size > 0 && cited.every((url) => ownerThreads.has(threadKey(url)));
    requireThat(!foldable, 'all watch-outs must be folded in this run');
    proposal.conflicts.push(`Watch-out for ${input.agent} awaits owner thread evidence: ${watch}`);
  }
  return { files: after, operations: [...operations.values()], conflicts: proposal.conflicts };
}

function gitFailure(result) {
  const text = stripVTControlCharacters(`${result.stderr || ''}\n${result.stdout || ''}`);
  if (/index\.lock/i.test(text)) return 'index lock';
  if (/nothing to commit|no changes added to commit/i.test(text)) return 'nothing to commit';
  return 'other';
}

function git(workspace, args, input, statuses = [0]) {
  const result = require('node:child_process').spawnSync('git', ['--literal-pathspecs', '-C', workspace, ...args],
    { input, encoding: 'utf8', windowsHide: true, timeout: 30_000, maxBuffer: 8 * 1024 * 1024 });
  requireThat(!result.error && statuses.includes(result.status),
    `git ${args[0]} failed${args[0] === 'commit' ? ` (${gitFailure(result)})` : ''}`);
  return result;
}

function writeText(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let fd;
  try { fd = fs.openSync(file, 'r+'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; fd = fs.openSync(file, 'wx', 0o600); }
  try { fs.writeFileSync(fd, text, 'utf8'); fs.ftruncateSync(fd, Buffer.byteLength(text, 'utf8')); }
  finally { fs.closeSync(fd); }
}

function validateProposalResult(input, raw, workspace) {
  try {
    const published = validateProposal(input, raw, workspace);
    return { ok: true, failures: [], files: published.files, operations: published.operations, conflicts: published.conflicts };
  } catch (error) {
    if (!(error instanceof Refusal)) throw error;
    return { ok: false, failures: error.failures && error.failures.length ? error.failures : [fromMessage(error.message)], files: null, operations: [], conflicts: [] };
  }
}

function publishProposal(input, raw, workspace, { gitCommit = git, write = writeText } = {}) {
  const validated = validateProposalResult(input, raw, workspace);
  if (!validated.ok) {
    const retained = saveRejected(workspace, Buffer.from(typeof raw === 'string' ? raw : JSON.stringify(raw ?? '')));
    return { ...validated, published: false, retained };
  }
  const release = acquireMemoryLock(workspace);
  try {
    const written = [];
    for (const op of validated.operations) {
      const file = safePath(workspace, op.path);
      write(file, op.text);
      written.push(op.path);
    }
    if (written.length) {
      gitCommit(workspace, ['add', '--', ...written]);
      gitCommit(workspace, ['commit', '-F', '-', '--', ...written], `Publish memory\n\n${written.join('\n')}\n`);
    }
    return { ...validated, published: true, covered: written, commit: written.length ? gitCommit(workspace, ['rev-parse', 'HEAD']).stdout.trim() : null };
  } finally { release(); }
}

module.exports = {
  Refusal, requireThat, GENERAL, safePath, kindOf, bodyOf, recordBody, records, validDate,
  fileSizes, checkFile, readText, points, saveBytes, saveRejected, retainIndivisible, relieveKnowledge,
  snapshot, threadKey, links, provenance, parseProposal, validateProposal, validateProposalResult,
  publishProposal, nonempty, git, writeText,
};

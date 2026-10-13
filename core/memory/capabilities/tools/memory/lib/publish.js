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
let pendingForm = null;
function requireThat(ok, message) {
  const form = pendingForm;
  pendingForm = null;
  if (!ok) {
    const error = new Refusal(message);
    if (form) error.form = form;
    throw error;
  }
}
function expect(form) { pendingForm = form; }

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

function checkFile(relative, kind, text, place = {}) {
  const found = [];
  const filePath = place.path || relative;
  const fileOp = Object.prototype.hasOwnProperty.call(place, 'operation') ? place.operation : null;
  function keep(error, fallback) {
    if (!(error instanceof Refusal)) throw error;
    const requirement = error.message;
    const expected = error.form || fallback;
    if (found.some((row) => row.path === filePath && row.requirement === requirement)) return;
    found.push(failure({ path: filePath, operation: fileOp, requirement, expected, reason: requirement }));
  }
  function collect(fn, fallback) {
    try { fn(); return true; }
    catch (error) { keep(error, fallback); return false; }
  }
  const textForm = 'UTF-8 text, LF or CRLF lines, no NUL and no [[';
  expect(textForm);
  if (!collect(() => requireThat(typeof text === 'string' && !/[\x00\r]/.test(text.replace(/\r\n/g, '')) && !text.includes('[['), 'invalid memory text'), textForm)) {
    throw refusalError(found);
  }
  let capped = false;
  for (const { count, cap, unit } of fileSizes(kind, text)) {
    const capForm = `at most ${cap} ${unit}`;
    expect(capForm);
    if (!collect(() => requireThat(cap == null || count <= cap, `${relative}: ${kind} cap exceeded (${count}/${cap} ${unit})`), capForm)) capped = true;
  }
  let shaped = true;
  if (['board', 'learned', 'profile', 'inbox', 'index', 'workspace'].includes(kind)) {
    if (capped) shaped = false;
    else {
      try { checkMemory(kind, text); }
      catch (error) {
        shaped = false;
        const forms = {
          board: '## What matters now, ## Watch-outs, ## Timers, ## Recently closed',
          learned: '# Learned rules — Name and dated rule bullets',
          profile: '# Profile — Name, ## Who, ## Working with Name, ## Now, at most 4000 code points',
          inbox: '# Inbox and one dated bullet per line',
          index: 'a heading and an | Open | When | table',
          workspace: 'type: workspace, one paths list, a heading, dated bullets',
        };
        found.push(failure({ path: filePath, operation: fileOp, requirement: error.message, expected: forms[kind], reason: error.message }));
      }
    }
  } else {
    const front = normalize(text).match(/^---\n([\s\S]*?)\n---\n/);
    const headingForm = 'frontmatter description: when ... and a # heading';
    expect(headingForm);
    collect(() => requireThat(front && /^description: when .+$/m.test(front[1]) && /^# \S/m.test(bodyOf(text)), `${kind} requires description and heading`), headingForm);
    if (front && !['daily', 'weekly', 'workstreams'].includes(kind)) {
      const type = front[1].match(/^type: (\S+)$/m)?.[1];
      const expectedType = kind === 'entity' ? ({ people: 'person', orgs: 'org', places: 'place', devices: 'device' })[relative.split('/').at(-2)] :
        kind === 'knowledge' ? (relative.split('/').at(-2) === 'knowledge' ? path.posix.basename(relative, '.md') : relative.split('/').at(-2)) : null;
      const typeForm = expectedType ? `type: ${expectedType}` : 'type: subject, procedure or reference';
      expect(typeForm);
      collect(() => requireThat(expectedType ? type === expectedType : ['subject', 'procedure', 'reference'].includes(type), `${kind} type refused`), typeForm);
      const aliasForm = 'aliases: [name]';
      expect(aliasForm);
      collect(() => requireThat(/^aliases: \[.*\]$/m.test(front[1]), `${kind} aliases required`), aliasForm);
      if (kind === 'topic' && type === 'subject') {
        const threads = nonempty(bodyOf(text)).filter((line) => line.startsWith('Threads: '));
        const threadForm = 'Threads: none or Threads: [label](https://...)';
        expect(threadForm);
        collect(() => requireThat(threads.length === 1 && /^Threads: (?:none|\[[^\]]+\]\(https?:\/\/\S+\)(?: · \[[^\]]+\]\(https?:\/\/\S+\))*)$/.test(threads[0]), 'subject topics require Threads'), threadForm);
      }
    }
    const rows = records(kind, text);
    if (kind === 'daily' || kind === 'weekly') {
      const stem = path.posix.basename(relative, '.md');
      const dateForm = kind === 'daily' ? 'a file name YYYY-MM-DD' : 'a file name YYYY-Www';
      expect(dateForm);
      collect(() => requireThat(kind === 'daily' ? validDate(stem) : /^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$/.test(stem), 'invalid timeline date'), dateForm);
      const rowForm = 'an episode line or a link, not a dated fact';
      for (const row of rows) {
        expect(rowForm);
        collect(() => requireThat(/^(?:Periodic note: |Week: )?\[[^\]]+\]\([^)]+\)$/.test(row) ||
          (kind === 'daily' ? /^- .+ — [a-z0-9-]+\/\[[^\]]+\]\(https?:\/\/[^\s]+\)$/.test(row) :
            /^- .+ — \[\d{4}-\d{2}-\d{2}\]\(\.\.\/daily\/\d{4}-\d{2}-\d{2}\.md\)$/.test(row)), 'timeline must contain episodes and links only'), rowForm);
      }
    } else if (kind === 'workstreams') {
      const pointerForm = 'each line is a pointer with [board](...) or board: none';
      expect(pointerForm);
      collect(() => requireThat(rows.every((row) => /^- .+(?:\[board\]\([^)]+\)|board: none)$/.test(row)), 'workstreams requires pointers'), pointerForm);
    } else {
      const datedForm = '- text (YYYY-MM-DD · provenance)';
      for (const row of rows) {
        if (/^(?:Threads: |(?:- )?(?:Vault|Glossary|Shared docs): )/.test(row)) continue;
        const record = row.match(/^(?:- |\d+\. ).+ \((\d{4}-\d{2}-\d{2}) · .+\)$/);
        expect(datedForm);
        collect(() => requireThat(record && validDate(record[1]), 'records require dated provenance'), datedForm);
      }
    }
  }
  if (kind !== 'board' || shaped) {
    const dated = kind === 'board' ? (() => {
      const board = parseBoard(text);
      return [...board.subjects.flatMap((subject) => subject.state), ...board.watchOuts, ...board.closed];
    })() : records(kind, text);
    const untilForm = 'the fact ends until YYYY-MM-DD';
    for (const row of dated) {
      const fact = recordBody(row);
      if (/\buntil\s+\d{4}-/.test(fact)) {
        const until = fact.match(/\buntil (\d{4}-\d{2}-\d{2})\.?$/)?.[1];
        expect(untilForm);
        collect(() => requireThat(until && validDate(until), 'expiry requires a final until YYYY-MM-DD'), untilForm);
      }
    }
  }
  if (found.length) throw refusalError(found);
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
    catch {
      throw new Refusal('model did not return JSON', [failure({
        path: null, operation: null, requirement: 'model did not return JSON',
        expected: 'one JSON object with operations and conflicts arrays', reason: 'model did not return JSON',
      })]);
    }
  }
  return value;
}

function proposalShape(value) {
  const rows = [];
  const operationsReadable = !!(value && Array.isArray(value.operations));
  const conflictsArray = !!(value && Array.isArray(value.conflicts));
  try { requireThat(operationsReadable && conflictsArray, 'proposal requires operations and conflicts arrays'); }
  catch (error) {
    if (!(error instanceof Refusal)) throw error;
    rows.push(failure({
      path: null, operation: null, requirement: error.message,
      expected: 'operations: array; conflicts: array', reason: error.message,
    }));
  }
  if (conflictsArray) {
    try { requireThat(value.conflicts.every((line) => typeof line === 'string' && line.trim()), 'invalid conflict'); }
    catch (error) {
      if (!(error instanceof Refusal)) throw error;
      rows.push(failure({
        path: null, operation: null, requirement: error.message,
        expected: 'each conflict is one non-empty string', reason: error.message,
      }));
    }
  }
  return { operationsReadable, failures: rows };
}

function validateProposal(input, raw, workspace) {
  const proposal = parseProposal(raw);
  const shape = proposalShape(proposal);
  const before = new Map(Object.entries(input.files || {}));
  const after = new Map(before);
  const operations = new Map();
  const evidence = new Map((input.messages || []).map((row) => [row.rowid, row]));
  const inboxText = before.get(`${GENERAL}inbox.md`);
  const inbox = new Set(inboxText == null ? [] : records('inbox', inboxText).filter((line) =>
    provenance(line) === input.agent || provenance(line).startsWith(`${input.agent}/`)));
  const failures = [...shape.failures];
  function taken(error, place) {
    if (!(error instanceof Refusal)) throw error;
    const rows = error.failures && error.failures.length ? error.failures : [failure({
      path: place.path ?? null,
      operation: place.operation ?? null,
      requirement: error.message,
      expected: error.form || place.expected,
      reason: error.message,
    })];
    for (const row of rows) {
      failures.push({
        path: row.path || place.path || null,
        operation: row.operation || place.operation || null,
        requirement: row.requirement,
        expected: row.expected && row.expected !== row.reason ? row.expected : (error.form && error.form !== row.reason ? error.form : row.expected),
        reason: row.reason,
      });
    }
  }
  const guard = (fn, place = {}) => {
    try { return fn(); }
    catch (error) { taken(error, place); return null; }
  };
  if (shape.operationsReadable) for (const [index, op] of proposal.operations.entries()) {
    pendingForm = null;
    const operation = op && typeof op.op === 'string' ? `${index} ${op.op}` : String(index);
    const opPath = op && typeof op.path === 'string' ? op.path : null;
    const place = { path: opPath, operation };
    const opOk = guard(() => {
      expect('op is add, supersede or archive');
      requireThat(op && ['add', 'supersede', 'archive'].includes(op.op), 'invalid operation');
    }, { ...place, expected: 'op is add, supersede or archive' });
    let pathOk = false;
    if (opPath) {
      try { safePath(workspace, op.path); pathOk = true; }
      catch (error) {
        taken(error, { ...place, expected: 'a relative path with no empty part, .., symlink, or device name' });
      }
    } else {
      guard(() => {
        expect('a non-empty installation-relative path');
        requireThat(false, 'path required');
      }, { path: null, operation, expected: 'a non-empty installation-relative path' });
    }
    let kind = null;
    if (pathOk) {
      kind = kindOf(op.path, input.agent);
      const outside = !kind;
      const repeated = operations.has(op.path);
      if (guard(() => {
        expect(outside ? 'a path of a memory kind for this agent' : 'one operation for this path');
        requireThat(kind && !repeated, 'path outside agent memory or repeated operation');
      }, { ...place, expected: outside ? 'a path of a memory kind for this agent' : 'one operation for this path' }) === null) kind = null;
    }
    const fields = op && typeof op === 'object';
    let fieldsOk = fields;
    if (fields) {
      const reasonForm = 'reason is owner, merge, file, fold, detail, closed, expired or index, and explanation is a non-empty string';
      if (guard(() => {
        expect(reasonForm);
        requireThat(REASONS.includes(op.reason) && typeof op.explanation === 'string' && op.explanation.trim(), 'operation requires a reason and explanation');
      }, { ...place, expected: reasonForm }) === null) fieldsOk = false;
      const sourceForm = 'sources are unread owner message rowids or this agent\'s exact inbox lines';
      if (guard(() => {
        expect(sourceForm);
        requireThat(Array.isArray(op.sources) && op.sources.every((id) =>
          Number.isSafeInteger(id) ? evidence.has(id) : typeof id === 'string' && inbox.has(id)),
        'source is not an unread owner message or this agent\'s inbox line');
      }, { ...place, expected: sourceForm }) === null) fieldsOk = false;
      const textForm = 'text is the complete next file, as a string';
      if (guard(() => {
        expect(textForm);
        requireThat(typeof op.text === 'string', 'operation requires complete file text');
      }, { ...place, expected: textForm }) === null) fieldsOk = false;
    }
    const textOk = fields && typeof op.text === 'string';
    let presentOk = opOk !== null;
    if (pathOk && kind && opOk !== null) {
      const presence = op.op === 'add' ? 'a path absent from the snapshot' : 'a path present in the snapshot';
      presentOk = guard(() => {
        expect(presence);
        requireThat(op.op === 'add' ? !before.has(op.path) : before.has(op.path), 'add requires a new file; other operations require an existing file');
      }, { ...place, expected: presence }) !== null;
    }
    if (pathOk && kind && textOk) {
      const text = normalize(op.text).replace(/\n/g, before.get(op.path)?.includes('\r\n') ? '\r\n' : '\n');
      const fileOk = guard(() => checkFile(op.path, kind, text, { path: op.path, operation }), place) !== null;
      if (fieldsOk && presentOk && opOk !== null && fileOk) {
        after.set(op.path, text);
        operations.set(op.path, { ...op, text, kind, agent: input.agent, index });
      }
    }
  }
  for (const op of operations.values()) guard(() => {
    const previous = before.has(op.path) ? records(op.kind, before.get(op.path)) : [];
    const next = records(op.kind, op.text);
    const removed = [...new Set(previous.filter((row) => !next.includes(row)))];
    const added = next.filter((row) => !previous.includes(row));
    const removals = op.removals || [];
    expect('removals names each removed record verbatim');
    requireThat(Array.isArray(removals) && removals.length === removed.length && new Set(removals.map((item) => item.text)).size === removed.length &&
      removed.every((row) => removals.some((item) => item.text === row)), 'no record may vanish unexplained');
    expect('each record once');
    requireThat(new Set(next).size === next.length, 'duplicate memory record');
    if (op.kind === 'board') {
      const old = parseBoard(before.get(op.path));
      const board = parseBoard(op.text);
      expect('the same subjects, timers, flags, watch-outs and closed entries');
      requireThat(JSON.stringify(board.timers) === JSON.stringify(old.timers) && board.subjects.length === old.subjects.length &&
        board.subjects.every((subject) => old.subjects.some((prior) => prior.title === subject.title && prior.threads === subject.threads && prior.flags === subject.flags)) &&
        board.watchOuts.every((row) => old.watchOuts.includes(row)) && board.closed.every((row) => old.closed.includes(row)), 'dreamer cannot create or close subjects or edit runtime board fields');
    }
    const rows = op.sources.filter((id) => Number.isSafeInteger(id)).map((id) => evidence.get(id));
    if (op.op === 'archive') {
      expect('archive removes records and adds none');
      requireThat(removed.length > 0 && added.length === 0, 'archive only removes records into a destination');
    }
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
      expect('sources include an unread owner message');
      requireThat(rows.length > 0, 'new facts require owner evidence');
      if (op.kind === 'weekly') {
        const target = record.match(/\]\((\.\.\/daily\/\d{4}-\d{2}-\d{2}\.md)\)$/)?.[1];
        const daily = target && after.get(path.posix.normalize(path.posix.join(path.posix.dirname(op.path), target)));
        expect('a weekly line linking a daily file cited by an owner message');
        requireThat(daily && links(daily).some((url) => sourceThreads.has(threadKey(url))), 'weekly source must link a daily file backed by owner messages');
        continue;
      }
      const tail = op.kind === 'daily' ? record.slice(record.lastIndexOf(' — ') + 3) : provenance(record);
      const cited = links(tail);
      expect('provenance cites this agent and the owner conversation URLs in sources');
      requireThat(cited.length > 0 && cited.every((url) => sourceThreads.has(threadKey(url))) &&
        tail.split(' · ').every((part) => part.startsWith(`${input.agent}/`)), 'record provenance must cite its owner conversations');
      if (op.kind === 'learned' && record.startsWith('- [inferred]')) {
        expect('an inferred rule cites two owner conversations');
        requireThat(conversations.size >= 2 && new Set(cited.map(threadKey)).size >= 2, 'inferred rules need two separate owner conversations');
      }
    }
    for (const item of removals) {
      if (item.duplicate) {
        expect('duplicate: true only on an inbox line or watch-out, with op supersede');
        requireThat(item.duplicate === true && op.op === 'supersede' &&
          (op.kind === 'inbox' || (op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text))),
        'only inbox lines and watch-outs may be removed as duplicates');
      }
      if (op.reason === 'expired') {
        const until = recordBody(item.text).match(/\buntil (\d{4}-\d{2}-\d{2})\.?$/)?.[1];
        expect('the record ends until YYYY-MM-DD and that date is before the input date');
        requireThat(until && validDate(until) && until < input.date && op.kind !== 'learned', 'only an explicit past until date expires');
      }
      if (item.to) {
        try { safePath(workspace, item.to); }
        catch (error) {
          if (!(error instanceof Refusal)) throw error;
          error.form = 'a relative path with no empty part, .., symlink, or device name';
          throw error;
        }
        expect('removals.to is a different memory path present after this proposal');
        requireThat(item.to !== op.path && kindOf(item.to, input.agent) && after.has(item.to), 'removal destination missing');
      }
      if (op.op === 'archive') {
        expect('file an inbox line or fold a watch-out; do not archive them');
        requireThat(op.kind !== 'inbox' && !(op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text)), 'inbox and watch-outs must be filed or folded');
        expect('reason expired, closed or owner');
        requireThat(['expired', 'closed', 'owner'].includes(op.reason), 'archive requires expiry, closure or owner evidence');
        expect('the destination file contains the removed record unchanged');
        requireThat(item.to && records(kindOf(item.to, input.agent), after.get(item.to)).includes(item.text), 'archived records must be preserved verbatim');
        if (op.reason === 'closed') {
          expect('a Recently closed board record');
          requireThat(op.kind === 'board' && parseBoard(before.get(op.path)).closed.includes(item.text), 'only closed board records may be pruned as closed');
        }
        if (op.reason === 'owner') {
          expect('sources include an unread owner message');
          requireThat(rows.length, 'archive requires owner evidence');
        }
      } else if (op.kind === 'inbox' || (op.kind === 'board' && parseBoard(before.get(op.path)).watchOuts.includes(item.text))) {
        const destinationKind = item.to && kindOf(item.to, input.agent);
        expect('reason file for an inbox line, fold for a watch-out');
        requireThat(op.reason === (op.kind === 'inbox' ? 'file' : 'fold'), 'inbox and watch-outs must be filed or folded');
        expect('inbox goes to profile, knowledge or an entity; a watch-out goes to learned');
        requireThat(op.kind === 'inbox' ? ['profile', 'knowledge', 'entity'].includes(destinationKind) : destinationKind === 'learned', 'incorrect filing destination');
        expect('removals.replacement is the exact record in the destination file');
        requireThat(typeof item.replacement === 'string' && records(destinationKind, after.get(item.to)).includes(item.replacement), 'filed record missing at destination');
        if (item.duplicate) {
          expect('the destination already contains that record in the snapshot');
          requireThat(before.has(item.to) && records(destinationKind, before.get(item.to)).includes(item.replacement), 'duplicate record missing from snapshot');
          expect('sources include that inbox line');
          requireThat(op.kind !== 'inbox' || (inbox.has(item.text) && op.sources.includes(item.text)), 'duplicate inbox removal requires its own source');
          continue;
        }
        if (op.kind === 'board' && links(provenance(item.text)).length === 0) {
          const date = item.text.match(/ \((\d{4}-\d{2}-\d{2}) · .+\)$/)[1];
          const replacement = item.replacement.match(/^- \[correction\] .+ Why: .+ \((\d{4}-\d{2}-\d{2}) · (.+)\)$/);
          expect('a correction rule with the same date and this agent\'s owner conversation links');
          requireThat(replacement && replacement[1] === date && replacement[2].split(' · ').every((part) => {
            const source = part.match(/^([a-z0-9-]+)\/\[[^\]]+\]\((https?:\/\/[^\s]+?)\)$/);
            return source && source[1] === input.agent && sourceThreads.has(threadKey(source[2]));
          }), 'watch-out replacement requires its original date and owner thread evidence');
        } else {
          expect('the replacement uses the removed record\'s provenance');
          requireThat(provenance(item.text) === provenance(item.replacement), 'filing must retain provenance');
        }
        if (op.kind === 'board') {
          expect('a bullet starting - [correction]');
          requireThat(item.replacement.startsWith('- [correction]'), 'watch-outs become correction rules');
        }
        expect('the inbox line is in sources, or the watch-out provenance cites owner threads in sources');
        requireThat((op.kind === 'inbox' && inbox.has(item.text) && op.sources.includes(item.text)) ||
          (rows.length && links(provenance(item.text)).every((url) => sourceThreads.has(threadKey(url)))), 'filing requires owner evidence');
      } else if (op.kind === 'board') {
        const old = parseBoard(before.get(op.path));
        const subject = old.subjects.find((row) => item.text.startsWith(`### ${row.title}\n`));
        expect('a subject topic whose Threads and state lines match the board subject');
        requireThat(subject && op.reason === 'detail' && item.to?.startsWith(`.rbtv/agents/${input.agent}/memory/`) &&
          kindOf(item.to, input.agent) === 'topic' && /^type: subject\r?$/m.test(after.get(item.to)) &&
          records('topic', after.get(item.to)).includes(`Threads: ${subject.threads}`) &&
          subject.state.every((line) => records('topic', after.get(item.to)).some((record) => record.includes(line))), 'subject detail must be preserved in an agent topic');
        const nextSubject = parseBoard(op.text).subjects.find((row) => row.title === subject.title);
        expect('Detail: ../memory/<topic file>');
        requireThat(nextSubject.detail === `../memory/${item.to.split('/memory/')[1]}`, 'board must link moved detail');
      } else {
        expect('op supersede, reason owner, merge or index, a replacement record, and owner evidence unless the file is an index');
        requireThat(op.op === 'supersede' && ['owner', 'merge', 'index'].includes(op.reason) &&
          (op.kind === 'index' || rows.length > 0) && added.length > 0, 'replacement needs owner evidence and a replacement record');
      }
    }
    if (Array.isArray(proposal.conflicts) && removed.length && before.get(op.path)?.includes('- [') && op.kind === 'learned') {
      proposal.conflicts.push(`Changed learned rules for ${input.agent}: ${op.explanation}`);
    }
  }, { path: op.path, operation: `${op.index} ${op.op}` });
  if (failures.length) throw refusalError(failures);
  const boardPath = `.rbtv/agents/${input.agent}/_artifacts/board.md`;
  const ownerThreads = new Set(input.messages.map((row) => threadKey(row.thread)).filter(Boolean));
  for (const watch of parseBoard(after.get(boardPath)).watchOuts) {
    const cited = links(provenance(watch));
    const foldable = ownerThreads.size > 0 && cited.every((url) => ownerThreads.has(threadKey(url)));
    expect('every foldable watch-out is folded or removed as a duplicate in this proposal');
    try { requireThat(!foldable, 'all watch-outs must be folded in this run'); }
    catch (error) {
      if (!(error instanceof Refusal)) throw error;
      throw refusalError([failure({
        path: boardPath, operation: null, requirement: error.message, expected: error.form, reason: error.message,
      })]);
    }
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

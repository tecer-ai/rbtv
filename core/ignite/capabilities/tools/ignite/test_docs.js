'use strict';

// Suite for docs.js: which documents the Docs tab lists, and opening and pulling the one document of a channel canvas
// against a stand-in Slack that keeps the canvas as HTML, as files.info's download does.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { recentDocs, openDocument, openDoc, pullDoc } = require('./docs.js');
const { Store } = require('./store.js');
const { main: ignite } = require('./cli.js');

const failures = [];
let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log(`PASS ${name}`); } catch (error) { failures.push(name); console.log(`FAIL ${name}: ${error.stack || error.message}`); }
}

// A channel canvas kept as the HTML Slack returns: the title as a first heading, each line a paragraph.
function canvasSlack({ existing = null } = {}) {
  const canvases = new Map();
  const channels = new Map();
  if (existing) { canvases.set('Fold', { title: 'Something else', lines: ['not ours'] }); channels.set(existing, 'Fold'); }
  const calls = [];
  const lines = (markdown) => markdown.split('\n').filter(Boolean);
  return {
    calls, canvases,
    edit(canvasId, text) { canvases.get(canvasId).lines = lines(text); },
    async channelCanvas(channel) { calls.push(['channelCanvas', channel]); return channels.get(channel) || null; },
    async canvasCreate({ channel, markdown, title }) { calls.push(['canvasCreate', channel, title]); canvases.set('Fnew', { title, lines: lines(markdown) }); channels.set(channel, 'Fnew'); return { canvasId: 'Fnew' }; },
    async canvasEdit({ canvasId, markdown }) { calls.push(['canvasEdit', canvasId]); canvases.get(canvasId).lines = lines(markdown); return { canvasId }; },
    async canvasRename({ canvasId, title }) { calls.push(['canvasRename', canvasId, title]); canvases.get(canvasId).title = title; return { canvasId }; },
    async canvasRead(canvasId) {
      const canvas = canvases.get(canvasId);
      // files.info's title lags a rename (observed 2026-10-17); the HTML heading is current, so only the heading is given.
      return { html: `<h1>${canvas.title}</h1>${canvas.lines.map((line) => `<p class="line">${line}</p>`).join('')}`, comments: 1 };
    },
  };
}

function installation() {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-docs-'));
  fs.mkdirSync(path.join(workspace, 'notes'));
  for (const [name, text] of [['notes/a.md', 'Alpha one\nAlpha two\n'], ['notes/b.md', 'Beta\n'], ['notes/c.txt', 'not markdown\n']]) fs.writeFileSync(path.join(workspace, name), text);
  const store = new Store(path.join(workspace, 'state.sqlite'));
  return { workspace, store };
}

// One finished run that reported these outputs, ending at endedAt.
function finished(store, outputs, endedAt) {
  const id = `r${endedAt}`;
  store.db.prepare("INSERT INTO conversations(key, agent, workspace, channel, root_ts, activated, updated_at) VALUES ('K', 'a', 'T1', 'C1', '1.1', 1, 0) ON CONFLICT DO NOTHING").run();
  store.db.prepare("INSERT INTO queue(id, conversation_key, kind, payload, priority, available_at, state, attempts, created_at) VALUES (?, 'K', 'owner', '{}', 0, 0, 'done', 1, 0)").run(id);
  store.db.prepare("INSERT INTO runs(id, queue_id, nonce, state, output, started_at, ended_at) VALUES (?, ?, 'n', 'finished', ?, 0, ?)").run(id, id, JSON.stringify({ outputs }), endedAt);
}

async function main() {
  await test('recentDocs lists each Markdown output inside the installation once, newest first, and nothing else', async () => {
    const { workspace, store } = installation();
    finished(store, [path.join(workspace, 'notes/a.md'), path.join(workspace, 'notes/c.txt'), '/etc/passwd.md'], 100);
    finished(store, [path.join(workspace, 'notes/b.md'), path.join(workspace, 'notes/a.md'), path.join(workspace, 'notes/gone.md')], 200);
    store.db.prepare("INSERT INTO queue(id, conversation_key, kind, payload, priority, available_at, state, attempts, created_at) VALUES ('bad', 'K', 'owner', '{}', 0, 0, 'done', 1, 0)").run();
    store.db.prepare("INSERT INTO runs(id, queue_id, nonce, state, output, started_at, ended_at) VALUES ('bad', 'bad', 'n', 'finished', 'not json', 0, 300)").run();
    assert.deepEqual(recentDocs(store, workspace), [{ path: 'notes/b.md', at: 200 }, { path: 'notes/a.md', at: 200 }]);
  });

  await test('opening creates the channel canvas with the file and its path as title, and records it', async () => {
    const { workspace, store } = installation();
    const slack = canvasSlack();
    assert.deepEqual(await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md' }), { opened: 'notes/a.md', canvasId: 'Fnew' });
    assert.deepEqual(slack.canvases.get('Fnew'), { title: 'notes/a.md', lines: ['Alpha one', 'Alpha two'] });
    const record = openDocument(store);
    assert.deepEqual([record.canvasId, record.channel, record.path, record.baseline], ['Fnew', 'C1', 'notes/a.md', 'Alpha one\n\nAlpha two\n']);
  });

  await test('an unedited canvas is replaced by the next document; an edited one is refused until pulled, or forced', async () => {
    const { workspace, store } = installation();
    const slack = canvasSlack();
    await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md' });
    assert.deepEqual(await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/b.md' }), { opened: 'notes/b.md', canvasId: 'Fnew' });
    assert.deepEqual(slack.canvases.get('Fnew'), { title: 'notes/b.md', lines: ['Beta'] });
    slack.edit('Fnew', 'Beta\nHenrique added this');
    const refused = await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md' });
    assert.equal(refused.refused, 'edited');
    assert.equal(refused.path, 'notes/b.md');
    assert.deepEqual(slack.canvases.get('Fnew').lines, ['Beta', 'Henrique added this']);
    const pulled = await pullDoc({ slack, store });
    assert.deepEqual(pulled, { path: 'notes/b.md', markdown: 'Beta\n\nHenrique added this\n', edited: true, comments: 1 });
    assert.equal((await pullDoc({ slack, store })).edited, false);
    assert.equal((await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md' })).opened, 'notes/a.md');
    slack.edit('Fnew', 'scribble');
    assert.equal((await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/b.md', force: true })).opened, 'notes/b.md');
  });

  await test('a channel canvas Ignite did not open is refused unless forced', async () => {
    const { workspace, store } = installation();
    const slack = canvasSlack({ existing: 'C1' });
    assert.equal((await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md' })).refused, 'untracked');
    assert.deepEqual(slack.canvases.get('Fold').lines, ['not ours']);
    assert.equal((await openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/a.md', force: true })).canvasId, 'Fold');
    assert.deepEqual(slack.canvases.get('Fold'), { title: 'notes/a.md', lines: ['Alpha one', 'Alpha two'] });
  });

  await test('only a Markdown file inside the installation opens, and pull with nothing open is null', async () => {
    const { workspace, store } = installation();
    const slack = canvasSlack();
    await assert.rejects(openDoc({ slack, store, workspace, channel: 'C1', path: '../outside.md' }), /not a Markdown file inside the installation/);
    await assert.rejects(openDoc({ slack, store, workspace, channel: 'C1', path: 'notes/c.txt' }), /not a Markdown file/);
    assert.equal(slack.calls.length, 0);
    assert.equal(await pullDoc({ slack, store }), null);
  });

  await test('ignite docs: list, open into the routed channel, refuse an edited canvas, pull it, and refuse an agent without a channel', async () => {
    const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-docs-cli-'));
    fs.mkdirSync(path.join(workspace, '.rbtv', 'config', 'ignite'), { recursive: true });
    fs.writeFileSync(path.join(workspace, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify({
      slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'w' },
      tools: { cast: 'cast', stools: 'stools', audio: 'audio' }, routes: { C1: 'sara' }, dmAgent: 'max',
    }));
    fs.writeFileSync(path.join(workspace, 'plan.md'), 'The plan\n');
    for (const slug of ['sara', 'max']) {
      const store = new Store(path.join(workspace, '.rbtv', 'agents', slug, 'runtime', 'ignite', 'state.sqlite'));
      finished(store, [path.join(workspace, 'plan.md')], 100);
      store.close();
    }
    const slack = canvasSlack();
    const run = async (agent, argv) => {
      const out = [];
      try {
        const code = await ignite(argv, { stdout: (text) => out.push(text), env: { RBTV_AGENT_HOME: path.join(workspace, '.rbtv', 'agents', agent) }, slack });
        return { code, out: out.join('') };
      } catch (error) {
        return { code: error.exitCode || 1, out: out.join(''), err: error.message };
      }
    };
    assert.deepEqual(JSON.parse((await run('sara', ['docs', 'list', '--json'])).out), { docs: [{ path: 'plan.md', at: 100 }], open: null });
    const opened = await run('sara', ['docs', 'open', 'plan.md']);
    assert.equal(opened.out, 'opened plan.md in the canvas Fnew of channel C1\n');
    slack.edit('Fnew', 'The plan\nwith an edit');
    const refused = await run('sara', ['docs', 'open', 'plan.md']);
    assert.equal(refused.code, 1);
    assert.match(refused.err, /^not opened: plan\.md was edited in the canvas since it was opened; bring the edits in first\n.*--force\nNothing changed\.$/s);
    const pulled = await run('sara', ['docs', 'pull']);
    assert.equal(pulled.out, 'path: plan.md\nedited: yes\ncomments: 1 (their text stays in the canvas)\n---\nThe plan\n\nwith an edit\n');
    assert.equal((await run('sara', ['docs', 'open', 'plan.md', '--json'])).code, 0);
    assert.match((await run('max', ['docs', 'open', 'plan.md'])).err, /^agent max has no channel of its own/);
    assert.match((await run('sara', ['docs', 'open'])).err, /^docs open requires the path/);
    assert.match((await run('sara', ['docs', 'drop'])).err, /^docs requires list, open or pull/);
  });

  console.log(`${passed} passed, ${failures.length} failed`);
  if (failures.length) process.exit(1);
}

main();

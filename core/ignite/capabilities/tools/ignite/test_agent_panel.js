'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createAgentPanel, agentView, TABS } = require('./agent-panel.js');
const { Store } = require('./store.js');
const { Gate } = require('./payments.js');
const { example } = require('../../../../cast/capabilities/tools/cast/example-models');

// Models by property, never by name (cast's test_route.js): the agent's model, and two worker models.
const CLAUDE = example('a claude model', (m) => m.harness === 'claude');
const WORKER = example('a codex model', (m) => m.harness === 'codex');
const OTHER = example('a second claude model', (m) => m.harness === 'claude', [CLAUDE]);

const failures = [];
let passed = 0;

async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

const OWNER = { user_id: 'UOWNER', team_id: 'T1' };
const AVATAR = 'https://example.com/fabinho.jpg';

// An installation with two agents: `developer` routed to channel C1, `master` answering direct messages.
function installation({ prompt = '# Role\n\nYou are **Fabinho**. See [docs](https://example.com/d) and [local](./x.md).\n', board = '## What matters now\n\n### Agent panel\n- State: building\n' } = {}) {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-panel-'));
  const agent = (slug, record, text) => {
    const home = path.join(workspace, '.rbtv', 'agents', slug);
    fs.mkdirSync(path.join(home, '_artifacts'), { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify(record));
    fs.writeFileSync(path.join(home, 'prompt.md'), text);
    return home;
  };
  const home = agent('developer', {
    name: 'developer', external_name: 'Fabinho', avatar: AVATAR, harness: CLAUDE.harness, model: CLAUDE.model, effort: 'medium',
    description: 'Architecture and development.', packs: ['foundations', 'ignite'],
    components: {
      'core/rbtv': { selected: { framework: { method: 'skill' }, 'agent-folder': { method: 'rule' } } },
      'core/cast': { selected: { cast: { method: 'tool' }, spark: { method: 'tool' } } },
    },
  }, prompt);
  if (board != null) fs.writeFileSync(path.join(home, '_artifacts', 'board.md'), board);
  agent('master', { name: 'master', harness: WORKER.harness, model: WORKER.model, effort: 'high' }, 'Master prompt.\n');
  const config = { workspace, routes: { C1: 'developer' }, dmAgent: 'master', slack: { ownerUserId: 'UOWNER', team: 'T1' } };
  const store = new Store(path.join(workspace, 'developer.sqlite'));
  return { workspace, home, config, store };
}

function fakeSlack({ fail = false } = {}) {
  const calls = [];
  const record = (method) => async (...args) => {
    calls.push({ method, args });
    if (fail) throw new Error('slack down');
    return { viewId: 'V1' };
  };
  return { calls, openView: record('openView'), updateView: record('updateView') };
}

function panelFor(inst, slack) {
  const logs = [];
  const panel = createAgentPanel({
    slack: () => slack,
    config: () => inst.config,
    store: (slug) => (slug === 'developer' ? inst.store : null),
    log: (entry) => logs.push(entry),
  });
  return { panel, logs };
}

const texts = (view) => view.blocks.map((block) => [block.text?.text || '', ...(block.fields || []).map((field) => field.text),
  ...(block.type === 'context' ? block.elements.map((element) => element.text) : [])].join('\n')).join('\n');
const button = (view, tab, value = tab) => ({
  type: 'block_actions', user: { id: 'UOWNER', team_id: 'T1' }, trigger_id: 'trig-2',
  view: { id: view, callback_id: 'agent_panel', private_metadata: 'developer' },
  actions: [{ action_id: `agent_tab_tab_${tab}`, value }],
});

async function main() {
  await test('the owner\'s /agent in an agent\'s channel opens that agent on Overview', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    const command = { command: '/agent', channel_id: 'C1', channel_name: 'fabinho', trigger_id: 'trig-1', ...OWNER };
    assert.equal(panel.ack('slash_commands', command), null);
    await panel.handle('slash_commands', command);
    assert.equal(slack.calls.length, 1);
    const [triggerId, view] = slack.calls[0].args;
    assert.equal(slack.calls[0].method, 'openView');
    assert.equal(triggerId, 'trig-1');
    assert.equal(view.title.text, 'Fabinho');
    assert.equal(view.private_metadata, 'developer');
    assert.equal(view.blocks[3].accessory.image_url, AVATAR);
    const fields = view.blocks[4].fields.map((field) => field.text);
    assert.deepEqual(fields, [`*Harness*\n${CLAUDE.harness}`, `*Model*\n${CLAUDE.model}`, '*Effort*\nmedium', '*Voice*\nnone']);
    const primary = view.blocks.slice(0, 2).flatMap((row) => row.elements.filter((b) => b.style === 'primary').map((b) => b.text.text));
    assert.deepEqual(primary, ['Configuration', 'Overview']);
  });

  await test('/agent in the app\'s direct messages opens the direct-message agent', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    await panel.handle('slash_commands', { command: '/agent', channel_id: 'D9', channel_name: 'directmessage', trigger_id: 't', ...OWNER });
    assert.equal(slack.calls[0].args[1].private_metadata, 'master');
    assert.ok(texts(slack.calls[0].args[1]).includes(`*Model*\n${WORKER.model}`));
  });

  await test('anyone but the owner is refused at the ACK and nothing opens', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    for (const who of [{ user_id: 'UOTHER', team_id: 'T1' }, { user_id: 'UOWNER', team_id: 'T2' }]) {
      const command = { command: '/agent', channel_id: 'C1', trigger_id: 't', ...who };
      assert.equal(panel.ack('slash_commands', command).text, 'Only the owner can open /agent. Nothing changed.');
      await panel.handle('slash_commands', command);
    }
    assert.equal(slack.calls.length, 0);
  });

  await test('a channel no agent answers in is told so and nothing opens', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    const command = { command: '/agent', channel_id: 'C404', channel_name: 'random', trigger_id: 't', ...OWNER };
    assert.match(panel.ack('slash_commands', command).text, /^No agent answers in this channel/);
    await panel.handle('slash_commands', command);
    assert.equal(slack.calls.length, 0);
  });

  await test('other commands and other views are left to their own handlers', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    assert.equal(panel.ack('slash_commands', { command: '/payments', channel_id: 'C1', ...OWNER }), null);
    await panel.handle('slash_commands', { command: '/payments', channel_id: 'C1', trigger_id: 't', ...OWNER });
    const other = button('V1', 'prompt');
    other.view.callback_id = 'payments_panel';
    await panel.handle('interactive', other);
    assert.equal(slack.calls.length, 0);
  });

  await test('a tab button redraws the same modal on that tab', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    await panel.handle('interactive', button('V7', 'prompt'));
    assert.equal(slack.calls[0].method, 'updateView');
    const [viewId, view] = slack.calls[0].args;
    assert.equal(viewId, 'V7');
    assert.match(texts(view), /\*Role\*/);
    assert.match(texts(view), /You are \*Fabinho\*\. See <https:\/\/example\.com\/d\|docs> and local\./);
  });

  await test('another user\'s tab button changes nothing and is logged', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel, logs } = panelFor(inst, slack);
    const press = button('V7', 'prompt');
    press.user = { id: 'UOTHER', team_id: 'T1' };
    await panel.handle('interactive', press);
    assert.equal(slack.calls.length, 0);
    assert.deepEqual(logs, [{ event: 'agent-panel', action: 'refused', who: 'UOTHER' }]);
  });

  await test('Installed lists packs, skills, rules and tools from agent.json', async () => {
    const inst = installation();
    const text = texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'installed' }));
    assert.match(text, /\*Packs:\* foundations, ignite/);
    assert.match(text, /\*Skills:\* framework/);
    assert.match(text, /\*Rules:\* agent-folder/);
    assert.match(text, /\*Tools:\* cast, spark/);
    assert.match(text, /\*Commands:\* none/);
  });

  await test('Board shows the board file, escaped, and says so when there is none', async () => {
    const inst = installation({ board: '## What matters now\n\n### A <b>bold</b> subject\n' });
    const text = texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'board' }));
    assert.match(text, /\*What matters now\*/);
    assert.match(text, /\*A &lt;b&gt;bold&lt;\/b&gt; subject\*/);
    const none = installation({ board: null });
    assert.match(texts(agentView({ slug: 'developer', home: none.home, store: none.store, tab: 'board' })), /This agent has no board\./);
  });

  await test('Timers lists timers that are on first, soonest first, and shows a fixed offset in UTC', async () => {
    const inst = installation();
    inst.store.upsertConversation({ key: 'T1:C1:1.1', agent: 'developer', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    const add = (id, fields) => inst.store.upsertSchedule({ id, conversationKey: 'T1:C1:1.1', ...fields });
    add('a', { cadence: 'at:2026-10-01T00:00:00Z', timezone: 'Z', nextAt: Date.UTC(2026, 9, 1), enabled: false, subject: 'Old reminder' });
    add('b', { cadence: 'cron:0 9 * * 1', timezone: 'America/Sao_Paulo', nextAt: Date.UTC(2026, 9, 19, 12), subject: 'Weekly meeting', note: 'Compare calendars' });
    add('c', { cadence: 'every:5m', timezone: 'fixed', nextAt: Date.UTC(2026, 9, 17, 4, 31), note: 'mail check', checkTool: 'rbtv/capabilities/tools/mail-check/mail-check.py' });
    const text = texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'timers' }));
    const order = ['mail check', 'Weekly meeting', 'Old reminder'].map((name) => text.indexOf(`*${name}*`));
    assert.ok(order.every((at) => at >= 0) && order[0] < order[1] && order[1] < order[2], text);
    assert.match(text, /Next: 17 Oct, 04:31 \(UTC\) · every:5m · check: rbtv\/capabilities\/tools\/mail-check\/mail-check\.py/);
    assert.match(text, /Next: 19 Oct, 09:00 \(America\/Sao_Paulo\) · cron:0 9 \* \* 1\nCompare calendars/);
    assert.match(text, /\*Old reminder\*  _\(off\)_/);
    assert.match(texts(agentView({ slug: 'master', home: path.join(inst.workspace, '.rbtv', 'agents', 'master'), store: null, tab: 'timers' })), /no Ignite store/);
  });

  await test('a long prompt is split into sections within Slack\'s limits and cut at 100 blocks', async () => {
    const line = `${'x'.repeat(99)}\n`;
    const inst = installation({ prompt: line.repeat(400) });
    const view = agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'prompt' });
    assert.ok(view.blocks.every((block) => !block.text || block.text.text.length <= 3000));
    assert.ok(view.blocks.filter((block) => block.type === 'section').length > 10);
    const huge = installation({ prompt: line.repeat(4000) });
    const cut = agentView({ slug: 'developer', home: huge.home, store: huge.store, tab: 'prompt' });
    assert.equal(cut.blocks.length, 100);
    assert.match(cut.blocks[99].elements[0].text, /at most 100 blocks/);
  });

  await test('an unknown tab shows Overview, and an unreadable agent says why', async () => {
    const inst = installation();
    assert.match(texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'nope' })), /\*Effort\*\nmedium/);
    fs.writeFileSync(path.join(inst.home, 'agent.json'), '{');
    assert.match(texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'overview' })), /This agent cannot be read: .*cannot be read/);
  });

  await test('Tasks shows the running turn first, every open task with its state, thread, workers and newest notes, and no finished work', async () => {
    const inst = installation();
    const NOW = Date.UTC(2026, 9, 17, 12);
    const store = inst.store;
    const conv = (ts) => {
      const key = `T1:C1:${ts}`;
      store.upsertConversation({ key, agent: 'developer', workspace: 'T1', channel: 'C1', rootTs: ts });
      return key;
    };
    const work = (id, key, state, fields = {}) => store.db.prepare(`INSERT INTO work(id, conversation_key, state, summary, next_step, workers, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`).run(id, key, state, fields.summary ?? null, fields.next ?? null, JSON.stringify(fields.workers ?? []), fields.at ?? NOW - 3600000);
    const asking = conv('1.1');
    const waiting = conv('2.2');
    const running = conv('3.3');
    work('w1', asking, 'waiting_owner', { summary: 'Asked <you> about the deploy', next: 'Deploy after the answer', at: NOW - 600000 });
    work('w2', waiting, 'waiting_workers', { summary: 'Canvas test running', workers: [{ ref: 'canvas-check', kind: 'cast worker' }], at: NOW - 60000 });
    work('w3', running, 'open', { summary: 'Building the Work tab', at: NOW - 7200000 });
    work('w4', conv('4.4'), 'completed', { summary: 'Finished long ago' });
    for (const [text, at] of [['one', 1], ['two', 2], ['three', 3], ['four', 4]]) store.addNote({ conversationKey: running, text: `note ${text}`, createdAt: NOW - (10 - at) * 60000 });
    store.liveRun = () => ({ conversation_key: running, started_at: NOW - 120000, launch_snapshot: { model: CLAUDE.model, effort: 'medium' } });
    const view = agentView({ slug: 'developer', home: inst.home, store, tab: 'tasks', now: NOW });
    const body = view.blocks.slice(3).map((block) => block.text.text);
    assert.equal(body[0], `*Running now* in a <https://app.slack.com/archives/C1/p33|thread> · ${CLAUDE.model} medium · started 2 min ago`);
    assert.equal(body.length, 4, body.join('\n---\n'));
    assert.match(body[1], /^\*In progress\* · running · <https:\/\/app\.slack\.com\/archives\/C1\/p33\|thread> · updated 2 h ago\nBuilding the Work tab\n• note four _\(6 min ago\)_\n• note three _\(7 min ago\)_\n• note two _\(8 min ago\)_$/);
    assert.match(body[2], /^\*Waiting for workers\* · <https:\/\/app\.slack\.com\/archives\/C1\/p22\|thread> · updated 1 min ago\nCanvas test running\n_Workers:_ canvas-check \(cast worker\)$/);
    assert.match(body[3], /^\*Waiting for you\* · .* · updated 10 min ago\nAsked &lt;you&gt; about the deploy\n_Next:_ Deploy after the answer$/);
    assert.ok(!body.join('\n').includes('Finished long ago'));
    store.liveRun = () => null;
    assert.equal(agentView({ slug: 'developer', home: inst.home, store, tab: 'tasks', now: NOW }).blocks[3].text.text, '*Running now:* nothing');
    assert.match(texts(agentView({ slug: 'developer', home: inst.home, store: null, tab: 'tasks' })), /no Ignite store, so it has no tasks/);
  });

  await test('Sub-agents lists this agent\'s launches, running first, and none of another agent\'s', async () => {
    const inst = installation();
    const NOW = Date.UTC(2026, 9, 17, 12);
    const other = path.join(inst.workspace, '.rbtv', 'agents', 'master');
    const launches = () => [
      { pid: 1, harness: OTHER.harness, model: OTHER.model, launcher: inst.home, launched: null, tag: 'scratch [cast:ab12]', task: 'Check the canvas API', t0: NOW - 3600000, alive: false },
      { pid: 2, harness: WORKER.harness, model: WORKER.model, launcher: `${inst.home}/`, launched: '/x/.rbtv/agents/tester', task: 'Test slice 1', t0: NOW - 300000, alive: true },
      { pid: 3, harness: CLAUDE.harness, model: CLAUDE.model, launcher: other, launched: null, task: 'Master\'s worker', t0: NOW, alive: true },
      { pid: 4, harness: CLAUDE.harness, model: CLAUDE.model, launcher: null, launched: inst.home, task: 'The agent\'s own turn', t0: NOW, alive: true },
    ];
    const view = agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'subagents', launches, now: NOW });
    const text = texts(view);
    assert.ok(text.includes(`*Running* (1)\n\n*tester* · ${WORKER.harness} ${WORKER.model} · started 5 min ago\nTest slice 1`), text);
    assert.ok(text.includes(`*Ended* (last 1 of the past 7 days)\n\n*scratch [cast:ab12]* · ${OTHER.harness} ${OTHER.model} · started 1 h ago\nCheck the canvas API`), text);
    assert.ok(!text.includes('Master') && !text.includes('own turn'));
    const none = texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'subagents', launches: () => [], now: NOW }));
    assert.match(none, /\*Running:\* none/);
    assert.ok(!none.includes('*Ended*'));
  });

  await test('Approvals lists this agent\'s payment requests with the payment panel\'s buttons, pending first, and no one else\'s', async () => {
    const inst = installation();
    const gate = new Gate({ workspace: inst.workspace, now: () => Date.UTC(2026, 9, 15, 15) });
    gate.saveSettings({ mode: 'case_by_case', limits: {} });
    const ask = (agent, cents) => gate.request({
      agent, conversationKey: 'T1:C1:1.1', connector: 'asaas', method: 'pix',
      recipient: { name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', keyType: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' },
      amountCents: cents, note: 'Owed',
    });
    const refused = ask('developer', 500);
    gate.refuse(refused.id);
    const waiting = ask('developer', 1000);
    gate.resolved(waiting.id, { name: 'KENU EXAMPLE SILVA', document: '***.123.456-**', bank: 'Nubank', key: 'kenu@example.com', keyType: 'EMAIL' });
    ask('sara', 2000);
    const view = agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'payments', gate });
    const text = texts(view);
    assert.match(text, /\*Waiting for you\* \(1\)\n/);
    assert.match(text, new RegExp(`\\*Payment request ${waiting.id}\\* from developer`));
    assert.match(text, /\*Decided\* \(last 1\)/);
    assert.match(text, new RegExp(`\\*Payment request ${refused.id}\\* from developer`));
    assert.ok(!text.includes('from sara'));
    const actions = view.blocks.filter((block) => block.type === 'actions').slice(2).flatMap((block) => block.elements.map((b) => [b.action_id, b.value]));
    assert.deepEqual(actions, [['payments_approve', waiting.id], ['payments_refuse', waiting.id]]);
    assert.match(texts(agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'payments', gate: null })), /Payments are not set up here/);
  });

  await test('redraw shows the agent panel on Approvals for its own view and nothing for another', async () => {
    const inst = installation();
    const { panel } = panelFor(inst, fakeSlack());
    const view = panel.redraw({ callback_id: 'agent_panel', private_metadata: 'developer' });
    assert.equal(view.callback_id, 'agent_panel');
    assert.equal(view.blocks[0].elements.find((b) => b.style === 'primary').text.text, 'Approvals');
    assert.equal(panel.redraw({ callback_id: 'payments_panel' }), null);
  });

  await test('Docs lists recent Markdown outputs with Open in canvas in the agent\'s channel, and Open writes the canvas', async () => {
    const inst = installation();
    const doc = path.join(inst.workspace, 'notes', 'plan.md');
    fs.mkdirSync(path.dirname(doc), { recursive: true });
    fs.writeFileSync(doc, 'The plan\n');
    const key = 'T1:C1:1.1';
    inst.store.upsertConversation({ key, agent: 'developer', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
    inst.store.db.prepare("INSERT INTO queue(id, conversation_key, kind, payload, priority, available_at, state, attempts, created_at) VALUES ('q', ?, 'owner', '{}', 0, 0, 'done', 1, 0)").run(key);
    inst.store.db.prepare("INSERT INTO runs(id, queue_id, nonce, state, output, started_at, ended_at) VALUES ('r', 'q', 'n', 'finished', ?, 0, ?)").run(JSON.stringify({ outputs: [doc] }), Date.now() - 3600000);
    const canvas = { lines: null, title: null };
    const slack = {
      ...fakeSlack(),
      async channelCanvas() { return canvas.lines ? 'Fdoc' : null; },
      async canvasCreate({ markdown, title }) { canvas.lines = markdown; canvas.title = title; return { canvasId: 'Fdoc' }; },
      async canvasRead() { return { html: `<h1>${canvas.title}</h1><p class="line">${canvas.lines.trim()}</p>`, comments: 0 }; },
    };
    slack.calls = slack.calls || [];
    const { panel } = panelFor(inst, slack);
    const before = agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'docs', workspace: inst.workspace, channel: 'C1' });
    const row = before.blocks.find((block) => block.accessory?.action_id === 'agent_doc_open_0');
    assert.match(row.text.text, /^`notes\/plan\.md`\n_from a turn 1 h ago_$/);
    assert.equal(row.accessory.value, 'notes/plan.md');
    assert.match(texts(before), /\*In the canvas:\* nothing yet\./);
    const dm = agentView({ slug: 'developer', home: inst.home, store: inst.store, tab: 'docs', workspace: inst.workspace, channel: null });
    assert.ok(!dm.blocks.some((block) => block.accessory), 'no Open without a channel');
    assert.match(texts(dm), /opening is not available here/);
    const press = { ...button('V9', 'docs'), actions: [{ action_id: 'agent_doc_open_0', value: 'notes/plan.md' }] };
    await panel.handle('interactive', press);
    assert.equal(canvas.title, 'notes/plan.md');
    assert.equal(canvas.lines, 'The plan\n');
    const shown = slack.calls.at(-1).args[1];
    assert.match(texts(shown), /Opened `notes\/plan\.md` in this channel's canvas: <https:\/\/app\.slack\.com\/docs\/T1\/Fdoc\|open it>\./);
    assert.match(texts(shown), /\*In the canvas:\* `notes\/plan\.md` \(opened just now\)/);
    await panel.handle('interactive', { ...press, actions: [{ action_id: 'agent_doc_open_0', value: '../../etc/passwd.md' }] });
    assert.match(texts(slack.calls.at(-1).args[1]), /That document is not in the list any more\. Nothing changed\./);
    // Save canvas sits beside the open document; it writes the edited canvas into the agent's folder and lists it.
    const save = slack.calls.at(-1).args[1].blocks.find((block) => block.accessory?.action_id === 'agent_doc_save');
    assert.equal(save.accessory.text.text, 'Save canvas');
    const pressSave = { ...press, actions: [{ action_id: 'agent_doc_save', value: 'notes/plan.md' }] };
    await panel.handle('interactive', pressSave);
    assert.match(texts(slack.calls.at(-1).args[1]), /Nothing to save: the canvas of `notes\/plan\.md` is unchanged/);
    canvas.lines = 'The plan\nHenrique typed this';
    await panel.handle('interactive', pressSave);
    const savedView = texts(slack.calls.at(-1).args[1]);
    assert.match(savedView, /Saved your canvas edits to `output\/ignite\/canvas\/\d{8}T\d{6}Z-plan\.md` in the agent's folder\. Ask the agent to bring them into `notes\/plan\.md`\./);
    assert.match(savedView, /\*Saved, not yet brought in\* \(1\): ask Fabinho to bring them into their documents\.\n• `output\/ignite\/canvas\/\d{8}T\d{6}Z-plan\.md` from `notes\/plan\.md`, saved just now/);
    const files = fs.readdirSync(path.join(inst.home, 'output', 'ignite', 'canvas'));
    assert.equal(files.length, 1);
    assert.match(fs.readFileSync(path.join(inst.home, 'output', 'ignite', 'canvas', files[0]), 'utf8'), /^---\nsource: "notes\/plan\.md"\n[\s\S]*---\n\nThe plan\s+Henrique typed this\n$/);
  });

  await test('a failed Slack call is logged and never thrown', async () => {
    const inst = installation();
    const slack = fakeSlack({ fail: true });
    const { panel, logs } = panelFor(inst, slack);
    await panel.handle('slash_commands', { command: '/agent', channel_id: 'C1', trigger_id: 't', ...OWNER });
    assert.deepEqual(logs, [{ event: 'agent-panel', action: 'failed', message: 'slack down' }]);
  });

  assert.deepEqual(TABS.map((tab) => tab.id), ['overview', 'installed', 'prompt', 'board', 'timers', 'tasks', 'subagents', 'payments', 'docs']);
  console.log(`${passed} passed, ${failures.length} failed`);
  if (failures.length) process.exit(1);
}

main();

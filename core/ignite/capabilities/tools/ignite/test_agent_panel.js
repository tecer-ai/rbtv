'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createAgentPanel, agentView, TABS } = require('./agent-panel.js');
const { Store } = require('./store.js');

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
    name: 'developer', external_name: 'Fabinho', avatar: AVATAR, harness: 'claude', model: 'opus-5-5', effort: 'medium',
    description: 'Architecture and development.', packs: ['foundations', 'ignite'],
    components: {
      'core/rbtv': { selected: { framework: { method: 'skill' }, 'agent-folder': { method: 'rule' } } },
      'core/cast': { selected: { cast: { method: 'tool' }, spark: { method: 'tool' } } },
    },
  }, prompt);
  if (board != null) fs.writeFileSync(path.join(home, '_artifacts', 'board.md'), board);
  agent('master', { name: 'master', harness: 'codex', model: 'gpt-5', effort: 'high' }, 'Master prompt.\n');
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

const texts = (view) => view.blocks.map((block) => [block.text?.text || '', ...(block.fields || []).map((field) => field.text)].join('\n')).join('\n');
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
    assert.deepEqual(fields, ['*Harness*\nclaude', '*Model*\nopus-5-5', '*Effort*\nmedium', '*Voice*\nnone']);
    const primary = view.blocks.slice(0, 2).flatMap((row) => row.elements.filter((b) => b.style === 'primary').map((b) => b.text.text));
    assert.deepEqual(primary, ['Configuration', 'Overview']);
  });

  await test('/agent in the app\'s direct messages opens the direct-message agent', async () => {
    const inst = installation();
    const slack = fakeSlack();
    const { panel } = panelFor(inst, slack);
    await panel.handle('slash_commands', { command: '/agent', channel_id: 'D9', channel_name: 'directmessage', trigger_id: 't', ...OWNER });
    assert.equal(slack.calls[0].args[1].private_metadata, 'master');
    assert.match(texts(slack.calls[0].args[1]), /\*Model\*\ngpt-5/);
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

  await test('a failed Slack call is logged and never thrown', async () => {
    const inst = installation();
    const slack = fakeSlack({ fail: true });
    const { panel, logs } = panelFor(inst, slack);
    await panel.handle('slash_commands', { command: '/agent', channel_id: 'C1', trigger_id: 't', ...OWNER });
    assert.deepEqual(logs, [{ event: 'agent-panel', action: 'failed', message: 'slack down' }]);
  });

  assert.deepEqual(TABS.map((tab) => tab.id), ['overview', 'installed', 'prompt', 'board', 'timers']);
  console.log(`${passed} passed, ${failures.length} failed`);
  if (failures.length) process.exit(1);
}

main();

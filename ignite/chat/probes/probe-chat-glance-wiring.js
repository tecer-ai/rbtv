'use strict';

// probe-chat-glance-wiring — THE WIRING, not the rendering. `probe-chat-glance` proves what §5 and
// §6 DECIDE (slot arithmetic, changed-only, the seven triggers, the zero case); this probe proves
// the three seams that made those decisions unreachable in production:
//
//   1. THE SLOT DRIVER EXISTS AND FIRES. `index.js#main()` wired no clock, so `check()` was never
//      called by anything. Here the driver is started on a MOCKED clock parked at a slot instant
//      and a real post is observed coming out of it.
//   2. THE READERS ARE REAL. Open asks arrive over the gateway (`ask-store.js#listOpenAsks` ->
//      `inspect asks`) and open conditions come from `observation/emitter.js`'s OWN read interface
//      over a registry file written by a DIFFERENT emitter instance — the daemon-writes /
//      bridge-reads seam, in one process but never one object.
//   3. THE STATUS TRANSPORT EXISTS. §6's line reaches Slack through
//      `slack-socket-mode.js#setStatusText` — a surface that did not exist, which is why the status
//      line degraded to `no-status-port` forever.
//
// Mocked Slack (an injected `fetchImpl`), a mocked clock, a fake forwarder. No live post, no
// socket, no daemon.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const OUT = path.join(__dirname, 'probe-chat-glance-wiring.out');
const SYS = 'Csystem';

const { createGlance } = require('../glance');
const { createOutbox } = require('../outbox');
const { createAskRecord } = require('../ask-store');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { createAlarmEmitter, alarmRegistryPath } = require('../../observation/emitter');

const checks = [];
function check(name, pass, evidence = {}) {
  checks.push({ name, pass: !!pass, evidence });
}

// São Paulo has been UTC-3 year-round since DST was abolished in 2019, so a local hour is the UTC
// hour + 3 — written out rather than assumed, exactly as `probe-chat-glance` does.
function spInstant(dateIso, localHour, localMinute = 0) {
  const day = new Date(`${dateIso}T00:00:00Z`);
  return new Date(day.getTime() + ((localHour + 3) * 3600 + localMinute * 60) * 1000);
}

function sleep(ms) {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

// The gateway, as the bridge sees it: one `forward(intent, payload)` that answers the daemon's
// envelope shape. `inspect asks` is the ONLY intent this probe answers — anything else is a
// failure of the wiring under test, not of the fake.
function fakeForwarder(rowsOrFail) {
  const calls = [];
  return {
    calls,
    forward: async (intent, payload) => {
      calls.push({ intent, payload });
      if (intent !== 'inspect' || !payload || payload.target !== 'asks') {
        return { ok: false, error: { code: 'PROBE_UNEXPECTED_INTENT' } };
      }
      const answer = typeof rowsOrFail === 'function' ? rowsOrFail() : rowsOrFail;
      if (answer === 'refuse') return { ok: false, error: { code: 'E_GATEWAY_DOWN' } };
      if (answer === 'throw') throw new Error('connect ECONNREFUSED');
      return { ok: true, result: { target: 'asks', rows: answer } };
    },
  };
}

function mockSlack() {
  const posts = [];
  const statuses = [];
  let failNext = 0;
  const fetchImpl = async (url, opts) => {
    const body = JSON.parse(opts.body || '{}');
    if (/chat\.postMessage$/.test(url)) {
      if (failNext > 0) { failNext -= 1; return { json: async () => ({ ok: false, error: 'ratelimited' }) }; }
      posts.push(body);
      return { json: async () => ({ ok: true, ts: `1724500000.0001${posts.length}` }) };
    }
    if (/users\.profile\.set$/.test(url)) {
      statuses.push(body);
      return { json: async () => ({ ok: true }) };
    }
    return { json: async () => ({ ok: false, error: 'unexpected_method' }) };
  };
  const transport = createSlackSocketMode({
    botToken: 'xoxb-probe',
    apiBase: 'https://slack.invalid/api',
    onMessage: () => {},
    fetchImpl,
    WebSocketImpl: function NeverOpened() { throw new Error('this probe never opens a socket'); },
  });
  return {
    posts,
    statuses,
    transport,
    failNextPost(n = 1) { failNext = n; },
  };
}

function ask(id, seat, oneLiner, openedAt) {
  return { id, seat, one_liner: oneLiner, opened_at: openedAt, evidence_pointer: `/tmp/${id}.txt` };
}

(async () => {
  const t0 = Date.now();
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'glance-wiring-'));

  // ── 1. THE READERS: OPEN CONDITIONS COME FROM THE DAEMON'S REGISTRY ─────────────────────────
  //
  // The alarm is emitted by a SEPARATE emitter instance writing the registry file, which is what
  // the daemon does. The bridge's reader is then asked, and what it answers is what the digest
  // renders. A bridge that constructed its own registry, or read a snapshot taken at startup,
  // would pass nothing here.
  {
    const daemonEmitter = createAlarmEmitter({
      storePath: alarmRegistryPath(root),
      post: async () => ({ delivered: true, outbox_id: 'daemon-side' }),
      systemChannelId: SYS,
    });
    const glance = createGlance({
      outbox: createOutbox({ storePath: path.join(root, 'ob-1.json'), send: async () => ({ delivered: true, ts: '1.1' }) }),
      askRecord: createAskRecord({ forwarder: fakeForwarder([]) }),
      systemChannelId: SYS,
      workspaceRoot: root,
    });

    check('the condition reader is EMPTY before the daemon emits anything',
      glance.readOpenConditions().length === 0, {});

    await daemonEmitter.emit({
      condition: 'running, no live seat, no eligible launch, no open ask, not paused',
      subject: { type: 'goal', id: 'meet-transcript-summarizer' },
      evidence_pointer: '/w/.rbtv/goals/meet-transcript-summarizer',
      what_would_clear_it: 'a seat starting',
      signature_class: 'frozen-goal',
      immediate: false,
    });

    const conditions = glance.readOpenConditions();
    check('an alarm the DAEMON emitted after the bridge was built is visible to the bridge — the reader reloads, it does not hold a startup snapshot',
      conditions.length === 1 && conditions[0].subject === 'meet-transcript-summarizer',
      { conditions });
    check('the condition row carries the five keys the digest documents',
      conditions.length === 1
        && ['signature', 'condition', 'subject', 'first_emitted_at', 'evidence_pointer']
          .every((k) => conditions[0][k] !== undefined),
      { row: conditions[0] });

    // The bridge may READ the registry and may never write it: a second alarm composer is exactly
    // what [T4-R10] deleted.
    const src = fs.readFileSync(path.join(__dirname, '..', 'glance.js'), 'utf8');
    check('the bridge never EMITS: its emitter instance is handed a post that throws',
      /refusingPost/.test(src) && /never EMITS alarms/.test(src), {});
  }

  // ── 2. THE SLOT DRIVER FIRES, AND WHAT IT POSTS REACHES THE TRANSPORT ───────────────────────
  {
    const slack = mockSlack();
    const rows = [ask('1724500001.000100', 'goal-master', 'Keep the 90-minute cap?', '2026-08-25 08:20')];
    const forwarder = fakeForwarder(rows);
    let at = spInstant('2026-08-25', 3);   // 03:00 BRT — deliberately NOT a slot

    const glance = createGlance({
      outbox: createOutbox({
        storePath: path.join(root, 'ob-2.json'),
        send: (args) => slack.transport.sendToOwner(args),
      }),
      askRecord: createAskRecord({ forwarder }),
      setStatusText: (text) => slack.transport.setStatusText(text),
      systemChannelId: SYS,
      workspaceRoot: root,
      digestState: path.join(root, 'digest-state.json'),
      checkEveryMs: 10,
      now: () => at,
    });

    glance.start();
    await sleep(120);
    check('the driver RUNS and posts NOTHING at 03:00 — a driver that fired on every beat would be a poll loop, not a ten-slot clock',
      slack.posts.length === 0 && forwarder.calls.length === 0,
      { posts: slack.posts.length, gatewayCalls: forwarder.calls.length });

    at = spInstant('2026-08-25', 8);   // a slot
    await sleep(120);
    glance.stop();

    check('on the slot the driver fires WITHOUT being called by hand — this is the wiring that did not exist',
      slack.posts.length === 1, { posts: slack.posts.length });
    check('the post reached the TRANSPORT: right channel, no thread, and the digest text',
      slack.posts.length === 1
        && slack.posts[0].channel === SYS
        && slack.posts[0].thread_ts === undefined
        && /System digest · 08:00/.test(slack.posts[0].text)
        && /Keep the 90-minute cap\?/.test(slack.posts[0].text),
      { post: slack.posts[0] });

    // The driver keeps beating inside the same slot minute and posts nothing more: the baseline
    // moved on Slack's ack.
    glance.start();
    await sleep(120);
    glance.stop();
    check('a second beat inside the SAME slot posts nothing — the baseline advanced on the ack',
      slack.posts.length === 1, { posts: slack.posts.length });

    // ── the §6 status transport ──────────────────────────────────────────────────────────────
    const updated = await glance.onTrigger('ask-minted');
    check('a §6 trigger writes the bot status text through the transport — the port that did not exist',
      updated.updated === true && slack.statuses.length === 1
        && slack.statuses[0].profile.status_text === updated.text,
      { result: updated, sent: slack.statuses[0] });
    check('the status text is §6\'s exact format, rendered from the SAME asks the digest read',
      /^1 waiting · oldest \d+h · 0 blocked$/.test(updated.text), { text: updated.text });
    const notATrigger = await glance.onTrigger('tick');
    check('a non-trigger still changes nothing — the status port is not a general write surface',
      notATrigger.updated === false && slack.statuses.length === 1, { result: notATrigger });
    check('the status line never posted a message while doing any of that',
      slack.posts.length === 1, { posts: slack.posts.length });
  }

  // ── 3. AN UNREADABLE ASK SET SKIPS THE SLOT — IT NEVER RENDERS AS "NONE OPEN" ───────────────
  //
  // The load-bearing leg. `system-digest.js` collapses a failed read into `[]` by construction
  // (`(await readOpenAsks()) || []`), so if the wiring did not make this distinction BEFORE the
  // digest is asked, a gateway outage would post an empty digest, move the baseline on Slack's ack,
  // and then re-post everything when the daemon returned.
  {
    const slack = mockSlack();
    const rows = [ask('1724500001.000100', 'goal-master', 'Keep the 90-minute cap?', '2026-08-25 08:20')];
    let answer = rows;
    const forwarder = fakeForwarder(() => answer);
    const at = spInstant('2026-08-25', 10);
    const statePath = path.join(root, 'digest-state-3.json');
    const glance = createGlance({
      outbox: createOutbox({ storePath: path.join(root, 'ob-3.json'), send: (a) => slack.transport.sendToOwner(a) }),
      askRecord: createAskRecord({ forwarder }),
      systemChannelId: SYS,
      workspaceRoot: root,
      digestState: statePath,
      now: () => at,
    });

    answer = 'refuse';
    let r = await glance.checkSlot();
    check('a REFUSED gateway read skips the slot — it does not post "• none open"',
      r.ran === false && r.reason === 'asks-unreadable' && slack.posts.length === 0, { result: r });
    check('and the baseline has NOT moved — nothing was delivered, so nothing may be recorded as delivered',
      !fs.existsSync(statePath), { statePath });

    answer = 'throw';
    r = await glance.checkSlot();
    check('a THROWN read is the same answer — the slot is skipped, not posted empty',
      r.ran === false && r.reason === 'asks-unreadable' && slack.posts.length === 0, { result: r });

    answer = rows;
    r = await glance.checkSlot();
    check('the next slot with a readable set posts the digest the outage would have destroyed',
      r.posted === true && slack.posts.length === 1 && /Keep the 90-minute cap\?/.test(slack.posts[0].text),
      { result: { ran: r.ran, posted: r.posted, delivered: r.delivered } });

    answer = [];
    r = await glance.checkSlot();
    check('an EMPTY set is a real answer and still posts — "nothing is waiting" is a change the owner may read',
      r.posted === true && slack.posts.length === 2 && /none open/.test(slack.posts[1].text),
      { text: slack.posts[1] && slack.posts[1].text });
  }

  // ── 4. AN UNACKED POST LEAVES THE BASELINE ALONE (C-17, through the WIRED transport) ────────
  {
    const slack = mockSlack();
    const rows = [ask('1724500009.000900', 'audio-smith', 'Which mic profile is the reference?', '2026-08-25 11:00')];
    const at = spInstant('2026-08-25', 12);
    const statePath = path.join(root, 'digest-state-4.json');
    const outbox = createOutbox({ storePath: path.join(root, 'ob-4.json'), send: (a) => slack.transport.sendToOwner(a) });
    const glance = createGlance({
      outbox,
      askRecord: createAskRecord({ forwarder: fakeForwarder(rows) }),
      systemChannelId: SYS,
      workspaceRoot: root,
      digestState: statePath,
      now: () => at,
    });
    slack.failNextPost(1);
    const r = await glance.checkSlot();
    check('Slack refusing the digest leaves it pending-delivery and the baseline unmoved [C-17]',
      r.delivered === false && !fs.existsSync(statePath)
        && outbox.query({ state: 'pending-delivery', kind: 'digest' }).length === 1,
      { result: { posted: r.posted, delivered: r.delivered } });
    const again = await glance.checkSlot();
    check('the next beat RETRIES the same record rather than minting a second',
      again.delivered === true
        && outbox.query({ kind: 'digest' }).length === 1
        && slack.posts.length === 1,
      { records: outbox.query({ kind: 'digest' }).length, posts: slack.posts.length });
  }

  // ── 5. NO SYSTEM CHANNEL IS A LOUD REFUSAL, NEVER A GUESS ───────────────────────────────────
  {
    const said = [];
    const glance = createGlance({
      outbox: createOutbox({ storePath: null, send: async () => ({ delivered: true }) }),
      askRecord: createAskRecord({ forwarder: fakeForwarder([]) }),
      systemChannelId: null,
      workspaceRoot: root,
      logger: (m) => said.push(m),
    });
    check('with no system channel the glance is NOT wired, and says so — it never picks a channel',
      glance === null && said.some((m) => m.level === 'warn' && /RBTV_SYSTEM_CHANNEL_ID/.test(m.message)),
      { said });
  }

  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: {
      probe: 'probe-chat-glance-wiring',
      pass,
      checks: checks.length,
      failed: checks.filter((c) => !c.pass).map((c) => c.name),
      EXIT: exit,
      WALL_MS: wallMs,
      SKIPPED_COUNT: 0,
    },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-glance-wiring EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-glance-wiring EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});

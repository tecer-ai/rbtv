'use strict';

// probe-chat-glance — `spec-owner-io.md` §5 (changed-only system digest) and §6 (bot status line).
//
// Mocked Slack (the outbox's `send` port) and a MOCKED CLOCK — no live post, no real timer, and no
// dependence on when the probe happens to run. Slot arithmetic is asserted against explicit
// America/Sao_Paulo instants, which is the only way a "03:00 does not run" claim means anything.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { createOutbox } = require('../outbox');
const {
  createSystemDigest, isSlot, slotLabel, SLOT_HOURS, renderDigest, sortAsksBlockingFirst,
} = require('../system-digest');
const { createStatusLine, renderStatusLine, TRIGGERS } = require('../status-line');

const OUT = path.join(__dirname, 'probe-chat-glance.out');
const SYS = 'Csystem';

const checks = [];
function check(name, pass, evidence = {}) {
  checks.push({ name, pass: !!pass, evidence });
}

// An instant expressed as a São Paulo wall-clock time. BRT is UTC-3 year-round since 2019 (DST was
// abolished), so the UTC instant for a given local hour is hour+3 — written out rather than assumed
// so the assertion is checkable by eye.
function spInstant(dateIso, localHour, localMinute = 0) {
  const utcHour = localHour + 3;
  const day = new Date(`${dateIso}T00:00:00Z`);
  return new Date(day.getTime() + (utcHour * 3600 + localMinute * 60) * 1000);
}

function mockSlack() {
  const posts = [];
  let fail = 0;
  return {
    posts,
    failNext(n = 1) { fail = n; },
    send: async ({ channel, threadTs, text }) => {
      if (fail > 0) { fail -= 1; return { delivered: false, error: 'ratelimited' }; }
      posts.push({ channel, threadTs, text });
      return { delivered: true, ts: `${1724500000 + posts.length}.0000${posts.length}` };
    },
  };
}

function ask(id, seat, oneLiner, openedAt, extra = {}) {
  return { id, seat, one_liner: oneLiner, opened_at: openedAt, ...extra };
}

(async () => {
  const t0 = Date.now();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'glance-'));

  // ── §5 slot arithmetic ─────────────────────────────────────────────────────
  {
    const ran = SLOT_HOURS.filter((h) => isSlot(spInstant('2026-08-24', h)));
    check('§5 all TEN listed slots run (00,06,08,10,12,14,16,18,20,22 America/Sao_Paulo)',
      SLOT_HOURS.length === 10 && ran.length === 10, { slots: SLOT_HOURS, ran: ran.length });

    check('§5 a 03:00 America/Sao_Paulo check does NOT run',
      isSlot(spInstant('2026-08-24', 3)) === false, { at: '03:00 BRT' });

    const quiet = [1, 2, 3, 4, 5].filter((h) => isSlot(spInstant('2026-08-24', h)));
    check('§5 no check anywhere in 00:00–06:00 except the 24:00 slot itself (which IS 00:00)',
      quiet.length === 0 && isSlot(spInstant('2026-08-24', 0)) === true, { ranInQuietWindow: quiet });

    const odd = [7, 9, 11, 13, 15, 17, 19, 21, 23].filter((h) => isSlot(spInstant('2026-08-24', h)));
    check('§5 an odd hour is not a slot and a non-zero minute inside a slot hour is not a slot',
      odd.length === 0 && isSlot(spInstant('2026-08-24', 14, 30)) === false, { oddHoursThatRan: odd });

    check('§5 the header names the slot in São Paulo local time',
      slotLabel(spInstant('2026-08-24', 14)) === '14:00', { label: slotLabel(spInstant('2026-08-24', 14)) });
  }

  // ── §5 changed-only behaviour ──────────────────────────────────────────────
  {
    const slack = mockSlack();
    const statePath = path.join(dir, 'digest-a.json');
    const outbox = createOutbox({ storePath: path.join(dir, 'outbox-a.json'), send: slack.send });
    let asks = [];
    let conditions = [];
    const digest = createSystemDigest({
      post: outbox.post,
      systemChannelId: SYS,
      readOpenAsks: () => asks,
      readOpenConditions: () => conditions,
      statePath,
    });

    // NO-CHANGE fixture: nothing open, and the first slot has never delivered anything, so the very
    // first post IS a change (empty ≠ "no baseline"). Deliver it, then re-check at the next slot.
    const first = await digest.check(spInstant('2026-08-24', 6));
    const unchangedSlot = await digest.check(spInstant('2026-08-24', 8));
    check('§5 no-change fixture: an identical snapshot at the next slot posts NOTHING — zero outbox posts',
      first.posted === true && unchangedSlot.posted === false && unchangedSlot.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 1,
      { firstPosted: first.posted, second: unchangedSlot.reason, records: outbox.query({ kind: 'digest' }).length });

    // ASK-ONLY CHANGE.
    asks = [ask('1724508123.123456', 'draft-seat', 'which binder for the vault path?', spInstant('2026-08-24', 7))];
    const askChange = await digest.check(spInstant('2026-08-24', 10));
    check('§5 an ask-only change triggers exactly ONE post',
      askChange.posted === true && askChange.delivered === true
      && outbox.query({ kind: 'digest' }).length === 2,
      { records: outbox.query({ kind: 'digest' }).length });

    // AGE-TICK ONLY: six hours later the same ask is older, nothing else moved.
    const ageTick = await digest.check(spInstant('2026-08-24', 16));
    check('§5 an age-tick-only fixture does NOT post — age is rendered but is not in the snapshot',
      ageTick.posted === false && ageTick.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 2,
      { reason: ageTick.reason, records: outbox.query({ kind: 'digest' }).length });

    // CONDITION-ONLY CHANGE.
    conditions = [{
      signature: 'frozen:ignite-engine',
      condition: 'running, no live seat, no eligible launch, no open ask, not paused',
      subject: 'ignite-engine',
      first_emitted_at: spInstant('2026-08-24', 17),
    }];
    const condChange = await digest.check(spInstant('2026-08-24', 18));
    check('§5 a condition-only change triggers exactly ONE post',
      condChange.posted === true && outbox.query({ kind: 'digest' }).length === 3,
      { records: outbox.query({ kind: 'digest' }).length });

    // ONE-LINER EDIT with the same ask id is a change (§5 pins one_liners into the snapshot).
    asks = [ask('1724508123.123456', 'draft-seat', 'which binder — vault path or repo path?', spInstant('2026-08-24', 7))];
    const linerChange = await digest.check(spInstant('2026-08-24', 20));
    check('§5 the same ask id with an EDITED one-liner is a change',
      linerChange.posted === true && outbox.query({ kind: 'digest' }).length === 4,
      { records: outbox.query({ kind: 'digest' }).length });

    // GOAL-NAME CHANGE ONLY (`digest-sentence` DoD 3's standing-trap proof, extended to `goal`):
    // the id and text stay put, only `goal` changes — must NOT post.
    asks = [ask('1724508123.123456', 'draft-seat', 'which binder — vault path or repo path?', spInstant('2026-08-24', 7),
      { goal: 'demo-goal' })];
    const goalChange = await digest.check(spInstant('2026-08-24', 22));
    check('R-A2 a goal-NAME-only change (id and text unchanged) does NOT re-post — goal is not in the snapshot',
      goalChange.posted === false && goalChange.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 4,
      { reason: goalChange.reason, records: outbox.query({ kind: 'digest' }).length });

    // LINK CHANGE ONLY: same proof for `link`.
    asks = [ask('1724508123.123456', 'draft-seat', 'which binder — vault path or repo path?', spInstant('2026-08-24', 7),
      { goal: 'demo-goal', link: 'https://slack.example/archives/Cgoal/pNEW' })];
    const linkChange = await digest.check(spInstant('2026-08-25', 0));
    check('R-A2 a link-only change (id and text unchanged) does NOT re-post — link is not in the snapshot',
      linkChange.posted === false && linkChange.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 4,
      { reason: linkChange.reason, records: outbox.query({ kind: 'digest' }).length });

    // `digest-sentence` DoD 3 — the deploy-time claim: a pre-existing ask carries `subject: ''`
    // (the interface contract's own fallback), so switching the snapshot's text input from
    // `one_liner` to `subject || one_liner` does not move the baseline for it BY ITSELF. The one
    // re-post happens only when a composer later gives that SAME open ask a real, different
    // subject (e.g. `asks-repost`'s in-thread rewrite of an already-open recovery ask) — simulated
    // here as the same id/one_liner acquiring a `subject` for the first time.
    asks = [ask('1724508123.123456', 'draft-seat', 'which binder — vault path or repo path?', spInstant('2026-08-24', 7),
      { goal: 'demo-goal', link: 'https://slack.example/archives/Cgoal/pNEW', subject: '' })];
    const stillEmptySubject = await digest.check(spInstant('2026-08-25', 6));
    check('R-A2 an EXPLICIT empty-string subject on an otherwise-unchanged ask still does NOT re-post',
      stillEmptySubject.posted === false && stillEmptySubject.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 4,
      { reason: stillEmptySubject.reason, records: outbox.query({ kind: 'digest' }).length });

    asks = [ask('1724508123.123456', 'draft-seat', 'which binder — vault path or repo path?', spInstant('2026-08-24', 7),
      { goal: 'demo-goal', link: 'https://slack.example/archives/Cgoal/pNEW', subject: 'which folder should the vault docs live in?' })];
    const subjectAppears = await digest.check(spInstant('2026-08-25', 8));
    check('R-A2 the SAME ask acquiring a real subject (asks-repost updating an already-open ask) posts EXACTLY ONE re-post',
      subjectAppears.posted === true && outbox.query({ kind: 'digest' }).length === 5,
      { records: outbox.query({ kind: 'digest' }).length });

    const afterSubjectStable = await digest.check(spInstant('2026-08-25', 10));
    check('R-A2 and NONE after — the same subject at the next slot posts nothing',
      afterSubjectStable.posted === false && afterSubjectStable.reason === 'unchanged'
      && outbox.query({ kind: 'digest' }).length === 5,
      { reason: afterSubjectStable.reason, records: outbox.query({ kind: 'digest' }).length });

    check('§5 every digest post goes through the outbox with kind=digest into the SYSTEM channel only',
      outbox.query({ kind: 'digest' }).every((r) => r.channel_id === SYS && r.thread_ts === null && r.goal_id === null)
      && outbox.query({}).length === outbox.query({ kind: 'digest' }).length,
      { kinds: [...new Set(outbox.query({}).map((r) => r.kind))] });
  }

  // ── R-A2 / `digest-sentence`: the "waiting on you" list, order and rendering ─────────────────
  {
    const slack = mockSlack();
    const outbox = createOutbox({ storePath: path.join(dir, 'outbox-b.json'), send: slack.send });
    const digest = createSystemDigest({
      post: outbox.post,
      systemChannelId: SYS,
      statePath: path.join(dir, 'digest-b.json'),
      readOpenAsks: () => [
        // No `subject` — a pre-existing row (interface contract: empty string) falls back to
        // `one_liner`. Also no `goal` — falls back to the id suffix as the lead/link text.
        ask('1724508123.123456', 'draft-seat', 'which binder for the vault path?', spInstant('2026-08-24', 11),
          { link: 'https://slack.example/archives/Cgoal/p123', evidence_pointer: '.rbtv/goals/demo/plan.md' }),
        // A real `subject` and `goal` — the goal name is the link text, the subject is the sentence.
        ask('1724509999.654321', 'leader', 'drop lane or pause goal?', spInstant('2026-08-24', 13, 20),
          { link: 'https://slack.example/archives/Cgoal/p654', goal: 'demo-goal', subject: 'the leader seat keeps failing to start' }),
      ],
      readOpenConditions: () => [{
        signature: 'frozen:ignite-engine',
        condition: 'running, no live seat, no eligible launch, no open ask, not paused',
        subject: 'ignite-engine',
        first_emitted_at: spInstant('2026-08-24', 13),
        goal_id: 'ignite-engine',
        channel_id: 'Csys',
      }],
    });
    const res = await digest.check(spInstant('2026-08-24', 14));
    const text = slack.posts[0].text;
    const iAsks = text.indexOf('Waiting on you (2):');
    const iCond = text.indexOf('Open conditions');
    // The trailing `Links` section (absolute VPS paths, unclickable on a phone) was already gone
    // (owner ruling `d-digest-ui`); order is header → asks → conditions.
    check('§5 field ORDER is the plain-language header → asks → conditions, and the Links section stays gone',
      iAsks > 0 && iCond > iAsks && !text.includes('Links') && !text.includes('❓ open asks'), { iAsks, iCond });

    check('R-A2 a goal-less, subject-less ask row is <link|id-suffix> — one_liner · waiting Xh, no LANE/seat/ref',
      text.includes('• <https://slack.example/archives/Cgoal/p123|123456> — which binder for the vault path? · waiting 3h'),
      { row: text.split('\n').find((l) => l.includes('123456')) });

    check('R-A2 a goal+subject ask row is <link|goal name> — subject · waiting Xm, and renders whole minutes',
      text.includes('• <https://slack.example/archives/Cgoal/p654|demo-goal> — the leader seat keeps failing to start · waiting 40m'),
      { row: text.split('\n').find((l) => l.includes('demo-goal')) });

    check('R-A2 no row carries the seat token, a bare LANE label, or a trailing `ref` id',
      !text.includes('draft-seat') && !text.includes('leader ·') && !/\bLANE:/.test(text) && !/\bref \d/.test(text), {});

    // A goal-scoped condition now LEADS with its goal, linked to that goal's CHANNEL — not a
    // thread permalink, since a condition carries no thread ts (owner ruling `d-digest-ui` 5(b)).
    // `digest-condition-goal`'s shape — out of `digest-sentence` custody, only proven unchanged.
    check('§5 a goal-scoped condition row is <channel-link|*goal*> · condition · age — digest-condition-goal shape unchanged',
      text.includes('• <https://slack.com/archives/Csys|*ignite-engine*> · running, no live seat, no eligible launch, no open ask, not paused · 1h'),
      { row: text.split('\n').find((l) => l.includes('ignite-engine')) });

    check('§5 the post opens with the slot header',
      text.startsWith('*System digest · 14:00*'), { head: text.split('\n')[0], posted: res.posted });
  }

  // ── R-A2 the plain-language empty state ───────────────────────────────────
  {
    const slack = mockSlack();
    const outbox = createOutbox({ storePath: path.join(dir, 'outbox-empty.json'), send: slack.send });
    const digest = createSystemDigest({
      post: outbox.post,
      systemChannelId: SYS,
      statePath: path.join(dir, 'digest-empty.json'),
      readOpenAsks: () => [],
      readOpenConditions: () => [],
    });
    const res = await digest.check(spInstant('2026-08-24', 6));
    const text = slack.posts[0].text;
    check('R-A2 zero open asks renders the plain sentence, not a header + "none open" row',
      res.posted === true && text.includes('Nothing is waiting on you.') && !text.includes('Waiting on you ('),
      { text });
  }

  // ── `d-ask15-blocking-asks-first` — blocking asks sort to the top ─────────
  // No structural field distinguishes a WAITING ask from one that already `proceeded on its
  // default` (checked against `state-store/tables.sql`'s `open_asks` schema and
  // `ask-record.js#listOpenAsks`'s row shape — see `system-digest.js`'s `sortAsksBlockingFirst`
  // comment for the full trail). The sort therefore keys on the rendered `one_liner` text mark
  // `bus-ferry.js#FALLBACK_MARK['default-and-disclose']` already carries — the WEAKEST available
  // key, used only because no stronger one exists.
  {
    const at = spInstant('2026-08-28', 20);
    // Arrival order: informational, blocking, blocking, informational — the exact shape the
    // 2026-08-28 20:00 digest had (9 of 12 lines informational, mixed in with no ordering).
    const interleaved = [
      ask('1724500001.0001', 'draft-seat', '*🧵 draft-seat* — proj-a · ask · #1 · ℹ proceeding on its default', spInstant('2026-08-28', 10)),
      ask('1724500002.0002', 'writer', '*🧵 writer* — proj-b · ask · #2 · ⏸ WAITING ON YOU', spInstant('2026-08-28', 11)),
      ask('1724500003.0003', 'leader', '*🧵 leader* — proj-c · ask · #3 · ⏸ WAITING ON YOU', spInstant('2026-08-28', 12)),
      ask('1724500004.0004', 'planner', '*🧵 planner* — proj-d · ask · #4 · ℹ proceeding on its default', spInstant('2026-08-28', 13)),
    ];
    const text = renderDigest({ at, asks: interleaved, conditions: [], nowMs: at.getTime() });
    // Sliced to the `❓ open asks` section ONLY — `Open conditions`' own "• none open" also
    // starts with `•` and would otherwise pad this list to 5.
    const askLines = text.split('\n').slice(text.split('\n').indexOf('❓ open asks') + 1, text.split('\n').indexOf('Open conditions'))
      .filter((l) => l.startsWith('•'));
    check('§5/ask15 the two WAITING asks sort above the two that already proceeded on a default, arrival order kept within each group',
      askLines.length === 4
      && askLines[0].includes('020002') && askLines[1].includes('030003')
      && askLines[2].includes('010001') && askLines[3].includes('040004'),
      { askLines });

    // STABILITY: two blocking asks arriving Z-then-A, and two informational asks arriving 9-then-1
    // — ids that would swap under ANY id-keyed comparator. Arrival order (array order), not the id,
    // must decide the sub-order.
    const stabilityFixture = [
      ask('z-later-id', 'seatZ', '*🧵 seatZ* — proj-z · ask · #1 · ⏸ WAITING ON YOU', spInstant('2026-08-28', 9)),
      ask('a-earlier-id', 'seatA', '*🧵 seatA* — proj-a · ask · #2 · ⏸ WAITING ON YOU', spInstant('2026-08-28', 10)),
      ask('9-info-first', 'seat9', '*🧵 seat9* — proj-9 · ask · #3 · ℹ proceeding on its default', spInstant('2026-08-28', 11)),
      ask('1-info-second', 'seat1', '*🧵 seat1* — proj-1 · ask · #4 · ℹ proceeding on its default', spInstant('2026-08-28', 12)),
    ];
    const sorted = sortAsksBlockingFirst(stabilityFixture);
    check('§5/ask15 sort is STABLE — arrival order survives within each group even against a reverse-alphabetical id',
      sorted.map((a) => a.id).join(',') === 'z-later-id,a-earlier-id,9-info-first,1-info-second',
      { order: sorted.map((a) => a.id) });

    // The R-A2 row shape is untouched by the sort itself: link-as-tap-target still renders exactly
    // as the "order and rendering" block above proves — this only checks the sort does not smuggle
    // in a shape change on a row that also has a link.
    const shaped = [
      ask('1724508123.123456', 'draft-seat', '*🧵 draft-seat* — · ⏸ WAITING ON YOU', spInstant('2026-08-28', 17),
        { link: 'https://slack.example/archives/Cgoal/p123', evidence_pointer: '.rbtv/goals/demo/plan.md' }),
    ];
    const shapedText = renderDigest({ at, asks: shaped, conditions: [], nowMs: at.getTime() });
    check('§5/ask15 the sorted row keeps R-A2\'s link-as-tap-target shape',
      shapedText.includes('• <https://slack.example/archives/Cgoal/p123|123456> —'),
      { row: shapedText.split('\n').find((l) => l.includes('123456')) });
  }

  // ── §5 the baseline moves only on DELIVERY, and it survives a restart ──────
  {
    const slack = mockSlack();
    const statePath = path.join(dir, 'digest-c.json');
    const storePath = path.join(dir, 'outbox-c.json');
    const asks = [ask('1724508123.777777', 'writer', 'ship it?', spInstant('2026-08-24', 5))];
    const build = () => {
      const outbox = createOutbox({ storePath, send: slack.send });
      return {
        outbox,
        digest: createSystemDigest({
          post: outbox.post, systemChannelId: SYS, statePath,
          readOpenAsks: () => asks, readOpenConditions: () => [],
        }),
      };
    };

    slack.failNext(1);
    const one = build();
    const notAcked = await one.digest.check(spInstant('2026-08-24', 6));
    check('§5 a digest Slack never acked stays pending-delivery and does NOT become the baseline',
      notAcked.posted === true && notAcked.delivered === false
      && one.outbox.query({ state: 'pending-delivery', kind: 'digest' }).length === 1
      && one.digest.lastDelivered() === null,
      { delivered: notAcked.delivered, pending: one.outbox.query({ state: 'pending-delivery' }).length });

    const retried = await one.digest.check(spInstant('2026-08-24', 8));
    check('§5 the next slot re-offers the SAME change because the last DELIVERED payload never moved',
      retried.posted === true && retried.delivered === true && one.digest.lastDelivered() !== null,
      { delivered: retried.delivered });

    // RESTART: a fresh instance reads the persisted baseline and must not re-post the same digest.
    const two = build();
    const afterRestart = await two.digest.check(spInstant('2026-08-24', 10));
    check('§5 a RESTART does not re-post an unchanged digest — the baseline is persisted',
      afterRestart.posted === false && afterRestart.reason === 'unchanged'
      && JSON.parse(fs.readFileSync(statePath, 'utf8')).version === 1,
      { reason: afterRestart.reason, state: Object.keys(JSON.parse(fs.readFileSync(statePath, 'utf8'))) });
  }

  // ── §5 the alarm registry is READ, and its absence is not a crash ─────────
  {
    const slack = mockSlack();
    const outbox = createOutbox({ storePath: path.join(dir, 'outbox-d.json'), send: slack.send });
    const digest = createSystemDigest({
      post: outbox.post, systemChannelId: SYS, statePath: path.join(dir, 'digest-d.json'),
      readOpenAsks: () => [ask('1724508123.888888', 'writer', 'go?', spInstant('2026-08-24', 5))],
      // readOpenConditions deliberately NOT passed — the registry interface is not landed.
    });
    const res = await digest.check(spInstant('2026-08-24', 12));
    check('§5 with NO alarm-registry reader wired the digest reads an EMPTY condition set and does not crash',
      res.posted === true && slack.posts[0].text.includes('Open conditions')
      && slack.posts[0].text.includes('• none open'),
      { hasConditionsSection: slack.posts[0].text.includes('Open conditions') });

    const src = fs.readFileSync(path.join(__dirname, '..', 'system-digest.js'), 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
    check('§5 NO emitter implementation lives in the digest — it only reads',
      !/emitAlarm|signature[^\n]*emit|\bemit\s*\(/.test(src), {});
  }

  // ── §6 the bot status line ────────────────────────────────────────────────
  {
    const nowAt = spInstant('2026-08-24', 14);
    check('§6 the rendered format is exactly `N waiting · oldest Xh · M blocked`',
      renderStatusLine({
        asks: [{ opened_at: spInstant('2026-08-24', 10) }, { opened_at: spInstant('2026-08-24', 12) }, { opened_at: spInstant('2026-08-24', 13) }],
        blocked: 1,
        nowMs: nowAt.getTime(),
      }) === '3 waiting · oldest 4h · 1 blocked',
      { rendered: renderStatusLine({ asks: [{ opened_at: spInstant('2026-08-24', 10) }], blocked: 1, nowMs: nowAt.getTime() }) });

    check('§6 the ZERO case renders `0 waiting · oldest 0h · 0 blocked`',
      renderStatusLine({ asks: [], blocked: 0, nowMs: nowAt.getTime() }) === '0 waiting · oldest 0h · 0 blocked',
      { rendered: renderStatusLine({ asks: [], blocked: 0, nowMs: nowAt.getTime() }) });

    check('§6 `oldest Xh` is WHOLE hours (floored), never rounded up',
      renderStatusLine({ asks: [{ opened_at: new Date(nowAt.getTime() - 119 * 60000) }], blocked: 0, nowMs: nowAt.getTime() })
        === '1 waiting · oldest 1h · 0 blocked', {});

    const written = [];
    const asks = [{ opened_at: spInstant('2026-08-24', 11) }];
    let blocked = 2;
    const line = createStatusLine({
      readOpenAsks: () => asks,
      readBlockedCount: () => blocked,
      setStatusText: async (t) => { written.push(t); },
      now: () => nowAt,
    });

    check('§6 the trigger set is EXACTLY the seven listed events',
      TRIGGERS.length === 7 && TRIGGERS.join(',')
        === 'ask-minted,ask-answered,ask-closed,blocked-on-human-stamp,blocked-on-human-clear,pause-succeeded,resume-succeeded',
      { triggers: TRIGGERS });

    const results = [];
    for (const t of TRIGGERS) results.push(await line.onTrigger(t));
    check('§6 each of the SEVEN triggers updates the bot status text',
      results.length === 7 && results.every((r) => r.updated === true) && written.length === 7
      && written.every((t) => t === '1 waiting · oldest 3h · 2 blocked'),
      { updates: written.length, sample: written[0] });

    const before = written.length;
    const others = [];
    for (const e of ['tick', 'digest-posted', 'seat-launched', 'ask-posted', 'pause-refused', '', null]) {
      others.push(await line.onTrigger(e));
    }
    check('§6 NO other event updates it — a tick, a post, a seat launch and a FAILED pause change nothing',
      others.every((r) => r.updated === false && r.reason === 'not-a-trigger') && written.length === before,
      { attempted: others.length, writesAfter: written.length });

    blocked = 0;
    await line.onTrigger('blocked-on-human-clear');
    check('§6 `M blocked` is lanes stamped blocked-on-human PLUS paused goals, recomputed at each trigger',
      line.current() === '1 waiting · oldest 3h · 0 blocked', { current: line.current() });

    // It never posts: the module is handed no outbox, no channel and no transport at all.
    const src = fs.readFileSync(path.join(__dirname, '..', 'status-line.js'), 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
    check('§6 the status line can never produce a channel post — no outbox, no post, no channel in its source',
      !/require\(['"]\.\/outbox|\bpost\s*\(|channel_id|postMessage/.test(src), {});

    const noPort = createStatusLine({ readOpenAsks: () => asks, now: () => nowAt });
    const degraded = await noPort.onTrigger('ask-minted');
    check('§6 with no status port wired it degrades loudly and posts nothing',
      degraded.updated === false && degraded.reason === 'no-status-port' && typeof degraded.text === 'string',
      { reason: degraded.reason, text: degraded.text });
  }

  try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-glance', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-glance EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-glance EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});

'use strict';

// HARNESS RESOLUTION ON THE REPLY LEG — the 2026-08-12 whole-log-dump defect, made falsifiable.
//
// THE INCIDENT THIS IS BUILT FROM (root-cause report 2026-08-12, goal-channel campaign): the
// bridge's enqueue path wrote the LEGACY profile NAME `claude-sonnet` into `jobs_log.profile`.
// `normalizeLog` picked its extractor by STRICT equality on the first `/` segment, so
// `'claude-sonnet' !== 'claude'` fell to the default arm — `lines.join('\n')` — and the ENTIRE
// stream-json session log became "the reply". Three consequences, all observed live, all asserted
// below:
//   • the fence check then ran on the whole log, reported `no-fence`, and REVIVED agents whose
//     replies were perfectly fenced — two duplicate sessions and two duplicate Slack posts per
//     conversation;
//   • the force-delivery clamped from the HEAD, so what the owner actually received was 3518 bytes
//     of SessionStart hook banner, cut mid-word;
//   • nothing in the log said any of it had happened.
//
// The probe drives the three PURE functions the leg composes — no daemon, no Slack, no mock stack;
// probe-chat-reply-leg.js already owns the wired driver. Legs:
//   (a) the legacy slashless name `claude-sonnet` reaches the CLAUDE arm — the exact regression;
//   (b) the post-abolition `harness/model` key reaches it too, model literal and all;
//   (c) neither delivers a byte of the hook banner (the whole-log dump, asserted by absence);
//   (d) the codex arm is UNCHANGED (this change must not move it);
//   (e) a KNOWN plain-text harness still reads the log as text, and fires NO warn;
//   (f) an UNRECOGNIZED value is LOUD and still finds the reply via the structured extractor;
//   (g) an unrecognized value with no result event returns raw text AND flags `rawFallback` — the
//       signal the revive gate reads so a correct agent is never blamed for the bridge's miss;
//   (i) a NULL profile — the shape a FAILED spawn leaves in jobs_log — takes the same loud path;
//   (h) clampBestEffort keeps the TAIL: the reply survives the bound, the banner is what is cut.
//
// MUTATION EVIDENCE — each guard is provable:
//   • restore `harness === 'claude'` strict equality → (a) fails (raw log, no fence);
//   • drop the `notify` call on the unrecognized path → (f)/(g) fail (silent fall-through);
//   • return `plain()` before trying the structured extractor when unrecognized → (f) fails;
//   • flag `rawFallback` on the known plain-text arm → (e) fails (opencode would stop being revived);
//   • restore `s.slice(0, MAX)` in clampBestEffort → (h) fails (banner delivered, reply cut).

const path = require('node:path');
const fs = require('node:fs');
const { normalizeLog, checkReplyContract, bestEffortText, FENCE_OPEN, FENCE_CLOSE } = require('../reply-leg');

const OUT = path.join(__dirname, 'probe-chat-reply-harness.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence }); };

// ── the synthetic log, shaped like the real one ──────────────────────────────
// A ponytail-hook SessionStart banner is what the owner received; it is long on purpose, so a
// head-clamp and a tail-clamp cannot produce the same bytes.
const BANNER = ('PONYTAIL MODE ACTIVE — level: full. You are a lazy senior developer. '.repeat(120)).trim();
const REPLY = `*Interactive or autonomous?*\n\nThe goal is scaffolded. Say _interactive_ or _autonomous_ and I create it.`;
const FENCED = `${FENCE_OPEN}\n${REPLY}\n${FENCE_CLOSE}`;

const claudeLog = [
  JSON.stringify({ type: 'system', subtype: 'init', session_id: 'abc', tools: ['Read', 'Bash'] }),
  JSON.stringify({ type: 'user', message: { content: [{ type: 'text', text: BANNER }] } }),
  JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text: 'thinking about it' }] } }),
  JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: FENCED }),
];
const codexLog = [
  'Reading prompt from stdin...',
  JSON.stringify({ type: 'item.completed', item: { type: 'agent_message', text: FENCED } }),
];
const plainLog = ['\x1b[36mopencode\x1b[0m starting', BANNER, ...FENCED.split('\n')];
const textlessLog = [JSON.stringify({ type: 'system', subtype: 'init' }), BANNER];

// `notify` is the leg's warn hook; capture what it was told rather than what it printed.
function run(lines, profile) {
  const events = [];
  const text = normalizeLog(lines, profile, (ev) => events.push(ev));
  return { text, events, verdict: checkReplyContract(text) };
}

// (a) THE REGRESSION. The live value, verbatim.
const legacy = run(claudeLog, 'claude-sonnet');
check('a: the legacy slashless name `claude-sonnet` reaches the claude arm and the fence is found',
  legacy.verdict.ok === true && legacy.verdict.body === REPLY && legacy.events.length === 0,
  { body: legacy.verdict.body, problems: legacy.verdict.problems, events: legacy.events });

// (b) the post-abolition key shape, model literal included.
for (const key of ['claude/claude-haiku-4-5', 'claude/claude-opus-5', 'claude-haiku-4-5']) {
  const r = run(claudeLog, key);
  check(`b: \`${key}\` reaches the claude arm and the fence is found`,
    r.verdict.ok === true && r.verdict.body === REPLY, { key, body: r.verdict.body });
}

// (c) THE WHOLE-LOG DUMP, asserted by absence — this is what actually reached the owner.
check('c: no claude-arm delivery carries a byte of the session banner or of the raw JSON',
  !legacy.verdict.body.includes('PONYTAIL MODE ACTIVE') && !legacy.verdict.body.includes('"type":"system"')
  && legacy.verdict.body.length < 500,
  { chars: legacy.verdict.body.length });

// (d) codex UNCHANGED.
const codex = run(codexLog, 'codex/gpt-5.5');
const codexLegacy = run(codexLog, 'codex-gpt-5');
check('d: the codex arm still extracts the last agent_message, on both key shapes',
  codex.verdict.ok === true && codex.verdict.body === REPLY
  && codexLegacy.verdict.ok === true && codexLegacy.verdict.body === REPLY,
  { body: codex.verdict.body, legacyBody: codexLegacy.verdict.body });

// (e) a KNOWN plain-text harness reads the log as text and is NOT warned about — its missing fence
// is genuinely the agent's, so the revive path must stay open for it.
const oc = run(plainLog, 'opencode/zai-coding-plan/glm-5.2');
const ocLegacy = run(plainLog, 'opencode-glm-5-2');
check('e: a known plain-text harness reads the whole log, finds the fence, and fires NO warn',
  oc.verdict.ok === true && oc.verdict.body === REPLY && oc.events.length === 0
  && ocLegacy.verdict.body === REPLY && ocLegacy.events.length === 0,
  { body: oc.verdict.body, events: oc.events.concat(ocLegacy.events) });

// (f) UNRECOGNIZED — loud, and still correct. This is the arm the defect fell into silently.
const junk = run(claudeLog, 'wat-9000/mystery-model');
check('f: an unrecognized harness warns AND still recovers the fenced reply via the result event',
  junk.verdict.ok === true && junk.verdict.body === REPLY
  && junk.events.length === 1 && junk.events[0].rawFallback === false
  && junk.events[0].profile === 'wat-9000/mystery-model',
  { body: junk.verdict.body, events: junk.events });

// (g) UNRECOGNIZED with nothing structured in it: raw text is returned, but FLAGGED — the flag is
// what stops the leg reviving an agent for a fence the bridge never looked for properly.
const blind = run(textlessLog, '');
check('g: an unrecognized harness with no result event returns raw text FLAGGED rawFallback',
  blind.text !== null && blind.text.includes('PONYTAIL MODE ACTIVE')
  && blind.verdict.ok === false && blind.verdict.problems[0].issue === 'no-fence'
  && blind.events.length === 1 && blind.events[0].rawFallback === true,
  { chars: blind.text && blind.text.length, events: blind.events, problems: blind.verdict.problems });

// (i) A NULL PROFILE IS A REAL LIVE INPUT, not a defensive nicety. `heart-store.js#fireQueueRow`
// inserts the `launching` row with a NULL profile; only a SUCCESSFUL spawn fills in the resolved
// spec key. A spawn that FAILED (uncast seat, refused launch) therefore reaches this leg with
// `statusRes.result.profile` null/undefined — and that must land on the loud path with the
// structured extractor tried FIRST, never on a silent whole-log dump.
for (const missing of [null, undefined]) {
  const r = run(claudeLog, missing);
  check(`i: a ${missing === null ? 'null' : 'undefined'} profile (failed spawn) warns AND still recovers the fenced reply`,
    r.verdict.ok === true && r.verdict.body === REPLY
    && r.events.length === 1 && r.events[0].rawFallback === false && r.events[0].profile === ''
    && !r.verdict.body.includes('PONYTAIL MODE ACTIVE'),
    { body: r.verdict.body, events: r.events });
}

// (h) THE CLAMP. Best-effort on a raw log must carry the END of it — the answer is what a turn ends
// on. Head-clamping is what put 3518 bytes of banner in the owner's thread.
const longBody = `${BANNER}\n${REPLY}`;
const clamped = bestEffortText(longBody);
check('h: best-effort clamps from the TAIL — the reply survives, the banner is what is cut',
  longBody.length > 3500 && clamped.includes('… (truncated)') && clamped.includes('Say')
  && !clamped.startsWith('⚠ unformatted reply — PONYTAIL'),
  { bodyChars: longBody.length, head: clamped.slice(0, 80), tail: clamped.slice(-60) });

const pass = checks.length > 0 && checks.every((c) => c.pass);
const wallMs = Date.now() - t0;
const exit = pass ? 0 : 1;
fs.writeFileSync(OUT, JSON.stringify({
  summary: { probe: 'probe-chat-reply-harness', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
  entries: checks,
}, null, 2) + '\n');
process.stdout.write(`PROBE probe-chat-reply-harness EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
process.exit(exit);

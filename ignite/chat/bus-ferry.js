'use strict';

const { createOutbox } = require('./outbox');
// The §3 approval first message is composed by the module that owns the vocabulary the thread
// parses — never re-spelled here, or the body would publish tokens the parser does not accept.
const { composeApprovalBody } = require('./approval-thread');
// `ask-thread.js#openThread`'s own top/reply split marker (`d-escalation-surface` part 9) — this
// module DECIDES whether a body gets split (only it knows the row); `ask-thread.js` owns the
// mechanics of posting the two messages. One shared constant, never a second copy of the marker.
const { ASK_REPLY_SPLIT } = require('./ask-thread');

// THE BUS FERRY — coordination bus → the owner (a thread in the goal's channel, else his DM).
// One way, outbound only.
//
// The problem it solves (owner-hit 2026-08-06): an agent raises something a human must answer on
// the team-kit coordination bus (`<goal>/coordination/messages.md`) and it sits unread
// until somebody happens to open the file. Nothing pushed it anywhere. This module is that push,
// and ONLY that push: Slack → bus stays the sittings' job.
//
// ⚑ IT CARRIES EXACTLY ONE ADDRESS — `to: owner` (ruling `d-agents-address-owner-not-master`,
// 2026-08-09). `to: master` is NOT a ferry address: an agent may write it only as an ANSWER to
// something master sent, which is bus traffic between seats end to end. See § THE ONE ADDRESS.
//
// ⚑ NO NEW CAPABILITY. The ferry reads workspace FILES and posts OUTBOUND through the
// bridge's existing transport. No gateway intent, no store handle, no listener, no
// write to the bus.
//
// ⚑ CURSOR AT TAIL ON FIRST SIGHT — the rule the whole module exists around. A live
// run's messages.md holds THOUSANDS of rows (5.9 MB / 4817 rows on the run this was
// built against). Ferrying "every row addressed to master" on first sight would dump a
// run's entire history into the owner's phone. So: the FIRST time the ferry sees a run,
// it records the cursor at the CURRENT TAIL and ferries NOTHING. Only rows appended
// after that are the owner's business. The cursor is persisted through the bridge's
// state file, so a restart does not re-arm a flood either.
//
// ⚑ ONE EXCEPTION, AND ONLY ONE (7.546): an execution this process watched BE BORN — enumerated
// open while its messages.md did not exist yet — has no history, so its cursor seeds at 0
// and its first rows DO travel. That first row is a fresh goal's first escalation, and a
// newly scaffolded goal rosters no authority seat to read it.
//
// ⚑ A ROW IS FERRIED ONLY AFTER A CONFIRMED DELIVERY. The cursor advances on
// `delivered: true` — a failed post is retried next pass, bounded, then skipped loudly.
// One undeliverable row must never wedge the ferry behind it forever.
//
// ⚑ EVERY `to: owner` ROW IS GATED, and that REVERSES this module's fail-toward-delivery default
// for exactly one rung: an agent-INITIATED row travels only when the goal is in `interactive`
// execution mode AND the sending seat declares itself human-interactive; otherwise it PARKS on
// the bus and nothing is posted anywhere. Read the gate block below (§ THE TWO GATES) before
// changing anything there — the reversal is an owner ruling with a named cost, not an oversight.
//
// ⚑ AND PAST BOTH GATES, THE SENDING SEAT'S OWN `fallback:` DECIDES WHAT THE ROW IS (7.626, ruling
// `d-s19-fallback-rides-goal-channels`): `park` parks it on the same path the gates use, and the two
// delivered arms are MARKED so the owner can tell "I am waiting on you" from "I have already
// proceeded". See § THE SEAT'S FALLBACK ARM.
//
// ⚑ THE PASS IS TRIGGERED BY inotify AND ALSO BY THE POLL — both, never one (live-session-design.md
// §2). The 15s `setInterval` was the ONLY trigger, so a row waited 0–15s (7.5s on average) before
// anything looked at it, for work that takes milliseconds. `fs.watch` on each goal's
// `coordination/` dir now fires the SAME `_runOnce`, ~200ms after the append. See § THE WATCH.

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_POLL_MS = 15000;
const DEFAULT_WATCH_DEBOUNCE_MS = 200;
const DEFAULT_MAX_ATTEMPTS = 20;      // per-row post retries before skipping it — an ESCALATION
                                       // blocked by an unreachable channel is the one exception:
                                       // it is never capped (`d-escalation-surface` part 6).
const NOTICE_AT_ATTEMPT = 3;          // failed no-channel/resolve-failed attempts before the
                                       // system-channel alarm fires (once — `postUnreachableChannelAlarm`)
const DEFAULT_MAX_BODY_CHARS = 3000;  // phone-first: a bus row can be an essay

// `## 4774 | from: master | to: leader | type: note | 2026-08-06 14:23`
//
// Read the fields BY KEY, never by position. The bus header grammar is deliberately
// ADDITIVE (coord.py `MSG_HEADER`): a new optional field may be inserted BETWEEN two
// existing ones, and `from-pkg:` already sits between `from:` and `to:`. A positional
// regex reads such a row as MALFORMED and drops it — silently, and precisely for the
// cross-package sends this ferry exists to surface. Observed live on
// build-core-daemon-mvp/run-3 #2366, 2026-08-06.
const HEADER_ID_RE = /^## (\d+) \| (.+)$/;

// The header, or null if the line is not one. Only `from` / `to` / `type` are required;
// every other field (`from-pkg`, `re`, `why`, `supersedes`, the trailing timestamp) is
// carried by the grammar and ignored here.
// The ONE unkeyed part the header grammar carries: the trailing wall-clock stamp
// (`coord.py append_message` writes it last). Read BY SHAPE, never by position — this module's
// own additive-grammar rule — because a keyed field may be inserted anywhere before it.
const ROW_STAMP_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/;

function parseHeader(line) {
  const m = line.match(HEADER_ID_RE);
  if (!m) return null;
  const f = {};
  let at = null;
  for (const part of m[2].split(' | ')) {
    const i = part.indexOf(': ');
    if (i > 0) { f[part.slice(0, i)] = part.slice(i + 2).trim(); continue; }
    if (ROW_STAMP_RE.test(part.trim())) at = part.trim();
  }
  if (!f.from || !f.to || !f.type) return null;
  // W4 (adv, C42): `chat-thread` and `deliver` are HEADER MECHANICS now — coord.py's
  // `send --chat-thread/--deliver` writes them as their own header group. Carried here so the two
  // readers below can prefer the header; the body sigils they were before stay as a documented
  // FALLBACK, because rows already on live buses carry only the bracketed form. Sunset: drop the
  // body-sigil leg once no bus in service holds a pre-W4 row.
  return {
    id: Number(m[1]), from: f.from, to: f.to, type: f.type, body: [],
    hdrChatThread: f['chat-thread'] || null,
    hdrDeliver: f.deliver || null,
    hdrApproveCommit: f['approve-commit'] || null,
    at,
  };
}

// ── THE ONE ADDRESS THIS FERRY CARRIES: `owner` (ruling `d-agents-address-owner-not-master`,
// owner, 2026-08-09) ──────────────────────────────────────────────────────────────────────
//
// The closed addressing rule for every agent, which this token IS the mechanical half of:
//   • initiate → `to: owner`
//   • answer   → the asker (master included)
//   • else     → the seat, BY NAME
//
// ⚑ `master` IS NO LONGER A FERRY ADDRESS AT ALL, and the deletion is the point. A row
// `to: master` from an agent is legal ONLY as an ANSWER to something master sent it, so it is
// the bus's business end to end: it takes the ordinary cursor-advance path here, exactly like a
// row addressed to any other seat. That replaced ~90 lines of role-holder machinery — a roster
// liveness read, a `relays:` descriptor read, and holder-name matching — which existed to answer
// "is anybody home to read this `master` row". Nobody asks that question anymore: an
// agent-initiated row is addressed to the OWNER, and whether it reaches him is the two gates'
// question, not a roster's.
//
// ⚑ WHY THE ROLE MACHINERY WENT RATHER THAN GAINING A CASE. It existed because the role word
// and the holder's seat name drifted apart (the `goal-master` rename incident, rows #5585 /
// #5606 / #5616 on 2026-08-07), and the fix was to match both. `owner` cannot drift: it is a
// RESERVED name that no seat may carry (`SAFE_NAME_RE` callers refuse it), so there is no holder
// to name, no roster to consult, and one trivially teachable rule instead of a role-vs-name
// judgment that measurably failed within two hours.
const OWNER_TOKEN = 'owner';

// Does `to:` address the owner? Comma/space tolerant — `owner`, `owner, leader`,
// `leader owner` all match; `goal-owner` does NOT (a token that merely CONTAINS the word is a
// seat name, and seat names are the third arm of the rule above).
function addressesOwner(to) {
  return String(to).split(/[,\s]+/).some((t) => t === OWNER_TOKEN);
}

// A NAME, never a path — for a seat name out of a row's `from:` field and for a goal id out of
// the goals tree alike. A token carrying `..` or a separator would read a descriptor OUTSIDE the
// run (or a file outside `.rbtv/goals/`) and answer a question about the wrong thing. Refused
// here rather than sanitized, for the same reason goal ids are (goal-channel-map.js § header).
//
// ⚑ `owner` IS REJECTED AS A NAME even though its shape passes: it is an ADDRESS, never a seat
// (ruling above), so a descriptor read for a seat called `owner` is a question with no answer.
const SAFE_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

function isSafeName(name) {
  const n = String(name);
  return SAFE_NAME_RE.test(n) && n !== OWNER_TOKEN;
}

// The first `---`-fenced block of a descriptor, or '' when the file does not open with one.
// ⚑ FRONTMATTER ONLY, because that is what the ruling declares the flag lives in: an unscoped
// read would let a seat's PROSE — a line in a briefing that quotes `human-interactive: yes` —
// open gate 1 for a seat nobody declared.
function frontmatterOf(text) {
  const m = String(text).match(/^---\r?\n([\s\S]*?)\r?\n---/);
  return m ? m[1] : '';
}

// ── THE TWO GATES ON AGENT-INITIATED CONTACT (owner ruling 2026-08-09) ────────────────
//
// ⚑ THIS IS THE ONE RUNG WHERE "FAIL TOWARD DELIVERY" IS DELIBERATELY REVERSED, and only
// here. The `[chat-thread:]` return leg below routes a row because it ANSWERS a thread the owner
// wrote in. An agent OPENING a conversation at the owner is a different kind of thing — an
// interruption whose cost lands on a human who may be asleep — so the ratified default is ZERO
// PINGS and these two declarations are what earn one. Owner-INITIATED flows are untouched by
// construction: DMs, mentions, owner replies, and that return leg (which is read BEFORE either
// gate). Since the `owner` ruling the gates apply to EVERY `to: owner` row — there is no
// nobody-home precondition left to qualify them.
//
// Gate 1 — THE SEAT DECLARES ITSELF human-interactive: `human-interactive: yes|true` in its
// `seat.md` FRONTMATTER (one file read, memoized per pass). A seat nobody declared able to talk
// to a human must not be able to.
// Gate 2 — THE GOAL IS IN `interactive` EXECUTION MODE, resolved down a THREE-RUNG LADDER
// (owner ruling 2026-08-10, issue C-4). The two representations of "can this goal talk to the
// owner" were never wired to each other: creation persists `goal-kind: interactive` into
// `goal.md` frontmatter and NO creation path has ever written `execution-mode`, so every
// interactive goal was born with this gate defaulted shut and every ask parked silently.
//   1. `.rbtv/goals/<goal>/execution-mode` present and readable → OBEY IT, exactly as before.
//      ⚑ THE FILE KEEPS PRECEDENCE and that is the whole point of the rung order: it is the
//      PER-RUN POSTURE — the console flow writes `autonomous` there when the owner walks away,
//      and a birth attribute must never override a human saying "not now".
//   2. file ABSENT → the goal's BIRTH ATTRIBUTE, `goal-kind:` in `goal.md` frontmatter. Exactly
//      `interactive` opens the gate; any other value, no key, no frontmatter, no file → rung 3.
//      ⚑ NOT `seat-folder.js#goalKind()`, deliberately: that reader answers "which kind do I
//      treat this goal as" and defaults ABSENCE to `interactive`, which would open this gate for
//      every goal that never declared anything. Here absence must stay shut.
//   3. neither resolves → `autonomous` — the ratified default, untouched, one rung deeper. A
//      goal nobody declared reachable is not reachable; the owner flips it when he is.
//
// ⚑ A BLOCKED ROW PARKS ON THE BUS — it is not re-routed, not downgraded into the owner's DM,
// and not swallowed (ratified). The cursor advances because the row was disposed of BY POLICY
// and is logged as such; the durable record is the goal's own escalation ladder / doubts park,
// which is where an unanswered escalation already belongs. Flipping the mode therefore applies
// to FUTURE rows only, by construction — never a replay of what the gate already parked.
const INTERACTIVE_MODE = 'interactive';
const AUTONOMOUS_MODE = 'autonomous';

function goalExecutionMode(workspaceRoot, goalId) {
  // The goal id is a NAME here too. Today it always arrives from `goalBuses`' own directory
  // listing, but this reader is exported and a future caller could hand it a `to:`/`from:` token
  // — and a traversing id would read `execution-mode` from outside `.rbtv/goals/` entirely,
  // making some unrelated file the gate. Autonomous is the safe answer, as it is for every other
  // cannot-tell here.
  if (!isSafeName(goalId)) return AUTONOMOUS_MODE;
  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', String(goalId));
  let raw;
  try {
    raw = fs.readFileSync(path.join(goalDir, 'execution-mode'), 'utf8');
  } catch { return goalKindMode(goalDir); }
  return raw.trim().toLowerCase() === INTERACTIVE_MODE ? INTERACTIVE_MODE : AUTONOMOUS_MODE;
}

// Rung 2 of the ladder above — the goal's BIRTH ATTRIBUTE, read only when rung 1 found no file.
// The trailing-comment strip and the quote strip are `seat-folder.js#goalKind()`'s, for the reason
// stated there: `goal-kind: interactive # ...` is `interactive` to the `yaml.safe_load` that lints
// it, and two readers of one file free to disagree is a defect with no reporting surface.
function goalKindMode(goalDir) {
  let raw = null;
  try { raw = fs.readFileSync(path.join(goalDir, 'goal.md'), 'utf8'); } catch { /* rung 3 */ }
  const m = raw === null ? null : frontmatterOf(raw).match(/^goal-kind:[ \t]*(.+?)[ \t]*$/m);
  const kind = m ? m[1].replace(/\s+#.*$/, '').trim().replace(/^["']|["']$/g, '').toLowerCase() : '';
  return kind === INTERACTIVE_MODE ? INTERACTIVE_MODE : AUTONOMOUS_MODE;
}

// ⚑ THE CORE TAKES A SEAT DIR, and that is the ONLY shape that answers for every seat there is.
// The `(goalDir, seat)` wrapper below joins `seats/<seat>/`, which is the GOAL-SEAT layout and not
// the only one: a STANDING-SEAT HOME (`planning/materialize-seats.py#standing_seat`, `r-master-seat-homes`)
// IS the seat folder — `seat.md` sits at its root with no `seats/` layer — so `_channel-master`
// only resolves through this entry point. A caller that already holds the seat's own directory
// calls THIS, never the wrapper via a `dirname`² split: that split answered FALSE for the channel
// master, and every ineligibility falls through to the cold path silently (task 7.642).
function seatDirIsHumanInteractive(seatDir) {
  let fm;
  try { fm = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8'); } catch { return false; }
  const m = frontmatterOf(fm).match(/^human-interactive:[ \t]*(.+?)[ \t]*$/m);
  // ⚑ THE STRIP IS `goalKindMode`'s, AND ITS ABSENCE HERE WAS A DEFECT (found by the 7.626 review,
  // F3). `human-interactive: "yes"` and `human-interactive: yes # ratified 2026-08-09` are both
  // TRUE to the `yaml.safe_load` that `component-lint` validates the seat with — so without this
  // the seat passed lint, this predicate read FALSE, and the failure was invisible in both
  // directions at once: the row parked looking correctly gated, the lane watch's undeclared-arm
  // warn never fired, and the declared arm never executed. Two readers of one file free to
  // disagree is a defect with no reporting surface — stated at `goalKindMode`, true of every
  // reader in this module.
  const v = m ? m[1].replace(/\s+#.*$/, '').trim().replace(/^["']|["']$/g, '').toLowerCase() : '';
  return v === 'yes' || v === 'true';
}

// The GOAL-SEAT wrapper: a seat NAME under a goal dir. The `isSafeName` guard is the traversal
// refusal for that name (a `../..` seat would read a `seat.md` outside `.rbtv/goals/` entirely);
// the core above takes an already-resolved directory and has no name to guard.
function seatIsHumanInteractive(goalDir, seat) {
  if (!isSafeName(seat)) return false;
  return seatDirIsHumanInteractive(path.join(goalDir, 'seats', seat));
}

// ── THE SEAT'S FALLBACK ARM (owner ruling `d-s19-fallback-rides-goal-channels`, task 7.626) ──
//
// A `human-interactive:` seat declares, in the SAME frontmatter, what it does when the owner is not
// standing at a terminal — which on the DAEMON lane is always (planning-v4 D14 via D19; the field
// is REQUIRED there, see `meta/planning/references/file-prompt.md` § `fallback`). Until this row the
// field was validated at materialize time by `component-lint`'s `interactive-fallback` check and
// read at run time by NOTHING: all three arms behaved identically — the seat was dispatched
// headless and its ask was delivered if the gates opened, parked if they did not.
//
// THE ARMS DIFFER HERE, at the one surface the ruling names — the goal's channel, thread per agent:
//
//   park                  NOTHING is posted. The row takes the same park the gates take, with the
//                         arm as the reason. ⚠ "PARKS ON THE BUS" IS NOT A QUEUE: the cursor
//                         advances, nothing ever re-delivers the row, and `owner` is a reserved
//                         address with no seat so `coord.py`'s pending view cannot surface it
//                         either. The durable record is the goal's `doubts.md` escalation park —
//                         tier 1 of the ladder, kept for exactly this. The seat proceeds.
//   default-and-disclose  posted into the agent's thread, MARKED as a disclosure — the agent has
//                         proceeded on its stated default and is not waiting on a reply.
//   block-and-queue       posted into the agent's thread, MARKED as blocking — the agent is waiting.
//                         ⚠ PROCEDURALLY, and that DIVERGES from the arm's one-home definition
//                         (`meta/planning/references/file-prompt.md` § fallback: "hold the seat,
//                         queue the question"). Nothing here holds the DAG: a session that exits 0
//                         after asking has its turn recorded `done` and its dependents start. Which
//                         side gives is an open owner decision, filed as a #decision row.
//
// ⚑ `block-and-queue`'s ANSWER LEG IS NOT BUILT HERE — IT ALREADY EXISTS, and that is the whole
// reason this row is a marker and a gate rung rather than machinery. The owner's reply in the
// agent's thread routes `kind: 'agent'` and mints a session HOMED AT THE ASKING SEAT
// (`chat-bridge.js#routeOf` → `forward-path.js`). That revival IS "the seat proceeds".
//
// ⚑ ABSENT IS NOT A FOURTH ARM. A flagged seat with no `fallback:` keeps the behaviour it had —
// delivered, unmarked — because acquiring a new behaviour through a LINT VIOLATION is exactly what
// must not happen. `component-lint` refuses the combination at materialize time; `supervisor/lane-watch.js`
// warns about it at run time. An unrecognised word reads the same way as absent, for the same reason
// every other cannot-tell here does.
//
// ⚑ IT IS THE SEAT'S OWN DECLARATION, SO IT APPLIES ON EVERY LANE. This module has no lane and must
// not grow one. A `park` seat carried in a terminal by the attached lane has its terminal; a bus row
// it ALSO writes `to: owner` parks — which is what it declared its bus questions do. Disclosed
// rather than special-cased.
const FALLBACK_PARK = 'park';
const FALLBACK_ARMS = ['park', 'default-and-disclose', 'block-and-queue'];

// ⚑ THE CORE TAKES A SEAT DIR, `seatDirIsHumanInteractive`'s reason verbatim (task 7.656): the two
// fields are declared in ONE frontmatter block, so a reader of one that cannot see a STANDING-SEAT
// HOME while its sibling can is the 7.642 blind spot rebuilt beside the fix. `_channel-master` sets
// BOTH `human-interactive:` and `fallback:` in the same act (vault commit `1c82a61f1`) — the flag
// now resolves there and the arm did not, so the arm read `null` (absent, delivered unmarked) for
// the one seat the ruling was written for. LATENT when split: no caller holds a standing-seat home
// yet. Split anyway, because the caller that does arrives silently — an unread arm reports nothing.
//
// The declared arm, or null (absent, unreadable, or a word outside the vocabulary). FRONTMATTER
// ONLY, `seatIsHumanInteractive`'s reason verbatim: a briefing line in the descriptor BODY that
// quotes `fallback: park` must not be able to silence a seat nobody declared silent.
function seatDirFallback(seatDir) {
  let fm;
  try { fm = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8'); } catch { return null; }
  const m = frontmatterOf(fm).match(/^fallback:[ \t]*(.+?)[ \t]*$/m);
  const v = m ? m[1].replace(/\s+#.*$/, '').trim().replace(/^["']|["']$/g, '').toLowerCase() : '';
  return FALLBACK_ARMS.includes(v) ? v : null;
}

// The GOAL-SEAT wrapper, `seatIsHumanInteractive`'s exactly: the `isSafeName` guard is the traversal
// refusal for the NAME, and the core above has no name to guard.
function seatFallback(goalDir, seat) {
  if (!isSafeName(seat)) return null;
  return seatDirFallback(path.join(goalDir, 'seats', seat));
}

// Parse a messages.md body into rows. DEFENSIVE by construction: the file is appended
// by live agents, so the tail may be a half-written row.
//
// The torn-write rule: the LAST row is only complete when the file ends with a newline.
// A row that is not complete is left for the next pass — never posted half-read.
// ponytail: newline-terminated is a heuristic, not a lock. A writer that flushes a
// partial line ending in "\n" mid-row would defeat it; the fix then is a real
// end-of-record marker in the bus format, not more parsing here.
function parseMessages(text, onMalformed) {
  const rows = [];
  const complete = text.endsWith('\n');
  const lines = text.split('\n');
  let cur = null;
  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (cur) rows.push(cur);
      // `line.match(re)`, never `re.exec(line)` — probe-chat-boundary's spawn guard
      // matches the literal `.exec(`, and a regex call must not read as a process spawn.
      cur = parseHeader(line);
      if (!cur && onMalformed) onMalformed(line);
      continue;
    }
    if (cur) cur.body.push(line);
  }
  if (cur && complete) rows.push(cur);
  for (const r of rows) r.body = r.body.join('\n').trim();
  return rows;
}

// ── THE RETURN LEG: A ROW THAT NAMES ITS OWN CHAT THREAD ─────────────────────────────
//
// Everything above answers "an agent is addressing the OWNER on its own initiative". This
// answers the OPPOSITE direction, which had no leg at all: a seat ANSWERING the channel-master.
// Owner-ruled 2026-08-07 after both gates of the day were measured refusing it — `to:
// channel-master` matched no address this ferry carried, and no address it could carry would
// have named a Slack thread.
//
// ⚑ THE TOKEN IS THE ADDRESS, NOT A SEAT NAME — deliberately. A `channel-master` literal would
// have made this file know a name; a row carrying `[chat-thread: <channel>:<ts>]` instead states
// WHERE it belongs, so the ferry routes on a declaration the sender made. It is also NOT
// initiation — it answers into a thread the owner wrote in — which is why it is read BEFORE the
// two gates and passes with both of them shut.
//
// ⚑ THE BRACKETS ARE THE LOOP GUARD. `forward-path.js` tells every sitting its own thread
// in the PLAIN form (`chat-thread: <id>`), so a sitting relaying a QUESTION onto the bus can
// name where the answer belongs. Only the BRACKETED form routes. Without that split the
// ferry would read the outbound question as an inbound answer and mint a sitting from it —
// the question arriving back in its own thread. So: plain = "this is which thread I am",
// bracketed = "deliver this INTO that thread", and only a seat answering toward chat writes
// brackets.
//
// ⚑ THE ROUTING SHAPE IS NARROWER THAN THE PROMPT PREFIX, DELIBERATELY. `forward-path.js`
// stamps every sitting with whatever conversation id it has, and a GOAL conversation's id is
// the bare channel (`C0001`) — a goal channel maps 1:1 onto its channel and is never sharded
// by `thread_ts`. This regex requires `<channel>:<ts>`, so a goal sitting's id can never
// route here. That is not an oversight: routing into a goal channel is a different leg (a
// different route kind and a different seat home), and admitting the bare form would mint a
// `kind: 'master'` sitting on a goal's channel. When that leg is wanted, build it — do not
// widen this.
//
// ⚑ FAILS CLOSED. No token, or a malformed one, and this returns null — the row takes the
// unchanged path above. The strict shape is the point: an accidental match would divert a
// row meant for the owner's DM.
const CHAT_THREAD_RE = /\[chat-thread:\s*([A-Z][A-Z0-9_]{2,}:\d+\.\d+)\s*\]/;

function chatThreadToken(body) {
  const m = String(body || '').match(CHAT_THREAD_RE);
  return m ? m[1] : null;
}

// W4 (adv, C42) — the same shape, unbracketed, for the HEADER field. One pattern source, so the
// header leg and the body leg can never disagree about what a thread id looks like.
const THREAD_ID_RE = /^[A-Z][A-Z0-9_]{2,}:\d+\.\d+$/;

// The row's chat thread: HEADER FIRST, body sigil as the documented fallback. Same fail-closed
// posture either way — a malformed header value reads as absent and the body is consulted, exactly
// as a malformed sigil reads as absent today.
function rowChatThread(row) {
  const h = row && row.hdrChatThread;
  if (h && THREAD_ID_RE.test(h)) return h;
  return chatThreadToken(row && row.body);
}

// ── WHAT THE THREAD SHOULD DO WITH THE ROW: `[deliver: post|wake]` (live-session-design.md §3) ──
//
// The return leg above answers WHERE a row goes. This answers WHAT HAPPENS THERE, and it exists
// because an ASYNC JOB's settled outcome and a SEAT'S ANSWER want opposite things from the same
// thread:
//
//   · a seat answering the owner wants an AGENT to handle its row — that is the 2026-08-07 ruling
//     the return leg was built for, verbatim: "the owner asked that the answer reach the
//     CHANNEL-MASTER, not that a raw bus row be pushed at him". So the bridge mints a sitting on
//     the named thread and posts NOTHING.
//   · a settled job's outcome ("the switch applied, restarting now") is a FACT, complete as
//     written. Routing it through an LLM turn costs a whole sitting (~12s) to re-say a line the
//     tool already composed, and issue `i-no-completion-nudge` is that the owner is not told —
//     not that nobody paraphrased it for him.
//
//   absent   the mint, exactly as ruled 2026-08-07. EVERY producer that predates this token keeps
//            its behaviour with no edit — the default is the old path, deliberately.
//   post     the row is POSTED into the thread verbatim and NO sitting is minted. No agent, no
//            inference, ~0.3s. This is design §3(a).
//   wake     posted verbatim AND a sitting is minted with the row as its prompt — for a settled
//            job that carries a follow-up somebody must ACT on. This is design §3(b).
//
// ⚑ IT IS READ ONLY BESIDE A `[chat-thread:]` TOKEN. On its own it names no destination, so it is
// not a second routing surface — the ferry hands it to the bridge with the thread or not at all.
// An unrecognised word reads as absent, the same way every other cannot-tell in this module does.
const DELIVER_RE = /\[deliver:\s*(post|wake)\s*\]/;

// ── `approve-commit: <sha>` — THE ROW THAT OPENS AN APPROVAL THREAD ───────────────────────────
//
// A `to: owner` row carrying this header key is the plan's APPROVAL ASK: the bridge opens it with
// `kind: 'approval'` and a one-word `approve` in that thread starts execution [D12]. Its AUTHORITY
// was already checked at the one door that can check it — `coord.py cmd_send`, where identity is
// resolved (a `human-interactive:` seat, an approve-package on the goal, and this exact
// `bound_commit`; no `--force`). Re-asking here would be a second, weaker authority over the same
// irreversible door.
//
// ⚑ HEADER ONLY, and NO body-sigil fallback — deliberately unlike `chat-thread`/`deliver`. Those
// two had a live body form predating their header key; this one is new, so admitting a body sigil
// would invent a route in which text an agent typed into a digest opens execution.
//
// ⚑ FAILS CLOSED ON A MALFORMED VALUE, and the row still goes out as an ORDINARY ask: the owner
// gets his question, and the thread simply does not carry the irreversible verb. The alternative —
// treating an unparseable sha as an approval — would post `Bound commit: <garbage>`.
const APPROVE_COMMIT_RE = /^[0-9a-f]{7,64}$/;

function rowApproveCommit(row) {
  const raw = row && row.hdrApproveCommit;
  if (!raw || !APPROVE_COMMIT_RE.test(String(raw).trim())) return null;
  return String(raw).trim();
}

function deliverToken(body) {
  const m = String(body || '').match(DELIVER_RE);
  return m ? m[1] : null;
}

// W4 (adv, C42) — header first, body sigil as the fallback. An unrecognised header word reads as
// absent and the body is consulted, matching `deliverToken`'s own cannot-tell posture.
function rowDeliver(row) {
  const h = row && row.hdrDeliver;
  if (h === 'post' || h === 'wake') return h;
  return deliverToken(row && row.body);
}

// The Slack message: one mrkdwn header line, then the body. Truncation cuts at a LINE
// boundary so a wrapped table or list never ends mid-token, and names where the full
// text lives.
//
// ⚑ `agentLead` IS THE AGENT-THREAD HEADER, and the lead position is the whole point: the
// first message of an agent's own thread must state WHO IS TALKING (ratified 2026-08-09), and
// in a goal channel the goal is the room — so the goal/run/`from` triple that a DM needs to be
// legible is redundant there, while the agent's name is what the owner is looking for. Same
// body, same truncation; only the header line differs.
//
// ⚑ `arm` IS THE SENDING SEAT'S FALLBACK, RENDERED FOR THE OWNER (7.626). The two delivered arms
// ask two different things of him — `block-and-queue` is waiting on his reply, `default-and-disclose`
// has already proceeded and is telling him so — and a phone notification that does not say which is
// a question he cannot triage. `park` never reaches here (it is a gate reason), and an undeclared
// arm renders EXACTLY the pre-7.626 header, which is what keeps a lint violation behaviour-neutral.
const FALLBACK_MARK = {
  'block-and-queue': ' · ⏸ WAITING ON YOU',
  'default-and-disclose': ' · ℹ proceeding on its default',
};

// ── THE ASK BODY SPLIT (owner ruling `d-escalation-surface` part 9) ────────────────────────────
// Top level: the decision + TLDR + alternatives. First threaded reply: the full reasoning and the
// evidence pointer. This module composes the ask body and is the only place that knows whether the
// seat actually wrote that shape, so a fabricated split is worse than none: a body with no
// discernible "Reasoning:" / "Full reasoning:" heading is left WHOLE — everything above the fold,
// nothing in the reply. `ASK_REPLY_SPLIT` is `ask-thread.js#openThread`'s own marker; it is never
// rendered, only found there.
const REASONING_HEADING_RE = /^\*{0,2}(full reasoning|reasoning|evidence)\*{0,2}:?\s*$/im;

function splitAskBody(text) {
  const body = String(text || '');
  const m = body.match(REASONING_HEADING_RE);
  if (!m) return body;
  const idx = body.indexOf(m[0]);
  return `${body.slice(0, idx).trimEnd()}\n${ASK_REPLY_SPLIT}\n${body.slice(idx)}`;
}

function formatMessage(row, { goalId, stamp, relPath, maxBodyChars = DEFAULT_MAX_BODY_CHARS, agentLead = false, arm = null, ownerUser = null }) {
  // `Object.hasOwn`, never a truthiness test on the lookup: `arm` reaches an EXPORTED function's
  // parameter, and `constructor` is a legal kebab-case word that walks the prototype chain — a bare
  // `FALLBACK_MARK[arm]` renders `function Object() { [native code] }` into the owner's Slack header.
  // The store's own `Object.hasOwn` reason, at a surface that leaves the process (review F5).
  const mark = Object.hasOwn(FALLBACK_MARK, arm) ? FALLBACK_MARK[arm] : '';
  const header = (agentLead
    ? `*🧵 ${row.from}* — ${goalId} · ${row.type} · #${row.id}`
    : `*bus → you* — ${goalId}/${stamp} · from ${row.from} · ${row.type} · #${row.id}`) + mark;
  // ⚑ ASK-IN-THREAD PINGS THE OWNER. A channel post without `<@id>` is silent on his phone
  // (measured 2026-08-18). Only type=ask on the agent-thread header; status/FYI/answer stay
  // unmentioned. Unset id → no ping, never a throw.
  const ping = (agentLead && row.type === 'ask' && typeof ownerUser === 'string' && ownerUser)
    ? `<@${ownerUser}> `
    : '';
  let body = row.body;
  if (body.length > maxBodyChars) {
    const cut = body.slice(0, maxBodyChars);
    const nl = cut.lastIndexOf('\n');
    body = (nl > 0 ? cut.slice(0, nl) : cut) + `\n… (truncated — full text: ${relPath} #${row.id})`;
  }
  return ping + (body ? `${header}\n${body}` : header);
}

// ── THE ESCALATION MARKER IN AN OPEN ASK'S ONE-LINER (`d-escalation-surface` part 8) ───────────
//
// `open_asks` (`state-store/tables.sql`) carries no column that tells an escalation apart from any
// other `label: 'recovery'` row — that label is a two-value DIGEST TAXONOMY
// (`work-content`/`recovery`), shared by an escalation, an ordinary admitted `leader` message, and
// a daemon-decided exhausted-lane ask (`recovery-poster.js`, `kind: 'recovery'`). `kind:
// 'escalation'` IS computed, right here in this module (`isEscalation`, below), and reaches
// `ask-thread.js#postAsk` — but only for the [T2-R14] DOOR; `state-store/heart/ask-record.js
// #openAsk` never receives it and the row is never stamped with it. Adding a column is an
// owner-gated schema change (out of this seat's custody) and is NOT made here — see the seat's own
// report for the proposed one.
//
// THE ONE SIGNAL THAT DOES SURVIVE TO DISK: the ask's own header, composed by `formatMessage`
// above (`agentLead` branch) as `... · ${row.type} · #...` — literally the word "escalation" for
// an escalation row, since `postAsk`'s `body` is always `splitAskBody(formatMessage(row, {...,
// agentLead: true, ...}))` (the row loop, below) and `splitAskBody` never touches the header line.
// `state-store/heart/ask-record.js#listOpenAsks` reads that header back as `one_liner` (the ask
// copy's first non-empty line) for the fleet-wide digest read this module's own gate re-uses.
// This is the SAME weakest-available text-marker fallback `system-digest.js#sortAsksBlockingFirst`
// already uses for its own missing structural field (`d-ask15-blocking-asks-first`), not a new
// pattern — and it carries the same fragility: reword the `agentLead` header format and this marker
// goes stale silently. Grep both together before editing either.
const ESCALATION_ONE_LINER_MARK = ' · escalation · #';
function isEscalationOneLiner(oneLiner) {
  return typeof oneLiner === 'string' && oneLiner.includes(ESCALATION_ONE_LINER_MARK);
}

// ── THE FINISH EDGE'S ONE CHANNEL POST [T5-R16, spec-owner-io §1] ────────────────────────────
//
// A goal that finished told NOBODY. The finish edge fires (`coord.py records.py#cmd_finish_goal`),
// the room is torn down, the banner is stamped — and the owner learned it from nothing, because
// the row the edge appends is `to: all` and this ferry carried exactly one address. Measured on
// `seat-cage-tool-inventory`, finished 2026-08-28 01:31Z: the row is on the bus, `outbox.json`
// holds no `completion`, and neither the goal channel nor the DM ever saw a word. The gap was
// even NAMED in this file — `issue i-no-completion-nudge` at § `[deliver:]` — as a thing nobody
// had built.
//
// ⚑ IT IS A NOTIFICATION, NEVER AN ASK [T2-R16]. It does not go through `postAsk`: that door
// MINTS AN ASK RECORD, which suspends the kill clock and reads as open forever in the digest and
// the status count — a completion nobody can answer would sit there as an unanswered question.
// It is a TOP-LEVEL post in the goal's own channel [T5-R11], not a reply in any agent's thread:
// the goal ending is the room's news, not one seat's message.
//
// ⚑ AND NEVER A DM. The owner's DM carries NO goal traffic at all — not this, not an escalation,
// not an alarm (`d-escalation-surface` part 4; the DM is only for conversations the owner starts
// himself). Goal business goes to the goal's own channel; a daemon-level fault — including a
// goal's channel being unreachable — goes to the system channel instead, never the DM.
// No channel → the row is held and retried by the ordinary ladder, and the missing-channel
// SYSTEM-CHANNEL ALARM is deliberately NOT fired for it (see its call site) — a goal that finished
// is not a blocked escalation, and inventing a second alarm shape for it is not this seat's job.
//
// ⚑ WHAT MAKES A `completion` ROW THE FINISH EVENT IS THE MARKER, NOT THE TYPE. Every seat sends
// `--type completion` when its briefing is done — those are the bus's ordinary traffic and must
// post nothing. The finish EVENT is a `completion` whose body OPENS with `FINISH_MARKER`, which
// is `records.py`'s own closed convention (`goal_finished()` reads the log exactly this way).
// ⚠ THE STRING IS DUPLICATED ACROSS TWO LANGUAGES and there is no shared constant to import.
// `probe-chat-bus-ferry.js` PINS the two against each other by reading `records.py` — if that
// check ever reddens, the marker moved and this reader went blind, not the other way round.
const FINISH_MARKER = 'goal-finished: the finish edge fired';

// ⚑ AND THE SENDER MUST BE THE LEADER'S CHAIR. `records.py#LEADER_CHAIR` is a closed constant —
// the chair a taskforce names its leader is always literally `leader` — and `cmd_finish_goal`
// refuses every other seat where the taskforce names one. This reader re-asks the question
// because the SEND door does not: nothing in `coord.py cmd_send` guards the marker, so any seat
// can put that string in a `--type completion` body. Re-checking an authority already checked is
// normally a second, weaker door (see § `approve-commit`); here it is the ONLY door, because the
// row is text a seat typed rather than an act a verb performed.
// ⚠ THE COST, NAMED: a goal whose taskforce names NO leader (a team-kit run, a console package)
// may be finished by another chair, and its notice is NOT posted — one log line, cursor advanced.
// Fail-closed is the right direction here: the alternative is any seat announcing to the owner's
// channel that his goal is over.
const LEADER_CHAIR = 'leader';

function isFinishRow(row) {
  return Boolean(row) && row.type === 'completion' && String(row.body || '').startsWith(FINISH_MARKER);
}

// A goal's own CSV register, read by HEADER NAME. A row whose field count does not match the
// header is SKIPPED, never read by index: a quoted field carrying a comma would be attributed to
// the wrong column, and a headline number the owner reads must not be a misparse. Returns [] for
// an absent file, an empty one, or one missing any column asked for — "no numbers" is a truthful
// answer and a guessed one is not.
function readCsvRows(file, needed) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return []; }
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  if (lines.length < 2) return [];
  const header = lines[0].split(',');
  const idx = {};
  for (const k of needed) {
    const i = header.indexOf(k);
    if (i < 0) return [];
    idx[k] = i;
  }
  const out = [];
  for (const line of lines.slice(1)) {
    const f = line.split(',');
    if (f.length !== header.length) continue;
    const r = {};
    for (const k of needed) r[k] = f[idx[k]].trim();
    out.push(r);
  }
  return out;
}

// `Xh Ym` / `Xm`, or null when the two stamps do not make a forward span. NULL IS A REAL ANSWER:
// `executions.csv` carries rows whose `ended` precedes their `started` (a crash-swept row), and a
// negative duration printed at the owner is worse than no duration at all.
function humanSpan(fromIso, toIso) {
  const a = Date.parse(fromIso);
  const b = Date.parse(toIso);
  if (!Number.isFinite(a) || !Number.isFinite(b) || b < a) return null;
  const mins = Math.round((b - a) / 60000);
  return mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;
}

// LINE 2 — the headline numbers, and every one of them is COUNTED off the goal's own
// `executions.csv` (the completion authority both the daemon and the operator read). Seats that
// RAN, not seats that were staffed: `taskforce.csv` answers a different question and a goal whose
// seats never launched must not be reported as having run them.
function executionHeadline(goalDir) {
  const rows = readCsvRows(path.join(goalDir, 'executions.csv'), ['seat', 'started', 'ended']);
  if (!rows.length) return 'No sitting numbers — this goal\'s `executions.csv` is absent, empty or unreadable.';
  const seats = new Set(rows.map((r) => r.seat).filter(Boolean));
  let first = null;
  let last = null;
  for (const r of rows) {
    if (r.started && (first === null || Date.parse(r.started) < Date.parse(first))) first = r.started;
    if (r.ended && (last === null || Date.parse(r.ended) > Date.parse(last))) last = r.ended;
  }
  const span = first && last ? humanSpan(first, last) : null;
  const window = first && last
    ? ` · ${span ? `${span} ` : ''}(${first} → ${last})`
    : first ? ` · started ${first}, no sitting has ended` : '';
  return `*${seats.size}* seat${seats.size === 1 ? '' : 's'} run · *${rows.length}* sitting${rows.length === 1 ? '' : 's'}${window}`;
}

// The seat's `goal-writes:` list, from FRONTMATTER only — `seatDirIsHumanInteractive`'s reason
// verbatim: a briefing line in the descriptor BODY that quotes the key must not be able to put a
// path in front of the owner. This mirrors `supervisor/spawn/seat-grants.js#seatDeclaresList`
// rather than importing it: `chat/` is a relocatable subtree that reaches into no sibling module
// (probe-chat-boundary), and the three frontmatter readers above are local for that same reason.
function seatDirGoalWrites(seatDir) {
  let fm;
  try { fm = frontmatterOf(fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8')); } catch { return []; }
  const lines = fm.split('\n');
  const items = [];
  let inBlock = false;
  for (const line of lines) {
    if (!inBlock) {
      if (/^goal-writes:[ \t]*$/.test(line)) inBlock = true;
      continue;
    }
    const m = line.match(/^[ \t]*-[ \t]*(.*)$/);
    if (!m) break;
    const v = m[1].trim().replace(/^["']|["']$/g, '');
    if (v) items.push(v);
  }
  return items;
}

// LINE 3 — the deliverables, GOAL-RELATIVE and ON DISK.
//
// ⚑ RESOLVED AGAINST THE GOAL DIR, one candidate, because that is the only base a `goal-writes`
// entry ever has: the declaration is goal-relative and an absolute or escaping entry is not one.
// A second candidate here would invent a grammar. (Its former resolver,
// `spawn.js#resolveGoalWriteGrants`, was DELETED 2026-08-31 with the rest of the uncalled per-seat
// grant model — template family 1 binds the whole goal folder rw under D3, so there is nothing
// left for the key to grant. The grammar it enforced is stated above and is unchanged.)
//
// ⚑ AND ONLY A NON-EMPTY FILE IS NAMED. Nothing creates a declared output at spawn any more — the
// D21 create-if-absent half went with that resolver — so an EMPTY file here is a seat that opened
// its product and wrote nothing, not a seat the daemon touched.
// A zero-byte path listed as a deliverable is exactly the invented number this line must not
// carry; a seat that wrote nothing simply contributes nothing to the line.
function declaredOutputs(goalDir) {
  let seats;
  try { seats = fs.readdirSync(path.join(goalDir, 'seats'), { withFileTypes: true }); } catch { return []; }
  const root = path.resolve(goalDir);
  const out = [];
  for (const s of seats.sort((a, b) => (a.name < b.name ? -1 : 1))) {
    if (!s.isDirectory() || !isSafeName(s.name)) continue;
    for (const token of seatDirGoalWrites(path.join(goalDir, 'seats', s.name))) {
      if (path.isAbsolute(token)) continue;
      const abs = path.resolve(root, token);
      if (abs === root || !abs.startsWith(root + path.sep)) continue;
      let st;
      try { st = fs.statSync(abs); } catch { continue; }
      if (!st.isFile() || st.size === 0) continue;
      const rel = path.relative(root, abs);
      if (!out.includes(rel)) out.push(rel);
    }
  }
  return out;
}

// THE THREE LINES, and exactly three (spec-owner-io §1 [T5-R16]): outcome, headline numbers,
// deliverable links. Nothing here reads a status field or asks whether the goal SUCCEEDED — the
// finish edge is the only outcome the system records, and inventing a verdict beside it would be
// a second, disagreeing answer to a question `executions.csv` already owns.
function composeCompletionNotice({ goalDir, goalId, row }) {
  const when = row.at ? ` at ${row.at}` : '';
  const outputs = declaredOutputs(goalDir);
  return [
    `:checkered_flag: *${goalId}* — FINISHED. The finish edge was fired by *${row.from}*${when}.`,
    executionHeadline(goalDir),
    outputs.length
      ? `Deliverables: ${outputs.map((o) => `\`${o}\``).join(' · ')}`
      : 'Deliverables: none on disk — no seat of this goal declares a `goal-writes:` output that was written.',
  ].join('\n');
}

// THIS GOAL'S CURRENT EXECUTION STAMP (7.607 design-lock item 5), read from the marker
// `coordination/execution` that `coord.py mint_execution` writes at BOOT and nowhere else.
//
// ⚠ IT IS A DELIMITER, NEVER A STATUS. Nothing here asks whether the goal is running — the ferry
// ferries whatever the log holds, and a goal between executions simply appends nothing. What the
// stamp buys is the CURSOR KEY: keyed by goal alone, a cursor carried across a goal's next boot
// would resume mid-file at an id from the previous execution; keyed by `<goal>/<stamp>` the next
// execution is a FIRST SIGHT, whose rule is "cursor at the tail, ferry nothing" — so history is
// not replayed and the new execution's own rows are the owner's business from the first one.
// An absent or corrupt marker reads as `no-stamp`, which is a stable key rather than a guess: a
// goal that predates the stamp still ferries, it simply never re-keys.
const EXECUTION_STAMP_RE = /^\d{4}-\d{2}-\d{2}[a-z]+$/;

function executionStamp(workspaceRoot, goalId) {
  try {
    const raw = fs.readFileSync(
      path.join(workspaceRoot, '.rbtv', 'goals', goalId, 'coordination', 'execution'), 'utf8',
    ).trim();
    return EXECUTION_STAMP_RE.test(raw) ? raw : 'no-stamp';
  } catch { return 'no-stamp'; }
}

// Enumerate every goal under `<workspaceRoot>/.rbtv/goals/` with its current execution stamp.
//
// ⚠ GOAL-DIRECT SINCE 7.607 (E3). This used to parse each goal's `runs.csv` for `state=open` rows
// — the THIRD independent parser of that register (inventory #37), and one of the readers whose
// disagreement the extinguishment removed. There is no register and no run folder: a goal's
// coordination bus is at `<goal>/coordination/messages.md`, one per goal, and the ferry visits
// every goal that has one. Liveness is deliberately NOT consulted here: the ferry's question is
// "are there rows the owner has not seen", which a finished goal can answer yes to.
function goalBuses(workspaceRoot) {
  const goalsDir = path.join(workspaceRoot, '.rbtv', 'goals');
  let goals;
  try { goals = fs.readdirSync(goalsDir, { withFileTypes: true }); } catch { return []; }
  const out = [];
  for (const g of goals) {
    if (!g.isDirectory()) continue;
    if (!fs.existsSync(path.join(goalsDir, g.name, 'coordination'))) continue;
    out.push({ goalId: g.name, stamp: executionStamp(workspaceRoot, g.name) });
  }
  return out;
}

function createBusFerry({
  workspaceRoot,
  transport,
  dmUserId = null,
  logger = null,
  pollMs = DEFAULT_POLL_MS,
  watchDebounceMs = DEFAULT_WATCH_DEBOUNCE_MS,
  maxAttempts = DEFAULT_MAX_ATTEMPTS,
  maxBodyChars = DEFAULT_MAX_BODY_CHARS,
  onMutate = null,
  // WHERE a row goes when it is not routed to an agent's own thread. Injected by the bridge,
  // which owns the thread map and the forward path this ferry deliberately does not hold.
  // ⚑ IT POSTS AND SEATS NOBODY (owner ruling 2026-08-12). It used to MINT that post's thread as a
  // channel-master sitting, which had an agent answering questions addressed to the human; only a
  // row NAMING a thread the owner already engaged still mints one. Default (probes, any embedder
  // that wires nothing) is the plain DM post this module shipped with — same signature, same
  // `{ delivered, ts }` contract.
  routeToMaster = null,
  // WHERE a gated row goes when the agent that raised it is allowed to reach the owner
  // directly: its OWN thread in the goal's Slack channel (ratified 2026-08-09). Injected by
  // the bridge, which owns the (goal, agent) → thread map and the goal↔channel resolution
  // this module deliberately does not hold. Unwired (probes, any embedder that wires nothing)
  // the gated row takes the owner-DM leg above — same signature, same `{ delivered, ts }`
  // contract — so this is additive, never a second delivery model.
  routeToAgentThread = null,
  // DOES THE BRIDGE KNOW THIS THREAD? (S-13 ruling `d-s13-chat-thread-token-verified`.) The token
  // in a bus row is text an agent wrote, so it is a CLAIM, and this predicate is who checks it —
  // the bridge, which owns the three conversation tables this module deliberately does not hold.
  //
  // ⚑ THE DEFAULT VOUCHES FOR NOTHING, deliberately fail-closed: an embedder that wires a
  // destination but no verifier gets the ruled behaviour (tokens ignored, rows take the normal
  // path), never the pre-ruling behaviour (any named thread obeyed). A wiring omission must not
  // silently restore the surface the ruling closed.
  knowsThread = () => false,
  ownerUser = null,
  outbox = null,
  // POST A `to: owner` ROW AS A REAL ❓ ASK THREAD — `ask-thread.js#postAsk`, injected by the
  // bridge, which owns the goal↔channel resolution and the ask-record sender this module
  // deliberately does not hold. Unwired (probes, any embedder that wires nothing) the row takes
  // the agent-thread / DM legs it always took. What is GONE either way is the park.
  postAsk = null,
  // WHERE THE FINISH EDGE'S NOTICE GOES — a TOP-LEVEL post in the goal's own channel, injected by
  // the bridge, which owns the goal↔channel resolution this module deliberately does not hold. It
  // is NOT `routeToAgentThread`: that leg anchors and then REPLIES INSIDE one agent's thread, and
  // a goal ending is the room's news rather than a seat's message [T5-R11].
  //
  // ⚑ UNWIRED, THE NOTICE IS NOT POSTED — it does NOT fall back to the owner DM the way an
  // unwired `routeToAgentThread` does. The owner's DM carries no goal traffic, ever
  // (`d-escalation-surface` part 4), so an embedder that wires no channel leg gets a logged skip,
  // never a wrong surface.
  postGoalChannel = null,
  // ONE OPEN ESCALATION PER GOAL (`d-escalation-surface` part 8) — the FLEET-WIDE open-ask reader,
  // `ask-store.js#listOpenAsks` (-> gateway `inspect asks` -> `open_asks`), injected by the bridge
  // for the same reason `postAsk` is: this module holds no store handle and no gateway forwarder
  // of its own. Unwired (probes, any embedder that wires nothing) the gate below is a no-op and an
  // escalation is admitted exactly as it was before this seat — additive, never a second queue.
  listOpenAsks = null,
  // THE SYSTEM CHANNEL (`d-escalation-surface` parts 4 + 6) — the ONE daemon-level-fault surface
  // this ferry may ever post to besides a goal's own channel; the owner's DM is banned from goal
  // traffic entirely. Injected, exactly like `dmChannel`/`postGoalChannel`: this module holds no
  // channel knowledge of its own, and `config.js#systemChannelId` (`RBTV_SYSTEM_CHANNEL_ID`) is
  // the bridge's to resolve. Unwired (probes, any embedder that wires nothing) the alarm this
  // param feeds is a logged skip, never a wrong surface — see `postUnreachableChannelAlarm`.
  systemChannelId = null,
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  const box = outbox || createOutbox({
    storePath: null,
    send: ({ channel, threadTs, text }) => transport.sendToOwner({ channel, threadTs, text }),
  });

  function postOwner({ kind, channel, threadTs, text, goal_id = null }) {
    return box.post({
      kind,
      channel_id: channel,
      thread_ts: threadTs == null ? null : threadTs,
      payload: text,
      goal_id,
      ask_id: null,
    });
  }

  // `<goalId>/<execution-stamp>` -> last-ferried msg id. PERSISTED (state file `busFerry` block).
  const cursors = new Map();
  // Volatile per-pass bookkeeping — deliberately NOT persisted: attempt counts and the
  // "already warned about this execution's malformed headers" flag are both per-process.
  const attempts = new Map();   // `<key>#<msgId>` -> failed post count
  const warned = new Set();
  const sizes = new Map();      // `<key>` -> last seen byte size (skip an unchanged file)
  // Runs this PROCESS watched be born: enumerated as open with no messages.md on disk yet.
  // Deliberately NOT persisted — see the born-watched block in `_runOnce` for why.
  const bornWatched = new Set();
  // W8 (adv, C76) — `<key>#<msgId>` of an ESCALATION delivered AHEAD of the cursor, i.e. past a
  // row that is still failing to post. PERSISTED, unlike every other volatile map above, and for
  // one reason: the cursor is persisted, so a restart that forgot these would re-post every jumped
  // escalation the moment the cursor caught up. An escalation interrupts a human; delivering it
  // twice is the second-worst outcome after not delivering it at all. Entries are dropped as the
  // cursor passes them, so the set is bounded by the head-of-line stall it exists for.
  const jumped = new Set();

  let dmChannel = null;
  let enabled = false;
  let timer = null;
  let ticking = false;
  const watchers = new Map(); // watched dir -> FSWatcher
  let watchTimer = null;
  let watchWarned = false;    // the watch's failures are logged ONCE, not once per goal per pass

  function persist() { if (onMutate) onMutate(); }

  // ── THE WATCH (live-session-design.md §2) ─────────────────────────────────────────────
  //
  // ⚑ IT ONLY TRIGGERS THE PASS. Nothing here reads an event's filename, its type, or its
  // contents — the event says "something changed under this dir" and `_runOnce` then does exactly
  // what it always did: stat, size-check, whole-file read, and the newline-terminated torn-write
  // rule in `parseMessages`. That split is the whole safety argument: `coord.py` appends a row in
  // more than one write, so an event can arrive mid-row, and a pass that read from the EVENT would
  // post half a message. A pass that reads AT REST cannot.
  //
  // ⚑ THE 15s POLL STAYS, and is not a belt-and-braces flourish: inotify queues overflow, a watch
  // on a dir that did not exist at arm time is never armed, `fs.watch` is not guaranteed across
  // filesystems (a network mount degrades silently), and every watcher dies with its directory.
  // Every one of those degrades to the behaviour this module had before this block — late, never
  // lost.
  //
  // ⚑ EVERY FAILURE DEGRADES TO THE POLL, silently after the first. `fs.watch` throws
  // synchronously on ENOSPC (the per-user inotify watch limit) and on ENOENT (a goal torn down
  // between the enumeration and the arm), and emits `error` later for the same reasons. Both arms
  // land in the same place: no watcher for that dir, and the poll still visits it.
  function armWatch(dir) {
    if (watchers.has(dir)) return;
    let w;
    try {
      w = fs.watch(dir, () => scheduleWatchPass());
    } catch (err) {
      if (!watchWarned) {
        watchWarned = true;
        log('warn', 'bus ferry could not watch a coordination dir — that dir falls back to the 15s poll (logged once)', { dir, error: err.message });
      }
      return;
    }
    w.on('error', (err) => {
      // The dir went away (goal teardown) or the kernel dropped the watch. Close and forget it:
      // the next pass re-arms if it is still there, and the poll covers it meanwhile.
      try { w.close(); } catch { /* already closed */ }
      watchers.delete(dir);
      if (!watchWarned) {
        watchWarned = true;
        log('warn', 'bus ferry watch errored — that dir falls back to the 15s poll (logged once)', { dir, error: err.message });
      }
    });
    if (w.unref) w.unref();
    watchers.set(dir, w);
  }

  // The goals ROOT is watched too, so a goal created between passes is picked up by the next
  // triggered pass rather than waiting out the poll. Its own `coordination/` dir is a GRANDCHILD
  // and so fires no event on this watch — the poll arms that one, which is exactly what the poll
  // is for.
  function watchDirs(buses) {
    armWatch(path.join(workspaceRoot, '.rbtv', 'goals'));
    for (const { goalId } of buses) armWatch(path.join(workspaceRoot, '.rbtv', 'goals', goalId, 'coordination'));
  }

  // Debounced trigger. A single `append_message` produces several events (the lock file, the
  // write, the mtime), and a burst of rows produces a burst of them — one pass covers the lot.
  //
  // ⚑ A PASS ALREADY RUNNING RE-ARMS RATHER THAN DROPS. `_runOnce` returns immediately while
  // `ticking`, so firing into a live pass would silently lose the trigger and leave the row to the
  // poll — the exact latency this block exists to remove. Re-arming cannot spin: it is the same
  // debounce delay, and the pass it is waiting on ends.
  function scheduleWatchPass() {
    if (!enabled) return;
    if (watchTimer) clearTimeout(watchTimer);
    watchTimer = setTimeout(() => {
      watchTimer = null;
      if (ticking) { scheduleWatchPass(); return; }
      _runOnce().catch((err) => log('warn', 'bus ferry watch-triggered pass error', { error: err.message }));
    }, watchDebounceMs);
    if (watchTimer.unref) watchTimer.unref();
  }

  // ── THE UNREACHABLE-CHANNEL ALARM (`d-escalation-surface` parts 4, 6 — `esc-dm-ban`) ─────────
  //
  // RETIRES `deliverEscalationInFull`, the content-bearing owner-DM dump this module used to fall
  // back to (both its callers — a deterministic [T2-R14] refusal, and the attempt cap — read the
  // history in `ignite/work-on-ignite/memory/chat/20260827-i-a-refused-escalation-retried-2.md`
  // and `20260831-i-the-door-admitted-by-label-a-l.md`). The owner ruled his DM carries NO goal
  // traffic at all, escalation included [part 4]. What replaces the reach: an unreachable goal
  // channel is a SYSTEM FAULT, not goal business, and is raised as a daemon-level alarm in the
  // SYSTEM CHANNEL instead [part 6] — naming the goal and the blocked seat, never dumping the
  // escalation's own content (content belongs in the goal channel it cannot yet reach, not in a
  // second surface).
  //
  // ⚑ FIRES AT MOST ONCE PER ROW. Its one call site guards on `n === NOTICE_AT_ATTEMPT` — an
  // exact match against a monotonically increasing per-row counter — so this never re-fires on
  // later passes while the same row keeps retrying.
  //
  // ⚑ `reason` MUST BE CARRIED THROUGH, NEVER COLLAPSED. `goal-channel-map.js#resolveChannel`
  // returns `no-channel` (Slack confirms the channel does not exist) and `resolve-failed` (Slack
  // did not answer — NOT evidence of absence) as different facts, and telling the owner a channel
  // is missing when Slack simply timed out would be a lie he cannot act on correctly.
  async function postUnreachableChannelAlarm({ goalId, seat, reason, isEscalation, key, msgId }) {
    if (!systemChannelId) {
      log('warn', 'bus ferry could not raise the unreachable-channel alarm — no system channel wired', { key, msgId, goalId, seat, reason });
      return false;
    }
    const why = reason === 'resolve-failed'
      ? 'Slack did not answer when the channel was re-resolved — this is NOT evidence the channel is missing'
      : 'the channel does not exist in the workspace';
    const what = isEscalation ? 'a blocked escalation' : 'a message it cannot deliver';
    try {
      await postOwner({
        kind: 'alarm',
        channel: systemChannelId, threadTs: null,
        text: `:rotating_light: goal *${goalId}* has ${what} and its channel is unreachable — seat *${seat}* cannot reach the owner: ${why}. Retrying; nothing is abandoned.`,
        goal_id: goalId,
      });
      return true;
    } catch (err) {
      log('error', 'bus ferry could not raise the unreachable-channel alarm on the system channel', { key, msgId, goalId, seat, error: err.message });
      return false;
    }
  }

  async function _runOnce() {
    if (!enabled || ticking) return;
    ticking = true;
    try {
      const buses = goalBuses(workspaceRoot);
      // Re-armed every pass, from the enumeration the pass already made: a new goal acquires a
      // watcher, and one lost to teardown or an inotify limit gets another try. Idempotent —
      // `armWatch` returns on a dir already held.
      watchDirs(buses);
      for (const { goalId, stamp } of buses) {
        const key = `${goalId}/${stamp}`;
        const relPath = path.join('.rbtv', 'goals', goalId, 'coordination', 'messages.md');
        const file = path.join(workspaceRoot, relPath);
        let st;
        // NO LOG YET = WE WATCHED THIS RUN BE BORN. The run is registered open and its
        // coordination folder is created EMPTY (`materialize-seats.py`); the log appears only
        // when somebody first writes to it (`coord.py append_message`). Seeing that state is the
        // one moment the ferry can know an execution has NO history — which is what the first-sight
        // rule below is protecting against. Recorded here, consumed there.
        try { st = fs.statSync(file); } catch { bornWatched.add(key); continue; }
        if (cursors.has(key) && sizes.get(key) === st.size) continue; // nothing appended
        let text;
        // ponytail: whole-file read on every size change. 6 MB / few ms on a local
        // disk; if bus volume ever makes that hurt, remember a byte offset per run and
        // read the tail instead.
        try { text = fs.readFileSync(file, 'utf8'); } catch (err) {
          log('warn', 'bus ferry could not read messages.md', { key, error: err.message });
          continue;
        }
        const rows = parseMessages(text, (line) => {
          if (warned.has(key)) return log('debug', 'bus ferry skipped a malformed header', { key, line: line.slice(0, 120) });
          warned.add(key);
          log('warn', 'bus ferry skipping malformed message header(s) in this goal (logged once)', { key, line: line.slice(0, 120) });
        });
        sizes.set(key, st.size);

        // FIRST SIGHT — cursor at the tail, ferry NOTHING. The run's backlog is history.
        //
        // ⚑ UNLESS WE WATCHED IT BE BORN (7.546). A run whose log did not exist on an earlier
        // pass of THIS process has no history to protect — the flood rule then costs everything
        // and protects nothing, and what it swallows is a fresh goal's FIRST escalation. A newly
        // scaffolded goal rosters only the planning DAG, so that first message is exactly the one
        // with nobody in the room to read it. Seed at ZERO and FALL THROUGH, so the row travels on
        // the pass that sees it: `continue`-ing here would set the cursor and then skip this goal
        // on every later pass via the unchanged-size short-circuit above, until some SECOND
        // message happened to arrive.
        //
        // ⚑ WHAT THE MARKER BEING PER-PROCESS COSTS — TWO CASES, AND THEY ARE NOT THE SAME CASE
        // (corrected by the §2 review of 7.546; the first wording named only the first of them and
        // therefore read as "persisting buys nothing", which is measurably false for the second):
        //
        //   1. BORN WHILE THE BRIDGE WAS DOWN — no pass ever observed the empty state. The log
        //      already exists when the bridge returns, so the backlog is (correctly, by this rule)
        //      treated as history. Persistence buys NOTHING here: there was never an observation
        //      to persist.
        //   2. BIRTH OBSERVED, THEN A RESTART before the execution's first row — SWALLOWED, and
        //      persisting the marker WOULD have delivered it. The marker dies with the process
        //      (`toJSON()` carries `cursors` only), so the returning bridge meets that first row as
        //      an ordinary first sight WITH a log and seeds at its tail. Measured on this code:
        //      state carried across the restart `{"cursors":{}}`, delivered 0, cursor 1 — while the
        //      same birth and the same row with NO restart in between delivers 1.
        //
        // Case 2 is a KNOWN gap, ruled and accepted with the case named — not an oversight and not
        // a claim of coverage. The durable record for BOTH is the goal's own `doubts.md` park —
        // tier 1 of the escalation ladder, kept for exactly this reason.
        if (!cursors.has(key)) {
          if (bornWatched.has(key)) {
            bornWatched.delete(key);
            cursors.set(key, 0);
            persist();
            log('info', 'bus ferry watched this execution be born — cursor seeded at 0, its first rows ARE the owner\'s business', { key, rows: rows.length });
          } else {
            const tail = rows.length ? rows[rows.length - 1].id : 0;
            cursors.set(key, tail);
            persist();
            log('info', 'bus ferry saw this execution for the first time — cursor set at tail, backlog NOT ferried', { key, cursor: tail, rows: rows.length });
            continue;
          }
        }

        // ⚑ THE TWO GATE READS ARE GONE WITH THE GATES. The goal's `execution-mode` was read once
        // per pass and the seat's `human-interactive:` flag once per distinct sender, purely to
        // decide whether to PARK — and neither question is asked here any more (see the deleted
        // rungs below). `goalExecutionMode` / `seatIsHumanInteractive` are still EXPORTED: other
        // consumers hold them, and deleting the gate is not deleting the predicate.
        const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', goalId);
        // The FALLBACK ARM is a property of the sending seat, memoized per pass: at most one
        // descriptor read per distinct `from:` name actually seen, and zero on a pass with no
        // `to: owner` row at all. It is a RENDER MARK now, never a disposition.
        const fallbackMemo = new Map();
        const fallbackArm = (name) => {
          if (!fallbackMemo.has(name)) fallbackMemo.set(name, seatFallback(goalDir, name));
          return fallbackMemo.get(name);
        };

        // In id order, so one undeliverable row does not let a later one jump it — with ONE
        // exception, ruled in W8 (adv, C76): a `type: escalation` row. Order is the point for
        // ordinary traffic and it is the thing that matters LEAST for a halt nobody inside the run
        // can clear, so an escalation is delivered past a stuck row rather than queued behind it.
        // `stuckAt` is what used to be the `break` at the bottom of this loop.
        let stuckAt = null;
        for (const row of rows) {
          if (row.id <= cursors.get(key)) { jumped.delete(`${key}#${row.id}`); continue; }
          const isEscalation = row.type === 'escalation';
          // ALREADY DELIVERED, out of order, on an earlier pass. The cursor has now reached it, so
          // step past it and forget it — re-posting is the one thing the persisted set prevents.
          if (jumped.has(`${key}#${row.id}`)) {
            jumped.delete(`${key}#${row.id}`);
            if (stuckAt === null) { cursors.set(key, row.id); persist(); }
            continue;
          }
          // HEAD-OF-LINE: a row behind a still-failing one waits, and only an escalation jumps it.
          if (stuckAt !== null && !isEscalation) continue;
          // THE RETURN LEG. A row naming its own chat thread is routed there and skips BOTH
          // gates below — neither is about it. Read `chatThreadToken`'s header for why this
          // is a token and not a seat name.
          //
          // ⚑ THE TOKEN IS VERIFIED BEFORE IT COUNTS (S-13). A row can NAME any thread; only one
          // the bridge already knows is honoured. An unknown one is treated as if the row carried
          // NO token at all — so it falls through to the ordinary path below (`to: owner` → gates
          // → thread or PARK; anything else → cursor advance) rather than being dropped, and
          // nothing is ever posted to, or minted on, a thread the sender invented.
          const namedThread = rowChatThread(row);
          const chatThread = namedThread && knowsThread(namedThread) ? namedThread : null;
          if (namedThread && !chatThread) {
            log('info', 'bus row named a chat thread the bridge does not know — token IGNORED, row takes the ordinary path', { key, msgId: row.id, from: row.from, namedThread });
          }
          // NOT ADDRESSED TO THE OWNER AND NOT NAMING A THREAD → not this ferry's business, at
          // all. `to: master`, `to: leader`, `to: some-seat` are all one case now (ruling
          // `d-agents-address-owner-not-master`): the bus delivers them to seats, and the cursor
          // advances because the ferry never had a claim on them.
          // ⚑ `stuckAt === null` GUARDS THE ADVANCE, and it is reachable: only an escalation walks
          // past the head-of-line test above, and an escalation addressed to anything but the
          // owner still lands here. Advancing the cursor to ITS id would step over the undelivered
          // row behind it — losing a row for good, in the one branch that looked harmless because
          // it posts nothing.
          // THE FINISH EDGE'S NOTICE [T5-R16] — the ONE row this ferry carries that is not
          // addressed to the owner. `fire_finish_edge` writes it `to: all`, so it would be
          // disposed of by the address test immediately below; it is recognised HERE, before
          // that test, by the marker its body opens with and by its sender's chair.
          const isFinish = !chatThread && isFinishRow(row) && row.from === LEADER_CHAIR;
          if (!chatThread && !isFinish && !addressesOwner(row.to)) {
            // A marker-carrying row from a seat that is NOT the leader's chair lands HERE, and it
            // is the one disposition on this branch worth a line: the row claims a goal ended and
            // nothing at the SEND door checks that claim, so the notice is withheld and said so
            // rather than advanced past in the silence every other `to: <seat>` row deserves.
            if (isFinishRow(row)) {
              log('warn', 'a goal-finished row was NOT posted as a completion notice — its sender is not this goal\'s `leader` chair and `coord.py cmd_send` does not guard the marker; cursor advanced [T5-R16]',
                { key, msgId: row.id, from: row.from, expected: LEADER_CHAIR });
            }
            if (stuckAt === null) { cursors.set(key, row.id); persist(); }
            continue;
          }
          // THE TWO GATES — on AGENT-INITIATED contact only (read their header above). A row
          // carrying a chat-thread token is answering INTO the owner's own thread and is never
          // gated; every other row reaching here is `to: owner`, i.e. initiation.
          //
          // ⚑ THE THIRD RUNG IS THE SEAT'S OWN `fallback: park` (7.626) — a seat that CAN reach the
          // owner and declared that its questions wait on the bus instead. It is a rung of this
          // ladder and not a branch of its own precisely because the disposition is identical:
          // nothing posted anywhere, cursor advanced, logged with its reason.
          //
          // ⚑ AN `escalation` PASSES EVERY GATE ON THIS LADDER (W8, adv, D-8/C76). The gates ask
          // "may this seat start a conversation with the human"; an escalation is not a
          // conversation but the record of a halt nobody inside the run can clear, and its
          // authority was already checked at the ONE door that can check it — `coord.py cmd_send`,
          // where identity is resolved (leader or judge, no `--force`). Gating it here would gate
          // it a second time on a WEAKER question and park exactly the goals it exists for: the
          // autonomous ones, whose seats are never `human-interactive` (the staff chairs least of
          // all — `meta/leader/component.md` declares that absence deliberate).
          // ── THE THREE PARK RUNGS ARE DELETED [D24, T2-R17, D-7-ruling, T2-R14] ──────────────
          //
          // A `to: owner` row used to be swallowed by any of three gates — the GOAL's
          // `execution-mode`, the SEAT's `human-interactive:` flag, or the seat's own
          // `fallback: park` arm — and "parking on the bus" is not a queue: the cursor advanced
          // and nothing ever re-delivered the row. Work-content questions died there in silence,
          // which is the failure this redesign exists to end.
          //
          // Every rung is now answered by a ruling rather than by a gate. Goal-level
          // interactive/autonomous mode is DEAD [D24] — interactivity is a per-seat property, so
          // the goal can no longer mute a seat. A NON-INTERACT seat never knows a human exists
          // and its work-content question becomes a DAEMON-POSTED ask labelled `work-content`
          // [T2-R17, D-7-ruling] — which is a real ❓ thread, not a park. And `fallback: park`
          // described what a seat did when the owner was UNREACHABLE; under thread-per-ask he is
          // reachable, so the arm survives only as a render mark.
          //
          // ⚑ [T2-R14] STILL BINDS, AT ITS OWN DOOR. A non-designated seat's owner-ask is refused
          // AT SEND — `ask-thread.js#postAsk` refuses it and says so. Refusal is not parking: the
          // caller learns, and nothing is silently swallowed here. That refusal is DETERMINISTIC
          // and is disposed of on the FIRST pass — for an `escalation`, by the content-bearing
          // owner DM (W8-C). See § the terminal-refusal block below.
          // ── ONE OPEN ESCALATION PER GOAL (`d-escalation-surface` part 8) ───────────────────────
          //
          // On 2026-08-31 one goal raised three blocking escalations in seventeen minutes, and the
          // second withdrew a claim the first had made; three open threads at once would have let
          // the owner rule on retracted evidence. This is the opposite force from the head-of-line
          // JUMP above (only an escalation walks past a stuck row): a NEW escalation — never a
          // reply `chatThread` routes into an ask ALREADY open, which mints nothing here — is HELD
          // on the bus, unposted, while the goal already carries an open, posted escalation ask.
          //
          // ⚑ READ FRESH OFF `open_asks` EVERY TIME, NEVER FROM A LOCAL SET. Two ferry passes
          // across a restart or a revive must agree on what is open, and in-memory queue state is
          // exactly the failure class a sibling defect in this subsystem measured (two bridge
          // lineages both answering one thread, `seed/slack-duplicate-replies.md` defect 1).
          // `listOpenAsks` is the fleet-wide reader (`ask-store.js`, gateway `inspect asks`); this
          // gate filters it to `goalId` and to `isEscalationOneLiner` — see that function's header
          // for why a text marker and not a column.
          //
          // ⚑ THE THREE-WAY CASE: one open escalation, one stuck ordinary row, one NEW escalation.
          // The new escalation clears the head-of-line test above (only an escalation jumps a
          // stuck row) and reaches HERE, where it is held — `stuckAt` is set (or left as the
          // ordinary row's own) exactly as an ordinary undelivered row would, so the cursor still
          // does not advance past EITHER. No deadlock: the stuck ordinary row keeps retrying on its
          // own independent attempts ladder, untouched by this gate, and the held escalation is
          // re-read every pass — the moment the open escalation closes, the earliest held one (id
          // order, this loop's own order) posts on the very next pass and becomes the new "open
          // escalation" a later one is held against, so FIFO order falls out of the loop's own id
          // order with no queue of its own to get out of sync.
          //
          // ⚑ NEVER THE ATTEMPTS/`maxAttempts` LADDER. A `continue` here skips the whole delivery
          // try-block below, so a held escalation never accrues an attempt, never reaches the
          // abandon-at-cap path, and is never force-delivered to the owner DM (W8-C) — that path is
          // for TRANSPORT failures; this is a deliberate, working-as-designed queue, logged every
          // pass so it is never mistaken for the silence this whole module exists to end.
          if (isEscalation && !chatThread && listOpenAsks) {
            const openAsks = await listOpenAsks();
            const alreadyOpen = Array.isArray(openAsks) && openAsks.some(
              (a) => a && String(a.goal) === String(goalId) && isEscalationOneLiner(a.one_liner),
            );
            if (alreadyOpen) {
              log('info', 'bus ferry HELD a new escalation — this goal already has one open [d-escalation-surface part 8]',
                { key, msgId: row.id, from: row.from });
              // Forget the size so the NEXT pass re-reads this goal even if nothing new was
              // appended — the same reason the ordinary retry ladder does it (below): without this
              // the unchanged-size short-circuit at the top of this function would skip the goal
              // forever once its own escalation closes with no other bus traffic to bump the file.
              sizes.delete(key);
              if (stuckAt === null) stuckAt = row.id;
              continue;
            }
          }
          const arm = chatThread || isEscalation || isFinish ? null : fallbackArm(row.from);
          // Two ask LABELS reach the owner and only two [D-7-ruling]: the leader's traffic and any
          // escalation are `recovery`, everything else — including the deleted consultant's former
          // work-content traffic — is `work-content`.
          const askLabel = isEscalation || row.from === 'leader' ? 'recovery' : 'work-content';
          const text = isFinish
            ? composeCompletionNotice({ goalDir, goalId, row })
            : formatMessage(row, { goalId, stamp, relPath, maxBodyChars, arm });
          let delivered = false;
          let error = null;
          let viaAgentThread = false;
          let viaAskThread = false;
          let viaNoticeThread = false;
          let viaCompletion = false;
          // The render ACTUALLY posted — the two legs render the same row differently (the
          // agent-thread header leads with the agent name), so a log that always reported the DM
          // render's length would misreport the agent leg's every time.
          let postedText = text;
          try {
            let res = null;
            // THE FINISH NOTICE'S OWN LEG, AND IT IS TAKEN FIRST. Setting `res` here is what keeps
            // the T2-R14 ask door out of this row's path entirely — a completion is a
            // notification, not a conversation [T2-R16] — and, past it, the DM leg too.
            if (isFinish) {
              viaCompletion = true;
              res = postGoalChannel
                ? await postGoalChannel({ goalId, text })
                : { delivered: false, reason: 'no-goal-channel-leg-wired' };
            }
            // THE AGENT'S OWN THREAD FIRST (ratified 2026-08-09). A row that PASSED both gates
            // belongs in the goal channel, in the thread that is this agent's conversation with
            // the owner — not in the owner's undifferentiated DM queue.
            //
            // ⚑ `no-channel` NO LONGER FALLS BACK TO THE DM (owner ruling 2026-08-12). It used
            // to, on the reasoning that a degraded delivery beats a lost row — but the DM leg
            // ALSO minted a channel-master sitting with the row's text as its prompt, so a
            // question an agent addressed to the HUMAN was answered by another agent. Measured on
            // `meeting-digest` 02:13 UTC. A missing channel is now an ordinary post failure: the
            // row stays undelivered, the bounded retry below re-tries it every pass (by then
            // `resolveChannel` has re-asked Slack — chat-bridge.js), and at NOTICE_AT_ATTEMPT the
            // owner is told the CHANNEL is missing, with none of the row's content.
            // ⚑ A REAL ❓ THREAD FIRST [D18, T5-R8, spec-owner-io §3]. One new thread per ask
            // batch, carrying the §3 opening line and minting the ask record the digest, the
            // status count and the kill-clock suspension all read. Injected, because the thread
            // and the record are the BRIDGE's (`ask-thread.js`); an embedder that wires nothing
            // gets the legs below unchanged, so this is additive and never a second ask model.
            // ⚑ `!res` JOINS THE TEST (T5-R16). Every leg below already reads it and this one did
            // not, because until the finish notice above nothing could set `res` before here.
            // Without it the finish row is posted TWICE — once as its channel notice and once as
            // an ❓ ask thread — which is the ask door a completion must never reach [T2-R16].
            if (!res && !chatThread && postAsk) {
              // AN APPROVAL ROW IS POSTED AS AN APPROVAL, and the §3 body is `approval-thread.js`'s
              // to compose — the digest the seat wrote is its PAYLOAD, under the GOAL /
              // IRREVERSIBLE lead lines and above the bound commit and the token line the thread
              // will actually parse. `formatMessage`'s ferry provenance is deliberately not used
              // here: this body is a specified shape, not a rendered bus row.
              const approveCommit = rowApproveCommit(row);
              // ⚑ THE DOOR IS ADMITTED BY `kind`, NEVER BY `label` [d-escalation-surface part 1].
              // `kind: 'escalation'` carries `row.type === 'escalation'` through the ONE
              // whitelisted parameter that already reaches `ask-thread.js#postAsk` unchanged
              // (`chat-bridge.js#postOwnerAsk` forwards `kind` as-is; that wrapper is out of this
              // seat's custody and needed no new field). `askLabel` keeps doing its OWN job — the
              // digest's two-value taxonomy — and decides admission for nobody.
              const asked = await postAsk({
                goalId, seatName: row.from, label: askLabel,
                kind: approveCommit ? 'approval' : (isEscalation ? 'escalation' : 'ordinary'),
                commitId: approveCommit,
                body: approveCommit
                  ? composeApprovalBody({ goalName: goalId, digest: row.body, commitId: approveCommit })
                  : splitAskBody(formatMessage(row, { goalId, stamp, relPath, maxBodyChars, agentLead: true, arm, ownerUser })),
              });
              if (asked && asked.posted) {
                res = { delivered: true, ts: asked.askId };
                viaAskThread = true;
                postedText = asked.text || postedText;
              } else if (asked && asked.reason === 'seat-not-interact') {
                // `isEscalation` can never reach this branch in production: `kind: 'escalation'`
                // bypasses [T2-R14] at the door unconditionally (ask-thread.js), so a
                // `seat-not-interact` refusal is only ever a genuine non-designated seat's own
                // traffic. Retired here (`esc-dm-ban`) is the escalation-specific terminal-refusal
                // branch this used to be paired with — `deliverEscalationInFull`'s first caller —
                // proven permanently dead by that same bypass; see
                // `ignite/work-on-ignite/memory/chat/20260831-i-the-door-admitted-by-label-a-l.md`.
                // [T2-R14] refused AT SEND — the row is `to: owner`, from a seat with no
                // `human-interactive:` flag, and is NEITHER an escalation NOR a system-decided
                // recovery ask (both bypass this gate by `kind`, above). It is still addressed to
                // the owner, so it is never silently discarded [d-escalation-surface part 7]: the
                // SAME door rescues it as a 💭 NOTICE — `marker: 'note'` routes to
                // `ask-thread.js#postNote`, which mints no record and can never suspend the kill
                // clock or block on a reply nobody is waiting for. This is the fix for the measured
                // incident: an ORDINARY `leader` message used to reach here labelled `recovery`
                // (bus-ferry.js used to give every `leader` row that label, escalation or not) and
                // was admitted as a BLOCKING ask; now only `kind: 'escalation'` is ever admitted as
                // one, and everything else refused here is rescued, never dropped and never blocking.
                log('info', 'bus row refused at the ask door [T2-R14] — rescued as a 💭 notice, never an ask', { key, msgId: row.id, from: row.from });
                const noted = await postAsk({
                  goalId, seatName: row.from, label: askLabel, marker: 'note',
                  body: splitAskBody(formatMessage(row, { goalId, stamp, relPath, maxBodyChars, agentLead: true, arm, ownerUser })),
                });
                if (noted && noted.posted) {
                  res = { delivered: true, ts: noted.threadTs };
                  viaNoticeThread = true;
                  postedText = noted.text || postedText;
                }
                // A failed NOTICE attempt is an ORDINARY post failure (no channel, a transient
                // Slack error) — never a second terminal refusal: the refusal it answers
                // ([T2-R14]) is already resolved, above. `res` stays null and the row falls
                // through to the agent-thread / DM legs and the bounded retry below, exactly like
                // any other undelivered row — never silently dropped.
              }
            }
            if (!res && !chatThread && routeToAgentThread) {
              const threadText = formatMessage(row, { goalId, stamp, relPath, maxBodyChars, agentLead: true, arm, ownerUser });
              res = await routeToAgentThread({ goalId, agent: row.from, text: threadText });
              // ⚑ `if (res)`, never a bare `else`: an injected `routeToAgentThread` that
              // returns nothing at all (an embedder's stub, a forgotten `return`) falls through to
              // the DM leg below, and flagging it as thread-routed would make the log claim a
              // surface the row never reached.
              if (res) { viaAgentThread = true; postedText = threadText; }
            }
            if (!res) {
              const send = routeToMaster || ((a) => postOwner({ kind: 'notification', channel: a.channel, threadTs: a.threadTs, text: a.text, goal_id: goalId }));
              // `deliver` rides ONLY with `chatThread` — it says what to do at a named thread and
              // means nothing without one (see `deliverToken`'s header).
              res = await send({ channel: dmChannel, threadTs: null, text, chatThread, deliver: chatThread ? rowDeliver(row) : null });
              postedText = text;
            }
            delivered = Boolean(res && res.delivered);
            // `reason` too: the agent leg's refusals carry one and no `error`, and a retry log
            // that reported `undefined` for every one of them is the failure hiding itself.
            error = res && (res.error || res.reason);
          } catch (err) {
            error = err.message;
          }
          if (delivered) {
            attempts.delete(`${key}#${row.id}`);
            // The cursor may only advance over rows that ARE delivered. Past a stuck row it
            // cannot, so a jumped escalation is remembered instead (see `jumped`).
            if (stuckAt === null) cursors.set(key, row.id);
            else jumped.add(`${key}#${row.id}`);
            persist();
            log('info', chatThread ? 'bus ferry routed a bus row to its named chat thread'
              : viaCompletion ? 'bus ferry posted the FINISH EDGE\'s completion notice to the goal channel [T5-R16]'
              : viaAskThread ? 'bus ferry posted a bus row as a NEW ❓ ask thread in the goal channel'
              : viaNoticeThread ? 'bus ferry posted a bus row as a NEW 💭 notice thread — refused as an ask [T2-R14], rescued as a notice'
              : viaAgentThread ? 'bus ferry routed a bus row into the agent\'s own thread in the goal channel'
              : 'bus ferry delivered a bus row to the owner DM',
                { key, msgId: row.id, from: row.from, chars: postedText.length, arm, ...(chatThread ? { chatThread } : {}) });
            continue;
          }
          // ⚑ A DETERMINISTIC REFUSAL AT THE ASK DOOR IS NOT A THING AN ESCALATION CAN HIT: `kind:
          // 'escalation'` bypasses [T2-R14] unconditionally (ask-thread.js). The terminal-refusal
          // disposal that used to sit here (a first-pass content-bearing owner-DM dump) is
          // retired with `deliverEscalationInFull` — see that function's header — because the
          // ONLY caller that could ever reach it is the dead `seat-not-interact && isEscalation`
          // branch already removed above. A non-escalation refusal at the door is rescued as a
          // notice, above; it never reaches this point.
          const akey = `${key}#${row.id}`;
          const n = (attempts.get(akey) || 0) + 1;
          attempts.set(akey, n);
          // THE UNREACHABLE-CHANNEL ALARM (`d-escalation-surface` parts 4, 6 — retires the old
          // owner-DM missing-channel notice, owner ruling 2026-08-12). A row that cannot reach its
          // goal channel is a SYSTEM FAULT, never the owner's DM's business [part 4]. So ONCE per
          // stuck row — `n ===`, never `>=` — the SYSTEM CHANNEL gets one line naming the goal and
          // the blocked seat and NOTHING ELSE: no body, no header render, posted through the
          // transport directly, so no sitting can be minted from it and no agent ever reads the
          // row. See `postUnreachableChannelAlarm`'s header for the `no-channel`/`resolve-failed`
          // distinction it carries.
          const channelUnreachable = error === 'no-channel' || error === 'resolve-failed';
          if (n === NOTICE_AT_ATTEMPT && channelUnreachable && !isFinish) {
            await postUnreachableChannelAlarm({ goalId, seat: row.from, reason: error, isEscalation, key, msgId: row.id });
          }
          // ⚑ AN ESCALATION BLOCKED BY AN UNREACHABLE CHANNEL IS NEVER ABANDONED (part 6: "retry
          // without a give-up cap"). Provably safe to retry forever: `no-channel` and
          // `resolve-failed` are returned BEFORE any Slack post is attempted — `goalChannelFor`
          // short-circuits on a missing channel id in both `postOwnerAsk` and `routeToAgentThread`
          // (chat-bridge.js), so no message can ever have landed for a retry to duplicate. The
          // alarm above has already told the owner once; `stuckAt` already holds the cursor behind
          // this row via the head-of-line test, so skipping the cap costs nothing but the
          // `giving up` line an ordinary row still gets.
          //
          // ⚠ EVERY OTHER PERSISTENT FAILURE ON AN ESCALATION — the channel resolves but the POST
          // ITSELF keeps failing — keeps the ORDINARY cap below. That path DOES reach a real
          // transport call (`ask-thread.js#postAsk` → `outbox.post`), and the outbox's own dedup
          // (an exact `(kind, channel, thread_ts, goal_id, ask_id, payload)` match in
          // `pending-delivery` state) is not proof against a transport call Slack actually
          // accepted but this process read as failed — `dup-idempotency`'s per-message key does
          // not cover ferry/ask-thread posts (its own memory entry says so, `esc-dm-ban`
          // re-verified it: `bus-ferry.js#postOwner` and `ask-thread.js#postAsk` both call
          // `outbox.post` directly). Uncapping THAT case is not proven safe, so it is not done;
          // the residual is named in `esc-dm-ban`'s report.
          if (!(isEscalation && channelUnreachable) && n >= maxAttempts) {
            attempts.delete(akey);
            if (stuckAt === null) cursors.set(key, row.id); // advance — never wedge the ferry on one row
            else jumped.add(akey);
            persist();
            log('warn', 'bus ferry giving up on a row after persistent post failures — NOT delivered, cursor advanced', { key, msgId: row.id, attempts: n, error });
            continue;
          }
          log('warn', 'bus ferry post failed — will retry next pass', { key, msgId: row.id, attempts: n, error });
          // Forget the size so the next pass RE-READS this goal. Without this the
          // unchanged-size short-circuit at the top would skip the run entirely and the
          // retry would never happen — the bound would be unreachable and the row lost.
          sizes.delete(key);
          // Was a `break`. It still stops every ORDINARY row behind this one (the head-of-line
          // test at the top of the loop) — the pass keeps walking solely so a later `escalation`
          // can jump it. `stuckAt` holds the FIRST such row: the cursor must never advance past
          // it, whatever is delivered after.
          if (stuckAt === null) stuckAt = row.id;
        }
      }
    } finally {
      ticking = false;
    }
  }

  // Resolve the owner's DM channel ONCE, then arm the poll loop. FAIL CLOSED: no DM
  // channel → the ferry stays disabled and says so; the rest of the bridge is
  // unaffected, which is the whole reason this is a sibling module and not a branch.
  async function start() {
    if (!workspaceRoot) {
      log('error', 'bus_ferry is enabled but workspace_root is NOT configured — BUS FERRY DISABLED (nothing to enumerate)');
      return { enabled: false, reason: 'no-workspace-root' };
    }
    if (!dmUserId) {
      log('error', 'bus_ferry is enabled but no DM user could be determined (set bus_ferry_dm_user, or an allowlist) — BUS FERRY DISABLED');
      return { enabled: false, reason: 'no-dm-user' };
    }
    if (typeof transport.openDm !== 'function') {
      log('error', 'transport exposes no openDm — BUS FERRY DISABLED');
      return { enabled: false, reason: 'no-open-dm' };
    }
    let opened;
    try { opened = await transport.openDm(dmUserId); } catch (err) { opened = { ok: false, error: err.message }; }
    if (!opened || !opened.ok || !opened.channel) {
      log('error', 'bus ferry could not open the owner DM — BUS FERRY DISABLED (the rest of the bridge is unaffected)', { dmUserId, error: opened && opened.error });
      return { enabled: false, reason: 'open-dm-failed', error: opened && opened.error };
    }
    dmChannel = opened.channel;
    enabled = true;
    timer = setInterval(() => {
      _runOnce().catch((err) => log('warn', 'bus ferry tick error', { error: err.message }));
    }, pollMs);
    if (timer.unref) timer.unref();
    // Armed HERE and not left to the first pass: the first pass is `pollMs` away, and a row
    // appended in that window is the one this whole block exists to deliver promptly.
    watchDirs(goalBuses(workspaceRoot));
    log('info', 'bus ferry started', { workspaceRoot, dmUserId, dmChannel, pollMs, watchDebounceMs, watching: watchers.size, knownRuns: cursors.size });
    return { enabled: true, dmChannel };
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (watchTimer) { clearTimeout(watchTimer); watchTimer = null; }
    for (const w of watchers.values()) { try { w.close(); } catch { /* already closed */ } }
    watchers.clear();
    enabled = false;
    log('info', 'bus ferry stopped');
  }

  // Serialization — this module owns its own shape inside the bridge's state file.
  // `jumped` rides ALONGSIDE `cursors` rather than inside it: an older state file carries no
  // `jumped` key and loads to an empty set, which is the correct reading (nothing was jumped by a
  // build that could not jump).
  function toJSON() { return { cursors: Object.fromEntries(cursors), jumped: [...jumped] }; }
  function load(obj) {
    cursors.clear();
    jumped.clear();
    for (const [k, v] of Object.entries((obj && obj.cursors) || {})) {
      if (Number.isInteger(v)) cursors.set(String(k), v);
    }
    for (const k of (obj && Array.isArray(obj.jumped) ? obj.jumped : [])) jumped.add(String(k));
    return cursors.size;
  }

  return { start, stop, tick: _runOnce, toJSON, load, _cursors: cursors, _jumped: jumped, _attempts: attempts, get enabled() { return enabled; }, get dmChannel() { return dmChannel; }, get watching() { return watchers.size; } };
}

module.exports = {
  createBusFerry, parseMessages, formatMessage, addressesOwner, goalBuses, executionStamp,
  chatThreadToken, deliverToken, rowChatThread, rowDeliver,
  OWNER_TOKEN, DEFAULT_MAX_BODY_CHARS, DEFAULT_WATCH_DEBOUNCE_MS,
  goalExecutionMode, seatIsHumanInteractive, seatDirIsHumanInteractive, isSafeName, INTERACTIVE_MODE, AUTONOMOUS_MODE,
  seatFallback, seatDirFallback, FALLBACK_ARMS, FALLBACK_PARK, FALLBACK_MARK,
  FINISH_MARKER, LEADER_CHAIR, isFinishRow, composeCompletionNotice,
  ESCALATION_ONE_LINER_MARK, isEscalationOneLiner,
};

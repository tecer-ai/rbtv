'use strict';

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
const DEFAULT_MAX_ATTEMPTS = 20;      // per-row post retries before skipping it (never unbounded)
const NOTICE_AT_ATTEMPT = 3;          // failed no-channel attempts before the owner is told (once)
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
function parseHeader(line) {
  const m = line.match(HEADER_ID_RE);
  if (!m) return null;
  const f = {};
  for (const part of m[2].split(' | ')) {
    const i = part.indexOf(': ');
    if (i > 0) f[part.slice(0, i)] = part.slice(i + 2).trim();
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
// the only one: a STANDING-SEAT HOME (`materialize-seats.py#standing_seat`, `r-master-seat-homes`)
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
// must not happen. `component-lint` refuses the combination at materialize time; `engine/lane-watch.js`
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

function formatMessage(row, { goalId, stamp, relPath, maxBodyChars = DEFAULT_MAX_BODY_CHARS, agentLead = false, arm = null }) {
  // `Object.hasOwn`, never a truthiness test on the lookup: `arm` reaches an EXPORTED function's
  // parameter, and `constructor` is a legal kebab-case word that walks the prototype chain — a bare
  // `FALLBACK_MARK[arm]` renders `function Object() { [native code] }` into the owner's Slack header.
  // The store's own `Object.hasOwn` reason, at a surface that leaves the process (review F5).
  const mark = Object.hasOwn(FALLBACK_MARK, arm) ? FALLBACK_MARK[arm] : '';
  const header = (agentLead
    ? `*🧵 ${row.from}* — ${goalId} · ${row.type} · #${row.id}`
    : `*bus → you* — ${goalId}/${stamp} · from ${row.from} · ${row.type} · #${row.id}`) + mark;
  let body = row.body;
  if (body.length > maxBodyChars) {
    const cut = body.slice(0, maxBodyChars);
    const nl = cut.lastIndexOf('\n');
    body = (nl > 0 ? cut.slice(0, nl) : cut) + `\n… (truncated — full text: ${relPath} #${row.id})`;
  }
  return body ? `${header}\n${body}` : header;
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
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
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

        // GATE 2 is a property of the GOAL, so it is read once per run pass — never per row.
        // GATE 1 is a property of the SENDING SEAT, memoized per pass: at most one descriptor
        // read per distinct `from:` name actually seen, and zero on a pass with no `to: owner`
        // row at all.
        const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', goalId);
        const executionMode = goalExecutionMode(workspaceRoot, goalId);
        const humanInteractiveMemo = new Map();
        const isHumanInteractive = (name) => {
          if (!humanInteractiveMemo.has(name)) humanInteractiveMemo.set(name, seatIsHumanInteractive(goalDir, name));
          return humanInteractiveMemo.get(name);
        };
        // The FALLBACK ARM is a property of the sending seat too, memoized the same way and read
        // only past both gates — a goal nobody can reach never opens a descriptor for it.
        const fallbackMemo = new Map();
        const fallbackArm = (name) => {
          if (!fallbackMemo.has(name)) fallbackMemo.set(name, seatFallback(goalDir, name));
          return fallbackMemo.get(name);
        };

        // In id order, so one undeliverable row does not let a later one jump it.
        for (const row of rows) {
          if (row.id <= cursors.get(key)) continue;
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
          if (!chatThread && !addressesOwner(row.to)) { cursors.set(key, row.id); persist(); continue; }
          // THE TWO GATES — on AGENT-INITIATED contact only (read their header above). A row
          // carrying a chat-thread token is answering INTO the owner's own thread and is never
          // gated; every other row reaching here is `to: owner`, i.e. initiation.
          //
          // ⚑ THE THIRD RUNG IS THE SEAT'S OWN `fallback: park` (7.626) — a seat that CAN reach the
          // owner and declared that its questions wait on the bus instead. It is a rung of this
          // ladder and not a branch of its own precisely because the disposition is identical:
          // nothing posted anywhere, cursor advanced, logged with its reason.
          let arm = null;
          if (!chatThread) {
            const gate = executionMode !== INTERACTIVE_MODE ? 'execution-mode'
              : !isHumanInteractive(row.from) ? 'human-interactive'
              : fallbackArm(row.from) === FALLBACK_PARK ? 'fallback-park'
              : null;
            if (gate) {
              cursors.set(key, row.id);
              persist();
              log('info', 'bus ferry PARKED a row — agent-initiated contact is gated, nothing posted anywhere', { key, msgId: row.id, from: row.from, gate, executionMode });
              continue;
            }
            arm = fallbackArm(row.from);
          }
          const text = formatMessage(row, { goalId, stamp, relPath, maxBodyChars, arm });
          let delivered = false;
          let error = null;
          let viaAgentThread = false;
          // The render ACTUALLY posted — the two legs render the same row differently (the
          // agent-thread header leads with the agent name), so a log that always reported the DM
          // render's length would misreport the agent leg's every time.
          let postedText = text;
          try {
            let res = null;
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
            if (!chatThread && routeToAgentThread) {
              const threadText = formatMessage(row, { goalId, stamp, relPath, maxBodyChars, agentLead: true, arm });
              res = await routeToAgentThread({ goalId, agent: row.from, text: threadText });
              // ⚑ `if (res)`, never a bare `else`: an injected `routeToAgentThread` that
              // returns nothing at all (an embedder's stub, a forgotten `return`) falls through to
              // the DM leg below, and flagging it as thread-routed would make the log claim a
              // surface the row never reached.
              if (res) { viaAgentThread = true; postedText = threadText; }
            }
            if (!res) {
              const send = routeToMaster || ((a) => transport.sendToOwner(a));
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
            cursors.set(key, row.id);
            persist();
            log('info', chatThread ? 'bus ferry routed a bus row to its named chat thread'
              : viaAgentThread ? 'bus ferry routed a bus row into the agent\'s own thread in the goal channel'
              : 'bus ferry delivered a bus row to the owner DM',
                { key, msgId: row.id, from: row.from, chars: postedText.length, arm, ...(chatThread ? { chatThread } : {}) });
            continue;
          }
          const akey = `${key}#${row.id}`;
          const n = (attempts.get(akey) || 0) + 1;
          attempts.set(akey, n);
          // THE MISSING-CHANNEL NOTICE (owner ruling 2026-08-12). A row that cannot reach its
          // goal channel is now held rather than downgraded into the DM, and a held row the owner
          // is never told about is the silence this whole module exists to end. So ONCE per stuck
          // row — `n ===`, never `>=` — he gets a line naming the goal and the seat and NOTHING
          // ELSE: no body, no header render, and posted through the transport directly, so no
          // sitting can be minted from it and no agent ever reads the row.
          if (n === NOTICE_AT_ATTEMPT && error === 'no-channel') {
            try {
              await transport.sendToOwner({
                channel: dmChannel, threadTs: null,
                text: `:warning: goal *${goalId}* has no Slack channel — seat *${row.from}* is trying to reach you and cannot. Nothing of its message is shown here. Create the channel (\`goal-channel-cli.js ensure ${goalId}\`) and it is delivered on the next pass.`,
              });
              log('warn', 'bus ferry told the owner a goal channel is MISSING — the row is held, not downgraded', { key, msgId: row.id, from: row.from, attempts: n });
            } catch (err) {
              log('warn', 'bus ferry could not post the missing-channel notice', { key, msgId: row.id, error: err.message });
            }
          }
          if (n >= maxAttempts) {
            attempts.delete(akey);
            cursors.set(key, row.id); // advance — never wedge the ferry on one row
            persist();
            log('warn', 'bus ferry giving up on a row after persistent post failures — NOT delivered, cursor advanced', { key, msgId: row.id, attempts: n, error });
            continue;
          }
          log('warn', 'bus ferry post failed — will retry next pass', { key, msgId: row.id, attempts: n, error });
          // Forget the size so the next pass RE-READS this goal. Without this the
          // unchanged-size short-circuit at the top would skip the run entirely and the
          // retry would never happen — the bound would be unreachable and the row lost.
          sizes.delete(key);
          break; // stop this goal's pass here; order is the point
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
  function toJSON() { return { cursors: Object.fromEntries(cursors) }; }
  function load(obj) {
    cursors.clear();
    for (const [k, v] of Object.entries((obj && obj.cursors) || {})) {
      if (Number.isInteger(v)) cursors.set(String(k), v);
    }
    return cursors.size;
  }

  return { start, stop, tick: _runOnce, toJSON, load, _cursors: cursors, get enabled() { return enabled; }, get dmChannel() { return dmChannel; }, get watching() { return watchers.size; } };
}

module.exports = {
  createBusFerry, parseMessages, formatMessage, addressesOwner, goalBuses, executionStamp,
  chatThreadToken, deliverToken, rowChatThread, rowDeliver,
  OWNER_TOKEN, DEFAULT_MAX_BODY_CHARS, DEFAULT_WATCH_DEBOUNCE_MS,
  goalExecutionMode, seatIsHumanInteractive, seatDirIsHumanInteractive, isSafeName, INTERACTIVE_MODE, AUTONOMOUS_MODE,
  seatFallback, seatDirFallback, FALLBACK_ARMS, FALLBACK_PARK, FALLBACK_MARK,
};

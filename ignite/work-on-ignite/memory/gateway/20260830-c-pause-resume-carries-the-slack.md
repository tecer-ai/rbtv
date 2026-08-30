# 20260830-c-pause-resume-carries-the-slack — pause-resume carries the Slack sender as chat_user

kind: change
component: gateway
date: 2026-08-30
commit: c1e3a864
deployed: no
pin: ignite/runtime/internal-api/probes/probe-pause-resume.js
components: chat,runtime,state-store

## Motivation
Owner ruling D-4(a) required the Slack pause/resume evidence text to name the person who
typed it, but the sender id never crossed the bridge boundary: `chat/pause-resume.js:126
handle({…senderId})` had the Slack principal and used it only for `isAuthorizedSender`, then
forwarded `{verb, goal}` at `:168` — the identity was BORN missing at that line, not at any
downstream consumer. A first attempt (seat `fix-pause-sender-stamp`) proposed threading the
gateway's own bearer-token `sender` through instead; that was refused correctly (`seats.md`
row) because the bearer token is always the bridge's fixed service identity
(`/etc/rbtv-ignite/senders.yaml`, one `kind: bridge` row) — wiring it through would have swapped
one constant for another and told the owner nothing new. The owner re-ruled on the corrected
premise: carry the Slack id itself, reported by the bridge, logged but never trusted.

## Design
One optional wire field, `chat_user`, added to the fifteenth intent's payload
(`{verb, goal, chat_user?}`) rather than a new intent or a new authorization channel. Optional
so a bridge deployed before this change keeps working during the deploy gap — absence is not a
refusal, a malformed value is. Shape-checked as a Slack member id (`^[UW][A-Z0-9]{2,}$`) at BOTH
independent copies (`gateway/parse.js`, `internal-api/dispatch.js#handlePauseResume`, DEC-3) —
the same lockstep the fifteenth intent's `verb`/`goal` fields already followed.
`authz.canPauseResume({sender})` is UNCHANGED and never reads `chat_user`: the bridge's
bearer-token identity stays the only authenticated principal, and the field is untrusted-but-
logged data forwarded by the bridge, never an authorization input.
Rejected: writing `chat_user` into `who_stamped`. That field is a closed two-member enum
(`owner`/`system`, `writers.js:294-301`) enforced by ~15 tests and `spec-state-store` §1.2 — a
person's identity has no legal home there. The free-text `evidence_pointer` was already the
field carrying the (wrong) literal `owner ${v} in chat · goal ${g}`, so it is where the
identity goes.

## How it works
`chat/pause-resume.js#handle` forwards `chat_user: String(senderId)` alongside `verb`/`goal` —
admission (`isAuthorizedSender`) already ran above this line, so the field is always the real
authorized sender, never re-decided. `gateway/parse.js#parsePauseResume` admits `chat_user` as
an optional key in its `rejectUnknownKeys` allowlist and shape-checks it with `CHAT_USER_RE`
before returning it in the parsed payload. `internal-api/dispatch.js#handlePauseResume` re-runs
the same allowlist + shape check independently (its own `CHAT_USER_RE` copy, DEC-3 — gateway
origin is not trust), then passes `chatUser: payload.chat_user` into
`pauseResume({…})` — a new parameter added after `countersFile`, before `logger` — without
touching the `authz.canPauseResume({sender})` call above it.
`state-store/heart/pause-resume.js#pauseResume` builds its `evidencePointer` closure
conditionally: with `chatUser` present, the text becomes
`` owner ${v} in chat · by ${chatUser} (reported by bridge) · goal ${g} ``; absent, the text is
byte-for-byte the pre-existing `` owner ${v} in chat · goal ${g} ``. `state-store/cli.js`'s
console route (`rbtv goal pause`/`resume`) passes no `chatUser`, so its evidence text — including
its known, deliberately-unfixed cost of saying "in chat" for a console action — is unchanged.

## Consequences
Nothing deleted. The mutation-anchored `pauseResume` signature the probe's R0d/R4 red-proof
pins verbatim (`probe-pause-resume.js`) was widened by one optional parameter, and the anchor
string was moved in the same change so the red-proof keeps testing the ending-home defect it
was built for, not a stale signature.

## Verification
`ignite/runtime/internal-api/probes/probe-pause-resume.js`: 59/59 (was 54/54 at 660e6cf2; +5
arms — a2a/a2b: `chat_user` present → `who_stamped` stays `owner`, evidence names the Slack id;
a2c: `chat_user` absent → pre-existing wording unchanged; f5/f6: a malformed `chat_user` is
refused at both the gateway and the core, naming the field). `ignite/chat/probes/probe-chat-
pause-resume.js`: 24/24 (was 23/23; +1 arm, a3: the forwarded `chat_user` tracks whichever
sender was actually authorized for that call, not a fixed value; a1 also now asserts the exact
three-key payload). `probe-intent-drift`: PASS, all three copies still at 15 (a field addition,
not a new intent). Gateway probes (5/5), the other 14 internal-api probes, and the remaining
chat probes (24/27, three pre-existing reds unrelated to this change) all still exit 0.
Red mutation: reverting `chat/pause-resume.js`'s forward call to `{verb, goal}` (dropping
`chat_user`) on a saved copy turned `probe-chat-pause-resume` a1/a3 red (2/24 failing); restored
and re-verified 24/24 green. `node -c` clean on all six touched `.js` files. tmux: no tmux
operation was performed by this change.
Pre-existing reds, NOT caused by this change (confirmed via a pristine `git worktree` at
26773c34): `probe-chat-ask-release` (arm E7), `probe-chat-boundary`, `probe-owner-ask-hold`,
`probe-daemon-code-fingerprint` (29/30, "and it covers a real slice of the daemon, not a token
few").
Not deployed at filing (commit c1e3a864 on `ignite/core-daemon`, HEAD advanced to `5aff5d42`
from an unrelated parallel seat's supervisor commits before this landed — no overlap).

## ATTENTION
1. BOTH HALVES MUST DEPLOY TOGETHER, same as the fifteenth intent itself. A bridge carrying `chat_user` in front of a daemon still on the old `parsePauseResume` allowlist gets `SHAPE_INVALID: pause-resume: unknown field "chat_user"` — loud, and it means the daemon-side commit did not land, not that the sender was rejected.
2. `chat_user` NEVER GATES. `authz.canPauseResume({sender})` reads only the bridge's bearer-token identity. Any future change that lets `chat_user` influence that decision reopens exactly the hole D-4(a) named: the daemon cannot verify a Slack id, so trusting it for authorization would let a forged or replayed value pause a goal in someone else's name.
3. THE CONSOLE ROUTE'S EVIDENCE TEXT IS DELIBERATELY UNTOUCHED. `state-store/cli.js`'s known cost — a console `pause`/`resume` still reads `owner ${v} in chat · goal ${g}`, naming a door the owner did not use — was NOT corrected here; fixing it means moving the R0d/R4 anchor again in a change scoped to that, per `cli.js`'s own comment on `runRootedOp`.
4. `who_stamped` STAYS THE CLOSED TWO-MEMBER ENUM. Nothing about this change touches `writers.js`'s `owner`/`system` check — a future ask to "stamp the real user" belongs in `evidence_pointer` again, never as a third enum member.
- BOTH HALVES MUST DEPLOY TOGETHER — a daemon without this commit refuses chat_user as an unknown field
- chat_user NEVER GATES — authz.canPauseResume reads only the bridge's bearer-token sender

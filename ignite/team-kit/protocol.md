# team-kit protocol — multi-agent tmux coordination

The coordination protocol every agent of a team-kit run MUST follow. A run package's `CLAUDE.md`
declares the roster and run-specific rules and points here; on any conflict, the run package wins.

Every rule below that carries a P-number was earned from a measured failure in a proving run.
P1–P26: the 2026-07-24 kg-edges-viz run (evidence: that package's `team-observations.md` and
`agent-teams-strategic-lessons.md`). P27–P38 and the queue/amendment items: the 2026-07-24
kg-views-rebuild run (evidence: its `run-observations.md` §4 proposals and `roster-review.md`
amendments, reconciled against this kit in `fact-check-views-rebuild-vs-kit.md`). These are not
style preferences.

An **`S§n`** pointer cites the same kg-edges-viz package's `agent-teams-strategic-lessons.md` at
section `n` — the observer's strategic findings, which were never numbered as proposals and so
carry no P-number. Rules citing `S§` were folded 2026-07-26 from the run-1 fact-check
(`fact-check-kg-edges-vs-kit.md`, beside the other two).

A **`PROP-n`** pointer cites the 2026-07-24 tv-ux-review run — the third proving run, a 28-seat
5-model wave test over an external CLI (evidence: that package's `run-observations.md`, one
`### PROP-n` section per proposal). Its unlanded proposals were folded 2026-07-26.

## The CLI

```
COORD="coordinate --run {run-tag}"     # or: python3 {team-kit}/coord.py --package {abs-run-package}
                                       # from inside the package folder, neither flag is needed

$COORD checkin <agent> "<summary ≤560 chars>"   # on start — binds this pane to your name, supersedes any prior row (P1); REFUSED while a live pane still holds the name (P37)
$COORD status                                   # where you stand: pane, owner, unread by type, cursor, asks waiting on you
$COORD read                                     # your unread messages, 10 at a time; cursor persisted + advances (P26)
$COORD read --digest | --msg N | --after N      # one line each | one message in full | replay from N (all peek-only)
$COORD read --peek | --all | --type T | --addressed any|direct|broadcast   # peek-only views too
$COORD pending                                  # open asks: waiting on you, open to everyone, yours unanswered
$COORD send <to> "<msg>" --type T --inline      # T ∈ completion|ask|answer|verdict|note (P2); --inline is REQUIRED for a typed body (G-181)
$COORD send <to> --file PATH|- --type T         # body from a file or stdin — no shell touches it (backticks, quotes, newlines)
$COORD send <to> "<msg>" --type answer --re N --inline   # the ask this settles — REQUIRED on answer, optional on verdict
$COORD send <to> "<msg>" --type T --supersedes N --inline   # retract message N (P12)
$COORD workers                                  # roster + live-pane check + owner presence + per-seat unread lag
$COORD owner present|reachable|afk [--note ".."]  # owner/leader only (P15). reachable = at the PC,
                                                #   no master session running: escalate by LAUNCHING
                                                #   THE DOOR. `--help` states all three (7.85)
$COORD launch [--only a,b,c] [--dry-run]        # leader only — per-seat harness/model/effort; pre-validates every seat's harness/model and refuses BEFORE opening any pane (PROP-8)
$COORD create-group <group> [member ...]        # creator + leader auto-included
$COORD add-to-group <group> <member ...>        # leader only
$COORD export-transcript <agent> [--label L]    # full pane scrollback -> workers/<agent>/transcripts/
$COORD checkout                                 # on finish (done disposition) — exports your transcript first (--no-export skips)
$COORD checkout --renew --handoff "<note>"      # renewal disposition — two-step, the CLI teaches it; the handoff lands in your memory.md (item 8)
$COORD depart                                   # ephemeral seats: export + checkout + kill own pane
$COORD close <agent> [--renew]                  # leader only — FAILURE PATH: spawn a closer to dirty-close/salvage a seat that cannot check itself out. A healthy seat renews itself (line above), never through this
$COORD close-seat <agent> [--renew] [--no-export]  # mechanical close — leader's remedy for a dead pane, and the closer's own tail step
$COORD panel                                    # leader only — open the control-panel overview pane (live tmux-overview + plan usage)
```

**You never type your own name.** Identity is resolved: `--as NAME` > `$COORD_AGENT` (injected
into every launched seat) > the calling pane's roster row. A claim that contradicts the pane's
registered agent is REFUSED, naming the registered one. Where `<agent>` still appears above
(`export-transcript`, `close`, `close-seat`, `approve`), it is the seat being ACTED ON, never the
caller. `--force` is the single deliberate override on any refusal (identity, role gate,
recipient/length/`--re` validation); leader-only commands hard-refuse everyone else.
`--pretty` (or `COORD_PRETTY=1`) adds colour and aligned columns to `status`/`workers`/`read`/
`pending` for a human reader; the default output is plain. Full surface: `coordinate -h` (grouped
one-line index) and `coordinate <command> -h` (arguments, one example, the step that follows).

**Control-panel layout.** The leader window is the run's control panel: leader, the oversight
seats (watcher/observers), on-demand closers, and the `panel` overview pane — target ≤6 panes.
Working seats declare `window: yes` and live in their own named windows (tabs).

State files (`{package}/coordination/`) are script-managed: NEVER edit them by hand;
`messages.md` is append-only.

## Session protocol — every agent

1. **Check in first.** Before any briefing work: `checkin` with your roster agent name and a
   summary of what you are working on. The summary (max 560 chars, enforced) is your discovery
   surface — name what you change/produce and which shared surfaces you touch; "working on the
   task" is useless. A re-check-in (relaunch, recovery) supersedes your prior row automatically —
   UNLESS the pane that already holds your name is still alive, in which case the check-in is
   REFUSED (P37): follow R-confirm-dead before you retry.
2. **Startup round — organize BEFORE you discuss.** No detailed cross-agent discussion on `all`
   at run start. Leader announces a turn order; each agent, in turn, sends ONE short intro
   (`--type note`, direct to `leader` — a note broadcast is refused by the tool): what it
   produces, which shared surfaces it touches, which overlaps
   with already-posted intros it foresees, and — **publish your contract** (S§3.3) — what it can
   and cannot ACCEPT from upstream: the constraint that would make a peer's output unusable to you
   (last run: "edges of these verbs render in my views; others are authored-but-invisible"), since
   a collaborator cannot avoid an interface it was never shown. No replies until the round
   completes. Then the
   overlapping agents `create-group` one group per identified workstream/overlap (leader
   auto-joins) and ALL detailed discussion happens in those groups. The same applies to
   later-launched agents: one intro note on checkin, then into groups. (The prior run opened with
   multicast-inside-broadcast walls of text and formed its first group at message #16 — the
   organizing step existed nowhere; now it does.)
3. **Send messages at coordination points:** when you start; BEFORE touching any shared surface
   another agent may also touch; when you complete a milestone that changes what another agent
   builds against; when blocked; and when done. Every send carries an honest `--type`: an ask that
   needs an answer is an `ask`, never a `note`. After the startup round, `all` carries only
   milestones, completions, retractions, and facts every seat needs — threads live in groups.
4. **Wakes.** `send` types a `[coord wake]` line into each recipient's pane carrying the exact
   `read` command to run — it names no agent, because your own pane resolves who you are. When one
   appears in your conversation, run it, act on the message, continue. Wakes CAN be lost (dialog
   open, pane busy) — failures are recorded in the log as `> delivery-failure:` lines, which
   `read` renders as a `[log]` trailer under the message they follow, and you MUST also run `read`
   at natural checkpoints. Never rely on wakes alone. A recipient parked on its harness's approval
   prompt is deliberately SKIPPED, never woken (8(b)) — keystrokes into a modal cannot be read and
   can land inside the gate itself; `send` names that seat in its summary so leader can `approve`
   it, and the seat picks the message up on its next `read`.
5. **Cursor discipline (P26).** `read` shows at most 10 messages, starting from your persisted
   cursor, and advances that cursor ONLY through the last message it actually SHOWED — so nothing
   you were not shown is ever marked read, and the footer tells you how many are still waiting.
   Every filtered or peek view (`--type`, `--addressed`, `--digest`, `--msg`, `--peek`, `--all`)
   leaves the cursor untouched and says so in its own output. After a context loss or revert, use
   `--after N` or `--all` to replay — auto-advance plus no override would turn a context loss into
   permanent message loss; the override is the safety.
6. **Retraction (P12).** The moment you discover a number, claim, or inventory you published is
   wrong, send the correction with `--supersedes N` pointing at the wrong message. Never rely on a
   later prose correction alone — an arbiter reading to catch up will rule on whichever message it
   reaches first.
7. **Conflicts and decisions go to `leader`.** If you and another worker discover an inconsistency
   between yourselves, do not settle it pairwise: `create-group` (you + the other; creator and
   leader auto-added) and put the question there. Anything owner-gated is escalated by leader to
   the owner — never ruled by leader, and never carried to the owner by you (R-owner-channel).
8. **Check out last — completion first.** When your briefing is complete: send your completion
   DIRECT to `leader` (`--type completion`; to `all` only when it carries a milestone or roster
   consequence — the broadcast `--why` gate enforces exactly that), then `checkout`. The transcript export is no longer yours to remember —
   `checkout` captures your pane's scrollback before flipping your row (`--no-export` is the
   escape when the pane is already dead). A checkout carries a DISPOSITION. Done: plain `checkout`
   — completion to `leader` first, then check out; no handoff. Renewal or context refresh:
   `checkout --renew`, which teaches you the second step; you MUST supply `--handoff "<note>"`
   before the seat is renewed. The handoff is appended to your seat's `memory.md` and printed to
   your successor at its check-in. A `close: mechanical` seat is REFUSED on this self-service
   path — memoryless by design, its renewal stays the leader-side close-and-relaunch. (Evidence:
   the build-core-daemon-mvp run-2 core-build batch, 2026-07-28 — a caller-only role gate refused
   a seat's owner-ruled self-renewal at 15:1x because the only renewal path ran through another
   seat's close ceremony; and G-257, a refusal text teaching `--force` as the remedy for a ruled
   act.) The second call can still REFUSE to bring the successor up — no briefing, no computable
   tmux target (a seat that has drifted out of the window its descriptor names is one), an
   unreadable caller identity, or an unwritable marker/log. Each refusal exits 2 and says YOUR
   CHECKOUT STANDS: the handoff is written and the roster flipped, only the relaunch did not
   happen, and the printed remedy is leader's `close-seat <you> --renew` — never a closer.
   Ephemeral seats use `depart` (export + checkout + killing
   the seat's own pane, one command, no name — a seat can only depart itself). Leader checks out
   only after all workers have.
9. **Memory (persistent seats only).** `workers/<you>/memory.md` is your seat's cross-session
   memory, co-written with a closer seat at a CLOSE, and appended to by `checkout --renew
   --handoff` at a RENEWAL (no closer is in the renewal path — evidence: the same run-2 15:1x
   gate refusal item 8 cites; the closer ceremony was the only renewal path and it never composed
   with a seat's own act). If it exists at boot, read it after your
   briefing and trust it as your own notes (re-verify what is cheap to verify). When a closer
   contacts you with a draft memory (`--type ask`), answering it IS briefing work: correct it,
   fill what only you know, reply promptly — an unanswered closer writes your memory alone.
   Ephemeral seats have NO memory by design: never create one, never read prior-pass artifacts.

## Execution rules

- **R-go-gate (P6).** A briefing's status line outranks a launch instruction. A launch prompt is
  NEVER the owner go a status line demands. If your briefing says "do not execute without an
  explicit owner go", downgrade to read-only preparation and ask leader.
- **R-audit-premises (P10).** Your briefing's first executable step, always: verify every factual
  claim it makes about the target system against the live system (compute, don't reason). A third
  of the last run's briefings contained a false premise. If the briefing is wrong, surface it —
  never silently reinterpret, never repair the data to fit the spec.
- **R-single-writer (P7).** Every shared file has exactly ONE writer at a time. The run package's
  `CLAUDE.md` carries the surface-ownership map; before touching a surface not clearly yours,
  claim it in a message and wait for no-objection or a leader ruling. New code beats patch-lists:
  if two agents need the same file, negotiate a boundary by change-kind and sequence.
- **R-grep-classify (P9).** Grep to FIND, read every hit to CLASSIFY. A raw `grep -c` is not a
  count; an inference from incidental lines is not an inventory. Both produced confident wrong
  numbers within twenty minutes last run. No sed/bulk-replace on tokens that are also English
  words — comments do not lint, so a corrupted comment ships green.
- **R-compute (deterministic-first).** Any figure you publish carries the command that derived it.
  Never hand-copy a count into prose a script can compute — hand-maintained numbers drift
  systematically (five stale counts in 25 minutes last run). Prefer count-free prose.
- **R-confirm-before-carry (P14).** Before a ruling or an owner-ask turns on a number or inventory
  a worker produced, cite the message it came from and have its producer confirm it still stands.
- **R-bounded-wait (P13).** When leader does not answer and you are blocked: proceed on the
  unambiguous part, record the blocked part as DEFERRED in the run's ledger/notes, file the open
  question per the run's issue conventions, and disclose — never invent a self-authorized timeout,
  never escalate past leader to the owner uninvited.
- **R-owner-channel (owner-ruled 2026-07-24).** ONLY leader initiates contact with the owner. A
  worker NEVER messages, prompts, or asks the owner unprompted — every owner-gated question goes
  to leader as an `ask`, and leader presents it in leader's own pane. If the owner addresses YOU
  in your pane, answer exactly what was asked (initiate nothing further), then relay per
  R-owner-relay. This matches the registry's own worker record: replies to the owner only when
  addressed, never initiates.
- **R-owner-relay (P16).** Any direct owner ruling received in YOUR pane is posted to `all`
  IMMEDIATELY (`--type verdict`, citing the ask it answers). The log must stay the complete
  decision record — an owner channel the log cannot see is how the last run lost rulings.
- **R-joint-executability (P20).** After any batch of rulings is relayed, the affected worker
  states in one line what the COMBINATION requires that no individual ruling did. Two
  individually-sound rulings were jointly unshippable last run; only code showed it.
- **R-cost-symmetry (P21).** In any decision ask, derive the cost enumeration for the option you
  are NOT recommending by the same method as for the one you are. An under-costed rival option
  corrupted an owner decision last run.
- **R-cheap-ask (S§6.3, S§3.3).** The decider is the scarcest resource in the run, so pay for the
  decision, not just the question. Two halves, both measured: **(a) design your unblock to cost one
  word** — when you are blocked on a call someone else must make, hand them a fallback they can
  approve with a single token ("proceed on the fallback unless you say otherwise"), never an open
  question that forces them to author the answer. **(b) Batch, with per-item defaults** — a set of
  questions goes out as ONE ask carrying a one-line recommended default per item, and the reply may
  settle any SUBSET: what the decider does not touch stays HELD. "Held" means exactly that — it is
  never a licence to proceed on an unanswered item, which is `R-bounded-wait`'s self-authorized
  timeout under a new name. Attacking the cost per decision compounds with leader's escalate-first
  drain order; ordering alone did not clear the queue last run.
- **R-negative-result (S§3.3).** When you report an analysis, list what you checked and found
  IRRELEVANT alongside what you found. "Absent from a list" is otherwise indistinguishable from
  "never looked at", and a decider cannot tell an exhaustive answer from an under-scoped one — which
  is exactly how a narrow analysis misleads without anyone lying.
- **R-disclose-challenge (S§3.3).** For a judgment call inside your own scope, neither ask
  permission nor act silently: make the call, state it explicitly in a message with the reasoning,
  and invite an override. Asking burns the arbiter on something already yours to decide; acting
  silently denies every peer the chance to catch a call their vantage can see is wrong and yours
  cannot.
- **R-commit-discipline (P18/P23/V1).** The git index is shared mutable state: commit by explicit
  pathspec only, never add-all; `git diff` every file at the instant of staging and confirm your
  delta is still present; treat regenerate-and-commit as a critical section (announce, hold, land,
  release). **Never leave anything staged in the shared index between your own commits** (V1) —
  stage and commit in one motion, and check `git diff --cached` is empty before you step away. A
  half-staged index is invisible to every other seat, and the next seat's explicit-pathspec commit
  sweeps your staged hunks into ITS commit without either of you seeing it happen.
- **R-last-lander (P24).** Whole-tree generated projections (views, logs) cannot be split by
  pathspec: the LAST lander regenerates them from the committed tree; earlier landers exclude them
  and disclose the gap.
- **R-write-through (P25).** Any analysis, finding, or draft you would grieve losing goes to disk
  the moment it exists, incrementally — never batch-at-the-end, never chat-only. A context revert
  mid-run cost nothing last time ONLY because the observer wrote live.
- **R-verify-claims (sub-agents rule).** On any dispatch or handoff, verify claimed files exist at
  their claimed paths before trusting the report.
- **R-stamp-wording (P19).** Never write a verification instruction that cannot pass (e.g.
  "byte-stable ×2" over output carrying a generation timestamp). Say "content-stable modulo the
  generation stamp" — a check that cannot pass trains rubber-stamping.
- **R-scan-stamp (P29).** A finding is only true of the artifact state you scanned. Before you
  start a validation/review pass, record the SCAN-START stamp — `git rev-parse HEAD` plus the
  clock — and open every finding you file with it (`scanned-at: <sha> <time>`). Whoever disposes
  of the finding re-checks it against the artifact NOW: `git diff <sha>.. -- <path>` empty means
  the finding still describes the file; non-empty means re-verify before ruling. Twice last run a
  finding was disposed against a file that had already changed under it — the reviewer and the
  arbiter were arguing about two different artifacts and neither could tell.
- **R-confirm-dead (P37).** Never relaunch a seat you have not CONFIRMED dead, and never kill one
  by name. Look at the pane first (`tmux capture-pane -p -t <pane-id>`); if it must go, kill it by
  PANE ID (`tmux kill-pane -t <pane-id>`) — a name matches whatever tmux resolves it to today,
  which during a double-launch is the wrong session. `checkin` enforces the confirm half (it
  refuses while the registered pane is alive); the kill-by-id half is yours. Two live sessions
  under one name are mutually blind: unread is filtered by NAME, so neither sees the other's
  messages, and only the newest pane receives wakes.
- **R-rebrief-on-resume (PROP-6).** A fix shipped to a briefing/config file mid-run does NOT
  reach a seat resumed from pre-fix context: a resume continues from the seat's own transcript
  memory, silently replaying the bug the run already closed (two crash-resumed seats re-hit the
  fixed checkin bug over half an hour after the fix landed in all 35 briefings). Whoever resumes
  or relaunches a seat that was alive before a mid-run fix landed MUST either relaunch it fresh
  from the fixed briefing (the standard remedy) or explicitly instruct the resumed seat to
  re-read its briefing before its next coordination call — never assume "fixed in the file"
  means fixed in the seat.
- **R-runnable-saves (PROP-7).** When the artifact you are editing is executed LIVE by other
  seats or by the run's own control loop (a fix-track seat editing the tool under test; this
  kit's own scripts), every SAVED state must be syntax-valid and selftest-green — never leave a
  multi-step edit mid-transition on disk. A two-write constant swap broke the run's own
  gate-scanning dashboard in the window between the writes, mid-wave. Stage multi-step changes
  so each save is runnable; seats that depend on the artifact keep a raw fallback (manual tmux
  scanning) for exactly this failure.
- **R-serialized-browser (queue 11).** Headless browsers are the run's scarcest resource, not a
  free one: each Chromium is hundreds of MB and several of them at once is how a run box reaches
  its memory ceiling and starts killing seats. Run at most ONE at a time across the whole run —
  claim it in a message before you launch, release it in a message when you close it, and never
  hold it across a wait. The same budget governs any other heavyweight local process a seat
  spawns.

## Role-scoped rules — beside this file, opened only when the trigger is yours

- **Authoring a run's briefings or seat descriptors** (the assembler at bootstrap, or a live run's
  seat-authoring role, at the moment it writes one): read `briefing-authoring.md`.
- **Holding a leader, deputy, scientist, judge, verifier, closer or watcher role — or running a
  codex/opencode harness**: read `roles.md`.

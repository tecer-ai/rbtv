---
id: summarizer-cycle
description: "Run one meeting-summarizer cycle inline, in the current turn: detect new meeting transcripts, summarize each, file and publish the settled ones, apply any owner answer from the last grouped question, and ask a new grouped question only when a doubt is genuinely open. A cycle with nothing new and no open question ends with replies: [] — never a status or verification note. Use on every scheduled wake of the meeting-summarizer agent — never in a chat reply to an unrelated request."
exposes:
  path: [materialize-config, detection-cycle, artifact-bindings, per-meeting-job, publish-job, doubt-answer, verify-access]
---

<role>
- **agent type** — staff. The same cycle for any account pair, any meeting, any owner.
- **persona** — the cycle runner. Your worth is that every new meeting gets exactly one summary,
  filed once, and that the owner is asked exactly once per open question — never zero times
  (a doubt going unasked is a summary that silently keeps a wrong guess), never twice.
- **scope** — one scheduled wake is one cycle, run start to finish in THIS turn, in the foreground.
  You never leave a background process to finish the turn: every command below runs to completion
  and its output is read before you act on it. You do not decide a destination, a summarizer
  skill, or an account list yourself — those are configuration, read at run time.
- **before you run anything**: decide your closing disposition LAST, from what actually happened this
  cycle — never write a status, verification, or "all good" note because the cycle ran. Nothing new,
  nothing applied, no doubt or routing question open → `replies: []`, `disposition: completed`, and
  say NOTHING — a quiet cycle IS the correct, reportable outcome, not a thing to additionally confirm
  (measured live, 2026-09-28: a when-useful cycle with nothing to report still posted a verification
  note — the rule existed later in this file but was not read before the agent acted). Step 7 restates
  this at the point you compose the reply; this line exists so you carry it from the first command on.
</role>

<procedure>
This capability carries no settings of its own — an agent installing it supplies a settings file
and a state folder, never a value typed into this skill (owner ruling 2026-09-28, "Agent settings
vs capabilities"). Resolve, ONCE per turn, before step 1:

- **Tools directory** — this capability's own `tools/` folder. Find it by reading `rbtv_path` from
  the workspace's `rbtv.json` (at the workspace root) and joining `office/meeting-summarizer/tools`.
  Call this `<tools>` below.
- **State directory** — `<agent-home>/state/` (`<agent-home>` is `$IGNITE_AGENT_HOME` inside a turn;
  starts empty on a new agent, nothing migrates from a prior instance). `doubts.jsonl`,
  `outcomes.jsonl`, `resolved-doubts.jsonl`, `asked-doubts.jsonl`, `processed-transcripts.jsonl`,
  `asked-routing.jsonl`, `resolved-routing.jsonl` all live directly under it — call this `<state>`
  below. The last two are this skill's own plain JSONL files (one line per row, appended with your
  own file tools — no CLI owns them) tracking which meetings have an open routing question and which
  are settled; they do not exist until the first routing question.
- **Config root** — `<agent-home>/config/`. Every tool call below passes `--config-root`/
  `--config-dir <agent-home>/config` explicitly; never rely on a tool's own default. **EVERY cycle,
  before anything else, run:**
  `python3 <tools>/materialize_config.py --settings <agent-home>/settings.json --config-root <agent-home>/config`
  It overwrites `config/*.json` fresh from `settings.json` (the agent's own settings, and its ONLY
  copy — standing instructions already tell you to read it) every time it runs. NEVER skip this
  because `config/` already exists from a prior cycle: it is a DERIVED cache, rebuilt every cycle,
  never a second copy an owner edit could leave stale. Nothing under `config/` is ever hand-edited or
  read as authoritative on its own. `detection-cycle` finds `<state>/processed-transcripts.jsonl` — the
  SAME file `publish-job` writes to — by itself, from `--config-dir` alone: it needs no flag from this
  command and no particular call order, because `<state>` is always `config_dir`'s sibling in the
  fixed agent-home layout. (Rounds 3-4 tried making this reachable only through a `--state` flag this
  command had to be given, before the tick, in the same turn — correctly judged "a prompt, not a fix":
  a turn that ran the tick FIRST, before reading this far, still ticked on the stale default. There is
  nothing left to pass or order for this specific store any more.)
- **Channel directory** (the per-meeting routing-ask bookkeeping `per_meeting_job.py` uses; nothing
  chat-specific) — `<state>/channel`.
- **Checkout root** (where destination repos are cloned) — read `<agent-home>/config/runtime.json` →
  `checkout-root` once config root is materialized. Call this `<checkout root>` below.
- **Scratch** — a fresh working directory for this cycle's own job files, artifact downloads and
  per-meeting work folders: `<agent-home>/tmp/<a timestamp you pick>/`. Call this `<scratch>` below;
  it is yours to create and never shared with another cycle.

1. **Apply any owner answer first.** Read this conversation's recent history for the owner's reply
   to the LAST grouped question you asked (if any is still open). There are two kinds of open
   question, checked and applied independently:

   a. **Glossary-term doubts** — check `doubt_answer.py list-open` below; a term it no longer lists
      is already resolved or was never asked, so there is nothing to apply. Match each answered term
      in the owner's reply to its open doubt by name — this is your own reading, not a lookup table,
      because there is one conversation and no per-meeting thread to key on. For each term the owner
      answered, run:
      `python3 <tools>/doubt_answer.py apply --meeting-key <K> --term <T> --answer-text "<owner's exact words for that term>" --config-root <agent-home>/config --checkout-root <checkout root> --state <state>`
      Read the JSON result. `"landed": true` means the summary was corrected, committed and pushed —
      report it plainly. `"landed": false` means it is still open; report why and leave it — a failed
      apply is never silently retried by guessing, and it stays open for the NEXT cycle to try again.

   b. **Routing questions** — read `<state>/asked-routing.jsonl` for a meeting-key with no matching
      row in `<state>/resolved-routing.jsonl`. For each one still open, read `<agent-home>/config/destination-routing.json`'s
      routes and match the owner's reply against a declared route `entity` name (your own reading —
      the owner may name it loosely; match it to the one route it clearly means, or treat the reply
      as not yet a clear answer and leave the question open). On a clear match:
      1. Append one line to `<state>/outcomes.jsonl`: `{"meeting-key": "<K>", "outcome": "amended", "content-entity": "<the matched entity>", "at": "<now, UTC ISO>"}` — this is the same shape
         `per_meeting_job.py`'s own settlement rows carry; `publish_job.py` reads the LATEST row per
         meeting-key, so this one now wins.
      2. Retry publishing that meeting immediately, in this same turn: run `publish_job.py precheck`
         then (if it no longer refuses) `cycle`, exactly as step 5 describes, using the SAME job file
         from `<scratch>/jobs/<meeting-key>.json` if this cycle already wrote one for it, otherwise
         reconstruct it from `detection_cycle.py status`.
      3. On success, append `{"meeting-key": "<K>", "resolved-at": "<now>"}` to
         `<state>/resolved-routing.jsonl`. On failure, report why and leave both files as they are —
         the question stays open and the same retry is attempted again next cycle once you re-read
         the (still-present) owner reply from history.
      A reply that names no recognizable entity is NOT applied and NOT marked resolved; say so
      plainly in this turn's reply and re-ask the SAME routing question in step 7's grouped message
      (a clarification, not a second question).

2. **Run one detection tick:**
   `python3 <tools>/detection_cycle.py tick --config-dir <agent-home>/config`
   Read the JSON result whole. A tick that refuses (REFUSED on stderr, empty stdout) is reported as
   a failed cycle — never re-run a refused tick; that is how one poll becomes two. From the result,
   keep every job whose disposition is NOT `already-done` and that is not in `skipped-parked` — that
   is this cycle's pending set. Report, by count (zero included): admitted meetings, meetings not
   admitted (parked, below-floor, already processed, awaiting-transcript), and the watermark before
   and after.

3. **Stage this cycle's artifacts, once, for the whole pending set** (skip if pending is empty):
   `python3 <tools>/artifact_bindings.py --jobs <pending-jobs.json> --out-dir <scratch>/artifacts --config-dir <agent-home>/config`
   where `<pending-jobs.json>` is the pending job list you just wrote to a scratch file. This
   downloads every Drive reference once and writes `bindings.json` in `<scratch>/artifacts/`.

4. **For every pending job, run one per-meeting job** (each is independent; running them serially
   in this turn is correct — do not background any of them):
   - Write the job's JSON to `<scratch>/jobs/<meeting-key>.json`.
   - Create its work directory `<scratch>/work/<meeting-key>/` and write a `CLAUDE.md` there
     carrying a `## Name Glossary` section naming `.user/docs/glossary.md`.
   - Run:
     `python3 <tools>/per_meeting_job.py --job <scratch>/jobs/<meeting-key>.json --artifacts <scratch>/artifacts/bindings.json --config-root <agent-home>/config --checkout-root <checkout root> --channel <state>/channel --state <state> --work <scratch>/work/<meeting-key>`
   - This call itself launches a separate, unattended `cast` turn that reads the transcript and
     writes the actual summary in the summarizer skill's own format — you do not read the
     transcript yourself and you do not draft any part of the summary. Read the JSON verdict this
     command prints: the action it took, the outcome, and whether a doubts handoff row landed.

5. **File every settled meeting.** For each meeting whose outcome is `filed` or `amended` in
   `outcomes.jsonl` and that carries no row yet in `processed-transcripts.jsonl`, run:
   `python3 <tools>/publish_job.py precheck --job <scratch>/jobs/<meeting-key>.json --config-root <agent-home>/config --checkout-root <checkout root> --state <state>`
   then, only if the precheck does not refuse:
   `python3 <tools>/publish_job.py cycle --job <scratch>/jobs/<meeting-key>.json --summary <the summary file the verdict named> --config-root <agent-home>/config --checkout-root <checkout root> --state <state>`
   Read each result. This commits and pushes inside this call — never a separate step, never
   deferred to a later turn.

   **A precheck that comes back `disposition: unroutable`** is NOT a refusal to report-and-move-on
   from (never `disposition: continue` for this) — it is an open routing question. If
   `<state>/asked-routing.jsonl` carries no row for this meeting-key yet, append
   `{"meeting-key": "<K>", "title": "<the meeting's title, for the question>", "asked-at": "<now>"}`
   and include it in step 7's grouped question. If it is already there, leave it — it is already
   asked and step 1 already checked this turn for an answer; do not run `cycle` for it and do not
   report it again as a fresh find (step 7 still lists it among the OPEN questions, so the owner is
   never left wondering whether it is still pending).

   **A `cycle` that REFUSES (`publish_job: summary: cannot read --summary ...`, exit `EXIT_REFUSED`)**
   means the summary path a verdict named is stale — the meeting's transcript and its content are
   still there, only the path a prior pass reported no longer resolves (the destination folder moved,
   or this scratch dir's own job file is older than you think). This is NEVER "the file was deleted":
   do not ask the owner about it, and do not touch `resolved-doubts.jsonl`/settlement rows on this
   premise. Re-run `per_meeting_job.py` for that meeting fresh (same as step 4) to get a CURRENT
   `summary-file` value, then retry `precheck`/`cycle` with it, in this same turn if time allows. If
   the refusal recurs, leave the meeting for the next cycle — report the refusal plainly, do not
   invent a reason for it.

6. **Check for open questions — both kinds.**
   - Glossary doubts: `python3 <tools>/doubt_answer.py list-open --state <state>`. For every doubt
     this prints that this cycle's own pending set produced (a fresh doubt from step 4), mark it
     asked once you include it in your question: `python3 <tools>/doubt_answer.py mark-asked --meeting-key <K> --term <T> --state <state>`.
     A doubt already asked in an earlier cycle and still unanswered is NOT re-asked — `list-open`
     already excludes it.
   - Routing questions: read `<state>/asked-routing.jsonl` minus `<state>/resolved-routing.jsonl` —
     every remaining meeting-key is an open routing question (step 5 already appended the fresh ones
     and step 1 already tried to resolve them from this turn's history).

7. **Compose the report.** ONE grouped reply, in the SAME conversation this wake arrived on — never
   open a new thread for it (`ignite-agent post` is for a proactive check that belongs to NO existing
   conversation; a scheduled wake of an already-created agent always continues its own conversation).
   - Nothing filed, nothing applied, nothing newly open: `replies: []`, `disposition: completed`.
     A quiet cycle is a correct cycle — never manufacture a status update.
   - Something filed and/or an answer was applied, with no doubt or routing question open: report it
     plainly (load the `slack-message-format` skill first), `disposition: completed`.
   - A doubt OR a routing question is open (whether or not something also filed this cycle): report
     what filed, THEN ask every open item in the SAME grouped message — each doubt (term, guess,
     meeting) and each routing question (meeting title, the declared entity choices from
     `destination-routing.json`) — `disposition: waiting_owner`. Do not end the turn on
     `waiting_owner` while a background command is still running; everything above must already be
     finished.
   - A stage refused for a reason that is NOT an open question (detection, a per-meeting job, a
     publish precheck/cycle failing for any reason other than `unroutable`): report the refusal
     plainly, do not retry it yourself, `disposition: continue` with `nextStep` naming the next
     scheduled wake as the retry point — unless the refusal means the whole cycle cannot proceed, in
     which case report it and still end the turn (never hold the turn open waiting for a fix).
     `unroutable` is never reported this way — it is step 5/6's open routing question, and it drives
     `disposition: waiting_owner`, never `continue`.
</procedure>

<resources>
- `materialize-config` (`materialize_config.py`) — overwrites `<agent-home>/config/*.json` from
  `settings.json`, every cycle. Run this FIRST; every tool below reads what it wrote.
- `detection-cycle` (`detection_cycle.py`) — `tick` polls every watched account and source once,
  settles meeting identity, advances the one whole-poll watermark, and emits this cycle's pending
  jobs; `status`/`retry`/`schedule`/`keys` read back state without polling.
- `artifact-bindings` (`artifact_bindings.py`) — downloads every Drive reference the pending job set
  names, once, into a shared `bindings.json`.
- `per-meeting-job` (`per_meeting_job.py`) — runs ONE meeting through the summarizer skill (via its
  own nested, unattended `cast` call) and records the settlement and any doubt.
- `publish-job` (`publish_job.py`) — `precheck` then `cycle` files, commits and pushes one settled
  meeting. Reads the latest `content-entity` row in `outcomes.jsonl` per meeting — a routing answer
  you settle there (step 1b) is what a retried `precheck` resolves against.
- `doubt-answer` (`doubt_answer.py`) — this agent's own glossary-doubt ledger: `list-open`,
  `mark-asked`, `apply`. Talks to no chat surface — that is your `replies`/`ignite-agent post`.
  Routing questions follow the same pattern with no CLI of their own (steps 1b, 5, 6).
- `verify-access` (`verify_access.py`) — reached only when a tick refuses at the account boundary:
  says which watched folder or account grounding is missing.
- `gtools` — the underlying Drive/Meet API client `source_adapter.py`/`artifact_bindings.py` call;
  you never call it directly.
- `slack-message-format` skill — load it before composing any owner-facing reply.
</resources>

<io-spec>
## Inputs
- Schema: a scheduled wake (no owner text) or a conversation turn carrying the owner's answer to a
  previously asked grouped question. Description: which accounts, folders, destinations and
  summarizer skill bindings apply is configuration, read at run time — never given in the trigger.

## Outcome
Every new meeting is either summarized, filed, and pushed exactly once, or is reported as
deliberately not admitted; every settled owner answer (a glossary term or a routing choice) is
applied and committed; every doubt or routing question still open is asked exactly once and never
silently dropped, and never reported as a plain refusal.

## Outputs
- Schema: this turn's `replies` (plain text, phone-first, grouped) and, on disk, the same
  `outcomes.jsonl` / `doubts.jsonl` / `processed-transcripts.jsonl` / `resolved-doubts.jsonl` /
  `asked-doubts.jsonl` rows the tools above write directly, plus `asked-routing.jsonl` /
  `resolved-routing.jsonl` and the synthetic settlement row in `outcomes.jsonl` (step 1b) that you
  write yourself with your own file tools — every OTHER write is a tool's own, never done by hand.
</io-spec>

<permissions>
- Read: this agent's `settings.json`, its materialized `<agent-home>/config/*.json`, `<state>` and
  its `channel` subfolder, and every summary/transcript file the tools above name.
- Run: `materialize-config` (every cycle, first), `detection-cycle`, `artifact-bindings`,
  `per-meeting-job`, `publish-job`, `doubt-answer`, and `verify-access` when a tick refuses at the
  account boundary.
- Write: `<agent-home>/config/*.json` (via `materialize-config`, every cycle — never by hand),
  `<scratch>`, and `<state>/asked-routing.jsonl` / `<state>/resolved-routing.jsonl` / the one
  synthetic settlement line you append to `<state>/outcomes.jsonl` for a resolved routing answer
  (step 1b) — every other write (doubt/outcome rows a tool produces itself, filed summaries, git
  commits/pushes) is a tool's own, never done by hand.
</permissions>

<restrictions>
- Never invent a destination, a summarizer skill, or an account — a tool's refusal is reported, not
  worked around. The one exception is a routing answer the owner has actually given (step 1b) —
  that is the owner naming it, not you inventing it.
- Never re-run a refused detection tick, and never move its watermark by hand.
- Never draft or edit summary text yourself — `per_meeting_job.py`'s nested agent call and
  `doubt_answer.py apply`'s amendment call are the only writers of a summary file.
- Never ask a doubt `list-open` does not currently list, and never ask the same term twice.
- Never report an `unroutable` precheck as a plain refusal with `disposition: continue` — it is an
  open routing question (steps 5-7), and it drives `waiting_owner`.
- Never mark a routing question resolved (`resolved-routing.jsonl`) on a reply that names no
  declared entity — leave it open and ask again as a clarification of the SAME question.
- Never end the turn with a command still running in the background — a turn is one shot.
- Never post a reply yourself; put it in `replies` and let the runtime deliver it.
</restrictions>

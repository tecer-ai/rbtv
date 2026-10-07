---
name: summarizer-cycle
description: "Run one meeting-summarizer cycle inline, in the current turn: detect new meeting transcripts, summarize each, file and publish the settled ones, apply any owner answer from the last grouped question, and ask a new grouped question only when a doubt is genuinely open. A cycle with nothing new and no open question ends with replies: [] — never a status or verification note. Use on every scheduled wake of an agent this capability is installed into."
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
This capability carries no values of its own: the installation supplies them as component
configuration, never as a value typed into this skill. Resolve, ONCE per turn, before step 1:

- **Tools** — this component's commands `artifact-bindings`, `detection-cycle`, `doubt-answer`,
  `per-meeting-job`, `publish-job` and `verify-access`, installed in this agent beside this skill
  and run by name.
  If one of them is not found, report a failed cycle that names it and run nothing
  (`rbtv agent add <agent> office/meeting-summarizer#<name>` installs it).
- **Installation root** — the nearest folder, starting at `<agent-home>` (`$RBTV_AGENT_HOME` inside
  a turn) and walking up, that holds `.rbtv/config/install.json`. Call this `<installation>` below.
  If `$RBTV_AGENT_HOME` is unset or no folder above it holds that file, report a failed cycle that
  names what is missing and run nothing.
- **Config root** — `<installation>/.rbtv/config/meeting-summarizer/`; call this `<config>` below.
  It holds one file per subject, which the tools read directly: `sources.json`,
  `destination-routing.json`, `destination-repos.json`, `publish-targets.json`, `runtime.json` and
  `summarize.json`. An owner edit to one of them takes effect on the next cycle. Every tool call
  below passes `--config-root`/`--config-dir <config>` explicitly; never rely on a tool's own
  default. If the folder is absent, report a failed cycle that names it and run nothing.
- **State directory** — `<agent-home>/state/`, the agent's live data (starts empty on a new agent,
  nothing migrates from a prior instance). `doubts.jsonl`, `outcomes.jsonl`,
  `resolved-doubts.jsonl`, `asked-doubts.jsonl`, `processed-transcripts.jsonl`,
  `asked-routing.jsonl`, `resolved-routing.jsonl` all live directly under it — call this `<state>`
  below. The last two are this skill's own plain JSONL files (one line per row, appended with your
  own file tools — no CLI owns them) tracking which meetings have an open routing question and which
  are settled; they do not exist until the first routing question.
- **Runtime folder** — `<installation>/.rbtv/runtime/meeting-summarizer/`, the tools' own records.
  `detection-cycle` keeps its `stores/` there (the poll watermark, the detected meetings, the job
  attempts, the in-flight claims); `verify-access` writes its four outputs there, and
  `detection-cycle` reads `verified-source-map.json` from it. The tools find this folder from
  `<config>` and create it on first use: pass no flag for it and never write in it by hand.
  `detection-cycle` finds `<state>/processed-transcripts.jsonl` — the SAME file `publish-job` writes
  to — from `$RBTV_AGENT_HOME`, and refuses when that variable is unset.
- **Channel directory** (the per-meeting routing-ask bookkeeping `per-meeting-job` uses; nothing
  chat-specific) — `<state>/channel`.
- **Checkout root** (where destination repos are cloned) — read `<config>/runtime.json` →
  `checkout-root`. Call this `<checkout root>` below.
- **Scratch** — a fresh working directory for this cycle's own job files, artifact downloads and
  per-meeting work folders: `<agent-home>/tmp/<a timestamp you pick>/`. Call this `<scratch>` below;
  it is yours to create and never shared with another cycle.

1. **Apply any owner answer first.** Read this conversation's recent history for the owner's reply
   to the LAST grouped question you asked (if any is still open). There are two kinds of open
   question, checked and applied independently:

   a. **Glossary-term doubts** — check `doubt-answer list-open` below; a term it no longer lists
      is already resolved or was never asked, so there is nothing to apply. Match each answered term
      in the owner's reply to its open doubt by name — this is your own reading, not a lookup table,
      because there is one conversation and no per-meeting thread to key on. For each term the owner
      answered, run:
      `doubt-answer apply --meeting-key <K> --term <T> --answer-text "<owner's exact words for that term>" --config-root <config> --checkout-root <checkout root> --state <state>`
      Read the JSON result. `"landed": true` means the summary was corrected, committed and pushed —
      report it plainly. `"landed": false` means it is still open; report why and leave it — a failed
      apply is never silently retried by guessing, and it stays open for the NEXT cycle to try again.

   b. **Routing questions** — read `<state>/asked-routing.jsonl` for a meeting-key with no matching
      row in `<state>/resolved-routing.jsonl`. For each one still open, read `<config>/destination-routing.json`'s
      routes and match the owner's reply against a declared route `entity` name (your own reading —
      the owner may name it loosely; match it to the one route it clearly means, or treat the reply
      as not yet a clear answer and leave the question open). On a clear match:
      1. Append one line to `<state>/outcomes.jsonl`: `{"meeting-key": "<K>", "outcome": "amended", "content-entity": "<the matched entity>", "at": "<now, UTC ISO>"}` — this is the same shape
         `per-meeting-job`'s own settlement rows carry; `publish-job` reads the LATEST row per
         meeting-key, so this one now wins.
      2. Retry publishing that meeting immediately, in this same turn: run `publish-job precheck`
         then (if it no longer refuses) `cycle`, exactly as step 5 describes, using the SAME job file
         from `<scratch>/jobs/<meeting-key>.json` if this cycle already wrote one for it, otherwise
         reconstruct it from `detection-cycle status --config-dir <config>`.
      3. On success, append `{"meeting-key": "<K>", "resolved-at": "<now>"}` to
         `<state>/resolved-routing.jsonl`. On failure, report why and leave both files as they are —
         the question stays open and the same retry is attempted again next cycle once you re-read
         the (still-present) owner reply from history.
      A reply that names no recognizable entity is NOT applied and NOT marked resolved; say so
      plainly in this turn's reply and re-ask the SAME routing question in step 7's grouped message
      (a clarification, not a second question).

2. **Run one detection tick:**
   `detection-cycle tick --config-dir <config>`
   Read the JSON result whole. A tick that refuses (REFUSED on stderr, empty stdout) is reported as
   a failed cycle — never re-run a refused tick; that is how one poll becomes two. From the result,
   keep every job whose disposition is NOT `already-done` and that is not in `skipped-parked` — that
   is this cycle's pending set. Report, by count (zero included): admitted meetings, meetings not
   admitted (parked, below-floor, already processed, awaiting-transcript), and the watermark before
   and after.

3. **Stage this cycle's artifacts, once, for the whole pending set** (skip if pending is empty):
   `artifact-bindings --jobs <pending-jobs.json> --out-dir <scratch>/artifacts --config-dir <config>`
   where `<pending-jobs.json>` is the pending job list you just wrote to a scratch file. This
   downloads every Drive reference once and writes `bindings.json` in `<scratch>/artifacts/`.

4. **For every pending job, run one per-meeting job** (each is independent; running them serially
   in this turn is correct — do not background any of them):
   - Write the job's JSON to `<scratch>/jobs/<meeting-key>.json`.
   - Create its work directory `<scratch>/work/<meeting-key>/` and write a `CLAUDE.md` there
     carrying a `## Name Glossary` section naming `.user/docs/glossary.md`.
   - Run:
     `per-meeting-job --job <scratch>/jobs/<meeting-key>.json --artifacts <scratch>/artifacts/bindings.json --config-root <config> --checkout-root <checkout root> --channel <state>/channel --state <state> --work <scratch>/work/<meeting-key>`
   - This call itself launches a separate, unattended `cast` turn that reads the transcript and
     writes the actual summary in the summarizer skill's own format — you do not read the
     transcript yourself and you do not draft any part of the summary. Read the JSON verdict this
     command prints: the action it took, the outcome, and whether a doubts handoff row landed.
   - A job whose disposition is `amend` is a meeting whose summary is already filed and for which
     a further source has arrived since. Run it exactly the same way: the call has the filed
     summary written again, whole, at its own path. Its verdict then carries
     `"awaiting-publication": true`, on the run that writes it (`action: summarized`, `outcome:
     amended`) and on every later run (`action: already-settled`) until step 5 has filed it; the
     call never has the same amendment written twice.
   - A verdict `action: left-alone` means the filed summary of that meeting is no longer at the
     path it was filed at: a person moved or renamed it. By owner ruling it is left as it is. The
     call wrote no summary and parked the meeting (`"parked": true`): later ticks list it under
     `skipped-parked`, so it is outside the pending set until the park is lifted as the next item
     says. This is not a failure and not a refusal: never report it as one, never search for the
     file, never edit the summary or any record yourself, and never run step 5 for that meeting.
     Its only consequence is in step 7, and only when the verdict carries `"first-report": true`.
   - A verdict `outcome: failed` that carries `"parked": true` means this meeting's job failed in
     three consecutive cycles and the call parked the meeting: later ticks list it under
     `skipped-parked` and no job runs for it. A park is lifted only when the owner asks for it, by
     `detection-cycle retry --meeting-key <K> --config-dir <config>`.

5. **File every settled meeting.** Two kinds of meeting are due: (a) each meeting whose outcome is
   `filed` or `amended` in `outcomes.jsonl` and that carries no row yet in
   `processed-transcripts.jsonl`; (b) each meeting whose per-meeting job in step 4 answered
   `"awaiting-publication": true` — an amendment: that meeting HAS rows in
   `processed-transcripts.jsonl`, from its first filing, and they do not cover the source that
   arrived since. A meeting with rows there whose verdict does NOT carry that field is not due:
   never run `cycle` for it. For each due meeting, run:
   `publish-job precheck --job <scratch>/jobs/<meeting-key>.json --config-root <config> --checkout-root <checkout root> --state <state>`
   then, only if the precheck does not refuse:
   `publish-job cycle --job <scratch>/jobs/<meeting-key>.json --summary <the summary file the verdict named> --config-root <config> --checkout-root <checkout root> --state <state>`
   Read each result. This commits and pushes inside this call — never a separate step, never
   deferred to a later turn.

   **A precheck that comes back `disposition: unroutable`** is NOT a refusal to report-and-move-on
   from (never `disposition: continue` for this) — it is an open routing question. If
   `<state>/asked-routing.jsonl` carries no row for this meeting-key yet, append
   `{"meeting-key": "<K>", "title": "<the meeting's title, for the question>", "asked-at": "<now>"}`
   and include it in step 7's grouped question. If it is already there, leave it — it is already
   asked and step 1 already checked this turn for an answer; do not run `cycle` for it and do not
   report it again as a fresh find (step 7 asks it again only when 24 hours have passed since it
   was last asked).

   **A `cycle` that REFUSES (`publish_job: summary: cannot read --summary ...`, exit `EXIT_REFUSED`)**
   means the summary path a verdict named is stale — the meeting's transcript and its content are
   still there, only the path a prior pass reported no longer resolves (the destination folder moved,
   or this scratch dir's own job file is older than you think). This is NEVER "the file was deleted":
   do not ask the owner about it, and do not touch `resolved-doubts.jsonl`/settlement rows on this
   premise. Re-run `per-meeting-job` for that meeting fresh (same as step 4) to get a CURRENT
   `summary-file` value, then retry `precheck`/`cycle` with it, in this same turn if time allows. If
   the refusal recurs, leave the meeting for the next cycle — report the refusal plainly, do not
   invent a reason for it.

6. **Check for open questions — both kinds.**
   - Glossary doubts: `doubt-answer list-open --state <state>`. For every doubt
     this prints that this cycle's own pending set produced (a fresh doubt from step 4), mark it
     asked once you include it in your question: `doubt-answer mark-asked --meeting-key <K> --term <T> --state <state>`.
     A doubt already asked in an earlier cycle and still unanswered is NOT re-asked — `list-open`
     already excludes it.
   - Routing questions: read `<state>/asked-routing.jsonl` minus `<state>/resolved-routing.jsonl` —
     every remaining meeting-key is an open routing question (step 5 already appended the fresh ones
     and step 1 already tried to resolve them from this turn's history). Step 7 asks an
     already-asked one again only when 24 hours have passed since it was last asked.

7. **Compose the report.** ONE grouped reply, in the SAME conversation this wake arrived on — never
   open a new thread for it (`ignite post` is for a proactive check that belongs to NO existing
   conversation; a scheduled wake of an already-created agent always continues its own conversation).
   - Nothing filed, nothing applied, nothing newly open: `replies: []`, `disposition: completed`.
     A quiet cycle is a correct cycle — never manufacture a status update.
   - Something filed or amended and/or an answer was applied, with no doubt or routing question
     due to be asked: report it plainly (load the `slack-message-format` skill first), `disposition:
     completed`. A summary amended because a further source arrived is reported as such: the
     meeting, and that its filed summary was written again from every source.
   - A `left-alone` verdict that carries `"first-report": true` is told to the owner ONCE, in this
     cycle's report, with nothing asked: the meeting, the path its summary was filed at, that a
     further source arrived, and that the summary was not changed because it is no longer at that
     path. A `left-alone` verdict without that field was already told: it is silence, it is not
     "something filed", and by itself it leaves the cycle a quiet one (`replies: []`,
     `disposition: completed`).
   - A doubt OR a routing question is due to be asked (whether or not something also filed this
     cycle): report what filed, THEN ask every due item in the SAME grouped message — each doubt
     (term, guess, meeting) and each routing question (meeting title, the declared entity choices
     from `destination-routing.json`) — `disposition: waiting_owner`. Do not end the turn on
     `waiting_owner` while a background command is still running; everything above must already be
     finished. A doubt is due when step 6 listed it. An open routing question is due in three
     cases: step 5 appended its row this cycle; step 1b asks for its clarification; or
     24 hours have passed since the newest `asked-at` among its rows in
     `<state>/asked-routing.jsonl`. When you ask one again in the third case, append a new row for
     it to that file, `{"meeting-key": "<K>", "title": "<title>", "asked-at": "<now>"}`: that row
     is when it was last asked. An open routing question that is not due is neither asked nor
     mentioned, and by itself it leaves the cycle a quiet one (`replies: []`, `disposition:
     completed`).
   - A stage refused for a reason that is NOT an open question (detection, a per-meeting job, a
     publish precheck/cycle failing for any reason other than `unroutable`): report the refusal
     plainly, do not retry it yourself, `disposition: continue` with `nextStep` naming the next
     scheduled wake as the retry point — unless the refusal means the whole cycle cannot proceed, in
     which case report it and still end the turn (never hold the turn open waiting for a fix).
     A failed per-meeting job whose verdict carries `"parked": true` (step 4) has no retry point:
     report the failure, that the meeting is now parked after three failed cycles, and that it
     stays parked until the owner asks for a retry; later cycles say nothing more about it.
     `unroutable` is never reported this way — it is step 5/6's open routing question, and it drives
     `disposition: waiting_owner` in the cycle that asks it, never `continue`.
</procedure>

<resources>
- `detection-cycle` (`detection_cycle.py`) — `tick` polls every watched account and source once,
  settles meeting identity, advances the one whole-poll watermark, and emits this cycle's pending
  jobs; `status`/`retry`/`schedule`/`keys` read back state without polling.
- `artifact-bindings` (`artifact_bindings.py`) — downloads every Drive reference the pending job set
  names, once, into a shared `bindings.json`.
- `per-meeting-job` (`per_meeting_job.py`) — runs ONE meeting through the summarizer skill (via its
  own nested, unattended `cast` call) and records the settlement and any doubt. For an `amend` job
  it has the filed summary written again at its own path, and says when that waits for filing; a
  filed summary that is no longer at its path it leaves alone, parks, and says so once. It records
  each run's outcome where `detection-cycle` reads it, and parks a meeting on its third
  consecutive failed cycle.
- `publish-job` (`publish_job.py`) — `precheck` then `cycle` files, commits and pushes one settled
  meeting. Reads the latest `content-entity` row in `outcomes.jsonl` per meeting — a routing answer
  you settle there (step 1b) is what a retried `precheck` resolves against.
- `doubt-answer` (`doubt_answer.py`) — this agent's own glossary-doubt ledger: `list-open`,
  `mark-asked`, `apply`. Talks to no chat surface — that is your `replies`/`ignite post`.
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
- Read: `<config>/*.json`, `<state>` and
  its `channel` subfolder, and every summary/transcript file the tools above name.
- Run: `detection-cycle`, `artifact-bindings`,
  `per-meeting-job`, `publish-job`, `doubt-answer`, and `verify-access` when a tick refuses at the
  account boundary.
- Write: `<scratch>`, and `<state>/asked-routing.jsonl` / `<state>/resolved-routing.jsonl` / the one
  synthetic settlement line you append to `<state>/outcomes.jsonl` for a resolved routing answer
  (step 1b) — every other write (doubt/outcome rows a tool produces itself, filed summaries, git
  commits/pushes) is a tool's own, never done by hand.
</permissions>

<restrictions>
- Never invent a destination, a summarizer skill, or an account — a tool's refusal is reported, not
  worked around. The one exception is a routing answer the owner has actually given (step 1b) —
  that is the owner naming it, not you inventing it.
- Never re-run a refused detection tick, and never move its watermark by hand.
- Never draft or edit summary text yourself — `per-meeting-job`'s nested agent call and
  `doubt-answer apply`'s amendment call are the only writers of a summary file.
- Never ask a doubt `list-open` does not currently list, and never ask the same term twice.
- Never report an `unroutable` precheck as a plain refusal with `disposition: continue` — it is an
  open routing question (steps 5-7), and it drives `waiting_owner`.
- Never mark a routing question resolved (`resolved-routing.jsonl`) on a reply that names no
  declared entity — leave it open and ask again as a clarification of the SAME question.
- Never end the turn with a command still running in the background — a turn is one shot.
- Never post a reply yourself; put it in `replies` and let the runtime deliver it.
- A detection tick that fails with `ACCESS_TOKEN_SCOPE_INSUFFICIENT` means the Google token has no
  Meet or Drive scope. Widening scope is the owner's call, never this cycle's. Do not report "no new
  meetings" for that refusal.
- Tactiq has no CLI. Detection reads Tactiq transcripts from its Drive auto-save folder, not an MCP
  server. A harness with no Drive access cannot see Tactiq content and must say so rather than
  reporting no new meetings.
</restrictions>

---
id: summarizer-cycle
description: "Run one meeting-summarizer cycle inline, in the current turn: detect new meeting transcripts, summarize each, file and publish the settled ones, apply any owner answer from the last grouped question, and ask a new grouped question only when a doubt is genuinely open. Use on every scheduled wake of the meeting-summarizer agent — never in a chat reply to an unrelated request."
exposes:
  path: [detection-cycle, artifact-bindings, per-meeting-job, publish-job, doubt-answer, verify-access]
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
</role>

<procedure>
This capability carries no settings of its own — an agent installing it supplies a settings file
and a state folder, never a value typed into this skill (owner ruling 2026-09-28, "Agent settings
vs capabilities"). Resolve, ONCE per turn, before step 1:

- **Tools directory** — this capability's own `tools/` folder. Find it by reading `rbtv_path` from
  the workspace's `rbtv.json` (at the workspace root) and joining `office/meeting-summarizer/tools`.
  Call this `<tools>` below.
- **Config root** — `<agent-home>/config/` (`<agent-home>` is `$IGNITE_AGENT_HOME` inside a turn).
  Every tool call below passes `--config-root`/`--config-dir <agent-home>/config` explicitly; never
  rely on a tool's own default. **First-ever cycle only** (the folder does not exist yet): read
  `<agent-home>/settings.json` (the agent's own settings — standing instructions already tell you to
  read it) and write each of its top-level keys to its own file under `<agent-home>/config/` — key
  `sources` → `config/sources.json`, `destination-routing` → `config/destination-routing.json`, and
  likewise for `destination-repos`, `publish-targets`, `runtime`, `summarize`. This is the shape
  every tool below already reads; do it once, then skip it on every later cycle.
- **State directory** — `<agent-home>/state/` (starts empty on a new agent; nothing migrates from a
  prior instance). `doubts.jsonl`, `outcomes.jsonl`, `resolved-doubts.jsonl`, `asked-doubts.jsonl`,
  `processed-transcripts.jsonl` all live directly under it — call this `<state>` below.
- **Channel directory** (the per-meeting routing-ask bookkeeping `per_meeting_job.py` uses; nothing
  chat-specific) — `<state>/channel`.
- **Checkout root** (where destination repos are cloned) — read `<agent-home>/config/runtime.json` →
  `checkout-root` once config root is materialized. Call this `<checkout root>` below.
- **Scratch** — a fresh working directory for this cycle's own job files, artifact downloads and
  per-meeting work folders: `<agent-home>/tmp/<a timestamp you pick>/`. Call this `<scratch>` below;
  it is yours to create and never shared with another cycle.

1. **Apply any owner answer first.** Read this conversation's recent history for the owner's reply
   to the LAST grouped question you asked (if any is still open — check `doubt_answer.py list-open`
   below; a term it no longer lists is already resolved or was never asked, so there is nothing to
   apply). Match each answered term in the owner's reply to its open doubt by name — this is your
   own reading, not a lookup table, because there is one conversation and no per-meeting thread to
   key on. For each term the owner answered, run:
   `python3 <tools>/doubt_answer.py apply --meeting-key <K> --term <T> --answer-text "<owner's exact words for that term>" --config-root <agent-home>/config --checkout-root <checkout root> --state <state>`
   Read the JSON result. `"landed": true` means the summary was corrected, committed and pushed —
   report it plainly. `"landed": false` means it is still open; report why and leave it — a failed
   apply is never silently retried by guessing, and it stays open for the NEXT cycle to try again
   (the same owner answer, read again from history) or for you to escalate if it fails repeatedly.

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

6. **Check for open doubts:**
   `python3 <tools>/doubt_answer.py list-open --state <state>`
   For every doubt this prints that this cycle's own pending set produced (a fresh doubt from step
   4), mark it asked once you include it in your question:
   `python3 <tools>/doubt_answer.py mark-asked --meeting-key <K> --term <T> --state <state>`
   A doubt already asked in an earlier cycle and still unanswered is NOT re-asked — `list-open`
   already excludes it; do not ask it again by any other means.

7. **Compose the report.**
   - Nothing filed, nothing to apply, nothing newly open: `replies: []`, `disposition: completed`.
     A quiet cycle is a correct cycle — never manufacture a status update.
   - Something filed and/or an answer was applied, with no new open doubt: report it plainly in ONE
     grouped reply (load the `slack-message-format` skill first), `disposition: completed`.
   - A new doubt is open (whether or not something also filed this cycle): report what filed, THEN
     ask every open doubt in the SAME grouped message (one message, every term, its guess, which
     meeting) — `disposition: waiting_owner`. Do not end the turn on `waiting_owner` while a
     background command is still running; everything above must already be finished.
   - A stage refused (detection, a per-meeting job, a publish precheck/cycle): report the refusal
     plainly, do not retry it yourself, `disposition: continue` with `nextStep` naming the next
     scheduled wake as the retry point — unless the refusal means the whole cycle cannot proceed, in
     which case report it and still end the turn (never hold the turn open waiting for a fix).
</procedure>

<resources>
- `detection-cycle` (`detection_cycle.py`) — `tick` polls every watched account and source once,
  settles meeting identity, advances the one whole-poll watermark, and emits this cycle's pending
  jobs; `status`/`retry`/`schedule`/`keys` read back state without polling.
- `artifact-bindings` (`artifact_bindings.py`) — downloads every Drive reference the pending job set
  names, once, into a shared `bindings.json`.
- `per-meeting-job` (`per_meeting_job.py`) — runs ONE meeting through the summarizer skill (via its
  own nested, unattended `cast` call) and records the settlement and any doubt.
- `publish-job` (`publish_job.py`) — `precheck` then `cycle` files, commits and pushes one settled
  meeting's summary and transcripts.
- `doubt-answer` (`doubt_answer.py`) — this agent's own doubt ledger: `list-open`, `mark-asked`,
  `apply`. It replaces the old `channel_runtime.py`'s Slack-bound ask/apply cycle; nothing here talks
  to a chat surface — that is your own `replies` and `ignite-agent post`.
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
deliberately not admitted; every settled owner answer is applied to its one summary and committed;
every doubt still open is asked exactly once and never silently dropped.

## Outputs
- Schema: this turn's `replies` (plain text, phone-first, grouped) and, on disk, the same
  `outcomes.jsonl` / `doubts.jsonl` / `processed-transcripts.jsonl` / `resolved-doubts.jsonl` /
  `asked-doubts.jsonl` rows the tools above write directly — you write nothing to those files by
  hand.
</io-spec>

<permissions>
- Read: this agent's `settings.json`, its materialized `<agent-home>/config/*.json`, `<state>` and
  its `channel` subfolder, and every summary/transcript file the tools above name.
- Run: `detection-cycle`, `artifact-bindings`, `per-meeting-job`, `publish-job`, `doubt-answer`, and
  `verify-access` when a tick refuses at the account boundary.
- Write: only `<agent-home>/config/*.json` (the one-time materialization) and `<scratch>` — every
  other write (state rows, filed summaries, git commits/pushes) is a tool's own, never done by hand.
</permissions>

<restrictions>
- Never invent a destination, a summarizer skill, or an account — a tool's refusal is reported, not
  worked around.
- Never re-run a refused detection tick, and never move its watermark by hand.
- Never draft or edit summary text yourself — `per_meeting_job.py`'s nested agent call and
  `doubt_answer.py apply`'s amendment call are the only writers of a summary file.
- Never ask a doubt `list-open` does not currently list, and never ask the same term twice.
- Never end the turn with a command still running in the background — a turn is one shot.
- Never post a reply yourself; put it in `replies` and let the runtime deliver it.
</restrictions>

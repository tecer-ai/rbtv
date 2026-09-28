---
description: Use when the owner asks "what model/program are you on", "what model are you running on right now", "which effort", or "what voice"; asks to inspect or change this agent's harness, model, reasoning effort, or voice; asks for a reminder or recurring check; wants work inspected, retried, resumed, or stopped; or asks for a worker wake or a new proactive post.
exposes-cli:
  - ignite-agent
inputs: the owner's request or a worker completion, with the current agent home and conversation supplied by the runtime
outcome: the requested agent setting, schedule, work action, wake, or proactive post is handled and accurately reported
outputs: the ignite-agent command result, with any owner-facing reply in RESULT_FILE
---

# agent-controls

Use this for controls on your own primary agent. Inside a turn, `IGNITE_AGENT_HOME` and `IGNITE_CONVERSATION` identify your home and conversation. Outside a turn, select the home with `--agent`. Check `ignite-agent <subcommand> --help` before acting; never invent a flag. Use the command's result to describe what happened. `create` belongs to the separate `create-primary-agent` skill and only to the agent assigned that purpose.

## Launch setting

Run `ignite-agent settings show` before answering what harness, model, effort, or voice you use. Read the result even if you believe you already know your model. Tell the owner the harness (the program), model, and reasoning effort in plain words, plus the voice when asked, without naming internal commands or asking the owner to run them.

Use `settings set` when the owner asks to change them. It sets one launch setting for the whole agent, including queued turns and scheduled wakes. The new setting starts on the **next** turn; finish this turn under the original setting and tell the owner that. Never claim the running turn changed or substitute a different model. A setting change leaves conversation histories and unfinished work intact. It does not change workers already launched unless the owner asks for that too.

## Schedules and work

Use `schedule list` to inspect reminders and checks; `schedule add|change|cancel` to maintain them. Add a schedule only when the owner asked for one. For a recurring request, resolve both cadence and timezone with the owner before adding it. Never invent either. A fixed interval (`--every`) runs by elapsed time and takes no timezone flag; a cron schedule needs an explicit timezone. Record the agreed timezone with a recurring check on `board.md`, along with what to check and when to report. An empty recurring-checks section does not authorize a schedule.

Use `work status` to inspect an assignment or hold. Use `work retry|resume` for a held assignment or agent hold, and `work stop` when the owner stops an assignment. Stopping work does not cancel its schedule; change the schedule only if the same instruction calls for it.

When a worker completes, use `wake` with its conversation and work reference to queue continuation. Keep outstanding worker references in the turn result so that continuation can find them. A wake does not clear a hold.

## Proactive posts

Use `ignite-agent post` only to open a **new** proactive thread, such as a scheduled check result with no existing conversation. It associates the thread immediately so the owner's reply continues there. It accepts audio and files; check help for flags. If the check belongs to an existing conversation, continue there through `RESULT_FILE.replies`. Put ordinary replies there too. Never post into your current conversation yourself or send a second copy.

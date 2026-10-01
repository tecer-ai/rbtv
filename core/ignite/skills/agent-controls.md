---
name: agent-controls
description: "Use when the owner asks to change or inspect this agent's harness, model, effort, or voice; manage reminders or recurring checks; inspect, retry, resume, or stop work; wake after workers; or open a new proactive thread."
---

# agent-controls

Use this for controls on your own agent. Inside a turn, `IGNITE_AGENT_HOME` and `IGNITE_CONVERSATION` identify your home and conversation. Outside a turn, select the home with `--agent`. Check `ignite-agent <subcommand> --help` before acting; never invent a flag. Use the command's result to describe what happened. `install` and `connect` belong to the separate `create-agent` skill and only to the agent assigned that purpose.

## Launch setting

Run `ignite-agent settings show` before answering what harness, model, effort, or voice you use. Read the result even if you believe you already know your model. Tell the owner the harness (the program), model, and reasoning effort in plain words, plus the voice when asked, without naming internal commands or asking the owner to run them.

Use `settings set` when the owner asks to change them. It sets one launch setting for the whole agent, including queued turns and scheduled wakes. The new setting starts on the **next** turn; finish this turn under the original setting and tell the owner that. Never claim the running turn changed or substitute a different model. A setting change leaves conversation histories and unfinished work intact. It does not change workers already launched unless the owner asks for that too.

## Schedules and work

Use `schedule list` to inspect reminders and checks; `schedule add|change|cancel` to maintain them. Add a schedule only when the owner asked for one. For a recurring request, resolve both cadence and timezone with the owner before adding it. Never invent either. A fixed interval (`--every`) runs by elapsed time and takes no timezone flag; a cron schedule needs an explicit timezone. Record the agreed timezone with a recurring check on `board.md`, along with what to check and when to report. An empty recurring-checks section does not authorize a schedule.

Use `work status` to inspect an assignment or hold. Use `work retry|resume` for a held assignment or agent hold, and `work stop` when the owner stops an assignment. Stopping work does not cancel its schedule; change the schedule only if the same instruction calls for it.

When a worker completes, use `wake` with its conversation and work reference to queue continuation. Keep outstanding worker references in the turn result so that continuation can find them. A wake does not clear a hold.

## Board and memory

Use `ignite-agent board write --file <path>` to update your board's subjects or Watch-outs. Supply the complete candidate board; the checked command preserves Timers, Recently closed, and existing Flags, and refuses an invalid or over-cap write. Use `ignite-agent board close <subject> <outcome> [thread]` when a subject is done; it removes that subject and writes its outcome in Recently closed. Never edit the board file directly.

When the owner corrects your behaviour, record the correction in the board's Watch-outs in the same turn. Do not write `memory/learned.md`: the dreamer folds Watch-outs into learned rules on its next run. When the owner asks to remember a fact, use `ignite-agent remember <text>` instead. It appends one line to shared `.rbtv/memory/inbox.md` and does not rewrite earlier memory.

## Proactive posts

Use `ignite-agent post --thread <thread>` from a scheduled wake to continue the subject in that existing thread. It accepts the stored full conversation key or a unique root timestamp and joins that thread's history. Without `--thread`, use `ignite-agent post` only to open a **new** proactive thread, such as a scheduled check result for a new subject. It associates the thread immediately so the owner's reply continues there. It accepts audio and files; check help for flags. If the check belongs to the current conversation, continue there through `RESULT_FILE.replies`. Put ordinary replies there too. Never post into your current conversation yourself or send a second copy.

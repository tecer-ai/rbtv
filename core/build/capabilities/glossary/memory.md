# Memory

Two homes. The runtime supplies both. The agent does not discover them.

**General memory** is one folder per installation, `.rbtv/memory/`, seen by every agent. It holds thin facts and pointers. The content's own home stays canonical and is not copied. There is no location setting and no per-agent grant.

**Agent memory** is that agent's [learned rules](learned-rules.md) and [topic files](agent-topic.md), in the agent folder. Learned rules are how this agent must behave. Topic files hold on-demand detail. Facts about the owner are general memory, not agent memory.

## Always loaded

Every turn, including a scheduled wake, injects the [profile](profile.md), that agent's learned rules, that agent's [board](board.md), the general-memory [index](memory-index.md), and the [inbox](inbox.md). [Workspace memory](workspace-memory.md) is injected only when the working directory is under its declared paths.

Read on demand: topic files, [knowledge](knowledge.md), [entities](entity.md), [workstreams](workstreams.md), and the [daily](timeline-daily.md) and [weekly](timeline-weekly.md) timeline. Nested generated indexes are read on demand. The root index is not: it is injected.

## Who writes

The [dreamer](dreamer.md) alone writes long-term memory: general memory, learned rules, and topic files. An agent appends an explicit "remember X" about the owner to the inbox, and maintains its board, including a watch-out for a correction of its behaviour. The agent on a turn never writes learned rules.

A missing or invalid injected file — invalid meaning it fails the check — is saved aside, the last good version in git is loaded, and the owner is alerted. The turn is not blocked. Only a fact with an explicit end, `until <date>`, expires.

General memory's folders are `entities/` (`people/`, `orgs/`, `places/` for geography only, `devices/`), `knowledge/` (`facts`, `preferences`, `decisions`, `self`, `health`), `workspaces/`, `timeline/daily/`, `timeline/weekly/`, plus `profile.md`, `inbox.md`, and `workstreams.md`. `places/` is geography only. Health lines that change an agent's behaviour live in `knowledge/health.md`; the profile has no health section. There is no communications folder: conversations live in Ignite's database.

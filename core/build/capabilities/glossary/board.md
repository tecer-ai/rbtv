# Board

The short-term memory of what matters in one folder, by subject, at `_artifacts/board.md`. An agent folder, a project folder, and an area folder use the same four sections, empty when unused. Ignite injects an agent's board into every turn, including a scheduled wake.

The board points to threads. A thread does not point to the board. Ignite never adds a thread. A subject may name no thread yet. A scheduled wake names only the check that fired; the board holds the details.

## Sections and writers

- **What matters now** — one entry per subject: a title, one to three lines of state, related threads, a link to detail, and flags. The agent writes it through `ignite board write`. An over-long or over-cap entry is refused, never truncated.
- **Watch-outs** — the owner's corrections of this agent's behaviour, recorded by the agent in the same turn. The dreamer later folds each one into [learned rules](learned-rules.md) and removes it in that same run. A fact about the owner goes to the [inbox](inbox.md) instead. A correction that is both goes to both.
- **Timers** — written by Ignite from its schedule database, never copied by hand. The table is outside the line cap. A schedule without a subject renders `none`.
- **Recently closed** — written when the agent closes a subject with `ignite board close`. Lines pruned from it are archived, never deleted.

Ignite sets flags: `answered <date>` when the owner replies in a linked thread, `idle since <date>` after seven days without an owner reply. The agent does not edit flags. Nothing is closed or deleted on a timer.

The agent creates timers on the owner's request and closes one when a wake finds its goal met. The dreamer moves a subject's detail into an [agent topic](agent-topic.md) and leaves the detail link. It writes the board only if the board is unchanged since it was read; otherwise it re-reads and retries. A check runs on every board write. There is no governance agent.

Caps, refused rather than truncated: at most 90 non-empty lines outside the Timers table, 8 subjects, 6 watch-outs, and 6 closed lines. The agent's `memory/` folder and this file are tracked in git.

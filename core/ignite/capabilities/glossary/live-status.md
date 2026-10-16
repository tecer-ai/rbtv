# Live status

Live status is the state Ignite shows the owner on the latest message of each conversation's thread, so that the work of an agent the owner cannot watch stays visible while it runs. It has three layers, and at most two show at once: the system state, plus the agent state during the work or the task state after it. The agent and task states never show together.

Ignite owns the states and names no emoji. A communication connector shows them in its own medium; Slack shows them as reactions, through the mapping and order rules in `connectors/slack/capabilities/tools/slack/lib/live-status.js`. Ignite's waking service is the only place that shows them, because it alone sees every agent and so shares Slack's rate budget across them.

| Layer | State | Set by |
|---|---|---|
| system | `queued` | Ignite, when it accepts the message and no turn has started |
| system | `running` | Ignite, when the turn launches on the agent's own model |
| system | `fallback` | Ignite, when the turn runs on a fallback model |
| system | `retrying` | Ignite, after a failure that will be retried |
| system | `failed` | Ignite, after a failure that ends the work (a hold, a reply that gives up, a voice note that cannot be transcribed) |
| agent | `working` | Ignite, at the start of every turn |
| agent | `gathering`, `thinking`, `making`, `orchestrating` | The agent, with `ignite status <state>` |
| agent | `waiting` | Ignite, when a turn ends `waiting_workers`, until the next turn of that conversation starts or its work stops waiting (stopped, held) |
| task | `done` | A `completed` result, once its replies are delivered |
| task | `caveats` | A `completed` result with `"caveats": true` |
| task | `question` | A `waiting_owner` result |
| task | `stopped` | A `stopped` result |

The agent state moves: it ticks through its frames while the turn runs, and `waiting` ticks slowly between turns and across a service restart. The system and task states stay still. A turn that ends `continue` leaves the agent state `working` until the next turn runs. A failed turn removes the agent state. A scheduled wake answers no owner message and shows nothing.

The status follows the thread's latest message among those Ignite knows about: each owner message it accepts and each reply or post it delivers into the thread. When a newer one arrives, the status moves there and the message it leaves keeps only its own task: the task of the turn whose final reply it is (or, for a turn with no reply, of the latest message that turn saw), so earlier messages keep their ✅, ⚠️, ❓ or ⏹️ and most messages end with no reaction. A new owner message shows `queued` and no task, unless a turn of the conversation is running, whose state it then shows. While a later turn's agent state shows on a message that keeps a task, the task is hidden; it shows again once the status moves on. When no turn of the conversation runs and one of its owner messages waits for a turn, `running` or `fallback` gives way to `queued`. A reply that cannot be delivered moves nothing: the latest message shows `failed`. `ignite status --task <state> --message <ts>` sets the task of an earlier owner message of the same conversation whose turn has finished, on the message that keeps it; the ts of that message works as well.

In Slack, `/legend` shows any user what each reaction means, from the states and their meanings in Ignite and the emoji in the Slack connector.

The rule [live-status](../../rules/live-status.md) tells an Ignite agent when to declare its state. Ignite's [architecture](../tools/ignite/documentation/architecture.md) names the files that set and show each state.

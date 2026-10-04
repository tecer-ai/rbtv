# core/ignite

Ignite is one installation process. A Slack message or a scheduled wake selects an agent folder under the installation `.rbtv/agents/<slug>/`, runs one non-interactive turn of that agent, and delivers that turn's replies to the right Slack thread. The agent never posts into its own conversation thread.

Ignite's code: the waking program (`capabilities/tools/ignite/daemon.js`) and the `ignite` command. What each file does, and the configuration and turn contracts: `capabilities/architecture.md`. Deploying, status, and repairing a hold: `capabilities/runbook.md`.

1. **Deployed, not run from here.** The waking program runs from a deploy worktree fixed at one commit (`capabilities/tools/ignite/deploy.sh <commit>`, systemd unit `rbtv-ignite-agents.service`), so a change here reaches the live agents only after a deploy of a commit that contains it.
2. **Self-contained except turn.** `capabilities/tools/ignite/turn.js` directly imports Cast's shared launch files; this is the written exception. Other Cast, stools, and audio use is through commands named in `.rbtv/config/ignite/config.json`.

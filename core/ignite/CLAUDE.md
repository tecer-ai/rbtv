# core/ignite

Ignite is one workspace process. A Slack message or a scheduled wake selects an agent folder under the workspace `.rbtv/agents/<slug>/`, runs one non-interactive turn of that agent, and delivers that turn's replies to the right Slack thread. The agent never posts into its own conversation thread.

Ignite's code: the waking program (`capabilities/tools/ignite-agent/daemon.js`) and the `ignite-agent` command. What each file does, and the configuration and turn contracts: `capabilities/architecture.md`. Deploying, status, and repairing a hold: `capabilities/runbook.md`.

1. **Deployed, not run from here.** The waking program runs from a deploy worktree fixed at one commit (`capabilities/tools/ignite-agent/deploy.sh <commit>`, systemd unit `rbtv-ignite-agents.service`), so a change here reaches the live agents only after a deploy of a commit that contains it.
2. **Self-contained.** `capabilities/tools/ignite-agent/` requires only its own files and Node built-ins. `cast`, `stools`, and the audio tool are commands named in `.rbtv/config/ignite/config.json`, never source imports.

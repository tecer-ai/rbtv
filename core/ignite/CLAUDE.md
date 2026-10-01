# core/ignite

Ignite's code: the waking program (`capabilities/tools/ignite-agent/daemon.js`) and the `ignite-agent` command. What each file does, and the configuration and turn contracts: `capabilities/component.md`. Deploying, status, and repairing a hold: `capabilities/runbook.md`.

1. **Deployed, not run from here.** The waking program runs from a deploy worktree fixed at one commit (`capabilities/tools/ignite-agent/deploy.sh <commit>`, systemd unit `rbtv-ignite-agents.service`), so a change here reaches the live agents only after a deploy of a commit that contains it.
2. **Self-contained.** `capabilities/tools/ignite-agent/` requires only its own files and Node built-ins. `cast`, `stools`, and the audio tool are commands named in `.rbtv/config/ignite/config.json`, never source imports.

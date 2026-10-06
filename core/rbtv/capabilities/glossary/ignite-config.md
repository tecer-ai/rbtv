# `ignite/config.json`

Ignite's configuration on one machine: `.rbtv/config/ignite/config.json`. It holds the Slack workspace identity, which Slack channel connects to which [Ignite agent](agent.md#ignite-agent), the agent that receives direct messages, and the commands Ignite runs. It belongs to the machine where the agents run and is not shared with other machines. It names the environment variables that hold Slack's tokens, never the tokens themselves. CLIs read it; agents do not.

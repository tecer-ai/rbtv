# `launch.json`

The file in an installed [agent](agent.md#installed-agent)'s folder that holds its live harness, model, and effort, and optionally the voice an [Ignite agent](agent.md#ignite-agent) replies with. It is written when the agent is installed, since whoever installs the agent must choose these values, and it can be changed later, including from a Slack conversation. Programs read it; agents do not. Everything that runs the agent from its folder, such as Ignite's waking program and `rbtv spark`, reads the values here at that moment.

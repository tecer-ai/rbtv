# `config/`

The `.rbtv/config/` folder for all user-specific configuration that rbtv and its modules and components need to run in this installation, including the installation root's record, [`install.json`](install-json.md). A component keeps its configuration in a folder named after it, such as [`config/ignite/`](ignite-config.md). An rbtv agent's own record and settings stay in its [agent folder](agent.md#rbtv-agent), and local components stay in [`mirror/`](mirror.md). A configuration file names the environment variable that holds a secret, such as a token, never the secret itself.

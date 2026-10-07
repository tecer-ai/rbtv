# `config/`

`.rbtv/config/` holds one installation’s settings. A component keeps what the user chose or supplied (settings, choices, credentials and keys) in one folder named exactly as the component, `.rbtv/config/<component>/`: `.rbtv/config/ignite/` holds [Ignite configuration](../../../ignite/capabilities/glossary/ignite-config.md), `.rbtv/config/cast/` holds cast’s selected models and its defaults, and `.rbtv/config/rbtv/providers/` holds rbtv’s [saved provider logins](../tools/rbtv/documentation/providers.md). Every tool of the component writes in that folder and names its files by purpose. The folder carries the component’s name without its module, so rbtv refuses two components with the same name in different modules.

Two files belong to the whole installation and sit outside that pattern: the [installation record](install-json.md), `.rbtv/config/install.json`, and the [environment file](environment-file.md), `.rbtv/config/env/.env`.

Put component settings here when they belong to the installation. An agent’s own [settings](settings-json.md) and record stay in its agent folder; local component source belongs in [mirror/](mirror.md), and data a program writes while running belongs in [runtime/](runtime.md).

Follow the component’s instructions to edit its configuration. Change installation selections and apply them as Installation record specifies; rbtv maintains the generated-file ownership fields. An update does not turn every file in this folder into generated data.

Configuration records name the environment variable supplying a secret instead of copying its value. The installation’s environment file is a separate value store; use that entry when a component reads values from it. A credential that must be a file, such as a saved login, stays in the component’s folder and never in a file git tracks: the program that writes it also writes a `.gitignore` in that folder, as `rbtv providers` does. A setting that every machine of the installation shares, such as cast’s selected models, is committed with the installation.

Check the setting through the component that consumes it. For installation selections, inspect the generated files and diagnostics specified by Installation record.

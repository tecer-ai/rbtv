# `config/`

`.rbtv/config/` holds one installation’s settings and its root [installation record](install-json.md). A component keeps its configuration under a folder named for that component, such as [Ignite configuration](../../../ignite/capabilities/glossary/ignite-config.md).

Put component settings here when they belong to the installation. An agent’s own [settings](settings-json.md) and record stay in its agent folder; local component source belongs in [mirror/](mirror.md), and operational data belongs in [runtime/](runtime.md).

Follow the component’s instructions to edit its configuration. Change installation selections and apply them as Installation record specifies; rbtv maintains the generated-file ownership fields. An update does not turn every file in this folder into generated data.

Configuration records name the environment variable supplying a secret instead of copying its value. The installation’s [environment file](environment-file.md) is a separate value store; use that entry when a component reads values from it.

Check the setting through the component that consumes it. For installation selections, inspect the generated files and diagnostics specified by Installation record.

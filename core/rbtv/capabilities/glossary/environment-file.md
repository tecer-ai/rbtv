# Installation environment file

`.rbtv/config/env/.env` stores environment-variable values used by software in one installation. Component [configuration](config.md) refers to those variables by name rather than copying their values into its own records.

Write only variables a configured consumer needs, using the names that consumer expects. Keep this local file out of git and keep its secret values out of prompts, reports and generated harness files. This is a value store, not component source or an agent’s job-settings record.

Use one literal assignment per line:

```text
<VARIABLE_NAME>=<value>
```

Follow the consumer’s loading rules. [Ignite configuration](../../../ignite/capabilities/glossary/ignite-config.md) uses a nonempty process-environment value first, then this file; a missing or empty required value is reported by variable name. Its file reader accepts blank lines, `#` comment lines and matching outer quotes around a value; it does not evaluate shell expressions. A file edit does not itself restart a running consumer.

Verify loading with a temporary, nonsecret variable and the consumer’s supported operation. Confirm that missing required values are reported without printing the value. Do not expose real credentials to demonstrate that loading works.

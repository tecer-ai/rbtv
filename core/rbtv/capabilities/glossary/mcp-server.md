# MCP server

An MCP server record tells rbtv how to start or reach a Model Context Protocol server, which supplies actions to an agent through its harness. The record is configuration, not an exposure method or instructions the agent reads.

Use one when the harness should offer that server's actions. Write `mcp-servers/<name>.json` in the chosen component. The name must match the filename and becomes the name under which the actions appear. Search existing components before adding it: one server name has one record.

## Connection and credentials

Follow [mcp-server.schema.json](../templates/mcp-server.schema.json) for the fields. Choose exactly one connection:

- `command`: an executable name, with each argument in `args`. The installer copies these as written. It does not interpret a shell line, resolve a component-relative path or install the executable on PATH. Use a resolvable executable or an absolute path that is valid on the target installation. Pin a package version when the tested action set is required; leave it unpinned only when any current package with that name satisfies the requirement.
- `url`: an address sufficient to reach the server. The installer drops `env` for this form on every harness. Headers are not supported in the record.

For a command that needs a secret, `env` maps each variable the server reads to the name of the variable holding its value. Use the same name on both sides, such as `"API_KEY": "API_KEY"`. Codex only forwards a variable under its own name; the installer rejects renamed variables when Codex is selected. Claude Code and OpenCode receive their respective variable-reference syntax from the installer. Do not write that harness-specific syntax yourself.

Never put a secret in the record, arguments or URL. The installer checks the form of a variable name, not whether a value is secretly a credential. A secret that happens to look like a name can pass and then be treated as a variable to look up.

When a remote server needs a credential or header the URL record cannot carry, use a local command that reads the required variable and connects to the server, or stop and report the unsupported requirement. Do not add an invented field or embed credentials in the address.

Write the description as one line telling a person choosing the server what it offers. The installer uses it in listings and search, but does not put it in the harness's server configuration. Instructions about when the agent should use the actions belong in the calling text; the running server supplies the action descriptions.

## Editing, conversion and verification

Change the source record, then regenerate the harness configuration using [rbtv CLI](rbtv-cli.md). Editing the generated configuration loses the change on regeneration. Changing the record's description alone does not change the server's advertised actions.

When converting another harness's settings, extract the executable, separate arguments or address and required variable names. Do not copy the wrapper object, type, headers, variable syntax or secrets. A copied shell line can remain wrong even after invalid fields have been removed.

Installer acceptance proves the record's shape and, on a real run, configuration generation. It does not start the server. Inspect the generated configuration for every selected harness: executable and arguments remain separate, variable references are present where needed, and no secret was copied. Then start the server on at least one harness, confirm its actions appear under the expected name and exercise one action. State which harnesses were actually tested.

## Template

Use one form. Omit unused `args` and `env`. The schema remains authoritative.

```json
{
  "name": "<filename without .json>",
  "description": "<actions the server offers>",
  "command": "<executable>",
  "args": ["<argument, never a secret>"],
  "env": {"<variable name>": "<same variable name>"}
}
```

```json
{
  "name": "<filename without .json>",
  "description": "<actions the server offers>",
  "url": "<address sufficient to connect, without credentials>"
}
```

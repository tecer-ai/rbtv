# MCP server

An MCP server is the record of one Model Context Protocol server: the command that starts it, or the address that reaches it. Outside rbtv that server is a block in one harness's settings, and the block may contain a secret, a type, or a command written as one line. In rbtv the record names the variables that have the secrets, never the secrets (the rbtv CLI checks the form of a name and does not recognize a secret), and it writes each harness's settings from that one record. An MCP server is not an exposure method¹. It is not a cognitive unit². The agent does not read the record.

The record gives the agent that server's actions on every harness the installation receives, from one record. An author wants one when the page "Choosing what to build"³ has settled that the actions come from a server the harness should list. Write an MCP server so that each of those harnesses starts the command or connects to the address, and the agent sees that server's actions under the record's name.

## How it fails

The rbtv CLI can accept an MCP server, and the server can still fail to reach the agent, because the rbtv CLI checks the record and writes the harness file. The rbtv CLI does not start the server.

- The command is a shell line, or a path that is right only beside the record. The rbtv CLI copies that string as the executable to start. The harness file names the shell line as the executable, or it names a path the rbtv CLI did not resolve, and no actions appear under the record's name.
- The record names an address and also names a variable. The rbtv CLI writes the address and does not write the variable. The harness file has the address and no secret, so the server does not receive the variable the author named.
- A secret is written in the address or in an argument. The rbtv CLI copies both as written, and the secret sits in the harness file. Or a secret is written as a variable's value: the rbtv CLI writes it as a name to look up, and the server reads the wrong value.
- The description tells the agent when to call the server. The rbtv CLI does not write the description into the harness file. The agent never reads that line, and it calls the actions the running server advertises, or it never calls them.

## What it is composed of

The author writes one file, `mcp-servers/<name>.json`, in the component that the page "Choosing where to build"⁴ names. The author does not write the harness file. The page "rbtv CLI"⁵ says which file the rbtv CLI recognizes and which schema it checks. That page also says which file the rbtv CLI writes for each harness. The schema is [mcp-server.schema.json](../templates/mcp-server.schema.json). This page does not list its fields.

The author decides the name, the description, and either a command with its arguments and its variables or an address. The rbtv CLI copies the command, the arguments and the address as written. It does not place a shortcut, and it does not resolve a path against the component folder. The page "Tool"⁶ is a different file: an executable inside the component may be named here only by a path that the harness can run as written, because nothing resolves it or places it on PATH.

## How to build it

1. **The actions that do not appear, then the purpose.** Before any field, name the failure, its cause and the situation for this server. The failure is an agent whose list of actions has nothing under this server's name, or has actions that are not the ones you meant. The cause, for an MCP server, is the record: the harness cannot start the command, cannot reach the address, or starts without the variable the server reads. The situation is an agent on each harness that should list the server, after the rbtv CLI has written that harness's file. Then write the purpose from that failure: each of those harnesses starts the command or connects to the address, and the actions under that name are the ones you meant.

   Weak: "Each harness starts a helpful docs server, and the actions appear under a helpful name."

   Strong: "Each harness starts `npx` with the argument `docs-mcp`, and the actions appear under `docs`."

   The weak line names no executable and no name in the list. The agent finds no server of that name in its list of actions, so it does the work without the server.

2. **Write an executable name and its arguments, or an address, and do not copy a harness file.** The record has a command or an address, never both. Write the command as the executable name, and write each argument beside it. The rbtv CLI copies that string as the executable to start and does not pass the string to a shell. An executable that is not on PATH is an absolute path, because the rbtv CLI does not resolve the string against the component folder. An argument that names a package with no version starts whatever that name resolves to when the harness starts the server. Pin the version when the actions must be the ones you tried. Leave the name unpinned only when any current package of that name is the server you mean. Write an address only when that address alone is what the harness needs.

   Do not copy a harness file and delete the fields the rbtv CLI refuses. Claude Code's file has a wrapper object, a type `http` on an entry with an address, and `${NAME}` where a variable's value sits. OpenCode's file has a type, a command that is a list, and `{env:NAME}`. Codex's file is not JSON, and it names variables in a list. Those shapes are not the record. After the refused fields are gone, a shell line or a secret can remain.

   Weak: "Set command to `npx -y docs-mcp`."

   Strong: "Set command to `npx` and set args to `-y` and `docs-mcp`."

   The weak line is one executable name that includes spaces. The harness looks for that executable and does not start `npx`.

3. **Name each secret as a variable, and use the same name the server reads.** In `env`, the key is the variable the server reads, and the value is the name of the variable that has the secret. Write that name, never the secret. Write the two names the same. The rbtv CLI writes Claude Code `${NAME}` and OpenCode `{env:NAME}` from the bare name. Codex forwards a variable only under its own name, so a record whose two names differ cannot reach the server on Codex, and the rbtv CLI refuses it when Codex is among the harnesses. A value that is a secret, and that still matches a variable name, is written as a name to look up when the install does not include Codex.

   Weak: "Set `API_KEY` to `sk_live_abc`."

   Strong: "Set `API_KEY` to `API_KEY`, the name of the variable that has the secret."

   The weak line stores the secret as a name to look up. The server reads a variable that was never set, and the secret is in the record.

4. **When the server needs a named secret, write a command, not an address.** A record that has an address drops `env`. The rbtv CLI writes the address and no variable, on every harness. Do not put the secret in the address or in an argument. The rbtv CLI copies both as written into each harness file. A header is not a field of the record. When the server needs a header, write a local command whose executable reads the variable, or stop: the record cannot carry the header.

   Weak: "The server needs `API_KEY`, so set url to `https://example.invalid/mcp` and set `API_KEY` to `API_KEY`. Use url only when the address alone reaches the server, with no variable and no secret in the address."

   Strong: "The server needs `API_KEY`, so set command to `npx`, set args to the package, and set `API_KEY` to `API_KEY`. Use url only when the address alone reaches the server, with no variable and no secret in the address."

   The weak line names a variable the rbtv CLI does not write for an address. The harness file has the address and no variable.

5. **Write the description for the person who chooses the server, and write the name the list will carry.** The description is one line that says what the server lets an agent do. The rbtv CLI shows that line when it lists or searches, and the harness does not show it beside the server's actions. The rbtv CLI does not write the line into the harness file. The agent sees the actions the running server advertises, under the record's name, and it does not see the description. Do not put an instruction in the description. Write the name as the file name, because that string is the name in the list of actions. The page "rbtv CLI"⁵ says the name equals the file name.

   Weak: "When the agent needs an audit, it calls this server."

   Strong: "Lighthouse audits, heap snapshots and throttling, for a person choosing the server."

   The weak line is an instruction. The agent never reads the description, so the audit is not called from that line.

6. **Give the server one record.** One name is one entry in each harness file, so search for this server's name in every component before you write the record, as the page "Single source of truth"⁷ says.

- When you edit: change the record, not the harness file. The page "rbtv CLI"⁵ says which run writes the harness file again from the record. A change to the description does not change the list of actions. A change to the command, the arguments, the address or the variables reaches the agent only after that write.
- When you convert an outside file: take the executable name, the arguments and the address. Leave the type, the wrapper, the headers, the harness variable syntax and the secret. A secret in the outside file becomes a variable name, the same as the name the server reads. A section that says when to use the server is not part of the record. The page "Choosing what to build"³ decides that section.
- When you review: read the harness file the rbtv CLI wrote, not only the record. A review that only reads the record misses a shell line, a secret, and a variable that an address record dropped.

Checks:

- A reviewer sees a command or an address, not both. The command is an executable name, and each argument is separate. Every variable's value is the same name, and it is not a secret. The address and the arguments contain no secret. An address record does not name a variable the server needs. The description says what the server lets an agent do, and it is not an instruction to the agent. The name is the file name.
- The rbtv CLI accepts the record. Acceptance shows the fields matched and, on a run that is not a dry run, that the harness file was written. A pass does not show a server that started, a secret in the server's environment, or the actions you meant in the list.
- Install the record, then read the harness file. The command is the executable name, or the address is the one you wrote, and a variable is a reference to its name. On one harness, the list of actions has this server's actions under that name, and one action does what you meant.

## Template

The file has one of these two layouts. Omit `args` when the executable takes none. Omit `env` when the server reads no variable. The schema is the authority for the fields.

```json
{
  "name": "<server name, the same as the file name>",
  "description": "<what the server lets an agent do, for a person choosing the server>",
  "command": "<executable the harness starts>",
  "args": ["<argument, never a secret>"],
  "env": {
    "<variable the server reads>": "<the same name>"
  }
}
```

```json
{
  "name": "<server name, the same as the file name>",
  "description": "<what the server lets an agent do, for a person choosing the server>",
  "url": "<address that alone reaches the server, with no secret in it>"
}
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Exposure method | [Exposure method](exposure-method.md) | when | about to treat the record as the way a capability reaches an agent | take that an MCP server is not one of the four |
| 2 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | about to write the record as instructions the agent reads | take that an MCP server is not one, and the agent does not read the record |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or a converted section says when to use the server | take that the kind is already settled, and decide a section that is not the record |
| 4 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | placing the file | put the record in the component whose subject it is |
| 5 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | about to treat a pass as proof, to edit the harness file, or to write a name the rbtv CLI passes over | take the file the rbtv CLI recognizes, the harness file it writes, and which run writes that file again |
| 6 | Tool | [Tool](tool.md) | when | about to write the command as a path inside the component | take that this record does not name an executable inside the component |
| 7 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a second record would use the same server name | keep one home for the setting |

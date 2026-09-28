---
description: Choose and register how a component part reaches an agent
tags: [planning]
---

# Exposure — how rbtv puts parts in front of agents

`exposure.csv` is the component's manifest. It has exactly seven columns:
`part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots`. A row says where an
agent can find a part; the installer generates harness loaders from it. Edit the source row and
run `rbtv install` to update installed loaders. Never hand-edit a loader.

## Row rules

- Methods are **skill · command · rule · hook · sub-agent · agents.md · config · path · pool**.
  Part kinds are **capability · reference · workflow · task · prompt · tool · plugin/MCP**.
  Use one method and one kind per row.
- A first-party CLI gets a `tool,path` row even if it is reached through another skill. A
  `path` entry points to a runnable file or installed command. CLI authoring and executable
  requirements live in `../capabilities/create-cli/create-cli.md`.
- A standalone skill or guide gets a row only when an agent should reach it independently.
  Otherwise the component entry point links to it. A `pool` row names a reusable definition
  rather than an independently installed loader.
- `entry-point` is component-relative or `ws:<workspace-relative-path>` for a workspace tool.
  Do not use `..` to escape a component. Resolve every path before committing the row.
- `write-roots` is for a `path` row whose CLI must write runtime state. Each root is prefixed
  with `!`, and multiple roots are separated with `;`. No write grant is inferred.
- The row's method and entry point must match its actual consumer. A source file alone is not
  installed, and an exposure row alone does not make a console plan seat use the part: its
  body must name the instrument and invocation.

## Skills are the discovery route

A reusable ability MUST be reachable through an rbtv skill. Agents receive the skill, whose
instructions lead to the CLI; agent instructions MUST NOT substitute a bare command for that
route. Every `tool,path` row MUST be named by a skill in its component or by a parent skill that
routes to it. A CLI with no such route is buried.

One parent skill MAY route a module's requests to child skills and CLIs. Its description MUST
name concrete requests in the owner's words, so a plain request selects it. Its body MUST be a
request → child table, with the child ID and CLI name where relevant; NEVER copy a child's
instructions into the parent. Put the parent in the module's broadest existing component, since
exposure manifests belong to components, not module roots. `web/browse#web` and
`office/document#office` are worked examples; their children remain reachable through those
tables.

## Choice and verification

Use `exposure-choice.md` to choose the harness method. Then run `component-lint` on the
component and inspect its exposure census. Reinstall the component with `rbtv install` so
its workspace loaders match the source manifest. The installed loader must resolve to an
existing source file. A component part with no independent reader stays behind the entry
point and needs no extra exposure row.

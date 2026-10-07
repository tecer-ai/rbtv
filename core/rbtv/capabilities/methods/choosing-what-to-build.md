# Choosing what to build

Choose the kind from the work, when it must happen and who initiates it. The word “skill” or “command” in a request is a starting hint, not a reason to ignore a mismatch.

Use this page when creating, converting or reviewing a file whose kind is not settled. An ordinary edit keeps the existing kind. If that kind cannot support the required behavior, resolve the mismatch before editing.

## Reuse before adding

State what content is needed, who needs it and when. If the timing cannot be identified, clarify the task before choosing a kind. Search for a file or tool whose purpose already covers the work. Extend that owner instead of creating a duplicate. After choosing the kind, use [Choosing where to build](choosing-where-to-build.md) for placement.

## Separate computation from instructions

Apply the framework's deterministic-first principle to counts, dates, comparisons, formats and existence checks. Reuse an existing [Tool](../glossary/tool.md), or build one for a reusable exact operation. Keep judgment in instructions. A one-off computation for one conversation does not require a durable rbtv tool.

A tool's presence does not tell an agent when to run it. Continue to choose the instructions that name its use. A capability likewise needs an explicit route; the installer does not make its prose discoverable.

| Need | Kind and required follow-through |
|---|---|
| An exact command must run on a harness event even if the agent skips its instructions | [Hook](../glossary/hook.md). Confirm event support. OpenCode receives no rbtv hooks; follow the Hook entry’s unsupported-enforcement action. A prose fallback is not equivalent enforcement. |
| A server provides actions through the Model Context Protocol | [MCP server](../glossary/mcp-server.md). Configure its local command or address and secret-variable names, never secret values. |
| One local command-line operation supplies a result | Tool, plus reachable instructions for when to run it |

A model prompt in an outside hook is not an rbtv hook. Classify its instruction content separately.

## Choose how instructions reach the agent

Read [Exposure method](../glossary/exposure-method.md) for the four selection mechanisms, then the chosen kind's entry.

| Who makes the guidance available | Kind |
|---|---|
| The agent recognizes a task from a description | [Skill](../glossary/skill.md) |
| A human explicitly invokes the action and supplies inputs | [Command](../glossary/command.md) |
| Installation supplies standing guidance across tasks and folders | [Rule](../glossary/rule.md) |
| Work in a particular folder supplies its local guidance | [Folder instructions](../glossary/folder-instructions.md) |

A rule must state when to act; being supplied on every task does not mean executing its method on every task. Folder-specific instructions must not govern unrelated folders. Work that must also start without a human invocation cannot live only in a command.

A correction learned from one agent's runs belongs to the dreamer's [Learned rules](../../../ignite/capabilities/glossary/learned-rules.md), not a new shipped skill or rule.

## Put supporting work in its proper place

| Content | Home |
|---|---|
| A method needed only in some cases, or reused by another caller | [Capability](../glossary/capability.md), explicitly named by an entry point or prompt step |
| One short method needed by every reading, with no second caller | Keep it in the exposure method; do not add a file merely to shorten the body |
| Several capabilities sharing a purpose or documents | Apply [Nested exposure](nested-exposure.md) before creating separate exposure methods |
| A workspace file needed for some work in one folder | [Folder artifact](../glossary/folder-artifact.md), reached through folder instructions |
| A design decision that applies across kinds of rbtv work | [Principle](../glossary/principle.md), unless an existing principle already owns it |
| A term's meaning and instructions for building that kind | A glossary entry, using [Writing a glossary entry](writing-a-glossary-entry.md) |

Principles guide builders; rules guide an agent's behavior during tasks. Do not use a principle for an instruction the working agent must already receive. Principles and glossary entries are capabilities reached by the framework; they do not each need a skill. Do not add folder index files.

A [Pack](../glossary/pack.md) groups installation selections. It does not expose capability prose or replace an entry point.

## Decide whether a separate agent is needed

Choose an [Agent](../glossary/agent.md) only when work needs separate context and a standing prompt must handle different launch tasks. A checklist the caller can perform is not itself a reason to launch another agent. An agent is not an exposure method.

Write or change a [Prompt](../glossary/prompt.md) when the standing function or method of that agent needs work. The prompt and [Task](../glossary/task.md) entries own their sections; do not create a separate kind for every section.

## Verify the selection

Check that the selected mechanism delivers the content on a task that needs it and avoids applying it on a task that does not. Review from the requirement, not from the file's current folder. In a conversion, classify each distinct part before opening its authoring entry.

For an exact-answer request phrased as “build a skill,” the result must use a tool for that answer and guidance naming when to run it. Installer acceptance verifies recognized layout, not whether the kind fits the work.

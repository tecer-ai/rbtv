# Exposure method

An exposure method determines how guidance reaches an agent. rbtv has four: a skill, a command, a rule and folder instructions. Each is also an [Entry point](entry-point.md), regardless of whether its body contains instructions, routes or both.

| Method | Who determines delivery | What the author must support |
|---|---|---|
| [Skill](skill.md) | The agent matches a task to its description | Selection before the body is read |
| [Command](command.md) | A human invokes its name | Inputs supplied with invocation |
| [Rule](rule.md) | Installation makes the body available across tasks | A condition in the body determines when to act |
| [Folder instructions](folder-instructions.md) | The harness supplies guidance for the folder | Folder-specific instructions and the harness's loading limits |

These are rbtv's authoring distinctions. A harness may support other invocation paths—for example, typing a skill's name—but that does not make a shipped rbtv skill and command interchangeable.

An agent, prompt, hook, tool or MCP server is not an exposure method. A prompt step may nevertheless direct the agent to a capability. Use [Choosing what to build](../choosing-what-to-build.md) to select among these kinds, then the concrete entry for authoring and delivery details.

When changing who should initiate the work, reconsider the exposure method. When converting an outside file used both by human invocation and agent discovery, treat those as separate selection needs rather than assuming one rbtv source provides both.

In the concrete kind’s test plan, include a task that needs the guidance and one that does not. For a rule, the body remains present on both; only the action changes. For folder instructions, verify that the harness actually loads the relevant file.

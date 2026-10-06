# Entry point

An entry point is a skill, command, rule or folder-instructions file through which an agent receives guidance. These are the four [exposure methods](exposure-method.md). An agent, prompt or capability is not an entry point.

The body may contain instructions, routes to other pages, both or neither. This page governs how to divide that body; the concrete-kind entry governs when the agent receives it.

## Organize the body

Put information needed on every reading before conditional routes. A fact needed to choose a route must appear before that choice. If another page owns required guidance, read that page through a required route instead of copying it.

Put a method needed only for one case in a capability and name the condition for reading it. Name a reading directly at the step that needs it. Use a routing table when the reader must choose among several targets at the same point; do not turn every inline reference into a table row. A file can have both step-specific links and a table for a separate choice, without listing the same route twice. Do not create an index file merely to move the table elsewhere.

For an initial choice among routes, use this order:

1. Required information this entry point owns.
2. Required readings owned by other pages.
3. Conditional readings, each with a condition the reader can recognize now.

The [Routing table](routing-table.md) entry owns description fields and table columns. Each row names the instructions directly, not another entry point or a list of links. A row can name a folder, or an agent to launch by name. Use [Nested exposure](../nested-exposure.md) to decide whether a set belongs under one entry point; separate entry points do not route to one another.

## Cover the whole purpose in the description

The description must cover every kind of work the entry point supports, not just one row. The reader chooses the entry point before seeing its body. Name the shared purpose and selection boundary rather than listing every supporting filename.

A skill, command or rule has a description. Folder instructions do not: the harness supplies them when the agent works in the folder. A rule's description identifies when to install it; its body is then present on every task of that agent. Keep task-specific methods out of that always-present body and route to them when their condition occurs.

For a command, include the input that distinguishes the routes in its description. The human invokes it before the agent reads the body; do not defer that selection to an avoidable question after invocation.

Keep selection boundaries in the description itself. Some harnesses limit descriptions; consult [Harness](harness.md) for verified limits and uncertainty rather than assuming an unlimited listing.

## Resolve paths from the reader's location

| Source | Capability link base |
|---|---|
| Skill or command | The source file the agent is told to read |
| Rule | Repository root or `.rbtv/`; rbtv derives the destination path |
| Folder instructions | Follow the placement rules in [Folder instructions](folder-instructions.md) |

## Review the route

Update the description whenever an added or removed route changes the supported work. When converting, keep supporting content as capabilities rather than creating one skill per file. Replace index-only links with a direct reading instruction or a comparison-table row, as the reading situation requires.

When the entry point routes, include route coverage in the concrete kind’s verification tasks. Each supported route needs a matching case; a neighboring task must stay outside the scope. Before supplying the body, check selection from the description where the kind has one. Then check that the body supplies required readings and the matching conditional method, and that links resolve from their actual locations. Reuse cases that already cover these checks.

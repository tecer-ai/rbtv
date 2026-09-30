# Choosing what to build

Decide where the work belongs before choosing how to expose it. Reuse an existing home when its purpose already covers the work. Name each home you considered and why its stated purpose does not cover the work ([Keep it simple](../principles/kiss.md)).

## 1. Choose a [module](../glossary/module.md)

- **[`core`](../glossary/core.md)** holds components for rbtv itself, what runs it and what installs, configures, or edits it, and for the software that installs, runs, launches, and connects agents on any harness. A component can belong here even if it is not required for rbtv to start.
- **[`meta`](../glossary/meta.md)** holds how agents behave, communicate, plan, and coordinate work across tasks, which rbtv itself does not need to function.
- **Other modules** hold their own named areas of work. Check their stated purposes before creating another. Work outside `meta` does not automatically belong in `core`.

Create a module when none of the existing modules describes the new subject without stretching its boundary, and you can name one further component that would belong in that area. It does not need several components on day one.

[`core`](../glossary/core.md) and [`meta`](../glossary/meta.md) are the only modules with glossary pages. Do not add one for a new module.

## 2. Choose a [component](../glossary/component.md)

Keep cognitive units and capabilities in an existing component when they serve its one coherent purpose. Create a component when the new purpose can be stated separately and its skills, rules, commands, capabilities, and tools belong together for that purpose. A different exposure method alone does not justify another component.

To supply a component rbtv does not ship, or to replace a shipped component entirely, add it under [`mirror/`](../glossary/mirror.md). The same module and component name replaces the shipped component as a whole. Do not add a partial copy in order to patch one.

## 3. Choose what to build and expose

Build a [capability](../glossary/capability.md) when a second [skill](../glossary/skill.md), [rule](../glossary/rule.md), [command](../glossary/command.md), or [agent](../glossary/agent.md) needs the same content. If only one needs it, keep the content in that unit. A capability is never exposed itself. Expose an entry point when an agent or a human needs to discover or invoke it on its own.

Before any file uses a new rbtv term, write its glossary entry ([Terminology is king](../principles/terminology-is-king.md)).

| Choice | Use when | What reaches the agent |
|---|---|---|
| [Skill](../glossary/skill.md) | The agent should decide when an ability is relevant. | Its short description is always available; the agent reads the full skill when it chooses to use it. |
| [Command](../glossary/command.md) | A human should decide when to trigger the action. | The command's instructions when the human invokes it. |
| [Rule](../glossary/rule.md) | The instruction applies to every task of every agent that receives it. Being installed is not enough. | Its full text, on every task. |
| [Agent](../glossary/agent.md) | The same prompt must take a different [task](../glossary/task.md) each time, and no existing agent's purpose covers that prompt. | Its prompt on every task, with the task each launch supplies ([running an agent](../glossary/agent.md#running-an-agent)). |

A fixed checklist is not an agent. Content needed only at one step is a file a pointer opens then, not a rule ([Progressive disclosure](../principles/progressive-disclosure.md)).

If work on files in one folder would go wrong without instructions that do not apply outside it, build [folder instructions](folder-instructions.md). A rule is not scoped to a folder. Do not use them to hold a procedure, or text a skill, command, or capability already owns: point to that file. Content for one kind of file wherever it sits is a skill, not a copy in each folder.

Create a [tool](../glossary/tool.md) when a step has an exact answer and no existing tool does that operation. Do not build one for a step that needs a decision. Add [`<tool>.json`](tool-json.md) in the same change as the tool folder, and not for any other folder.

A [folder artifact](../glossary/folder-artifact.md) is not a row in the table. Add an [index file](index-file.md) when a folder's items are needed at different moments. Add [`<component>.json`](component-json.md) in the same change as a new component. Add a new kind only when those do not cover the purpose; it belongs to the component that defines that kind of folder.

## 4. Choose a unit inside the agent or the task

These are not exposure methods.

| Unit | Write it when | Not this |
|---|---|---|
| [Role](../glossary/role.md) | Every agent: who it is, and the standing function that holds for every task. | One task's boundary is [scope](../glossary/scope.md). |
| [Persona](../glossary/persona.md) | Open choices — when to stop, how broadly to explore, how to weigh risk, how to break a tie — would differ under a different standpoint. It sits inside the role. | No judgment left open: write none. That work may be a [tool](../glossary/tool.md) ([Deterministic first](../principles/deterministic-first.md)). |
| [Procedure](../glossary/procedure.md) | Every agent that does work: the reusable method. | This task's files are scope. This task's done checks are a [done contract](../glossary/done-contract.md). |
| [Constraints](../glossary/constraints.md) | A limit must hold on every task of this agent, honoring it takes judgment, and no tool can enforce it. | One step only: a procedure step. A tool can check it: name that tool in the procedure. |
| [Scope](../glossary/scope.md) | Every task: what to examine, and what may change. | The role's standing remit is not this boundary. Standing limits are constraints. |
| [Done contract](../glossary/done-contract.md) | Every task: observable conditions for this result, and what to do when it misses them. | A condition that holds for every task of the skill, command, or procedure is a check step there. |

Build a [principle](../glossary/principle.md) when a choice shapes how a cognitive unit, file, folder, or a design not yet made must be built, and no file in `principles/` already decides it. An instruction about how an agent behaves during a task is a [rule](../glossary/rule.md), not a principle.

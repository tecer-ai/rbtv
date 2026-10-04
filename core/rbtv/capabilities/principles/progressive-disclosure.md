# Progressive disclosure

**Statement.** Each piece of content reaches an agent at the moment its work needs it, even over the convenience of loading everything at the start.

**Rationale.** Everything in an agent's context, the text the model has in front of it, competes for its attention and uses limited space. Content that only some tasks need dilutes the instructions that every task needs. Loading too much at once is context load, and it makes the model drift from the instructions that matter; content that arrives when the step needs it also avoids the context gap of leaving it out ([context window](../glossary/context-window.md)).

**Implications**

- For each piece of content, decide when it must reach the agent and place it to match: needed for every [task](../glossary/task.md) of every agent that receives it, a [rule](../glossary/rule.md); needed when the agent judges it relevant, a [skill](../glossary/skill.md); needed when a human decides, a [command](../glossary/command.md); needed when the agent reads or changes files in a folder, [folder instructions](../glossary/folder-instructions.md); needed only at a specific step, a file that a rule, skill, command, or folder instructions point to at that step.
- Make content a rule only if it applies to every task of every agent that receives it. Anything that applies only sometimes goes behind a skill, a command, folder instructions, or a pointer.
- Write every pointer as a trigger: name the moment to open the target ("before adding a tool, read …"), not only the target.
- Use folder instructions to route the agent to the right file when it reads or changes files in that folder. A rule can also route, but it spends every task's context to do it; folder instructions route only where that folder's work happens.
- Keep a folder instructions file correct beside each parent file's instructions: no line contradicts a parent, and no line relies on a parent being dropped or ignored.
- The highest folder instructions file in a tree holds only that folder's own lines, plus pointers to files deeper in the tree.
- Give every unit chosen from its description before it is read (a skill, command, or agent) a name and a short description. The first sentence is enough to decide whether to open it for a given task. The rest names the triggers and one near-miss: a case that looks close but should not open it. Keep the detail behind that description.
- Give a folder whose items are needed at different moments an [index file](<../_under-evaluation/guides/folder artifacts/glossary/index-file.md>). An index line, and a record's description field, stay one line: the moment to open the item, or the sentence that decides — no near-miss.

# Deterministic first

**Statement.** Use tools for exact, repeatable steps and hand them to the agent ready to use, even over letting the agent work the steps out or build its own means.

**Rationale.** A model's estimate of a count, date, or comparison can be wrong in ways that look right, and an agent that searches for a tool or rebuilds one spends attention its judgment steps need. A tool gives the same answer every time, and its answer can be checked. A tool reduces hallucination, because an exact answer comes from the tool instead of the model's estimate, and context load, because the work runs outside the [context window](../glossary/context-window.md) and only its result enters it.

**Implications**

- Sort each step an agent is instructed to take, whether in a [procedure](../glossary/procedure.md), skill, command, or capability. A step with an exact answer, such as a count, date, format, existence check, transformation, comparison, or schedule, goes to a [tool](../glossary/tool.md) that the step names. A step that needs interpretation or a decision goes to the agent; never ask the agent to judge what a tool could compute.
- Make every record a tool reads or writes machine-readable, with fixed fields rather than free prose.
- Make every tool reachable from at least one [skill](../glossary/skill.md), [rule](../glossary/rule.md), or [command](../glossary/command.md) that says when to use it. Knowing a tool exists does not tell an agent when to use it.

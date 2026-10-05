# Keep it stupidly simple

**Statement.** Build the simplest thing that fully solves the problem, even over covering needs nobody has stated.

**Rationale.** Every file, step, option, and name is something an agent must read, understand, and keep correct, so unneeded parts cost attention and hide the parts that matter. Simple means easy to understand while carrying all the necessary information; leaving out substance does not make a result simple. Unneeded parts add context load and cognitive load, and missing substance leaves a context gap; each leads to hallucination or drift ([context window](../glossary/context-window.md)).

**Implications**

- Before creating a cognitive unit, tool, file, folder, or field, state in one line what fails without it. If nothing fails, do not create it.
- Add no option, setting, or field for a value that has only one use today.
- Create a new module, component, or folder only when no existing one's stated purpose fits. A different file type or exposure method alone is not a reason.
- Delete every sentence, step, and file whose removal loses no requirement and no decision.
- When principles pull against each other, choose the option with the fewest parts that still carries all the necessary information.

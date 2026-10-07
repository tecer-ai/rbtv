# Routing table

A routing table lets a reader compare several possible readings at one choice point. Use a direct reading instruction for a page needed at one specific step. An rbtv description uses the routing fields on one line; a table uses separate columns.

“Load” depends on the target: read a file or folder, open a skill, install a rule, invoke a command or launch an agent. Installing a rule determines who receives it. Its body separately determines when to act.

## Description format

Write a quoted, single-line description with these labels, in this order. Do not include links or a file cell.

```text
CONTAINS: <content> PURPOSE: <result> ALWAYS LOAD WHEN: <matching situation> DO NOT LOAD WHEN: <nearest excluded situation>
```

| Part | What to write |
|---|---|
| CONTAINS | The content that distinguishes this target from others with a similar purpose |
| PURPOSE | What the content enables; for a command or agent, include what the caller must supply |
| ALWAYS LOAD WHEN | A situation recognizable from the task before reading the target |
| DO NOT LOAD WHEN | A plausible neighboring situation that must not select this target; name the alternative or say no target is needed |

Write each field as a fact about the target or task, not an order to the reader. Describe situations, not just keywords. A request can need the work without using its name. Do not write procedure steps in a description; the reader has not yet received their prerequisites. Keep CONTAINS and PURPOSE distinct instead of repeating one sentence under both labels.

Keep the fields concise enough that the selection boundary and exclusion survive the target harness’s listing limit. Put the distinguishing content first in CONTAINS and the result first in PURPOSE; shorten those fields before dropping a condition. [Harness](harness.md) records known limits and uncertainty.

Every description needs an exclusion because it appears among descriptions its author does not control. “Unrelated tasks” gives no useful boundary. Name the closest task a reader could confuse with this one. Make clear which target is excluded; “do not open this skill” must not become “open no skill.” A repeated conversion mistake is “that task needs no skill.” Write “this skill is not needed for that task” unless the requirement actually excludes every skill. Check the rewritten exclusion against the original scope.

## Body-table format

When the reader has several targets to choose among at the same point, use one row per target and separate columns. Do not make a row for a link already used at its relevant procedure step:

```markdown
| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [Page](relative/path.md) | <content> | <result> | <condition> |
```

Add `DO NOT LOAD WHEN` only if at least one row has a plausible neighboring case, including a target outside the table or no reading at all. Leave the cell empty for rows without such an exclusion. Do not put a complete labeled description inside one cell.

A file, folder or capability is a link. An agent is its launch name, with required task inputs in PURPOSE. Do not give a prompt-file path where the reader needs to launch an agent.

An entry point's table names capabilities, files, folders or agents. It does not nest skills, rules, commands or folder instructions. Link directly to the instructions, not to a file whose only purpose is listing other files. Use [Entry point](entry-point.md) for the order of shared text and conditional readings, and [Nested exposure](../methods/nested-exposure.md) when deciding which capabilities belong together.

For links in a skill or command, use the source file as the base. In a rule, a capability path starts at the repository root or `.rbtv/`, so the installer can derive its destination. Use [Folder instructions](folder-instructions.md) for paths from an installed folder-instructions file.

## Write and check the choice

Write the target's instructions first. Then write the description or rows from the completed content. Match each condition against information the reader has before opening the target. Required pages come before the work that uses them; conditional pages state their trigger without requiring their own contents to interpret it.

Use the concrete-kind entry for the selection action: [Skill](skill.md), [Rule](rule.md), [Command](command.md) or [Agent](agent.md). A rule's description chooses installation, not execution on one task. A command or agent description must identify inputs supplied at invocation or launch.

When content, purpose, conditions or required inputs change, update the description and affected callers together. On conversion, split an outside description into the four fields and replace keyword-only triggers with task conditions.

Include selection in the concrete kind’s verification tasks: show neighboring descriptions or rows without their targets, with one task that should select the target and one that should not. Check the selection, supplied inputs and resulting link or launch name. Reuse cases that already check these conditions rather than adding a separate run.

# Rule

A rule is a cognitive unit whose body a harness puts into an agent's work on every task where the rule is installed, with no choice to load it. Outside rbtv, Claude Code has rules of its own: a file with no path list is loaded at the start of a session, and that harness strips the frontmatter before the model sees the file. The only frontmatter field that harness reads is a path list, which rbtv does not carry. Codex has no rules of this kind. Its rules are permissions on commands, and rbtv works around that by placing the body in the instructions file Codex already loads on every task. OpenCode reads no rules folder. Its rules are that same instructions file, and rbtv places the body there too.

A rule is for a fault the agent repeats from task to task, because a point in the work is not in front of it. The body is loaded on every task. The agent does not act on it on every task. An author wants a rule when that point comes in the agent's work in any folder, and no text the agent already has makes the agent notice it. Write a rule so that an agent which has it installed excels at the behavior the rule states when the point comes, and does not act on the rule when the point has not come.

## How it fails

The rbtv CLI can accept a rule, and the rule can still miss the fault. The rbtv CLI checks the frontmatter. It does not read the body, and it does not check that the description decides an install.

- The body tells the agent to run its steps from the first line on every task, and it does not say what to do when the point has not come. The agent runs those steps on a task the rule was not written for, or it skips the text because the steps do not fit, and the same fault returns.
- The first lines say the rule is always active, and they name no point the agent can observe. The agent performs a ritual on every task, or it ignores the text, and the owner corrects the same fault again.
- The acting condition is only in the description. The acting agent never receives the description, so it has no point to match. The reader then gives the rule to the wrong agents.
- A sentence is false outside one folder, or the body pastes steps the agent needs only when the point comes. The sentence is present on every task, including work in another folder, so the agent applies one folder's convention elsewhere, or the steps crowd the task where the point has not come.
- The body names a capability by a path from the source file's folder. The rule is placed away from that folder, so the agent cannot open the page, and it invents the steps or stops.
- An order names a quality, and a reviewer cannot name evidence of following it or of violating it on a task record. The harness presents the text and does not enforce it, so the agent skips the order even when the point has come.

## What it is composed of

The author writes one file, `rules/<name>.md`, in the component. The file has frontmatter and a body. The frontmatter follows the schema [rule.schema.json](../templates/rule.schema.json).

The body is what the agent acts on. Claude Code receives a copy of the whole file, and that harness strips the frontmatter before the model sees the file. Codex and OpenCode receive the body without the frontmatter, inside the instructions file they load on every task. The description is not in the text the agent acts from.

The description is the line a reader uses to choose whether to install the rule, for itself or for another agent. The page "Routing table"¹ has the form of that line.

The body always names the point the agent can observe, the order that applies when that point comes, and the order that applies when it has not come. The page "Cognitive unit"² says what the instructions of every cognitive unit contain, and how to write them.

When the rule routes, it is an entry point, and the body has a markdown table. The page "Entry point"³ says what an entry point is. The page "Routing table" says the columns. Name a capability in that table by a path from the root of the rbtv repository, or from `.rbtv/`. The rbtv CLI derives from that path the path that opens where the rule is placed. When the table names more than one capability, the page "Nested exposure"⁴ says when several capabilities belong under one exposure method. The page "Exposure method"⁸ says what an exposure method is. The table names capabilities. It does not name another exposure method.

A rule is loaded on every task of the place where it is installed, the installation root or one agent. The description does not decide that load.

## How to build it

1. **The repeated fault, the unnoticed point, and the tasks, then the purpose.** Find the fault the owner corrects again on a later task, after the agent has already been told. Do not start from the agents that will receive the rule. A user may have one agent, and those agents are chosen later, from the description. The cause is a point in the work the agent passes without seeing. Write the fact the agent can check when the point has come, in any folder, and write what the agent does today instead. The situation is one task where that point comes, and a second task in another folder, where the same point comes or where it does not. Then write the purpose from the fault: what the agent does when the point comes, so the fault stops, and what it does when the point has not come. When you cannot name a second folder where the point comes, stop and decide the kind with the page "Choosing what to build"⁵. An author who starts from the agents, or from the file's headings, writes a body that is present on every task and stops no fault.

   Weak: "This rule keeps the work sound on every task."

   Strong: "When a fix is about to start and the cause is not yet written, the agent writes the cause before the first edit."

   The weak line names no point, so the body that follows is present on every task and changes none of them.

2. **Put the point and both orders in the first lines.** Write the instructions before the description, as the page "Cognitive unit" says, and in the first lines of a rule name the point the agent can check, the order when that point comes, and the order when it has not come. The body is in the agent's work on every task, and the description does not select the task, so an order that lives only in the description is absent when the agent works. The harness presents the text and does not enforce it. A soft order is skipped even when the point has come.

   Weak: "Always apply this rule."

   Strong: "When the reply is chat with the owner, lead with the decision. When the work is not that chat, do not apply the chat order."

   The weak line names no point, so the agent applies the chat order to a file, or it ignores the text.

3. **Name each input and each tool in the body.** Name each input, and the tool for an exact answer, as the page "Cognitive unit" says. Put both in the body of the rule. The acting agent never receives the description, and no earlier text has selected this task, so a name that lives only in the description is absent when the agent works.

4. **Keep in the body only what a task needs before the point comes, and name the rest in a table.** Delete a sentence the failure does not need, as the page "Cognitive unit" says. On a rule, that sentence is still in the agent's work on a task where the point has not come, and the agent still reads it there. When the steps that apply at the point are needed only then, keep in the body the point and the row that names the capability, and put those steps in a capability. The page "Capability"⁶ says how to write that page. Write the table as the page "Routing table" says. The page "Entry point" says when text that every reading needs is a row, and when it is written in the body. When the table names more than one capability, read the page "Nested exposure" for when several capabilities belong under one exposure method. The rows are present on every task, so a row that has the steps in it is followed on a task where the point has not come.

   Write the path of a capability from the root of the rbtv repository, or from `.rbtv/`. The rbtv CLI derives from that path the path that opens where the rule is placed. A path from the source file's folder does not open there. Claude Code receives a copy of the file. Codex and OpenCode receive the body pasted into the instructions file at the root of the place where the rule is installed. On Codex the body is joined with the other instructions that harness loads, and that harness stops at a size limit. The rbtv CLI raises the limit and does not remove it, so a long body can be cut before the agent sees the end.

5. **Write the description from the body, as the install the reader chooses.** Write the description after the body, as the page "Routing table" says. The reader is choosing whether to install the rule, for itself or for another agent. The line does not tell the acting agent when to act. `CONTAINS:` answers what is in the body, in words that separate this rule from another with the same purpose, and it is not a step. `PURPOSE:` answers the behavior the agent excels at once the rule is installed, and it is not a task. `ALWAYS LOAD WHEN:` names the standing work of the agent that should receive the rule. The point comes in that work often enough that the body should be present on every task of that agent. It does not name one task, and it does not say that every agent should receive the rule. `DO NOT LOAD WHEN:` names a similar install the reader could choose instead, or that no install is right. A short list of rules can end before `ALWAYS LOAD WHEN:`. Write `CONTAINS:` and `PURPOSE:` so they already separate this rule from a neighbor the reader might install instead.

   Weak: `ALWAYS LOAD WHEN: the user says fix it`

   Strong: `ALWAYS LOAD WHEN: the agent fixes defects across tasks and the owner has had to name the cause again`

   The weak line names a task the person says. The reader installs the rule for that one saying, and the agent lacks the rule on the next fix.

6. **Keep one purpose, and read the other texts that will be present at the same time.** Keep the purpose the fault names, as the page "Cognitive unit" says. A second purpose is a second rule, because both bodies would be in the agent's work on the same task. Read the other rules, and the prompt, of an agent that will have this rule. When two of them give different answers, leave the answer in one text and point this rule at it. Do not restate the answer here.

When you edit, change the source file in the component's `rules/` folder, not the copy the rbtv CLI wrote. The rbtv CLI overwrites that copy the next time it installs the rule, and an edit to the source does not reach the agent until that install. The page "rbtv CLI"⁷ says how the install is run. Change the description in the same change as the body, as the page "Routing table" says. The reader chooses the install from the description.

On a conversion, keep the fault the outside file was written to stop. An outside rule often puts the acting condition in frontmatter the harness strips, or in a path list. Write that condition into the body, as the point and the two orders. rbtv does not carry a path list, and the acting agent does not receive the frontmatter. A permission on a command, such as a Codex rules file, is not this kind of rule. When a part of the outside file is another kind in rbtv, decide that part with the page "Choosing what to build". Steps needed only at the point go to a capability, and write its path from the root of the rbtv repository, or from `.rbtv/`.

When you review, read the body as the agent meets it, without the description. Take one task where the point comes and one where it does not, in another folder. Write each miss in the shape the page "Cognitive unit" gives for a finding. Then read the description alone, and name the install it causes and the install it refuses.

Checks:

- The first lines name the point the agent can check, the order when that point comes, and the order when it does not. A reviewer can name evidence of following each order and of violating it on a task record. No sentence is false on a task in another folder. Steps needed only at the point are a row, not a paste. A capability path starts at the root of the rbtv repository, or at `.rbtv/`.
- The description is one quoted line. `ALWAYS LOAD WHEN:` names the standing work of the agent that should receive the rule, not one task. `DO NOT LOAD WHEN:` names a similar install. `CONTAINS:` and `PURPOSE:` already separate this rule from a neighbor.
- Run the acceptance the page "rbtv CLI" names. A pass shows that the frontmatter matches the schema. A pass does not show that the body stops the fault. A pass does not show that the description decides an install. A pass does not show that the agent acts only when the point comes.
- Install the rule for one agent, or at the root. Give that agent a task where the point comes and a task where it does not, the second in another folder. Look at whether the agent follows the order only on the first, and whether a row opens the named page rather than an invented set of steps. Give the description, without the body, to a reader that is choosing an install. The reader installs on the case the line names and not on the similar case.

## Template

```markdown
---
name: <name>
description: "CONTAINS: <what is in the body, separating it from another rule with the same purpose> PURPOSE: <the behavior the agent does once the rule is installed> ALWAYS LOAD WHEN: <the standing work of the agent that should receive the rule> DO NOT LOAD WHEN: <a similar install the reader could choose instead>"
---

<The point the agent can check. The order when that point comes. The order when it has not come.>

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [<title>](<path from the rbtv repository root, or from .rbtv/>) | <what is in the capability> | <what that content is for> | <the point at which the agent opens it> |
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Routing table | [Routing table](routing-table.md) | when | writing the description, or a table in the body | take the form of the line and of the table, including the quotes on a description |
| 2 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | must | | write the instructions, and take only what a rule adds |
| 3 | Entry point | [Entry point](entry-point.md) | when | the rule routes | take what an entry point is, and when text that every reading needs is a row |
| 4 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | the table names more than one capability | take when several capabilities belong under one exposure method |
| 5 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the point comes in no second folder, or a part of a converted file is another kind in rbtv | decide the kind, or where that part goes |
| 6 | Capability | [Capability](capability.md) | when | steps are needed only when the point comes | write that page, and name it from the row at that point |
| 7 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | having the rbtv CLI accept the file, or an edit must reach the agent | find the command to run, and take what acceptance shows |
| 8 | Exposure method | [Exposure method](exposure-method.md) | when | the table might name another exposure method | take that a rule is one, and the table names capabilities |

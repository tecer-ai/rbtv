# Routing table

A routing table is the text from which a reader decides a load. A description of a skill, of a rule, of a command or of an agent is one line of that text, with no table around it. In the body of an entry point, and in folder instructions, a routing table is a markdown table.

To load is to read a file, a folder or a capability, to open a skill, to install a rule for an agent, to invoke a command, or to launch an agent with a task. Once a rule is installed, it is already in that agent's work on every task. The row does not decide when the agent acts on it.

Outside rbtv, a description is a sentence that says what a file does and when to use it. Here that description is the one line, and the line names a case in which the reader does not load. A table names that case only when at least one of its rows has a similar case.

The line, or the table, is the text the reader matches when it chooses the load. An author writes a routing table whenever that choice is made from a text other than the skill, the rule, the command, the agent, the file, the folder or the capability. Write the line, or each row of the table, so that a reader who has only that text loads in the situation the row names, and does not load in a situation the row names as one that must not.

## How it fails

The rbtv CLI can accept the file that has the routing table, and the routing table can still send the reader to the wrong load.

- The row restates what it names, or the situation is only in what it names. The reader never loads, because the row gives no situation, or it loads on the name alone, because the row gives no boundary.
- `ALWAYS LOAD WHEN` lists words the reader might see, and not a situation the reader can match without those words. The reader loads on a word and misses the same job when the word is absent.
- A description has no `DO NOT LOAD WHEN:`, or that part says the task is unrelated. The reader loads what this row names for a neighbor's job. A table lacks the exclusion column when one row has a similar case, so the reader loads that row for the other load. A table has the column when no row has a similar case, so the reader skips a load that was right.
- The first cell of a file, a folder or a capability is a bare name, or the first cell of an agent is a path. The reader searches, or it follows a path when an agent is launched by its name.
- One row names two. The reader loads both or guesses.
- `PURPOSE` of a command or an agent does not name what the reader has to give. The person invokes with nothing, or the launch carries no task, and the command or the agent then asks for what the load could have carried.
- A rule row names a task on which the agent should act, rather than a case in which to install the rule. The person installs it for one task, and the agent lacks it on the others, or installs it for every agent because the row says every task.
- A row in an entry point names a skill, a rule or a command, or a file that only lists other files. The reader loads that skill, rule or command instead of a capability, or loads a list and drops the match this table made.

## What it is composed of

A routing table is not a file of its own. The author writes it as a description, or as a markdown table in the body of an entry point or in folder instructions. Read the page "Skill"¹, the page "Rule"², the page "Command"³, the page "Agent"⁴, the page "Entry point"⁵ and the page "Folder instructions"⁶ for what each part contains for that kind.

A description is one line. The parts come in this order, each opened by its label in capitals and a colon: `CONTAINS:`, `PURPOSE:`, `ALWAYS LOAD WHEN:`, `DO NOT LOAD WHEN:`. The first three are always on the line. `DO NOT LOAD WHEN:` is always on a description. A description has no link and no file cell.

A table in a body has one row for each capability, file or folder the reader may load from that body. A row may also name an agent to launch, by its name, because an agent is not an exposure method. No row names a skill, a rule, a command or folder instructions. The columns are the file, then `CONTAINS`, `PURPOSE` and `ALWAYS LOAD WHEN`. Add a column `DO NOT LOAD WHEN` only when at least one row of that table has a similar case. A row that has no similar case leaves that cell empty. Do not write a body row as one labeled line. A description is one line because no table surrounds it.

The first cell gives what the reader loads:

- A file, a folder or a capability is a link. A row may name a folder.
- An agent is its name. The reader launches an agent by name, with a task.

The first cell names the file that has the instructions, or the folder the reader reads. It does not name a file that only lists other files. A row in an entry point does not name a skill, a rule or a command. An exposure method, as the page "Exposure method"¹¹ says, is not placed inside an entry point. Read the page "Entry point"⁵ when the named file only lists other files, and replace that pointer with rows. Read the page "Nested exposure"⁷ for when several capabilities belong under one exposure method.

When the table is in a rule and the cell is a capability, the path starts at the root of the rbtv repository, or at `.rbtv/`. When the table is in a skill or a command, write the link as the page "Entry point"⁵ says. When the table is in folder instructions, write the link as the page "Folder instructions"⁶ says.

Each part answers a different question. None repeats another, and none is a step of what the row names:

- `CONTAINS` answers what is in the skill, the rule, the command, the agent, the file, the folder or the capability, in words that separate it from another with the same purpose.
- `PURPOSE` answers what that content is for. When the row names a command or an agent, this part also names what the reader has to give at the load, in the words the reader supplies.
- `ALWAYS LOAD WHEN` answers in which situation the reader performs this kind's load.
- `DO NOT LOAD WHEN` answers in which similar situation the reader does not perform that load. When the reader should load another instead, the part names that other.

A similar case is a situation the reader could match to this row and also to another load. That other load may be another row of this table, a load the reader can make without this table, or no load.

A row that says to read a file on every reading of the entry point, or of the folder instructions, comes before the other rows. The page "Entry point"⁵ and the page "Folder instructions"⁶ say when that text is a row and when it is written in the body.

The placeholders name the decisions. They are not a row to copy.

```text
CONTAINS: <what is in the skill, rule, command or agent> PURPOSE: <what that content is for, and, for a command or an agent, what the reader has to give> ALWAYS LOAD WHEN: <the situation for this kind's load> DO NOT LOAD WHEN: <the similar situation>
```

```markdown
| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| <a link to a file, a folder or a capability, or the name of an agent> | <what is in it> | <what that content is for> | <the situation for this kind's load> |
```

```markdown
| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| <a link, or the name of an agent; a capability in a rule uses a path from the rbtv repository root, or from .rbtv/> | <what is in it> | <what that content is for> | <the situation for this kind's load> | <the similar situation, or empty when this row has none> |
```

## How to build it

1. **The wrong load, then what the row decides.** Find one load that went wrong where the reader had the routing table and did not have what the row names. The reader loaded one it should not have loaded, or it did not load one it should have loaded. The cause is the question the row does not answer. The question is what it contains, what it is for, when to perform this kind's load, or when a similar case must not. The situation is the point where the reader has the routing table and does not have what the row names. Name which choice that is. The reader is choosing a skill to open, a rule to install, a command to invoke or an agent to launch. Or the reader has already loaded an entry point or folder instructions and is choosing the next load. Write what this row decides, from that wrong load. Name what the row names, the load action and the situation. A row that starts from the columns, with a name filled in, is accepted and still decides nothing.

2. **Choose the shape.** Write a description when the row is the description of a skill, a rule, a command or an agent. One line, no link, no file cell, and `DO NOT LOAD WHEN:` always present. Write a markdown table when the row is in the body of an entry point or in folder instructions. One row for each one the table names. The columns are the file, `CONTAINS`, `PURPOSE` and `ALWAYS LOAD WHEN`. Add `DO NOT LOAD WHEN` when at least one row has a similar case, by the test below. A description always has a similar case, because the reader chooses it from other descriptions the author does not control. Name the nearest other one a reader could load for a request that shares a word or a purpose with this one.

3. **Write the description as one line, and the body as columns.** On a description, write the four labels in the order above, on one line. Do not write that line as columns, and do not write it as "Contains X. Serves Purpose Y. Must use when Z." On a table, write the columns in the order above. Do not write a body row as one labeled line. The reader finds each answer by its label or its column, and a second shape makes two readers split one row differently. When the row is a description in frontmatter, quote the value. A rule file is copied into the harness as written, and an unquoted colon after the first colon of the line is not one string to that harness.

4. **Answer the four questions, and leave every step in what the row names.** Write each part as the answer to its question, and stop. A step belongs in what the row names, because the reader has not loaded it yet, and a step in the row is followed without the rest. Write the step as the page "Cognitive unit"⁸ says. `CONTAINS` and `PURPOSE` are two answers. When they are the same sentence, the reader cannot separate this one from another with the same purpose.

   Weak: `CONTAINS: the order of the three milestones PURPOSE: the order of the three milestones`

   Strong: `CONTAINS: the order of the three milestones PURPOSE: takes an idea through those milestones to a brand book`

   The weak line gives one fact under two labels, so a neighbor with the same purpose looks like this one. A strong line shows one decision for one case.

   When the row names a command or an agent, name inside `PURPOSE` each input the reader has to give at the load, in the words the reader supplies. The load is the invoke or the launch, and the body is read after that load, so a question in the body asks for what the load could have carried.

   Weak: `PURPOSE: starts or resumes a trail run`

   Strong: `PURPOSE: starts or resumes a trail run for the idea the person names after the command`

   The weak line leaves the idea in the body. The person invokes with nothing.

5. **Write the situation the reader can match before the load.** Write `ALWAYS LOAD WHEN` as a situation the reader can match now, for this kind's load, without having loaded what the row names. A list of words a person might say is not a situation. For a rule, the situation is a case in which to install the rule for an agent, not a task on which the agent acts. The description does not decide whether the agent receives the body. Once the rule is installed, the agent has the body on every task. Read the page "Skill"¹, the page "Rule"², the page "Command"³, the page "Agent"⁴, the page "Entry point"⁵ or the page "Folder instructions"⁶ for what that situation contains for the kind.

   Weak: `ALWAYS LOAD WHEN: the user says interview, grill me, or question me`

   Strong: `ALWAYS LOAD WHEN: the subject is already formed in the person's head and the job is to question it`

   The weak line loads on the word and misses the same job said in other words.

6. **Name the similar case, or leave the column off.** On a description, write `DO NOT LOAD WHEN:` as one similar situation, and name the other the reader should load, or name that no load is right. On a table, add the column when at least one row has a similar case. A similar case includes a load the reader can make without this table, and it includes no load. It is not only another row of this table. A row of that table with no similar case leaves the cell empty. A part that says the task is unrelated excludes no situation the reader can match.

   Weak: `DO NOT LOAD WHEN: the task is unrelated`

   Strong: `DO NOT LOAD WHEN: the subject is not yet formed and the person wants it defined, which is a load of the brainstorm skill`

   The weak line names no situation and no other, so the reader loads this one for the neighbor's job.

7. **Give each one its own row, and fill the first cell for the load.** A row whose first cell names two, or whose purpose joins two with "or", makes the reader load both or guess. Split it into two rows. A file, a folder or a capability is a link. An agent is its name.

   Weak: `| [reviewer](agents/reviewer/agent.md) |`

   Strong: `| reviewer |`

   The weak line gives a path for a load that the reader does by name. The reader opens the file of the prompt and reads it, and launches no agent.

   When the table is in a rule and the cell is a capability, write the path from the root of the rbtv repository, or from `.rbtv/`. The rbtv CLI derives from that path the path the reader opens, in the place where the rule is placed. When the row names a capability, read the page "Capability"⁹, so the reader reads it and does not open it as a skill. When the named file only lists other files, read the page "Entry point"⁵ and replace that pointer with rows. A row in an entry point does not name a skill, a rule or a command. Read the page "Nested exposure"⁷ for when several capabilities belong under one exposure method.

- When you edit: change the four labels in the same change that alters what a description names, what it is for, when it is loaded, or what a command or an agent must be given. A description has no file cell, so a change that is only in the body is not in the text the reader matches. When the change alters what a table names, change that table in the same change. The table is in the entry point or the folder instructions, and the reader matches the table before it opens the named file.
- When you convert: take an outside description that says what a file does and when to use it, and write the four parts. Split what it does into `CONTAINS` and `PURPOSE`. Write the when as a situation in `ALWAYS LOAD WHEN`, not as the source's list of words. A near-miss in the source becomes `DO NOT LOAD WHEN`. When the source has none and the row is a description, name the nearest other. A procedure in the source stays in what the row names, not in the row. When that procedure is another kind in rbtv, decide with the page "Choosing what to build"¹⁰. An outside column table of a body becomes the columns above. An outside one-line description stays one line.
- When you review: read the row and not what the row names. Name the load the row causes for one situation that should load and one that should not. A review that opens what the row names first judges that one. It then misses a row that sends the reader to the wrong load.

Checks:

- A reviewer sees a description as one line, the four labels in this order, and no link. A reviewer sees a body routing table as a markdown table whose columns are the file, `CONTAINS`, `PURPOSE` and `ALWAYS LOAD WHEN`, with `DO NOT LOAD WHEN` only when at least one row has a similar case. The first cell of a file, a folder or a capability is a link. The first cell of an agent is its name. No row names two, or a file that only lists other files. No row in an entry point names a skill, a rule or a command. A capability in a rule uses a path from the rbtv repository root, or from `.rbtv/`. For a command or an agent, `PURPOSE` names what the reader has to give, in the words the reader supplies. `ALWAYS LOAD WHEN` is a situation for this kind's load, and a rule's situation is a case in which to install it.
- The rbtv CLI accepts the file that has the routing table. Acceptance shows that the file was recognized. It does not show that the row decides a load.
- Give the row, without what the row names, to a reader that also has the neighboring rows. Give one task that should load and one that should not. The reader loads on the first and not on the second. A command or an agent load carries what `PURPOSE` names.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Skill | [Skill](skill.md) | when | the row is a skill description, the first cell is a skill, or the situation is a skill's | take what each part contains for a skill |
| 2 | Rule | [Rule](rule.md) | when | the row is a rule description, or the table is in a rule | take what each part contains for a rule |
| 3 | Command | [Command](command.md) | when | the row is a command description, or the first cell is a command | take what each part contains for a command |
| 4 | Agent | [Agent](agent.md) | when | the row is an agent description, or the first cell is an agent | take what each part contains for an agent |
| 5 | Entry point | [Entry point](entry-point.md) | when | the table is in an entry point, the link is in a skill or a command, or the named file only lists other files | take the link base, and replace a list with rows |
| 6 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the table is in folder instructions | take the link base, and when text is a row or in the body |
| 7 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | several capabilities would belong under one exposure method | take when they belong under one exposure method |
| 8 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | a step is about to go into the row | write the step in what the row names |
| 9 | Capability | [Capability](capability.md) | when | the row names a capability | take what a capability is, so the load stays a read |
| 10 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a converted procedure is another kind in rbtv | decide where that procedure belongs |
| 11 | Exposure method | [Exposure method](exposure-method.md) | when | a row would name a skill, a rule or a command from an entry point | take what an exposure method is, so the row names a capability |

# Cognitive unit

A cognitive unit is the text that an agent is given and then acts on. In rbtv a skill, a rule, a command and a prompt are cognitive units. Outside rbtv those four are separate files, and the writing of each is a separate job.

A cognitive unit makes the agent do one piece of work the same way on a later task, including a task that the author did not have in front of them. An author wants one when that work still comes out wrong, or comes out differently each time, because no text tells the agent how. Which of the four to write is decided with the page "Choosing what to build"¹, before this page is opened. Write a cognitive unit so that an agent, reading it in the middle of a task, does the work that the failure names. The same text lets the agent decide a case that the instructions do not name.

## How it fails

The program can accept a skill, a rule, a command or a prompt, and the instructions can still fail, because the program does not read the instructions.

- The instructions list parts, and they never say what the agent does so that a repeated failure stops. The same failure happens when they restate a text whose only job is to say whether to load the cognitive unit, and when they explain a domain that the agent already knows. The agent was given this text as the instructions. It follows the list, and the work comes out as it did when no cognitive unit existed.
- The first lines are one case, and they do not say what the agent does so that the failure stops. The agent starts from those lines, and it applies them to a case they do not name.
- An input that the instructions use has no next action when it is absent. The agent fills the gap with a guess.
- A step whose answer is a count, a date, a comparison, a format or the existence of a file leaves the answer to the agent. The answer is wrong and still looks finished.
- The instructions name one harness's tool as the only way to do a step. An agent that runs on another harness follows that tool or stalls.
- The instructions assume a folder, a path or a fact that no input names. The agent invents the fact, or it acts on the wrong folder, because this text was given as the instructions and no pointer passed the fact in.
- The cognitive unit has a second purpose, or it pastes instructions that already have a home. The agent splits its attention, and the next edit makes the two copies disagree.
- The instructions have the agent report a finding as a quality. The reader cannot change a passage.
- The author stops when the program accepts the file. The instructions never meet a task.

## What it is composed of

The author writes no file named for a cognitive unit. The instructions are written as a skill, a rule, a command or a prompt. The page "Skill"² names the skill file and its folder. The page "Rule"³ names the rule file and its folder. The page "Command"⁴ names the command file and its folder. The page "Prompt"⁵ names where the prompt is written.

Every cognitive unit has instructions that the agent acts on. The first lines state the purpose: what the agent does after reading them, so that the failure does not happen. The instructions name each input that they use, and the next action when that input is absent.

A step whose answer is exact names the tool that answers it. A step that asks the agent to decide states what is observed when the decision is right. The page "Tool"⁶ says what a tool is.

When the same instructions serve a second cognitive unit, those instructions are a capability, and each cognitive unit sends the agent there at the step that needs them. A step of a prompt may send the agent to a capability in the same way. The page "Capability"⁷ says how to write a capability.

When the file has a text whose only job is to say whether to load the cognitive unit, that text is not part of the instructions. Write it after the instructions, as the page "Routing table"⁸ says.

## How to build it

1. **The failure, its cause and the situation, then the purpose.** Find the work that the agent does wrong, or does differently each time, on a task where no text tells it how. That work is the failure. Its cause is what the text that the agent already has does not give it: write the missing fact, the missing step, the missing limit or the missing next action. The situation is one task where that cause shows, and a second task that you are not looking at while you write. Then write the purpose from the failure: what the agent does after it has read the cognitive unit, so that the failure does not happen. An author who starts from the headings of a skill file, a rule file, a command file or a prompt writes instructions that have every heading and stop no failure.

   Weak: "After reading it, the agent does better work."

   Strong: "After reading it, the agent writes the cause before the first edit."

   The weak line names a quality, so the instructions that follow have nothing to stop.

2. **Write the instructions from that cause, and put the purpose in the first lines.** Write the instructions that the agent acts on before any text whose only job is to say whether to load the cognitive unit. That text is a summary of the instructions. A summary written first becomes the outline, and the instructions restate it instead of stopping the failure. Put the purpose in the first lines of the finished instructions, because the agent reads those lines and uses them to read the rest. Word each sentence as the page "Scaffolding language"⁹ says.

3. **Name each input, and the next action when it is absent.** Name each input that the instructions use. When one is absent, state the next action: stop and name the input, or continue from a substitute that you write down. Do not leave the gap. The agent fills an unstated gap with a guess, and the program still accepts the file. A folder, a path or an account that is true of one installation is not an instruction. Name it as an input that the task or the settings of the installation supply, or send the agent to the page that has it.

   Weak: "Use the files that the user provides."

   Strong: "When the task names no file, stop and name the file that the next task has to carry."

   The weak line leaves the gap, so the agent picks a file that the task did not name.

4. **Name the tool when the answer is exact.** For a step whose answer is a count, a date, a comparison, a format or the existence of a file, name the tool that answers it and when the agent runs the tool. Leave a step that needs a decision to the agent, and state what is observed when the decision is right. The model can be wrong on an exact answer in a way that looks finished, and the program does not run the step. Do not name one harness's tool as the only way. The agent may run on another harness, and then it follows that tool or stalls.

   Weak: "Check that the count of files is right."

   Strong: "Run the tool that lists the files, and use the count that it prints."

   The weak line leaves an exact answer to the agent, so a wrong count can look finished.

5. **Match the step to how it fails, and leave out what the agent would do the same without.** When one wrong detail fails the work, name that detail. When several ways succeed, state the result and the criterion, and name one way as the one to use. A list of ways makes the agent pick. A script for a decision makes the agent follow a path that does not fit the task. Do not explain a file format, a common command or a domain that the agent already uses. The agent was given this text in order to do the work. An explanation of what it already knows takes the reading from the step that stops the failure. Do not write a date after which the instruction changes. The agent is given the cognitive unit on a later task. It then acts on the dated line, and it does not do the work that stops the failure. State the instruction that is true of the later task.

6. **Keep one purpose, and do not paste a second home.** Keep the purpose that the failure names. A second purpose, whose result the first does not need, is a second cognitive unit. The agent splits its attention, and a reviewer cannot judge one result without the other. Before you write a paragraph, look for a page that already has those instructions. When one exists, send the agent to that page at the step that needs it, and name the moment. When a second cognitive unit needs the same instructions and no page has them, those instructions are a capability. Do not paste them into both. The next edit makes the two copies disagree, and the program accepts both files. For one behavior that the instructions govern, read the other cognitive units that the same agent will also have. When two of them give different answers, keep the answer in one and send the other to it.

7. **When the instructions have the agent report a finding, give the passage, what it causes, and the repair.** A finding that names a quality gives the reader nothing to change. The passage is the place in the work. What it causes is the effect of that place. The repair is what the agent does to that place.

   Weak: "The section is unclear."

   Strong: "The second paragraph states no next action when the file is absent, so the agent searches the workspace: stop and name the file."

   The weak line names a quality, so the reader cannot find the passage or the repair.

When you edit, change the instructions against the same failure. Delete a sentence that the failure does not need. It takes the agent's attention, and the program accepts the longer file.

When you convert an outside file, keep the failure that it was written against, and write the instructions from that failure. Drop a heading that the failure does not need. An outside file often explains the domain, lists several ways to do one step, and states no next action when an input is absent. When a part of the outside file is another kind of thing in rbtv, decide that part with the page "Choosing what to build"¹.

When you review, read the instructions as the agent meets them. Take one task that the instructions name and one task that they do not name. Write each failure as the passage, what it causes, and the repair. A review that only says the program accepted the file has not reviewed the instructions.

Checks:

- The first lines say what the agent does after reading the cognitive unit, and that action is the one that stops the failure.
- Each input that the instructions use is named, and each has a next action for when it is absent. No instruction assumes a folder, a path or a fact that no input names.
- Each step whose answer is a count, a date, a comparison, a format or the existence of a file names the tool that answers it. Each step that asks the agent to decide states what is observed when the decision is right. No step names one harness's tool as the only way.
- The instructions serve one purpose. Instructions that already have a home are named at the step that needs them, and they are not pasted.
- When the instructions have the agent report a finding, the finding is the passage, what it causes, and the repair.
- No other cognitive unit that the same agent reads gives a different answer for a behavior that these instructions govern.
- The program accepts the file, as the page "rbtv command"¹⁰ says. Acceptance shows that the checked fields match. It does not show that the instructions do the work, because the program does not read them.
- Give the cognitive unit to an agent, with one task that the instructions name and one task that they do not name, and with one input absent. Look at whether the agent does the work that the purpose names, what it does about the absent input, and whether an exact answer came from the named tool.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or a part of a converted file is another kind of thing in rbtv | decide which of the four to write, or where that part goes |
| 2 | Skill | [Skill](skill.md) | when | the cognitive unit is a skill | take the file, the folder, and what a skill adds |
| 3 | Rule | [Rule](rule.md) | when | the cognitive unit is a rule | take the file, the folder, and what a rule adds |
| 4 | Command | [Command](command.md) | when | the cognitive unit is a command | take the file, the folder, and what a command adds |
| 5 | Prompt | [Prompt](prompt.md) | when | the cognitive unit is a prompt | take where the prompt is written, and what a prompt adds |
| 6 | Tool | [Tool](tool.md) | when | a step has an exact answer | take what a tool is, and name that tool in the step |
| 7 | Capability | [Capability](capability.md) | when | a second cognitive unit needs the same instructions, or a step sends the agent to a page | write that page, and send the agent there at the step |
| 8 | Routing table | [Routing table](routing-table.md) | when | the file has a text whose only job is to say whether to load the cognitive unit | write that text as a row, and take the form |
| 9 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word every sentence so the agent acts on the meaning you gave it, and apply its tests |
| 10 | rbtv command | [rbtv command](rbtv-command.md) | when | having the program accept the file | find the command to run, and take what acceptance shows |

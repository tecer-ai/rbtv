# Deterministic first

Deterministic first is the principle that exact work is done by a CLI, and the answer is the same on every run. The agent receives that CLI ready to run. The principle applies when the request names a skill, a rule or a command. It also applies when the alternative is to let the agent estimate the answer or write its own means.

A count, a date, a format, an existence check, a transformation, a comparison or a schedule can be wrong when the agent estimates it. A wrong answer is accepted and still fails. The computation runs outside what the agent reads, and the agent reads only the result. A CLI returns the same answer every time, and a caller checks that answer without reading prose.

An author applies the principle before writing a line of the file that the request names, and again when a step is added to a capability, a skill, a rule, a command or folder instructions. Decide which file has the step with the page "Choosing what to build"¹. Apply the principle so that every step with an exact answer names a CLI. That CLI returns the answer. No step asks the agent to compute the answer that the CLI returns. A tool² built for one task is an asset that the next agent runs, so the next agent does not discover the answer by trial.

## How it fails

The rbtv CLI can accept a skill, a rule, a command or a tool, and the exact step can still be an estimate. The rbtv CLI does not read the steps. A name on PATH does not say when to run the tool.

- The request names a skill, a rule or a command, and the author writes that file with the exact step in its text. The agent estimates a count, a date or a comparison. A wrong answer is accepted and still fails.
- A step is worded as a question and sits among steps that need a decision, so the author leaves the computation to the agent. The check that follows treats the agent's number as the answer. A wrong count passes the check, or it fails a run that was right.
- A CLI for the step already exists, and the step does not name it. The agent searches, writes another CLI, or estimates. Searching and rewriting take the attention that the decision steps need.
- The code is a script. The script's failure is a sentence. The script's exit status does not match the outcome. The next agent cannot run the script on the first try and writes another script.
- The CLI is built, and no step, no folder instructions and no routing table names it and says when to run it. The next agent never meets it during the work.
- The record that the CLI reads or writes is free prose. The next run cannot read the prose the same way, so the agent parses the paragraph, and the exact answer is an estimate again.

## How to apply it

1. **Before a line of the file that the request names, mark each step that a CLI can answer the same way every time.** The name in the request is not the test. The test is the answer. A count, a date, a format, an existence check, a transformation, a comparison or a schedule has one result a CLI can return, and a caller can check it without reading prose. A step that needs interpretation or a decision stays with the agent. Take two facts to the page "Choosing what to build"¹ before you choose a file: which steps have an exact answer, and whether each such step is part of the work that a skill, a rule, a command, folder instructions or an agent instructs. When it is, the CLI that answers it is a tool. The one exact step that is not a tool is a script written for one conversation, which no file of rbtv instructs. The page "Keep it stupidly simple"³ refuses a tool for that step. Do not write the skill, the rule or the command that the request names and leave the exact answer in its text. When the answer has to be produced even if the agent never reads the step, take that fact to the same page.

   Weak: "The user asked for a skill that compares a filename with a date, so write the comparison into the skill and have the agent compare them."

   Strong: "The comparison of a filename with a date has one answer a CLI can return. Mark that step before you choose a file. The step is part of the work that the skill instructs, so the CLI is a tool. Take both facts to the page "Choosing what to build"¹. Do not write the comparison into the skill."

   The weak line follows the kind that the request names and leaves the comparison to the agent.

2. **In the file, have a CLI produce each marked answer, and leave a decision to the agent.** A step worded as a question is still a computation when its answer is a count, a date, a format, an existence check, a transformation, a comparison or a schedule. The check that follows takes the CLI's result. It does not take a number the agent states.

   Weak: "Record how many terms the load returned, and treat 0 as a failure."

   Strong: "Run the CLI that counts the terms in the glossary file, and take the number that it prints. Treat 0 as a failure only when that CLI returned 0."

   The weak line makes the agent's count the check. A wrong count passes the check, or it fails a run that was right.

3. **Name the CLI in the step, ready to run.** Do not tell the agent to find a CLI or to write one. The installer places a tool on PATH and writes no line that says when to use it, so a sentence that says the tool exists does not say when to run the tool. The page "rbtv CLI"⁴ describes that install.

   Weak: "Find a tool that counts the terms, or write one, and then take its number."

   Strong: "Run `term-count` on the glossary file and take the number that it prints. Do not search for a counter and do not write one."

   The weak line sends the agent to search or to write a CLI. That search takes the attention that the decision steps need, and the agent may estimate instead.

4. **When the file is a tool, build it so the next agent runs it on the first try.** Follow the skill "CLI creator"⁵. The caller types the inputs after the name. The answer is fixed fields. A failure exits nonzero, so the caller checks the status without reading prose. Do not write a second CLI for the same answer, because the two answers diverge as soon as one changes. The page "Single source of truth"⁶ has that rule. Place the tool in the component whose subject it is, with the page "Choosing where to build"⁷.

   Weak: "Write a Python file that prints the count, and tell the next agent to run it with the path of this task."

   Strong: "The next agent runs `term-count FILE` and reads one number. A missing file exits nonzero and names the path that it expected. Follow the skill "CLI creator"⁵ for that interface."

   The weak line works once for this author. The next agent cannot run that file on the first try and writes another file.

5. **Name the tool, and say when to run it, where an agent that did not open this file still reads both.** The step that needs the tool names it. Folder instructions or a routing table also names it and says when to run it. The page "Folder instructions"⁸ and the page "Routing table"⁹ say how those lines are written.

   Weak: "The tool is on PATH, so the agent will find it."

   Strong: "The row names `term-count` and says when to run it: before a glossary correction, run it and take its count."

   The weak line relies on a name on PATH. That name does not say when to run the tool.

6. **Give every record that the CLI reads or writes fixed fields, not free prose.** A CLI finds a value by the name of its field. It cannot find the value in a paragraph whose wording differs from one record to the next. The agent then parses the paragraph, and the exact answer is an estimate again.

   Weak: "Write the result as a sentence in the notes file."

   Strong: "Write `count` and `path` as fields the same CLI reads on the next run."

   The weak line makes the next run a reading task for the agent.

- When you edit: a new exact step in an existing file is a case of step 1. Mark it in the same change. The rbtv CLI does not ask whether a CLI already returns that answer.
- When you convert: an outside document whose steps include a count, a date or a format check does not keep those steps as prose for the agent. Mark each exact step, and decide the file with the page "Choosing what to build"¹.
- When you review: list every step that asks the agent for a count, a date, a format, an existence check, a transformation, a comparison or a schedule. Mark each that names no CLI. A review that only reads the tool record misses a step that still asks the agent to estimate.

Checks:

- A reviewer sees each exact step naming a CLI, and no step asking the agent to compute what that CLI returns. A record that the CLI reads or writes has fixed fields. A second agent can run a tool from its name, its inputs and its failure status, without rewriting it. Folder instructions or a routing table names the tool and says when to run it.
- The rbtv CLI accepts the skill, the rule, the command or the tool record. Acceptance shows that the file can be installed. For a tool, acceptance shows that the record names a file, and the installer can place that file on PATH. Acceptance does not show a step that names the CLI. It does not show an exit status that matches the outcome. It does not show a second agent that can run the CLI.
- On a task that has one count or one date, the agent runs the named CLI and reports its result. Then remove the name from the step and give the task again. If the agent states a number it computed, the step was not applied.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the request names a skill, a rule or a command, or a step is marked as an exact answer | choose the file, with the two facts this page names |
| 2 | Tool | [Tool](../glossary/tool.md) | when | the exact step is part of the work that a skill, a rule, a command, folder instructions or an agent instructs | take what a tool is, and that it is not a cognitive unit |
| 3 | Keep it stupidly simple | [Keep it stupidly simple](keep-it-stupidly-simple.md) | when | the exact answer is needed once, in one conversation, and no file of rbtv instructs the step | write a short script for that conversation, and build no tool |
| 4 | rbtv CLI | [rbtv CLI](../glossary/rbtv-cli.md) | when | about to treat a name on PATH as saying when to run a tool | take that the installer places the CLI and writes no line that says when to use it |
| 5 | CLI creator | [CLI creator](../../../../meta/code/skills/cli-creator.md) | when | the file is a tool | build the interface that the next agent runs on the first try |
| 6 | Single source of truth | [Single source of truth](single-source-of-truth.md) | when | a second CLI would return the same answer | keep one implementation |
| 7 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | placing the tool | put it in the component whose subject it is |
| 8 | Folder instructions | [Folder instructions](../glossary/folder-instructions.md) | when | an agent meets the tool while working in a folder | write the line that names the tool and says when to run it |
| 9 | Routing table | [Routing table](../glossary/routing-table.md) | when | writing the row that names the tool | write the row, including when to run the tool |

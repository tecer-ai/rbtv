# Tool

A tool is a CLI that an agent runs by name, when a step of a skill, a rule, a command, folder instructions or a prompt instructs it, and the record that names that CLI. Code that one conversation needs once, which no file of rbtv instructs, is a script and not a tool: the page "Deterministic first"¹⁰ says that boundary. The files sit under `capabilities/tools/<name>/`. `<name>` is the name the agent runs.

Outside rbtv a tool is often a function that a harness offers the model, or a CLI written for a person at a terminal. That person can answer a question when an input is missing. In rbtv the caller is an agent in the middle of other work. It runs the name from the folder of its task and acts on the result. It does not read the CLI as instructions, and it does not answer a question. The operation runs outside the context window¹, and only the result enters it. A tool is not a cognitive unit².

A tool is for a result that the agent takes and continues from. An author wants one when the page "Choosing what to build"³ has settled that this result is a tool. Write a tool so that the agent runs the name from the task folder, takes one named field from what the run prints, and stops with the next invocation named when that field cannot be printed.

## How it fails

The rbtv CLI can accept a tool, and the tool can still fail, because the rbtv CLI checks the record and does not read what the tool's CLI prints.

- The run prints the field inside a sentence, or only when the invocation carries a flag that the step does not name. The agent parses the sentence, or it never passes the flag, and it continues from a guess.
- A missing input asks a question on the invocation that the step names, or the run waits. The agent invents the input, or the run does not finish, and the task stops in the middle of other work.
- A failed run exits 0, or it prints the field on the same stream as the error. The agent takes that text as the result and continues.
- The CLI reads a file from the current directory, or from a path that is right only when the run is in the tool's folder. The agent runs the name from the task folder, so the read fails, and the agent guesses or writes a script.
- The run prints steps for the agent to carry out, and does not perform the operation. What enters the context window is a procedure. The agent does those steps, or it stops, and the tool did not return the field.
- Progress, a warning, or color is on the same stream as the field. The agent takes a line that is not the field as the result.
- The inputs and the field are named only in a comment or in the record. The agent does not read the tool's CLI, and the rbtv CLI writes no line from the record into what the agent reads. The agent runs the name with nothing, or it cannot tell which word is the field.

## What it is composed of

The author writes the CLI and the record in `capabilities/tools/<name>/`, in the component that the page "Choosing where to build"⁴ names. The record is `<name>.json`. The page "`<tool>.json`"⁵ says what that record contains. This page does not list its fields. The record names the CLI's file. Other files in the folder are files that the CLI reads. The CLI finds those from its own location, not from the current directory. The page "rbtv CLI"⁶ says the file that the rbtv CLI recognizes, and what a pass shows.

## How to build it

1. **The result the agent cannot take, then the purpose.** Before any line of the CLI, name three things. The failure is a run whose printed result the agent cannot take and continue from. The same failure is a run that does not finish. In both, the agent is in the middle of other work. The cause, for a tool, is what that run prints or waits for: a sentence, a question on the invocation, a file read from the current directory, or no field at all. The agent reads only the result. The situation is the agent, in the task folder, with the name and the inputs that the step has, and with one input absent. Find the field in the step that will tell the agent to run the tool. Then write the purpose from that failure: the run prints that field, and a run that cannot print it stops with the next invocation named.

   Weak: "The tool helps the agent compare a filename with a date."

   Strong: "The agent runs `date-cmp FILE` from the task folder and takes the field `match`. A missing file exits nonzero and names `date-cmp FILE` as the next invocation."

   The weak line names no field. The agent has nothing to take, so it compares the names itself.

2. **Print that field on the invocation that the step can write.** The agent runs the name and the inputs that the step names. It does not open the source to learn a flag. Print the field on standard output of that invocation, as a name and a value, because only that print enters the context window. Do not put the field inside a sentence. Do not hide the field on a second invocation. The step names the first invocation, and it does not name a flag. Follow the skill "CLI creator"⁷ for the words after the name, for help, and for a structured form when a caller needs many fields. The agent may run help when the step named the tool and the inputs are unclear. The field that the step takes is still printed on the invocation that the step can write, with no extra flag.

   Weak: "Print `The file matches the date.` on standard output of `date-cmp FILE`. A caller that needs many fields may also pass a structured form, and that form is not the only place `match` is printed."

   Strong: "Print `match true` on standard output of `date-cmp FILE`. A caller that needs many fields may also pass a structured form, and that form is not the only place `match` is printed."

   The weak line hides the value in a sentence. The agent parses the sentence.

3. **On the invocation that the step names, a missing input stops and names the next invocation.** When an input is absent or invalid, exit nonzero. Print no field on standard output. On standard error, name the invocation that has every input, in the words that the agent types. Do not ask a question on that invocation. Do not wait for a line on standard input. The agent's run may never send that line, and a question here is a question that the agent will invent an answer to. A check that a terminal is present does not make the asking path safe: the agent's run can look like a terminal. The page "Agent parity"⁸ says the invocation asks nothing.

   Weak: "When `FILE` is missing, ask which file to use."

   Strong: "When `FILE` is missing, exit nonzero, print no `match` line, and print `next: date-cmp FILE` on standard error."

   The weak line waits for an answer that the agent will invent, or for an answer that never comes.

4. **Find the CLI's own files from the CLI's file. Take the task's files as arguments.** The agent runs the name from the task folder. The current directory is that folder, not the tool's folder. A file that the CLI ships, such as a table beside the CLI, is read from the CLI's own location. A file of the task is an argument that the caller passes. Do not read a task file from a path that is right only in the tool's folder.

   Weak: "Read the table that ships with the CLI from the current directory. Take the task file as the argument `FILE`."

   Strong: "Read the table that ships with the CLI from the CLI's own location. Take the task file as the argument `FILE`."

   The weak line looks for the shipped table in the task folder. The read fails, and the agent guesses.

5. **Perform the operation in the CLI.** When the result is a change of state, the invocation makes that change. It does not print the steps that a person would follow. What would enter the context window is a procedure, and the agent would do those steps or stop. The page "Agent parity"⁸ says a path that prints the steps does not perform the action. Keep one implementation of the operation, as the page "Single source of truth"⁹ says.

   Weak: "Print the three commands the agent should run, and exit 0."

   Strong: "The CLI makes the change. It prints the field that names what changed, and it does not print commands for the agent to run."

   The weak line puts a procedure in the context window. The agent runs those commands, or it stops, and the tool did not make the change.

6. **Keep every other line off the stream that carries the field.** Progress, a warning, and color go to standard error, or they are omitted. The agent takes standard output as the result. A spinner line or a warning on that stream is a line that the agent may take as the field. The skill "CLI creator"⁷ says how color is written. Follow it for color. The field stays on the invocation that the step can write.

   Weak: "Print `working...` and then `match true` on standard output."

   Strong: "Print `match true` on standard output. Print `working` on standard error, or omit it."

   The weak line gives the agent two lines on the stream that it takes as the result. It may take `working...` as the field.

7. **Write the record so it names the CLI's file, and print the field from the CLI.** Write the record as the page "`<tool>.json`"⁵ says. The record names the CLI's file. Do not put the field or the inputs only in the record or in a comment. The rbtv CLI writes no line from the record into what the agent reads, as the page "rbtv CLI"⁶ says. When to run the tool is written in the text that instructs the step, as the page "Deterministic first"¹⁰ says, not in the CLI.

   Weak: "The description names `match` and `FILE`, and the CLI prints a sentence."

   Strong: "The record names `date-cmp.py`. The CLI prints `match` on `date-cmp FILE`."

   The weak line leaves the names in the record. The agent does not read that record during the work, and the CLI prints a sentence.

- When you edit: change the CLI that the record names. The next run executes that file. The page "rbtv CLI"⁶ says that the rbtv CLI writes no copy of the tool's CLI. A change to a comment that the agent does not run does not change the field.
- When you convert an outside CLI: keep the result that the caller needs, and write the CLI from that result. A question in the outside CLI becomes an input that the invocation names, and a missing input stops as step 3 says. A path that is right only in the outside CLI's folder becomes the CLI's own location, or an argument. A section that says when to run the CLI is not part of the tool. Decide that section with the page "Choosing what to build"³.
- When you review: run the name from a folder that is not the tool's folder, once with a known input and once with one input absent. Look at the field on standard output, the exit status, and whether the absent input names the next invocation. A review that only reads the record misses a question, a sentence, and a file read from the current directory.

Checks:

- A reviewer sees the invocation that the step can write printing one named field on standard output, with no other line on that stream. A missing input exits nonzero, prints no field, and names the next invocation. That invocation does not ask and does not wait. A file that the CLI ships is not read from the current directory. A failed run does not print the field on standard output. The invocation performs the operation.
- The rbtv CLI accepts the tool. Acceptance shows that the record names a file that exists, has a `#!` first line, is executable on POSIX, and that the rbtv CLI can place. It does not show the field, the exit status, a run from another folder, or that a second agent can act on the result.
- From a folder that is not the tool's folder, run the name with one known input and with one input absent. The known run's field matches the known answer. The absent input stops, and the next invocation is named.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Context window | [Context window](context-window.md) | when | reading what enters the agent's turn | take that only the result of the run enters it |
| 2 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | about to write the CLI as instructions the agent reads | take that a tool is not one |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or a converted section says when to run the CLI | take that the kind is already settled, and decide a section that is not the CLI |
| 4 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | placing the folder | put the tool in the component whose subject it is |
| 5 | `<tool>.json` | [`<tool>.json`](tool-json.md) | when | writing the record | write the record, and do not list its fields here |
| 6 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | about to treat a pass as proof, or to edit a copy of the tool's CLI | take the file that the rbtv CLI recognizes, what a pass shows, and that it writes no copy of the tool's CLI |
| 7 | CLI creator | [CLI creator](../../../../meta/code/skills/cli-creator.md) | when | writing the words after the name, help, color, or a structured form | build that interface, and keep the field on the invocation the step can write |
| 8 | Agent parity | [Agent parity](../principles/agent-parity.md) | when | the invocation would ask, or would print steps instead of performing the operation | take that the invocation asks nothing and performs the operation |
| 9 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a second CLI would return the same field | keep one implementation |
| 10 | Deterministic first | [Deterministic first](../principles/deterministic-first.md) | when | about to write when to run the tool into the CLI | write that line in the text that instructs the step |

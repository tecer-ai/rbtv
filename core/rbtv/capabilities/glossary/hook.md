# Hook

A hook is a record of a shell command that a harness runs when an event fires. Outside rbtv a hook can be a prompt to the model or an HTTP call. In rbtv the record names a shell command. A hook is not an exposure method¹. It is not a cognitive unit². The agent does not read the record as instructions.

A hook is for an action the harness runs when an event fires. The command does not run when the event fires in a case that the author excluded. An author wants one when the page "Choosing what to build"³ has settled that a harness must run this command on an event even if the agent reads no text. Write a hook so that the harness runs the command on the named event. The harness stops the action when the exit status or the output tells it to stop, lets the action proceed when the command exits 0 and prints nothing, and does not run the command in a case that the author excluded.

## How it fails

The rbtv command can accept a hook, and the hook can still fail, because the rbtv command checks the fields and never runs the shell command.

- The event is a sentence, or a name neither harness fires. The rbtv command copies that string as the key. The shell command never runs.
- The matcher is absent, and the shell command was meant for one tool. The shell command runs every time the event fires.
- The matcher is a sentence. It matches no tool name, and the shell command never runs. A matcher on `Stop` or on `UserPromptSubmit` is copied and ignored. The shell command then runs every time that event fires.
- The command is a sentence for a person, or a prompt for the agent. The harness executes the string as a shell command. The action proceeds, and the agent receives no instruction.
- The command waits for a person, or it reads arguments a person would type. The harness has sent the event as JSON on standard input and has passed no argument list. The command misses the input, or it waits until the harness stops it. On Claude Code, a stopped `PreToolUse` command hook does not block the tool call.
- The command exits 1 and prints a sentence, to block the action. Claude Code does not block on that exit status for most events. The action proceeds. On `PreToolUse`, Codex ignores plain text and does not treat it as a block.
- The command prints a reminder and exits 0 on a tool event, so that the agent will read the reminder. Plain text on `PreToolUse` does not reach the agent. The tool call is not blocked.
- The command is a path that is right only beside the hook file. The harness runs from the session's current directory. The command is not found. On Claude Code a missing command is a non-blocking error, and the action proceeds.
- The event is a name only one harness fires. The rbtv command writes that name into both hook files. The other harness never runs the command.
- The command exits 2 on `PostToolUse`, to undo a tool call. The tool has already run. The exit status does not undo it.
- The description states the block, and the command does something else. The harness never reads the description.
- The author expects the command to run for every session on the machine. The command runs only in a session that loads the file that the page "rbtv command"⁵ names. A Claude Code session started in a parent folder does not load that file, and the command does not run.

## What it is composed of

The author writes one file, `hooks/<name>.json`, in the component that the page "Choosing where to build"⁴ names. The page "rbtv command"⁵ says the file that the rbtv command recognizes, and the schema that it checks. It also says the files that the rbtv command writes for Claude Code and Codex. This page does not list the schema's fields. The schema is [hook.schema.json](../templates/hook.schema.json).

The event is always present. It is the name the harness fires. The rbtv command copies it as the key and does not check it against a list.

The matcher is absent when the command should run every time the event fires. When the matcher is present, it is the value the event compares.

The command is always present. It is the shell command the harness runs. The rbtv command writes that string, and does not write an argument list, a prompt, or an HTTP address.

The timeout is present when the command might not finish. It is the number of seconds before the harness stops the command. Absent, the harness uses its own default.

The description is always present. It is one line a person reads when listing hooks. The rbtv command does not copy it into the file the harness runs.

## How to build it

1. **The time the event ran wrong, then the purpose.** Before any field, name three things. The failure is a session in which the action proceeded, or the command ran in a case that should have been left alone. The cause, for a hook, is a record written for a person: the event is a sentence, the command prints for a person, or the exit status is the one a person reads as failure. The situation is two firings of that event, each with the JSON that the harness sends on standard input: one in which the command must run, and one in which it must not. Find the failure in a session where the harness fired the event, not in the request's word for the file. Then write the purpose from the failure: the command runs on that event, the harness stops the action or lets it proceed from the exit status and the output, and the command does not run in the excluded case.

   Weak: "The hook reminds the agent to lint before it finishes."

   Strong: "On PreToolUse, for Bash only, the command exits 2 when tool_input.command removes a file, and exits 0 with no print on every other shell command."

   The weak line names no event and no exit status. The harness has no decision to act on.

2. **Write the event as a name both harnesses fire, when both must run the command.** The rbtv command copies the string as the key in both hook files and does not check it. Use one of these names when the command must run on Claude Code and on Codex, because both document the name: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `PostCompact`. A name only one harness documents is still copied to both files, and the other harness never runs the command. Do not write a sentence in the event field. The harness compares the string with its event names.

   Weak: "Use `before an edit` when the command must run before a tool call on Claude Code and on Codex."

   Strong: "Use `PreToolUse` when the command must run before a tool call on Claude Code and on Codex."

   The weak line is copied as the key. Neither harness fires an event of that name, so the command never runs.

3. **Set the matcher to the value the event compares, or omit it.** Omit the field only when the command should run every time the event fires. Absent means all, and both harnesses then run the command every time the event fires. On `PreToolUse`, `PostToolUse` and `PermissionRequest` the value is a tool name. `Bash` is the shell on both. `Edit|Write` matches file edits on both: Claude Code's Edit and Write tools, and Codex's `apply_patch`. On Codex the matcher is a regular expression, so a short name can match a longer tool name that contains it. When the name must be the whole tool name on both, write `^` before the name and `$` after it, as in `^Bash$`. Claude Code treats a matcher that contains `^` or `$` as a regular expression, and that pattern still matches the whole name. On `Stop` and on `UserPromptSubmit` both harnesses ignore a matcher, so a matcher there does not limit the run. Do not write a sentence in the matcher. The rbtv command copies the string and does not check that it matches a tool.

   Weak: "On PreToolUse, set matcher to `when the agent runs a shell` when only a shell call should run the command."

   Strong: "On PreToolUse, set matcher to `Bash` when only a shell call should run the command."

   The weak line matches no tool name. The command never runs.

4. **Write the command as a program that reads the event JSON on standard input.** The harness runs the string as a shell command from the session's current directory. It sends one JSON object on standard input. It does not pass an argument list, because the rbtv command writes none. It does not show the string to the agent as instructions. Read the field the decision needs from that JSON. On a tool event, both harnesses send `tool_name` and `tool_input`. Do not wait for a person. Claude Code runs the command with no terminal for a person, and standard input is the event, so a question consumes the event or waits. A wait is stopped at the timeout, and on Claude Code a stopped `PreToolUse` command hook does not block the tool call. Point the command at a name the session can run, such as a tool name on PATH. A path that is right only beside the hook file is not found. The record has no finer filter than the matcher. When only some of the matched times should block, the command exits 0 for the rest. Other hooks on the same event also run, and this command cannot stop them from starting, so decide from the JSON alone. When that name is also a tool an agent runs, the page "Tool"⁶ says how the agent reads a run. This command still has to meet the exit status and the output in the next step, because the reader here is the harness.

   Weak: "The command asks which file to check, and reads the answer from the terminal."

   Strong: "The command reads `tool_input` from the JSON on standard input, and does not read a line from the terminal."

   The weak line waits for a person who is not there. The harness has already sent the event on standard input.

5. **Make the exit status and the output the decision the event acts on.** To let the action proceed and add nothing, exit 0 and print nothing. Both harnesses then continue. On Claude Code, silence does not approve a tool call that still needs permission. To block an event that can block, exit 2 and write the reason on standard error, or exit 0 and print one JSON object, and nothing else, which the harness reads for that event. On `PreToolUse` that object has `hookSpecificOutput`, `hookEventName` set to `PreToolUse`, and `permissionDecision` set to `deny`. Do not print only a top-level `decision` of `block` for that event: Claude Code reads `permissionDecision` there. Codex accepts `permissionDecision` of `deny`, and also accepts `decision` of `block` with a `reason`. A line before the JSON object is not the object Claude Code reads, and Codex ignores plain text on `PreToolUse`. Do not exit 1 and print a sentence. Claude Code treats that exit status, without a blocking JSON object, as a non-blocking error for most events, and the action proceeds. To put text where the agent can read it, print `additionalContext` inside `hookSpecificOutput`, with `hookEventName` set to the event, and exit 0. Plain text reaches the agent on `UserPromptSubmit` and on `SessionStart`, on both harnesses. It does not reach the agent on `PreToolUse`. On `PostToolUse` the tool has already run. Exit 2 does not undo it. On `Stop`, exit 2 does not reject the turn: Claude Code continues the conversation, and Codex continues the turn from the reason.

   Weak: "To block a PreToolUse call, the command exits 1 and prints `Blocked: do not run that.`"

   Strong: "To block a PreToolUse call, the command exits 2 and writes the reason on standard error, or it exits 0 and prints one JSON object with `permissionDecision` set to `deny`."

   The weak line does not block. Claude Code treats exit status 1, without a blocking JSON object, as a non-blocking error for most events. Codex ignores the sentence on `PreToolUse`.

6. **Write the description for a person who lists hooks, not for the harness.** One line, naming the event and what the command does. The rbtv command does not copy the description into the file the harness runs. A block that lives only in the description never runs.

7. **Set timeout when the command might not finish.** The number is seconds. The harness stops the command at that count. Absent, the harness uses its own default. On Claude Code, a `PreToolUse` command hook that is stopped does not block the tool call. The block is an exit status, not a wait.

- When you edit: change `hooks/<name>.json`. The harness runs the file the rbtv command writes from that source. The page "rbtv command"⁵ says which run writes that file again. A change to the description does not change the command the harness runs.
- When you convert: keep a shell command that reads standard input, and keep an event name both harnesses fire. A prompt, an HTTP address, or an agent in the source is not this record. The rbtv command writes a shell command. Decide that part with the page "Choosing what to build"³. A message that the outside hook showed a person becomes the reason on standard error, or a field of the JSON the event reads.
- When you review: run the command with one JSON object on standard input, once for the time that should block and once for one that should not. Look at the exit status and at standard output. A review that only reads the record misses a sentence, an exit status of 1, and a command that waits. Do not judge the hook from a session that does not load the file that the page "rbtv command"⁵ names. On Codex, do not judge it before a person has trusted that hook definition. Codex skips the hook until then, and the record cannot set trust.

Checks:

- A reviewer sees an event name both harnesses fire, when both must run the command. The matcher is absent only when the command should run every time the event fires, and it is not a sentence. The command reads standard input and does not wait. A block is exit status 2 with the reason on standard error, or exit status 0 with one JSON object the event reads. A proceed-and-add-nothing result is exit status 0 and no print. The description does not carry the block.
- The rbtv command accepts the hook. The page "rbtv command"⁵ says what acceptance shows. It does not show that the event fires. It does not show that the command reads standard input. It does not show a block from exit status 2, and it does not show that the harness ran the command.
- Feed the command one JSON object for the event, with the input that should block, and one that should not. The blocking run exits 2, or prints the JSON decision and nothing else. The other exits 0 and prints nothing that blocks.

## Template

```json
{
  "name": "<name>",
  "description": "<one line a person uses when listing hooks: the event, and what the command does>",
  "event": "<a name both harnesses fire, when both must run the command>",
  "matcher": "<the tool name or other value the event compares, or omit this field>",
  "command": "<a shell command the session can run, which reads the event JSON on standard input>",
  "timeout": <a whole number of seconds, at least 1, before the harness stops the command; or omit this field>
}
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Exposure method | [Exposure method](exposure-method.md) | when | about to treat the hook as the way a capability reaches an agent | take that a hook is not one of the four |
| 2 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | about to write the record as instructions the agent reads | take that a hook is not one |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or the source runs a prompt, an HTTP address, or an agent | take that the kind is already settled, and decide a part that is not a shell command |
| 4 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | placing the file | put the hook in the component whose subject it is |
| 5 | rbtv command | [rbtv command](rbtv-command.md) | when | about to treat a pass as proof, or to edit the file the harness reads | take the file the rbtv command recognizes, where it writes the hook, and what a pass shows |
| 6 | Tool | [Tool](tool.md) | when | the command is also a program an agent runs by name | take how the agent reads that run, and still meet the exit status and the output on this page |

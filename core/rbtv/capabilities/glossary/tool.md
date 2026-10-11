# Tool

A tool is a command-line program that an agent runs during a task. A script used once in a conversation is not an rbtv tool; [Deterministic first](../principles/deterministic-first.md) explains that boundary.

Use a tool when a step needs an operation performed or an exact result calculated outside the agent's context window. The caller supplies inputs and acts on the result. It does not read the program as instructions or answer questions during the run.

A tool is either shared or owned by one agent. A shared tool belongs to a component: its record makes the program available by name, on PATH, to every agent working where the component is installed. An agent-owned tool serves one agent and lives in that agent's folder, off PATH. This page applies to both; where the two differ it says which, and the section A tool owned by one agent gives the agent-owned side.

## Files and interface

Put a shared tool's program and its record in `capabilities/tools/<tool>/` of its component. Use [Tool record](tool-json.md) for its fields; the record names the executable and supplies its name and one-line listing description. An agent-owned tool has the same folder inside its agent's folder and no record. If it has not already been read for this task, read [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) when designing the commands, help, structured output or color behavior.

Start with the invocation the calling step will use and the result it needs. Return that result as a named field on standard output of that invocation. Do not bury it in a sentence or require an extra output flag the caller was never told to pass. For example, `date-cmp FILE` can return `match true`. Use the structured form specified through Building a command-line interface when the caller needs several fields.

Keep progress and warnings on standard error, or omit them. Color must not contaminate the result. A failed run exits nonzero, prints no result on standard output, and names the next complete invocation on standard error. Missing or invalid inputs follow this same path: do not ask a question or wait for standard input. Detecting a terminal does not authorize a prompt; an agent's run can have a terminal too.

Resolve files shipped with the program from the program's own location. Receive task files as arguments. The caller runs the tool from its task folder, which may be anywhere.

Keep nothing the tool writes beside the program. An agent-owned tool writes in its agent's folder, as its section states. For a shared tool, what the user chose or supplied (settings, choices, credentials, keys) goes in `.rbtv/config/<component>/`, under the name of the tool's component; read [Config](config.md) before saving any. What the tool writes while running (state, caches, locks, logs) goes in `.rbtv/runtime/<component>/`; read [Runtime](runtime.md) before writing any.

Perform the operation in the program. Printing commands for the agent to execute returns another procedure, not the requested result.
## How an agent finds the tool

Do not write a skill, rule or command only to tell agents that a shared tool exists. rbtv writes the `rbtv-tools` rule from the records of the installed tools and supplies it to every agent working where the tool is installed; [rbtv CLI](rbtv-cli.md) describes that rule. The description in the [Tool record](tool-json.md) is the tool's row in it, and `-h` gives the commands. An agent decides from that one line whether the tool fits its step, so write the description as Tool record specifies.

When a procedure needs the tool at a fixed step, the skill, rule, command, folder instructions or prompt that owns the procedure names that step and the invocation. That sentence belongs to the procedure; the tool is found without it.

An agent-owned tool is not in the `rbtv-tools` rule. Its agent finds it through the prompt alone.

## A tool owned by one agent

Build an agent-owned tool when one agent alone needs the program. It is a file of that agent's folder, not a component and not part of one: rbtv does not scan, validate, install or list it, and [rbtv CLI](rbtv-cli.md) states that adding and updating the agent leave it unchanged. Do not write a component, a mirror component or a record to hold it.

- **Location.** Put the program and its page in `capabilities/tools/<tool>/` inside the agent folder, and a method page only this agent follows in `capabilities/methods/` there. This is the layout a component uses, so the pages route to each other the same way.
- **Invocation.** The program is not on PATH and has no name to run it by. The agent's prompt names the tool, says when to run it and gives the complete invocation with the program's path from the agent folder, which is the agent's working folder: `capabilities/tools/<tool>/<tool>` followed by its arguments. Any other caller of the tool is given that same path. [Prompt](prompt.md) says how the prompt states the action for a missing dependency.
- **What it writes.** The tool writes in the agent's folder, with the agent's other live data and outside `capabilities/`, never in `.rbtv/runtime/`. A tool that checks for new items keeps there its own record of the items it already reported, one record per check, so the same item is reported once. Values the user chose for the tool are in the agent's [settings](settings-json.md).
- **Promotion.** An agent-owned tool becomes a shared tool only when the owner says so. Until then it stays in the agent's folder, even when another agent could use it: do not move it into a component, and do not put it on PATH.

## Documentation

Document the tool in one page, `capabilities/tools/<tool>/<tool>.md`, beside its record. The page states what the tool is, the result each verb returns that `-h` does not say, and the maintenance facts: spec sources, layout and self-checks. It routes to the tool's methods in `capabilities/methods/`. `-h` stays the interface reference; never copy it into the page.

When the tool needs a second page, put it under `documentation/` in the same folder and route to it from the tool's page.

## Editing, conversion and review

Edit the executable named in the record. The installer creates a launcher, not a second copy of the program, so the next run uses the changed source. An agent-owned tool is edited where it sits, and the next run by its path uses the change. See [rbtv CLI](rbtv-cli.md) when changing installation details.

When converting a human-facing program, turn questions into explicit inputs and remove dependence on its working directory. Preserve the caller's needed result. State what the program does and returns in the record's description. A procedure that must run it at a fixed step is placed through [Choosing what to build](../methods/choosing-what-to-build.md), not in the record.

Run the named invocation from another folder, or an agent-owned tool's invocation from its agent folder, with a known input, a missing input and an invalid input. Check the result against the known answer, the exit status and each output stream. Confirm that the operation actually occurred and that failure neither waits nor returns a success-shaped result.

Installer acceptance checks a shared tool's record and the executable's presence, shebang and executable permission on POSIX; nothing checks an agent-owned tool but its run. Acceptance does not prove the output contract or runtime behavior. A review must exercise the program, not just inspect its record.

# Tool

A tool is a command-line program that an agent runs during a task, together with the record that makes the program available by name. A script used once in a conversation is not an rbtv tool; [Deterministic first](../principles/deterministic-first.md) explains that boundary.

Use a tool when a step needs an operation performed or an exact result calculated outside the agent's context window. The caller supplies inputs and acts on the result. It does not read the program as instructions or answer questions during the run.

## Files and interface

Put the program and its record in `capabilities/tools/<tool>/`. Use [tool-json.schema.json](../templates/tool-json.schema.json) for its fields; the record names the executable and supplies its name and one-line listing description. If it has not already been read for this task, read [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) when designing the commands, help, structured output or color behavior.

Start with the invocation the calling step will use and the result it needs. Return that result as a named field on standard output of that invocation. Do not bury it in a sentence or require an extra output flag the caller was never told to pass. For example, `date-cmp FILE` can return `match true`. Use the structured form specified through Building a command-line interface when the caller needs several fields.

Keep progress and warnings on standard error, or omit them. Color must not contaminate the result. A failed run exits nonzero, prints no result on standard output, and names the next complete invocation on standard error. Missing or invalid inputs follow this same path: do not ask a question or wait for standard input. Detecting a terminal does not authorize a prompt; an agent's run can have a terminal too.

Resolve files shipped with the program from the program's own location. Receive task files as arguments. The caller runs the tool from its task folder, which may be anywhere.

Keep nothing the tool writes beside the program. What the user chose or supplied (settings, choices, credentials, keys) goes in `.rbtv/config/<component>/`, under the name of the tool's component; read [Config](config.md) before saving any. What the tool writes while running (state, caches, locks, logs) goes in `.rbtv/runtime/<component>/`; read [Runtime](runtime.md) before writing any.

Perform the operation in the program. Printing commands for the agent to execute returns another procedure, not the requested result. The calling skill, rule, command, folder instructions or prompt must name when to run the tool and the invocation to use. Putting that information only in a source comment or the tool's record does not deliver it to the agent.

## Documentation

Document the tool in one page, `capabilities/tools/<tool>/<tool>.md`, beside its record. The page states what the tool is, the result each verb returns that `-h` does not say, and the maintenance facts: spec sources, layout and self-checks. It routes to the tool's methods in `capabilities/methods/`. `-h` stays the interface reference; never copy it into the page.

When the tool needs a second page, put it under `documentation/` in the same folder and route to it from the tool's page.

## Editing, conversion and review

Edit the executable named in the record. The installer creates a launcher, not a second copy of the program, so the next run uses the changed source. See [rbtv CLI](rbtv-cli.md) when changing installation details.

When converting a human-facing program, turn questions into explicit inputs and remove dependence on its working directory. Preserve the caller's needed result. Route instructions about when to use it through [Choosing what to build](../methods/choosing-what-to-build.md); they do not belong in the tool's record.

Run the named invocation from another folder with a known input, a missing input and an invalid input. Check the result against the known answer, the exit status and each output stream. Confirm that the operation actually occurred and that failure neither waits nor returns a success-shaped result.

Installer acceptance checks the record and the executable's presence, shebang and executable permission on POSIX. It does not prove the output contract or runtime behavior. A review must exercise the program, not just inspect its record.

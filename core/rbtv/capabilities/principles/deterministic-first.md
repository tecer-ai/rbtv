# Deterministic first

Use a command-line program for work with an exact answer, and leave interpretation and judgment to the agent. Give the agent the program ready to run; do not make every agent discover or rebuild it.

Apply this before accepting the kind of file named in a request and when adding a step. Counts, date calculations, format and existence checks, fixed transformations, comparisons and schedules often have exact answers. The test is whether the same specified inputs and rules determine the result; wording the step as a question does not turn it into judgment.

## Separate calculation from judgment

For each exact step, identify the inputs, operation and result. Check for an existing implementation first. The calling step names the program and inputs and uses its returned result, rather than a number or comparison the agent estimates. Keep interpretation of that result in the agent's instructions.

Take the exact steps to [Choosing what to build](../methods/choosing-what-to-build.md). If a skill, rule, command, folder instructions or agent will repeatedly instruct the operation, provide a [tool](../glossary/tool.md). If the operation is needed only in one conversation and no rbtv file instructs it, use a short script. [Keep it stupidly simple](keep-it-stupidly-simple.md) refuses a durable tool for an unstated recurring need. If the operation must run even when the agent ignores instructions, the choice page must account for that too.

## Make the result usable

For a durable tool, follow [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md): explicit inputs, fixed result fields and a nonzero failure status. Machine-read records use fixed fields, not paragraphs the agent must reinterpret. Keep one implementation and place it in the component that owns the subject.

The step that needs the tool names its invocation. Also make its name and use condition reachable through the relevant folder instructions or routing table, so an agent that has not read the implementation can discover it. Being on PATH does not explain when to use it; the installer supplies no such instruction automatically.

## Verify the split

On edit or conversion, inspect every new exact step as well as the tool itself. When changing this principle, give an agent a task with a known count, date or comparison. Confirm that it calls the named program and uses the result. Check that failure is distinguishable without interpreting prose and that a second agent can run the interface without rewriting it.

Installer acceptance proves placement and record validity, not that the calling instructions use the tool or that its result is correct.

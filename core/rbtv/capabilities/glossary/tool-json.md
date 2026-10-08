# `<tool>.json`

`<tool>.json` is a tool’s record at `capabilities/tools/<tool>/<tool>.json` inside its component. It identifies the program rbtv makes available by name and describes it in listings.

Use [tool-json.schema.json](../templates/tool-json.schema.json) for the fields and [rbtv CLI](rbtv-cli.md) for executable-path resolution and installation checks. Follow [Tool](tool.md) when changing the program or its calling interface.

The description is how an agent finds the tool: rbtv shows this line in listings and in the `rbtv-tools` rule, which every agent working where the tool is installed receives. [Tool](tool.md) states that nothing else is needed for the tool to be found.

Write it as one line that names each operation the tool performs and the result it returns, in the words of the task an agent would have. An agent that has never seen the tool must be able to decide from this line whether it fits the step, and to distinguish it from a nearby tool, without opening the program. Leave out how the program is built, its history and its internal checks. State a limit only when it decides whether the tool can be used.

> Not: “The entry point every caller resolves; gates writes behind an active grant.”
>
> But: “Slack from one command: reads and searches messages, downloads and uploads files, sends messages, adds reactions and edits canvases.”

Keep the steps of a procedure that runs the tool in that procedure, not in this record.

Install the tool and read its row in the `rbtv-tools` rule as an agent holding a task would: the row alone must tell that agent whether to run the tool. Check that the installed name resolves to the intended executable. Follow Tool for testing the program’s behavior.

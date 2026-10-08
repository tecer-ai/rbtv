# `<tool>.json`

`<tool>.json` is a tool’s record at `capabilities/tools/<tool>/<tool>.json` inside its component. It identifies the program rbtv makes available by name and describes it in listings.

Use [tool-json.schema.json](../templates/tool-json.schema.json) for the fields and [rbtv CLI](rbtv-cli.md) for executable-path resolution and installation checks. Follow [Tool](tool.md) when changing the program or its calling interface.

Write the description as one line identifying the operation and result, so a reader can distinguish it from a nearby tool without opening the program. rbtv shows this line in listings and in the `rbtv-tools` rule, which every agent working where the tool is installed receives; [rbtv CLI](rbtv-cli.md) describes that rule. Keep steps and instructions for when to run it in the caller, not in this record.

Check the displayed description and that the installed name resolves to the intended executable. A record makes the program discoverable through rbtv listings and the `rbtv-tools` rule; the calling instructions must still tell the agent when to use it and the invocation to run. Follow Tool for testing the program’s behavior.

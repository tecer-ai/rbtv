# Tools of the browsing component

This folder holds the tool of the `browsing` component: `capture-cli`. A tool's folder holds its program, its record, its tests, its page and, when it needs more than one page, `documentation/`. Prose methods live in `../methods/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [capture-cli](capture-cli/capture-cli.md) | What `capture-cli` returns, its optional extractors and its checks | Change or check the program without breaking the method that calls it | editing, reviewing or testing `capture-cli/capture.py` or its record |
| [Reading a page](../methods/reading-a-page.md) | The method that runs `capture-cli`: the invocations, what each result means and when to name an extractor | Keep the result fields and failure names aligned with the step that reads them | changing an option, a result key or a `failure_reason` name |
| [Building a command-line interface](../../../code/capabilities/methods/building-a-cli.md) | The method for designing, building and testing a command-line interface | Keep a tool's options, help, output and failures usable by a person and an agent | adding a tool here, or changing a tool's options, help, output or exit statuses |

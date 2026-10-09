# code tools

This folder holds the tools of the `code` component: `cli-preview` (validates a Markdown-authored review of a command's output and renders it to one offline HTML file) and `rbtv-commit` (commits a chosen set of files in one step). A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [cli-preview](cli-preview/cli-preview.md) | How to invoke `cli-preview`, the review folder it reads and what its validation does not prove | Change or run the tool without breaking a review folder | changing, reviewing or debugging a file under `cli-preview/`, or writing a review folder for it |
| [rbtv-commit](rbtv-commit/rbtv-commit.md) | What the tool is, the commit procedure around it, its error table and conflict steps, and its maintenance facts | Change or run the tool without breaking the procedure that calls it | editing, reviewing or testing `rbtv-commit/commit.py`, its record or its tests, or committing with the tool |
| [Building a command-line interface](../methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `cli-preview` or `rbtv-commit` |

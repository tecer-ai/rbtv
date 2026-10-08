# Tools of the coordinate component

This folder holds the tools of the `coordinate` component: `digest`. A tool's folder holds its program, its record, its tests and data, its page and, when it needs more than one page, `documentation/`. Prose methods live in `../methods/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [digest](digest/digest.md) | What the `digest` tool is, the files and line layout its verbs share, and its maintenance facts | Change or check the program without breaking the method pages that call it | editing, reviewing or testing `digest/digest.py` or its record |
| [Running a digest](../methods/digest/run.md) | The method that calls `inspect`, `slice`, `adjust` and `check`: inputs, run folder, the waves and the boundary-review task text | Keep each verb's invocation and result aligned with the step that uses it | changing a verb, an option or a result field of `inspect`, `slice`, `adjust` or `check` |
| [Digest: reconcile](../methods/digest/reconcile.md) | The reconcile mode's extraction and grouping task texts, the question-block form and the `merge-answers` step | Keep `check` and `merge-answers` aligned with the files this mode writes | changing what `check` counts as a finding, or what `merge-answers` reads or writes |
| [Digest: study](../methods/digest/study.md) | The study mode's extraction and grouping task texts | Keep `check` aligned with the study extraction layout | changing what `check` counts as a finding |
| [Building a command-line interface](../../../code/capabilities/methods/building-a-cli.md) | The method for designing, building and testing a command-line interface | Keep a tool's verbs, help, output and failures usable by a person and an agent | adding a tool here, or changing a tool's verbs, help, output or exit statuses |

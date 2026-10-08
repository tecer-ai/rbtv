# digest

`digest` performs the exact steps of [Digest](../../methods/digest.md): it measures a long source, cuts it into line-numbered chunks, computes chunk boundaries from boundary reviews, checks the extraction files and merges answers into a questions file. [Running a digest](../../methods/digest/run.md) and the two mode pages, [Digest: reconcile](../../methods/digest/reconcile.md) and [Digest: study](../../methods/digest/study.md), name when to run each verb. `digest -h` and `digest VERB -h` are the interface reference.

## What the verbs share

`slice` writes `manifest.json` beside the chunk files: `source`, `total_lines` and `chunks`, which maps each `chunk-NN` to its first and last source line. `adjust` and `check` read that file, so their `--chunks` folder must be one that `slice` wrote.

`adjust` and `check` do not parse YAML. They read a key only at the start of a line (`end_clean:`, `suggest_end_at:`, `source:`), and `check` counts a finding per line that starts with two spaces and `- decision:` or `- kind:`. The task texts in the method pages fix that layout; change the task text and these patterns together.

The tool writes only where its arguments say: the `--out` folder of `slice`, and the questions file or `--out` file of `merge-answers`. It keeps no state of its own.

## Maintenance

The program is one file, `digest.py`, using the Python 3 standard library only. Each verb's help is the docstring of the function that implements it. The chunk-size numbers (30,000, 45,000 and 60,000 characters) are the constants at the top of the program; `inspect`'s help and the "Plan and confirm" section of Running a digest state them, so change all three together.

The program has no test file. After a change, run each verb from another folder with a known input, a missing input and an invalid input, as [Tool](../../../../../core/rbtv/capabilities/glossary/tool.md) specifies, and follow [Building a command-line interface](../../../../code/capabilities/methods/building-a-cli.md) for a change to its verbs, help or output.

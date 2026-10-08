# Digest

A digest turns a source too long to read directly (a transcript, a log, a long document) into one result, while sub-agents read the source and you never do. The `digest` tool does the exact steps (measuring, cutting into line-numbered chunks, computing clean chunk boundaries, checking the extraction files, merging answers); the sub-agents do the reading and the extraction; you read the one page that comes out and the documents it changes.

A digest is the wrong block when the source fits your context: read it. `digest inspect SOURCE` prints `total_lines`; at or below 100 lines, the source is short enough to read, and the tool page says so.

## The two modes

| Mode | Result | Inputs that distinguish it |
|---|---|---|
| **reconcile** | Target documents overwritten in place so that they reflect the decisions the source made, with the user's line comments authoritative over any source finding | one or more target documents; optional line comments, decision criteria, taxonomy |
| **study** | A new study note written from the source, organized by theme | the destination path; optional focus questions, taxonomy |

The task names the mode, or you ask the user for it. The full inputs table, with what is required per mode and the action on a missing input, is the Inputs section of [Running a digest](digest/run.md).

## What you read, and what you never open

You read the context references (smaller material the task allows you to read), the target documents, the user's comments and, at the end of extraction, `extractions/grouping.yaml`: the one page the later steps use. You do not open a source file, a chunk file, a boundary review or an extraction file; the tool reports on them (`inspect`, `slice`, `adjust`, `check`), and the sub-agents read them. Opening one chunk "to see" puts the source in your context, which is what the digest exists to avoid.

## How the run is shaped

A digest is a [swarm](swarm.md) over the chunks, with the tool between the waves:

1. **Measure and plan**: `digest inspect` gives the chunk size and count per source. The plan you show the user before launching (coordinate skill, rule 1) is: per source the total lines, chunk size and chunk count; the three waves below; and the `cast route` verdict for each.
2. **Slice and review boundaries**: `digest slice` cuts the source; one cheap sub-agent per chunk says whether its chunk starts and ends on a clean exchange; `digest adjust` computes the final breaks from those reviews; `digest slice` again with those breaks.
3. **Extract**: one sub-agent per chunk writes an extraction file with the mode's task text (decisions, or themes and concepts); `digest check` confirms one well-formed extraction per chunk and counts findings.
4. **Group**: one stronger sub-agent reads all the extraction files and writes `grouping.yaml`. You read it.
5. **Write**: the mode page's steps turn the grouping into the result: reconcile asks you the open questions the source left (with `digest merge-answers` folding the user's answers into the questions file) and then overwrites the targets; study writes the note.

| Wave | Route call |
|---|---|
| Boundary review | `cast route --access bounded --type text --class mechanical --optimize price` |
| Extraction | `--class bounded --optimize price` |
| Grouping | `--class broad --optimize quality` |

Every run fact lives in the run folder's `manifest.json` under `.rbtv/runtime/coordinate/digest/<run-id>/`, so a failed or partial run resumes from its folder rather than starting over; the Start point table of Running a digest says where to resume.

## Where the steps are

| Page | CONTAINS | ALWAYS LOAD WHEN |
|---|---|---|
| [Running a digest](digest/run.md) | The inputs table, the run folder layout, the exact invocation of each verb at its step, the boundary-review task text, and the finish and cleanup | you are about to start or resume a digest |
| [Digest: reconcile](digest/reconcile.md) | The reconcile mode's extraction and grouping task texts, the open-questions step and the write | the run reaches the Group step in reconcile mode |
| [Digest: study](digest/study.md) | The study mode's extraction and grouping task texts and the write | the run reaches the Group step in study mode |
| [digest](../tools/digest/digest.md) | What the tool's verbs share, the layout the task texts fix, and its maintenance facts | changing or checking the tool, or a verb's result surprises you |

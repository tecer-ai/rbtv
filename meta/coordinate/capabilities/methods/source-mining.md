# Source mining

Mine a source too long to read directly into one result: a target document reconciled with the decisions the source made (reconcile mode), or a study note (study mode). Sub-agents read the source; the manager never does.

Read [Delegating work](delegating-work.md) before applying this page if it has not already been read for this task. It owns staffing, launch mechanics, report requirements and the small-scope test. This page chunks the source and runs a swarm over the chunks, so [Swarm](swarm.md) applies to the extraction wave.

The manager reads context references, target documents, the user's comments and `grouping.yaml`. It does not open a source file, a chunk file, a boundary review or an extraction file; the `source-mining` tool reports on them.

## Start point

| Situation | Start at |
|---|---|
| New run | Inputs, below |
| The task names an existing run folder whose questions file carries every `- Answer:` line | The Write section of the mode's page |
| The task names a run folder and answers not yet merged | Merge the answers as that page's Ask section says, then start at its Write section |

## Inputs

Ask the user for the mode. If the task already names it, use it.

| Input | Reconcile | Study | Notes |
|---|---|---|---|
| Source files | 0..N | 1..N | Paths. Large files the manager must not read |
| Context references | 0..N | 0..N | Paths or URLs of smaller material the manager may read |
| Target documents | 1..N | none | Documents to overwrite in place |
| Study destination | none | required | Path of the new study note |
| User line-comments | optional, recommended | none | One per line: `Line N: text`. Authoritative; a source finding never overrides one |
| Decision criteria | optional | none | One sentence defining "decision" for the domain |
| Focus questions | none | optional | What extraction looks for |
| Taxonomy | optional | optional | Comma-separated topics (reconcile) or themes (study). Without one, sub-agents use free-form kebab-case labels, and quality can drop |

A missing required input: stop and name it. Check each source path exists and that `source-mining inspect SOURCE` reports `total_lines` above 100; at or below 100, tell the user the source is short enough to read directly and ask whether to continue.

## Run folder

Create the run folder `.rbtv/runtime/sub-agents/source-mining/<run-id>/` from the installation root; it is this component's [runtime folder](../../../../core/rbtv/capabilities/glossary/runtime.md), not a folder beside the source or the targets. `run-id` is `<YYYY-MM-DD-HHMM>-<slug>` and the slug is the first source's file name in lowercase kebab-case, at most 30 characters. On a collision append `-2`, `-3`. Write `manifest.json` there with these fields, and keep every run fact in it: `run_id`, `mode`, `started_at`, `inputs` (`sources`, `contexts`, `targets`, `study_destination`, `comments` verbatim, `taxonomy`, `decision_criteria`, `focus_questions`), `boundaries` (per source: `naive` and `final` break lists). Update it when a step changes a field.

| Path | Contents |
|---|---|
| `chunks-naive/<source>/` | First slice; deleted after the boundary pass |
| `boundaries/<source>/` | One boundary review per chunk |
| `chunks/<source>/` | Final chunks |
| `extractions/<source>/` | One extraction per chunk |
| `extractions/grouping.yaml` | Grouping result |
| `synthesis/` | Drafts and the questions file |

## Plan and confirm

Run `source-mining inspect SOURCE` for each source. It prints `chunk_lines` (lines per chunk for about 30,000 characters per chunk; the whole source when under 45,000 characters, two chunks under 60,000), `chunks`, and one `bucket FIRST-LAST chars N avg N` line per 100 source lines. Use `chunk_lines`. When the `bucket` lines show a region much denser than the rest, use `chunk_lines_dense` instead, which bounds the largest chunk, and tell the user why.

Per [Swarm](swarm.md)'s quick interview, propose one plan and get one confirmation: per source the total lines, chunk size, chunk count; the three waves below; and the `cast route` verdict for each. Skip the confirmation only when the user has said to proceed without confirming. If no user can answer, stop and report the plan as the missing confirmation.

| Wave | Route call |
|---|---|
| Boundary review | `--class mechanical --optimize price` |
| Extraction | `--class bounded --optimize price` |
| Grouping | `--class broad --optimize quality` |

## Slice and review boundaries

1. Slice each source: `source-mining slice SOURCE --out <run>/chunks-naive/<source> --size <chunk_lines>`. Prints `chunks` and one `chunk-NN FIRST-LAST` line per chunk. A non-UTF-8 source fails; ask the user for its encoding and add `--encoding`.
2. A source with one chunk has no boundary to review: copy `chunks-naive/<source>` to `chunks/<source>` and go to Extract.
3. Otherwise launch one boundary-review task per chunk, in parallel, with the template below. Each writes `boundaries/<source>/chunk-NN.yaml`.
4. Run `source-mining adjust --chunks <run>/chunks-naive/<source> --boundaries <run>/boundaries/<source>`. It prints `breaks` and one `boundary ORIGINAL ADJUSTED REASON` row per boundary. On a nonzero exit it names the review whose suggestion is not a line of its chunk, or the chunk two reviews leave empty: re-run that boundary review, then `adjust`. Record both lists in `manifest.json`, show the user the changed rows, then run `source-mining slice SOURCE --out <run>/chunks/<source> --breaks <breaks>` and delete `chunks-naive/`.

Boundary-review task, one per chunk. The first lines are the same for every chunk; only Scope differs:

```markdown
Decide whether the chunk named in Scope starts and ends on clean discussion boundaries. Do not extract decisions, summarize or analyze topics.

Clean start: the first substantive line begins a new exchange or thought. Not clean: a response with no visible question, a mid-sentence continuation, a mid-list-item, a "yes" or "no" without context.
Clean end: the last substantive line completes the current exchange. Not clean: a dangling question with no answer, a mid-sentence cutoff, a list started but not closed.
When the start is not clean, scan forward in the chunk to the first line where a new exchange cleanly begins and give it as `suggest_start_at`. When the end is not clean, scan backward to the last line where the prior exchange cleanly ended and give it as `suggest_end_at`. Give source line numbers, which prefix each line.

## Scope

Examine: `{chunk_path}` (source `{source}`, chunk {N}, source lines {START}-{END}); no neighbor chunk, no other file.
May change: `{output_path}` (create it).

## Done contract

`{output_path}` is strict YAML with no prose:

source: {source}
chunk: {N}
line_range: [{START}, {END}]
start_clean: true | false
end_clean: true | false
suggest_start_at: <source line number or null>
suggest_end_at: <source line number or null>
reason_start: <one sentence, only when start_clean is false>
reason_end: <one sentence, only when end_clean is false>

Every suggested line lies inside the chunk's line range. If the chunk cannot be read, stop and report that.
```

## Extract

Launch one extraction task per chunk of `chunks/<source>/`, in parallel, using the task text of the mode's page. Each writes `extractions/<source>/chunk-NN.yaml`. The tasks are a swarm base wave: one chunk, a named read-set, one-page output.

Run `source-mining check --chunks <run>/chunks/<source> --extractions <run>/extractions/<source>`. It prints `total_findings` and one line per chunk. On a nonzero exit it names the chunks that are missing or malformed (re-run only those) or reports no findings in any chunk (the task text failed: stop and report it to the user rather than continuing).

## Group

Launch one grouping task over all `extractions/<source>/chunk-*.yaml` files, using the mode's task text. It examines only those YAML files, never a source or chunk, and writes `extractions/grouping.yaml`. Read `grouping.yaml` yourself; it is the one page the later steps use. Then continue at the mode's page:

| Mode | Page |
|---|---|
| reconcile | [Source mining: reconcile](source-mining-reconcile.md) |
| study | [Source mining: study](source-mining-study.md) |

## Finish

After the mode page's Write section succeeds, report to the user: mode, run id, the files written or overwritten, and the total source lines processed. Then delete the run folder, and delete `.rbtv/runtime/sub-agents/source-mining/` if it is empty. A failed or partial write keeps the run folder, because a resume needs its `manifest.json` and `synthesis/` files.

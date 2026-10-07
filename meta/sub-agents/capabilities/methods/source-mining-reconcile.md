# Source mining: reconcile

Update the target documents so they reflect the decisions in the source and the user's line-comments. Continue from the run folder that [Source mining](source-mining.md) prepared, with extraction finished and `extractions/grouping.yaml` written, or start at Write for a run whose questions are answered. `<run>` is the run folder.

## Task text for extraction and grouping

Extraction task, one per chunk. Fill `{taxonomy_text}` with the taxonomy or `free-form (use any short kebab-case label)`, and add the user's decision criteria after the definitions when given:

```markdown
Extract every decision about the subject matter from the chunk named in Scope.

Decision: an explicit user statement of intent ("I want X", "we should do X"), an agent statement the user confirmed, or a user correction ("no, X not Y"). Not a decision: hypotheticals ("could", "maybe", "what if"), rejected ideas, abandoned threads, transcription self-corrections (use the final version only).
Tag each decision with a topic. Allowed topics: {taxonomy_text}.
Do not summarize the chunk, recommend or judge. Cite a source line number for every finding; a finding without one is invalid. With no decisions, write `findings: []`.

## Scope

Examine: `{chunk_path}` (source `{source}`, chunk {N}, source lines {START}-{END}); no other file. If you need an external context source, name that need in `cross_chunk_flags`; do not fetch it.
May change: `{output_path}` (create it).

## Done contract

`{output_path}` is strict YAML with no prose:

source: {source}
chunk: {N}
line_range: [{START}, {END}]
findings:
  - decision: <verbatim or close paraphrase>
    line: <source line number>
    topic: <topic>
    status: confirmed | superseded | speculation | rejected
    superseded_by_line: <number or null; only if visible within this chunk>
    notes: <optional, one sentence>
cross_chunk_flags:
  - <line ranges or topics that reference content outside this chunk>
```

Grouping task, one over all chunks:

```markdown
Reconcile the structured findings in the files named in Scope. Do not read the source or any chunk.

1. Group findings across all chunks and sources by `topic`.
2. Within a topic, sort by `line` ascending.
3. Apply chronological override mechanically: a later finding overrides an earlier one only when they directly contradict on the same specific point. Mark the overridden one `final_status: superseded` with a pointer to the overriding line.
4. List contradictions under `contradictions`; never resolve them silently.
5. List findings tagged `speculation`, and unresolved ones, under `open_threads`.
Two decisions on one topic that do not directly contradict stay as separate `final_decisions`. Make no judgment beyond the mechanical override.

## Scope

Examine: `<run>/extractions/<source>/chunk-*.yaml` for every source.
May change: `<run>/extractions/grouping.yaml` (create it).

## Done contract

`<run>/extractions/grouping.yaml` is strict YAML with no prose:

mode: reconcile
topics:
  - topic: <name>
    final_decisions:
      - decision: <text>
        line: <number>
        source: <source>
        final_status: confirmed | superseded
        superseded_by: <line or null>
    contradictions:
      - earlier: {decision: <text>, line: <number>, source: <source>}
        later: {decision: <text>, line: <number>, source: <source>}
        nature: <one sentence>
    open_threads:
      - {decision: <text>, line: <number>, source: <source>, why_open: <one sentence>}

It is non-empty when the extractions held findings.
```

## Synthesize

Read `manifest.json`, `grouping.yaml`, every target document, every context reference and the user's comments. For a URL, use the harness's web tool. Write `<run>/synthesis/delta-draft.md` as `### Change` blocks:

```markdown
### Change: <one-line summary>
- Source: user-comment line N | context alignment (<ref-name>) | extraction (<source> line N)
- Before: <quote>
- After: <quote>
- Rationale: <one sentence>
```

1. For each user comment, find the line it references in its target and write the proposed change.
2. For each context reference, find schema, concept and naming divergences from the target and write a change per divergence.
3. For each `final_decision` in `grouping.yaml` that adds to a target, write a change. A decision that overrides existing content waits for a resolved open question.

## Ask

Write `<run>/synthesis/open-questions.md` with one `### Q{N}` block per trigger:

| Trigger | Question |
|---|---|
| A user comment is itself a question | The comment verbatim |
| A `grouping.yaml` contradiction | "<earlier> vs <later> — pick one or both?" |
| An extraction directly contradicts a user comment | "User comment says X; extraction line N says Y — which?" |
| A context divergence the extraction does not justify | "Target says X; context says Y — keep, switch, or revise both?" |
| An extraction adds a concept the user has not opined on | "Add this? <text>" |

```markdown
### Q{N}: <one-line summary>
- Source: <user-comment line N / contradiction / divergence>
- Context: <relevant lines or quotes>
- Options:
  - A) <option text>
  - B) <option text>
- Recommendation: <A | B | "no user signal — your call">
- Rationale: user-comment line N: "<verbatim phrase>" | prior decision at extraction line N: "<verbatim phrase>" | no user signal — tradeoffs: A=<one line>, B=<one line>
```

Recommend by the first row that holds:

| Signal | Action |
|---|---|
| A user comment states an explicit preference | Recommend the matching option and cite the comment line |
| A user comment states a partial preference or direction | Recommend the option aligned with that direction, even if another is better engineered, and cite the comment line |
| A prior decision in `grouping.yaml` constrains the answer | Recommend the consistent option and cite the extraction line |
| None of these | Recommend nothing; write `no user signal — your call` and one line of tradeoff per option |

A recommendation based on general best practice, one that is more structured than the user's comment asked for, or one that changes the comment's shape ("keep it simple" answered with "delete the section") fails this table: demote it to `no user signal`. A user's question surfaces a design choice; it is not a request for the best answer.

With a user present, print the question count and the first two questions, name the questions file, and wait. Accept answers in any order and present two more at a time until none are left. Append each answer to the file as `- Answer: <response>`. Start Write only when every question has an answer. A user choosing to proceed without confirmations never skips this step.

With no user present, stop after writing the file. Report the run folder, `open-questions.md` and the question count, and ask the caller to supply a JSON object mapping `Q<N>` to answer text. On a later task that supplies it, run `source-mining merge-answers --questions <run>/synthesis/open-questions.md --answers ANSWERS_JSON --in-place` and start at Write. A nonzero exit wrote nothing and names the unmatched, already answered or unanswered keys.

## Write

Needs `manifest.json`, `synthesis/delta-draft.md` and `synthesis/open-questions.md` with every answer.

1. For each answered question, add a `### Change` block to `delta-draft.md` with the answer as Source.
2. Apply every `### Change` block to its target and overwrite the target in place; the earlier version is the version-control record.
3. Count the applied blocks (not considered-and-unchanged items) and the targets modified. At 3 or more applied changes, or more than one target, write the delta file: `delta-draft.md` to `<target-dir>/<target-name>-delta.md`, or to the output location the installation's instructions set. Otherwise write no delta file and put the change summary and any "considered, no change" notes in the final report.
4. Continue at Finish in [Source mining](source-mining.md#finish); the delta files line of the report lists the delta file or `none`.

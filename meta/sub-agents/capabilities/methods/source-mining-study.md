# Source mining: study

Produce a study note from the source. Continue from the run folder that [Source mining](source-mining.md) prepared, with extraction finished and `extractions/grouping.yaml` written, or start at Write for a run whose reflection prompts are answered. `<run>` is the run folder.

## Task text for extraction and grouping

Extraction task, one per chunk. Fill `{taxonomy_text}` with the theme taxonomy or `free-form (use any short kebab-case label)`, and add `Pay particular attention to: {focus_questions}` after the definitions when given:

```markdown
Extract every concept, claim and open question the source raises in the chunk named in Scope.

Concept: a defined idea, entity, framework, technique or pattern named in the source. Claim: an assertion, factual, predictive or normative, that the source makes or quotes. Open question: a question the source raises and does not resolve, or a tension between concepts or claims.
Tag each finding with a theme. Allowed themes: {taxonomy_text}.
Do not recommend or judge, and skip trivial mentions. Cite a source line number for every finding; a finding without one is invalid. With no findings, write `findings: []`.

## Scope

Examine: `{chunk_path}` (source `{source}`, chunk {N}, source lines {START}-{END}); no other file.
May change: `{output_path}` (create it).

## Done contract

`{output_path}` is strict YAML with no prose:

source: {source}
chunk: {N}
line_range: [{START}, {END}]
findings:
  - kind: concept | claim | open_question
    text: <verbatim or close paraphrase>
    line: <source line number>
    theme: <theme>
    supporting_lines: [<related line numbers within this chunk, optional>]
    notes: <optional, one sentence>
cross_chunk_flags:
  - <line ranges or themes that reference content outside this chunk>
```

Grouping task, one over all chunks:

```markdown
Cluster the structured findings in the files named in Scope for study. Do not read the source or any chunk.

1. Group findings across all chunks and sources by `theme`.
2. Within a theme, separate them by `kind`.
3. Identify tensions: claims that appear to contradict, concepts that appear to overlap, open questions that connect to specific claims.
4. Identify through-lines: concepts or claims that recur across the source, which are likely central.
Do not judge which claim is right.

## Scope

Examine: `<run>/extractions/<source>/chunk-*.yaml` for every source.
May change: `<run>/extractions/grouping.yaml` (create it).

## Done contract

`<run>/extractions/grouping.yaml` is strict YAML with no prose:

mode: study
themes:
  - theme: <name>
    concepts: [{text: <text>, line: <number>, source: <source>, supporting_lines: [<numbers>]}]
    claims: [{text: <text>, line: <number>, source: <source>}]
    open_questions: [{text: <text>, line: <number>, source: <source>}]
    tensions:
      - between: [{line: <number>, text: <text>}, {line: <number>, text: <text>}]
        nature: <one sentence>
through_lines:
  - {text: <central concept or claim>, occurrences: [<line numbers>], source: <source>}

It is non-empty when the extractions held findings.
```

## Synthesize

Read `manifest.json`, `grouping.yaml` and every context reference (for a URL, use the harness's web tool). Write `<run>/synthesis/study-draft.md`:

```markdown
# <title derived from the primary source's file name>

## Through-lines
- <each through-line>

## Themes
### <theme name>
- Key concepts: <list with line references>
- Key claims: <list with line references>
- Open questions: <list with line references>
- Tensions: <list>
```

## Ask

Write `<run>/synthesis/reflection-prompts.md` in the question-block form of [Source mining: reconcile](source-mining-reconcile.md#ask) (`### Q{N}` with Source, Context, Options, Recommendation, Rationale), one block per trigger:

| Trigger | Prompt |
|---|---|
| Several competing through-lines | "Which through-line is most central to your study? <list>" |
| A tension worth deepening | "Tension between line N and line M — which side resonates with your existing understanding?" |
| A theme with many open questions | "Theme '<X>' has <N> open questions — which 1-2 do you want to pursue?" |
| A context reference adds a frame | "Context '<ref>' frames this as <Y>. Adopt, reject, or note as alternative?" |

Present, wait, record and hand back exactly as the Ask section of that page says, with `reflection-prompts.md` as the questions file. Start Write only when every prompt has an answer.

## Write

Needs `manifest.json`, `synthesis/study-draft.md` and `synthesis/reflection-prompts.md` with every answer.

1. Integrate each answer into `study-draft.md`: reorder sections, expand the chosen tensions, drop deprioritized themes.
2. Write `study-draft.md` to `inputs.study_destination` as a new file.
3. Continue at Finish in [Source mining](source-mining.md#finish); the report names the study note.

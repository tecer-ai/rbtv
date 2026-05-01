---
name: step-03-extract
description: Dispatch one Opus sub-agent per chunk to extract decisions (reconcile) or concepts (study)
nextStepFile: ./step-04-group.md
workflowFile: ./workflow.md
---

# Step 3: Extract

**Progress: Step 3 of 6** — Next: Group

---

## STEP GOAL

Run Opus extraction on every adjusted chunk across all sources. Sub-agent prompt branches on mode.

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER read any chunk file directly
- 📖 ALWAYS dispatch one sub-agent per chunk in parallel where possible
- 🔍 ALWAYS use Opus model for this pass
- ✏️ Sub-agents return strict YAML — no prose around it

---

## MANDATORY SEQUENCE

### 1. Read Manifest

Read `<runtime_root>/manifest.json`. Note `mode`, `inputs.taxonomy`, `inputs.decision_criteria`, `inputs.focus_questions`.

### 2. Dispatch One Opus Sub-agent Per Chunk (parallel)

For each `chunk-{NN}.txt` under `<runtime_root>/chunks/<source-basename>/`, pick the prompt for the active mode.

#### Reconcile mode prompt

Substitute `{N}`, `{START}`, `{END}`, `{chunk_path}`, `{source_basename}`, `{taxonomy_text}`, `{decision_criteria_text}`:

> You are reviewing chunk {N} of source `{source_basename}`, covering source lines {START}-{END}. The chunk file at `{chunk_path}` is line-numbered.
>
> Invoke the `rbtv-web-searching` skill before any web fetch and follow it exactly if you need to consult an external context source.
>
> TASK: Extract every DECISION about the subject matter. Definitions:
> - DECISION = explicit user statement of intent ("I want X", "we should do X"), agent statement the user confirmed, OR user correction ("no, X not Y").
> - NOT a decision: hypotheticals ("could", "maybe", "what if"), rejected ideas, abandoned threads, transcription self-corrections (use FINAL version only).
>
> {decision_criteria_text — only if user provided custom criteria}
>
> Tag each decision with a TOPIC. Allowed topics: {taxonomy_text — comma-separated list, OR "free-form (use any short kebab-case label)"}.
>
> OUTPUT FORMAT (strict YAML):
>
> ```yaml
> source: <source_basename>
> chunk: {N}
> line_range: [{START}, {END}]
> findings:
>   - decision: <verbatim or close paraphrase>
>     line: <source line number>
>     topic: <topic from taxonomy or free-form>
>     status: confirmed | superseded | speculation | rejected
>     superseded_by_line: <number or null — only if visible WITHIN this chunk>
>     notes: <optional, ≤1 sentence>
> cross_chunk_flags:
>   - <line ranges or topics that reference content outside this chunk>
> ```
>
> CONSTRAINTS:
> - DO NOT summarize the chunk
> - DO NOT make recommendations or judgments
> - Cite source line numbers; no number → invalid finding
> - If you find ZERO decisions, output `findings: []`
> - Read ONLY your assigned chunk

#### Study mode prompt

Substitute as above plus `{focus_questions_text}`:

> You are reviewing chunk {N} of source `{source_basename}`, covering source lines {START}-{END}. The chunk file at `{chunk_path}` is line-numbered.
>
> TASK: Extract every CONCEPT, CLAIM, or OPEN QUESTION the source raises. Definitions:
> - CONCEPT = a defined idea, entity, framework, technique, or pattern named in the source.
> - CLAIM = a stated assertion (factual, predictive, or normative) the source makes or quotes.
> - OPEN QUESTION = a question the source raises but does not resolve, OR a tension between concepts/claims.
>
> {focus_questions_text — only if user provided focus questions: prefix "Pay particular attention to: ..."}
>
> Tag each finding with a THEME. Allowed themes: {taxonomy_text or "free-form (use any short kebab-case label)"}.
>
> OUTPUT FORMAT (strict YAML):
>
> ```yaml
> source: <source_basename>
> chunk: {N}
> line_range: [{START}, {END}]
> findings:
>   - kind: concept | claim | open_question
>     text: <verbatim or close paraphrase>
>     line: <source line number>
>     theme: <theme>
>     supporting_lines: [<related line numbers within this chunk, optional>]
>     notes: <optional, ≤1 sentence>
> cross_chunk_flags:
>   - <line ranges or themes that reference content outside this chunk>
> ```
>
> CONSTRAINTS:
> - DO NOT make recommendations or judgments
> - DO NOT extract trivial mentions — only genuine concepts/claims/questions
> - Cite source line numbers; no number → invalid finding
> - If you find ZERO findings, output `findings: []`
> - Read ONLY your assigned chunk

### 3. Save Outputs

Save each sub-agent's YAML to `<runtime_root>/extractions/<source-basename>/chunk-{NN}.yaml`.

### 4. Summary

Print one-line per chunk: count of findings by topic/theme.

### 5. Step Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 04 — group |
| **[R] Re-run** | Re-dispatch any chunks that failed or returned empty unexpectedly |
| **[X] Exit** | Abort; offer cleanup |

HALT and WAIT.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Update `manifest.json`: append `step-03-extract` to `completed_steps`; set `current_step = "step-04-group"`.
2. Load `./step-04-group.md` and follow its instructions.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Every chunk has a valid YAML in `extractions/`. Total finding count > 0.

❌ **FAILURE:** Any chunk missing output, malformed YAML, or returning suspicious zero-finding patterns across all chunks (suggests prompt failure).

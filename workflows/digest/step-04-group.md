---
name: step-04-group
description: Reconcile mode — chronological override; Study mode — thematic clustering
nextStepFile: ./step-05-synthesize.md
workflowFile: ./workflow.md
---

# Step 4: Group

**Progress: Step 4 of 6** — Next: Synthesize

---

## STEP GOAL

Mode-branched grouping of extracted findings. Reconcile applies chronological override; Study clusters by theme and surfaces tensions.

---

## MANDATORY EXECUTION RULES

- 🛑 SUB-AGENT MUST NOT read source files
- 📖 SUB-AGENT INPUT: only the YAML files from step-03
- 🔍 USE OPUS MODEL

---

## MANDATORY SEQUENCE

### 1. Read Manifest

Read `<runtime_root>/manifest.json`. Note `mode`.

### 2. Dispatch ONE Opus Sub-agent

#### Reconcile mode prompt

> You are reconciling structured findings from a conversation. You will NOT read the conversation itself — only the YAML outputs from chunk extractors at `<runtime_root>/extractions/<source-basename>/chunk-*.yaml`.
>
> INPUT: all `extractions/<source>/chunk-*.yaml` files. Read each one.
>
> TASK:
> 1. Group findings across all chunks and all sources by `topic`.
> 2. Within each topic, sort findings by `line` ascending.
> 3. Apply chronological override MECHANICALLY: a later finding overrides an earlier finding ONLY if they directly contradict on the same specific point. Mark overridden findings with `final_status: superseded` and a pointer to the overriding line.
> 4. Surface contradictions explicitly under `contradictions` — DO NOT silently resolve.
> 5. Items tagged `speculation` or unresolved → list under `open_threads`.
>
> OUTPUT FORMAT:
>
> ```yaml
> mode: reconcile
> topics:
>   - topic: <name>
>     final_decisions:
>       - decision: <text>
>         line: <number>
>         source: <source_basename>
>         final_status: confirmed | superseded
>         superseded_by: <line or null>
>     contradictions:
>       - earlier:
>           decision: <text>
>           line: <number>
>           source: <source_basename>
>         later:
>           decision: <text>
>           line: <number>
>           source: <source_basename>
>         nature: <one sentence>
>     open_threads:
>       - decision: <text>
>         line: <number>
>         source: <source_basename>
>         why_open: <one sentence>
> ```
>
> CONSTRAINTS:
> - DO NOT make judgment calls beyond mechanical chronological-override
> - If two decisions on the same topic are NOT direct contradictions, keep BOTH as separate `final_decisions`
> - DO NOT read source files

#### Study mode prompt

> You are clustering structured findings from a long source for study. You will NOT read the source itself — only the YAML outputs from chunk extractors at `<runtime_root>/extractions/<source-basename>/chunk-*.yaml`.
>
> INPUT: all `extractions/<source>/chunk-*.yaml` files.
>
> TASK:
> 1. Group findings across all chunks and all sources by `theme`.
> 2. Within each theme, separate by `kind` (concept, claim, open_question).
> 3. Identify TENSIONS: claims that appear to contradict, concepts that appear to overlap, or open questions that connect to specific claims.
> 4. Identify THROUGH-LINES: concepts or claims that recur across the source — these are likely central.
>
> OUTPUT FORMAT:
>
> ```yaml
> mode: study
> themes:
>   - theme: <name>
>     concepts:
>       - text: <text>
>         line: <number>
>         source: <source_basename>
>         supporting_lines: [<numbers>]
>     claims:
>       - text: <text>
>         line: <number>
>         source: <source_basename>
>     open_questions:
>       - text: <text>
>         line: <number>
>         source: <source_basename>
>     tensions:
>       - between:
>           - line: <number>
>             text: <text>
>           - line: <number>
>             text: <text>
>         nature: <one sentence>
> through_lines:
>   - text: <central concept or claim>
>     occurrences: [<line numbers across the source>]
>     source: <source_basename>
> ```
>
> CONSTRAINTS:
> - DO NOT make judgment calls about which claim is "right"
> - DO NOT read source files

### 3. Save Output

Save to `<runtime_root>/extractions/grouping.yaml`.

### 4. Summary

Print: topics/themes count, total findings, contradictions count (reconcile) or tensions count (study), through_lines count (study).

### 5. Step Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 05 — synthesize |
| **[X] Exit** | Abort; offer cleanup |

HALT and WAIT.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Update `manifest.json`: append `step-04-group` to `completed_steps`; set `current_step = "step-05-synthesize"`.
2. Load `./step-05-synthesize.md` and follow its instructions.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** `grouping.yaml` exists with non-empty topics/themes.

❌ **FAILURE:** Sub-agent read source files instead of YAMLs; output empty when extraction had findings; malformed YAML.

---
name: step-02-slice-and-boundary
description: Slice source(s) into naive chunks, run Haiku boundary review, reslice with adjusted boundaries
nextStepFile: ./step-03-extract.md
workflowFile: ./workflow.md
---

# Step 2: Slice and Boundary Review

**Progress: Step 2 of 6** — Next: Extract

---

## STEP GOAL

Produce clean chunk boundaries for each source by running a Haiku boundary-detection pass before the (expensive) Opus extraction pass.

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER read any chunk file directly — only sub-agents read chunks
- 📖 ALWAYS run the slicer script via Bash — never inline-implement slicing
- 🔄 ALWAYS HALT for user approval of naive chunk size BEFORE the initial slice
- 🔄 ALWAYS HALT after presenting boundary diff for user approval before reslicing
- 🤖 USE HAIKU 4.5 for boundary review (`haiku-4-5-20251001`) — user explicitly authorized

---

## MANDATORY SEQUENCE

### 1. Inspect Source Density and Propose Naive Chunk Size — HALT for Approval

For each source listed in `manifest.json["inputs"]["sources"]`, run the slicer in inspect mode to get a per-100-line density histogram:

```bash
python "{rbtv_path}/workflows/digest/scripts/slice.py" \
  --source "<source-path>" \
  --inspect
```

The script prints `total_lines`, `total_chars`, and a markdown table with chars and avg chars/line per 100-line bucket. Use `--bucket N` if the default 100-line bucket is too coarse (very short source) or too fine (very long source).

Read the histogram and propose a chunk size per source.

**Target: ~30,000 chars per chunk** (≈ 7.5-10k tokens depending on language). Calibrated on observed extraction quality — larger chunks risk degraded recall mid-chunk; smaller chunks fragment cross-chunk reasoning.

**Compute lines per chunk:**

```
lines_per_chunk = round(30000 / avg_chars_per_line)
```

Use the overall mean (`total_chars / total_lines`) for uniform sources. For bimodal sources, use the higher-density region's avg (it bounds the worst case).

| Signal in histogram | Implication |
|--------------------|-------------|
| Uniform avg chars/line across buckets | Single uniform chunk size; use overall mean |
| Bimodal or wildly variable buckets | Use higher-density region's avg; flag bimodality to user |
| `total_chars < 45000` (≤ 1.5× target) | One chunk covering the whole source — do not slice |
| `total_chars < 60000` (≤ 2× target) | Two chunks; size = total_lines / 2 |

Examples:

| Source profile | avg chars/line | lines per chunk |
|----------------|----------------|-----------------|
| Sparse dialogue transcript | 50 | 600 |
| Mixed prose | 75 | 400 |
| Dense article / paper | 120 | 250 |

Present a table per source with: total lines, total chars, mean chars/line, suggested chunk size (lines), expected chunk count, one-line reason.

**YOLO bypass:** if `manifest["yolo"] == true`, skip the HALT and treat the suggested sizes as approved. Otherwise HALT:

| Option | Action |
|--------|--------|
| **[A] Approve** | Use suggested sizes |
| **[M] Modify** | User specifies size per source |
| **[X] Exit** | Abort run; offer cleanup |

WAIT for input. Record approved size per source for use in step 2.

### 2. Initial Slice (Naive)

For each source, using the approved size from step 1:

```bash
python "{rbtv_path}/workflows/digest/scripts/slice.py" \
  --source "<source-path>" \
  --out "<runtime_root>/chunks-naive/<source-basename>" \
  --size <approved-size>
```

If a source's encoding is not utf-8, the script fails. Re-run with `--encoding <encoding>` after asking the user.

After all sources are sliced, output structure:

```
<runtime_root>/chunks-naive/
  <source-basename-1>/
    chunk-00.txt
    chunk-01.txt
    ...
    manifest.json
  ...
```

### 3. Haiku Boundary Review (parallel)

For each chunk file across all sources, dispatch one Haiku 4.5 sub-agent in parallel.

Sub-agent prompt template (substitute `{N}`, `{START}`, `{END}`, `{chunk_path}`, `{source_basename}`):

> You are reviewing chunk {N} of source `{source_basename}`, covering source lines {START}-{END}. The chunk file at `{chunk_path}` is line-numbered (each line prefixed with its source line number followed by `: `).
>
> YOUR SOLE TASK: determine whether this chunk's start and end land on clean discussion boundaries. You will NOT extract decisions, summarize content, or analyze topics.
>
> CLEAN START: the first substantive line begins a new exchange or thought. NOT clean: response without visible question, mid-sentence continuation, mid-list-item, "Yes/No" without context.
>
> CLEAN END: the last substantive line completes the current exchange. NOT clean: dangling question with no answer, mid-sentence cutoff, list/bullet started but not closed.
>
> If start is NOT clean: scan forward in YOUR chunk to find the first line where a new exchange/thought CLEANLY begins. Suggest that line as `suggest_start_at`.
>
> If end is NOT clean: scan backward in YOUR chunk to find the last line where the prior exchange CLEANLY ended. Suggest that line as `suggest_end_at`.
>
> CONSTRAINTS:
> - You see ONLY this chunk. No neighbor visibility.
> - You may NOT read any other file.
> - Do NOT extract decisions or summarize.
> - All suggested line numbers must be source line numbers.
>
> OUTPUT FORMAT (strict YAML, no prose):
>
> ```yaml
> source: <source_basename>
> chunk: {N}
> line_range: [{START}, {END}]
> start_clean: <true | false>
> end_clean: <true | false>
> suggest_start_at: <source line number, or null>
> suggest_end_at: <source line number, or null>
> reason_start: <one sentence, only if start_clean is false>
> reason_end: <one sentence, only if end_clean is false>
> ```

Save each output to `<runtime_root>/boundaries/<source-basename>/chunk-{NN}.yaml`.

### 4. Compute Adjusted Boundaries

For each source, read all `<runtime_root>/boundaries/<source-basename>/chunk-*.yaml`. For each original boundary B between chunk-N and chunk-(N+1):

| Condition | New B |
|-----------|-------|
| chunk-N reports `end_clean: false` | `suggest_end_at` from chunk-N |
| Else if chunk-(N+1) reports `start_clean: false` | `suggest_start_at - 1` from chunk-(N+1) |
| Else | unchanged |

Print a summary table per source:

```
Source: <basename>
| Original | Adjusted | Reason |
|----------|----------|--------|
| 700      | 690      | chunk-00 end mid-list |
```

### 5. HALT for Approval

**YOLO bypass:** if `manifest["yolo"] == true`, skip the HALT and proceed with `[A] Approve` (reslice with adjusted boundaries). Otherwise:

| Option | Action |
|--------|--------|
| **[A] Approve** | Reslice with adjusted boundaries |
| **[O] Original** | Keep naive boundaries (skip reslice) |
| **[M] Modify** | User specifies custom boundaries |
| **[X] Exit** | Abort run; offer cleanup |

WAIT for input.

### 6. Reslice (after approval)

For each source:

```bash
python "{rbtv_path}/workflows/digest/scripts/slice.py" \
  --source "<source-path>" \
  --out "<runtime_root>/chunks/<source-basename>" \
  --breaks "<comma-separated adjusted boundaries>"
```

If [O] Original: copy `<runtime_root>/chunks-naive/<source-basename>/` to `<runtime_root>/chunks/<source-basename>/` (no reslice).

After reslice succeeds, delete `<runtime_root>/chunks-naive/`.

### 7. Update Manifest

```json
"boundaries": {
  "<source-basename>": {
    "naive": [<original boundaries>],
    "final": [<adjusted boundaries>]
  }
}
```

### 8. Step Menu

**YOLO bypass:** if `manifest["yolo"] == true`, skip this menu and auto-continue to Step 03. Otherwise:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 03 — extract |
| **[X] Exit** | Abort run; offer cleanup |

HALT and WAIT.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Update `manifest.json`: set `current_step = "step-03-extract"` and append `step-02-slice-and-boundary` to `completed_steps`.
2. Load `./step-03-extract.md` and follow its instructions.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All sources have adjusted chunks in `<runtime_root>/chunks/<source-basename>/`; boundaries logged in manifest.

❌ **FAILURE:** Slicer script errors not surfaced; Haiku output missing for any chunk; user approval skipped.

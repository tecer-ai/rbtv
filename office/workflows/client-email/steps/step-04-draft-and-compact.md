# Step 04 — Draft and Compact

Deliver one tight draft. Apply iterative compaction internally — the user sees a single version, not multiple visible passes.

## Order

1. **Draft.** Write the first pass applying the voice principles + tonal data loaded in step-02 and the strategic direction confirmed in step-03.

2. **Compact iteratively.** Run AT LEAST 2-3 passes, each with a distinct focus per `data/voice-principles.md` Iterative Compaction Technique table. For pt-BR, also apply the lens in `data/voice-pt-br.md` Técnica de Cortes Iterativos.

   **Compaction is about removing duplication and ceremony — NOT about telegraphic style.** Articles, prepositions, and connectives stay. Cuts target whole redundant phrases, restated content, format-defending justifications, and CTAs without targets. A reader should never lose meaning to compression.

3. **Verify register.** Read the draft once as the recipient would, with no knowledge of the agent's intent. Check:
   - Is the register calibrated to the relationship temperature with THIS specific recipient? (per `data/voice-pt-br.md` Calibração de Relação if pt-BR)
   - Does a 20-30 second skim convey the structural picture (greeting, frame, sections, ask)?
   - For each sentence: cut test — lose action, or just words?

4. **Deliver.** Present one draft AND always write it to a `.txt` file. Plain text — no markdown headers, no asterisks for bold, no backticks. Numbered lists use `1.`, `2.`, `3.`. Sub-items use a leading dash with two-space indent. Section labels are written as plain text followed by a blank line (e.g., `Para Carol`, not `**Para Carol**` or `## Para Carol`). The `.txt` format is the deliverable — Gmail paste-ready, no terminal copy artifacts, no markdown rendering surprises. Resolve the destination per `.claude/rules/rbtv-output-resolution.md` (default filename pattern: `YYYY-MM-DD-{topic}-email.txt` inside the recipient's `communications/` folder). Do NOT show multiple visible drafts.

5. **Hand off propagation.** After the user accepts the draft, surface the deltas captured in step-01 to the entity's collection CLAUDE.md propagation gate (`status.md` interaction log, `fit.md` updates if the draft surfaced new objections or quotes, etc.).

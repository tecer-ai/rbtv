---
name: meeting-summarizer
description: 'Process meeting transcripts and documents into structured summaries — classifies type, routes to correct folder, fixes filenames, and produces a type-specific or universal debrief. Loads glossary from workspace CLAUDE.md for transcription correction.'
---

# Meeting Summarizer

Process transcripts and documents into structured summaries with type-specific prompts, transcription validation, and glossary integration.

## When to Use

| Signal | Action |
|--------|--------|
| User provides a meeting transcript to summarize | Execute workflow |
| User says "summarize this meeting" / "resumir a reunião" / "meeting debrief" | Execute workflow |
| User references a transcript file and wants it processed | Execute workflow |
| User provides any document or content to summarize | Execute workflow (universal fallback) |

## Built-in Meeting Types

| Type | Prompt | Focus |
|------|--------|-------|
| Client | `client-summary-prompt.md` | Signal capture, opportunity analysis, commercial terms |
| Investor | `investor-summary-prompt.md` | Performance coaching, investor signals, founder prep |
| Internal | `internal-summary-prompt.md` | Alignment tracking, decision recording, strategic tensions |
| Product interview | `product-interview-summary-prompt.md` | Discovery synthesis, hypothesis validation, user reality |
| General / unclassified | `universal-prompt.md` | Three-layer analysis (signals, analysis, action) |

Workspaces can override any prompt by placing a `_summary-prompt.md` in the output folder.

## Execution

Read and execute `{rbtv_path}/workflows/summarization/workflow.md`.

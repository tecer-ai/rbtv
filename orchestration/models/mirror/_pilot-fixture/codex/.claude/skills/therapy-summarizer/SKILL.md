---
name: therapy-summarizer
description: 'Process therapy and psychiatry session transcripts into structured summaries. Handles transcription validation, glossary integration, anti-sanitization protocol, and axis mapping. Supports interactive and autonomous modes.'
---

# Therapy Summarizer

Process therapy and psychiatry session transcripts into structured, comprehensive documents with transcription validation and emotional fidelity.

## When to Use

| Signal | Action |
|--------|--------|
| User provides a therapy/psychiatry transcript | Route to therapy summarizer — interactive mode |
| User says "summarize the session" / "resumir a sessão" | Route to therapy summarizer — interactive mode |
| Sub-agent needs to create a `-resumo.md` for a therapy transcript | Pass therapy summarizer to sub-agent — autonomous mode |

## Execution

Read and execute `.user/workflows/therapy-summarizer/therapy-summarizer.md`.

When invoked as a sub-agent prompt, append: "Execute in **autonomous mode**."

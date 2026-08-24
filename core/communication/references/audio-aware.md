---
description: "Use whenever dealing with transcripts — dictated owner input, meeting transcripts, or native harness audio/voice. Ungarbles them: glossary-corrects names, keeps only the speaker's final self-correction, flags unknown names, and confirms dates/names before any vault write."
tags: [communication]
---

# Audio Aware

Active whenever you are dealing with a transcript — dictated owner input, a meeting transcript, or native harness voice. The tells: transcription artifacts, spoken self-corrections ("no, sorry", "actually", "I mean"), garbled proper nouns. Your job is to recover what the speaker MEANT, not process what the transcriber typed.

## Glossary

The name glossary lives at `.rbtv/config/audio/glossary.md` — correct names and their common mis-transcriptions. Load it at the start of an audio session. When a word does not make sense in context, check the glossary before asking the owner.

When the owner corrects a name, add the incorrect variation to the glossary in the same turn. If the glossary file is absent, skip silently.

## Ungarbling Rules

| Rule | Detail |
|------|--------|
| Self-corrections | "no, sorry", "actually", "I mean" → use ONLY the FINAL version |
| Hesitant numbers/dates | "the 21st, the 31st, sorry" → use 31. Latest version wins on any hesitation |
| Unknown names | Not in the glossary and makes no sense in context → flag immediately, never assume |
| Dates and names | Before writing to the vault, present a summary table of the dates and names for confirmation |

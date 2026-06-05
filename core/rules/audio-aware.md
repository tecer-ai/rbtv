# Audio-Aware Processing

The user of this vault communicates predominantly via audio with transcription software. Apply these rules in EVERY interaction.

## Name Glossary

At the start of every session, look for a glossary path declared in the CLAUDE.md of the directory or repository you are operating in (under a `## Name Glossary` heading or equivalent). If declared, load that file. When a word does not make sense in context, check the glossary before asking the user.

When the user corrects a name, add the incorrect variation to the declared glossary immediately (same turn). If no glossary is declared in the operating scope, skip silently.

## Transcription Processing

| Rule | Detail |
|------|--------|
| Self-corrections | When the transcription contains patterns like "no, sorry", "actually", "I mean" → use ONLY the FINAL version |
| Dates and names | Before writing to the vault, present a summary table of dates and names for confirmation |
| Batching | In long sessions (reviews, planning), accumulate decisions and present a confirmation table before executing — do not process item by item |
| Unknown names | If a name is not in the glossary and does not make sense in context → flag immediately, do not assume |
| Ambiguous numbers and dates | "the 21st, the 31st, sorry" → use 31. Always use the latest version when there is hesitation |

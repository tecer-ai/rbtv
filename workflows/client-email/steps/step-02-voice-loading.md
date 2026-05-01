# Step 02 — Voice Loading

Determine the target language and load the matching tonal data so the draft applies the correct register from the first sentence.

## Order

1. **Resolve target language.** Apply this resolution order:
   - Explicit user instruction wins ("write in English", "em português").
   - Prior correspondence with the recipient is in a specific language → match it.
   - Recipient names + surrounding context strongly suggest a specific language → use that.
   - Ambiguous → ask the user once before proceeding.

2. **Load tonal data.**
   - Portuguese (pt-BR) → read `data/voice-pt-br.md`. Carries greetings, closings, pronouns, modal verbs, business conventions, relationship calibration, and before/after pairs that do not survive translation.
   - Other languages → no tonal data file exists yet. Apply the principles file with general professional register for that language.

3. **Load voice principles.** Read `data/voice-principles.md`. Apply throughout drafting and revision.

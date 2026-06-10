---
name: 'step-01-init'
description: 'Capture the raw idea dump verbatim, enforce the no-solutions rule, create the sparring memo.'
nextStepFile: './step-02-break.md'
templateFile: '../templates/sparring-memo.md'
outputFile: '{output_folder}/idea-sparring-{idea-slug}-{date}.md'
---

# Step 1: The Dumb Idea Dump

**Progress: Step 1 of 6** — Next: Break the Idea

---

## STEP GOAL

Capture the idea exactly as messy as it is and create the sparring memo — polishing an idea too early disguises a bad concept.

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER generate content without user input — you are a facilitator, not a content generator
- 📝 Capture the dump VERBATIM — do not clean up language, do not summarize, do not "improve"
- 🚫 BAN solutions, features, and market sizing at this step — park them, do not discuss them

---

## MANDATORY SEQUENCE

### 1. Resolve Output Destination

Determine the output folder per the workflow Initialization section (`outputFile` frontmatter / `ASK-CLAUDE-MD` / `rbtv-output-resolution` rule). Propose the resolved path and wait for confirmation.

### 2. Elicit the Dump

**Prompt:**
> "Give me the idea exactly as it lives in your head right now — messy, vague, ugly. Fragments are perfect. What's nagging you?"

Accept fragments, complaints, and half-thoughts. The uglier the better — if an idea survives being vague and ugly, it is worth exploring.

### 3. Enforce the No-Polish Rule

While the user dumps:

| If the user... | Do |
|----------------|----|
| Pitches features or solutions | Park each in a "Parked solutions" list. Say: "Parked. Solutions come back later — if the problem survives." |
| Quotes market sizes or TAM | Strike it. Say: "No market sizing yet. Problem first." |
| Polishes language mid-dump | Ask for the unpolished version: "Say it the way you'd complain about it to a friend." |

### 4. Name the Idea

Ask for (or propose) a 2-4 word working name. Derive `{idea-slug}` from it (lowercase-kebab).

### 5. Create the Sparring Memo

Create the output document from `templateFile`, filling `{idea-name}` and `{date}`. Append:

```markdown
## Idea Dump

{User's notes, verbatim — fragments and bullets preserved as given}

**Parked solutions (not idea material yet):**
- {parked item, or "none"}
```

### 6. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 2: Break the Idea |
| **[R] Revise** | Amend the dump before sparring starts |

HALT and WAIT for user input.

---

## ON CONTINUE

1. Update memo frontmatter: add `step-01-init` to `stepsCompleted`
2. Save the memo
3. Load `./step-02-break.md` and follow it exactly

# Writing

## Purpose

This module is for long-form written pieces — essays, opinion articles, analytical arguments — where the quality of reasoning matters as much as the prose. It's built around an Orwell-influenced writing philosophy: clarity is intelligence, vagueness is dishonesty, and first drafts are excavation not architecture. Reach for this module when you need to build a structured, evidence-backed essay from scratch, pressure-test an argument, or extract the voice signature from a body of writing so it can be replicated or refined.

---

## Components

### `/rbtv-writer`

- **What**: Activates George Orwell, the Critical Essay Architect persona. Orwell is a blunt diagnostician of weak thinking — he names fallacies, demands evidence for every claim, and treats complexity without purpose as intellectual cowardice. He collaborates with you as a demanding peer, not a yes-and assistant. The workflow he runs is compound: it builds a persistent style guide across essays, separating his editorial defaults (always applied) from your personal voice (evolves over time).

- **When to use**: You want to write a rigorous, well-structured essay or article — a new piece from scratch, or resuming one in progress. Also useful when you want Orwell to tear apart a text you've written or found, checking it for fallacies, weak logic, and shallow thinking.

- **How to invoke**: `/rbtv-writer`  
  Orwell greets you and presents a numbered menu. The main options are:
  - `NE` (or "new essay") — start a new piece from scratch
  - `CE` (or "continue essay") — resume an essay in progress; bring the existing `essay.md` into context
  - `CR` (or "critical review") — submit a text for rigorous critique
  - `SG` (or "style guide") — view, update, or seed your persistent writing style guide

- **What it produces**: Three separate output documents built incrementally through a 11-step workflow:
  - `essay.md` — the main essay, built step by step with frontmatter state tracking
  - `research-brief.md` — a structured brief of research topics for external AI tools (created at step 6)
  - `visual-assets.md` — AI prompts for charts and infographics (created at step 9)
  - `style-guide.md` — a persistent voice profile that grows smarter with each essay (seeded at step 3, updated at step 11)

- **Example**:
  - User: `/rbtv-writer` → Orwell presents the menu → User types `NE`
  - Orwell walks you through framing the thesis, pressure-tests the argument structure through targeted questions, identifies which claims need evidence, and builds the essay section by section — halting at each step for your input before loading the next.

---

### `/rbtv-tone-extractor`

- **What**: A standalone task that extracts a voice signature from any text sample — analyzing emotional tone, structural patterns, and vocabulary/register across three dimensions. The output is written *in* the extracted voice, not about it. Rather than listing "the writer uses short sentences," the profile demonstrates those patterns directly, making it immediately usable as a writing guide.

- **When to use**: You want to capture the voice of a specific writer, your own past writing, or a body of content, so you (or an AI agent) can replicate or extend it consistently. Works on any language — Portuguese input produces a Portuguese profile.

- **How to invoke**: `/rbtv-tone-extractor`  
  The agent asks you to provide the source text (paste it directly, give a file path, or give a URL). Text must be at least 100 words for a meaningful extraction.

- **What it produces**: A 400–600 word voice profile written in the extracted voice, covering:
  - Emotional core and psychological register
  - Structural preferences (list/prose ratio, sentence length, question density, formatting patterns)
  - Vocabulary patterns (formality, domain terms, metaphor use, language mixing)
  - 2–3 signature elements that make the voice immediately recognizable

- **Example**:
  - User: `/rbtv-tone-extractor` → agent asks for text → User pastes three paragraphs from a Substack essay they admire
  - Agent produces a 500-word profile that *sounds like* the original author, covering their conversational directness, use of rhetorical questions, and resistance to jargon — ready to paste into a writing prompt.

---

## How they fit together

The two commands are designed to work in sequence. Run `/rbtv-tone-extractor` on a body of writing to capture its voice signature, then bring that profile into `/rbtv-writer` via the Style Guide (`SG`) option — feed the extracted profile as a text sample to seed or update your persistent `style-guide.md`. From that point forward, Orwell applies your personal voice patterns on top of his editorial defaults every time you write.

They also work independently: tone extraction is useful any time you need a voice profile (for replication, for analysis, for feeding another generator), and the writer is useful any time you need rigorous essay structure regardless of voice.

---
---

# Template Instructions: ai_model

**Purpose:** AI model-specific prompting guidance for adapting general techniques to specific models.

**Required:** Optional. Create when a project uses multiple models or when model-specific behavior matters.

---

## Design Principles

| Principle | Requirement |
|-----------|-------------|
| Intermediate-to-pro focus | MUST assume reader knows basics; focus on optimization, edge cases, mastery |
| Lean but deep | Structure MUST be minimal; content MUST be thorough and immediately actionable |
| Delta-focused | MUST document only what makes this model different — NEVER generic AI advice |
| Practitioner-ready | Every technique MUST include enough detail for immediate application |
| Practical over theoretical | MUST use specific examples over abstract descriptions |

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| Characteristics | Required | Quick reference table; add subsections for multimodal models |
| Use Cases | Required | Model selection — when to choose or avoid this model |
| Techniques | Required | Actionable deltas from baseline |
| Pitfalls | Required | Anti-patterns and common errors with solutions |
| Examples | Required | Min 2-3; MUST show model-specific deltas, NEVER generic prompting advice |
| Checklists | Recommended | Model-specific, actionable verification items |
| Technical Reference | Recommended | Links to official docs |
| Sources | Required | TS >= 6 after marketing penalty; group links from same domain |
| Discarded Sources | Required | Transparency on sources below threshold |
| Last updated | Required | Footer in `YYYY-MM-DD` format |

---

## Notes

### Scope

Model documents capture **prompting deltas** — how to adjust technique for this specific model. Each document MUST include:
- Model-specific techniques and pitfalls
- Technique implementations with code examples
- Before/after comparisons with measurable results
- Quality checklists for progression
- Links to official documentation

Documents MUST NOT:
- Repeat general prompting best practices
- Duplicate agent instructions
- Serve as getting started guides
- Show generic examples (examples MUST demonstrate model-specific deltas)

### Naming

Files follow pattern: `[model_name].md` (e.g., `claude.md`, `gpt4o.md`, `gemini_pro.md`)

### When to Create

Create a model document when:
- Model behavior differs significantly from defaults
- Team encounters repeated model-specific issues
- Multiple agents need the same model adjustments
- Production deployment requires implementation guidance

Do NOT create if standard prompting works and no implementation guidance is needed.

### Modality Considerations

Different model types require different section emphasis:

| Modality | Required Sections | Optional/Reduced Sections |
|----------|-------------------|---------------------------|
| Text/Code | All sections required | — |
| Image | Characteristics, Use Cases, Techniques, Pitfalls, Examples | Checklists, Technical Reference |
| Video | Characteristics, Use Cases, Techniques, Pitfalls, Examples | Checklists, Technical Reference |
| Audio | Characteristics, Use Cases, Techniques, Pitfalls, Examples | Checklists, Technical Reference |
| Multimodal | All sections; add subsections per modality | — |

For non-text models, adapt section content to the modality:

| Modality | Key Focus Areas |
|----------|-----------------|
| Text/Code | Token management, structured outputs, chain-of-thought, caching, error handling |
| Image | Style vocabulary, composition terms, negative prompts, seed control, aspect ratios |
| Video | Shot lists, camera vocabulary, temporal coherence, audio design, duration limits |
| Audio | Voice characteristics, timing, emotion, pronunciation, format specifications |
| Multimodal | Cross-modal coordination, input ordering, modality-specific subsections |

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Model Name]

**Version:** [Model version or date cutoff]  
**Provider:** [OpenAI | Anthropic | Google | etc.]  
**Modality:** [Text | Code | Image | Audio | Video | Multimodal]

---

## Table of Contents

1. [Characteristics](#characteristics)
2. [Use Cases](#use-cases)
3. [Techniques](#techniques)
4. [Pitfalls](#pitfalls)
5. [Examples](#examples)
6. [Pre-Publishing Checklist](#pre-publishing-checklist)
7. [Technical Reference](#technical-reference)
8. [Sources](#sources)
9. [Discarded Sources](#discarded-sources)

---

## Characteristics

| Aspect | Value |
|--------|-------|
| Input Types | [Text, Image, Audio, Video — list all supported] |
| Output Types | [Text, Image, Audio, Video — list all supported] |
| Context Window | [e.g., 200K tokens] (if applicable) |
| Strengths | [e.g., Long-form reasoning, code generation] |
| Weaknesses | [e.g., Math, recent events] |

---

## Use Cases

| Ideal For | Avoid For |
|-----------|-----------|
| [Scenarios where this model excels] | [Scenarios where this model underperforms or is unsuitable] |

---

## Techniques

What works differently with this model vs. general practice.

> **Column definitions:**  
> - **API:** Whether this technique is available via API/programmatic access (Yes/No)  
> - **Interface:** Whether this technique is available through the provider's web interface or UI (Yes/No)

| Technique | How to Apply | When to Use | API | Interface |
|-----------|--------------|-------------|-----|-----------|
| [Technique name] | [Specific instructions for this model] | [Use case or scenario] | Yes/No | Yes/No |

---

## Pitfalls

Anti-patterns and common errors when working with this model.

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| [What to avoid or what people do wrong] | [Consequence or impact] | [How to fix or prevent] |

---

## Examples

Technique implementations with before/after comparisons. Each example must demonstrate **model-specific deltas** — what works differently with this model compared to standard prompting practice or other models.

**Critical requirement:** Examples must show what makes this model unique, not generic prompting advice that applies to all models.

### Example 1: [Technique Name] — [Problem Domain]

**Problem:** [What intermediate practitioners struggle with when applying this technique specifically with this model]

**Model-specific delta:** [What makes this technique different for this model vs. standard practice or other models]

**Standard approach (works for most models):**

[Input/output showing the standard approach that works for other models]

**Why standard approach fails with this model:** [Model-specific failure mode — e.g., "This model requires explicit schema definitions, while others infer structure", "This model's context window behavior differs", "This model's tokenization affects prompt structure"]

**Model-specific implementation:**

[Code showing how to apply the technique specifically for this model — SDK calls, configuration, prompt structure that differs from standard]

**After (with model-specific technique):**

[Input/output showing the improved result]

**Result:** [Measurable improvement — e.g., "30% accuracy gain", "99% schema compliance", "50% cost reduction"] — must be specific to this model's behavior

---

## Pre-Publishing Checklist

Before finalizing any prompt for this model, verify model-specific requirements. This checklist must be **actionable** and **model-specific** — not generic prompting advice that applies to all models.

**Actionable means:** Each item must be verifiable with a yes/no answer or specific test. Avoid vague items like "ensure prompt is clear" — use "prompt includes explicit [model-specific requirement]".

**Model-specific means:** Focus on what differs for this model. Do not duplicate general prompting best practices or agent instructions.

- [ ] [Model-specific verification item — e.g., "Prompt includes explicit schema definition (required for this model's structured output)"] 
- [ ] [Model-specific verification item — e.g., "Context window usage verified against model's [X] token limit"]
- [ ] [Model-specific verification item — e.g., "Prompt structure optimized for model's [specific behavior]"]

---

## Technical Reference

Links to official documentation for model-specific mechanisms. Link to the most specific page available; if no specific page exists, link to the model's main documentation.


| Topic | Official Documentation |
|-------|------------------------|
| [Feature/mechanism name] | [URL to official docs page] |
| [Feature/mechanism name] | [URL to official docs page] |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | [Source title] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |
| 2 | [Grouped source — parent] | — | — | — | [avg] | [avg] | [avg] | [avg] |
|   | ↳ [Nested source 1] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |
|   | ↳ [Nested source 2] | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | [x.x] | [x] | [x] | [x] |
|   | ↳ ~~[Discarded nested]~~ | [URL] | [YYYY-MM-DD] | [YYYY-MM-DD or n.a] | ~~[x.x]~~ | [x] | ~~[x]~~ | [x] |

> **Format:** 
> - Each nested source has its own evaluation; parent shows average of non-discarded entries
> - Apply marketing language penalty (-1 to -3 TR) before calculating TS
> - Strikethrough discarded nested entries (TS < 6); they still count toward transparency

---

## Discarded Sources

[List sources that were considered but did not meet the TS >= 6 threshold, including nested entries that were discarded from grouped sources.]

| Source | TS | Reason |
|--------|-----|--------|
| [Title](URL) | [x.x] | [e.g., Low authority (AT:4), Marketing language penalty (TR: 8→5), Poor topic match (TM:3)] |


---

*Last updated: 2026-02-04*

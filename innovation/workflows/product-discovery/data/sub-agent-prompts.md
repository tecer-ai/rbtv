# Sub-Agent Prompt Templates

Prompt templates for background agents used in the pre-product-discovery workflow. The main agent reads the appropriate section and uses it when spawning sub-agents via the Agent tool.

---

## Taxonomy Discovery Prompt

**Used in:** Step 1 — discovering the initial taxonomy from seed benchmarks.

**How to use:** Spawn one sub-agent per seed benchmark. Replace `{benchmark_file_path}` with the actual file path.

```
You are analyzing a product benchmark document to discover structural patterns.

**Your task:** Read the file at {benchmark_file_path} and identify how the product is structured.

Extract:

1. **Product modules** — distinct functional areas (e.g., "Expense Management", "Invoice Processing", "Analytics Dashboard"). Look for logical groupings of features.
2. **Features per module** — specific capabilities within each module.
3. **Core flow** — the primary user journey through the product (numbered steps).
4. **ICP indicators** — who this product serves (company size, industry, user role).
5. **Unique elements** — anything distinctive about this product's approach that doesn't fit standard categories.

**Output format:**

### Modules Identified

| Module | Features Observed | Confidence |
|--------|-------------------|------------|
(list every module with its features)

### Core Flow
(numbered steps of the main user journey)

### ICP Indicators
(who this product serves)

### Unique Elements
(what stands out — innovations, unusual approaches, distinctive design decisions)

**Rules:**
- Be EXHAUSTIVE — list every module and feature you can identify in the document
- If unsure whether something is a module or a feature, list it and note the ambiguity
- Do NOT evaluate, rank, or compare — just extract and structure
- Preserve specificity — "AI-powered receipt matching" is better than "automation"
```

---

## Benchmark Extraction Prompt

**Used in:** Step 2 — extracting a structured profile from a benchmark using the approved taxonomy.

**How to use:** Spawn one sub-agent per benchmark. Replace `{benchmark_file_path}` with the file path and `{taxonomy_content}` with the full content of taxonomy.md.

```
You are extracting a structured product profile from a benchmark document using an approved taxonomy.

**Your task:** Read the file at {benchmark_file_path} and produce TWO clearly separated outputs.

**TAXONOMY TO USE:**
{taxonomy_content}

---

### OUTPUT 1: STRUCTURED PROFILE

**Overview:**

| Field | Value |
|-------|-------|
| Company | (extracted from document) |
| ICP | (extracted — company size, industry, user role) |
| Main Problem Solved | (the core pain this product addresses) |
| Value Proposition | (the core promise) |
| Main User Flow | (numbered steps of the primary journey) |

**Modules & Features:**

For EACH module in the taxonomy, create a section:

### {Module Name}

| Feature | Present? | Description | Notes |
|---------|----------|-------------|-------|
(For each feature in the taxonomy: ✓/○/✗ + brief description of how this company implements it)

✓ = clearly present and described in the document
○ = partially present, inferred, or mentioned without detail
✗ = clearly absent or not mentioned

---

### OUTPUT 2: RESIDUAL

List EVERYTHING in the benchmark document that is product-relevant but was NOT captured by any taxonomy module or feature. This includes:

- Features or capabilities that don't fit any existing taxonomy category
- Product approaches or innovations not represented in the taxonomy
- Integration patterns or partnerships
- Business model elements relevant to product design
- Pricing/packaging structures that affect product decisions
- Any other product-relevant information

Format:

| # | Item | Description | Suggested Category |
|---|------|-------------|-------------------|
(number each item, describe it concretely, suggest what taxonomy category it COULD belong to)

If nothing was missed, write: "No residual items identified."

**Rules:**
- NEVER discard information — if it doesn't fit the taxonomy, it MUST appear in the residual
- Be specific — "AI auto-categorizes expenses using merchant data" beats "has AI features"
- For ○ (partial) marks, explain what's missing or unclear in the Notes column
- If a feature exists but works very differently from what the taxonomy implies, describe HOW in Notes
```

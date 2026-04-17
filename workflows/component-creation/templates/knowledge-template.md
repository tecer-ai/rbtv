# Knowledge File Templates

Use these templates to create knowledge and data files for BMAD.

---

## CSV Data File Template

```csv
name,category,description,when_to_use
"Item A","category-1","What this item does","When it's appropriate"
"Item B","category-2","What this item does","When it's appropriate"
```

### CSV Rules
- Headers in first row
- Quote strings that contain commas
- Include a `category` column for filtering
- Include a `description` column for context

---

## Knowledge Fragment Template (Markdown)

```markdown
# {Topic Title}

{Brief introduction — 1-2 sentences.}

---

## Overview

{What this topic covers and why it matters.}

---

## Key Concepts

### {Concept 1}
{Explanation with practical examples.}

### {Concept 2}
{Explanation with practical examples.}

---

## Patterns

| Pattern | Use When | Example |
|---------|----------|---------|
| {Pattern A} | {Condition} | {Code or text example} |
| {Pattern B} | {Condition} | {Code or text example} |

---

## Common Mistakes

1. **{Mistake}** — {Why it fails and what to do instead}

---

## Quick Reference

- {Key point 1}
- {Key point 2}
- {Key point 3}
```

---

## Index File Template (for large knowledge bases)

```csv
id,topic,path,tags
fixture-arch,"Fixture Architecture","knowledge/fixture-architecture.md","testing,architecture"
api-testing,"API Testing Patterns","knowledge/api-testing.md","testing,api"
```

### Index Rules
- **id**: Unique identifier for the fragment
- **topic**: Human-readable topic name
- **path**: Relative path to the fragment file
- **tags**: Comma-separated keywords for filtering

---

## Knowledge Loading Patterns

### Small Knowledge Base (< 10 files)
Load eagerly during agent activation. Reference in activation steps:
```xml
<step n="3">Load knowledge from {rbtv_path}/personas/*.md</step>
```

### Large Knowledge Base (10+ files)
Use index-based selective loading:
1. Agent consults index file based on user's question
2. Agent loads only relevant fragments
3. Fragments are discarded after use

---

## Size Guidelines

| File Type | Target Lines | Max |
|-----------|-------------|-----|
| Knowledge fragment | 50-200 | 300 |
| CSV data file | 10-100 rows | 500 rows |
| Index file | 10-50 entries | 100 entries |

---

## Writing Guidelines

1. **One topic per file** — Keep knowledge fragments focused

2. **Write imperatively** — "Do X" not "One might consider X"

3. **Include practical examples** — Show, don't just tell

4. **No outbound references** — Each fragment should be self-contained

5. **Use tables for structured data** — Easier to scan than prose

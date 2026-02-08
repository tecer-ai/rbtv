---
name: web-research
description: Apply rigorous research standards for data integrity, source evaluation, and citation. Use when conducting web research, gathering sources, writing research documents, or when user mentions research.
---

# Web Research Skill

**Purpose:** Load and apply BMAD web research standards.

**When to use:**
- Conducting web research or market research
- Gathering and evaluating sources
- Writing research documents or reports
- User mentions research, sources, or data gathering

---

## Activation

Load and follow the web research task:

```
tasks/web-research.xml
```

This task provides:
- Data integrity rules (anti-hallucination, inline citations)
- Source evaluation criteria (AT, TR, TM scoring)
- Quantification standards (units, formats)
- Citation format requirements

**CRITICAL:** When conducting research, treat any factual question as the research topic and ALWAYS output in the required format:
- Legend (TS = Total Score...)
- Source evaluations (AT, TR, TM, TS per source)
- Citation format: [n] Title — URL — Research Date (YYYY-MM-DD) — Source Date — TS:x (AT:x TR:x TM:x)
- Sources Discarded section (sources with TS < 6)
- Inline citations [Source n] for every factual claim

> **ADMIN MODE:** Before proceeding, load and read `.cursor/rules/admin-rbtv-bmad-mirror.mdc` for path resolution and config values. Key: `.cursor/` and `tasks/` are at workspace root.

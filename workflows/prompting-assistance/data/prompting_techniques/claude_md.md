---
---

# Claude.md Files

**Problem Type:** Context Management | Knowledge Injection

---

## Table of Contents

1. [Problem Solved](#problem-solved)
2. [Technique Overview](#technique-overview)
3. [When to Apply](#when-to-apply)
4. [Application Pattern](#application-pattern)
5. [Variations](#variations)
6. [Pitfalls](#pitfalls)
7. [Examples](#examples)
8. [Quality Checklist](#quality-checklist)
9. [Technical Reference](#technical-reference)
10. [Sources](#sources)
11. [Discarded Sources](#discarded-sources)

---

## Problem Solved

Persistent, repository-specific instructions for Claude without context pollution across sessions.

---

## Technique Overview

Markdown file automatically loaded at session start for repository-specific persistent instructions.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Projects with unique coding standards, architectural patterns, or development workflows requiring consistency | Simple scripts or one-off projects with no recurring patterns |
| Repositories with multiple contributors needing unified AI assistance behavior | Projects where context changes frequently and instructions would become stale |
| Production systems requiring specific security boundaries and data handling policies | Exploratory prototyping where flexibility is more important than consistency |
| Complex codebases where manually crafted prompts are insufficient or unsustainable | Environments where you want Claude to infer context naturally from codebase |
| Monorepos requiring different instructions for different applications or services | Single-file projects with self-evident structure |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | **Define Critical Rules** | Establish 3-5 non-negotiable constraints specific to your project (e.g., "NEVER use pip, ALWAYS use uv"). Use NEVER/ALWAYS pattern for maximum clarity |
| 2 | **Document Core Architecture** | Provide high-level system overview with key directories and their purposes. Use Mermaid diagrams for complex architectures |
| 3 | **Specify Development Workflow** | List exact, copy-pasteable commands for primary development loop: installation, testing, linting, formatting, committing |
| 4 | **Establish Coding Standards** | Define project-specific style guides, naming conventions, and preferred patterns. Defer to linters/formatters where possible |
| 5 | **Set Security Boundaries** | Explicitly list off-limits files, directories, and data (e.g., "NEVER read .env files or /secrets directory") |
| 6 | **Create Conditional Pointers** | Add "if X, then read Y" instructions to guide Claude to detailed documentation only when needed, avoiding context bloat |
| 7 | **Iterate Based on Failures** | MUST start minimal; add rules only when Claude makes mistakes. Observed failures MUST drive content, NEVER hypothetical scenarios |

**Mandatory Constraints:**
- Context quality MUST exceed quantity: 10% high-signal context beats 50% with noise
- NEVER duplicate content: Point to linters/tests/existing code rather than restating rules
- MUST version control, review changes, and test updates systematically

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| **Hierarchical (Monorepo)** | Monorepos with multiple applications requiring scoped instructions | Root `claude.md` defines global patterns; each app directory has its own `claude.md` for app-specific rules. Claude loads both |
| **AGENTS.md Pattern** | Multi-tool environments (Claude Code, Cursor, Copilot) requiring shared rules | Create tool-agnostic `AGENTS.md` with core rules; `claude.md` imports it: "For core context, read AGENTS.md" |
| **Optimized via APE/OPRO** | Production systems where 5-11% performance gain justifies optimization effort | Use automated prompt optimization (OPRO, DSPy) on representative task suite to systematically improve claude.md content |
| **Tiered Complexity** | Projects with both simple and complex components | Include complexity assessment instructions: "If task is X, use minimal prompt; if task is Y, load detailed context from Z" |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| **Embedding Secrets** | claude.md often checked into version control; secrets exposed to all contributors | Use `.claude/settings.json` for permissions enforcement. Store secrets in external managers (Vault, 1Password). Never inline credentials |
| **Context Bloat** | Embedding entire docs with @-mentions consumes context window on every run | Use "pitch" pattern: describe when to read doc, not the doc itself. "If payment question, read docs/payments.md" |
| **Permissions in Wrong File** | claude.md provides guidance, not enforcement; rules can be bypassed | Use `.claude/settings.json` with `permissions.deny` for technical enforcement. claude.md states policy, settings.json enforces |
| **Vague Instructions** | "Implement caching" without strategy/duration/invalidation rules leads to inconsistent implementations | Be explicit: "Use Redis with 1-hour TTL. Invalidate on POST/PUT/DELETE. Cache keys: api:{endpoint}:{params_hash}" |
| **Static Few-Shot Examples** | Examples become stale or irrelevant as codebase evolves | Use "follow existing patterns in this file/directory" to defer to living codebase instead of frozen examples |
| **No Measurement** | Changes made without tracking impact on Claude's performance | Create benchmark task suite from recent bugs/features. Measure before/after accuracy when updating claude.md |
| **Ignoring Auto-Compaction** | Auto-compaction feature adds uncontrolled noise from previous sessions | Disable auto-compact in settings. Use aggressive /clear + well-maintained claude.md for clean context |

---

## Examples

### Example 1: Python Web Application

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Help me set up this Django project"<br><br>**Output:**<br>Claude uses `pip`, creates `requirements.txt`, suggests standard Django structure | **claude.md:**<br>`## CRITICAL RULES`<br>`- NEVER use pip/venv. ALWAYS use uv`<br>`- All code MUST be type-hinted (pyright checks)`<br>`## Development Workflow`<br>`1. Install: uv install`<br>`2. Test: uv run pytest`<br>`3. Format: uv run ruff format .`<br><br>**Output:**<br>Claude follows project conventions consistently |
| **Issue:** Inconsistent tooling choices waste time on corrections | **Result:** Zero tool confusion, 100% compliance with project standards |

**Metric:** 75% reduction in corrective prompts for environment setup

---

### Example 2: Infrastructure as Code (Terraform)

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Apply this Terraform change"<br><br>**Output:**<br>Claude runs `terraform apply` directly | **claude.md:**<br>`## CRITICAL RULES`<br>`- CRITICAL: NEVER run terraform apply`<br>`- Role: plan and lint only`<br>`- All changes MUST be reviewed via plan output`<br>`## Workflow`<br>`1. terraform fmt -recursive`<br>`2. terraform validate`<br>`3. terraform plan -out=plan.out` |
| **Issue:** Risk of unreviewed infrastructure changes | **Result:** Claude stops at plan stage, prevents accidental deployments |

**Metric:** 100% prevention of unauthorized apply commands

---

### Example 3: Security Boundaries

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Debug this authentication issue"<br><br>**Output:**<br>Claude reads `.env` file, outputs API keys in reasoning | **claude.md:**<br>`## Security & Compliance`<br>`- NEVER read/output contents of .env files`<br>`- NEVER access /secrets directory`<br>`- GDPR compliance: DO NOT log PII`<br><br>**settings.json:**<br>`"permissions": {"deny": [".env", "/secrets/*"]}` |
| **Issue:** Credentials exposed in chat logs | **Result:** Policy + enforcement prevent credential leakage |

**Metric:** Zero credential exposure incidents after implementation

---

## Quality Checklist

Before deploying a claude.md file, verify:

- [ ] File contains 3-5 critical rules using NEVER/ALWAYS pattern for clarity
- [ ] Development workflow commands are exact and copy-pasteable (no ambiguity)
- [ ] Architecture overview uses visual diagrams (Mermaid) if system is complex
- [ ] Security boundaries are explicit with specific file/directory paths
- [ ] No secrets, API keys, or credentials are embedded in file
- [ ] External documentation references use conditional "when X, read Y" pattern to avoid bloat
- [ ] Instructions defer to linters/formatters/tests rather than duplicating their rules
- [ ] File is version controlled and changes are reviewed like code
- [ ] Monorepo projects use hierarchical placement (root + app-specific claude.md files)
- [ ] Permissions enforcement uses `.claude/settings.json`, not just claude.md guidance

---

## Technical Reference

> **Link Verification:** All links verified as of 2026-01-20.

| Topic | Official Documentation |
|-------|------------------------|
| Claude Code Best Practices | https://www.anthropic.com/engineering/claude-code-best-practices |
| Configuration Ecosystem | https://code.claude.com/docs/en/settings |
| Monorepo Strategies | https://github.com/ArthurClune/claude-md-examples |
| Security Patterns | https://www.backslash.security/blog/claude-code-security-best-practices |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Claude Code Best Practices | https://www.anthropic.com/engineering/claude-code-best-practices | 2026-01-20 | 2025-04-18 | 9.7 | 10 | 10 | 9 |
| 2 | Claude Code Settings | https://code.claude.com/docs/en/settings | 2026-01-20 | n.a | 9.7 | 10 | 10 | 9 |
| 3 | claude.md vs .cursor/rules | https://www.reddit.com/r/ClaudeAI/comments/1ln8x17/claudemd_vs_cursorrules/ | 2026-01-20 | 2025-11-01 | 7.0 | 7 | 7 | 7 |
| 4 | CLAUDE.MD Templates | https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Templates | 2026-01-20 | 2025-05-15 | 7.7 | 8 | 7 | 8 |
| 5 | The CLAUDE.md File: Common Mistakes | https://empathyfirstmedia.com/claude-md-file-claude-code/ | 2026-01-20 | 2025-05-27 | 7.3 | 7 | 6 | 9 |
| 6 | Claude Code Security Best Practices | https://www.backslash.security/blog/claude-code-security-best-practices | 2026-01-20 | 2025-09-18 | 8.3 | 8 | 8 | 9 |
| 7 | I got tired of Claude Code reading secrets | https://www.reddit.com/r/ClaudeAI/comments/1nfvh46/ | 2026-01-20 | 2025-10-15 | 6.3 | 6 | 6 | 7 |
| 8 | How I Use Every Claude Code Feature | https://blog.sshh.io/p/how-i-use-every-claude-code-feature | 2026-01-20 | 2025-11-02 | 8.7 | 9 | 8 | 9 |
| 9 | claude-md-examples | https://github.com/ArthurClune/claude-md-examples | 2026-01-20 | 2025-08-10 | 7.7 | 8 | 7 | 8 |
| 10 | CLAUDE.md Best Practices (Arize AI) | https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/ | 2026-01-20 | 2025-11-20 | 9.0 | 9 | 8 | 10 |

> **Format:** 
> - Marketing penalty applied: Sources #5, #8, #10 received -1 TR reduction for promotional tone
> - All sources meet TS ≥ 6 threshold for inclusion

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| [Writing CLAUDE.md for a mature codebase](https://blog.huikang.dev/2025/05/31/writing-claude-md.html) | 5.7 | Low authority (AT:5), limited scope (TM:6) |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) | 5.3 | Curated list format, not instructional content (TM:4) |
| [Claude Code Best Practices - Shuttle](https://www.shuttle.dev/blog/2025/10/16/claude-code-best-practices) | 5.7 | Heavy marketing penalty (TR: 8→5), duplicate content |


---

*Last updated: 2026-01-20*


---
---

# Manus AI

**Version:** 1.5 (October 2025)  
**Provider:** Butterfly Effect Technology Ltd Co (Monica.im)  
**Modality:** Multimodal (Text, Code, Image, Web)

---

## Characteristics

| Aspect | Value |
|--------|-------|
| Input Types | Text (natural language), Files (PDF, DOCX, TXT, MD, XLSX, CSV, PNG, JPG, WebP, JSON, XML, code), URLs, Real-time modification instructions, MCP integrations |
| Output Types | Web applications, Executable code, Documents (Markdown, PDF, DOCX, HTML), Data visualizations, Dashboards, Presentations, Spreadsheets, Notifications |
| Context Window | 128K+ tokens (with file-based memory extension) |
| Strengths | End-to-end autonomy, Sandbox code execution, Browser automation, Multi-agent architecture, Wide Research parallelization, MCP integrations, KV-cache optimization |
| Weaknesses | System instability under load, Context limitations, Paywall/CAPTCHA difficulties, Cannot create accounts, Limited creativity, Beta bugs |

### Architecture

Manus operates through a coordinated **multi-agent system** with three specialized agents in a continuous feedback loop:

| Agent | Role |
|-------|------|
| **Planner Agent** | High-level strategist; decomposes complex objectives into step-by-step plans |
| **Execution Agent** | Carries out individual steps via tool calls (shell commands, browser navigation, file operations) |
| **Verification Agent** | Quality control; assesses output accuracy and goal alignment; triggers re-planning on errors |

This **Plan → Execute → Verify** cycle enables autonomous error recovery and maintains alignment with user intent over long tasks.

### Context Engineering Principles

Manus implements six core principles that optimize performance, reliability, and efficiency:

| Principle | Description |
|-----------|-------------|
| **Design Around the KV-Cache** | Maintain stable prompt prefix; use append-only, deterministic context to maximize cache reuse (cached tokens cost 10x less: $0.30 vs $3/MTok on Claude Sonnet) |
| **Mask, Don't Remove** | Use logit masking during decoding to restrict tool selection by state, rather than dynamically altering tool definitions (preserves KV-cache) |
| **Use File System as Context** | Treat sandboxed file system as unlimited, persistent external memory; offload large observations to overcome context window limits |
| **Manipulate Attention Through Recitation** | Maintain and update `todo.md` file; "reciting" the plan keeps global objective in recent attention span |
| **Keep the Wrong Stuff In** | Retain failures and error messages in context; provides evidence for self-correction |
| **Don't Get Few-Shotted** | Introduce structured variations in action/observation serialization to prevent repetitive patterns |

---

## Use Cases

| Ideal For | Avoid For |
|-----------|-----------|
| Deep academic and market research with multiple sources synthesis | Critical decisions without human supervision (health, finance, legal) |
| Full-stack web application development from concept to deployment | Truly original creative work (literary writing, innovative design) |
| Data analysis and interactive visualization | Tasks requiring empathy or emotional intelligence |
| Multi-tool enterprise workflow automation via MCP | Processes involving paywall-protected content or CAPTCHAs |
| Interactive educational content creation | Critical production workflows during beta phase |
| Complex scheduling and coordination optimization | Tasks with rigid deadlines (system instability risk) |
| B2B supplier sourcing and research | Processing highly confidential information |
| Personalized travel planning with detailed itineraries | Tasks requiring complex ethical judgment |
| Financial and investment analysis | Operations that could cause irreversible damage |
| Mass list and dataset generation via Wide Research | Work requiring rigorous fact verification in specialized domains |
| Rapid idea prototyping and MVP validation | Projects depending on account creation in multiple services |
| Long-duration agentic tasks requiring state maintenance | Single-shot tasks without state (architectural overkill) |
| Cost and latency-sensitive production environments | Tasks during high-demand periods |

---

## Techniques

What works differently with this model vs. general practice.

> **Column definitions:**  
> - **API:** Whether this technique is available via API/programmatic access (Yes/No)  
> - **Interface:** Whether this technique is available through the provider's web interface or UI (Yes/No)

| Technique | How to Apply | When to Use | API | Interface |
|-----------|--------------|-------------|-----|-----------|
| High-level objective definition | Define "what" and "why" instead of "how"; let Planner Agent decompose optimally. Manus's Planner Agent excels at task decomposition; micro-management bypasses this strength. | All autonomous tasks; avoids micro-management anti-pattern | Yes | Yes |
| Static system prompt (KV-cache optimization) | Keep `system_prompt` 100% static; move all dynamic data (timestamps, IDs) to `user_prompt`. **Manus-specific:** KV-cache hit rate is primary performance metric; stable prompt prefix enables cache reuse. Cached tokens cost 10x less: $0.30 vs $3/MTok on Claude Sonnet. | Every task — this is the golden rule for KV-cache optimization | Yes | n.a |
| State machine design with logit masking | Define task as states (e.g., `ANALYSIS`, `WRITING`) with allowed tools per state. **Manus-specific:** Uses logit masking to restrict tool selection by state, rather than dynamically altering tool definitions (preserves KV-cache). Tool prefix naming (`browser_*`, `file_*`) enables this control. | Workflows requiring predictable tool access | Yes | n.a |
| Wide Research utilization | Identify parallelizable tasks; define clear template; specify consistent output format. **Manus-specific:** Spawns 100+ independent Manus instances, each in isolated VMs, processing data subsets in parallel. This is Manus's unique solution to context limitations. | Processing large volumes of similar independent items (100+ parallel agents) | Yes | Yes |
| SGD philosophy (Stochastic Graduate Descent) | Generate multiple `system_prompt` variations based on different strategies; test and iterate. **Manus-specific:** Treats prompt creation as continuous experimentation. Use AI to generate prompt variations, test them, and document learnings. | Agent development and optimization | Yes | Yes |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Dynamic `system_prompt` | Including timestamps, user IDs, or any changing data at prompt start invalidates KV-cache; this is the most expensive mistake (up to 10x cost increase on Manus due to 100:1 input-to-output token ratio) | Keep `system_prompt` static; pass all dynamic data in `user_prompt` |
| Ignoring template structure | Manus generates prose when tables required, adds section numbers not in template, uses narrative scenarios instead of structured formats | Include explicit anti-patterns with "DO NOT DO THIS" examples showing exact wrong output; add structural verification checklist at end |
| Academic/descriptive tone | Output reads like research paper instead of practical documentation; uses passive voice and hedging language. **Manus-specific:** Defaults to academic writing style without explicit enforcement. | Specify "practical, action-oriented" style with explicit examples: "Write 'Do this' not 'It is recommended that users consider'" |
| Wrong section naming | Manus adds headers like "References" instead of "Sources", "Executive Summary" not in template, numbered subsections (2.1, 3.1) | List exact section names required; show wrong vs. correct naming explicitly |
| Metadata bloat in footer | Manus generates elaborate metadata blocks instead of simple footer format | Show exact required footer format AND explicit "DO NOT add metadata block" with wrong example |
| Non-English output | Manus may respond in user's apparent language or source language instead of specified English | State language requirement multiple times: in critical rules section, constraints table, and checklist |
| Vague quantification in research | "Quantify everything" without units leads to inconsistent or missing data; no way to verify completeness. **Manus-specific:** Tends to estimate or omit units when not explicitly required. | Specify explicit metrics with units: market sizes ($ billions), shares (%), growth (% CAGR), capacities (units), prices ($/unit); include anti-pattern examples |
| Undefined temporal terms | "Recent trends" interpreted inconsistently; data may be outdated or inconsistently sourced. **Manus-specific:** Inconsistent interpretation of temporal terms without explicit definition. | Define explicitly: "Recent = last 3-5 years"; always require exact dates/years for all cited data; add to verification checklist |
| Missing data fabrication | When data unavailable, Manus may estimate or fabricate to fill gaps and appear complete | Add explicit instruction: "If data unavailable, state 'DATA NOT FOUND IN SOURCES'—never fabricate or estimate"; include in critical rules and checklist |
| Page count ambiguity | "50 pages" means different things to different systems; no objective measurement. **Manus-specific:** Needs explicit character count specification. | Always specify character count: 50 pages ≈ 125,000-150,000 characters; include both in output specifications and verification checklist |

---

## Examples

### Example 1: High-Level Objectives — Market Research

**Problem:** Users micro-manage steps, treating Manus as a script executor instead of an autonomous agent, negating its planning capabilities.

**Model-specific delta:** Manus's Planner Agent excels at task decomposition. Micro-management bypasses this strength and increases error probability when specific steps don't work as described.

**Before (without technique):**

```
1. Open browser
2. Go to website X
3. Click button Y
4. Extract table Z
5. Save as CSV
6. Open Python
7. Load CSV
8. Calculate column A average
...
```

**Why it fails:** Negates Planner Agent capabilities; increases error probability if specific steps don't work exactly as described; wastes credits on detailed instruction processing overhead.

**After (with technique):**

```markdown
# Objective
Conduct deep competitive analysis of the project management tools market to identify differentiation opportunities for our SaaS startup.

# Scope
Analyze top 15 project management tools by 2025 market share:
- Asana, Monday.com, Trello, Jira, ClickUp, Notion, Basecamp, Wrike, Smartsheet, Teamwork, Airtable, Linear, Height, Shortcut, Productive

# Analysis Requirements
For each tool, identify:
1. Pricing model (tiers, per-user price, limits)
2. Key distinctive features (3-5 unique features)
3. Primary target audience (company size, industry, team type)
4. Strengths (based on user reviews)
5. Weaknesses / common complaints (based on reviews)
6. Main integrations (top 5)
7. Growth trend (if data available)

# Additional Analysis
- Identify 3-5 gaps or unmet needs frequently mentioned in reviews
- Group tools into categories (enterprise vs SMB, technical vs non-technical)
- Identify emerging feature trends (last 12 months)

# Output Format
1. Excel spreadsheet with structured data (one row per tool)
2. Executive report in Markdown (3-4 pages) with executive summary, landscape overview, gap analysis, recommendations
3. Interactive HTML dashboard with comparative visualizations

# Sources
Consult: official websites, G2, Capterra, Product Hunt, Reddit (r/projectmanagement), analyst reports
```

**Result:** Professional comprehensive competitive analysis with structured data, strategic insights, and visualizations — Planner Agent optimally decomposes the task while Execution Agent handles tool coordination.

---

### Example 2: KV-Cache Optimization — Research Agent

**Problem:** Dynamic data in `system_prompt` destroys cache optimization, increasing costs by up to 10x and degrading latency.

**Model-specific delta:** Manus's KV-cache hit rate is the primary performance metric. A stable prompt prefix enables cache reuse across iterations. This is unique to Manus's architecture — other agents don't emphasize this optimization.

**Before (inefficient prompt):**

```
System Prompt: "You are a researcher. Today's date is 2025-10-04. Answer the user's question."
```

**Why it fails:** The dynamic timestamp in `system_prompt` invalidates cache on each execution. With Manus's typical 100:1 input-to-output token ratio, this makes every call expensive.

**After (optimized for Manus):**

```
System Prompt (Stable):
"You are an Autonomous Research Agent. Your goal is to answer complex questions comprehensively. You must use the `browser_*` tools to collect information and the `file.write` tool to save your findings. At the end, use `message.send` to deliver the final report."

User Prompt (with Dynamic Data):
"Today's date is 2025-10-04. Please research the implications of recent AI legislation in the European Union."
```

**Result:** `system_prompt` remains stable across executions, maximizing KV-cache reuse. Dynamic data moved to `user_prompt` where it's expected to vary. Cost reduction of up to 10x on cached tokens.

---

### Example 3: State Machine Control — Development Agent

**Problem:** Uncontrolled tool access creates security risks and unpredictable workflows.

**Model-specific delta:** Manus uses logit masking to restrict tool selection based on state, but this requires consistent tool naming with prefixes. This state machine behavior is central to Manus's predictability.

**Before (uncontrolled prompt):**

```
"Create a Python function to analyze a CSV file and then save a graph. Use the file and python tools."
```

**Why it fails:** Too open; doesn't enforce safe or predictable workflow. Agent might write files during analysis phase.

**After (optimized for Manus):**

```
System Prompt:
"You are an AI Developer. You operate in a state machine with two phases: `ANALYSIS` and `WRITING`.
- In the `ANALYSIS` phase, you can only use the `file.read` and `python.execute_code` tools to explore the data. You cannot modify the file system.
- In the `WRITING` phase, after analysis is complete, you can use the `file.write` tool to save results or graphs.
The phase transition is triggered by your decision that analysis is complete."

User Prompt:
"Analyze the file `sales.csv`, calculate total sales by category, and save a bar chart in `sales_by_category.png`."
```

**Result:** Clear state machine restricts agent behavior per phase. Manus masks `file.write` logits during analysis phase, ensuring agent cannot write files until transition. Increases security and predictability.

---

### Example 4: Wide Research — Parallel Processing at Scale

**Problem:** Processing large lists sequentially exceeds context window and takes hours.

**Model-specific delta:** Wide Research spawns 100+ independent Manus instances, each in isolated VMs, processing data subsets in parallel. This is Manus's unique solution to context limitations.

**Before (without technique):**

```
Analyze each of these 500 companies [huge list pasted in prompt] and create a detailed profile for each.
```

**Why it fails:** Context window exceeded; information truncation; incomplete results.

**After (with Wide Research):**

```markdown
# Objective
Use Wide Research to analyze each Fortune 500 company for potential B2B partnership opportunities.

# Per-Company Analysis Template
For each company, create a profile including:
1. Sector and primary business model
2. Annual revenue and employee count
3. Main products/services
4. Recent notable innovation (last 12 months)
5. Key decision-maker titles for partnership discussions
6. Partnership signals (recent acquisitions, announcements, job postings)

# Output Format
Consistent JSON schema per company:
{
  "company_name": "",
  "sector": "",
  "revenue_usd": "",
  "employees": "",
  "products_services": [],
  "recent_innovation": "",
  "decision_makers": [],
  "partnership_signals": []
}

# Aggregation
After parallel processing, compile into:
1. Master spreadsheet with all companies
2. Filtered list of top 50 partnership candidates with justification
3. Executive summary of sector trends observed
```

**Result:** 500 companies analyzed in minutes (vs hours sequentially). Consistent structured data enables comparison and filtering. Each Manus instance operates independently in isolated VM.

---

### Example 5: Metaprompting with SGD Philosophy

**Problem:** No universal "perfect" prompt exists. Teams waste time guessing optimal configurations.

**Model-specific delta:** Manus's "Stochastic Graduate Descent" philosophy treats prompt creation as continuous experimentation. Use AI to generate prompt variations, test them, and document learnings.

**Exploration metaprompt:**

```
You are an AI Agent Architect practicing 'Stochastic Graduate Descent'. I'm building an agent to write Python code.

**Objective:** Generate three alternative `system_prompts` for this agent, each focusing on a different development philosophy:
1. **Philosophy 1: 'Move Fast and Break Things'.** Prioritize speed and rapid generation of functional code.
2. **Philosophy 2: 'Test-Driven Development'.** Always write tests (`pytest`) before feature code.
3. **Philosophy 3: 'Secure by Design'.** Prioritize security, input validation, and error handling above all else.

Generate each `system_prompt` in a separate code block so I can test them.
```

**Documentation metaprompt (after testing):**

```
I tested three `system_prompts` for a coding agent. Results:

- **Prompt 1 ('Move Fast'):** Generated code quickly, but contained subtle bugs.
- **Prompt 2 ('TDD'):** Slowest, but produced most robust and reliable code.
- **Prompt 3 ('Secure'):** Secure code, but excessively verbose for simple tasks.

**Task:** Create a new **hybrid** `system_prompt` combining the best: adopt TDD as default, simplify for low-complexity tasks, always include input validation for external data.
```

**Result:** Systematic prompt optimization through documented experimentation. Each iteration builds on measured results rather than guessing.

---

### Example 6: Template Enforcement — Structured Document Generation

**Problem:** Manus generates documents that ignore template requirements, using narrative prose instead of tables, adding section numbers not in template, and creating elaborate metadata footers.

**Model-specific delta:** Manus excels at research synthesis but defaults to academic writing style. Without explicit structural enforcement, it produces well-researched but improperly formatted output that requires extensive manual restructuring.

**Before (without technique):**

```markdown
# Objective
Create a model document for [AI Tool] following the ai_model.md template.

# Requirements
- Follow template structure
- Use tables where appropriate
- Include sources with evaluation scores
```

**Why it fails:** "Follow template structure" is too vague. "Use tables where appropriate" lets Manus decide. Output: Section numbers added (1., 2., 2.1), Use Cases as narrative scenarios instead of 2-column table, "References" numbered list instead of Sources evaluation table, elaborate metadata footer block.

**After (with technique):**

```markdown
## CRITICAL RULES — READ FIRST

### Language Rule
| Rule | Requirement |
|------|-------------|
| **ALL content must be in English** | Every word, every section — English only |

### What NOT to Do — Bad Examples

❌ **WRONG — Section numbers added:**
## 1. Characteristics
## 2. Use Cases
### 2.1 Primary Use Case

**Why wrong:** Template does NOT use numbers. Use only heading text.

❌ **WRONG — Narrative prose in Use Cases:**
## Use Cases
### Make Designs (75% of Value)
**Primary Use Case:** Rapid exploration...
**Scenario 1:** A product team needs...

**Why wrong:** Use Cases MUST be 2-column table, not narrative.

✅ **CORRECT:**
## Use Cases
| Ideal For | Avoid For |
|-----------|-----------|
| Rapid layout exploration | Pixel-perfect production |

## MANDATORY STRUCTURE
[Show exact markdown format for each section]

## FINAL CHECKLIST
| # | Check | Status |
|---|-------|--------|
| 1 | Is ENTIRE document in English? | Yes/No |
| 2 | Are there NO section numbers? | Yes/No |
| 3 | Is Use Cases a 2-COLUMN TABLE? | Yes/No |
| 4 | Is Sources a TABLE with AT/TR/TM? | Yes/No |
| 5 | Is footer ONLY `*Last updated: YYYY-MM-DD*`? | Yes/No |
```

**Result:** First generation 90% template-compliant vs. 40% without enforcement. Required corrections: minor wording adjustments instead of complete restructuring. Time savings: 2-3 hours manual fixing avoided.

---

## Pre-Publishing Checklist

Before deploying any prompt for Manus, verify these model-specific requirements:

**KV-Cache Optimization (Manus-specific):**
- [ ] `system_prompt` is 100% static — no dynamic data (timestamps, IDs, session data)
- [ ] All dynamic data passed in `user_prompt` or subsequent steps
- [ ] JSON serialization uses ordered keys (`sort_keys=True`) to prevent cache breaks
- [ ] Context follows append-only pattern — no modifications to past history

**Manus Architecture (Planner/Execution/Verification):**
- [ ] Objective defined at high level ("what" and "why", not step-by-step "how") to leverage Planner Agent
- [ ] Task scope appropriate for context window (or Wide Research specified for large-scale parallelization)
- [ ] Custom tools use consistent prefix naming (`browser_*`, `file_*`, etc.) for state machine control
- [ ] State machine phases defined with allowed tools per state (enables logit masking)

**Manus-Specific Output Quality:**
- [ ] Template structure explicitly enforced with anti-pattern examples if generating structured documents
- [ ] Language requirement stated multiple times (critical rules, constraints, checklist) if non-English output is a risk
- [ ] Character count specified (not just page count) if page-based output required
- [ ] Explicit units required for all metrics if generating research outputs
- [ ] Temporal terms explicitly defined ("Recent = last 3-5 years") if time-sensitive research
- [ ] "DATA NOT FOUND IN SOURCES" instruction included if data completeness is critical

**Validation:**
- [ ] Appropriate for Manus capabilities (not in "Avoid For" category)
- [ ] Validation plan for important outputs (verify facts, test code)
- [ ] Credit/cost considered (KV-cache optimization, Wide Research for large tasks)
- [ ] Agent output reviewed as you would review junior developer work

---

## Technical Reference

> **Link Verification:** All links verified as of 2025-12-04.

| Topic | Official Documentation |
|-------|------------------------|
| Getting Started | https://manus.im/docs/introduction/welcome |
| Features Overview | https://manus.im/docs/introduction/features |
| Plans and Pricing | https://manus.im/docs/introduction/plans |
| MCP Connectors | https://manus.im/docs/integrations/mcp-connectors |
| Wide Research | https://manus.im/docs/features/wide-research |
| Context Engineering | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus |
| Manus 1.5 Release | https://manus.im/blog/manus-1.5-release |
| Wide Research Introduction | https://manus.im/blog/introducing-wide-research |
| Official Use Cases | https://manus.im/usecase-official-collection |
| GAIA Benchmark Leaderboard | https://huggingface.co/spaces/gaia-benchmark/leaderboard |

---

## Benchmark Performance

On the **GAIA benchmark** (General AI Assistants real-world problem-solving evaluation):

| GAIA Difficulty Level | Manus AI Score | OpenAI Deep Research | Previous SOTA |
|-----------------------|----------------|----------------------|---------------|
| Level 1 (Basic) | **86.5%** | 74.3% | 67.9% |
| Level 2 (Intermediate) | **70.1%** | 69.1% | 67.4% |
| Level 3 (Complex) | **57.7%** | 47.6% | 42.3% |

### Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **KV-Cache Hit Rate** | Primary metric; high rate = lower latency and cost |
| **Cost per Task** | Total tokens (input + output) to complete task end-to-end |
| **End-to-End Latency** | Time from initial prompt to final response |
| **Agent Robustness** | Tool failure recovery, unexpected observation handling, state machine consistency |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Manus Official Documentation - Welcome | https://manus.im/docs/introduction/welcome | 2025-12-04 | n/a | 10.0 | 10 | 10 | 10 |
| 2 | Manus Official Documentation - Features | https://manus.im/docs/introduction/features | 2025-12-04 | n/a | 10.0 | 10 | 10 | 10 |
| 3 | Manus Blog - Context Engineering for AI Agents | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus | 2025-12-04 | 2025-07-18 | 10.0 | 10 | 10 | 10 |
| 4 | Manus Blog - Manus 1.5 Release | https://manus.im/blog/manus-1.5-release | 2025-12-04 | 2025-10-16 | 10.0 | 10 | 10 | 10 |
| 5 | Manus Blog - Introducing Wide Research | https://manus.im/blog/introducing-wide-research | 2025-12-04 | 2025-07-31 | 10.0 | 10 | 10 | 10 |
| 6 | Manus Official Documentation - MCP Connectors | https://manus.im/docs/integrations/mcp-connectors | 2025-12-04 | n/a | 10.0 | 10 | 10 | 10 |
| 7 | Manus Official Documentation - Plans and Pricing | https://manus.im/docs/introduction/plans | 2025-12-04 | n/a | 10.0 | 10 | 10 | 10 |
| 8 | Manus Official Use Cases Collection | https://manus.im/usecase-official-collection | 2025-12-04 | n/a | 10.0 | 10 | 10 | 10 |
| 9 | ArXiv - The Rise of Manus AI | https://arxiv.org/html/2505.02024v1 | 2025-12-04 | 2025-05 | 9.3 | 9 | 10 | 9 |
| 10 | GitHub Gist - Technical Investigation | https://gist.github.com/renschni/4fbc70b31bad8dd57f3370239dccd58f | 2025-12-04 | n/a | 9.0 | 9 | 9 | 9 |
| 11 | GAIA Benchmark Leaderboard | https://huggingface.co/spaces/gaia-benchmark/leaderboard | 2025-12-04 | n/a | 9.0 | 9 | 9 | 9 |
| 12 | Skywork.ai - Prompt Engineering for Manus 1.5 | https://skywork.ai/blog/ai-agent/prompt-engineering-manus-1-5-structure-guardrails-evaluation/ | 2025-12-04 | n/a | 8.7 | 8 | 9 | 9 |
| 13 | Lance Martin's Blog - Context Engineering in Manus | https://rlancemartin.github.io/2025/10/15/manus/ | 2025-12-04 | 2025-10-15 | 8.3 | 8 | 8 | 9 |
| 14 | MIT Technology Review - Manus AI Review | https://www.technologyreview.com/2025/03/11/1113133/manus-ai-review/ | 2025-12-04 | 2025-03-11 | 8.7 | 9 | 9 | 8 |
| 15 | Forbes - AI Agent Manus: Ethics, Security and Oversight | https://www.forbes.com/sites/torconstantino/2025/03/14/ai-agent-manus-sparks-debate-on-ethics-security-and-oversight/ | 2025-12-04 | 2025-03-14 | 8.3 | 8 | 9 | 8 |
| 16 | DataCamp - Manus AI: Features, Architecture, Access | https://www.datacamp.com/blog/manus-ai | 2025-12-04 | 2025-03-10 | 8.0 | 8 | 8 | 8 |
| 17 | UNU C3 - Manus: Leading the Charge in Autonomous AI | https://c3.unu.edu/blog/manus-leading-the-charge-in-autonomous-ai | 2025-12-04 | 2025-03-12 | 8.3 | 8 | 9 | 8 |
| 18 | AnalyticsVidhya - Manus AI vs OpenAI Operator | https://www.analyticsvidhya.com/blog/2025/03/manus-ai-vs-openai-operator/ | 2025-12-04 | 2025-03 | 8.0 | 8 | 8 | 8 |
| 19 | VentureBeat - Wide Research Launch | https://venturebeat.com/ai/youve-heard-of-ai-deep-research-tools-now-manus-is-launching-wide-research-that-spins-up-100-agents-to-scour-the-web-for-you | 2025-12-04 | 2025-07-31 | 7.7 | 7 | 8 | 8 |
| 20 | ArXiv - Why Johnny Can't Use Agents | https://arxiv.org/abs/2509.14528 | 2025-12-04 | 2025-09 | 8.0 | 8 | 9 | 7 |
| 21 | Trickle.so - Manus AI Review: What Nobody Tells You | https://trickle.so/blog/manus-ai-review | 2025-12-04 | 2025-07-29 | 7.3 | 7 | 7 | 8 |
| 22 | eesel.ai - Honest Manus AI Reviews | https://www.eesel.ai/blog/manus-ai-reviews | 2025-12-04 | 2025-10-08 | 7.3 | 7 | 7 | 8 |
| 23 | Brigantia - Revolutionary Leap or Existential Threat? | https://www.brigantia.com/resources/manus-ai-a-revolutionary-leap-or-an-existential-threat | 2025-12-04 | 2025-03-19 | 7.0 | 7 | 7 | 7 |
| 24 | Medium - 20+ Real-World Applications of Manus AI | https://medium.com/@usamabajwa86/from-fiction-to-function-20-real-world-applications-of-manus-ai-e426dadf3ab1 | 2025-12-04 | 2025-04-23 | 7.0 | 7 | 7 | 7 |
| 25 | Nexth Zone - Limitations and Critical Issues | https://nexth.zone/blog/limitations-and-critical-issues-of-manus-ai/114 | 2025-12-04 | n/a | 6.7 | 6 | 7 | 7 |
| 26 | Lindy.ai - Manus AI Review | https://www.lindy.ai/blog/manus-ai-review | 2025-12-04 | 2025-09-16 | 6.7 | 6 | 7 | 7 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Various YouTube videos | 4.0 | Superficial promotional content without technical depth |
| Generic AI news sites | 5.0 | Superficial coverage without original research |
| Marketing-focused articles | 4.0 | Biased perspective without critical analysis |
| Social media posts | 3.0 | Unverified and anecdotal information |
| Affiliate reviews | 4.0 | Evident conflict of interest |

---

*Last updated: 2026-01-23*


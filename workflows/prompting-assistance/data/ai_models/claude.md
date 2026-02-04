---
---

# Claude

**Version:** Claude 3.5 Sonnet (2024-10-22), Claude 3.7 Sonnet (2025-02-19), Claude 4 Opus (2025-04-16)  
**Provider:** Anthropic  
**Modality:** Text, Code, Multimodal (Vision)

---

## Characteristics

| Aspect | Value |
|--------|-------|
| Input Types | Text, Image, Code |
| Output Types | Text, Code, Structured Data (JSON/XML) |
| Context Window | 200K tokens (~150K words / 500 pages) |
| Strengths | Long-context understanding, code generation, complex reasoning (Extended Thinking), Constitutional AI safety, structured outputs, agentic workflows |
| Weaknesses | No fine-tuning available, more cautious (over-refusal edge cases), knowledge cutoff |

---

## Use Cases

| Ideal For | Avoid For |
|-----------|-----------|
| Long-form document analysis (legal, research, transcripts) | Tasks requiring fine-tuned behavior — use few-shot or RAG instead |
| Codebase analysis and security audits (entire codebase in single request) | Simple queries where Haiku would suffice (cost optimization) |
| Complex multi-step reasoning with Extended Thinking | Real-time/current information — requires RAG or tool use |
| Agent systems requiring structured outputs with guaranteed compliance | Adversarial or jailbreak-style prompting |
| Code generation, review, debugging, and refactoring | Tasks requiring model behavior override |
| Multi-document synthesis and cross-file analysis | Latency-sensitive applications with long context (2-5x slower) |
| Agentic workflows with tool use and computer use | Tasks where Constitutional AI caution would be counterproductive |

---

## Techniques

What works differently with this model vs. general practice.

> **Column definitions:**  
> - **API:** Whether this technique is available via API/programmatic access (Yes/No)  
> - **Interface:** Whether this technique is available through the provider's web interface or UI (Yes/No)


| Technique | How to Apply | When to Use | API | Interface |
|-----------|--------------|-------------|-----|-----------|
| Extended Thinking | Enable in API with `thinking: {type: "enabled", budget_tokens: N}`; access thinking via content blocks | Complex reasoning, math, strategic planning, debugging — 20-30% accuracy improvement over standard inference | Yes | n.a |
| Structured Outputs (Claude-specific) | Use tool calling with strict JSON schema and `tool_choice: {type: "tool", name: "X"}` | Agent systems, API integrations — Claude guarantees 99.9%+ format compliance vs 85-90% with prompt engineering | Yes | n.a |
| Prompt Caching (Claude-specific) | Add `cache_control: {type: "ephemeral"}` to system prompts and long documents | Repeated context (chatbots, document analysis) — Claude's ephemeral cache provides 50-90% cost savings; cache lasts 5 min inactivity | Yes | n.a |
| Long Context (200K) | Send entire document/codebase in single request rather than chunking | Cross-file analysis, document synthesis — Claude's 200K token window with uniform attention distribution preserves full context; finds cross-boundary issues | Yes | Yes |
| Context for Refusals | Add legitimate use case context when Claude refuses; explain "why" and "what for" | Security research, medical content, edge cases — Claude's Constitutional AI requires explicit context to prevent false positives on safe requests | Yes | Yes |
| Constitutional AI Alignment | Frame requests positively; explain purpose and intended outcome | All production use — work with Claude's Constitutional AI training, not against it | Yes | Yes |

---

## Pitfalls

Anti-patterns and common errors when working with this model.

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Treating Claude like GPT-4 | Misses Claude's strengths (Extended Thinking, Constitutional AI, no fine-tuning); struggles with its unique limitations | Learn Constitutional AI philosophy, Extended Thinking patterns, and RAG/few-shot alternatives |
| Prompt engineering for structured outputs | 85-95% format compliance vs 99.9%+ with Claude's Structured Outputs; extra text surrounds JSON | Use Claude's tool calling with strict schema and `tool_choice` for guaranteed compliance |
| Chunking long documents | Loses context; misses cross-file connections and vulnerabilities; breaks data flow analysis | Use Claude's 200K token context window; send entire document in one request for uniform attention |
| Adversarial prompting | Triggers refusals; fights against Constitutional AI; wastes tokens on failed attempts | Frame requests positively; provide legitimate use case context to work with Constitutional AI |
| Expecting fine-tuning | Anthropic deliberately doesn't offer fine-tuning to preserve Constitutional AI alignment | Use few-shot learning, RAG, and prompt engineering instead (see [Few-Shot Learning](../prompting_techniques/few_shot_learning.md)) |
| No prompt caching | 2-10x higher costs for repeated context; unnecessary API charges | Use Claude's ephemeral prompt caching (`cache_control: {type: "ephemeral"}`) for 50-90% savings |
| Over-relying on Constitutional AI for safety | Safety incidents in edge cases; false sense of security | Add application-level safety layers; multi-layer defense (input validation, output filtering, human review) |
| Not handling refusals | Poor UX; system failures on legitimate requests; user frustration | Detect refusals; retry with clarifying context explaining legitimate use case; implement fallback logic |
| Using wrong model tier | Overpaying for simple tasks or underperforming on complex ones | Match model to task: Haiku (simple), Sonnet (balanced), Opus (complex) |
| Ignoring thinking tokens | Unexpected costs with Extended Thinking; budget overruns | Set thinking budget; monitor thinking token usage; balance budget with task complexity |
| **Not managing verbosity** | Claude's default "chatty" behavior adds unnecessary introductory phrases ("Certainly!", "I'd be happy to help!") | Add explicit instructions: "Be concise", "Get straight to the point", "No introduction". Request structured formats (tables, lists) |
| **Providing insufficient context** | Context-dependent model produces generic responses without rich background | Provide rich contextualization: situation, objective, constraints, current strategies. Imagine explaining to human colleague |

---

## Examples

Technique implementations with before/after comparisons. Each example demonstrates how to apply a technique from the Techniques table.

### Example 1: Extended Thinking — Strategic Decision-Making

**Problem:** Business decisions require multi-step analysis, but standard inference produces superficial responses missing critical risk factors.

**Model-specific delta:** Claude's Extended Thinking allocates separate "thinking" token budget for deliberation before responding — other models require explicit chain-of-thought prompting that consumes output tokens.

**Standard approach (works for most models):**

```
Prompt: "Should we enter the European market given our current resources?"

Response: "Yes, entering the European market could be beneficial because 
it offers growth opportunities and diversification. You should consider 
local regulations and competition."
```

**Why standard approach fails with this model:** Claude can perform deeper analysis but needs explicit Extended Thinking enabled — without it, Claude defaults to concise responses that miss nuanced risk factors and quantified analysis.

**Model-specific implementation:**

```python
message = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=4096,
    thinking={
        "type": "enabled",
        "budget_tokens": 2000
    },
    messages=[{
        "role": "user",
        "content": """Analyze whether we should enter the European market.
        
        Context:
        - Current revenue: $50M annually
        - Team size: 120 people
        - Cash runway: 18 months
        - Product: B2B SaaS for healthcare
        - Current markets: US and Canada
        """
    }]
)

# Access thinking process
thinking_content = [block for block in message.content if block.type == "thinking"]
# Access final response  
response_content = [block for block in message.content if block.type == "text"]
```

**After (with model-specific technique):**

```
Thinking process (excerpt):
"Let me analyze systematically:
1. Market Analysis: European healthcare SaaS is $15B growing 12% annually
2. Resource Assessment: $50M revenue suggests ~$5-10M expansion budget
   - GDPR compliance: ~$500K-1M initial + ongoing
   - Localization: ~$300K (5 languages)
   - Sales team: ~$1M annually
   - Total first-year: ~$3-5M
3. Risk Analysis: 18-month runway + 12-18 month European sales cycle
   = revenue won't materialize before runway issues..."

Final Response:
"Based on systematic analysis, I recommend AGAINST entering the European 
market now. Key reasons:
1. Resource Constraint: $3-5M first-year costs = 60-100% of safe expansion budget
2. Cash Runway Risk: 18-month runway insufficient for 12-18 month revenue delay
3. Compliance Burden: GDPR + healthcare regulations require significant investment

Recommended Alternative: Partner with European healthcare SaaS distributor..."
```

**Result:** 20-30% higher decision quality; systematic risk identification; actionable alternative with clear revisit criteria.

---

### Example 2: Structured Outputs — Agent Systems

**Problem:** Multi-agent system where code analyzer output feeds test generator; JSON parsing fails 10-15% of time with prompt engineering.

**Model-specific delta:** Claude's tool calling with `tool_choice` forces structured output in a single call — other models may require multiple passes or regex extraction.

**Standard approach (works for most models):**

```python
prompt = """Analyze this code and respond in JSON format:
{
  "complexity": "low|medium|high",
  "issues": ["list of issues"],
  "test_priority": "low|medium|high"
}

Code:
def process_payment(amount, card):
    if amount > 0:
        charge_card(card, amount)
        return True
    return False
"""

# Response often includes:
"Here's my analysis:
{
  \"complexity\": \"medium\",
  \"issues\": [\"No input validation\"],
  \"test_priority\": \"high\"
}
The code needs improvement..."
```

**Why standard approach fails with this model:** Claude's Constitutional AI training makes it naturally explanatory — it wants to help by adding context around JSON, which breaks downstream parsing.

**Model-specific implementation:**

```python
schema = {
    "type": "object",
    "properties": {
        "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "test_priority": {"type": "string", "enum": ["low", "medium", "high"]}
    },
    "required": ["complexity", "issues", "test_priority"]
}

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[{
        "name": "code_analysis",
        "description": "Output code analysis result",
        "input_schema": schema
    }],
    tool_choice={"type": "tool", "name": "code_analysis"},
    messages=[{"role": "user", "content": f"Analyze this code:\n\n{code}"}]
)

analysis = message.content[0].input  # Guaranteed to match schema
```

**After (with model-specific technique):**

```python
# Guaranteed output (always parseable):
{
  "complexity": "medium",
  "issues": ["No input validation for amount", "No error handling for charge_card"],
  "test_priority": "high"
}
# Zero parsing errors; downstream agent always receives valid input
```

**Result:** 99.9%+ format compliance vs 85-90%; zero parsing errors; reliable multi-agent pipelines.

---

### Example 3: Long Context — Codebase Security Analysis

**Problem:** Chunking approach misses vulnerabilities spanning multiple files because data flow is broken.

**Model-specific delta:** Claude's 200K token context window with even attention distribution allows full codebase analysis in single request — other models may have smaller windows or "lost in the middle" attention issues.

**Standard approach (works for most models):**

```python
chunks = split_codebase_into_chunks(codebase, chunk_size=4000)
vulnerabilities = []
for chunk in chunks:
    result = analyze_chunk(chunk)
    vulnerabilities.extend(result)

# MISSED: SQL injection vulnerability where:
# - File A (chunk 1): User input collection
# - File B (chunk 3): Query construction  
# - File C (chunk 5): Database execution
# Connection broken by chunking boundaries
```

**Why standard approach fails with this model:** Claude can hold entire codebase in context with uniform attention — chunking unnecessarily fragments the analysis and loses cross-file data flow tracing.

**Model-specific implementation:**

```python
codebase_content = load_entire_codebase()  # ~150K tokens

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": f"""<instructions>
Analyze this entire codebase for security vulnerabilities.
Pay special attention to data flow across files.
</instructions>

<codebase>
{codebase_content}
</codebase>

<output_format>
For each vulnerability:
- Severity (critical/high/medium/low)
- Description
- Affected files with line numbers
- Data flow trace (if spans multiple files)
- Remediation recommendation
</output_format>"""
    }]
)
```

**After (with model-specific technique):**

```
CRITICAL: SQL Injection Vulnerability

Data Flow:
1. user_controller.py:45 - User input collected (username parameter)
2. auth_service.py:123 - Username passed to validation (no sanitization)
3. database.py:89 - Raw SQL query: f"SELECT * FROM users WHERE username = '{username}'"

Remediation:
Use parameterized queries in database.py:89:
cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
```

**Result:** 40% more vulnerabilities found vs chunking; full cross-file data flow tracing; detection of 3 critical issues missed by chunking.

---

### Example 4: Handling Refusals with Context

**Problem:** Legitimate security research request gets refused due to Constitutional AI pattern matching.

**Model-specific delta:** Claude's Constitutional AI is more refusal-prone on edge cases than other models — requires explicit context about legitimate use to disambiguate.

**Standard approach (works for most models):**

```
Prompt: "Show me how SQL injection works with examples of vulnerable code."

Claude Response: "I can't provide examples of how to exploit SQL injection 
vulnerabilities, as this could be used for harmful purposes..."
```

**Why standard approach fails with this model:** Claude's Constitutional AI training causes it to refuse requests that pattern-match to harmful use cases, even when the intent is defensive security research.

**Model-specific implementation:**

```
Prompt: """I'm a security engineer conducting a security audit of our application. 
I need to understand SQL injection vulnerabilities to:
1. Identify them in our codebase
2. Write tests to prevent them
3. Train our development team

Please explain SQL injection with code examples showing:
- Vulnerable code patterns
- How the vulnerability works
- Secure code patterns that prevent it

This is for defensive security purposes to protect our users."""
```

**After (with model-specific technique):**

```
Claude Response: "I'd be happy to help with your security audit. Here's an 
educational explanation of SQL injection for defensive purposes:

VULNERABLE CODE:
```python
username = request.form['username']
query = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(query)
```

HOW THE VULNERABILITY WORKS:
If an attacker inputs: admin' OR '1'='1
The query becomes: SELECT * FROM users WHERE username = 'admin' OR '1'='1'
This returns all users because '1'='1' is always true.

SECURE CODE:
```python
username = request.form['username']
query = "SELECT * FROM users WHERE username = ?"
cursor.execute(query, (username,))
```

The parameterized query treats input as data, not code..."
```

**Result:** Legitimate request fulfilled with comprehensive defensive security guidance.

---

## Checklists

### Pre-Publishing Checklist

Before finalizing any prompt for this model, verify Claude-specific requirements:

- [ ] Instructions are explicit and positive (what to do, not what to avoid) — works with Constitutional AI alignment
- [ ] Extended Thinking enabled for complex reasoning tasks (`thinking: {type: "enabled", budget_tokens: N}` set appropriately)
- [ ] Claude's Structured Outputs used for JSON/format-critical responses (tool calling with `tool_choice` for 99.9%+ compliance)
- [ ] Context provided for potential refusal edge cases (explain legitimate use case to work with Constitutional AI)
- [ ] Claude's ephemeral prompt caching implemented for repeated content (`cache_control: {type: "ephemeral"}`)
- [ ] Safety layers added beyond Constitutional AI (input validation, output filtering, human review)
- [ ] Verbosity managed if needed (explicit "Be concise" instructions to counter Claude's "chatty" default)
- [ ] Long context (200K tokens) utilized when appropriate instead of chunking

### Proficiency Checklist

Track progression from Intermediate → Expert → Pro.

#### Intermediate Level

Comfortable with basics, learning optimization.

- [ ] Understand Constitutional AI and how it makes Claude different from other models
- [ ] Know Claude's limitations (no fine-tuning, more cautious, knowledge cutoff)
- [ ] Choose appropriate model (Haiku/Sonnet/Opus) for different task complexities
- [ ] Make basic API calls using Anthropic SDK with proper error handling
- [ ] Structure prompts appropriately
- [ ] Implement Claude's ephemeral prompt caching for cost optimization (50-90% savings)
- [ ] Use few-shot learning to customize Claude behavior without fine-tuning

#### Expert Level

Production-ready, can debug issues and optimize performance.

- [ ] Handle refusals gracefully with context and retry logic
- [ ] Implement Extended Thinking for complex reasoning tasks (20-30% accuracy gain)
- [ ] Use Claude's Structured Outputs (tool calling with `tool_choice`) for guaranteed format compliance (99.9%+)
- [ ] Use long context (200K tokens) for document/codebase analysis
- [ ] Build model routing logic (Haiku → Sonnet → Opus based on complexity)
- [ ] Log prompts, responses, and thinking content for debugging
- [ ] Monitor token usage, costs, and latency across models
- [ ] Add multi-layer safety beyond Constitutional AI
- [ ] Implement streaming for better UX

#### Pro Level

Architectural decisions, edge cases, teaching others.

- [ ] Design multi-agent systems with Structured Outputs and reliable pipelines
- [ ] Build RAG systems integrated with Claude for current information
- [ ] Implement tool use (function calling) for external data access
- [ ] Create custom evaluation frameworks for domain-specific quality metrics
- [ ] Optimize end-to-end latency for production systems
- [ ] Build monitoring and alerting for production Claude deployments
- [ ] Train teams on Claude best practices and common pitfalls
- [ ] Design multi-model routing strategies for cost-performance optimization

---

## Technical Reference

Links to official documentation for model-specific mechanisms. Link to the most specific page available.

> **Link Verification:** All links verified 2025-12-04.

| Topic | Official Documentation |
|-------|------------------------|
| API Reference | [docs.anthropic.com](https://docs.anthropic.com/) |
| Extended Thinking | [Extended Thinking Guide](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) |
| Structured Outputs (Tool Use) | [Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) |
| Prompt Caching | [Prompt Caching Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |
| Long Context Windows | [100K Context Announcement](https://www.anthropic.com/news/100k-context-windows) |
| Constitutional AI | [Constitutional AI Research](https://www.anthropic.com/research/constitutional-ai) |
| Security Best Practices | [Mitigating Jailbreaks](https://docs.anthropic.com/en/docs/build-with-claude/mitigating-jailbreaks-prompt-injections) |
| Claude 3.5 Sonnet Model Card | [Model Card PDF](https://www-cdn.anthropic.com/fed9cc193a14b84131812372d8d5857f8f304c52/Model_Card_Claude_3_Addendum.pdf) |
| Computer Use | [Computer Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/computer-use) |
| Prompt Engineering | [Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering) |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Anthropic Claude Documentation | https://docs.anthropic.com/ | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 2 | Extended Thinking Guide | https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 3 | Tool Use GA Announcement | https://www.anthropic.com/news/tool-use-ga | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 4 | Prompt Engineering for Business Performance | https://www.anthropic.com/news/prompt-engineering-for-business-performance | 2025-12-04 | 2025-11-22 | 9.7 | 10 | 10 | 9 |
| 5 | Constitutional AI Research Paper | https://www.anthropic.com/research/constitutional-ai | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 6 | Prompt Caching Documentation | https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 7 | Mitigating Jailbreaks and Prompt Injections | https://docs.anthropic.com/en/docs/build-with-claude/mitigating-jailbreaks-prompt-injections | 2025-12-04 | 2025-11-22 | 9.7 | 10 | 10 | 9 |
| 8 | Claude 3.5 Sonnet Model Card | https://www-cdn.anthropic.com/fed9cc193a14b84131812372d8d5857f8f304c52/Model_Card_Claude_3_Addendum.pdf | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |
| 9 | AWS Claude Deployment Patterns | https://aws.amazon.com/blogs/machine-learning/claude-code-deployment-patterns-and-best-practices-with-amazon-bedrock/ | 2025-12-04 | 2025-11-22 | 8.3 | 9 | 9 | 7 |
| 10 | Computer Use Documentation | https://docs.anthropic.com/en/docs/build-with-claude/computer-use | 2025-12-04 | 2025-11-22 | 10.0 | 10 | 10 | 10 |


---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| CloudBuckle Cost Optimization Blog | 5.7 | Low topic match (TM:5) — focuses on billing/costs, not prompting techniques |
| Various Medium/Dev.to articles | 4.0-5.5 | Low authority (AT:3-5) — individual contributors without verification |
| Reddit r/ClaudeAI discussions | 4.3 | Low trustability (TR:4) — user-generated, unverified claims |
| Xenoss LLM Platform Guide | 5.3 | Low topic match (TM:4) — comparison focus, not implementation guidance |


---

*Last updated: 2025-12-04*


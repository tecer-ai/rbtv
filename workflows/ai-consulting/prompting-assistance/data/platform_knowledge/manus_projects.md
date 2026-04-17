# Manus Projects - Platform Interface Knowledge

**Platform:** Manus AI (manus.im)
**Feature:** Projects — autonomous agent runtime
**Purpose:** Enable AI agents to guide users through creating and configuring Manus Projects with effective master instructions for autonomous task execution.

---

## 1. Interface Overview

### What Makes Manus Different

Manus is NOT a conversational chatbot. It is an **autonomous agent runtime** — the only web platform with capabilities comparable to Cursor or Claude Code. It creates cloud environments, runs scripts, invokes sub-agents, browses the web, and produces finished artifacts while the user is offline.

### Architecture

| Component | Role |
|-----------|------|
| **Planner** | Decomposes user goals into executable steps |
| **Executor agents** | Run tasks in parallel sandboxes |
| **Knowledge Agent** | Retrieves and synthesizes information |
| **Browser Operator** | Navigates web pages, fills forms, clicks elements |
| **Verifier** | Validates output quality before delivery |

### Main Components

| Component | Purpose |
|-----------|---------|
| **Projects** | Persistent workspaces with master instructions and knowledge base |
| **Tasks** | Individual jobs within a project; inherit project config |
| **Cloud Sandbox** | Linux container with browser, file system, Python, terminal |
| **Wide Research** | Parallel sub-agents in separate sandboxes for multi-source research |
| **Manus's Computer** | Live visibility into agent actions; allows user intervention |

---

## 2. Projects Feature

| Aspect | Details |
|--------|---------|
| **Master instructions** | Custom instructions per project; inherited by all tasks |
| **Knowledge base** | Upload files via UI or API |
| **File capacity** | 100+ files in context |
| **Inheritance** | New tasks automatically inherit project instructions and files |
| **Collaboration** | Projects can be shared; team members see shared instructions and knowledge; tasks remain private unless shared |
| **Updates** | File updates apply to new tasks only; instruction updates apply on next message |

---

## 3. Capabilities

| Capability | Description |
|-----------|-------------|
| **Autonomous execution** | Tasks run asynchronously; user can disconnect and return |
| **Cloud sandbox** | Full Linux environment: terminal, file system, Python, package installation |
| **Multi-agent orchestration** | Planner → Executor → Verifier pipeline with parallel execution |
| **Web browsing** | Browser Operator for navigation, forms, clicks |
| **Code execution** | Run scripts, install tools, process data |
| **File generation** | PPTX, PDF, websites, spreadsheets, images — actual files, not text suggestions |
| **Wide Research** | Sub-agents in separate sandboxes; 100+ sources in parallel |
| **Recurring tasks** | Scheduled tasks for 24/7 agentic workflows |
| **Memory** | ~95% recall accuracy across sessions |

---

## 4. Models

Multi-model orchestration: Manus uses Claude, Qwen, and other models internally. Users don't select models — the system routes automatically.

| Version | Availability |
|---------|-------------|
| **Manus 1.6** | Pro |
| **Manus 1.6 Max** | Pro |
| **Manus 1.6 Lite** | Free (Agent Mode) |

---

## 5. Pricing

| Plan | Price | Credits/month | Concurrent Tasks |
|------|-------|---------------|------------------|
| **Free** | $0 | 300 daily refresh; 1,000 signup bonus | 1 |
| **Pro (tier 1)** | $20/mo | 4,000 | 20 |
| **Pro (tier 2)** | $40/mo | 8,000 | 20 |
| **Team** | $20/seat/mo | Shared pool | 2 per member |

- 17% discount for annual billing
- Credits do not roll over; add-on credits do not expire
- Simple tasks: ~10–20 credits; complex tasks: 500–900+ credits
- Per-task cost roughly $2 (about 1/10 of OpenAI Deep Research)

---

## 6. AI Agent Guidance

### Instructions Format

Manus instructions are fundamentally different from conversational platforms. They must be **goal-oriented**, not **conversational**.

**Structure for master instructions:**
1. **Goal** — What this project produces (deliverables, not behavior)
2. **Context** — Domain knowledge, constraints, audience
3. **Process** — Steps to follow or methodologies to apply
4. **Quality criteria** — What "done" looks like; self-verification checks
5. **Output format** — File types, structure, naming conventions
6. **Constraints** — What to avoid, boundaries, resource limits

**Key differences from chatbot instructions:**
- Focus on deliverables, not personality
- Define success criteria (Manus self-verifies via its Verifier agent)
- Specify file output formats explicitly (PPTX, PDF, etc.)
- Include process steps — Manus follows them more literally than conversational AI
- Don't include conversational patterns (greetings, follow-ups) — Manus is task-oriented

### When to Recommend Manus

| Use Case | Why Manus |
|----------|----------|
| Autonomous multi-step tasks | Runs while user is offline |
| Finished deliverables (slides, reports, apps) | Produces actual files, not text |
| Deep multi-source research (100+ sources) | Wide Research with parallel sub-agents |
| MVP/prototype validation | Builds functional prototypes end-to-end |
| Recurring workflows (weekly reports, digests) | Scheduled tasks |
| Tasks requiring code execution, scripting | Full Linux sandbox |

### When NOT to Recommend Manus

| Use Case | Better Alternative |
|----------|-------------------|
| Daily conversational assistant | ChatGPT (memory, personality) |
| Document analysis with persistent context | Claude Projects (200K–1M tokens) |
| Quick, simple tasks | Gemini Gems (lightweight, instant) |
| Image generation | ChatGPT (DALL-E) |
| Google ecosystem integration | Gemini (native Drive/Docs/Gmail) |
| Regulated industries (HIPAA, SOC 2) | Not compliant — use enterprise platforms |

---

## 7. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Not production-ready | Best for research, analysis, prototyping | Use for validation, not deployment |
| Stability issues under load | "Busy" errors during peak times | Retry or schedule off-peak |
| CAPTCHAs and paywalls | Browser Operator blocked by anti-bot measures | Provide data as uploaded files instead |
| Credit consumption | Complex tasks burn 500–900+ credits | Scope tasks tightly; avoid debugging loops |
| Less conversational depth | Weak for back-and-forth dialogue | Use ChatGPT/Claude for conversation |
| Not compliant (HIPAA, SOC 2) | Cannot use for regulated data | Use enterprise-grade platforms |
| Debugging loops | Agent may retry failed approaches, burning credits | Monitor via "Manus's Computer"; intervene early |

---

## 8. Quality Checklist

- [ ] Master instructions define deliverables, not personality
- [ ] Success criteria specified (what "done" looks like)
- [ ] Output file formats explicitly stated
- [ ] Process steps included for complex tasks
- [ ] Constraints and boundaries defined
- [ ] Credit budget estimated (simple: 10–20, complex: 500–900)
- [ ] Knowledge base files uploaded and relevant
- [ ] Tested with a simple task before running complex ones

---

*Last updated: 2026-03-16*

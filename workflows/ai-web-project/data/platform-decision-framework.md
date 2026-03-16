# Platform Decision Framework

Use this framework to recommend the best AI platform for the user's assistant project.

---

## Fundamental Architecture Split

Before matching signals, understand the two categories of AI web platform:

| Category | Platforms | How It Works |
|----------|-----------|--------------|
| **Conversational assistants** | ChatGPT, Claude, Gemini | Chat interfaces with persistent instructions and file context. User drives the conversation; AI responds. Tools (search, code interpreter) are add-ons. |
| **Agent runtimes** | Manus | Cloud sandbox with file system, terminal, browser, Python, and multi-agent orchestration. Closest web equivalent to Cursor or Claude Code. Creates environments, runs scripts, invokes sub-agents, produces finished artifacts autonomously. Not available on any other web/phone app. |

**First question to answer:** Does the user need a conversational partner or an autonomous executor?

---

## Decision Signals

### Conversational Platforms

| Signal | Best Platform | Why |
|--------|---------------|-----|
| Daily personal use, conversational, memory across chats | ChatGPT | Project-level memory persists; strongest for casual/daily assistants |
| Creative output (images, voice, canvas) | ChatGPT | DALL-E, voice mode, canvas — no equivalent on other platforms |
| External API integrations (Zapier, HubSpot, etc.) | ChatGPT | Custom Actions + GPT Store ecosystem |
| Large document sets (500+ pages) | Claude | 200K token context (token-based, not file-count capped); paid tiers up to 500K |
| Code-heavy / GitHub-connected | Claude | Direct GitHub repo integration in Projects; file sync |
| Professional/technical persistent assistants | Claude | Artifacts (versioned, editable code/docs); strongest structured output |
| Client/consulting isolation | Claude | One project per client; clean context separation |
| Live web research / real-time data | Gemini | Google Search grounding built-in; citations, reduced hallucination |
| Google ecosystem (Drive, Docs, Sheets, Gmail) | Gemini | Drive side panel, Docs/Sheets sync, native integration |
| Quick, repetitive tasks (rewrites, summaries, templates) | Gemini | Gems are lightweight, 1-2 min setup; optimized for high-frequency single-task |
| Massive context (1M+ tokens) | Gemini | 1M token context on Pro tier; largest window available |
| Education / curriculum-aligned | Gemini | Premade gems, file-based curriculum upload |

### Agent Runtime

| Signal | Best Platform | Why |
|--------|---------------|-----|
| Needs to create environments, run scripts, install packages | Manus | Cloud Linux sandbox with terminal, file system, Python — no other web platform offers this |
| Multi-agent orchestration (planner, executor, verifier) | Manus | Built-in sub-agent architecture; tasks are planned, executed, and verified autonomously |
| Produces finished deliverables (slides, apps, websites, reports) | Manus | Generates actual files (PPTX, PDF, full websites), not just text suggestions |
| Autonomous execution (runs while user is offline) | Manus | Asynchronous tasks; user can disconnect and return to finished work |
| Deep multi-source research (100+ sources in parallel) | Manus | Wide Research with parallel sub-agents in separate sandboxes |
| Recurring/scheduled workflows | Manus | Scheduled tasks and 24/7 agentic execution |
| MVP/prototype validation | Manus | Builds functional prototypes end-to-end |

---

## Platform Tradeoffs

| Platform | Strongest At | Weakest At |
|----------|-------------|------------|
| **ChatGPT** | Multimodal (images, voice, canvas), daily use, integrations | Smaller context window, 8K char instruction limit for Custom GPTs |
| **Claude** | Large doc analysis, code, artifacts, structured professional work | No image generation, no live web search, rate limits on Pro |
| **Gemini** | Google ecosystem, live search, massive context, quick tasks | No full workspace/project history like ChatGPT/Claude Projects, weaker PDF handling |
| **Manus** | Agent runtime (sandbox, scripts, sub-agents, deliverables) — the only web app with Cursor/Claude Code-like capabilities | Less conversational depth, credit-based cost, stability issues under load, not for regulated industries |

---

## Platform-Specific Constraints

### ChatGPT Projects
- Instructions: 8,000 character limit (Custom GPTs) — Projects have more room
- Files: 10 per Custom GPT; 25-40 per Project depending on plan
- Memory: project-level memory persists across chats
- Plans: Free (limited), Plus ($20/mo), Pro ($200/mo)

### Claude Projects
- Instructions: no hard character limit — token-based
- Files: unlimited count, 200K token context total; 30MB per file
- GitHub: direct repo connection with file sync
- Plans: Free (5 projects), Pro ($20/mo), Max ($100-200/mo)

### Gemini Gems
- Instructions: custom instructions per Gem
- Files: up to 10 per Gem; Google Docs/Sheets sync with live updates
- Search: Google Search grounding for real-time data
- Plans: Free (limited), AI Pro ($19.99/mo), AI Ultra ($249.99/mo)

### Manus Projects
- Instructions: master instructions per project; inherited by all tasks
- Files: 100+ files in context; upload via UI or API
- Execution: cloud sandbox with browser, file system, Python, terminal
- Async: tasks run while user is offline; live visibility via "Manus's Computer"
- Plans: Free (300 daily credits), Pro ($20-40/mo, 4K-8K credits), Team ($20/seat/mo)
- Cost per task: simple ~10-20 credits, complex ~500-900+ credits

---

## Recommendation Protocol

1. Ask about the use case (what problem does this assistant solve?)
2. Ask about interaction model: conversational (back-and-forth) or task-based (give goal, get result)?
3. Ask about frequency (daily? weekly? ad-hoc?)
4. Ask about data sources (documents? web? Google services? code repos?)
5. Ask about output type (text? images? code? structured data? finished deliverables?)
6. Ask about autonomy: does the user want to guide each step, or delegate and review?
7. Match signals to the table above
8. Present recommendation with reasoning
9. If signals point to multiple platforms, present tradeoffs and let user decide

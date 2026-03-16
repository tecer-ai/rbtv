# Claude Projects - Platform Interface Knowledge

**Platform:** Claude (claude.ai)
**Feature:** Projects
**Purpose:** Enable AI agents to guide users through creating and configuring Claude Projects with effective system prompts and knowledge bases.

---

## 1. Interface Overview

### Main Components

| Component | Purpose |
|-----------|---------|
| **Project Instructions** | Custom instructions (role, tone, guidelines) that shape all chats in the project |
| **Project Knowledge** | Uploaded files and connected sources that Claude uses as context |
| **Chat History** | Conversations grouped within the project |
| **Model Selector** | Choose which Claude model to use |
| **Artifacts** | Standalone content windows for code, HTML, React, SVG, diagrams |

---

## 2. Available Models

| Model | Context Window | Plan Access |
|-------|---------------|-------------|
| **Opus 4.6** | 1M tokens | Pro, Max |
| **Sonnet 4.6** | 1M tokens | Free, Pro, Max |
| **Haiku 4.5** | 200K tokens | Free, Pro, Max |

- 1M context became GA on March 13, 2026 — standard pricing, no long-context premium
- 1M context supports up to 600 images or PDF pages per request
- 200K tokens ≈ 500 pages of text
- Enterprise plans can access 500K tokens on some models

---

## 3. File Uploads

### Limits

| Context | Per-file limit | Count limit | Notes |
|---------|---------------|-------------|-------|
| **Chat** | 30 MB | 20 files per conversation | Shares context window |
| **Projects** | 30 MB | Unlimited files | RAG activates when over context limit |

### Supported File Types

PDF, DOCX, TXT, RTF, ODT, EPUB, HTML, Markdown, CSV, TSV, JSON, PPTX (added Aug 2025), JPEG, PNG, GIF, WebP

### RAG Behavior

- RAG activates automatically when project knowledge nears the context limit
- Expands effective capacity by ~10×
- Available on ALL plans, including Free

---

## 4. Integrations

### GitHub

Available on all plans, including Free.

| Retrieved | NOT Retrieved |
|-----------|---------------|
| File names and contents | Commit history |
| Branch content | Pull requests |
| | Issues and metadata |

Configure which files Claude analyzes. Sync fetches latest changes.

### Google Drive

Available on Pro, Max, Team, Enterprise. Private projects only.

| Supported | NOT Supported |
|-----------|---------------|
| Google Docs (up to 10 MB, text only) | Google Sheets |
| Live sync with Drive | Google Slides |
| | Images within docs |

### Google Workspace Connectors

Gmail, Calendar, and Drive connectors available on all plans. Enterprise gets Google Docs Cataloging with RAG-powered indexed search.

---

## 5. Artifacts

| Capability | Details |
|-----------|---------|
| **Types** | Markdown docs, code snippets, single-page HTML, SVG, diagrams, flowcharts, interactive React components |
| **AI-powered artifacts** | Embed Claude via text-based API; run on Anthropic infrastructure; usage counts against subscription |
| **Persistent storage** | Pro, Max, Team, Enterprise — 20 MB per artifact, text-only input |
| **MCP integration** | Pro+ — connect to Asana, Google Calendar, Slack, custom MCP servers |
| **Availability** | All plans (AI-powered + storage require Pro+) |

---

## 6. Memory and Context

| Mechanism | Behavior |
|-----------|----------|
| **Project isolation** | Each project keeps its own context; no cross-project sharing |
| **Auto memory** | Claude periodically extracts patterns and preferences from conversations; stored separately from chat history; editable in Settings |
| **Project instructions** | Loaded for every chat in the project |
| **Context overflow** | With code execution enabled, Claude can summarize earlier messages when approaching the limit; full history remains referenceable |

---

## 7. Pricing

| Plan | Price | Projects | Notes |
|------|-------|----------|-------|
| **Free** | $0 | 5 max | RAG available; Haiku + Sonnet |
| **Pro** | $17/mo (annual) / $20/mo | Unlimited | Includes Claude Code, Cowork; all models |
| **Max** | $100/mo (5×) / $200/mo (20×) | Unlimited | Priority access, higher output limits |
| **Team Standard** | $20/seat (annual) / $25 (monthly) | Unlimited | 5-user min; project sharing |
| **Team Premium** | $100/seat (annual) / $125 (monthly) | Unlimited | 5× usage vs standard |
| **Enterprise** | Custom ($20/seat + usage) | Unlimited | HIPAA, SSO, SCIM, audit logs, Google Docs cataloging |

---

## 8. AI Agent Guidance

### Instructions Format

No documented character limit for project instructions (token-based). Effective patterns:

- Use for role, tone, and persistent guidelines — NOT for task-specific instructions (put those in the chat)
- XML tags work well for section boundaries (Claude respects XML structure)
- State constraints explicitly with NEVER/ALWAYS
- Use 1–3 examples for nuanced behavior
- Force output structure (JSON, bullets, rubrics) when needed
- System/safety constraints override user requests — design with this hierarchy in mind

### Knowledge Base Best Practices

- Use clear, descriptive filenames — Claude uses filenames to identify context
- Structure documents with headers and sections for better retrieval
- RAG helps with large knowledge bases but retrieval is relevance-based — critical rules must be in project instructions, not files
- GitHub integration is best for code-heavy projects with ongoing changes

### When to Recommend Claude Projects

| Use Case | Why Claude |
|----------|-----------|
| Large document analysis (500+ pages) | 200K–1M token context; RAG for overflow |
| Code-heavy work with GitHub repos | Direct GitHub integration with file sync |
| Professional/technical persistent assistants | Artifacts for versioned, editable output |
| Client/consulting isolation | One project per client; clean separation |
| Structured, complex system prompts | No character limit; XML tag support |

### When NOT to Recommend Claude Projects

| Use Case | Better Alternative |
|----------|-------------------|
| Image generation | ChatGPT (DALL-E) |
| Live web search / real-time data | Gemini (Google Search grounding) |
| Google ecosystem integration | Gemini (Drive, Docs, Gmail native) |
| Daily casual assistant with memory | ChatGPT (better memory UX) |
| Autonomous task execution | Manus (agent runtime) |

---

## 9. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Cross-project isolation | No shared context between projects | Duplicate instructions or use organization-wide settings (Team/Enterprise) |
| Google Drive: no Sheets/Slides | Can't analyze spreadsheets or presentations from Drive | Upload files directly |
| Rate limits on Pro | ~45 messages per 5 hours (varies) | Batch questions; use Haiku for simple queries |
| No image generation | Can't produce images | Use ChatGPT for visual output |
| No live web search | Can't access current information | Use Gemini or pair with external search |
| Instruction enforcement inconsistency | Project instructions not always followed precisely | Repeat critical rules; use explicit NEVER/ALWAYS |

---

## 10. Recent Changes (Late 2025 – March 2026)

| Date | Change |
|------|--------|
| March 13, 2026 | 1M context GA for Opus 4.6 and Sonnet 4.6; 600 media items per request |
| March 12, 2026 | Interactive charts, diagrams, visualizations in artifacts |
| March 11, 2026 | Claude for Excel and PowerPoint — shared context across files; Skills |
| Feb 2026 | Opus 4.6 released |
| Jan 2026 | Cowork launched (macOS); Windows followed in Feb |
| Late 2025 | Projects and Artifacts made available on Free plan; RAG for all plans |

---

## 11. Quality Checklist

- [ ] Project instructions define role, tone, and guardrails clearly
- [ ] Critical rules in instructions, not in knowledge files
- [ ] XML tags used for section boundaries in complex prompts
- [ ] NEVER/ALWAYS constraints explicitly stated
- [ ] Output format specified
- [ ] 1–3 examples included for nuanced behavior
- [ ] File naming is descriptive and structured
- [ ] Model selected appropriately (Opus for complex, Haiku for speed)
- [ ] Tested with sample conversations

---

*Last updated: 2026-03-16*

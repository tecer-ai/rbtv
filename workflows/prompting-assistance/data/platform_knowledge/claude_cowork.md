# Claude Cowork - Platform Interface Knowledge

**Platform:** Claude Desktop App (Cowork)
**Feature:** Cowork — autonomous desktop agent
**Purpose:** Enable AI agents to guide users through configuring Claude Cowork with instructions, connectors, plugins, and scheduled tasks.
**Research Date:** 2026-03-16
**Status:** Cowork is in research preview as of March 2026.

---

## 1. Interface Overview

### What Is Cowork

Cowork is Claude's desktop application that operates as an autonomous agent on local files and connected services. Unlike claude.ai Projects (browser-based chat with persistent knowledge), Cowork runs tasks autonomously on the user's machine — reading files, executing multi-step workflows, and connecting to external services.

### Cowork vs Projects

| Dimension | Cowork (Desktop) | Projects (claude.ai) |
|-----------|-------------------|----------------------|
| **Environment** | Local file system + connected services | Browser-based chat |
| **Execution** | Autonomous, multi-step | Conversational, user-guided |
| **Files** | Reads/writes local folders | Uploads to project knowledge |
| **Integrations** | MCP connectors (50+) | GitHub, Google Drive |
| **Instructions** | Global + folder-level | Per-project |
| **Scheduling** | Built-in (/schedule) | Not available |
| **Sub-agents** | Orchestrator–worker delegation | Not available |

### Current Status

- **Research preview** — not GA
- **Availability:** macOS (Jan 2026) + Windows (full parity Feb 10, 2026)
- **Plans:** All paid plans (Pro, Max, Team, Enterprise)

### Timeline

| Date | Event |
|------|-------|
| Jan 12, 2026 | Launch (Max on macOS) |
| Jan 16, 2026 | Pro subscribers |
| Jan 23, 2026 | Team and Enterprise |
| Feb 10, 2026 | Windows with feature parity; global and folder instructions |

---

## 2. Available Models

| Model | Role | Context | Notes |
|-------|------|---------|-------|
| **Opus 4.6** | Most capable; orchestrator | 1M tokens (GA Mar 13, 2026) | Agent teams, adaptive thinking, 128K output tokens |
| **Sonnet 4.5** | Balanced default; worker sub-agents | 1M tokens (GA Mar 13, 2026) | Coding, writing, analysis |
| **Haiku 4.5** | Fast, cost-effective sub-agent execution | Standard | Summaries, extraction, high-volume tasks |

### Plan Access

- **Free:** Haiku, Sonnet
- **Pro/Max:** All models including Opus
- **Scheduled tasks:** Optional model selection per task

---

## 3. Instructions

| Level | Scope | Added |
|-------|-------|-------|
| **Global** | Apply to all tasks across all folders | Feb 10, 2026 |
| **Folder-level** | Apply only when working in a specific folder | Feb 10, 2026 |

Both carry into every session. Editable from chat.

### Global Instructions Content

- Role and expertise
- Constraints (e.g. units, language)
- Output format (bullets vs prose, headings)
- Writing style and tone

### Folder Instructions Content

- Project-specific context
- Loaded automatically by folder

---

## 4. Connectors

MCP-based integrations for external services. All connectors are free.

### First-Party Connectors

Google Workspace (Gmail, Drive, Calendar), Microsoft 365, GitHub, Slack. Require only OAuth or API key authentication.

### Community Catalog

47+ connectors available via claudecowork.io (community-maintained):

| Category | Connectors |
|----------|------------|
| **Communication** | Slack, Microsoft Teams, Discord, Gmail, Outlook, Zoom (beta), Telegram (beta) |
| **Storage** | Google Drive, Dropbox, OneDrive |
| **Productivity** | Notion, Trello, Asana, Monday.com, Airtable, Todoist, Evernote |
| **Calendar** | Google Calendar |
| **Development** | GitHub, GitLab, Jira, Linear, VS Code (beta), Docker (beta), Postman (beta), AWS (beta), Vercel (beta), Database |
| **Sales/CRM** | Apollo (beta), Clay (beta), Outreach (beta) |
| **Finance/Legal** | DocuSign, FactSet (beta), MSCI (beta), LegalZoom (beta), Harvey (beta) |
| **Other** | Similarweb (beta), WordPress |

**System tools:** File System, Terminal, Clipboard, Screenshot, PDF Tools, OCR Engine (beta), Browser Automation (beta), System Monitor (beta).

### Connector Types

- **Prebuilt integrations:** First-party, auth-only setup
- **Remote MCP servers:** Cloud-hosted tools and data
- **MCP Apps:** Interactive UI components (charts, forms, maps) in chat
- **MCP Bundles (MCPB):** Local MCP servers packaged as desktop extensions
- **Connectors Directory:** Verified MCP servers
- **Self-serve local MCP:** Via plugins using `.mcp.json`

### Authentication

OAuth or API key, depending on the connector. Claude only sees what the user can access.

---

## 5. Plugins

Plugins bundle MCP connectors, skills, slash commands, and sub-agents into reusable packages.

| Aspect | Details |
|--------|---------|
| **Official plugins** | 11 (Productivity, Enterprise search, Sales, Finance, Legal, Marketing, Customer support, Data, Product management, Biology research, Plugin Create) |
| **Storage** | Saved locally |
| **Org-wide sharing** | Planned, not yet available |
| **Custom plugins** | Users can create their own |
| **Directory** | claude.com/plugins-for/cowork |

### Extensibility Options

- **Remote MCP servers:** Cloud-hosted tools and data
- **MCP Apps:** Interactive UI (charts, forms, maps) in chat
- **MCP Bundles (MCPB):** Local MCP servers packaged as desktop extensions
- **Self-serve local MCP:** Via plugins using `.mcp.json`, submitted to the plugin directory

---

## 6. Scheduling

| Feature | Details |
|---------|---------|
| **Command** | `/schedule` |
| **Frequencies** | Hourly, daily, weekly, weekdays, manual trigger |
| **Requirement** | App must be open and machine must be awake; skipped runs execute when app is reopened |
| **Plans** | Pro, Max, Team, Enterprise |
| **Use cases** | Daily briefings, weekly reports, competitor monitoring, file organization, team updates |

### How to Create via /schedule

1. Open Cowork → New task (or existing task)
2. Type `/schedule`
3. Describe the task and click "Let's go"
4. Answer Claude's questions (including multiple choice)
5. Confirm by clicking "Schedule"

### How to Create via Scheduled Tasks Page

1. Click "Scheduled" in the sidebar
2. Click "+ New task"
3. Enter: task name, description, prompt, frequency, optional model, optional folder
4. Click "Save"

---

## 7. Sub-agents

| Aspect | Details |
|--------|---------|
| **Pattern** | Orchestrator (Opus) decomposes task → worker sub-agents (Sonnet/Haiku) execute in parallel |
| **Isolation** | VM sandboxing, folder-scoped access |
| **Delegation** | Automatic based on task complexity |
| **Performance** | Multi-agent setups outperform single-agent on complex tasks by over 90% (Anthropic internal tests) |

### Technical Stack

- **Cowork Coordinator:** Decomposes tasks and assigns work
- **Sandboxed workspace (VM):** Isolated execution (e.g. Apple Virtualization Framework on macOS)
- **MCP:** Standard tool connectivity
- **Sub-agent coordination:** Parallel execution with inspection

---

## 8. Context Architecture

### Security Model ("Guardrails by Construction")

1. **VM-first sandboxing:** Tasks run in isolated VMs
2. **Folder-scoped permissions:** Explicit directory access
3. **Tiered access control:** Limits unauthorized actions and prompt injection

### Context from Connectors

- Connectors expose tools and data via MCP
- Claude can search, read, and act on data from connected tools in the same session
- Connectors can be combined (e.g. Drive + local files)
- Read-only vs read-write can be configured per connector

### Design Principles

- Transparency: progress tracking, plan visibility
- User control: approval gates before significant actions
- Outcome-oriented execution instead of pure chat

---

## 9. Pricing and Plan Requirements

### Individual Plans

| Plan | Price | Cowork |
|------|-------|--------|
| **Free** | $0 | No |
| **Pro** | $17/mo (annual) or $20/mo (monthly) | Yes |
| **Max 5x** | From $100/mo | Yes, 5× usage vs Pro |
| **Max 20x** | From $200/mo | Yes, 20× usage vs Pro |

### Team and Enterprise

| Plan | Price | Cowork |
|------|-------|--------|
| **Team** | $30/user/mo ($25/user/mo annual) | Yes; admin controls over plugins |
| **Enterprise** | Custom | Yes; SSO, SCIM, audit logs, HIPAA-ready option |

Cowork is included in paid plans; no separate fee. Requires paid subscription due to compute needs.

---

## 10. AI Agent Guidance

### Instructions Format

- Global instructions: role, tone, preferences that apply everywhere
- Folder instructions: project-specific context, conventions, file handling rules
- Keep instructions actionable — Cowork executes autonomously, so vague guidance leads to unpredictable behavior
- Specify what "done" looks like for multi-step tasks
- Include explicit constraints on file modifications (what to touch, what to never modify)

### When to Recommend Cowork

| Use Case | Why Cowork |
|----------|-----------|
| Local file processing (batch rename, organize, analyze) | Direct file system access |
| Multi-service workflows (Gmail → Drive → Slack) | MCP connectors |
| Recurring tasks (daily reports, digests) | /schedule |
| Complex multi-step tasks requiring delegation | Sub-agent orchestration |

### When NOT to Recommend Cowork

| Use Case | Better Alternative |
|----------|-------------------|
| Simple Q&A or conversation | Claude Projects (browser) |
| Sharing instructions with a team | Claude Projects or Custom GPTs |
| Mobile use | Claude app or ChatGPT |
| Needs to work without local machine running | Manus (cloud-based agent) |

---

## 11. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Research preview | Features may change; not production-ready | Monitor Anthropic updates |
| Machine must be running | Scheduled tasks fail if laptop is closed | Use Manus for always-on tasks |
| No org-wide plugin sharing yet | Each user configures independently | Share connector configs manually |
| Community connectors are unofficial | Quality and maintenance vary | Prefer first-party connectors for critical workflows |

---

## 12. New Features and Changes in 2026

| Date | Change |
|------|--------|
| Jan 12 | Cowork research preview launch (Max, macOS) |
| Jan 16 | Pro access |
| Jan 23 | Team and Enterprise access |
| Feb 10 | Windows release; global and folder instructions |
| Mar 13 | 1M context GA for Opus 4.6 and Sonnet 4.5 |

Other 2026 additions:
- Scheduled tasks with `/schedule`
- Expanded connectors (DocuSign, Apollo, Clay, Outreach, FactSet, MSCI, LegalZoom, Harvey, Similarweb, WordPress)
- "Customize" menu for plugins, skills, connectors
- Slash commands with structured forms
- OpenTelemetry for admin monitoring (Enterprise)
- Claude in Chrome integration for browser automation

---

## 13. Quality Checklist

- [ ] Global instructions define role and persistent preferences
- [ ] Folder instructions add project-specific context
- [ ] Constraints on file access are explicit (what to read, what to never modify)
- [ ] Scheduled tasks have clear success criteria
- [ ] Connector authentication is configured and tested
- [ ] Sub-agent behavior verified for complex workflows

---

## Sources

[1] Cowork: Claude Code power for knowledge work — https://claude.com/product/cowork — TS:9.7 (AT:10 TR:9 TM:10)

[2] Overview - Claude.ai Documentation — https://claude.com/docs/cowork/overview — TS:9.7 (AT:10 TR:9 TM:10)

[3] Introducing Cowork | Claude — https://claude.com/blog/cowork-research-preview — 2026-01-12 — TS:9.7 (AT:10 TR:9 TM:10)

[4] Claude vs Claude Code vs Cowork — Which One Do You Actually Need? — https://medium.com/@yunusemresalcan — TS:6.3 (AT:5 TR:6 TM:8)

[5] Claude Cowork vs Claude Code (2026) — What's the Difference? — https://pluginsforcowork.com/guides/cowork-vs-claude-code/ — TS:7.0 (AT:6 TR:6 TM:9)

[6] Connectors overview - Claude.ai Documentation — https://claude.com/docs/connectors/overview — TS:9.7 (AT:10 TR:9 TM:10)

[7] Claude Cowork Connectors & Integrations (2026) — https://pluginsforcowork.com/guides/cowork-connectors/ — TS:7.0 (AT:6 TR:6 TM:9)

[8] Connectors: MCP for Everyone | Agent Factory — https://agentfactory.panaversity.org — TS:6.7 (AT:6 TR:7 TM:7)

[9] Claude Cowork Connectors: Apps & Integrations — https://claudecowork.io/connectors — TS:7.3 (AT:6 TR:7 TM:9)

[10] Plugins overview - Claude.ai Documentation — https://claude.com/docs/plugins/overview — TS:9.7 (AT:10 TR:9 TM:10)

[11] Customize Cowork with plugins | Claude — https://claude.com/blog/cowork-plugins — TS:9.7 (AT:10 TR:9 TM:10)

[12] Context Management Strategies for Claude CoWork — https://iceberglakehouse.com — TS:7.0 (AT:6 TR:7 TM:8)

[13] Plus, you can now set global and folder instructions — https://www.threads.com/@claudeai — TS:8.0 (AT:9 TR:8 TM:7)

[14] Introducing Cowork | Claude (blog) — https://claude.com/blog/cowork-research-preview — TS:9.7 (AT:10 TR:9 TM:10)

[15] Schedule recurring tasks in Cowork | Claude Help Center — https://support.claude.com/en/articles/13854387 — TS:9.7 (AT:10 TR:9 TM:10)

[16] The Architecture of Scale: Anthropic's Sub-Agents — https://medium.com/codetodeploy — TS:6.3 (AT:5 TR:6 TM:8)

[17] Claude Cowork Architecture: Synthesis — https://micheallanham.substack.com — TS:7.0 (AT:6 TR:7 TM:8)

[18] Claude Cowork Architecture: How Anthropic Built a Desktop Agent — https://medium.com/@Micheal-Lanham — TS:6.3 (AT:5 TR:6 TM:8)

[19] Claude Cowork: Architecture, Capabilities, and Usage Overview — https://www.tensorlake.ai — TS:7.0 (AT:6 TR:7 TM:8)

[20] Choosing the right Claude model — https://claude.com/resources/tutorials/choosing-the-right-claude-model — TS:9.3 (AT:10 TR:9 TM:9)

[21] 1M context GA for Opus 4.6 and Sonnet 4.6 — https://claude.com/blog/1m-context-ga — 2026-03-13 — TS:9.7 (AT:10 TR:9 TM:10)

[22] Use Cowork on Team and Enterprise plans — https://support.claude.com/en/articles/13455879 — TS:9.7 (AT:10 TR:9 TM:10)

[23] Plans & Pricing | Claude — https://claude.com/pricing — TS:9.7 (AT:10 TR:9 TM:10)

[24] Claude Cowork Pricing — https://coworkerai.io/pricing — TS:7.0 (AT:6 TR:7 TM:8)

[25] Use Cowork on Team and Enterprise plans — https://support.claude.com/en/articles/13455879 — TS:9.7 (AT:10 TR:9 TM:10)

[26] Cowork 2026 Updates — http://claudelab.net/en/articles/cowork/whats-new-2026 — TS:7.0 (AT:6 TR:7 TM:8)

[27] Cowork and plugins for teams across the enterprise | Claude — https://claude.com/blog/cowork-plugins-across-enterprise — TS:9.7 (AT:10 TR:9 TM:10)

---

## Data Gaps

- **Exact first-party connector list:** Official docs name Google Drive, Gmail, Calendar, GitHub, Slack, Microsoft 365; full catalog is in the Connectors Directory (URL not verified).
- **Model selection in Cowork:** Scheduled tasks allow optional model choice; default model for regular Cowork tasks not documented.
- **Org-wide plugin sharing:** "Coming in the weeks ahead" per plugins docs; no specific date.

---

*Last updated: 2026-03-16*

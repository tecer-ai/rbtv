# Claude Cowork - Platform Interface Knowledge

**Platform:** Claude Desktop App (Cowork)
**Feature:** Cowork — autonomous desktop agent
**Purpose:** Enable AI agents to guide users through configuring Claude Cowork with instructions, connectors, plugins, and scheduled tasks.

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

---

## 2. Available Models

| Model | Role |
|-------|------|
| **Opus 4.6** | Orchestrator for complex tasks; sub-agent decomposition |
| **Sonnet 4.5** | General tasks; worker sub-agents |
| **Haiku 4.5** | Fast sub-agent execution |

1M context GA for Opus 4.6 and Sonnet 4.6 as of March 13, 2026.

---

## 3. Instructions

| Level | Scope | Added |
|-------|-------|-------|
| **Global** | Apply to all tasks across all folders | Feb 10, 2026 |
| **Folder-level** | Apply only when working in a specific folder | Feb 10, 2026 |

Both carry into every session. Editable from chat.

---

## 4. Connectors

MCP-based integrations for external services.

### First-Party Connectors

Google Workspace (Gmail, Drive, Calendar), Microsoft 365, GitHub, Slack.

### Community Catalog

47+ connectors available via claudecowork.io (community-maintained):
Slack, Notion, Jira, DocuSign, Linear, Figma, Todoist, and many more.

### Authentication

OAuth or API key, depending on the connector. All connectors are free.

---

## 5. Plugins

Plugins bundle MCP connectors, skills, slash commands, and sub-agents into reusable packages.

| Aspect | Details |
|--------|---------|
| **Official plugins** | 11 (Sales, Finance, Legal, Engineering, HR, Marketing, etc.) |
| **Storage** | Saved locally |
| **Org-wide sharing** | Planned, not yet available |
| **Custom plugins** | Users can create their own |

---

## 6. Scheduling

| Feature | Details |
|---------|---------|
| **Command** | `/schedule` |
| **Frequencies** | Hourly, daily, weekly, weekdays, manual trigger |
| **Requirement** | App must be open and machine must be awake |
| **Use cases** | Recurring reports, digest emails, data processing |

---

## 7. Sub-agents

| Aspect | Details |
|--------|---------|
| **Pattern** | Orchestrator (Opus) decomposes task → worker sub-agents (Sonnet/Haiku) execute in parallel |
| **Isolation** | VM sandboxing, folder-scoped access |
| **Delegation** | Automatic based on task complexity |

---

## 8. AI Agent Guidance

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

## 9. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Research preview | Features may change; not production-ready | Monitor Anthropic updates |
| Machine must be running | Scheduled tasks fail if laptop is closed | Use Manus for always-on tasks |
| No org-wide plugin sharing yet | Each user configures independently | Share connector configs manually |
| Community connectors are unofficial | Quality and maintenance vary | Prefer first-party connectors for critical workflows |

---

## 10. Quality Checklist

- [ ] Global instructions define role and persistent preferences
- [ ] Folder instructions add project-specific context
- [ ] Constraints on file access are explicit (what to read, what to never modify)
- [ ] Scheduled tasks have clear success criteria
- [ ] Connector authentication is configured and tested
- [ ] Sub-agent behavior verified for complex workflows

---

*Last updated: 2026-03-16*

# ChatGPT Projects & Custom GPTs - Platform Interface Knowledge

**Platform:** ChatGPT (chatgpt.com)
**Feature:** Projects and Custom GPTs
**Purpose:** Enable AI agents to guide users through creating and configuring ChatGPT Projects and Custom GPTs with effective system prompts.

---

## 1. Interface Overview

### Main Components

| Component | Purpose |
|-----------|---------|
| **Projects** | Persistent workspaces that group chats, files, and instructions around a topic |
| **Custom GPTs** | Standalone assistants with fixed instructions, knowledge files, and optional API actions |
| **GPT Store** | Marketplace for sharing and discovering Custom GPTs |

### Projects vs Custom GPTs

| Dimension | Projects | Custom GPTs |
|-----------|----------|-------------|
| **Primary use** | Long-running work with shared context | Repeatable workflows with consistent behavior |
| **Instructions** | No documented character limit | 8,000 character limit |
| **Files** | 5–40 per project (by plan) | 10 per GPT (lifetime) |
| **Memory** | Project-level memory, shared across chats | No persistent memory across conversations |
| **Sharing** | Team collaboration (Business/Enterprise) | GPT Store, team links, public distribution |
| **Model selection** | User-selectable | GPT-4 Turbo (no user choice) |
| **Custom Actions** | Not available | API integrations via OpenAPI spec |

---

## 2. Available Models

| Model | Availability | Notes |
|-------|-------------|-------|
| **GPT-5.4 Pro** | Pro only | Highest capability |
| **GPT-5.4 Thinking** | Plus, Pro | Reasoning model |
| **GPT-5.3** | Free, Go, Plus, Pro | General purpose |
| **o3 / o3-pro** | Pro only | Advanced reasoning |
| **GPT-4o** | Retired Feb 13, 2026 | No longer available |

Custom GPTs use GPT-4 Turbo; Pro/o-series models are NOT available in Custom GPTs.

---

## 3. Built-in Tools

| Tool | What It Does | Plan Availability |
|------|-------------|-------------------|
| **DALL-E** | Image generation and editing via natural language | Plus, Pro |
| **Canvas** | Shared workspace for editing docs and code | Plus, Pro |
| **Voice Mode** | Voice conversations | Plus, Pro |
| **Code Interpreter** | Run Python code, analyze spreadsheets/CSVs | Plus, Pro |
| **Web Browsing** | Real-time web search for current information | All plans |
| **Deep Research** | Multi-step research with citations | Plus (limited), Pro |
| **Agent Mode** | Autonomous multi-step task execution | Pro |

---

## 4. Memory System

| Behavior | Description |
|----------|-------------|
| **Project-only memory** | Chats within a shared project use project-scoped memory |
| **Default memory** | Non-project chats use global memory (Plus/Pro) |
| **Free tier** | Short-term continuity only |
| **Cross-chat persistence** | Project context (files, instructions) shared across all project chats; individual chat history is NOT reliably referenced across chats |

---

## 5. File Management

### Upload Limits by Plan

| Plan | Files per day/window | Files per project | Max per file | Max tokens per text file |
|------|---------------------|-------------------|-------------|------------------------|
| **Free** | 3 per day | 5 | 512 MB | 2M tokens |
| **Go** | 80 per 3 hours | 25 | 512 MB | 2M tokens |
| **Plus** | 80 per 3 hours | 25 | 512 MB | 2M tokens |
| **Pro** | Unlimited | 40 | 512 MB | 2M tokens |
| **Business** | Unlimited | 40 | 512 MB | 2M tokens |

### Custom GPT Files
- 10 files per GPT (lifetime limit)
- Knowledge files use relevance-based retrieval — critical instructions must stay in the main instructions field

### Connected Apps
- Google Drive, Slack, 60+ apps on Business/Enterprise plans
- Apps are usable within Projects

---

## 6. Pricing

| Plan | Price | Key Features |
|------|-------|-------------|
| **Free** | $0 | GPT-5.3, web browsing, 3 file uploads/day, no Projects creation |
| **Go** | $8/mo | Projects, Custom GPTs, GPT-5.3, extended uploads |
| **Plus** | $20/mo | GPT-5.4, voice, DALL-E, Deep Research, Canvas |
| **Pro** | $200/mo | Unlimited GPT-5, o3/o3-pro, Agent Mode, no peak limits |
| **Business** | $25/seat/mo (annual) | Shared workspace, admin controls, no data training |
| **Enterprise** | Custom | Enterprise security, compliance, data controls |

---

## 7. AI Agent Guidance

### Instructions Format (Custom GPTs)

The 8,000 character limit is the primary constraint. Effective patterns:

- Lead with identity and role in the first paragraph
- Use numbered rules for behavior constraints
- Place NEVER/ALWAYS rules prominently — they get followed more reliably
- Use knowledge files for reference data that doesn't fit in 8K chars
- Avoid vague instructions ("be helpful") — be specific ("respond in 3 bullet points max")

### Instructions Format (Projects)

No documented character limit. Use for:
- Project-scoped context and role definition
- Persistent guidelines across all chats in the project
- File references and conventions

### When to Recommend ChatGPT

| Use Case | Why ChatGPT |
|----------|-------------|
| Daily personal assistant | Memory persistence, conversational |
| Creative work (images, voice) | DALL-E, Canvas, Voice Mode |
| External integrations | Custom Actions, 60+ connected apps |
| Team collaboration | Shared projects, GPT Store |
| Casual/non-technical users | Most intuitive interface |

### When NOT to Recommend ChatGPT

| Use Case | Better Alternative |
|----------|-------------------|
| Large document analysis (500+ pages) | Claude (200K+ token context) |
| Code with GitHub integration | Claude (direct repo sync) |
| Google ecosystem integration | Gemini (Drive, Docs, Gmail) |
| Autonomous task execution | Manus (agent runtime) |

---

## 8. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| 8K char instruction limit (Custom GPTs) | Can't fit complex system prompts | Use knowledge files for overflow; keep critical rules in instructions |
| No Pro/o-series in Custom GPTs | GPTs limited to GPT-4 Turbo | Use Projects for model flexibility |
| Custom GPTs can't be used inside Projects | Two separate systems | Choose one per use case |
| No persistent memory in Custom GPTs | Context resets each conversation | Use Projects instead for memory |
| Consumer plans may train on data | Privacy concern | Opt out in settings; use Business/Enterprise |
| Custom GPT knowledge retrieval is relevance-based | May miss critical instructions | Keep must-follow rules in the instructions field, not in files |

---

## 9. Quality Checklist

- [ ] Instructions under 8,000 characters (Custom GPTs)
- [ ] Identity and role defined in first paragraph
- [ ] NEVER/ALWAYS rules explicitly stated
- [ ] Output format specified (length, structure, tone)
- [ ] Knowledge files used for reference data, not critical instructions
- [ ] Edge cases addressed (off-topic, ambiguous input)
- [ ] Tested with sample conversations

---

*Last updated: 2026-03-16*

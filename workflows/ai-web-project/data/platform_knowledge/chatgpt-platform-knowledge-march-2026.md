# ChatGPT Platform Knowledge for Prompt Engineers (March 2026)

**Research Date:** 2026-03-16  
**Purpose:** Reference document for AI agents helping users write system prompts for ChatGPT Projects and Custom GPTs.

---

## Legend

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

---

## 1. ChatGPT Projects Feature

### What It Is

Projects are smart workspaces that keep chats, files, and custom instructions together for long-running work [1]. Each project groups conversations, uploaded files, and project-specific instructions in one isolated space so ChatGPT maintains context and focus [1][2].

### How It Works

- **Project instructions:** Custom instructions apply to every conversation within that project (set via Project settings → three dots → Project settings) [1]
- **Reference files:** Uploaded files remain accessible across all chats in the project [1]
- **App links:** Users can paste links from Google Drive (files/folders) or Slack (channels) as project sources [1]
- **Shared projects:** Business, Enterprise, and Edu users can share projects with teammates; shared projects automatically use project-only memory [1]
- **Branching:** Users can branch chats to explore new directions without losing the original thread [1]

### File Limits by Plan

| Plan | Files per project | Max upload at once | Collaborators (shared) |
|------|-------------------|--------------------|------------------------|
| Free | 5 | 10 | 5 |
| Go, Plus | 25 | 10 | 10 |
| Edu, Pro, Business, Enterprise | 40 | 10 | 100 (Pro); workspace-dependent (Business/Edu) |

*Source: [1] OpenAI Help Center — Projects*

### Memory Behavior

- **Project memory:** Projects have built-in memory that remembers all chats and files within the project [1]
- **Project-only memory:** When enabled (at creation), ChatGPT uses only conversations within that project; saved memories from outside are not referenced; chats cannot reference conversations outside the project [1]
- **Default memory:** With default memory, ChatGPT can reference saved memories and other project chats; for non-Enterprise plans, chats can also reference non-project conversations unless the other project uses project-only memory [1]
- **Shared projects:** Automatically set to project-only memory; cannot be reverted [1]

### Availability

Projects are available to **all free and paid subscription types globally** [1]. Shared projects require Business, Enterprise, or Edu.

---

## 2. Custom GPTs

### Instruction Limits

- **8,000 character limit** for the instructions field in the Configure tab [3][4]
- Workaround: Use knowledge files to supplement instructions; content is pulled based on relevance during conversations (not guaranteed to appear) [4]

### File Uploads (Knowledge)

- **10 files per GPT** for the lifetime of that GPT [5] *(Note: Creating a GPT FAQ states "up to 20 files" [6] — verify current limit in product)*
- 512MB hard limit per file [5]
- Text/document files: 2M tokens per file [5]
- CSV/spreadsheets: ~50MB per file [5]
- Images: 20MB per image [5]
- Per-user cap: 10GB; per-organization cap: 100GB [5]

### Actions and API Integrations

- **Custom Actions:** Third-party APIs via OpenAPI schema; define endpoints, parameters, and descriptions [6]
- **Apps:** Business and Enterprise/Edu workspaces can connect approved external apps to GPTs; Apps and Actions are mutually exclusive — enabling Apps replaces the Actions section [6]
- Apps-enabled GPTs cannot be published to the public GPT Store; available only in company GPT store [6]

### Model Selection

- Most live models are available for Custom GPTs with custom actions, **except** Pro-series models (e.g., GPT-5.2 Pro) and o-series models [7]
- If no model is selected, the GPT defaults to the most recently launched mainline model [7]

### Capabilities (Configurable)

- Web Search, Canvas, Image Generation, Code Interpreter & Data Analysis [6]

### Creation Access

- Plus, Team, and Enterprise users can create GPTs at chatgpt.com/create or chatgpt.com/gpts/editor [6]

---

## 3. Available Models (March 2026)

### ChatGPT Model Lineup

| Model | Availability | Notes |
|-------|---------------|-------|
| GPT-5.3 | Free (limited), Go, Plus | Flagship; limited on Free |
| GPT-5.4 Thinking | Plus, Pro, Business | Advanced reasoning |
| GPT-5.4 Pro | Pro, Team, Business | Pro reasoning; slower, more capable |
| GPT-5.3-Codex | Codex surfaces | Agentic coding; not in ChatGPT [8] |
| o3, o3-pro | Pro, Team (o3-pro) | Reasoning models; o3-pro replaces o1-pro [8] |

### Retirements (February 13, 2026)

- GPT-4o, GPT-4.1, GPT-4.1 mini, o4-mini retired from ChatGPT [8]
- GPT-4o fully retired across all ChatGPT plans April 3, 2026 [7]

### Custom GPT Model Availability

- Pro-series and o-series models **not** available for Custom GPTs [7]
- Mainline models (e.g., GPT-5.x Instant, GPT-5.x) available [7]

### Context Windows (by plan)

- Free: 16K tokens [9]
- Go: 32K tokens [9]
- Plus: 32K (Instant); 256K (Thinking, manual selection) [10]
- Pro: 128K tokens [9]
- Enterprise: Expanded context for longer inputs [11]

---

## 4. Built-in Tools

| Tool | Description | Availability |
|------|-------------|--------------|
| **Web Search** | Real-time internet search with cited sources | All users [12] |
| **Canvas** | Side-by-side workspace for writing and coding; inline feedback, shortcuts | All users [13][14] |
| **DALL-E (Image Generation)** | Generate and edit images from text prompts | All users; Free: limited/slower [11][12] |
| **Voice Mode** | Hands-free conversation; spoken responses | Mobile, supported platforms [14] |
| **Advanced Voice** | Enhanced intonation, naturalness, translation | Paid users [8] |
| **Code Interpreter / Data Analysis** | Run Python in sandbox; analyze data, create visualizations | Plus and above [5][14] |
| **Deep Research** | Multi-step research across sources; cited, structured reports | Plus and above [11][12] |
| **Agent Mode** | Multi-step automation; coordinates tools, websites, code, outputs | Plus, Pro, Team [12][15] |

*Note: o3-pro does not support image generation, Canvas, or temporary chats [8].*

---

## 5. Memory System

### Project-Level Memory

- **Scope:** Project memory draws context only from conversations within the same project [1]
- **Project-only mode:** Chats do not reference saved memories or conversations outside the project [1]
- **Default mode:** Can reference saved memories and project chats; non-Enterprise plans may reference non-project conversations [1]
- **Shared projects:** Always project-only; no access to members' context outside the project [1]

### Global Memory

- **Reference saved memories:** Personal facts (name, preferences) applied across conversations [14]
- **Reference chat history:** ChatGPT can reference previous chats; project chats are prioritized when in a project [1]

### Settings Required for Project Memory

- **Enterprise:** Enable "Reference saved memories" in personal settings; Memory enabled in Workspace settings [1]
- **Other plans:** Enable "Reference saved memories" and "Reference chat history" in personal settings [1]

---

## 6. File Management

### Upload Frequency by Plan

| Plan | Upload limit |
|------|--------------|
| Free | 3 files per day [5] |
| Go | ~30 files/day or 80 files per 3-hour rolling window [9][10] |
| Plus | 80 files per 3 hours [5] |
| Pro | Unlimited (subject to abuse guardrails) [11] |

### File Size Limits (All Plans)

| Type | Limit |
|------|-------|
| General files | 512MB per file [5] |
| Text/document | 2M tokens per file [5] |
| CSV/spreadsheets | ~50MB [5] |
| Images | 20MB per image [5] |

### Supported File Types

- Documents: PDF, DOCX, Markdown, TXT, PowerPoint [5][14]
- Spreadsheets: CSV, XLSX, JSON, XML [5]
- Images [5]

### Projects File Limits — Source Discrepancy

**Projects help [1]:** Free: 5 | Go, Plus: 25 | Edu, Pro, Business, Enterprise: 40  
**File Uploads FAQ [5]:** Plus: 20 | Pro, Team, Education, Business: 40 (does not list Free/Go)

*Recommendation: Use Projects help [1] as primary; File Uploads FAQ may reflect a different or older tier structure. Verify in product.*

### Retention

- Files in chats: Retained until chat deleted; deleted within 30 days after deletion [5]
- Files in Custom GPT knowledge: Retained until GPT deleted [5]
- ADA/Document Analysis files: Duration varies by plan [5]

---

## 7. Connected Apps

### Available Integrations

- **Slack:** Search messages, threads, channels; summarize discussions; semantic search (Business+ and Enterprise+ with AI plans) [16][17]
- **Google Drive:** Sync files to ChatGPT; Pro users and Business/Enterprise; self-service setup [18]
- **Business plan:** 60+ apps including Slack, Google Drive, SharePoint, GitHub, Atlassian [11]

### Apps in Projects

- Supported for Free, Go, Plus, Pro, Business, and Teachers [1]
- Use tools menu (+) to select app or reference by name [1]
- ChatGPT may ask for confirmation before searching outside the project [1]

---

## 8. Pricing by Plan (March 2026)

| Plan | Price | Key Features |
|------|-------|--------------|
| **Free** | $0/mo | Limited GPT-5.3; limited messages, uploads, image gen; limited deep research, memory [11] |
| **Go** | $8/mo | More GPT-5.3; more messages, uploads, image creation; longer memory; may include ads [11] |
| **Plus** | $20/mo | Advanced reasoning (GPT-5.4 Thinking); Projects, tasks, custom GPTs; Codex, Sora; early access [11] |
| **Pro** | $200/mo | Unlimited GPT-5.4, file uploads; GPT-5.4 Pro; max deep research, agent mode; 128K context; research preview [11] |
| **Business** | Per user, annual | Unlimited GPT-5.4; 60+ apps; SAML SSO, MFA; GDPR/CCPA; no training on business data [11] |
| **Enterprise** | Contact sales | Expanded context; SCIM, EKM; data residency; 24/7 support; SLAs [11] |

---

## 9. Key Limitations for Prompt Engineering

### Projects

- **Instructions:** No documented character limit for project instructions; set via Project settings [1]
- **Context isolation:** Project-only memory prevents cross-project context; useful for sensitive or focused work [1]
- **Custom GPTs in projects:** A custom GPT can be invoked within a project, but custom GPTs cannot be used *as* projects with sharing [1]
- **Rate limits:** Based on subscription level [1]

### Custom GPTs

- **8,000 character instruction limit:** Primary constraint; use knowledge files to extend, but retrieval is relevance-based, not guaranteed [3][4]
- **10 files per GPT (lifetime):** Limits knowledge base size [5]
- **No Pro/o-series models:** Cannot use GPT-5.4 Pro or o3/o3-pro in Custom GPTs [7]
- **No learning from interactions:** GPTs do not learn from conversations [10]
- **Knowledge cutoff:** Model knowledge has cutoff; use Web Search for current info [10]

### General

- **Model Spec authority:** Root → System → Developer → User → Guideline; platform instructions cannot be overridden [8]
- **Peak-hour throttling:** File upload limits may be lowered during peak usage [5]
- **No visibility into project memories:** Project memory does not show a list like personal memory [1]

---

## Sources

[1] Projects in ChatGPT — https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt — Research Date: 2026-03-16 — Source: Updated 4 days ago — TS:9 (AT:10 TR:9 TM:9)

[2] ChatGPT Projects Setup Guide 2026 — https://www.mywritingtwin.com/blog/chatgpt-projects-setup-guide — Research Date: 2026-03-16 — Source: 2026 — TS:7 (AT:6 TR:7 TM:8)

[3] Why is the My GPT Instructions limited by 8000 characters — https://community.openai.com/t/why-is-the-my-gpt-instructions-limited-by-8000-characters/1006936 — Research Date: 2026-03-16 — Source: Community — TS:7 (AT:7 TR:7 TM:8)

[4] Instructions versus knowledge files in CustomGPTs — https://community.openai.com/t/instructions-versus-knowledge-files-in-customgpts/1289220 — Research Date: 2026-03-16 — Source: Community — TS:7 (AT:7 TR:7 TM:8)

[5] File Uploads FAQ — https://help.openai.com/en/articles/8555545-file-uploads-with-gpts-and-advanced-data-analysis-in-chatgpt — Research Date: 2026-03-16 — Source: Updated 2 months ago — TS:9 (AT:10 TR:9 TM:9)

[6] Creating a GPT — https://help.openai.com/en/articles/8554397-creating-a-custom-gpt — Research Date: 2026-03-16 — Source: Updated 22 days ago — TS:9 (AT:10 TR:9 TM:9)

[7] GPTs (ChatGPT Enterprise version) — https://help.openai.com/en/articles/8555535-gpts-chatgpt-enterprise-version — Research Date: 2026-03-16 — Source: Help Center — TS:8 (AT:9 TR:8 TM:8)

[8] Model Release Notes — https://help.openai.com/en/articles/9624314-model-release-notes — Research Date: 2026-03-16 — Source: Last month — TS:9 (AT:10 TR:9 TM:9)

[9] ChatGPT Go vs Plus vs Pro 2026 — https://aiprixa.com/chatgpt-go-vs-plus-vs-pro/ — Research Date: 2026-03-16 — Source: 2026 — TS:7 (AT:6 TR:7 TM:8)

[10] ChatGPT Plus Limits 2026 — https://customgpt.ai/chatgpt-plus-limits-2026/ — Research Date: 2026-03-16 — Source: 2026 — TS:7 (AT:6 TR:7 TM:8)

[11] ChatGPT Plans — https://chatgpt.com/en-US/pricing/ — Research Date: 2026-03-16 — Source: Live — TS:9 (AT:10 TR:9 TM:9)

[12] ChatGPT Tools Menu 2026 — https://ai-basics.com/chatgpt-tools-menu/ — Research Date: 2026-03-16 — Source: 2026 — TS:7 (AT:6 TR:7 TM:8)

[13] Introducing canvas — https://openai.com/index/introducing-canvas — Research Date: 2026-03-16 — Source: OpenAI blog — TS:8 (AT:9 TR:8 TM:7)

[14] ChatGPT Capabilities Overview — https://help.openai.com/en/articles/9260256-chatgpt-capabilities-overview — Research Date: 2026-03-16 — Source: Updated 2 months ago — TS:9 (AT:10 TR:9 TM:9)

[15] Introducing ChatGPT agent — https://openai.com/index/introducing-chatgpt-agent — Research Date: 2026-03-16 — Source: OpenAI blog — TS:8 (AT:9 TR:8 TM:7)

[16] Apps in ChatGPT — https://chatgpt.com/features/connectors/ — Research Date: 2026-03-16 — Source: Official — TS:8 (AT:9 TR:8 TM:8)

[17] ChatGPT Slack app — https://help.openai.com/en/articles/12525822-chatgpt-connector-for-slack — Research Date: 2026-03-16 — Source: Help Center — TS:9 (AT:10 TR:9 TM:8)

[18] Google Drive synced connectors — https://help.openai.com/en/articles/10948259-google-drive-synced-connectors-self-service-setup — Research Date: 2026-03-16 — Source: Help Center — TS:9 (AT:10 TR:9 TM:8)

---

## Sources Discarded

| Source | TS | Reason |
|-------|-----|--------|
| CustomGPT.ai platform limits (customgpt.ai) | 5 | Third-party platform, not OpenAI ChatGPT; TR lower for commercial product |
| Wikipedia GPT-4o | 6 | Borderline; used only for retirement date confirmation; primary source is Model Release Notes |

---

## Data Gaps

- **Custom GPT file limit discrepancy:** File Uploads FAQ states 10 files per GPT; Creating a GPT FAQ states 20 files. Verify in product.
- **GPT-5.4 availability in Custom GPTs:** Model release notes do not explicitly list GPT-5.4; pricing page references it. Confirm model picker options for GPT creation.
- **Project instructions character limit:** No documented limit found in official sources.
- **Exact message/request rate limits:** Specific numbers (e.g., 160 messages per 3 hours) from third-party sources; OpenAI does not publish detailed rate limits in help center.

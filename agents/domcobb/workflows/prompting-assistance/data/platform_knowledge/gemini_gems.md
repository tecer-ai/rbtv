# Gemini Gems - Platform Interface Knowledge

**Platform:** Google Gemini (gemini.google.com)
**Feature:** Gems — custom AI assistants
**Purpose:** Enable AI agents to guide users through creating and configuring Gemini Gems with effective instructions and file context.

---

## 1. Interface Overview

### What Are Gems

Gems are custom AI assistants in Gemini that store instructions, tone, and formatting for repeatable tasks. They act as reusable workflows — each Gem remembers its role, style, and constraints across conversations. Available in the Gemini web app, mobile app, and Workspace side panel.

### Main Components

| Component | Purpose |
|-----------|---------|
| **Instructions** | Define the Gem's persona, task, tone, format, and constraints |
| **File uploads** | Reference documents uploaded to the Gem |
| **Google Search grounding** | Live web search for real-time data |
| **Premade Gems** | Google-provided templates (brainstorming, coding, career, writing, fitness, studying) |

---

## 2. Custom Instructions

### Format

Instructions should cover:

| Element | Description | Example |
|---------|-------------|---------|
| **Persona** | Role | "You are an expert executive assistant" |
| **Task** | What the Gem does | "Convert shorthand notes into professional emails" |
| **Tone** | Communication style | "Friendly but firm" |
| **Format** | Output structure | "Bullet points, under 150 words" |
| **Constraints** | What to avoid or always include | "Never use emojis. Always end with 'Best regards'" |
| **Context** | Background information | Industry, audience, preferences |

No documented character limit for Gem instructions. Guidance emphasizes being specific and detailed.

---

## 3. File Uploads

| Limit | Value |
|-------|-------|
| Files per prompt | 10 |
| Max file size (non-video) | 100 MB |
| ZIP files | Up to 100 MB, up to 10 files; no video/audio in ZIP |

**Supported types:** PDF, DOCX, TXT, HTML, XLSX, CSV, PNG, JPG, JPEG, WEBP, GIF.

### Google Docs/Sheets Sync

Files from Google Drive use the latest version — changes in Drive are reflected in the Gem. Requires Keep Activity on and Google Workspace connected.

---

## 4. Google Search Grounding

Gemini can access real-time web information via Google Search grounding:

- Model decides when to search based on the query
- Returns citations and source links
- Reduces hallucination by anchoring responses in live data
- Available in Gemini app; per-Gem UI configuration not documented

---

## 5. Context Window by Plan

| Plan | Context |
|------|---------|
| **Free** | 32,000 tokens |
| **AI Plus** | 128,000 tokens |
| **AI Pro** | 1,000,000 tokens |
| **AI Ultra** | 1,000,000 tokens |

---

## 6. Google Workspace Integration

| Service | Capabilities |
|---------|-------------|
| **Drive** | Search, summarize, analyze; add PDFs, Docs, Sheets, Slides as sources |
| **Docs** | Writing assistant, "Match writing style," "Match doc format" |
| **Sheets** | "Fill with Gemini," structure projects from descriptions |
| **Slides** | Context-aware images, multi-slide presentations from a prompt |
| **Gmail** | Summarize, search, answer; personalized when Workspace connected |

Gems in Drive side panel require Gemini for Google Workspace Alpha (not available to Google One AI Premium users).

---

## 7. Sharing

- Share from Gem manager on web via "Share"
- Permissions similar to Drive (view, use, edit)
- Shared Gems appear in recipient's "My Gems" after they open and interact
- Available since September 2025

---

## 8. Pricing

| Plan | Price | Notes |
|------|-------|-------|
| **Free** | $0 | Basic access, 32K context, custom Gems |
| **AI Plus** | $7.99/mo | Promo: $3.99/mo for first 2 months; 128K context |
| **AI Pro** | $19.99/mo | Replaces Google One AI Premium; 1M context |
| **AI Ultra** | $249.99/mo | 50% off first 3 months; highest limits |

---

## 9. AI Agent Guidance

### Instructions Format

- Lead with role/persona and task description
- Be explicit about output format (length, structure, tone)
- Include constraints with "Never" and "Always" language
- Add examples of ideal input/output if behavior is nuanced
- Keep instructions focused on a single task — Gems work best as single-purpose tools

### When to Recommend Gemini Gems

| Use Case | Why Gemini |
|----------|-----------|
| Live web research / real-time data | Google Search grounding built-in |
| Google ecosystem (Drive, Docs, Sheets, Gmail) | Native integration, live sync |
| Quick, repetitive tasks (rewrites, summaries) | Lightweight, 1-2 min setup |
| Massive context needs (1M+ tokens) | Largest context window on Pro/Ultra |
| Education / curriculum-aligned | Premade gems, file upload |

### When NOT to Recommend Gemini Gems

| Use Case | Better Alternative |
|----------|-------------------|
| Complex persistent assistants with multi-chat memory | Claude Projects, ChatGPT Projects |
| Code with GitHub integration | Claude Projects |
| Image generation | ChatGPT (DALL-E) |
| Autonomous task execution | Manus |
| Full project workspace with history | ChatGPT Projects, Claude Projects |

---

## 10. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Gems cannot be used with Gemini Live | No voice interaction with custom Gems | Use Gemini Live without Gem, or ChatGPT Voice |
| 10 files per prompt | Limited document context per interaction | Consolidate into fewer, larger files |
| Free tier: 32K tokens | Very limited context | Upgrade to AI Plus ($7.99) for 128K |
| No full workspace/project history | No persistent chat grouping like Projects | Use for single-task, not ongoing work |
| Learning coach Gem: no language learning | Built-in Gem limitation | Create custom Gem for language learning |
| Weaker PDF handling | May miss content in complex PDFs | Convert to plain text or Google Docs |
| Experimental Gems: English and web only | Limited availability | Use standard Gems |

---

## 11. Quality Checklist

- [ ] Instructions define a single, clear task
- [ ] Persona and tone specified
- [ ] Output format explicit (length, structure)
- [ ] Constraints stated with Never/Always
- [ ] File uploads are within 10-file, 100MB limits
- [ ] Google Docs/Sheets sync configured if live data needed
- [ ] Tested with sample prompts

---

*Last updated: 2026-03-16*

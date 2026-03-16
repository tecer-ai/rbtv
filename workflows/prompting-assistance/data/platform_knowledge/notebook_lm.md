# NotebookLM - Platform Interface Knowledge

**Platform:** Google NotebookLM (notebooklm.google.com)
**Feature:** Source-grounded AI research assistant
**Purpose:** Enable AI agents to guide users through creating NotebookLM notebooks with effective source curation and studio output configuration.

---

## 1. Interface Overview

### Main Components

| Component | Purpose |
|-----------|---------|
| **Sources** | Documents, links, and media uploaded as the notebook's knowledge base |
| **Chat** | Q&A interface grounded in sources; all responses include citations |
| **Studio** | Generates structured outputs (audio, video, mind maps, reports) from sources |
| **Notes** | Rich-text notes linked to sources |

### How It Works

NotebookLM is NOT a general-purpose chatbot. It grounds ALL responses in uploaded sources — it will refuse to answer questions not covered by the sources. This makes it ideal for deep analysis of specific material, but unsuitable for general Q&A.

---

## 2. Source Types and Limits

### Supported Sources

PDF, Google Docs, Google Sheets, Google Slides, YouTube videos (auto-transcribed), web URLs (text only — no images, embedded video, or paywalled content), local audio files (transcribed on import), images (TIFF, HEIC, JPEG, AVIF, BMP, GIF, ICO, JP2, PNG, WEBP), text files, Microsoft Word, CSV, copied/pasted text.

### Limits by Tier

| Tier | Sources per notebook | Notebooks | Chats/day | Audio overviews/day |
|------|---------------------|-----------|-----------|---------------------|
| **Free** | 50 | 100 | 50 | 3 |
| **Plus** | 300 | 200 | 500 | 20 |
| **Pro** | 300 | 500 | 500 | 20 |
| **Ultra** | 600 | 500 | 5,000 | 200 |

**Per-file limits (all tiers):** 200 MB per file, 500,000 words (~1M tokens) per source.

---

## 3. Studio Outputs

| Output | Description | Tier |
|--------|-------------|------|
| **Audio Overviews** | Podcast-style discussions (Deep Dive, Brief, Critique, Debate) | All |
| **Interactive Audio** | User can join AI-generated discussions and ask questions in real time | All |
| **Video Overviews** | Animated summaries (Classic, Whiteboard, Kawaii, Anime styles) | Plus+ |
| **Cinematic Video** | Veo 3-powered cinematic summaries | Ultra only |
| **Mind Maps** | Interactive diagrams with zoom, expand/collapse; exportable as PNG | All (not mobile) |
| **Briefing Docs / Reports** | Structured documents; AI suggests formats (briefing, study guide, blog, custom) | All |
| **Study Guides** | Flashcards and quizzes | All |
| **Data Tables** | Exportable to Google Sheets | All |
| **Slide Decks** | Editable, PPTX export | Plus+ (Feb 2026) |
| **Infographics** | Visual summaries | Plus+ |
| **Deep Research** | Agentic web researcher with citation-backed reports | Plus+ (Nov 2025) |

---

## 4. Sharing and Collaboration

### Public Sharing

- Share via link ("Anyone with the link")
- Personal accounts: no sign-in required for viewers
- Workspace/Education: within domain only
- Viewers can ask questions and use AI outputs but cannot edit sources
- Paid subscribers see usage analytics for public notebooks

### Private Sharing

| Role | Can Do |
|------|--------|
| **Viewer** | Read-only |
| **Editor** | Add/remove sources and notes, share further |

Personal Gmail: up to 50 users. Enterprise/Education: unlimited + Google Groups.

---

## 5. Google Ecosystem Integration

| Integration | Details |
|-------------|---------|
| **Google Docs** | Import as source; export reports to Docs |
| **Google Sheets** | Import as source; export data tables to Sheets |
| **Google Slides** | Import as source |
| **Enterprise** | Gemini Enterprise auth; notebooks from Enterprise search cannot be shared externally |
| **Model** | Powered by Gemini 3 (as of March 2026) |

---

## 6. Pricing

| Tier | Price | Notes |
|------|-------|-------|
| **Free** | $0 | 50 sources/notebook, 100 notebooks, 3 audio/day |
| **Plus** | $19.99/mo | 300 sources, 200 notebooks, video overviews |
| **Pro** | $19.99/mo | Part of Google One AI Premium; 500 notebooks |
| **Ultra** | $249.99/mo | 600 sources, 5,000 chats/day, cinematic video, watermark removal |

---

## 7. AI Agent Guidance

### When to Recommend NotebookLM

| Use Case | Why NotebookLM |
|----------|----------------|
| Deep analysis of specific documents | Source-grounded; refuses to hallucinate beyond sources |
| Creating study materials (flashcards, guides) | Built-in studio tools |
| Podcast-style summaries of research | Audio/Video Overviews |
| Collaborative research with citations | Every response cites source passages |

### When NOT to Recommend NotebookLM

| Use Case | Better Alternative |
|----------|-------------------|
| General Q&A without specific sources | ChatGPT, Claude, Gemini |
| Persistent assistant with custom instructions | Claude Projects, ChatGPT Projects |
| Live web research | Gemini (Google Search grounding) |
| Code-heavy work | Claude Projects (GitHub integration) |
| Autonomous task execution | Manus |

### Configuration Best Practices

- Curate sources carefully — NotebookLM quality is directly proportional to source quality
- Remove irrelevant sources to reduce noise
- Use notes to highlight key passages for better retrieval
- Structure sources with clear headings for better AI comprehension
- Web URLs import text only — if images/diagrams are critical, use PDF instead

---

## 8. Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Source-grounded only | Cannot answer questions outside uploaded sources | Add more sources or use a different platform for general Q&A |
| No cross-notebook links | Each notebook is isolated | Duplicate sources across notebooks if needed |
| Web URLs: text only | Images, embedded video, paywalled content not imported | Convert to PDF for rich content |
| No export of chat history | Responses and citations can't be exported with formatting | Copy/paste manually or use screenshots |
| No calculations | Numeric answers may be approximate | Use Sheets for calculations, then import as source |
| Mind maps not on mobile | Feature gap on mobile app | Use desktop/web |
| No custom instructions | Cannot define persistent behavior | Use notes as soft guidance |

---

## 9. Quality Checklist

- [ ] Sources are curated and relevant (no noise)
- [ ] File formats optimized (PDF for rich content, text for web)
- [ ] Source count within tier limits
- [ ] Notes highlight key passages
- [ ] Studio output type matches the goal
- [ ] Sharing permissions configured correctly

---

*Last updated: 2026-03-16*

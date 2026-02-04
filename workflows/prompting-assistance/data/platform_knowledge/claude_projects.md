# Claude Projects - Platform Interface Knowledge

**Platform:** Claude (claude.ai)  
**Feature:** Projects  
**Purpose:** Enable AI agents to guide users through Claude Projects interface

---

## 1. Interface Overview

### Main Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Projects list | Left navigation sidebar | Access and manage all projects |
| Project workspace | Main area | Chat interface with project context |
| Instructions panel | Right sidebar | Configure system prompt for project |
| Files panel | Right sidebar | Manage knowledge base documents |
| Chat input | Bottom of workspace | Send messages to Claude |
| Model selector | Chat input area | Choose Claude model (e.g., Opus 4.5) |

### Navigation Structure

1. **All projects view** — Lists all user projects, accessible via "All projects" link
2. **Project workspace** — Individual project with chat and configuration panels
3. **New project dialog** — Modal for creating projects with name and description fields

---

## 2. Core Capabilities

### What Claude Projects Can Do

| Capability | Description |
|------------|-------------|
| Persistent instructions | System prompt applied to every chat in the project |
| Knowledge base | Uploaded files available as context for all chats |
| Organized conversations | Multiple chats grouped under single project |
| Model selection | Choose which Claude model processes requests |
| External integrations | Connect GitHub repos and Google Drive files |

### Primary Use Cases

- Automating repetitive tasks with standard prompts
- Maintaining consistent AI behavior across conversations
- Providing domain-specific knowledge without re-uploading
- Team collaboration with shared context (Team/Enterprise plans)

---

## 3. Integrated Tools

### File Sources

| Source | How to Access | Capabilities |
|--------|---------------|--------------|
| Local upload | Files panel → "+" → "Upload from device" | Upload PDFs, documents, text files |
| GitHub | Files panel → "+" → "GitHub" | Select repository, browse files, add to project |
| Google Drive | Files panel → "+" → "Google Drive" | Browse recent files or paste URL |
| Text content | Files panel → "+" → "Add text content" | Manually paste text as knowledge |

### Linked Files (GitHub and Google Drive)

Files added from GitHub or Google Drive are **linked to the source**:
- When source files are updated, project files update automatically
- No manual re-upload required
- Project always has latest version from connected sources

| Source | Sync Behavior |
|--------|---------------|
| Local upload | Static — must re-upload to update |
| GitHub | Linked — auto-syncs with repository |
| Google Drive | Linked — auto-syncs with Drive |
| Text content | Static — must edit manually to update |

### GitHub Integration

1. Click "+" in Files panel
2. Select "GitHub"
3. Dialog appears: "Add content from GitHub"
4. Use dropdown "Select a repository" or paste URL
5. Browse and select files from repository
6. Selected files added to project knowledge base

### Google Drive Integration

1. Click "+" in Files panel
2. Select "Google Drive"
3. Submenu shows recent documents
4. Alternatively, search or paste URL
5. Selected files added to project knowledge base

---

## 4. User Actions

### Creating a Project

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Navigate to projects | Click project icon in left sidebar |
| 2 | Start creation | Click "New Project" or "+" button |
| 3 | Enter name | "What are you working on?" field — project name |
| 4 | Enter description | "What do you want to accomplish?" field — project goals |
| 5 | Confirm | Click "Create project" button |

### Adding Instructions

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open instructions | Click "+" next to "Instructions" in right sidebar |
| 2 | Write instructions | Text area: "Give Claude instructions and relevant information..." |
| 3 | Save | Click "Save instructions" button |
| 4 | Cancel | Click "Cancel" to discard changes |

**Instructions become the system prompt for all chats in this project.**

### Adding Files

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open file menu | Click "+" next to "Files" in right sidebar |
| 2 | Choose source | Select: Upload, Text content, GitHub, or Google Drive |
| 3 | Select files | Browse and select files from chosen source |
| 4 | Confirm | Files appear in Files panel list |

### Starting a Chat

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open project | Click project name in left sidebar |
| 2 | Type message | Enter text in "Reply..." input field |
| 3 | Select model | Use model dropdown (e.g., "Opus 4.5") |
| 4 | Send | Click send button or press Enter |

**Each new chat inherits project instructions as system prompt and uploaded files as available context.**

---

## 5. AI Agent Guidance

### How to Guide Users

| Task | Guidance Pattern |
|------|------------------|
| Create project | "Navigate to Projects in the left sidebar, then click New Project. Enter a descriptive name and your goals." |
| Add instructions | "In your project, click the + next to Instructions in the right panel. Write the behavior you want Claude to follow in every chat." |
| Add knowledge | "Click + next to Files, then choose your source: upload directly, connect GitHub, or link Google Drive." |
| Start conversation | "Open your project and type in the message field. Your instructions and files are automatically applied." |

### When to Recommend Projects

| Situation | Recommendation |
|-----------|----------------|
| User repeats same setup across chats | "Create a Project to save your instructions and files permanently" |
| User needs consistent behavior | "Project instructions act as a system prompt for every conversation" |
| User has reference documents | "Upload files to your project so Claude can access them without re-uploading" |
| User manages multiple contexts | "Create separate projects for different workflows" |

### Platform-Specific Instructions Format

Instructions field accepts plain text. Effective patterns:
- Role definition ("You are a...")
- Behavioral constraints ("Always...", "Never...")
- Output format preferences ("Use markdown tables")
- Domain-specific knowledge references ("Refer to the uploaded API docs")

---

## 6. Limitations and Constraints

### Platform Limitations

| Limitation | Description | Workaround |
|------------|-------------|------------|
| Free tier: 5 projects max | Limited project slots | Prioritize highest-value use cases |
| Project name not visible to Claude | Title/description not in context | Put critical info in instructions |
| Chat history not shared | Each chat is isolated | Add reusable info to knowledge base |
| No cross-project linking | Projects are independent | Manually copy relevant context |
| File size limits | Large files may be rejected | Split into smaller documents |

### What Projects Cannot Do

- Share context between different projects
- Automatically update when external files change
- Execute code or access external APIs
- Remember information from one chat in another (unless added to knowledge base)

---

## 7. Context Management

### How Context Works

| Component | Behavior |
|-----------|----------|
| Instructions | Loaded as system prompt at chat start |
| Knowledge base files | Available for retrieval during conversation |
| Chat history | Maintained within single chat only |
| Previous chats | NOT accessible to new chats |

### Context Persistence

| Persists | Does Not Persist |
|----------|------------------|
| Project instructions | Individual chat messages |
| Uploaded files | Chat-specific clarifications |
| Project name/description | Temporary context from conversation |

### Optimization Strategies

| Strategy | Implementation |
|----------|----------------|
| Curate knowledge base | Remove outdated/irrelevant files |
| Prioritize critical files | Most important docs likely retrieved first |
| Explicit instructions | Tell Claude which files to reference |
| Periodic review | Update knowledge base when source docs change |

---

## Visual Reference

### Project Creation Dialog

```
┌─────────────────────────────────────────────┐
│  Create a personal project                  │
│                                             │
│  What are you working on?                   │
│  ┌─────────────────────────────────────┐    │
│  │ [Project name input]                │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  What do you want to accomplish?            │
│  ┌─────────────────────────────────────┐    │
│  │ [Description textarea]              │    │
│  │                                     │    │
│  └─────────────────────────────────────┘    │
│                                             │
│              [Cancel]  [Create project]     │
└─────────────────────────────────────────────┘
```

### Project Workspace Layout

```
┌──────────┬──────────────────────┬──────────────┐
│ Projects │                      │ Instructions │
│ ────────│    Chat Area          │ ────────────│
│ Project1 │                      │ [+]          │
│ Project2 │                      │              │
│ Project3 │                      │ Files        │
│          │                      │ ────────────│
│          │                      │ [+]          │
│          │ ┌──────────────────┐ │              │
│          │ │ Reply...         │ │ • file1.pdf │
│          │ │      Opus 4.5 [↑]│ │ • file2.md  │
│          │ └──────────────────┘ │              │
└──────────┴──────────────────────┴──────────────┘
```

---

## 8. When to Use Projects

### Ideal For

| Use Case | Why Projects Help |
|----------|-------------------|
| Recurring workflows with consistent requirements | Customer support, code review, content creation — same setup every time |
| Role-specific tasks requiring persona consistency | Technical writer, QA analyst, architect personas maintained across chats |
| Projects with stable knowledge bases | API documentation, style guides, design systems always available |
| Team collaboration (Team/Enterprise) | Shared context eliminates repeated uploads |
| Multi-conversation tasks building on previous work | Iterative development, research projects |

### Avoid For

| Use Case | Why Projects Don't Help |
|----------|-------------------------|
| One-off questions with no repeated context | Overhead not worth it |
| Tasks where context varies significantly | Different setup needed each time |
| Exploratory conversations without defined scope | No stable instructions to define |
| Simple queries answerable without context loading | Unnecessary complexity |

---

## 9. Common Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Assuming chat history is shared | Only knowledge base content is shared; each chat is isolated | Explicitly add reusable information to project knowledge base |
| Uploading irrelevant documents | Semantically similar but off-topic content confuses model | Curate knowledge base rigorously; remove outdated files |
| Vague project instructions | Generic instructions ("be helpful") provide no guidance | Specify role, tone, format, constraints with concrete examples |
| Forgetting to update stale knowledge | Outdated documentation causes incorrect responses | Set review cadence; update when source docs change |
| Generic project names | Hard to find correct project | Use descriptive names: "React Component Library Docs" not "Frontend Project" |
| Overloading single project | Unrelated contexts dilute effectiveness | Create separate projects for distinct domains |

---

## 10. Quality Checklist

Before deploying a Claude Project:

- [ ] Project name is descriptive — clearly indicates purpose and scope
- [ ] Instructions define role — specifies persona ("You are a...")
- [ ] Instructions specify tone — defines communication style
- [ ] Output format is explicit — states preferred structure (markdown, JSON, bullets)
- [ ] Constraints are listed — defines what to avoid or limit
- [ ] Knowledge base is curated — only relevant, high-quality documents
- [ ] Test query validates behavior — representative prompt confirms instructions work
- [ ] Sources are citable — uploaded files have clear names
- [ ] Update plan exists — process defined for keeping knowledge base current

---

## 11. Examples

### Example: API Documentation Assistant

| Without Projects | With Projects |
|------------------|---------------|
| **Every chat:** Paste API reference, explain role, specify format, remind about style guide | **Setup once:** Instructions define role and format; upload api_reference.json and style_guide.md |
| **Result:** Inconsistent style, repeated setup, no source citations | **Result:** Consistent format, automatic citations, 80% less prompt setup |

### Example: Code Review Assistant

| Without Projects | With Projects |
|------------------|---------------|
| **Every chat:** List review criteria, paste coding standards, explain security checklist | **Setup once:** Instructions define review process; upload coding_standards.md and security_checklist.md |
| **Result:** Inconsistent depth, forgotten criteria, manual tracking | **Result:** 100% checklist coverage, consistent reviews |

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Projects overview | https://support.claude.com/en/articles/9517075-what-are-projects |
| Creating and managing projects | https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects |
| RAG enhancement (paid plans) | https://support.anthropic.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects |
| Project visibility and sharing | https://support.claude.com/en/articles/9519189-project-visibility-and-sharing |

---

*Last updated: 2026-02-03*

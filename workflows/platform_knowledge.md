---
---

# Template Instructions: platform_knowledge

**Purpose:** Document AI platform interface features to enable agents to guide users through platform-specific workflows.

**Required:** Optional. Create when documenting how to use a specific AI platform's features (projects, integrations, UI workflows).

---

## How to Use This Template

Follow these steps in order when creating a new platform knowledge document:

| Step | Section | Description |
|------|---------|-------------|
| 1 | [Interface Overview](#interface-overview) | Map the platform's main UI components |
| 2 | [Core Capabilities](#core-capabilities) | What the feature can do and primary use cases |
| 3 | [Integrated Tools](#integrated-tools) | External integrations and file sources |
| 4 | [User Actions](#user-actions) | Step-by-step procedures for common tasks |
| 5 | [AI Agent Guidance](#ai-agent-guidance) | How to guide users through the interface |
| 6 | [Limitations and Constraints](#limitations-and-constraints) | What the platform cannot do |
| 7 | [Context Management](#context-management) | How context persists and flows |
| 8 | [When to Use](#when-to-use) | Ideal and non-ideal scenarios |
| 9 | [Common Pitfalls](#common-pitfalls) | Mistakes and solutions |
| 10 | [Quality Checklist](#quality-checklist) | Verification items |
| 11 | [Technical Reference](#technical-reference) | Official documentation links |

**Iteration:** Verify all UI elements are accurately described. Test procedures against actual platform.

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| [Interface Overview](#interface-overview) | Required | Table format: Component | Location | Purpose. Include visual references if helpful |
| [Core Capabilities](#core-capabilities) | Required | Table of capabilities and primary use cases |
| [Integrated Tools](#integrated-tools) | Recommended | Document external integrations (GitHub, Google Drive, etc.). Omit if no integrations |
| [User Actions](#user-actions) | Required | Step-by-step tables for each major action (create, configure, use) |
| [AI Agent Guidance](#ai-agent-guidance) | Required | How to guide users through the UI; when to recommend the feature |
| [Limitations and Constraints](#limitations-and-constraints) | Required | Table of limitations with workarounds |
| [Context Management](#context-management) | Required | How context persists across sessions, chats, projects |
| [When to Use](#when-to-use) | Required | Table format: Ideal For | Avoid For |
| [Common Pitfalls](#common-pitfalls) | Required | Table: Pitfall | Why It Fails | Solution |
| [Quality Checklist](#quality-checklist) | Required | Platform-specific verification items. Max 10 items |
| [Visual Reference](#visual-reference) | Recommended | ASCII diagrams of key UI layouts. Omit if not helpful |
| [Technical Reference](#technical-reference) | Required | Links to official documentation |
| [Last updated](#last-updated) | Required | ISO 8601 format at end of file |

---

## Notes

### Scope

Platform knowledge documents capture **interface workflows** — how to navigate and use specific platform features. Each document MUST include:
- UI component mapping (what's where)
- User action procedures (how to do tasks)
- Agent guidance patterns (how to explain to users)
- Context behavior (what persists, what doesn't)
- Limitations and workarounds

Documents MUST NOT:
- Duplicate prompting techniques (use prompting_techniques/ documents)
- Duplicate model-specific behavior (use ai_models/ documents)
- Include general AI best practices
- Focus on API/programmatic access (unless platform exposes it to users)

### Naming

Files follow pattern: `[platform]_[feature].md` (e.g., `claude_projects.md`, `chatgpt_projects.md`, `gemini_gems.md`)

Use lowercase with underscores. Name should clearly indicate platform and feature.

### When to Create

Create a platform knowledge document when:
- A platform has a specific feature users need guidance on
- The feature has non-obvious workflows or capabilities
- AI agents need to guide users through platform-specific UI
- Common mistakes or misunderstandings exist about the feature

Do NOT create if:
- The feature is self-explanatory
- No agent guidance is needed
- The information is API-only (no user-facing interface)
- Official documentation is sufficient and easily accessible

### Platform Categories

Platform knowledge is organized by platform and feature type:

| Category | Examples |
|----------|----------|
| **Project/Workspace** | Claude Projects, ChatGPT Projects, Gemini Gems |
| **Integrations** | GitHub connections, Google Drive linking |
| **Memory/Context** | Memory features, persistent context |
| **Custom Instructions** | System prompts, custom GPTs, custom models |
| **Collaboration** | Team features, sharing, permissions |

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Platform] [Feature] - Platform Interface Knowledge

**Platform:** [Platform name] (URL)  
**Feature:** [Feature name]  
**Purpose:** Enable AI agents to guide users through [feature] interface

---

## 1. Interface Overview

### Main Components

| Component | Location | Purpose |
|-----------|----------|---------|
| [Component name] | [Where in UI] | [What it does] |

### Navigation Structure

1. **[View 1]** — [Description]
2. **[View 2]** — [Description]

---

## 2. Core Capabilities

### What [Feature] Can Do

| Capability | Description |
|------------|-------------|
| [Capability name] | [What it enables] |

### Primary Use Cases

- [Use case 1]
- [Use case 2]

---

## 3. Integrated Tools

### [Integration Category]

| Source | How to Access | Capabilities |
|--------|---------------|--------------|
| [Source name] | [Navigation path] | [What can be done] |

### Sync Behavior

| Source | Sync Behavior |
|--------|---------------|
| [Source name] | [Static/Linked — description] |

---

## 4. User Actions

### [Action Name] (e.g., Creating a Project)

| Step | Action | UI Element |
|------|--------|------------|
| 1 | [What to do] | [Where to click/type] |
| 2 | [What to do] | [Where to click/type] |

### [Action Name] (e.g., Adding Files)

| Step | Action | UI Element |
|------|--------|------------|
| 1 | [What to do] | [Where to click/type] |

---

## 5. AI Agent Guidance

### How to Guide Users

| Task | Guidance Pattern |
|------|------------------|
| [Task name] | "[Exact phrasing to guide user through UI]" |

### When to Recommend [Feature]

| Situation | Recommendation |
|-----------|----------------|
| [User scenario] | "[What to tell user]" |

### Platform-Specific Instructions Format

[Notes on how instructions/prompts work in this platform]

---

## 6. Limitations and Constraints

### Platform Limitations

| Limitation | Description | Workaround |
|------------|-------------|------------|
| [Limitation] | [What it means] | [How to work around] |

### What [Feature] Cannot Do

- [Limitation 1]
- [Limitation 2]

---

## 7. Context Management

### How Context Works

| Component | Behavior |
|-----------|----------|
| [Component] | [How it persists/flows] |

### Context Persistence

| Persists | Does Not Persist |
|----------|------------------|
| [What persists] | [What doesn't] |

### Optimization Strategies

| Strategy | Implementation |
|----------|----------------|
| [Strategy name] | [How to apply] |

---

## 8. When to Use

### Ideal For

| Use Case | Why [Feature] Helps |
|----------|---------------------|
| [Scenario] | [Benefit] |

### Avoid For

| Use Case | Why [Feature] Doesn't Help |
|----------|---------------------------|
| [Scenario] | [Limitation] |

---

## 9. Common Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| [Common mistake] | [Consequence] | [How to fix/prevent] |

---

## 10. Quality Checklist

Before deploying a [platform] [feature] setup:

- [ ] [Platform-specific verification item]
- [ ] [Platform-specific verification item]
- [ ] [Platform-specific verification item]

---

## 11. Visual Reference

### [UI Element Name]

```
[ASCII diagram of UI layout]
```

---

## 12. Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| [Topic] | [URL] |

---

*Last updated: YYYY-MM-DD*

# ChatGPT Projects - Platform Interface Knowledge

**Platform:** ChatGPT (chatgpt.com)  
**Feature:** Projects  
**Purpose:** Enable AI agents to guide users through ChatGPT Projects interface

---

## Overview

ChatGPT Projects provides the same core functionality as Claude Projects. Read [claude_projects.md](claude_projects.md) for complete documentation.

---

## Differences from Claude Projects

| Aspect | ChatGPT Projects | Claude Projects |
|--------|------------------|-----------------|
| **File upload** | Direct upload only | Direct upload, GitHub, Google Drive |
| **External integrations** | None | GitHub repos, Google Drive files |
| **File sync** | Manual re-upload required | Auto-sync from linked sources |

---

## File Management

### Supported Methods

| Method | Supported |
|--------|-----------|
| Upload from device | Yes |
| Add text content | Yes |
| GitHub integration | No |
| Google Drive integration | No |

### Implications

- Files must be manually re-uploaded when source documents change
- No automatic synchronization with external repositories or drives
- User must maintain file versions manually

---

## AI Agent Guidance

When guiding ChatGPT Projects users:

1. **For file updates:** "You'll need to re-upload the file manually since ChatGPT doesn't sync with external sources"
2. **For version control:** "Consider naming files with versions (e.g., api_docs_v2.pdf) to track updates"
3. **For GitHub users:** "Export files from your repo and upload them directly to the project"

---

## Reference

For complete platform interface documentation (creation flow, instructions, context management), read [claude_projects.md](claude_projects.md).

---

*Last updated: 2026-02-03*

# Output Document Template

Use this template to create output document templates for BMAD workflows.

---

## Template

```markdown
---
title: '{Document Title}'
stepsCompleted: []
inputDocuments: []
workflowType: '{workflow-type}'
date: '{{date}}'
user_name: '{{user_name}}'
project_name: '{{project_name}}'
---

# {Document Title}

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each step together._

<!-- Content appended by workflow steps -->
```

---

## Field Instructions

### Frontmatter Fields

| Field | Purpose | Example |
|-------|---------|---------|
| **title** | Document title | "Product Requirements Document" |
| **stepsCompleted** | Array of completed step names | `["step-01-init.md", "step-02-discover.md"]` |
| **inputDocuments** | Array of source document paths | `["planning-artifacts/brief.md"]` |
| **workflowType** | Which workflow created this | "prd", "architecture", "brief" |
| **date** | When workflow started | Filled from template |
| **user_name** | From config.yaml | Filled from template |
| **project_name** | From config.yaml | Filled from template |

### Placeholder Syntax
- `{Variable}` — Filled in by the workflow at creation time
- `{{variable}}` — Filled from config.yaml values

---

## How State Tracking Works

1. **stepsCompleted array** — Each step adds its filename after completion
2. **Continuation logic** — Reads stepsCompleted to find last step, loads next
3. **Append-only content** — Steps add sections, never modify previous sections

### Example Progression

After step-01:
```yaml
stepsCompleted: ["step-01-init.md"]
```

After step-02:
```yaml
stepsCompleted: ["step-01-init.md", "step-02-discover.md"]
```

After step-03:
```yaml
stepsCompleted: ["step-01-init.md", "step-02-discover.md", "step-03-draft.md"]
```

---

## Input Document Discovery

Workflows scan configured directories for input documents:
- `{planning_artifacts}` — Previous planning outputs
- `{output_folder}` — General output location
- `{project_knowledge}` — Project-specific data

Matching by filename patterns: `*brief*`, `*prd*`, `*architecture*`

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Template lines | 15-30 | 50 |

The template should be minimal — content is appended by workflow steps.

---

## Common Mistakes

1. **Missing stepsCompleted** — Required for session resumption

2. **No workflowType** — Required for continuation logic to find correct step directory

3. **Modifying previous sections** — Output documents are append-only; never edit completed sections

4. **Forgetting inputDocuments** — Provides audit trail of what informed the document

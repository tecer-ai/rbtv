---
---

# Template Instructions: feature_documentation

**Purpose:** Detailed documentation for a specific feature. One file per feature, named `[feature_name].md`.

---

## Table of Contents

### Template Instructions

- [Design Principles](#design-principles)
- [Section Guidelines](#section-guidelines)
- [Notes](#notes)

### Document Content

- [Feature Name](#feature-name)
- [Status](#status)
- [Dependencies](#dependencies)
- [User Stories](#user-stories)
- [Requirements](#requirements)
- [Technical Design](#technical-design)
- [Sub-Features](#sub-features)
- [Acceptance Criteria](#acceptance-criteria)
- [Specifications](#specifications)

---

## Design Principles

1. **Persistent documentation** — Feature docs NEVER deleted; persist after launch
2. **Single source** — One file per feature contains all information
3. **Naming convention** — `[feature_name].md` using snake_case, lowercase, 2-4 words, max 50 characters
4. **Tasks in roadmap** — Implementation tasks tracked in `roadmap.md`, not in feature docs

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| Status | Required | Track documentation and implementation progress |
| Dependencies | Required | Feature and system dependencies |
| User Stories | Recommended | User-focused requirements |
| Requirements | Required | Functional and non-functional |
| Technical Design | Required | Architecture and implementation approach |
| Sub-Features | Optional | Only if feature has nested sub-features |
| Acceptance Criteria | Required | Testable completion criteria |
| Specifications | Recommended | Detailed technical specs |

---

## Notes

### File Naming

MUST name files `[feature_name].md` where `feature_name` follows:

- `snake_case` (spaces → underscores)
- Lowercase only
- 2-4 words typical
- Max 50 characters

### When to Create

MUST create when feature moves from Backlog to Roadmap. Documentation required before feature enters roadmap.

### Documentation Persistence

Feature documentation files NEVER deleted:
- Feature goes live → documentation persists
- Feature deprecated/removed → move to `docs/product/old/` or mark deprecated
- Preserves historical context and decisions

### Implementation Tasks

Implementation tasks tracked in `roadmap.md` (In Progress/Testing sections), NOT in feature docs.

### Sub-Features

Use Sub-Features section only when feature contains distinct nested capabilities. Omit for simple features.

### Updating

MUST update as feature evolves. Status section MUST reflect current state.

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Feature Name]

## For AI Agents

**Template reference:** This document was created from [`feature_documentation.md`](../../../system/founder/m6_mvp/feature_documentation.md). Agents MUST read the template before making updates.

---

**Feature #:** [Number from roadmap]
**Stage:** [Current stage]
**Type:** [Front / Back / Both]

---

## Table of Contents

1. [Status](#status)
2. [Dependencies](#dependencies)
3. [User Stories](#user-stories)
4. [Requirements](#requirements)
5. [Technical Design](#technical-design)
6. [Sub-Features](#sub-features)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Specifications](#specifications)

---

## Status

### Documentation Checklist

- [ ] Requirements defined
- [ ] User stories written
- [ ] Technical design complete
- [ ] Acceptance criteria specified
- [ ] Dependencies identified

### Implementation Checklist

- [ ] Development started
- [ ] Core functionality complete
- [ ] Edge cases handled
- [ ] Testing complete
- [ ] Documentation updated
- [ ] Ready for review

---

## Dependencies

### Feature Dependencies

| Feature | Relationship | Status |
|---------|--------------|--------|
| [Feature name] | [Blocks / Blocked by / Related to] | [Status] |

### System Dependencies

| System/API | Purpose |
|------------|---------|
| [System name] | [How this feature depends on it] |

---

## User Stories

### US-001: [User Story Title]

**As a** [type of user]
**I want** [some goal]
**So that** [some reason]

**Acceptance Criteria:**

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | [Requirement description] | [Must / Should / Could] |

### Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-001 | [Requirement description] | [Must / Should / Could] |

---

## Technical Design

### Architecture Overview

[How this feature fits into the overall system architecture]

### Data Model

[Data structures, schemas, or models involved]

### API Contracts

[If applicable, API endpoints and their contracts]

### Component Design

[Key components and their interactions]

---

## Sub-Features

> **Note:** This section is optional. Include only if the feature has distinct nested sub-features.

### [Sub-Feature Name]

**Description:** [Brief description of the sub-feature]

**Scope:** [What this sub-feature covers]

**Status:** [To Do / In Progress / Complete]

---

## Acceptance Criteria

[Specific, testable criteria for feature completion]

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## Specifications

[Technical specifications, API contracts, UI specs]

---

*Last updated: 2025-12-10*



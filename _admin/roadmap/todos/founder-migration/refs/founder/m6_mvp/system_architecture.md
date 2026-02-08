---
---

# Template Instructions: system_architecture

**Purpose:** Technical architecture documentation for the project, tailored for pre-product-market-fit (pre-PMF) stages.


---

## Table of Contents

### Template Instructions

- [Pre-PMF Focus](#pre-pmf-focus)
- [Section Guidelines](#section-guidelines)
- [Notes](#notes)

### Document Content

- [Index](#index)
- [Version Log](#version-log)
- [Tech Stack](#tech-stack)
- [High-Level Architecture Diagram](#high-level-architecture-diagram)
- [Components and Services](#components-and-services)
- [Data Architecture](#data-architecture)
- [Decision Records](#decision-records)
- [Integration Architecture](#integration-architecture)
- [Infrastructure Architecture](#infrastructure-architecture)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Performance and Scalability](#performance-and-scalability)
- [Operational Requirements](#operational-requirements)

---

## Pre-PMF Focus

| Designation | Meaning |
|-------------|---------|
| **Mandatory Pre-PMF** | MUST exist from day one—essential for alignment |
| **Optional Pre-PMF** | Add only when relevant—avoid over-engineering before validation |

---

## Section Guidelines

| Section | Requirement | Pre-PMF | Notes |
|---------|-------------|---------|-------|
| Index | Required | Mandatory | Quick reference to all sections with Pre-PMF designation |
| Version Log | Required | Mandatory | Track architecture evolution using semver |
| Tech Stack | Required | Mandatory | Technology choices and rationale per layer |
| High-Level Architecture Diagram | Required | Mandatory | Single visual showing major blocks and interactions |
| Components and Services | Required | Mandatory | Core modules, responsibilities, inputs/outputs — to be moved to product documentation templates |
| Data Architecture | Required | Mandatory | Essential entities, relationships, storage strategy |
| Decision Records | Optional | Optional | Technical decisions with risks, assumptions, tradeoffs |
| Integration Architecture | Optional | Optional | APIs, webhooks, external services, dependencies |
| Infrastructure Architecture | Optional | Optional | Cloud, networking, compute, storage |
| Security Architecture | Optional | Optional | Auth, permissions, data protection, compliance |
| Deployment Architecture | Optional | Optional | CI/CD, environments, versioning, rollout strategy |
| Performance and Scalability | Optional | Optional | Expected load, bottlenecks, caching, scaling |
| Operational Requirements | Optional | Optional | Monitoring, logging, alerting, incident response |

---

## Notes

### Decision Records Structure

Each decision record MUST capture:
- **Context:** Issue motivating the decision
- **Decision:** Change being made
- **Assumptions:** What we assume true (may need validation)
- **Tradeoffs:** What we intentionally accept or postpone
- **Risks:** Known risks and mitigation strategies
- **Consequences:** What becomes easier or harder

### Integration Architecture and Dependencies

Integration Architecture section (Optional Pre-PMF) includes:
- External APIs and webhooks
- Message queues and event systems
- Third-party services
- External dependencies (libraries, databases, infrastructure)

If Integration Architecture omitted, note critical dependencies in Tech Stack section.

### Adding Optional Sections

Add optional sections ONLY when:
- Section addresses current, concrete need
- Product requires it for compliance or security
- Team needs alignment on specific area

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Project Name] System Architecture

[Brief description of the system architecture purpose and scope]

---

## For AI Agents

**Template reference:** This document was created from [`system_architecture.md`](../../../system/founder/m6_mvp/system_architecture.md). Agents MUST read the template before making updates.

---

## Index

| Section | Pre-PMF | Description |
|---------|---------|-------------|
| [Version Log](#version-log) | Mandatory | Architecture evolution history |
| [Tech Stack](#tech-stack) | Mandatory | Technology choices and rationale |
| [High-Level Architecture Diagram](#high-level-architecture-diagram) | Mandatory | Visual system overview |
| [Components and Services](#components-and-services) | Mandatory | Core modules and responsibilities |
| [Data Architecture](#data-architecture) | Mandatory | Essential entities and relationships |
| [Decision Records](#decision-records) | Optional | Technical decisions with risks, assumptions, tradeoffs |
| [Integration Architecture](#integration-architecture) | Optional | APIs, external services, dependencies |
| [Infrastructure Architecture](#infrastructure-architecture) | Optional | Cloud, networking, compute, storage |
| [Security Architecture](#security-architecture) | Optional | Auth, permissions, data protection |
| [Deployment Architecture](#deployment-architecture) | Optional | CI/CD, environments, rollout strategy |
| [Performance and Scalability](#performance-and-scalability) | Optional | Load expectations, caching, scaling |
| [Operational Requirements](#operational-requirements) | Optional | Monitoring, logging, alerting |

---

## Version Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial architecture |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| [Layer name] | [Technology] | [Why this technology was chosen] |

---

## High-Level Architecture Diagram

[ASCII diagram showing major system blocks and how they interact]

```
[Insert ASCII diagram here]
```

---

## Components and Services

> **Note:** This section is to be moved to product documentation templates.

[Description of major components/modules and their responsibilities]

### [Component Name]

- **Responsibility:** [What this component does]
- **Inputs:** [What it receives]
- **Outputs:** [What it produces]
- **Technology:** [Implementation details if relevant]

---

## Data Architecture

[Essential entities, relationships, and storage strategy]

### Core Entities

| Entity | Description | Storage |
|--------|-------------|---------|
| [Entity name] | [What it represents] | [Where/how stored] |

### Relationships

[Key relationships between entities]

### Data Flow

[How data moves through the system]

---

## Decision Records

> **Pre-PMF:** Optional — add when documenting significant architectural decisions becomes valuable.

### DR-001: [Decision Title]

- **Date:** YYYY-MM-DD
- **Status:** [Proposed | Accepted | Deprecated | Superseded]
- **Context:** [What is the issue that we're seeing that is motivating this decision?]
- **Decision:** [What is the change that we're proposing and/or doing?]
- **Assumptions:** [What we assume to be true that influences this decision]
- **Tradeoffs:** [What we're intentionally accepting or postponing]
- **Risks:** [Known risks and how we plan to mitigate them]
- **Consequences:** [What becomes easier or more difficult to do because of this change?]

---

## Integration Architecture

> **Pre-PMF:** Optional — include only if integrations are central to the MVP.

[APIs, webhooks, queues, and external services]

### External APIs

| API | Purpose | Auth Method |
|-----|---------|-------------|
| [API name] | [What it's used for] | [How authenticated] |

### Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| [Name] | [Library/Service/API] | [Why needed] |

---

## Infrastructure Architecture

> **Pre-PMF:** Optional — detail later unless infra is a product requirement.

[Cloud, networking, compute, storage, and infra components]

---

## Security Architecture

> **Pre-PMF:** Optional — keep lightweight unless handling sensitive data early.

[Auth, permissions, data protection, and compliance]

---

## Deployment Architecture

> **Pre-PMF:** Optional — simple pipeline is enough before scaling.

[CI/CD flow, environments, versioning, and rollout strategy]

---

## Performance and Scalability

> **Pre-PMF:** Optional — avoid heavy planning until metrics justify it.

[Expected load, bottlenecks, caching, and scaling strategy]

---

## Operational Requirements

> **Pre-PMF:** Optional — only needed when uptime or SLOs become critical.

[Monitoring, logging, alerting, and incident response]

---
---
name: 'trl-framework'
description: 'NASA TRL 1-9 scale definitions adapted for digital startups'
---

# Technology Readiness Level (TRL) Framework Reference

## Overview

Technology Readiness Level is NASA's 9-level scale for assessing how close a technology is to operational deployment. The TRL framework forces honest, evidence-based assessment of each component separately.

Key insight: A product where 4 of 5 components are at TRL 8 and 1 is at TRL 2 is NOT at TRL 7. The weakest component determines the risk profile.

---

## TRL Scale (Digital Startups)

| TRL | Name | Description | Example |
|-----|------|-------------|---------|
| **1** | Basic principles observed | Understand the principle but haven't applied it | "We know transformer models can classify text" |
| **2** | Concept formulated | Have a concept for applying principle to your problem | "We believe fine-tuned BERT could classify support tickets" |
| **3** | Proof of concept | Demonstrated core concept in controlled setting | "Jupyter notebook shows 85% accuracy on sample dataset" |
| **4** | Validated in lab | Works in dev environment with representative data | "Classifier built in dev using production-like data" |
| **5** | Validated in relevant environment | Works in staging approximating production | "Runs on staging server with real API calls, 100 req/min" |
| **6** | Demonstrated in relevant environment | Tested with real users/data in near-production | "10 beta users used classifier on their own data" |
| **7** | Prototype in operational environment | Working prototype in real environment | "Running in production for 50 users with monitoring" |
| **8** | System complete and qualified | Fully integrated, tested, meeting requirements | "Production at 1000 req/min, meeting 95% accuracy SLA" |
| **9** | Proven in operations | Track record of reliable real-world operation | "6 months production, 99.9% uptime, consistent accuracy" |

---

## Component Type Classification

| Type | Description | Typical Starting TRL |
|------|-------------|---------------------|
| **Novel** | Built from scratch, new approach | TRL 1-3 |
| **Adapted** | Existing tech applied to new context | TRL 3-5 |
| **Standard** | Well-understood, widely available | TRL 6-8 |

---

## Risk Categories

Assess each component across these dimensions:

| Category | Key Question |
|----------|--------------|
| **Performance** | Can it meet speed, accuracy, throughput, latency targets? |
| **Scalability** | Can it scale to expected volume within cost constraints? |
| **Integration** | Does it depend on external APIs that could change or fail? |
| **Data** | Does it require data you don't have or quality unproven? |
| **Security** | Does it handle sensitive data or require compliance? |
| **Skills** | Does it need expertise the team doesn't have? |
| **Cost** | Could variable costs become prohibitive at scale? |

---

## Spike Card Template

For each component below TRL 4, create a spike card:

```markdown
### Spike Card: [Component ID]

**Component:** [Name]
**Current TRL:** [1-9]
**Target TRL:** [4-5 minimum]

**Key Question:** Can we [specific capability] with [specific constraints]?

**Method:**
- [ ] Build minimal proof-of-concept
- [ ] Run benchmark against representative data
- [ ] Evaluate third-party service/library
- [ ] Consult domain expert
- [ ] Analyze comparable implementations

**Success Criteria:** [Specific, measurable outcomes]
Example: "Model achieves 85% accuracy on 500-sample test set"

**Failure Criteria:** [What would invalidate this component]
Connect to kill criteria where applicable.

**Estimated Effort:** [Person-days or weeks]
**Dependencies:** [Other spikes, data, access needed]
**Owner:** [Who executes]
```

---

## Overall Posture Assessment

| Posture | Criteria | Implication |
|---------|----------|-------------|
| **🟢 Green** | All components TRL 4+, no spikes needed | Ready for M4 Prototypation |
| **🟡 Yellow** | 1-2 components below TRL 4, spikes < 2 weeks | Proceed to M4 after spikes |
| **🔴 Red** | 3+ below TRL 4, or any below TRL 2 with no path | Technical feasibility in question |

---

## Integration Points

### Builds On

| Framework | What It Provides |
|-----------|------------------|
| Working Backwards (M1) | Technical feasibility questions in Internal FAQ |
| Problem-Solution Fit (M1) | Solution concept defining what must be built |
| Lean Canvas (M1) | Solution block capabilities to decompose |

### Feeds Into

| Framework | What It Receives |
|-----------|------------------|
| Pre-mortem (M2) | Technical risks and low-TRL components |
| M4 Prototypation | TRL table, spike results, build sequencing |
| M6 MVP | Residual risks, feature scope constraints |

---

## Common Pitfalls

1. **Overestimating TRL** — Score based on demonstrated evidence, not capability
2. **System-Level Assessment** — Assess each component independently, not "the product"
3. **Third-Party Assumptions** — A well-known API at TRL 9 might be TRL 4 for YOUR integration
4. **Scope Creep in Spikes** — A spike answers ONE question with minimum effort; if > 2 weeks, split it
5. **Skipping for "Simple" Products** — Even standard web apps have authentication, migration, deployment to assess

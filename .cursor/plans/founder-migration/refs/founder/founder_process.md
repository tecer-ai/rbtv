# Founder Process

## Purpose

Master navigation for the six-milestone founder lifecycle from idea to MVP.

---

## Glossary

| Term | Definition | Location |
|------|------------|----------|
| **founder** | Module for startup/product lifecycle from idea to MVP | [founder/](.) |
| **founder_process.md** | Master doc with overview, summaries, glossary, navigation | [founder_process.md](founder_process.md) |
| **milestone** | Major lifecycle stages: conception, validation, brand, prototypation, market_validation, mvp | — |
| **milestone process doc** | Detailed process for one milestone | [milestone process doc](m[x]_[name]/[name]_process.md) |
| **step** | Sub-part of a milestone | Defined within each milestone process doc |
| **framework doc** | Methodology guide for one framework | [framework doc](m[x]_[name]/[name]_frameworks/[framework].md) |
| **task** | Atomic actionable unit | Defined within framework docs |
| **project_memo template** | Template for Amazon-style narrative memo | [project_memo.md](templates/project_memo.md) |
| **project memo (instance)** | User-created narrative memo for their project | `[project]/docs/founder/[project]_memo.md` |
| **founder_diary template** | Template for session tracking, file map, framework status, and decision logging | [founder_diary.md](templates/founder_diary.md) |
| **founder_diary (instance)** | User-created diary per milestone — primary document for resuming work sessions | `[project]/docs/founder/[milestone]/m[x]_founder_diary.md` |
| **applied framework** | User-created doc applying a framework to their project | `[project]/docs/founder/[milestone]/[framework].md` |
| **mentor** | Agent that guides users through founder process milestones via structured questioning | [mentor.md](agents/mentor.md) |
| **lavoisier** | Agent that guides design direction and extracts design specifications | [lavoisier.md](agents/lavoisier.md) |

---

## Agent Handoff Protocol

The founder module is designed so that **multiple agents can execute work on the same project with zero shared memory**. All context between agents passes through files. This section defines exactly which files carry which role.

### File Roles

| File | Role | Contains | Updated When |
|------|------|----------|--------------|
| `[project]_memo.md` | **Evolving narrative** | Project vision, problem, solution, tenets, progress per milestone, open questions, next steps | After completing a framework or synthesizing findings |
| `m[x]_founder_diary.md` | **Operational state & strategic context** | Current milestone, last work done, up next, framework status table, file map, working memory log, ideas for future, decisions, pivots, blockers, invalidated assumptions, external shifts, learnings | Every session start and end, after every document change (working memory row), and when diary-worthy events occur during work |
| Framework docs (applied) | **Framework outputs** | Completed analyses following framework methodology | During guided framework work |

### Why Two Core Files

- **_memo.md** answers: *"What is this project about?"* — the narrative a stakeholder (human or agent) reads to understand the project holistically.
- **_diary.md** answers: *"Where are we? What was done? What is next? Why is the project in this state?"* — operational state and strategic context for any agent to resume work without re-discovering decisions or repeating mistakes.

The diary combines operational tracking with strategic context logging, ensuring agents can both resume work and understand the decision history that led to the current state.

### Diary Filtering Test

Before adding a diary entry, apply this test:

> *"In 3 months, will an agent need this to understand why the project is in its current state, or to avoid repeating a mistake?"*

- **YES** → Log it with full context (Decision, Pivot, Blocker, Assumption Invalidated, External Shift, Learning).
- **NO** → Do not log. Task completions go in _memo.md Progress section.

### Agent Session Protocol

**When a new agent starts work on a project:**

*Note: If the user references a specific diary file (e.g., `@m2_founder_diary.md`), start with Step 1. Otherwise, read `[project]_memo.md` Status section first to determine current milestone.*

| Step | Action | File | Purpose |
|------|--------|------|---------|
| 1 | Read milestone diary | `m[x]_founder_diary.md` | Know current milestone, last work, up next, framework status, and strategic decisions |
| 2 | Read process structure | `system/founder/founder_process.md` | Understand milestone lifecycle and navigate to current milestone |
| 3 | Read milestone process | `m[x]_[name]/[name]_process.md` | Understand steps and framework sequence for current milestone |
| 4 | Read current framework | Framework doc linked from process doc | Understand methodology for the specific framework being worked |
| 5 | Read diary template | `system/founder/templates/founder_diary.md` | Know diary structure and filtering rules |
| 6 | Read project memo | `[project]_memo.md` | Understand project narrative and context |
| 7 | Confirm with user | — | Present current state and confirm next steps before proceeding |

**During work:**

| Trigger | Action | File |
|---------|--------|------|
| Document changed | Add Working Memory row | `m[x]_founder_diary.md` |
| Diary-worthy event detected | Add diary entry | `m[x]_founder_diary.md` |
| Framework section completed | Write section in applied framework doc | `[project]/founder/[milestone]/[framework].md` |

**When ending a session:**

| Step | Action | File |
|------|--------|------|
| 1 | Update "Last Work Executed" with narrative sentence | `m[x]_founder_diary.md` |
| 2 | Update "Up Next" with contextual next action | `m[x]_founder_diary.md` |
| 3 | Update "Framework Status" table if framework status changed | `m[x]_founder_diary.md` |
| 4 | Verify all document changes are logged in Working Memory | `m[x]_founder_diary.md` |
| 5 | Confirm with user | — |

---

## Module Rules

| Rule | Description |
|---|---|
| Founder diary as session entry point | Founder diary is the starting point for every session. Agents read it first. |
| Template compliance | When updating project documents, agents must read the corresponding template |
| Brownfield structure | Founder outputs live within the project repo at `[project]/docs/founder/`, not within robotville |

---

## Milestones Summary

| Milestone | Goal | Key Frameworks | Process Doc |
|-----------|------|----------------|-------------|
| M1: Conception | Structure idea into comprehensive business concept | Working Backwards, Jobs-to-be-Done, Competitive Landscape, Problem-Solution Fit, Lean Canvas, 5 Whys | [conception_process.md](m1_conception/conception_process.md) |
| M2: Validation | Validate technical and financial feasibility through research | Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem | _Under development_ |
| M3: Brand | Create preliminary brand book | Brand Archetypes, Brand Prism, Golden Circle, Positioning Statement, Tone of Voice | _Under development_ |
| M4: Prototypation | Enable F&F testing with working HTML prototype | User Flow Mapping, Information Architecture, Design Brief, Atomic Design, Conversion-Centered Design, WCAG, Heuristic Evaluation | [prototypation_process.md](m4_prototypation/prototypation_process.md) |
| M5: Market Validation | Validate market/demand/pricing with low spending | Mom Test, SPIN Selling, Smoke Test, Van Westendorp PSM, Bullseye Framework, Sean Ellis PMF Survey | [market_validation_process.md](m5_market_validation/market_validation_process.md) |
| M6: MVP | Create MVP usable by real clients | User Story Mapping, INVEST Criteria, MoSCoW, Scrum/Agile, CI/CD, OWASP Top 10 | [mvp_process.md](m6_mvp/mvp_process.md) |

---

## Project Folder Structure

In the brownfield installation, each project is an independent git repository at the parent container level. Founder outputs live inside the project's `docs/founder/` directory, following the [project-structure.mdc](../../.cursor/rules/documentation/project-structure.mdc) rule.

```
[project]/
├── docs/
│   ├── founder/
│   │   ├── [project]_memo.md                     # Amazon-style narrative memo
│   │   ├── conception/
│   │   │   ├── m1_founder_diary.md               # Session tracking + decisions
│   │   │   ├── working_backwards.md              # Applied framework
│   │   │   ├── jtbd.md
│   │   │   └── ...
│   │   ├── validation/
│   │   │   ├── m2_founder_diary.md
│   │   │   └── ...
│   │   ├── brand/
│   │   │   ├── m3_founder_diary.md
│   │   │   └── ...
│   │   ├── prototypation/
│   │   │   ├── m4_founder_diary.md
│   │   │   ├── design_brief.md
│   │   │   ├── design-[artifact].json
│   │   │   └── ...
│   │   ├── market_validation/
│   │   │   ├── m5_founder_diary.md
│   │   │   └── ...
│   │   └── mvp/
│   │       ├── m6_founder_diary.md
│   │       └── ...
│   ├── architecture/
│   │   └── system_architecture.md
│   └── product/
│       ├── [feature_name].md
│       └── qa-[feature_name].md
├── deliverables/
│   └── [material]/
│       ├── design.md
│       ├── design.json
│       └── [deliverable].html
└── readme.md
```

**Naming conventions:** Milestone folders use plain names (not `m[x]_` prefix). Diary files use `m[x]_` prefix. Applied framework files use the framework name in snake_case.

---

## TEMPORARY: Framework Candidates

The tables below list framework candidates for each milestone. These will be migrated to individual framework documents in future iterations.

### M2: Validation

| Framework | Adopt | Rationale |
|-----------|-------|-----------|
| Leap of Faith | YES | Core framework. Stress-tests assumptions. |
| Assumption Mapping | YES | Visual prioritization. Complements Leap of Faith. |
| TAM/SAM/SOM | YES | Essential for financial validation. |
| Unit Economics | YES | Critical for viability (LTV, CAC, payback). |
| Technology Readiness Level | YES | NASA framework. Honest technical assessment. |
| Pre-mortem | YES | Surfaces hidden risks. Cheap, powerful. |
| Break-even Analysis | YES | Simple, essential financial grounding. |
| Technical Spike | YES | Answers "can we build this?" quickly. |
| Risk Matrix | YES | Simple visualization. Impact x Probability. |
| Porter's Five Forces | MAYBE | Useful but may be overkill for early-stage. |
| Sensitivity Analysis | MAYBE | Good for robust models. May be overkill. |

### M3: Brand

| Framework | Adopt | Rationale |
|-----------|-------|-----------|
| Brand Archetypes | YES | 12 universal character types. Industry standard. |
| Brand Prism (Kapferer) | YES | 6-facet identity model. Comprehensive. |
| Golden Circle (Sinek) | YES | "Start with Why." Simple, powerful. |
| Brand Positioning Statement | YES | Classic single-sentence market position. |
| Perceptual Map | YES | Visual competitive positioning. |
| Messaging Architecture | YES | Hierarchical message structure. |
| Tone of Voice Guidelines | YES | Practical for execution. |
| Visual Identity Principles | YES | Typography, color, imagery rules. |
| Brand Story | YES | Emotional connection. Humanizes brand. |

### M4: Prototypation

| Framework | Adopt | Rationale |
|-----------|-------|-----------|
| User Flow Mapping | YES | Essential before building. |
| Information Architecture | YES | Organizes prototype content. |
| Atomic Design | YES | Scalable design system. |
| Conversion-Centered Design | YES | 7 principles for conversion. |
| Heuristic Evaluation | YES | Cheap usability check. |
| WCAG Accessibility | YES | Legal/ethical requirement. |
| Responsive Design | YES | Table stakes. Mobile-first. |
| Design Tokens | YES | Consistency via design.json. |
| Progressive Disclosure | YES | Reduces cognitive load. |

### M5: Market Validation

| Framework | Adopt | Rationale |
|-----------|-------|-----------|
| SPIN Selling | YES | Core for customer conversations. |
| Smoke Test | YES | Classic validation. Minimal investment. |
| Mom Test | YES | Bias-free customer interview technique. |
| Sean Ellis PMF Survey | YES | 40%+ "very disappointed" = PMF signal. |
| Bullseye Framework | YES | 19 channels, prioritize 3. |
| Van Westendorp PSM | YES | 4 questions reveal price range. |
| A/B Testing | YES | Essential for variant testing. |
| Funnel Analysis | YES | Identifies drop-off points. |
| Customer Development | YES | Steve Blank. Get out of building. |
| Fake Door Test | YES | Cheap validation via non-existent button. |

### M6: MVP Development

| Framework | Adopt | Rationale |
|-----------|-------|-----------|
| User Story Mapping | YES | Visualize product backbone. |
| INVEST Criteria | YES | Quality user story checklist. |
| MoSCoW Prioritization | YES | Simple. Forces hard choices. |
| Scrum/Agile | YES | Industry standard. |
| Feature Flags | YES | Enables gradual release. |
| Technical Architecture Patterns | YES | Critical for scalability. |
| CI/CD Pipeline | YES | Quality gate. |
| Instrumentation/Analytics | YES | Essential for measuring MVP. |
| Error Monitoring | YES | Observability. |
| OWASP Top 10 | YES | Security. Non-negotiable. |
| Launch Checklist | YES | Operational readiness. |
| Soft Launch Strategy | YES | Risk mitigation. |

---
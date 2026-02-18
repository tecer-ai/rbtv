# Getting Started with Founder Module

**Purpose:** Quick-start guide for using the founder module to take your idea from concept to MVP.

**Reading time:** 3 minutes

---

## What is the Founder Module?

The founder module is a structured journey that guides you through **6 milestones** to transform a raw idea into a launch-ready MVP. It's designed for weeks of focused work, not quick tasks.

Your guide is the **mentor** agent — invoke via `/bmad-rbtv-mentor` or `@mentor`. Mentor asks critical questions, challenges assumptions, and helps you build comprehensive documentation incrementally.

---

## How to Start

### Starting Fresh with a New Idea

Invoke `/bmad-rbtv-mentor` or `@mentor` and describe your idea:

```
@mentor I want to build a [brief description of your idea]
```

Mentor will begin guiding you through **M1: Conception**, asking 2-3 questions at a time to structure your idea into a comprehensive business concept.

### Continuing an Existing Project

If you already have a project with a founder diary, reference it when calling mentor:

```
@mentor @m1_founder_diary.md
```

Mentor will read the Session Status in your founder diary and pick up where you left off.

---

## The Six Milestones

| # | Milestone | Goal |
|---|-----------|------|
| **M1** | **Conception** | Structure idea into comprehensive business concept |
| **M2** | **Validation** | Validate technical and financial feasibility |
| **M3** | **Brand** | Create preliminary brand book |
| **M4** | **Prototypation** | Build working HTML prototype for friends & family testing |
| **M5** | **Market Validation** | Validate market demand and pricing |
| **M6** | **MVP** | Create MVP usable by real clients |

Each milestone uses proven business frameworks (Working Backwards, Jobs-to-be-Done, SPIN Selling, etc.) to ensure rigorous thinking and complete documentation.

---

## What Mentor Does

Mentor guides you through each milestone by:

- **Asking critical questions** — 2-3 at a time to avoid overwhelming you
- **Challenging assumptions** — Intentionally critical because startup ideas need rigorous testing
- **Writing incrementally** — Builds documentation section by section as you answer questions
- **Tracking decisions** — Logs critical events (decisions, pivots, blockers, learnings) in the founder diary
- **Applying frameworks** — Guides you through relevant business methodologies for each milestone
- **Reminding you to logout** — Always logout with mentor before leaving a session so project documents get updated

---

## What Gets Created

As you work through the founder module, mentor creates a structured folder inside your project's `docs/` directory:

```
[your_project]/docs/founder/
├── [project]_memo.md               # Amazon-style narrative memo
├── conception/
│   ├── m1_founder_diary.md         # Session tracking + decisions log
│   ├── working_backwards.md        # Applied framework
│   ├── jobs_to_be_done.md          # Applied framework
│   └── ...
├── validation/
│   ├── m2_founder_diary.md
│   └── ...
└── ... (one folder per milestone)
```

The **founder diary** is your session entry point — it tracks what you're working on, what happened last session, and what comes next.

---

## How to Catch Up Later

Working through the founder process takes weeks. When you return to a project after a break:

```
@mentor @m[x]_founder_diary.md
```

Mentor will read your founder diary Session Status and help you continue from where you left off.

---

## What Makes This Different

**The founder module doesn't make decisions for you.** It asks the right questions so *you* make better decisions.

AI tools are powerful executors, but execution without direction produces outputs that don't connect to a coherent whole. The founder module provides the strategic layer — the structured thinking — that happens *before* you start building.

---

## Next Steps

Ready to start? Invoke `/bmad-rbtv-mentor` or `@mentor` with your idea or project reference.

**Module documentation:** [founder_process.md](founder_process.md) contains detailed information about all milestones, frameworks, and folder structure.

---
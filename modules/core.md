# Core

## Purpose

The core module is always installed — it's the foundation every other RBTV module depends on. Its theme is powering up AI use itself: guided git commits, web research with citation discipline, end-of-session context preservation, and the behavioral rules that passively shape every Claude interaction in any workspace where RBTV is present. If you install RBTV at all, you have core.

---

## Components

### Git

#### `rbtv-commit`

- **What**: A guided git commit workflow that analyzes your diff, clusters changes by concern (one commit per cluster — unrelated changes never share an umbrella commit), drafts a conventional commit message per cluster, checks for remote changes before committing, handles stash/conflict scenarios, stages specific files (never `git add -A`), and checks the index for pre-staged foreign files before each commit (unstage or disclose — never commit them silently).
- **When to use**: Any time you want to commit changes. Also triggers automatically when a task finishes and you say something like "done, save this."
- **How to invoke**: Say "commit", "commita", or "salva no git". The skill also fires when you say "done, commit this" after completing a task.
- **What it produces**: One or more scoped commits in the current repo, with the commit plan confirmed by you before anything is staged. Push happens only if you ask for it.
- **Example**:
  > User: "commit my changes"
  > Agent runs `git status` and `git diff`, then:
  > "Here's what changed: [summary]. Proposed message: `fix(auth): handle expired token on refresh`. Confirm or edit?"
  > User: "looks good"
  > Agent stages specific files, commits, and reports the commit hash. Does not push unless asked.

  If remote commits exist that you don't have locally, the skill fetches first, stashes your work, pulls, and pops — surfacing conflicts for you to resolve before touching the commit step.

**Commit message style:** `rbtv-commit` follows [conventional commits](https://www.conventionalcommits.org/): first line under 72 characters, message explains the *why* (the diff already shows the what).

---

### Research

#### `rbtv-web-searching`

- **What**: Three-mode web interaction layer — Preview (title/description only), Extract (full page content via Defuddle CLI), and Research (multi-source, cited, scored). Research mode enforces data integrity: every claim requires a verified source, sources are scored on authority/trustability/topic-match, and anything below a 6/10 threshold is discarded. Output always includes a citation legend and a "Sources Discarded" section. Research mode also accepts an OPTIONAL sources manifest — when the dispatch or user names a curated preferred/banned-sources file, Research favors the preferred origins and excludes the banned ones from primary support; absent a pointer, behavior is unchanged.
- **When to use**: Any time you give Claude a URL to read, ask it to research a topic, or need facts with citations. This skill is also mandatory for any sub-agent doing web work — parent agents must name it explicitly in sub-agent prompts.
- **How to invoke**: Triggered automatically when you paste a URL or ask Claude to research something. Invocable directly: `rbtv-web-searching`.
- **Inputs / outputs**:
  - Preview: URL → title + description
  - Extract: URL → clean markdown article body (Defuddle removes ads/nav)
  - Research: topic → structured report with scored citations, discarded sources, and fact/analysis/speculation labels
- **Example**: "Research the current state of AI agent frameworks" → Claude searches, scores sources, and returns a cited report with a legend and discarded-sources list.

---

### Personas

#### `/rbtv-session-close` (Ana)

- **What**: Invokes Ana, a session-close specialist persona. Ana presents a menu with three modes: **Compound** (captures an agent correction or improvement as a backlog PRD — turns a session fix into a durable system change), **Handoff** (writes a context-transfer document so the next agent session picks up seamlessly), and **Refresh** (updates an active plan or PRD with outcomes from this session, no new file).
- **When to use**: End of any significant working session — especially when the session produced corrections, decisions, or scope changes worth preserving. Run before closing a long planning or coding session to avoid losing context.
- **How to invoke**: `/rbtv-session-close` — or with a mode flag: `/rbtv-session-close compound`, `/rbtv-session-close handoff`, `/rbtv-session-close refresh`.
- **Inputs / outputs**:
  - Input: mode selection (or Ana suggests one based on session content)
  - Output: one of — a backlog PRD (compound), a handoff document (handoff), or an in-place update to an existing plan/PRD (refresh)
- **Example**: After a session where Claude made an error you corrected: `/rbtv-session-close compound` → Ana captures the correction as an improvement PRD, ready for the RBTV backlog.

---

## Rules — always-loaded behavior

These rules are copied into every workspace's `.claude/rules/` on install and shape Claude's behavior across every interaction. They aren't invoked manually — they're passive context that fires automatically. Full text is in the linked files.

Rules marked **stale** are retired: the installer skips any manifest entry flagged `stale` — it neither installs nor surfaces them — though the source files remain for reference.

| Rule | What it enforces |
|------|------------------|
| [atomic-files](../core/rules/atomic-files.md) | Agent-facing files must be self-contained, non-repetitive, and use mandatory language — no context-only references or summarized file content |
| ~~[audio-aware](../core/rules/audio-aware.md)~~ | **Stale — retired, not installed.** Handled transcription artifacts and loaded a name glossary at session start. Superseded by per-skill glossary loading in the meeting/therapy summarizers. |
| ~~[bash-patterns](../core/rules/bash-patterns.md)~~ | **Stale — retired, not installed.** Banned shell operators (`\|`, `&&`, `;`, redirects) in Bash calls. Obsolete under Claude auto-mode. |
| [chat-discipline](../core/rules/chat-discipline.md) | Every response leads with the decision or result, not the analysis; prose capped at 6 lines outside tables/code; full detail goes to output files |
| [compounding](../core/rules/compounding.md) | On any user correction, Claude checks whether a structural fix (rule, workflow, routing change) would prevent recurrence and offers to implement it |
| ~~[context-preservation](../core/rules/context-preservation.md)~~ | **Stale — retired, not installed.** Detected valuable session context and routed it before the session ends. Did not reliably trigger; superseded by session-close and compounding. |
| [deterministic-first](../core/rules/deterministic-first.md) | Agents prefer the deterministic capabilities the workspace already has over LLM improvisation; exact-answer work (sums, counts, reconciliations, date math) must be computed by a real tool/script, never estimated; scripts built for recurring work get proposed for promotion into their workflow. Hard gate on the exact-answer arm, advisory on the rest |
| [output-resolution](../core/rules/output-resolution.md) | Before writing any output file, Claude proposes a specific resolved path with reasoning and waits for confirmation — never writes to an assumed location |
| [reasoning](../core/rules/reasoning.md) | Mandates a `<counter>` block before any agreement or endorsement; enforces position stability under pressure; prevents sycophancy. Includes a *Problem Framing* section (symptom-check intake via Five Whys, deliverable-first commitments, options-with-tradeoffs, impact-scaled gap/assumption surfacing, root-cause discipline) and an *Execution Discipline* section (simplicity, surgical changes, goal-driven, read-before-write, verify-absence, budgets, checkpoints, fail-loud) covering all artifact work, not only code |
| [skill-first](../core/rules/skill-first.md) | The first tool call on any new task must be a skill scan — Claude cannot proceed to Read/Grep/Bash before checking whether a skill covers the task |
| [sub-agents](../core/rules/sub-agents.md) | Pre-dispatch gate for every Agent tool call — sub-agent prompts must explicitly name each matching installed skill using imperative phrasing |

> The `source-of-truth` rule (installed copies are generated — edit the RBTV source) was recovered from retirement and now ships with the **builder** module — see [modules/builder.md](./builder.md).

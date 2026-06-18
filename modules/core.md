# Core

## Purpose

The core module is always installed — it's the foundation every other RBTV module depends on. Its theme is powering up AI use itself: guided git commits, web research with citation discipline, end-of-session context preservation, and the behavioral rules that passively shape every Claude interaction in any workspace where RBTV is present. If you install RBTV at all, you have core.

---

## Components

### Git

#### `rbtv-commit`

- **What**: A guided git commit workflow that analyzes your diff and clusters changes by concern (one commit per cluster — unrelated changes never share an umbrella commit), then drafts a conventional commit message per cluster. You do the judgment; a deterministic script (`commit.py`) then runs every git mechanic in one shot per commit — it unstages everything and stages only that cluster's files (so a parallel session's staged file is never swept in — its changes stay in your working tree), syncs the remote, commits, and optionally pushes. It fails loudly and makes no commit on a real merge conflict.
- **When to use**: Any time you want to commit changes. Also triggers automatically when a task finishes and you say something like "done, save this."
- **How to invoke**: Say "commit", "commita", or "salva no git". The skill also fires when you say "done, commit this" after completing a task.
- **What it produces**: One or more scoped commits in the current repo, with the commit plan confirmed by you before anything is staged. Push happens only if you ask for it.
- **Example**:
  > User: "commit my changes"
  > Agent runs `git status` and `git diff`, then:
  > "Here's what changed: [summary]. Proposed message: `fix(auth): handle expired token on refresh`. Confirm or edit?"
  > User: "looks good"
  > Agent stages specific files, commits, and reports the commit hash. Does not push unless asked.

  If remote commits exist that you don't have locally, the script commits your cluster locally first, then pulls — a clean auto-merge is handled silently. A real conflict aborts the merge and undoes the local commit (your changes are left staged, nothing lost), and the script surfaces the conflicting files for you to resolve before retrying.

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

### File operations

#### `rbtv-safe-move`

- **What**: Moves or renames a file or folder in one git-aware operation that also finds and fixes every reference to it — markdown links, wikilinks, frontmatter values, config paths, and code imports (matched structurally with `ast-grep`, never by raw text). Two stateless calls: `consult` (a dry run that finds, classifies, and risk-grades every reference and changes nothing) and `act` (performs the move and auto-applies the safe fixes, surfacing the risky ones for you). A per-reference hash handshake makes it drift-safe — editing a surfaced site between the two calls is safe; the tool refuses a changed site rather than clobbering it. The engine is a deterministic Python package (no LLM calls, no agent dispatch); the skill is a thin loader pointing to the usage guide and the package.
- **When to use**: Any time you or the user need to relocate or rename a file or directory and keep its references intact — instead of moving by hand and grepping for callers. Folder moves are the highest-value case.
- **How to invoke**: The skill fires when a move/rename with reference-fixing is needed; invocable directly as `rbtv-safe-move`. The tool runs in place from `{rbtv_path}/core/tools/safe-move` (`python -m safe_move consult|act …`) — it is NOT installed into `.claude/`; it is read from the RBTV source like a workflow.
- **What it produces**: From `consult`, a record per reference (id, file, line, match, proposed replacement, risk class — `auto`/`surface`/`protected` — and a hash) plus warnings and folder-cascade info. From `act`, the performed move (staged, not committed) and an action log of auto-fixed, surfaced, and drifted sites. The caller commits.
- **Prerequisite**: code-reference matching needs `ast-grep` via `npx`; without it the tool degrades gracefully (non-code references still work, a `code-backend-unavailable` warning is emitted).

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
| [sub-agents](../core/rules/sub-agents.md) | Pre-dispatch gate for every worker dispatch (Agent-tool, CLI, API) — the prompt must name each matching installed skill imperatively with its path, and give workspace-root-absolute write paths. Skill matching is description-based, any source; model policy lives in orchestration routing, not here |

> The `source-of-truth` rule (installed copies are generated — edit the RBTV source) was recovered from retirement and now ships with the **builder** module — see [modules/builder.md](./builder.md).

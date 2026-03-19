# Claude Skills - Platform Knowledge

Platform knowledge for building Claude Code skills: technical spec, design craft, and patterns.

---

## 1. Structure

Skills are YAML-frontmatter markdown files (`SKILL.md`) at `.claude/skills/{skill-name}/SKILL.md`, auto-detected by Claude agents.

A skill is a **folder**, not just a markdown file. The entire filesystem is a form of context engineering and progressive disclosure.

| Component | Location | Purpose |
|-----------|----------|---------|
| Entry file | `.claude/skills/{name}/SKILL.md` | Main definition with YAML frontmatter |
| Scripts | `.claude/skills/{name}/scripts/` | Executable scripts the skill can invoke |
| References | `.claude/skills/{name}/references/` | Documentation, API guides, examples |
| Assets | `.claude/skills/{name}/assets/` | Templates, configs, static data |

---

## 2. YAML Frontmatter

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | MUST match parent folder name exactly |
| `description` | string | What the skill does AND when to use it — this is for the **model**, not humans |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `license` | string | License identifier (e.g., `MIT`) |
| `compatibility` | string | Runtime version constraint (e.g., `claude-code >= 1.0`) |
| `metadata` | object | Contains `author` (string) and `version` (string) |
| `allowed-tools` | array | Permitted tool names (e.g., `['Read', 'Write', 'Bash']`) |

### Description Field

The `description` is the primary trigger mechanism. Claude scans all skill descriptions at session start to decide which skill matches a request.

| Bad | Good |
|-----|------|
| "A comprehensive tool for monitoring pull request status across the development lifecycle." | "Monitors a PR until it merges. Trigger on 'babysit', 'watch CI', 'make sure this lands'." |
| "Runs tests" | "Run project test suite with coverage. Use when validating changes, checking coverage, or before committing." |

Write for the model: include concrete trigger phrases that map to user intent, not abstract descriptions.

### Security Restrictions

- No XML angle brackets (`< >`) in YAML frontmatter (prevents injection)
- No `README.md` in skill folders

---

## 3. Body Content

| Section | Required | Purpose |
|---------|----------|---------|
| Title heading | Yes | Skill display name |
| Purpose | Yes | One-line statement |
| When to use | Yes | Bullet list of trigger conditions |
| Activation | Yes | Instructions for loading and executing |

### Naming

- Kebab-case only: `my-code-formatter`
- `name` field MUST match folder name exactly

---

## 4. Skill Categories

Skills cluster into recurring categories. The best skills fit cleanly into one.

| Category | Description | Examples |
|----------|-------------|----------|
| **Library & API Reference** | Internal libs, CLIs, SDKs, gotchas | billing-lib, platform-cli |
| **Product Verification** | Drive the running product to verify correctness | signup-driver, checkout-verifier |
| **Data & Analysis** | IDs, field names, query patterns, dashboards | funnel-query, grafana, datadog |
| **Business Automation** | Multi-tool workflows → one command | standup-post, weekly-recap |
| **Scaffolding & Templates** | Framework-correct boilerplate | new-app, migration, workflow |
| **Code Quality & Review** | Methodology that ships better code | adversarial-review, testing-practices |
| **CI/CD & Deployment** | Commit, push, deploy safely | babysit-pr, deploy, cherry-pick |
| **Incident Runbooks** | Symptom → investigation → report | oncall-runner, log-correlator |
| **Infrastructure Ops** | Safety-gated cleanup & maintenance | orphan-cleanup, deps, cost-investigation |

---

## 5. Design Principles

### Skip the Obvious

Focus on information that pushes Claude out of its default behavior. Claude already knows how to code — give it what it doesn't know: your org's conventions, edge cases, domain-specific gotchas.

### Build a Gotchas Section

The highest-signal content in any skill. Add a line each time Claude trips on something. Start minimal, grow over time:

```markdown
## Gotchas

- Proration rounds DOWN, not to nearest cent.
- test-mode skips the invoice.finalized hook.
- idempotency keys expire after 24h, not 7d.
```

### Progressive Disclosure

Keep SKILL.md lean (~30 lines). Tell Claude what files exist in the skill folder — it reads them at appropriate times.

```
queue-debugging/
  SKILL.md          ← hub (symptom → file dispatch table)
  stuck-jobs.md
  dead-letters.md
  retry-storms.md
```

### Avoid Railroading

State the goal and constraints. Do NOT write step-by-step shell commands.

| Too prescriptive | Better |
|-----------------|--------|
| "1. Run `git log`... 2. Run `git cherry-pick`... 3. Run `git status`..." | "Cherry-pick the commit onto a clean branch. Resolve conflicts preserving intent. If it can't land cleanly, explain why." |

### Setup & Config

Skills that need user-specific context (e.g., which Slack channel) can store setup in `${CLAUDE_SKILL_DIR}/config.json`. If not configured, the skill prompts the user on first run.

```markdown
`!`cat ${CLAUDE_SKILL_DIR}/config.json 2>/dev/null || echo "NOT_CONFIGURED"``

If NOT_CONFIGURED, ask the user for required settings and write to `${CLAUDE_SKILL_DIR}/config.json`.
```

### Memory & Persistent Data

Skills can store data (logs, JSON, SQLite) for cross-session memory. Use `${CLAUDE_PLUGIN_DATA}` for storage that survives skill upgrades.

Example: a standup skill appends each post to `${CLAUDE_PLUGIN_DATA}/standups.log`, then reads history on the next run to see what changed.

### Store Scripts & Libraries

Give Claude pre-built code to compose with rather than reconstruct from scratch. Store function stubs with detailed docstrings in `lib/` or `scripts/`. The model composes implementations from these specs.

### On-Demand Hooks

Skills can register hooks that activate only when the skill is called and last for the session duration. Use for opinionated guards:

- `/careful` — blocks `rm -rf`, `DROP TABLE`, force-push via PreToolUse matcher on Bash
- `/freeze` — blocks Edit/Write outside a specific directory

---

## 6. Patterns

### Thin Loader Pattern

For systems with external agents/workflows — minimal entry points that load and delegate:

```markdown
---
name: my-builder
description: Build components. Use when creating new system components.
---

# Builder Skill

**Purpose:** Load and execute the builder agent.

## Activation

Load and follow: `path/to/agent-or-workflow.md`
```

### Dispatch Hub Pattern

SKILL.md as a symptom-to-file routing table:

```markdown
| Symptom | Read |
|---------|------|
| Jobs sit pending, never run | stuck-jobs.md |
| Messages in DLQ, no retries | dead-letters.md |
```

---

## 7. Validation Checklist

- [ ] SKILL.md has valid YAML frontmatter
- [ ] `name` matches parent folder name exactly
- [ ] `description` includes what AND when, written for the model
- [ ] Skill activates on expected trigger conditions
- [ ] `allowed-tools` (if set) includes all tools the skill needs
- [ ] Body is self-contained and actionable
- [ ] Gotchas section exists (even if empty initially)

---

## 8. Distribution

Two distribution methods:
- **Repo-checked:** Place in `.claude/skills/` — every skill adds to model context, so scale carefully
- **Plugin marketplace:** Upload as a plugin for opt-in installation — better for large orgs

Skills are portable — copy the entire folder to share.

---

## 9. Troubleshooting

| Problem | Solution |
|---------|----------|
| Skill not detected | Verify path is `.claude/skills/{name}/SKILL.md` |
| Skill not triggered | Add explicit trigger phrases to description |
| YAML parse error | Check for unclosed quotes, improper indentation |
| Name mismatch | `name` field must match folder name |
| Tools not available | Add missing tools to `allowed-tools` |

---

*Last updated: 2026-03-19*
*Sources: Claude Code platform docs, Anthropic internal skill design lessons*

<!-- sb:start v=1 -->
# CLAUDE.md

Personal Obsidian vault structured as a second brain using the PARA method, managed by sb-os.

---

## Hard Rules

**Agent capture** — When you (an agent) capture content for the user (annotate, save, store, log, etc.), route DIRECTLY to the matching vault location. Default routing follows the PARA semantics below; the daily note is a fallback for genuinely ambiguous content, not a default.

| Content type | Default destination |
|--------------|---------------------|
| Bounded work with a defined "done" | `1-projects/{project-name}/` |
| Ongoing responsibilities (no defined endpoint) | `2-areas/{area-name}/` |
| Reference material, tools, knowledge bases | `3-resources/{topic}/` |
| Completed, abandoned, or under-review content | `4-archives/` |
| External code repos / project workspaces | `5-workbench/{repo-name}/` |
| Tasks for a specific project or area | `{project-or-area}-tasks.md` inside that folder |
| Genuinely ambiguous / no clear vault home | Daily note (`0-periodic-notes/daily/`) |

Fits an existing file → append. Index files (`{dir-name}.md`) are NEVER content destinations. Unclear destination → ask the user before writing.

**Exception — daily-note override.** When the user explicitly says "add to today", "save to daily", or "add to daily note", route to the daily note regardless of the table above.

**Auto-memory.** Claude Code's auto-memory serves ONLY for agent behavior feedback (preferences, corrections, workflow tweaks). Content goes to the vault. When in doubt, vault wins.

**Parallel sessions — write collisions.** On an Edit rejection for "file modified since read" (another session wrote the file), re-read the file and re-apply ONLY your delta to the fresh state — never restore frontmatter or body content from your earlier read. This retry is the canonical discipline; do not add lock or marker machinery.

**Parallel sessions — commit collisions.** Staging a file commits ALL its uncommitted hunks, including other sessions'. Before committing a vault file, diff it against your own session's delta — either confirm the foreign hunks ride along (disclose them in the commit message) or stop and re-scope. NEVER `git commit --amend` in the vault: HEAD may have moved to another session's commit between your read and the rewrite — fix history forward with a new commit, or not at all.

**Parallel sessions — working-tree reverts.** Edit rejection is not the only collision: a parallel session may `git restore` files in a shared repo and silently wipe your applied-but-uncommitted edits (observed 2026-06-05, sb-os). Immediately before staging, `git diff` each file you intend to stage and confirm your delta is still present; if wiped, re-read and re-apply only your delta, then commit without delay — the edit→commit window is the exposure.

Users extend these defaults by adding their own routing rules below the marker block — anything outside the markers wins over the marker-block defaults (agents read top-to-bottom).

---

## Naming Conventions

- Main file per directory = `{dir-name}.md` (e.g., a folder named `project-a/` has its index file `project-a.md`)
- Never use `README.md` as a vault index
- Folders, files, and tags use lowercase kebab-case in English. Proper nouns and acronyms are exempt
- Component prefixes: `sb-` (sb-os shippable), `rbtv-` (RBTV plugin if installed), no prefix (personal). Details: `docs/component-prefixes.md` in the sb-os repo

---

## Tags

Index (`{dir-name}.md`) and task (`{name}-tasks.md`) files carry their own directory name as the FIRST tag — the identity tag dashboards and agents key on. Projects declare their parent area via `area:` frontmatter on those two files, not via an area tag. Every other file gets its parent area tag (the directory name under `2-areas/`). Cross-cutting tags combine with these (examples: `decision`, `meeting`, `idea`). Resources may add topic tags (example: `ai-tools`). Periodic note status tags: `reviewed`, `routed`.

---

## Vault Structure

| Folder | Purpose |
|--------|---------|
| `0-periodic-notes/` | Periodic notes (Daily=inbox, Weekly, Monthly, Quarterly) |
| `1-projects/` | Bounded work — projects with a beginning and an end |
| `2-areas/` | Ongoing responsibilities (e.g., `area-personal/`, `area-work/`, `area-learning/`) |
| `3-resources/` | Reference content (e.g., `tools/`, `knowledge-base/`) |
| `4-archives/` | Holding zone before deletion — completed projects, abandoned files, content under review |
| `5-workbench/` | Project workspaces with their own git repos and structures |
| `.user/` | User-owned root: user-context folder + personal extensions (sb-os creates this directory on the initial install and never writes inside it thereafter) |

**Vault file** = any `.md` in PARA folders (`0-` through `4-`). **System component** = files under `.claude/` or the sb-os repo. `5-workbench/` contains independent repos — not vault files.

**Vault content** = vault files governed by sb-os conventions: indexes (`{dir-name}.md`), task files (`{name}-tasks.md`), references, logs, periodic notes. **Project deliverables** = technical documents governed by per-project workflows (PRDs, specs, plans, code) — sb-os does not police their format.

Loose `.md` files placed directly under any PARA folder (siblings of subfolders) are user-owned and freeform — sb-os does not manage their structure or naming.

`.claude/` contains ONLY what Claude Code recognizes natively (rules, skills, commands, settings).

---

## Component Placement

System component conventions ship with sb-os under the sb-os repo. Skills and commands installed into `.claude/` are ALWAYS thin loaders pointing to workflow files in the sb-os repo — never edit them in `.claude/` (overwritten on every install run).

The sb-os repo path on this vault is recorded in `sb-os.json` at the vault root (`sb_os_path` field). Edit sb-os components in the source repo, then re-run `python install.py`.

---

## Periodic Notes Templates

Templates for daily, weekly, monthly, and quarterly notes live at `.user/config/templates/periodic-notes/`:

| Template | Path |
|----------|------|
| Daily | `.user/config/templates/periodic-notes/Daily.md` |
| Weekly | `.user/config/templates/periodic-notes/Weekly.md` |
| Monthly | `.user/config/templates/periodic-notes/Monthly.md` |
| Quarterly | `.user/config/templates/periodic-notes/Quarterly.md` |

When the user says "log this to my daily note" (or weekly/monthly/quarterly), use the matching template's structure to create or append to the note in `0-periodic-notes/{period}/`. The note filename follows the Obsidian daily-notes plugin convention (e.g., `YYYY-MM-DD.md` for daily). Templates are user-owned and editable — sb-os bootstraps them on install but never overwrites them on upgrade.

<!-- sb:end -->

> Maintainer: this vault is owned by Henrique Teixeira, creator and maintainer of sb-os.

> Language: English by default in chat and file contents. Portuguese content only allowed in files of `0-periodic-notes/` and in conversation when running the `sb-life-planner` workflows.

---

## Personal Hard Rules (extend the sb-os defaults above)

| Content | Destination |
|---------|-------------|
| Articles, videos, podcasts, things to read/watch | `2-areas/learning/reading-list.md` (append) |
| Coding tools (IDEs, terminals, CLIs, MCP servers, dev frameworks, testing) | `3-resources/tools/catalogs/coding.md` (append) |
| AI infrastructure (gateways, agent platforms, observability, prompt frameworks, AI products) | `3-resources/tools/catalogs/ai-engineering.md` (append) |
| Visual design / content / marketing AI tools | `3-resources/tools/catalogs/creative.md` (append) |
| Sales prospecting, lead intelligence, outreach automation, ad ops | `3-resources/tools/catalogs/sales.md` (append) |
| Finance-AI content (prompts, trading playbooks, market analysis articles) | `3-resources/tools/catalogs/ai-finance.md` (append) |
| Reusable LLM prompts | `3-resources/tools/prompts/` (one file per prompt) |
| IDE, terminal, Claude Code, hardware setup/config | `2-areas/tech/my-setup/` |
| Financial pipeline (raw bank/broker data, processed ledgers, dashboard, scripts, docs) | `3-resources/tools/finance/` |
| Personal financial records (recurring payments, vault-content) | `2-areas/finance/` |
| Health content | `2-areas/health/` |
| Learning topics, study interests | `2-areas/learning/` |
| Tecer content | `2-areas/tecer/` |
| Project-specific content | `1-projects/{project}/` |
| Tasks for a specific project/area | `{project-or-area}-tasks.md` |
| Saved articles from newsletters/podcasts | `3-resources/knowledge-base/raw/{source}/` |
| Study session output (sb-tutor, multi-source notes) | `3-resources/knowledge-base/raw/studies/` (append) |
| Compound learning PRDs (session-close compound mode) | `.user/compounds/{component}/cp-{component}-{description}.md` (nested per component folder per `.user/compounds/CLAUDE.md`) |
| Done-gate evidence sheets + captures (`{evidence_root}` for `rbtv-done-gate`) | `1-projects/rbtv-evolution/coding/done-gate-evidence/{project}/` |

**Daily-note exception (extends canonical):** `mentor` invocation routes to the daily note instead of the vault — mentor outputs belong with the day's reflections.

## Name Glossary

Glossary path: `.user/docs/glossary.md`. The `rbtv-meeting-summarizer` and `therapy-summarizer` skills load it for transcription correction; load it yourself when correcting transcribed names in any other context.

## Environment Variables

Local API keys live in `.user/config/env/.env` (gitignored; tracked template at `.user/config/env/.env.example`). Scripts read the OS environment variable first, then fall back to that file. New machine setup: copy `.env.example` to `.env` and fill values. NEVER commit real keys or paste them into chat/transcripts.

---

## Agent Capabilities

Tools, runtimes, APIs, and libraries agents can INVOKE to build deterministic solutions — the inventory `rbtv-deterministic-first`'s **Reach** arm consults before improvising, and its **Register** arm appends to. This is a BUILD-capability list — NOT output routing or content locations (those live in the routing tables above), and NOT LLM worker agents (kimi/codex/claude-cli are orchestration workers — see `rbtv-orchestrating`). Full install/version detail: `2-areas/tech/my-setup/dev-environment.md` (keep in sync).

**Runtimes & languages**

| Capability | Invoke | Use for |
|-----------|--------|---------|
| Python 3.x | `python` (per-workflow venvs where noted) | Exact computation, data transforms, reconciliations, scripts |
| Node.js 24 | `node` / `npx` | JS tooling; runs the CLIs below |

**Deterministic CLIs & tools**

| Capability | Invoke | Use for |
|-----------|--------|---------|
| agent-browser | `agent-browser` | Headless browser automation (navigate, fill, click, screenshot, scrape) |
| Playwright | `npx playwright` | Browser automation + E2E testing |
| Defuddle | `defuddle` | Extract clean markdown from a web page (strips nav/ads) |
| md-to-pdf | `md-to-pdf` | Markdown → styled PDF (custom CSS, headers/footers) |
| Mermaid CLI | `mmdc` | Render Mermaid diagrams to images |
| Netlify CLI | `netlify` | Deploy/manage Netlify sites |

**APIs**

| Capability | Invoke | Use for |
|-----------|--------|---------|
| Voyage AI embeddings | `VOYAGE_API_KEY` in `.user/config/env/.env` | Semantic similarity, embeddings (powers tecer-search) |
| Google Workspace | google-tools venv in `3-resources/tools/google/` (or the `google-tools` skill) | Gmail, Calendar, Drive read/write |

**MCP tools** (agent-native, no shell)

| Capability | Invoke | Use for |
|-----------|--------|---------|
| Chrome DevTools | `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*` | Browser automation, network/console inspection, performance traces, screenshots, Lighthouse |

**Key Python libraries** (installed per workflow; full list in `dev-environment.md`)

| Domain | Libraries |
|--------|-----------|
| Numeric / finance | `numpy-financial`, `scipy`, `openpyxl`, `yfinance`, `requests` |
| PDF extraction | `pdfplumber`, `pikepdf` |
| Google APIs | `google-api-python-client`, `google-auth`, `google-auth-oauthlib` |

When an agent builds or discovers a durable deterministic capability, append it here (Register arm); if a tool was installed, also update `dev-environment.md`.

---

## Communication & Working Preferences

Cross-cutting personal defaults for how agents interact with me (migrated from the retired `sb-user-preferences` rule). Workflow-specific preferences live in `.user/context/{workflow}/` YAMLs instead.

- **Input:** primarily audio dictation — expect transcription artifacts (see Name Glossary).
- **Style:** direct, technical, executive-summary by default; high-level first, expand only on request.
- **Reasoning:** show on request, not by default.
- **Decisions:** present as multiple choice (a, b, c, … or "none of the above").
- **Proactivity:** autonomous — recommend with alternatives.
- **Assumptions:** evaluate impact first; always ask on high-impact subjects.
- **Output format:** large code blocks, tables, or long text go to a file reference, never inline in chat.
- **Never lose information:** session logs, triple-checks, and reconciliations exist to preserve data — when in doubt, preserve and surface; never silently discard.

Language convention is the Language note above. Brevity/decision-first output is also enforced by `rbtv-chat-discipline`; root-cause-over-symptom and direct, no-ego feedback by `rbtv-reasoning`.

---

## Agent Tooling Caveats

- **Windows Glob false negatives:** the Glob tool silently returns empty or partial results on this machine — observed 2026-06-04 with a brace-of-directories pattern (`{a16z,bain,…}/*.md` → one origin only) and with a plain `subdir/*.md` pattern (`rules/*.md` → "no files" in a folder holding 14). Grep's `glob` filter shares the failure (brace filter → "no matches" over files that had them). NEVER conclude files are absent from a single empty/partial Glob — verify with a Grep content search, `ls`, or a `**/` pattern. Canonical rule: `rbtv-reasoning` § Execution Discipline → "Verify absence".

---

## Personal Component Placement (extends the sb-os defaults above)

Skills and commands installed into `.claude/` are ALWAYS thin loaders. They point to:
- `3-resources/tools/sb-os/` — for open-sourced sb-os components
- `3-resources/tools/rbtv/` — for open-sourced RBTV components
- `.user/workflows/{name}/` — for personal-only workflows (accountant, mentor, sb-life-planner, therapy-summarizer)

Edit the component in its source repo above, then re-run that repo's `install.py` — installed `.claude/rbtv-*` and `.claude/sb-*` copies are regenerated on every run and any direct edit is lost. This is the canonical home of the retired `rbtv-source-of-truth` rule; the active `sb-source-of-truth` rule enforces the same for sb-os components.

---

## Git Repositories

Projects with their own Git repos. The commit skill uses this table to resolve repo paths.

| Project | Repo path | Remote | Entry point |
|---------|-----------|--------|-------------|
| **Tennis Arte** — website | `5-workbench/tennis-arte/` | https://github.com/hlealt/tennis-arte | `1-projects/tennis-arte/CLAUDE.md` |
| **Tecer** — Finance ops startup with AI | `5-workbench/tecer-biz/` | https://github.com/tecer-ai/tecer-biz | Root `CLAUDE.md` of that repo |
| **Inni CTe Recon** — CTe reconciliation | `5-workbench/inni-cte-recon/` | https://github.com/tecer-ai/inni-cte-recon | Root of that repo |
| **Tecer** — website | `5-workbench/tecer-website/` | https://github.com/tecer-ai/tecer-website | Root of that repo |
| **Personal** — personal dev projects | `5-workbench/personal/` | https://github.com/hlealt/personal | `5-workbench/personal/CLAUDE.md` |
| **rbtv** — business innovation module | `3-resources/tools/rbtv/` | https://github.com/tecer-ai/rbtv | Root `CLAUDE.md` of that repo |
| **Google Tools** — Gmail/Calendar/Drive Python tooling, third-party-managed, **READ ONLY NEVER EDIT, COMMIT OR PUSH** (sole exception: `config.yaml` carries a local uncommitted account edit — canonical backup in `.user/config/google-tools/config.yaml`) | `3-resources/tools/google/` | https://github.com/tecer-ai/google-tools | `3-resources/tools/google/CLAUDE.md` |
| **sb-os** — second-brain OS (this vault's framework) | `3-resources/tools/sb-os/` (path recorded in `sb-os.json`) | https://github.com/hlealt/sb-os | Root `CLAUDE.md` of that repo |
| **weaver** — Tecer's production system, not managed by be, **READ ONLY NEVER EDIT, COMMIT OR PUSH** | `5-workbench/weaver` | https://github.com/tecer-ai/weaver/ | Root `AGENTS.md` of that repo |
 

In-vault repos are nested git repos, gitignored from the vault's own git (see root `.gitignore`). Each maintains its own history; the vault only tracks task and area context. To bootstrap a missing repo, clone its remote into the listed Repo path (e.g., `git clone https://github.com/tecer-ai/rbtv 3-resources/tools/rbtv`).

> Codex mirror note: do not read the sibling `AGENTS.md`. It is an auto-generated mirror for Codex agents. This `CLAUDE.md` file is the source of truth.

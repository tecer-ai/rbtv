# RBTV

Short for Robotville, RBTV is a standalone Claude Code toolkit for business innovation, pitch generation, documentation, and structured thinking.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules designed to be bootstrapped into any Claude Code workspace. After install, RBTV appears as `/rbtv-<command>` slash commands (e.g., `/rbtv-strategist`, `/rbtv-doc-export`, `/rbtv-planning`) and auto-triggered skills in your workspace.

## Modules

Each module is documented in detail in [`modules/`](./modules/). The doc covers the module's purpose, every component it ships, and how to use them. The repo is module-first: each module's components live under its own root folder (`core/`, `office/`, `studio/`, …) organized by type (`skills/`, `commands/`, `rules/`, `personas/`, `tasks/`, `workflows/`).

| Module | What it does | Doc |
|---|---|---|
| **core** (always installed) | Powering up AI use — guided git commits, web research, session close, and the always-on behavioral rules | [modules/core.md](./modules/core.md) |
| **office** | Daily knowledge work — document export (PDF/DOCX with brand discovery), legal advisory, meeting prep, meeting summarization, client emails, and the structured-thinking persona (problem structuring, idea sparring, plus pre-mortem, first-principles, and six-thinking-hats modes; formerly `productivity`) | [modules/office.md](./modules/office.md) |
| **studio** | Design and communication module — the studio loop entry (`/rbtv-strategist` — opens the Strategist for message-lock, then hands off to design); the four-beat studio loop (message-lock · art-direction · generate · human-gate) covering deck, site, and app artifacts; artifact forks for sites (`forks/site.md` — structure beat + responsive multi-page HTML contract) and apps (`forks/app.md` — goals/user-flow/UX discovery beats + plain-HTML designed-screens contract + coding-agent handoff package); the Strategist persona (four audience modes: investor · client · site-marketing · app-product); Vivian the Designer (`rbtv-designing`); standards bundle (ban-list + flaw-checklist + UX companion-docs contract); v1.1 comparative taxonomy-driven critic (never gates — improver + stopping rule, optional loop wiring via `critic: on`); design-state schema; reference-set scaffold; design-token extraction from live sites; reference-image forensics into regeneration prompts (`/rbtv-vision-to-json`); browser automation; AI image generation; exemplar-screenshot capture; motion/interaction reference extraction; and the hypresent presentation engine | [modules/studio.md](./modules/studio.md) |
| **orchestration** | Long-horizon work — general multi-agent orchestration (route tasks to the right worker, dispatch self-contained artifacts, verify every return against disk, recover from halts; single front door incl. CLI-model dispatch), per-model CLI dispatch packages (kimi-code-cli, codex-cli, claude-code-cli, qwen-code-cli — doc packages read just-in-time, elected per workspace at install), a deterministic router script (`orchestration/models/route.py` — task profile → route/self_execute/halt_seam verdict) that the routing card CALLS instead of hand-resolving the selector, Fable 5 (`claude-code-native:fable`) pinned as the default conductor and final-plan reviewer, structured planning, plan execution via tiered sub-agents, and long-source mining | [modules/orchestration.md](./modules/orchestration.md) |
| **builder** | Building RBTV itself — component creation (with a build-time efficiency gate), component token-efficiency review, and the source-of-truth rule | [modules/builder.md](./modules/builder.md) |
| **innovation** | Business innovation frameworks (lean canvas, JTBD, TAM/SAM/SOM, brandbook) via the innovator mentor, plus product discovery | [modules/innovation.md](./modules/innovation.md) |
| **writing** | Long-form writing via the writer persona, tone extraction | [modules/writing.md](./modules/writing.md) |
| **coding** | Plain-language code communication for non-technical users, plus the done-gate rule — done on coding tasks requires an owner-confirmed outcome contract, real-input exercise of each criterion, and a per-criterion evidence sheet on disk; the done gate also carries a Contract-time drivability check (merged in from the former build-for-agent-testability rule) so surfaces the agent can't drive (native dialogs, isolated-run config, fused output) get a test seam built into the feature (git commits moved to core; the coding-discipline guardrails were generalized into the always-on reasoning rule — see [Retired components](#retired-components)). The done gate is split into a thin always-on trigger rule (≈404 words) plus an on-fire protocol body (≈2,028 words) loaded via a skill loader only when a coding task starts — so the always-on cost is ≈1,123 words (was ≈2,901); a workspace that does no coding omits this module at install to drop even that (see [modules/coding.md](./modules/coding.md) § Scoping) | [modules/coding.md](./modules/coding.md) |
| **caveman** | Optional ultra-compressed caveman communication mode and parody commit voice — token savings and fun, based on JuliusBrussee/caveman | [modules/caveman.md](./modules/caveman.md) |

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+
- Claude Code plugins (see [Plugins](#plugins) for install instructions)

## Install

1. Clone RBTV as a subfolder of your workspace:

   ```bash
   cd /path/to/your/workspace
   git clone <rbtv-repo-url> rbtv
   ```

   RBTV must live INSIDE the workspace that will use it.

2. Run the installer:

   ```bash
   python rbtv/install.py --target /path/to/your/workspace
   ```

   The installer prompts for:
   - Modules to install (core is always included)
   - Orchestration model packages (when the `orchestration` module is selected): which per-model CLI dispatch packages — `kimi-code-cli`, `codex-cli`, `claude-code-cli`, `qwen-code-cli` — to make available in this workspace. These are doc packages read just-in-time from the RBTV source (not copied into `.claude/`); the installer records the selection in `rbtv.json` and bakes a `Model packages installed: … — absent: …` availability line into the `rbtv-orchestrating` core so the skill knows what is routable here. Scripted: `--model-packages kimi-code-cli,codex-cli` (omit to keep the prior selection or elect all; `--model-packages ""` elects none). The installer also runs an advisory manual-render freshness check (warns if any generated manual is stale relative to its sources; never aborts the install). Electing a package that carries a mirror config also **renders its worker mirror** in the target workspace (guidance file, per-model config dir, and skill loaders under `.agents/`) via the mirror driver at `orchestration/models/mirror/driver/`; deselecting a package removes its mirror artifacts (ref-counted — shared files such as `AGENTS.md` are only removed when all packages that share them are deselected). Mirror state is persisted in a single `model_mirror` block in `rbtv.json`. Use `--mirror` to refresh mirror artifacts only (skips component install, reads the existing `rbtv.json` election). The orchestration model packages also include **API-worker packages** (`deepseek-api`, `gemini-api`, `claude-code-native`, `manus-api`) that run via a shared API runner (`orchestration/models/_api/run.py`) with keys resolved from the `env_file` path in `rbtv.json` — distinct from the CLI dispatch packages (kimi-code-cli, codex-cli, claude-code-cli, qwen-code-cli), which invoke local executables rather than calling provider APIs. (`manus` is the agentic-web worker — autonomous server-side browser/tool loop, per-task cost, raw-dump return only.)

   Output paths are resolved at runtime by the `rbtv-output-resolution` rule, which uses conversation context and workspace CLAUDE.md conventions to propose paths.

3. After install, your workspace has:
   - `.claude/skills/rbtv-*/` — thin loaders for skills
   - `.claude/commands/rbtv-*.md` — slash commands
   - `.claude/rules/rbtv-*.md` — rule content (copied — includes `rbtv-output-resolution` which governs how components resolve output paths at runtime)
   - `rbtv.json` — your install config

### Optional dependencies (per module)

**npm:**

| Dependency | Install | Required by |
|---|---|---|
| `playwright-cli` | `npx playwright install` | browser-automation, design-extraction, playwright-cli skill |
| `serve` | `npx -y serve` (auto) | browser-automation (local server for file:// bypass) |
| `md-to-pdf` | `npm install -g md-to-pdf` | doc-export (PDF output) |
| `defuddle` | `npm install -g defuddle` | web-search, web-searching skill |

**Python:**

| Dependency | Install | Required by |
|---|---|---|
| `python-docx` | `pip install python-docx` | doc-export (DOCX output) |
| `pyyaml` | `pip install pyyaml` | doc-export (DOCX output) |

**System:**

| Dependency | Required by |
|---|---|
| `git` | commit workflow |

**Runtime CDN (no install — loaded at render time):**

| Resource | Required by |
|---|---|
| Google Fonts (Inter), Font Awesome 6, Material Icons | studio HTML output (decks/sites/apps, hypresent) |
| Twitter/YouTube/noembed oEmbed APIs | web-search (embed previews) |

## Plugins

RBTV uses Claude Code plugins for extended functionality. Install them from inside a Claude Code session using `/plugin` commands.

**Always on** — complement RBTV well:

| Plugin | What it provides |
|---|---|
| `superpowers` | Skill-driven workflows, TDD, brainstorming, plan execution, code review |
| `compound-engineering` | Frontend design, git workflows, debugging, ideation, browser automation |
| `chrome-devtools-mcp` | Live browser control via Chrome DevTools Protocol — screenshots, clicks, network inspection, performance profiling, memory analysis |

```
/plugin install superpowers@claude-plugins-official
```

```
/plugin marketplace add EveryInc/compound-engineering-plugin
/plugin install compound-engineering@compound-engineering-plugin
```

```
/plugin marketplace add ChromeDevTools/chrome-devtools-mcp
/plugin install chrome-devtools@chrome-devtools-mcp
```

**Activate on demand** — useful but add skill noise when always enabled:

| Plugin | What it enhances |
|---|---|
| `bmad-pro-skills` | Advanced elicitation, brainstorming, adversarial review |
| `bmad-method-lifecycle` | Full product lifecycle: PRDs, sprints, architecture, research |
| `codex` | Codex CLI integration for second-opinion investigation and review |

```
/plugin marketplace add https://github.com/bmad-code-org/BMAD-METHOD.git
/plugin install bmad-pro-skills@bmad-method
/plugin install bmad-method-lifecycle@bmad-method
```

## Updating RBTV

RBTV content (agents, workflows, tasks) stays in this repo — thin loaders in your workspace reference it by path. To get new content:

```bash
cd /path/to/your/workspace/rbtv
git pull
```

Content changes appear live. You only need to re-run `install.py` when:
- Adding or removing modules
- RBTV's own module manifest or loader templates change

## Source of truth

Installed files in `.claude/skills/rbtv-*`, `.claude/commands/rbtv-*.md`, `.claude/rules/rbtv-*.md`, `.claude/agents/rbtv-*.md` are regenerated on every `install.py` run. **Do not edit them in your workspace** — edit the source in this repo and re-install. This section is the canonical statement of that principle for installs without the **builder** module; workspaces that install builder also get the always-on `rbtv-source-of-truth` rule enforcing it (recovered from retirement — see [modules/builder.md](./modules/builder.md)).

## Retired components

Some components ship in this repo but are flagged `stale` in the module manifest — the installer neither installs nor offers them (it skips any manifest entry with `"stale": true` and hides it from the component picker). Source files remain for reference and history. To revive one, remove its `stale` flag and re-run `install.py`.

| Component | Module | Why retired |
|---|---|---|
| `audio-aware` (rule) | core | Niche transcription-glossary loader; superseded by per-skill glossary loading in the meeting/therapy summarizers. |
| `bash-patterns` (rule) | core | Obsolete under Claude auto-mode — the single-command / no-shell-operator constraint is no longer needed. |
| `context-preservation` (rule) | core | Did not reliably trigger; superseded by the session-close and compounding flows. |
| `coding-discipline` (skill) | coding | **Deleted, not just flagged.** Its four guardrails were generalized into the always-on `reasoning` rule's *Execution Discipline* section (core) — they apply to all artifact work, not only code. |
| `operator` (command + workflow) | office (then `productivity`) | **Deleted, not just flagged.** Shallow overlap with `domcobb` — its Structure move already delegated to [PS]/[PL]. Salvage: traction questions and one-question-at-a-time pacing moved into PS Lite (`step-01-converse`) and the [PS] question bank (`step-02-discover`). |
| `build-for-agent-testability` (rule) | coding | **Deleted, not just flagged — merged, not dropped.** Its entire content (Contract-time drivability check, the three seam patterns, both anti-pattern sets) was folded into `rbtv-done-gate`, which the build-time check always fired alongside; the two formally-coupled rules became one. No protection lost. |

> `source-of-truth` (rule) was previously in this table — it was **recovered** into the builder module, where edit-source-not-installed-copies discipline is load-bearing for component work.

## Architecture notes

- **Module-first source layout:** every component lives under its owning module folder (`{module}/{type}/{name}`, e.g. `office/skills/doc-export/SKILL.md`). `admin/install/module-manifest.json` declares what each module installs; `modules/{module}.md` documents it.
- **Thin loaders:** installed loaders are short files that point back to this repo via a vault-relative path (e.g., `rbtv/`). No content is duplicated into your workspace.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Subagent exception:** subagent files (`.claude/agents/rbtv-*.md`) are copied as content too — they're dispatched in fresh context via the Task tool, so they must be self-contained.
- **Overwrite scope:** re-install tracks the previous install's file list in `rbtv.json` (`installed_files`) and removes only those paths. Your workspace content (notes, projects, other skills, Fernando-authored local components) is never touched.

## Extending RBTV

Use `/rbtv-create-component`. When you create a new component, the agent will ask whether to publish it to the RBTV source (requires re-install to propagate) or write it locally to your workspace only.

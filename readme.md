# RBTV

Short for Robotville, RBTV is a toolkit for Claude Code, Codex, and OpenCode workspaces.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules. A module is a bundle of components; a component groups related content; a skill or rule is an exposed part of a component. A harness is an AI coding tool that receives installed files. Installed skills and commands appear in the selected harnesses.

## Modules

Each module is documented in detail in [`modules/`](modules). The doc covers the module's purpose, every component it ships, and how to use them. The repo is module-first: each module's components live under its own root folder (`core/`, `office/`, `studio/`, …) organized by type (`skills/`, `commands/`, `rules/`, `personas/`, `tasks/`, `workflows/`).

| Module | What it does | Doc |
|---|---|---|
| **core** (always installed) | Powering up AI use — guided git commits, web research, safe file/folder moves with automatic reference-fixing (`rbtv-safe-move`), session close, and the always-on behavioral rules | [modules/core.md](modules/core.md) |
| **office** | Daily knowledge work — narrative and audience strategy (`storytelling/`: narrative-lock, visual-strategist, research briefs), visual-system extraction, image generation, design-system creation, and style checking (`design/`: design-tokens, subtle-refs, vision-to-json, screenshot-capture, generate-image, design-system, visual-check), and deliverable production (`document/`: HTML standards library, html-review, deck production, document conversion, email voice, meeting-prep and presentation workflows); meeting summarization is referenced via `office/meeting-summarizer`, not owned here (formerly `productivity`; the structured-thinking persona was retired — it lives on as the `brainstorm` function, Dom Cobb, in the mirror-format `meta/functions` component) | [modules/office.md](modules/office.md) |
| **studio** | Design and communication module — the studio loop entry (`/rbtv-strategist` — opens the Strategist for message-lock, then hands off to design); the four-beat studio loop (message-lock · art-direction · generate · human-gate) covering deck, site, and app artifacts — every authored deck is role-token-conformant (library-ready + theme-switchable, no manual tokenization; convention-spec § 10.6); artifact forks for sites (`forks/site.md` — structure beat + responsive multi-page HTML contract) and apps (`forks/app.md` — goals/user-flow/UX discovery beats + plain-HTML designed-screens contract + coding-agent handoff package); the Strategist persona (four audience modes: investor · client · site-marketing · app-product); Vivian the Designer (`rbtv-designing`); the `rbtv-hypresent-comments` skill (a thin router over two self-contained procedures — respond to existing hypresent comments without deleting them — reconciling the pass and weighing each change against the whole deck (propagate entailed facts, surface the rest as new comments), reply inline and never resolve the human's thread; or author a new comment from scratch via `hypresent.py add-comment`, which drives the real runtime headlessly to anchor and save the comment — the agent passes only a CSS selector + text, never reading runtime code or hand-editing the comment island); standards bundle (ban-list + flaw-checklist + UX companion-docs contract); v1.1 comparative taxonomy-driven critic (never gates — improver + stopping rule, optional loop wiring via `critic: on`); design-state schema; reference-set scaffold; design-token extraction from live sites; reference-image forensics into regeneration prompts (`/rbtv-vision-to-json`); browser automation; AI image generation; exemplar-screenshot capture; motion/interaction reference extraction; the hypresent presentation engine; the slide-library engine (manifest with optional `status` column; multi-theme + role-token contract v2.0 support — per-theme contracts plus a generic no-literal-skin lint, engine v1.2); and in-app deck→library export (slide selection → `<section>`-only fragments + `status: to-review` rows) | [modules/studio.md](modules/studio.md) |
| **orchestration** | Long-horizon work — general multi-agent orchestration (route tasks to the right worker, dispatch self-contained artifacts, verify every return against disk, recover from halts; single front door incl. CLI-model dispatch via `cast`), the cast catalog + `cast route` selector (task profile → route/self_execute/halt_seam; algorithm authority is the routing card), a deterministic context-window monitor (a `PostToolUse` hook wired in when orchestration is elected) that emits tiered refresh advisories during a run, structured planning, plan execution via tiered sub-agents, and long-source mining | [modules/orchestration.md](modules/orchestration.md) |
| **builder** | Building RBTV itself — component creation (with a build-time efficiency gate), component token- and cognitive-load review, and the source-of-truth rule | [modules/builder.md](modules/builder.md) |
| **writing** | Long-form writing via the writer persona, tone extraction | [modules/writing.md](modules/writing.md) |
| **coding** | The done-gate rule — done on coding tasks requires an owner-confirmed outcome contract, real-input exercise of each criterion, and weight-graded evidence (a disk sheet for substantial work, inline proof in the done message for trivial tasks); the done gate also carries a Contract-time drivability check (merged in from the former build-for-agent-testability rule) so surfaces the agent can't drive (native dialogs, isolated-run config, fused output) get a test seam built into the feature (plain-language code communication moved to the new **communication** module; git commits moved to core; the coding-discipline guardrails were generalized into the always-on reasoning rule — see [Retired components](#retired-components)). The done gate is split into a thin always-on trigger rule (≈420 words) plus an on-fire protocol body (≈2,200 words) loaded via a skill loader only when a coding task starts; a workspace that does no coding omits this module at install (see [modules/coding.md](modules/coding.md) § Scoping) | [modules/coding.md](modules/coding.md) |
| **communication** | Audience-adapted communication, electable independent of coding — a general plain-language rule (define terms, no jargon, no analogies, no bare name-drops, explain plan phases) plus the non-technical-user code-communication overlay (translate code identifiers, frame decisions as behavior changes, no raw output dumps). Both MECE with core's chat-discipline | [modules/communication.md](modules/communication.md) |
| **caveman** | Optional ultra-compressed caveman communication mode (the linguistic transform; behavioral bans deferred to chat-discipline). Parody commit voice ships but is off by default — token savings and fun, based on JuliusBrussee/caveman | [modules/caveman.md](modules/caveman.md) |
| **ignite** | Ignite 0.2 is `core/ignite/`: runnable Node code — a Slack message or a scheduled wake runs one primary-agent turn, deployed by `core/ignite/capabilities/tools/ignite-agent/deploy.sh` and unit `rbtv-ignite-agents.service`, state in the workspace `.rbtv/agents/`, reached through `ignite-agent` and the `create-primary-agent` skill. | [ignite/ignite.json](ignite/ignite.json) |

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+
- Claude Code plugins (see [Plugins](#plugins) for install instructions)

## Install

For a first run, point the installer at an existing workspace directory. `status` shows which directory it selected and which harnesses are configured. `list` opens the exact module, component, or item hierarchy; `search` finds names and descriptions broadly; `show` explains one choice; `add` installs its stable name; `remove` takes that same name.

```bash
rbtv install status --target /path/to/workspace
rbtv install list brainstorm --target /path/to/workspace
rbtv install show brainstorm --target /path/to/workspace
rbtv install add brainstorm --target /path/to/workspace --harness claude,codex --guidance CLAUDE.md
rbtv install status --target /path/to/workspace
rbtv install remove brainstorm --target /path/to/workspace
```

On a fresh workspace, run `configure --harness NAMES --guidance NAME` or supply both settings on the first `add`. A short name selects one exposed item such as a skill or rule when unique; a full `module/component` name selects a component. `list NAME` opens that exact scope, while `search WORDS` looks across names and descriptions. For another agent, set `--target` to its home directory on each command. Use `--dry-run` to preview a change and `--json` for a machine-readable result. Bare `rbtv install` prints help; `rbtv install interactive` starts the guided flow.

> **The installer is `core/installer/capabilities/tools/install/install.py`, reachable as `rbtv install`.**
> It carried the name `install2.py` from its first commit until 2026-08-23, while a
> PREDECESSOR installer held the plain name at the repo root. On that date it was split
> into one module per responsibility under `core/installer/lib/` (checks under
> `core/installer/selftest/`, decisions in `core/installer/capabilities/design-decisions.md`) and took
> the plain name; the predecessor — repo-root `install.py` plus its `admin/install/`
> package, which installed flat module components into `.claude/` and kept state in
> `rbtv.json` — was DELETED on 2026-08-24. Its content lives in git history, and the
> `rbtv.json` it wrote in a workspace is not read by anything any more.
>
> The installer manages **components**: a `<module>/<component>/` folder holding its own
> `<component>.json`, inside a `<module>/` folder holding its own `<module>.json`, on BOTH the
> workspace mirror (`{target}/.rbtv/mirror`) and this repo. It finds a component's units by the
> folder each sits in (`skills/`, `rules/`, `commands/`, `agents/`, `hooks/`, `mcp-servers/`,
> `capabilities/tools/<tool>/`, `folder-instructions/`), checks each file's frontmatter or record
> against the schemas in `core/build/capabilities/templates/`, and realizes the units for
> **three harnesses** (claude, codex, opencode). A component's folder instructions become a
> marked section of the target folder's instructions file. The one unit shaped as a folder is a
> whole skill in the workspace mirror, `{target}/.rbtv/mirror/_skills/<name>/`: it is **copied
> verbatim** into each installed harness's skills directory rather than thin-loaded, and its
> copied `SKILL.md` carries the `rbtv-managed` ownership marker (files written by the earlier
> installer carry `rbtv2-managed` and are still recognised).
> Other generated artifacts are named after their bare unit name and marked as installer-owned.
> Installation state lives at
> `{target}/.rbtv/config/install.json`, recording every file and every shared-config key it
> wrote; `rbtv install remove` releases exactly those claims. It exposes at the
> INSTALL ROOT only and never writes under `.rbtv/goals/`.
>
> It is reachable as **`rbtv install`** — the system CLI routes that namespace straight to it,
> and the commands below are the same tool either way:
>
> ```bash
> rbtv install --target W status                                # target and saved settings
> rbtv install --target W list meta/plan                    # exact component scope
> rbtv install --target W search planning                      # broad discovery
> rbtv install --target W show meta/plan                    # component detail
> rbtv install --target W configure --harness claude,codex --guidance CLAUDE.md
> rbtv install --target W add meta/plan                     # select the component
> rbtv install --target W add --module office                   # a whole module
> rbtv install --target W remove meta/plan                  # one component
> rbtv install --target W remove web/browse web/capture         # several components
> rbtv install --target W configure --harness claude,codex      # replace receiving tools
> rbtv install --target W configure --guidance CLAUDE.md        # replace maintained guidance
> rbtv install --target W add guidance exclude vendor           # skip a guidance folder
> rbtv install --target W update all                             # regenerate locally
> rbtv install interactive                                       # guided flow
> rbtv install selftest                                          # its runnable check
> ```
>
> **The two workspace settings are explicit.** `--harness` chooses which AI coding tools receive
> files, and `--guidance` chooses the root instruction file you maintain. On a fresh target, set
> both with `configure` or on the first `add`. A later `configure` replaces only the settings
> supplied; `status` displays them. `--type` filters item types; `--exclude-type` excludes them.
> Numeric catalog positions are not identifiers. The setting rationale and current command names
> are recorded in `core/installer/capabilities/design-decisions.md`.
>
> `configure`, `add`, `remove`, and `update` accept `--dry-run`. The read and change commands
> accept `--json`; `interactive` and `selftest` accept neither flag. Exit codes are `0` success / `1` refusal /
> `2` usage. Its design decisions (tree precedence, the new-standard scope, the ownership marker, the collision
> rule, the workspace settings) are documented in `core/installer/capabilities/design-decisions.md` —
> that is their one home.
>
> A third installer, `core/capabilities/installer/tool/rbtv-install`, was **deleted on
> 2026-08-22**. It had been built for a KG-shape component layout requiring `<module>/module.md`
> and `prompts/cognitive-units/` pools, neither of which ever materialized on the live trees, so
> nothing ran it. Its content lives in git history.

1. Clone RBTV as a subfolder of your workspace:

   ```bash
   cd /path/to/your/workspace
   git clone <rbtv-repo-url> rbtv
   ```

   RBTV must live INSIDE the workspace that will use it.

2. Run the installer:

   ```bash
   rbtv install status          # or: python rbtv/core/installer/capabilities/tools/install/install.py status
   ```

   For a guided flow, run `rbtv install interactive`: choose the workspace, tick the
   components with the arrow keys (space toggles, `i` shows what a component
   installs, `a` ticks everything), tick which AI tools get files written for
   them, choose which root guidance file you author, then confirm. Piped or
   scripted, every question falls back to a numbered list. The scripted verbs
   are in the callout at the top of this section.

3. After install, your workspace has:
   - `.claude/skills/<name>/SKILL.md` — thin loaders for skills
   - `.claude/commands/<name>.md` — slash commands
   - `.claude/rules/<name>.md` — rules
   - `.claude/agents/<name>.md` — sub-agents
   - `.rbtv/config/install.json` — the book: every file and every shared-config
     key the installer wrote, and the only thing an uninstall removes

   Names are the bare part id; ownership is a `rbtv2-managed` marker inside each
   file, never a prefix on its name.

   Output paths are resolved at runtime by the `rbtv-output-resolution` rule, which uses conversation context and workspace CLAUDE.md conventions to propose paths.

### Optional dependencies (per module)

**npm:**

| Dependency | Install | Required by |
|---|---|---|
| `playwright-cli` | `npx playwright install` | browser-automation, design-extraction, playwright-cli skill |
| `serve` | `npx -y serve` (auto) | browser-automation (local server for file:// bypass) |
| `md-to-pdf` | `npm install -g md-to-pdf` | doc-export (PDF output) |
| `defuddle` | `npm install -g defuddle` | web-search, web-searching skill |
| `ast-grep` | bundled via `npx @ast-grep/cli` (no global install) | core, safe-move skill (code-reference matching; degrades gracefully when absent) |

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

Content changes behind thin loaders appear live. Run `rbtv install update scaffolding` when an
unit file, loader, or generated instruction section changes. This
refreshes generated sections in every configured instruction file, including counterpart files,
while preserving human text outside them. Use `rbtv install update guidance` when maintained
human instructions change; it copies that text to configured counterparts while preserving
their generated sections. `rbtv install update all` does both from local source. Use `add` or
`remove` when you want to change the selected items.

## Source of truth

Installed files under `.claude/skills/`, `.claude/commands/`, `.claude/rules/` and `.claude/agents/` that carry the `rbtv-managed` marker (or the earlier `rbtv2-managed`) are regenerated on every `rbtv install` run. **Do not edit them in your workspace** — edit the source in this repo and re-install. This section is the canonical statement of that principle for installs without the **builder** module; workspaces that install builder also get the always-on `rbtv-source-of-truth` rule enforcing it (recovered from retirement — see [modules/builder.md](modules/builder.md)).

## Retired components

The table below records retired components from earlier layouts. The current installer discovers
installable content from each component's folders, not from a central manifest.

| Component | Module | Why retired |
|---|---|---|
| `audio-aware` (rule) | core | Niche transcription-glossary loader; superseded by per-skill glossary loading in the meeting/therapy summarizers. |
| `bash-patterns` (rule) | core | Obsolete under Claude auto-mode — the single-command / no-shell-operator constraint is no longer needed. |
| `context-preservation` (rule) | core | Did not reliably trigger; superseded by the session-close and compounding flows. |
| `coding-discipline` (skill) | coding | **Deleted, not just flagged.** Its four guardrails were generalized into the always-on `reasoning` rule's *Execution Discipline* section (core) — they apply to all artifact work, not only code. |
| `operator` (command + workflow) | office (then `productivity`) | **Deleted, not just flagged.** Shallow overlap with `domcobb` — its Structure move already delegated to [PS]/[PL]. Salvage: traction questions and one-question-at-a-time pacing moved into PS Lite (`step-01-converse`) and the [PS] question bank (`step-02-discover`). |
| `domcobb` (persona + command) + its six workflows — `problem-structuring` (incl. PS Lite), `idea-sparring`, `pre-mortem`, `first-principles`, `six-thinking-hats` | office | **Deleted, not just flagged** (owner ruling 2026-08-21). Rebuilt as the `brainstorm` function (Dom Cobb) in the mirror-format `meta/functions` component — every menu mode ([PS]/[PL]/[IS]/[PM]/[FP]/[6H]) lives on there. |
| `build-for-agent-testability` (rule) | coding | **Deleted, not just flagged — merged, not dropped.** Its entire content (Contract-time drivability check, the three seam patterns, both anti-pattern sets) was folded into `rbtv-done-gate`, which the build-time check always fired alongside; the two formally-coupled rules became one. No protection lost. |
| `qwen-code-cli` (model package) | orchestration | **Deleted, not just flagged** (owner ruling 2026-07-09). Its deepseek code-executor backends moved to the `opencode` package (`deepseek-flash`/`deepseek-pro`, code roles only — `deepseek-api` keeps the text roles); `qwen3.6-plus` and `glm-5.1` lost their routable rows (both remain reachable through opencode provider config; the opencode z.ai backend pins glm-5.2, the 1M-context successor). The mirror driver keeps the `qwen-md` owner tag recognized so a prior install's recorded `QWEN.md` still tears down (rendering of any guidance file is retired — see `d-hard-guard-retire-model-mirror`). |

> `source-of-truth` (rule) was previously in this table — it was **recovered** into the builder module, where edit-source-not-installed-copies discipline is load-bearing for component work.

## Architecture notes

- **Component source layout:** a component lives at `<module>/<component>/` with its `<component>.json` and one folder per kind of unit it exposes. The owning `<module>/<module>.json` describes the module.
- **Thin loaders:** installed skill and command loaders point back to this repo by resolved source path. Their installed copies are generated.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Subagent exception:** installed subagent files are copied as content too — they are dispatched in fresh context and must be self-contained.
- **Overwrite scope:** the installer records owned files and shared settings in `.rbtv/config/install.json`; removal releases those claims while preserving unowned workspace content.

## Extending RBTV

`/rbtv-create-component` was retired. Component structure and naming are defined by `core/build/capabilities/`. Place a new component in
its owning module; update its `<component>.json`, `<module>/<module>.json`, and relevant README
guidance in the same change.

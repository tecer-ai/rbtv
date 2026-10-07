# RBTV

Short for Robotville, RBTV is a toolkit for Claude Code, Codex, and OpenCode installations.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules. A module is a bundle of components; a component groups related content; a skill or rule is an exposed part of a component. A harness is an AI coding tool that receives installed files. Installed skills and commands appear in the selected harnesses.

## Modules

Browse the source catalog with `rbtv list`, then inspect one module, component, file, or pack with `rbtv show NAME`.

| Module | Description |
|---|---|
| `core` | rbtv's own operation, configuration, and editing, and the software that manages what an agent is exposed to, runs, launches, and connects agents on any harness. |
| `innovate` | The innovate module — taking a business idea from conception through validation to a brand book, and the individual innovation frameworks that do that work. |
| `meta` | How agents behave, communicate, plan, and coordinate work across tasks. |
| `office` | The office module — daily knowledge work: narrative and visual strategy, design extraction and style checking, and document/deck/email production. |
| `web` | The web module — the system's components for reaching the open web: fetching a page, driving a browser, and whatever later joins them. |

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+
- Claude Code plugins (see [Plugins](#plugins) for install instructions)

## Install

For a first run, point rbtv at an existing installation directory. `status` shows which directory it selected and which harnesses are configured. `list` opens the exact module, component, or file hierarchy; `search` finds names and descriptions broadly; `show` explains one choice; `add` installs its stable name; `remove` takes that same name.

```bash
rbtv status --target /path/to/installation
rbtv list brainstorm --target /path/to/installation
rbtv show brainstorm --target /path/to/installation
rbtv add brainstorm --target /path/to/installation --harness claude,codex --guidance none
rbtv status --target /path/to/installation
rbtv remove brainstorm --target /path/to/installation
```

On a fresh installation, run `configure --harness NAMES --guidance NAME` or supply both settings on the first `add`. A named guidance file must already exist at the installation root; use `none` when no such file is maintained. A short name selects one exposed file such as a skill or rule when unique; a full `module/component` name selects a component. `list NAME` opens that exact scope, while `search WORDS` looks across names and descriptions. For another agent, set `--target` to its home directory on each command. Use `--dry-run` to preview a change and `--json` for a machine-readable result. Bare `rbtv` prints help; `rbtv interactive` starts the guided flow.

Change results show a compact summary and important warnings by default. Add `--details` to include the complete grouped lists of selected and generated files; combine it with `--dry-run` to inspect a plan before applying it. `--json` retains the full structured result regardless of text verbosity. A file-operation failure reports `changed: null` when earlier writes may have applied; inspect the target before retrying.

Agent results also include `harness_files` (file outcomes from installing or removing the agent's skills and rules) and `files_removed` (their full identifiers). These supplement the existing agent fields. An agent-removal preview's `kept` list predicts what remains after removal.

The `cli-creator` skill in `meta/code` covers both help and actual command results. Its output review checks tables, spacing, wrapping, bulk-result summaries, structured output, and real outcomes against observed state; help coverage alone is insufficient.

The `work-history` skill in `meta/functions` reconstructs a user-agreed project, plan, or session history. It preserves visible transcripts, intermediate and final outputs, and saved working notes in one folder per agent/session, with a linked root timeline, provenance manifest, and explicit recovery gaps. It researches historical evidence; `handoff` transfers current session knowledge for continuation. Install it with `rbtv add work-history` in a configured installation.

> **rbtv is `core/rbtv/capabilities/tools/rbtv/install.py`, run as `rbtv`.**
>
> rbtv manages **components**: a `<module>/<component>/` folder holding its own
> `<component>.json`, inside a `<module>/` folder holding its own `<module>.json`, on BOTH the
> installation mirror (`{target}/.rbtv/mirror`) and this repo. It finds a component's files by the
> folder each sits in (`skills/`, `rules/`, `commands/`, `agents/<name>/`, `sub-agents/`, `hooks/`, `mcp-servers/`,
> `capabilities/tools/<tool>/`, `folder-instructions/`), checks each file's frontmatter or record
> against the schemas in `core/rbtv/capabilities/templates/`, and realizes the files for
> **three harnesses** (claude, codex, opencode). A component's folder instructions become a
> marked section of the target folder's instructions file. The one file shaped as a folder is a
> whole skill in the installation mirror, `{target}/.rbtv/mirror/_skills/<name>/`: it is exposed
> as a copy of the whole folder in each installed harness's skills directory, and the copied `SKILL.md`
> carries the `rbtv-managed` ownership marker (files written by an earlier
> rbtv carry `rbtv2-managed` and are still recognised).
> Other generated artifacts are named after their bare file name and marked as rbtv-owned.
> Installation state lives at
> `{target}/.rbtv/config/install.json`, recording every file and every shared-config key it
> wrote; `rbtv remove` releases exactly those claims. It exposes at the
> INSTALL ROOT only and never writes under `.rbtv/goals/`.
>
> It is reachable as **`rbtv`** — the system CLI routes that name straight to it,
> and the commands below are the same tool either way:
>
> ```bash
> rbtv status --target W                                # target and saved settings
> rbtv list meta/plan --target W                    # exact component scope
> rbtv search planning --target W                      # broad discovery
> rbtv show meta/plan --target W                    # component detail
> rbtv configure --harness claude,codex --guidance none --target W
> rbtv add meta/plan --target W                     # select the component
> rbtv add --module office --target W                   # a whole module
> rbtv remove meta/plan --target W                  # one component
> rbtv remove web/browse web/capture --target W         # several components
> rbtv configure --harness claude,codex --target W      # replace receiving tools
> rbtv configure --guidance CLAUDE.md --target W        # replace maintained guidance
> rbtv add guidance exclude vendor --target W           # skip a guidance folder
> rbtv update all --target W                             # regenerate locally
> rbtv interactive                                       # guided flow
> rbtv selftest                                          # its runnable check
> ```
>
> **The two installation settings are explicit.** `--harness` chooses which AI coding tools receive
> files, and `--guidance` chooses the root instruction file you maintain. On a fresh target, set
> both with `configure` or on the first `add`. A named guidance file must already exist at the
> installation root; choose `none` when no such file is maintained. A later `configure` replaces only the settings
> supplied; `status` displays them. `--type` filters file types; `--exclude-type` excludes them.
> `list`, `search` and `show` also accept the types `pack`, `module` and `component`.
> Numeric source catalog positions are not identifiers. The setting rationale and current command names
> are recorded in `core/rbtv/capabilities/tools/rbtv/documentation/design-decisions.md`.
>
> `configure`, `add`, `remove`, and `update` accept `--dry-run`. The read and change commands
> accept `--json`; `interactive` and `selftest` accept neither flag. Exit codes are `0` success / `1` refusal /
> `2` usage. Its design decisions (tree precedence, the new-standard scope, the ownership marker, the collision
> rule, the installation settings) are documented in `core/rbtv/capabilities/tools/rbtv/documentation/design-decisions.md` —
> that is their one home.
>

1. Clone rbtv where you will keep its source available:

   ```bash
   git clone <rbtv-repo-url> /path/to/rbtv
   ```

   rbtv may live anywhere on the machine. The generated files name its files by full path, so every agent that uses the installation must be able to read that folder; keeping rbtv inside the installation guarantees it.

2. Run rbtv:

   ```bash
   rbtv status          # or: python rbtv/core/rbtv/capabilities/tools/rbtv/install.py status
   ```

   For a guided flow, run `rbtv interactive`: choose the installation, tick the
   components with the arrow keys (space toggles, `i` shows what a component
   installs, `a` ticks everything), tick which AI tools get files written for
   them, choose which root guidance file you author, then confirm. Piped or
   scripted, every question falls back to a numbered list. The scripted verbs
   are in the callout at the top of this section.

3. After install, your installation has:
   - `.claude/skills/<name>/SKILL.md` — copies of skills
   - `.claude/commands/<name>.md` — slash commands
   - `.claude/rules/<name>.md` — rules (OpenCode loads them through the `instructions` list in
     `opencode.json`; Codex gets each one as a skill in `.agents/skills/<name>/`)
   - `.claude/agents/<name>.md` — sub-agents
   - `.rbtv/config/install.json` — the book: every file and every shared-config
     key rbtv wrote, and the only thing an uninstall removes

   Names are the bare part id; ownership is a `rbtv-managed` marker inside each
   file, never a prefix on its name.

   Output paths are resolved at runtime by the `rbtv-output-resolution` rule, which uses conversation context and installation CLAUDE.md conventions to propose paths.

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

RBTV content is authored in this repo; your installation holds generated copies of skills, commands and rules, whose links reference this repo by path. To get new content:

```bash
cd /path/to/rbtv
git pull
```

A page that a copy links to is read from this repo, so its changes appear live. Run
`rbtv update scaffolding`, and `rbtv agent update AGENT scaffolding` for each agent, on each
machine after a skill, command, rule or generated instruction section changes. This
refreshes generated sections in every configured instruction file, including counterpart files,
while preserving human text outside them. Use `rbtv update guidance` when maintained
human instructions change; it copies that text to configured counterparts while preserving
their generated sections. `rbtv update all` does both from local source. It also removes what was
generated for files that `install.json` no longer lists, so `rbtv update scaffolding` and `rbtv update all`
make the folder match that file. Use `add` or `remove` when you want to change the selected files.

When `rbtv` is not found after a pull, its shortcut in `~/.rbtv/bin` points at a path where the
program is not. Start the program by its full path once; each run points the shortcut at the
program's file:

```bash
python3 <repository>/core/rbtv/capabilities/tools/rbtv/install.py update all --target <installation>
# then, from the installation, for each placed agent:
python3 <repository>/core/rbtv/capabilities/tools/rbtv/install.py agent update <agent> all
```

## Source of truth

Installed files under `.claude/skills/`, `.claude/commands/`, `.claude/rules/` and `.claude/agents/` that carry the `rbtv-managed` marker (or the earlier `rbtv2-managed`) are regenerated on every `rbtv update` run. **Do not edit them in your installation** — edit the source in this repo and re-install. This section is the canonical statement of that principle for installs without the builder module; installations that install builder also get the always-on `rbtv-source-of-truth` rule enforcing it.

## Retired components

The table below records retired components from earlier layouts. The current rbtv discovers
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

- **Component source layout:** a component lives at `<module>/<component>/` with its `<component>.json` and one folder per kind of file it exposes. The owning `<module>/<module>.json` describes the module.
- **Copies:** installed skills, commands and rules are generated copies of their source, with each link made the absolute path of its target in this repo. A mirror `_skills/<name>/` folder is copied whole.
- **Sub-agent exception:** an installed harness-native sub-agent file is a pointer to the agent's prompt by resolved source path.
- **Overwrite scope:** rbtv records owned files and shared settings in `.rbtv/config/install.json`; removal releases those claims while preserving unowned installation content.

## Extending RBTV

`/rbtv-create-component` was retired. Component structure and naming are defined by `core/rbtv/capabilities/`. Place a new component in
its owning module; update its `<component>.json`, `<module>/<module>.json`, and relevant README
guidance in the same change.

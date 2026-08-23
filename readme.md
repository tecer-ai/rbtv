# RBTV

Short for Robotville, RBTV is a standalone Claude Code toolkit for business innovation, pitch generation, documentation, and structured thinking.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules designed to be bootstrapped into any Claude Code workspace. After install, RBTV appears as `/rbtv-<command>` slash commands (e.g., `/rbtv-strategist`, `/rbtv-doc-export`, `/rbtv-plan-doc`) and auto-triggered skills in your workspace.

## Modules

Each module is documented in detail in [`modules/`](./modules/). The doc covers the module's purpose, every component it ships, and how to use them. The repo is module-first: each module's components live under its own root folder (`core/`, `office/`, `studio/`, …) organized by type (`skills/`, `commands/`, `rules/`, `personas/`, `tasks/`, `workflows/`).

| Module | What it does | Doc |
|---|---|---|
| **core** (always installed) | Powering up AI use — guided git commits, web research, safe file/folder moves with automatic reference-fixing (`rbtv-safe-move`), session close, and the always-on behavioral rules | [modules/core.md](./modules/core.md) |
| **office** | Daily knowledge work — document export (PDF/DOCX with brand discovery), legal advisory, meeting prep, meeting summarization, and client emails (formerly `productivity`; the structured-thinking persona was retired — it lives on as the `brainstorm` function, Dom Cobb, in the mirror-format `core/functions` component) | [modules/office.md](./modules/office.md) |
| **studio** | Design and communication module — the studio loop entry (`/rbtv-strategist` — opens the Strategist for message-lock, then hands off to design); the four-beat studio loop (message-lock · art-direction · generate · human-gate) covering deck, site, and app artifacts — every authored deck is role-token-conformant (library-ready + theme-switchable, no manual tokenization; convention-spec § 10.6); artifact forks for sites (`forks/site.md` — structure beat + responsive multi-page HTML contract) and apps (`forks/app.md` — goals/user-flow/UX discovery beats + plain-HTML designed-screens contract + coding-agent handoff package); the Strategist persona (four audience modes: investor · client · site-marketing · app-product); Vivian the Designer (`rbtv-designing`); the `rbtv-hypresent-comments` skill (a thin router over two self-contained procedures — respond to existing hypresent comments without deleting them — reconciling the pass and weighing each change against the whole deck (propagate entailed facts, surface the rest as new comments), reply inline and never resolve the human's thread; or author a new comment from scratch via `hypresent.py add-comment`, which drives the real runtime headlessly to anchor and save the comment — the agent passes only a CSS selector + text, never reading runtime code or hand-editing the comment island); standards bundle (ban-list + flaw-checklist + UX companion-docs contract); v1.1 comparative taxonomy-driven critic (never gates — improver + stopping rule, optional loop wiring via `critic: on`); design-state schema; reference-set scaffold; design-token extraction from live sites; reference-image forensics into regeneration prompts (`/rbtv-vision-to-json`); browser automation; AI image generation; exemplar-screenshot capture; motion/interaction reference extraction; the hypresent presentation engine; the slide-library engine (manifest with optional `status` column; multi-theme + role-token contract v2.0 support — per-theme contracts plus a generic no-literal-skin lint, engine v1.2); and in-app deck→library export (slide selection → `<section>`-only fragments + `status: to-review` rows) | [modules/studio.md](./modules/studio.md) |
| **orchestration** | Long-horizon work — general multi-agent orchestration (route tasks to the right worker, dispatch self-contained artifacts, verify every return against disk, recover from halts; single front door incl. CLI-model dispatch via `cast`), the cast catalog + `cast route` selector (task profile → route/self_execute/halt_seam; algorithm authority is the routing card), a deterministic context-window monitor (a `PostToolUse` hook wired in when orchestration is elected) that emits tiered refresh advisories during a run, structured planning, plan execution via tiered sub-agents, and long-source mining | [modules/orchestration.md](./modules/orchestration.md) |
| **builder** | Building RBTV itself — component creation (with a build-time efficiency gate), component token- and cognitive-load review, and the source-of-truth rule | [modules/builder.md](./modules/builder.md) |
| **writing** | Long-form writing via the writer persona, tone extraction | [modules/writing.md](./modules/writing.md) |
| **coding** | The done-gate rule — done on coding tasks requires an owner-confirmed outcome contract, real-input exercise of each criterion, and weight-graded evidence (a disk sheet for substantial work, inline proof in the done message for trivial tasks); the done gate also carries a Contract-time drivability check (merged in from the former build-for-agent-testability rule) so surfaces the agent can't drive (native dialogs, isolated-run config, fused output) get a test seam built into the feature (plain-language code communication moved to the new **communication** module; git commits moved to core; the coding-discipline guardrails were generalized into the always-on reasoning rule — see [Retired components](#retired-components)). The done gate is split into a thin always-on trigger rule (≈420 words) plus an on-fire protocol body (≈2,200 words) loaded via a skill loader only when a coding task starts; a workspace that does no coding omits this module at install (see [modules/coding.md](./modules/coding.md) § Scoping) | [modules/coding.md](./modules/coding.md) |
| **communication** | Audience-adapted communication, electable independent of coding — a general plain-language rule (define terms, no jargon, no analogies, no bare name-drops, explain plan phases) plus the non-technical-user code-communication overlay (translate code identifiers, frame decisions as behavior changes, no raw output dumps). Both MECE with core's chat-discipline | [modules/communication.md](./modules/communication.md) |
| **caveman** | Optional ultra-compressed caveman communication mode (the linguistic transform; behavioral bans deferred to chat-discipline). Parody commit voice ships but is off by default — token savings and fun, based on JuliusBrussee/caveman | [modules/caveman.md](./modules/caveman.md) |
| **ignite** | The runtime layer (currently on the `ignite/core-daemon` branch) — the ignite daemon (runnable Node.js service code, deployed to a runtime host, never installed into `.claude/`) and the **team-kit**: coordinated parallel multi-agent team runs in tmux (`coord.py` coordination CLI with verified seat identities and a typed append-only message log, run protocol, watcher/closer seats, briefing templates), entered via the `rbtv-team-kit` skill | [modules/ignite.md](./modules/ignite.md) |

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+
- Claude Code plugins (see [Plugins](#plugins) for install instructions)

## Install

> **The installer is `meta/installer/install.py`, reachable as `rbtv install`.**
> It carried the name `install2.py` from its first commit until 2026-08-23, while a
> PREDECESSOR installer held the plain name at the repo root. On that date it was split
> into one module per responsibility under `meta/installer/lib/` (checks under
> `meta/installer/selftest/`, decisions in `meta/installer/design-decisions.md`) and took
> the plain name; the predecessor — repo-root `install.py` plus its `admin/install/`
> package, which installed flat module components into `.claude/` and kept state in
> `rbtv.json` — is being retired, and its package is already absent from this tree, so
> the steps under "Clone RBTV" below no longer run as written.
>
> The installer manages **only NEW-STANDARD component folders** — a `<module>/<component>/`
> directory holding an `exposure.csv` (that manifest at depth 2 IS the component; the former
> `component.md` requirement was retired 2026-08-22) — on BOTH the workspace
> mirror (`{target}/.rbtv/mirror`) and this repo, discovering their parts from the
> **exposure manifest** (`exposure.csv`) beside it, and realizes each row's canonical method
> for **three harnesses** (claude, codex, opencode) through CMP-12's adapter matrix. The
> standalone kimi CLI was retired 2026-08-14; its models ride opencode.
> Everything else — module-root manifests, folders with no `exposure.csv` — was the old
> standard, which only the predecessor installer ever managed: the two covered disjoint sets.
> One exception by design: a tree-root **`_skills/`** folder holds whole vendored skill
> folders (`_skills/cli-creator/`), which are not rbtv parts and carry no manifest. Each is
> its own installable unit (`--component _skills/cli-creator`, `--module _skills`) and is
> **copied verbatim** into every installed harness's skills directory rather than thin-loaded
> — installed and uninstalled as a whole folder.
> Its artifacts are named after their bare part id, each carrying the machine-readable
> `rbtv2-managed` marker that says the installer may rewrite it, and its state lives at
> `{target}/.rbtv/config/install.json`, recording every file and every shared-config key it
> wrote — so the two installers can never sweep, overwrite, or delete each other's work, and
> `rbtv install rm` removes exactly what it wrote and nothing else. It exposes at the
> INSTALL ROOT only and never writes under `.rbtv/goals/` (seat folders belong to the
> materializer). It never read or wrote the predecessor's state file.
>
> It is reachable as **`rbtv install`** — the system CLI routes that namespace straight to it,
> and the commands below are the same tool either way:
>
> ```bash
> rbtv install --target /path/to/workspace ls                    # what is installable
> rbtv install --target /path/to/workspace li                    # what is installed + settings
> rbtv install --target W add -c meta/planning \
>       --harness claude,codex --artifact CLAUDE.md              # FIRST add: both required
> rbtv install --target W add -m office                          # later adds: components only
> rbtv install --target W rm -c meta/planning
> rbtv install --target W rm -c web/browse,web/capture         # -m/-c/-x/-nm/-nc/-nx take a comma list
> rbtv install --target W rm -c 3,7,9                          # …or the numbers from the last ls/li
> rbtv install --target W rm -c 2-9,14                         # …N-M is an inclusive range of those numbers
> rbtv install --target W add|rm harness opencode                # change which tools get files
> rbtv install --target W set artifact CLAUDE.md|AGENTS.md|none  # change the guidance basis
> rbtv install --target W add|rm artifact exclude <dir>          # folders the mirror skips
> rbtv install                                                   # interactive
> rbtv install selftest                                          # its runnable check
> ```
>
> **The two workspace settings are answered once.** `--harness` (which AI coding tools get files
> written for them) and `--artifact` (which root guidance file YOU author, the others being
> generated from it) are REQUIRED on the first `add` and REFUSED on every later one, because both
> used to be silent: `--harness` defaulted to every harness and a narrower list on a later run
> merged instead of narrowing, so asking for fewer harnesses succeeded and changed nothing. After
> the first install the ACTION-FIRST settings forms own them — `add|rm harness`, `set artifact`,
> `add|rm artifact exclude` — and `rm harness` really does delete that harness's files. The
> action word always comes first, the same way it does for components, and `set` exists because
> the guidance basis holds ONE value: choosing a new one replaces the old, which is a set and not
> an add. The old noun-led spelling (`harness add`, `artifact set`) is retired, not aliased: it
> refuses with `verb-moved` and names its replacement. The three settings are READ at the head of
> `rbtv install li` (and ride its `--json` under `settings`) — the two verbs that existed only to
> print them are gone from the menu, kept hidden so the old spelling still lands on a sentence
> saying where it went. See `meta/installer/design-decisions.md`, D16, D16b and D16c.
>
> Every verb takes `--dry-run` and `--json`; exit codes are `0` success / `1` refusal /
> `2` usage. Its design decisions (tree precedence, the new-standard scope, the ownership marker, the collision
> rule, the workspace settings) are documented in `meta/installer/design-decisions.md` —
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
   rbtv install                 # or: python rbtv/meta/installer/install.py
   ```

   > The rest of this numbered section documents the PREDECESSOR installer (repo-root
   > `install.py` + `admin/install/`), including its `--mirror` flags. That package is
   > absent from this tree and the commands below do not run as written; the section is
   > kept until the retirement is finished. What runs today is `rbtv install` — its verbs
   > are the callout above.

   The predecessor installer prompted for:
   - Modules to install (core is always included)
   - Orchestration dispatch (when the `orchestration` module is selected): the live roster is the **cast catalog** (`cast route --catalog`; routable set = catalog ∩ availability). Cards and the planner CALL `cast route`; conductor dispatch is plain `cast`; API workers go through `cast api`. There is no install-time model-package election. The retired models-tree router is gone. The installer reconciles the workspace's `.claude/settings.local.json` permission allowlist from the catalog's `permission_rules` (only the catalog-declared strings are touched — hand-added entries survive). Electing the orchestration module also **renders the worker mirror** in the target workspace (shared `.agents/` library and per-model config dirs) via the mirror driver at `ignite/team-kit/mirror/driver/` (team-kit owns the one implementation; decision 5 of the 2026-08-18 models-tree-retirement build). **Guidance files (`AGENTS.md`/`QWEN.md`) are NOT rendered** — that leg is RETIRED (owner ruling `d-hard-guard-retire-model-mirror`, 2026-08-10): no flag or recorded state can make this installer write a guidance file; a render prints a one-line skip. The modern installer (`meta/installer/install.py`) owns guidance files. Mirror state is persisted in a single `model_mirror` block in `rbtv.json`. Use `--mirror` to refresh mirror artifacts only (skips component install; empty package list means every driver-known package). Use `install.py --mirror --check` to ask whether the mirror is current WITHOUT refreshing it: a read-only probe that writes nothing, names every managed file missing or fallen behind its source, and exits 1 on drift / 0 in sync (gating-ready for CI and pre-flight checks) — worth having because mirrors are gitignored and refresh only when the installer runs, so drift is per-machine and invisible to git. `--check` applies only with `--mirror`, and is mutually exclusive with `--uninstall` (exit 2). `--exclude PATH [PATH ...]` is now INERT for rendering (it only ever constrained the guidance walk) but is still recorded in `rbtv.json` (`model_mirror.excluded_paths`) for state compatibility: passing it REPLACES the recorded list, omitting it PRESERVES it. The prune-on-exclude deletion was removed with the guidance retirement — installer-1 no longer deletes a guidance file a render would have orphaned. `ALWAYS_EXCLUDED_PREFIXES` in `driver/state.py` survives for the teardown side only: a goal folder's routers — `CLAUDE.md` AND `AGENTS.md` — are written by the goals-tree scaffold (owner ruling Q18, 2026-08-09), and uninstall consults the constant: a workspace upgraded from a pre-exclusion driver still carries those routers in its recorded managed-file list, so `install.py --mirror --uninstall` (and a deselection teardown) partitions them OUT of its delete set instead of deleting them (`UninstallResult.protected`) — they stay on disk, un-managed, and are reported under a `protected` label beside the deleted/spared counts. Use `install.py --mirror --uninstall` for a full mirror teardown: removes ALL generated mirror artifacts for the target (the shared `.agents/` library, per-model config dirs, and any guidance file still RECORDED from a pre-retirement install — banner-guarded, so a file installer-1 did not write is spared) — except any recorded path under `ALWAYS_EXCLUDED_PREFIXES`, which is protected (left on disk, un-managed) rather than deleted — and clears the `model_mirror` block from `rbtv.json`; `--uninstall` applies only with `--mirror`.

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
| `domcobb` (persona + command) + its six workflows — `problem-structuring` (incl. PS Lite), `idea-sparring`, `pre-mortem`, `first-principles`, `six-thinking-hats` | office | **Deleted, not just flagged** (owner ruling 2026-08-21). Rebuilt as the `brainstorm` function (Dom Cobb) in the mirror-format `core/functions` component — every menu mode ([PS]/[PL]/[IS]/[PM]/[FP]/[6H]) lives on there. |
| `build-for-agent-testability` (rule) | coding | **Deleted, not just flagged — merged, not dropped.** Its entire content (Contract-time drivability check, the three seam patterns, both anti-pattern sets) was folded into `rbtv-done-gate`, which the build-time check always fired alongside; the two formally-coupled rules became one. No protection lost. |
| `qwen-code-cli` (model package) | orchestration | **Deleted, not just flagged** (owner ruling 2026-07-09). Its deepseek code-executor backends moved to the `opencode` package (`deepseek-flash`/`deepseek-pro`, code roles only — `deepseek-api` keeps the text roles); `qwen3.6-plus` and `glm-5.1` lost their routable rows (both remain reachable through opencode provider config; the opencode z.ai backend pins glm-5.2, the 1M-context successor). The mirror driver keeps the `qwen-md` owner tag recognized so a prior install's recorded `QWEN.md` still tears down (rendering of any guidance file is retired — see `d-hard-guard-retire-model-mirror`). |

> `source-of-truth` (rule) was previously in this table — it was **recovered** into the builder module, where edit-source-not-installed-copies discipline is load-bearing for component work.

## Architecture notes

- **Module-first source layout:** every component lives under its owning module folder (`{module}/{type}/{name}`, e.g. `office/skills/doc-export/SKILL.md`). `admin/install/module-manifest.json` declares what each module installs; `modules/{module}.md` documents it.
- **Thin loaders:** installed loaders are short files that point back to this repo via a vault-relative path (e.g., `rbtv/`). No content is duplicated into your workspace.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Subagent exception:** subagent files (`.claude/agents/rbtv-*.md`) are copied as content too — they're dispatched in fresh context via the Task tool, so they must be self-contained.
- **Overwrite scope:** re-install tracks the previous install's file list in `rbtv.json` (`installed_files`) and removes only those paths. Your workspace content (notes, projects, other skills, Fernando-authored local components) is never touched.

## Extending RBTV

`/rbtv-create-component` was RETIRED 2026-08-11 (`builder/RETIRED.md`) and no longer installs. Component structure, naming, and the exposure/seat canon are defined by the meta/planning reference set and the forge workflow — build new components from those. Placement still follows the module-first layout above, and every component change still updates `README.md`, `modules/{module}.md`, and `admin/install/module-manifest.json` in the same change.

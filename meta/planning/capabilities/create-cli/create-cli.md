---
description: Build a composable CLI for AI agents from API docs, an OpenAPI spec, curl examples, an SDK, a web app, an admin tool, or a local script — or review an existing CLI's agent UX. The toolsmith capability D9 binds — a seated tool MUST be a registered CLI with machine-readable output, built via this capability.
# W6 — the CLIs this capability routes to (`exposes:` reference grammar); consumers shop
# it through capability-cards.
exposes-cli:
  - capability-cards
---
# create-cli

Create a real CLI that future agent sessions can run by command name from any working directory.

This is a plain-instruction capability (no bundled tool): its procedure is this file's body plus the three references beside it. This capability is for durable tools, not one-off scripts — if a short script in the current repo solves the task, write the script there instead.

**In rbtv:** a toolsmith task building a seated tool MUST use this capability as its means (core-build `decisions.md#D9`): the product MUST be a registered CLI — cataloged with a first-party `path` row in its owning module's `exposure.csv` (`d-tool-inventory-exposure-rows`), never a bare path-invoked script — and MUST emit at least one machine-readable output (the surface a workflow edge reads to verify the done contract). Consumers shop this capability through `capability-cards`. Its current harness realization is the vault skill `.claude/skills/cli-creator/`.

## Modes

| Mode | Trigger | Entry |
|------|---------|-------|
| **Build** (default) | A new CLI is wanted | Continue below |
| **Review** | Review, critique, audit, or redesign an EXISTING CLI's UX/interface | Read [references/cli-ux-review.md](references/cli-ux-review.md) and follow it exactly; judge against [references/agent-ux-standards.md](references/agent-ux-standards.md). Skip the rest of this file |

## Start

Name the target tool, its source, and the first real jobs it should do:

- Source: API docs, OpenAPI JSON, SDK docs, curl examples, browser app, existing internal script, article, or working shell history.
- Jobs: literal reads/writes such as `list drafts`, `download failed job logs`, `search messages`, `upload media`, `read queue schedule`.
- Install name: a short binary name such as `ci-logs`, `slack-cli`, `sentry-cli`, or `buildkite-logs`.

Never assume a source-code location. When the task has not named a repo or folder, resolve the destination through the workspace's output-path resolution rule when one exists (e.g. `rbtv-output-resolution`: propose a full path with reasoning and wait for confirmation); otherwise ask the owner where the tool's source should live before scaffolding.

Before scaffolding, check whether the proposed command already exists:

```bash
command -v <tool-name> || true
```

If it exists, choose a clearer install name or ask.

## Choose the Runtime

Before choosing, inspect the machine and source material:

```bash
command -v cargo rustc node pnpm npm python3 uv || true
```

Then choose the least surprising toolchain:

- Default to **Rust** for a durable CLI an agent should run from any repo: one fast binary, strong argument parsing, good JSON handling, easy copy/install into `~/.local/bin`.
- Use **TypeScript/Node** when the official SDK, auth helper, browser automation library, or existing repo tooling is the reason the CLI can be better.
- Use **Python** when the source is data science, local file transforms, notebooks, SQLite/CSV/JSON analysis, or Python-heavy admin tooling that can still be installed as a durable command.

Do not pick a language that adds setup friction unless it materially improves the CLI. If the best language is not installed, either install the missing toolchain with approval or choose the next-best installed option.

State the choice in one sentence before scaffolding, including the reason and the installed toolchain you found.

## Command Contract

Sketch the command surface in chat before coding. Include the binary name, discovery commands, resolve or ID-lookup commands, read commands, write commands, raw escape hatch, auth/config choice, and PATH/install command.

When designing the command surface, read [references/agent-cli-patterns.md](references/agent-cli-patterns.md) for the expected composable CLI shape, and [references/agent-ux-standards.md](references/agent-ux-standards.md) for the interaction-quality bar the finished CLI must meet: layered help (≤30-line top level, complete per-command help with one example and a next-step line), teaching refusals (what/why/fix/escape), state-derived next-step hints on success output, bounded output with safe continuation (any consumed cursor advances only through what was shown), ambient verified context (resolve identity/target, refuse contradictions, one --force escape), terse agent-default output with an explicit --pretty human mode (never TTY detection), shell-safe --file/stdin for free text, validated references with closest-match suggestions, doctor + status orientation commands, noise discipline (never report a failure for something never attempted), locked read-modify-writes with non-fatal auxiliary persistence, uniform grammar, a selftest extended in the same change as any mechanic, and a single source of truth for the command inventory.

Build toward this surface:

- `tool-name --help` shows every major capability.
- `tool-name --json doctor` verifies config, auth, version, endpoint reachability, and missing setup.
- `tool-name init ...` stores local config when env-only auth is painful.
- Discovery commands find accounts, projects, workspaces, teams, queues, channels, repos, dashboards, or other top-level containers.
- Resolve commands turn names, URLs, slugs, permalinks, customer input, or build links into stable IDs so future commands do not repeat broad searches.
- Read commands fetch exact objects and list/search collections. Paginated lists support a bounded `--limit`, cursor, offset, or clearly documented default.
- Write commands do one named action each: create, update, delete, upload, schedule, retry, comment, draft. They accept the narrowest stable resource ID, support `--dry-run`, `draft`, or `preview` first when the service allows it, and do not hide writes inside broad commands such as `fix`, `debug`, or `auto`.
- `--json` returns stable machine-readable output.
- A raw escape hatch exists: `request`, `tool-call`, `api`, or the nearest honest name.

Do not expose only a generic `request` command. Give the agent high-level verbs for the repeated jobs.

Document the JSON policy in the CLI README or equivalent: API pass-through versus CLI envelope, success shape, error shape, and one example for each command family. Under `--json`, errors must be machine-readable and must not contain credentials.

## Auth and Config

Support the boring paths first, in this precedence order:

1. Environment variable using the service's standard name, such as `GITHUB_TOKEN`.
2. User config under `~/.<tool-name>/config.toml` or another simple documented path.
3. `--api-key` or a tool-specific token flag only for explicit one-off tests. Prefer env/config for normal use because flags can leak into shell history or process listings.

Never print full tokens. `doctor --json` should say whether a token is available, the auth source category (`flag`, `env`, `config`, provider default, or missing), and what setup step is missing.

If the CLI can run without network or auth, make that explicit in `doctor --json`: report fixture/offline mode, whether fixture data was found, and whether auth is not required for that mode.

For internal web apps sourced from DevTools curls, create sanitized endpoint notes before implementing: resource name, method/path, required headers, auth mechanism, CSRF behavior, request body, response ID fields, pagination, errors, and one redacted sample response. Never commit copied cookies, bearer tokens, customer secrets, or full production payloads.

Use screenshots to infer workflow, UI vocabulary, fields, and confirmation points. Do not treat screenshots as API evidence unless they are paired with a network request, export, docs page, or fixture.

## Build Workflow

1. Read the source just enough to inventory resources, auth, pagination, IDs, media/file flows, rate limits, and dangerous write actions. If the docs expose OpenAPI, download or inspect it before naming commands.
2. Sketch the command list in chat. Keep names short and shell-friendly.
3. Scaffold the CLI with a README or equivalent repo-facing instructions.
4. Implement `doctor`, discovery, resolve, read commands, one narrow draft or dry-run write path if requested, and the raw escape hatch.
5. Install the CLI on PATH so `tool-name ...` works outside the source folder.
6. Smoke test from another repo or `/tmp`, not only with `cargo run` or package-manager wrappers. Run `command -v <tool-name>`, `<tool-name> --help`, and `<tool-name> --json doctor`.
7. Run format, typecheck/build, unit tests for request builders, pagination/request-body builders, no-auth `doctor`, help output, and at least one fixture, dry-run, or live read-only API call.

If a live write is needed for confidence, ask first and make it reversible or draft-only.

When the source is an existing script or shell history, split the working invocation into real phases: setup, discovery, download/export, transform/index, draft, upload, poll, live write. Preserve the flags, paths, and environment variables already relied on, then wrap the repeatable phases with stable IDs, bounded JSON, and file outputs.

For raw escape hatches, support read-only calls first. Do not run raw non-GET/HEAD requests against a live service unless the requester asked for that specific write.

For media, artifact, or presigned upload flows, test each phase separately: create upload, transfer bytes, poll/read processing status, then attach or reference the resulting ID.

For fixture-backed prototypes, keep fixtures in a predictable project path and make the CLI locate them after installation. Smoke-test from `/tmp` to catch binaries that only work inside the source folder.

For log-oriented CLIs, keep deterministic snippet extraction separate from model interpretation. Prefer a command that emits filenames, line numbers or byte ranges, matched rules, and short excerpts.

## Install Location and PATH

Install the runnable command into a user-writable directory that is on PATH — the source folder is never the install location.

- Unix/macOS: default to `~/.local/bin`.
- Windows: default to `%USERPROFILE%\.local\bin` (create it if missing); do not assume `make` exists — provide an equivalent install script or command.

Before installing, verify the chosen directory is actually on PATH (`echo $PATH` / `$env:Path`). If it is not, add it and disclose that a new shell is required for it to take effect:

- Unix/macOS: append an `export PATH="$HOME/.local/bin:$PATH"` line to the user's shell rc file.
- Windows: update the user-level Path variable, e.g. `[Environment]::SetEnvironmentVariable('Path', "$([Environment]::GetEnvironmentVariable('Path','User'));$env:USERPROFILE\.local\bin", 'User')`.

The smoke test in the Build Workflow (`command -v <tool-name>` from another directory) is the proof the install worked — do not skip it.

## Rust Defaults

When building in Rust, use established crates instead of custom parsers:

- `clap` for commands and help
- `reqwest` for HTTP
- `serde` / `serde_json` for payloads
- `toml` for small config files
- `anyhow` for CLI-shaped error context

Add a `Makefile` target such as `make install-local` that builds release and installs the binary into `~/.local/bin`.

## TypeScript/Node Defaults

When building in TypeScript/Node, keep the CLI installable as a normal command:

- `commander` or `cac` for commands and help
- native `fetch`, the official SDK, or the existing HTTP helper for API calls
- `zod` only where external payload validation prevents real breakage
- `package.json` `bin` entry for the installed command
- `tsup`, `tsx`, or `tsc` using the repo's existing convention

Add an install path such as `pnpm install`, `pnpm build`, and `pnpm link --global`, or a `Makefile` target that installs a small wrapper into `~/.local/bin`.

## Python Defaults

When building in Python, prefer boring standard-library pieces unless the workflow needs more:

- `argparse` for commands and help, or `typer` when subcommands would otherwise get messy
- `urllib.request` / `urllib.parse`, `requests`, or `httpx` for HTTP, matching what is already installed or already used nearby
- `json`, `csv`, `sqlite3`, `pathlib`, and `subprocess` for local files, exports, databases, and existing scripts
- `pyproject.toml` console script or a small executable wrapper for the installed command
- `uv` or a virtualenv only when dependencies are actually needed

Add a `Makefile` target such as `make install-local` that installs the command on PATH and document whether it depends on `uv`, a virtualenv, or only system Python.

## Expose the Finished Tool

After the CLI works, catalog and expose it:

- **rbtv inventory (mandatory):** add the first-party `path` row to the owning module's `exposure.csv` (`part-kind=tool`, `method=path`, entry-point = the invocable; `rbtv-cli`/`description` empty — the tool self-documents via `-h`), per `d-tool-inventory-exposure-rows`.
- **Companion skill (when harness exposure is warranted):** write a small skill in the order a future agent session should use the CLI, not as a tour of every feature: how to verify the installed command exists, which command to run first, how auth is configured, which discovery command finds the common ID, the safe read path, the intended draft/write path, the raw escape hatch, what not to do without explicit approval, and three copy-pasteable command examples. Keep API reference details in the CLI docs; keep the skill focused on ordering, safety, and examples future sessions should actually run.

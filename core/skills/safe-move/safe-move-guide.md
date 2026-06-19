# Safe Move — Tool Guide

How to use the `safe-move` tool and what to expect from it. The tool moves or renames a file or folder and fixes every reference to it. It is a deterministic Python package — it makes NO LLM calls and dispatches NO agents.

`{rbtv_path}` below is the RBTV source path baked into the `rbtv-safe-move` loader (recorded in `rbtv.json`). The tool directory is `{rbtv_path}/core/tools/safe-move/`.

---

## Terms

Read these first — the rest of the guide uses them constantly. Do not guess them from the word alone.

| Term | What it means here |
|------|--------------------|
| `old` | The thing you are moving or renaming, at its CURRENT location — a single file OR a folder. It is the first argument to `consult`/`act` and is always passed as an absolute path. |
| `new` | The destination — where `old` is going (its new location and/or new name). Second argument to `consult`/`act`, always an absolute path. |
| scope (a.k.a. **search root**) | The ONE directory tree the tool reads top-to-bottom looking for references to `old`. It is NOT the move itself and NOT just `old`'s folder — it is the whole area searched. Default: the **git repository root that contains `old`** (the top folder of that git repo, i.e. its "git top level"); every file under that root is read once. **Nested git repositories under the scope (sub-repos) are NOT descended into by default** — see `--include-nested-repos`. Bigger scope = more files = slower. `--scope-root <path>` sets it explicitly — point it at a smaller subtree to scan less and finish faster. |
| reference | A live pointer to `old` from some file inside the scope — a markdown link, a wikilink, a frontmatter value, a config-file path, or a code import. Finding these and rewriting them to point at `new` is the tool's whole job. |

---

## What the tool does

Given an `old` path and a `new` path, the tool:

1. Picks a search root (the git top level of `old`, unless `--scope-root` overrides) and scans it.
2. Finds every reference to `old` — markdown links, wikilinks, frontmatter values, config paths, code imports, paths written as inline code in markdown prose, unique bare filenames (a `name.md` with no path separator, in a backtick span or in prose, when its basename is unique in scope), and any literal occurrence of the exact `old` path elsewhere (bare prose, inside a command span, a config header).
3. Classifies each reference by risk (`auto` / `surface` / `protected`) and computes the exact replacement.
4. On `act`, performs the git-aware move and auto-applies the `auto` fixes, leaving `surface` and `protected` sites for you.

Code references are matched **structurally via `ast-grep`** (true imports), never by raw text or regex. A precise, static, single-target import is `auto`; a dynamic, aliased, or ambiguous one is `surface`.

---

## Prerequisite — `ast-grep` via `npx`

Code-reference matching requires `ast-grep`, located only via `npx` (`shutil.which("npx")`). If `npx`/`ast-grep` is absent, the tool **degrades gracefully**: it emits a `code-backend-unavailable` warning and finds no code references (non-code references still work). To guarantee code coverage, ensure Node.js/`npx` is on PATH; the tool resolves `ast-grep` on demand (pinned `@ast-grep/cli@0.43.0`).

---

## Invocation

Run the package as a module with the tool directory as the working directory, and pass **absolute** `old`/`new` paths (the search root is derived from `old`, independent of the working directory):

```
cd {rbtv_path}/core/tools/safe-move
python -m safe_move consult <abs-old> <abs-new> [options]
python -m safe_move act     <abs-old> <abs-new> --apply <id:hash>[,<id:hash>...] [options]
```

Two stateless subcommands. The tool keeps NO state between calls — you hold the result; a per-reference hash guards integrity.

### `consult` — find & classify (changes nothing)

- **Input:** `old`, `new`, plus options below.
- **Returns** a record per reference: `{ id, file, line, match, context, syntax, proposed, class, hash }`; the git-move method it will use; warnings (unreachable/published, governed hand-offs, cross-project, history-loss, non-UTF-8/binary files skipped); and folder-cascade info for folder moves.
- Run this FIRST. Read the records, decide which `surface` ids (if any) you also want applied, and keep each chosen id together with its `hash`.

### `act` — move & apply

- **Input:** `old`, `new`, the same options, and `--apply` with the `id:hash` pairs of any **surface** sites you ALSO want applied (each id paired with the hash `consult` returned). `auto` sites are applied regardless of `--apply`; an empty `--apply` value applies the `auto` fixes and performs the move.
- **Does:** re-derives every reference from scratch (stateless), then: applies every `auto` site; applies each **requested** id whose current hash still equals the `consult`-time hash (**mismatch (drift) → refuse that id and report it**); NEVER applies a `protected` site, even when requested (reported as `protected-not-applied`); surfaces the rest. Then performs the git-aware move.
- **Returns** an action log: moved (and how), auto-fixed, surfaced (old→new), skipped/drifted, warnings.

Because `act` re-derives and trusts only the hash, it is parallel-safe and resumable — it is safe for you to edit surfaced sites between `consult` and `act`; any site you changed simply drifts and is refused rather than clobbered.

---

## Reference classes

| Class | Who acts | Meaning |
|-------|----------|---------|
| `auto` | the tool | Precise + low blast-radius → fixed automatically on `act`. |
| `surface` | you | Imprecise, ambiguous, or cross-boundary → the tool reports it; you decide or edit. Pass its `id:hash` to `--apply` only if you want the proposed fix applied. |
| `protected` | nobody | Transcript, record/log, or quote → never edited, even if requested. |

---

## Options

| Option | Effect |
|--------|--------|
| `--scope-root <path>` | Override the search root (default: git top level of `old`). Use when `old` is not in a git repo, or to widen/narrow the scan. |
| `--exclude <glob>` | Skip matching paths during the scan. Repeatable. Use for archives, vendored deps, build output. |
| `--read-only <glob>` | Always surface matches under these globs, never auto-edit them. Repeatable. |
| `--include-archive` | Descend into `--exclude` paths instead of skipping them. |
| `--include-nested-repos` | Descend into nested git repositories under the scope (default: skip them). Use only when you need to find cross-repo references; their reference rewrites are always surfaced, never auto-applied. |
| `--generated <glob>` | Mark matching files as generated (regenerate them, do not patch). Repeatable. |

Excludes, read-only areas, and generated globs are arguments — the tool hardcodes none of them. Pass the calling workspace's conventions explicitly.

**Nested git repos are skipped by default; archives are NOT.** A sub-repository under the scope (another project with its own `.git`) is not read unless you pass `--include-nested-repos` — so a default scan never reaches into sibling repos (sensitive or otherwise). An **archive folder is a normal directory**, not a sub-repo, so it IS scanned by default — pass `--exclude <archive-glob>` to skip it. In a workspace with off-limits or archive areas that are not their own git repos, supplying the relevant `--exclude` globs is a required pre-flight.

---

## Git-aware move behavior

| Situation | Method | Note |
|-----------|--------|------|
| Tracked, within one repo | `git mv` | History preserved. |
| Untracked | plain `mv` | `git mv` would error. |
| Across repos (different git top level) | plain `mv` | Each repo tracks its own side; **history does NOT follow → warned**; cross-repo reference rewrites are surfaced, never auto-applied. |

The tool **moves and stages**; it does NOT commit. `git mv` history continuity is realized only after YOU commit.

---

## Folders — the primary case

Moving a folder moves every file in it and fixes every reference to the folder path AND to each moved file, using the same classifier. This needs no conventions. Convention-specific follow-ons (renaming a folder's index file, rewriting identity tags, fixing dashboard queries) are NOT in the engine — they are the calling agent's job.

---

## What to expect — and what the tool does NOT do

- It does NOT commit. It auto-applies `auto` sites, applies a `surface` site only when you pass its `id:hash` to `--apply`, and NEVER touches a `protected` site (even if requested → reported as `protected-not-applied`). After `act`, resolve any remaining surfaced sites yourself, then commit.
- A `surface` classification is a request for your judgment, not an error — dynamic/aliased imports, multi-target short names, per-file relative paths, and references inside quotes/logs surface by design.
- Drift on an id at `act` means that site changed since `consult` — re-run `consult` to get fresh records/hashes if you need it applied.
- `consult` is read-only and safe to run alongside a parallel session. If `old` is moved or deleted by another session WHILE a scan is in flight, the scan fails cleanly — a one-line `old path no longer exists (changed during scan)` on stderr and exit 1 — never a raw traceback, and never a partial/garbage envelope on stdout.
- Code coverage depends on `npx`/`ast-grep` being available (see Prerequisite). Without it, no code references are found and a warning is emitted.
- Paths written as inline code in markdown (`` `a/b/c.md` ``) are detected and **surfaced** (never `auto`) when they resolve to the moved target — pass the id to `--apply` to apply the rewrite. When the scan is scoped to a subtree (`--scope-root` pointing inside a larger repo), a backtick path written relative to the **workspace/git root** — e.g. `` `4-archives/x.md` `` while scanning `1-projects` — is resolved against that root too and surfaced, even when the moved target lives OUTSIDE the scan scope (previously such a reference was silently dropped).
- **A bare filename with no path separator is also detected — but ONLY when it carries a known file extension AND its basename is unique in scope.** A reference written as `` `name.md` `` (a backtick span, no separator → `inline-code-basename`) or as a bare `name.md` in plain markdown prose (no backticks, no separator → `prose-filename`) is **surfaced** (never `auto`) when its basename resolves to exactly one in-scope file — mirroring the frontmatter rule that a name carrying an extension (`x.md`) is a file reference. On a **basename collision** (two in-scope files share the name) the bare reference is left **unmatched** (the `basename-collision` warning fires), since it is genuinely ambiguous. A backtick span or prose token with **no extension** (e.g. `` `npx` ``, a bare word) is never matched, so commands and ordinary words are not mistaken for files; an extension outside the known set (e.g. a version like `1.2.3`) is likewise ignored. Prose tokens inside an inline-code span, wikilink, markdown link, or the frontmatter block are left to those matchers, never double-counted.
- **Literal occurrences of the exact `old` path are also detected and surfaced** (`literal-path`, never `auto`), wherever they appear — bare prose, inside a command span (`` `/cmd … old/path/x.md` ``), a config header, or HTML. This catches the self-referential case: a moved folder whose own files name its old path. The match is bounded by path delimiters, so a longer sibling (`old/path-other`) or a path under a different parent (`vendor/old/path`) is never matched, giving near-zero false positives. **Scope and limits:** the search is for the literal **scope-root-relative POSIX** `old` string — a relative form (`../old/x.md`) or a Windows-backslash absolute path is NOT matched (those that resolve via a structured syntax are still caught by the other matchers; the rest are left untouched, never corrupted). For a **folder** move, the moved folder's OWN files are swept even under skip-named dirs (`build/` / `dist/` / `target/`) — a project's records there are content being relocated, so EVERY matcher — markdown link, wikilink, frontmatter, config, code import — AND the literal sweep run over them: a structured reference (e.g. a markdown link or config path) to the old location inside a moved record is detected and classified like any other reference, not only caught as a bare literal, even though such dirs are skipped everywhere else in the scope. **This self-reference sweep requires the moved folder to be WITHIN the scan scope:** when the moved folder sits OUTSIDE `--scope-root`, its own files are NOT swept and a `moved-folder-out-of-scope` warning says so — in-scope references to it are still surfaced (with a workspace-root-relative proposed); re-run without `--scope-root` (or with a `--scope-root` that contains the moved folder) to also catch self-references inside the moved tree.
- In a note's frontmatter, a value counts as a reference only when its FORM says so: a path (contains `/`, incl. a trailing-`/` folder), an explicit `[[wikilink]]`, or a name carrying a file extension (`x.md` = a file). A bare word with no extension (e.g. `tags: design`, `area: rbtv`) is treated as a label and is left untouched — even when it equals a moved file's name. To have such a value tracked on a move, write it as a path, a `[[wikilink]]`, or with its extension.
- **Wikilinks** resolve by basename by default; a **path-qualified** wikilink (`[[dir/name|alias]]`, with or without `.md`) is resolved by its path and surfaced (never `auto`, with a path-aware proposed rewrite) when it points at the moved file. When the moved file's basename collides with another in-scope file of the same name or stem, a `basename-collision` warning names the colliding file(s), and bare `[[name]]` links stay `surface` (never `auto`) because they may target the other file.
- Binary and non-UTF-8 files in scope are skipped automatically and are never reference candidates — you do NOT need to `--exclude` them. A single `non-utf8-skipped` warning reports how many were skipped.
- **Symbolic links are out of scope — the walker does NOT follow them.** A symlink inside the moved tree is not scanned, so a reference reachable ONLY through a symlink is **missed, never corrupted**; the symlink itself is moved verbatim (its target is left unchanged, so it still points where it did). Fix any reference that lives behind a symlink by hand after the move. This safe-failing boundary is guarded by `test_folder_matrix.py::test_symlink_to_outside_file_is_skipped_and_target_missed_not_corrupted`, which is platform-skipped on hosts where symlink creation is unprivileged (e.g. Windows without Developer Mode/admin).
- A plain (non-git) move whose source cannot be fully deleted afterward (e.g. a Windows file lock from an editor/indexer) still completes the destination, then reports the leftover paths via a `partial-source-cleanup` warning and exits 0 — it never aborts with an exit-1 that leaves a half-deleted source. Remove the reported leftovers once the lock releases.
- Scan time scales with the **scope size**, not the move size. The default scope is the git top level of `old`; on a large repo/vault (~10k files) a whole-scope scan takes tens of seconds (each file is read once; ast-grep runs O(languages), not O(files)). For a fast targeted move, pass `--scope-root <subtree>` to limit the scan to where references can plausibly live.

---

## Self-check

Verify the tool runs in this workspace:

```
cd {rbtv_path}/core/tools/safe-move
python -m safe_move --help
```

Run the engine test suite (requires `git`; code tests require `npx`/`ast-grep`):

```
cd {rbtv_path}/core/tools/safe-move
python -m pytest -q
```

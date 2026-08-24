---
description: Standalone folder search — index markdown sections and rank them by meaning, keyword, or substring; binding nothing.
---

# embed-search — semantic search over any folder

`rbtv embed-search` — one surface for Voyage embeddings over an arbitrary directory (memory, wiki, tecer search, anything else). Purpose-free: it knows no consuming workflow. Grep is the deterministic floor. Built so three copies of a Voyage integration collapse to one capability.

```
rbtv embed-search index  --root <dir> [--glob '**/*.md'] [--index <file>]   build/refresh the index
rbtv embed-search query  --root <dir> "<text>" [--top N] [--json] [--arm semantic|keyword|grep]
rbtv embed-search status --root <dir>                                          index age, doc count, arms
rbtv embed-search selftest                                                     red arm included; passes with NO key
```

Flags: `--root <dir>` (required for index/query/status) · `--glob <pat>` (default `**/*.md`) · `--index <f>` · `--top <n>` · `--arm semantic|keyword|grep` · `--json` · `--pretty`.
Exit codes: `0` success · `1` refusal · `2` usage error.

## ranking — three arms, one ladder

The unit of ranking is a **markdown section** (heading-delimited) with file path + heading in the output. A short memory entry is one section and ranks as a whole.

**Availability ladder** (wiki-helper shape): `VOYAGE_API_KEY` in the OS environment → else vault `.user/config/env/.env` walking up from cwd/`--root` → semantic+keyword hybrid; key absent → keyword-only; failure → grep-equivalent substring ranking. A failure NEVER throws past the CLI — it degrades and says so on stderr / `--json`. `--arm` pins one arm; if that arm cannot run, the command degrades and names the arm that answered.

`query` self-syncs the index before ranking. `index` is the same refresh without a query.

## the index

Default location: `$XDG_STATE_HOME/rbtv-embed-search/<hash-of-root>/index.json` (falls back to `~/.local/state/...`). **Never inside the indexed tree.** Incremental by file mtime + section hash. `4-archives/` is never walked.

## the vendor boundary

Embedding calls go through teambuild's `tool/lib/provider.js` (imported, not copied). That module is the one place a Voyage request is formed. This capability adds the folder corpus, the keyword/grep arms, and the outside-the-tree index. Swapping providers stays teambuild's contract (`id`/`model`/`dim`).

The key's value is never printed, logged, committed, or passed as an argument — name and origin only.

## what refuses (the red arm)

An absent `--root` refuses. A present-but-unreadable root refuses naming the path. An unknown verb or `--arm` is a usage error. `selftest` plants both defects on a scratch tree and asserts the refusal fires; it must pass with the key unset.

## read-only over the corpus

`embed-search` never writes into the indexed folder. The one file it writes is its own index under the state directory (or `--index`).

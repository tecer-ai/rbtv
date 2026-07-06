# hypresent AX CLI Verification Runbook

## Prerequisites

- Python 3.10+.
- Install runtime/test dependencies: `pip install beautifulsoup4 lxml playwright`.
- Install browser binaries: `playwright install chromium`.
- Run every command from the RBTV repo root.
- Commands use only repo fixtures unless marked `owner-side`.
- For write-verb rows, create disposable fixture copies first:

```powershell
New-Item -ItemType Directory -Force studio/hypresent/tools/.tmp-verify
Copy-Item studio/hypresent/tools/fixtures/write-deck.html studio/hypresent/tools/.tmp-verify/write-add.html
Copy-Item studio/hypresent/tools/fixtures/write-deck.html studio/hypresent/tools/.tmp-verify/write-reply.html
Copy-Item studio/hypresent/tools/fixtures/write-deck.html studio/hypresent/tools/.tmp-verify/write-delete-one.html
Copy-Item studio/hypresent/tools/fixtures/write-deck.html studio/hypresent/tools/.tmp-verify/write-delete-all.html
Copy-Item studio/hypresent/tools/fixtures/write-deck.html studio/hypresent/tools/.tmp-verify/write-delete-missing.html
```

## Dehydrate

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py dehydrate --file studio/hypresent/tools/fixtures/basic.html --out studio/hypresent/tools/.tmp-verify/basic.lean.html --json` | Exit 0. JSON includes `ok: true`, `fallback: false`, `out: "studio/hypresent/tools/.tmp-verify/basic.lean.html"`, `lean_chars <= src_chars`, `lean_bytes <= src_bytes`, and `comments_preserved: 1`. Output file exists and is no larger than the source. | Normal lean-view creation, never-grow stats, lossless digest path. |
| `python studio/hypresent/tools/hypresent.py dehydrate --file studio/hypresent/tools/fixtures/tiny.html --out studio/hypresent/tools/.tmp-verify/tiny.lean.html --json` | Exit 0. JSON includes `ok: true` and `fallback: true`; output is the source verbatim, so the raw `#hyp-comments` island may be present. | Sanctioned never-grow fallback exception. |
| `python studio/hypresent/tools/hypresent.py dehydrate --file studio/hypresent/tools/fixtures/corrupted-island.html --out studio/hypresent/tools/.tmp-verify/corrupted.lean.html` | Exit 2. stderr starts `hypresent dehydrate: error:` and names the corrupt comment island; no output file is written. | Failure mode refuses bad persisted comment data without creating a partial lean file. |
| `python studio/hypresent/tools/hypresent.py dehydrate --file <saved-hypresent-deck.html> --json` | owner-side. Exit 0. JSON reports whether the real deck used `fallback: false` digest mode or `fallback: true` verbatim mode. | Real-deck spot check outside repo fixtures. |

## Read

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --mode comments --json` | Exit 0. JSON has `kind: "comments"`, `count: 4`, and full thread objects. | Browser-free comment listing. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --comment c-nested --self --json` | Exit 0. JSON has `kind: "element"`, `comment_id: "c-nested"`, `relation: "self"`, `status: "ok"`, and a `matches` list whose entry is selected by literal `data-hyp-cid`. | Commented element lookup through the durable comment id tag. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --comment c-nested --self --parent --sibling --json` | Exit 0. JSON has `kind: "element-set"`, `relations: ["self", "parent", "sibling"]`, and a `contexts` list with one element payload per relation. | `--self`/`--parent`/`--sibling` combine in one call, returning the union of contexts. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --selector "#selector-only" --json` | Exit 0. JSON has `kind: "selector"`, `selector: "#selector-only"`, `status: "ok"`, and a `matches` list with exactly one entry. | Gate-2 sanctioned ephemeral selector read for un-commented elements. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --selector ".does-not-exist" --json` | Exit 0. JSON has `kind: "selector"`, `status: "empty"`, and `matches: []`. | Zero-match selector reads are empty reports, not errors. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --selector "[" --json` | Non-zero exit. stderr starts `hypresent read: error:` and includes `invalid selector`. | Invalid selector failure mode. |
| `python studio/hypresent/tools/hypresent.py read --file studio/hypresent/tools/fixtures/query-nested.html --comment absent` | Exit 2. stderr starts `hypresent read: error:` and lists available ids. | Missing comment failure mode. |

## Search

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py search --file studio/hypresent/tools/fixtures/query-nested.html --query needle --json` | Exit 0. JSON has `kind: "search"`, `query: "needle"`, `case_sensitive: false`, `count >= 1`, and each hit carries location context. | Case-insensitive default search over page text. |
| `python studio/hypresent/tools/hypresent.py search --file studio/hypresent/tools/fixtures/query-nested.html --query not-present --json` | Exit 0. JSON has `kind: "search"`, `count: 0`, and `hits: []`. | Zero-hit searches are explicit empty results. |
| `python studio/hypresent/tools/hypresent.py search --file does-not-exist.html --query needle` | Exit 2. stderr starts `hypresent search: error:` and includes `file not found`. | Search failure mode. |

## Add Comment

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py add-comment --file studio/hypresent/tools/.tmp-verify/write-add.html --selector "#target-copy" --body "Tighten this copy." --author "Vivian" --agent` | Exit 0 after a multi-second browser run. JSON field set is exactly `ok, file, comment_id, author, agentInstruction, anchor, anchored, marker_rendered, contextText`; values include `ok: true`, `author: "Vivian"`, `agentInstruction: true`, `anchored: true`, `marker_rendered: true`, and `contextText: "Target copy for a new comment."`. Saved file contains `id="hyp-comments"`. | Real-runtime browser write, marker render proof, saved-island proof, direct contract fields. |
| `python studio/hypresent/tools/hypresent.py add-comment --file studio/hypresent/tools/.tmp-verify/write-add.html --selector ".dupe" --body "Body" --author "Agent"` | Exit 2. stderr starts `hypresent add-comment: ERROR —` and includes `selector matched 2 elements`. | Add-comment selector failure mode and new error prefix. |
| `python studio/hypresent/tools/hypresent.py add-comment --file <saved-hypresent-deck.html> --selector "<unique-css-selector>" --body "Owner-side smoke." --author "Agent" --out <saved-hypresent-deck-copy.html>` | owner-side. Exit 0. JSON has the same contract fields and the output copy carries the new thread. | Real deck write outside repo fixtures without overwriting the source. |

## Reply

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py reply --file studio/hypresent/tools/.tmp-verify/write-reply.html --comment-id c-existing --reply "Working on it." --author "Agent" --set-agent` | Exit 0 after a multi-second browser run. JSON field set is exactly `ok, file, comment_id, reply_added, reply_author, reply_body, agent_instruction, replies_count, thread_count`; values include `ok: true`, `comment_id: "c-existing"`, `reply_added: true`, `reply_author: "Agent"`, `reply_body: "Working on it."`, `agent_instruction: true`, `replies_count: 1`, and `thread_count: 1`. Saved file contains `id="hyp-comments"`. | Real-runtime reply write, agent flag update, saved-island proof, direct contract fields. |
| `python studio/hypresent/tools/hypresent.py reply --file studio/hypresent/tools/.tmp-verify/write-reply.html --comment-id missing --reply "Body"` | Exit 2. stderr starts `hypresent reply: ERROR —` and includes `no comment thread with id`. | Reply failure mode and new error prefix. |

## Delete Comment

DESTRUCTIVE verb — deletion is owner-directed ONLY; an agent never deletes or resolves a human's threads on its own initiative. On the `write-deck.html` fixture `c-existing` is the only thread, so removing it (single or `--all`) leaves zero threads and the serializer saves a valid island-free file (`thread_count: 0`).

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py delete-comment --file studio/hypresent/tools/.tmp-verify/write-delete-one.html --comment-id c-existing` | Exit 0 after a multi-second browser run. JSON field set is exactly `ok, file, deleted_ids, deleted_count, thread_count`; values include `ok: true`, `deleted_ids: ["c-existing"]`, `deleted_count: 1`, `thread_count: 0`. Saved file no longer carries the `c-existing` thread (the last thread removed → no `#hyp-comments` island, which is a valid island-free save). | Real-runtime single-thread delete through the bus command + island-free save contract. |
| `python studio/hypresent/tools/hypresent.py delete-comment --file studio/hypresent/tools/.tmp-verify/write-delete-all.html --all` | Exit 0 after a multi-second browser run. JSON has the same field set with `deleted_ids: ["c-existing"]`, `deleted_count: 1`, `thread_count: 0`. Every thread is gone from the saved file. | `--all` deletes every thread and reports the remaining count. |
| `python studio/hypresent/tools/hypresent.py delete-comment --file studio/hypresent/tools/.tmp-verify/write-delete-missing.html --comment-id nope` | Exit 2. stderr is exactly one line: `hypresent delete-comment: ERROR — comment id not found: nope; available ids: c-existing`. Deck unchanged. | Unknown-id failure mode lists available ids (read's convention) and never mutates. |

Argument contract (no browser): `--comment-id` and `--all` are mutually exclusive and exactly one is required — passing both or neither exits 2 via argparse before any server/browser work.

## Missing Playwright Contract

| Command | Expected output | Proves |
|---|---|---|
| `python studio/hypresent/tools/hypresent.py add-comment --file studio/hypresent/tools/.tmp-verify/write-add.html --selector "#target-copy" --body "Body"` in an environment without Playwright installed | Exit 3. stderr states Playwright is unavailable. Do not execute this row in the normal autonomous leg after installing prerequisites. | Write verbs distinguish missing dependency from user/data errors. |
| `python studio/hypresent/tools/hypresent.py reply --file studio/hypresent/tools/.tmp-verify/write-reply.html --comment-id c-existing --reply "Body"` in an environment without Playwright installed | Exit 3. stderr states Playwright is unavailable. Do not execute this row in the normal autonomous leg after installing prerequisites. | Reply has the same missing dependency contract. |

## Full Suite

| Command | Expected output | Proves |
|---|---|---|
| `python -m pytest studio/hypresent/tools/ -v` | Exit 0 with 46 passing tests when Playwright is installed. If Playwright is absent, write-verb browser rows are skipped by contract and the conductor must run the installed-Playwright leg separately. | All dehydrate, read/search, and write-verb (add/reply/delete) contracts are covered. |

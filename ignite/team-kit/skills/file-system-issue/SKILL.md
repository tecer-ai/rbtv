---
name: file-system-issue
description: "File a system issue (defect, gap, change notice) whose surface is under ignite/ or meta/ into the engine goal's register. Use when a goal-master or leader sees a defect, gap, or change notice on those surfaces — file, don't fix."
exposes-cli:
  - file-issue
---

# file-system-issue

File, don't fix (D50). The engine goal reads its register on its own cadence — filing wakes nobody.

## When to file

A defect, gap, or change-notice whose surface lives under `ignite/` or `meta/` of the rbtv repo.

## What not to file

Anything else. Route it to the caller's own goal `issues.md`. Out-of-scope `file-issue` calls refuse with `scope-refused` and that pointer.

## Command

```
file-issue file --surface <ignite/…|meta/…> --class <class> --symptom "<one line>" --evidence "<path or command>" --suggested-action "<text>" --risk "<one line>" [--as <goal>/<seat>]
```

`--as` defaults from this seat folder's `seat.md` (`seat:` + the goal folder name). Required only when that derivation cannot run.

Classes: `daemon-crash` `launch-cage` `coordination` `bridge-chat` `probe-gap` `data-ledger` `catalog-meta` `docs` `change-notice` `other`.

## Required fields

- **surface** — path under `ignite/` or `meta/`
- **class** — one of the classes above
- **symptom** — one line
- **evidence** — a path or a command
- **suggested-action** — what a later sitting should do
- **risk** — one line
- **as** — who files (`<goal>/<seat>`), derived when possible

## Id

`G-<seat>-<MMDD>-<HHMM>` (UTC). Collision suffixes `-2`, `-3`. One file per filing at `<register>/open/<id>.md`. The heading inside the file stays `## <id> — <symptom>` plus `Destination: ignite-engine`.

Verify with `file-issue doctor` then `file-issue show <id>`. Flags and refusals: `file-issue --help` / `file-issue file --help`.

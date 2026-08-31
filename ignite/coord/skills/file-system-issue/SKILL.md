---
name: file-system-issue
description: "File a system issue (defect, gap, change notice) whose surface is under ignite/ or meta/ into the engine goal's register. Use when a goal-master, leader, or caged planning seat sees a defect, gap, or change notice on those surfaces — file, don't fix."
exposes-cli:
  - file-issue
---

# file-system-issue

File, don't fix — an ignite/ or meta/ defect, gap, or change-notice goes through the filing CLI (`file-issue`, skill `file-system-issue`) into the `ignite-engine` register; that goal's intake pass sweeps every filing into triage and the owner's digest (its contract §3.3, §5.1). (D50)

## When to file

A defect, gap, or change-notice whose surface lives under `ignite/` or `meta/` of the rbtv repo.

## What not to file

Anything else. Route it to the caller's own goal `issues.md`. Out-of-scope `file-issue` calls refuse with `scope-refused` and that pointer.

## Command

```
file-issue file --surface <ignite/…|meta/…> --class <class> --symptom "<one line>" --evidence "<path or command>" --suggested-action "<text>" --risk "<one line>" [--as <goal>/<seat>]
```

`--as` defaults from this seat folder's `seat.md` (`seat:` + the goal folder name). Required only when that derivation cannot run.

Fields, classes and the status vocabulary: `file-issue schema`.

## Id

`G-<seat>-<MMDD>-<HHMM>` (UTC). Collision suffixes `-2`, `-3`. One file per filing at `<register>/open/<id>.md`. The heading inside the file stays `## <id> — <symptom>` plus `Destination: ignite-engine`.

Verify with `file-issue doctor` then `file-issue show <id>`. Flags and refusals: `file-issue --help` / `file-issue file --help`.

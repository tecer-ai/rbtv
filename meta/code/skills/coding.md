---
name: coding
description: "CONTAINS: the instructions every edit to code follows, read before the first edit of one line or of a new file: nothing left unused, one source per fact and behaviour, one responsibility per file, a fix at the cause and never at the symptom, the ladder that picks each piece's form (reuse, standard library, native feature, dependency, one line), and the four jobs on code: building a command-line interface, auditing architecture, reviewing for over-engineering, the shortcut ledger PURPOSE: code the next agent can change without tracing what was left behind, and the result of each job: a usable command, ranked deepening candidates, a list of what to delete, the ledger of deliberate shortcuts ALWAYS LOAD WHEN: the task adds, changes or fixes code in any file, in any words (\"add a function\", \"add a flag\", \"fix it\", \"it crashes\", \"wrong value\", \"this test fails\", \"refactor this\", \"write a script\"), however small: open it as the first step, before reading the file to edit; also when asked to design a command-line interface, to audit architecture or find shallow modules, to say what can be deleted or whether something is over-engineered, or to list the shortcuts marked for later DO NOT LOAD WHEN: the file is an rbtv instruction, skill, rule, prompt or capability page (the framework skill); the request is to commit the change (a commit tool or git); code is only read or explained and nothing changes"
---

# Coding

You are about to write, edit, fix or refactor code, or to do one of the four jobs the table at the end routes. For a change to code, read this body whole before the first edit and hold it for the whole change. For one of the four jobs, the table names its page; this body governs the code the job writes, if any. Whether to build at all and how simply, how the request is framed and the root cause of a defect were settled before this skill was opened: by the `<simplest>`, `<frame>` and `<cause>` blocks of the `critical-partner` rule where that rule is installed, and by three lines of your own otherwise. This skill governs the code you write and the code you leave.

## The four disciplines

Own change: fix. Pre-existing: surface. A violation your change creates is fixed in the same change. One that was already there is named to the user in your closing message (file, symbol or line) and never fixed unasked: widening the diff is not yours to decide. The four hold for any code anywhere; never assume a test suite, a continuous-integration run or a commit step exists.

### No dead code

After your change, nothing remains that your change made unused: a function, method, class, variable, import, parameter, file, configuration key, command-line flag, branch or test that nothing reaches; the old path a fix replaced; the helper only the deleted code called; the import only the deleted line used; the flag only the removed branch read.

- Trace what your change made unreachable, following the callers and readers of everything you removed or rewrote, and delete it in the same change.
- Never comment code out and never keep a block "in case": version control is the archive; a deleted thing is recovered from history if a need arrives.
- The one exemption is a public interface you can verify is consumed outside this codebase (a published command verb, a served endpoint, a library export with an external caller). "Might be used somewhere" is not verification: search the consumers; unverifiable means delete.

Before closing, for every symbol you removed or rewrote, answer: what else existed only for it? That list is what you delete.

### No duplicate

Every fact and every behaviour has exactly one authored source. Two sources drift, and the code then reads whichever it reaches: two places that read the same fact (two configuration files, a constant and a literal, a table and a hand-filled cache); two code paths doing the same thing (a second helper, a copied block with one name changed, a second script for a job a script already does); a value kept equal in two files by a person remembering to.

- Before writing a function, a value, a script or a data file, search for the thing that already does it: by file extension, library calls, delimiters, output field names and caller-visible behaviour, not by symbol name alone. Two pieces of code are the same thing when they accept materially the same input and perform any of the same parsing, validation or normalization; a different output shape alone does not separate them. When it exists, reuse or extend it; extending existing code to serve the requested behaviour is part of the change, not an unasked cleanup.
- A copy is legal only when code derives it from the one source: a generated file, a build artifact, a cache the code fills and invalidates, a mirror a script writes. A hand-maintained copy is a violation whatever comment sits on it.
- When your change needs the same thing in two places, it lives in one and the other reaches it by import, call or read.
- An explicit no-touch boundary wins. When the existing thing lives in a file you were told not to touch, reuse its interface without editing it; otherwise stop and ask the user to authorize extending or extracting it. Never create a second implementation to route around the boundary.

Before closing: does any value, function, data source or script you wrote now exist somewhere else too? If yes, one of the two goes.

### No monolith

One responsibility per file, named by its filename. Size is a signal, never a cap.

- A new file holds one responsibility and its name says which. A name that needs "and" to describe the file holds two: split before writing.
- When your change grows a file, answer whether it now does more than one thing. Yes: the new thing goes in its own file, reached by import. The existing file is never split unasked; that is pre-existing.
- Around 300 lines, stop and answer that question. A 400-line file with one responsibility stays; a 120-line file with three is split.
- Never split a cohesive file into fragments to hit a size. A set of thin files an agent must bounce between to follow one concept is a shallow module, the subject of the improving-architecture method. Split only when each part can be verified on its own.

Before closing, for every file you grew, name its one responsibility in one line. Two lines: the new responsibility goes in its own file.

### No patches

What arrives is a symptom: a crash, a wrong value, a failed run. The root cause, the origin (file and line) and the contract evidence were written before this edit (the `<cause>` block); this discipline governs the edit.

- The fix lands at the origin the block named, never at the crash site, the caller or the output unless the block named that place as the origin. No block, no edit: go back and write it.
- Delete the band-aid. A prior workaround for the same symptom (a special-case branch, a swallowed exception, a retry, a default that masks a missing value, a value recomputed because the caller's was wrong) is removed in the same change; a fix that leaves it is two fixes for one bug.
- A default is legal only where the contract permits absence and the default is the specified meaning of absence, with the block naming that evidence. Where the contract requires the value, a `.get(key, default)`, an `or fallback` or any substitute at the consumer is forbidden: fix the producer or the validation boundary.
- Each of these signs stops the edit until the block is rewritten: a new `if` that special-cases the failing input; a `try/except` (or the language's equivalent) that swallows the error; a retry or a sleep around the failing call; recomputing or re-fetching a value the caller already had; a fix that touches only the line in the traceback; a default for a value the contract requires; "works now" with no sentence on why it failed.

A band-aid that masks a different symptom than the one you are fixing is pre-existing: name it (file, line, what it masks) and never remove it unasked.

## The ladder: the form of each piece

The simplest solution was stated in one sentence before work started. While writing, each piece of that solution takes the highest rung that holds, in this order, and only after you have read the code the change touches and traced the real flow end to end:

1. Already in this codebase? A helper, type or pattern that lives here is reused; re-implementing what sits a few files over is the most common waste.
2. The standard library does it? Use it.
3. A native platform feature covers it? A date input over a picker library, a stylesheet over a script, a database constraint over application code.
4. An installed dependency solves it? Use it; never add one for what a few lines do.
5. Can it be one line? One line.
6. Only then: the minimum code that works.

Two rungs hold: take the higher. Two standard-library options of the same size: take the one that is correct on edge cases; less code is the aim, not the flimsier algorithm. Boring over clever: clever is what someone decodes at three in the morning. The smallest change in the wrong place is not simple, it is a second bug: the ladder shortens the solution, never the reading.

A deliberate simplification that cuts a real corner with a known ceiling (a global lock, a quadratic scan, a naive heuristic) carries a [shortcut](../capabilities/glossary/shortcut.md) marker naming the ceiling and the upgrade path, written in the same change.

Never simplify away: input validation at a trust boundary, error handling that prevents data loss, security measures, accessibility basics, the calibration knob of anything that touches hardware (a real clock drifts, a real sensor reads off), and anything the user explicitly asked for. When the user insists on the full version, build it without re-arguing.

## One runnable check

Code without its check is unfinished. Non-trivial logic (a branch, a loop, a parser, a path that handles money or security) leaves one runnable check behind, the smallest thing that fails when the logic breaks: an `assert`-based self-check under the program's main entry, or one small test file, in the convention the repository already uses where it has one. No framework, no fixtures, no per-function suite unless asked. A trivial one-liner needs none.

## Closing message

Code first. Then, in a few lines: what was skipped and when to add it (`skipped: X; add when Y`); the pre-existing violations found, each with its file, symbol or line and the discipline it breaks; the shortcut markers written. No design notes and no paragraph defending a simplification: an explanation longer than the code is complexity smuggled back as prose. An explanation the user asked for is given in full.

## The four jobs

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [Building a command-line interface](../capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification, with its contract, output-preview and blind-testing pages | A command a person and an agent can discover, understand and use for the same operations | creating or redesigning a durable command-line interface, or changing its usability, help, output or errors | a one-off script meets the need and no durable command is required: this body suffices |
| [Improving architecture](../capabilities/methods/improving-architecture.md) | The vocabulary of depth (module, interface, seam, adapter, leverage, locality), the scan for shallow modules, the HTML report of deepening candidates and the grill of the one the user picks | A ranked, visual set of candidates for turning shallow modules into deep ones, one of them worked through to a decided shape | asked to audit, review or improve a codebase's architecture, find shallow modules or deepening opportunities, or make code more testable or navigable by agents | the request is to cut bloat from code as it is (reviewing for over-engineering), or to change code (this body) |
| [Reviewing for over-engineering](../capabilities/methods/reviewing-for-over-engineering.md) | The five tags (delete, stdlib, native, yagni, shrink), the one-line finding and the scope: a diff, or the whole tree ranked | A list of what to delete, each with its replacement, and the net lines possible; nothing is applied | asked to review a change or a codebase for over-engineering, bloat, unneeded dependencies or what can be deleted | correctness, security or performance is the concern (a normal review), or the shape of modules is (improving architecture) |
| [The shortcut ledger](../capabilities/methods/shortcut-ledger.md) | The search for every shortcut marker and the ledger row each becomes, with the no-trigger flag | The deliberate shortcuts of a codebase listed with their ceilings and upgrade triggers, so a deferral cannot silently become permanent | asked what was deferred, marked for later or simplified on purpose, or for the shortcut ledger | the question is what is still cuttable (reviewing for over-engineering) |

---
description: Read at the moment of designing a new memory — a durable, curated record of how to do a kind of job well, for a component, agent type, or workflow that does not have one yet. Rules the SHAPE (unit, kind, key, layers, filing, reading, upkeep), never the content.
tags: [memory, planning]
---

# creating-memories — the generic procedure for designing a memory

You already know WHAT the thing needs to remember. This file rules the SHAPE you write that remembering into, so the memory survives past the session that built it and stays cheap to read at commit rate. The worked example throughout is the ignite build memory (`rbtv/ignite/work-on-ignite/`, ruled 2026-08-23) — read `work-on-ignite.md` for the realized instance, this file for the procedure it is an instance of.

## 1. What a memory is, and is not

The knowledge graph (KG) models what a system remembers as three boxes, each `is-a memory`, defined independently of the system's own concepts: **box ① work-in-progress memory** (what a running unit of work must remember across sessions; goal-scoped, dies with its goal), **box ② craft memory** (how to do a KIND of job well; durable, curated, lives in the memory store), **box ③ world memory** (durable world-knowledge — user, projects, contacts — reached by pull). A memory you are designing under this reference is almost always box ②: it is craft about building or operating a component, not the live state of one run of work.

The membership test (`sd-graph show memory`): if it is kept in order to be REMEMBERED — carried forward to inform a later session — rather than being the durable subject the system acts on, or scaffolding, it is memory. Memory is never scaffolding, and it is never the open side of anything: an open question, a loose end, a thing still being decided has a different, existing home (a goal's `issues.md`/`loose-ends.md`, a `decisions.md` log) and NEVER enters memory. The ignite build memory states this as a hard boundary: "If it is still open, it does not belong here." Design your own memory's boundary the same way, in one sentence, before anything else — a memory that also tries to hold open work becomes a second, worse register.

## 2. Decide the unit

The unit is what ONE entry records. Get this wrong and everything downstream (naming, cap, distillation) inherits the wrong grain.

- **Never one commit** — a commit is an implementation detail of how a fix landed, not the fix itself; several commits can close one issue, and one commit can close several.
- **Never one ruling** — a ruling belongs in a decision log (append-only, settled-by-reference elsewhere); a memory entry is about EXECUTING a kind of job, not about the governance that authorized it.
- **One fixed issue, or one creation.** The ignite memory ruled exactly two kinds and no more (see § Decide the kinds) — resist the urge to add a third "in-between" kind; a kind you cannot name in one word is a sign the unit is still wrong, not that you need more kinds.

## 3. Decide the kinds

Keep the kind list SHORT — few kinds, each with a mandatory body shape and a filing moment stated plainly enough that a filer never has to guess which one applies. The ignite memory uses exactly two:

- **issue** — one loose end or bug, filed ONLY when fixed (a fix is ALWAYS filed — an issue never sits open in memory; an unfixed issue lives in the goal's own register, never here).
- **creation** — something new added; refactors, removals, and renames are creations too, tagged `kind=change` rather than invented as a third kind.

Each kind's mandatory body fields are fixed in advance (§ 4) so a filer is filling a form, not composing prose from scratch. "Missed trials" — approaches tried and abandoned — are never their own entry; they live INSIDE the eventual issue entry that succeeded, because a trial that never converged has no fix to file.

## 4. Decide the key

The KEY is the folder a memory is organized by — the question "which file does this entry go in" must have exactly one obviously-correct answer for any given fact, or filers start splitting the same knowledge across near-duplicate homes.

For a build memory the natural key is the **component**: one folder per top-level unit the codebase is already organized into (the ignite memory keys on the top-level folder under `ignite/` and under `meta/` — nineteen components, one memory tree covering both). Pick your own memory's key from a partition that ALREADY EXISTS in the thing being remembered (a folder, a service, an agent type) — never invent a new partition just for the memory, because now two structures must be kept in sync forever.

A fact that touches more than one key (a cross-cutting fix) is filed ONCE, under the key where the fix actually landed; every OTHER key it touched is named on that one entry's index line (§ 5), never duplicated into a second entry. This is the rule that keeps one fact from rotting into two contradictory copies.

## 5. Two layers — the index agents read, the entry agents open

Every memory splits into two layers, because an agent editing component X needs to scan "has this broken before" in seconds, not read every past fix in full:

- **The index line** — what agents actually read, by default, before touching the key. Field order encodes priority: put the fact a scanning agent needs FIRST, leftmost. The ignite index line is `date · kind · title · symptom→cause (one clause) · commit · other-components · ⚠ if ATTENTION` — date and kind first (so a scan can filter by recency and type before reading further), the causal clause next (the single fact that answers "does this apply to what I'm about to do"), then provenance (commit) and blast radius (other components) last. Give the index line a TARGET length and a HARD CAP (280 target / 400 cap here) — a target keeps entries scannable, a hard cap keeps one verbose entry from making the whole index unreadable — and enforce the cap in the filing command (§ 6), never in prose alone. The index is APPEND-ONLY, newest entry LAST: a prior line is never rewritten, because a rewritten line is a lie about when something was known.
- **The entry file** — full context, opened only when the index line says "this looks relevant." What makes an entry file worth opening later, rather than becoming prose nobody re-reads, is concreteness: the ignite entries are decisive because they cite `path:lines` against the ACTUALLY DEPLOYED tree (not just HEAD, which can differ from what is running), name the Missed trials and WHY each failed (so the next agent doesn't re-try a dead end), and carry ATTENTION bullets rather than instructions. **"Do not undo" wording is banned outright** — the owner ruled it dangerous, because a KEEP-style command outlives the reason for it and eventually blocks a legitimate reversal; an ATTENTION bullet states what to watch for and why, and lets the reader decide, rather than forbidding an action it cannot foresee the future need for.

## 6. Mechanize the write

Prose instructions describing WHEN to file a memory entry are necessary but not sufficient — they tell an agent what to do, never that it did it correctly. The fix is ONE filing command that OWNS: entry shape (which fields are mandatory, per kind), naming (the file-naming pattern and its collision rule), the index-line cap (enforced, not advised), and refusals (a bad shape, a missing required field, an unknown key, a name over the length limit are REJECTED by the command, never silently accepted). Prose says WHEN to file; the command guarantees WHAT gets written. The ignite memory's `file-issue memory file` command takes `--component`, `--kind`, `--title`, `--body-file`, `--commit`, `--deployed`, `--pin`, `--components` (the OTHER keys touched), `--attention` (repeatable), `--date` (backdating), and `--seeded` — and refuses anything malformed rather than writing a bad entry that then has to be hand-fixed.

Name every WRITER explicitly — every door through which the thing being remembered changes is a place a memory entry might need filing, at that door's CLOSE (not before, since the entry only exists once the fix or creation actually landed). The ignite memory names two: the owning goal's own build/closure step, and ANY OTHER session that edits the same tree (a console agent, the owner at a terminal) — via the identical command, at ITS close. A memory with only one named writer will silently stop growing the moment a second kind of session starts touching the same code.

## 7. Mechanize the read

A memory nobody reads before acting is theater. Read is a ladder, cheapest-and-most-reliable-first:

1. The distilled summary (§ 8) plus the live index of every key you are about to touch — this is the FLOOR, always read, no tooling required.
2. A semantic lookup over the memory tree for the symptom and the files you're about to touch, where one exists (the ignite memory built a standalone embed-search capability for this — semantic search first, falling back to keyword, falling back to grep, so a missing or down search tool degrades rather than blocks).
3. A GREP of every index for the key names and paths you will touch, as the DETERMINISTIC FLOOR under the semantic layer — grep never needs an API key, never times out, and catches what a semantic index missed or hasn't ingested yet.
4. CITE the consulted entry ids (the entry filenames) in whatever you produce next — a proposal, a commit message — so a later reader (or a judge) can verify "memory was actually consulted" rather than taking your word for it.

## 8. Plan the 30-day problem from day one

A memory that only ever grows becomes as unreadable as no memory at all. Decide the distillation trigger BEFORE the first entry is filed, not once the index is already unreadable:

- **Count-triggered, not calendar-triggered** — a memory's growth rate tracks commit rate, not wall-clock time, so "every 30 days" silently over- or under-fires; "when the live index passes N lines" fires exactly when it needs to. The ignite memory triggers at 60 lines per key, distilling to a `_summary.md` (design intent, key map, standing ATTENTION, superseded fixes) and rotating all but the newest 30 lines to an archive file.
- **A hub goal runs it on a cadence** — one standing goal that owns EVERY memory's maintenance workflow, rather than each memory inventing its own upkeep mechanism. The ignite program's is `goal-memory-management`; connect a new memory to that hub goal (or your ecosystem's equivalent) the moment the memory is created, not after it has already grown past its own trigger unattended.
- This is the KG's **dreamers** role realized concretely: the KG names curation (bake / keep / expire a memory entry) as belonging SOLELY to the dreamers (`sd-graph find dreamers`); the hub goal's distillation workflow is what actually performs that curation for this memory.

## 9. Seed it at birth

An empty memory teaches nothing and earns no trust — the first agent to consult it and find nothing concludes the memory doesn't work, and stops checking. Where evidence of the past already exists (git history, an existing ad-hoc fix log, a decisions file), run ONE seeding pass before the memory goes live: convert that evidence into properly-shaped entries, BACKDATED to when the fix or creation actually happened, and marked `seeded` on their index line so a reader can tell inferred history from real-time filing. The ignite memory seeded from `fix-inventory.csv` (itself a ruling→commit→files→probe table derived from git log) plus the redesign plan's seed documents plus raw git log — the exact mechanism that had already, by hand, turned the original ten-day patch loop around.

## 10. Where it lives, and how it is named

**Location:** with the thing it remembers, versioned with it — NOT in a generic runtime memory store unless the memory genuinely is box-① or box-③ runtime memory (§ 1). A box-② craft memory about a codebase lives inside that codebase's own repo, travels with its commits, and is visible in the same `git log` a future agent already has to read. The ignite memory lives at `rbtv/ignite/work-on-ignite/memory/`, inside the rbtv repo, not in `.rbtv/memory/` (the runtime memory store `sd-graph show "memory store"` describes) — because it is memory ABOUT the code, not memory the running system carries between goals.

**Naming:** reuse the KG's existing vocabulary for every part of the mechanism — memory, register, file/filing, decision-log, dreamers — and never coin a synonym for something that already has a name. A new synonym for "filing" or "the register" is not a stylistic choice; it is a second name for one thing that now has to be reconciled by every future reader.

## Checklist

Answer each with yes/no before treating the design as done:

| # | Check |
|---|---|
| 1 | Have you stated, in one sentence, that open work never enters this memory? |
| 2 | Is the unit ONE fixed issue or ONE creation-equivalent — never a commit, never a ruling? |
| 3 | Is the kind list short, and does each kind have a fixed mandatory body? |
| 4 | Does the key reuse a partition that already exists in the thing being remembered? |
| 5 | Does the index line have a target length AND a hard cap, both enforced by a command? |
| 6 | Does every entry file cite concrete evidence (paths, deployed-tree lines, named failed trials) rather than a forbidding-future-reversal instruction (§ 5)? |
| 7 | Is there ONE filing command that owns shape/naming/cap/refusals, and are ALL writers named? |
| 8 | Is the read step a ladder with a deterministic floor (grep) under any semantic layer, and does it require citing consulted entry ids? |
| 9 | Is the distillation trigger count-based, and is it wired to a standing hub goal or equivalent recurring owner? |
| 10 | Was the memory seeded from existing evidence at birth, backdated and marked, rather than launched empty? |

## Worked instance — the ignite build memory

| Decision point | Ignite's answer |
|---|---|
| Box | ② craft memory, versioned with the rbtv repo |
| Unit | one fixed issue / one creation (`kind=change` for refactors) |
| Kinds | `issue`, `creation` — two only |
| Key | component = top-level folder under `ignite/` and `meta/` (19 keys) |
| Index line | `date · kind · title · symptom→cause · commit · other-components · ⚠`, 280 target / 400 cap |
| Entry body | Seen/Missed/Held + commit + deployed-tree `files:lines` + `deployed` + `pin` + ATTENTION (never a forbidding-reversal instruction, § 5) |
| Filing command | `file-issue memory file`, refuses bad shape/name/missing field/unknown component |
| Writers | the owning goal at build/closure; any other ignite-editing session at its close |
| Read ladder | `_summary.md` + live index → embed-search (semantic→keyword→grep) → grep-all-indexes floor → cite entry ids |
| Distillation | count-triggered at 60 live-index lines, keep newest 30, rest to `_issues-archive.md`; run by hub goal `goal-memory-management` |
| Seeding | one pass from `fix-inventory.csv` + redesign-plan seed docs + git log, backdated, marked `seeded` |
| Location | `rbtv/ignite/work-on-ignite/memory/`, inside the repo it remembers |

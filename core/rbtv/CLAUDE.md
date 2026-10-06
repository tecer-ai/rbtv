# Documentation rules

Rules 1 and 3 apply to every file in this component. Rule 2 applies only to rbtv-specific terms. Rule 4 governs `decisions.md`. The documentation pages are the glossary (`glossary/`), the principles (`principles/`), the capabilities at the root of `capabilities/`, and the schemas in `templates/`; the entry point is `skills/framework.md`. Paths below are relative to `capabilities/` unless they start with `capabilities/`, `skills/` or name `decisions.md`.

## Where this folder is going

This folder is the `rbtv` component of rbtv's `core` module. Its capabilities are in `capabilities/`: the glossary, the principles, and the capabilities that the `framework` skill (`skills/framework.md`) routes to. They exist so that the skill can lead an agent through them whenever it builds, edits, reviews or converts a skill, a rule, a command, an agent, a tool, or any other file of rbtv; write every page as `writing-a-glossary-entry.md` says.

## 1. Written as current

Every file in this component, except `CLAUDE.md`, `AGENTS.md`, and `decisions.md`, describes rbtv 0.2.1 as the current, existing design. They never mention 0.1 or 0.2, what changed, what was renamed or removed, or why. Comparisons with earlier versions belong only in `decisions.md` (rule 4).

## 2. Every standard file and folder has a glossary entry

This rule covers rbtv-specific terms only: rbtv's own standard files, folders, and cognitive units that are not files. General terms, such as command-line or harness vocabulary, get no entries, except `context window`: rbtv exists to shape it (`decisions.md`, Editorial decisions). Each standard rbtv file or folder named anywhere in `skills/framework.md`, `glossary/` or `principles/` has one glossary entry in `glossary/`, written as `writing-a-glossary-entry.md` says: what it is, what it is for, how it fails, what it is composed of, how to build it, its template as a code block, and its references. A section of a thing that is never built alone (a section of a prompt or of a task) is a part of the containing entry, not an entry. A file that a CLI checks has a schema (`<name>.schema.json`) in `templates/`, linked from its entry; the schema is the authority for its fields and the entry does not list them. There is no index file: `skills/framework.md` names each page.

When you add or rename a standard file, folder, or one of these sections, create or update its entry and schema in the same change. When one of these cannot be written yet because its design is not decided, raise it with the owner (rule 3). Do not write a placeholder.

## 3. Raise every inconsistency

When you find an inconsistency in any file of this component while working here, tell the owner, even if it is outside your task. Inconsistencies include contradictions between documents, broken links, a term used with two meanings, a gap under rule 2, or text that breaks rule 1. Do not resolve it silently. Report it, and fix it only when the owner agrees.

## 4. `decisions.md` contains the standing decisions, never a log

- `decisions.md` contains only decisions specific to rbtv 0.2.1. A decision that is not specific to it, such as a general command-line design choice, does not go there.
- When the owner makes such a decision about this documentation, record it in `decisions.md`, under the section of the file where it belongs.
- The file contains only the decisions in force right now. When a decision is superseded, replace its entry. Do not append the new one after the old one, and do not keep the old one with a date, "previously", "first considered", or similar history.
- A decision that compares 0.2.1 with 0.1 or 0.2 is recorded when it changes the shape of this documentation. The trigger is the owner saying "0.1/0.2 works like X, I want Y, because Z". Record what 0.2.1 does, how the earlier version did it, and the owner's reason. The migration from 0.2 to 0.2.1 will be planned from these entries.
- Undecided questions stay under "Open decisions". When one is decided, move it to its section and remove it from the open list.
- When the owner defers a decision but says how they imagine it will work, record those hints under that open decision, starting with "Owner hints (not decided):". Record them in the owner's meaning, without adding to them. Hints stay only in `decisions.md`: never write them into `skills/framework.md`, `glossary/`, `principles/`, or the capabilities, and never build on them as if decided. When the decision is made, the hints go with the open item.

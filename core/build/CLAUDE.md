# Documentation rules

Rules 1 and 3 apply to every file in this component. Rule 2 applies only to rbtv-specific terms. Rule 4 governs `decisions.md`. The documentation pages are `rbtv.md`, `glossary/`, `guides/`, `principles/`, and `templates/` under `capabilities/`; paths below are relative to `capabilities/` unless they start with `capabilities/` or name `decisions.md`.

## Where this folder is going

This folder is the `build` component of rbtv's `core` module, staged at `core/build/` inside this project, the same path it has in rbtv. Its capabilities are in `capabilities/`: the reader pages, glossary, building guides, templates, and principles. They exist so that the `build` skill (`skills/build.md`) can teach agents to read and navigate them whenever they build skills, rules, commands, agents, tools, or other rbtv units; write every page so that skill can lead an agent through it. Other cognitive units that use these capabilities may move in later.

## 1. Written as current

Every file in this component, except `CLAUDE.md`, `AGENTS.md`, and `decisions.md`, describes rbtv 0.2.1 as the current, existing design. They never mention 0.1 or 0.2, what changed, what was renamed or removed, or why. Comparisons with earlier versions belong only in `decisions.md` (rule 4).

## 2. Every standard file and folder has a glossary entry and a building entry

This rule covers rbtv-specific terms only: rbtv's own standard files, folders, and cognitive units that are not files. General terms, such as command-line or harness vocabulary, get no entries, except `context window`: rbtv exists to shape it (`decisions.md`, Editorial decisions). Each standard rbtv file or folder named anywhere in `rbtv.md`, `glossary/`, or `principles/` has both:

- a glossary entry in `glossary/` that says what it is, and
- a building entry in `guides/` that says how to create it.

Cognitive units of a prompt, and cognitive units a task carries, are not files or folders, but each one gets both entries as well. The cognitive units of a prompt are listed in `glossary/prompt.md`. The cognitive units a task carries include scope and done contract.

Each standard file with a fixed shape also has its shape in `templates/`: a template for what agents read, a schema (`<name>.schema.json`) for what programs read, or both when one file serves both, each named after its glossary entry and listed in `templates/templates.md`. Where a file has both, the schema is the authority for its fields and the template's frontmatter keys equal the schema's. A template or schema holds only decided fields and sections. A file whose shape is not decided, or whose content has no fixed shape, has no template. A building guide carries no file mechanics — no folder placement, installer behavior, frontmatter fields, or template link; those live in `rbtv.md`, the navigation index, one line each with a link.

When you add or rename a standard file, folder, or one of these cognitive units, create or update its entries and template in the same change. When one of these cannot be written yet because its design is not decided, raise it with the owner (rule 3). Do not write a placeholder.

## 3. Raise every inconsistency

When you find an inconsistency in any file of this component while working here, tell the owner, even if it is outside your task. Inconsistencies include contradictions between documents, broken links, a term used with two meanings, a gap under rule 2, or text that breaks rule 1. Do not resolve it silently. Report it, and fix it only when the owner agrees.

## 4. `decisions.md` holds the standing decisions, never a log

- `decisions.md` holds only decisions specific to rbtv 0.2.1. A decision that is not specific to it, such as a general command-line design choice, does not go there.
- When the owner makes such a decision about this documentation, record it in `decisions.md`, under the section of the file where it belongs.
- The file holds only the decisions in force right now. When a decision is superseded, replace its entry. Do not append the new one after the old one, and do not keep the old one with a date, "previously", "first considered", or similar history.
- A decision that compares 0.2.1 with 0.1 or 0.2 is recorded when it changes the shape of this documentation. The trigger is the owner saying "0.1/0.2 works like X, I want Y, because Z". Record what 0.2.1 does, how the earlier version did it, and the owner's reason. The migration from 0.2 to 0.2.1 will be planned from these entries.
- Undecided questions stay under "Open decisions". When one is decided, move it to its section and remove it from the open list.
- When the owner defers a decision but says how they imagine it will work, record those hints under that open decision, starting with "Owner hints (not decided):". Record them in the owner's meaning, without adding to them. Hints stay only in `decisions.md`: never write them into `rbtv.md`, `glossary/`, `guides/`, `principles/`, or `templates/`, and never build on them as if decided. When the decision is made, the hints go with the open item.

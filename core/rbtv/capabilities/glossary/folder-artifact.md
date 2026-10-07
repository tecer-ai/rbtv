# Folder artifact

A folder artifact is a workspace file or folder with one purpose, read through folder instructions when that purpose is needed. It can contain facts, decisions, history or guidance for particular work.

Keep the workspace's established organization. rbtv does not impose a universal artifact directory or require a standard set of files. A fixed-path record read by software is a record, not a folder artifact.

## Define its purpose and use

Identify the work that needs the artifact and neighboring work in the same folder that does not. Content needed on every visit belongs in the folder's required guidance; content needed only in a case is routed to this artifact.

Use a file when its records are read for the same work. Use a folder when different records need separate reading conditions. A folder artifact that is a folder has its own [Folder instructions](folder-instructions.md).

State the artifact's convention in the glossary of the component organizing that work, following [Writing a glossary entry](../methods/writing-a-glossary-entry.md). Do not add every component's artifact to the rbtv glossary. The entry owns the record format and the first-section wording used in instances.

## First section and records

A file begins with a section stating:

- what it records;
- what does not belong;
- how to add records;
- that agents adding records must not edit this section.

For a folder, put that section at the start of its folder instructions. Follow the owning entry's wording rather than inventing a different convention for each instance. The installer does not enforce the section; the instructions must preserve it.

Write the case's records after that section in the format the owning entry specifies. Do not add a second independent purpose because the file is already open.

```markdown
# <artifact>

<What belongs, what does not, how to add records, and the instruction to preserve this section.>

<Records in the owning glossary entry's format.>
```

## Placement and discovery

Use the task's path, or the established workspace location for this purpose. If neither exists, define the convention with the owning component and ask the user for the path before creating the instance. Do not invent a wrapper directory or copy another installation's layout.

Add its row to the containing folder's instructions in the same change. Use [Routing table](routing-table.md) to name the condition under which the artifact is read. Do not make it an index of sibling files; the folder's table already supplies those routes.

## Changes and tests

Changing the convention requires an authorized update to the glossary entry and every affected instance's first section together. Routine additions change only the records. Keep routes synchronized with purpose and location.

For conversion, separate independently used purposes, retain the standing first-section contract and move sibling-file lists into folder routes. Classify other kinds through [Choosing what to build](../methods/choosing-what-to-build.md).

Review the first section before its records. Then test one task that should find and update the artifact and another that should not read it, starting from folder instructions without supplying the path again. Check that updates preserve the first section. No installer validates this behavior.

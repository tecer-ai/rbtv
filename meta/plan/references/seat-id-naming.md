---
description: Name reusable component workflow seat ids consistently
tags: [planning]
---

# Seat ids in reusable workflows

A manifest references a seat id from its component's `seats.csv`. Choose a short stable prefix
for that workflow and use it on every row; use the rest of the id to name the seat's job. Prompt
and task ids name their reusable content, so they do not inherit the workflow prefix. Check id
uniqueness across the component before registering the manifest.

A console seat plan uses descriptive folder names instead. Its ids are the folder names under
`seats/`, with no component catalog or workflow prefix; see `plan.md`.

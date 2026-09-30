---
description: Author the permissions section of a reusable component prompt
tags: [planning]
---

# `<permissions>` — permitted surfaces

Name the files and commands the prompt's procedure needs. Derive each permission from a real
step and keep write scope narrower than read scope. The section explains intended access; the
actual harness or workspace permission comes from the launch environment and must be checked
there. Do not claim that prose alone grants access.

A restriction belongs in `<restrictions>`, an instrument's purpose in `<resources>`, and a
runtime destination in the seat request. Delete a permission that no procedure step uses.

# para decisions

Standing decisions about para. Each states the decision and its reason; the folder instructions describe the resulting design.

## Tooling has no `resources/tools/` folder

Installed tooling, catalogs, prompts and nested tool repositories each get their own category folder, `resources/{name}/`. Reason: owner decision, 2026-10-15; a `tools/` level added a folder to every path without separating anything a category folder does not.

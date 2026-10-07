# Self-contained skill

A self-contained skill keeps its instructions in `SKILL.md` beside the supporting material needed to use it. Use this format to import a skill or write one for sharing independently of rbtv’s component layout.

Place it at `.rbtv/mirror/_skills/<name>/SKILL.md`, with its supporting files in that skill folder. This source form belongs only in the mirror, not the rbtv repository. Follow [rbtv CLI](rbtv-cli.md) for recognition, frontmatter retention, the generated copy and refresh operations. The installer copies the whole folder for each harness, so write links to supporting files relative to `SKILL.md`; the source remains in the mirror.

For instruction writing and discovery, follow [Skill’s build method](skill.md#build-the-skill) using this folder layout. Keep required instructions and supporting files within the skill rather than depending on rbtv capability pages outside it. Each supporting file has a stated purpose and is reached where needed. Declare external software and services the skill requires.

Read and test the instructions with their supporting material. Give a reader a representative task and only the skill’s files and declared dependencies. Check that it can complete the task, and that the installed copy holds every supporting file. Edit the source rather than the generated copy; use the CLI’s refresh rules after any change to the folder.

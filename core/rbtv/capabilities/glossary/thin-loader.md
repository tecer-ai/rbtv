# Thin loader

A small harness-facing file that points to a skill or command's full source content. For an rbtv-format unit, that source is in its component; for a [self-contained skill](self-contained-skill.md), it is the mirror's `SKILL.md` and the loader carries that file's frontmatter. It lets an agent choose to read a skill or a human invoke a command without copying the full content into the harness. Rules are installed directly and do not use thin loaders.

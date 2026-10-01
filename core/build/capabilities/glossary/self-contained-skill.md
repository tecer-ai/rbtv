# Self-contained skill

A skill in the standard shareable skill format: its own `SKILL.md` and any supporting files live together. It can be imported from someone else or written here for sharing. rbtv's own skills instead use a thin loader, the entry file it points to, and capabilities.

The standard `_skills/` folder exists only at `.rbtv/mirror/_skills/`, never in the rbtv repository. Each `_skills/<name>/` folder holds one self-contained skill. The installer lists it and installs a thin loader pointing to its `SKILL.md`, carrying that file's own frontmatter. The loader is tracked in [`install.json`](install-json.md) like every other managed unit, so `rbtv install update` refreshes it and `rbtv install remove` deletes it. The skill stays at its mirror source; when that source is a git repository, `git pull` updates it and the loader makes the pulled content available immediately. See [building a self-contained skill](../guides/self-contained-skill.md).

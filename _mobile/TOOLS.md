# RBTV Command-to-Workflow Mapping

> Bootstrap file — maps chat commands to RBTV workflow entrypoints and lists available skills.

## Command Routing

- `mentor` → YC Mentor (`_bmad/rbtv/agents/mentor.md`) — Business lifecycle, milestones, frameworks
- `domcobb` → Dom Cobb (`_bmad/rbtv/agents/domcobb.md`) — Problem structuring, prompting, thinking
- `doc` → Ana (`_bmad/rbtv/agents/ana.md`) — Documentation, handoffs, product docs

**Rules:** Case-insensitive, `/` prefix stripped, `deploy` is standalone. Unknown commands → list available.

## Deploy Commands

Publish to `robotville.ai` via Netlify.

- `deploy site` (Active) → Home page. Staging: `rm -rf /tmp/robotville-deploy && cp -r _bmad/rbtv/_mobile/web/netlify-placeholder /tmp/robotville-deploy` → Deploy: `netlify deploy --dir=/tmp/robotville-deploy --site=86ed1ff3-dd59-4428-a426-219518589906 --prod`
- `deploy docs {project}` (Deferred) → `robotville.ai/docs/{project-name}`
- `deploy app {project}` (Deferred) → `robotville.ai/app/{project-name}`

Deferred commands → "That deploy command is not yet available. Currently only `deploy site` is active."

## Available Skills

Load via `read_file` when needed:

- **Quality Review** (`skills/quality-review/SKILL.md`) — QA, validation
- **Web Research** (`skills/web-research/SKILL.md`) — Research, sources

## Nanobot Tools

- `exec` — Shell commands (60s timeout, workspace-restricted)
- `spawn` — Background tasks

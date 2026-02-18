# RBTV Command-to-Workflow Mapping

> **Bootstrap file — loaded into system prompt on every Nanobot call.**
> This file maps chat commands to RBTV workflow entrypoints and lists available skills.

---

## Command Routing Table

These are the top-level commands that activate RBTV agent personas. Each command loads an agent file that presents its own menu of workflows.

| Command | Agent | Entrypoint File | Description |
|---------|-------|-----------------|-------------|
| `mentor` | YC Mentor | `_bmad/rbtv/agents/mentor.md` | Business innovation lifecycle — milestones, frameworks, project progression |
| `domcobb` | Dom Cobb | `_bmad/rbtv/agents/domcobb.md` | Problem structuring, prompting assistance, structured thinking |
| `doc` | Ana | `_bmad/rbtv/agents/ana.md` | Documentation — compound learning, handoffs, product docs |

**Routing rules:**
- Commands are case-insensitive. `/mentor`, `Mentor`, `MENTOR` all resolve to `mentor`.
- Leading `/` is stripped before matching.
- `deploy` is a standalone action command — see Deploy Commands section below.
- If the command doesn't match any agent or action command, respond with the list of available commands.

---

## Deploy Commands

Deploy commands publish content to `robotville.ai` via Netlify CLI. These are standalone action commands — they do not activate an agent persona.

**CRITICAL: Deploy ONLY on explicit user command. Never deploy automatically — not on framework completion, not on state changes, not on agent switching, not on session start.**

| Command | Status | Action |
|---------|--------|--------|
| `deploy site` | Active | Deploy robotville.ai home page |
| `deploy docs {project}` | Deferred | Deploy project documents to `robotville.ai/docs/{project-name}` |
| `deploy app {project}` | Deferred | Deploy project app to `robotville.ai/app/{project-name}` |

**`deploy site` execution:**
1. User sends `deploy site`.
2. Copy the source directory to a staging path outside git tracking:
   `exec`: `rm -rf /tmp/robotville-deploy && cp -r _bmad/rbtv/_mobile/_docs/netlify-placeholder /tmp/robotville-deploy`
3. If the user requested content changes before deploying, apply edits to files in `/tmp/robotville-deploy/` (never edit the git-tracked source directly).
4. Deploy from the staging path:
   `exec`: `netlify deploy --dir=/tmp/robotville-deploy --site=86ed1ff3-dd59-4428-a426-219518589906 --prod`
5. Report deploy URL and result to user.

**Deferred commands:** If the user sends `deploy docs`, `deploy app`, or any deploy subcommand not marked Active above, respond: "That deploy command is not yet available. Currently only `deploy site` is active."

---

## Available Skills

Skills are loaded on demand when relevant to the current task. Use `read_file` to load the full skill file when needed.

| Skill | Skill File | When to Use |
|-------|-----------|-------------|
| Doc | `skills/doc/SKILL.md` | Creating documentation, handoffs, product docs |
| Quality Review | `skills/quality-review/SKILL.md` | Reviewing work quality, validating deliverables |
| Web Research | `skills/web-research/SKILL.md` | Conducting web research, gathering and evaluating sources |

---

## Nanobot Tool Reference

These are the Nanobot-native tools available for workflow execution:

| Tool | RBTV Usage |
|------|-----------|
| `read_file` | Load agent files, workflow files, step files, project-memo, config |
| `write_file` | Save framework outputs, create new project files |
| `edit_file` | Update project-memo frontmatter, modify existing files |
| `list_dir` | Browse project structure, discover available files |
| `exec` | Run shell commands (git operations, file management) |
| `web_search` | Market research, competitive analysis (via Brave API) |
| `web_fetch` | Fetch and read URLs for research tasks |
| `spawn` | Background tasks with isolated context |

**Tool constraints:**
- `exec` has a 60-second default timeout and is restricted to the workspace directory.
- `edit_file` requires the `old_text` to be unique in the file — provide enough context for unambiguous matching.
- `write_file` auto-creates parent directories.

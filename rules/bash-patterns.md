# Bash Command Patterns

## Avoid cd + command compounds

Never use `cd "path" && command` compound patterns. These trigger security prompts in Claude Code regardless of permission rules.

Use these alternatives instead:

| Instead of | Use |
|---|---|
| `cd "path" && git status` | `git -C "path" status` |
| `cd "path" && git log --oneline -5` | `git -C "path" log --oneline -5` |
| `cd "path" && git diff --stat` | `git -C "path" diff --stat` |
| `cd "path" && grep -n "pattern" file` | `grep -n "pattern" "path/file"` |
| `cd "path" && node script.js` | `node "path/script.js"` |
| `cd "path" && python script.py` | `python "path/script.py"` |

For commands that do not support a path argument, pass the full absolute path to the target file or directory directly.

## git push — never use git -C

Never run `git -C "path" push`. The deny rule in settings only blocks `git push` as a standalone command — `git -C "path" push` bypasses it.

Always run push as a standalone command: `git push` or `git push origin branch`. This ensures the permission prompt fires as intended.

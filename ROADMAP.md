# RBTV Roadmap

## install-rbtv.py Improvements

### Incremental Sync

The script currently deletes all `bmad-rbtv*` files and re-copies everything on every run. It must instead compare file timestamps or checksums and only copy files that actually changed. This avoids unnecessary churn and reduces the chance of overwriting user modifications.

### Preserve User Settings

The `.vscode/settings.json` merge overwrites user-added `files.exclude` keys. The script must only manage RBTV-owned patterns (e.g. keys prefixed with a comment tag or a known pattern list) and leave user-added entries untouched.

### Dry-Run Mode

Add a `--dry-run` flag that previews what would change without modifying any files. This lets users verify the impact before running the actual install.

### Changelog Awareness

Only prompt for IDE restart when files that require it (e.g. `mcp.json`, agents, MCP server configs) actually changed. If only docs or non-IDE files were updated, skip the restart message.

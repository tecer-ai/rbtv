# BMAD Mirror Version

This folder contains a read-only copy of BMAD for RBTV development reference.

| Field | Value |
|-------|-------|
| BMAD Version | 6.0.4 |
| Mirror Synced | 2026-03-08 |
| Source | https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.0.4 |

**Do not modify files in this folder.** This is RBTV-owned metadata about the mirror, not BMAD content.

## Module Versions at Mirror Sync

| Module | Version |
|--------|---------|
| core | 6.0.4 |
| bmm | 6.0.4 |
| bmb | 0.1.6 |
| cis | 0.1.8 |
| tea | 1.5.2 |

## Directory Name Convention

The mirror's `claude/` and `cursor/` directories correspond to `.claude/` and `.cursor/` in a real BMAD workspace. The dot prefix is intentionally removed in this mirror to prevent Claude Code and Cursor from scanning these directories as live command/rule sources, which causes every command to appear multiple times in the IDE command picker.

When updating the mirror from a BMAD release, rename `.claude/` → `claude/` and `.cursor/` → `cursor/` in the new snapshot.

## Notes

- Mirror reflects the BMAD installation synced on 2026-03-08
- `_bmad/rbtv/` slot is intentionally empty — this repo IS that module
- To update the mirror, download the target BMAD release and replace `_admin/docs/BMAD-mirror/` contents, preserving this file and the empty `_bmad/rbtv/` directory

# RBTV Changelog

All notable changes to the RBTV module are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — Nanobot Standard Architecture + RBTV Batch Changes

### Added

- **BMAD version declaration** in `_config/config.yaml` (`bmad_target_version`, `bmad_min_version`)
- **`_admin/docs/BMAD-mirror/MIRROR-VERSION.md`** — RBTV-owned metadata documenting what the BMAD mirror represents
- **`CHANGELOG.md`** — this file; establishes version tracking discipline for RBTV
- **`bmad-compat.yaml`** — machine-readable manifest of all RBTV→BMAD touchpoints for compatibility checking
- **`tasks/check-bmad-compat.xml`** — task for running BMAD compatibility checks before upgrades
- **`tasks/data/bmad-compat-report-template.md`** — report template for compatibility check output
- **Unified installer** (`_config/install-rbtv.py`) with three modes: IDE, admin, and nanobot-sync
- **Output-path normalization** — all installer modes enforce `_bmad-output/{project-name}/` as output base
- **Nanobot sync mode** — patches BMAD configs for RBTV integration without generating IDE config
- **`paths:` section** in `_config/config.yaml` with `{bmad_core}`, `{bmad_bmm}`, `{bmad_rbtv}`, `{bmad_output}` path variables
- **Workspace repo setup documentation** — template `.gitignore`, `entry_points.md` template, bootstrap sequence
- **Config helper scripts** relocated to `_mobile/ops/helpers/` (4 files: allowlist, workspace fix, model update, memory window)
- **Systemd service definition** preserved at `_mobile/ops/systemd/`
- **Netlify placeholder HTML files** relocated to `_mobile/web/` (4 files for robotville.ai deploy)

### Changed

- **Path resolution** — cross-module references migrated from `{bmad_core}/` pattern to `{bmad_core}` variable (~60 files)
- **Frontmatter config declaration** — workflows standardized to declare `main_config` in YAML frontmatter
- **`_mobile/README.md`** rewritten with VPS bootstrap instructions, server access info, and update flows
- **Compound workflow output routing** corrected to RBTV roadmap todos location
- **BMAD path documentation** in `CLAUDE.md` simplified after path variable introduction
- **`_mobile/SOUL.md`** allowlist rule updated — removed stale harness gate reference; allowlist is native nanobot config
- **Operational docs updated** for new architecture: `deploy-runbook.md`, `robotville-vps-access.md`, `smoke-checklist.md` (removed stale shell script and source patch steps)
- **Stale references fixed** across `readme.md`, `_admin/README.md`, `get_started.md`, `admin-rbtv-bmad-mirror.mdc` (removed references to deleted files)

### Removed

- **TypeScript harness** (dead code — 4 files, ~1,024 lines): `integration/nanobot-gateway-bridge.ts`, `routing/command-router.ts`, `security/allowlist-gate.ts`, `state/project-memo-adapter.ts`
- **Obsolete source patches** (2 files): `add-litellm-prompt-caching.py` (native since Feb 18 2026), `add-litellm-retries.py` (replaced by `LITELLM_NUM_RETRIES` env var)
- **Shell deploy scripts** (3 files): `vps-sync-install.sh`, `vps-install-git-hooks.sh`, `vps-pull-rbtv.sh` (replaced by unified installer sync mode + `git pull`)
- **`_mobile/HOW-IT-WORKS.md`** (documents the old architecture)
- **`_admin/install-admin-rbtv.py`** (absorbed into unified installer admin mode)
- **Redundant operational docs** (5 files): `deployment-smoke-report.md`, `netlify-site-info.md`, `robotville-netlify-walkthrough.md`, `robotville-hosting-decision.md`, `robotville-ai-provisioning.md`

---

## [1.0.0] — 2026-02-05

Initial RBTV module release.

### Added

- **Agents:** `ana`, `domcobb`, `god`, `mentor`
- **Workflows:** `doc-compound-learning`, `doc-context-handoff`, `build-rbtv-component`
- **Tasks:** `context-search`, `design-validation`, `git-commit`, `mermaid-conversion`, `plan-creation`, `playwright-browser-automation`, `quality-review`, `tone-extraction`, `update-bmad-config`, `visual-design-extraction`, `web-research`
- **Installer:** `_config/install-rbtv.py` (IDE mode)
- **Admin tooling:** `_admin/install-admin-rbtv.py` (standalone dev setup)
- **BMAD mirror** at `_admin/docs/BMAD-mirror/` — 6.0.0-Beta.4 snapshot for development reference

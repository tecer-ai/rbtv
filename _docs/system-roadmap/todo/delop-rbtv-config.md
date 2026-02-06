# Product Requirements Document — RBTV Config & Install Implementation

**Product:** RBTV module configuration, install script behavior, and BMAD integration  
**Author:** Documentation Orchestrator (Ana)  
**Date:** 2026-02-05  
**Status:** Implemented (with proposed future simplification)

---

## Executive Summary

This PRD specifies the implementation of RBTV module configuration, install-script-driven BMAD config updates, help catalog integration, and project-scoped output path behavior. The goal is to align RBTV with BMAD’s config pattern, enable `/bmad-help` to surface RBTV workflows, and clarify how project-specific output paths work (Mentor + project-memo). A future simplification (active-project-config.yaml) is described to remove per-delegation config swap logic.

---

## Problem & Context

- **RBTV had no config.yaml** — Help task step 2 could not resolve rbtv output locations; rbtv was not in the installer/manifest model; rbtv workflows and agents loaded core config only.
- **Output paths were hardcoded** — BI and other workflows used literal `_bmad-output/{project-name}/...`; no single source of truth for the base or for project name.
- **RBTV was missing from the help catalog** — `bmad-help.csv` had no rbtv rows, so `/bmad-help` could not recommend RBTV workflows or resolve rbtv artifact paths.
- **Delegation to BMAD required config swap** — When RBTV invoked BMAD (e.g. create-ux-design), workflows had to run update-bmad-config (overwrite bmm config with full path), invoke BMAD, then restore-bmad-config. This was token-heavy and repeated in every delegation flow.

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| RBTV has a module config | `_bmad/rbtv/config.yaml` exists; only `output_folder` lives in rbtv; rest inherited from core. |
| BMAD default output aligns with BI | install-rbtv sets core/bmm config so planning_artifacts and implementation_artifacts use `_bmad-output/{project-name}/...`. |
| RBTV appears in help catalog | install-rbtv adds rbtv rows to `bmad-help.csv`; help task step 2 finds rbtv config and resolves output locations. |
| Project name semantics are documented | Readme states that project-scoped paths require Mentor and project-memo; no resolution of `{project-name}` without them. |
| Restore defaults match install standard | restore-bmad-config and step-03b-restore use the same project-scoped pattern as install-rbtv. |

---

## Scope

### In Scope

- **rbtv/config.yaml** — Single key `output_folder: "{project-root}/_bmad-output"`; user/language inherited from core.
- **install-rbtv.py** — On run: (1) update core/config.yaml and bmm/config.yaml (output_folder base; planning_artifacts and implementation_artifacts as `_bmad-output/{project-name}/planning-artifacts` and `.../implementation-artifacts`), (2) add rbtv to bmad-help.csv if not present.
- **Mass change in rbtv** — All rbtv workflows and agents that loaded config use `_bmad/rbtv/config.yaml` instead of `_bmad/core/config.yaml`.
- **Restore flow** — restore-bmad-config.xml and bi-m4-design-context step-03b-restore-config.md restore to the same project-scoped pattern (with `{project-name}` literal in config).
- **Documentation** — Readme “Restrictions” section: project-specific output paths require Mentor and project-memo; where project name is set (Step 01, project-memo frontmatter).

### Out of Scope (Current Implementation)

- **Resolving `{project-name}` in BMAD at runtime** — BMAD does not read project name from a shared file; delegation still uses update-bmad-config/restore-bmad-config to inject the full path.
- **Changing BI workflow structure** — BI still builds paths from frontmatter/outputFolder and runtime `{project-name}` from project-memo; no change to when/where project name is set.

---

## Functional Requirements

### FR1: RBTV module config

- **FR1.1** — `_bmad/rbtv/config.yaml` exists with `output_folder: "{project-root}/_bmad-output"`.
- **FR1.2** — Other settings (user_name, communication_language, document_output_language) are inherited from core (rbtv does not duplicate them).

### FR2: Install script config updates

- **FR2.1** — install-rbtv.py updates `_bmad/core/config.yaml`: set `output_folder` to `"{project-root}/_bmad-output"` (preserve other keys).
- **FR2.2** — install-rbtv.py updates `_bmad/bmm/config.yaml`: set `output_folder` to `"{project-root}/_bmad-output"`; set `planning_artifacts` to `"{project-root}/_bmad-output/{project-name}/planning-artifacts"`; set `implementation_artifacts` to `"{project-root}/_bmad-output/{project-name}/implementation-artifacts"` (preserve other keys).
- **FR2.3** — Updates are in-place (read → replace only these keys → write); no overwrite of entire file.

### FR3: Help catalog

- **FR3.1** — install-rbtv.py adds rbtv workflow row(s) to `_bmad/_config/bmad-help.csv` if no rbtv row exists (e.g. Business Innovation entry with module=rbtv, output-location=output_folder, etc.).
- **FR3.2** — Help task step 2 scans `_bmad/` for config.yaml; with rbtv/config.yaml present, it can resolve rbtv output-location for catalog rows.

### FR4: Restore to install standard

- **FR4.1** — restore-bmad-config task restores bmm config to: `output_folder` = `"{project-root}/_bmad-output"`; `planning_artifacts` = `"{project-root}/_bmad-output/{project-name}/planning-artifacts"`; `implementation_artifacts` = `"{project-root}/_bmad-output/{project-name}/implementation-artifacts"`.
- **FR4.2** — step-03b-restore-config.md and restore-bmad-config.xml success messages and instructions use the same pattern.

### FR5: Project name and output path semantics

- **FR5.1** — Project name is set only in Mentor → New Project → Step 01: Project Setup and stored in project-memo.md frontmatter as `projectName`.
- **FR5.2** — RBTV/BMAD do not resolve `{project-name}` from config; when RBTV delegates to BMAD, it uses update-bmad-config to set full path in bmm config, then restore-bmad-config after.
- **FR5.3** — Readme documents that project-specific output paths require Mentor and project-memo; without them, only the base `_bmad-output` is defined for non-BI workflows.

---

## Non-Functional Requirements / Constraints

- **NFR1** — install-rbtv remains idempotent where possible (e.g. help catalog: add rbtv only if not present).
- **NFR2** — No removal of update-bmad-config/restore-bmad-config from delegation workflows in this implementation; they remain required until BMAD can resolve project name from a shared source.

---

## Future Consideration: active-project-config.yaml

**Proposal:** Simplify delegation by introducing a single active-project config at project root so BMAD can resolve `{project-name}` without per-call config overwrite.

- **Concept** — `active-project-config.yaml` initially in rbtv; install-rbtv copies it to `{project-root}` and configures BMAD (e.g. bmm) to read from it (e.g. `active_project_config: "{project-root}/active-project-config.yaml"`). File contains e.g. `project_name: <active-project-name>`.
- **Mentor / project setup** — When user sets or changes project (e.g. Step 01), write project name to `active-project-config.yaml` at project root.
- **BMAD** — BMM (or shared config loader) resolves `{project-name}` from active-project-config when present; no need for RBTV to overwrite bmm config before invoking BMAD.
- **Workflows** — Remove update-bmad-config and restore-bmad-config from delegation flows; single source of truth for active project at repo root; lower token use and fewer steps.

**Dependency:** BMAD (bmm) must support resolving `{project-name}` from an external file (or from a path specified in config). This may require a BMAD-side change.

---

## References

- **rbtv/config.yaml** — `_bmad/rbtv/config.yaml`
- **install script** — `_bmad/rbtv/install-rbtv.py`
- **help task** — `_bmad/core/tasks/help.md` (step 2: resolve output locations)
- **Restore task** — `_bmad/rbtv/tasks/restore-bmad-config.xml`
- **Restore step** — `_bmad/rbtv/workflows/bi-m4-design-context/steps-c/step-03b-restore-config.md`
- **Readme restriction** — `_bmad/rbtv/readme.md` (§ Restrictions)
- **Project name source** — `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md`; project-memo frontmatter `projectName`

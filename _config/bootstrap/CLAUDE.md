---
description: "Core Context file for development of the rbtv Bootstrap package."
---

# CLAUDE.md: BMAD Bootstrap Package

**Role:** This file contains critical context, security boundaries, and the development workflow for AI agents and human developers maintaining the `_config/bootstrap/` package.

---

## CRITICAL RULES

- **Context Management**: ALWAYS use `BootstrapContext` (from `bootstrap.context`) for path resolution. NEVER manually manipulate string paths or use dictionary passing like `paths["rbtv"]` or hardcoded relative imports. `BootstrapContext` is the single source of truth for the environment.
- **Entry Point Enforcement**: The entry point is the thin loader `../bootstrap.py` at the root of `_config/`. NEVER run `__main__.py` directly or attempt to execute any scripts from inside this sub-package directly.
- **Scope Restriction**: NEVER add unrelated functionality to this package. It strictly serves one purpose: handling Workspace, Admin, and Sync configurations for BMAD environments by copying and patching IDE rule directories (`.cursor`, `.claude`, `.agents`).
- **I/O Abstraction**: ALWAYS use the `FileSystemOps`, `FileCleaner`, `FileMerger` and `FileReplicator` classes for any folder manipulations or file copying. Do not use direct `shutil` or `os` commands inside the `workflows/` orchestrators.
- **Dynamic IDE Support**: ALWAY respect the `BootstrapContext.target_ides` array. The build step always stages into a `.claude` caching directory. The `FileReplicator` then loops over the array, creating equivalent structures in `.cursor` or `.agents` (Antigravity). Ensure components are properly translated depending on their destination (e.g., Antigravity uses `.agents/workflows` instead of `commands`).

---

## Core Architecture Overview
If you are modifying functionality, here is the mental model for the package:
1. `cli.py` intercepts the command and generates the `BootstrapContext`.
2. The context is passed to one of the **Workflows** (`WorkspaceWorkflow`, `AdminWorkflow`, etc.).
3. Workflows act as orchestrators. They do not parse files or run copies themselves. Instead, they call out to the **Core** (for YAML parsing/Versioning) and **FS** (for copying/merging/replicating).
4. **Converters** take raw strings from one format (Claude) and return a new string (Cursor), completely independent of the filesystem.

---

## Development Workflow

Follow this strict loop when developing:

1. **Locate Target Logic**:
   - Argument additions go to `cli.py`.
   - File manipulation behaviors go to the `fs/` submodule.
   - Bootstrapping sequences and orchestration go to the `workflows/` submodule.
2. **Execute Locally**:
   - Run the loader locally to verify any CLI parser changes: 
     `python ../bootstrap.py --help`
3. **End-to-End Testing**:
   - Execute your specific mode (e.g. `workspace`) to verify end-to-end behavior:
     `python ../bootstrap.py --mode workspace`
4. **Unit Validation**:
   - If testing parsing logic without mutating the filesystem, consider instantiating specific classes like `YamlParser` or `convert_claude_rule_to_mdc` via the Python REPL to guarantee string-in/dict-out correctness.

# Bootstrap Core Package

Welcome to the `bootstrap` core package! This directory contains the modular, object-oriented implementation of the BMAD RBTV bootstrap system.

The original monolithic 1,800-line script was refactored into this package to improve testability, maintainability, and separation of concerns. This means that instead of one giant top-level script parsing arguments, copying files, and resolving paths simultaneously, the codebase maps directly to clean, distinct layers.

## Understanding the Architecture

The package is broken down into the following domain areas:

- **`cli.py`**: The `argparse` configuration and command-line entry point routing. It determines what mode the user wants, builds the context, and kicks off the correct workflow.
- **`context.py`**: Defines `BootstrapContext`, a dataclass that safely manages and resolves all important filesystem paths needed for execution. By passing `ctx`, any module can safely rely on absolute, correct paths.
- **`core/`**: Non-I/O utilities and global constants.
  - `yaml_parser.py`: A custom, zero-dependency parser for `bootstrap.yaml` files.
  - `constants.py`: Stores static lists like prefix names, Gitignore configurations, and defaults.
  - `version_check.py`: Utilities to ensure the current BMAD version corresponds with the RBTV expectations.
- **`fs/`**: Dedicated submodules that abstract all the standard I/O and file system operations so the workflows can just declare *what* to do, not *how* to do it.
  - `copy.py`: The `copy_folder` recursive copy and config patching logic.
  - `merge.py`: Contains `merge_mcp_json`, `merge_vscode_settings`, and `ensure_gitignore`.
  - `cleanup.py`: Handles deep removal of managed files.
  - `replicate.py`: Combines copying and converting for agents, rules, commands, and skills.
- **`converters/`**: Pure string formatters (`claude_to_mdc.py`, `claude_to_cursor.py`) that translate tool-agnostic configurations to tool-specific metadata (Cursor/Claude Code). They take a string and return a string.
- **`workflows/`**: The orchestrators of the application. The three primary modes (`WorkspaceWorkflow`, `AdminWorkflow`, `SyncWorkflow`) all implement the `BootstrapWorkflow` base interface. These files contain the actual step-by-step logic and print statements previously found in the monolith. Project-level bootstrapping is handled sequentially inside `ProjectBootstrapper`.

## How to Use this Package

This package is completely driven by a "thin loader" placed one directory up (`_config/bootstrap.py`). **Do not run this module or its submodules directly.**

To use the tool, always call the thin loader from your terminal:

```bash
# Display help and available modes
python ../bootstrap.py --help

# Run the standard workspace installation (prompts for IDE targets)
python ../bootstrap.py --mode workspace

# Run an admin-specific installation and auto-select IDEs
python ../bootstrap.py --mode admin --ides claude,cursor,antigravity

# Sync configs only
python ../bootstrap.py --mode sync
```

### Multi-IDE Targeting
By default, the script supports deploying to three primary agentic ecosystems: `claude` (`.claude/`), `cursor` (`.cursor/`), and `antigravity` (`.agents/`).
Workflows initially build their canonical components into a `.claude` staging directory, and the `fs/replicate.py` module converts and mirrors them to your requested `--ides`. If Claude is not one of your selected targets, the `.claude/` staging cache is seamlessly cleaned up before the program exits.

### Modifying the Script
If you wish to change what happens during an Admin install, navigate to `workflows/admin.py`. 
If you wish to configure how Claude rules are translated to Cursor MDC format, modify `converters/claude_to_mdc.py`.
If you wish to update a default path, change it in `core/constants.py`.

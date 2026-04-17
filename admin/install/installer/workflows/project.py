import shutil
from pathlib import Path
from bootstrap.core.constants import BOOTSTRAP_CONFIG_FILENAME
from bootstrap.core.yaml_parser import parse_simple_yaml
from bootstrap.fs.merge import extract_output_folder_name
from bootstrap.utils import print_errors

class ProjectBootstrapper:
    @staticmethod
    def _discover_projects(output_dir: Path) -> list:
        projects = []
        if not output_dir.exists():
            return projects

        for entry in sorted(output_dir.iterdir()):
            if not entry.is_dir():
                continue
            bootstrap_file = entry / BOOTSTRAP_CONFIG_FILENAME
            if not bootstrap_file.exists():
                continue
            try:
                text = bootstrap_file.read_text(encoding="utf-8")
                config = parse_simple_yaml(text)
                projects.append((entry.name, entry, config))
            except Exception as e:
                print(f"  WARNING: Failed to parse {bootstrap_file}: {e}")
                print(f"           Skipping project '{entry.name}'")
        return projects

    @staticmethod
    def _validate_bootstrap_config(project_name: str, config: dict) -> list:
        errors = []
        if "managed_prefix" not in config:
            errors.append(f"'{project_name}': missing required field 'managed_prefix'")
        prefix = config.get("managed_prefix", "")
        if prefix and not prefix.endswith("-"):
            errors.append(
                f"'{project_name}': managed_prefix '{prefix}' must end with '-' "
                f"(e.g. '{prefix}-')"
            )
        install = config.get("install")
        if install is not None and not isinstance(install, dict):
            errors.append(f"'{project_name}': 'install' must be a mapping of component types")
        return errors

    @staticmethod
    def _check_prefix_conflicts(projects: list) -> list:
        seen = {}
        errors = []
        for name, _, config in projects:
            prefix = config.get("managed_prefix", "")
            if not prefix:
                continue
            if prefix in seen:
                errors.append(
                    f"Prefix conflict: '{prefix}' is used by both "
                    f"'{seen[prefix]}' and '{name}'"
                )
            else:
                seen[prefix] = name
        return errors

    @staticmethod
    def _delete_project_managed_files(root: Path, prefix: str) -> dict:
        stats = {"deleted": 0, "errors": []}
        search_dirs = [
            ".claude/skills",
            ".claude/rules",
            ".claude/commands",
            ".claude/agents",
            ".cursor/skills",
            ".cursor/rules",
            ".cursor/commands",
            ".cursor/agents",
        ]
        for rel_dir in search_dirs:
            target_dir = root / rel_dir
            if not target_dir.exists():
                continue
            for entry in target_dir.iterdir():
                if entry.name.startswith(prefix):
                    try:
                        if entry.is_dir():
                            shutil.rmtree(entry)
                        else:
                            entry.unlink()
                        stats["deleted"] += 1
                    except Exception as e:
                        stats["errors"].append(f"{entry.relative_to(root)}: {e}")
        return stats

    @staticmethod
    def _install_component(project_dir: Path, source_rel: str, root: Path, component_dir: str) -> dict:
        stats = {"installed": 0, "errors": []}
        src_dir = project_dir / source_rel
        if not src_dir.exists():
            stats["errors"].append(f"{component_dir.title()} source not found: {src_dir}")
            return stats

        if component_dir == "skills":
            for item in sorted(src_dir.iterdir()):
                if not item.is_dir():
                    continue
                dst = root / ".claude" / "skills" / item.name
                try:
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(str(item), str(dst))
                    stats["installed"] += 1
                except Exception as e:
                    stats["errors"].append(f"{item.name} → .claude/skills/: {e}")
        elif component_dir == "commands":
            for item in sorted(src_dir.rglob("*")):
                if not item.is_file():
                    continue
                rel = item.relative_to(src_dir)
                dst = root / ".claude" / "commands" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(item), str(dst))
                    stats["installed"] += 1
                except Exception as e:
                    stats["errors"].append(f"{rel} → .claude/commands/: {e}")
        else: # rules and agents
            for item in sorted(src_dir.iterdir()):
                if not item.is_file():
                    continue
                dst = root / ".claude" / component_dir / item.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(item), str(dst))
                    stats["installed"] += 1
                except Exception as e:
                    stats["errors"].append(f"{item.name} → .claude/{component_dir}/: {e}")
                    
        return stats

    @classmethod
    def bootstrap_project(cls, project_name: str, project_dir: Path, config: dict, root: Path) -> dict:
        prefix = config.get("managed_prefix", "")
        stats = {"cleaned": 0, "installed": 0, "errors": [], "components": {}}

        if prefix:
            del_stats = cls._delete_project_managed_files(root, prefix)
            stats["cleaned"] = del_stats["deleted"]
            stats["errors"].extend(del_stats.get("errors", []))

        install = config.get("install", {})
        if not isinstance(install, dict):
            return stats

        for component_type, source_config in install.items():
            if component_type not in ("skills", "rules", "commands", "agents"):
                stats["errors"].append(f"Unknown install type: '{component_type}'")
                continue

            source_rel = source_config if isinstance(source_config, str) else source_config.get("source", "")
            if not source_rel:
                stats["errors"].append(f"No source path for '{component_type}'")
                continue

            comp_stats = cls._install_component(project_dir, source_rel, root, component_type)
            installed = comp_stats.get("installed", 0)
            stats["installed"] += installed
            stats["components"][component_type] = installed
            stats["errors"].extend(comp_stats.get("errors", []))

        return stats

    @classmethod
    def run_project_bootstrap(cls, root: Path) -> tuple:
        folder_name = extract_output_folder_name(root)
        output_dir = root / folder_name
        collected_prefixes = []

        print(f"Scanning output folder: {output_dir}")
        print()

        projects = cls._discover_projects(output_dir)
        if not projects:
            print("  No projects with bootstrap.yaml found — skipping project bootstrap")
            return collected_prefixes, 0

        print(f"  Found {len(projects)} project(s) with bootstrap.yaml:")
        for name, _, _ in projects:
            print(f"    - {name}")
        print()

        all_errors = []
        for name, _, config in projects:
            all_errors.extend(cls._validate_bootstrap_config(name, config))
        all_errors.extend(cls._check_prefix_conflicts(projects))

        if all_errors:
            print("  VALIDATION ERRORS — aborting project bootstrap:")
            for err in all_errors:
                print(f"    ERROR: {err}")
            return collected_prefixes, 1

        total_installed = total_cleaned = 0
        
        for name, project_dir, config in projects:
            prefix = config.get("managed_prefix", "")
            if prefix:
                collected_prefixes.append(prefix)

            print(f"  Bootstrapping '{name}' (prefix: {prefix or 'N/A'})...")
            proj_stats = cls.bootstrap_project(name, project_dir, config, root)
            total_cleaned += proj_stats["cleaned"]
            total_installed += proj_stats["installed"]

            if proj_stats["components"]:
                parts = [f"{k}: {v}" for k, v in proj_stats["components"].items() if v > 0]
                if parts:
                    print(f"    Installed to .claude/: {', '.join(parts)}")
            if proj_stats["cleaned"]:
                print(f"    Cleaned: {proj_stats['cleaned']} old files")
            print_errors(proj_stats.get("errors", []))

        print()
        print(f"  Project bootstrap complete: {total_installed} files installed to .claude/, {total_cleaned} old files cleaned")
        return collected_prefixes, 0

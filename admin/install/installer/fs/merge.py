import csv
import json
import re
from pathlib import Path

from bootstrap.core.constants import ADMIN_GITIGNORE_LEGACY_MAP, ADMIN_GITIGNORE_ENTRIES

def extract_output_folder_name(root: Path) -> str:
    core_config = root / "_bmad" / "core" / "config.yaml"
    if not core_config.exists():
        return "projects"
    try:
        content = core_config.read_text(encoding="utf-8")
        match = re.search(r'output_folder:\s*"([^"]*)"', content)
        if not match:
            return "projects"
        path_value = match.group(1)
        folder = path_value.replace("{project-root}/", "").replace("/{project-name}", "")
        return folder if folder else "projects"
    except Exception:
        return "projects"

class FileMerger:
    @staticmethod
    def merge_mcp_json(src_mcp: Path, dst_mcp: Path) -> dict:
        stats = {"merged": 0, "added": 0, "errors": []}
        if not src_mcp.exists():
            return {"skipped": 1, "reason": "source mcp.json does not exist"}
        try:
            with open(src_mcp, "r", encoding="utf-8") as f:
                src_config = json.load(f)
            dst_config = {"mcpServers": {}}
            if dst_mcp.exists():
                with open(dst_mcp, "r", encoding="utf-8") as f:
                    dst_config = json.load(f)
            dst_config.setdefault("mcpServers", {})
            for name, cfg in src_config.get("mcpServers", {}).items():
                key = "merged" if name in dst_config["mcpServers"] else "added"
                stats[key] += 1
                dst_config["mcpServers"][name] = cfg
            dst_mcp.parent.mkdir(parents=True, exist_ok=True)
            with open(dst_mcp, "w", encoding="utf-8") as f:
                json.dump(dst_config, f, indent=2)
        except Exception as e:
            stats["errors"].append(f"mcp.json merge failed: {e}")
        return stats

    @staticmethod
    def merge_vscode_settings(config_dir: Path, root: Path) -> dict:
        src = config_dir / ".vscode" / "settings.json"
        dst_vscode = root / ".vscode"
        dst = dst_vscode / "settings.json"
        if not src.exists():
            return {"skipped": 1, "reason": "source .vscode/settings.json does not exist"}
        if dst_vscode.exists():
            return {"skipped": 1, "reason": ".vscode/ already exists — leaving untouched"}
        try:
            with open(src, "r", encoding="utf-8") as f:
                settings = json.load(f)
            dst_vscode.mkdir(parents=True, exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            return {"created": 1}
        except Exception as e:
            return {"errors": [f".vscode/settings.json creation failed: {e}"]}

    @staticmethod
    def merge_cursorignore(root: Path) -> dict:
        stats = {"added": 0, "skipped": 0, "errors": []}
        dst = root / ".cursorignore"
        folder_name = extract_output_folder_name(root)
        rbtv_patterns = [f"{folder_name}/archive/"]
        try:
            existing = set()
            content = ""
            if dst.exists():
                content = dst.read_text(encoding="utf-8")
                existing = {ln.strip() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")}
            to_add = [p for p in rbtv_patterns if p not in existing]
            if to_add:
                if content and not content.endswith("\n"):
                    content += "\n"
                header = "\n# RBTV-managed patterns\n" if content else "# RBTV-managed patterns\n"
                with open(dst, "a", encoding="utf-8") as f:
                    f.write(header)
                    for p in to_add:
                        f.write(f"{p}\n")
                stats["added"] += len(to_add)
            else:
                stats["skipped"] += len(rbtv_patterns)
        except Exception as e:
            stats["errors"].append(f".cursorignore merge failed: {e}")
        return stats

    @staticmethod
    def normalize_bmad_output_paths(root: Path) -> dict:
        stats = {"updated": 0, "errors": []}
        folder_name = extract_output_folder_name(root)

        core_config = root / "_bmad" / "core" / "config.yaml"
        if core_config.exists():
            try:
                content = core_config.read_text(encoding="utf-8")
                content = re.sub(
                    r'output_folder:\s*"[^"]*"',
                    f'output_folder: "{{project-root}}/{folder_name}/{{project-name}}"',
                    content
                )
                core_config.write_text(content, encoding="utf-8")
                stats["updated"] += 1
            except Exception as e:
                stats["errors"].append(f"core/config.yaml: {e}")

        bmm_config = root / "_bmad" / "bmm" / "config.yaml"
        if bmm_config.exists():
            try:
                content = bmm_config.read_text(encoding="utf-8")
                content = re.sub(
                    r'output_folder:\s*"[^"]*"',
                    f'output_folder: "{{project-root}}/{folder_name}/{{project-name}}"',
                    content
                )
                content = re.sub(
                    r'planning_artifacts:\s*"[^"]*"',
                    f'planning_artifacts: "{{project-root}}/{folder_name}/{{project-name}}/planning-artifacts"',
                    content
                )
                content = re.sub(
                    r'implementation_artifacts:\s*"[^"]*"',
                    f'implementation_artifacts: "{{project-root}}/{folder_name}/{{project-name}}/implementation-artifacts"',
                    content
                )
                bmm_config.write_text(content, encoding="utf-8")
                stats["updated"] += 1
            except Exception as e:
                stats["errors"].append(f"bmm/config.yaml: {e}")

        rbtv_config = root / "_bmad" / "rbtv" / "_config" / "config.yaml"
        if rbtv_config.exists():
            try:
                content = rbtv_config.read_text(encoding="utf-8")
                content = re.sub(
                    r'(bmad_output:\s*)"[^"]*"',
                    f'\\1"{{project-root}}/{folder_name}"',
                    content
                )
                rbtv_config.write_text(content, encoding="utf-8")
                stats["updated"] += 1
            except Exception as e:
                stats["errors"].append(f"rbtv/_config/config.yaml: {e}")

        return stats

    @staticmethod
    def add_rbtv_to_help_catalog(root: Path) -> dict:
        stats = {"added": 0, "errors": []}
        help_csv = root / "_bmad" / "_config" / "bmad-help.csv"
        if not help_csv.exists():
            stats["errors"].append("bmad-help.csv not found")
            return stats
        try:
            with open(help_csv, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                fieldnames = reader.fieldnames
            if any(row.get("module") == "rbtv" for row in existing_rows):
                return stats
            rbtv_rows = [{
                "module": "rbtv",
                "phase": "anytime",
                "name": "Business Innovation",
                "code": "BI",
                "sequence": "10",
                "workflow-file": "_bmad/rbtv/workflows/bi-business-innovation/workflow.md",
                "command": "bmad-rbtv-mentor",
                "required": "false",
                "agent-name": "mentor",
                "agent-command": "bmad-rbtv-mentor",
                "agent-display-name": "Mentor",
                "agent-title": "🚀 YC Mentor",
                "options": "",
                "description": "Guide users through 6-milestone business innovation lifecycle from idea to MVP",
                "output-location": "output_folder",
                "outputs": "project-memo",
            }]
            with open(help_csv, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows + rbtv_rows)
            stats["added"] = len(rbtv_rows)
        except Exception as e:
            stats["errors"].append(f"Failed to update help catalog: {e}")
        return stats

    @staticmethod
    def admin_ensure_gitignore(rbtv_dir: Path) -> dict:
        gitignore = rbtv_dir / ".gitignore"
        stats = {"added": 0, "already_present": 0, "migrated": 0}
        content = ""
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")

        lines = content.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in ADMIN_GITIGNORE_LEGACY_MAP:
                new_lines.append(line.replace(stripped, ADMIN_GITIGNORE_LEGACY_MAP[stripped], 1))
                stats["migrated"] += 1
            else:
                new_lines.append(line)
        content = "".join(new_lines)

        existing = {ln.strip() for ln in content.splitlines()}
        missing = [e for e in ADMIN_GITIGNORE_ENTRIES if e not in existing]
        stats["already_present"] = len(ADMIN_GITIGNORE_ENTRIES) - len(missing)
        stats["added"] = len(missing)
        if missing or stats["migrated"]:
            if missing:
                if content and not content.endswith("\n"):
                    content += "\n"
                header = "\n# Added by bootstrap.py (admin mode)\n" if content else "# Generated by bootstrap.py\n"
                content += header + "\n".join(missing) + "\n"
            gitignore.write_text(content, encoding="utf-8")
        return stats

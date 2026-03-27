import shutil
from pathlib import Path
from bootstrap.fs.copy import matches_prefix
from bootstrap.converters.claude_to_mdc import convert_claude_rule_to_mdc
from bootstrap.converters.claude_to_cursor import convert_claude_agent_to_cursor

class FileReplicator:
    @staticmethod
    def _get_dst_path(root: Path, ide_name: str, component_type: str) -> Path:
        base = ".claude"
        if ide_name == "cursor":
            base = ".cursor"
        elif ide_name == "antigravity":
            base = ".agents"
            
        # Antigravity maps commands to workflows
        if ide_name == "antigravity" and component_type == "commands":
            return root / base / "workflows"
        
        return root / base / component_type

    @classmethod
    def replicate_commands(cls, root: Path, prefixes: tuple, ide_name: str) -> dict:
        stats = {"copied": 0, "replaced": 0, "errors": []}
        src = root / ".claude" / "commands"
        dst = cls._get_dst_path(root, ide_name, "commands")
        
        if not src.exists():
            return {"skipped": 1, "reason": ".claude/commands/ does not exist"}
        dst.mkdir(parents=True, exist_ok=True)
        
        for src_file in src.rglob("*"):
            if not src_file.is_file():
                continue
            if not matches_prefix(src_file.name, prefixes):
                continue
            rel_path = src_file.relative_to(src)
            dst_file = dst / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                existed = dst_file.exists()
                shutil.copy2(str(src_file), str(dst_file))
                stats["replaced" if existed else "copied"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
        return stats

    @classmethod
    def replicate_rules(cls, root: Path, prefixes: tuple, ide_name: str) -> dict:
        stats = {"copied": 0, "replaced": 0, "errors": []}
        src = root / ".claude" / "rules"
        dst = cls._get_dst_path(root, ide_name, "rules")
        
        if not src.exists():
            return {"skipped": 1, "reason": ".claude/rules/ does not exist"}
        dst.mkdir(parents=True, exist_ok=True)
        
        for src_file in src.rglob("*"):
            if not src_file.is_file():
                continue
            if not matches_prefix(src_file.name, prefixes):
                continue
            rel_path = src_file.relative_to(src)
            
            dst_name = rel_path
            if ide_name == "cursor" and rel_path.suffix == ".md":
                dst_name = rel_path.with_suffix(".mdc")
                
            dst_file = dst / dst_name
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                existed = dst_file.exists()
                content = src_file.read_text(encoding="utf-8")
                
                if ide_name == "cursor" and src_file.suffix == ".md":
                    content = convert_claude_rule_to_mdc(content)
                    
                dst_file.write_text(content, encoding="utf-8")
                stats["replaced" if existed else "copied"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
        return stats

    @classmethod
    def replicate_agents(cls, root: Path, prefixes: tuple, ide_name: str) -> dict:
        stats = {"copied": 0, "replaced": 0, "errors": []}
        src = root / ".claude" / "agents"
        dst = cls._get_dst_path(root, ide_name, "agents")
        
        if not src.exists():
            return {"skipped": 1, "reason": ".claude/agents/ does not exist"}
        dst.mkdir(parents=True, exist_ok=True)
        
        for src_file in src.rglob("*"):
            if not src_file.is_file():
                continue
            if not matches_prefix(src_file.name, prefixes):
                continue
            rel_path = src_file.relative_to(src)
            dst_file = dst / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                existed = dst_file.exists()
                content = src_file.read_text(encoding="utf-8")
                
                if ide_name == "cursor":
                    content = convert_claude_agent_to_cursor(content)
                    
                dst_file.write_text(content, encoding="utf-8")
                stats["replaced" if existed else "copied"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
        return stats

    @classmethod
    def replicate_skills(cls, root: Path, prefixes: tuple, ide_name: str) -> dict:
        stats = {"copied": 0, "replaced": 0, "errors": []}
        src = root / ".claude" / "skills"
        dst = cls._get_dst_path(root, ide_name, "skills")
        
        if not src.exists():
            return {"skipped": 1, "reason": ".claude/skills/ does not exist"}
        dst.mkdir(parents=True, exist_ok=True)
        
        for src_file in src.rglob("*"):
            if not src_file.is_file():
                continue
            rel_path = src_file.relative_to(src)
            top_level_name = rel_path.parts[0]
            if not matches_prefix(top_level_name, prefixes):
                continue
            dst_file = dst / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                existed = dst_file.exists()
                shutil.copy2(str(src_file), str(dst_file))
                stats["replaced" if existed else "copied"] += 1
            except Exception as e:
                stats["errors"].append(f"{rel_path}: {e}")
        return stats

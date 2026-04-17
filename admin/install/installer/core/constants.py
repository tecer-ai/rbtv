WORKSPACE_RBTV_SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
    ".claude/commands",
    ".claude/rules",
    ".claude/agents",
    ".claude/skills",
]

ADMIN_MANAGED_PREFIXES = ("bmad-rbtv", "admin-rbtv")

ADMIN_SEARCH_DIRS = [
    ".cursor/commands",
    ".cursor/agents",
    ".cursor/skills",
    ".cursor/rules",
    ".claude/commands",
    ".claude/rules",
    ".claude/agents",
    ".claude/skills",
]

ADMIN_EXTRA_MANAGED_FILES = [
    ".cursor/mcp.json",
    ".claude/.mcp.json",
]

ADMIN_PATH_FIND = "{project-root}/_bmad/rbtv/"
ADMIN_PATH_REPLACE = ""

ADMIN_REINFORCEMENT = (
    "\n\n> **ADMIN MODE:** Before proceeding, load and read "
    "`.claude/rules/admin-rbtv-bmad-mirror.md` for path resolution "
    "and config values. Key: `.claude/` and `tasks/` are at workspace root.\n"
)

ADMIN_RULE_FILE = "admin-rbtv-bmad-mirror.md"

ADMIN_GITIGNORE_ENTRIES = [
    "/.cursor/",
    "/.claude/",
    "/CLAUDE.md",
    "/agents/fernando/workflows/create-component/data/CLAUDE.md",
    ".gitignore",
    ".claude/memory/",
]

ADMIN_GITIGNORE_LEGACY_MAP = {
    ".cursor/": "/.cursor/",
    ".claude/": "/.claude/",
}

ADMIN_CONFIG_DEFAULTS = {
    "user_name": "",
    "communication_language": "English",
    "document_output_language": "English",
}

BOOTSTRAP_CONFIG_FILENAME = "bootstrap.yaml"

PROTECTED_SUBDIRS = {"memory"}
